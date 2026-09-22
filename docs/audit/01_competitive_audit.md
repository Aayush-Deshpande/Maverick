# Competitive Audit — PS-26054

*Every public implementation of this problem statement I could find, read, scored, and ranked. No hedging.*

**Analysed:** 15 repositories identified · **11 examined in technical depth** · 4 excluded (1 returned 404, 1 is a byte-identical fork, 2 had insufficient public content to score).

**Date of survey:** 22 September 2026. These are live repositories and will keep moving.

---

## 1. The headline answer

> ### We do not currently win.
> **1st — PRAHARI** (`atharv20s/sih-26`) — 85/100
> **2nd — ANUMAAN (us)** — 79/100
> **3rd — AERO-TWIN** (`Gagguverse`) — 77/100
>
> We are **second in a field of eleven**, six points behind the leader. Close enough that the gap is closable; not close enough to assume it closes by itself.

🔶 This is my honest assessment against a rubric I state openly in §3. It is a judgement, not a measurement, and the panel's weighting will differ from mine.

### ⚠️ Three corrections I had to make to my own first draft

I initially scored us **74 and third**, based on the documentation. Reading the actual code changed three findings, and I record them because they show the audit was evidence-driven rather than impressionistic — and because two of them were me being unfairly harsh:

1. ❌ **"Our spectral analyser commits an aliasing error."** **Wrong.** [`spectral_analyser.py`](../../backend/ml/spectral_analyser.py) explicitly computes `nyquist_hz`, tests `target_hz > nyquist_hz`, and falls back to an envelope/RMS path rather than producing a bogus DFT. It is Nyquist-aware and correct. The real finding is narrower — see [`02_self_audit.md`](02_self_audit.md) §2.
2. ❌ **"We do not do anti-leakage splitting."** **Wrong.** `model_metrics.json` records *"Strict Mission-Level Group Isolation (Train / Val / Test)"* across 30 missions, 10 per split.
3. ❌ **"Our evaluation rigour is our worst axis (5/15)."** **Wrong, and badly so.** We report held-out **test-mission** accuracy (0.9751) *separately from* validation (0.9931), per-fault precision/recall/F1 with support, macro-F1, and a full confusion matrix. Reporting the honest ~1.8-point val→test drop instead of quoting the better number is better practice than anything else I found in this field. Revised to **10/15**.

🔶 Net effect: **74 → 79, third → second.** Our measurement discipline is a genuine strength that our own documentation undersells.

---

## 2. The teams

