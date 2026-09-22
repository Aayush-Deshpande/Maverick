# Part II — Engine Sensors and Data Representation

*For every parameter: what physically measures it, what the signal actually is, how fast it must be sampled, what it looks like, and what it can tell you.*

---

## 2.0 The mental model for this part

A sensor is a **transducer**: it converts a physical quantity into an electrical one. Nothing more. The electrical quantity is then conditioned, digitised, and scaled into engineering units. Understanding *which* electrical quantity matters, because it determines the noise behaviour, the failure modes, and the sampling rate.

Three signal families cover almost everything on an engine:

| Family | Physical output | Examples | Failure signature |
|---|---|---|---|
| **Analog level** | A voltage or resistance proportional to the quantity | Thermocouples, RTDs, pressure transducers | Drift, offset, open circuit → rails to min/max |
| **Pulse / frequency** | A train of pulses whose *rate* encodes the quantity | RPM pickup, fuel flow turbine | Dropout → reads zero, not garbage |
| **AC dynamic** | A continuously varying waveform, information in its *shape and spectrum* | Accelerometer (vibration) | Mount loosening changes the spectrum, not just amplitude |

The third family is the one that breaks naive architectures. Everything else reduces to a number. Vibration does not.

---

## 2.1 RPM — rotational speed

**Physical quantity:** crankshaft revolutions per minute.

