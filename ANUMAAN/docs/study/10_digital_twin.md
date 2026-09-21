# Part X — The Digital Twin

*What actually makes something a digital twin, and how to build one that earns the name.*

---

## 10.1 The definitional ladder

These terms are used interchangeably in marketing and mean quite different things in engineering. The distinction is the difference between a demo and a system.

| Level | Name | Data flow | What it can do |
|---|---|---|---|
| 0 | **3D model** | None | Look like the object |
| 1 | **Visualisation** | Data → display | Show current values |
| 2 | **Digital Model** | Manual both ways | Simulate offline; no live connection |
| 3 | **Digital Shadow** | Physical → digital, automatic | Mirror the physical object's state in real time |
| 4 | **Digital Twin** | Physical ↔ digital, automatic | Mirror **and** feed decisions back |
| 5 | **Real-time Digital Twin** | Bidirectional, within the process timescale | Influence operation while it matters |

### The distinction that matters most: Shadow versus Twin

```
DIGITAL SHADOW                          DIGITAL TWIN
                                        
  Physical ──────────▶ Digital            Physical ──────────▶ Digital
     engine    data      model               engine    data      model
                                                ▲                  │
                                                └──────────────────┘
                                                  decisions, advisories,
                                                  control influence
  "The model knows what the              "The model knows, AND that
   engine is doing."                      knowledge changes what happens."
```

A dashboard that displays live telemetry is a **digital shadow**. It becomes a **twin** when its outputs — advisories, go/no-go decisions, maintenance actions, derate recommendations — actually influence the physical asset's operation.

⬜ **Where ours sits:** a digital twin at **level 4**, closing the loop through the operator rather than through direct control. The twin computes health, RUL, and advisories; the operator acts on them; the engine's future operation changes as a result. That is a genuine feedback loop, and it is the honest claim. Claiming level 5 autonomous control would be false — we never command the aircraft ([Part IV §4.4](04_telemetry_and_comms.md): we are a STANAG LOI-2 consumer).

---

## 10.2 The three ingredients

✅ The PS requires the system to integrate engine sensor data, thermodynamic behaviour models, engine performance maps, failure/degradation logic, and AI/ML predictive analytics.

Reduced to essentials, a twin needs three things, and it is a twin only when all three are present:

```
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ 1. LIVE DATA     │   │ 2. PHYSICS MODEL │   │ 3. LEARNED       │
│                  │   │                  │   │    PATTERNS      │
│ What the engine  │   │ What it SHOULD   │   │ What past        │
│ IS doing         │   │ be doing         │   │ failures looked  │
│                  │   │                  │   │ like             │
│ Telemetry,       │   │ Thermodynamics,  │   │ ML models on     │
│ 20 Hz            │   │ performance maps │   │ historical data  │
└────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
         │                      │                      │
         └──────────┬───────────┘                      │
                    ▼                                  │
            ┌───────────────┐                          │
            │   RESIDUAL    │◀─────────────────────────┘
            │ actual − expected                    interprets
            └───────┬───────┘
                    ▼
         THE DIGITAL TWIN STATE
```

**The residual is the twin.** Everything else is plumbing. If you remember one thing from this part, it is that a system computing meaningful residuals is doing twin-like work, and a system displaying raw values is not — no matter how good the 3D rendering is.

---

## 10.3 Why the residual is everything

Consider CHT = 130 °C.

| Context | Expected | Residual | Interpretation |
|---|---|---|---|
| Sea level, cruise, +15 °C OAT | 128 °C | **+2 °C** | Normal |
| 25,000 ft, cruise, −35 °C OAT | 108 °C | **+22 °C** | **Abnormal — investigate** |
| Sea level, climb, +45 °C OAT | 134 °C | **−4 °C** | Normal, even slightly cool |

**The same measurement is normal, alarming, or reassuring depending on context.** A threshold system cannot express this. A twin can, because the physics model supplies the expectation.

Three consequences that shape the whole architecture:

1. **Residuals are regime-independent.** A healthy engine produces near-zero residuals in *every* flight condition. This makes downstream statistics dramatically simpler ([Part VII §7.4](07_anomaly_detection.md)).
2. **Residuals need far less training data.** You are no longer asking a model to learn all of thermodynamics from examples — the physics provides it.
3. **Residuals are inherently explainable.** "CHT₂ is 22 °C above physics-expected" is a statement a propulsion engineer immediately understands ([Part VIII §8.8](08_fault_diagnosis.md)).

✅ This is precisely what "physics-informed AI", a PS-named innovation area, means in practice.

---

## 10.4 The physics model

### What it must compute

Given: RPM, throttle/MAP, altitude, OAT, airspeed, fuel flow —
Produce: expected CHT per cylinder, expected EGT per cylinder, expected oil temperature and pressure, expected fuel flow, expected power.

### The physical relationships that matter

⬜ At the fidelity appropriate for our prototype:

**Air density** — everything starts here:
```
ρ = p / (R · T)
```
Air density falls with altitude. Less oxygen means less power; less mass flow means less cooling. This single quantity drives most altitude effects.

