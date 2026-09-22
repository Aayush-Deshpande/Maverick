# Part XXIV — Combustion Cycle and Crank Dynamics

*The physics layer beneath [Part XVII](17_simulation_design.md). Implementation-grade: every equation here is meant to be typed into code.*

---

## 24.1 Why this part exists

[Part XVII §17.5](17_simulation_design.md) synthesises vibration as a **sum of prescribed order components** — sines at orders 0.5, 1, 2, 4, plus gear mesh and bearing impulses. That is good enough to exercise an envelope-analysis pipeline, and it was the right call at that stage.

But it has a structural limit: **it never computes crankshaft angular velocity.** `combustion_impulses(t, f_shaft, n_cyl, misfire_cyl)` prescribes an impulse train and deletes one impulse for a misfire. The misfire signature is *asserted*, not *derived*.

🔶 Consequence: a detector trained against it learns "an impulse is missing from a synthetic impulse train," which is circular. And there is no `ω(θ)` signal at all, so the per-cylinder torque-deficit method ([Part XXV](25_misfire_and_combustion_diagnostics.md)) has nothing to run on.

⬜ **This part supplies the missing layer:** cylinder pressure → torque → crank dynamics → **ω(θ)**. With it, a misfire is "no heat release in cylinder 3 this cycle" and every downstream signature — angular velocity dip, order-0.5 growth, EGT drop — *emerges from the physics* rather than being painted on.

---

## 24.2 Reference engine parameters

✅ **VERIFIED** — public manufacturer and type-certificate data. ⬜ Estimated values are marked.

