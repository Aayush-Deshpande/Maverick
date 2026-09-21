# Part XVII — Realistic Simulation Design

*How to generate synthetic telemetry that is physically honest rather than random numbers with a fault flag.*

---

## 17.1 Why this must be done properly

✅ The PS permits demonstration using "simulated or real engine datasets". Since no suitable real dataset exists ([Part XIV](14_datasets.md)), simulation is our primary data source — which makes its quality the ceiling on everything else.

✅ The team's own breakdown already identifies the failure mode: a dashboard with fake or hardcoded values is "a picture of a dashboard, not a working one", and a simulation that produces the same output regardless of inputs "isn't simulating anything".

**The test a good generator must pass:** if you hand the output to someone who knows engines, without telling them it is synthetic, the *relationships between channels* should look right — even if the absolute values are approximate.

🔶 That is the key insight. Our absolute values will be imperfect because we lack a calibrated performance map. But the *relationships* — CHT rising during climb, oil pressure falling as oil warms, EGT dropping on a misfiring cylinder while vibration half-order energy rises — are what the detection algorithms actually learn from, and those we can get right from physics.

---

## 17.2 Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. MISSION PROFILE          phases, durations, altitude, throttle   │
└───────────────────────────┬──────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  2. ENVIRONMENT MODEL        ISA + deviation → p, T, ρ at altitude   │
└───────────────────────────┬──────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  3. ENGINE PHYSICS (healthy) power, heat balance, thermal ODEs,      │
│                              oil, fuel flow, base vibration          │
└───────────────────────────┬──────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  4. DEGRADATION MODEL        slow parameter drift over hours         │
└───────────────────────────┬──────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  5. FAULT INJECTION          modifies PHYSICS PARAMETERS,            │
│                              never the output signals directly ★     │
└───────────────────────────┬──────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  6. SENSOR MODEL             noise, quantisation, lag, drift, faults │
└───────────────────────────┬──────────────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│  7. TRANSPORT MODEL          CAN framing, link loss, latency         │
└──────────────────────────────────────────────────────────────────────┘
```

**Stage 5 carries the most important rule in this part:**

> **Faults must modify physical parameters, not output signals.**

Wrong: `if fault: cht_2 += 30`
Right: `if fault: cooling_effectiveness[2] *= 0.6`

🔶 Why this matters enormously: if you add 30 °C to a channel, nothing else changes, and any detector that looks at cross-sensor consistency will see an *inconsistent* pattern — which is the signature of a **sensor** fault, not an engine fault. Your classifier then learns to detect "someone added a constant", which is not a skill that transfers to reality. If instead you degrade cooling effectiveness, the physics propagates it: CHT rises, the thermal ODE gives it the right time constant, oil temperature follows, and the correlation structure is automatically correct.

**This single design choice determines whether the synthetic data teaches anything real.**

---

## 17.3 Environment model

⬜ Standard atmosphere with deviations:

```python
def atmosphere(alt_ft: float, isa_dev_c: float = 0.0) -> Environment:
    alt_m = alt_ft * 0.3048
    T_isa = 288.15 - 0.0065 * alt_m            # K, troposphere
    T = T_isa + isa_dev_c
    p = 101325 * (T_isa / 288.15) ** 5.2561    # Pa
    rho = p / (287.05 * T)                      # kg/m³
    return Environment(T_k=T, p_pa=p, rho=rho,
                       density_alt_ft=density_altitude(p, T))