**Power** — scales roughly with air density for a naturally aspirated engine:
```
P ≈ P_sealevel × (ρ / ρ_0)        (naturally aspirated)
```
A turbocharged variant (like the Rotax 914) maintains manifold pressure to a critical altitude, changing this relationship — worth noting since ✅ TAPAS prototypes have flown with a Rotax 914.

**Heat generation** — a fraction of fuel energy becomes waste heat in the head:
```
Q_gen ≈ ṁ_fuel × LHV × (1 − η_thermal)
```

**Heat rejection** — convective cooling, dependent on cooling airflow and temperature difference:
```
Q_rej ≈ h(ṁ_air, v) × A × (T_head − T_ambient)
```

**Equilibrium temperature** — where generation equals rejection. The residual is the gap between this and the measurement.

**Thermal dynamics** — the head has thermal mass, so it lags:
```
m·c · dT/dt = Q_gen − Q_rej
```
This first-order lag is why CHT changes slowly, and hence why a fast jump indicates a sensor fault ([Part VII §7.5](07_anomaly_detection.md)).

**Oil viscosity** — falls with temperature, which changes pressure at a given RPM. This is why oil pressure must be interpreted against both RPM *and* oil temperature.

### Performance maps

✅ The PS explicitly lists "Engine performance maps" as a system input. A performance map is a lookup table or fitted surface of measured engine behaviour: power, fuel flow and temperatures as functions of RPM, MAP, and ambient conditions.

⬜ **Our approach:** derive an approximate map from published Rotax operating data where available, and document every assumption. ✅ Rotax operator's manuals and EASA TCDS documents are publicly available and are the right source. ([OM-912 iS](https://avsport.org/acft/Rotax/912iS/912iS_operators_manual_d05875.pdf), [EASA TCDS E.121](https://www.easa.europa.eu/en/downloads/7633/en))

🔶 A detailed validated performance map for a specific engine is manufacturer data and generally not public. Our map will be an approximation, and we must label it as such. An approximate map still produces useful residuals, provided its error is smaller than the fault signatures we are looking for — and stating that condition explicitly is the mark of doing this properly.

### The model-error trap

> **Model error looks exactly like a fault.**

If the physics model says 108 °C and the truth for a healthy engine is 115 °C, every healthy engine shows a +7 °C residual, and the anomaly detector spends its life explaining a modelling mistake.

⬜ **Mitigation:**
1. **Calibrate on healthy data** — fit model parameters so residuals centre on zero for known-good flights.
2. **Track residual bias per engine** — a persistent offset is a model/installation artefact; a *growing* offset is degradation. Separating the two is essential.
3. **Monitor residual variance in healthy operation** — if it is comparable to your fault signatures, the model is not accurate enough to detect them, and you must improve it before blaming the classifier.

---

## 10.5 Twin state estimation

The twin's state is not merely the last telemetry frame. It is a filtered estimate that combines the measurement with the model's prediction.

