"""FastAPI Mission Planning & Simulation REST & WebSocket Endpoints (ARCH-2026-MP-001, Task 1.6).

Exposes full mission planning CRUD, live execution control, scheduled & live fault injection,
operator derate / RTB, and 20 Hz authoritative WebSocket state streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from backend.mission.executive import (
    MissionExecutive,
    create_endurance_phase_preset,
    create_ladakh_preset,
    create_thar_preset,
    create_endurance_preset,
    create_rapid_throttle_preset,
)
from backend.mission.models import (
    EnvironmentalConditions,
    FlightPhase,
    MissionDefinition,
    MissionState,
    MissionStatus,
    ScheduledEvent,
    Waypoint,
)
from backend.server.engine_api import get_hub

logger = logging.getLogger("MissionAPI")
router = APIRouter(prefix="/api/missions", tags=["Mission Planning"])

_mission_exec: Optional[MissionExecutive] = None


def get_mission_executive() -> MissionExecutive:
    global _mission_exec
    if _mission_exec is None:
        hub = get_hub()
        _mission_exec = MissionExecutive(hub=hub)
    return _mission_exec


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------
class WaypointModel(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    alt_msl_m: float
    airspeed_ktas: float = 120.0
    loiter_radius_m: float = 0.0
    loiter_duration_sec: float = 0.0
    terrain_alt_m: float = 0.0


class ScheduledEventModel(BaseModel):
    trigger_time_sec: float
    action: str = "INJECT_FAULT"
    fault_mode: Optional[str] = None
    cylinder: Optional[int] = None
    severity: float = 0.8
    ramp_sec: float = 10.0
    target_value: Optional[float] = None


class EnvironmentalConditionsModel(BaseModel):
    theater_name: str = "LADAKH_HIGH_COLD"
    qnh_hpa: float = 1013.25
    isa_temp_offset_c: float = 0.0
    base_elevation_m: float = 3097.64
    ambient_wind_kt: float = 0.0
    wind_direction_deg: float = 0.0
    dust_density_mg_m3: float = 0.15


class MissionPhaseSpecModel(BaseModel):
    name: str
    duration_sec: float
    start_alt_ft: float
    end_alt_ft: float
    throttle_pct: float = 65.0
    oat_c: float = 15.0
    dust_mg_m3: float = 0.15


class PhaseScheduledEventModel(BaseModel):
    phase_name: str
    elapsed_in_phase_sec: float
    action: str = "INJECT_FAULT"
    fault_mode: Optional[str] = None
    cylinder: Optional[int] = None
    severity: float = 0.8
    ramp_sec: float = 10.0


class MissionDefinitionModel(BaseModel):
    mission_id: str
    name: str
    engine_id: str
    airframe_id: str = "TAPAS-BH-201"
    planned_duration_sec: float = 600.0
    environment: EnvironmentalConditionsModel
    phases: List[MissionPhaseSpecModel] = []
    phase_events: List[PhaseScheduledEventModel] = []
    waypoints: List[WaypointModel] = []
    scheduled_events: List[ScheduledEventModel] = []


class DerateRequest(BaseModel):
    scale: float = Field(0.85, ge=0.5, le=1.0)


class TimeScaleRequest(BaseModel):
    scale: float = Field(1.0, ge=0.25, le=20.0)


class LiveFaultRequest(BaseModel):
    mode: str
    cylinder: Optional[int] = None
    severity: float = 0.8
    ramp_sec: float = 10.0


class DivertRequest(BaseModel):
    lat: float
    lon: float
    alt_msl_m: Optional[float] = None
    name: str = "DIVERT"


class LaunchBlenderRequest(BaseModel):
    mode: str = "client"  # "client" (mission_flight_client.py) or "canyon" (standalone_canyon_flight_app.py)


# -----------------------------------------------------------------------------
# REST Endpoints
# -----------------------------------------------------------------------------
@router.get("/templates")
def list_mission_templates() -> List[Dict[str, Any]]:
    """Returns preset mission profiles for quick selection."""
    presets = [
        create_endurance_phase_preset("rotax_912is"),
        create_ladakh_preset("rotax_912is"),
        create_ladakh_preset("rotax_914"),
        create_thar_preset("rotax_915is"),
        create_endurance_preset("austro_ae300"),
        create_rapid_throttle_preset("vrde_jayem_2_2l"),
    ]
    return [p.to_dict() for p in presets]


@router.post("/validate")
def validate_mission(mission: MissionDefinitionModel) -> Dict[str, Any]:
    """Validates mission definition before launch."""
    if len(mission.phases) == 0 and len(mission.waypoints) < 2:
        raise HTTPException(400, "Mission requires either at least 1 phase or at least 2 waypoints.")
    if mission.planned_duration_sec < 10.0:
        raise HTTPException(400, "Mission planned duration must be at least 10 seconds.")
    hub = get_hub()
    if mission.engine_id not in hub.runtimes:
        raise HTTPException(400, f"Unsupported engine {mission.engine_id}; supported: {list(hub.runtimes.keys())}")
    return {"valid": True, "message": "Mission definition valid and ready for loading."}


@router.post("/load")
def load_mission(mission: MissionDefinitionModel) -> Dict[str, Any]:
    """Loads a mission definition into the authoritative executive."""
    exec_sim = get_mission_executive()
    defn = MissionDefinition.from_dict(mission.model_dump())
    exec_sim.load_mission(defn)
    return {"status": "LOADED", "mission": defn.to_dict(), "state": exec_sim.state.to_dict()}


@router.post("/start")
def start_mission() -> Dict[str, Any]:
    """Starts live mission execution."""
    exec_sim = get_mission_executive()
    exec_sim.start()
    return {"status": exec_sim.state.status, "time_scale": exec_sim.time_scale}


@router.post("/pause")
def pause_mission() -> Dict[str, Any]:
    """Pauses live mission execution."""
    exec_sim = get_mission_executive()
    exec_sim.pause()
    return {"status": exec_sim.state.status}


@router.post("/resume")
def resume_mission() -> Dict[str, Any]:
    """Resumes paused mission execution."""
    exec_sim = get_mission_executive()
    exec_sim.resume()
    return {"status": exec_sim.state.status}


@router.post("/abort")
def abort_mission() -> Dict[str, Any]:
    """Commands emergency mission abort / RTB and exports sortie."""
    exec_sim = get_mission_executive()
    res = exec_sim.abort()
    return res


@router.post("/derate")
def derate_mission(req: DerateRequest) -> Dict[str, Any]:
    """Operator action: derates propulsion demand."""
    exec_sim = get_mission_executive()
    return exec_sim.derate(scale=req.scale)


@router.post("/divert")
def divert_mission(req: DivertRequest) -> Dict[str, Any]:
    """Operator action: diverts the aircraft to an alternate lat/lon, replacing the
    remaining route ahead of the aircraft's current position."""
    exec_sim = get_mission_executive()
    return exec_sim.divert(lat=req.lat, lon=req.lon, alt_msl_m=req.alt_msl_m, name=req.name)


