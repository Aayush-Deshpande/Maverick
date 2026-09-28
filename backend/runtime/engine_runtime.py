"""EngineRuntime -- one engine profile's simulator + injectors + detector bank (R1/R2/R3/R7, D29, D05).

No module-level state: every runtime owns its plant, levers, sensor levers, detector, buffers and locks,
so a fault on one engine can never touch another. Tier-0 (calibrated residual scorers, FlyHash) runs every tick;
tier-1 (reservoir) is trained and stepped only while this engine is the SELECTED one (D29/D36).

Implements ingest(frame, truth): processing a live tick and ingesting a replayed frame run the identical path.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional

import numpy as np

from backend.core.frame import Frame, TruthRecord
from backend.detect import DetectionResult, Reservoir, ResidualDetector
from backend.diagnose.bn import DiagnosticBayesianNetwork
from backend.diagnose.evidence_adapter import build_evidence
from backend.diagnose.explain import ExplanationGenerator
from backend.ml.flyhash_novelty import (
    FlyNoveltyDetector,
    NoveltyReport,
    residual_and_order_features,
)
from backend.mission.engine_components import components_for
from backend.mission.prescriptive import PrescriptiveAdvisor
from backend.mission.reliability import ISR_18H_PROFILE, MissionProfile, MissionReliabilityEngine
from backend.physics.engine_config import EngineConfig, load_engine_config
from backend.runtime.levers import Levers
from backend.runtime.registry import FAULT_REGISTRY, faults_for, thermal_visible_faults
from backend.runtime.sensor_levers import SensorLevers
from backend.sources import PlantSource

DT = 1.0                      # simulated seconds per tick (calibrated at this cadence)
WARMUP_TICKS = 900            # ground run-up used to calibrate this tail
_WARM_SCHEDULE = [(45, 2000, 25), (60, 9000, 10), (75, 12000, 0), (90, 18000, -15), (70, 5000, 30), (85, 15000, -5)]


@dataclass
class Tick:
    engine_id: str
    frame: Frame
    truth: TruthRecord
    detection: Optional[DetectionResult]
    heavy: Optional[Dict[str, Any]]
    diagnosis: Optional[List[Dict[str, Any]]] = None
    novelty: Optional[NoveltyReport] = None


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
        self.bn: DiagnosticBayesianNetwork = DiagnosticBayesianNetwork(self.cfg)
        self.explainer: ExplanationGenerator = ExplanationGenerator()
        self.reliability_engine: MissionReliabilityEngine = MissionReliabilityEngine(components_for(self.cfg), seed=seed)
        self.advisor: PrescriptiveAdvisor = PrescriptiveAdvisor(self.reliability_engine, n_trials=500)
        self.flyhash: FlyNoveltyDetector = FlyNoveltyDetector(seed=seed, calibration_frames=100)
        self.manual_origin = False
        self.injected: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._heavy_lock = threading.Lock()
        self._warmup_ticks = warmup_ticks
        self.ready = False
        self.heavy_ready = False

    # ---- lifecycle ------------------------------------------------------------------------
    def calibrate(self) -> None:
        """Nominal ground run-up on THIS tail, then fit calibration + conformal thresholds."""
        rng = np.random.default_rng(self.seed + 12345)
        op, frames = _WARM_SCHEDULE[0], []
        for i in range(self._warmup_ticks + 24):
            if i % 30 == 0:
                op = _WARM_SCHEDULE[int(rng.integers(len(_WARM_SCHEDULE)))]
            f, _ = self.source.step(DT, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
            if i >= 24:
                frames.append(f)
        with self._lock:
            self.detector = ResidualDetector.calibrate(frames, alpha=0.01)
            # Fold nominal frames into FlyHash seen dictionary
            self.flyhash.reset_calibration()
            for f in frames:
                z = self.detector.cal.z(f)
                names = self.detector.cal.channel_names()
                res_dict = {k: float(v) for k, v in zip(names, z)}
                vec = residual_and_order_features(res_dict, getattr(f, "order_features", None))
                self.flyhash.observe_nominal(vec)
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
            faults = thermal_visible_faults(self.cfg)
            seqs, labs = [], []

            def collect(fault: Optional[str], seed_off: int):
                src = PlantSource(self.engine_id, seed=self.seed)
                rng = np.random.default_rng(self.seed * 31 + seed_off)
                if fault:
                    cyl = int(rng.integers(1, src.n_cylinders + 1)) if FAULT_REGISTRY[fault].per_cylinder else None
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
            self.levers.set_targets(**kw)
            self.manual_origin = True
            return {"throttle_target": self.levers.throttle_target,
                    "altitude_target": self.levers.altitude_target, "oat_target": self.levers.oat_target}

    def inject_fault(self, mode: str, cylinder: Optional[int] = None, severity: float = 0.8,
                     ramp_sec: float = 60.0, origin: str = "MANUAL") -> Dict[str, Any]:
        spec = FAULT_REGISTRY.get(mode)
        if spec is None or not spec.applies_to(self.cfg):
            raise ValueError(f"{mode!r} is not a valid fault for {self.engine_id}")
        if spec.per_cylinder:
            if cylinder is None or not 1 <= cylinder <= self.cfg.cylinder_count:
                raise ValueError(f"{mode} needs cylinder 1..{self.cfg.cylinder_count}")
        else:
            cylinder = None
        with self._lock:
            self.source.inject_fault(mode, cylinder=cylinder, severity=severity, ramp_sec=ramp_sec)
            if origin == "MANUAL":
                self.manual_origin = True
            rec = {"mode": mode, "cylinder": cylinder, "severity": severity, "ramp_sec": ramp_sec,
                   "origin": origin, "t": self.source.plant._elapsed_sec}
            self.injected.append(rec)
            return rec

    def clear_faults(self) -> None:
        with self._lock:
            self.source.clear_faults()
            self.sensor_levers.clear()
            self.injected.clear()
            if self.detector:
                self.detector.gate.reset()

    def set_sensor_fault(self, kind: str, channel: str, **kwargs) -> None:
        """Inject sensor-level fault (R7): bias, drift, stuck, noise, dropout, spoof."""
        with self._lock:
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
        """Process one Frame through the detector stack. Identical for live and replay."""
        with self._lock:
            if truth is None:
                truth = TruthRecord(t=frame.t, origin="REPLAY")

            det = self.detector.score(frame) if self.detector else None
            hv = None
            if heavy and self.reservoir is not None and self.detector is not None:
                cal = self.detector.cal
                label, scores = self.reservoir.predict_step(cal.features(cal.z(frame)))
                hv = {"label": str(label), "classes": [str(c) for c in self.reservoir.classes_],
                      "scores": [round(float(s), 3) for s in scores]}

            diag: Optional[List[Dict[str, Any]]] = None
            if det is not None and (det.raw_alarm or det.confirmed or det.top_channels):
                evidence = build_evidence(det, frame, self.cfg)
                if evidence:
                    hypotheses = self.bn.diagnose(evidence)
                    if hypotheses:
                        diag = []
                        for h in hypotheses:
                            exp = self.explainer.explain(h, {"rpm": getattr(frame, "rpm", 0)})
                            diag.append({
                                "mode_id": h.mode_id,
                                "location": h.location,
                                "probability": round(h.probability, 4),
                                "ambiguity_group_id": h.ambiguity_group_id,
                                "supporting_evidence": h.supporting_evidence,
                                "operator_text": exp.operator_text,
                                "engineer_text": exp.engineer_text,
                                "maintainer_text": exp.maintainer_text,
                                "ata_chapter": exp.ata_chapter,
                            })

            novelty_rep: Optional[NoveltyReport] = None
            if self.detector is not None:
                z = self.detector.cal.z(frame)
                names = self.detector.cal.channel_names()
                res_dict = {k: float(v) for k, v in zip(names, z)}
                vec = residual_and_order_features(res_dict, getattr(frame, "order_features", None))
                novelty_rep = self.flyhash.score(vec)

            t = Tick(self.engine_id, frame, truth, det, hv, diag, novelty_rep)
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

    def mission_reliability(self, hours: float = 18.0, profile: Optional[MissionProfile] = None) -> Dict[str, Any]:
        """Compute mission reliability and prescriptive derate options for this engine.

        `profile`, when given, is the ACTUAL mission profile being flown (built from a live
        phase-based mission's real remaining phases -- see
        backend/mission/executive.py's `_build_live_reliability_profile()`) and is used
        directly instead of the generic canned `ISR_18H_PROFILE`. Falls back to the generic
        profile (truncated to `hours`) only when no real mission profile is available, e.g.
        the standalone `/api/engines/{id}/reliability` endpoint with no mission loaded.
        """
        if profile is None:
            profile = ISR_18H_PROFILE.truncated_to(hours) if hours != 18.0 else ISR_18H_PROFILE
        res = self.reliability_engine.analytic_reliability(profile)
        derates = self.advisor.derate_options(profile, scales=(1.0, 0.95, 0.90, 0.85, 0.80))
        rec = self.advisor.recommend_derate(profile)
        return {
            "engine_id": self.engine_id,
            "mission_hours": hours,
            "reliability": round(res["reliability"], 4),
            "limiting_component": res["limiting_component"],
            "limiting_component_survival": round(res.get("limiting_component_survival", 1.0), 4),
            "per_component_survival": {k: round(v, 4) for k, v in res.get("per_component_survival", {}).items()},
            "derate_options": [d.as_dict() for d in derates],
            "recommendation": rec.sentence() if rec else "Nominal operation meets reliability target.",
        }

    @staticmethod
    def payload(t: Tick) -> Dict[str, Any]:
        f, d = t.frame, t.detection
        return {
            "engine_id": t.engine_id, "t": f.t, "source": f.source, "evidence_class": "SIMULATION",
            "channels": f.channels(), "cht": f.cht, "egt": f.egt,
            "detection": None if d is None else {
                "scores": d.scores, "ratios": d.ratios, "raw_alarm": d.raw_alarm, "confirmed": d.confirmed,
                "top_channels": d.top_channels},
            "heavy": t.heavy,
            "diagnosis": t.diagnosis,
            "novelty": None if t.novelty is None else {
                "novelty_score": t.novelty.novelty_score,
                "is_novel": t.novelty.is_novel,
                "calibrated": t.novelty.calibrated,
                "calibration_frames_seen": t.novelty.calibration_frames_seen,
                "active_bits": t.novelty.active_bits,
                "unseen_bits": t.novelty.unseen_bits,
                "novelty_threshold": 0.6,
            },
        }
