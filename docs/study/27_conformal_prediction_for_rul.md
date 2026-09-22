# Part XXVII — Conformal Prediction for RUL

*How to produce an RUL interval that means something, and how to prove it does. Implements feature F12.*

---

## 27.1 The problem with every RUL interval in this field

[Part IX](09_rul_prognostics.md) states that "RUL without a visible degradation trend and an uncertainty bound is decoration." Correct — but *how* the bound is produced decides whether it is decoration too.

Across the 15 competing implementations audited ([`05_expanded_survey.md`](../audit/05_expanded_survey.md)), every one that reports uncertainty reports it heuristically:

| Team | Claimed interval | Basis |
|---|---|---|
| AERIS | "90% confidence bounds" | scaled by "operational stress acceleration" |
| Gagguverse | "~182 h [172–192 h], confidence ~92%" | sensor trust + trend stability |
| VIKASHL25 | "P10–P90" | sub-ensemble variance |
| Dronanetra / GARUDA | "95% CI" | undefined |
| **Us, currently** | margin only | no interval |

⚠️ **None of them verify that their 90% interval actually contains the truth 90% of the time.** An unvalidated "90% CI" is a decorative number with a percent sign. **0 of 15 report empirical coverage** — this remains genuinely open.

---

## 27.2 What conformal prediction gives