✅ Hybrid digital twins combining physics-based simulation, **Kalman filtering**, and ML models for fault diagnosis and RUL are an established pattern. ([UAV piston engine PHM review](https://link.springer.com/article/10.1007/s10973-025-14728-1))

### Why filtering rather than raw values

```
Raw telemetry:     noisy, gappy, occasionally corrupt, arrives late
Physics model:     smooth, but drifts from reality
Kalman filter:     optimally combines both, weighted by their uncertainties
```

The filter gives three things we genuinely need:

1. **Noise reduction** without the lag a simple moving average would introduce.
2. **Gap handling** — when packets are lost (routine on this link, ✅ Part IV), the model propagates the state forward, and the estimate degrades gracefully with a widening uncertainty rather than freezing or jumping.
3. **Explicit uncertainty** — the covariance tells you how much to trust the current state, which feeds directly into how confidently downstream models should act.

⬜ **Our design:** an extended Kalman filter, or a simpler complementary filter for the prototype, per slow thermal state; direct pass-through with validity flags for fast states.

**The link-loss behaviour is a real design decision.** When telemetry stops, the GCS twin must show `STALE — last update T−47 s`, with widening uncertainty, and **never** a frozen value that looks live. Meanwhile the *onboard* twin keeps running on real data. This divergence is intrinsic and should be visible in the UI.

---

## 10.6 Full twin architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DIGITAL TWIN CORE (GCS)                        │
│                                                                     │
│  ┌──────────────┐      ┌────────────────────┐                       │
│  │ TELEMETRY IN │      │  FLIGHT CONTEXT    │                       │
│  │ (validated)  │      │  alt, OAT, IAS,    │                       │
│  │              │      │  throttle, phase   │                       │
│  └──────┬───────┘      └─────────┬──────────┘                       │
│         │                        │                                  │
│         │        ┌───────────────┴──────────────┐                   │
│         │        ▼                              │                   │
│         │  ┌─────────────────────────────┐      │                   │
│         │  │  PHYSICS ENGINE MODEL       │      │                   │
│         │  │  · air density              │◀─────┘                   │
│         │  │  · power / heat balance     │                          │
│         │  │  · thermal dynamics         │                          │
│         │  │  · performance maps         │                          │
│         │  │  · oil viscosity model      │                          │
│         │  └──────────┬──────────────────┘                          │
│         │             │ EXPECTED values                             │
│         ▼             ▼                                             │
│  ┌────────────────────────────────┐                                 │
│  │  RESIDUAL COMPUTATION          │                                 │
│  │  Δ = measured − expected       │                                 │
│  └──────────┬─────────────────────┘                                 │
│             ▼                                                       │
│  ┌────────────────────────────────┐                                 │
│  │  STATE ESTIMATOR (Kalman)      │                                 │
│  │  → smoothed state + covariance │                                 │
│  └──────────┬─────────────────────┘                                 │
│             ▼                                                       │
│  ╔════════════════════════════════════════════════════════════════╗ │
│  ║           TWIN STATE  (the authoritative object)               ║ │
│  ║  · measured values      · expected values                      ║ │
│  ║  · residuals            · uncertainty                          ║ │
│  ║  · health indices       · validity flags                       ║ │
│  ║  · degradation history  · staleness                            ║ │
│  ╚═══════╤════════════════════════════════════════════════════════╝ │
└──────────┼──────────────────────────────────────────────────────────┘
           │  everything below CONSUMES the twin state
  ┌────────┼────────┬──────────────┬──────────────┬─────────────┐
  ▼        ▼        ▼              ▼              ▼             ▼
Anomaly  Fault    RUL          Mission        Dashboard      Replay
detect   classify prognosis    simulation     (incl. 3D)     store
```

**The single architectural rule:** everything below the double line is a **consumer** of the twin state. The 3D view, the dashboard, the alerts — none of them compute anything. If you deleted all of them, the twin would still be detecting and predicting faults. ✅ This is the team's own stated test in the PS breakdown, and it is the right one.

---

## 10.7 What makes ours genuinely a twin

A checklist to test our own work honestly:

| Requirement | How we satisfy it | Test |
|---|---|---|
| **Continuously synchronised** | State updates on every telemetry frame | Cut the feed → UI shows STALE, not a frozen value |
| **Physics-based expectation** | Thermodynamic model runs alongside | Change altitude → expected values change |
| **Engine-specific, not generic** | Per-airframe calibration and baseline | Two engines with identical telemetry but different histories give different health |
| **Bidirectional influence** | Advisories change operator decisions | Go/No-Go recommendation alters the mission |
| **Independent of visualisation** | 3D consumes twin state only | Delete the 3D view → detection still works |
| **Simulatable** | Same physics runs on hypothetical inputs | Mission simulation works without live data |
| **Replayable** | State reconstructible from stored telemetry | Replay a flight → identical twin states |

The last two are what distinguish a twin from a shadow in practice: the model can run *without* the physical object, on hypothetical or historical inputs. A shadow cannot, because it has no model — only a data feed.

---

## 10.8 The flow from telemetry to decision

```
Telemetry frame arrives
   ↓
Validity check                     → invalid sensors flagged, excluded
   ↓
Physics model runs                 → expected values for current conditions
   ↓
Residuals computed                 → regime-independent deviation vector
   ↓
State estimator updates            → smoothed state + uncertainty
   ↓
Health indices recomputed          → per-subsystem 0–100 scores
   ↓
Anomaly detector scores            → "something is off" (0→1)
   ↓  [if above threshold]
Fault classifier runs              → named fault + confidence + evidence
   ↓
Degradation history updated        → trend slope, per indicator
   ↓
RUL re-estimated                   → hours + confidence interval
   ↓
Mission simulator evaluates        → "does RUL cover the planned sortie?"
   ↓
Advisory generated                 → specific recommended action
   ↓
Dashboard + alert + replay store   → operator sees it, and it is recorded
```

Each arrow is a well-defined interface. ⬜ Building them as explicit, individually testable stages — rather than one monolithic function — is what makes the system demonstrable and debuggable, and it directly serves the PS's "modular architecture for future scalability" requirement.

---

## 10.9 The 3D visualisation — correctly scoped

✅ The PS requires a "Visualization Dashboard" showing real-time health status, fault alerts, efficiency trends, maintenance advisory, and mission-wise reports. **It does not require 3D.**

⬜ Our Blender-based model is one skin over the twin's outputs. Its legitimate jobs:

- Spatial context — *which* cylinder, *where* on the engine
- Intuitive severity — colour mapping on the affected component
- Operator engagement in a demo

Its illegitimate jobs, which must never happen:

- Containing any detection or decision logic
- Being the only way to see a fault
- Consuming development time while a PS-required capability is unimplemented

✅ The team's own breakdown already classifies high-fidelity terrain and cinematic camera work as cosmetic and at risk of scope creep, to be addressed only after the required capabilities are proven. That judgment is correct and this course endorses it.

---

**Next:** [Part XI — Mission Simulation](11_mission_simulation.md)
