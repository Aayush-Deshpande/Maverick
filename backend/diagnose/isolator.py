"""Bayesian fault isolation on residual signatures (card M3-05, idea text I-05, P Part 0 rule 4).

Evidence: the detector's unclipped residual z-vector (backend/detect/calibration.py; measured minus the nominal
model, per tail), exponentially averaged over window_frames. Hypotheses:
  - NOMINAL: zbar ~ N(0, v I)
  - process fault f at location l: zbar ~ N(s * m_f,l, v I), severity s ~ U[0, S]. m_f,l is the CALIBRATED
    signature (configs/diagnose/signatures/<engine>.json, measured at severity 1); cylinder faults are measured
    at one cylinder and the cylinder channels are permuted for the others;
  - sensor fault on channel c (S02 bias / S03 drift that the one-channel FDI checks cannot see): only channel c
    moves, zbar ~ N(b e_c, v I), b ~ U[-B, B]. A process fault moves its physically coupled channels together, so
    the two are told apart by the other channels, not by the size of the offset.
The severity is integrated out in closed form (Gaussian x uniform -> normal CDF difference), which also gives the
Occam penalty: a hypothesis that could explain anything pays for it. Priors come from the FMECA occurrence of the
fault's mode (docs/reliability/fmeca.json, mapping in configs/diagnose/isolation.json). Posterior over all
hypotheses = softmax(log prior + log marginal likelihood). Signatures closer than the ambiguity cosine form one
ambiguity group (they cannot be separated by these channels; the report says so instead of guessing).
Reads only the residual vector: no plant truth, no injected-fault list (tests/test_no_truth_leak.py).
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
from scipy.special import ndtr

from backend.sim.source import registry          # cached registry: the schema check runs once

ROOT = Path(__file__).resolve().parents[2]
SIGNATURES = ROOT / "configs" / "diagnose" / "signatures"
SETTINGS = ROOT / "configs" / "diagnose" / "isolation.json"
FMECA = ROOT / "docs" / "reliability" / "fmeca.json"
NOMINAL = "NOMINAL"
SENSOR_FAULT_ID = "S02"            # a single-channel offset; S03 drift is the same hypothesis growing in time


def _v(d: Dict, k: str):
    return d[k]["value"]


@dataclass
class IsolationHypothesis:
    fault_id: Optional[str]
    name: str
    kind: str                          # NOMINAL | PROCESS | SENSOR
    posterior: float
    cylinder: Optional[int] = None
    channel: Optional[str] = None
    severity: Optional[float] = None   # MAP severity relative to the signature (1 = calibrated severity 1)
    group: Optional[str] = None        # ambiguity group id (hypotheses that cannot be told apart)
    supporting: List[tuple] = field(default_factory=list)       # (channel, z) agreeing with the signature
    contradicting: List[tuple] = field(default_factory=list)    # (channel, z) the signature predicts but is absent

    def to_dict(self) -> Dict:
        return {"fault_id": self.fault_id, "name": self.name, "kind": self.kind, "posterior": round(self.posterior, 4),
                "cylinder": self.cylinder, "channel": self.channel,
                "severity": None if self.severity is None else round(self.severity, 3), "group": self.group,
                "supporting": [{"channel": c, "z": round(z, 2)} for c, z in self.supporting],
                "contradicting": [{"channel": c, "z": round(z, 2)} for c, z in self.contradicting]}


def _log_marginal(z: np.ndarray, m: np.ndarray, var: float, lo: float, hi: float) -> tuple[float, float]:
    """log of (1/(hi-lo)) * integral_lo^hi N(z; s m, var I) ds (constants common to all hypotheses dropped),
    and the MAP amplitude clipped to [lo, hi]."""
    a = float(m @ m) / var
    c = float(z @ z) / var
    if a <= 1e-12:
        return -0.5 * c, 0.0
    b = float(z @ m) / var
    s_hat = b / a
    ra = math.sqrt(a)
    mass = float(ndtr(ra * (hi - s_hat)) - ndtr(ra * (lo - s_hat)))
    log_int = -0.5 * (c - b * b / a) + 0.5 * math.log(2 * math.pi / a) + math.log(max(mass, 1e-300))
    return log_int - math.log(hi - lo), min(max(s_hat, lo), hi)


class BayesianIsolator:
    def __init__(self, engine_id: str, channels: Sequence[str]) -> None:
        self.engine_id = engine_id
        self.channels = list(channels)
        cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
        self.var = float(_v(cfg, "residual_var"))
        self.s_max = float(_v(cfg, "severity_max"))
        self.b_max = float(_v(cfg, "sensor_bias_max_z"))
        self.cos_amb = float(_v(cfg, "ambiguity_cosine"))
        self.top_k = int(_v(cfg, "top_k"))
        self.min_post = float(_v(cfg, "min_posterior"))
        self.alpha = 1.0 / float(_v(cfg, "window_frames"))
        fm_map, default_occ = _v(cfg, "fmeca_map"), float(_v(cfg, "default_occurrence"))
        occ = {m["mode_id"]: float(m["occurrence"]) for m in json.loads(FMECA.read_text(encoding="utf-8"))["modes"]}
        reg = registry()
        self.names: Dict[str, str] = {}
        sig_path = SIGNATURES / f"{engine_id}.json"
        sig = json.loads(sig_path.read_text(encoding="utf-8")) if sig_path.exists() else {"faults": {}, "channels": []}
        self.available = sig_path.exists()
        n_cyl = sum(1 for c in self.channels if c.startswith("cht_"))
        loc = int(sig.get("location_cylinder", 1))
        index = {c: i for i, c in enumerate(self.channels)}
        # hypothesis table: (fault_id, kind, cylinder, channel, mean vector, log prior)
        self.hyp: List[tuple] = []
        for fid, entry in sig["faults"].items():
            spec = reg.get(fid)
            self.names[fid] = spec.name
            base = np.zeros(len(self.channels))
            for ch, val in zip(sig["channels"], entry["z"]):
                if ch in index:
                    base[index[ch]] = val
            prior = math.log(occ.get(fm_map.get(fid) or "", default_occ))
            if entry["scope"] == "CYLINDER":
                for k in range(1, n_cyl + 1):
                    self.hyp.append((fid, "PROCESS", k, None, self._move_cylinder(base, loc, k, n_cyl), prior - math.log(n_cyl)))
            else:
                self.hyp.append((fid, "PROCESS", None, None, base, prior))
        s_prior = math.log(occ.get(fm_map.get(SENSOR_FAULT_ID) or "", default_occ)) - math.log(max(len(self.channels), 1))
        self.names[SENSOR_FAULT_ID] = reg.get(SENSOR_FAULT_ID).name
        shared = _v(cfg, "shared_sensors")                  # sensor name -> prefix of the channels it feeds (D61)
        grouped = {ch for ch in self.channels for p in shared.values() if ch.startswith(p)}
        for i, ch in enumerate(self.channels):
            if ch in grouped:
                continue
            e = np.zeros(len(self.channels))
            e[i] = 1.0
            self.hyp.append((SENSOR_FAULT_ID, "SENSOR", None, ch, e, s_prior))
        self.sensor_groups: Dict[str, List[int]] = {}
        for sensor, prefix in shared.items():                # one hypothesis: all of that sensor's channels shift
            idx = [i for i, ch in enumerate(self.channels) if ch.startswith(prefix)]
            if idx:
                self.sensor_groups[sensor] = idx
                e = np.zeros(len(self.channels))
                e[idx] = 1.0 / math.sqrt(len(idx))
                self.hyp.append((SENSOR_FAULT_ID, "SENSOR", None, sensor, e, s_prior))
        best_prior = max((h[5] for h in self.hyp), default=0.0)
        self.nominal_prior = best_prior + float(_v(cfg, "nominal_log_odds"))
        self.groups = self._ambiguity_groups()
        self.zbar: Optional[np.ndarray] = None

    @staticmethod
    def _move_cylinder(v: np.ndarray, src: int, dst: int, n: int) -> np.ndarray:
        """Signature measured at cylinder src -> the same fault at cylinder dst (swap both cylinder blocks)."""
        out = v.copy()
        for block in (0, n):
            a, b = block + src - 1, block + dst - 1
            out[a], out[b] = v[b], v[a]
        return out

    def _ambiguity_groups(self) -> List[str]:
        """Group id per hypothesis: collinear signatures (|cos| >= ambiguity cosine) share the first one's id."""
        ids: List[str] = []
        units = [h[4] / max(np.linalg.norm(h[4]), 1e-12) for h in self.hyp]
        for i, h in enumerate(self.hyp):
            gid = None
            for j in range(i):
                if float(units[i] @ units[j]) >= self.cos_amb:
                    gid = ids[j]
                    break
            ids.append(gid or f"G{i}")
        return ids

    def reset(self) -> None:
        self.zbar = None

    def update(self, z: Sequence[float]) -> None:
        """Feed one frame's unclipped residual z-vector (in self.channels order); NaN = unmeasured (no evidence)."""
        z = np.nan_to_num(np.asarray(z, dtype=float), nan=0.0)
        self.zbar = z if self.zbar is None else self.zbar + self.alpha * (z - self.zbar)

    def posterior(self, coupling: Optional[np.ndarray] = None) -> List[IsolationHypothesis]:
        """Ranked hypotheses (NOMINAL included) for the current averaged residual. coupling: the calibration's
        sensor_coupling for the latest frame (a biased INPUT sensor also moves the channels predicted from it);
        without it a sensor hypothesis moves its own channel only."""
        if self.zbar is None:
            return []
        z = self.zbar
        logs = [self.nominal_prior - 0.5 * float(z @ z) / self.var]
        sev = [None]
        idx = {c: i for i, c in enumerate(self.channels)}
        for fid, kind, cyl, ch, m, prior in self.hyp:
            if kind == "SENSOR" and coupling is not None:
                m = self._coupled(coupling, idx, ch)
            lo, hi = (0.0, self.s_max) if kind == "PROCESS" else (-self.b_max, self.b_max)
            ll, s = _log_marginal(z, m, self.var, lo, hi)
            logs.append(prior + ll)
            sev.append(s)
        logs = np.array(logs)
        p = np.exp(logs - logs.max())
        p /= p.sum()
        order = np.argsort(-p)
        out: List[IsolationHypothesis] = []
        for i in order[: self.top_k + 1]:
            if p[i] < self.min_post and out:
                break
            if i == 0:
                out.append(IsolationHypothesis(None, NOMINAL, "NOMINAL", float(p[0])))
                continue
            fid, kind, cyl, ch, m, _prior = self.hyp[i - 1]
            if kind == "SENSOR" and coupling is not None:
                m = self._coupled(coupling, idx, ch)
            out.append(IsolationHypothesis(fid, self.names.get(fid, fid), kind, float(p[i]), cylinder=cyl, channel=ch,
                                           severity=sev[i], group=self.groups[i - 1],
                                           supporting=self._evidence(z, m, agree=True),
                                           contradicting=self._evidence(z, m, agree=False)))
        return out

    def _coupled(self, coupling: np.ndarray, idx: Dict[str, int], ch: str) -> np.ndarray:
        """Sensor-offset signature through the calibration coupling: one channel, or a shared sensor's channels."""
        if ch in idx:
            return coupling[:, idx[ch]]
        cols = self.sensor_groups[ch]
        return coupling[:, cols].sum(axis=1) / math.sqrt(len(cols))

    def _evidence(self, z: np.ndarray, m: np.ndarray, agree: bool, k: int = 3) -> List[tuple]:
        """Channels that support the hypothesis (z along the signature) or contradict it (signature expects a
        clear move that is absent or opposite). Per-channel contribution = z_i * m_i / |m|."""
        norm = max(float(np.linalg.norm(m)), 1e-12)
        contrib = z * m / norm
        if agree:
            idx = [i for i in np.argsort(-contrib) if contrib[i] > 0][:k]
        else:
            expected = np.abs(m) / norm > 0.3
            idx = [i for i in np.argsort(contrib) if expected[i] and contrib[i] < 0.5 * abs(m[i]) / norm][:k]
        return [(self.channels[i], float(z[i])) for i in idx]