**Sensor:** a magnetic (variable reluctance) or Hall-effect pickup facing a toothed wheel or flywheel ring gear. Each tooth passing the sensor generates one pulse. On the Rotax 912 iS this is handled inside the ECU, which publishes RPM on the CAN bus. ✅ **VERIFIED** — RPM is among the parameters published by the 912/915 iS engine computers over a dual-channel CAN interface. ([RDAC-CAN](https://aeroshop.eu/en/rdac-can-rotax-912is.html))

**Signal type at the sensor:** pulse train (frequency-encoded). **After the ECU:** a scalar integer.

**Units:** RPM. Rotax 912-series idles around 1,400 RPM and cruises around 5,000–5,500 RPM. ✅ ([Rotax 912 operator's manual](https://avsport.org/acft/Rotax/OM_912_Series_ED4_R0.pdf))

**Realistic rate:** 10–50 Hz as a reported scalar. ⬜ We assume 20 Hz.

**Why the raw pulse train still matters.** If you keep only the averaged scalar, you throw away *instantaneous angular velocity*, and that is where misfire detection lives. Combustion in each cylinder produces a torque pulse that momentarily accelerates the crankshaft. A cylinder that fails to fire produces a missing acceleration, a detectable dip in the crank speed waveform within a single revolution.

✅ **VERIFIED** — misfire detection from crankshaft angular speed fluctuation is an established technique. Methods include measuring the difference between maximum and minimum angular speed across cylinders, DFT of crankshaft angular acceleration with characteristic harmonics per cylinder, and wavelet analysis of block vibration. ([Misfire detection via crankshaft angular velocity](https://www.academia.edu/8333959/Misfire_detection_system_based_on_the_measurement_of_crankshaft_angular_velocity), [characteristic harmonics of angular acceleration](https://www.researchgate.net/publication/331726855_Detection_of_engine_misfire_using_characteristic_harmonics_of_angular_acceleration))

🔶 **INFERENCE** — this means "misfire", one of the eight PS fault targets, is *not reliably detectable from 20 Hz averaged RPM alone*. At 5,000 RPM a 4-stroke 4-cylinder engine fires 10 times per second (two revolutions per cycle, four firings per cycle → 5000/60/2×4 ≈ 167 firings/s... see the worked example below). Detecting a single missing firing event requires either crank-angle-resolved speed or block vibration. This is one of the most important design consequences in this entire course.

**Worked firing-rate example.** 4-stroke, 4-cylinder, at 5,000 RPM:
- Crankshaft: 5000/60 ≈ 83.3 rev/s
- One complete cycle = 2 revolutions → 41.7 cycles/s
- 4 cylinders fire once per cycle → **166.7 firing events per second**
- Therefore the fundamental firing frequency is ≈ 167 Hz, and half-order content sits at ≈ 41.7 Hz.

A 20 Hz sampler cannot see any of this. See [Part VI](06_vibration_analysis.md) on Nyquist.

**Faults it reveals:** misfire (sub-cycle speed dips), combustion instability (cycle-to-cycle variability), governor/throttle hunting, drivetrain torsional problems.

---

## 2.2 CHT — Cylinder Head Temperature

**Physical quantity:** metal temperature of the cylinder head, indicating how well combustion heat is being carried away.

**Sensor:** a thermocouple or RTD/thermistor at the head, one per cylinder on a properly instrumented engine. On liquid-cooled Rotax 912-series engines, cylinder head temperature (or coolant temperature, depending on variant and instrumentation) is available. ✅ Rotax monitoring systems commonly display CHT and coolant temperature. ([AvMap EngiBOX](https://www.americanaviationparts.com/avmap-engibox-stand-alone-engine-monitoring-system-displays-egt-exhaust-gas-temp-cht-cylinder-head-temp-coolant-temp-oil-temp-air-temp-oil-pressure-rpm-map-compatible-with-rotax-engines-912-91s-914-618-582-503-and-447-series-ux0ems10a.html))

**Signal type:** analog level — millivolts (thermocouple) or resistance (RTD/thermistor). After ADC: scalar float.

**Units:** °C.

**Realistic rate:** 1–10 Hz is ample. **Why:** a cylinder head has large thermal mass. Its temperature cannot change quickly. ⬜ We assume 10 Hz.

**This slowness is a diagnostic tool, not a limitation.** A genuine thermal event follows heat-transfer physics and is gradual. An *instantaneous* jump is physically impossible for a metal mass and therefore indicates a sensor or wiring fault, not an engine fault. This is the core of sensor-vs-engine discrimination:

```
dT/dt within physical bounds  (≲ 1–2 °C/s)  → plausible thermal event
dT/dt far beyond them        (≫ 10 °C/s)    → electrical artefact, open circuit, ADC fault
```

🔶 **INFERENCE** — the specific gradient thresholds must be calibrated per engine and installation; the *principle* is standard practice.

**What one minute looks like:** at 10 Hz, 600 samples per cylinder, a smooth curve with small ripple (±0.2 °C is typical analog transducer noise). A perfectly flat, noise-free reading is itself suspicious — it suggests a frozen ADC buffer or a stuck value.

**Faults it reveals:** cooling degradation, overheating trends, and — critically — *per-cylinder divergence*. One cylinder running hot while its three neighbours are normal is a localised fault (baffle, injector, plug). All four rising together is a system-level cooling problem (coolant, radiator, airflow). **This is why per-cylinder instrumentation matters far more than a single averaged CHT.**

---

## 2.3 EGT — Exhaust Gas Temperature

**Physical quantity:** temperature of the exhaust gas leaving each cylinder, a direct window into the combustion event itself.

**Sensor:** K-type thermocouple in the exhaust runner, one per cylinder. ✅ **VERIFIED** — grounded or ungrounded K-type thermocouples are used for EGT on Rotax installations, typically 4 probes. ([Rotax engine monitor parameters](https://www.rotax-owner.com/en/912-914-technical-questions/9485-engine-monitor-parameters)) ✅ Per-cylinder EGT is among the values published by the 912/915 iS ECU over CAN. ([RDAC-CAN](https://aeroshop.eu/en/rdac-can-rotax-912is.html))

**How a thermocouple works** — worth understanding because its failure modes matter. Two dissimilar metals joined at a point generate a small voltage proportional to the temperature *difference* between that junction and the reference ("cold") junction. K-type produces roughly 41 µV per °C. Two consequences:

1. **Cold-junction compensation is mandatory.** The instrument must know its own terminal temperature or every reading is offset.
2. **The signal is tiny.** Tens of millivolts. It is vulnerable to electrical noise, and a broken wire produces a characteristic open-circuit reading rather than a plausible-looking wrong value.

**Signal type:** analog level (mV). After ADC: scalar float.

**Units:** °C. EGT runs far hotter than CHT — typically several hundred °C.

**Realistic rate:** 1–10 Hz. Faster than CHT in principle (exhaust gas has little thermal mass, the probe does), but still slow relative to combustion. ⬜ We assume 10 Hz.

**Faults it reveals:** this is the richest diagnostic channel on the engine.

| Pattern | Likely meaning |
|---|---|
| One cylinder's EGT drops sharply | That cylinder is not burning properly — misfire, injector, ignition |
| One cylinder's EGT rises | Lean mixture on that cylinder, or timing advance |
| All EGTs shift together | Mixture, fuel supply, or air-charge change affecting the whole engine |
| EGT rises while CHT falls on same cylinder | Classic late-combustion signature — heat leaving in exhaust instead of head |
| Increased cycle-to-cycle EGT variance | Combustion instability |

**The cross-sensor rule:** EGT and CHT on the *same* cylinder, read together, distinguish far more faults than either alone. A fault model fed only "mean EGT" is throwing away most of the diagnostic information.

---

## 2.4 Oil pressure and oil temperature

**Physical quantity:** the health of the lubrication system, which is the fastest path to catastrophic engine destruction when it fails.

**Sensors:**
- **Pressure:** a transducer — typically a piezoresistive or strain-gauge element. ✅ **VERIFIED** — Rotax installations use Honeywell/Keller-type sensors, and depending on production date either a VDO-type sensor (before September 2008) or a 4–20 mA sensor. ([Rotax sensor types](https://www.rotax-owner.com/en/912-914-technical-questions/7581-sensor-type-on-older-912-ul))
- **Temperature:** RTD or thermistor.

**Why 4–20 mA is used and worth knowing about.** A *current* loop is immune to voltage drop along the cable, and — the clever part — the live range starts at 4 mA, not 0. So:
- 4–20 mA = valid measurement
- **0 mA = broken wire**, unambiguously distinguishable from "minimum reading"

This is a built-in fault detection mechanism and a good design pattern to mirror in software: make "no data" distinguishable from "zero".

**Signal type:** analog level (current or voltage). After ADC: scalar float.

**Units:** bar or psi (pressure); °C (temperature).

**Realistic rate:** pressure 10–50 Hz, temperature 1–10 Hz. Pressure can genuinely change fast (pump cavitation, pickup uncovering in a manoeuvre); bulk oil temperature cannot. ⬜ We assume 20 Hz / 10 Hz.

**Faults they reveal:**

| Signature | Meaning |
|---|---|
| Slow pressure decline over hours at constant RPM/temp | Pump wear, bearing clearance growth — a genuine degradation trend suitable for RUL |
| Pressure drop with simultaneous temperature rise | Oil viscosity loss, possible imminent lubrication failure |
| Sharp transient pressure drops | Oil starvation in manoeuvres, foaming, pickup uncovering |
| Temperature rise with stable pressure | Cooling side issue, not a pumping issue |

**The critical confound:** oil pressure depends strongly on both RPM *and* oil temperature (viscosity). Raw oil pressure is nearly useless as a fault indicator. Pressure *relative to what is expected at this RPM and this oil temperature* is highly informative. This is a textbook case for the residual approach — see [Part X](10_digital_twin.md).

---

## 2.5 Fuel flow

**Physical quantity:** mass or volume of fuel consumed per unit time.

**Sensor:** typically a turbine flowmeter — fuel spins a small rotor, and a pickup counts rotations. ✅ Fuel flow monitoring is an available option on Rotax engine monitoring systems. ([Rotax engine monitor parameters](https://www.rotax-owner.com/en/912-914-technical-questions/9485-engine-monitor-parameters))

**Signal type:** pulse frequency. After conversion: scalar float.

**Units:** litres/hour or kg/hour.

**Realistic rate:** 1–10 Hz. The measurement is inherently an average over some number of rotor pulses, so very high rates add nothing. ⬜ We assume 5 Hz.

**Faults it reveals:** injector faults (flow inconsistent with commanded injection), fuel system degradation (filter clogging, pump wear), and — the most valuable use — **specific fuel consumption as an efficiency trend**:

```
SFC  ≈  fuel_flow / power_output
```

A slow rise in SFC at matched conditions over many flight hours is one of the cleanest whole-engine degradation indicators available, and it is an excellent RUL input.

---

## 2.6 Vibration signatures — the parameter that is fundamentally different

**This section explains why vibration breaks the architecture that works for everything else.**

**Physical quantity:** acceleration of the engine structure, in m/s² or g.

**Sensor:** a piezoelectric accelerometer bolted to the engine case, gearbox housing, or mount. Unlike every other sensor here, this one is **not typically part of the stock ECU data**. 🔶 **INFERENCE** — the publicly documented Rotax 912/915 iS CAN parameter set (RPM, manifold pressure, oil pressure/temperature, coolant temperature, per-cylinder EGT, ECU voltage, engine hours) does not include vibration. ✅ That parameter list is verified ([RDAC-CAN](https://aeroshop.eu/en/rdac-can-rotax-912is.html)); the inference is that **vibration monitoring requires adding instrumentation** — an accelerometer plus its own high-rate acquisition path.

### Why it is different

Every other sensor answers "what is the value?". A vibration sensor's value at any single instant is *meaningless*. The information is in the **pattern over time and across frequency**.

```
CHT:        128.4 °C                       ← the number IS the information
Oil press:  4.2 bar                        ← the number IS the information
Vibration:  −0.3, +1.7, −2.1, +0.4, ...    ← a single number tells you nothing.
                                              The SPECTRUM tells you everything.
```

A bearing with a spalled outer race and a healthy bearing can have **identical RMS amplitude**. They differ in *where in the frequency spectrum* the energy sits. Reducing vibration to a single RMS scalar discards exactly the information that identifies the fault.

### The sampling rate consequence

Fault signatures live at high frequency — gear mesh, bearing defect frequencies, combustion harmonics. From §2.1, the firing fundamental alone is ≈167 Hz at 5,000 RPM, and meaningful harmonics extend well above that.

By the Nyquist theorem you must sample at **more than twice** the highest frequency you care about. Therefore:

| To see | You need roughly |
|---|---|
| Firing fundamental (~167 Hz) | ≥ 400 Hz |
| Several combustion harmonics (~1 kHz) | ≥ 2.5 kHz |
| Gear mesh and bearing defects | 10–25 kHz |

✅ **VERIFIED** — standard vibration benchmark datasets reflect this: CWRU samples at 12 kHz, XJTU-SY at 25.6 kHz, FEMTO/PRONOSTIA at 25.6 kHz. ([CWRU 12 kHz](https://digibuo.uniovi.es/dspace/bitstream/handle/10651/69892/Bearing_Fault_Diagnosis_With_Envelope_Analysis_and_Machine_Learning_Approaches_Using_CWRU_Dataset.pdf?sequence=1&isAllowed=y), [XJTU-SY / FEMTO rates](https://arxiv.org/pdf/2109.12513)) ✅ Edge deployments on microcontrollers commonly use ~2 kHz with 256-sample windows. ([TinyML vibration pipeline](https://github.com/Shafqat-16/stm32-edge-ai-vibration-anomaly-detection))

⬜ **ASSUMPTION for our design:** a dedicated vibration channel at **2–10 kHz**, separate from the 20 Hz CAN telemetry path.

### The bandwidth consequence — the pivotal calculation

A single accelerometer at 10 kHz, 16-bit:

```
10,000 samples/s × 2 bytes           = 20 kB/s
                                     = 160 kbit/s   for ONE sensor, raw
```

Compare with the datalink: ✅ Ku-band SATCOM control links are characterised at roughly **122 kbps or less**. ([Data Links chapter](https://kstatelibraries.pressbooks.pub/unmannedaircraftsystems/chapter/chapter-13-data-links-functions-attributes-and-latency/))

**One accelerometer, raw, exceeds the entire satellite link — before any other telemetry, and with nothing left for command, navigation, or payload.**

This is not a tuning problem. It is structural. It forces the architecture:

> **Vibration must be acquired and analysed onboard. Only extracted features, health scores, and events may cross the link.**

🔶 **INFERENCE** — this is precisely why the PS lists "Edge AI" and "lightweight onboard analytics" as desired innovation areas. The physics of the link makes them mandatory, not optional.

**Faults it reveals:** bearing wear, gear mesh degradation, shaft imbalance and misalignment, mount deterioration, combustion roughness, propeller/gearbox problems. Vibration is also usually the *earliest* indicator of mechanical wear — it degrades measurably long before temperature or pressure notice.

---

## 2.7 Battery / alternator health

**Physical quantity:** the electrical system that powers the ECU, ignition, and fuel pumps. On an aircraft with dual-lane electronic engine control, **electrical failure is engine failure**.

**Sensors:** voltage divider for bus voltage; Hall-effect current sensor for alternator/charge current. ✅ **VERIFIED** — a 50 A Hall-effect current sensor can be added to Rotax engine monitoring. ([Rotax engine monitor parameters](https://www.rotax-owner.com/en/912-914-technical-questions/9485-engine-monitor-parameters)) ✅ ECU voltage is among the CAN-published parameters. ([RDAC-CAN](https://aeroshop.eu/en/rdac-can-rotax-912is.html))

**Signal type:** analog level. After ADC: scalar float.

**Units:** volts, amperes.

**Realistic rate:** 10–100 Hz. Electrical transients are genuinely fast. ⬜ We assume 20 Hz.

**Faults it reveals:** alternator failure (voltage sagging toward battery-only, current going to zero), regulator instability (voltage oscillation), increasing electrical load, battery degradation under load. On a long-endurance sortie, an alternator failure starts a countdown clock set by battery capacity — a genuinely different and very actionable kind of RUL.

---

## 2.8 Injection timing parameters

**Physical quantity:** when and for how long each injector opens, and ignition timing, relative to crank angle.

**Sensor:** none, in the usual sense. These are **ECU-internal commanded values**, reported rather than measured. This is an important category distinction — see [Part III §3.6](03_ecu_can_acquisition.md).

**Signal type:** digital values, reported by the ECU. Possibly event/message rather than continuous stream.

**Units:** degrees before top dead centre (timing), milliseconds (injector pulse width).

**Realistic rate:** 10–50 Hz as reported values.

**Faults they reveal:** the real diagnostic power is **commanded versus achieved**. If the ECU commands a certain injector pulse width and the resulting fuel flow, EGT, and RPM do not match the physics expectation, the injector itself is suspect. This is a closed-loop consistency check, not a single-sensor threshold, and it is exactly the kind of cross-domain reasoning a digital twin is for.

🔶 **INFERENCE** — whether a given ECU exposes commanded timing on its public CAN messages varies by manufacturer and firmware, and detailed Rotax CAN mapping is not publicly documented (see [Part III](03_ecu_can_acquisition.md)).

---

## 2.9 Flight context parameters — not engine sensors, but mandatory

These come from the flight computer, not the engine, and **without them the residual approach cannot work at all**.

| Parameter | Source | Why the engine model needs it |
|---|---|---|
| Pressure altitude | Air data / GPS | Air density sets both available power and cooling capacity |
| Outside air temperature | OAT probe | Sets cooling gradient and charge density |
| Airspeed | Pitot-static | Determines cooling airflow through the radiator/baffles |
| Throttle position | Flight control | The commanded operating point |
| Manifold pressure | Engine sensor | Actual air charge delivered. ✅ Published by 912/915 iS ECU over CAN |
| Flight phase | Mission system | Expected stress profile differs by phase |

**Why this is non-negotiable:** the same CHT of 130 °C is entirely normal during a hot-day climb and genuinely alarming during a cold cruise. A model that does not receive altitude and OAT will either raise constant false alarms or be desensitised into uselessness. ✅ This is standard practice in the field — NASA's C-MAPSS benchmark explicitly includes three operational settings (altitude, Mach number, throttle resolver angle) alongside its 21 sensors, and its harder subsets exist precisely to test performance across six operating conditions. ([C-MAPSS structure](https://arxiv.org/pdf/2202.10916))

---

## 2.10 Master summary table

| Parameter | Sensor | Raw signal type | Realistic rate ⬜ | Units | Onboard raw? | Downlink? |
|---|---|---|---|---|---|---|
| RPM (scalar) | Hall/VR pickup | Pulse train | 20 Hz | RPM | — | ✅ yes |
| RPM (crank-angle resolved) | Same, high-res | Pulse timing | kHz-equivalent | rad/s | ✅ yes | ❌ features only |
| CHT ×4 | Thermocouple/RTD | Analog mV / Ω | 10 Hz | °C | — | ✅ yes |
| EGT ×4 | K-type thermocouple | Analog mV | 10 Hz | °C | — | ✅ yes |
| Oil pressure | Transducer (4–20 mA) | Analog current | 20 Hz | bar | — | ✅ yes |
| Oil temperature | RTD/thermistor | Analog Ω | 10 Hz | °C | — | ✅ yes |
| Fuel flow | Turbine flowmeter | Pulse frequency | 5 Hz | L/h | — | ✅ yes |
| **Vibration** | **Accelerometer** | **AC waveform** | **2–10 kHz** | **g** | **✅ yes** | **❌ features only** |
| Bus voltage | Divider | Analog V | 20 Hz | V | — | ✅ yes |
| Alternator current | Hall effect | Analog V | 20 Hz | A | — | ✅ yes |
| Injection timing | ECU internal | Digital value | 20 Hz | °BTDC / ms | — | ✅ yes |
| Manifold pressure | Pressure sensor | Analog | 20 Hz | kPa | — | ✅ yes |
| Altitude / OAT / IAS | Air data | Analog/digital | 5–20 Hz | ft / °C / kt | — | ✅ yes |

**Read the last two columns as the architecture.** Everything that is a scalar goes down the link. The one AC-waveform channel stays onboard and is reduced to features. That single asymmetry shapes the entire system.

---

## 2.11 Bandwidth budget for the scalar telemetry

🔶 **INFERENCE** — a rough calculation to show that scalars are affordable and vibration is not.

About 30 scalar channels, 4 bytes each, at 20 Hz:

```
30 × 4 bytes × 20 Hz = 2,400 bytes/s ≈ 19.2 kbit/s
```

Add framing, headers, and CRC overhead — call it ~25 kbit/s. Against a ~122 kbit/s Ku-band budget that is comfortable, and there is room left for vibration *features* (a few dozen floats per second, ~1–2 kbit/s) and event messages.

Against the ~160 kbit/s for a single raw accelerometer, it is not close. **The scalars fit. The waveform does not.** That is the whole story.

---

**Next:** [Part III — ECU, CAN and Data Acquisition](03_ecu_can_acquisition.md)
