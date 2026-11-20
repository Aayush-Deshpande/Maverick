# Missions, Recording and Replay

The problem statement asks the twin to simulate engine behaviour across mission profiles and environments (high altitude, endurance, hot weather, rapid throttle changes) and to support post-flight analysis and replay. ANUMAAN does this with missions written as data, an executive that flies them through the same controls an operator uses, and a recorder whose sorties can be replayed and re-analysed.

---

## 1. Missions are configuration

Each mission is a JSON file in `configs/missions/` with ordered phases. A phase has a duration in simulated seconds, a lever setting, a target altitude, either an outside air temperature or an ISA deviation, and optional scheduled faults. Every file carries its source.

| Preset | What it exercises | Source |
|---|---|---|
| High altitude, Leh to 25,000 ft | Take-off from about 10,700 ft, climb to FL250, cruise, descent | Leh airfield elevation (AIP India) |
| Hot weather, Thar, ISA+30 | Take-off, climb and a one-hour patrol about 45 °C above standard at the surface | Roadmap scenario (dust not yet modelled) |
| Rapid throttle transitions | 20 idle / take-off cycles, 20 s each | Roadmap scenario |
| Endurance 18 h | ISR loiter profile | Roadmap scenario |
| Endurance 24 h (VRDE only) | The same profile at 24 h | Jayem's stated 24-30 h mission class |

---

## 2. The mission executive

The executive runs on the engine's simulation clock and sets lever targets through exactly the path the operator's sliders use. A climbing aircraft gets its outside air temperature recomputed from its *current* altitude, using the ISA lapse rate plus the phase's deviation. Scheduled faults enter through the normal fault path, labelled as scripted. While a mission runs:

- the **remaining mission** becomes the profile of the [mission-reliability](17-mission-reliability.md) Monte Carlo;
- a predicted limit crossing **before the mission ends** raises a CAUTION with the reason "will exceed … in … min";
- the state message carries the mission, the current phase, the elapsed and remaining time, and the number of throttle transitions.

**Measured (SIMULATION).**

| Scenario | Result |
|---|---|
| Leh, 912 iS (naturally aspirated) | Manifold pressure in the climb at FL200–250 is below 75 % of its value at 11,000–13,500 ft |
| Leh, 915 iS (turbocharged) | The turbo control unit holds climb manifold pressure flat (about 126 kPa) from 12,500 to 15,000 ft, and it decays to about 95 kPa above 20,000 ft |
| Thar ISA+30 | Every temperature margin shrinks against the same leg at ISA (head temperature +5 °C, coolant +4 °C, EGT +30 °C). The thermostats hold the oil temperature within a few degrees. |
| Rapid throttle | All 39 commanded transitions are flown; engine speed swings by more than 1,000 rpm on each |

---

## 3. Recording a sortie

A recording is a folder per sortie:

| File | Content |
|---|---|
| `meta.json` | engine, tail, seed, calibration length, mission and its start, configuration hash, start/stop time |
| `frames.jsonl.gz` | every **measured** frame, exactly as the system received it, before any inference touched it |
| `timeline.jsonl` | the decision record of every tick: status level, reason codes, confirmed alarm, the three leading hypotheses |
| `states.jsonl.gz` | every state message published to the operator |

No simulator truth is ever written to a recording.

---

## 4. Replay and re-analysis

- **Replay** serves the recorded state messages page by page, flagged as replay, so the interface shows exactly what the operator saw.
- **Re-analysis** proves where the decisions came from. A fresh runtime of the same tail is rebuilt from its seed. The recorded measured frames are then pushed through the identical processing path with **no truth and no fault list**, and the decision timeline must come out identical.

**Measured.** A 240-second Thar sortie with an oil-pressure fault injected during the flight re-analyses to an identical decision timeline, tick by tick. The status levels, reasons and hypotheses therefore came from the measurements alone. A recording that did not start at a known runtime state is reported as "not comparable" instead of being claimed identical.

---

## 5. Sortie health report

Every recording produces a self-contained HTML report with these sections:

- summary;
- status timeline with reasons;
- limit exceedances, recomputed from the measured values against the engine-manual limits, with duration and limit source;
- alerts with operator actions;
- hypotheses with their supporting channels;
- fuel-flow and temperature trends;
- end-of-sortie prognostics and mission reliability;
- maintenance work orders raised;
- configuration hash with the limit sources;
- software version.

The first line states the evidence class.

---

## 6. Terrain-aware route planning

The planner answers one operational question: *can this aircraft, with this engine in its present condition, get from here to there over the terrain?*

**Terrain.** Elevation comes from the Copernicus GLO-30 digital surface model (30 m posts), the public ESA dataset on the AWS open-data registry. The demonstration tile N34 E077 covers Leh and the Nubra valley. As a check, the model reads 3263 m at Leh airfield, against a published elevation of about 3256 m. If the tile has not been downloaded, the service reports TERRAIN UNAVAILABLE. It never plans over an assumed flat earth.

