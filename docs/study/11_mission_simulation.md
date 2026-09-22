# Part XI — Mission Simulation

*Running the twin on hypothetical inputs, and the parameters beyond the engine that matter.*

---

## 11.1 What mission simulation means

✅ The PS requires "Simulating engine behavior under different mission profiles and environmental conditions", specifically naming high-altitude operations, endurance missions, hot-weather operation, and rapid throttle transitions.

Mission simulation is the twin's physics model running on **hypothetical inputs instead of live telemetry**.

```
LIVE MODE                              SIMULATION MODE
                                       
 real telemetry ──▶ physics model       synthetic inputs ──▶ physics model
                         │              (chosen altitude,         │
                         ▼               OAT, profile)            ▼
                  expected values                          predicted values
                         │                                        │
                         ▼                                        ▼
                    residuals                            "what would happen"
```

**This is why a twin must contain a model rather than only a data feed.** A digital shadow cannot do this at all — with no physical object producing data, it has nothing to display. The twin can, because the model works without the engine.

### Three distinct uses

| Use | Question | When |
|---|---|---|
| **Pre-flight planning** | Can this engine, in its current state, complete this sortie? | Before launch |
| **In-flight replanning** | Given the degradation we have observed, what can we still do? | During flight |
| **Post-flight analysis** | What would have happened if we had continued? | After landing |

The second is the most operationally valuable and the most distinctive: it combines the *current degraded state* with a *hypothetical future profile*. That is something neither a dashboard nor an offline simulator can do alone.

---

## 11.2 The parameter space

Far more than the eight engine parameters is involved. This section catalogues them and — more usefully — says which actually matter for piston-engine PHM.

### Flight state parameters

| Parameter | Unit | PHM relevance | Why |
|---|---|---|---|
| **Pressure altitude** | ft | ★★★★★ | Sets air density → power available and cooling capacity |
| **Airspeed (IAS/TAS)** | kt | ★★★★ | Determines cooling airflow mass through radiator/baffles |
| Groundspeed | kt | ★ | Navigation; only matters via fuel-range planning |
| Vertical speed | ft/min | ★★★ | Climb rate implies sustained high power — a thermal stress proxy |
| Pitch | deg | ★★ | Affects oil pickup, cooling airflow angle |
| Roll | deg | ★★ | Sustained bank can uncover the oil pickup — a real transient-pressure cause |
| Yaw / heading | deg | ★ | Navigation only |
| GPS position | lat/lon | ★★ | Mission context, terrain, recovery-field distance |

### Engine state parameters

All eight PS groups from [Part II](02_engine_sensors.md), plus:

| Parameter | Unit | PHM relevance | Why |
|---|---|---|---|
| **Throttle position** | % | ★★★★★ | The commanded operating point — the model's primary input |
| **Manifold pressure** | kPa | ★★★★★ | Actual air charge delivered. ✅ Published by the 912/915 iS ECU |
| **Engine load** | % | ★★★★ | Normalises stress across conditions |
| Fuel quantity remaining | L | ★★★ | Endurance limit, independent of engine health |
| Engine hours | h | ★★★★ | Cumulative life — the denominator for RUL |
| Propeller pitch | deg | ★★ | If variable-pitch, changes load at a given RPM |

### Environmental parameters

| Parameter | Unit | PHM relevance | Why |
|---|---|---|---|
| **Outside air temperature** | °C | ★★★★★ | Sets the cooling temperature gradient |
| **Ambient pressure** | hPa | ★★★★★ | With OAT, determines air density |
| **Density altitude** | ft | ★★★★★ | The single derived number combining both |
| Humidity | % | ★★ | Minor effect on charge density and detonation margin |
| Wind | kt/deg | ★ | Navigation; indirect via power required |
| Terrain elevation | ft | ★★ | Determines minimum safe altitude and glide options |
| Icing conditions | bool | ★★★ | Carburettor/induction icing is a genuine piston-engine hazard |

**Density altitude deserves emphasis.** It combines pressure altitude and temperature into the single number that actually governs engine performance:

```
Density altitude ≈ pressure altitude + 120 × (OAT − ISA temperature at that altitude)
```

🔶 A hot day at a high-altitude field can give a density altitude thousands of feet above the physical elevation — meaning the engine behaves as if it were far higher than it is. For Indian operations (Ladakh high-and-cold, Thar high-and-hot) this matters enormously and makes a genuinely compelling demo contrast.

### Mission parameters

| Parameter | PHM relevance | Why |
|---|---|---|
| **Flight phase** | ★★★★★ | Each phase has a characteristic stress profile |
| Planned duration | ★★★★★ | The number RUL must be compared against |
| Waypoints / route | ★★ | Determines altitude profile and time to recovery field |
| Payload state | ★★ | Electrical load on the alternator |
| Altitude profile | ★★★★ | Drives the thermal and power history |
| Time to nearest recovery field | ★★★★ | **The operationally critical number when a fault appears** |