| Parameter | Rotax 912 iS | Rotax 914 | Source |
|---|---|---|---|
| Configuration | 4-cyl horizontally opposed, 4-stroke | same | ✅ |
| Bore | 84.0 mm | 79.5 mm | ✅ [912](https://en.wikipedia.org/wiki/Rotax_912) / [914](https://en.wikipedia.org/wiki/Rotax_914) |
| Stroke | 61.0 mm | 61.0 mm | ✅ |
| Displacement | 1,352 cm³ | 1,211.2 cm³ | ✅ |
| Compression ratio | 10.8 : 1 | 8.75 : 1 | ✅ |
| **Firing order** | **1 – 4 – 2 – 3** | **1 – 4 – 2 – 3** | ✅ [Rotax 912 maintenance manual](https://www.manualslib.com/manual/877282/Rotax-912-Series.html?page=257) |
| Gear reduction | 2.4286 : 1 | 2.273 or 2.43 : 1 | ✅ |
| Induction | naturally aspirated, EFI | turbocharged, carburetted | ✅ |

⬜ **Values we must assume** (not public; label them as assumptions everywhere):

| Parameter | Assumed | Basis |
|---|---|---|
| Connecting rod length `l` | 110 mm | 🔶 λ = r/l ≈ 0.277, typical for this class |
| Reciprocating mass per cylinder | 0.45 kg | 🔶 piston + rings + pin + small end |
| Crank+flywheel inertia `J` | 0.08 kg·m² | 🔶 tune so idle speed fluctuation is realistic |
| Wiebe efficiency factor `a` | 5.0 | ✅ standard — gives 99.3% burn completion |
| Wiebe shape factor `m` | 2.0 | ✅ typical for spark ignition |
| Burn duration `Δθ` | 60° CA | 🔶 40–70° typical SI |
| Combustion start `θ₀` | −15° ATDC | 🔶 varies with timing map |

✅ **Cross-check:** our existing `spectral_analyser.py` uses `GEAR_REDUCTION_RATIO = 2.43`, which matches the 914's optional ratio and is within 0.06% of the 912 iS's 2.4286. That constant is correct.

---

## 24.3 Slider-crank kinematics

With crank radius `r = stroke/2`, rod length `l`, crank angle `θ` measured from TDC:

```
Piston displacement from TDC:
    x(θ) = r(1 − cos θ) + l(1 − √(1 − λ² sin²θ)) ,   λ = r/l

Piston velocity (per unit crank rate):
    dx/dθ = r·sin θ · [ 1 + (λ cos θ)/√(1 − λ² sin²θ) ]

Piston acceleration:
    d²x/dθ² = r·cos θ + r·λ·(cos 2θ + λ² sin⁴θ)/(1 − λ² sin²θ)^{3/2}
```

**Cylinder volume:**
```
    A_p = π·bore²/4                       piston area
    V_d = A_p · stroke                    swept volume per cylinder
    V_c = V_d / (CR − 1)                  clearance volume
    V(θ) = V_c + A_p · x(θ)
```

⚠️ **Common error:** using `2r` for stroke *and* `r = stroke/2` together. Pick one. Here `r = stroke/2 = 30.5 mm` for both Rotax variants.

---

## 24.4 Wiebe heat release

✅ The industry-standard empirical burn-rate correlation for 0-D combustion simulation ([regression models for Wiebe parameters, *Energy*](https://www.sciencedirect.com/science/article/abs/pii/S0360544220315504)).

**Mass fraction burned:**
```
    x_b(θ) = 1 − exp( −a · ((θ − θ₀)/Δθ)^(m+1) )      for θ₀ ≤ θ ≤ θ₀+Δθ
    x_b = 0   before θ₀
    x_b = 1   after θ₀+Δθ
```

**Burn rate (what we actually need):**
```
    dx_b/dθ = a(m+1)/Δθ · ((θ−θ₀)/Δθ)^m · exp( −a·((θ−θ₀)/Δθ)^(m+1) )
```

**Heat release rate:**
```
    dQ/dθ = Q_total · dx_b/dθ ,    Q_total = m_fuel,cycle · LHV · η_comb
```

⬜ **This is the single injection point for combustion faults** — and it is what makes the whole approach honest:

| Fault | Wiebe modification |
|---|---|
| **Misfire** | `Q_total = 0` for that cylinder, that cycle |
| **Partial burn / injector fault** | `Q_total ×= 0.6` |
| **Slow burn / degraded ignition** | `Δθ ×= 1.4` |
| **Combustion instability** | `θ₀`, `Δθ`, `Q_total` given cycle-to-cycle random jitter |
| **Detonation** | `Δθ` collapsed + pressure spike superimposed |

🔶 Every downstream observable — the ω(θ) dip, order-0.5 energy, EGT deficit on that cylinder, vibration change — then *follows from physics*. This is [Part XVII §17.1](17_simulation_design.md)'s rule ("faults modify physical parameters, never output signals") applied one layer deeper than Part XVII currently applies it.

---

## 24.5 Cylinder pressure — single-zone first law

```
    dp/dθ = (γ−1)/V(θ) · dQ/dθ  −  γ·p/V(θ) · dV/dθ
```

γ ≈ 1.35 for burned mixture (⬜ 1.4 for air is acceptable at our fidelity).

**Integrate over the 720° four-stroke cycle** with 0.5–1° steps. Boundary conditions:
- Intake (0–180° ATDC, cycle start): `p ≈ MAP`
- Compression (180–360°): polytropic `p·V^n = const`, n ≈ 1.32
- Combustion/expansion (around TDC): the equation above
- Exhaust (540–720°): `p ≈ p_exhaust`

⚠️ **Turbocharged 914:** intake pressure is boost, not ambient. Our existing thermo model already computes MAP — feed it in rather than recomputing.

**Validation targets** (🔶 if the model does not produce these, it is wrong):
- Peak pressure ~45–60 bar at full load, occurring **10–15° ATDC**
- Peak pressure earlier than 5° ATDC → combustion phased too early
- IMEP ~8–12 bar at full load

---

## 24.6 Torque

**Gas torque** — pressure force through the slider-crank:
```
    F_gas(θ) = (p(θ) − p_crankcase) · A_p
    T_gas(θ) = F_gas(θ) · dx/dθ
```

**Inertial torque** — reciprocating mass being accelerated:
```
    T_inert(θ) = − m_recip · ω² · (d²x/dθ²) · (dx/dθ)
```

⚠️ **Do not omit the inertial term.** It is comparable to gas torque at high RPM and is what makes the ω(θ) waveform realistic. A model with gas torque alone produces an unphysically clean signal, and a misfire detector tuned on it will not transfer.

**Total instantaneous torque**, 4 cylinders phased by firing order 1-4-2-3 at 180° intervals:
```
    T_total(θ) = Σᵢ [ T_gas,i(θ − φᵢ) + T_inert,i(θ − φᵢ) ]
    φ = {cyl1: 0°, cyl4: 180°, cyl2: 360°, cyl3: 540°}
```

🔶 **Boxer note:** in a horizontally-opposed engine, opposing pistons largely cancel *primary* reciprocating forces — which is why a boxer is smooth. The **torque** contributions do not cancel; they are what we measure. Keep the distinction clear.

---

## 24.7 Crank dynamics — producing ω(θ)

**The equation that generates our key signal:**
```
    J · dω/dt = T_total(θ) − T_load(ω)
    dθ/dt = ω
```

`T_load` = propeller load ≈ `k·ω²` through the 2.43:1 reduction, plus accessory drag.

Integrate (RK4 or fine-step Euler) over crank angle. **Output: `ω(θ)` — instantaneous crankshaft angular velocity.**

### What healthy ω(θ) looks like

- Four torque pulses per 720°, one per cylinder, at 180° spacing
- Peak-to-peak fluctuation **~2–5% of mean ω** at cruise (🔶 depends on `J`; tune to match)
- Dominant frequency content at **order 2** (4 firings per 2 revolutions = 2 per revolution)

### What a misfire does — the whole point

A dead cylinder contributes **no gas torque** during its power stroke. ω decelerates through that 180° window instead of accelerating. The deficit appears **in that cylinder's own angular window**, which makes it *directly attributable* — no classifier needed.

✅ This is the established basis of production misfire detection ([SAE 960039](https://saemobilus.sae.org/papers/overview-misfiring-cylinder-engine-diagnostic-techniques-based-crankshaft-angular-velocity-measurements-960039), [2024 crank-angular-velocity study](https://journals.sagepub.com/doi/10.1177/14680874241261419)). Algorithms in [Part XXV](25_misfire_and_combustion_diagnostics.md).

---

## 24.8 From torque to the accelerometer

⬜ To keep [Part XVII §17.5](17_simulation_design.md)'s vibration output but make it *derived*:

```
    a(t) = Σ_k  h_k(t) ∗ F_k(t)     structural transfer of each force path
```

Practical approach at our fidelity: treat each combustion event as an impulse whose **amplitude is proportional to that cylinder's actual peak `dp/dθ`**, convolved with a decaying-sine structural response (exactly the mechanism Part XVII already uses correctly for bearing faults).

🔶 **The gain over the current implementation:** amplitude is no longer a prescribed constant. A weak-burning cylinder automatically produces a weaker impulse; a misfiring one produces none; a detonating one produces a sharp high-frequency spike. All three emerge, none are scripted.

---

## 24.9 Sampling and cost

| Quantity | Resolution | Why |
|---|---|---|
| Cycle integration | 0.5–1.0° CA | Resolves peak pressure phasing |
| `ω(θ)` output | ≥ 1° CA | 🔶 at 5,000 RPM, 1° ≈ 33 µs ⇒ ~30 kHz equivalent |
| Tach/encoder model | 60–2 teeth typical | ⚠️ Real crank sensors give discrete edges, **not** continuous ω. Model the quantisation — our detector must survive it |
| Accelerometer | 2–10 kHz | ✅ matches [Part VI §6.2](06_vibration_analysis.md) requirement |

⚠️ **Model the tach wheel honestly.** A 36-tooth wheel gives 10° resolution, which is *coarse* relative to a 180° power stroke — workable, but it sets the real detection limit. Assuming continuous ω would flatter our results and would not transfer to hardware.

**Cost:** 720 steps/cycle × ~42 cycles/s at 5,000 RPM ≈ 30 k evaluations/s. Trivially vectorisable in NumPy; precompute kinematics once since `x(θ)`, `dx/dθ`, `V(θ)` are θ-only.

---

## 24.10 Validation checklist

🔶 Run these before building anything on top. If any fails, the model is wrong and everything downstream inherits the error.

| # | Check | Expected |
|---|---|---|
| 1 | Order spectrum of healthy ω(θ) | **Order 2 dominant** (4-cyl 4-stroke) |
| 2 | Peak cylinder pressure | 45–60 bar full load, **10–15° ATDC** |
| 3 | IMEP | 8–12 bar full load |
| 4 | Indicated power vs. published | Within ~10% of 100 hp (912 iS) / 115 hp (914) |
| 5 | ω peak-to-peak | 2–5% of mean at cruise |
| 6 | Misfire one cylinder | Clear deficit **in that cylinder's window**; order-0.5 energy rises |
| 7 | Misfire → EGT | That cylinder's EGT **drops** (no combustion), others unchanged |
| 8 | Firing order | Torque pulses appear in sequence **1-4-2-3** |

⚠️ **Check 7 is the cross-domain one and the most valuable.** It proves the combustion layer and the thermal layer are coupled through shared physics rather than being two independent simulators. It is also exactly the corroboration our sensor-validation logic relies on to distinguish a real fault from a drifting sensor.

---

## 24.11 Honest limits

🔶 State these rather than let a panel find them:

- **Single-zone, no heat transfer submodel.** No Woschni correlation; wall heat loss is folded into `η_comb`. Fine for *relative* signatures, not for absolute efficiency prediction.
- **No gas dynamics.** Intake/exhaust tuning, wave action and valve-overlap scavenging are ignored; MAP is imposed rather than computed.
- **Wiebe parameters are assumed, not fitted.** ✅ `a=5, m=2` are standard, but real Rotax burn duration varies with load, speed and mixture. Sensitivity-test `Δθ` and report the range.
- **Torsional crank compliance ignored.** We treat the crank as rigid with lumped inertia `J`. Real cranks have torsional modes; at a 2.43:1 geared prop there is a real drivetrain resonance we do not model.
- **The result is still synthetic.** ⬜ Validate against **NASA ACES** real Rotax 914 telemetry ([dataset](https://data.nasa.gov/dataset/aces-aircraft-and-mechanical-data-v1)) — see [Part XIV](14_datasets.md) and the [audit addendum](../audit/05_expanded_survey.md).

---

*Next: [Part XXV — Misfire and Combustion Diagnostics](25_misfire_and_combustion_diagnostics.md), which consumes `ω(θ)` from this part.*
