"""Evaluation harness (card M3-08, P Part 7 T-DET): engine x fault x severity x seed on test tails, nominal flight
hours, the threshold-only baseline and an independent plant variant. Evidence class: SIMULATION.

- Nominal: random legs over the envelope (lever, altitude, OAT from the seed) -> confirmed false-alarm episodes per
  flight hour for the residual detector, and non-GO episodes for the THRESHOLD-ONLY baseline (the M2 status
  evaluator: engine-manual limits, no model).
- Faults: each applicable physical fault at each severity, injected after the tail settles at a cruise point,
  run for the registry's ramp + detect window + MARGIN_S. Recorded: first confirmed detection (ours), first
  CAUTION/NO-GO (baseline), per-frame score after the ramp (ROC positives, negatives = nominal frames of the same
  tail), and the isolator's top-1 / top-3 / ambiguity-group hit.
- Independent plant: a plant variant whose sensors are VARIANT_NOISE x noisier than the datasheet values the
  method was developed on, calibrated on itself like any new tail - nominal false alarms are re-measured.
Run: python -m backend.evaluation.run_matrix [engine_id ...]  -> reports/evaluation/detection_<date>.csv + summary.md
Reads plant truth only to label runs (failure, injected fault): this is an offline evaluator, not inference.
"""
from __future__ import annotations

import copy
import csv
import datetime as _dt
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Sequence

import numpy as np
from sklearn.metrics import roc_auc_score

from backend.diagnose.isolator import BayesianIsolator
from backend.evaluation.tail import calibrated
from backend.faults.registry import load_fault_registry
from backend.physics.engine_config import available_engines, load_engine_config
from backend.status.evaluator import StatusEvaluator

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "evaluation"
TEST_SEEDS = (1001, 1002)
SEVERITIES = (0.5, 1.0)
CRUISE = (70.0, 8000.0, 10.0)
SETTLE_S, MARGIN_S = 200, 120
NOMINAL_HOURS = 2.0
LEG_S = 600
ENVELOPE = {"throttle": (45.0, 95.0), "altitude_ft": (1000.0, 18000.0), "isa_dev_c": (-15.0, 15.0)}
VARIANT_NOISE = 1.5
ALARM_LEVELS = ("CAUTION", "NO-GO")
ISA_LAPSE_C_PER_FT = 0.0019812           # 1.98 C per 1000 ft (ISA troposphere)
ISA_SL_C = 15.0


def _score(r) -> float:
    return max(r.ratios.values())