That last row is often forgotten. When the system says "RUL 3 hours", the decision depends entirely on whether a landing site is 30 minutes or 4 hours away. A genuinely useful advisory must incorporate it.

---

## 11.3 Flight phases and their stress signatures

✅ The PS names high altitude, endurance, hot weather, and rapid throttle transitions as the scenarios to simulate. 🔶 The stress characterisation below is inference from engine physics.

| Phase | Duration | Power | Thermal stress | Dominant risk |
|---|---|---|---|---|
| **Takeoff** | minutes | Maximum | Rising fast | Peak mechanical and thermal load in a short burst |
| **Climb** | 20–60 min | High, sustained | **Highest sustained** | Cooling degrades as density falls while power demand stays high |
| **Cruise** | hours | Moderate | Steady | Low — the reference condition |
| **Loiter** | **many hours** | Low–moderate | Low but prolonged | **Cumulative wear** — nothing dramatic, but this is where most life is consumed |
| **Descent** | 10–30 min | Low | Falling fast | Thermal shock from rapid cooling; shock cooling of cylinders |
| **Landing** | minutes | Variable | Transient | Rapid throttle changes |

**Climb is the worst case and the most diagnostically useful.** Power demand is high while cooling capability is falling with altitude — the two work against each other. A cooling-system degradation that is invisible in cruise often becomes obvious in climb. 🔶 This suggests a useful design idea: **evaluate cooling health specifically during climb segments**, where the system is stressed enough to reveal the fault.

**Loiter dominates life consumption.** An 18-hour sortie is mostly loiter. Damage accumulates slowly and invisibly there, which is exactly why trend analysis over hours — rather than instantaneous detection — is where the value lies.

---

## 11.4 How environment changes engine behaviour

⬜ **ILLUSTRATIVE** figures showing the *direction and rough magnitude* of effects. Real values require a calibrated performance map.

### Altitude, at constant throttle

| Altitude | Rel. air density | Power (NA engine) | Cooling capacity | Expected CHT |
|---|---|---|---|---|
| Sea level | 1.00 | 100% | 100% | Baseline |
| 10,000 ft | ~0.74 | ~74% | ~74% | Roughly similar (less heat, less cooling) |
| 20,000 ft | ~0.53 | ~53% | ~53% | Rises if power demand is maintained |
| 30,000 ft | ~0.37 | ~37% | ~37% | **Significantly higher for the same power** |

**The key insight:** power and cooling both fall with density, so at *reduced* power the temperatures can stay similar. But a MALE UAV at altitude must often maintain power to stay airborne — at which point the cooling shortfall dominates and temperatures climb. 🔶 This is why altitude is the single most important context parameter.

### Ambient temperature, at constant altitude

| OAT | Cooling gradient | Expected CHT | Margin to limit |
|---|---|---|---|
| −40 °C (Ladakh, high) | Very large | Low | Large |
| 0 °C | Large | Moderate | Comfortable |
| +25 °C | Moderate | Higher | Reduced |
| +45 °C (Thar, summer) | Small | **High** | **Small** |

The engine has less thermal headroom in hot conditions before the same degradation becomes limiting. **The same 20% cooling degradation is a non-event at −40 °C and a mission-ender at +45 °C.**

⬜ This gives us an excellent demo: the *same* simulated degradation, evaluated under two environment presets, producing different go/no-go outcomes. It demonstrates that the simulation genuinely responds to inputs — which ✅ the team's own breakdown correctly identifies as the test of whether a simulation is real or a pre-baked animation.

---

## 11.5 Mission simulation architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  INPUTS                                                              │
│                                                                      │
│  ┌────────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ CURRENT ENGINE     │  │ MISSION PROFILE  │  │ ENVIRONMENT      │  │
│  │ STATE              │  │                  │  │                  │  │
│  │ from the twin:     │  │ phases, duration,│  │ altitude band,   │  │
│  │ health indices,    │  │ altitude profile,│  │ OAT, pressure,   │  │
│  │ degradation rates, │  │ payload/elec load│  │ humidity         │  │
│  │ residual biases    │  │                  │  │                  │  │
│  └─────────┬──────────┘  └────────┬─────────┘  └────────┬─────────┘  │
└────────────┼──────────────────────┼─────────────────────┼────────────┘
             └──────────────────────┼─────────────────────┘
                                    ▼
             ┌──────────────────────────────────────────┐
             │  PHYSICS MODEL (same one as the twin)    │
             │  stepped forward through the profile     │
             │  + degradation model applied over time   │
             └──────────────────┬───────────────────────┘
                                ▼
             ┌──────────────────────────────────────────┐
             │  PREDICTED TRAJECTORY                    │
             │  CHT/EGT/oil/vibration vs mission time   │
             │  health index vs time                    │
             │  limit exceedance times, if any          │
             └──────────────────┬───────────────────────┘
                                ▼
             ┌──────────────────────────────────────────┐
             │  MISSION ASSESSMENT                      │
             │  · Does any parameter exceed a limit?    │
             │  · Does health cross the threshold?      │
             │  · Does RUL cover the duration?          │
             │  · With what confidence?                 │
             │  → GO / GO-WITH-RESTRICTIONS / NO-GO     │
             └──────────────────────────────────────────┘
