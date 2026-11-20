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

## 6. Not yet built

- Terrain-aware route planning (Copernicus DEM, A* with clearance and climb feasibility) and replanning when engine health drops.
- The glide-reachability map driven by the aircraft's real position.
- A converter for the recordings made by the earlier prototype.

---

## Related systems

- [Mission Reliability Enhancement](17-mission-reliability.md)
- [Fault Diagnosis and Isolation](11-fault-diagnosis.md)
- [Remaining Useful Life Estimation](14-remaining-useful-life.md)
