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
| Austro AE300 | 0.25 / 0.00 | 69 / 4 of 124 | 30 s | 0.94 | 58 % / 64 % |
| Rotax 912 iS | 0.00 / 1.00 | 31 / 9 of 100 | 127 s | 0.96 | 51 % / 58 % |
| Rotax 914 | 0.25 / 0.00 | 54 / 12 of 104 | 17 s | 0.95 | 57 % / 72 % |
| Rotax 915 iS | 16.0* / 2.25 | 70 / 87 of 120 | 23 s | 0.89 | 43 % / 48 % |
| VRDE 2.2 L | 0.00 / 0.00 | 67 / 0 of 124 | 32 s | 1.00 | 60 % / 66 % |

Each engine was tested with all applicable registry faults at severities 0.5 and 1.0 on two test tails. The nominal rows are 2 hours of random legs per tail, covering lever settings of 45–95 %, altitudes of 1,000–18,000 ft and ISA ±15 °C. On an independently built plant variant (sensors 1.5× noisier than the datasheet values, calibrated on itself), the false-alarm rates were 0.25 / 0 / 0 / 6.5 / 0 per hour.

Where a fault was detected, our detection came earlier than the limits-only baseline in almost every case (for example AE300 69 of 69, VRDE 67 of 67, 914 50 of 54).

\* The 915 iS figures are dominated by its fixed-pitch overspeed. At high lever settings above about 12,000 ft the engine runs into its ECU rev limiter, an abnormal state that both the limits-only baseline and our detector flag. Its other numbers are not comparable with the other engines until a constant-speed or governed installation is modelled for it.

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
