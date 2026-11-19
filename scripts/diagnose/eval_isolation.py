"""Isolation evaluation (cards M3-05 isolability report / M3-08). Writes reports/evaluation/isolation_<date>.csv and
prints the summary.

Test tail seeds EVAL_SEEDS (>= 1000) are disjoint from the signature seeds (11, 12) (D17). For each engine, each
applicable physical fault (and sensor offsets on a few channels) at each operating point: calibrate the tail,
settle, inject at EVAL_SEVERITY with a 60 s ramp, run RUN_S seconds feeding the detector and the isolator exactly
as the runtime does, then record the first confirmed detection time and the final ranking. Success measures:
top-1 / top-3 (fault id + cylinder or channel) and "group hit" (the leader is in the true fault's ambiguity group).
Evidence class: SIMULATION. Run: python scripts/diagnose/eval_isolation.py [engine_id ...]
"""
import copy
import csv
import datetime as _dt
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.diagnose.isolator import BayesianIsolator                   # noqa: E402
from backend.faults.registry import load_fault_registry                   # noqa: E402
from backend.physics.engine_config import available_engines, load_engine_config   # noqa: E402
from backend.evaluation.tail import calibrated                            # noqa: E402

EVAL_SEEDS = (1001,)
OPERATING_POINTS = ((65.0, 6000.0, 15.0), (85.0, 10000.0, 0.0))
EVAL_SEVERITY = 0.8
RAMP_S, SETTLE_S, RUN_S = 60.0, 200, 400
SENSOR_CHANNELS = ("cht[2]", "oil_t", "oil_p", "map_kpa")
OUT = ROOT / "reports" / "evaluation"


def case(snapshot, engine, fid, cyl, channel, op):
    src, det = copy.deepcopy(snapshot)
    iso = BayesianIsolator(engine, det.cal.channel_names())
    for _ in range(SETTLE_S):
        f, _ = src.step(1.0, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
        iso.update(det.score(f).z_raw)
    src.apply(SimpleNamespace(fault_id=fid, cylinder=cyl, channel=channel, severity=EVAL_SEVERITY, ramp_s=RAMP_S,
                              t0_s=src.now()))
    first, failed = None, False
    for i in range(RUN_S):
        f, truth = src.step(1.0, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
        r = det.score(f)
        iso.update(r.z_raw)
        if r.confirmed and first is None:
            first = i
        failed = failed or truth.failed
    hyps = iso.posterior(det.cal.sensor_coupling(f))
    want_ch = None if channel is None else channel.replace("[", "_").replace("]", "")
    key = lambda h: (h.fault_id, h.cylinder, h.channel)                      # noqa: E731
    want = (fid if channel is None else "S02", cyl, want_ch)
    keys = [key(h) for h in hyps]
    groups = {h.group for h in hyps if key(h) == want}
    return {"detected_s": first, "top1": keys[:1] == [want], "top3": want in keys[:3],
            "group_hit": bool(hyps) and hyps[0].group in groups, "leader": "%s/%s" % (hyps[0].fault_id or "NOMINAL",
                                                                                     hyps[0].cylinder or hyps[0].channel or "-"),
            "leader_posterior": round(hyps[0].posterior, 3), "engine_failed": failed}


def main(engines) -> None:
    reg = load_fault_registry()
    rows = []
    for e in engines:
        cfg = load_engine_config(e)
        specs = [s for s in reg.applicable(cfg) if s.kind != "SENSOR"]
        for seed in EVAL_SEEDS:
            snap = calibrated(e, seed)
            for op in OPERATING_POINTS:
                cases = [(s.id, (3 if cfg.cylinder_count >= 3 else 1) if s.raw["scope"] == "CYLINDER" else None, None) for s in specs]
                cases += [("S02", None, ch) for ch in SENSOR_CHANNELS]
                for fid, cyl, ch in cases:
                    res = case(snap, e, fid, cyl, ch, op)
                    rows.append({"engine_id": e, "seed": seed, "throttle": op[0], "altitude_ft": op[1], "fault_id": fid,
                                 "cylinder": cyl, "channel": ch, **res})
                    print(e, fid, cyl or ch or "", res, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"isolation_{_dt.date.today().isoformat()}.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for e in engines:
        rs = [r for r in rows if r["engine_id"] == e]
        n = len(rs)
        print(f"{e}: n={n} detected {sum(r['detected_s'] is not None for r in rs)}/{n}  top1 {sum(r['top1'] for r in rs)}/{n}"
              f"  top3 {sum(r['top3'] for r in rs)}/{n}  group {sum(r['group_hit'] for r in rs)}/{n}")
    print("->", out)


if __name__ == "__main__":
    main(sys.argv[1:] or available_engines())
