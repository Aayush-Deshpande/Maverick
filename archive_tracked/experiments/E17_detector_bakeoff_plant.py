"""
E17 -- Universal vs per-engine detectors, and fly-inspired novelty vs classical, on the
multi-engine plant.  (docs/build/DETECTOR_DECISION.md)

Question: with several engines running at once, do we want (a) one universal detector fed
engine-normalised residuals, (b) one detector per engine, or (c) a fly-inspired novelty
detector -- and does a NEW engine (never seen in training, only calibrated on nominal data)
work with a universal model?

Evidence class: SIMULATION only.  The plant is not engine-class-aware internally (rpm map
and EGT formula are shared -- FINDINGS F21), so cross-engine differences here are partly
artefacts of the plant.  Read the results as *relative behaviour of method families on
tabular thermal channels*, not as engine performance.  Waveform / high-dimensional
behaviour (where fly-inspired methods are expected to be strongest) is NOT tested here.

Design (leakage-safe): train and test use different plant seeds = different physical builds
(EngineVariation + sensor model).  Split is by run, never by frame.  Fault labels are used
only for the supervised classifiers and for scoring; novelty detectors train on nominal only.

Run:  python experiments/E17_detector_bakeoff_plant.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import Ridge
from sklearn.metrics import f1_score, roc_auc_score, roc_curve

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from backend.ml.flyhash_novelty import FlyHashEncoder  # noqa: E402
from backend.physics.engine_config import available_engines, load_engine_config  # noqa: E402
from backend.sources import PlantSource  # noqa: E402

DT = 5.0
N_FRAMES = 180
SETTLE = 24                      # frames dropped while thermal states settle
POS_FROM = 30                    # fault frames counted once the ramp is >= 60 % done
FAULTS = ["MISFIRE", "COOLING_DEGRADATION", "OIL_PRESSURE_LOSS", "AIR_FILTER_BLOCKAGE",
          "SENSOR_STUCK", "BOOST_LEAK"]            # BOOST_LEAK: turbo engines only
CYL_FAULTS = {"MISFIRE", "SENSOR_STUCK"}
INVISIBLE_THERMALLY = ["INJECTOR_COKING", "INJECTOR_NEEDLE_STICK", "RAIL_PRESSURE_DECAY",
                       "TURBO_BEARING_WEAR"]       # probed: no effect on any thermal channel
OPS = [(45, 2000, 25), (60, 9000, 10), (75, 12000, 0), (90, 18000, -15), (100, 22000, -30),
       (70, 5000, 30), (85, 15000, -5)]           # (throttle %, altitude ft, OAT C)
N_RUN = {"nom_train": 10, "nom_test": 6, "fault_train": 5, "fault_test": 3}
SEED_TEST_OFFSET = 1000


# --------------------------------------------------------------------------- data

def simulate_run(engine: str, seed: int, fault: str | None):
    rng = np.random.default_rng(seed)
    src = PlantSource(engine, seed=seed)
    if fault:
        cyl = int(rng.integers(1, src.n_cylinders + 1)) if fault in CYL_FAULTS else None
        src.inject_fault(fault, cylinder=cyl, severity=float(rng.uniform(0.7, 1.0)), ramp_sec=240.0)
    X_cmd, Y, keep = [], [], []
    op = OPS[int(rng.integers(len(OPS)))]
    for i in range(N_FRAMES):
        if i % 30 == 0:
            op = OPS[int(rng.integers(len(OPS)))]
        frame, _truth = src.step(DT, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
        X_cmd.append([op[0] / 100.0, op[1] / 1e4, op[2] / 50.0])
        Y.append(frame.cht + frame.egt + [frame.oil_p, frame.oil_t, frame.fuel_flow,
                                          frame.map_kpa, frame.rpm])
        keep.append(i >= (POS_FROM if fault else SETTLE))
    return np.array(X_cmd), np.array(Y), np.array(keep)


def build(engine: str, n_cyl: int, turbo: bool):
    """Returns dict split -> list of (X_cmd, Y, label) with label 0 = nominal, else fault idx+1."""
    faults = [f for f in FAULTS if turbo or f != "BOOST_LEAK"]
    out = {"train": [], "test": []}
    for split, off in (("train", 0), ("test", SEED_TEST_OFFSET)):
        for r in range(N_RUN["nom_" + split]):
            X, Y, k = simulate_run(engine, off + r, None)
            out[split].append((X[k], Y[k], 0))
        for fi, f in enumerate(faults):
            for r in range(N_RUN["fault_" + split]):
                X, Y, k = simulate_run(engine, off + 100 * (fi + 1) + r, f)
                out[split].append((X[k], Y[k], FAULTS.index(f) + 1))
    return out


# --------------------------------------------------------------------------- features

def design(Xc):
    t, a, o = Xc[:, 0], Xc[:, 1], Xc[:, 2]
    return np.column_stack([t, a, o, t * t, a * a, t * a, o * t])


class Calib:
    """Per-engine 'twin-lite': regress every channel on the commanded operating point using
    NOMINAL data only; residuals are z-scored.  This is where engine universality lives."""

    def __init__(self, nominal_runs, n_cyl):
        X = np.vstack([design(x) for x, _, _ in nominal_runs])
        Y = np.vstack([y for _, y, _ in nominal_runs])
        self.n_cyl = n_cyl
        self.m = Ridge(alpha=1e-3).fit(X, Y)
        res = Y - self.m.predict(X)
        self.sigma = np.maximum(res.std(0), 1e-3 * np.maximum(np.abs(Y.mean(0)), 1.0))

    def z(self, Xc, Y):
        return (Y - self.m.predict(design(Xc))) / self.sigma

    def features(self, Xc, Y):
        z = self.z(Xc, Y)
        n = self.n_cyl
        f = []
        for blk in (z[:, :n], z[:, n:2 * n]):
            f += [blk.mean(1), blk.max(1), blk.min(1), blk.std(1)]
        f += [z[:, 2 * n + j] for j in range(5)]
        return np.column_stack(f)

    @staticmethod
    def raw_features(Y, n):
        f = []
        for blk in (Y[:, :n], Y[:, n:2 * n]):
            f += [blk.mean(1), blk.max(1), blk.min(1), blk.std(1)]
        f += [Y[:, 2 * n + j] for j in range(5)]
        return np.column_stack(f)


def stack(runs, fn):
    X = np.vstack([fn(x, y) for x, y, _ in runs])
    lab = np.concatenate([[l] * len(x) for x, _, l in runs])
    return X, lab


# --------------------------------------------------------------------------- novelty

class FBF:
    """Fly-inspired novelty: FlyHash (sparse random projection + winner-take-all) feeding a
    frequency memory of nominal activations (Fly-Bloom-Filter-like, distance sensitive).
    Own minimal implementation of the published algorithm (Dasgupta et al., Science 2017,
    PNAS 2018); the open-source libs (fbfc MIT; ffbf: no licence) implement the same idea."""

    def __init__(self, dim, expansion=20, fan_in=6, sparsity=0.05, f0=0.05, seed=7):
        self.enc = FlyHashEncoder(dim, expansion, fan_in, sparsity, seed)
        self.f0 = f0

    def fit(self, Z):
        codes = np.array([self.enc.encode(z) for z in Z])
        self.freq = codes.mean(0)
        return self

    def score(self, Z):
        out = np.empty(len(Z))
        for i, z in enumerate(Z):
            act = self.enc.encode(z)
            fam = np.minimum(1.0, self.freq[act] / self.f0)
            out[i] = 1.0 - fam.mean()
        return out


class Maha:
    def fit(self, Z):
        self.mu = Z.mean(0)
        self.P = np.linalg.pinv(np.cov(Z.T) + 1e-6 * np.eye(Z.shape[1]))
        return self

    def score(self, Z):
        d = Z - self.mu
        return np.sqrt(np.einsum("ij,jk,ik->i", d, self.P, d))


class MaxZ:
    def fit(self, Z):
        return self

    def score(self, Z):
        return np.abs(Z).max(1)


class IF:
    def fit(self, Z):
        self.m = IsolationForest(n_estimators=100, random_state=0).fit(Z)
        return self

    def score(self, Z):
        return -self.m.score_samples(Z)


def novelty_metrics(score, lab):
    y = (lab > 0).astype(int)
    auc = float(roc_auc_score(y, score))
    fpr, tpr, _ = roc_curve(y, score)
    tpr1 = float(np.interp(0.01, fpr, tpr))
    return auc, tpr1


DETECTORS = {"FlyHash-FBF": lambda d: FBF(d), "Mahalanobis": lambda d: Maha(),
             "IsolationForest": lambda d: IF(), "max|z| threshold": lambda d: MaxZ()}


# --------------------------------------------------------------------------- main

def rf():
    return RandomForestClassifier(n_estimators=100, random_state=0, n_jobs=-1)


def macro_f1(y, p):
    return float(f1_score(y, p, average="macro", zero_division=0))


def main():
    t0 = time.time()
    engines = available_engines()
    print("engines:", engines)
    data, calib, feat = {}, {}, {}
    for e in engines:
        cfg = load_engine_config(e)
        d = build(e, cfg.cylinder_count, cfg.is_turbocharged)
        c = Calib([r for r in d["train"] if r[2] == 0], cfg.cylinder_count)
        data[e], calib[e] = d, c
        Xtr, ytr = stack(d["train"], c.features)
        Xte, yte = stack(d["test"], c.features)
        Rtr, _ = stack(d["train"], lambda x, y, n=cfg.cylinder_count: Calib.raw_features(y, n))
        Rte, _ = stack(d["test"], lambda x, y, n=cfg.cylinder_count: Calib.raw_features(y, n))
        feat[e] = dict(Xtr=Xtr, ytr=ytr, Xte=Xte, yte=yte, Rtr=Rtr, Rte=Rte,
                       turbo=cfg.is_turbocharged, ci=cfg.is_compression_ignition)
        print(f"  {e:16s} train frames {len(ytr):5d}  test frames {len(yte):5d}  ({time.time()-t0:.0f}s)")

    R = {"engines": engines, "classes": ["nominal"] + FAULTS,
         "invisible_on_thermal_channels": INVISIBLE_THERMALLY}

    # ---- A. supervised classification (macro-F1 over classes present for the engine)
    def ohe(e):
        return np.array([[1.0 if feat[e]["ci"] else 0.0, 1.0 if feat[e]["turbo"] else 0.0]])

    A = {"per_engine_rf": {}, "universal_rf": {}, "universal_rf_with_class_flags": {},
         "universal_rf_loeo_calibrated": {}, "universal_rf_loeo_no_normalisation": {},
         "per_engine_rf_no_normalisation": {}}
    Xall = np.vstack([feat[e]["Xtr"] for e in engines]); yall = np.concatenate([feat[e]["ytr"] for e in engines])
    Xall_f = np.vstack([np.hstack([feat[e]["Xtr"], np.repeat(ohe(e), len(feat[e]["ytr"]), 0)]) for e in engines])
    uni = rf().fit(Xall, yall)
    uni_f = rf().fit(Xall_f, yall)
    for e in engines:
        f = feat[e]
        A["per_engine_rf"][e] = macro_f1(f["yte"], rf().fit(f["Xtr"], f["ytr"]).predict(f["Xte"]))
        A["per_engine_rf_no_normalisation"][e] = macro_f1(f["yte"], rf().fit(f["Rtr"], f["ytr"]).predict(f["Rte"]))
        A["universal_rf"][e] = macro_f1(f["yte"], uni.predict(f["Xte"]))
        A["universal_rf_with_class_flags"][e] = macro_f1(
            f["yte"], uni_f.predict(np.hstack([f["Xte"], np.repeat(ohe(e), len(f["yte"]), 0)])))
        others = [o for o in engines if o != e]
        Xo = np.vstack([feat[o]["Xtr"] for o in others]); yo = np.concatenate([feat[o]["ytr"] for o in others])
        A["universal_rf_loeo_calibrated"][e] = macro_f1(f["yte"], rf().fit(Xo, yo).predict(f["Xte"]))
        Ro = np.vstack([feat[o]["Rtr"] for o in others])
        A["universal_rf_loeo_no_normalisation"][e] = macro_f1(f["yte"], rf().fit(Ro, yo).predict(f["Rte"]))
    R["A_classification_macroF1"] = {k: {**v, "MEAN": float(np.mean(list(v.values())))} for k, v in A.items()}

    # ---- B. novelty / anomaly detection (train on nominal only)
    B = {}
    for name, mk in DETECTORS.items():
        per, uni_s, loeo = {}, {}, {}
        Zall = np.vstack([feat[e]["Xtr"][feat[e]["ytr"] == 0] for e in engines])
        d_all = mk(Zall.shape[1]).fit(Zall)
        for e in engines:
            f = feat[e]
            per[e] = novelty_metrics(mk(f["Xtr"].shape[1]).fit(f["Xtr"][f["ytr"] == 0]).score(f["Xte"]), f["yte"])
            uni_s[e] = novelty_metrics(d_all.score(f["Xte"]), f["yte"])
            Zo = np.vstack([feat[o]["Xtr"][feat[o]["ytr"] == 0] for o in engines if o != e])
            loeo[e] = novelty_metrics(mk(Zo.shape[1]).fit(Zo).score(f["Xte"]), f["yte"])
        summ = lambda d: {"AUROC": float(np.mean([v[0] for v in d.values()])),
                          "TPR@1%FPR": float(np.mean([v[1] for v in d.values()])),
                          "per_engine_AUROC": {k: round(v[0], 3) for k, v in d.items()}}
        B[name] = {"per_engine_detector": summ(per), "universal_detector": summ(uni_s),
                   "universal_leave_one_engine_out": summ(loeo)}
    R["B_novelty"] = B

    # ---- C. latency (this machine; single row unless noted)
    e0 = engines[2]
    f0 = feat[e0]
    row = f0["Xte"][:1]
    m = RandomForestClassifier(n_estimators=100, random_state=0, n_jobs=1).fit(f0["Xtr"], f0["ytr"])
    def tm(fn, n=200):
        fn(); t = time.perf_counter()
        for _ in range(n): fn()
        return (time.perf_counter() - t) / n * 1e6
    Z0 = f0["Xtr"][f0["ytr"] == 0]
    fbf, mh, iso = FBF(Z0.shape[1]).fit(Z0), Maha().fit(Z0), IF().fit(Z0)
    R["C_latency_us_per_sample_this_machine"] = {
        "RandomForest100 sklearn single row": tm(lambda: m.predict_proba(row)),
        "RandomForest100 sklearn, batch of 20 (per sample)": tm(lambda: m.predict_proba(f0["Xte"][:20])) / 20,
        "FlyHash-FBF score": tm(lambda: fbf.score(row)),
        "Mahalanobis": tm(lambda: mh.score(row)),
        "IsolationForest single row": tm(lambda: iso.score(row), n=50),
        "feature+residual computation (calib.features)": tm(lambda: calib[e0].features(
            data[e0]["test"][0][0][:1], data[e0]["test"][0][1][:1])),
    }
    R["meta"] = {"runtime_sec": round(time.time() - t0, 1), "dt_sec": DT, "frames_per_run": N_FRAMES,
                 "runs": N_RUN, "features": "13 n_cyl-agnostic z-residual features per frame"}
    out = REPO / "docs" / "evaluation" / "E17_detector_bakeoff.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(R, indent=2), encoding="utf-8")
    print(json.dumps({k: R[k] for k in ("A_classification_macroF1",)}, indent=1)[:3000])
    for name, v in B.items():
        print(f"{name:18s} per-engine AUROC {v['per_engine_detector']['AUROC']:.3f} TPR@1% {v['per_engine_detector']['TPR@1%FPR']:.3f} | "
              f"universal {v['universal_detector']['AUROC']:.3f}/{v['universal_detector']['TPR@1%FPR']:.3f} | "
              f"LOEO {v['universal_leave_one_engine_out']['AUROC']:.3f}/{v['universal_leave_one_engine_out']['TPR@1%FPR']:.3f}")
    print(json.dumps(R["C_latency_us_per_sample_this_machine"], indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