| # | Repo | Identity | Depth analysed |
|---|---|---|---|
| 1 | [`atharv20s/sih-26`](https://github.com/atharv20s/sih-26) | **PRAHARI** — PINN + DRL + agentic | Full |
| 2 | [`Gagguverse/aero-twin-sih-2026`](https://github.com/Gagguverse/aero-twin-sih-2026) | **AERO-TWIN** — sensor-trust-first | Full |
| 3 | [`VIKASHL25/SIH-26`](https://github.com/VIKASHL25/SIH-26) | Microservices + Simulink + CAN-FD | Full |
| 4 | [`nainanishourya/aeris-uav-twin`](https://github.com/nainanishourya/aeris-uav-twin) | **AERIS** — physics-anchored | Full |
| 5 | [`24ug1byme021-commits/AeroTwin-X`](https://github.com/24ug1byme021-commits/AeroTwin-X) | Mission-dependent RUL | Full |
| 6 | [`Sahilpatil092006/AeroTwin-UAV`](https://github.com/Sahilpatil092006/AeroTwin-UAV) | Best ML methodology | Full |
| 7 | [`Mehak2513kaur/sih26054-digital-twin`](https://github.com/Mehak2513kaur/sih26054-digital-twin) | Canonical baseline | Full |
| 8 | [`manansumit-code/Aero-Digital-Twin`](https://github.com/manansumit-code/Aero-Digital-Twin) | ISA + IsolationForest | Full |
| 9 | [`Ash180905/AEROTWIN-AI`](https://github.com/Ash180905/AEROTWIN-AI) | GCS dashboard (frontend only public) | Partial |
| 10 | [`gammaoverload-gs/uav-aero-digital-twin`](https://github.com/gammaoverload-gs/uav-aero-digital-twin) | Streamlit prototype | Full |
| 11 | [`Monika-Srinithi/TwinProp-DX`](https://github.com/Monika-Srinithi/TwinProp-DX) | Scaffolding only | Full |
| — | `vinayraut71-source/sih26054-digital-twin` | Fork of #7 — excluded | — |
| — | `panditharshpandey1-gif/aerotwin-uav` | 404 — excluded | — |
| — | `ADARSH200703/SIH-2026`, `Manwithu/UAV-Twin-Engine-Monitor` | Insufficient content | — |

---

## 3. Rubric

⬜ My weighting, chosen to reflect what a DRDO technical panel plausibly rewards. Stated so it can be argued with.

| Axis | Weight | What earns points |
|---|---|---|
| PS requirement coverage | 15 | All six lettered sections A–F actually implemented |
| Physics model depth | 10 | Real thermodynamics, not a lookup curve |
| ML/AI sophistication | 15 | Beyond IsolationForest + RandomForest |
| Uncertainty & evaluation rigour | 15 | Calibrated intervals, leakage control, honest metrics |
| Sensor validation | 10 | Distinguishes bad sensor from bad engine |
| Mission reliability | 10 | The PS *title*. Mission-conditioned, not a label |
| Vibration / signal processing | 5 | Real DSP, not a scalar RMS |
| Visualisation / HMI | 10 | Operationally useful, not decorative |
| Engineering quality | 10 | Tests, reproducibility, documentation |

---

## 4. Scores

| Rank | Team | PS | Phys | ML | Rigour | Sensor | Mission | Vib | Viz | Eng | **Total** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **PRAHARI** | 12 | 9 | **15** | **13** | 9 | 6 | 3 | 9 | 9 | **85** |
| **2** | **ANUMAAN (us)** | 13 | 8 | 9 | 10 | 9 | 8 | 4 | **10** | 8 | **79** |
| **3** | **AERO-TWIN (Gagguverse)** | **15** | 7 | 8 | 8 | **10** | 9 | 2 | 9 | 9 | **77** |
| 4 | VIKASHL25 | 13 | 7 | 13 | 10 | 6 | 6 | 3 | 6 | **10** | **74** |
| 5 | AeroTwin-X | 13 | 7 | 7 | 7 | 8 | **9** | 2 | 8 | 8 | **69** |
| 6 | AERIS | 14 | 8 | 7 | 7 | 9 | 7 | 2 | 6 | 8 | **68** |
| 7 | Sahilpatil | 12 | 7 | 8 | **11** | 5 | 7 | 3 | 7 | 7 | **67** |
| 8 | Mehak2513kaur | 13 | 7 | 7 | 5 | 4 | 5 | 2 | 7 | 7 | **57** |
| 9 | manansumit | 11 | 7 | 5 | 4 | 3 | 6 | 2 | 7 | 5 | **50** |
| 10 | AEROTWIN-AI | 8 | 6 | 6 | 3 | 8 | 5 | 2 | 8 | 6 | **52*** |
| 11 | gammaoverload | 8 | 6 | 3 | 2 | 3 | 4 | 0 | 5 | 4 | **35** |
| 12 | TwinProp-DX | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 7 | **15** |

\* AEROTWIN-AI's backend is private; scored on the public frontend plus documented claims. Likely under-scored.

---

## 5. Why PRAHARI wins

🔶 It is the only entry doing research-grade work rather than integration work.

- **PINN with Fourier heat conduction in the loss function** — `ℒ_total = ℒ_data + λ_f·ℒ_fourier + λ_c·ℒ_consistency`, with λ ramped over the first 30% of training. This is a genuine physics-informed model, not "physics model beside an ML model."
- **Leakage control** — classifier trained *exclusively on the early 60% of engine lifecycles*. Almost nobody else in this field controls for late-stage leakage, and it is the single most common way to get a fraudulently high RUL score.
- **Ablation studies** — 8-channel PCA vs 12-channel raw vs PINN. They tested their architecture choice instead of asserting it.
- **Sensor Auditor with a reported 77.4% self-healing recovery** on telemetry dropout — a *number*, on a failure mode most teams ignore.
- **HMAC telemetry signing + JWT auth** — the secure-telemetry innovation area, actually built.
- **DRL/PPO strategist with a deterministic thermodynamic safety shield** clamping actions that breach CHT/vibration limits.

⚠️ **Their one real vulnerability:** the DRL strategist issues throttle/mixture commands. The PS asks for a *health monitoring and advisory* system for a GCS. An autonomous agent commanding a UAV powerplant raises an airworthiness and authority question a DRDO panel is well placed to ask — and "we put a safety shield on it" may not satisfy them. 🔶 If we are ever compared head-to-head, that is the honest technical objection, and it is a real one, not a cheap shot.

---

## 6. The brutal part: our two "differentiators" are already built

In [`rnd_solution_report.md`](../study/rnd_solution_report.md) I proposed sensor validation and mission-conditioned reliability as our differentiators. **I was wrong — both are already in the field, and in some cases done better than ours.**

| "Our" idea | Who already has it | How theirs compares |
|---|---|---|
| Sensor fault ≠ engine fault | **Gagguverse** (4-gate validation, quarantine, *residual shielding* so a bad sensor cannot penalise health), **AERIS** (cross-channel thermodynamic invariants), **AEROTWIN-AI** (the exact 145 °C thermocouple demo I proposed), **AeroTwin-X**, **PRAHARI** (imputation + recovery %) | Gagguverse's residual shielding is **better than ours** — we detect a bad sensor; they detect it *and* prevent it contaminating the health index |
| Mission-conditioned RUL | **AeroTwin-X** ("RUL is mission-dependent, not just time-based", leaky-integrator stress, Mission Twin projection), **Gagguverse** (Mission Reliability Score 0–100), **Sahilpatil** (composite reliability weighting) | AeroTwin-X's framing is essentially identical to what I proposed |
| Signed telemetry | **PRAHARI** (HMAC + JWT) | Already done |
| Ablation / baseline comparison | **PRAHARI** | Already done; we do **not** |
| Anti-leakage splitting | **PRAHARI**, **Sahilpatil**, **us** | We already do this — mission-level group isolation |

🔶 **Conclusion: there is no differentiation left in the "residual → classify → RUL → dashboard" paradigm.** Eleven teams have saturated it. Anything incremental inside that frame is a tie-breaker at best.

---

## 7. What *nobody* in the field has — the real openings

I checked every entry for these. Counts are out of the 11 examined.

| Opening | Teams that have it | Why it is open |
|---|---|---|
| **Real vibration DSP** — kHz sampling, order tracking, envelope analysis, sidebands | **0 / 11** | Everyone treats vibration as a single scalar RMS. The PS explicitly names "vibration signatures" and "abnormal vibration patterns" |
| **Crank-angle misfire detection** (instantaneous angular velocity per cylinder) | **0 / 11** | The canonical piston-engine diagnostic. ✅ Mature technique — [SAE 960039](https://saemobilus.sae.org/papers/overview-misfiring-cylinder-engine-diagnostic-techniques-based-crankshaft-angular-velocity-measurements-960039), [2024 study](https://journals.sagepub.com/doi/10.1177/14680874241261419), multiple patents |
| **Calibrated uncertainty** (conformal prediction, coverage reported) | **0 / 11** | Everyone ships heuristic bands: "90% CI", "P10–P90", "±confidence". None report *empirical coverage vs nominal* |
| **Quantified comparison vs the threshold baseline** | **0 / 11** | The PS's own framing invites it ("transitions from threshold-based") and nobody measures detection lead time against it |
| **Bandwidth-constrained edge/ground split, demonstrated** | **0 / 11** | Everyone runs one process on one machine. Nobody demos link loss |
| **Per-tail-number calibration** | **0 / 11** | Everyone has a generic engine model with a live overlay |
| **External validation** (methods on real public data) | ~1 / 11 (AERIS ingests C-MAPSS for *replay*, not validation) | Everyone reports accuracy on self-generated synthetic data |

🔶 **The 98–99% accuracy numbers across this field (AERIS 98%, Gagguverse 99.2%) are self-graded on self-generated data.** They are not evidence of anything, and a sharp panel member knows it. This is the field's shared, unacknowledged weakness — and the first team to address it honestly gains disproportionately.

---

## 8. Where we actually stand

**Genuinely ahead of the field:**
- **Visualisation** — Blender-authored engine assets, GLB pipeline, canyon flight simulation, mission graph viewer. Nobody is close. This is a real asset.
- **Documentation depth** — the 23-part study course has no equivalent in the field. ⚠️ But documentation does not win a demo; it wins the *questions after* the demo.
- **Dataset honesty** — [`Datasets/Piston_Engine/README.md`](../../Datasets/Piston_Engine/README.md) records a negative search result rather than overclaiming. Rare and creditable.
- **Vibration *theory*** — [Part VI](../study/06_vibration_analysis.md) is the only serious treatment of Nyquist/FFT/order analysis in the field. ⚠️ Our implementation does not honour it — see [`02_self_audit.md`](02_self_audit.md).

- **Measurement discipline** — held-out test missions, per-class metrics, confusion matrix, honest val→test gap. Best in field on this axis. ⚠️ Undersold everywhere in our own documentation.

**Genuinely behind:**
- **ML sophistication (9/15, our worst axis)** — RandomForest + autoencoder against PRAHARI's PINN-with-Fourier-loss and VIKASHL25's XGBoost ensemble with TreeSHAP. This is now our largest single gap.
- **No calibrated uncertainty** — we have no conformal intervals and report no coverage. (Nobody else does either, so this is an opening, not a deficit — see §7.)
- **No ablation, no baseline comparison** — PRAHARI tested its architecture choice; we asserted ours.
- **Scope discipline** — voice, RAG, knowledge graph and a 4B LLM are carried weight no competitor bothers with, and none of it appears in the PS.

---

## 9. Verdict

🔶 **On current trajectory we place second.** Second is a good team that loses.

The reason is not execution quality — our engineering is sound and our measurement discipline is the best in the field. It is that **we are competing inside a saturated paradigm.** Eleven teams built the same system; the winner is simply whoever built it with the most sophistication, and PRAHARI did. We cannot out-sophisticate a PINN-plus-DRL entry by adding another classifier.

⬜ **The only way to win is to change what is being compared.** §7 lists seven openings that the entire field has left untouched. The strongest of them — and the one our own documentation is already unusually well-prepared for — is **real vibration signal processing**, which nobody has and which the PS explicitly requires.

That argument is made in full in [`03_the_actual_solution.md`](03_the_actual_solution.md).

---

*Companion documents: [`02_self_audit.md`](02_self_audit.md) — unsparing audit of our own implementation · [`03_the_actual_solution.md`](03_the_actual_solution.md) — what to build instead.*
