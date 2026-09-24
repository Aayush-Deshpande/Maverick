# 12 — Datasets: Why, Which, and Exactly How They Plug In

*Written 23 September 2026, after inspecting the files that actually arrived on disk. It answers three questions: what the downloads are, whether they are needed, and how they are implemented.*

---

## 1. What they are, and why they are needed

**PS §4, deliverable 6:** *"Demonstration using simulated **or real** engine datasets."*

✅ No public dataset exists for an aero piston engine on a MALE UAV with labelled faults. So a system trained and tested only on our own simulator can only prove that it agrees with itself (08 §1). The downloads are the way out: **real signals from neighbouring machines**, each used to prove **one specific component**, never "the whole system".

| We claim… | …so we must show it on real data from… |
|---|---|
| The thermal twin tracks a real engine and doesn't cry wolf | A real Rotax 914 in flight (**ACES**, already on disk) |
| Per-cylinder combustion/injection diagnosis from crank torsional orders works | Diesel crank-torsional data with per-cylinder fault labels (**3500-DEFault**) |
| Anomaly detection works on a real diesel | A real diesel with induced faults (**marine engine**) |
| The vibration DSP (order tracking, envelope, novelty) works at real kHz rates | Real bearing vibration at 12–64 kHz (**CWRU**, **Paderborn**) |
| RUL, PHM metrics and **federated** RUL work | The standard run-to-failure benchmark (**C-MAPSS**) |
| Battery health (PS §3B) | Real battery ageing (**NASA battery**) |
| Detection works in real UAV flight | Real UAV flights with engine failures (**ALFA**) |
| The CAN intrusion detector works | Real CAN attacks (**ROAD**, **SynCAN**) |

**Rule:** a proxy result is never presented as an engine result, and a simulation result is never presented as independent validation (as [`Datasets/README.md`](../../Datasets/README.md) already says). Reports always keep three columns separate: **simulation**, **public proxy** and **real flight**.

---

## 2. Is each one needed? Triage after inspecting the actual files

| Dataset | Status | Verdict | Why |
|---|---|---|---|
| NASA ACES (Rotax 914, Altus II) | On disk | **Essential** | Only real flight data from a MALE-class piston engine. Blocked on the EGT channel-binding fix. |
| **3500-DEFault** (diesel, crank torsional) | ✅ On disk | **Essential, and the best find** | 3,500 samples × 97 columns: **24 torsional orders (frequency, amplitude, phase)** plus per-cylinder max pressure; labels are **per-cylinder compression faults (`fcomp1–6`) and combustion faults (`fcomb1–6`)** on a 6-cylinder diesel, at 0/15/30/60 dB noise. 🔶 It is model-generated (a published diesel model with added noise), so it is a *proxy*, not flight data. It is still exactly the input for the fly-vs-RF test on order spectra (§4, E06). Stored as MATLAB `table` objects, so a one-time conversion is needed (§3.3). |
| **C-MAPSS** | ✅ On disk | **Essential** | Standard RUL benchmark; FD001–FD004 act as four "operators" for federated learning |
| **CWRU** (161 files, 12/48 kHz) | ✅ On disk | **Essential** | Canonical vibration benchmark; validates the DSP chain at real sample rates |
| **ALFA** (47 real UAV flights) | ✅ Processed + telemetry on disk | **Essential** | Real fixed-wing UAV, **engine-failure** flights, per-topic CSVs with ground truth |
| **Marine diesel engine faults** | ⏳ Blocked by Zenodo's traffic filter | **Essential** | The only *real* diesel with induced faults. Retry with one connection. |
| **ROAD** CAN intrusion | ⏳ Blocked by Zenodo | **Essential for the secure-telemetry claim** | Real vehicle CAN with fuzzing, fabrication and masquerade attacks |
| **Paderborn** (32 bearings, 64 kHz) | ⏳ ~half done | Useful | **Artificial vs real damage**, a real-world analogue of sim-to-real transfer; vibration + motor current + speed + torque |
| **NASA battery** | ✅ On disk | Useful | Battery state of health / RUL for the PS's battery item |
| SynCAN | ⏳ Pending | Useful | Synthetic CAN IDS, complements ROAD |
| SKAB | ✅ On disk | Useful | Sanity check for our anomaly-scoring protocol against a public leaderboard |
| IMS, FEMTO | ⏳ Pending | Optional | Vibration run-to-failure (bearing RUL). Only needed if we claim vibration-based RUL. |
| N-CMAPSS (15.8 GB) | ⏳ Queued last | **Optional, and the first thing to cut** | Only for federated learning at scale; C-MAPSS already covers the claim |
| MIMII DG/DUE (gearbox, bearing) | ⏳ Blocked by Zenodo | Optional | Domain-shift audio; nice for personalisation experiments, not required |
| NASA randomized battery | ⏳ Pending | Optional | Extends the battery experiment |
| **Engine Journal Bearings** (Mendeley) | ✅ On disk (1.4 GB extracted) | **Low value** | On inspection it holds **shaker-test report documents**: `.docx` summaries with per-channel RMS values and `.rtf` files with *embedded chart images*. There are no raw waveforms. At most usable for condition-level RMS comparisons. Candidate for deletion. |

