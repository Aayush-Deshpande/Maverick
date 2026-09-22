# Part VI — Vibration Analysis from Zero

*The full tutorial: sampling, Nyquist, FFT, orders, envelope analysis, and the features that actually detect faults.*

---

## 6.1 Sampling — turning a continuous signal into numbers

A vibration sensor outputs a continuously varying voltage. A computer can only store discrete values. **Sampling** measures that voltage at regular intervals.

```
Continuous:    ╱‾╲    ╱‾╲    ╱‾╲
              ╱   ╲__╱   ╲__╱   ╲
Sampled:      •  •  •  •  •  •  •      ← fs = samples per second
```

**Sampling frequency (fs)** is measured in Hz. At fs = 10,000 Hz you take 10,000 measurements per second, one every 100 µs.

---

## 6.2 Nyquist and aliasing — the most important constraint

**Concept → Why it exists → How it works → Example → How we use it**

### The Nyquist–Shannon theorem

> To reconstruct a signal containing frequencies up to `f_max`, you must sample at **more than 2 × f_max**.

`fs / 2` is the **Nyquist frequency** — the highest frequency your sampling can represent.

### What goes wrong below it: aliasing

A frequency above Nyquist does not vanish. It **folds back** and masquerades as a lower frequency. This is catastrophic, because the false low frequency is indistinguishable from a real one.

```
True signal:   9 Hz sine
Sampled at:    10 Hz   (Nyquist = 5 Hz)

Observed:      1 Hz sine     ← completely wrong, and looks perfectly valid
```

The alias formula: an input at `f` sampled at `fs` appears at `|f − round(f/fs) × fs|`.

**The wagon-wheel effect in old films is aliasing** — a wheel spinning faster than the frame rate appears to rotate slowly backwards.

### Why this decides the architecture

Recall from [Part II §2.1](02_engine_sensors.md): a 4-stroke 4-cylinder at 5,000 RPM has a **firing fundamental of ≈167 Hz**.

```
Sampling at 20 Hz  →  Nyquist = 10 Hz
167 Hz content     →  ALIASES into the 0–10 Hz band as garbage
```

**A 20 Hz telemetry channel cannot see engine vibration. It can only see a distorted, aliased shadow of it.** Any spectral analysis done on 20 Hz vibration data is not measuring engine harmonics — this is a genuine, common, and serious error.

### The defence: anti-alias filtering

You must **low-pass filter in analog hardware, before the ADC**, to remove everything above Nyquist. You cannot do this in software afterwards, because by then the aliased content is already mixed in and mathematically unrecoverable.