**Search.** The tile is divided into planning cells of 60 × 60 posts (about 1.85 km × 1.5 km at 34° N). Each cell carries the **highest** elevation inside it, which makes the clearance check conservative. Altitude is divided into 1000 ft layers. An A* search moves level to the eight neighbouring cells, or climbs or descends one layer inside a cell (a climbing orbit). A diagonal move must clear both cells it cuts across. A state is usable only when:

$$h_{\text{layer}} \ge z_{\max}(\text{cell}) + 1000\ \text{ft} \quad\text{and}\quad h_{\text{layer}} \le h_{\text{ceiling}}(\text{engine health})$$

The route cost is distance plus three metres for every metre climbed (an energy weighting). The heuristic is the great-circle distance to the goal, which never overestimates, so the route found is the cheapest one available.

**Engine health enters through the service ceiling.** Available power is computed by the calibrated engine model at full lever and maximum-continuous rpm in the actual atmosphere. It is then multiplied by a **power factor**:

$$\text{PF} = \min\!\left(1, \frac{\text{MAP}_{\text{measured}}}{\text{MAP}_{\text{model}}}\right) \cdot \min\!\left(1, \frac{\text{rpm}_{\text{measured}}}{\text{rpm}_{\text{model}}}\right)$$

The model term is evaluated at the measured lever, air and rpm. The rpm term is used only with a fixed-pitch propeller, where lost torque shows as lost rpm. The power factor uses measured evidence only, never the list of injected faults. With no running engine there is no evidence, and the planner refuses to assume a healthy engine.

Climb rate follows from a drag polar for the airframe:

$$\text{ROC} = \frac{\eta_p P_{\text{avail}} \cdot \text{PF} - D \cdot V}{W}, \qquad D = \tfrac12 \rho V^2 S \left(C_{D0} + k C_L^2\right)$$

Climb is flown at constant equivalent airspeed. The service ceiling is the highest layer where the climb rate is at least 100 ft/min. The airframe values describe a generic single-engine MALE UAV. They are labelled ASSUMED, because no specific airframe's data is public.

**Refusal and replanning.** When no route exists, the planner searches again with a raised ceiling to find the lowest altitude that any route over the terrain needs. It then states both numbers. Replanning means planning again from the present position with the present power factor.

**Measured (SIMULATION, Rotax 912 iS Sport, ISA, Leh → Thoise, over the Ladakh range):**

| Power factor | Service ceiling | Result |
| :--- | :--- | :--- |
| 1.00 (healthy) | 20,000 ft | Route found: 61 km, highest layer 20,000 ft, minimum terrain clearance 1,074 ft |
| 0.85 | 18,000 ft | Refused: terrain on every route needs 20,000 ft |
| 0.70 | 15,000 ft | Refused, same reason |
| 0.50 | 9,000 ft | Refused, same reason |

Power factor measured at 90 % lever, 9000 ft:

| Engine and fault (severity 1) | Power factor |
| :--- | :--- |
| Healthy tails | 0.98–1.00 |
| Rotax 912 air-filter blockage | 0.95 |
| Rotax 914 wastegate stuck open | 0.54 |
| VRDE wastegate stuck open | 0.37 |
| AE300 boost leak | 1.00 |

The AE300 boost leak is a known limitation. At that operating point the governed diesel still reaches its manifold-pressure target, so the measured air path shows no loss.

**API.**

- `GET /api/v1/terrain/elevation?lat=&lon=`
- `POST /api/v1/planning/route` with the engine, start (with altitude), goal, ISA deviation and an optional operator power factor. The response returns the waypoints with altitude, terrain and climb rate, the distance, the minimum clearance, the ceiling, the power-factor source (MEASURED with its ratios, or OPERATOR), and the refusal reason when there is one.

**Acceptance test (T-MIS-6).** The test uses synthetic terrain: a 5800 m ridge with a single 4500 m pass. With a healthy engine the route goes through the pass and never over the ridge. Without the pass, the route is refused with its reason. At power factor 0.7 the pass is no longer reachable, so the route is refused, and a goal on the same side of the ridge is still planned below the reduced ceiling.

---

## 7. Not yet built

- The glide-reachability map driven by the aircraft's real position, and one-click divert through the planner.
- A map view of the route in the console.
- Wind and no-fly zones in the route cost.
- A converter for the recordings made by the earlier prototype.

---

## Related systems

- [Mission Reliability Enhancement](17-mission-reliability.md)
- [Fault Diagnosis and Isolation](11-fault-diagnosis.md)
- [Remaining Useful Life Estimation](14-remaining-useful-life.md)
