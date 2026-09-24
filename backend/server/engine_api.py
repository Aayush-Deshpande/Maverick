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
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

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
                _hub.start(rate_hz=20.0)

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
    mode: str
    cylinder: Optional[int] = None
    severity: float = 0.8
    ramp_sec: float = 60.0


class LeverBody(BaseModel):
    throttle_pct: Optional[float] = None
    altitude_ft: Optional[float] = None
    oat_c: Optional[float] = None


@router.get("/api/engines")
def list_engines():
    return get_hub().state()


@router.post("/api/engines/select")
def select_engine(body: SelectBody):
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


@router.post("/api/engines/{engine_id}/faults")
def inject_fault(engine_id: str, body: FaultBody):
    rt = _rt(engine_id)
    try:
        return rt.inject_fault(body.mode, body.cylinder, body.severity, body.ramp_sec)
    except ValueError as e:
        raise HTTPException(422, str(e))


@router.delete("/api/engines/{engine_id}/faults")
def clear_faults(engine_id: str):
    _rt(engine_id).clear_faults()
    return {"cleared": True}


@router.post("/api/engines/{engine_id}/levers")
def set_levers(engine_id: str, body: LeverBody):
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
