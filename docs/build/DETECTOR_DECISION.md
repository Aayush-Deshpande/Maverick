# Detector Decision — Jev, Fly-Brain, or Cheap Classical ML? One Universal Detector or Many?

*Decision record, 24 September 2026. Written to end the confusion, so it leads with the answer, then the evidence, then the caveats. Experiment: [`experiments/E17_detector_bakeoff_plant.py`](../../experiments/E17_detector_bakeoff_plant.py), raw results [`../evaluation/E17_detector_bakeoff.json`](../evaluation/E17_detector_bakeoff.json). Decisions D31–D33, D35 in [`DECISIONS.md`](DECISIONS.md).*

---

## 1. The answer

| Your option | Verdict | One-line reason |
|---|---|---|
| **Open-source Jev, run locally** | ⚠️ **Amended:** not on the 20 Hz path; tier-2 ground contender + advisory ranker on the selected engine (D37, bake-off W10). | It is a text/typed-decision model, not a numeric-telemetry detector; cannot run at 20 Hz × N engines; weeks old, unaudited. |
| **Fly-brain / connectome from an open-source lib** | ❌ **Connectome simulators: no.** ✅ **Fly-inspired *algorithm* (FlyHash / Fly Bloom Filter): candidate for one narrow job** — the Raspberry Pi tier-0 gate on *waveform* features — **only if it wins a test we have not run yet.** | Connectome sims are neuroscience tools, too heavy, no training loop for our data. The algorithm lost badly on tabular scalars (below); its home ground is high-dimensional spectra, untested. |
| **RF and traditional cheap ML** | ✅ **The backbone.** But the winning form is *not* "numerous random forests" — it is **engine-calibrated residuals + a cheap classical detector, with a universal classifier and optional per-engine specialisation.** | Measured: best detection (AUROC 0.976), engine-universal, 7 µs per sample. |

**One universal detector, or one per engine?** Both, layered — because *the universality lives in the normalisation layer, not the classifier*:

1. **Per-engine calibration** (cheap, needs only nominal data): a small model of "what this engine normally reads at this operating point" → z-scored residuals. This is engine-specific *data* but a universal *method*.
2. **Universal detector on the residuals** (Mahalanobis + max|z|): works on any engine that has a calibration, including one never seen before (measured, §3).
3. **Classifier for *which* fault:** one **universal** model by default (works for a new engine with zero labelled faults), **replaced by a per-engine model once that engine has labelled data** (measured +3 to +5 points).
4. **Physics/waveform channel for what scalars cannot see** (injector faults: §4).

## 2. What we compared (and did not)

| Family | Tested in E17? | How |
|---|---|---|
| Random Forest — per-engine, universal, universal+class flags, leave-one-engine-out | ✅ | macro-F1 over nominal + up to 6 fault classes |
| Fly-inspired novelty (FlyHash + Fly-Bloom-Filter-like memory) | ✅ (untuned, our own implementation of the published algorithm) | AUROC, TPR at 1 % false-alarm rate |
| Mahalanobis, max\|z\| threshold ("smart threshold"), Isolation Forest | ✅ | same |
| Jev / OpenJev | ❌ | reasoned from architecture (§5) |
| Connectome spiking simulators | ❌ | reasoned from architecture (§5) |
| Fly-inspired methods on **high-dimensional waveform features** | ❌ **not tested — this is the one open question** | backlog W5 |
| Deep 1-D CNN, zero-shot time-series foundation model | ❌ | backlog W5 / W8 |

**Design guarantees:** train and test use **different plant seeds** (different physical builds, different sensor biases); the split is by run, never by frame; novelty detectors train on nominal data only; features are engine-agnostic (13 numbers per frame regardless of cylinder count).

## 3. Results (simulation, tabular thermal channels, 5 engines)

