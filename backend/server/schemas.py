"""
Pydantic Data Schemas & API Contracts
Rotax 912 iS MALE UAV Digital Twin — Laptop Backend Server
DRDO / iDEX Problem Statement ID: 26054
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class EngineTelemetry(BaseModel):
    """Raw and processed 27-parameter flight propulsion telemetry."""
    # Kinematics
    ENGINE_RPM: float = Field(5120.0, description="Engine crankshaft RPM (0 - 5800)")
    PROP_RPM: float = Field(2107.0, description="Propeller output RPM (0 - 2400)")
    TPS: float = Field(72.0, description="Throttle position percentage (0 - 100%)")
    
    # Thermal (°C)
    CHT_1: float = Field(104.5, description="Cylinder #1 Head Temp (°C)")
    CHT_2: float = Field(105.2, description="Cylinder #2 Head Temp (°C)")
    CHT_3: float = Field(104.8, description="Cylinder #3 Head Temp (°C)")
    CHT_4: float = Field(104.6, description="Cylinder #4 Head Temp (°C)")
    
    EGT_1: float = Field(780.0, description="Exhaust Gas Temp Runner #1 (°C)")
    EGT_2: float = Field(780.5, description="Exhaust Gas Temp Runner #2 (°C)")
    EGT_3: float = Field(782.0, description="Exhaust Gas Temp Runner #3 (°C)")
    EGT_4: float = Field(779.5, description="Exhaust Gas Temp Runner #4 (°C)")
    
    # Fluids & Pressures
    OIL_PRESS: float = Field(3.85, description="Oil pressure (bar)")
    OIL_TEMP: float = Field(92.0, description="Oil temperature (°C)")
    FUEL_FLOW: float = Field(17.8, description="Total fuel flow rate (L/h)")
    FUEL_RAIL_P: float = Field(3.0, description="Fuel injection rail pressure (bar)")
    MAP: float = Field(88.2, description="Manifold Absolute Pressure (kPa)")
    
    # Mechanical & Electrical
    VIB_GEARBOX_RMS: float = Field(0.48, description="Gearbox vibration RMS (mm/s)")
    BUS_VOLTAGE: float = Field(14.12, description="DC Bus Voltage (V)")
    BATTERY_CURRENT: float = Field(0.2, description="Battery Charge/Discharge current (A)")
    FADEC_ACTIVE_LANE: str = Field("LANE_A", description="Active ECU Lane (LANE_A / LANE_B)")
    
    # Environmental Context
    ALTITUDE_FT: float = Field(20000.0, description="Altitude MSL (feet)")
    OAT_C: float = Field(-22.0, description="Outside Air Temp (°C)")
    TAS_KNOTS: float = Field(90.0, description="True Airspeed (knots)")
    FLIGHT_PHASE: str = Field("CRUISE_LOITER", description="Flight operational phase")
    THEATER: str = Field("LADAKH", description="Active operational theater/region: LADAKH | THAR_DESERT")

    # Engine Management & Efficiency (FADEC / Performance Map)
    INJ_TIMING_BTDC: float = Field(18.5, description="Fuel injection start timing (°BTDC)")
    INJ_PULSE_WIDTH_MS: float = Field(4.2, description="Fuel injection pulse width (ms)")
    IGN_TIMING_BTDC: float = Field(22.0, description="Ignition advance timing (°BTDC)")
    LAMBDA_AFR: float = Field(14.7, description="Air-Fuel Ratio (AFR)")
    BSFC_G_KWH: float = Field(270.0, description="Brake Specific Fuel Consumption (g/kWh)")
    POWER_KW: float = Field(65.0, description="Engine brake shaft power (kW)")
    THERMAL_EFFICIENCY: float = Field(0.31, description="Engine brake thermal efficiency (0.0 - 1.0)")


class AnalyticsState(BaseModel):
    """Real-time machine learning inference, physics residuals & diagnostics."""
    residuals: Dict[str, float] = Field(default_factory=dict, description="14 physics residuals (Actual - Expected)")
    anomaly_score: float = Field(0.0, description="Continuous Autoencoder L2 anomaly score (0.0 to 1.0)")
    health_index: float = Field(1.0, description="Propulsion system health index (0.0 to 1.0)")
    
    diagnosed_fault_id: int = Field(0, description="Diagnosed Fault ID (0 = Nominal, 1..8 = Faults)")
    diagnosed_fault_name: str = Field("NOMINAL_FLIGHT", description="Diagnosed fault name")
    diagnosed_confidence: float = Field(0.99, description="ML classifier probability confidence (0.0 to 1.0)")
    
    target_3d_mesh: str = Field("All", description="Target 3D CAD mesh to highlight in Blender")
    target_parts: List[str] = Field(default_factory=list, description="Target mesh component names")
    
    ata_chapter: str = Field("ATA 00-00", description="Authoritative ATA chapter citation")
    subsystem: str = Field("PROPULSION_CORE", description="Affected propulsion subsystem")
    severity: str = Field("NORMAL", description="Alert severity: NORMAL | CAUTION | WARNING | CRITICAL")
    root_cause: str = Field("All propulsion subsystems operating within flight envelope.", description="Root cause explanation")
    prescriptive_action: str = Field("Maintain standard flight profile.", description="Immediate pilot/GCS action")
    emergency_checklist: List[str] = Field(default_factory=list, description="DRDO SOP step-by-step checklist")
    maintenance_order: str = Field("No maintenance required.", description="Condition-Based Maintenance work order")
    
    go_no_go: str = Field("GO", description="Mission flight readiness advisory: GO | CAUTION | NO-GO")
    go_no_go_reason: str = Field("All propulsion subsystems flight-ready.", description="Go/No-Go reason")
    rul_p10_hours: float = Field(14.2, description="Remaining Useful Life (10th percentile conservative hours) of the limiting component")
    rul_p50_hours: float = Field(18.0, description="Remaining Useful Life (50th percentile nominal hours) of the limiting component")
    limiting_component: Optional[str] = Field(None, description="Subsystem with the lowest RUL_p10 — the Go/No-Go bottleneck")
    planned_sortie_hours: float = Field(18.0, description="Planned sortie duration used for the Go/No-Go comparison")
    rul_by_component: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description=(
            "Per-subsystem probabilistic RUL from the 500-sample Monte Carlo estimator: "
            "rul_p10_hours, rul_p50_hours, rul_p90_hours, confidence (fit R^2) for each of "
            "the 6 monitored components. Empty until a degradation trend is detected."
        )
    )
    
    sensor_sanity: Dict[str, Any] = Field(default_factory=dict, description="Sensor sanity validation report")
    early_warning_trend: Optional[Dict[str, Any]] = Field(None, description="Sub-threshold prognostic drift trend")
    threshold_baseline: Dict[str, Any] = Field(default_factory=dict, description="Conventional fixed-threshold baseline comparator & lead-time (F13)")
    conformal_rul: Dict[str, Any] = Field(default_factory=dict, description="Conformal prediction intervals for component RUL (F12)")
    
    subsystem_health: Dict[str, float] = Field(
        default_factory=lambda: {
            "propulsion": 1.0,
            "fuel_system": 1.0,
            "electrical": 1.0,
            "thermal": 1.0,
            "mechanical": 1.0,
        },
        description="Physical health index (0.0 to 1.0) per subsystem calculated from residuals"
    )
    causal_chain: List[str] = Field(
        default_factory=list,
        description="Multi-step physical and mechanical causal propagation chain"
    )

    ai_diagnosis: Dict[str, Any] = Field(
        default_factory=lambda: {"status": "IDLE", "fault_name": "NOMINAL_FLIGHT", "explanation": "", "citations": []},
        description=(
            "RAG-grounded natural-language diagnosis from the local Qwen3-4B reasoning layer. "
            "status: IDLE | THINKING | READY | ERROR. Qwen only explains/recommends over the "
            "deterministic causal_chain and retrieved manuals above — it never invents fault IDs, "
            "sensor values, or the causal chain itself."
        )
    )


class UnifiedTelemetryState(BaseModel):
    """The unified, single source of truth broadcast to all clients at 20 Hz."""
    timestamp: float = Field(..., description="UNIX epoch timestamp in seconds")
    sortie_id: str = Field(..., description="Active Sortie Identifier")
    is_engine_running: bool = Field(True, description="Whether engine is running")
    active_commanded_fault_id: int = Field(0, description="Commanded fault scenario ID (0..8)")
    active_commanded_fault_name: str = Field("NOMINAL", description="Commanded fault name")
    telemetry: EngineTelemetry
    analytics: AnalyticsState


class ControlCommand(BaseModel):
    """Incoming command from Mobile Web Frontend or GCS."""
    action: str = Field(..., description="Action: START_ENGINE | STOP_ENGINE | SET_FAULT | CLEAR_FAULT | SET_THROTTLE | SET_ALTITUDE | SET_OAT | SET_REGIME | SET_ROLE | EXPORT_DEBRIEF")
    fault_id: Optional[int] = Field(None, description="Fault ID (0 to 8)")
    throttle: Optional[float] = Field(None, description="Throttle percentage (0 - 100%)")
    altitude_ft: Optional[float] = Field(None, description="Altitude MSL (feet)")
    oat_c: Optional[float] = Field(None, description="Outside Air Temp (°C)")
    region: Optional[str] = Field(None, description="Operating region: LADAKH | THAR_DESERT")
    regime: Optional[str] = Field(None, description="Mission regime: LADAKH | THAR_DESERT | ENDURANCE_LOITER | RAPID_THROTTLE_TRANSIENTS")
    role: Optional[str] = Field(None, description="Active GCS role: OPERATOR | PROPULSION_ENGINEER | MAINTENANCE_CREW")


class VoiceConverseResponse(BaseModel):
    """Response for a single spoken turn: transcript in, spoken reply + audio out."""
    status: str = Field(..., description="SUCCESS | GUARDRAIL_BLOCKED | EMPTY_AUDIO | ERROR")
    session_id: str = Field(..., description="Client-persisted conversation session identifier")
    transcript: str = Field("", description="Speech-to-text transcript of the operator's utterance")
    response: str = Field("", description="Spoken-form Mission Copilot reply (plain text, no markdown)")
    audio_base64: Optional[str] = Field(None, description="Base64-encoded WAV audio of the spoken reply")
    audio_format: str = Field("wav", description="Audio container format")
    sample_rate: int = Field(24000, description="Audio sample rate (Hz)")
    citations: List[str] = Field(default_factory=list, description="Technical manual sources grounding the reply")
    active_fault: Optional[Dict[str, Any]] = Field(None, description="Diagnostic directive if the reply concerns an active fault")


class ServerHealthResponse(BaseModel):
    """Server health and connected clients information."""
    status: str = "ONLINE"
    service: str = "Rotax 912 iS Digital Twin Server"
    sortie_id: str
    is_engine_running: bool
    active_fault_id: int
    connected_web_clients: int
    connected_blender_clients: int
    loop_frequency_hz: float = 20.0
