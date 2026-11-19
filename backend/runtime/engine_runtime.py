"""EngineRuntime -- one engine profile's simulator + injectors + detector bank (R1/R2/R3/R7, D29, D05).

No module-level state: every runtime owns its plant, levers, sensor levers, detector, buffers and locks,
so a fault on one engine can never touch another. Tier-0 (calibrated residual scorers, FlyHash) runs every tick;
tier-1 (reservoir) is trained and stepped only while this engine is the SELECTED one (D29/D36).

Implements ingest(frame, truth): processing a live tick and ingesting a replayed frame run the identical path.
"""

from __future__ import annotations

import math
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

from backend.core.frame import Frame, TruthRecord, Q_INTERPOLATED, Q_SHIELDED
from backend.detect import DetectionResult, Reservoir, ResidualDetector
from backend.physics.engine_config import EngineConfig, load_engine_config
from backend.runtime.levers import Levers
from backend.runtime.registry import FAULT_REGISTRY, faults_for, thermal_visible_faults
from backend.runtime.sensor_levers import SensorLevers
from backend.sources import PlantSource
from backend.sim.source import registry as sim_registry

from backend.detect.sensor_fdi import SensorFDI
from backend.dsp.order_tracker import OrderTracker
from backend.twin.sim_ukf import SimThermalUKF
from backend.twin.virtual_sensors import VirtualSensorSynthesizer
from backend.twin.validity import TwinValidityMonitor
from backend.evaluation.damage_accumulation import DamageAccumulator
from backend.evaluation.conformal import SplitConformalRUL
from backend.prognose.trends import TrendTracker
from backend.status.evaluator import frame_readings
from backend.mission.reliability import (
    MissionReliabilityEngine, ISR_18H_PROFILE, DEFAULT_COMPONENTS, components_for_fault,
)
from backend.mission.glide import UAVGlidePolar
from backend.diagnose.directive import directive, status_hypotheses
from backend.diagnose.isolator import BayesianIsolator
from backend.status.alerts import AlertManager
from backend.status.evaluator import StatusEvaluator

DT = 1.0                      # simulated seconds per tick (calibrated at this cadence)
UKF_EVERY = 5                  # observer update every 5 ticks (its own dt is the real elapsed time)
WARMUP_TICKS = 900            # ground run-up used to calibrate this tail
EVENT_LOG_LEN = 200           # retained transitions per engine, served by /events
_WARM_SCHEDULE = [
    (45, 2000, 25), (60, 9000, 10), (75, 12000, 0), (95, 9000, 10),
    (90, 18000, -15), (70, 5000, 25), (85, 15000, -5), (95, 22000, -25),
    (50, 9000, 10), (80, 9000, 10), (95, 2000, 25), (60, 22000, -25),
    (100, 9000, 10), (40, 5000, 20)
]



@dataclass
class Tick:
    engine_id: str
    frame: Frame
    truth: TruthRecord
    detection: Optional[DetectionResult]
    heavy: Optional[Dict[str, Any]]
    sanity: Optional[Dict[str, Any]] = None
    ukf: Optional[Dict[str, Any]] = None
    validity: Optional[Dict[str, Any]] = None
    prognostics: Optional[Dict[str, Any]] = None
    reliability: Optional[Dict[str, Any]] = None
    glide: Optional[Dict[str, Any]] = None
    diagnosis: Optional[Dict[str, Any]] = None
    # M3-05 ranked isolation hypotheses (IsolationHypothesis.to_dict), published while an alarm is active
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    status: Optional[Dict[str, Any]] = None           # backend/status evaluator (M2-01)
    # Transitions raised on this tick only (usually empty). The client appends them
    # to its timeline; /events backfills after a reconnect.
    events: List[Dict[str, Any]] = field(default_factory=list)


_CYL_CHANNEL = re.compile(r"^(?:cht|egt)_(\d+)$", re.IGNORECASE)


def _first_cylinder_index(
    top_channels: Sequence[Union[str, Tuple[str, float]]]
) -> Optional[int]:
    """Return the cylinder index of the highest-ranked per-cylinder channel, if any.

    `top_channels` is ordered by residual magnitude and its entries are either a bare
    channel name or a (name, z-score) pair. Only `cht_N`/`egt_N` carry a cylinder, so a
    fault whose strongest residuals are engine-wide (rpm, oil_p) still resolves to the
    right cylinder via the first per-cylinder channel further down the list.
    """
    for entry in top_channels:
        name = entry[0] if isinstance(entry, (tuple, list)) else entry
        match = _CYL_CHANNEL.match(str(name))
        if match:
            return int(match.group(1))
    return None


