# Proposal note — vibration vs. telemetry frequency, and the edge/ground split

*A condensed, pitch-ready answer to "what frequency do we need, and why split compute at all?" Full derivations live in [Part V](05_edge_ai.md), [Part VI](06_vibration_analysis.md), and [Part XIII](13_edge_vs_ground_split.md); this note pulls the numbers together in one place.*

---

## The core point

Transmitting raw vibration to the ground is not "not ideal" — it is arithmetically impossible on this link. Vibration must be analysed onboard, and the numbers below are why.

## Three different "frequencies" — do not conflate them

The question "what frequency do we need" has three separate correct answers, because vibration, telemetry, and the radio link are three different things measured in three different units.

| What | Rate | Why this number |
|---|---|---|
| **Vibration sampling** (onboard accelerometer ADC) | **2–10 kHz** | Nyquist: to resolve a frequency you must sample at more than 2× it. A 4-stroke engine at 5,000 RPM has a firing fundamental of ≈167 Hz, plus harmonics and bearing-defect frequencies well above that — kHz-range sampling is required or the content aliases into meaningless noise. ⬜ Our requirement, ✅ consistent with practice (CWRU: 12 kHz, XJTU-SY/FEMTO: 25.6 kHz, TinyML edge deployments: ~2 kHz) |
| **Telemetry/CAN scalars** (onboard bus: RPM, CHT, EGT, oil pressure, etc.) | **~20 Hz** | These are slow physical quantities — thermal time constants are seconds — so 20 Hz already oversamples them. A 20 Hz channel *cannot* see engine vibration; sampling vibration at telemetry rate aliases it into garbage that looks like a valid but wrong signal |
| **Downlink to ground** (the actual radio link) | **~19 kbit/s continuous + ~1.3 kbit/s periodic**, within a ✅ ~122 kbit/s total Ku-band SATCOM budget | This is a *bandwidth* number, not a sample rate — one accelerometer alone at 10 kHz already produces ~160 kbit/s, which exceeds the entire link budget before any other telemetry is added |

**Vibration and telemetry are not the same signal class.** Vibration is a raw waveform needing spectral analysis; telemetry is slow-changing scalars. Treating them with one shared "communication frequency" is the mistake this table exists to prevent.

## Why raw vibration can never be transmitted

The wall is arithmetic, not a design preference:

```
1 accelerometer @ 10 kHz  ≈ 160 kbit/s
Entire Ku-band C2 link    ≈ 122 kbit/s or less  (✅ VERIFIED)

160 kbit/s > 122 kbit/s  — before adding any other channel, and
before the link degrades from terrain masking, weather, or jamming.
```

There is no configuration of "just send it to the ground" that fits. Onboard reduction is mandatory, not optional.

## What that forces onboard

- **Raw vibration acquisition (2–10 kHz) → windowed FFT → order analysis.** This is the **~4,000× data-reduction step**: a kHz waveform becomes a compact feature vector (RMS, kurtosis, spectral peak amplitudes) small enough to fit the link.
- **Physics residual computation + a lightweight anomaly score at 20 Hz.** The link can vanish entirely — terrain masking, jamming, handover — so detection that matters must survive comms loss. A fault that needs a reaction cannot wait on a channel that might not exist at that moment.

## What stays on the ground, and why

- **RUL/prognosis, trend analysis, mission replay, maintenance advisory, the operator dashboard.** These need longer historical context and heavier models, have no latency pressure, and the ground station has grid power and real compute — none of the UAV's weight/power/thermal limits apply.
- **The human in the loop.** Prognosis-grade decisions (mission go/no-go) should have one, and the ground segment is where that happens.

## The actual downlink pattern (not one fixed rate — three tiers)

| Tier | Content | Rate |
|---|---|---|
| **Continuous** | Core scalars + health index | 20 Hz (~19 kbit/s) |
| **Periodic** | Compressed vibration *feature* vector — never the raw waveform | 1 Hz (~1.3 kbit/s) |
| **On-request** | A detailed snapshot around a flagged timestamp, pulled by the operator after the edge raises an event | Event-triggered |

**The principle:** spend scarce, unreliable bandwidth *retrospectively* — only on the moment that turned out to matter — instead of streaming everything continuously and starving the link exactly when something important happens.

---

*Part of the ANUMAAN documentation suite. See [Part V — Edge AI](05_edge_ai.md) for the bandwidth-reducer argument in full, [Part VI — Vibration Analysis](06_vibration_analysis.md) for the Nyquist/FFT derivation, and [Part XIII — Edge vs. Ground Split](13_edge_vs_ground_split.md) for the complete compute-split table.*
