# Feature Specification — what to actually build

*Concrete build list derived from the audit. Every item states what it does, what it needs, what it outputs, and roughly what it costs. Ordered so that the differentiating capability lands first.*

---

## What the project becomes

> **ANUMAAN — the digital twin that measures combustion directly.**
>
> Eight slow scalars tell you an engine is unwell. The crankshaft tells you *which cylinder, on which cycle, and how often.* ANUMAAN reads the crank at kHz rates, resolves combustion per cylinder, compresses it to a few hundred bits per second because the datalink cannot carry more, and gives the operator a mission-conditioned go/no-go with a calibrated confidence interval.

Everything below serves that sentence. Anything that does not serve it is in §6.

---

## Tier 0 — Keep (already built, already good)

⬜ No work needed. Listed so nobody rebuilds them.

| Feature | Where | Note |
|---|---|---|
| Thermodynamic model + residuals | `backend/physics/thermo_model.py` | Deepen (§3.1), do not replace |
| Sensor validator | `backend/physics/sensor_validator.py` | Add shielding (F14) |
| 8-class fault classifier | `backend/ml/fault_classifier.py` | Mission-level group isolation already correct |
| Anomaly detector + autoencoder | `backend/ml/anomaly_detector.py` | |
| Component RUL + go/no-go + limiting subsystem | `backend/ml/rul_estimator.py` | Add conformal (F12) |
| Trend analyser | `backend/ml/trend_analyser.py` | |
| Telemetry gen + framing + transport | `backend/telemetry/` | Extend to kHz (F01) |
| FastAPI + WebSocket + React GCS | `backend/server/`, `frontend/` | |
| 3D twin, GLB pipeline, mission replay | `apps/`, `site/` | Make diagnostic (§4) |
| Evaluation harness + confusion matrix | `backend/ml/models/` | **Best in field — publicise it** |

---

## Tier 1 — The differentiator

🔶 **0 of 11 competitors have any of this.** Build in order; each depends on the previous.

### F01 · Crank-angle-resolved telemetry generator
**Does:** replaces "vibration RMS scalar @ 20 Hz" with a physically-derived signal chain.
**Chain:** per-cylinder pressure trace *p(θ)* → gas torque + inertial torque → **instantaneous crank angular velocity ω(θ)** → structural transfer → accelerometer *a(t)* @ 2–10 kHz.
**Inputs:** engine geometry (bore, stroke, rod, compression ratio, firing order 1-4-2-3 typical for a 4-cyl boxer), RPM, load, per-cylinder combustion state.
**Outputs:** `ω(θ)` array per revolution; `a(t)` @ kHz; tach pulse train.
**Rule:** faults modify *p(θ)* and physical parameters — never the output signal. A misfire is "no combustion in cylinder 3 this cycle," not "subtract 20 from vibration."
**Approach:** physics. Wiebe-function heat release is the standard closed-form for *p(θ)*.
**Validation:** a healthy 4-cylinder must produce dominant order-2 content (4 firings per 2 revolutions); if it does not, the model is wrong.
**Effort:** **High — this is the hardest item in the plan and everything else depends on it. Build it first.**