# Severity ladder used by both the event log and the UI. INFORMATION is a normal system
# event, ADVISORY is worth watching, WARNING means behaviour is outside expectation, and
# CRITICAL means mission or engine reliability is implicated.
EVENT_LEVELS = ("INFORMATION", "ADVISORY", "WARNING", "CRITICAL")


class EngineRuntime:
    def __init__(self, engine_config_id: str, seed: int = 0, tail_id: Optional[str] = None,
                 warmup_ticks: int = WARMUP_TICKS, buffer_len: int = 3600) -> None:
        self.engine_id = engine_config_id
        self.cfg: EngineConfig = load_engine_config(engine_config_id)
        self.seed = seed
        self.tail_id = tail_id or f"TAIL-{engine_config_id}-{seed}"
        self.source = PlantSource(engine_config_id, seed=seed, tail_id=self.tail_id)
        self.levers = Levers()
        self.sensor_levers = SensorLevers(seed=seed)
        self.buffer: Deque[Tick] = deque(maxlen=buffer_len)
        self.detector: Optional[ResidualDetector] = None
        self.reservoir: Optional[Reservoir] = None
        self.manual_origin = False
        self.injected: List[Dict[str, Any]] = []
        # Event log. The stream is stateless per frame, so without this the client would
        # have to infer "something happened" by diffing consecutive frames -- which loses
        # every transition that occurs between two frames it happens to render, and gives
        # an event no stable identity to acknowledge or scroll to. Events are emitted on
        # transition only; each frame carries just the ones raised on that tick.
        self.events: Deque[Dict[str, Any]] = deque(maxlen=EVENT_LOG_LEN)
        self._event_seq = 0
        self._event_state: Dict[str, Any] = {
            "detector": "NOMINAL", "verdict": None,
            "quarantined": frozenset(), "suppressed": False, "fault_names": frozenset(),
        }
        self._lock = threading.RLock()
        self._heavy_lock = threading.Lock()
        self._warmup_ticks = warmup_ticks
        self.ready = False
        self.heavy_ready = False

        # Scientific, DSP, and State Estimation Modules
        self.sensor_fdi = SensorFDI(engine_config_id)     # M3-03 sensor validation (replaces the legacy validator)
        self.order_tracker = OrderTracker(self.cfg, seed=seed)
        self.ukf = SimThermalUKF(self.cfg)
        # observer cadence: every UKF_EVERY ticks, phase-shifted per engine so five engines never update together
        self._ukf_phase = sum(map(ord, engine_config_id)) % UKF_EVERY
        self.virtual_synthesizer = VirtualSensorSynthesizer(self.cfg)
        sigma_map = {f"cht_{i+1}": 4.5 for i in range(self.cfg.cylinder_count)}
        sigma_map["oil_t"] = 3.5
        self.validity_monitor = TwinValidityMonitor(              # oil pressure: no twin model, so no residual
            channels=[f"cht_{i+1}" for i in range(self.cfg.cylinder_count)] + ["oil_t"],
            expected_sigma=sigma_map,
        )
        self.damage_accumulator = DamageAccumulator(name=f"{self.engine_id}_cyl1_head")
        # placeholder RUL calibration kept only until M4-03 replaces it with the run-to-failure conformal RUL (D38:
        # tests/test_canonical_runtime_pipeline.py is ported then); not a real calibration
        self.conformal_rul = SplitConformalRUL()
        preds = [float(x) for x in np.linspace(18.0, 1.0, 25)]
        truths = [p + float(0.25 * math.sin(i)) for i, p in enumerate(preds)]
        scales = [0.4 + 0.03 * i for i in range(25)]
        self.conformal_rul.calibrate(predictions=preds, truths=truths, scales=scales)
        self.trends: Optional[TrendTracker] = None        # M4-02, built on the detector's channels at calibration

        components = DEFAULT_COMPONENTS()
        if not self.cfg.is_turbocharged:
            components = [c for c in components if c.name != "turbocharger"]
        self.reliability_engine = MissionReliabilityEngine(components=components, seed=seed)
        self.glide_polar = UAVGlidePolar()
        self.isolator: Optional[BayesianIsolator] = None          # built on the detector's channels at calibration
        self._cached_hypotheses: List[Dict[str, Any]] = []
        self.status_evaluator = StatusEvaluator(self.cfg)
        self.alert_manager = AlertManager()

        self._tick_count = 0
        self._cached_orders: Optional[Dict[str, float]] = None
        self._cached_ukf: Optional[Tuple[float, Any]] = None
        self._cached_validity: Optional[Dict[str, Any]] = None
        self._cached_prognostics: Optional[Dict[str, Any]] = None
        self._cached_reliability: Optional[Dict[str, Any]] = None
        self._cached_glide: Optional[Dict[str, Any]] = None
        self._cached_diagnosis: Optional[Dict[str, Any]] = None
        self._dmg_finalise_counter: int = 0




    # ---- lifecycle ------------------------------------------------------------------------
    def calibrate(self) -> None:
        """Nominal ground run-up on THIS tail, then fit calibration + conformal thresholds."""
        rng = np.random.default_rng(self.seed + 12345)
        op, frames, order = _WARM_SCHEDULE[0], [], []
        for i in range(self._warmup_ticks + 24):
            if i % 30 == 0:                      # every schedule point once per cycle (shuffled): envelope coverage
                if not order:
                    order = list(rng.permutation(len(_WARM_SCHEDULE)))
                op = _WARM_SCHEDULE[int(order.pop())]
            f, _ = self.source.step(DT, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
            if i >= 24:
                frames.append(f)
        with self._lock:
            self.detector = ResidualDetector.calibrate(frames, alpha=0.01)
            self.isolator = BayesianIsolator(self.engine_id, self.detector.cal.channel_names())
            self.trends = TrendTracker(self.cfg.limits or {}, self.detector.cal.channel_names(), self.detector.cal.sigma)
            self.levers = Levers()
            self.ready = True

    def ensure_heavy(self) -> None:
        """Tier-1: train the reservoir readout on a simulated fault library for this tail (SIMULATION)."""
        if self.heavy_ready or not self.ready:
            return
        with self._heavy_lock:
            if self.heavy_ready:
                return
            cal = self.detector.cal
            faults = []
            for mode in thermal_visible_faults(self.cfg):       # legacy library names -> registry faults
                try:
                    self.source._resolve(mode)
                    faults.append(mode)
                except ValueError:
                    pass
            seqs, labs = [], []

            def collect(fault: Optional[str], seed_off: int):
                src = PlantSource(self.engine_id, seed=self.seed)
                rng = np.random.default_rng(self.seed * 31 + seed_off)
                if fault:
                    cyl = int(rng.integers(1, src.n_cylinders + 1)) if src._resolve(fault).scope == "CYLINDER" else None
                    src.inject_fault(fault, cylinder=cyl, severity=0.9, ramp_sec=120.0)
                op, U = _WARM_SCHEDULE[0], []
                for i in range(260):
                    if i % 30 == 0:
                        op = _WARM_SCHEDULE[int(rng.integers(len(_WARM_SCHEDULE)))]
                    f, _ = src.step(DT, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
                    U.append(cal.features(cal.z(f)))
                return np.vstack(U)

            for k in range(2):
                U = collect(None, k)
                y = np.full(len(U), "NOMINAL", dtype=object)
                y[:30] = -1
                seqs.append(U)
                labs.append(y)
                for fname in faults:
                    U = collect(fname, 10 + k)
                    y = np.full(len(U), -1, dtype=object)
                    y[150:] = fname
                    seqs.append(U)
                    labs.append(y)
            res = Reservoir.random(len(cal.feature_names()), n=500, seed=self.seed)
            res.fit(seqs, labs, ridge=1.0)
            res.reset()
            self.reservoir = res
            self.heavy_ready = True

    # ---- operator actions (R2/R3/R7) --------------------------------------------------------
    def set_levers(self, **kw) -> Dict[str, float]:
        with self._lock:
            throttle_pct = kw.get("throttle_pct", kw.get("throttle"))
            altitude_ft = kw.get("altitude_ft", kw.get("altitude"))
            oat_c = kw.get("oat_c", kw.get("oat"))
            snap = kw.get("snap", False)
            climb_rate_fps = kw.get("climb_rate_fps")
            self.levers.set_targets(
                throttle_pct=throttle_pct,
                altitude_ft=altitude_ft,
                oat_c=oat_c,
                snap=snap,
                climb_rate_fps=climb_rate_fps
            )
            self.manual_origin = True
            return {"throttle_target": self.levers.throttle_target,
                    "altitude_target": self.levers.altitude_target, "oat_target": self.levers.oat_target}

    def inject_fault(self, mode: str, cylinder: Optional[int] = None, severity: float = 0.8,
                     ramp_sec: float = 60.0, origin: str = "MANUAL") -> Dict[str, Any]:
        """Registry id (F01..S07) or a registry plant_mode_legacy name, validated against configs/faults.json.
        A legacy name given without a cylinder keeps its legacy meaning: every cylinder (registry ids need one)."""
        spec = self.source._resolve(mode)
        channel = None
        legacy = FAULT_REGISTRY.get(mode)                    # old library: was this mode engine-wide?
        all_cylinders = (spec.scope == "CYLINDER" and cylinder is None and legacy is not None
                         and not legacy.per_cylinder)
        if spec.scope == "CHANNEL":
            channel = f"cht[{cylinder}]" if cylinder is not None else None
            cylinder = None
        elif spec.scope != "CYLINDER":
            cylinder = None
        sim_registry().validate_request(self.cfg, spec.id, cylinder=1 if all_cylinders else cylinder,
                                        channel=channel, severity=severity, ramp_s=ramp_sec)
        fault = SimpleNamespace(fault_id=spec.id, cylinder=cylinder, channel=channel, severity=float(severity),
                                ramp_s=float(ramp_sec), t0_s=self.source.now())
        self.apply_fault(fault, origin=origin)
        return {"mode": spec.id, "cylinder": cylinder, "channel": channel, "severity": severity,
                "ramp_sec": ramp_sec, "origin": origin, "t": fault.t0_s}

    def apply_fault(self, fault: Any, origin: str = "MANUAL") -> bool:
        """Hand one registry fault (fault_id, cylinder, channel, severity, ramp_s, t0_s) to the plant."""
        with self._lock:
            ok = self.source.apply(fault)
            if origin == "MANUAL":
                self.manual_origin = True
            self.injected.append({"mode": fault.fault_id, "cylinder": fault.cylinder, "channel": fault.channel,
                                  "severity": fault.severity, "ramp_sec": fault.ramp_s, "origin": origin,
                                  "t": fault.t0_s})
            return ok

    def engine_command(self, command: str) -> Dict[str, Any]:
        with self._lock:
            {"START": self.source.start, "STOP": self.source.stop, "RESET": self.source.reset}[command]()
            self.manual_origin = True
            return {"command": command, "engine_state": self.source.plant.state}

    def clear_faults(self) -> None:
        with self._lock:
            self.source.clear_faults()
            self.sensor_levers.clear()
            self.injected.clear()
            self.sensor_fdi.reset()
            self.validity_monitor.reset()
            self._cached_validity = None
            self._cached_diagnosis = None
            self._cached_hypotheses = []
            if self.isolator is not None:
                self.isolator.reset()
            self._cached_prognostics = None
            if self.trends is not None:
                self.trends.reset()
            if self.detector:
                self.detector.gate.reset()
                if self.detector.cusum is not None:
                    self.detector.cusum.reset()

    def set_sensor_fault(self, kind: str, channel: str, **kwargs) -> None:
        """Inject sensor-level fault (R7): bias, drift, stuck, noise, dropout, spoof."""
        with self._lock:
            self.sensor_fdi.quarantine(channel)
            if kind == "bias":
                self.sensor_levers.inject_bias(channel, kwargs.get("offset", 0.0))
            elif kind == "drift":
                self.sensor_levers.inject_drift(channel, kwargs.get("rate_per_sec", 0.0))
            elif kind == "stuck":
                self.sensor_levers.inject_stuck(channel, kwargs.get("frozen_value"))
            elif kind == "noise":
                self.sensor_levers.inject_noise(channel, kwargs.get("sigma", 1.0))
            elif kind == "dropout":
                self.sensor_levers.inject_dropout(channel)
            elif kind == "spoof":
                self.sensor_levers.inject_spoof(channel, kwargs.get("spoof_value", 0.0))
            else:
                raise ValueError(f"unknown sensor fault kind {kind!r}")
            self.manual_origin = True

    # ---- ingest and simulation (D05: Live = Replay at 1x) -----------------------------------
    def ingest(self, frame: Frame, truth: Optional[TruthRecord] = None, heavy: bool = False) -> Tick:
        """Process one Frame through the detector, UKF, DSP, prognostics, and reliability stack."""
        with self._lock:
            self._tick_count += 1
            if truth is None:
                truth = TruthRecord(t=frame.t, origin="REPLAY")

            # 1. Sensor Sanity Validation & Residual Shielding (R7)
            fdi = self.sensor_fdi.validate(frame)
            sanity_dict = fdi.to_dict()
            _quarantined_lower = list(fdi.quarantined)
            for ch in fdi.quarantined:
                frame.quality[ch] = frame.quality.get(ch, 0) | Q_SHIELDED
            for k, v in getattr(frame, "quality", {}).items():
                if (v & Q_SHIELDED) != 0 and k.lower() not in _quarantined_lower:
                    _quarantined_lower.append(k.lower())

            # 2. Vibration Order Tracking (DSP) - 10 Hz cadence
            if frame.rpm is not None and frame.throttle is not None and (
                    (self._tick_count % 2 == 1) or (self._cached_orders is None)):
                self._cached_orders = self.order_tracker.track(rpm=float(frame.rpm), throttle_pct=float(frame.throttle))
            # measured orders (the plant's accelerometer, faults included) win; the tracker only adds the extra
            # keys legacy consumers read until the DSP stage is rebuilt on measured data (M3)
            frame.vibration_orders = {**(self._cached_orders or {}), **(frame.vibration_orders or {})}

            # 3. State observer (M3-01: UKF on the M1 thermal model, measured inputs only)
            if self.ukf.ready(frame) and ((self._tick_count % UKF_EVERY == self._ukf_phase)
                                          or (self._cached_ukf is None)):
                shielded = {c for c in _quarantined_lower} | {
                    k.lower() for k, v in (frame.quality or {}).items() if v & Q_SHIELDED}
                ukf_nis = self.ukf.step(frame, skip={c.replace("oil_temp", "oil_t") for c in shielded})
                ukf_params = self.ukf.get_parameter_estimates(frame.t)
                self._cached_ukf = (ukf_nis, ukf_params)
            elif self._cached_ukf is not None:
                ukf_nis, ukf_params = self._cached_ukf
            else:
                ukf_nis, ukf_params = 0.0, []                  # no measured inputs yet: no twin estimate

            # quarantined temperature sensors: publish the observer's estimate instead, marked VIRTUAL (M3-03)
            if self.ukf.initialised:
                est = self.ukf.estimates()
                for ch in _quarantined_lower:
                    if ch not in est:
                        continue
                    if ch.startswith("cht_"):
                        frame.cht[int(ch[4:]) - 1] = est[ch]
                    else:
                        setattr(frame, ch, est[ch])
                    frame.quality[ch] = frame.quality.get(ch, 0) | Q_SHIELDED | Q_INTERPOLATED

            ukf_dict = {
                "nis": round(ukf_nis, 4),
                "params": [
                    {"name": p.name, "location": p.location, "mean": round(p.mean, 4),
                     "ci": [round(p.ci_lower, 4), round(p.ci_upper, 4)], "healthy": p.is_healthy}
                    for p in ukf_params
                ]
            }

            # 4. Virtual Sensor Synthesis
            virt = self.virtual_synthesizer.synthesize(frame)
            frame.virtual_sensors = virt

            # 5. Anomaly Detection (ResidualDetector)
            det = self.detector.score(frame, shielded_channels=_quarantined_lower) if self.detector else None
            # If the only anomaly was a quarantined sensor, suppressed_anomaly prevents false engine alarms
            if det and det.raw_alarm and len(_quarantined_lower) > 0:
                top_chans = [c[0].lower() for c in det.top_channels if abs(c[1]) > 2.5]
                if top_chans and all(c in _quarantined_lower for c in top_chans):
                    det.raw_alarm = False
                    det.confirmed = False
            if det is not None and self.isolator is not None and det.z_raw is not None:
                self.isolator.update(det.z_raw)
            if det is not None and self.trends is not None:
                self.trends.update(frame.t, det.z_raw, frame_readings(frame))

            hv = None
            if heavy and self.reservoir is not None and self.detector is not None:
                cal = self.detector.cal
                label, scores = self.reservoir.predict_step(cal.features(cal.z(frame, shielded_channels=_quarantined_lower)))
                hv = {"label": str(label), "classes": [str(c) for c in self.reservoir.classes_],
                      "scores": [round(float(s), 3) for s in scores]}

            # 6-9. Analytical layers (validity, damage/RUL, reliability, glide, diagnosis): on the observer's staggered
            # cadence - validity is judged from the observer's residuals, and the rest changes over minutes
            step_analytical = (self._tick_count % UKF_EVERY == self._ukf_phase) or self._cached_validity is None

            if step_analytical:
                # 6. Twin Validity & 3-Way Attribution
                res_dict = {}
                for i in range(min(len(frame.cht), self.cfg.cylinder_count)):
                    if frame.cht[i] is not None:
                        res_dict[f"cht_{i+1}"] = frame.cht[i] - float(self.ukf.x[i])
                if frame.oil_t is not None:
                    res_dict["oil_t"] = float(frame.oil_t) - float(self.ukf.x[self.cfg.cylinder_count + 1])
                self.validity_monitor.update(res_dict, operating_point={"throttle": frame.throttle, "rpm": frame.rpm,
                                                                        "alt": frame.alt})
                verdict = self.validity_monitor.assess(
                    fault_suspected=bool(det and det.confirmed),
                    sensor_quarantined=_quarantined_lower
                )
                self._cached_validity = verdict.as_dict()

                # 6b. Isolation (M3-05): Bayesian posterior over registry faults and sensor offsets while any
                # detection channel is alarming; evidence only, never the injected list (M3-07, T-DYN-4)
                alarm = bool(det and (det.confirmed or (det.drift or {}).get("alarm") or (det.novelty or {}).get("alarm")))
                if alarm and self.isolator is not None:
                    hyps = self.isolator.posterior(self.detector.cal.sensor_coupling(frame))
                    self._cached_hypotheses = [h.to_dict() for h in hyps]
                else:
                    self._cached_hypotheses = []

                # 7. Fatigue Damage Accumulation & Conformal RUL Intervals
                head_t = float(frame.cht[0]) if frame.cht and frame.cht[0] is not None else None
                if head_t is not None:
                    self.damage_accumulator.update(frame.t, head_t)
                self._dmg_finalise_counter += 1
                if self._dmg_finalise_counter >= 100:
                    self.damage_accumulator.finalise()
                    self._dmg_finalise_counter = 0
                dmg_state = self.damage_accumulator.current_state()
                # Time-to-limit from residual trends (M4-02). The RUL below is the M4-03 placeholder (see __init__).
                pred_rul = max(0.5, 18.0 * (1.0 - min(0.95, dmg_state.total * 3.0)))
                conf_int = self.conformal_rul.interval(pred_rul, alpha=0.05, scale=max(0.5, 2.0 * dmg_state.total))
                self._cached_prognostics = {
                    "damage": dmg_state.as_dict(),
                    "time_to_limit": self.trends.time_to_limit() if self.trends is not None else [],
                    "rul": {**conf_int.as_dict(), "status": "PLACEHOLDER (M4-03)"},
                }

                # 8. Mission Reliability & Glide Polar Reachability
                _n_cyl = self.cfg.cylinder_count
                _cyl_dmg = {f"cylinder_head_{i+1}": dmg_state.total for i in range(_n_cyl)}
                # Attribute damage to the components of the ISOLATED faults (posterior x estimated severity), so the
                # limiting component follows the evidence. The injected-fault list is never read (M3-07).
                for h in self._cached_hypotheses:
                    if h["kind"] != "PROCESS":
                        continue
                    weight = h["posterior"] * min(1.0, max(0.0, h.get("severity") or 0.0))
                    for _comp in components_for_fault(h["name"], h.get("cylinder")):
                        _dmg = min(0.90, weight * 0.75 + dmg_state.total)
                        _cyl_dmg[_comp] = max(_cyl_dmg.get(_comp, 0.0), _dmg)
                self.reliability_engine.set_damage(_cyl_dmg)
                rel_result = self.reliability_engine.analytic_reliability(profile=ISR_18H_PROFILE)
                glide_assessment = self.glide_polar.assess_glide(
                    alt_ft=float(frame.alt or 20000.0),
                    feathered=True,
                    uav_lat=34.2,
                    uav_lon=77.3
                )
                self._cached_reliability = {
                    "mission_reliability": round(rel_result["reliability"], 4),
                    "limiting_component": rel_result["limiting_component"],
                    "limiting_component_survival": round(rel_result["limiting_component_survival"] or 1.0, 4),
                    "mission_hours": rel_result["mission_hours"],
                    # Full ranking so the UI can show which components are actually
                    # driving the number rather than only naming the worst one.
                    "per_component_survival": {
                        name: round(value, 5)
                        for name, value in sorted(
                            rel_result["per_component_survival"].items(),
                            key=lambda kv: kv[1],
                        )
                    },
                    "damaged_components": sorted(
                        name for name, frac in _cyl_dmg.items() if frac > 0.01
                    ),
                }
                self._cached_glide = glide_assessment.as_dict()

                # 9. Deterministic directive from the registry for the leading hypothesis (M3-06/I-07)
                self._cached_diagnosis = directive(self._cached_hypotheses)

            validity_dict = self._cached_validity
            prognostics_dict = self._cached_prognostics
            reliability_dict = self._cached_reliability
            glide_dict = self._cached_glide
            diagnosis_dict = self._cached_diagnosis

            tick_events = self._detect_events(
                frame, det, sanity_dict, validity_dict, diagnosis_dict
            )

            verdict = self.status_evaluator.evaluate(frame.t, frame, engine_state=frame.engine_state,
                                                     quarantined=_quarantined_lower,
                                                     hypotheses=status_hypotheses(self._cached_hypotheses))
            alerts = [a.to_dict() for a in self.alert_manager.update(frame.t, verdict)]
            status = {**verdict.to_dict(), "alerts": alerts, "master": self.alert_manager.master()}
            t = Tick(
                engine_id=self.engine_id,
                frame=frame,
                truth=truth,
                detection=det,
                heavy=hv,
                sanity=sanity_dict,
                ukf=ukf_dict,
                validity=validity_dict,
                prognostics=prognostics_dict,
                reliability=reliability_dict,
                glide=glide_dict,
                diagnosis=diagnosis_dict,
                hypotheses=list(self._cached_hypotheses),
                status=status,
                events=tick_events,
            )
            self.buffer.append(t)
            return t

    def tick(self, heavy: bool = False) -> Tick:
        with self._lock:
            self.levers.advance(DT)
            raw_frame, truth = self.source.step(DT, throttle_pct=self.levers.throttle_pct,
                                                altitude_ft=self.levers.altitude_ft, oat_c=self.levers.oat_c)

            # Apply sensor layer manipulations (R7)
            frame = self.sensor_levers.apply(raw_frame, DT)

            if self.manual_origin or self.sensor_levers.has_active_faults:
                truth.origin = "MANUAL"
            else:
                truth.origin = "SCRIPTED"

            if self.sensor_levers.has_active_faults:
                truth.active_faults.extend(self.sensor_levers.active_fault_truths(frame.t))

            return self.ingest(frame, truth, heavy=heavy)

    # ---- presentation ------------------------------------------------------------------------
    def profile(self) -> Dict[str, Any]:
        c = self.cfg
        return {"engine_id": self.engine_id, "display_name": c.display_name, "n_cylinders": c.cylinder_count, "turbocharged": c.is_turbocharged,
                "compression_ignition": c.is_compression_ignition, "ready": self.ready,
                "heavy_ready": self.heavy_ready, "tail_id": self.tail_id,
                # These are operator commands, not plant truth; returning them lets a UI restore
                # its commanded-fault badge after a reconnect without exposing TruthRecord.
                "commanded_faults": list(self.injected),
                "faults": [{"mode": s.mode, "per_cylinder": s.per_cylinder, "scalar_visible": s.scalar_visible,
                            "layer": s.layer, "description": s.description} for s in faults_for(c)]}

    # ------------------------------------------------------------------
    # Event log
    # ------------------------------------------------------------------
    @property
    def event_seq(self) -> int:
        """Highest event sequence number issued so far, for incremental client catch-up."""
        return self._event_seq

    def _emit(self, level: str, kind: str, title: str, t_sim: float,
              detail: str = "", **extra: Any) -> Dict[str, Any]:
        """Append one event and return it. Caller holds self._lock."""
        self._event_seq += 1
        event = {
            "id": f"{self.engine_id}:{self._event_seq}",
            "seq": self._event_seq,
            "engine_id": self.engine_id,
            "t": t_sim,
            "wall_clock": time.time(),
            "level": level,
            "kind": kind,
            "title": title,
            "detail": detail,
            **extra,
        }
        self.events.append(event)
        return event

    def _detect_events(self, frame: Frame, det: Optional[DetectionResult],
                       sanity: Optional[Dict[str, Any]],
                       validity: Optional[Dict[str, Any]],
                       diagnosis: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Emit events for state transitions observed on this tick.

        Only transitions produce events, so a steady confirmed fault raises one WARNING
        rather than 20 per second.
        """
        new: List[Dict[str, Any]] = []
        st = self._event_state
        t_sim = frame.t

        # -- detector escalation / de-escalation
        stage = "CONFIRMED" if (det and det.confirmed) else \
                "RAW_ALARM" if (det and det.raw_alarm) else "NOMINAL"
        if stage != st["detector"]:
            channels = [c[0] if isinstance(c, (tuple, list)) else c
                        for c in (det.top_channels if det else [])][:4]
            cyl = _first_cylinder_index(det.top_channels) if det else None
            if stage == "CONFIRMED":
                name = (diagnosis or {}).get("fault_name") or "Residual anomaly"
                new.append(self._emit(
                    "WARNING", "DETECTOR_CONFIRMED",
                    f"{name} confirmed" + (f" · cylinder {cyl}" if cyl else ""),
                    t_sim,
                    detail="Persistence gate confirmed the residual anomaly.",
                    channels=channels, cylinder=cyl,
                    ata_chapter=(diagnosis or {}).get("ata_chapter"),
                ))
            elif stage == "RAW_ALARM":
                new.append(self._emit(
                    "ADVISORY", "DETECTOR_RAW_ALARM", "Residual anomaly (unconfirmed)",
                    t_sim,
                    detail="Tier-0 score crossed its threshold; the persistence gate has "
                           "not confirmed it yet.",
                    channels=channels, cylinder=cyl,
                ))
            else:
                new.append(self._emit(
                    "INFORMATION", "DETECTOR_CLEAR", "Residual anomaly cleared", t_sim,
                    detail="Tier-0 score returned below threshold.",
                ))
            st["detector"] = stage

        # -- sensor quarantine. Reported separately from the detector because a
        # quarantine suppresses the very residuals the detector would have raised.
        quarantined = frozenset((sanity or {}).get("failed_channels") or ())
        if quarantined != st["quarantined"]:
            added = sorted(quarantined - st["quarantined"])
            removed = sorted(st["quarantined"] - quarantined)
            if added:
                new.append(self._emit(
                    "WARNING", "SENSOR_QUARANTINE",
                    f"{len(added)} channel(s) quarantined", t_sim,
                    detail=(sanity or {}).get("advisory", ""), channels=added,
                ))
            if removed:
                new.append(self._emit(
                    "INFORMATION", "SENSOR_RESTORED",
                    f"{len(removed)} channel(s) returned to service", t_sim,
                    channels=removed,
                ))
            st["quarantined"] = quarantined

        suppressed = bool((sanity or {}).get("suppressed_anomaly"))
        if suppressed != st["suppressed"]:
            if suppressed:
                new.append(self._emit(
                    "WARNING", "EVIDENCE_SUPPRESSED", "Detector evidence suppressed", t_sim,
                    detail="Residual shielding is active for quarantined channels, so "
                           "anomaly evidence on them is being withheld. Absence of an "
                           "alarm is not evidence of a healthy engine.",
                    channels=sorted(quarantined),
                ))
            else:
                new.append(self._emit(
                    "INFORMATION", "EVIDENCE_RESTORED", "Detector evidence restored", t_sim,
                ))
            st["suppressed"] = suppressed

        # -- twin validity
        verdict = (validity or {}).get("verdict")
        if verdict and verdict != st["verdict"]:
            attribution = (validity or {}).get("attribution") or "UNATTRIBUTED"
            if verdict == "VALID":
                new.append(self._emit(
                    "INFORMATION", "TWIN_VALID", "Twin consistent with the engine", t_sim,
                ))
            else:
                new.append(self._emit(
                    "CRITICAL" if attribution == "ENGINE_FAULT" else "WARNING",
                    "TWIN_INVALID", f"Twin self-assessment: {verdict} ({attribution})",
                    t_sim, detail=(validity or {}).get("explanation", ""),
                    reasons=list((validity or {}).get("TWIN_REASONS") or ()),
                ))
            st["verdict"] = verdict

        # -- operator-commanded scenarios
        fault_names = frozenset(
            f"{i.get('mode')}:{i.get('cylinder') or ''}" for i in self.injected
        )
        if fault_names != st["fault_names"]:
            for key in sorted(fault_names - st["fault_names"]):
                mode, _, cyl = key.partition(":")
                new.append(self._emit(
                    "INFORMATION", "FAULT_INJECTED",
                    f"Scenario injected: {mode}" + (f" · cylinder {cyl}" if cyl else ""),
                    t_sim, detail="Operator-commanded scenario. Origin MANUAL.",
                    cylinder=int(cyl) if cyl else None, origin="MANUAL",
                ))
            if st["fault_names"] and not fault_names:
                new.append(self._emit(
                    "INFORMATION", "FAULT_CLEARED", "Scenarios cleared", t_sim,
                    origin="MANUAL",
                ))
            st["fault_names"] = fault_names

        return new

    @staticmethod
    def payload(t: Tick) -> Dict[str, Any]:
        f, d = t.frame, t.detection
        diag_out = dict(t.diagnosis) if t.diagnosis else None
        if diag_out and "fault_id" in diag_out:
            diag_out["mode_code"] = diag_out.pop("fault_id")
        return {
            "engine_id": t.engine_id, "t": f.t, "source": f.source, "evidence_class": "SIMULATION",
            "channels": f.channels(), "cht": f.cht, "egt": f.egt,
            "detection": None if d is None else {
                "scores": d.scores, "ratios": d.ratios, "raw_alarm": d.raw_alarm, "confirmed": d.confirmed,
                "top_channels": d.top_channels},
            "heavy": t.heavy,
            "sanity": t.sanity,
            "ukf": t.ukf,
            "validity": t.validity,
            "prognostics": t.prognostics,
            "reliability": t.reliability,
            "glide": t.glide,
            "diagnosis": diag_out,
            "vibration_orders": f.vibration_orders,
            "virtual_sensors": f.virtual_sensors,
            "events": t.events,
        }