**Net:** the essential set is **ACES, 3500-DEFault, C-MAPSS, CWRU, ALFA, the marine diesel set and ROAD**, all small. Everything else is supporting or optional.

---

## 3. How they plug in: the architecture

### 3.1 Principle: each dataset enters at the layer it validates

A bearing dataset never passes through the engine twin, because it isn't an engine. It goes straight to the DSP and novelty components. **Only flight telemetry (ACES, ALFA) is replayed through the full pipeline**, as if it were live.

```
                        ┌────────────────────── full pipeline (replay as live) ─────────────────────┐
 ACES, ALFA ──► ReplaySource ──► canonical Frame ──► edge node ──► link ──► twin ──► diagnosis ──► HMI
                        └────────────────────────────────────────────────────────────────────────────┘
 CWRU, Paderborn, IMS, FEMTO ──► SignalRecord ──► DSP core (order tracking, envelope) ──► novelty / recognisers
 3500-DEFault, marine, SKAB  ──► FeatureTable ──► detectors / recognisers / bake-off
 C-MAPSS, N-CMAPSS, battery  ──► RunToFailure ──► prognostics (dual path, conformal) ──► federated experiments
 ROAD, SynCAN                ──► CanLog ──► CAN intrusion detector (+ physics-integrity analogue)
```

### 3.2 Code layout

```
backend/datasets/
    __init__.py
    base.py          DatasetCard (name, machine, licence, tier, what it may prove) + provenance
                     read from Datasets/MANIFEST.json (sha256 recorded into every result)
    records.py       SignalRecord · FeatureTable · RunToFailure · CanLog  (plain dataclasses)
    aces.py          → wraps existing backend/telemetry/aces_loader.py, yields canonical Frames
    alfa.py          per-flight CSV topics → Frames + ground-truth failure time
    cmapss.py        FD001–FD004 train/test/RUL → RunToFailure (unit-grouped)
    cwru.py          .mat keys X###_DE_time / _FE_time / _BA_time / RPM → SignalRecord (fs from folder: 12k/48k)
    paderborn.py     .mat struct Y{vibration_1 @64 kHz, phase_current_1/2 @64 kHz, speed/torque/force @4 kHz}
                     → SignalRecord; damage type from bearing code (K=healthy, KA/KI artificial|real, KB combined)
    default3500.py   Parquet (converted once, §3.3) → FeatureTable
                     X = F_k/A_k/P_k (24 orders) [+ Mp_1–6 as auxiliary], y = fcomp1–6, fcomb1–6, DP; noise level
    marine.py        (after download) → FeatureTable / SignalRecord depending on contents
    battery.py       nested .mat cycles → RunToFailure (capacity fade per cell)
    road.py, syncan.py  → CanLog (timestamp, arbitration id, dlc, payload, attack label)
experiments/
    E01_aces_sim2real_far.py … E14_*.py      one script per experiment (§4)
    run_all.py                               regenerates every result; writes JSON + markdown
docs/evaluation/                              generated only, never hand-edited
```

