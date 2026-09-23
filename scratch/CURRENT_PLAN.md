# ANUMAAN — current plan and feature status

*Working scratch copy. Generated 2026-09-23. Authoritative sources:
[`docs/audit/07_unoccupied_axes_and_ground_up_plan.md`](../docs/audit/07_unoccupied_axes_and_ground_up_plan.md)
(the plan) and [`docs/IMPLEMENTATION_LOG.md`](../docs/IMPLEMENTATION_LOG.md)
(what was actually verified, including what failed).*

---

## Where we are

**65 features in scope · 36 implemented and verified (55 %)**
**Both structural blockers closed: G01 and G03.**

The two things that made every previous number meaningless are now fixed:

| Gap | Was | Now |
|---|---|---|
| **G01** | The "engine" and the twin were the same model, so residuals were noise + the injected fault and detection could not fail | Independent plant (`backend/plant/virtual_engine.py`) with its own physics, build variation and sensor model. Publishes sensor frames only; no ground truth leaks |
| **G03** | Lead time was asserted, never measured | Measured head-to-head against a conventional limit monitor — see below |

### The headline numbers, now measured

From `docs/evaluation/detection_report.md`, 8 scenarios against the independent plant:

| Metric | Result |
|---|---|
| Fault scenarios detected by the twin (either channel) | **6 / 6** |
| Detected by the conventional threshold baseline | **1 / 6** |
| Found by the twin but **invisible** to the baseline | **4** |
| Median detection lead time over the baseline | **7.92 min** |
| False alarms per flight hour (3 nominal hours) | twin **0.0**, baseline **0.0** |
| Cooling degradation | caught at 1304 s, **694 s before the engine destroyed itself** at 1998 s |
| Sensor drift | correctly classified `SENSOR_FAULT`, not an engine fault |

**The two detection channels are complementary, and the report says so.**
Thermal residuals miss the slow injector coking entirely; the crank detector
catches it at 750 s and names cylinder 2. The crank channel is silent on
cooling, oil and turbo faults, which are not combustion events.

### The differentiator, as a number

| Metric | Healthy | Misfire cyl 3 | Change |
|---|---|---|---|
| Order-0.5 fraction | 0.00013 | 0.01464 | **114×** |
| Broadband RMS — what every competitor uses | 0.0044 | 0.0042 | **0.97×, flat** |

Intermittent misfire **rate recovered exactly**: 6.0 % detected vs 6.0 % injected,
14.0 % vs 14.0 %, 40.7 % vs 40.7 %, correct cylinder every time.

### The edge argument, as arithmetic

| Quantity | Value |
|---|---|
| Raw crank channel @ 10 kHz / 16-bit | **160 kbit/s** |
| Datalink spare after video/command/housekeeping | **22 kbit/s** |
| Raw over budget by | **7.3×** — cannot be downlinked |
| Compressed feature frame | **29 bytes**, 0.232 kbit/s = **1.05 %** of spare |
| Compression ratio | **690×** |
| Edge analysis latency | median **3.7 ms**, p95 **6.5 ms** (50 ms deadline) |
| Power cost | 9.5 W → **0.62 min** endurance over an 18 h sortie |

---

## Done (36)

| Tier | Features |
|---|---|
| **Crank chain** | F01 crank dynamics · F02 per-cylinder misfire · F03 combustion instability · F04 order tracking · F05 order features · F06 envelope · F08 edge compressor |
| **Credibility** | F12 conformal RUL · F13 threshold baseline · F18 evaluation harness |
| **A — reframe** | F31 engine config (912iS/914/AE300) · F32 turbocharger · F33 FMECA · F34 OSA-CBM mapping · F35 isolability |
| **B — life** | F36 rainflow+Miner · F37 shock cooling · F39 oil/wear metals · F40 exposure accumulator |
| **C — HFE/env** | F41 CI injector faults · F42 fuel thermal/CFPP · F43 induction + dust chain |
| **D — interfaces** | F46 MAVLink EFI_STATUS · F48 NASA ACES loader |
| **E — trust** | F50 per-tail calibration · F51 twin validity · F52 drift/fault/sensor separation · F53 adaptive conformal |
| **F — security** | F54 physics-constrained FDI · F55 lane disagreement / stale frames |
| **G — mission** | F56 mission reliability · F57 prescriptive derate · F58 re-planning |
| **H — evaluation** | F60 PHM standard metrics |
| **J — edge** | F67 power budget · F68 latency budget |

---

## Remaining (29)

Ordered by what I intend to do next.

### Next up — evaluation honesty and cheap wins
| # | Feature | Why now |
|---|---|---|
| **F14** | Residual shielding for quarantined sensors | Very low effort; we detect a bad sensor but still let it pollute downstream |
| **F17** | UNKNOWN / novelty class | Lets the classifier say "anomalous, matches nothing known" instead of confidently mislabelling |
| **F16 / F63** | External validation + sim2real gap against NASA ACES | Real Rotax 914 telemetry is already in-repo and unused for validation |
| **F62** | Correct AD evaluation protocol (no point-adjust inflation) | Cheap, and protects every number above |
| **F61** | Zero-shot foundation-model baseline | The control that kills "you only beat your own simulator" |
| **F38** | Dual-path RUL + disagreement alarm | Damage-accumulation vs data-driven; disagreement is itself a signal |

### Then — completing tiers already started
| # | Feature |
|---|---|
| **F07** | Feed the kHz channel to the dormant DFT path in `spectral_analyser.py` |
| **F44 / F45** | Turbo fault suite and mass-flow-limited cooling as first-class twin models (currently only in the plant) |
| **F15** | Edge/ground process split + link-loss demo |
| **F47** | Real CAN via DBC (python-can, SocketCAN/vcan) |
| **F49** | Test-rig / HIL mode — the PS's second named deployment context |
| **F59** | Fleet tail-to-mission assignment |

### Then — operator-facing
| # | Feature |
|---|---|
| **F64** | ISA-18.2 alarm management (rationalisation, nuisance rate, shelving) |
| **F65** | Physics causal-chain explanation + counterfactual (beats SHAP bars) |
| **F66** | Case-based retrieval with citation from the knowledge graph |
| **F19–F24** | Visualisation: per-cylinder residual heat map, firing-order animation with the misfiring cylinder visibly skipping, live order waterfall, sensor-trust overlay, degradation ghost, bandwidth meter |

### Last — Tier 4 slack
**F25** differentiable physics (JAX) · **F26** particle-filter RUL · **F27** foundation-model baseline to beat · **F28** signed telemetry (HMAC) · **F29** federation hooks · **F30** multi-engine fleet deployment

---

## Standing caveat, applies to everything above

Every damage law, hazard rate, wear coefficient, oil limit and combustion
constant in this implementation is a **labelled placeholder** — marked as such in
the `source` field of the relevant dataclass. Relative comparisons (this
environment vs that one, this derate vs none, twin vs baseline) are defensible.
**No absolute number is**, until these are replaced with OEM- or
fleet-traceable values.

Three real defects were found by verification during this work and are recorded
in the log rather than quietly fixed: a detector that fired on the clock rather
than the engine (3 143 false alarms/hour), a change detector blind to the exact
failure mode that matters (slow degradation), and an isolability analysis that
reported a meaningless 100 % for any system. The harness catching these is the
argument for having built it.
