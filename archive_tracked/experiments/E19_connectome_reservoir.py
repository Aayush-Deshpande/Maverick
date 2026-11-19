"""E19 - fly connectome as a reservoir (temporal detector) vs its own controls.
Evidence class: SIMULATION (plant data).  Pre-registered rule: docs/build/FLY_100_WAYS.md.
Contenders (same z-features, same ridge readout unless noted):
  connectome | shuffled (edge-target rewired) | random ESN (same N/nnz) | windowed RF | static RF
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigs
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import RidgeClassifier
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import E17_detector_bakeoff_plant as E17  # noqa: E402
from backend.physics.engine_config import load_engine_config  # noqa: E402

N_RES = 1000
ENGINES = sys.argv[1:] or ["rotax_914", "vrde_jayem_2_2l"]
SEEDS = [0, 1, 2]


def load_conn():
    t = (ROOT / "mk-jev-fly-brain/mk/fly_circuit.js").read_text(encoding="utf-8")
    d = json.loads(t[t.index("{"): t.rindex("}") + 1])
    n = len(d["neurons"])
    sign = np.array([x[3] for x in d["neurons"]], float)
    pre, post, w = np.array(d["pre"]), np.array(d["post"]), np.array(d["w"], float)
    A = sparse.coo_matrix((w * sign[pre], (post, pre)), shape=(n, n)).tocsr()
    deg = np.asarray(abs(A).sum(0)).ravel() + np.asarray(abs(A).sum(1)).ravel()
    top = np.argsort(-deg)[:N_RES]
    return A[top][:, top].tocsr()


def scale(A, rho=0.9):
    try:
        r = abs(eigs(A.astype(float), k=1, return_eigenvectors=False)[0])
    except Exception:
        r = np.sqrt(A.multiply(A).sum())
    return A * (rho / max(r, 1e-9))


def shuffled(A, rng):
    C = A.tocoo()
    post = C.row.copy()
    rng.shuffle(post)
    return sparse.coo_matrix((C.data, (post, C.col)), shape=A.shape).tocsr()


def random_esn(A, rng):
    C = A.tocoo()
    n = A.shape[0]
    return sparse.coo_matrix((rng.permutation(C.data), (rng.integers(0, n, C.nnz), rng.integers(0, n, C.nnz))),
                             shape=A.shape).tocsr()


def run_res(W, Win, Z, leak=0.3):
    x = np.zeros(W.shape[0])
    S = np.empty((len(Z), W.shape[0]))
    for i, z in enumerate(Z):
        x = (1 - leak) * x + leak * np.tanh(W @ x + Win @ z)
        S[i] = x
    return S


def feats(runs, calib):
    return [(np.clip(calib.features(x, y), -10, 10), l) for x, y, l in runs]


def mf1(y, p):
    return float(f1_score(y, p, average="macro"))


def windowed(Z):
    m = np.array([Z[max(0, i - 4): i + 1].mean(0) for i in range(len(Z))])
    return np.hstack([Z, m])


def main():
    t0 = time.time()
    base = load_conn()
    Wc = scale(base)
    out = {"n_res": N_RES, "engines": {}}
    for e in ENGINES:
        cfg = load_engine_config(e)
        d = E17.build(e, cfg.cylinder_count, cfg.is_turbocharged)
        cal = E17.Calib([r for r in d["train"] if r[2] == 0], cfg.cylinder_count)
        tr, te = feats(d["train"], cal), feats(d["test"], cal)
        ytr = np.concatenate([[l] * len(z) for z, l in tr])
        yte = np.concatenate([[l] * len(z) for z, l in te])
        Xs, Xt = np.vstack([z for z, _ in tr]), np.vstack([z for z, _ in te])
        Wtr = np.vstack([windowed(z) for z, _ in tr])
        Wte = np.vstack([windowed(z) for z, _ in te])
        res = {}
        res["static_rf"] = mf1(yte, RandomForestClassifier(200, n_jobs=-1, random_state=0).fit(Xs, ytr).predict(Xt))
        res["windowed_rf"] = mf1(yte, RandomForestClassifier(200, n_jobs=-1, random_state=0).fit(Wtr, ytr).predict(Wte))
        for name in ("connectome", "shuffled", "random_esn"):
            sc = []
            for s in SEEDS:
                rng = np.random.default_rng(s)
                if name == "connectome":
                    W = Wc
                else:
                    W = scale(shuffled(base, rng) if name == "shuffled" else random_esn(base, rng))
                Win = (rng.random((N_RES, Xs.shape[1])) < 0.1) * rng.normal(0, 0.5, (N_RES, Xs.shape[1]))
                Str = np.vstack([run_res(W, Win, z) for z, _ in tr])
                Ste = np.vstack([run_res(W, Win, z) for z, _ in te])
                sc.append(mf1(yte, RidgeClassifier(alpha=1.0).fit(Str, ytr).predict(Ste)))
            res[name] = {"mean": float(np.mean(sc)), "std": float(np.std(sc)), "seeds": sc}
        out["engines"][e] = res
        print(e, json.dumps(res, indent=1), f"({time.time() - t0:.0f}s)", flush=True)
    p = ROOT / "docs/evaluation/E19_connectome_reservoir.json"
    p.write_text(json.dumps(out, indent=1))
    print("wrote", p)


if __name__ == "__main__":
    main()