### F02 · Per-cylinder misfire detector
**Does:** names the misfiring cylinder from torque deficit — no classifier involved.
**Method:** segment `ω(θ)` TDC-to-TDC → one segment per firing event → compute each cylinder's angular-acceleration contribution → a misfire is a deficit in *its own* segment.
**Inputs:** `ω(θ)`, firing order, TDC reference. **Outputs:** per-cylinder misfire flag, misfire *rate* (% of cycles), onset time, trend.
**Approach:** deterministic physics. ✅ Mature technique — [SAE 960039](https://saemobilus.sae.org/papers/overview-misfiring-cylinder-engine-diagnostic-techniques-based-crankshaft-angular-velocity-measurements-960039).
**Output example:** *"Cylinder 3 misfiring at 4.2% of cycles, onset 11 min ago, trending +0.3%/min."*
**Effort:** Medium. **Highest payoff item in the project.** Directly solves PS fault #1 — our current worst class (recall 0.8359).

### F03 · Combustion instability detector
**Does:** PS fault #6, which nobody detects properly.
**Method:** cycle-to-cycle variance of per-cylinder IMEP/torque contribution (COV of IMEP is the standard metric). Rising COV = unstable combustion before any misfire occurs.
**Effort:** Low — reuses F02's segmentation.

### F04 · Tach-synchronous angular resampling (order tracking)
**Does:** makes every vibration feature **speed-invariant** — essential because a UAV changes power constantly.
**Method:** interpolate `a(t)` onto a uniform crank-angle grid using the tach signal → `a(θ)` → FFT gives an *order* spectrum.
**Why:** without it, spectral lines smear across a varying-RPM sortie and faults hide. Already specified at [`06_vibration_analysis.md:174–187`](../study/06_vibration_analysis.md).
**Effort:** Medium (~20–30 lines of interpolation plus care with the tach edge timing).

### F05 · Order-domain feature extractor
**Outputs:** band energies at orders 0.5 / 1 / 2 / 4, gear-mesh frequency and **sideband energy around GMF** (the classic gear-wear indicator), spectral kurtosis, crest factor.
**Effort:** Low once F04 exists.

### F06 · Envelope analysis
**Method:** band-pass around a structural resonance → Hilbert transform magnitude → FFT of the envelope → bearing defect tones (BPFO/BPFI, non-integer orders).
**Why:** ✅ our own Part VI says this "is worth more to our fault-detection performance than any model architecture choice" — it detects faults while RMS still looks normal.
**Effort:** Low (SciPy `hilbert` + existing FFT).

### F07 · Activate the dormant DFT path
**Does:** `spectral_analyser.py` already has correct Nyquist-aware DFT code that never executes at 20 Hz. Feed it the kHz channel and it works as designed.
**Effort:** **Trivial** — pass `sample_rate_hz=10000`. The capability is already written.

### F08 · Edge feature compressor + bandwidth accounting
**Does:** kHz vibration → ~200 bit/s feature vector; proves the edge split is necessary rather than decorative.
**Outputs:** compressed feature frame + a live **bandwidth meter** (raw kHz rate vs. link capacity vs. actual usage).
**Effort:** Low. Very high demo value.

---

## Tier 2 — Credibility (cheap, and nobody else has it)

### F12 · Conformal prediction on RUL ⭐
**Does:** replaces heuristic "±90% CI" with **distribution-free intervals carrying a coverage guarantee**.
**Method:** split-conformal — calibration set of held-out missions → nonconformity scores → interval at nominal 1−α.
**Critical output:** **empirical coverage vs nominal**, plotted. If we claim 90% we show 90% was achieved.
**Why:** **0/11 competitors have calibrated uncertainty.** Everyone ships heuristic bands. This is the cheapest genuine differentiator available.
**Effort:** **Low** (~100 lines). Highest credibility-per-hour in the entire plan.

### F13 · Threshold-baseline comparator ⭐
**Does:** runs the naive `if CHT > limit: alert()` comparator in parallel with our stack and logs both.
**Outputs:** **detection lead time** (us vs. baseline, in minutes), false alarms/hour for each, and the sensor-drift case where the baseline false-alarms and we do not.
**Why:** the PS explicitly frames the task as "transitions from conventional threshold-based monitoring." **0/11 measure this.** It converts our core claim from assertion to measurement.
**Effort:** **Low.** Do this early — it makes every later result quotable.

### F14 · Residual shielding for quarantined sensors
**Does:** when the validator marks a channel FAILED, zero its residual so it cannot contaminate the health index or trigger a false engine fault.
**Why:** Gagguverse has this and we do not. We detect a bad sensor; we do not yet stop it polluting downstream.
**Effort:** Very low.

### F15 · Edge/ground process separation + link-loss demo
**Does:** edge runs as a genuinely separate process behind the `TelemetrySource` interface; link simulator injects latency/loss/blackout; edge keeps detecting and logging through a blackout; GCS backfills on reconnect.
**Why:** **0/11 demo link loss.** Our Parts V/XIII already argue for it — this makes it visible.
**Effort:** Medium. Optional Raspberry Pi variant behind the same interface (see [`rnd_solution_report.md`](../study/rnd_solution_report.md) §11) — must never be load-bearing for the demo.

### F16 · External validation on C-MAPSS
**Does:** runs our RUL method unchanged on real public data and reports the number honestly.
**Why:** every team including us reports metrics on self-generated data. This is the one sentence that survives hostile questioning: *"the machine is simulated; the methods are validated on real data."*
**Effort:** Medium.

### F17 · UNKNOWN / novelty path
**Does:** lets the classifier say "anomalous, matches no known signature" instead of confidently mislabelling a 9th fault.
**Effort:** Low.

### F18 · Ablation harness
**Does:** physics-only vs ML-only vs hybrid on identical scenarios, as a table.
**Why:** PRAHARI tested their architecture; we asserted ours.
**Effort:** Low–medium.

---

## Tier 3 — Visualisation (our strongest axis — make it diagnostic, not decorative)

🔶 **Test for every item: does it show something the charts cannot?** If not, cut it.

| # | Feature | Why it earns its place |
|---|---|---|
| **F19** | **Per-cylinder residual heat map on the 3D engine** | Colour by *residual*, not absolute temperature — a cylinder glows only when it deviates from physics expectation at this altitude and power |
| **F20** | **Firing-order animation with the misfiring cylinder visibly skipping** | The single most legible output in the whole system. Nobody else can render this because nobody else computes it |
| **F21** | **Live order-spectrum waterfall** | Shows the fault *appearing* in the spectrum while scalar RMS stays flat |
| **F22** | **Sensor-trust overlay** | Failed/suspect channels marked on the engine — makes F14 legible at a glance |
| **F23** | **Degradation ghost** | Translucent overlay of predicted state at mission end vs now — makes *rate* spatial |
| **F24** | **Bandwidth meter** | kHz raw vs link capacity vs actual usage; the edge split made visible |

---

## Tier 4 — Only with genuine slack

F25 differentiable physics (JAX) → per-tail calibration by gradient descent · F26 particle-filter RUL · F27 foundation-model baseline to beat · F28 signed telemetry (HMAC) · F29 federation-ready hooks across N simulated tails · F30 test-rig deployment mode (PS's second named deployment context).

---

## §6 — Cut or constrain

| Item | Action | Reason |
|---|---|---|
| `backend/voice` (472 lines) | ❌ **Cut** | Appears nowhere in the PS. Operationally dubious in a noisy GCS. Demos well, which is the weakest argument available |
| `backend/agent` (1,950 lines) | 🔶 **Constrain** to retrieval-with-citation | "Autonomous maintenance advisory" *is* a listed innovation area, but free-form generation about maintenance on a defence platform is a hallucination liability. The LLM retrieves and cites; templates driven by the deterministic diagnosis produce the advisory text |
| `backend/knowledge` (582 lines) | 🔶 Keep only what F-agent needs | |
| `scratch/`, `.backup_pre_*`, `Qwen3-4B/`, 33 MB site assets | ❌ **Clean before anyone browses the repo** | Low technical severity, bad impression |

🔶 Roughly **3,000 lines sit outside the PS** while `backend/physics` — the module the entire twin rests on — is the smallest core module at 577 lines. That allocation is the single clearest signal of where effort went wrong.

---

## Build order

```
1.  F13  threshold baseline          ← do FIRST; makes everything else quotable
2.  F12  conformal RUL               ← cheapest real differentiator
3.  F14  residual shielding          ← hours
4.  F01  crank-angle generator       ← THE hard one. Validate before building on it
5.  F02  misfire detector            ← the payoff
6.  F03  combustion instability
7.  F04  order tracking → F05 → F06 → F07
8.  F08  edge compressor + bandwidth meter
9.  F15  link-loss demo
10. F20, F21, F19  visualisation of the above
11. F16  C-MAPSS external validation
12. F17, F18
```

🔶 **Risk gate after F01.** If the crank-angle generator does not produce a physically plausible healthy-engine order spectrum, stop and keep the existing 20 Hz pipeline — it already scores 79/100 on its own. The differentiator is worth pursuing, not worth betting the project on.

---

## The demo this produces

| Beat | What they see |
|---|---|
| Kill cylinder 3 | System names **cylinder 3** from torque deficit, in seconds |
| Scalar-RMS side-by-side | Our detector fires; the scalar every competitor uses is **still flat** |
| Bandwidth meter | Raw kHz cannot fit the link; features can |
| Pull the cable | Edge keeps detecting; GCS backfills on reconnect |
| Sensor drift | We say SENSOR; the baseline aborts the sortie |
| Coverage plot | Empirical coverage tracks nominal 90% |
| Two mission profiles | Same engine, different go/no-go and limiting factor |
| Honesty slide | Confusion matrix, val→test drop, C-MAPSS result, plain statement of what synthetic data proves |

---

*Audit set: [`README.md`](README.md) · [`01_competitive_audit.md`](01_competitive_audit.md) · [`02_self_audit.md`](02_self_audit.md) · [`03_the_actual_solution.md`](03_the_actual_solution.md) · this document.*