@router.post("/timescale")
def set_time_scale(req: TimeScaleRequest) -> Dict[str, Any]:
    """Adjusts simulation time compression (1x, 2x, 5x, 10x)."""
    exec_sim = get_mission_executive()
    scale = exec_sim.set_time_scale(req.scale)
    return {"time_scale": scale}


FAULT_MODE_ALIASES: Dict[str, str] = {
    "OIL_PUMP_RELIEF_VALVE": "OIL_PRESSURE_LOSS",
    "OIL_PUMP_FAILURE": "OIL_PRESSURE_LOSS",
    "OIL_PRESSURE_DROP": "OIL_PRESSURE_LOSS",
    "INJECTOR_CLOGGED": "MISFIRE",
    "SPARK_PLUG_FOULING": "MISFIRE",
    "CYLINDER_MISFIRE": "MISFIRE",
    "WASTEGATE_STUCK": "WASTEGATE_STUCK_OPEN",
    "INTERCOOLER_BLOCKAGE": "AIR_FILTER_BLOCKAGE",
    "AIR_RESTRICTION": "AIR_FILTER_BLOCKAGE",
    "COOLING_FAILURE": "COOLING_DEGRADATION",
}


@router.post("/faults")
def inject_live_fault(req: LiveFaultRequest) -> Dict[str, Any]:
    """Injects a real live fault into the selected engine runtime during simulation."""
    exec_sim = get_mission_executive()
    mode = FAULT_MODE_ALIASES.get(req.mode, req.mode)
    cyl = req.cylinder
    if mode == "MISFIRE" and (cyl is None or cyl < 1):
        cyl = 1
    try:
        rec = exec_sim.inject_live_fault(
            mode=mode,
            cylinder=cyl,
            severity=req.severity,
            ramp_sec=req.ramp_sec,
        )
        return rec
    except Exception as err:
        logger.exception("Error injecting fault: %s", err)
        raise HTTPException(400, str(err))


@router.delete("/faults")
def clear_faults() -> Dict[str, Any]:
    """Clears all injected faults from the active engine."""
    exec_sim = get_mission_executive()
    exec_sim.clear_faults()
    return {"status": "CLEARED"}


@router.get("/state")
def get_mission_state() -> Dict[str, Any]:
    """Returns authoritative current MissionState."""
    exec_sim = get_mission_executive()
    return exec_sim.state.to_dict()


@router.get("/definition")
def get_mission_definition() -> Dict[str, Any]:
    """Returns currently loaded MissionDefinition."""
    exec_sim = get_mission_executive()
    return exec_sim.definition.to_dict()