**Contracts every loader must meet:**

1. **Group keys for splitting.** Unit, bearing, flight, cell and noise level are exposed so that splits are never by random frame or window, which is the leakage behind most inflated benchmark numbers.
2. **The label is never inside the input.** Ground truth lives in a separate field, and a test asserts it (the lesson of the FlyHash `FAULT_ID` leak, 08 §5.D).
3. **Provenance.** Every loader returns the MANIFEST SHA-256 of each file it read, and every result JSON stores it.
4. **Units and sample rates are explicit** in every record. Nothing is inferred downstream.

### 3.3 One-time conversions (keep runtime dependencies small)

| Source format | Converter | Output |
|---|---|---|
| 3500-DEFault MATLAB `table` (MCOS objects that scipy cannot read) | `scripts/convert_3500_default.py` using **mat-io** (BSD-3-Clause), needed only for conversion | `Datasets/Piston_Engine/3500_default/*.parquet` |
| NASA nested zips | `python Datasets/download_all.py --extract-nested` | Unpacked in place |
| Paderborn `.rar` | Already extracted by the downloader (UnRAR) | `.mat` per measurement |

### 3.4 Dependencies to add

| Package | Why | Licence |
|---|---|---|
| `pyarrow` | Parquet | Apache-2.0 |
| `h5py` | N-CMAPSS (HDF5) | BSD |
| `flwr` | Federated experiments | Apache-2.0 |
| `pysindy` | SINDy (physics-informed) | MIT |
| `onnxruntime` | INT8 edge models | MIT |
| `opacus` | Differential privacy in federated learning | Apache-2.0 |
| `mat-io` | Conversion script only | BSD-3-Clause |

All are to be recorded in the SBOM (10 §2.6).

---

## 4. The experiment catalogue

Each experiment is one script. It produces one JSON and one report section, and it states which PS clause it serves.

| ID | Dataset | Component under test | Protocol | Compared against | Metrics | PS clause |
|---|---|---|---|---|---|---|
| **E01** | ACES | Thermal twin + detectors on **real healthy flight** | Fix EGT binding → replay all granules → twin + threshold baseline | Threshold monitor | Sim-to-real error per channel; **false alarms per flight hour with 95 % upper bound** | Background; §3A; §3C |
| E02 | ACES | Full pipeline as live replay over the link emulator | 1× replay; 1–20 kbit/s; injected link loss | — | End-to-end latency, dropped frames, store-and-forward recovery | §2 replay; §3A ingestion |
| **E03** | C-MAPSS | Dual-path RUL + conformal intervals | Unit-grouped splits; standard test sets | Published baselines | RMSE, NASA score, **PH, α-λ, RA**, interval coverage | §3D; F12/F38/F60 |
| **E04** | C-MAPSS FD001–FD004 as 4 operators | **Federated RUL** | Local / centralised / FedAvg / FedProx / personalised; then 1–2 **failure-masking poisoners** | Robust aggregation ± personalisation ± **canary gate** | Accuracy per client; attack success rate; bytes per round | **§5 federated learning** |
| E05 | C-MAPSS | SINDy / physics-informed degradation law | Fit on training units | Pure data-driven | Law sparsity; extrapolation error | **§5 physics-informed AI** |
| **E06** | **3500-DEFault** | **The fly-vs-RF bake-off on order spectra**, plus per-cylinder localisation | Train on healthy only (novelty), and on labelled faults (recognition); across 0/15/30/60 dB; hold one fault family out (open-set); k = 1/5/10 examples (few-shot) | FlyHash-FBF · FlyNN · **dense random-projection null** · RF · LightGBM · MLP · PCA-Mahalanobis | AUROC at fixed false-alarm rate; per-cylinder localisation accuracy; open-set detection; few-shot accuracy; latency and memory; **explanation-to-cylinder agreement** | §3C injector/combustion; §5 XAI; §5 edge AI |
| E07 | Marine diesel (after download) | Anomaly detection + fault classification on a **real** diesel | Train on baseline; test on 5 fault classes, split by recording | Same contenders as E06 | Detection at fixed false-alarm rate; classification F1 | §3C on real engine data |
| **E08** | CWRU, Paderborn | DSP chain (order tracking, kurtogram → envelope → defect orders) + novelty; **Paderborn artificial → real damage transfer**; edge latency at real sample rates under CPU/memory caps | Split by bearing (never by window) | Published envelope baselines | Defect-order detection; transfer accuracy; p99 latency under caps | §3C abnormal vibration; **§5 edge AI** |
| E09 | IMS, FEMTO (optional) | Vibration-based RUL | Run-to-failure split by bearing | — | PH, α-λ | §3D |
| E10 | NASA battery | Battery state of health / RUL (equivalent-circuit EKF + data-driven) | Split by cell | — | Capacity estimation error; RUL metrics | **§3B battery/alternator** |
| **E11** | ALFA | Engine-failure detection in real UAV flight | Replay flights; flight-phase conditioning | Threshold on engine telemetry | Detection delay after the ground-truth failure time; false alarms on no-fault flights | §3C in UAV context |
| **E12** | ROAD, SynCAN | CAN intrusion detection | Time-ordered splits; attack types held out | Published CAN IDS baselines | Point-wise **and** point-adjusted F1 (F62) side by side; masquerade detection | **§5 secure telemetry** |
| E13 | SKAB | Anomaly-scoring protocol sanity check | Official splits | SKAB leaderboard | Our numbers match the leaderboard's under the same protocol | §4 evidence credibility |
| E14 | MIMII DG/DUE (optional) | Domain generalisation; federated personalisation | Machines as clients | Local vs federated vs personalised | AUC on shifted domains | §5 federated learning |

