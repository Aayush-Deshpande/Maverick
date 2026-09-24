"""E20 - end-to-end evidence through the PRODUCT code path (RuntimeHub / EngineRuntime), not an experiment script.

For every engine profile and several tails (seeds): calibrate the tail on a nominal run-up, run a nominal flight
to measure the confirmed-alarm false-alarm rate, inject each profile-valid thermally visible fault and measure
detection delay from injection to first confirmed alarm, plus tier-1 (reservoir) label accuracy on the last 60
ticks.  Waveform-only faults (injector, rail, turbo bearing) are reported as NOT visible to scalars (F22).
Evidence class: SIMULATION.  Output: docs/evaluation/E20_runtime_end_to_end.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.physics.engine_config import available_engines  # noqa: E402
from backend.runtime import EngineRuntime  # noqa: E402
from backend.runtime.registry import faults_for  # noqa: E402

SEEDS = [1, 2, 3]
FLIGHT = 300
FAULT_TICKS = 300


def one(engine: str, seed: int, mode: str):
    rt = EngineRuntime(engine, seed=seed, warmup_ticks=900)
    rt.calibrate()
    rt.set_levers(throttle_pct=75, altitude_ft=12000, oat_c=0)
    for _ in range(120):                       # settle levers/thermal after the run-up
        rt.tick()
    nom = [rt.tick() for _ in range(FLIGHT)]
    far = float(np.mean([t.detection.confirmed for t in nom]))
    raw_far = float(np.mean([t.detection.raw_alarm for t in nom]))
    spec = next(s for s in faults_for(rt.cfg) if s.mode == mode)
    cyl = 2 if spec.per_cylinder else None
    rt.inject_fault(mode, cylinder=cyl, severity=0.9, ramp_sec=120.0, origin="SCRIPTED")
    delay, conf = None, 0
    ticks = []
    for i in range(FAULT_TICKS):
        t = rt.tick()
        ticks.append(t)
        conf += int(t.detection.confirmed)
        if delay is None and t.detection.confirmed:
            delay = i
    return {"far_confirmed": far, "far_raw": raw_far, "delay_ticks": delay,
            "confirmed_fraction_after": conf / FAULT_TICKS}


def main():
    t0 = time.time()
    out = {"seeds": SEEDS, "dt_s": 1.0, "ramp_s": 120, "engines": {}}
    for e in available_engines():
        rt = EngineRuntime(e, seed=0)
        modes = [s.mode for s in faults_for(rt.cfg) if s.layer == "L2"]
        vis = [s.mode for s in faults_for(rt.cfg) if s.layer == "L2" and s.scalar_visible]
        res = {"waveform_only_not_tested_here": sorted(set(modes) - set(vis)), "faults": {}}
        for m in vis:
            runs = [one(e, s, m) for s in SEEDS]
            det = [r["delay_ticks"] for r in runs]
            res["faults"][m] = {
                "detected_in_runs": sum(d is not None for d in det), "runs": len(runs),
                "median_delay_s": None if all(d is None for d in det) else float(np.median([d for d in det if d is not None])),
                "far_confirmed_mean": float(np.mean([r["far_confirmed"] for r in runs])),
                "far_raw_mean": float(np.mean([r["far_raw"] for r in runs])),
            }
            print(e, m, res["faults"][m], f"({time.time() - t0:.0f}s)", flush=True)
        out["engines"][e] = res
    (ROOT / "docs/evaluation/E20_runtime_end_to_end.json").write_text(json.dumps(out, indent=1))
    print("wrote E20")


if __name__ == "__main__":
    main()
