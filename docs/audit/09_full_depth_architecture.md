# 09 — ANUMAAN at Full Depth: Engine-Cycle Intelligence

*Companion to [`08_deployable_system_blueprint.md`](08_deployable_system_blueprint.md). Doc 08 is about honesty and integration: making what exists into one trustworthy system. **This document is the full technical ambition.** It describes what the system becomes when every layer is built at the depth the physics allows, not at the depth a hackathon usually reaches.*

**Written 23 September 2026.** Evidence labels as in the rest of `docs/`: ✅ verified from a source, 🔶 engineering judgement or derived calculation, ⬜ proposal. All numbers in §2 and §9 come from a calculation that is reproduced inline, so they can be checked.

**Reference engine.** This document targets the **VRDE-class 2.2 L inline-4 turbocharged CRDi with FADEC**, which is the indigenous TAPAS BH-201 engine ✅ (see [08 §0](08_deployable_system_blueprint.md)). Its internal data (bore, rpm limits, injector type, FADEC functions) is not public, so values marked 🔶 are assumptions (bore 85 mm, 4,000 rpm maximum) that VRDE would replace. The Rotax 914 appears alongside for comparison.

---

## 0. The idea in one page

**Everyone in this field monitors symptoms.** They sample eight slow averages (CHT, EGT, oil pressure…) at 1–50 Hz, compare them to a threshold or feed them to a classifier, and alarm when the average moves.

**This system measures the process that produces the symptoms.** At 4,000 rpm a four-cylinder four-stroke completes **33 combustion cycles per second: 133 individual combustion events**. The system resolves each one: when it started, how much work it did, how hard it burned, how the injector opened and closed, and what the crankshaft, gearbox and bearings did while it happened. Every second it updates a Bayesian estimate of the physical health of **this particular engine**: per-cylinder injector delivery, compression, cooling effectiveness, turbocharger efficiency, and bearing and gear condition. When the evidence is ambiguous, it asks the engine a question by requesting a diagnostic test from the FADEC. It knows when it is wrong.

### The seven principles everything below follows

| # | Principle | Consequence |
|---|---|---|
| 1 | **Measure the process, not the symptom** | Move left on the P-F curve (§1): combustion and vibration first, temperature last |
| 2 | **The engine cycle is the unit of analysis** | Work in the crank-angle domain, not in clock time. One cycle is one observation. |
| 3 | **The engine is its own reference** | Four cylinders share the same altitude, load, fuel and air *at the same moment*, so common-mode effects cancel. A cylinder that differs from its three peers is a fault, not an operating condition. |
| 4 | **The FADEC hides faults. Watch its effort.** | A CRDi FADEC balances cylinders and learns injector drift ✅, so it compensates the very faults we want to see. The size of that compensation is the earliest health signal. |
| 5 | **The twin is an estimator of *this* engine** | A hierarchical Bayesian model at three time scales (cycle, second, flight). Health is estimated physical parameters with uncertainty, not a class label. |
| 6 | **Labels are rare; cycles are abundant** | About 120,000 cycles per engine-hour. Self-supervised learning and physics priors do the work; supervised classifiers are only one source of evidence. |
| 7 | **Interrogate, don't just listen** | When hypotheses are ambiguous, the twin selects the diagnostic test with the highest expected information gain (cylinder cut-out, rail-pressure step…) and requests it. |

---

## 1. Where the information physically lives

### 1.1 The P-F curve: why the field is late

Reliability-centred maintenance describes every developing failure with a **P-F curve**. P is the point where a potential failure first becomes detectable, and F is the functional failure. Different evidence appears at different points along it:

```
condition
  │ P
  │  ●─────── (1) combustion/injection signatures: SOC shift, per-cylinder work, FADEC trim growth
  │   ╲────── (2) angle-resolved vibration: impacts, resonance excitation, envelope, gear sidebands
  │     ╲──── (3) oil debris / wear-metal fingerprint
  │       ╲── (4) performance: power margin, fuel flow, boost
  │         ╲ (5) temperature: EGT, CHT, oil T        ◄── where the field operates
  │          ╲(6) noise, smoke, audible change
  │           ●F  functional failure
  └───────────────────────────────────────────────── time
```

🔶 Every competitor we analysed operates at stages 4–5. Our own evaluation harness has already demonstrated this ([`detection_report.md`](../evaluation/detection_report.md)): **thermal residuals missed injector coking entirely; the crank channel caught it and named cylinder 2.** That result is the P-F curve, measured.

### 1.2 The information map

For each fault family: where its information first appears, and what it takes to capture it. This table *derives the sensor suite* rather than assuming it.

| Fault family (CRDi turbo-diesel) | Earliest physical evidence | Domain | Channel | Rate needed |
|---|---|---|---|---|
| Injector nozzle coking / internal deposits | Per-cylinder delivery ↓ → **FADEC balancing trim ↑** → work deficit per cylinder | Control effort + angle | FADEC CAN (trims), crank tooth timing | Trims ~1–10 Hz; teeth per edge |
| Needle sticking / leakage | Altered needle-opening and closing impacts; post-injection dribble → late burn | Angle-windowed high frequency | Head accelerometer; rail-pressure wave | ≥ 51.2 kHz accel; rail ≥ 30 kHz |
| Injection timing drift | **Start of combustion (SOC) moves** relative to commanded start of injection (SOI) | Angle | Virtual cylinder pressure (§4.3); rail-pressure drop timing | 51.2 kHz + crank edges |
| Rail-pressure decay / pump wear | Rail-pressure ripple and recovery after each injection; pressure-control-valve duty | Time, per injection | Rail-pressure sensor; FADEC duty | ≥ 30 kHz ✅ |
| Compression loss (rings, valves) | Compression-stroke deceleration per cylinder; longer ignition delay | Angle | Crank edges (especially during start and shutdown) | Per edge |
| Misfire / combustion instability | Missing or variable work per cylinder per cycle; order 0.5 | Angle | Crank edges | Per edge |
| Harsh combustion / "diesel knock" | Chamber acoustic resonance excited by dp/dθ | Time (resonance), angle-windowed | Block/head accelerometer | **5–20 kHz content → 51.2 kHz** (§2.2) |
| Valve train (clearance, seat wear) | Seating-impact timing and energy in each valve's angle window | Angle-windowed high frequency | Head accelerometer | 51.2 kHz |
| Gearbox (PSRU) wear | Mesh-order sidebands; FM4/NA4 condition indicators | Angle (gear TSA) | Gearbox accelerometer + prop-shaft speed | 51.2 kHz |
| Rolling bearings | Impact-modulated resonance → envelope order spectrum | Angle-time cyclostationary | Accelerometers | 51.2 kHz (carriers of 3–20 kHz) |
| Torsional coupling / damper | Crank-to-propeller twist at torsional orders | Angle, two shafts | Crank edges + prop-shaft edges | Per edge |
| Turbocharger bearing / imbalance / surge | Synchronous and sub-synchronous (whirl) vibration; MAP oscillation | Time | Turbo accelerometer, turbo speed, MAP | 102.4 kHz, or a speed sensor |
| Cooling degradation | Per-cylinder heat-rejection parameter drift | Slow thermal | CHT/coolant/EGT | 1–10 Hz |
| Lubrication / wear | Oil pressure–temperature–speed relation; debris count; Fe/Al/Cu/Cr/Si | Slow + chemical | Oil P/T, inductive debris sensor, SOAP lab results | 1 Hz + events |
| Fuel waxing / cold soak (Jet-A1 at altitude) | **Ignition delay ↑ on *all* cylinders** (common mode); filter ΔP | Angle + slow | SOC − SOI; fuel temperature | Per cycle |
| Sensor failure / spoofing | Physical inconsistency across channels; IEPE bias shift | Cross-channel | All | — |