def _legs(seed: int, hours: float):
    rng = np.random.default_rng(seed + 777)
    for _ in range(int(hours * 3600 // LEG_S)):
        alt = rng.uniform(*ENVELOPE["altitude_ft"])
        yield (rng.uniform(*ENVELOPE["throttle"]), alt, ISA_SL_C - ISA_LAPSE_C_PER_FT * alt + rng.uniform(*ENVELOPE["isa_dev_c"]))


def nominal(engine: str, seed: int, hours: float = NOMINAL_HOURS, variant: bool = False) -> Dict:
    src, det = calibrated(engine, seed, VARIANT_NOISE if variant else 1.0)
    ev = StatusEvaluator(src.cfg)
    ep = base_ep = 0
    prev = base_prev = False
    scores: List[float] = []
    for thr, alt, oat in _legs(seed, hours):
        for _ in range(LEG_S):
            f, _ = src.step(1.0, throttle_pct=thr, altitude_ft=alt, oat_c=oat)
            r = det.score(f)
            scores.append(_score(r))
            ep += r.confirmed and not prev
            prev = r.confirmed
            lvl = ev.evaluate(f.t, f, engine_state=f.engine_state).level in ALARM_LEVELS
            base_ep += lvl and not base_prev
            base_prev = lvl
    return {"engine_id": engine, "seed": seed, "variant": variant, "hours": hours, "fa_episodes": ep,
            "fa_per_fh": ep / hours, "baseline_episodes": base_ep, "baseline_per_fh": base_ep / hours,
            "scores": np.array(scores)}


def fault_case(snapshot, engine: str, spec, severity: float, neg_scores: np.ndarray) -> Dict:
    src, det = copy.deepcopy(snapshot)
    iso = BayesianIsolator(engine, det.cal.channel_names())
    ev = StatusEvaluator(src.cfg)
    cyl = (3 if src.cfg.cylinder_count >= 3 else 1) if spec.raw["scope"] == "CYLINDER" else None
    for _ in range(SETTLE_S):
        f, _ = src.step(1.0, *CRUISE)
        iso.update(det.score(f).z_raw)
        ev.evaluate(f.t, f, engine_state=f.engine_state)
    ramp, window = float(spec.raw["default_ramp_s"]), float(spec.raw["detect_window_s"])
    src.apply(SimpleNamespace(fault_id=spec.id, cylinder=cyl, channel=None, severity=severity, ramp_s=ramp,
                              t0_s=src.now()))
    n = int(ramp + window + MARGIN_S)
    t_ours = t_base = None
    pos: List[float] = []
    failed = False
    for i in range(n):
        f, truth = src.step(1.0, *CRUISE)
        r = det.score(f)
        iso.update(r.z_raw)
        if r.confirmed and t_ours is None:
            t_ours = i
        if t_base is None and ev.evaluate(f.t, f, engine_state=f.engine_state).level in ALARM_LEVELS:
            t_base = i
        if i >= ramp:
            pos.append(_score(r))
        failed = failed or truth.failed
    hyps = iso.posterior(det.cal.sensor_coupling(f))
    keys = [(h.fault_id, h.cylinder) for h in hyps]
    want = (spec.id, cyl)
    group = {h.group for h in hyps if (h.fault_id, h.cylinder) == want}
    y = np.r_[np.zeros(len(neg_scores)), np.ones(len(pos))]
    auc = float(roc_auc_score(y, np.r_[neg_scores, pos])) if pos else float("nan")
    return {"fault_id": spec.id, "fault": spec.name, "severity": severity, "cylinder": cyl,
            "detect_s": t_ours, "baseline_detect_s": t_base, "window_s": ramp + window, "auc": round(auc, 4),
            "top1": keys[:1] == [want], "top3": want in keys[:3], "group_hit": bool(hyps) and hyps[0].group in group,
            "leader": f"{hyps[0].fault_id or 'NOMINAL'}/{hyps[0].cylinder or hyps[0].channel or '-'}",
            "engine_failed": failed}


def run(engines: Sequence[str], seeds: Sequence[int] = TEST_SEEDS, severities: Sequence[float] = SEVERITIES) -> Dict:
    reg = load_fault_registry()
    rows, nominal_rows = [], []
    for e in engines:
        cfg = load_engine_config(e)
        specs = [s for s in reg.applicable(cfg) if s.kind != "SENSOR"]
        for seed in seeds:
            nom = nominal(e, seed)
            var = nominal(e, seed, variant=True)
            nominal_rows += [{k: v for k, v in d.items() if k != "scores"} for d in (nom, var)]
            print(e, seed, "nominal FA/FH", nom["fa_per_fh"], "baseline", nom["baseline_per_fh"],
                  "variant", var["fa_per_fh"], flush=True)
            snap = calibrated(e, seed)
            for spec in specs:
                for sev in severities:
                    res = fault_case(snap, e, spec, sev, nom["scores"])
                    rows.append({"engine_id": e, "seed": seed, **res})
                    print(e, seed, spec.id, sev, {k: res[k] for k in ("detect_s", "baseline_detect_s", "auc", "top3")},
                          flush=True)
    return {"faults": rows, "nominal": nominal_rows}


def summary(result: Dict) -> str:
    lines = ["# Detection and isolation evaluation (SIMULATION)", "",
             f"Test tails {list(TEST_SEEDS)} (signature tails 11, 12). Cruise {CRUISE}. Nominal: {NOMINAL_HOURS} h of "
             f"random legs per tail. Variant plant: sensor noise x{VARIANT_NOISE}.", "",
             "| Engine | FA/FH ours | FA/FH limits-only | FA/FH variant plant | faults detected | median detect s | "
             "limits-only detected | median AUC | top-1 | top-3 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for e in sorted({r["engine_id"] for r in result["faults"]}):
        nom = [r for r in result["nominal"] if r["engine_id"] == e and not r["variant"]]
        var = [r for r in result["nominal"] if r["engine_id"] == e and r["variant"]]
        fs = [r for r in result["faults"] if r["engine_id"] == e]
        det = [r["detect_s"] for r in fs if r["detect_s"] is not None]
        aucs = [r["auc"] for r in fs if r["auc"] == r["auc"]]
        lines.append(f"| {e} | {np.mean([r['fa_per_fh'] for r in nom]):.2f} | {np.mean([r['baseline_per_fh'] for r in nom]):.2f} "
                     f"| {np.mean([r['fa_per_fh'] for r in var]):.2f} | {len(det)}/{len(fs)} | "
                     f"{np.median(det) if det else float('nan'):.0f} | "
                     f"{sum(r['baseline_detect_s'] is not None for r in fs)}/{len(fs)} | {np.median(aucs):.3f} | "
                     f"{sum(r['top1'] for r in fs)}/{len(fs)} | {sum(r['top3'] for r in fs)}/{len(fs)} |")
    return "\n".join(lines) + "\n"


def main(engines: Optional[Sequence[str]] = None) -> None:
    result = run(engines or available_engines())
    OUT.mkdir(parents=True, exist_ok=True)
    day = _dt.date.today().isoformat()
    with (OUT / f"detection_{day}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["engine_id", "seed"] + [k for k in result["faults"][0] if k not in ("engine_id", "seed")])
        w.writeheader()
        w.writerows(result["faults"])
    with (OUT / f"nominal_{day}.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(result["nominal"][0]))
        w.writeheader()
        w.writerows(result["nominal"])
    text = summary(result)
    (OUT / f"summary_{day}.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