**E06 is the direct answer to the question from 21 September** ("could the fly brain beat Random Forest?"). The data for it is already on disk, the input is exactly the high-dimensional order spectrum where expand-and-sparsify should work, the dense-projection null tests whether the fly structure itself matters, and the labels allow per-cylinder localisation. Whatever it shows, positive or negative, is publishable in our V&V report.

---

## 5. Where the results show up

- **V&V report** (generated by `experiments/run_all.py`). Three separated sections: simulation, public proxy, real flight. Every row carries the experiment ID, dataset, MANIFEST hash, split and date.
- **HMI "Evidence" page.** Each capability on the dashboard links to the experiment that supports it, so a judge can click from "per-cylinder injection health" to E06's numbers.
- **Pitch.** Each headline number names its dataset. For example: *"false alarms on 70 real flight-hours of a Rotax 914: X per hour"*, not *"99 % accuracy"*.

---

## 6. Order of implementation

| Step | Why this order |
|---|---|
| 1. `backend/datasets/` base + `records.py` + `default3500.py` (with the conversion) → **E06** | Data is on disk; it answers the fly-vs-RF question; it exercises FlyHash on the right input |
| 2. `cmapss.py` → **E03**, then **E04** | Data is on disk; covers RUL, PHM metrics and the federated-learning PS item |
| 3. `cwru.py`, `paderborn.py` → **E08** | Data mostly on disk; validates the DSP core and the edge-latency claims |
| 4. Fix the ACES EGT binding → **E01**, **E02** | The single most persuasive real-data numbers |
| 5. `alfa.py` → **E11**; `battery.py` → **E10** | Data on disk |
| 6. `road.py`, `syncan.py` → **E12**; `marine.py` → **E07** | After the Zenodo retries succeed |
| 7. Optional: E05, E09, E13, E14 | As time allows |

**Download housekeeping:**

- Retry Zenodo with `python Datasets/download_all.py --only marine,road --connections 1` once the traffic block clears.
- N-CMAPSS (15.8 GB) can be cancelled without losing any PS claim.
- The Engine Journal Bearings folder (1.4 GB of report documents) can be deleted.

*Audit set: [`README.md`](README.md) · [`11`](11_entire_ps_software_only.md) (software-only design) · this document (datasets).*
