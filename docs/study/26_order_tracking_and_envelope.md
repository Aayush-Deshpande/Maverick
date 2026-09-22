# Part XXVI — Order Tracking and Envelope Analysis: Implementation

*[Part VI](06_vibration_analysis.md) explains why these techniques matter. This part is the algorithms, the parameter choices, and the ways they go wrong.*

---

## 26.1 Scope

[Part VI §6.6](06_vibration_analysis.md) establishes that order tracking is required and that "our vibration acquisition must be **synchronised with a crank/tach signal** — an acquisition-hardware decision that cannot be retrofitted in software." [§6.8](06_vibration_analysis.md) establishes that envelope analysis "is worth more to our fault-detection performance than any model architecture choice."

Both statements are correct and neither is implemented. This part closes that gap.

⬜ Implements features **F04, F05, F06, F07** of the [feature spec](../audit/04_feature_spec.md).

---

## 26.2 Angular resampling — the core algorithm

**Problem:** a UAV changes power constantly. Vibration sampled uniformly in *time* has spectral lines that move with RPM and smear when averaged. Resampling uniformly in *crank angle* freezes them.

```
INPUT   a[n]      accelerometer, uniform in time, fs = 10 kHz
        tach[k]   tach edge timestamps
OUTPUT  a_θ[m]    uniform in crank angle, N samples/revolution

1.  Build the angle-vs-time curve from tach edges:
        θ(t_k) = k · Δθ_tooth
    Interpolate to a continuous θ(t) — cubic spline, NOT linear.
    ⚠️ Linear interpolation makes ω piecewise-constant and injects
       discontinuities at every tooth, producing broadband artifacts.

2.  Invert to get t(θ) on a uniform angle grid:
        θ_grid = [0, Δθ, 2Δθ, …],  Δθ = 360° / N

3.  Resample the signal at those times:
        a_θ[m] = interp(a, t(θ_grid[m]))
    Band-limited interpolation (sinc / high-order spline). Linear here
    attenuates high orders.

4.  FFT of a_θ → ORDER spectrum. Bin k = order k·(N_rev/N_total).
```

### Choosing N (samples per revolution)

```
    N ≥ 2 × (highest order of interest) × (safety factor)
```

⬜ For us: gear mesh is the highest interesting feature. With ~30 teeth on the reduction gear, GMF ≈ order 30; with sidebands, order ~35. So `N ≥ 2 × 35 × 1.5 ≈ 105` → **use N = 128 or 256** (power of two).

⚠️ **N is limited by the real sample rate.** At 10 kHz and 5,000 RPM (83.3 rev/s), you have 120 time samples per revolution. Asking for N = 256 is asking for information you did not acquire — you will get interpolation artifacts, not resolution. **Rule: N ≤ fs/(RPM/60).** At 5,000 RPM this caps N at 120, so N = 64 or 128 is honest and 256 is not.

---

## 26.3 Order spectrum features

After resampling, FFT over an integer number of revolutions (⬜ 16–32 revolutions gives 1/16–1/32 order resolution — enough to separate sidebands).

| Order | Meaning (4-cyl 4-stroke) | Fault relevance |
|---|---|---|
| **0.5** | Once per cycle (720°) | **Misfire, cylinder imbalance** — [Part XXV §25.4](25_misfire_and_combustion_diagnostics.md) |
| 1 | Shaft rotation | Imbalance, bent shaft |
| 1.5 | Half-order harmonic | Misfire harmonic |
| **2** | **Firing frequency** | Normal combustion rhythm. Falls when a cylinder dies |
| 4 | 2nd firing harmonic | Combustion harshness |
| GMF (~30) | Gear mesh | Gear wear |
| GMF ± 1 | **Sidebands** | ✅ **Sideband growth is a more sensitive wear indicator than GMF amplitude itself** ([Part VI §6.7](06_vibration_analysis.md)) |

**Feature vector to extract** (this is what gets downlinked, F08):
```
E_0.5, E_1, E_1.5, E_2, E_4        band energies
E_0.5/E_2                          misfire ratio      ← dimensionless
E_GMF, E_sideband, SB/GMF          gear wear ratio    ← dimensionless
kurtosis, crest factor, RMS        broadband stats
```
🔶 **Prefer ratios over absolute energies.** Ratios are invariant to sensor mounting, gain drift, and overall level — so they transfer across airframes and survive a re-installed accelerometer. Absolute energies do not.

---

## 26.4 Envelope analysis

Bearing and gear defects produce **repetitive impacts** that excite a high-frequency structural resonance which then rings down. The defect rate is in the *modulation*, not the carrier — so the raw spectrum shows a resonance hump, and the diagnostic information is invisible until demodulated.

