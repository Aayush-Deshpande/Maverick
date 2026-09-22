# Expanded Survey — corrections to the first audit

*Second sweep across GitHub and LinkedIn surfaced 6 repositories the first pass missed. Two of my headline claims were wrong. Both corrections weaken our position, and both are recorded here rather than quietly dropped.*

**Revised totals: 21 repositories identified · 15 analysed in technical depth.**

---

## 1. The six additional entries

| Repo | Identity | Key capability |
|---|---|---|
| [`Jyotirmoy-006/Dronanetra`](https://github.com/Jyotirmoy-006/Dronanetra) | Team AlgoX.6 | **3-axis FFT vibration spectrum analyser to 5 kHz**; PINN loss; LSTM+TCN RUL; XGBoost classifier; SHAP; 50 Hz WebSocket; biometric security |
| [`mohit200628-cpu/Aero-Digital-Twin`](https://github.com/mohit200628-cpu/Aero-Digital-Twin) | GARUDA-Twin | **Vibration FFT with harmonic orders (1X, 2X, Turbo)**; ISA + turbo physics; IsolationForest; 95% CI RUL |
| [`Adityaraj13b/AeroPulse`](https://github.com/Adityaraj13b/AeroPulse) | AeroPulse-X | ⚠️ **Trains and validates on REAL data (NASA ACES)** — 87.2% accuracy, 80.4% balanced accuracy on held-out flight groups. Explicitly declines to claim RUL accuracy |
| [`krishnatayal1410/twinguard-aero`](https://github.com/krishnatayal1410/twinguard-aero) | TwinGuard Aero | Four-twin architecture; **exceptionally honest** — "not a calibrated probability", "synthetic proof-of-concept only", 14 documented validation prerequisites |
| [`neeravjain91-jpg/AeroPulse`](https://github.com/neeravjain91-jpg/AeroPulse) | AeroPulse variant | Related to the above |
| [`harish029-svg/engine-twin`](https://github.com/harish029-svg/engine-twin) | engine-twin | Not deeply assessed |

---

## 2. ❌ Correction 1 — "0 of 11 do real vibration DSP" was wrong

**Two teams do FFT-based vibration analysis at kHz rates.**

- **Dronanetra** — a real-time 3-axis FFT vibration spectrum analyser to 5 kHz, with the fault classifier keying on "elevated 2X rotational harmonic vibration."
- **GARUDA-Twin** — vibration FFT with harmonic orders labelled 1X, 2X and Turbo.

🔶 **What survives of the thesis, stated precisely.** Neither team shows evidence of:

| Technique | Status across all 15 analysed |
|---|---|
| Vibration FFT at kHz | ⚠️ **2 teams have it** (was claimed 0) |
| **Tach-synchronous order tracking** (angular resampling for varying RPM) | **0** — "2X harmonic" at fixed frequency is not order tracking; on a UAV that constantly changes power, fixed-frequency bins smear |
| **Envelope / Hilbert demodulation** | **0** |
| **Crank-angle-resolved ω(θ)** | **0** |
| **Per-cylinder misfire from torque deficit** | **0** |
| **Cycle-to-cycle COV → combustion instability** | **0** |
| **Conformal prediction / reported coverage** | **0** (everyone ships heuristic "90%/95% CI") |
| **Link-loss / edge demonstration** | **0** |
| **Quantified threshold-baseline comparison** | **0** |

⬜ **Revised claim — narrower, and still defensible:** we would not be "the only team doing vibration analysis." We would be **the only team doing *crank-angle-resolved, per-cylinder combustion diagnostics*, and the only team whose vibration features are speed-invariant.** That is a smaller flag to plant than I first wrote, and it must be claimed in those exact words. Saying "only we do vibration FFT" is now **false** and would be caught.

---

## 3. ❌ Correction 2 — a real aero-piston UAV dataset exists, and we told ourselves it did not

⚠️ **This is the most consequential finding of the second sweep.**

[`Datasets/Piston_Engine/README.md`](../../Datasets/Piston_Engine/README.md) records: *"We searched for a public dataset containing aero piston engine sensor data… and did not find one."*

✅ **One exists.** **NASA ACES** (Altus Cumulus Electrification Study) contains real operational flight telemetry from the **Altus II UAV**, powered by a **four-cylinder Rotax 914 Turbo** — the exact engine class and platform class in our problem statement. ([NASA Open Data Portal](https://data.nasa.gov/dataset/aces-aircraft-and-mechanical-data-v1), [ACES Triggered Data](https://catalog.data.gov/dataset/aces-triggered-data-v1))

**What it contains:** aircraft state (pitch, roll, yaw) and mechanical data (engine speed, tail commands, fuel levels) recorded across real sorties.

**What it does *not* contain — the part of our negative result that stands:**
- ❌ No run-to-failure trajectories — all flights completed safely, so no RUL ground truth
- ❌ No labelled instances of the eight PS fault modes

🔶 So our claim was **half right, stated too broadly.** The correct statement is: *"No public dataset contains aero-piston engine telemetry with **labelled faults or run-to-failure trajectories**. Real un-faulted operational telemetry for this exact engine class **does** exist, in NASA ACES."*

### Why this matters competitively

**AeroPulse-X already trains and validates on it**, reporting 87.2% accuracy and 80.4% balanced accuracy on **held-out real flight groups**. ⚠️ In [`01_competitive_audit.md`](01_competitive_audit.md) §7 I listed external validation as an opening that was "near-unique" to us. **That was wrong — a competitor already occupies it, on more relevant data than the C-MAPSS turbofan route I proposed.**

⬜ **Action, and it is a clear upgrade to our plan:**
1. Amend the `Datasets/Piston_Engine` README — the negative result is partly falsified and leaving it uncorrected is exactly the overclaim our own evidence-label discipline exists to prevent.
2. **Validate our physics model against ACES.** Real Rotax 914 telemetry lets us check that our thermodynamic model reproduces real CHT/EGT/RPM relationships. That is far stronger than C-MAPSS, which is a turbofan.
3. **Use ACES as the healthy baseline** for anomaly detection — train the normal model on *real* engine behaviour, inject faults synthetically. This is a materially better data strategy than pure synthesis and directly attacks the "you learned your own simulator" objection.
4. ⚠️ Note honestly that ACES has zero engine failures, so every "critical" label on real data is a flight-envelope transient, not a fault.

---

## 4. Revised competitive position

🔶 The additional entries do not displace PRAHARI at the top, and do not move us out of roughly second — but the field is deeper than the first audit implied, and **two of the three openings I identified are narrower than claimed.**

| Opening | First audit | After second sweep |
|---|---|---|
| Vibration DSP | "0/11 — wide open" | ⚠️ **2 teams have FFT.** Crank-angle/order-tracking/envelope still open |
| External validation | "near-unique to us" | ❌ **AeroPulse already does it on real Rotax data** |
| Conformal / calibrated uncertainty | "0/11" | ✅ **Still 0/15 — genuinely open** |
| Threshold-baseline comparison | "0/11" | ✅ **Still 0/15 — genuinely open** |
| Link-loss / edge demo | "0/11" | ✅ **Still 0/15 — genuinely open** |
| Per-cylinder misfire from ω(θ) | "0/11" | ✅ **Still 0/15 — genuinely open** |

---

*Supersedes the counts in [`01_competitive_audit.md`](01_competitive_audit.md) §7 where they conflict. The feature plan in [`04_feature_spec.md`](04_feature_spec.md) survives intact — F02/F03/F04/F06/F12/F13/F15 all remain unoccupied — but F16 should retarget from C-MAPSS to NASA ACES.*
