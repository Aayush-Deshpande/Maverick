# Datasets — ANUMAAN / DRDO SIH PS-26054

Catalogue of datasets for aero-piston-engine PHM on MALE UAVs.

**No dataset files are stored in this repository.** Each folder holds a `README.md` with the source, licence, structure, and acquisition instructions. Download into the folder locally; `.gitignore` keeps the data out of version control.

The reasoning behind these choices is in [Part XIV — Datasets](../ANUMAAN/docs/study/14_datasets.md) of the study course.

---

## The honest starting position

**There is no public run-to-failure dataset for an aero piston engine on a MALE UAV with the eight PS fault modes labelled.**

We searched and did not find one. Such data would require destroying instrumented aero engines, and for a defence platform would likely be restricted. This shapes everything below.

| Tier | Meaning | What may be claimed |
|---|---|---|
| **Directly relevant** | Same machine class, same faults | None exist publicly |
| **Proxy** | Different machine, transferable *methods* | Method validation only |
| **Synthetic** | Our own physics model | Pipeline validation and demonstration only |

> **Rule:** never present a proxy result as an engine result, and never present a synthetic result as independent validation. A bearing dataset is not an engine dataset.

---

## Folder map

| Folder | Contents | Tier |
|---|---|---|
| [`Engine_PHM/`](Engine_PHM/README.md) | C-MAPSS, N-CMAPSS turbofan degradation | Proxy — RUL methods |
| [`Piston_Engine/`](Piston_Engine/README.md) | **Empty — nothing public found.** Documents the gap and how to close it | — |
| [`Aviation/`](Aviation/README.md) | Rotax manuals, EASA TCDS, public engine documentation | Reference |
| [`Vibration/`](Vibration/README.md) | General vibration and machine-signal datasets | Proxy — DSP methods |
| [`Bearing/`](Bearing/README.md) | CWRU, Paderborn, XJTU-SY, FEMTO, IMS, MFPT | Proxy — vibration classification and RUL |
| [`RUL/`](RUL/README.md) | Index of run-to-failure sources across folders | Proxy |
| [`UAV_Telemetry/`](UAV_Telemetry/README.md) | ALFA, UAV-SEAD | Proxy — UAV flight context |
| [`CAN_ECU/`](CAN_ECU/README.md) | CAN/DBC tooling, our own DBC. Rotax mapping is proprietary | Reference |
| [`Environmental/`](Environmental/README.md) | ISA atmosphere, Indian operating environments | Reference |
| [`Synthetic/`](Synthetic/README.md) | Our generator's output and scenario library | Ours |

---

## Quick summary

| Dataset | Machine | Faults | RUL | Vibration | Licence | Use |
|---|---|---|---|---|---|---|
| **C-MAPSS** | Turbofan | Degradation | ✅ | ❌ | US Gov work | RUL pipeline + benchmark |
| **N-CMAPSS** | Turbofan | Degradation | ✅ | ❌ | US Gov work | Harder RUL variant |
| **CWRU** | Bearing | Seeded | ❌ | ✅ 12 kHz | Check site | Vibration classification dev |
| **Paderborn** | Bearing | Seeded + **natural** | ❌ | ✅ | Check site | More realistic vibration |
| **XJTU-SY** | Bearing | Natural | ✅ | ✅ 25.6 kHz | Check repo | **Vibration-based RUL** |
| **FEMTO** | Bearing | Natural | ✅ | ✅ 25.6 kHz | Check repo | Vibration RUL, PHM 2012 |
| **IMS** | Bearing | Natural | ✅ | ✅ | US Gov work | Natural defect progression |
| **ALFA** | Fixed-wing UAV | Sudden + surfaces | ❌ | ❌ | Check repo | Real UAV telemetry |
| **MIMII** | Industrial | Various | ❌ | acoustic | CC BY-SA 4.0 | Unsupervised anomaly dev |
| **SKAB** | Pump circuit | Induced | ❌ | ❌ | Check repo | Multivariate TS anomaly |
| **Ours** | **Piston** | **All 8 PS** | ✅ | ✅ | Ours | Pipeline + demo |

⚠️ **Verify licences at the source before use or redistribution.** Terms change, and the summary above is a pointer, not legal advice. Cite every dataset in any publication or presentation.

---

## Our data strategy

**Phase A — Method development on public proxies.** Validate each component where established benchmarks exist: RUL on C-MAPSS, vibration classification on Paderborn, vibration RUL on XJTU-SY, multivariate anomaly on SKAB.

**Phase B — Synthetic piston-engine data.** Build the physics-based generator covering all eight PS faults.

**Phase C — Cross-validation.** Apply Phase-A-validated methods to Phase-B data. Report both sets of numbers, clearly distinguished. Never merge them into one headline figure.

**Phase D — Real data acquisition (roadmap).** An instrumented Rotax test-cell campaign with a high-rate vibration channel, seeded-fault runs, and ideally a run-to-failure programme. This belongs in the deployment roadmap the PS asks for as a deliverable.

---

## Download helper

`fetch.py` in this folder downloads the openly-accessible datasets (C-MAPSS, IMS). Others require registration or manual download — the per-folder READMEs give instructions.

```bash
python Datasets/fetch.py --list
python Datasets/fetch.py --dataset cmapss
```
