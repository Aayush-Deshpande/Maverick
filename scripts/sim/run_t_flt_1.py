"""T-FLT-1 runner (card M1-13): every (engine, applicable physical fault) at severity 1, paired lockstep run, every
expected_signature channel checked. Writes docs/physics/t_flt_1_report.csv. ~30 min on one core.
Run: python scripts/sim/run_t_flt_1.py   (tests/sim/test_t_flt_1.py, marked slow, checks the pass set never shrinks)"""
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.faults.registry import load_fault_registry          # noqa: E402
from backend.physics.engine_config import available_engines, load_engine_config   # noqa: E402
from backend.sim.signature import run_pair                       # noqa: E402


def main() -> None:
    reg = load_fault_registry()
    rows, t0 = [], time.time()
    for e in available_engines():
        cfg = load_engine_config(e)
        for spec in reg.applicable(cfg):
            if spec.kind == "SENSOR":
                continue
            for r in run_pair(cfg, reg, spec.id):
                rows.append({"engine_id": e, "fault_id": spec.id, "fault": spec.name, "channel": r.channel,
                             "direction": r.direction, "min_delta": r.min_delta,
                             "delta": "" if r.delta is None else round(r.delta, 3), "ok": r.ok})
    out = ROOT / "docs" / "physics" / "t_flt_1_report.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    pairs = {}
    for r in rows:
        pairs.setdefault((r["engine_id"], r["fault_id"]), []).append(r["ok"])
    ok = sum(all(v) for v in pairs.values())
    print(f"{ok}/{len(pairs)} pairs pass every signature channel; {time.time() - t0:.0f} s -> {out}")


if __name__ == "__main__":
    main()
