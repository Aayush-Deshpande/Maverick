# Environmental — atmosphere and operating conditions

Reference data for the environment model that feeds the physics twin.

Without altitude and temperature, the residual approach cannot work — the same CHT is normal at sea level and alarming at 25,000 ft. See [Part II §2.9](../../ANUMAAN/docs/study/02_engine_sensors.md).

---

## International Standard Atmosphere (ISA)

The reference model. Real conditions are expressed as deviations from it.

### Troposphere (to ~11 km / 36,089 ft)

```
Temperature:  T = 288.15 − 0.0065 × h        (K, h in metres)
Pressure:     p = 101325 × (T/288.15)^5.2561  (Pa)
Density:      ρ = p / (287.05 × T)            (kg/m³)
```

Sea-level reference: 288.15 K (15 °C), 101,325 Pa, 1.225 kg/m³. Lapse rate 6.5 K/km.

### Values at altitude

| Altitude | ISA temp | Pressure | Density | ρ/ρ₀ |
|---|---|---|---|---|
| Sea level | 15.0 °C | 101.3 kPa | 1.225 | 1.000 |
| 5,000 ft | 5.1 °C | 84.3 kPa | 1.056 | 0.862 |
| 10,000 ft | −4.8 °C | 69.7 kPa | 0.905 | 0.739 |
| 15,000 ft | −14.7 °C | 57.2 kPa | 0.771 | 0.629 |
| 20,000 ft | −24.6 °C | 46.6 kPa | 0.653 | 0.533 |
| 25,000 ft | −34.5 °C | 37.6 kPa | 0.549 | 0.448 |
| 30,000 ft | −44.4 °C | 30.1 kPa | 0.458 | 0.374 |

**Read the last column as the engine's problem.** At 25,000 ft a naturally-aspirated engine has ~45% of sea-level air density — which means roughly 45% of the power *and* roughly 45% of the cooling mass flow. Both fall together, which is why altitude behaviour is not intuitive and must be modelled rather than guessed.

---

## Density altitude

The single number combining pressure altitude and temperature into the altitude the engine actually "feels":

```
DA ≈ pressure_altitude + 120 × (OAT − ISA_temp_at_that_altitude)      [ft, °C]
```

**Worked example — a hot day at a high field:**

```
Field elevation:   10,000 ft
ISA temp there:    −4.8 °C
Actual OAT:        +25 °C
Deviation:         +29.8 °C

DA ≈ 10,000 + 120 × 29.8 ≈ 13,580 ft
```

The engine performs as if it were 3,580 ft higher than it is. For Indian operations this matters enormously.

---

## Operating environment presets

⬜ Our scenario presets, representing realistic Indian operating theatres:

| Preset | Altitude | ISA deviation | OAT | Character |
|---|---|---|---|---|
| `LADAKH_HIGH_COLD` | 25,000 ft | −15 °C | ≈ −49 °C | High and very cold — **large cooling margin** |
| `THAR_HOT` | 15,000 ft | +25 °C | ≈ +10 °C | Hot — **small thermal margin** |
| `COASTAL_STANDARD` | 10,000 ft | 0 °C | ≈ −5 °C | Reference condition |
| `MONSOON_HUMID` | 12,000 ft | +10 °C, high humidity | ≈ +1 °C | Reduced charge density |

**The Ladakh/Thar pair is the key demonstration.** The *same* degradation under these two environments should produce *different* go/no-go verdicts — which proves the simulation is physics-driven rather than scripted. See [Part XI §11.4](../../ANUMAAN/docs/study/11_mission_simulation.md).

---

## Why thermal margin differs

| OAT | Cooling gradient (T_head − T_ambient) | Margin to CHT limit |
|---|---|---|
| −40 °C | Very large | Large |
| 0 °C | Large | Comfortable |
| +25 °C | Moderate | Reduced |
| +45 °C | Small | **Small** |

Heat rejection is proportional to the temperature difference. In hot conditions the engine starts with less headroom, so **the same 20% cooling degradation is a non-event at −40 °C and a mission-ender at +45 °C.**

---

## Environmental effects summary

| Parameter | Effect on engine | Modelled? |
|---|---|---|
| **Pressure altitude** | Air density → power and cooling mass flow | ✅ Primary |
| **OAT** | Cooling gradient, charge density | ✅ Primary |
| **Density altitude** | Combined effect | ✅ Derived |
| Humidity | Slightly reduces charge density; affects detonation margin | 🔶 Secondary |
| Airspeed | Cooling airflow through radiator/baffles | ✅ Primary |
| Icing conditions | Induction icing — a genuine piston-engine hazard | 🔶 Flag only |
| Wind | Indirect, via power required | ❌ Not modelled |

---

## Data sources

| Source | Use |
|---|---|
| ISA standard (ICAO/ISO 2533) | The atmosphere model — implemented directly, no download needed |
| IMD (India Meteorological Department) | Real temperature profiles for Indian theatres, if wanted for realism |
| ERA5 reanalysis (ECMWF/Copernicus) | Historical upper-air data — likely overkill for our purposes |

⬜ For the prototype, the ISA model plus configurable deviations is sufficient and fully self-contained. Real meteorological data adds realism but not capability.
