"""In-memory audit probes. No server, external calls, or product file changes."""
from pathlib import Path
import copy
import json
import os
import sys
import threading

os.environ['PYTEST_CURRENT_TEST'] = 'review-probes'
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.core.frame import Frame, TruthRecord, FaultTruth
from backend.detect.detector import DetectionResult
from backend.runtime.engine_runtime import EngineRuntime, Tick
from backend.server.engine_service import EngineStateService

results = {}

# The bridge can be exercised without constructing its live service or threads.
service = EngineStateService.__new__(EngineStateService)
service.state_lock = threading.RLock()
service.latest_state = None
service.flight_phase = 'GROUND'
service.region = 'AUDIT'
service.sortie_id = 'AUDIT-IN-MEMORY'
service.active_fault_id = 0
zero = Frame(t=1, source='PLANT', engine_config_id='rotax_912is', rpm=0,
             throttle=0, alt=0, oat=0, oil_p=0, oil_t=0, fuel_flow=0,
             map_kpa=0, bus_v=0, cht=[90]*4, egt=[500]*4)
state = service.sync_from_tick(Tick('rotax_912is', zero, TruthRecord(t=1), None, None))
results['zero_bridge'] = {
    'input': {'altitude_ft': 0, 'oat_c': 0, 'oil_pressure_bar': 0, 'fuel_flow': 0, 'map_kpa': 0, 'bus_voltage': 0},
    'output': {'altitude_ft': state.telemetry.ALTITUDE_FT, 'oat_c': state.telemetry.OAT_C,
               'oil_pressure_bar': state.telemetry.OIL_PRESS, 'fuel_flow': state.telemetry.FUEL_FLOW,
               'map_kpa': state.telemetry.MAP, 'bus_voltage': state.telemetry.BUS_VOLTAGE},
}
score = DetectionResult(1, {'mahalanobis': 3.127}, {'mahalanobis': .32}, False, False,
                        [('cht_2', -1.8)])
mixed = service.sync_from_tick(Tick(
    'rotax_912is', zero, TruthRecord(t=1), score, None,
    prognostics={'rul': {'rul_point': .9, 'rul_p_lower': 0}, 'damage': {'damage_total': .5}},
    reliability={'mission_reliability': 0, 'limiting_component': 'cylinder_head_1'},
))
results['mixed_contract'] = {
    'go_no_go': mixed.analytics.go_no_go,
    'planned_sortie_hours': mixed.analytics.planned_sortie_hours,
    'rul_p10_hours': mixed.analytics.rul_p10_hours,
    'rul_p50_hours': mixed.analytics.rul_p50_hours,
    'mission_reliability': mixed.analytics.mission_reliability,
    'residuals': mixed.analytics.residuals,
    'score_presented_as_probability_by_legacy_ui': mixed.analytics.anomaly_score,
}

# Fixed detector evidence and identical observations; only hidden truth changes.
class FixedDetector:
    def score(self, frame, **kwargs):
        return DetectionResult(frame.t, {'mahalanobis': 2}, {'mahalanobis': 2}, True, True,
                               [('cht_2', 4.0), ('rpm', -3.0), ('oil_p', -2.0)])

rt = EngineRuntime('rotax_912is', seed=42, warmup_ticks=400)
rt.detector = FixedDetector()
frame = Frame(t=10, source='PLANT', engine_config_id='rotax_912is', rpm=4500,
              throttle=60, alt=9000, oat=10, oil_p=3.5, oil_t=85, fuel_flow=10,
              map_kpa=55, bus_v=14.2, cht=[100, 110, 100, 100], egt=[530]*4)
diagnoses = []
for mode in ('MISFIRE', 'COOLING_DEGRADATION'):
    truth = TruthRecord(t=10, active_faults=[FaultTruth(mode, 2, .8, 0)])
    tick = rt.ingest(copy.deepcopy(frame), truth)
    diagnoses.append({'hidden_mode': mode, 'diagnosis': tick.diagnosis.get('fault_name'),
                      'fault_id': tick.diagnosis.get('fault_id'), 'confidence': tick.diagnosis.get('confidence')})
results['hidden_truth_changes_diagnosis_with_identical_frame_and_detector'] = diagnoses
out = Path(__file__).with_name('probe-results.json')
out.write_text(json.dumps(results, indent=2), encoding='utf-8')
print(json.dumps(results, indent=2))
