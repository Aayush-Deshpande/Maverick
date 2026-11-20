# Fault Diagnosis and Isolation

Detection says *something is wrong*. Isolation says *what, where, how badly, and how sure we are*. ANUMAAN isolates faults with a Bayesian comparison of every candidate explanation against the physics-informed residual (see [Residual Analysis](08-residual-analysis.md)). It then turns the leading explanation into a directive taken word for word from the fault registry.

---

## 1. Candidate explanations

For one engine, the isolator compares:

| Hypothesis | What it predicts in the residual vector $\bar z$ |
|---|---|
| **Nominal** | Nothing: $\bar z \sim \mathcal N(0, vI)$ |
| **Engine fault** $f$ at location $\ell$ (each applicable registry fault F01–F37; each cylinder for cylinder faults) | Its signature scaled by an unknown severity: $\bar z \sim \mathcal N(s\,m_{f,\ell}, vI)$, $s \sim \mathcal U[0, S]$ |
| **Sensor offset** on channel $c$ (bias or slow drift, S02/S03) | Only that sender moves: $\bar z \sim \mathcal N(b\,e_c, vI)$, $b \sim \mathcal U[-B, B]$ |

$\bar z$ is an exponential average of the per-frame residual over about ten frames.

**Signatures** $m_{f,\ell}$ are measured, not written by hand. For each engine and fault, a training tail is calibrated, the fault is injected at half severity at three cruise points on two tails, and the settled residual is averaged and stored per unit severity. A cylinder fault is measured on one cylinder; for the others the cylinder channels are swapped. A run in which the engine fails stops averaging at the failure, so the signature describes the developing fault, not the wreck. The signatures are stored as CALIBRATED configuration (`configs/diagnose/signatures/`).

**Sensor offsets on model inputs.** Engine speed and oil temperature are also *inputs* of the nominal model. A biased oil-temperature sender therefore shifts the predicted oil pressure too, and that coupled pattern is computed for each frame by finite difference. A genuinely hotter oil does not shift the oil-pressure residual, and this is what separates the two.

---

## 2. Posterior

Each hypothesis is scored by its marginal likelihood, with the unknown severity integrated out in closed form:

$$p(\bar z \mid f,\ell) = \frac{1}{S}\int_0^S \mathcal N(\bar z;\, s\,m, vI)\,ds
= \frac{1}{S}\,\sqrt{\tfrac{2\pi}{a}}\;e^{-\frac12\left(c-\frac{b^2}{a}\right)}\left[\Phi\!\big(\sqrt a(S-\hat s)\big)-\Phi\!\big(-\sqrt a\,\hat s\big)\right]$$

where $a = \|m\|^2/v$, $b = \bar z\cdot m/v$, $c=\|\bar z\|^2/v$ and $\hat s=b/a$ is the most likely severity. The bracket is the *Occam factor*: a hypothesis that could explain almost anything pays for that flexibility.

$$P(f,\ell \mid \bar z) \propto P(f)\; p(\bar z \mid f,\ell)$$

**Priors** come from the FMECA occurrence rating of the fault's failure mode (MIL-STD-1629A-style table, `docs/reliability/fmeca.json`). Each registry fault is mapped to one of the FMECA modes. While an alarm is active, "nominal" keeps a prior advantage, because alarms can be false and the model must earn its call.

**Ambiguity groups.** Two faults whose signatures point the same way (cosine ≥ 0.95) cannot be told apart by the available channels. They are reported as one group with their individual posteriors instead of a forced pick. Examples are a coolant leak vs a blocked radiator (both raise every head temperature) and an oil-pressure loss vs an oil-pressure sender offset (only one channel moves).

Each published hypothesis carries its posterior, cylinder or channel, estimated severity, ambiguity group, and the channels that **support** it ($z_i m_i > 0$) or **contradict** it (the signature expects a clear move that is absent).

---

## 3. From hypothesis to action

The leading hypothesis is turned into a directive from the fault registry only (no generated text):

