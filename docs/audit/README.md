# Audit Set — PS-26054

*Competitive and self-audit conducted 22 September 2026. Written to be uncomfortable rather than reassuring.*

| # | Document | What it answers |
|---|---|---|
| 1 | [`01_competitive_audit.md`](01_competitive_audit.md) | Who else is building this, how good are they, **who wins**, and where do we actually rank |
| 2 | [`02_self_audit.md`](02_self_audit.md) | What our code actually does versus what our documentation claims |
| 3 | [`03_the_actual_solution.md`](03_the_actual_solution.md) | Given all of the above, what should we build instead |
| 4 | [`04_feature_spec.md`](04_feature_spec.md) | **The concrete build list** — 30 numbered features, tiered, with effort and build order |
| 5 | [`05_expanded_survey.md`](05_expanded_survey.md) | ⚠️ **Second sweep — 21 repos found, 15 analysed. Corrects two headline claims from doc 1** |
| 6 | [`06_repo_cleanup_plan.md`](06_repo_cleanup_plan.md) | Repository cleanup — inventory, verdicts, 6-phase gated procedure, rollback. **Plan only, not executed** |

---

## The three findings that matter

**1. We are second, not first.** 15 repositories found, **11 analysed in depth**. [PRAHARI](https://github.com/atharv20s/sih-26) leads at 85/100 with a physics-informed neural network, a PPO controller, ablation studies and signed telemetry. We score 79. Third place is one point behind us.

**2. The paradigm is saturated.** All 11 teams built the same system — physics residuals → IsolationForest/RandomForest → health index → RUL vs TBO → dashboard. Both differentiators proposed in [`rnd_solution_report.md`](../study/rnd_solution_report.md) (sensor validation, mission-conditioned RUL) turned out to be **already built by multiple competitors**, in places better than ours. There is no incremental win available inside this frame.

**3. The whole field discards its richest signal.** **0 of 11** teams do any real vibration signal processing — no order tracking, no envelope analysis, no kHz acquisition. Everyone reduces vibration to one scalar RMS number, despite five of the PS's eight fault targets living in the vibration spectrum. We already have the theory ([Part VI](../study/06_vibration_analysis.md)), the bandwidth argument ([Part V](../study/05_edge_ai.md)), and Nyquist-aware DFT code that is written and dormant. **That is the opening.**

---

## Corrections made during the audit

Three claims in my first draft were wrong and were corrected after reading the code. Recording them because the direction matters — two were me being unfairly harsh on our own work:

- ❌ "Our spectral analyser has an aliasing bug" → **it is Nyquist-aware and correct.**
- ❌ "We do not do anti-leakage splitting" → **we use strict mission-level group isolation.**
- ❌ "Evaluation rigour is our worst axis" → **it is the best in the field**; we publish held-out test-mission metrics, per-class P/R/F1, and a full confusion matrix while competitors quote bare accuracy headlines.

Net effect: 74 → 79, third → second.