```

⬜ Presets for the demo scenarios in [Part XI §11.8](11_mission_simulation.md):

| Preset | Altitude | ISA deviation | Character |
|---|---|---|---|
| `LADAKH_HIGH_COLD` | 25,000 ft | −15 °C | High, very cold — large cooling margin |
| `THAR_HOT` | 15,000 ft | +25 °C | Hot — **small thermal margin** |
| `COASTAL_STANDARD` | 10,000 ft | 0 °C | Reference condition |
| `MONSOON_HUMID` | 12,000 ft | +10 °C, high humidity | Reduced charge density |

---

## 17.4 Engine physics

⬜ The healthy model, following [Part X §10.4](10_digital_twin.md):

```python
def engine_step(state, inputs, env, params, dt):
    # --- Air charge and power -------------------------------------------
    map_kpa   = inputs.throttle * params.map_max * (env.rho / RHO_SL)
    m_dot_air = params.displacement * inputs.rpm / 120 * env.rho * params.ve
    m_dot_fuel = m_dot_air / params.afr

    power = m_dot_fuel * LHV * params.eta_thermal

    # --- Heat balance, per cylinder -------------------------------------
    for i in range(params.n_cyl):
        q_gen = (m_dot_fuel / params.n_cyl) * LHV * (1 - params.eta_thermal)

        # Cooling depends on airflow (airspeed AND density) and ΔT
        h = params.h_base * (inputs.ias / params.ias_ref) ** 0.8 * (env.rho / RHO_SL)
        q_rej = h * params.area * (state.cht[i] - env.T_k) * params.cool_eff[i]

        # First-order thermal dynamics — this gives the correct LAG
        state.cht[i] += (q_gen - q_rej) / (params.mass_head * params.cp) * dt

        # EGT tracks combustion, faster than CHT
        egt_target = params.egt_base * combustion_quality[i] * charge_factor
        state.egt[i] += (egt_target - state.egt[i]) / params.tau_egt * dt

    # --- Oil -------------------------------------------------------------
    state.oil_temp += (heat_to_oil - oil_cooling) / params.oil_thermal_mass * dt
    viscosity = params.visc_ref * exp(params.visc_b * (1/state.oil_temp - 1/T_ref))
    state.oil_press = params.pump_gain * inputs.rpm * viscosity * params.clearance_factor
```

**Three physical behaviours this produces automatically**, which a naive generator would miss:

1. **Thermal lag.** CHT cannot jump, because it is integrated through thermal mass. This is what makes rate-of-change sensor validation ([Part VII §7.5](07_anomaly_detection.md)) meaningful rather than arbitrary.
2. **Altitude coupling.** `env.rho` appears in both power and cooling, so climb behaviour emerges rather than being scripted.
3. **Oil pressure depends on RPM *and* temperature** through viscosity, which is exactly the confound described in [Part II §2.4](02_engine_sensors.md) — and exactly what makes raw oil pressure a poor fault indicator and its residual a good one.

---

## 17.5 Vibration synthesis

⬜ The base signal is a sum of order components plus noise:

```python
def vibration_window(rpm, params, faults, n=2048, fs=10000):
    t = np.arange(n) / fs
    f_shaft = rpm / 60
    x = np.zeros(n)

    # Order components — see Part VI §6.5
    for order, amp in params.base_orders.items():        # {0.5:…, 1:…, 2:…, 4:…}
        x += amp * np.sin(2*np.pi * order * f_shaft * t + params.phase[order])

    # Gear mesh plus sidebands
    gmf = params.gear_teeth * f_shaft
    x += params.gmf_amp * np.sin(2*np.pi*gmf*t)
    for sb in (-1, 1):
        x += params.sb_amp * np.sin(2*np.pi*(gmf + sb*f_shaft)*t)

    # Bearing defect: impulses at BPFO exciting a structural resonance
    if faults.bearing_severity > 0:
        for t_imp in np.arange(0, n/fs, 1/ (params.bpfo_order * f_shaft)):
            x += faults.bearing_severity * decaying_sine(
                    t - t_imp, f_res=params.resonance_hz, damping=params.zeta)

    # Combustion impulses, locked to firing events
    x += combustion_impulses(t, f_shaft, params.n_cyl, faults.misfire_cyl)

    return x + np.random.normal(0, params.noise_floor, n)