@router.get("/reliability")
def get_mission_reliability() -> Dict[str, Any]:
    """Full mission-reliability + What-If advisory for the LIVE loaded mission (ARCH-2026-
    MP-002): built from the mission's actual real phases (not the generic canned ISR
    profile the standalone /api/engines/{id}/reliability endpoint falls back to), via
    PrescriptiveAdvisor.advise() -- the assessment, the derate-options comparison table
    (the What-If mode), and the F58 re-plan search, all already-built machinery in
    backend/mission/prescriptive.py, now fed the real mission for the first time."""
    exec_sim = get_mission_executive()
    runtime = exec_sim.hub.runtimes.get(exec_sim.definition.engine_id)
    if runtime is None:
        raise HTTPException(400, f"No runtime available for engine {exec_sim.definition.engine_id}")
    if not exec_sim.is_phase_mode:
        raise HTTPException(400, "Live mission reliability requires a phase-based mission; this mission is in legacy waypoint/route mode.")
    try:
        exec_sim._apply_live_fault_damage(runtime)
        profile = exec_sim._build_live_reliability_profile()
        return runtime.advisor.advise(profile)
    except Exception as err:
        raise HTTPException(500, f"Mission reliability computation failed: {err}")


@router.get("/blender-status")
def get_blender_status() -> Dict[str, Any]:
    """Returns availability of native Blender executable and simulation batch files."""
    project_root = Path(__file__).resolve().parent.parent.parent
    candidate_paths = [
        r"D:\Blender\blender.exe",
        r"E:\Blender\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    ]
    found_path = None
    for p in candidate_paths:
        if Path(p).exists():
            found_path = p
            break
    if not found_path:
        which_b = shutil.which("blender")
        if which_b:
            found_path = which_b

    canyon_bat = project_root / "launch_canyon_simulation.bat"
    client_bat = project_root / "launch_mission_flight_client.bat"
    terrain_blend = project_root / "assets" / "models" / "terrain.blend"

    return {
        "blender_available": found_path is not None,
        "blender_executable": found_path,
        "canyon_sim_bat_exists": canyon_bat.exists(),
        "mission_client_bat_exists": client_bat.exists(),
        "terrain_blend_exists": terrain_blend.exists(),
    }


@router.post("/launch-blender")
def launch_blender_process(req: LaunchBlenderRequest) -> Dict[str, Any]:
    """Launches the authoritative native Blender flight simulation on the host desktop.

    Modes:
      - 'client': launch_mission_flight_client.bat (Live visual cockpit coupled to current mission via WebSocket)
      - 'canyon': launch_canyon_simulation.bat (Standalone Canyon UAV Flight physics simulator with Auto-GCAS)
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    if req.mode == "canyon":
        bat_file = project_root / "launch_canyon_simulation.bat"
        title = "Standalone Canyon Flight Simulation"
    else:
        bat_file = project_root / "launch_mission_flight_client.bat"
        title = "Mission Flight Client (Blender Cockpit)"

    if not bat_file.exists():
        raise HTTPException(404, f"Batch file not found: {bat_file}")

    try:
        creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        proc = subprocess.Popen(
            [str(bat_file)],
            cwd=str(project_root),
            shell=True,
            creationflags=creationflags,
        )
        logger.info("Launched Blender %s (PID %s) via %s", req.mode, proc.pid, bat_file)
        return {
            "status": "LAUNCHED",
            "mode": req.mode,
            "title": title,
            "pid": proc.pid,
            "bat_path": str(bat_file),
            "message": f"Successfully launched {title} in a native window.",
        }
    except Exception as err:
        logger.error("Failed to launch Blender: %s", err)
        raise HTTPException(500, f"Failed to launch Blender: {err}")


# -----------------------------------------------------------------------------
# WebSocket: 20 Hz Authoritative State Stream (bidirectional -- also accepts optional
# manual flight-control key state from the client, same feel as the standalone Blender
# sim's W/S=pitch, A/D=turn, E/Q=throttle, but applied to the one authoritative
# AutopilotFlightModel server-side so the backend stays the single source of truth).
# -----------------------------------------------------------------------------
@router.websocket("/ws")
async def mission_websocket(websocket: WebSocket) -> None:
    """Streams 20 Hz canonical MissionState to connected frontend cockpit & 3D viewers,
    and concurrently accepts small JSON key-state messages
    ({"type": "MANUAL_KEYS", "keys": {"pitch_up": bool, "pitch_down": bool,
    "turn_left": bool, "turn_right": bool, "throttle_up": bool, "throttle_down": bool}})
    for optional manual override of the autopilot."""
    await websocket.accept()
    exec_sim = get_mission_executive()

    async def _sender() -> None:
        while True:
            state_dict = exec_sim.state.to_dict()
            await websocket.send_text(json.dumps(state_dict))
            await asyncio.sleep(0.05)  # 20 Hz

    async def _receiver() -> None:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            if msg.get("type") == "MANUAL_KEYS":
                exec_sim.set_manual_keys(msg.get("keys", {}))

    sender_task = asyncio.create_task(_sender())
    receiver_task = asyncio.create_task(_receiver())
    try:
        done, pending = await asyncio.wait(
            {sender_task, receiver_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
        for task in done:
            task.exception()  # surface/log below, never let a task's exception be silent
    except WebSocketDisconnect:
        pass
    except Exception as err:
        logger.debug("Mission WebSocket disconnected: %s", err)
    finally:
        sender_task.cancel()
        receiver_task.cancel()
        # Manual control should never persist after the operator's client disconnects.
        exec_sim.clear_manual_keys()
