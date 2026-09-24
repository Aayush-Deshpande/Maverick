# 100 Ways the Fly / Connectome Idea Can Be Made To Work

*24 Sep 2026. Written after the user's correction: heavy inference runs only for the **selected** engine, ground infra is DRDO-class (A100-scale), and the fly line was suggested as an alternative Jev-style detector. Rule for this file: **every row is a way to make it work**; each carries a status (`SRC` = published/open source found on the web, `LOCAL` = on disk, `TEST` = we must measure, `IDEA` = ours) and the test that would prove or kill it. Nothing here is a claim of result — results go to `FINDINGS.md` after `experiments/E19+`.*

## Sources found (not limited to the local repo)

| Source | What it is |
|---|---|
| [The Drosophila Connectome as a Computational Reservoir for Time-Series Prediction (PMC12109256)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12109256/) | Full FlyWire connectome as an Echo State Network matrix; chaotic multivariate forecasting; resilient to overfitting, low regularisation |
| [ESA Advanced Concepts Team – Connectome of a Fly as a Computational Reservoir](https://www.esa.int/gsp/ACT/projects/fly_connectome/) | Aerospace-agency precedent: connectome reservoir for space/flight-type series |
| [arXiv 2606.17745 – frozen rate operator from the complete larval connectome](https://arxiv.org/pdf/2606.17745) | Degree and weight govern gross response; exact wiring governs input routing and mushroom-body modes → tells us which null controls matter |
| [bioRxiv – cross-species connectome comparisons: memory capacity & time-series prediction](https://www.biorxiv.org/content/10.1101/2025.10.29.685101v1.full) | Network attributes that predict reservoir memory capacity → pick sub-circuits by measured metric |
| conn2res (Nat. Commun. 2024) | Toolbox: connectome → reservoir, fly/mouse/rat/macaque matrices, task suite |
| [aditya1212singh/fly-connectome-forecasting](https://github.com/aditya1212singh/fly-connectome-forecasting) | Third-party forecasting code using a fly connectome |
| [rithram/fbfc](https://github.com/rithram/fbfc) (MIT) | Fly Bloom Filter Classifier, KDD 2021 |
| [dataplayer12/Fly-LSH](https://github.com/dataplayer12/Fly-LSH) | FlyHash + DenseFly |
| [cauldr0nx/flyPaper](https://github.com/cauldr0nx/flyPaper) | FlyHash + Bloom filter novelty score |
| [arXiv 2006.03741 expressivity of expand-and-sparsify](https://arxiv.org/pdf/2006.03741), [arXiv 2206.09222 bioinspired random projections](https://arxiv.org/pdf/2206.09222) | Theory: when sparse expansion beats dense projections; robustness |
| [arXiv 2104.04121 fast smart neuromorphic sensors](https://arxiv.org/pdf/2104.04121) | Mixed-encoding heterogeneous nets for sensor edge classification |
| Local: `mk-jev-fly-brain/mk/fly_circuit.js` | maleCNS 12,000-neuron subgraph, 941,464 synapses, density 0.65 %, 8,149 excitatory / 3,851 inhibitory, 16 named groups (measured 24 Sep) |
| Local: `backend/ml/flyhash_novelty.py` | Existing FlyHash novelty scorer (FBF) |

**Why this is not dead:** three independent lines exist — (a) expand-and-sparsify *novelty* (our FBF), (b) connectome-as-*reservoir* for time series (PMC12109256, ESA, conn2res), (c) *simulation* of the brain (Shiu LIF etc., irrelevant to detection). (b) was never tested by us. The earlier dismissal conflated (b) and (c).

## A. Connectome as a reservoir (the temporal detector) — ways 1–20

1. Build ESN matrix from `pre/post/w` of the local 12k circuit; scale to spectral radius 0.9; ridge readout on z-feature windows. `LOCAL/TEST` (E19)
2. Same but sign from transmitter/neuron-type field (+1/−1 measured: 8,149/3,851). `LOCAL/TEST`
3. Null control: degree-preserving shuffled connectome (lesson from Model Kombat). `TEST`
4. Null control: random sparse ESN with equal size and density. `TEST`
5. Null control: shuffled weights, same topology. `TEST`
6. Use only the top-N most connected neurons (PMC12109256 selection). `SRC/TEST`
7. Class-proportion-preserving vs class-breaking subsampling (same paper). `SRC/TEST`
8. Full FlyWire/larval reservoir (up to ~140k neurons) on GPU — A100 handles a sparse 140k matrix trivially; selected-engine only. `SRC/TEST`
9. conn2res task suite (memory capacity, nonlinear memory) to *choose* the sub-circuit by metric before touching engine data. `SRC`
10. Input routing via the sensory groups (`taste`, `body_touch`, visual projection) mapped to channel families (thermal, pressure, rpm) — arXiv 2606.17745 says routing is what wiring uniquely governs. `SRC/TEST`
11. Readout from descending neurons (676) only vs all — biological "motor" readout as a fault classifier head. `TEST`
12. Multiple readouts on one frozen reservoir: detection head, fault-class head, RUL head → one reservoir, N cheap ridge heads. `IDEA`
13. Reservoir states as **features into the RF** (hybrid), not replacing it. `IDEA`
14. Reservoir *prediction error* as anomaly score (train to forecast nominal next-step; residual = novelty). `IDEA`
15. Leak-rate sweep to match engine thermal time constants (CHT ~10–100 s vs EGT ~1 s). `TEST`
16. Multi-timescale: three reservoirs with different leak rates per channel family. `IDEA`
17. Spiking (LIF) version of the same wiring driven by rate-coded features → gives the Pi 5 an event-driven path. `SRC/IDEA`
18. Quantise reservoir to int8/binary state for Pi 5 (echo-state nets tolerate it). `TEST`
19. Sparse-matrix CSR on Pi 5: 941k nnz × 1 matvec per step ≈ 2 MFLOP → sub-ms; **measure**. `TEST`
20. Train readout per tail (ridge is closed-form, seconds) = per-tail calibration with no retraining of the reservoir. `IDEA`

## B. Expand-and-sparsify / FlyHash / FBF (the novelty detector) — 21–40

21. Keep current FBF as tier-0 all-engine gate (cheap, 4 µs claim). `LOCAL`
22. Swap to MIT `fbfc` reference for a clean-licence baseline (ffbf has no licence). `SRC`
23. DenseFly / Fly-LSH variants as encoder alternatives. `SRC/TEST`
24. FlyPaper-style similarity-graded novelty score (not just binary). `SRC`
25. Encode *windows* of z-features (temporal FBF) instead of single frames. `IDEA/TEST`
26. Encode order-domain spectra (angle-domain) for waveform anomalies — needed for injector faults invisible to scalars (F22). `IDEA`
27. Winner-take-all sparsity sweep 2–20 % (fly uses ~5 %). `TEST`
28. Expansion ratio sweep (fly ≈ 40×). `TEST`
29. Learned projection (supervised sparse coding) vs random — expressivity paper says when it wins. `SRC/TEST`
30. Per-cylinder FBF (cylinder-symmetric encoders, peer referencing). `IDEA`
31. Per-phase FBF (taxi/climb/cruise) to stop mission phase looking like a fault. `IDEA`
32. Federated FBF: fly colonies — union of Bloom filters across tails is exact and privacy-friendly (lacuna "colony of fruit-flies" federated NN paper). `SRC`
33. Bloom-filter merge = federated learning with no gradients: ideal for DRDO air-gapped fleets. `IDEA`
34. Counting Bloom filter → forgetting/ageing of nominal region. `IDEA`
35. Novelty score → conformal p-value threshold (guaranteed false-alarm rate). `IDEA`
36. FBF over *residuals* of the twin, not raw channels. `IDEA`
37. FBF as memory of *known fault signatures* (classification, FBFC's original use). `SRC`
38. Multi-FBF ensemble with different random seeds (variance reduction). `TEST`
39. FBF hardware path: bitwise ops → microcontroller/FPGA. `IDEA`
40. Explain alarms: which Kenyon-cell tags fired → which input channels → XAI. `IDEA`

## C. Fly-inspired pieces beyond these two — 41–55

41. Mushroom-body-style *dopaminergic* update: reinforce/inhibit tags after operator feedback (maintainer says "false alarm"). `IDEA`
42. APL-style global inhibition = adaptive sparsity as operating point changes. `IDEA`
43. Looming-detector circuit (LC/loom groups) as a rate-of-change detector for sudden events (EGT spike). `LOCAL/IDEA`
44. Elementary motion detector (Hassenstein–Reichardt) across cylinder sequence = firing-order timing anomaly detector. `IDEA`
45. Central-complex ring attractor tracks crank phase — robust phase estimation under missing teeth. `IDEA`
46. Antennal-lobe lateral inhibition = channel decorrelation / whitening. `IDEA`
47. Habituation (fly ignores steady odour) = automatic baseline drift adaptation. `IDEA`
48. Novelty via Hopfield/dense-associative memory (modern Hopfield ≈ attention) with fly-style sparse keys. `IDEA`
49. Sparse distributed memory case retrieval for maintenance history (F66). `IDEA`
50. Fly-inspired *sensor trust* voting across redundant channels. `IDEA`
51. Neuromodulator-style gain control by flight phase. `IDEA`
52. Descending-neuron readout as a discrete action selector for alarm tiers. `IDEA`
53. Optic-lobe-style centre-surround filtering across the cylinder ring (spatial anomaly = one cylinder differs from neighbours). `IDEA`
54. Sleep-like offline consolidation of the Bloom filters after flight. `IDEA`
55. Ground-side "brain" of many flies: one reservoir per tail, shared readout pretraining. `IDEA`

## D. Heavy models on the GPU tier (selected engine only) — 56–70

56. Connectome reservoir with 100k+ neurons on A100 (see 8). `TEST`
57. TabPFN (research use; 2.5+ is non-commercial) on windowed z-features as a zero-training strong baseline. `SRC/TEST`
58. TimesFM / Chronos (Apache-2.0) zero-shot forecast residual as anomaly score. `SRC/TEST`
59. Moirai (CC BY-NC) as research comparison only. `SRC`
60. Fine-tune a small 1D-CNN/Transformer on plant data across all 5 engines; run only for selected engine. `IDEA`
61. Self-supervised masked-signal pretraining on all engine plant streams → per-engine finetune. `IDEA`
62. Contrastive learning between healthy runs of the same tail. `IDEA`
63. Open Jev-style text model **not** for detection but to turn top-k alarm evidence into maintenance rankings at ground. `LOCAL`
64. LLM reads structured HealthFrame v2 JSON and returns FMECA-grounded next actions (grounded, offline provider). `IDEA`
65. Diffusion/generative model of nominal engine → reconstruction-error anomaly score. `IDEA`
66. Neural ODE twin fitted per tail; residual as detector. `IDEA`
67. Physics-informed UKF residual → connectome reservoir on the *residual stream*. `IDEA`
68. Ensemble stacking: FBF + reservoir + RF + Mahalanobis → conformal-calibrated final score. `IDEA`
69. Knowledge distillation: GPU teacher → Pi 5 student (tiny RF/FBF). `IDEA`
70. On-demand escalation: tier-0 flags on any engine → heavy tier wakes for that engine only. `IDEA`

## E. Runtime / architecture that makes it work — 71–85

71. Tier-0 (FBF, Mahalanobis) runs on all five engine simulators concurrently; ~µs each. `IDEA`
72. Tier-1 (RF/reservoir readout) runs for the dropdown-selected engine; hot-switch swaps the active heavy model. `IDEA`
73. Warm cache of reservoir states per engine so switching is instantaneous. `IDEA`
74. Detector registry keyed by `engine_config_id` with universal fallback (W2). `IDEA`
75. Same 13 n_cyl-agnostic features feed every contender (fair bake-off). `LOCAL`
76. All contenders behind one `score(frame_window) -> (score, evidence)` interface. `IDEA`
77. Pi 5 runs tier-0 + persistence gate; downlink scalars only when gate persists. `IDEA`
78. GPU ground runs tier-1/2 on the scalars and on requested waveform snippets. `IDEA`
79. Waveform snippet on demand: ground requests a 2 s raw capture when tier-1 is uncertain. `IDEA`
80. Record-and-replay corpus (W3) so every detector is evaluated on identical waveforms. `LOCAL`
81. Leave-one-engine-out for every contender (the universality claim's proof). `LOCAL`
82. CI ratchet: a new detector must beat baseline AUROC and not raise latency budget. `IDEA`
83. Latency budget table per tier written into HealthFrame v2. `IDEA`
84. Kill switch: if reservoir/foundation model disagrees with physics residual, physics wins, alarm is downgraded. `IDEA`
85. All third-party code passes the licence gate (D35) before import. `LOCAL`

## F. Evaluation designs that would *prove* it — 86–100

86. E19: connectome vs shuffled vs random ESN vs windowed RF vs Mahalanobis, macro-F1 + AUROC, multiple seeds, CIs. `TEST`
87. Lead-time-to-failure metric (already built) per contender. `LOCAL`
88. Injector-fault case: scalar detectors silent, waveform-FBF alarms (W6). `TEST`
89. Sensor-fault vs process-fault separation score. `TEST`
90. Cross-engine zero-shot: train on 4 engines, detect on the 5th, per contender. `TEST`
91. Noise/dropout robustness sweeps (fly codes claimed robust). `TEST`
92. Label-efficiency curve: accuracy vs number of labelled faults (reservoir ridge head should win at small n). `TEST`
93. Training-time comparison (ridge readout seconds vs RF). `TEST`
94. Pi 5 measured latency/power (real board, not emulation). `TEST`
95. NASA ACES real-flight anchor: novelty score on real recorded flights (evidence class REAL_FLIGHT). `LOCAL`
96. N-CMAPSS / public PHM datasets as external validity check for the reservoir. `LOCAL`
97. Ablations: remove inhibitory neurons; remove recurrence; 1-, 2-, 3-hop subgraphs. `TEST`
98. Report negative results in `FINDINGS.md` verbatim; a killed idea is still a finding. `POLICY`
99. Judge-facing slide: "we tested the fly idea against its own shuffled brain — here is the number." `IDEA`
100. If the connectome ties the random ESN: keep FBF (tier-0) and the *ridge-reservoir* pattern, drop the biological claim — decision written before seeing the result, in `DETECTOR_DECISION.md`. `POLICY`

## Decision rule (pre-registered)

Ship the connectome reservoir as a tier-1 contender **only if** it beats the shuffled-connectome control and the random ESN on leave-one-engine-out macro-F1 by more than the seed-to-seed spread; otherwise it stays a documented negative result. FBF stays tier-0 regardless, because it already met its latency and AUROC targets (E17).

## E19 result (24 Sep 2026, SIMULATION, `experiments/E19_connectome_reservoir.py` → `docs/evaluation/E19_connectome_reservoir.json`)

Top-1000-degree subgraph of the local maleCNS circuit, spectral radius 0.9, leak 0.3, ridge readout, 3 seeds, frame-level macro-F1 on 13 calibrated z-features (E17 data, test seeds disjoint).

| Engine | static RF | windowed RF | connectome | shuffled connectome | random ESN |
|---|---|---|---|---|---|
| rotax_914 | 0.906 | 0.896 | 0.951 ± 0.024 | 0.941 ± 0.029 | 0.955 ± 0.028 |
| vrde_jayem_2_2l | 0.949 | 0.944 | 0.998 ± 0.0003 | 0.999 ± 0.0001 | 0.999 ± 0.0002 |

**Reading (pre-registered rule applied):** the connectome does **not** beat its shuffled or random-ESN controls (differences ≤ seed spread) → the *biological wiring* claim is not supported on this data. But the **reservoir + ridge-readout pattern** beats RF by +4.5 points (rotax) and +5 points (VRDE): temporal state helps. Decision: adopt a reservoir tier-1 contender (any sparse ESN; connectome allowed as an equally-good, more-narratable initialisation), do **not** claim fly-wiring advantage in judge material. Caveats: one seed set, 2 engines, thermal-scale plant faults, frame-level (not lead-time) metric; repeat with LOEO and more engines before wiring (backlog W1/W2).