```

**Why the bearing fault is modelled as decaying sines rather than added noise:** that is the actual physics ([Part VI §6.8](06_vibration_analysis.md)) — impacts excite a resonance which rings down. Modelling it correctly means **envelope analysis genuinely works on our synthetic data**, which in turn means our envelope pipeline is being tested rather than merely executed. If we modelled it as broadband noise, envelope analysis would find nothing, and we would wrongly conclude our implementation was broken.

---

## 17.6 The eight fault models

⬜ Each modifies parameters, with a realistic onset profile:

| # | Fault | Parameter modified | Onset | Emergent signature |
|---|---|---|---|---|
| 1 | **Misfire** | `combustion_quality[i]` → intermittent 0 | Sudden or intermittent | EGT[i]↓, 0.5-order vibration↑↑, RPM roughness↑ |
| 2 | **Injector** | `fuel_split[i]` reduced | Gradual over hours | EGT[i] deviates, fuel-flow residual, commanded≠achieved |
| 3 | **Cooling degradation** | `cool_eff[all]` ×0.98/hour | Slow, gradual | All CHT residuals rise together; worse at altitude |
| 4 | **Lubrication** | `clearance_factor`↑, `pump_gain`↓ | Very slow | Oil pressure residual↓ at matched RPM/temp; oil temp↑ |
| 5 | **Sensor drift** | Added to the **sensor model**, not physics | Slow ramp or step | **Uncorrelated** with neighbours — that is the tell |
| 6 | **Combustion instability** | `combustion_quality` variance↑ | Gradual | EGT cycle-to-cycle variance↑, irregular vibration |
| 7 | **Overheating trend** | `cool_eff`↓ **while still within limits** | Very slow | CHT trending up inside the legal band ★ |
| 8 | **Bearing/vibration** | `bearing_severity`↑ | Gradual | Envelope line at BPFO, kurtosis↑, RMS↑ late |

**Fault 5 is deliberately different.** It is injected into the *sensor model*, not the physics — because that is what a sensor fault physically is. This is what makes fault 5 separable from the others: the physics never changed, so neighbouring channels are unaffected, and the cross-sensor correlation test ([Part VII §7.5](07_anomaly_detection.md)) fires correctly. Injecting it into physics would make it indistinguishable from a real fault, and our sensor-validation layer would be untestable.

**Fault 7 is the PS's core ask**, and it must be generated carefully: a degradation that never exceeds a limit within the sortie, so that only trend detection can catch it. If our generator lets it exceed a threshold, we are testing a threshold system, not a predictive one.

---

## 17.7 Degradation and run-to-failure

⬜ For RUL development we need full trajectories:

```python
def degrade(params, hours, profile):
    """Slow parameter drift. Separate from fault injection."""
    # Wear accelerates with cumulative thermal and mechanical stress
    stress = profile.thermal_load_integral + profile.mechanical_load_integral

    params.cool_eff      *= (1 - 0.001 * hours * stress_factor)
    params.clearance_factor *= (1 + 0.0008 * hours * stress_factor)
    params.bearing_severity += 0.0005 * hours ** 1.3   # accelerating
    params.eta_thermal   *= (1 - 0.0003 * hours)
    return params
```

🔶 Design notes worth being deliberate about:
- **Accelerating degradation** (the `** 1.3` exponent) is more realistic than linear, and it is what makes trend extrapolation genuinely challenging rather than trivial. A purely linear degradation makes linear extrapolation perfect, which would flatter our RUL results dishonestly.
- **Stress-dependent wear** means mission profile affects life — which enables a genuinely interesting demo: two identical engines, different mission profiles, different RUL.
- **Degradation is separate from fault injection.** Degradation is normal ageing; faults are discrete events. Both can be present.

---

## 17.8 Sensor model

⬜ The physics output is *truth*. The sensor model makes it realistic:

```python
def sense(true_value, sensor_params, t):
    x = true_value
    x = x + first_order_lag(x, sensor_params.tau, t)      # probe thermal lag
    x = x + np.random.normal(0, sensor_params.noise_std)  # analog ripple
    x = x + sensor_params.drift_rate * t                  # slow drift
    x = x + sensor_params.offset                          # calibration error
    x = quantise(x, sensor_params.lsb)                    # ADC resolution

    if sensor_params.failed:
        return sensor_params.fail_value    # railed / frozen / zero
    return x
