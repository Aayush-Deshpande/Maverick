"""API v1 (card M0-06; DECISIONS D3, D7; P Part 4 Steps 0.5 and 0.8).

REST under /api/v1 and ONE WebSocket per client at /ws/v1. A client sends {"subscribe": "<engine_id>"} (or a list,
or "fleet") and receives StateMessage JSON for its engines. Every surface (console, 3D, Blender app, phone, voice)
injects and clears faults through the same FaultManager per engine, so a fault injected anywhere appears in every
client's next message.

Broadcast: one asyncio task builds each engine's message once per new tick and puts it into a per-client queue of
size 1 (latest only: an unread older message is dropped and counted), with a send timeout so a slow client never
delays the others (T-WS-1). This module never simulates: it reads RuntimeHub.latest (the hub owns the clock).
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.faults.manager import FaultManager, RuntimeAdapter
from backend.sim.maps import maps_for
from backend.faults.registry import FaultRejected, load_fault_registry
from backend.physics.engine_config import load_engine_config
from backend.maintenance.work_orders import WorkOrderStore
from backend.mission.executive import list_missions
from backend.recording.recorder import list_recordings, read_states, recordings_dir
from backend.recording.replay import compare
from backend.reports.sortie_report import write_report
from backend.server.security import COMMAND_LOG, command_guard
from backend.server.state_builder import build_state

router = APIRouter()

# Fail fast: an invalid fault registry stops the server at import (T-CFG-1).
REGISTRY = load_fault_registry()

SEND_TIMEOUT_S = 2.0
BROADCAST_POLL_S = 0.02


# ---------------------------------------------------------------------------------------------------------------
# Per-engine services: fault manager + message sequencing
# ---------------------------------------------------------------------------------------------------------------

@dataclass
class EngineChannel:
    engine_id: str
    manager: FaultManager
    seq: int = 0
    last_t: Optional[float] = None
    last_wall: Optional[float] = None
    rate_hz: Optional[float] = None
    last_message: Optional[str] = None
    pending_events: List[Any] = field(default_factory=list)


class Services:
    def __init__(self, hub: Any, work_orders: Optional[WorkOrderStore] = None):
        self.hub = hub
        self.channels: Dict[str, EngineChannel] = {}
        self._lock = threading.Lock()
        self.work_orders = work_orders or WorkOrderStore()      # one store per simulation owner (var/maintenance)
        for rt in hub.runtimes.values():
            rt.work_orders = self.work_orders

    def channel(self, engine_id: str) -> EngineChannel:
        with self._lock:
            if engine_id not in self.channels:
                if engine_id not in self.hub.runtimes:
                    raise HTTPException(404, f"unknown engine {engine_id!r}; have {sorted(self.hub.runtimes)}")
                rt = self.hub.runtimes[engine_id]
                ch = EngineChannel(engine_id, manager=None)  # type: ignore[arg-type]
                ch.manager = FaultManager(REGISTRY, rt.cfg, RuntimeAdapter(rt), on_event=ch.pending_events.append)
                self.channels[engine_id] = ch
            return self.channels[engine_id]

    def build_message(self, engine_id: str) -> Optional[str]:
        """Build the next message if the engine produced a new tick; None otherwise."""
        ch = self.channel(engine_id)
        tick = self.hub.latest.get(engine_id)
        if tick is None or tick.frame.t == ch.last_t:
            return None
        now = time.perf_counter()
        if ch.last_t is not None and ch.last_wall is not None and now > ch.last_wall:
            inst = 1.0 / (now - ch.last_wall)
            ch.rate_hz = inst if ch.rate_hz is None else 0.9 * ch.rate_hz + 0.1 * inst
        ch.last_t, ch.last_wall = tick.frame.t, now
        ch.seq += 1
        events, ch.pending_events[:] = list(ch.pending_events), []
        lv = getattr(self.hub.runtimes.get(engine_id), "levers", None)
        levers = None if lv is None else {"throttle": tick.frame.throttle, "throttle_target": lv.throttle_target,
                                          "altitude_target_ft": lv.altitude_target, "oat_target_c": lv.oat_target}
        msg = build_state(tick, ch.seq, registry=REGISTRY, active_faults=ch.manager.active(), fault_events=events,
                          rate_hz_actual=None if ch.rate_hz is None else round(ch.rate_hz, 2), levers=levers,
                          maintenance=self.work_orders.open_orders(engine_id))
        ch.last_message = msg.model_dump_json()
        rec = getattr(self.hub.runtimes.get(engine_id), "recorder", None)
        if rec is not None:
            rec.add_state(ch.last_message)                       # M5-04: what the operator saw, for replay
        return ch.last_message


_services: Optional[Services] = None


def services() -> Services:
    global _services
    if _services is None:
        from backend.server.engine_api import get_hub  # the single hub (one simulation owner)
        _services = Services(get_hub())
    return _services


# ---------------------------------------------------------------------------------------------------------------
# REST
# ---------------------------------------------------------------------------------------------------------------

class FaultRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fault_id: str = Field(description="F01..F37 or S01..S07 (configs/faults.json)")
    cylinder: Optional[int] = None
    channel: Optional[str] = None
    severity: Optional[float] = None
    ramp_s: Optional[float] = None
    source: str = "api"
    request_id: Optional[str] = None


class LeverRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    throttle_pct: Optional[float] = Field(default=None, ge=0, le=100)
    altitude_ft: Optional[float] = Field(default=None, ge=-1000, le=40000)
    oat_c: Optional[float] = Field(default=None, ge=-60, le=60)


class AlertCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alert_id: Optional[str] = Field(default=None, max_length=200, description="omit to acknowledge every alert")
    duration_s: Optional[float] = Field(default=None, gt=0, le=86400)


class RecordingCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["START", "STOP"]


class MissionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["START", "ABORT"]
    mission_id: Optional[str] = Field(default=None, min_length=1, max_length=80, pattern=r"^[a-z0-9_]+$")


class WorkOrderCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to: Literal["IN_WORK", "SIGNED_OFF"]
    by: Optional[str] = Field(default=None, min_length=1, max_length=80, description="person signing (needed to sign off)")
    note: Optional[str] = Field(default=None, max_length=500)


class EngineCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: Literal["START", "STOP", "RESET"]


class GeoPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    altitude_ft: Optional[float] = Field(default=None, ge=-1000.0, le=36000.0)


class RouteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    engine_id: str
    start: GeoPoint
    goal: GeoPoint
    isa_dev_c: float = Field(default=0.0, ge=-40.0, le=40.0)
    power_factor: Optional[float] = Field(default=None, ge=0.0, le=1.0)   # None: from the engine's measured frame


def _reject(exc: FaultRejected) -> HTTPException:
    return HTTPException(status_code=422, detail={"code": "FAULT_REJECTED", "message": str(exc)})


@router.get("/api/v1/engines")
def v1_engines() -> Dict[str, Any]:
    hub = services().hub
    out = []
    for engine_id, rt in hub.runtimes.items():
        cfg = rt.cfg
        out.append({"engine_id": engine_id, "display_name": cfg.display_name, "manufacturer": cfg.manufacturer,
                    "ignition_mode": cfg.ignition_mode, "induction": cfg.induction, "fuel_system": cfg.fuel_system,
                    "cylinders": cfg.cylinder_count, "ready": bool(getattr(rt, "ready", False))})
    return {"engines": out}


@router.get("/api/v1/engines/{engine_id}/config")
def v1_engine_config(engine_id: str) -> Dict[str, Any]:
    services().channel(engine_id)
    return load_engine_config(engine_id).to_dict()


@router.get("/api/v1/engines/{engine_id}/maps")
def v1_engine_maps(engine_id: str) -> Dict[str, Any]:
    """Performance maps of the calibrated plant (backend/sim/maps.py; evidence SIMULATION)."""
    services().channel(engine_id)
    return maps_for(load_engine_config(engine_id))


@router.get("/api/v1/faults")
def v1_faults(engine: Optional[str] = None) -> Dict[str, Any]:
    if engine is None:
        return {"faults": [f.raw for f in REGISTRY.all()]}
    cfg = load_engine_config(engine) if engine in services().hub.runtimes else None
    if cfg is None:
        raise HTTPException(404, f"unknown engine {engine!r}")
    return {"engine_id": engine, "faults": [f.raw for f in REGISTRY.applicable(cfg)]}


@router.get("/api/v1/engines/{engine_id}/faults")
def v1_active_faults(engine_id: str) -> Dict[str, Any]:
    ch = services().channel(engine_id)
    return {"engine_id": engine_id, "active": [f.to_dict() for f in ch.manager.active()]}


@router.post("/api/v1/engines/{engine_id}/faults")
def v1_inject(engine_id: str, body: FaultRequest, cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    cmd.update(request_id=body.request_id, source=body.source)
    ch = services().channel(engine_id)
    try:
        f = ch.manager.inject(body.fault_id, cylinder=body.cylinder, channel=body.channel, severity=body.severity,
                              ramp_s=body.ramp_s, source=body.source, request_id=body.request_id)
    except FaultRejected as exc:
        raise _reject(exc) from None
    return {"engine_id": engine_id, "fault": f.to_dict()}


@router.delete("/api/v1/engines/{engine_id}/faults/{fault_uuid}")
def v1_clear_one(engine_id: str, fault_uuid: str, source: str = "api",
                 cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    cmd.update(source=source)
    ch = services().channel(engine_id)
    try:
        cleared = ch.manager.clear(fault_uuid, source=source)
    except FaultRejected as exc:
        raise HTTPException(404, {"code": "NOT_FOUND", "message": str(exc)}) from None
    return {"engine_id": engine_id, "cleared": [f.to_dict() for f in cleared]}


@router.delete("/api/v1/engines/{engine_id}/faults")
def v1_clear_all(engine_id: str, source: str = "api", cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    cmd.update(source=source)
    ch = services().channel(engine_id)
    return {"engine_id": engine_id, "cleared": [f.to_dict() for f in ch.manager.clear(source=source)]}


@router.post("/api/v1/engines/{engine_id}/levers")
def v1_levers(engine_id: str, body: LeverRequest, cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    services().channel(engine_id)
    rt = services().hub.runtimes[engine_id]
    kw = {}
    if body.throttle_pct is not None:
        kw["throttle"] = body.throttle_pct
    if body.altitude_ft is not None:
        kw["altitude_ft"] = body.altitude_ft
    if body.oat_c is not None:
        kw["oat_c"] = body.oat_c
    return {"engine_id": engine_id, "targets": rt.set_levers(**kw)}


@router.post("/api/v1/engines/{engine_id}/engine")
def v1_engine_command(engine_id: str, body: EngineCommand, cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    """Engine state machine (M1-12): START (crank), STOP (fuel off), RESET (after a failure, R 19.4)."""
    services().channel(engine_id)
    return {"engine_id": engine_id, **services().hub.runtimes[engine_id].engine_command(body.command)}


@router.post("/api/v1/engines/{engine_id}/status/acknowledge")
def v1_status_ack(engine_id: str, cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    """Acknowledge a latched NO-GO; it clears once its cause has also cleared (P Step 2.2)."""
    services().channel(engine_id)
    services().hub.runtimes[engine_id].status_evaluator.acknowledge()
    return {"engine_id": engine_id, "acknowledged": True}


@router.post("/api/v1/engines/{engine_id}/alerts/acknowledge")
def v1_alert_ack(engine_id: str, body: AlertCommand, cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    services().channel(engine_id)
    rt = services().hub.runtimes[engine_id]
    try:
        ids = rt.alert_manager.acknowledge(body.alert_id)
    except KeyError:
        raise HTTPException(404, {"code": "NO_SUCH_ALERT", "message": f"no alert {body.alert_id!r}"}) from None
    if any(a.level == "NO-GO" for a in rt.alert_manager.alerts.values()) or body.alert_id is None:
        rt.status_evaluator.acknowledge()                     # acknowledging the warning also releases the latch
    return {"engine_id": engine_id, "acknowledged": ids}


@router.post("/api/v1/engines/{engine_id}/recording")
def v1_recording(engine_id: str, body: RecordingCommand, cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    services().channel(engine_id)
    rt = services().hub.runtimes[engine_id]
    return {"engine_id": engine_id, "recording": rt.start_recording() if body.action == "START" else rt.stop_recording()}


@router.get("/api/v1/recordings")
def v1_recordings() -> Dict[str, Any]:
    return {"recordings": list_recordings()}


def _sortie_dir(sortie_id: str):
    d = recordings_dir() / sortie_id
    if not sortie_id.replace("-", "").replace("_", "").isalnum() or not (d / "meta.json").exists():
        raise HTTPException(404, {"code": "NO_SUCH_RECORDING", "message": f"no recording {sortie_id!r}"})
    return d


@router.get("/api/v1/recordings/{sortie_id}/states")
def v1_recording_states(sortie_id: str, offset: int = Query(0, ge=0), limit: int = Query(200, ge=1, le=2000)) -> Dict[str, Any]:
    """Replay: the recorded state messages, page by page, flagged as replay (the UI shows a REPLAY badge)."""
    return {"sortie_id": sortie_id, "source": "REPLAY", "offset": offset,
            "states": read_states(_sortie_dir(sortie_id), offset, limit)}


@router.get("/api/v1/recordings/{sortie_id}/report", response_class=HTMLResponse)
def v1_recording_report(sortie_id: str) -> HTMLResponse:
    """Sortie health report (M5-06), generated from the recording on first request."""
    d = _sortie_dir(sortie_id)
    path = d / "report.html"
    if not path.exists():
        path = write_report(d)
    return HTMLResponse(path.read_text(encoding="utf-8"))


@router.post("/api/v1/recordings/{sortie_id}/reanalyse")
def v1_recording_reanalyse(sortie_id: str, cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    d = _sortie_dir(sortie_id)
    return compare(d, json.loads((d / "meta.json").read_text(encoding="utf-8")))


@router.get("/api/v1/missions")
def v1_missions() -> Dict[str, Any]:
    return {"missions": list_missions()}


@router.post("/api/v1/engines/{engine_id}/mission")
def v1_mission(engine_id: str, body: MissionCommand, cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    services().channel(engine_id)
    rt = services().hub.runtimes[engine_id]
    if body.action == "ABORT":
        return {"engine_id": engine_id, "mission": rt.abort_mission()}
    if not body.mission_id:
        raise HTTPException(422, {"code": "MISSION_REJECTED", "message": "START needs mission_id"})
    try:
        return {"engine_id": engine_id, "mission": rt.start_mission(body.mission_id)}
    except KeyError:
        raise HTTPException(404, {"code": "NO_SUCH_MISSION", "message": f"no mission {body.mission_id!r}"}) from None
    except ValueError as e:
        raise HTTPException(422, {"code": "MISSION_REJECTED", "message": str(e)}) from None


@router.get("/api/v1/engines/{engine_id}/work_orders")
def v1_work_orders(engine_id: str, status: Optional[Literal["OPEN", "IN_WORK", "SIGNED_OFF"]] = None) -> Dict[str, Any]:
    services().channel(engine_id)
    return {"engine_id": engine_id, "work_orders": services().work_orders.list(engine_id, status)}


@router.post("/api/v1/work_orders/{wo_id}/transition")
def v1_work_order_transition(wo_id: str, body: WorkOrderCommand, cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    store = services().work_orders
    try:
        wo = store.transition(wo_id, body.to, body.by, body.note)
    except KeyError:
        raise HTTPException(404, {"code": "NO_SUCH_WORK_ORDER", "message": f"no work order {wo_id!r}"}) from None
    except ValueError as e:
        raise HTTPException(409, {"code": "TRANSITION_REJECTED", "message": str(e)}) from None
    repaired = 0
    rt = services().hub.runtimes.get(wo["engine_id"])
    if body.to == "SIGNED_OFF" and rt is not None and wo["fault_id"]:
        # simulated repair of the signed-off fault: through the fault manager (events, active list), then the runtime
        # removes anything injected directly and restarts inference on the repaired engine
        ch = services().channel(wo["engine_id"])
        for f in [f for f in ch.manager.active() if f.fault_id == wo["fault_id"]]:
            repaired += len(ch.manager.clear(f.uuid, source="maintenance"))
        repaired += rt.complete_repair(wo["fault_id"])
    return {"work_order": wo, "repaired_plant_faults": repaired, "events": store.events(wo_id)}


@router.post("/api/v1/engines/{engine_id}/alerts/shelve")
def v1_alert_shelve(engine_id: str, body: AlertCommand, cmd: Dict[str, Any] = Depends(command_guard)) -> Dict[str, Any]:
    services().channel(engine_id)
    rt = services().hub.runtimes[engine_id]
    if not body.alert_id or body.duration_s is None:
        raise HTTPException(422, {"code": "SHELVE_REJECTED", "message": "shelve needs alert_id and duration_s"})
    try:
        a = rt.alert_manager.shelve(body.alert_id, rt.source.now(), body.duration_s)
    except KeyError:
        raise HTTPException(404, {"code": "NO_SUCH_ALERT", "message": f"no alert {body.alert_id!r}"}) from None
    except ValueError as exc:
        raise HTTPException(422, {"code": "SHELVE_REJECTED", "message": str(exc)}) from None
    return {"engine_id": engine_id, "alert": a.to_dict()}


@router.get("/api/v1/commands")
def v1_commands(limit: int = 100) -> Dict[str, Any]:
    """Recent command log (D52): who sent what, with request_id and result. Newest last."""
    items = list(COMMAND_LOG)[-max(1, limit):]
    return {"commands": items}


def _terrain_tile():
    from backend.planning.performance import planning_config
    from backend.terrain.dem import TerrainUnavailable, load_tile
    try:
        return load_tile(planning_config()["dem"]["tile"])
    except TerrainUnavailable as e:
        raise HTTPException(503, {"code": "TERRAIN_UNAVAILABLE", "message": str(e)}) from None


@router.get("/api/v1/terrain/elevation")
def v1_terrain_elevation(lat: float = Query(ge=-90.0, le=90.0), lon: float = Query(ge=-180.0, le=180.0)) -> Dict[str, Any]:
    """Copernicus GLO-30 elevation (M5-07); 503 TERRAIN_UNAVAILABLE when the tile is not downloaded."""
    tile = _terrain_tile()
    if not tile.contains(lat, lon):
        raise HTTPException(422, {"code": "OUTSIDE_TERRAIN", "message": f"({lat}, {lon}) is outside {tile.name}",
                                  "bounds": tile.bounds})
    return {"lat": lat, "lon": lon, "elevation_m": round(tile.elevation_m(lat, lon), 1), "tile": tile.name,
            "source": "Copernicus GLO-30 DSM"}


@router.post("/api/v1/planning/route")
def v1_plan_route(body: RouteRequest) -> Dict[str, Any]:
    """Terrain route with engine-health feasibility (M5-08, T-MIS-6). Read-only: it commands nothing.
    Without power_factor the engine's latest MEASURED frame sets it (nominal model MAP/rpm ratio); an engine with no
    running frame gives 409 instead of an assumed healthy engine."""
    from backend.planning.performance import power_factor_for_frame
    services().channel(body.engine_id)
    tile = _terrain_tile()
    if body.power_factor is not None:
        pf, source = body.power_factor, {"kind": "OPERATOR"}
    else:
        tick = services().hub.latest.get(body.engine_id)
        frame = None if tick is None else tick.frame
        pf, ratios = (None, {}) if frame is None or not frame.rpm else power_factor_for_frame(body.engine_id, frame)
        if pf is None:
            raise HTTPException(409, {"code": "NO_POWER_EVIDENCE", "message": f"{body.engine_id} has no running "
                                      "measured frame to estimate available power; pass power_factor explicitly"})
        source = {"kind": "MEASURED", "ratios": {k: round(v, 4) for k, v in ratios.items()}, "sim_time_s": frame.t}
    start_alt = body.start.altitude_ft
    if start_alt is None:
        raise HTTPException(422, {"code": "ROUTE_REJECTED", "message": "start.altitude_ft is required"})
    plan = _planner(tile.name).plan(body.engine_id, (body.start.lat, body.start.lon, start_alt),
                                    (body.goal.lat, body.goal.lon), pf, body.isa_dev_c)
    return {**plan.as_dict(), "power_factor_source": source, "terrain": tile.name, "evidence_class": "SIMULATION"}


_PLANNERS: Dict[str, Any] = {}


def _planner(tile_name: str) -> Any:
    from backend.planning.planner import Planner
    from backend.terrain.dem import load_tile
    if tile_name not in _PLANNERS:
        _PLANNERS[tile_name] = Planner(load_tile(tile_name))
    return _PLANNERS[tile_name]


@router.get("/api/v1/engines/{engine_id}/state")
def v1_state(engine_id: str) -> Any:
    ch = services().channel(engine_id)
    msg = services().build_message(engine_id) or ch.last_message
    if msg is None:
        raise HTTPException(503, {"code": "CALIBRATING", "message": f"{engine_id} has no tick yet"})
    return json.loads(msg)


# ---------------------------------------------------------------------------------------------------------------
# WebSocket fan-out
# ---------------------------------------------------------------------------------------------------------------

@dataclass
class Client:
    ws: WebSocket
    id: str
    engines: Set[str] = field(default_factory=set)
    queue: "asyncio.Queue[str]" = field(default_factory=lambda: asyncio.Queue(maxsize=1))
    dropped: int = 0

    def offer(self, message: str) -> None:
        """Latest-only: if the previous message was not sent yet, replace it and count the drop."""
        if self.queue.full():
            try:
                self.queue.get_nowait()
                self.dropped += 1
            except asyncio.QueueEmpty:
                pass
        self.queue.put_nowait(message)


class Broadcaster:
    def __init__(self) -> None:
        self.clients: Dict[str, Client] = {}
        self._task: Optional[asyncio.Task] = None

    def ensure_running(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(self._run())

    async def _run(self) -> None:
        while self.clients:
            wanted = set().union(*(c.engines for c in self.clients.values())) if self.clients else set()
            services().hub.set_active(wanted)            # watched engines tick at full rate (M0-07)
            for engine_id in wanted:
                try:
                    msg = services().build_message(engine_id)
                except HTTPException:
                    continue
                if msg is None:
                    continue
                for c in list(self.clients.values()):
                    if engine_id in c.engines:
                        c.offer(msg)
            await asyncio.sleep(BROADCAST_POLL_S)
        if _services is not None:
            _services.hub.set_active(set())               # nobody watches: back to the idle rate


BROADCASTER = Broadcaster()


@router.websocket("/ws/v1")
async def ws_v1(ws: WebSocket) -> None:
    await ws.accept()
    client = Client(ws=ws, id=uuid.uuid4().hex[:8])
    BROADCASTER.clients[client.id] = client
    BROADCASTER.ensure_running()

    async def sender() -> None:
        while True:
            message = await client.queue.get()
            try:
                await asyncio.wait_for(ws.send_text(message), timeout=SEND_TIMEOUT_S)
            except asyncio.TimeoutError:
                await ws.close(code=1008, reason="client too slow")
                return

    send_task = asyncio.create_task(sender())
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "message": "send JSON like {\"subscribe\": \"<engine_id>\"} (ids from GET /api/v1/engines)"})
                continue
            sub = msg.get("subscribe")
            if sub is not None:
                hub = services().hub
                wanted = set(hub.runtimes) if sub == "fleet" else set(sub if isinstance(sub, list) else [sub])
                unknown = wanted - set(hub.runtimes)
                if unknown:
                    await ws.send_json({"type": "error", "message": f"unknown engines {sorted(unknown)}"})
                    continue
                client.engines = wanted
                for e in wanted:                       # snapshot on subscribe (R 19.3 resync)
                    ch = services().channel(e)
                    if ch.last_message:
                        client.offer(ch.last_message)
                await ws.send_json({"type": "subscribed", "engines": sorted(wanted)})
    except WebSocketDisconnect:
        pass
    finally:
        send_task.cancel()
        BROADCASTER.clients.pop(client.id, None)
