# Bearing — vibration fault and run-to-failure datasets

Proxy tier. **These are bearing test rigs, not engines.** They validate signal processing and classification *methods*.

⚠️ **Critical caveat before using any number from these.** A piston engine is cyclic and impulsive — combustion events, valve impacts, piston reversals — while these rigs run a shaft at near-constant speed. Published accuracies here do **not** transfer. See [Part VIII §8.4](../../ANUMAAN/docs/study/08_fault_diagnosis.md).

---

## CWRU Bearing Data Center

| Field | Value |
|---|---|
| **Source** | Case Western Reserve University |
| **URL** | https://engineering.case.edu/bearingdatacenter |
| **Sampling** | 12 kHz (48 kHz for some drive-end records) |
| **Faults** | Seeded inner race, outer race, ball — several defect diameters |
| **Labels** | Fault type, size, motor load |
| **RUL** | ❌ No — condition snapshots, not trajectories |
| **Format** | MATLAB `.mat` files |
| **Licence** | Check the site before redistribution |
| **Relevance** | ★★★ method · ★ machine |

⚠️ Published 1D-CNN results reach ~97.6% here, and the literature notes this is **because of** the controlled laboratory environment. Treat any CWRU accuracy above ~97% as a statement about the dataset, not the method.

**Use for ANUMAAN:** validate the envelope-analysis and order-analysis pipeline on real vibration. If our implementation cannot find a known CWRU outer-race defect, it is broken.

---

## Paderborn (KAt-DataCenter) Bearing Dataset

| Field | Value |
|---|---|
| **Source** | Paderborn University, KAt-DataCenter |
| **URL** | https://mb.uni-paderborn.de/kat/forschung/kat-datacenter/bearing-datacenter |
| **Contents** | Artificially induced **and naturally worn** bearings; motor current alongside vibration |
| **Labels** | Fault type and severity |
| **RUL** | ❌ No |
| **Relevance** | ★★★★ method — **better than CWRU** |

**Why it is better:** it includes naturally-developed damage, not only machined defects. Published 1D-CNN accuracy drops to ~95.6% here from ~97.6% on CWRU — and that gap is itself a useful lesson about generalisation from seeded to natural faults.

**Use for ANUMAAN:** primary benchmark for vibration classification. Report Paderborn rather than CWRU as the headline proxy number, precisely because it is harder and more honest.

---

## XJTU-SY Bearing Run-to-Failure

| Field | Value |
|---|---|
| **Source** | Xi'an Jiaotong University / Changxing Sumyoung Technology |
| **URL** | https://biaowang.tech/xjtu-sy-bearing-datasets/ |
| **Sampling** | 25.6 kHz, 1.28 s recorded each minute |
| **RUL** | ✅ **Yes — full run-to-failure** |
| **Relevance** | ★★★★ — vibration **with** RUL |

**Why this matters specifically to us:** C-MAPSS gives RUL without vibration; CWRU/Paderborn give vibration without RUL. XJTU-SY gives both, which is exactly what our vibration-based prognostic path needs to demonstrate.

---

## FEMTO / PRONOSTIA

| Field | Value |
|---|---|
| **Source** | FEMTO-ST Institute, Besançon, France — PRONOSTIA platform |
| **Sampling** | 25.6 kHz, 0.1 s every 10 s |
| **RUL** | ✅ Yes — run-to-failure |
| **Known for** | IEEE PHM 2012 Prognostic Challenge |
| **Relevance** | ★★★★ vibration RUL |

Note the duty cycle: 0.1 s sampled every 10 s. This is itself instructive — even a lab rig does not store continuous high-rate vibration, for the same storage reasons discussed in [Part XII §12.7](../../ANUMAAN/docs/study/12_data_pipeline.md).

---

## IMS / NASA Bearing Dataset

| Field | Value |
|---|---|
| **Source** | Center for Intelligent Maintenance Systems, University of Cincinnati, via NASA PCoE |
| **URL** | https://catalog.data.gov/dataset/ims-bearings |
| **Direct download** | https://phm-datasets.s3.amazonaws.com/NASA/4.+Bearings.zip |
| **Contents** | Natural bearing defect history, run to failure |
| **Licence** | https://www.usa.gov/government-works |
| **Relevance** | ★★★★ — **naturally developed** defects |

Freely downloadable, permissive licence, natural degradation. A good first choice for development.

---

## MFPT

Machinery Failure Prevention Technology society bearing dataset. Smaller than the others; useful as an additional cross-check. Available via the MFPT society site.

---

## Bearing defect frequencies — why these datasets teach the right thing

Rolling-element bearings generate characteristic frequencies that are **non-integer multiples of shaft speed**:

| Abbrev. | Name | Location |
|---|---|---|
| BPFO | Ball Pass Frequency, Outer race | Outer race |
| BPFI | Ball Pass Frequency, Inner race | Inner race |
| BSF | Ball Spin Frequency | Rolling element |
| FTF | Fundamental Train Frequency | Cage |

Because they are non-integer, they do not coincide with shaft harmonics — which is what makes them separable from imbalance and combustion content. This same reasoning applies directly to our gearbox monitoring, which is why these proxies transfer at the *method* level even though the machine differs.

See [Part VI §6.7–6.8](../../ANUMAAN/docs/study/06_vibration_analysis.md).

---

## Use for ANUMAAN

| Dataset | Our use |
|---|---|
| IMS | First development target — free, permissive, natural faults |
| CWRU | Pipeline sanity check on real vibration |
| **Paderborn** | **Primary classification benchmark** — hardest, most honest |
| XJTU-SY / FEMTO | Vibration-based RUL validation |

**Splitting rule:** split by bearing unit or operating condition, never by window. Windows from one recording are near-duplicates.

---

## Citation

Cite each dataset's own reference publication. Check licence terms at source before redistribution.