🔶 **Two consequences follow.** First, the richest diagnostic domains are *control effort* and *angle-resolved high-frequency vibration*, and nobody else is using either. Second, the fuel-waxing row shows what physics buys you: a single measured quantity, ignition delay, separates a fuel problem (all cylinders together) from a compression problem (one cylinder) with no classifier involved.

---

## 2. The frequency plan: the 20 kHz answer

> **Correction to earlier docs.** [`study/02`](../study/02_engine_sensors.md), [`06`](../study/06_vibration_analysis.md), [`24`](../study/24_combustion_cycle_and_crank_dynamics.md), [`26`](../study/26_order_tracking_and_envelope.md) and [`proposal.md`](../study/proposal.md) specify vibration at **2–10 kHz**. That covers orders, firing harmonics and gear-mesh fundamentals. It is **too low** for combustion resonance, injector and valve impacts, and bearing envelope carriers. The requirement is **≥ 20 kHz of usable bandwidth, meaning 51.2 kHz sampling** for block and head accelerometers. The derivation follows.

### 2.1 Engine event rates (🔶 computed)

| Quantity | CI at 3,000 rpm (cruise) | CI at 4,000 rpm (🔶 max) | Rotax 914 at 5,800 rpm |
|---|---|---|---|
| Cycle frequency (order 0.5) | 25.0 Hz | 33.3 Hz | 48.3 Hz |
| Firing frequency (order 2) | 100 Hz | 133 Hz | 193 Hz |
| Cycle duration (720°) | 40.0 ms | 30.0 ms | 20.7 ms |
| Tooth rate, 60-2 wheel | 2,900 /s | 3,867 /s | 5,607 /s |
| Tooth period | 333 µs | 250 µs | 172 µs |
| 1° crank angle | 55.6 µs | 41.7 µs | 28.7 µs |
| 0.1° CA pressure sampling (test cell) | 180 kHz | 240 kHz | 348 kHz |

### 2.2 Combustion-chamber acoustic resonance: why 20 kHz

The rapid pressure rise of combustion (premixed diesel combustion, or knock in SI engines) excites the gas in the cylinder into acoustic standing waves. **Draper's relation** gives their frequencies:

```
f(m,n) = c · α(m,n) / (π · B)          c = √(γ R T) of burned gas,  B = bore
α: (1,0)=1.841  (2,0)=3.054  (0,1)=3.832  (3,0)=4.201  (4,0)=5.318  (1,1)=5.331   (Bessel J′ zeros)
```

| Bore | Gas temperature | (1,0) | (2,0) | (0,1) | (3,0) | (1,1) |
|---|---|---|---|---|---|---|
| 85 mm (🔶 CI assumed) | 1,800–2,600 K | 5.6–6.8 kHz | 9.4–11.3 | 11.8–14.1 | 12.9–15.5 | **16.4–19.7 kHz** |
| 83 mm (OM640/AE300) | 1,800–2,600 K | 5.8–7.0 | 9.6–11.5 | 12.0–14.5 | 13.2–15.9 | **16.8–20.1** |
| 79.5 mm (Rotax 914) | 1,800–2,600 K | 6.0–7.3 | 10.0–12.0 | 12.6–15.1 | 13.8–16.6 | **17.5–21.0** |

**The diagnostically useful combustion band runs from about 5.6 to about 20 kHz.** Standard analyser practice sets the sampling rate at 2.56 × the maximum frequency for anti-alias filter roll-off, so **2.56 × 20 kHz = 51.2 kHz.** That is where the "20 kHz" figure comes from.

🔶 Caveats that don't change the conclusion. Draper assumes a flat cylindrical chamber, and a bowl-in-piston diesel shifts the modes. The engine structure attenuates high frequencies on the way to the accelerometer. The accelerometer's mounted resonance must sit well above 20 kHz, which means a stud mount rather than a magnet or adhesive.

### 2.3 Full sampling plan

| Channel | Physics it must capture | Sampling | Resolution | Notes |
|---|---|---|---|---|
| **Crank tooth edges** | ω(θ), per-cylinder work | **Edge timestamps**, not samples | Timer ≤ 25 ns (40 MHz+) | At 4,000 rpm a 250 µs tooth measured at 25 ns gives 1 × 10⁻⁴ speed resolution per tooth |
| Cam phase | Cycle phase (which revolution) | Edge | — | Resolves the 720° ambiguity |
| **Prop-shaft edges** (🔶 new) | Torsional twist, coupling health | Edge | ≤ 25 ns | Twist from the phase difference against the crank |
| **Block accelerometers ×2** (triaxial) | Combustion resonance, impacts, bearings | **51.2 kHz** | 24-bit ΣΔ, simultaneous | Stud-mounted near cylinders 1–2 and 3–4 |
| **Head accelerometer** | Injector needle and valve impacts | **51.2 kHz** | 24-bit | Hot location; needs a 150 °C-rated sensor |
| **Gearbox accelerometer** | Mesh orders and sidebands | 51.2 kHz | 24-bit | — |
| Turbo accelerometer | Sync, whirl, blade pass | **102.4 kHz** | 24-bit | 🔶 Compressor blade pass ≈ 20–50 kHz. Alternatively an eddy-current speed sensor gives blade pulses directly. |
| **Rail pressure** | Per-injection pressure wave | **≥ 30 kHz** (✅ ≥ 10 kHz minimum, ~30 kHz preferred for injection duration; research uses 250 kHz) | 16-bit | From the FADEC's own sensor, exposed by the FADEC |
| Injector drive current (optional) | Armature/needle motion signature | 250 kHz–1 MHz | 12–16-bit | Only if the FADEC exposes it |
| FADEC CAN | Trims, commanded SOI/quantity, MAP, boost, temperatures | 10–100 Hz | — | Includes **cylinder-balancing corrections and drift adaptations** |
| CHT/EGT per cylinder, oil P/T, fuel T/flow | Thermal and fluid state | 10 Hz | — | — |
| Oil debris (inductive) | Ferrous/non-ferrous particle count and size | Event | — | — |
| **Test-cell only:** in-cylinder pressure | Ground truth for combustion | Encoder-triggered at 0.1–0.2° CA | 16-bit | Calibrates the virtual pressure sensor (§4.3) |

### 2.4 Data volume, and why onboard processing is mandatory

🔶 Computed for eight channels at 51.2 kHz, one at 102.4 kHz, crank edges and CAN, all at 24 bits:

| Quantity | Value |
|---|---|
| Raw rate | **12.6 Mbit/s** (1.58 MB/s) |
| Spare datalink capacity ([`edge/compressor.py`](../../backend/edge/compressor.py)) | ~22 kbit/s |
| Raw ÷ link | **573× over budget. It cannot be downlinked.** |
| One 18 h sortie, fully raw | **~102 GB** |

**That last row changes the architecture.** 102 GB fits on a 256 GB industrial SSD, so the aircraft can record **the entire sortie at full fidelity**, like a HUMS "black box", while downlinking only a ~0.2–2 kbit/s health stream. After landing, the raw record transfers over Gigabit Ethernet in about 15 minutes, and the ground re-runs every analysis at full depth. Live monitoring and forensic depth stop being a trade-off.

---

## 3. Acquisition hardware architecture

