# `docs/build/` — Build Handoff Set

*The documents that let a different person or LLM continue this project without re-doing the archaeology. Written 24 September 2026. Start at the top and stop reading when you have what you need.*

| Order | File | Read it to learn | Length |
|---|---|---|---|
| 1 | [`MENTAL_MODEL.md`](MENTAL_MODEL.md) | What the project is, how the docs fit together, the two-parallel-systems fact, the 20 Hz → 51.2 kHz story, the traps, the pickup loop | short |
| 2 | [`FINDINGS.md`](FINDINGS.md) | **Everything that was discovered**, with evidence, impact and status (F01–F30) | medium |
| 3 | [`VERIFICATION_CHECKLIST.md`](VERIFICATION_CHECKLIST.md) | What to check before you write code and before you say "done" — every row is a real past mistake | short |
| 4 | [`SUPERSEDED_VS_CURRENT.md`](SUPERSEDED_VS_CURRENT.md) | Seven old/new implementation pairs: which to wire, which to retire | medium |
| 5 | [`UNIVERSALITY_AUDIT.md`](UNIVERSALITY_AUDIT.md) | Why this is still a one-engine simulator, the `EngineProfile` design, dataset benefits, freshness of every model/dataset | long |
| 5b | [`MULTI_ENGINE_ARCHITECTURE.md`](MULTI_ENGINE_ARCHITECTURE.md) | Simulators + fault injectors + detectors per engine, all running at once; the lever verdict; waveform and Raspberry-Pi-5 edge pipeline; assets | long |
| 5e | [`DEV_EXECUTION_PLAN.md`](DEV_EXECUTION_PLAN.md) | **How the build is run: directory operations, slices, gates, guardrails** | short |
| 5d | [`FLY_100_WAYS.md`](FLY_100_WAYS.md) | **100 ways the fly/connectome idea can work + E19 result** | medium |
| 5c | [`DETECTOR_DECISION.md`](DETECTOR_DECISION.md) | **Jev vs fly-brain vs cheap ML; one universal detector or many** — with an experiment | medium |
| 5d | [`DEAD_CODE_AUDIT.md`](DEAD_CODE_AUDIT.md) | Reachability numbers; what to delete, archive, keep, never touch | medium |
| 5e | [`IDEAS_AND_GAPS_SWEEP.md`](IDEAS_AND_GAPS_SWEEP.md) | Planned work in the older docs that had no backlog row | short |
| 6 | [`DECISIONS.md`](DECISIONS.md) | The 35 standing decisions (D01–D35) and why | long |
| 7 | [`INTERFACES.md`](INTERFACES.md) | The data contracts (`Frame`, `TruthRecord`, `CycleHealthVector`, config schema, dataset records, result JSON) | long |
| 8 | [`BACKLOG.md`](BACKLOG.md) | The ordered task list E0–E14 with acceptance criteria — **pick the first unblocked item** | long |
| 9 | [`CURRENT_STATE.md`](CURRENT_STATE.md) | File-by-file: live / harness / orphan / test-only, known issues, recommended action | long |
| 10 | [`RESEARCH_LEDGER.md`](RESEARCH_LEDGER.md) | What has been researched, how deep, from which sources; what hasn't; the corrections table | long |

## Where the deeper reasoning lives (outside this folder)

- `docs/audit/07`–`12` — the design documents: feature plan, integration audit, full-depth architecture (51.2 kHz, estimator hierarchy, active diagnosis), red-team review, the software-only redesign of every PS clause, and the dataset plan.
- `docs/study/01`–`27` — the ground-up teaching course (corrected where later docs say so).
- `docs/IMPLEMENTATION_LOG.md` — dated, per-change record in *what was broken / done / verified / unproven* form. **The ground truth for "is X really built."**

## The operating loop (from `MENTAL_MODEL.md` §8)

1. `pytest` from the repo root (currently **163 passing**). 2. Read the relevant `SUPERSEDED_VS_CURRENT` entry. 3. Take the first unblocked `BACKLOG` row; run the `VERIFICATION_CHECKLIST`. 4. Build it to its acceptance criteria. 5. Log it; update `BACKLOG`, `CURRENT_STATE`, `FINDINGS` if relevant. 6. `pytest` again — the count must not drop.

## Automated guards that already exist (they fail the build if you regress)

| Test | Guards |
|---|---|
| `tests/test_no_truth_leak.py` | No ground-truth field read on the inference path |
| `tests/test_engine_agnostic_ratchet.py` | Engine-specific literal counts may only go down (baseline `tests/engine_agnostic_baseline.json`) |
| `tests/test_engine_config_provenance.py` | Every numeric engine-config field has a classified provenance |
| `tests/test_llm_provider_default.py` | LLM defaults to disabled, never a Chinese-origin model |
| `tests/test_aces_channel_binding.py` | ACES EGT/CHT bind to the right columns (skips if the data isn't present) |
| `experiments/E17_detector_bakeoff_plant.py` | (experiment, not a test) universal-vs-per-engine and fly-vs-classical bake-off; re-run before changing D31 |
| `scripts/tools/audit_reachability.py` | (tool) live/harness/test/orphan module counts; re-run per milestone |
| `tests/test_frame_and_plant_source.py` | `Frame` carries no truth; plant faults never appear in frames |