⬜ **Our requirement:** a dedicated vibration channel at **2–10 kHz** with a hardware anti-alias filter. ✅ This matches practice: CWRU samples at 12 kHz, XJTU-SY and FEMTO at 25.6 kHz, and edge deployments commonly use 2 kHz. ([CWRU](https://digibuo.uniovi.es/dspace/bitstream/handle/10651/69892/Bearing_Fault_Diagnosis_With_Envelope_Analysis_and_Machine_Learning_Approaches_Using_CWRU_Dataset.pdf?sequence=1&isAllowed=y), [XJTU-SY/FEMTO](https://arxiv.org/pdf/2109.12513), [TinyML 2 kHz](https://github.com/Shafqat-16/stm32-edge-ai-vibration-anomaly-detection))

---

## 6.3 Time domain versus frequency domain

The **time domain** is amplitude versus time — what the sensor produces. The **frequency domain** is energy versus frequency — which vibration "tones" are present and how strong.

```
TIME DOMAIN                        FREQUENCY DOMAIN
amplitude                          magnitude
   │  ╱╲  ╱╲╱╲ ╱╲                    │    │
   │ ╱  ╲╱    ╲  ╲      ──FFT──▶     │    │       │
   │╱          ╲  ╲                  │    │   │   │
   └─────────────── time             └────┴───┴───┴──── frequency
   "messy, uninformative"            "83 Hz, 167 Hz, 334 Hz — readable"
```

**Why this transformation is the whole game:** a rotating or reciprocating machine produces vibration at frequencies determined by its *geometry and speed*. Each component has a characteristic frequency. In the time domain everything is superimposed into noise. In the frequency domain each component gets its own line, and **a fault changes the height of a specific, identifiable line**.

---

## 6.4 The FFT and its parameters

The **Fourier Transform** decomposes a signal into constituent sinusoids. The **FFT (Fast Fourier Transform)** computes it efficiently: O(N log N) rather than O(N²).

### The three numbers you must be able to compute

Given `fs` and a window of `N` samples:

```
Frequency resolution:  Δf = fs / N        (Hz per bin)
Maximum frequency:     f_max = fs / 2     (Nyquist)
Window duration:       T = N / fs         (seconds)
```

**Worked example** — fs = 10,000 Hz, N = 2048:

```
Δf = 10000/2048  ≈ 4.88 Hz per bin
f_max = 5,000 Hz
T = 2048/10000   ≈ 0.205 s
```

So this window resolves frequencies about 5 Hz apart, sees up to 5 kHz, and covers 205 ms.

### The resolution/time trade-off — a real engineering tension

Better frequency resolution requires a longer window. But a longer window assumes the machine's speed is constant *throughout* it — and averages over transients. This is the fundamental tension in vibration analysis:

| | Short window | Long window |
|---|---|---|
| Frequency resolution | Poor | Good |
| Time localisation | Good | Poor |
| Speed-change tolerance | Good | Poor — smears spectral lines |

⬜ For our system: **~0.2–0.5 s windows** as a balance. A UAV in steady cruise changes speed slowly, so this is comfortable; during throttle transients we should either extend the window or flag the result as low-confidence.

### Windowing functions

Cutting a finite window creates artificial discontinuities at its edges, which smear energy across the spectrum ("spectral leakage"). A window function (Hann, Hamming, Blackman) tapers the ends to zero to suppress this.

⬜ Use a **Hann window** unless there is a specific reason not to. It is the sensible default for general vibration work.

### PSD — Power Spectral Density

A PSD is a normalised FFT magnitude-squared, expressed as power per unit frequency (g²/Hz). Normalising by bin width makes PSDs comparable across different window lengths and sample rates — which raw FFT magnitudes are not. **Use PSD whenever you compare spectra computed with different parameters.**

### STFT and spectrograms

A **spectrogram** is a sequence of FFTs over successive (usually overlapping) windows — a picture of how the spectrum evolves.

```
frequency
    │ ░░░░▓▓▓▓████     ← this band grows over time = degradation
    │ ░░░░░░░░░░░░
    │ ████████████     ← this line is constant = normal running
    └──────────────── time
```

Spectrograms matter for us for two reasons: they show degradation *trends* directly, and they turn vibration into an image, which lets you use 2D CNNs ([Part VIII](08_fault_diagnosis.md)).

---

## 6.5 Orders — the concept that makes variable speed tractable

### The problem

Engine vibration frequencies are proportional to shaft speed. At 4,000 RPM the firing fundamental is ≈133 Hz; at 5,000 RPM it is ≈167 Hz. **The same fault appears at a different frequency depending on throttle setting.** Comparing raw spectra across a flight is therefore comparing incomparable things — and a UAV changes power constantly.

### The solution: normalise by rotation

An **order** is a multiple of shaft rotational frequency.

```
Shaft frequency:  f_shaft = RPM / 60   (Hz)

Order 1  =  1 × f_shaft   — once per revolution
Order 2  =  2 × f_shaft   — twice per revolution
Order 0.5 = half shaft speed — once per two revolutions
```

At 5,000 RPM, `f_shaft = 83.3 Hz`. So:

| Order | Frequency @5000 RPM | Physical meaning (4-stroke, 4-cyl) |
|---|---|---|
| 0.5 | 41.7 Hz | One full engine cycle (2 revolutions) |
| 1 | 83.3 Hz | Shaft imbalance |
| 2 | 166.7 Hz | **Firing frequency** (4 cyl × 0.5) — reciprocating 2nd order |
| 4 | 333.3 Hz | Firing harmonic |

**In the order domain, a given fault sits at the same order regardless of speed.** That is what makes cross-condition comparison possible.

### Order tracking

✅ **VERIFIED** — order tracking (angular resampling) resamples the vibration signal to synchronise it with the **rotational angle of the shaft rather than with time**. It requires a speed measurement — a tachometer or encoder — to estimate instantaneous angular position, and the vibration and angle signals must be acquired **synchronously**. It is described as a perfect tool for machines running at varying speeds, and is used in condition-based maintenance of engines, gears, turbines and pumps. ([Order tracking](https://en.wikipedia.org/wiki/Order_tracking_(signal_processing)), [Dewesoft order analysis](https://dewesoft.com/blog/what-is-order-analysis))

```
TIME DOMAIN (speed varying)           ANGLE DOMAIN (after resampling)
  fault frequency smears               fault sits at a fixed order
  across many bins                     in one sharp line
       ╱╲__╱╲                                  │
    ╱╲╱      ╲╱╲                               │
  ──────────────── Hz                  ────────┴──────── order
```

⬜ **Design requirement this creates:** our vibration acquisition must be **synchronised with a crank/tach signal**. This is an acquisition-hardware decision that cannot be retrofitted in software, and it is easy to overlook until too late.

### Synchronous averaging

✅ Representing acceleration in the angle domain enables **time/rotor synchronous averaging (TSA/RSA)** to remove non-synchronous effects. ([Angle measurements in gear condition monitoring](https://www.sciencedirect.com/science/article/pii/S0888327024011531))

Averaging many revolutions, aligned by angle, reinforces anything locked to rotation and cancels everything else. It is an extremely effective noise reducer for rotating-machinery faults.

---

## 6.6 Reciprocating engines are not rotating machines

This distinction is central to our problem and is frequently missed.

✅ **VERIFIED** — piston engines "demonstrate complex dynamic behavior due to cyclic variations in pressure and volume, unlike steady-state rotating equipment, introducing unique challenges for fault detection." ([Piston engine fault diagnostics review](https://link.springer.com/article/10.1007/s10973-025-14728-1))

A turbine's vibration is broadly stationary. A piston engine's is fundamentally **cyclic and impulsive**: discrete combustion events, valve impacts, piston reversals at top and bottom dead centre. The signal is a train of impulses locked to crank angle, not a steady tone.

Consequences:

1. **Crank-angle-domain analysis is the natural frame.** ✅ Raw vibration from cylinder accelerometers is converted into a synchronised acceleration waveform versus crank angle, which can then be filtered and averaged. ([Baker Hughes reciprocating compressor monitoring](https://www.bakerhughes.com/bently-nevada/orbit-home/orbit-article/reciprocating-compressor-condition-monitoring-q2), [crank-angle reconstruction](https://www.researchgate.net/publication/286312783_Engine_Fault_Detection_Using_Vibration_Signal_Reconstruction_in_the_Crank-Angle_Domain))
2. **Half-orders are meaningful.** A 4-stroke cycle takes two revolutions, so cylinder-specific events appear at half-integer orders — something that does not arise in purely rotating machinery.
3. **Bearing-dataset intuitions transfer only partially.** CWRU-style constant-speed rotating-machinery results do not map cleanly onto a cyclic engine. See [Part VIII §8.6](08_fault_diagnosis.md).

---

## 6.7 Characteristic fault frequencies

### Bearing defect frequencies

A rolling-element bearing generates specific frequencies when a defect strikes rolling elements. They depend on geometry (pitch diameter, ball diameter, number of balls, contact angle) and shaft speed, and are **non-integer multiples of shaft speed**:

| Abbrev. | Name | Defect location |
|---|---|---|
| BPFO | Ball Pass Frequency, Outer race | Outer race |
| BPFI | Ball Pass Frequency, Inner race | Inner race |
| BSF | Ball Spin Frequency | Rolling element |
| FTF | Fundamental Train Frequency | Cage |

**The key diagnostic property:** because they are non-integer orders, they do **not** coincide with shaft harmonics. Energy appearing at a non-integer order is therefore strong evidence of a bearing defect rather than imbalance or combustion. 🔶 This separation is what makes bearing diagnosis feasible at all.

### Gear mesh frequency

```
GMF = number_of_teeth × shaft_frequency
```

A reduction gearbox (a Rotax 912 has one driving the propeller) produces a strong line at GMF plus sidebands. **Sideband growth around GMF is a classic wear indicator** — often more sensitive than the GMF amplitude itself.

### Combustion-related

| Feature | Order | Meaning |
|---|---|---|
| Firing frequency | cylinders × 0.5 (4-stroke) | Normal combustion rhythm |
| Individual cylinder | 0.5 order components | Cylinder-specific events |
| **Half-order growth** | 0.5 and odd half-orders | **Misfire signature** — one cylinder behaving differently per cycle |

🔶 **INFERENCE** — this is why misfire is detectable in vibration: a misfire breaks the cycle-to-cycle symmetry, dumping energy into half-order components that are small in a healthy engine.

---

## 6.8 Envelope analysis — extracting weak impulsive faults

### The problem it solves

An early bearing defect produces tiny impacts. Their direct energy is buried under combustion and gear vibration, which is orders of magnitude larger. A plain FFT will not show it.

### The insight

The impacts do not merely add energy at the defect frequency. They **excite a structural resonance** — the housing "rings" like a bell each time. The result is a high-frequency carrier *amplitude-modulated* at the defect frequency.

```
Raw signal:   high-frequency ringing, bursting at each impact

    ╱╲╱╲╱╲        ╱╲╱╲╱╲        ╱╲╱╲╱╲
   ╱      ╲      ╱      ╲      ╱      ╲       ← 3 kHz carrier
  ╱        ╲____╱        ╲____╱        ╲
  ↑                       ↑
  └──── impacts at BPFO ──┘

Envelope (the outline):    ╱‾╲___╱‾╲___╱‾╲     ← repeats at BPFO
FFT of the envelope:       a clean line at BPFO ✓
```

### The procedure

1. **Band-pass filter** around the resonance (found empirically, or via kurtogram).
2. **Rectify and demodulate** — typically the magnitude of the Hilbert transform — to get the envelope.
3. **FFT the envelope.**
4. **Look for lines at BPFO/BPFI/BSF/FTF.**

✅ Envelope analysis is standard practice for bearing diagnosis and is used with CWRU-type data. ([Envelope analysis with CWRU](https://digibuo.uniovi.es/dspace/bitstream/handle/10651/69892/Bearing_Fault_Diagnosis_With_Envelope_Analysis_and_Machine_Learning_Approaches_Using_CWRU_Dataset.pdf?sequence=1&isAllowed=y))

**Why this matters for us:** envelope analysis routinely detects faults *far earlier* than RMS does — often while overall amplitude still looks normal. Early detection is precisely what the PS is asking for. **This one technique is worth more to our fault-detection performance than any model architecture choice.**

---

## 6.9 Time-domain features

Cheap to compute, useful as trend indicators, and the natural inputs to a small edge model.

### RMS — Root Mean Square

```
RMS = √( (1/N) Σ xᵢ² )
```

Overall energy. Rises with most faults, but **late** — it is a blunt instrument, and a fault can be well advanced before RMS moves noticeably.

### Kurtosis — the early-warning statistic

```
Kurtosis = E[(x − μ)⁴] / σ⁴
```

The fourth standardised moment: a measure of "peakiness". Gaussian noise has kurtosis 3.

**Why it is valuable:** the fourth power weights outliers enormously. An early impulsive fault adds a few sharp spikes that barely move RMS but move kurtosis substantially. Kurtosis is therefore an **early** indicator where RMS is a late one.

🔶 **Important caveat:** kurtosis is non-monotonic over a fault's life. It rises as discrete impacts appear, then *falls* as the defect worsens and impacts become frequent enough to look like continuous noise again. **Never use kurtosis alone as a degradation index** — a falling kurtosis can mean recovery or severe deterioration. Pair it with RMS: RMS low + kurtosis high = early fault; RMS high + kurtosis falling = advanced fault.

### Crest factor

```
Crest factor = peak / RMS
```

Also impulsiveness, and shares kurtosis's non-monotonic behaviour.

### Peak-to-peak

Maximum minus minimum in the window. Simple, sensitive to single events, and noisy.

### Band energy

Energy summed within specific frequency or order bands — e.g. "energy in orders 2.8–3.2" to watch a particular harmonic. 🔶 **These are usually the most diagnostically valuable features**, because each band is tied to a physical component. They are also inherently explainable: "band 3 rose 40%" maps directly to a mechanical story, which matters for the explainable-AI requirement ([Part XX](20_novelty_and_research.md)).

---

## 6.10 The complete feature pipeline

⬜ Our proposed onboard chain:

```
Accelerometer @ 10 kHz  +  crank/tach signal
            │
            ▼
   [Anti-alias filter — ANALOG, before ADC]    ← cannot be done later
            │
            ▼
   [Window: 2048 samples, Hann, 50% overlap]   → ~10 windows/s
            │
            ├──────────────────────────────────────────┐
            ▼                                          ▼
   [Angular resampling using tach]         [Band-pass around resonance]
            │                                          │
            ▼                                          ▼
   [Order spectrum]                           [Hilbert envelope]
            │                                          │
            ▼                                          ▼
   [Order band energies:                      [Envelope FFT]
    0.5, 1, 2, 4, GMF, sidebands]                      │
            │                                          ▼
            │                              [BPFO/BPFI/BSF/FTF energies]
            │                                          │
            └────────────────┬─────────────────────────┘
                             ▼
              [Time-domain stats: RMS, kurtosis,
               crest factor, peak-to-peak]
                             ▼
              ┌──────────────────────────────┐
              │  FEATURE VECTOR ≈ 40 floats  │
              │  at ~1 Hz  ≈ 1.3 kbit/s      │
              │  ~4,000× reduction from raw  │
              └──────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                ▼                         ▼
        [Edge anomaly model]      [Telemetry downlink]
```

---

## 6.11 Worked example — how a fault changes the spectrum

⬜ **ILLUSTRATIVE** — constructed to teach the reasoning, not measured data.

**Healthy engine, 5,000 RPM** (`f_shaft` = 83.3 Hz):

| Order | Frequency | Amplitude | Source |
|---|---|---|---|
| 1 | 83 Hz | 0.8 g | Residual imbalance — normal |
| 2 | 167 Hz | 2.1 g | Firing frequency — dominant, normal |
| 4 | 333 Hz | 0.6 g | Firing harmonic |
| GMF | ~2.1 kHz | 0.4 g | Gearbox mesh |
| 0.5 | 42 Hz | 0.05 g | Very small — cycles are symmetric |

RMS 2.4 g, kurtosis 3.1 (near-Gaussian).

**Same engine, cylinder 2 misfiring:**

| Order | Amplitude | Change |
|---|---|---|
| 0.5 | **0.9 g** | **↑ 18×** — cycle symmetry broken |
| 1 | 1.1 g | ↑ modest |
| 2 | 1.7 g | ↓ — one cylinder contributing less |
| 4 | 0.5 g | ↓ slightly |

RMS 2.5 g — **essentially unchanged**. Kurtosis 4.8 — clearly up.

**The lesson in one line:** RMS moved by 4% and would not trip any sensible threshold. The 0.5-order energy moved by 1,800%. **A scalar RMS channel would miss this fault entirely; an order-band feature catches it trivially.** This is the concrete justification for everything in this part.

**Bearing outer-race defect**, by contrast: order spectrum barely changes, but envelope FFT grows a clear line at BPFO (a non-integer order such as ~3.6×), and kurtosis rises while RMS stays near normal. Different fault, different feature, both invisible to RMS.

---

## 6.12 Common mistakes

| Mistake | Consequence |
|---|---|
| Sampling vibration at telemetry rate (20 Hz) | Aliasing. The analysis is meaningless |
| No analog anti-alias filter | Unrecoverable corruption — cannot be fixed in software |
| FFT without order tracking on a variable-speed engine | Spectral lines smear; faults hide |
| Using RMS alone | Misses early and cycle-asymmetric faults (see §6.11) |
| Kurtosis alone as a degradation index | Non-monotonic — falling kurtosis is ambiguous |
| Ignoring the tach/crank synchronisation requirement | Order tracking becomes impossible after the fact |
| Applying rotating-machinery assumptions to a piston engine | Cyclic, impulsive behaviour needs crank-angle framing ✅ |

---

**Next:** [Part VII — Anomaly Detection](07_anomaly_detection.md)
