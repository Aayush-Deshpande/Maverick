"""Engine API (R4): per-engine REST + WebSocket routes over the concurrent RuntimeHub (D29).

  GET    /api/engines                      -> profiles (valid faults per engine), selected engine, readiness
  POST   /api/engines/select               -> {"engine_id": ...}; warms the heavy tier for that engine only
  GET    /api/engines/{id}/state           -> latest tick payload
  POST   /api/engines/{id}/faults          -> {mode, cylinder?, severity?, ramp_sec?}  (origin=MANUAL)
  DELETE /api/engines/{id}/faults
  POST   /api/engines/{id}/levers          -> {throttle_pct?, altitude_ft?, oat_c?}   (first-order dynamics)
  WS     /ws/engines/{id}                  -> that engine's payload every tick
  WS     /ws/fleet                         -> compact status of every engine every tick

The hub is created lazily on first use (calibration runs in a background thread), so importing this module
and the existing routes cost nothing.  Ground truth is never sent: payloads come from Frame + detector only.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.server.security import command_guard

from backend.runtime import EngineRuntime, RuntimeHub

router = APIRouter()
_hub: Optional[RuntimeHub] = None
_lock = threading.Lock()


def get_hub() -> RuntimeHub:
    global _hub
    with _lock:
        if _hub is None:
            _hub = RuntimeHub()

            def boot():
                _hub.calibrate_all()
                _hub.select(_hub.selected)
                _hub.start()

            threading.Thread(target=boot, daemon=True, name="hub-boot").start()
        return _hub


def _rt(engine_id: str) -> EngineRuntime:
    hub = get_hub()
    if engine_id not in hub.runtimes:
        raise HTTPException(404, f"unknown engine {engine_id!r}; have {sorted(hub.runtimes)}")
    return hub.runtimes[engine_id]


class SelectBody(BaseModel):
    engine_id: str


class FaultBody(BaseModel):
    action: Optional[str] = None
    fault_id: Optional[int] = None
    mode: Optional[str] = None
    cylinder: Optional[int] = None
    severity: Optional[float] = None      # registry default when omitted
    ramp_sec: Optional[float] = None


class LeverBody(BaseModel):
    throttle_pct: Optional[float] = Field(default=None, ge=0, le=100)      # same ranges as /api/v1 levers
    altitude_ft: Optional[float] = Field(default=None, ge=-1000, le=40000)
    oat_c: Optional[float] = Field(default=None, ge=-60, le=60)


@router.get("/api/engines")
def list_engines():
    return get_hub().state()


@router.post("/api/engines/select")
def select_engine(body: SelectBody, cmd: Dict[str, Any] = Depends(command_guard)):
    hub = get_hub()
    try:
        hub.select(body.engine_id)
    except KeyError:
        raise HTTPException(404, f"unknown engine {body.engine_id!r}")
    return {"selected": hub.selected}


@router.get("/api/engines/{engine_id}/state")
def engine_state(engine_id: str):
    rt = _rt(engine_id)
    if not rt.buffer:
        raise HTTPException(503, "engine still calibrating")
    return EngineRuntime.payload(rt.buffer[-1])


@router.get("/api/engines/{engine_id}/history")
def engine_history(engine_id: str, n: int = 600, channels: Optional[str] = None,
                   step: int = 1):
    """Recent frames from the runtime's ring buffer, oldest first.

    The buffer already holds up to 3600 ticks per engine; without this route the client
    had no way to reach them, so every chart opened empty and could only grow forward
    from the moment the page loaded. That made trend, drift and threshold-approach
    unanswerable for the first minute of a session.

    `channels` is a comma-separated allowlist (plus the always-present cht/egt arrays),
    and `step` decimates server-side so a 1200-point request over a 3600-tick buffer
    stays a single small response instead of shipping the whole frame payload 1200 times.
    """
    rt = _rt(engine_id)
    if not rt.buffer:
        raise HTTPException(503, "engine still calibrating")
    n = max(1, min(int(n), rt.buffer.maxlen or 3600))
    step = max(1, min(int(step), 60))
    wanted = {c.strip() for c in channels.split(",") if c.strip()} if channels else None

    # deque slicing is O(n) per index, so materialise the tail once.
    ticks = list(rt.buffer)[-(n * step):][::step]
    samples = []
    for t in ticks:
        f = t.frame
        chans = f.channels()
        samples.append({
            "t": f.t,
            "channels": {k: v for k, v in chans.items() if k in wanted} if wanted else chans,
            "cht": f.cht,
            "egt": f.egt,
            # Enough detector/prognostic context to draw the score and RUL series without
            # a second request; everything else stays in the live frame.
            "ratios": (t.detection.ratios if t.detection else None),
            "raw_alarm": (t.detection.raw_alarm if t.detection else None),
            "confirmed": (t.detection.confirmed if t.detection else None),
            "rul": ((t.prognostics or {}).get("rul") or {}).get("rul_point"),
            "rul_lower": ((t.prognostics or {}).get("rul") or {}).get("rul_p_lower"),
            "rul_upper": ((t.prognostics or {}).get("rul") or {}).get("rul_p_upper"),
            "damage": ((t.prognostics or {}).get("damage") or {}).get("damage_total"),
            "mission_reliability": (t.reliability or {}).get("mission_reliability"),
        })
    return {
        "engine_id": engine_id,
        "count": len(samples),
        "step": step,
        "buffer_len": len(rt.buffer),
        "evidence_class": "SIMULATION",
        "samples": samples,
    }


@router.get("/api/engines/{engine_id}/events")
def engine_events(engine_id: str, since_seq: int = 0, limit: int = 100):
    """Retained state-transition events, oldest first.

    Live frames carry only the events raised on that tick, so a client that just
    connected (or reconnected) uses this to backfill its timeline. `since_seq` makes the
    catch-up incremental rather than re-sending the whole log.
    """
    rt = _rt(engine_id)
    events = [e for e in rt.events if e["seq"] > int(since_seq)]
    return {
        "engine_id": engine_id,
        "latest_seq": rt.event_seq,
        "events": events[-max(1, min(int(limit), 200)):],
    }


@router.get("/api/engines/{engine_id}/schema")
def engine_schema(engine_id: str):
    from backend.core.profile import load_profile
    try:
        prof = load_profile(engine_id)
        return prof.to_schema()
    except FileNotFoundError:
        raise HTTPException(404, f"unknown engine {engine_id!r}")


@router.post("/api/engines/{engine_id}/faults")
def inject_fault(engine_id: str, body: FaultBody, cmd: Dict[str, Any] = Depends(command_guard)):
    """DEPRECATED (use POST /api/v1/engines/{id}/faults). Goes through the ONE fault manager (M0-10), so the fault
    shows on every client. Numeric ids resolve only through registry legacy_ids (audit #18: never list position);
    'mode' resolves through registry plant_mode_legacy. Anything else -> 422 with the reason."""
    from backend.faults.registry import FaultRejected
    from backend.physics.engine_config import load_engine_config
    from backend.server.api_v1 import REGISTRY, services
    cmd.update(source="legacy")
    _rt(engine_id)
    manager = services().channel(engine_id).manager
    if body.action == "CLEAR_FAULT" or body.fault_id == 0:
        return {"cleared": [f.to_dict() for f in manager.clear(source="legacy")]}
    try:
        if body.fault_id is not None:
            spec = REGISTRY.by_legacy_id(body.fault_id)
            cylinder = body.cylinder if body.cylinder is not None else spec.raw.get("legacy_cylinder")
        elif body.mode:
            cfg = load_engine_config(engine_id)
            matches = [f for f in REGISTRY.applicable(cfg) if f.raw.get("plant_mode_legacy") == body.mode]
            if not matches:
                raise FaultRejected(f"mode {body.mode!r} has no registry fault applicable to {engine_id}")
            spec, cylinder = matches[0], body.cylinder
        else:
            raise HTTPException(422, "Either 'mode' or 'fault_id' must be specified.")
        f = manager.inject(spec.id, cylinder=cylinder, severity=body.severity, ramp_s=body.ramp_sec, source="legacy")
    except FaultRejected as exc:
        raise HTTPException(422, str(exc)) from None
    return {"status": "SUCCESS", "fault": f.to_dict()}


@router.delete("/api/engines/{engine_id}/faults")
def clear_faults(engine_id: str, cmd: Dict[str, Any] = Depends(command_guard)):
    from backend.server.api_v1 import services
    cmd.update(source="legacy")
    _rt(engine_id)
    return {"cleared": [f.to_dict() for f in services().channel(engine_id).manager.clear(source="legacy")]}


@router.post("/api/engines/{engine_id}/levers")
def set_levers(engine_id: str, body: LeverBody, cmd: Dict[str, Any] = Depends(command_guard)):
    return _rt(engine_id).set_levers(**body.model_dump(exclude_none=True))


@router.websocket("/ws/engines/{engine_id}")
async def ws_engine(ws: WebSocket, engine_id: str):
    hub = get_hub()
    if engine_id not in hub.runtimes:
        await ws.close(code=4404)
        return
    await ws.accept()
    rt, last = hub.runtimes[engine_id], -1.0
    try:
        while True:
            if rt.buffer and rt.buffer[-1].frame.t != last:
                last = rt.buffer[-1].frame.t
                await ws.send_json(EngineRuntime.payload(rt.buffer[-1]))
            await asyncio.sleep(0.05)
    except (WebSocketDisconnect, RuntimeError):
        return


@router.websocket("/ws/fleet")
async def ws_fleet(ws: WebSocket):
    hub = get_hub()
    await ws.accept()
    try:
        while True:
            snap = []
            for e, rt in hub.runtimes.items():
                if not rt.buffer:
                    snap.append({"engine_id": e, "ready": False})
                    continue
                t = rt.buffer[-1]
                d = t.detection
                snap.append({"engine_id": e, "ready": True, "t": t.frame.t, "selected": e == hub.selected,
                             "rpm": t.frame.rpm, "max_cht": max(t.frame.cht), "max_egt": max(t.frame.egt),
                             "raw_alarm": d.raw_alarm if d else None, "confirmed": d.confirmed if d else None,
                             "top_channels": d.top_channels[:1] if d else []})
            await ws.send_json({"selected": hub.selected, "engines": snap})
            await asyncio.sleep(0.25)
    except (WebSocketDisconnect, RuntimeError):
        return