```
1. SELECT THE BAND
   Find the resonance: highest-kurtosis band, or spectral-kurtosis (kurtogram).
   ⚠️ This is the step that decides whether envelope analysis works.
      Wrong band → nothing found → wrongly conclude the method failed.

2. BAND-PASS
   Butterworth, order 4, around the resonance.
   ⬜ Typical: 2–5 kHz for a small engine/gearbox structure.

3. DEMODULATE
   env = |hilbert(x_bandpassed)|      # scipy.signal.hilbert, take magnitude

4. LOW-PASS + DECIMATE
   Envelope bandwidth only needs to cover defect frequencies (< ~500 Hz).

5. FFT THE ENVELOPE
   Peaks at defect frequencies. Express in ORDERS (defect frequencies are
   non-integer multiples of shaft speed, e.g. BPFO ≈ 3.6×).
```

**Defect frequency formulae** (bearing geometry, `n` balls, ball dia `d`, pitch dia `D`, contact angle `φ`, shaft freq `f_s`):
```
    BPFO = (n/2)·f_s·(1 − (d/D)cos φ)      outer race
    BPFI = (n/2)·f_s·(1 + (d/D)cos φ)      inner race
    BSF  = (D/2d)·f_s·(1 − ((d/D)cos φ)²)  ball
    FTF  = (1/2)·f_s·(1 − (d/D)cos φ)      cage
```
⬜ Rotax bearing geometry is not public 🔒 — assume plausible values and **label them**. The *method* is what we demonstrate; exact defect orders would come from the OEM.

✅ **Why this matters:** envelope analysis routinely detects faults while overall RMS still looks normal ([Part VI §6.8](06_vibration_analysis.md)). Early detection is precisely what the PS asks for.

---

## 26.5 Activating the existing analyser (F07)

`backend/ml/spectral_analyser.py` already contains correct Nyquist-aware DFT code:

```python
nyquist_hz = self._fs / 2.0
use_rms_fallback = target_hz > nyquist_hz     # True at 20 Hz → DFT never runs
```

At 20 Hz the 3rd-harmonic target (~103 Hz at 5,000 RPM through the 2.43:1 reduction) exceeds the 10 Hz Nyquist limit, so the module always takes the RMS fallback. **The DFT path is written and dormant.**

⬜ **Fix:** construct with `sample_rate_hz=10000`. Nyquist becomes 5 kHz, 103 Hz is comfortably resolved, and the module delivers the early-warning advantage its own docstring describes (fires at 3× baseline instead of 6.8×).

⬜ **Then upgrade:** replace the fixed-frequency `_peak_in_band` with an *order*-domain lookup so the target tracks RPM automatically instead of assuming a fixed Hz.

⚠️ Until this is done, no one should describe our system as doing "FFT vibration analysis" — at 20 Hz it does not, and two competitors ([Dronanetra](https://github.com/Jyotirmoy-006/Dronanetra), [GARUDA-Twin](https://github.com/mohit200628-cpu/Aero-Digital-Twin)) genuinely do. See the [audit addendum](../audit/05_expanded_survey.md).

---

## 26.6 Failure modes

⚠️ Each of these produces plausible-looking but wrong output — the dangerous kind of bug.

| Failure | Symptom | Cause | Fix |
|---|---|---|---|
| **Smeared lines** | Broad humps instead of sharp orders | FFT in time domain on varying RPM | Order tracking (§26.2) |
| **Phantom half-orders** | Spurious 0.5/1.5 content | Tooth-spacing error, uncorrected | Per-tooth correction ([Part XXV §25.2](25_misfire_and_combustion_diagnostics.md)) |
| **Envelope finds nothing** | Flat envelope spectrum | Wrong band selected | Kurtogram-driven band selection |
| **Aliased content** | Impossible low-frequency lines | No analog anti-alias filter | ⚠️ Hardware. Cannot be fixed in software |
| **Over-resampling** | High orders look clean but are fabricated | N > fs/(RPM/60) | Cap N (§26.2) |
| **Interpolation artifacts** | Broadband noise floor rises | Linear interp of θ(t) | Cubic spline |

---

## 26.7 Compute budget (edge feasibility)

⬜ Per 32-revolution window at 5,000 RPM (~0.38 s of data):

| Step | Cost |
|---|---|
| Angular resampling (N=128, 32 rev = 4096 pts) | ~1 ms |
| FFT 4096-pt | ~0.5 ms |
| Band-pass + Hilbert + envelope FFT | ~2 ms |
| Feature extraction | negligible |
| **Total** | **~4 ms per window, ~2.6 windows/s → ~1% of one core** |

🔶 Comfortably real-time on a Raspberry Pi 4. This is the number that makes the edge/ground split credible rather than aspirational — and it is worth quoting directly when explaining why onboard processing is feasible.

**Downlink:** ~15 features × 4 bytes ≈ 60 bytes per window → ~160 bytes/s at 2.6 windows/s. ✅ Against a ~122 kbit/s link carrying ~160 kbit/s of raw vibration, that is a reduction of roughly **1000×** — the concrete number behind [Part V](05_edge_ai.md)'s bandwidth argument.

---

*Depends on: [Part VI](06_vibration_analysis.md) (theory), [Part XXIV](24_combustion_cycle_and_crank_dynamics.md) (signal source). Feeds: [Part XXV](25_misfire_and_combustion_diagnostics.md).*