```
 ENGINE BAY                                   ENGINE HEALTH UNIT (EHU)                         AVIONICS
 ──────────                                   ────────────────────────                         ────────
 accel ×4 (IEPE) ──► IEPE 4 mA + AA filter ──► 24-bit ΣΔ ADC, simultaneous ──┐
 turbo accel ──────► IEPE + AA ─────────────► 24-bit ADC @102.4k ────────────┤
 crank / cam / prop pickups ─► conditioning ─► timer-capture (≤25 ns) ────────┼─► FPGA/MCU front end ──► SoC (DSP + estimators + NN)
 rail P (from FADEC) ─► buffered ───────────► 16-bit ADC ≥30k ───────────────┤     • common clock          • per-cycle analysis
 debris sensor ────────────────────────────► digital I/O ────────────────────┘     • angle-tagging         • 1 Hz health frame ─► MAVLink ─► datalink
 FADEC ───────────── CAN (trims, commands, temps) ──────────────────────────────────────────────────────► • event snippets
                                                                                                           • full raw ─► SSD (256 GB)
```

**Design rules**

- **One clock.** Every sample and every tooth edge is timestamped against the same clock, so each vibration sample has an exact crank angle. Angle-tagging in the front end is what makes angle-domain processing exact rather than interpolated.
- **Simultaneous sampling** across accelerometer channels, because the analysis compares phases between them.
- **Self-test.** Monitor each IEPE channel's bias voltage (open, short, cable fault), and inject a known test signal at power-up. A sensor must be able to report its own failure; this is how "sensor failure" (a PS fault target) is handled at the hardware level.
- **Partitioning.** The FPGA/MCU front end is deterministic and certifiable. The SoC runs analysis and learned models. Everything is advisory: nothing on the EHU writes to the FADEC except *requests* for ground diagnostic tests, which the FADEC is free to refuse.
- **Environment.** Rated for engine-bay temperature and vibration, with DO-160-class environmental qualification on the roadmap.
- 🔶 **FADEC access is the critical dependency.** Trims, rail pressure and commanded SOI must be exposed by the FADEC. In India this is unusually feasible, because **VRDE designs both the engine and the integration**, so the requirement goes into their FADEC ICD rather than being reverse-engineered.

---

## 4. Signal intelligence: the per-cycle DSP core

Every engine cycle (30 ms at 4,000 rpm) produces a **Cycle Health Vector** (§4.7). Six channels feed it.

### 4.1 Crank channel: per-cylinder work, compression and torsion

1. **Tooth-period capture** → raw ω per tooth.
2. **Wheel-error learning.** Real trigger wheels have tooth-spacing errors that look exactly like combustion non-uniformity. Learn a per-tooth correction during motored or low-load periods. This is standard OBD misfire-monitor practice, and without it every result is contaminated.
3. **Inverse crankshaft dynamics** gives gas torque:

```
T_gas(θ) = J_eq(θ)·ω·dω/dθ + ½·J_eq′(θ)·ω²  −  T_inertia(θ, ω)  +  T_friction(θ, ω)  +  T_load(ω)
```
   Here `J_eq(θ)` includes the reciprocating mass. `T_inertia` comes from the slider-crank kinematics already in [`crank_dynamics.py`](../../backend/physics/crank_dynamics.py). `T_load` is the propeller, calibrated through the gearbox.

4. **Per-cylinder pressure deconvolution.** Gas torque is a sum over cylinders:

```
T_gas(θ) = Σᵢ  A_p · (dx/dθ)(θ − φᵢ) · pᵢ(θ − φᵢ)
```
   Each `pᵢ` is parametrised as motored pressure plus a small combustion model (§5.2). A regularised least-squares fit over the cycle gives, per cylinder, the **indicated work (IMEP), compression health and combustion phasing**. This resolves the overlap between one cylinder's power stroke and the next one's compression, which simple windowing gets wrong.

5. **Free tests the engine performs every day.**
   - **Engine start (cranking, before fuel):** per-cylinder compression-stroke deceleration is a *relative compression test* on every start.
   - **Shutdown run-down:** the last revolutions after the fuel is cut are motored, so they give friction and compression per cylinder.

   🔶 Every sortie therefore includes two controlled diagnostic experiments at no cost.

6. **Torsional channel.** The phase difference between the crank and prop-shaft wheels gives dynamic twist. Its amplitude at the torsional-resonance orders tracks coupling and damper health, a known weak point of geared aero-diesel installations.

### 4.2 Angle-domain vibration

1. **Computed order tracking.** Resample to angle using the angle-tags, at 1,536 samples per cycle (0.47°). That is the honest limit, because 51.2 kHz at 4,000 rpm gives 768 samples per revolution ([`study/26`](../study/26_order_tracking_and_envelope.md) rule).
2. **Time-synchronous average (TSA) per cycle** gives the *deterministic* part: combustion and valve events, which repeat every cycle. The **TSA residual** is the *random* part: bearing impacts that slip, and cycle-to-cycle combustion variability.
3. **Angle-window features.** For each cylinder, fixed crank-angle windows around physical events:

