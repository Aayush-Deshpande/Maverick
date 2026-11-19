"""Fault signatures for the Bayesian isolator (card M3-05). Writes configs/diagnose/signatures/<engine_id>.json.

For each engine and each applicable PHYSICAL registry fault: calibrate the residual detector on a nominal run of a
training tail (seeds SIGNATURE_SEEDS, disjoint from the evaluation seeds >= 1000, D17), inject the fault at
SIGNATURE_SEVERITY at each cruise operating point, average the unclipped z-vector over the last quarter of ramp +
detect window, and store it per unit severity. A moderate severity keeps the developing fault, not the end state: a
run whose engine fails (offline tool, so it may read the plant's truth record) stops averaging at the failure.
Cylinder-scope faults are injected at LOCATION_CYLINDER; the isolator permutes the cylinder channels for the other
locations. Sensor faults (S01-S07) need no signature: their hypotheses move one channel (backend/diagnose/isolator.py).
Run: python scripts/diagnose/gen_signatures.py [engine_id ...]   (~1-2 min per engine)
"""
import copy
import datetime as _dt
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.faults.registry import load_fault_registry                   # noqa: E402
from backend.physics.engine_config import available_engines, load_engine_config   # noqa: E402
from backend.evaluation.tail import calibrated                            # noqa: E402

SIGNATURE_SEEDS = (11, 12)
SIGNATURE_SEVERITY = 0.5
OPERATING_POINTS = ((60.0, 9000.0, 10.0), (75.0, 5000.0, 20.0), (90.0, 12000.0, 0.0))
LOCATION_CYLINDER = 2
OUT = ROOT / "configs" / "diagnose" / "signatures"


def settled(engine_id: str, seed: int, op):
    """Calibrated tail settled at the operating point (frames scored in order so the reference is in step)."""
    src, det = calibrated(engine_id, seed)
    for _ in range(300):
        f, _ = src.step(1.0, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
        det.cal.z(f)
    return src, det


def signature(snapshot, spec, op) -> np.ndarray:
    src, det = copy.deepcopy(snapshot)
    cyl = LOCATION_CYLINDER if spec.raw["scope"] == "CYLINDER" else None
    ramp, window = float(spec.raw["default_ramp_s"]), float(spec.raw["detect_window_s"])
    src.apply(SimpleNamespace(fault_id=spec.id, cylinder=cyl, channel=None, severity=SIGNATURE_SEVERITY, ramp_s=ramp,
                              t0_s=src.now()))
    n = int(ramp + window)
    zs, last = [], None
    for i in range(n):
        f, truth = src.step(1.0, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
        if truth.failed:
            break
        last = det.cal.z(f, clip=False)
        if i >= n - max(n // 4, 1):
            zs.append(last)
    if not zs:                                             # failed before the averaging window: last healthy-running z
        zs = [last if last is not None else np.zeros(len(det.cal.channel_names()))]
    return np.mean(zs, axis=0) / SIGNATURE_SEVERITY


def main(engines) -> None:
    reg = load_fault_registry()
    OUT.mkdir(parents=True, exist_ok=True)
    for e in engines:
        cfg = load_engine_config(e)
        specs = [s for s in reg.applicable(cfg) if s.kind != "SENSOR"]
        vecs = {s.id: [] for s in specs}
        names = None
        for seed in SIGNATURE_SEEDS:
            for op in OPERATING_POINTS:
                snap = settled(e, seed, op)
                names = snap[1].cal.channel_names()
                for spec in specs:
                    vecs[spec.id].append(signature(snap, spec, op))
        faults = {}
        for spec in specs:
            m = np.mean(vecs[spec.id], axis=0)
            faults[spec.id] = {"scope": spec.raw["scope"], "z": [round(float(x), 3) for x in m],
                               "spread": round(float(np.mean(np.std(vecs[spec.id], axis=0))), 3)}
            print(e, spec.id, "norm", round(float(np.linalg.norm(m)), 2), flush=True)
        doc = {"schema": "fault_signatures/1", "engine_id": e, "status": "CALIBRATED",
               "ref": "scripts/diagnose/gen_signatures.py on the backend/sim plant (SIMULATION evidence class)",
               "date": _dt.date.today().isoformat(), "channels": names, "location_cylinder": LOCATION_CYLINDER,
               "operating_points": [list(o) for o in OPERATING_POINTS], "seeds": list(SIGNATURE_SEEDS),
               "severity": SIGNATURE_SEVERITY, "per_unit_severity": True, "faults": faults}
        (OUT / f"{e}.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:] or available_engines())