✅ Conformal prediction produces prediction *sets* rather than point estimates, and under mild assumptions **formally guarantees** the true value is covered with a prespecified probability ([Conformal Prediction Intervals for RUL, *IJPHM*](https://papers.phmsociety.org/index.php/ijphm/article/view/3417)).

Three properties that matter here:

1. **Distribution-free** — no Gaussian assumption on errors. RUL errors are famously skewed.
2. **Finite-sample** — the guarantee holds at our calibration-set size, not asymptotically.
3. **Model-agnostic** — wraps our *existing* `RULEstimator` unchanged. We do not replace what works; we jacket it.

✅ Established for this exact task: [uncertainty-aware bearing RUL via CP (2026)](https://papers.phmsociety.org/index.php/phme/article/view/4902), and [isotonic-calibrated split-CP validated on C-MAPSS (2026)](https://www.sciencedirect.com/science/article/pii/S0951832026005740).

---

## 27.3 Split conformal — the algorithm

⬜ Use **split (inductive) conformal**. It costs one extra data split and one quantile computation.

```
SPLIT the data by MISSION (never by time within a mission):
    train_missions        fit the RUL model
    calibration_missions  compute nonconformity scores   ← held out from fitting
    test_missions         report coverage

CALIBRATE
    for each sample j in calibration set:
        s_j = |RUL_true_j − RUL_pred_j|           # absolute-residual score
    q = Quantile( {s_j}, ceil((n+1)(1−α))/n )     # finite-sample correction

PREDICT for a new sample:
    interval = [ RUL_pred − q , RUL_pred + q ]

GUARANTEE
    P( RUL_true ∈ interval ) ≥ 1 − α
```

⚠️ **The `ceil((n+1)(1−α))/n` correction is not cosmetic.** Using the plain empirical quantile under-covers at small `n`. With n=500 calibration points and α=0.1 the difference is small but real; with n=50 it is large.

⚠️ **Calibration data must never have been used for fitting.** Reusing training data collapses the guarantee silently — coverage looks perfect in development and fails on test.

✅ Our existing mission-level group isolation (`model_metrics.json`: *"Strict Mission-Level Group Isolation"*, 10/10/10 missions) is already the correct structure. We split the 10 validation missions into calibration and a coverage-test set.

---

## 27.4 Adaptive intervals — because RUL error is not uniform

A single global `q` gives every prediction the same width. That is wrong: a nearly-new engine and one near end-of-life have very different predictability.

⬜ **Normalised (Mondrian) conformal** — scale the score by a difficulty estimate `σ(x)`:
```
    s_j = |RUL_true_j − RUL_pred_j| / σ(x_j)
    interval = [ pred − q·σ(x) , pred + q·σ(x) ]
```
⬜ Candidates for `σ(x)`: predicted RUL magnitude (error typically grows with horizon), degradation-rate variance, or ensemble spread if we have one.

🔶 Coverage is preserved; intervals become narrow when we are confident and wide when we are not — which is the behaviour an operator expects and the earlier flat interval cannot provide.

✅ [Bearing RUL work (2026)](https://papers.phmsociety.org/index.php/phme/article/view/4902) finds exactly this: irregular or non-stationary degradation needs wider calibrated intervals to hold coverage.

---

## 27.5 The asymmetry that matters operationally

⚠️ **Over-predicting RUL is far more dangerous than under-predicting.** Saying 50 h when the truth is 20 h risks losing the aircraft. Saying 20 h when the truth is 50 h costs an unnecessary inspection.

[Part XIX](19_evaluation.md) already adopts asymmetric RUL scoring. The interval should be asymmetric too:

⬜ **One-sided conformal lower bound** — the operationally meaningful quantity:
```
    s_j = RUL_true_j − RUL_pred_j        # SIGNED, not absolute
    q_lo = Quantile({s_j}, α)            # lower tail only
    RUL_lower = RUL_pred + q_lo

    Guarantee: P( RUL_true ≥ RUL_lower ) ≥ 1 − α
```

🔶 **This is the number that should drive go/no-go.** Not the point estimate, not the interval centre — the **lower bound**. Our `MissionGoNoGoAdvisory` should compare `planned_sortie_hours` against `RUL_lower`, not against `estimated_rul_hours`.

⬜ That is a small code change in `backend/ml/rul_estimator.py` with a large defensibility gain: *"we plan against the statistically guaranteed lower bound, not the expected value."*

---

## 27.6 Validation — the part that makes it a claim rather than a decoration

⬜ **Produce this plot. It is the single most credible artifact in the project.**

```
COVERAGE CURVE
  x: nominal coverage (1−α)   0.5 … 0.99
  y: empirical coverage on held-out test missions
  Perfect calibration = the diagonal.
```

| Diagnostic | Meaning | Action |
|---|---|---|
| Empirical ≈ nominal | Calibrated ✅ | Report it |
| Empirical < nominal | **Over-confident — dangerous** | Check calibration/test leakage |
| Empirical > nominal | Conservative — safe but wide | Try normalised CP (§27.4) |

**Also report:** mean interval width (a trivially wide interval achieves coverage and is useless — width is the honesty check), and coverage broken down by degradation stage.

🔶 **The sentence this earns:** *"We claim 90% coverage, and here is the measurement showing we achieved 89.4% on held-out missions."* **No competitor can currently say anything equivalent.**

---

## 27.7 Assumptions and honest limits

⚠️ State these; a sharp panel will ask.

**Exchangeability.** CP assumes calibration and test data are exchangeable. Degradation time-series are *not* i.i.d. — consecutive samples are correlated.
- ⬜ Mitigation: treat each **mission** as the exchangeable unit (mission-level splitting, which we already do). Within-mission correlation then sits inside the unit rather than across the split.
- 🔶 Residual risk: if test missions are drawn from a different regime than calibration missions, coverage degrades. Report coverage per regime.

**Synthetic-data ceiling.** ⚠️ Coverage is measured against our own generator's ground truth. It proves our intervals are calibrated *with respect to our simulator*, not with respect to a real Rotax. ⬜ Say this explicitly. Then strengthen it: run the same procedure on **C-MAPSS**, which has real run-to-failure labels, and report that coverage number too. Calibration holding on both is a far stronger claim than either alone.

**Distribution shift.** A genuinely novel fault violates exchangeability outright and the guarantee does not apply. ⬜ This is why the UNKNOWN/novelty path (F17) matters: CP tells you how wrong you usually are, not how wrong you are on something you have never seen.

---

## 27.8 Implementation

⬜ Roughly 100 lines. Wraps the existing estimator; changes nothing inside it.

```
backend/ml/conformal.py
    class ConformalRUL:
        fit_calibration(preds, truths, groups)   # mission-grouped
        predict_interval(pred, x, alpha)         # two-sided
        predict_lower_bound(pred, x, alpha)      # one-sided  ← drives go/no-go
        coverage_report(preds, truths, alphas)   # the §27.6 plot
```

**Integration:** `RULEstimator` gains `rul_lower_bound_hours`; `MissionGoNoGoAdvisory.margin_hours` is computed from the lower bound; the dashboard shows the band, not just the point.

**Order of work:** calibration split → absolute-residual CP → coverage plot → one-sided bound → wire into go/no-go → normalised CP if the plot shows width is poorly adapted.

🔶 **Effort is low and payoff is high.** It is the cheapest genuine differentiator in the [feature spec](../audit/04_feature_spec.md), it strengthens a component we already have rather than adding a new subsystem, and it produces a checkable number in a field where everyone else produces a decorative one.

---

*Related: [Part IX](09_rul_prognostics.md) (RUL fundamentals) · [Part XIX](19_evaluation.md) (asymmetric scoring) · [feature spec F12](../audit/04_feature_spec.md).*