```

**The critical design point:** the simulator uses **the same physics model** as the live twin. Not a copy, not a similar model — the same code. This guarantees consistency (a simulated 25,000 ft matches a real 25,000 ft) and halves the validation work. ⬜ Architecturally this means the physics model must be a pure function of its inputs, with no hidden dependence on live data.

---

## 11.6 Go / No-Go logic

⬜ Our proposed decision rule, with the reasoning:

```python
def assess_mission(twin_state, mission_profile, environment):
    trajectory = physics_model.simulate(twin_state, mission_profile, environment)

    # 1. Hard limits — any exceedance is disqualifying
    if trajectory.any_limit_exceeded():
        return NO_GO, trajectory.first_exceedance()

    # 2. RUL versus duration — use the PESSIMISTIC bound, not the point estimate
    if twin_state.rul_lower_bound < mission_profile.duration:
        return NO_GO, "RUL lower bound below planned duration"

    # 3. Margin check — is there enough left for contingency?
    if twin_state.rul_lower_bound < mission_profile.duration * SAFETY_FACTOR:
        return GO_WITH_RESTRICTIONS, suggest_reduced_profile(trajectory)

    # 4. Recovery reachability under a worst-case fault
    if not trajectory.recovery_field_reachable_throughout():
        return GO_WITH_RESTRICTIONS, "Route exceeds single-engine recovery range"

    return GO, trajectory
```

**Two deliberate choices worth defending:**

**Use the lower confidence bound, never the point estimate.** If RUL is 10 h with an interval of [8.9, 11.5], plan against 8.9. Planning against 10 means accepting a substantial probability of exceeding actual remaining life. This is the single most important line in the function.

**"GO-WITH-RESTRICTIONS" must exist.** A binary go/no-go throws away the most useful answer: *"you cannot fly the 18-hour sortie, but you can fly 10 hours at reduced power."* Real operations need this middle option, and a system that cannot express it will be overridden and ignored.

---

## 11.7 Mission replay

✅ The PS requires "Replay of historical mission data" and support for post-flight analysis.

**What replay is:** re-feeding recorded telemetry through the same pipeline as if live, with timeline control.

```
Stored telemetry ──▶ same ingestion ──▶ same twin ──▶ same analytics
                     (variable speed, pause, seek)
```

⬜ Requirements:

| Capability | Why |
|---|---|
| Variable speed (0.1× to 100×) | Scan an 18 h sortie quickly, then study 10 seconds closely |
| Pause and step | Frame-by-frame examination of an event |
| **Seek to flagged events** | The most-used feature — jump straight to what mattered |
| Deterministic reconstruction | Same input must give same twin state, every time |
| Side-by-side comparison | Compare the flagged flight against a known-good one |

**The determinism requirement has a real architectural consequence:** the twin must not depend on wall-clock time, random seeds, or non-reproducible state. If replaying the same flight twice gives different results, the replay is useless for investigation — which is its primary purpose.

**Replay also reveals the live/log divergence** from [Part III §3.7](03_ecu_can_acquisition.md). Post-flight you have the full onboard log; in flight you had only the downlinked subset. Replaying the *full log* legitimately shows things the live system never saw. ⬜ This is a feature to expose deliberately: "here is what the operator saw; here is what was actually happening" is a genuinely valuable analysis view and an honest illustration of the bandwidth constraint.

---

## 11.8 What to simulate for the demo

⬜ Four scenarios that between them exercise every PS requirement:

| # | Scenario | Demonstrates |
|---|---|---|
| 1 | **Ladakh high-altitude cold** — 25,000 ft, −35 °C | Altitude effects, cold-weather margin, density-altitude reasoning |
| 2 | **Thar hot-and-high** — 15,000 ft, +45 °C | Thermal margin loss; same degradation, different verdict from #1 |
| 3 | **Endurance loiter** — 18 h at low power | Slow degradation accumulation, trend detection, RUL convergence |
| 4 | **Rapid throttle transitions** | Transient response, thermal shock, distinguishing transients from faults |

Scenarios 1 and 2 as a **pair** are the strongest demonstration: identical engine state and identical degradation, different environment, different go/no-go outcome. It proves the simulation is physics-driven rather than scripted — which ✅ is precisely the misconception the team's own breakdown warns against.

---

**Next:** [Part XII — The Complete Data Pipeline](12_data_pipeline.md)
