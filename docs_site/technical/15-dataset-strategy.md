# Dataset Strategy

There is no public dataset that combines aero piston engine telemetry, the eight PS-26054 fault modes, and run-to-failure labeling. Producing one would mean deliberately damaging instrumented aircraft engines until they fail, and for a defence-relevant platform the resulting data would likely be restricted even if it existed. This is not a gap unique to ANUMAAN. It is the normal starting condition for prognostics and health management research on any machine whose failure data is operationally sensitive, safety-critical, or simply too expensive to generate by destroying real hardware.

The standard response in the PHM literature, and the one ANUMAAN follows, is a tiered dataset strategy: validate individual methods against public benchmarks that share a relevant characteristic with the target problem (a similar failure mechanism, a similar sensing modality, a similar operating envelope) and then apply the validated methods to a physics-based synthetic model of the actual target machine. Each tier answers a narrower question than "does this system detect engine faults," and the combination of tiers is what makes the full claim defensible.

## The dataset catalogue

Twelve dataset sources are used across four public tiers, one project-specific engine-class proxy tier, and the project's own synthetic generator. The table below covers every dataset in the catalogue, drawn from the repository's dataset documentation.

| Dataset | Machine type | Contents | Sampling / structure | Engineering question / subsystem | Evaluation purpose |
|---|---|---|---|---|---|
| **C-MAPSS** | Simulated turbofan | Run-to-failure trajectories: engine ID, cycle, three operational settings, twenty-one sensor channels, across four subsets of increasing operating-condition and fault-count complexity | 26 channels per cycle, cycle-indexed | RUL pipeline development | The standard published benchmark for RUL estimation and the asymmetric-scoring evaluation convention used across the field |
| **N-CMAPSS** | Simulated turbofan | Higher-fidelity successor to C-MAPSS with more realistic flight profiles | Flight-cycle structured, harder operating-condition variation | RUL pipeline development, harder variant | Stress-tests a RUL method beyond what C-MAPSS alone can validate |
| **CWRU** | Bearing test rig | Seeded inner race, outer race, and ball bearing defects | 12 kHz vibration | Vibration and order-tracking methodology | Vibration classification development on laboratory-seeded faults |
| **Paderborn (KAt-DataCenter)** | Bearing test rig | Both artificially induced and naturally worn bearing damage, motor current alongside vibration | Multi-channel, vibration plus current | Vibration and order-tracking methodology | A more realistic complement to CWRU's seeded-fault laboratory data |
| **XJTU-SY** | Bearing test rig | Full run-to-failure bearing trajectories | 25.6 kHz vibration | Vibration and order-tracking methodology, RUL | The closest public analogue to predicting remaining life directly from a vibration signal |
| **FEMTO / PRONOSTIA** | Bearing test rig | Run-to-failure bearing data used in the IEEE PHM 2012 challenge | 25.6 kHz vibration | Vibration and order-tracking methodology, RUL | A second independent run-to-failure vibration benchmark |
| **IMS** | Bearing test rig | Naturally developed bearing defect histories through to failure | Vibration, long-duration natural degradation | Vibration and order-tracking methodology | Natural (not seeded) defect progression, complementing CWRU's artificial faults |
| **ALFA** | Fixed-wing UAV | Forty-seven autonomous flights, including twenty-three sudden full engine failure scenarios and flights across seven control-surface fault types, with ground-truth fault time and type | Flight telemetry, labeled fault onset | UAV flight context, fault-onset detection latency | Real flight-dynamics telemetry and practice measuring detection latency against a known ground-truth fault time |
| **NASA ACES** | UAV (Altus II, Rotax 914 Turbo) | Real operational flight telemetry from a four-cylinder Rotax 914 Turbo, the same engine class and platform class ANUMAAN targets | Aircraft-state and mechanical telemetry, no labeled faults | UAV flight context, telemetry realism | Genuine healthy-flight telemetry from the same engine family, without run-to-failure or fault labels |
| **SKAB** | Water-pump circuit (industrial) | Labeled multivariate time series with induced anomalies | Multivariate sensor time series | Multivariate anomaly detection methodology | Realistic class imbalance for developing and testing anomaly detection against sparse anomaly labels |
| **MIMII** | Industrial machines (valves, pumps, fans, slide rails) | Acoustic recordings under normal and anomalous operation | Acoustic time series | Multivariate anomaly detection methodology | Unsupervised anomaly detection development on a modality distinct from vibration or engine telemetry |
| **Marine diesel / 3500-DEFault / journal-bearing proxies** | Reciprocating engine (marine diesel, diesel crank-torsional and cylinder-pressure, IC-engine journal bearing) | Real induced-fault engine data (marine diesel, five induced faults), crank-torsional and cylinder-pressure feature data, and journal-bearing vibration | Varies by source | Engine-class methodology | Closer in machine class to a reciprocating piston engine than the turbofan and pure-bearing datasets above, though not aero-rated or UAV-installed |
| **ANUMAAN synthetic generator** | Aero piston engine (project's own physics model) | All eight PS-26054 fault modes, full mission phase model, perfect ground truth by construction | Configurable environments and fault onset timing | Full pipeline validation, all eight fault modes | End-to-end pipeline validation, coverage of fault modes no public dataset offers, controllable fault-onset timing for measuring detection latency |

## Why a tiered strategy, not a single dataset

A single dataset that covered the target machine, the target faults, and run-to-failure ground truth would be the ideal input, but it does not exist publicly for this combination and could not be produced without damaging real instrumented aircraft engines. Treating this as a blocking problem would be a mistake: PHM research routinely validates a detection or prognostics method on a dataset that shares a mechanism with the target problem, not the target machine itself, precisely because run-to-failure data on the actual asset of interest is almost always unavailable. The correct discipline is not to avoid proxy data but to be explicit about what each proxy does and does not establish, and to never present a proxy result as if it were a result on the target engine.

### RUL methodology

C-MAPSS and N-CMAPSS are turbofan datasets, not piston engine datasets, but they are the field's standard benchmark for the RUL estimation problem itself: given multivariate degrading sensor trends, predict remaining cycles to failure, and be scored on the field's asymmetric penalty convention that penalizes late predictions more heavily than early ones. Validating a RUL pipeline's mechanics and its scoring behavior on C-MAPSS establishes that the pipeline is sound before it is pointed at piston-engine degradation trajectories from the synthetic generator or the engine-class proxies.

### Vibration and bearing methodology

CWRU, Paderborn, XJTU-SY, FEMTO, and IMS form a five-dataset cluster covering seeded and naturally developed bearing faults at high sampling rates, with XJTU-SY and FEMTO additionally offering full run-to-failure trajectories. This cluster is what validates the order-tracking and envelope-analysis methodology used against the engine's own gearbox and bearing channels: tach-synchronous resampling and Hilbert envelope demodulation are general vibration-diagnostics techniques, and these five datasets are where that general capability is exercised and checked, independent of engine make or fault list.

### UAV flight context

ALFA and NASA ACES address a different question: not "can the method detect a fault in a vibration signal" but "does the pipeline behave sensibly against real flight telemetry, with the dynamics and noise characteristics of an actual airframe." ALFA's labeled sudden-failure and control-surface fault events give a ground-truth timestamp to measure detection latency against, on real flight data rather than simulation. NASA ACES is notable specifically because it comes from the Altus II UAV, powered by a four-cylinder Rotax 914 Turbo, the same engine family and platform class ANUMAAN targets, making it the closest available real-world telemetry analogue even though it carries no fault labels or run-to-failure record.

### Multivariate anomaly detection methodology

SKAB and MIMII are both industrial rather than aeronautical, but they exercise the anomaly-detection problem in its general form: multivariate sensor time series (SKAB) and acoustic signatures (MIMII) with realistic class imbalance between normal and anomalous operation. This is where the detection layer's behavior under sparse-anomaly conditions is developed and checked before it is applied to engine telemetry.

### Engine-class proxies

The marine diesel dataset, the 3500-DEFault diesel crank-torsional and cylinder-pressure dataset, and the IC-engine journal-bearing dataset sit closer to the target machine class than any of the tiers above: they are reciprocating engines, not turbines or generic industrial equipment. They are not aero-rated and were not collected from a UAV installation, but they let combustion- and crank-related methodology be checked against real reciprocating-engine behavior rather than only against a turbofan or a bearing rig.

### The synthetic generator

None of the public tiers can supply all eight PS-26054 fault modes on the actual target engine with known ground truth, because no such public source exists. ANUMAAN's own physics-based synthetic generator closes that gap: it produces telemetry for all eight fault modes across the full mission phase model, with perfect ground truth by construction because the fault is injected into the physics rather than inferred after the fact. This is what makes end-to-end pipeline validation possible, including measuring detection latency against a precisely known fault-onset time, something no public dataset in this catalogue can offer for this specific fault taxonomy.

## Dataset-to-model pipeline

```mermaid
flowchart LR
    subgraph RUL["RUL methodology"]
        CMAPSS["C-MAPSS / N-CMAPSS"]
    end
    subgraph VIB["Vibration and order-tracking"]
        BRG["CWRU / Paderborn / XJTU-SY / FEMTO / IMS"]
    end
    subgraph CTX["UAV flight context"]
        UAV["ALFA / NASA ACES"]
    end
    subgraph ANOM["Multivariate anomaly methodology"]
        IND["SKAB / MIMII"]
    end
    subgraph PROXY["Engine-class proxies"]
        ENG["Marine diesel / 3500-DEFault / journal bearing"]
    end
    subgraph SYN["ANUMAAN synthetic generator"]
        GEN["All 8 fault modes, full mission profile"]
    end

    CMAPSS --> RULPIPE["RUL pipeline"]
    BRG --> ORDER["Order tracking / envelope analysis"]
    UAV --> TELEM["Flight telemetry realism"]
    IND --> NOVELTY["Novelty / anomaly detection"]
    ENG --> COMBUST["Combustion / crank methodology"]
    GEN --> FULL["Full pipeline validation, all 8 faults"]

    RULPIPE --> TWIN["ANUMAAN digital twin"]
    ORDER --> TWIN
    TELEM --> TWIN
    NOVELTY --> TWIN
    COMBUST --> TWIN
    FULL --> TWIN
```

*Each dataset tier validates the specific method or subsystem it is suited to; the synthetic generator is the only source that exercises the full pipeline against the actual fault taxonomy.*

## How the tiers connect

The discipline running through this strategy is that a method is validated where a suitable public benchmark exists, and the same validated method is then applied to the project's own physics-based data, with each result reported against its own dataset rather than blended into a single headline figure. A RUL scoring result on C-MAPSS says the scoring and pipeline mechanics are correct. A vibration classification result on Paderborn says the order-tracking and envelope-analysis chain works on real bearing signals. A detection-latency result on the synthetic generator says the full pipeline, exercised against all eight PS-26054 fault modes with known ground truth, behaves correctly end to end. None of these results is a substitute for the others, and none of them is presented as if it were flight validation on a real aero piston engine.

Reference engine specifications used throughout the physics model, including bore, stroke, compression ratio, and firing order for the Rotax 912 iS and 914, are drawn from published manufacturer documentation rather than from any dataset in this catalogue. An instrumented test-cell campaign, and ultimately flight validation on real hardware, is the natural next phase of this data strategy: the tiered public-benchmark and synthetic-data approach establishes that the methods work, and a physical test campaign is what would close the loop with genuine run-to-failure evidence on the target machine class.

## Related systems

- [Mission Reliability](17-mission-reliability.md)
- [Mission Planning](16-mission-planning.md)
- [The 3D Digital Twin](18-3d-digital-twin.md)