Engines: Rotax 912 iS, 914, 915 iS, Austro AE300, VRDE-class CRDi. Per engine: 16 nominal + 30–36 faulty runs. Faults visible on thermal channels: MISFIRE, COOLING_DEGRADATION, OIL_PRESSURE_LOSS, AIR_FILTER_BLOCKAGE, SENSOR_STUCK, BOOST_LEAK (turbo engines only).

### A. Which fault is it? (macro-F1, mean over the 5 engines, tested on unseen builds)

| Setup | Macro-F1 | Reading |
|---|---|---|
| Per-engine RF (each engine's own labelled data) | **0.904** | Best, needs labelled faults for every engine |
| Per-engine RF, *no* normalisation | 0.897 | Normalisation barely matters *within* one engine… |
| Universal RF (all engines' data, no engine info) | 0.852 | −5 points vs per-engine |
| Universal RF + engine-class flags (diesel?, turbo?) | 0.876 | Cheap flags recover half the gap |
| **New engine** — universal RF, engine never seen, calibrated on nominal data only | **0.840** | Only −6 points vs the per-engine ideal, with **zero** labelled faults for that engine |
| New engine, **no** normalisation | 0.794 | …but it matters a lot *across* engines (+4.6 points) |

### B. Is anything wrong? (novelty/anomaly detection, trained on nominal data only)

| Detector | AUROC / TPR @ 1 % false alarms — per-engine | — one universal detector | — new engine (leave-one-out) |
|---|---|---|---|
| **Mahalanobis on calibrated residuals** | **0.976 / 0.941** | 0.974 / 0.942 | **0.973 / 0.939** |
| max\|z\| ("smart threshold") | 0.950 / 0.837 | 0.950 / 0.837 | 0.950 / 0.837 |
| FlyHash-FBF (fly-inspired, untuned) | 0.836 / 0.143 | 0.858 / 0.112 | 0.850 / 0.124 |
| Isolation Forest | 0.715 / 0.127 | 0.728 / 0.171 | 0.734 / 0.181 |

**The headline:** with per-engine calibration, one universal anomaly detector performs the same as a dedicated one (0.974 vs 0.976) and the same on an engine it has never seen (0.973). That is the strongest evidence for the "dropdown switches instantly" architecture: **you do not need N detectors, you need N calibrations.**

### C. Cost (this laptop; a Raspberry Pi 5 core will be roughly 3–6× slower — 🔶 estimate, not measured)

| Operation | Time | Note |
|---|---|---|
| Mahalanobis score | **7 µs** | |
| FlyHash-FBF score | 26 µs | cheap, but see §3B |
| Residual/feature computation | 344 µs | dominated by the regression call; can be optimised to a matrix multiply |
| Random Forest, sklearn, **one row** | **11,500 µs** | ⚠️ a trap, see below |
| Random Forest, batch of 20 | 616 µs per sample | 19× cheaper per sample when batched |
| Isolation Forest, one row | 12,700 µs | same trap |

⚠️ **Trap:** calling scikit-learn one row at a time costs ~11.5 ms. Five engines × 20 Hz = 100 calls/s ≈ **1.15 CPU-seconds per second — infeasible.** The fix is architectural and already in D16: a cheap gate runs every frame; the RF runs **only on flagged frames**, **batched**, or from a compiled forest (ONNX Runtime / hand-rolled tree arrays). The existing live pipeline already gates the RF; keep that.

## 4. The blind spot no tabular detector can fix

We probed every plant fault for its effect on all 13 thermal/electrical channels. **INJECTOR_COKING, INJECTOR_NEEDLE_STICK, RAIL_PRESSURE_DECAY and TURBO_BEARING_WEAR change nothing on any scalar channel** (measured Δ = 0.0). They act only on the crank/rail waveform — which is exactly the earlier finding that "thermal residuals missed injector coking; the crank channel caught it." For a common-rail diesel, injector health is the *primary* fault family (D01). So:

> **A scalar-only system — ours today, and (per `audit/01`/`05`) all 11 competitor teams we analysed — is structurally blind to the most important diesel faults.** The waveform pipeline (§6, `MULTI_ENGINE_ARCHITECTURE.md` §7) is not an extra; it is the only route to detecting them.

## 5. Why Jev and the connectome were first ruled out (SUPERSEDED — see addendum and D36/D37)

> Correction 24 Sep 2026: this section assumed M4-Pro-class hardware and all-engines-concurrent heavy inference. Both were wrong. The connectome reservoir was then **tested** (E19) and kept; Jev is re-admitted as a tier-2 ground contender (D37).

**Jev / OpenJev.** Jev is a *typed-decision language model*: text state in, calibrated choice out. Open reproductions found on 24 Sep: `Open-Jev-27B-v1.1` (27 B parameters — needs a large GPU), `razorback16/openjev` (a diffusion-LM server), `Verdict-open-jev` (ModernBERT 151 M, claims < 35 ms per decision on GPU). Problems for *detection*: (1) our input is a numeric time series — it would have to be serialised to text; (2) even 35 ms × 5 engines × 20 Hz = 3.5 CPU-seconds/second on a GPU-less box; (3) all are weeks old, unaudited, with differing licences and base models; (4) a black-box typed choice is the opposite of the explainable, certifiable evidence path (D02). **Allowed role:** ranking maintenance actions from a fixed list at the ground station, on-prem, logged, never auto-actioned (D33) — or, better, distil its decisions into a transparent policy (the Model Kombat lesson).

**Connectome simulators** (`philshiu/Drosophila_brain_model`, `flymsg`, several `fly-brain` forks, `drosophila-brain-mlx`). These are leaky-integrate-and-fire *neuroscience* simulators of ~139 k neurons; the fastest reported (Apple M4 Pro, MLX) is 0.29 s per *biological* second — not real-time on a Pi. They have no mechanism to learn from engine telemetry. Our own `mk-jev-fly-brain` experiments showed the competence came from the readout and reward, not the wiring (the shuffled-connectome control kept 23–1 against the rule bot). **Not used.** (Not benchmarked here; ruled out on architecture and on that evidence.)

**Fly-inspired *algorithms* — the part worth keeping.** Open-source options, verified 24 Sep:

| Library | Licence | Form | Verdict |
|---|---|---|---|
| [`rithram/fbfc`](https://github.com/rithram/fbfc) — Fly Bloom Filter Classifier (Ram & Sinha, KDD 2021) | **MIT** | Python 3.8 research code, not a package | ✅ usable as a reference/fork |
| [`clembarr/ffbf-novelty-detector`](https://github.com/clembarr/ffbf-novelty-detector) | **none** (GitHub API: no licence) | Rust + Python (PyO3); streaming, forgetting, "4 µs per novelty()" on 384-d (author's claim) | ⚠️ **cannot legally be shipped without the author's permission** (no licence = all rights reserved). Attractive fit for the Pi; ask the author to add a licence, or reimplement from the paper |
| [`dataplayer12/Fly-LSH`](https://github.com/dataplayer12/Fly-LSH) | not verified | LSH implementation | reference only |

The algorithm itself is published (Dasgupta et al., *Science* 2017; *PNAS* 2018) and is ~100 lines; our repo already contains a version (`backend/ml/flyhash_novelty.py`). **We do not need a library to use it — we need evidence that it earns its place.**

## 5b. What the FlyHash-FBF result does and does not mean

FlyHash-FBF scored 0.84 vs Mahalanobis 0.976 on the 13 tabular features. Three honest readings, all true at once: (1) this is the regime the design notes predicted it is weak in (expand-and-sparsify needs high-dimensional input; 13 numbers is not that); (2) it was **untuned** (expansion 20×, fan-in 6, 5 % sparsity, familiarity threshold 0.05 — defaults, no search); (3) the plant data is simple enough that a Gaussian fits it almost perfectly, which flatters Mahalanobis. **Do not conclude "fly-inspired is bad."** Conclude "fly-inspired has not earned a place on tabular scalars, and the high-dimensional test is still owed."

## 6. What to build, in order

1. **Calibrated-residual detector** (`backend/detect/`): per-tail calibration on a nominal window → 13 n_cyl-agnostic z-features → Mahalanobis + max\|z\|, thresholds set by conformal calibration to a false-alarms-per-flight-hour target (D11). Runs for **every engine, every frame**, microseconds. *(Prototype: `experiments/E17`; promote after B0.9.)*
2. **Classifier registry:** universal RF/GBM with engine-class flags as the default; per-engine override when labelled data exists; **gated and batched**, compiled for the edge; provenance sidecar per model (D28).
3. **Physics-based per-cylinder channel** for waveform faults (peer-referenced torque deficit, order features) — deterministic and engine-agnostic by construction (`n_cyl` is a parameter).
4. **The owed experiment (W5):** fly-inspired vs Mahalanobis vs Isolation Forest vs a 1-D CNN on **order-spectrum / waveform features** — CWRU (12/48 kHz), Paderborn (64 kHz, artificial vs real damage), plant crank signal now, 51.2 kHz plant later, and 3500-DEFault once its labels are decoded. If the fly-inspired detector wins on cost *or* detection at equal false-alarm rate, it takes the Pi tier-0 slot (with `fbfc` MIT code, our own implementation, or a licensed `ffbf`). If not, publish the negative result (per `study/20` §20.5) and ship Mahalanobis.
5. **Add the zero-shot time-series-foundation-model control** (F61) to W5 — it answers "you only beat your own simulator."

## 7. Limits of this evidence (read before quoting any number)

- **Simulation only.** Evidence class: SIMULATION. No real fault data was used.
- **The plant is not engine-class-aware internally** (FINDINGS F21: shared rpm map, SI-style EGT formula, diesels read EGT 1,150–1,190 °C, VRDE runs above rated rpm). Cross-engine differences here are partly artefacts. The *direction* of the results (calibration makes detectors transfer; per-engine RF slightly better than universal) is plausible; the *magnitudes* should not be quoted as engine performance.
- MISFIRE is exaggerated in the plant (EGT −650 °C); it inflates all detectors equally.
- Thermal-channel faults only; no waveform data; no real healthy flight hours (ACES false-alarm rate is a separate, still-owed result, E01).
- 5 engines, single random seed per run set; no confidence intervals yet (E17 should be repeated over ≥ 5 seed sets before anything here is quoted externally).
- The FBF result is a single untuned configuration.

## Addendum 24 Sep 2026 — fly line is kept as the innovation tier (user direction)

- **Tier-0 (all engines, Pi 5):** FlyHash / Fly Bloom Filter novelty gate (E17: cheap, AUROC target met).
- **Tier-1 (selected engine):** sparse reservoir + ridge readout, initialised from the fly connectome (E19: beats RF by ~4–5 macro-F1 points; ties its shuffled and random-ESN controls).
- **Tier-2 (ground, A100-class, selected engine only):** heavy contenders (TabPFN research use, TimesFM/Chronos, larger reservoir).
- **RF stays as the reference baseline**, not removed. Rule: the fly tiers ship because they are *satisfactory and edge-cheap*, whether or not they beat RF; claims are limited to what E17/E19 measured (no "fly wiring is better" claim). Differentiator vs cloud-dependent competitors: edge-first, no cloud, federated Bloom-filter merge, tiny footprint.

## Addendum 24 Sep 2026 (2) — Jev

Jev/open-Jev is retained as a **tier-2 ground contender for the selected engine** (HealthFrame-as-text) and as the maintenance ranker; it must beat the reservoir tier or add explanation value at equal false-alarm rate to stay (D37, W10). Runs on DRDO-class GPUs; offline; never auto-actions.