- **root cause:** the registry's physics explanation, with the cylinder filled in;
- **in-flight mitigation** and **maintenance action**, each with its source;
- the **ATA chapter**;
- the **status level** the registry assigns at full severity. The status evaluator uses it: an engine fault raises its registry level, while a sensor offset raises ADVISORY, because the engine itself is not implicated;
- **alternatives** in the same ambiguity group or with a comparable posterior.

The mission-reliability estimate attributes damage to the components of the isolated faults, weighted by posterior × estimated severity. Nothing downstream reads which fault was injected in the simulator.

---

## 4. Results (evidence class: SIMULATION)

Test tails use seeds 1001 and 1002; signature tails use seeds 11 and 12. Faults are injected at a cruise point (70 % lever, 8,000 ft) after the tail has settled. The registry's ramp plus its detection window plus 120 s is then observed.

| Engine | False alarms per flight hour (ours / engine-manual limits only) | Faults detected in the window (ours / limits only) | Median detection time | Median ROC AUC | Isolation top-1 / top-3 |
|---|---|---|---|---|---|
| Austro AE300 | 0.25 / 0.00 | 68 / 4 of 124 | 28 s | 0.94 | 68 % / 77 % |
| Rotax 912 iS | 0.00 / 0.75 | 32 / 9 of 100 | 146 s | 0.95 | 55 % / 65 % |
| Rotax 914 | 0.50 / 0.00 | 53 / 12 of 104 | 17 s | 0.95 | 71 % / 87 % |
| Rotax 915 iS | 0.25 / 0.00 | 68 / 8 of 124 | 26 s | 0.97 | 67 % / 77 % |
| VRDE 2.2 L | 0.00 / 0.00 | 58 / 0 of 124 | 32 s | 1.00 | 69 % / 77 % |

Each engine was tested with all applicable registry faults at severities 0.5 and 1.0 on two test tails.

- **Nominal runs.** Each test tail flew 2 hours of random legs: lever settings 45–95 %, altitudes 1,000–18,000 ft
  and ISA ±15 °C.
- **Independent plant variant.** Sensors were 1.5× noisier than the datasheet values, and the detector was
  calibrated on that variant itself. False-alarm rates were 0.25 / 0 / 0 / 0 / 0 per hour, in the table's engine
  order.
- **Earlier than the limits-only baseline.** Where we detected a fault, we detected it before the baseline did (or
  the baseline never did) in almost every case: AE300 68 of 68, VRDE 58 of 58, 915 64 of 68, 914 49 of 53 and 912
  29 of 32. The 912 had 2 ties.
- **The 915 iS.** It is modelled with a constant-speed (governed) propeller, the usual MALE UAV installation. With
  the fixed-pitch installation used before, the engine ran into its ECU rev limiter at high lever settings, and its
  false-alarm rate was 16 per hour.

Measured 20 Nov 2026 (`reports/evaluation/summary_2026-11-20.md`), after the oil relief valve was set inside the
normal band and the fault signatures were regenerated.

The full per-fault table (detection time, limits-only detection time, ROC AUC of the detector score against nominal frames, isolation rank) is generated by `python -m backend.evaluation.run_matrix` into `reports/evaluation/`.

**What the numbers mean.** Some registry faults leave no trace in the channels the residual covers today:
- oil quantity (F24) has no sensor;
- vibration-borne faults (propeller imbalance F28, mount F29, gearbox F27) show in the vibration orders, which are not yet residual channels;
- an electrical fault with a healthy alternator (F34) is masked on the bus voltage.

The table reports them as missed rather than hiding them.

---

## Related Systems

- [Residual Analysis](08-residual-analysis.md)
- [The AI and ML Architecture](09-ai-ml-architecture.md)
- [Bio-Inspired Sparse Novelty Coding](10-bio-inspired-sparse-novelty-coding.md)
- [Vibration Analysis and Order Tracking](12-vibration-analysis.md)
- [Mission Reliability Enhancement](17-mission-reliability.md)
