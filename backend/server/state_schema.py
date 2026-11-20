"""Versioned state message (card M0-05; P Part 4 Step 0.7; DECISIONS D3-D5, D7).

ONE message per engine per tick, read by every client (React console, 3D viewer, Blender app, phone). Fields that
the current runtime cannot fill yet are null - never a default number (D7). The JSON schema is exported to
configs/schema/state.schema.json and the TypeScript types are generated from it (frontend/src/api/state.ts), so
backend and frontend cannot drift (T-API-2): `python scripts/assets/export_state_schema.py` then
`cd frontend && npm run gen:types`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1

EngineState = Literal["OFF", "CRANKING", "RUNNING", "DEGRADED", "FAILED", "CALIBRATING"]
StatusLevel = Literal["ENGINE_OFF", "GO", "ADVISORY", "CAUTION", "NO-GO", "UNKNOWN"]
Quality = Literal["OK", "SUSPECT", "QUARANTINED", "VIRTUAL", "NO_DATA"]
Source = Literal["SIM", "REPLAY", "CAN", "MAVLINK"]


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Reading(_M):
    value: Optional[float] = Field(description="null when there is no data (never a default)")
    unit: str
    quality: Quality = "OK"
    age_ms: Optional[float] = None


class Reason(_M):
    code: str
    text: str
    channel: Optional[str] = None
    fault_id: Optional[str] = None
    value: Optional[float] = None
    limit: Optional[float] = None


class Status(_M):
    level: StatusLevel = Field(description="UNKNOWN until the status evaluator (card M2-01) runs")
    reasons: List[Reason] = []
    latched: bool = False
    acknowledged: bool = False


class AlertOut(_M):
    id: str
    level: Literal["NO-GO", "CAUTION", "ADVISORY"]
    code: str
    text: str
    action: str = Field(description="operator action (U3: every alert has one)")
    group: str = Field(description="root cause: the fault id of a hypothesis, else the channel's subsystem")
    channel: Optional[str] = None
    fault_id: Optional[str] = None
    first_s: float
    last_s: float
    count: int
    active: bool
    acknowledged: bool
    shelved_until: Optional[float] = None


class Evidence(_M):
    channel: str
    z: float


class Hypothesis(_M):
    fault_id: Optional[str]
    name: str
    kind: Literal["NOMINAL", "PROCESS", "SENSOR"] = "PROCESS"   # SENSOR: one sender offset (S02/S03), not the engine
    cylinder: Optional[int] = None
    channel: Optional[str] = None
    posterior: Optional[float] = None
    severity: Optional[float] = Field(None, description="estimated severity relative to the calibrated signature")
    group: Optional[str] = Field(None, description="ambiguity group: hypotheses these channels cannot tell apart")
    supporting: List[Evidence] = []
    contradicting: List[Evidence] = []


class Highlight(_M):
    component_id: str
    nodes: List[str]
    level: Literal["NO-GO", "CAUTION", "ADVISORY", "SENSOR", "INJECTED"]
    reason: str
    marker_for: Optional[str] = None


class ActiveFaultOut(_M):
    uuid: str
    fault_id: str
    name: str
    kind: Literal["PHYSICAL", "SENSOR"]
    cylinder: Optional[int] = None
    channel: Optional[str] = None
    severity: float
    ramp_s: float
    source: str
    t0_s: float
    simulated: bool
    components: List[str] = Field(default=[], description="resolved component ids (training mode display only, D5)")
    marker_for: Optional[str] = None


class EventOut(_M):
    seq: int
    t_s: float
    type: str
    text: str
    source: Optional[str] = None


class StateMessage(_M):
    schema_version: Literal[1] = SCHEMA_VERSION
    engine_id: str
    seq: int
    sim_time_s: float
    wall_time_iso: str
    rate_hz_actual: Optional[float] = None
    time_scale: float = 1.0
    source: Source = "SIM"
    evidence_class: Literal["SIMULATION", "PUBLIC_PROXY", "REAL_FLIGHT"] = "SIMULATION"
    engine_state: Optional[EngineState] = None
    levers: Dict[str, Optional[float]] = {}
    environment: Dict[str, Optional[float]] = {}
    readings: Dict[str, Reading] = {}
    derived: Dict[str, Optional[float]] = {}
    twin: Optional[Dict[str, Any]] = None
    residuals: Dict[str, float] = {}
    detections: Optional[Dict[str, Any]] = None
    hypotheses: List[Hypothesis] = []
    status: Status
    alerts: List[AlertOut] = []
    master: Dict[str, bool] = Field(default_factory=dict, description="master warning / caution (unacknowledged)")
    highlights: List[Highlight] = []
    prognostics: Optional[Dict[str, Any]] = None
    reliability: Optional[Dict[str, Any]] = None
    maintenance: List[Dict[str, Any]] = []
    mission: Optional[Dict[str, Any]] = Field(None, description="mission executive progress (M5); null = manual flight")
    active_faults: List[ActiveFaultOut] = []
    events_since: List[EventOut] = []
    vibration_orders: Dict[str, float] = {}
    virtual_sensors: Dict[str, float] = {}


def state_json_schema() -> Dict[str, Any]:
    schema = StateMessage.model_json_schema()
    schema["$id"] = "anumaan/configs/schema/state.schema.json"
    schema["title"] = "StateMessage"
    return schema
