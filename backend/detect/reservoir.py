"""
Sparse reservoir tier (backlog W11, decision D36) -- temporal detector on calibrated features.

E19 finding (SIMULATION): a fixed sparse recurrent reservoir + ridge readout beat windowed RF by ~4-5
macro-F1 points; the FLY connectome initialisation tied its degree-shuffled and random-ESN controls, so the
gain comes from the reservoir pattern, not the biology.  The connectome is offered as an initialiser
(``from_connectome``) and is not required: ``random`` gives an equivalent reservoir with no external file.

The reservoir is frozen; only the ridge readout is trained, so per-tail specialisation is a closed-form fit.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigs

DEFAULT_CONNECTOME = Path("mk-jev-fly-brain/mk/fly_circuit.js")


def _scale(A: sparse.csr_matrix, rho: float) -> sparse.csr_matrix:
    try:
        r = abs(eigs(A.astype(float), k=1, return_eigenvectors=False)[0])
    except Exception:  # ARPACK non-convergence on tiny/degenerate matrices
        r = float(np.sqrt(A.multiply(A).sum()))
    return A * (rho / max(r, 1e-9))


def connectome_matrix(path: str | Path, n: int = 1000) -> sparse.csr_matrix:
    """Top-``n``-degree subgraph of the maleCNS circuit; signed by neuron type (+1 exc / -1 inh)."""
    t = Path(path).read_text(encoding="utf-8")
    d = json.loads(t[t.index("{"): t.rindex("}") + 1])
    m = len(d["neurons"])
    sign = np.array([x[3] for x in d["neurons"]], float)
    pre, post, w = np.array(d["pre"]), np.array(d["post"]), np.array(d["w"], float)
    A = sparse.coo_matrix((w * sign[pre], (post, pre)), shape=(m, m)).tocsr()
    deg = np.asarray(abs(A).sum(0)).ravel() + np.asarray(abs(A).sum(1)).ravel()
    top = np.argsort(-deg)[:n]
    return A[top][:, top].tocsr()


def random_matrix(n: int = 1000, nnz_per_row: int = 12, seed: int = 0) -> sparse.csr_matrix:
    rng = np.random.default_rng(seed)
    rows = np.repeat(np.arange(n), nnz_per_row)
    cols = rng.integers(0, n, n * nnz_per_row)
    vals = rng.normal(0, 1, n * nnz_per_row)
    return sparse.coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsr()


class Reservoir:
    """Frozen leaky-integrator reservoir with a streaming ``step`` and a ridge-trained readout."""

    def __init__(self, W: sparse.csr_matrix, n_in: int, rho: float = 0.9, leak: float = 0.3,
                 input_density: float = 0.1, seed: int = 0) -> None:
        rng = np.random.default_rng(seed)
        self.W = _scale(W.tocsr(), rho)
        n = W.shape[0]
        self.Win = (rng.random((n, n_in)) < input_density) * rng.normal(0, 0.5, (n, n_in))
        self.leak = leak
        self.x = np.zeros(n)
        self.readout: Optional[np.ndarray] = None
        self.classes_: Optional[np.ndarray] = None

    @classmethod
    def from_connectome(cls, n_in: int, path: str | Path | None = None, n: int = 1000, **kw) -> "Reservoir":
        p = Path(path or os.environ.get("ANUMAAN_CONNECTOME", DEFAULT_CONNECTOME))
        return cls(connectome_matrix(p, n), n_in, **kw)

    @classmethod
    def random(cls, n_in: int, n: int = 1000, seed: int = 0, **kw) -> "Reservoir":
        return cls(random_matrix(n, seed=seed), n_in, seed=seed, **kw)

    def reset(self) -> None:
        self.x[:] = 0.0

    def step(self, u: np.ndarray) -> np.ndarray:
        self.x = (1 - self.leak) * self.x + self.leak * np.tanh(self.W @ self.x + self.Win @ np.clip(u, -10, 10))
        return self.x

    def states(self, U: np.ndarray) -> np.ndarray:
        self.reset()
        return np.vstack([self.step(u).copy() for u in U])

    def fit(self, sequences: Sequence[np.ndarray], labels: Sequence, ridge: float = 1.0) -> "Reservoir":
        """``sequences``: list of (T_i, n_in) calibrated feature runs; ``labels``: per run either one label
        or a length-T_i array; a label of -1 keeps the step for state build-up but excludes it from training."""
        S_all, y_all = [], []
        for U, lab in zip(sequences, labels):
            S = self.states(U)
            y = np.full(len(U), lab) if np.ndim(lab) == 0 else np.asarray(lab)
            keep = y != -1
            S_all.append(S[keep])
            y_all.append(y[keep])
        S, y = np.vstack(S_all), np.concatenate(y_all)
        self.classes_ = np.unique(y)
        T = (y[:, None] == self.classes_[None, :]).astype(float) * 2 - 1
        S1 = np.hstack([S, np.ones((len(S), 1))])
        self.readout = np.linalg.solve(S1.T @ S1 + ridge * np.eye(S1.shape[1]), S1.T @ T)
        self.reset()
        return self

    def predict_step(self, u: np.ndarray):
        """Streaming: returns (label, per-class scores) for one feature vector."""
        assert self.readout is not None, "fit() first"
        s = np.append(self.step(u), 1.0) @ self.readout
        return self.classes_[int(np.argmax(s))], s
