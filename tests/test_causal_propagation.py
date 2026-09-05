"""
Unit Tests for Multi-Parameter Causal Fault Propagation
DRDO / iDEX PS-26054 Rotax 912 iS Digital Twin
"""

import pytest
from backend.telemetry.can_streamer import TelemetryStreamer
from backend.physics.thermo_model import RotaxThermoModel
from backend.server.engine_service import EngineStateService


def test_streamer_fault_causality():
    """Verify that every fault modulates its primary and correlated secondary parameters."""
    streamer = TelemetryStreamer()
    
    # 1. FAULT 1: Cylinder 2 CHT Overheat -> CHT_2, OIL_TEMP, EGT_2, CHT_4
    streamer.set_fault(1, ramp_duration_sec=0.1)
    for _ in range(30):
        actual, expected, res = streamer.generate_frame()
    
    assert actual.CHT_2 > expected.CHT_2 + 20.0, "CHT_2 must elevate significantly"
    assert actual.OIL_TEMP > expected.OIL_TEMP + 4.0, "OIL_TEMP must rise due to thermal conduction"
    assert actual.EGT_2 > expected.EGT_2 + 8.0, "EGT_2 must rise due to hotter chamber walls"
    
    # 2. FAULT 2: Fuel Injector 1 Clog -> FUEL_FLOW drop, EGT_1 spike, CHT_1 rise, RPM sag/flutter, VIB rise
    streamer.set_fault(2, ramp_duration_sec=0.1)
    for _ in range(30):
        actual, expected, res = streamer.generate_frame()
    
    assert actual.FUEL_FLOW < expected.FUEL_FLOW - 1.5, "FUEL_FLOW must drop"
    assert actual.EGT_1 > expected.EGT_1 + 40.0, "EGT_1 must spike due to lean burn"
    assert actual.CHT_1 > expected.CHT_1 + 5.0, "CHT_1 must rise"
    assert actual.VIB_GEARBOX_RMS > expected.VIB_GEARBOX_RMS + 0.2, "Vibration must rise from torque ripple"

    # 3. FAULT 3: Ignition Misfire -> EGT_2 drop, RPM jitter, VIB spike
    streamer.set_fault(3, ramp_duration_sec=0.1)
    for _ in range(30):
        actual, expected, res = streamer.generate_frame()
    
    assert actual.EGT_2 < expected.EGT_2 - 50.0, "EGT_2 must drop due to unburnt fuel"
    assert actual.VIB_GEARBOX_RMS > expected.VIB_GEARBOX_RMS + 0.6, "VIB must spike from misfire shock"

    # 4. FAULT 4: Oil Pressure Decay -> OIL_PRESS drop, OIL_TEMP surge, all CHTs rise, RPM sag, VIB rise
    streamer.set_fault(4, ramp_duration_sec=0.1)
    for _ in range(30):
        actual, expected, res = streamer.generate_frame()
    
    assert actual.OIL_PRESS < 2.5, "OIL_PRESS must collapse"
    assert actual.OIL_TEMP > expected.OIL_TEMP + 12.0, "OIL_TEMP must surge from bearing friction"
    assert actual.CHT_1 > expected.CHT_1 + 4.0, "CHT_1 must rise from block friction"
    assert actual.CHT_3 > expected.CHT_3 + 4.0, "CHT_3 must rise from block friction"

    # 5. FAULT 5: Gearbox Vibration -> VIB spike, RPM drag, MAP compensation, OIL_TEMP rise
    streamer.set_fault(5, ramp_duration_sec=0.1)
    for _ in range(30):
        actual, expected, res = streamer.generate_frame()
    
    assert actual.VIB_GEARBOX_RMS > 2.5, "VIB_GEARBOX_RMS must spike above warning threshold"
    assert actual.MAP > expected.MAP + 1.0, "MAP must rise from load compensation"
    assert actual.OIL_TEMP > expected.OIL_TEMP + 3.0, "OIL_TEMP must rise from gear friction"

    # 6. FAULT 6: Exhaust EGT Imbalance -> EGT_3 spike, CHT_3 rise, VIB rise
    streamer.set_fault(6, ramp_duration_sec=0.1)
    for _ in range(30):
        actual, expected, res = streamer.generate_frame()
    
    assert actual.EGT_3 > expected.EGT_3 + 40.0, "EGT_3 must spike"
    assert actual.CHT_3 > expected.CHT_3 + 6.0, "CHT_3 must rise"

    # 7. FAULT 7: Alternator Voltage Sag -> BUS_VOLTAGE drop, BATTERY_CURRENT discharge
    streamer.set_fault(7, ramp_duration_sec=0.1)
    for _ in range(30):
        actual, expected, res = streamer.generate_frame()
    
    assert actual.BUS_VOLTAGE < 13.0, "BUS_VOLTAGE must sag below 13V"
    assert actual.BATTERY_CURRENT < -5.0, "BATTERY_CURRENT must swing to net discharge"

    # 8. FAULT 8: Dual FADEC Drift -> MAP rise, FUEL_FLOW rise, EGT_1..4 drop
    streamer.set_fault(8, ramp_duration_sec=0.1)
    for _ in range(30):
        actual, expected, res = streamer.generate_frame()
    
    assert actual.MAP > expected.MAP + 4.0, "MAP must drift high"
    assert actual.FUEL_FLOW > expected.FUEL_FLOW + 1.2, "FUEL_FLOW must increase due to over-fueling"
    assert actual.EGT_1 < expected.EGT_1 - 15.0, "EGT_1 must cool from rich quench"
    assert actual.EGT_3 < expected.EGT_3 - 15.0, "EGT_3 must cool from rich quench"


def test_engine_service_dynamic_subsystems():
    """Verify that EngineStateService computes real-time subsystem health from physics residuals."""
    service = EngineStateService()
    
    # Check Nominal
    service._tick(0.05)
    nominal_state = service.get_latest_state()
    sub_nom = nominal_state.analytics.subsystem_health
    assert sub_nom["propulsion"] >= 0.85
    assert sub_nom["thermal"] >= 0.85
    assert sub_nom["mechanical"] >= 0.85
    assert sub_nom["electrical"] >= 0.85
    assert sub_nom["fuel_system"] >= 0.85
    assert len(nominal_state.analytics.causal_chain) > 0

    # Command Fault 4 (Oil Pressure Decay)
    service.set_fault(4)
    for _ in range(40):
        service._tick(0.05)
    
    f4_state = service.get_latest_state()
    sub_f4 = f4_state.analytics.subsystem_health
    assert sub_f4["mechanical"] < 0.60, "Mechanical health must drop on oil pressure failure"
    assert len(f4_state.analytics.causal_chain) >= 3

    # Command Fault 3 (Ignition Misfire)
    service.set_fault(3)
    for _ in range(40):
        service._tick(0.05)
    f3_state = service.get_latest_state()
    assert f3_state.analytics.subsystem_health["electrical"] < 0.65, "Electrical health must drop on ignition misfire"

    # Command Fault 8 (Dual FADEC Drift)
    service.set_fault(8)
    for _ in range(40):
        service._tick(0.05)
    f8_state = service.get_latest_state()
    assert f8_state.analytics.subsystem_health["fuel_system"] < 0.70, "Fuel system health must drop on FADEC MAP drift"
    assert f8_state.analytics.subsystem_health["electrical"] < 0.75, "Electrical health must drop on FADEC MAP drift"

    # Clear fault back to nominal
    service.clear_fault()
    for _ in range(40):
        service._tick(0.05)
    nom_cleared = service.get_latest_state()
    assert nom_cleared.analytics.subsystem_health["propulsion"] >= 0.85