| Window (relative to that cylinder's TDC) | Physical event | Features |
|---|---|---|
| −25° … −5° | Pilot/main injection, needle opening | Band energy 8–20 kHz, peak time, kurtosis |
| −5° … +20° | Start of combustion, pressure rise | Draper-band energy (5.6–20 kHz), onset angle |
| +20° … +60° | Diffusion combustion, needle closing | Energy, late-burn indicator |
| Exhaust valve opening / intake valve closing (from valve timing) | Valve events | Seating-impact energy and angle; clearance drift shows up as a timing shift |

   **Peer referencing (principle 3).** Each feature is expressed relative to the median of the other cylinders in the same cycle. Operating condition cancels, and a cylinder-specific fault stands out.

4. **Order spectrum** at 0.5-order resolution to order 40, with sidebands. This is the input FlyHash is designed for (§6.3).
5. **Order-frequency spectral correlation (OFSC).** For angle-time cyclostationary signals, carriers are time-invariant resonances (Hz) while modulations are angle-periodic (orders):

```
S_x(α, f) ≈ E{ X_w(f + α/2) · X_w*(f − α/2) }     α in cyclic orders, f in Hz
```
   ✅ This jointly decodes the angle-dependent modulations (kinematics) and time-dependent carriers (dynamics). It has been applied to diesel malfunctions in firing conditions: injection advance and delay, misfires and knock. Use the fast estimator (cyclic modulation spectrum). Indicators are the energy at the cylinder's cyclic orders inside the Draper band, per cylinder.
6. **Bearings.** Spectral kurtosis (fast kurtogram) finds the most impulsive band → envelope → **envelope order spectrum** → BPFO, BPFI, BSF and FTF indices, which are speed-invariant because they are expressed in orders.
7. **Gearbox (PSRU).** Gear TSA on the prop-shaft reference → regular and residual signals → the standard HUMS condition indicators **FM0, FM4, NA4, NB4** and the sideband index, the same family rotorcraft HUMS use.

### 4.3 Virtual cylinder pressure: the flagship signal

A pressure transducer in every cylinder is impractical in flight. ✅ Reconstructing cylinder pressure from block vibration and crank speed is an established research line: inverse filtering with frequency-response functions (Randall et al.), time-domain smoothing (Gao & Randall), RBF networks, and, more recently, sensor fusion of vibration with flywheel speed.

🔶 **Our design is complementary fusion**, in the same spirit as a complementary filter for attitude:

- **Crank speed** carries the low-frequency content (up to about 20 orders) accurately: work, IMEP, peak location. It is poor at sharp detail.
- **Vibration**, through an inverse structural FRF, carries the high-frequency content: dp/dθ, start of combustion, resonance. Its absolute level is poor because the transfer path drifts.
- **Fused estimate:** p̂ᵢ(θ) = LowPass[crank inverse] + HighPass[vibration inverse], with the crossover and FRF **calibrated on the test cell** against real pressure transducers, then re-calibrated per tail.

**Outputs per cylinder per cycle:**

- **SOC** (start of combustion)
- **CA10/CA50/CA90** (angles at which 10/50/90 % of the fuel has burned)
- p_max and its angle
- max dp/dθ (combustion harshness)
- IMEP
- **Ignition delay = SOC − SOI**, with SOI from rail-pressure-drop timing or the FADEC command
- Resonance index (Draper band)

🔶 Ignition delay is an unusually powerful quantity. Rising on *all* cylinders means cold fuel, low cetane or intake-temperature trouble (a direct altitude and waxing indicator). Rising on *one* cylinder means compression loss or an injector spray fault in that cylinder. Stable ignition delay with a moving SOC means injection-timing drift.

### 4.4 Injection health

1. **Rail-pressure wave per injection.** Each injection causes a pressure drop. ✅ The drop magnitude relates to injected quantity (published estimation errors below 3.5 %), and its timing marks the actual start of injection. Faults show as a changed drop or recovery for *that* injector.
2. **FADEC effort monitor (principle 4).** ✅ Cylinder-balancing controllers integrate per-cylinder fuel corrections from crankshaft acceleration, and set-point adaptation compensates injector drift over the injector's life. **Track each correction's level and growth rate.** A slowly rising trim on cylinder 2 is injector 2 degrading, *while every temperature still looks normal*, because the FADEC is hiding it. The trim reaching its authority limit marks the moment the fault becomes visible to everyone else.
3. **Injector drive current** (if available): armature motion appears as an inflection in the current. Stuck or slow needles are visible.
4. **Commanded versus achieved.** Compare commanded SOI and quantity against the rail-pressure-derived and combustion-derived estimates, per cylinder.

### 4.5 Thermal and fluid channels

Per-cylinder EGT/CHT with their dynamics (not steady-state), oil pressure against temperature and speed, fuel temperature and filter ΔP, coolant. These feed the slow estimator (§5.3).

### 4.6 Turbocharger

Turbo speed; synchronous vibration (imbalance); sub-synchronous whirl at 0.4–0.5× (bearing and oil-film instability); MAP oscillation (surge); wastegate/VGT position against command; compressor efficiency estimated from the pressure ratio and outlet temperature against the map in [`turbo_model.py`](../../backend/physics/turbo_model.py).

### 4.7 The Cycle Health Vector

The per-cycle output of the DSP core. It is physically named, versioned, and the input to everything downstream.

```
CycleHealthVector v1
  meta:        cycle_id, t_start, rpm_mean, load, phase, regime_bin, quality_flags
  per_cyl[4]:  imep, work_peer_ratio, comp_index, soc, ca10, ca50, ca90, pmax, pmax_angle,
               dpdtheta_max, ign_delay, resonance_idx, inj_window_energy, needle_close_energy,
               valve_ivc_energy/angle, valve_evo_energy/angle, rail_drop, rail_recovery,
               fadec_trim, fadec_trim_rate, egt, egt_peer_ratio
  engine:      order_spectrum[80], ofsc_indices[k], env_order_indices[bearings],
               gear_ci{fm0, fm4, na4, nb4, sb_index}, twist_amp[torsional orders],
               turbo{speed, sync, subsync, surge_idx}, map, boost_err
  embedding:   z[256]   (self-supervised encoder, §8.2)
```

At 33 cycles per second this is the dense, physically meaningful representation the field lacks. It is also exactly the "high-dimensional regime" in which the fly-inspired methods earn their place.

---

## 5. The digital twin proper: a hierarchical, multi-rate Bayesian estimator

### 5.1 Three time scales

| Layer | Rate | State and parameters estimated | Estimator | Runs on |
|---|---|---|---|---|
| **Combustion** | Per cycle (33 Hz) | Per cylinder: injector delivery efficiency kᵢ, SOI offset Δφᵢ, compression health cᵢ, burn-rate shape | Per-cylinder EKF / moving-horizon estimator over §4 observations | Edge |
| **Thermofluid** | 1–10 Hz | Cylinder, coolant and oil temperatures; per-cylinder cooling effectiveness ηᵢ, oil-pump efficiency, turbo efficiency, sensor biases | **UKF, joint state and parameter** (parameters as random walks) | Edge + GCS |
| **Degradation** | Per flight / per hour | Injector deposit index, bore/ring wear, bearing damage, filter loading, cumulative damage | **Particle filter** over physics-of-failure models ([`damage_accumulation.py`](../../backend/evaluation/damage_accumulation.py), [`oil_system.py`](../../backend/physics/oil_system.py), [`induction.py`](../../backend/physics/induction.py)) | GCS / depot |

The layers feed each other. The combustion layer's kᵢ trend is an observation for the degradation layer's injector-deposit state. The thermofluid layer's ηᵢ drift is an observation for cooling degradation. Parameter posteriors propagate upward with their uncertainty.

### 5.2 Combustion model for a CRDi engine (what the estimator inverts)

🔶 The SI Wiebe model in [`study/24`](../study/24_combustion_cycle_and_crank_dynamics.md) is replaced for CI by:

- **Ignition delay** from an Arrhenius-type correlation in charge temperature and pressure: τ_id = A · p⁻ⁿ · exp(Eₐ/RT), with cetane dependence.
- **Double Wiebe** heat release: a premixed spike (fuel injected during the delay) plus diffusion burning. The split depends on τ_id.
- **Multi-injection** (pilot/main/post), each with its own quantity and timing, driven by the injector model in [`injector_faults.py`](../../backend/physics/injector_faults.py).
- **Rail hydraulics:** rail volume, pump delivery, pressure-control valve and injection draw, which produce the pressure waves of §4.4.

The per-cylinder estimator fits (kᵢ, Δφᵢ, cᵢ) so that this model reproduces that cylinder's observed IMEP, SOC, CA50 and ignition delay, cycle after cycle. **That is combustion-level system identification, running live.**

### 5.3 Thermofluid UKF

A lumped thermal network per cylinder (gas → head → coolant/air), plus the oil circuit and the turbocharger. There are about 40 augmented states. The operating point (rpm, load, altitude, OAT, TAS) enters as input, and parameters drift slowly. Cooling degradation becomes "η₃ dropped from 1.00 to 0.87 ± 0.03 over 6 h" instead of "CHT₃ residual is +11 °C".

### 5.4 Grey-box learning, with guardrails

Physics will be wrong in places: the transfer path, bowl geometry, heat-transfer coefficients. Add **learned residual terms** only where the validity monitor shows persistent structured innovation. They are small networks, constrained (bounded output, monotonic where physics demands it), trained on test-cell and nominal-flight data, and **never allowed to absorb a fault**. They train only on confirmed-nominal data and freeze in flight, the same logic as [`residual_detector.py`](../../backend/twin/residual_detector.py)'s frozen calibration.

### 5.5 Per-tail and fleet: hierarchical priors

```
fleet level:     μ_k, Σ_k      distribution of injector efficiency / wear rates across all engines
engine level:    k_i ~ N(μ_k, Σ_k)     prior for a new engine, sharpened by its own data
cylinder level:  k_i,c                 estimated live
```

A new engine starts with the fleet's knowledge and converges to its own identity within its acceptance runs. An engine whose parameters sit far out in the fleet tail is itself a finding.

### 5.6 Validity

The NIS and whiteness tests of [`twin/validity.py`](../../backend/twin/validity.py) run on **every estimator's innovations**, at every layer. When the combustion layer's innovations stop being white, the system reports "twin no longer matches cylinder 3" rather than silently fitting garbage.

---

## 6. Detection and diagnosis

### 6.1 Four detectors, each with a distinct job

| Detector | Question it answers | Input | Output |
|---|---|---|---|
| **Parameter-change detector** | "Has a physical parameter of this engine changed?" | Estimated θ̂ and innovations (§5) | GLR/CUSUM statistic per parameter per cylinder |
| **Peer detector** | "Is one cylinder different from its three peers right now?" | Peer-normalised Cycle Health Vector | Per-cylinder deviation |
| **Novelty detector** | "Has this engine ever looked like this, in this regime?" | Order spectrum + embedding (§6.3) | Novelty score, and which orders/bins |
| **Recogniser** | "Does this match a known fault?" | Cycle Health Vector | Class posterior (FlyNN / GBM, §8) |

These are *evidence sources*, not decision makers. The diagnostic network (§6.4) makes the decision.

### 6.2 Thresholds that mean something

Each detector's threshold is set by **conformal calibration** on nominal data to a target false-alarm rate *per flight hour*:

```
per-window false-alarm probability ≤ α   ⇒   alarms per hour ≲ α · W · P(persistence)
W = 3,600 one-second windows per hour
```

🔶 For 0.01 alarms per hour with a 3-of-5-window persistence rule, α per window is roughly 10⁻⁴–10⁻³. Calibrating that needs 10⁴–10⁵ nominal windows per operating regime, which means tens of hours of simulated and real nominal data per regime. This is why [08 §6.5](08_deployable_system_blueprint.md) insists on hundreds of Monte Carlo hours and on ACES.

### 6.3 Where the fly brain lives: regime-conditioned Fly Bloom Filter

✅ The Fly Bloom Filter (Dasgupta et al., PNAS 2018) gives novelty scores that are sensitive to both distance and time: similar to the familiar reads as familiar, and recently seen reads as more familiar.

**Our version**, over x = [order spectrum (80), peer-normalised per-cylinder features (~80), embedding z (256)]:

```
code(x)   = top-k( W_sparse · normalise(x) )           m ≈ 20·d units, fan-in 6, k = 5 %   (FlyHash)
regime r  = (rpm bin, load bin, flight phase)          ← efference copy (Model Kombat lesson)
memory    M_r ∈ [0,1]^m, one per regime
familiar  f(x) = mean_{j ∈ code(x)} M_r[j]
novelty   n(x) = 1 − f(x)                               explanation = which active units, hence which orders/features
learn     on confirmed-nominal cycles: M_r[j] ← 1 for j ∈ code(x)
decay     M_r ← M_r · exp(−Δt / τ)                      recency; τ per regime
```

**Why it belongs here:** the input is several hundred dimensions, the regime where expand-and-sparsify works. It costs about 8 MFLOP/s (§9), learns in one pass, needs no labels, and uses bit-array memory that fits an MCU. **Required alongside it:** the dense-projection null model and the other contenders in [08 §4.2](08_deployable_system_blueprint.md). The claim stands or falls on measurement.

**FlyNN** (FlyHash plus one Fly Bloom Filter per fault class) is the recogniser for the **open-set, few-shot and federated** job. A new fault type seen once at one base becomes a new bit array, OR-merged fleet-wide over a thin link, with no retraining.

### 6.4 Diagnostic Bayesian network: from evidence to a hypothesis

- **Structure** from FMECA: modes × location (cylinder, injector, bearing), linked to observable signatures through the isolability matrix in [`reliability/`](../../backend/reliability/).
- **Evidence:** detector outputs from §6.1, oil lab results, maintenance history, the exposure accumulator.
- **Output:** ranked hypotheses with probabilities, plus **explicit ambiguity groups**. For example: *"Injector 2 nozzle deposits 0.71 · compression loss cylinder 2 0.19 · rail-pressure sensor drift 0.06. Injector 2 and compression cylinder 2 are not separable from in-flight evidence."*

### 6.5 Active diagnosis: the twin interrogates the engine

When the top hypotheses are ambiguous, choose the test that best separates them:

```
t* = argmax_t   H(F | E)  −  E_{o ~ p(o | t, E)} [ H(F | E, o) ]   −   λ · cost(t)      subject to safety(t, flight state)
```

The expected outcomes `p(o | t, E)` come from **the twin itself**, which simulates each hypothesis's response to each test. The twin becomes a hypothesis simulator, not just a monitor.

| Test (✅ standard diesel practice where noted) | When allowed | What it separates |
|---|---|---|
| **Cylinder cut-out / contribution test** ✅ | Ground run | Injector versus compression versus mechanical, per cylinder |
| Relative compression (cranking) | Every start | Compression per cylinder |
| Run-down analysis | Every shutdown | Friction and compression |
| Rail-pressure step | Ground run | Pump/pressure-control valve versus injector leakage |
| SOI sweep ±2° | Ground run | Timing drift versus spray/combustion fault |
| Wastegate/VGT step | Ground, or benign flight phase | Actuator versus turbo efficiency versus leak |
| Small throttle perturbation | Flight, benign phase, operator-approved | Improves observability of thermal parameters |

The output is a maintenance action with an expected finding: *"Run cylinder cut-out test (4 min ground run). If the cylinder-2 drop is below 60 % of peers, the injector is confirmed (P = 0.93)."* That is what a maintainer can act on.

### 6.6 Explanation

Every alert carries:

1. The **causal chain in physical terms**, for example: *"Cylinder 2 trim +6.1 % over 40 h → SOC +1.4° late → CA50 +2.1° → IMEP −4 % vs peers → EGT₂ unchanged (FADEC compensating)"*
2. The **evidence** (plots of the relevant windows and orders)
3. The **counterfactual**, for example: *"a sensor fault would not have moved SOC"*
4. The **nearest past cases** from the knowledge graph, with citations

The LLM copilot can *phrase* this. It never generates the facts.

---

## 7. Prognostics and decision

### 7.1 Remaining life per component, per cylinder

- **Path A, physics of failure:** the particle filter over degradation states (§5.1), propagated forward under the planned mission profile.
- **Path B, data-driven:** extrapolation of the trajectories of kᵢ, ηᵢ and bearing indices, with fleet priors.
- **Conformal intervals** on both (ACI under shift), and a **disagreement alarm** when A and B diverge (F38).
- RUL is expressed **in the units the maintainer uses**: flight hours, and sorties of this profile, to a named functional limit (for example "trim authority exhausted", "FM4 > limit").

### 7.2 Mission reliability and risk-based decisions

- **R(mission) = P(no propulsion-induced abort | θ̂ posterior, damage state, profile, forecast environment)** by Monte Carlo ([`mission/reliability.py`](../../backend/mission/reliability.py), now fed by *estimated* rather than placeholder parameters).
- **Go/No-Go as expected loss.** Choose from GO, GO-derated, GO-shortened and NO-GO by minimising expected cost (asset loss, mission value, maintenance cost). This replaces a threshold on a health score.
- **Prescriptive:** the power setting and profile that maximise mission success subject to a damage budget ([`mission/prescriptive.py`](../../backend/mission/prescriptive.py)).
- **In-flight contingency:** *"Cylinder 2 degrading at the current rate. Reduce to 75 % power to hold the damage rate; RTB margin remains 3.2 h at 0.97 reliability."*

### 7.3 Closing the loop with maintenance

Every advisory produces a work package: expected finding, confidence, and the disambiguation test. Every finding (confirmed, different, or no fault found) returns as a **label**. The no-fault-found rate is tracked as a system KPI. This is the "dopamine" signal from [08 §4.3](08_deployable_system_blueprint.md), and the only honest source of real fault labels over time.

---

## 8. The learning system

### 8.1 The data engine

```
flight ─► SSD (full raw) ─► hangar download ─► ground re-analysis at full depth
        ─► auto-labelling by the twin (parameter estimates, events)
        ─► + maintenance outcomes (confirmed / NFF)          ─► curated, versioned dataset
        ─► training (self-supervised + supervised heads)     ─► shadow deployment ─► promotion
```

### 8.2 A self-supervised engine-cycle encoder

🔶 About 120,000 cycles per engine-hour, nearly all healthy, almost none labelled. That is the textbook setting for self-supervised learning.

- **Input:** per-cycle angle-domain representation (8 channels × 1,536 angle samples, or angle-frequency patches).
- **Pretext tasks:**
  - (a) Masked angle-frequency patch reconstruction. ✅ Recent vibration foundation models do exactly this and learn transferable primitives: narrowband ridges, modulation sidebands, impulsive transients.
  - (b) **Cylinder-equivariance.** After phase alignment, a healthy engine's four cylinder windows should be exchangeable. The encoder learns this, and a cylinder whose embedding leaves its peers' cluster is anomalous by construction (principle 3, learned).
  - (c) Temporal consistency across adjacent cycles.
- **Curriculum** (Model Kombat's lesson: order matters): randomised physics simulation → public vibration corpora → lab rig → test cell → per-tail fine-tuning.
- **Output:** embedding z (256) in the Cycle Health Vector, consumed by novelty (§6.3) and the recognisers.

### 8.3 The model contest, restated

The requirement is not "must be cheaper than the Random Forest" (§9 shows compute is not the constraint). It is **"detect more, earlier, at a lower false-alarm rate, and still fit the real-time budget."** The contenders run on the Cycle Health Vector and the spectrum:

- Physics-parameter detectors (§6.1)
- FlyHash-FBF and FlyNN
- Self-supervised encoder + reconstruction score
- Deep SVDD / normalising-flow density on z
- GBM / RF on named features
- A 1D-CNN on the raw angle domain
- A zero-shot time-series foundation model as a control
- The dense-projection null

**The best is adopted per job** (novelty, recognition, few-shot, federated), under the protocol in [08 §4.2](08_deployable_system_blueprint.md). The likely result, stated in advance so it can be checked: physics-parameter detectors win on known physical faults, the self-supervised encoder and FBF win on novelty, FlyNN wins on few-shot and federated, and GBM stays competitive on closed-set recognition of named features.

### 8.4 Governance

- Models are **frozen in flight**.
- New models run in **shadow mode** beside the current one for N flight hours and are promoted only when they agree or outperform on the evidence metrics.
- Every model is versioned, hashed, signed, and linked to its training-data manifest.
- **Federated updates** move bit arrays (FlyNN) or small parameter deltas, never raw data. Classified data stays at the base that owns it.
- Heavy ground models are distilled into edge-sized ones (Model Kombat lesson 1), and agreement on confident calls is reported after every flight.

---

## 9. Compute and latency: it fits, with enormous margin

🔶 Estimated floating-point operations per second at 4,000 rpm (33.3 cycles/s), computed from standard operation counts:

| Stage | MFLOP/s |
|---|---|
| Front-end filtering / decimation (9 channels) | 10.2 |
| Angular resampling (8 ch, 1,536 per cycle) | 12.3 |
| Per-cycle FFT (2,048 points, 8 ch) | 30.0 |
| Fast kurtogram (3 ch, 1 s windows) | 39.3 |
| Envelope + envelope order spectrum (3 ch) | 47.2 |
| Order-frequency spectral correlation (3 ch) | 44.2 |
| Crank inverse dynamics + pressure least squares (4 cyl) | 6.2 |
| Vibration → pressure inverse filter (4 cyl) | 98.3 |
| FlyHash / Fly Bloom Filter | 7.7 |
| Thermofluid UKF (n = 40, 10 Hz) | 3.1 |
| **Total DSP + estimation** | **≈ 300 MFLOP/s** |
| Self-supervised encoder, standard 1D-CNN (74 MFLOP per cycle) | 2,480 |
| — or depthwise-separable version | ≈ 310 |

**Every second, the system fully analyses 133 individual combustion events** from 1.58 MB of raw data, for a total of **0.6–2.8 GFLOP/s**. The current Random Forest does about 24,000 comparisons per second. The full stack is roughly **10⁵× more computation**, and it still uses only a small fraction of a Jetson Orin-class module. The DSP core alone (0.3 GFLOP/s) runs on a single ARM Cortex-A76-class core with room to spare.

**Latency:** a per-cycle result every 30 ms; a statistically confident per-cylinder verdict within about 10–30 cycles (0.3–1 s); thermal-parameter changes within minutes (limited by physics, not compute). **Compute is not the constraint. Information is**, which is why §1–§4 matter more than any model choice.

**Hardware path:** a Python/NumPy reference implementation first. Then Numba on a Raspberry Pi 5 or Jetson Orin Nano for the demo. Then C/C++ with fixed-point front-end DSP on a certifiable MCU/FPGA plus an SoC for the flight article. **Bit-exact test vectors** from the reference implementation guarantee that every port computes the same numbers.

---

## 10. Assurance, security and certification

- **Architectural partition.**
  - The deterministic core (front end, DSP, physics estimators, conformal thresholds) is simple enough to verify.
  - The learned components are advisory evidence sources.
  - Runtime monitors gate the learned outputs: out-of-distribution input (novelty) and invalid twin (NIS) → *"ML evidence withheld"*.
- **Safety case** in GSN (Goal Structuring Notation). Top claim: *"EHU advisories do not increase the risk of an unsafe flight decision."* Its arguments cover the partitioning, the verified deterministic core, the monitored ML, and the operator procedures. This is the language CEMILAC reviewers work in.
- **Software level.** Advisory-only with no control authority, which targets a low DO-178C design-assurance level. Any future control coupling moves only deterministic components into a higher-assurance path.
- **Security.** Secure boot on the EHU; signed models and configs; MAVLink 2 signing; the DO-326A-style airworthiness-security process on the roadmap; physics integrity checks ([`twin/integrity.py`](../../backend/twin/integrity.py)) as the defence against spoofed sensors.
- **Deterministic replay.** Any flight can be re-run bit-exactly through any software version, which is essential for incident investigation and for certification evidence.

---

## 11. What each person sees

| Role | Primary view | Example |
|---|---|---|
| UAV operator (GCS) | A few rationalised ISA-18.2 alarms, each with an action and a time-to-act; mission reliability with its interval | *"CAUTION — Cylinder 2 injection degrading. Mission reliability 0.95 [0.92–0.97]. No action required this sortie. Maintenance flagged."* |
| Propulsion engineer | **Per-cylinder combustion view**: reconstructed p-θ curves overlaid across cylinders; SOC/CA50/IMEP/ignition-delay trends; cylinder × time heatmaps; OFSC maps | Sees cylinder 2's SOC drifting 1.4° late over 40 h while its trim climbs |
| Maintainer | A work package with the expected finding, confidence, the disambiguation test, parts and time estimate | *"Run cut-out test. Expected: cylinder-2 contribution < 60 %. If confirmed, replace injector 2 (P/N …)."* |
| Fleet manager | Tail health ranking, tail-to-mission assignment, parts forecast | — |
| Post-flight analyst | Synchronised replay of the full raw record: waveform, angle-domain views, estimator states and the 3D engine | Scrubs to the moment the anomaly began |

🔶 **The 3D twin gets a real job.** The Blender and WebGL engine visualises **estimated per-cylinder state**: colouring by reconstructed IMEP or SOC deviation, animating the p-θ reconstruction, and marking the component each hypothesis points to. Visualisation becomes an interface to the estimator instead of a decoration.

---

## 12. The simulation needed to train and test all of this

The current plant ([`virtual_engine.py`](../../backend/plant/virtual_engine.py), [`crank_dynamics.py`](../../backend/physics/crank_dynamics.py)) is correct in structure but cannot yet produce 51.2 kHz waveforms with the content §4 depends on. It needs:

| Component | Upgrade |
|---|---|
| Combustion | CI model of §5.2: ignition delay, double Wiebe, pilot/main/post injection, cycle-to-cycle variability |
| Rail hydraulics | Pump, pressure-control valve, rail volume, injection draw → pressure waves |
| Chamber acoustics | Draper modes excited by dp/dθ, damped, so the 5.6–20 kHz content *emerges* from combustion |
| Structure | A modal transfer model (several modes per path, per cylinder) instead of the single damped resonance |
| Impacts | Needle opening and closing, valve seating, piston slap, as impulse sources at their kinematic angles |
| Bearings and gears | Defect impacts with slip (for cyclostationarity) and mesh stiffness with tooth faults |
| Turbocharger | Rotor dynamics: imbalance, whirl, blade pass |
| Torsional | Crank–coupling–gearbox–propeller chain with a damper |
| Sensor chain | IEPE response, mounted resonance, anti-alias filter, 24-bit quantisation, trigger-wheel tooth errors, timer quantisation, bias faults |
| FADEC | Cylinder balancing and drift adaptation loops, **so faults get masked the way they will be in reality** |
| Randomisation | Build variation, transfer-path variation, sensor placement, fuel properties, environment |

**Plus a hardware-in-the-loop bench.** A crank/cam signal emulator plus DAC outputs replaying synthetic or recorded waveforms into the *real* EHU hardware. ECU developers test this way, and it proves the edge node on its real I/O without an engine.

---

## 13. Validation: the evidence ladder

| Rung | Evidence | Proves |
|---|---|---|
| 1. Unit | Bit-exact DSP test vectors; analytic cases (a known tone in → known order out) | The algorithms compute what they claim |
| 2. Simulation Monte Carlo | Thousands of runs; detection and isolation curves; false alarms per flight hour with CIs | Performance *under our physics assumptions* |
| 3. Public data | CWRU/Paderborn (bearing envelope), 3500-DEFault (diesel torsional), C-MAPSS (prognostic metrics) | The methods work on real signals from other machines |
| 4. Real healthy flight | ACES Rotax 914: thermal sim-to-real error, and the **false-alarm rate on real flight hours** | No crying wolf on real data |
| 5. Lab engine rig | Real CI combustion with seeded faults; **virtual pressure checked against a real pressure transducer** | The flagship signal chain works on metal |
| 6. HIL | The real EHU on the emulator bench: latency, power, determinism | The edge claim |
| 7. VRDE test cell | The target engine | TRL 5 |

The acceptance numbers and the one-command evidence report are specified in [08 §6.6](08_deployable_system_blueprint.md).

---

## 14. The capability ladder

🔶 Levels are defined per axis. "Field" is the best competitor observed in [`01`](01_competitive_audit.md), [`05`](05_expanded_survey.md) and the [architecture breakdown](../COMPETITOR_ARCHITECTURE_BREAKDOWN.md).

| Axis | L1 | L2 | L3 | L4 | L5 | Field | Us today | Target |
|---|---|---|---|---|---|---|---|---|
| **Sensing** | Scalars ≤ 50 Hz | + RMS vibration | kHz vibration, time domain | Angle-tagged 51.2 kHz + crank edges + rail | + FADEC effort + active tests | L1–L2 | L2 (L4 in sim, harness only) | **L5** |
| **Unit of analysis** | Sample | Window | Order spectrum | Cycle, per cylinder | Cycle, per cylinder, peer-referenced | L1–L2 | L2 | **L5** |
| **Twin** | Threshold table | Steady-state physics expectation | + PINN / learned correction | Dynamic model + joint estimation | Hierarchical multi-rate Bayesian, per tail + fleet | L2–L3 | L2 | **L5** |
| **Diagnosis** | Rules | Classifier | Classifier + XAI | Probabilistic, with ambiguity groups | + active diagnosis | L2–L3 | L2 | **L5** |
| **Prognosis** | Fixed life | Curve fit | Curve fit + interval | Physics of failure + Bayesian update | Dual path + conformal + disagreement + fleet priors | L2–L3 | L1 live / L3 built | **L5** |
| **Decision** | Go/No-Go threshold | Health score | Mission reliability | + prescriptive | Risk-based expected loss + contingency + maintenance loop | L1–L2 | L1 live / L4 built | **L5** |
| **Learning** | Supervised on sim | + augmentation | + transfer | Self-supervised + open-set | Data engine, federated, shadow mode, distillation | L1 | L1 | **L4–L5** |
| **Edge** | None | Claimed | Budget arithmetic | Measured on a board | HIL-verified, deterministic core | L1–L2 | L3 | **L5** |
| **Assurance** | None | Tests | + honest evaluation | V&V plan + evidence | Safety case + certification path | L1–L2 | L3 | **L4–L5** |

The gap from the field to the target is three levels on most axes. That is not incremental. It is a different class of system.

---

## 15. Build plan

This is a staircase in which **each step is independently demonstrable**. It maps onto the gates in [08 §7](08_deployable_system_blueprint.md): Phases 0–1 there are prerequisites for all of this.

| Step | Content | Demonstrable result | Effort (4 people) |
|---|---|---|---|
| **S1. Waveform-grade simulation** | §12 upgrades; 51.2 kHz output; FADEC balancing loop; sensor chain | Healthy spectrum shows Draper-band content; FADEC masks an injector fault in EGT while the trim grows | 3–4 weeks |
| **S2. Signal intelligence core** | §4.1–4.4 and 4.7: crank inverse dynamics, angle windows, OFSC, envelope, gear CIs, virtual pressure, trim monitor | Cycle Health Vector at 33 Hz; SOC/CA50 recovered in simulation within stated error; bit-exact test vectors | 4–6 weeks |
| **S3. Estimator hierarchy** | §5: per-cylinder combustion estimator, thermofluid UKF, degradation particle filter, validity on all | θ̂ tracks injected degradation within its CI; validity flags model mismatch | 4–6 weeks |
| **S4. Diagnosis + active tests** | §6.1–6.5: detectors, conformal thresholds, Bayesian network, test selection | Blind-injected fault → correct hypothesis *or* correct ambiguity group + the right test requested → resolved | 3–4 weeks |
| **S5. Learning system** | §8: self-supervised encoder, FBF, FlyNN, bake-off, distillation | Published bake-off table with nulls and CIs | 4 weeks |
| **S6. Edge + HIL** | Port to a board; crank emulator bench | Latency and power on the board; deterministic replay | 3–4 weeks |
| **S7. Lab rig campaign** (in parallel from week 2) | Instrumented CI engine: accelerometers at 51.2 kHz, encoder, pressure transducer | **Virtual pressure against real pressure on metal**; seeded injector and timing faults | Continuous |

**The full depth is about 5–6 months of work for 4 people.** If the finale is about 10 weeks away, the version that already leaves the field far behind is:

- S1
- S2 (crank, angle windows, virtual pressure, trim monitor)
- S3 (combustion estimator + thermal UKF)
- S4 (Bayesian network + cut-out test)
- The FlyNN/FBF bake-off
- One lab-rig recording
- The HIL demo on a Pi or Jetson

**The finale demo:** a judge picks a fault and a cylinder in secret. The emulator streams the 51.2 kHz engine. The screen shows per-cylinder p-θ reconstructed live, the FADEC trim hiding the fault from EGT, the hypothesis ranking, the twin requesting a cut-out test, the answer, the RUL and mission reliability updating, and the work package. **Nobody else will be in the same category.**

**Suggested roles:** DSP and physics (S1, S2); estimation and prognostics (S3, §7); diagnosis and ML (S4, S5); systems, edge and interfaces (S6, the ICDs, the lab rig).

---

## 16. Honest limits

- The VRDE engine's constants, FADEC functions and data access are **not public**. Every CI parameter here is an assumption until VRDE supplies it. The architecture is designed so that supplying them is a config change.
- Draper frequencies are first-order estimates; bowl-in-piston geometry and gas properties shift them. The 51.2 kHz requirement holds with margin.
- The vibration transfer path varies with mounting, temperature and airframe, so the virtual pressure sensor **requires test-cell calibration** and per-tail re-calibration. Without a pressure transducer anywhere, it is a model, not a measurement.
- Adding sensors to a certified engine installation is a certification activity in its own right. The flight roadmap depends on it; the test cell does not.
- Active tests in flight must be restricted to operator-approved benign perturbations. Anything else is ground-only.
- Everything in this document that is not yet built is a plan. [08](08_deployable_system_blueprint.md) is the ledger of what is real today.

---

## 17. Corrections this document makes to earlier docs

| Doc | Says | Should say |
|---|---|---|
| [`study/02`](../study/02_engine_sensors.md), [`06`](../study/06_vibration_analysis.md), [`24`](../study/24_combustion_cycle_and_crank_dynamics.md), [`26`](../study/26_order_tracking_and_envelope.md), [`proposal.md`](../study/proposal.md) | Vibration at 2–10 kHz | Block/head accelerometers at **51.2 kHz (20 kHz band)**; turbo at 102.4 kHz; rail pressure ≥ 30 kHz; crank edges timestamped at ≤ 25 ns (§2) |
| [`study/24`](../study/24_combustion_cycle_and_crank_dynamics.md), [`25`](../study/25_misfire_and_combustion_diagnostics.md) | SI-only combustion (Wiebe, spark, misfire) | Add the CI model (§5.2): ignition delay, double Wiebe, multi-injection, rail hydraulics. For a CRDi engine, **injection health, not misfire**, is the primary combustion diagnostic. |
| [`study/05`](../study/05_edge_ai.md) | Raw vibration ~160 kbit/s against the link | The full sensor suite is **12.6 Mbit/s**. The conclusion is stronger, and full-sortie raw recording to an SSD (~102 GB) is feasible (§2.4). |

---

## Sources (checked 23 September 2026)

- Cylinder-pressure reconstruction from vibration and speed: [Gao & Randall, time-domain smoothing, MSSP](https://www.sciencedirect.com/science/article/abs/pii/S0888327099912293) · [complex RBF networks from vibration and speed, MSSP](https://www.sciencedirect.com/science/article/abs/pii/S0888327005001421) · [RBF reconstruction in a diesel](https://www.researchgate.net/publication/281912346_Reconstruction_of_In-Cylinder_Pressure_in_a_Diesel_Engine_from_Vibration_Signal_Using_a_RBF_Neural_Network_Model) · [recursive reconstruction with sensor-fused engine speed, *Sensors* 2024](https://pmc.ncbi.nlm.nih.gov/articles/PMC11360257/) · [acoustic-emission cylinder pressure](https://www.sciencedirect.com/science/article/abs/pii/S0888327004001554)
- Cyclostationarity: [Antoni, *Cyclostationarity by examples*](https://docente.unife.it/docenti/dleglc/a-a-2010-2011-dmsm/ciclostazionarieta.pdf) · [order-frequency analysis of machine signals, MSSP](https://www.sciencedirect.com/science/article/abs/pii/S0888327016304368) · [spectral correlation and envelope analysis](https://www.sciencedirect.com/science/article/abs/pii/S0888327001914153) · [cyclostationary indicators in IC engine cold tests](https://www.sciencedirect.com/science/article/abs/pii/S0888327015000205) · [*Cyclostationarity in condition monitoring: 10 years after*](https://past.isma-isaac.be/downloads/isma2016/papers/isma2016_0246.pdf) · [angle-time cyclostationarity-gram, 2025](https://www.sciencedirect.com/science/article/abs/pii/S0888327025011471)
- Injection diagnostics: [injection diagnosis through common-rail pressure](https://www.researchgate.net/publication/245391135_Injection_diagnosis_through_common-rail_pressure_measurement) · [injection duration identification of CR injectors](https://www.degruyterbrill.com/document/doi/10.1515/eng-2018-0001/html) · [vibration diagnostics of CR injectors](https://www.tandfonline.com/doi/full/10.1080/20464177.2017.1387088) · [CR injector fault diagnosis (IFOA-VMD)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7514255/) · [marine CR injector vibration monitoring](http://www.diagnostyka.net.pl/Marine-diesel-engine-common-rail-injectors-monitoring-with-vibration-parameters,109793,0,2.html)
- FADEC compensation: [Bosch zero-fuel quantity calibration patent](https://www.freepatentsonline.com/y2015/0034048.html) · [method of controlling fuel injection (cylinder balancing, set-point adaptation)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9523324)
- Cut-out testing: [cylinder cut-out test explained](https://www.wholefleet.ca/news/cylinder-cutout-test) · [cylinder power diagnosis by cut-off snap-throttle tests (patent)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6002980) · [Pico diesel performance test](https://www.picoauto.com/library/automotive-guided-tests/heavy-duty/heavy-duty-off-highway/AGT-904-diesel-engine-performance-test/)
- Chamber resonance: [in-cylinder pressure resonance excitation, *Applied Energy*](https://www.sciencedirect.com/science/article/abs/pii/S0306261918310274) · [combustion acoustic phenomena (OSTI)](https://www.osti.gov/pages/servlets/purl/1660557). Mode coefficients are zeros of Bessel-function derivatives.
- HUMS: [HBK — HUMS](https://www.hbkworld.com/en/solutions/applications/vibration/machine-analysis/health-and-usage-monitoring-systems-hums) · [flight-state-driven HUMS thresholds](https://doi.org/10.3390/aerospace12121110)
- Vibration foundation models: [*Learning the Language of Vibration* (VibFM), PHME](https://papers.phmsociety.org/index.php/phme/article/view/4912) · [FISHER](https://arxiv.org/pdf/2507.16696) · [SSL + federated for condition monitoring](https://arxiv.org/pdf/2304.14398)
- Fly methods: [Fly Bloom Filter, PNAS 2018](https://www.pnas.org/doi/10.1073/pnas.1814448115) · [FlyNN-FL, AAAI 2022](https://arxiv.org/abs/2112.07157)
- Public diesel data: [3500-DEFault, Mendeley](https://data.mendeley.com/datasets/k22zxz29kr/1)

*Audit set: [`README.md`](README.md) · [`07`](07_unoccupied_axes_and_ground_up_plan.md) (features) · [`08`](08_deployable_system_blueprint.md) (integration & honesty) · this document (full depth).*
