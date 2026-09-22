# What the Actual Solution Should Be

*Written after auditing 11 competing implementations and our own. The conclusion is not "do the same thing better."*

---

## 1. The strategic situation, in one paragraph

Eleven teams independently built the same system: physics residuals → IsolationForest/RandomForest → health index → RUL vs TBO → React dashboard. The paradigm is saturated. Within it, the winner is whoever adds the most sophistication, and [PRAHARI](https://github.com/atharv20s/sih-26) has already added a physics-informed neural network with Fourier heat conduction in the loss, a PPO controller, ablation studies and HMAC-signed telemetry. 🔶 **We will not beat that by adding a ninth classifier.** We beat it by competing on an axis the entire field has left empty.

---

## 2. The empty axis

> **All eleven teams treat vibration as a single scalar RMS number.**

Counted explicitly in [`01_competitive_audit.md`](01_competitive_audit.md) §7: **0 of 11** do order tracking, envelope analysis, sideband detection, or any kHz-rate acquisition. Sahilpatil's own feature-importance table puts vibration **first at 0.4532** — the most informative channel in their model — and it is still one scalar.

### Why that is the biggest unforced error in the field

For a reciprocating engine, vibration is not one number. It is a **crank-angle-resolved signal** in which every significant fault has a distinct, physically-predictable signature:

| PS fault target | Vibration signature | Visible in scalar RMS? |
|---|---|---|
| **Misfire** | Missing combustion impulse at that cylinder's firing angle → torsional deficit at order 0.5/1 | ❌ Almost invisible until severe |
| **Combustion instability** | Cycle-to-cycle variance at firing orders | ❌ No |
| **Injector abnormality** | Altered pressure-rise rate → changed impulse shape | ❌ No |
| **Gearbox / bearing wear** | Sidebands around mesh frequency; envelope-spectrum defect tones | ❌ Only when severe |
| **Abnormal vibration patterns** | Literally the spectrum | ❌ |

✅ **Five of the PS's eight named fault targets live in the vibration spectrum**, and the PS explicitly lists "Vibration signatures" as a monitored parameter and "Abnormal vibration patterns" as a detection target. The field is discarding the richest diagnostic channel in the machine and then applying sophisticated ML to what is left.

### ⚠️ This requires NO new study scope — the folder already mandates all of it

🔶 **This is not an expansion of our research. Every element was already specified, sourced, and flagged as critical in the study folder — and then not implemented.** Verbatim from the existing documents:

| Already written | Where |
|---|---|
| "If you keep only the averaged scalar, you throw away *instantaneous angular velocity*, and **that is where misfire detection lives**. A cylinder that fails to fire produces a missing acceleration, a detectable dip in the crank speed waveform within a single revolution." | [`02_engine_sensors.md:35`](../study/02_engine_sensors.md) |
| ✅ VERIFIED sources for crank-angular-velocity misfire detection, plus: "misfire is **not reliably detectable from 20 Hz averaged RPM alone**… **This is one of the most important design consequences in this entire course.**" | [`02_engine_sensors.md:37–39`](../study/02_engine_sensors.md) |
| A telemetry table row already reserved for `RPM (crank-angle resolved) — kHz-equivalent` | [`02_engine_sensors.md:282`](../study/02_engine_sensors.md) |
| "⬜ **Our requirement:** a dedicated vibration channel at **2–10 kHz** with a hardware anti-alias filter" | [`06_vibration_analysis.md:61`](../study/06_vibration_analysis.md) |
| Order tracking / angular resampling, fully explained — "our vibration acquisition must be **synchronised with a crank/tach signal**… **cannot be retrofitted in software, and it is easy to overlook until too late**" | [`06_vibration_analysis.md:174–187`](../study/06_vibration_analysis.md) |
| Envelope analysis — "routinely detects faults *far earlier* than RMS… **This one technique is worth more to our fault-detection performance than any model architecture choice.**" | [`06_vibration_analysis.md:248–280`](../study/06_vibration_analysis.md) |
| The complete acquisition→order-spectrum→envelope pipeline, already drawn as a diagram | [`06_vibration_analysis.md:331–348`](../study/06_vibration_analysis.md) |
| "Faults 1, 6 and 8 — three of the eight — **cannot be reliably detected without proper high-rate vibration or crank-angle data**. This is the single most important design consequence in the whole diagnosis problem, and it is why Part VI matters more than the choice of classifier." | [`08_fault_diagnosis.md:22`](../study/08_fault_diagnosis.md) |

🔶 **The study folder predicted this exact failure and warned against it in advance.** Part VI said the tach-synchronised acquisition decision is "easy to overlook until too late." It was overlooked. Part VIII said Part VI matters more than the classifier choice; we built the classifier and left the vibration path dormant.

⬜ **So the proposal is not "expand the scope." It is "stop expanding the scope."** Cut the ~3,000 lines of voice/agent/knowledge that sit *outside* the PS, and implement Parts II, VI and VIII, which are already researched, already sourced, and already declared the most important consequences in the course.

### Why we specifically are positioned to take it

🔶 We are 80% built for this and nobody else is close:

- ✅ [Part VI](../study/06_vibration_analysis.md) is a complete treatment of sampling, Nyquist, FFT, order tracking and envelope analysis — the only such document in the field.
- ✅ [`spectral_analyser.py`](../../backend/ml/spectral_analyser.py) already has correct, Nyquist-aware DFT scaffolding with a `sample_rate_hz` parameter. **The DFT path is written and dormant** ([`02_self_audit.md`](02_self_audit.md) §2). We do not need to build it; we need to feed it.
- ✅ [Part V](../study/05_edge_ai.md) already contains the bandwidth argument (~160 kbit/s raw vs a ~122 kbit/s link) that makes onboard processing *necessary* rather than decorative.

---

## 3. The thesis

> ## ANUMAAN is the digital twin that listens to the engine.
>
> Everyone else reads eight slow scalars and infers. We read the crankshaft at kHz, resolve combustion **cylinder by cylinder, cycle by cycle**, and detect the faults that are physically invisible to a scalar RMS — then compress that to a few hundred bits/s because the link cannot carry more.

🔶 This single thesis does five things at once, which is why I think it is the right one rather than just a novel one:

1. **It differentiates absolutely.** 0/11 competitors. Not "we did it better" — "we did it."
2. **It makes the edge split necessary.** kHz vibration genuinely cannot be downlinked. Our Parts V/XIII stop being architecture documentation and become the load-bearing justification for the whole design. The link-loss demo becomes essential rather than a nice extra.
3. **It attacks the field's weakest fault.** Misfire is PS fault #1 and the hardest for everyone else — Mehak's team reports it as a class; ours has recall 0.8359, our worst. Crank-angle detection solves it directly.
4. **It is physically legitimate, not a gimmick.** ✅ Crankshaft-angular-velocity misfire detection is a mature, documented discipline: [SAE 960039 overview](https://saemobilus.sae.org/papers/overview-misfiring-cylinder-engine-diagnostic-techniques-based-crankshaft-angular-velocity-measurements-960039), [2024 in-cylinder-gas-property study](https://journals.sagepub.com/doi/10.1177/14680874241261419), and multiple granted patents ([US7197916](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/7197916), [US7540185](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/7540185)). Every production car does it for OBD-II. **We are not inventing; we are the only team applying the standard technique.**
5. **It demos in five seconds.** Kill cylinder 3. The system names cylinder 3. No competitor can do that — their scalar RMS barely moves.

---

## 4. What to build

### 4.1 Crank-angle-resolved acquisition (the foundation)

⬜ Upgrade the generator from "vibration RMS scalar at 20 Hz" to a physically-derived signal chain:

```
cylinder pressure trace (crank-angle resolved, per cylinder)
        ↓  gas-torque + inertial-torque model
instantaneous crankshaft angular velocity  ω(θ)     ← the key signal
        ↓  forced-response / structural transfer
accelerometer signal  a(t)  @ 2–10 kHz
        ↓  tach-synchronous resampling
order-domain signal  a(θ)                            ← speed-invariant
```

🔶 Faults inject at the **pressure-trace level** — a misfire is "no combustion in cylinder 3 this cycle," not "add noise to the vibration channel." This is [Part XVII](../study/17_simulation_design.md)'s existing rule applied one layer deeper, and it is what makes the resulting signatures real rather than painted on.

### 4.2 Per-cylinder misfire detection from ω(θ)

⬜ The canonical method, which we can implement exactly:
1. Segment ω(θ) by TDC-to-TDC intervals, one per cylinder firing event.
2. Compute each cylinder's angular-acceleration contribution over its power stroke.
3. A misfiring cylinder shows a **torque deficit in its own segment** — directly attributable, no classifier required.
4. Track deficit per cylinder over cycles → misfire *rate* per cylinder, and cycle-to-cycle variance → combustion instability.

**Output:** *"Cylinder 3 misfiring at 4.2% of cycles, onset 11 minutes ago, trending +0.3%/min."* 🔶 That is a sentence no other team in this field can produce, and it is a physical measurement rather than a model inference.

### 4.3 Order-domain features for mechanical faults

⬜ Tach-synchronous resampling makes features **speed-invariant**, which matters because a UAV changes power constantly ([Part VI §6.9](../study/06_vibration_analysis.md)). Then: order spectrum for firing/shaft harmonics · envelope spectrum for bearing defect tones · sideband energy around gear mesh for the gearbox micro-pitting our spectral analyser already targets.

✅ This finally switches on the dormant DFT path — at 2–10 kHz the 103 Hz third harmonic is comfortably below Nyquist and the module works as designed.

### 4.4 The bandwidth story becomes the architecture story

⬜ kHz vibration → order/envelope features → a few hundred bits/s downlink. ✅ ~160 kbit/s raw vs a ~122 kbit/s link *forces* onboard computation. This is the point where our documentation and our demo finally say the same thing.

### 4.5 Close the cheap gaps while we are there

| Gap | Fix | Effort |
|---|---|---|
| No calibrated uncertainty | Conformal prediction on RUL; report **empirical coverage vs nominal** | Low. **0/11 have this** |
| No baseline comparison | Run the threshold comparator alongside; report detection lead time | Low. **0/11 have this** |
| Sensor residual not shielded | Zero residuals for quarantined channels (Gagguverse's approach) | Very low |
| Edge split undemonstrated | Separate process + link-loss demo; optionally a Pi | Medium |
| No external validation | Run our RUL method unchanged on C-MAPSS; report the number honestly | Medium. Near-unique |

---

## 5. The demonstration

🔶 Built around what only we can show.

| # | Beat | What the panel sees | Why it lands |
|---|---|---|---|
| **1** | **Kill cylinder 3** | System names **cylinder 3** in seconds, from torque deficit — not a classifier guess | 0/11 can do this |
| **2** | **Scalar-RMS comparison, side by side** | Our order-domain detector fires; the scalar RMS every competitor uses is **still flat** | Shows the field's shared blind spot without naming anyone |
| **3** | **Bandwidth meter** | kHz raw vs link capacity; features fit, raw does not | Makes the edge split self-evident |
| **4** | **Pull the cable** | Edge keeps detecting; GCS backfills on reconnect | 0/11 demo link loss |
| **5** | **Sensor drift vs engine fault** | We say SENSOR; threshold baseline aborts the sortie | Parity with the best competitors |
| **6** | **Conformal coverage plot** | Empirical coverage tracks nominal 90% | The only calibrated-uncertainty claim in the field |
| **7** | **Two mission profiles** | Same engine state, different go/no-go and limiting factor | The PS title |
| **8** | **The honesty slide** | Confusion matrix, val→test drop, C-MAPSS external result, and a plain statement of what synthetic data does and does not prove | We can afford this sentence; teams quoting bare "99.2%" cannot |

---

## 6. What this costs

**Keep:** evaluation methodology, sensor validator, component RUL + limiting subsystem, visualisation, study course, dataset honesty.

**Build:** crank-angle generator · ω(θ) misfire detector · order tracking + envelope · conformal RUL · baseline comparator · link-loss demo.

**Cut:** `backend/voice` (472 lines). Constrain `backend/agent` to retrieval-with-citation. Clean `scratch/` and `.backup_pre_*`.

🔶 **Honest risk:** §4.1 is real engine modelling and is the hardest thing in this plan. If the crank-angle generator is not physically credible, the whole thesis collapses into a prettier fake. ⬜ Mitigation: build it *first*, validate that a simulated healthy engine produces a plausible order spectrum before building anything on top, and keep the current 20 Hz pipeline running untouched as the fallback — it already scores 79/100 on its own.

---

## 7. The one-line pitch

> **Every other team infers engine health from eight slow numbers. We measure combustion directly — cylinder by cylinder, cycle by cycle — and we do it onboard, because the datalink physically cannot carry what we are listening to.**

---

*Audit set: [`01_competitive_audit.md`](01_competitive_audit.md) · [`02_self_audit.md`](02_self_audit.md) · this document.*