```

⬜ Per-sensor realism, from [Part II](02_engine_sensors.md):

| Sensor | Noise | Lag | Failure mode |
|---|---|---|---|
| Thermocouple (EGT) | ±0.5 °C | ~1 s (probe mass) | Open circuit → rails |
| RTD (CHT/oil) | ±0.2 °C | ~2 s | Short → reads low |
| Pressure (4–20 mA) | ±0.02 bar | ~50 ms | ✅ 0 mA = broken wire, distinguishable from zero |
| RPM pulse | ±5 RPM | ~50 ms | Dropout → reads 0 |
| Accelerometer | broadband floor | negligible | Mount loosening → spectrum changes |

**The ±0.2 °C analog ripple matters more than it looks.** ✅ Real aviation transducers have natural ripple, and a perfectly flat reading indicates a frozen ADC buffer. If our synthetic data has zero noise, our noise-floor validation check ([Part VII §7.5](07_anomaly_detection.md)) can never be tested — and worse, our models will be trained on impossibly clean data and will fail on anything real.

---

## 17.9 Validating the generator

⬜ A generator that is wrong produces a system that is confidently wrong. Checks before trusting it:

| Check | Test | Why |
|---|---|---|
| **Steady-state plausibility** | Cruise values within published operating ranges | ✅ Compare against Rotax operator's manual figures |
| **Altitude response** | Climb → correct direction and rough magnitude | Physics sanity |
| **Thermal time constants** | Step throttle → CHT settles over tens of seconds | Lag must be realistic, not instant |
| **Correlation structure** | Healthy CHT/EGT/oil correlations resemble real engines | 🔶 The hardest to verify without real data — state as a limitation |
| **Residuals near zero** | Our own physics model on healthy synthetic data | If not, either model or generator is wrong |
| **Fault signatures emerge** | Each injected fault produces its table-row signature *without being told to* | Confirms parameters propagate |
| **Spectral content** | Order spectrum has the right lines at the right orders | Validates the vibration synthesis |
| **Envelope analysis works** | Injected bearing fault is detectable via envelope FFT | Validates both signal and pipeline |

🔶 The correlation-structure row is the honest weak point. Without real engine data we cannot confirm that our inter-channel correlations match reality, and those correlations are exactly what multivariate detectors learn. **This should be stated as a known limitation**, not quietly assumed away.

---

## 17.10 Avoiding the leakage trap

⚠️ The central danger, restated from [Part XIV §14.6](14_datasets.md): **if the same generator with the same parameters produces training and test data, the evaluation measures the model's ability to invert our simulator.**

⬜ Mitigations, in increasing strength:

1. **Different parameters for test** — different degradation rates, noise levels, environments, mission profiles
2. **Held-out "airframes"** — simulated engines with different baseline characteristics (different `cool_eff`, `h_base`, wear history)
3. **Unseen corruptions in test** — dropouts, drift, and packet loss patterns absent from training
4. **Unseen fault severities and onset rates**
5. **Cross-validation on public proxies** — ✅ the strongest defence: report C-MAPSS RUL numbers and Paderborn vibration numbers alongside our synthetic results

⬜ **How to report it honestly:**

> "Fault classification: 0.89 macro F1 on held-out simulated airframes with unseen degradation rates. This is synthetic data generated by our own physics model, so it validates the pipeline rather than field accuracy. The same methods achieve [X] on C-MAPSS and [Y] on the Paderborn bearing dataset, which are independent public benchmarks."

That sentence is worth more to a knowledgeable evaluator than an unqualified 99%.

---

## 17.11 Scenario library

⬜ Pre-built scenarios for development, testing and demonstration:

| Scenario | Duration | Environment | Fault | Purpose |
|---|---|---|---|---|
| `NOMINAL_CRUISE` | 2 h | Standard | None | Baseline, false-alarm rate measurement |
| `FULL_SORTIE` | 18 h | Standard | None | Endurance, drift and trend behaviour |
| `LADAKH_COOLING_DEGRADE` | 6 h | High, cold | Cooling, slow | Trend detection with large margin |
| `THAR_COOLING_DEGRADE` | 6 h | Hot | **Identical fault** | ★ Same fault, different verdict — the paired demo |
| `MISFIRE_ONSET` | 3 h | Standard | Misfire at T+2 h | Vibration-based detection, latency |
| `BEARING_RUN_TO_FAILURE` | 40 h | Standard | Bearing, progressive | RUL development |
| `OIL_DEGRADATION` | 8 h | Standard | Lubrication | Multi-sensor correlation |
| `SENSOR_DRIFT` | 4 h | Standard | CHT₂ drift | ★ Must NOT be classed as an engine fault |
| `LINK_LOSS` | 4 h | Standard | Cooling + 20-min outage | ★ Edge autonomy demonstration |
| `THROTTLE_TRANSIENTS` | 1 h | Standard | None | Transients must not trigger false alarms |

The three starred scenarios are the ones that best demonstrate the architecture rather than merely the models — a paired environment comparison, correct sensor-fault rejection, and edge autonomy under link loss.

---

**Next:** [Part XVIII — Implementation Roadmap](18_roadmap.md)
