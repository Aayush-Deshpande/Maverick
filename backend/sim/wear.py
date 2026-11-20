"""Slow wear processes (card M4-01, P Part 4 Step 4.1). Plant side: this is part of the simulated engine, not of the
twin - inference never imports it (tests/test_no_truth_leak.py).

Each process grows the severity of one registry fault (configs/faults.json parameter effects, so the physics change
is the registry's) over operating hours:
    d severity / dt = rate_per_h * tail_multiplier * stress
  stress "hours"          1 while the engine runs
  stress "load_oil_temp"  load fraction x exp((oil_t - ref) / scale)   (hot, loaded oil wears bearings faster)
  stress "low_load"       1 below low_load_fraction of rated power, else 0 (diesel injector coking at idle/loiter)
The per-tail multiplier is lognormal (configs/wear.json tail_rate_sigma), drawn from the tail seed, so a fleet of
seeds is a fleet of differently ageing engines. Only processes whose fault applies to the engine are created.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

from backend.sim.source import registry

ROOT = Path(__file__).resolve().parents[2]
S_PER_H = 3600.0
MAX_SEVERITY = 1.0


def load_wear_config() -> Dict[str, Any]:
    return json.loads((ROOT / "configs" / "wear.json").read_text(encoding="utf-8"))


class WearModel:
    def __init__(self, source: Any, seed: int, cfg: Dict[str, Any] | None = None) -> None:
        c = cfg or load_wear_config()
        self.source = source
        rng = random.Random(seed * 104729 + 17)
        sigma = float(c["tail_rate_sigma"]["value"])
        n_cyl = source.n_cylinders
        self.processes: List[Dict[str, Any]] = []
        for p in c["processes"]["value"]:
            ok, _why = registry().get(p["fault_id"]).applicability(source.cfg)
            if not ok:
                continue
            cyl = rng.randint(1, n_cyl) if p.get("cylinder") == "random" else None
            fault = SimpleNamespace(fault_id=p["fault_id"], cylinder=cyl, channel=None, severity=0.0, ramp_s=0.0,
                                    t0_s=source.now())
            source.apply(fault)
            self.processes.append({**p, "fault": fault, "multiplier": math.exp(rng.gauss(0.0, sigma))})

    def _stress(self, p: Dict[str, Any], load: float, oil_t: float) -> float:
        kind = p["stress"]
        if kind == "hours":
            return 1.0
        if kind == "load_oil_temp":
            return max(load, 0.0) * math.exp((oil_t - p["oil_t_ref_c"]) / p["oil_t_scale_c"])
        if kind == "low_load":
            return 1.0 if load < p["low_load_fraction"] else 0.0
        raise ValueError(f"unknown wear stress {kind!r}")

    def advance(self, dt_s: float) -> None:
        """Grow every process by dt_s of operation at the plant's current state (no wear while stopped)."""
        out = self.source.last
        if out is None or out.rpm <= 0:
            return
        load = out.power_kw / self.source.cfg.rated_power_kw
        for p in self.processes:
            f = p["fault"]
            f.severity = min(MAX_SEVERITY, f.severity + p["rate_per_h"] * p["multiplier"]
                             * self._stress(p, load, out.oil_c) * dt_s / S_PER_H)

    def state(self) -> Dict[str, float]:
        return {f"{p['fault_id']}{'' if p['fault'].cylinder is None else '/' + str(p['fault'].cylinder)}": p["fault"].severity
                for p in self.processes}
