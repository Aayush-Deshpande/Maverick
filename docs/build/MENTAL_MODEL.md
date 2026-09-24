# Mental Model — Read This First

*For any human or LLM picking up this project cold, including "my own quota ran out, someone else is continuing." Written 24 September 2026. Nothing here is new information — it distils and cross-references documents that already exist, so you get oriented in one read instead of ten.*

**If you read only one section, read §7 (traps) before you touch any code. Then run [`VERIFICATION_CHECKLIST.md`](VERIFICATION_CHECKLIST.md) before you write and before you say "done".**

---

## 1. What this project actually is, in one paragraph

DRDO (India's defence research organisation) ran Smart India Hackathon problem statement **PS-26054**: build an AI-enabled digital twin that monitors the health of the piston engine on a MALE (Medium-Altitude Long-Endurance) UAV — predicts failures before they happen, estimates remaining life, and computes the probability a planned mission completes. The team built a prototype (`backend/`, `frontend/`, `apps/`) around a **Rotax 912 iS** engine, simulated telemetry at **20 Hz**, and a Random Forest classifier. Then, across several long research sessions (21–24 September 2026), it became clear that this prototype — while functional — falls far short of what a real DRDO evaluator would need, and far short of what the underlying engineering problem actually calls for. A second, much deeper design was produced (docs 07–12 below), and a small set of honesty/integration fixes has begun (E0, done). **The bulk of the deeper design is not yet built.**

## 2. Why this document set exists, and how to read it

There are three layers of documentation in this repo, from oldest/shallowest to newest/deepest. **Read in this order if you're starting cold:**

1. **This file** (`docs/build/MENTAL_MODEL.md`) — orientation. Folder index: [`README.md`](README.md).
1b. **`docs/build/FINDINGS.md`** — everything that was discovered (F01-F20) with evidence, impact and status. Read before trusting any claim in an older document.
2. **`docs/build/UNIVERSALITY_AUDIT.md`** and **`docs/build/VERIFICATION_CHECKLIST.md`** — the first answers "is this a one-engine simulator?" (yes, today; here is the evidence and the fix) and lists stale artifacts; the second is the pre/post-change checklist. Read both.
2a. **`docs/build/MULTI_ENGINE_ARCHITECTURE.md`** and **`docs/build/DETECTOR_DECISION.md`** — the target runtime (all engines live, injectors, levers, waveform edge pipeline) and *why cheap calibrated classical ML beats Jev/connectome/fly-brain for detection* (with an experiment). Read before designing anything runtime- or detector-related.
2b. **`docs/build/SUPERSEDED_VS_CURRENT.md`** — which implementations are current and which are dead weight. **Read before writing or wiring any code.** This is the direct answer to "there's GBs of stuff in here, what's actually real."
3. **`docs/build/DECISIONS.md`** — the 26 standing architectural decisions (D01–D26), each with why and evidence. If you're about to make a design choice, check here first — it's probably already decided.
4. **`docs/build/INTERFACES.md`** — the exact data contracts (schemas) every component must agree on. Non-negotiable once code depends on them.
5. **`docs/build/BACKLOG.md`** — the ordered task list (E0–E14, 103 items). Pick the first unblocked item, per its own instructions at the top.
6. **`docs/build/CURRENT_STATE.md`** — a file-by-file map of what's LIVE / HARNESS-only / ORPHAN / TEST-only, with a recommended action per file.
7. **`docs/build/RESEARCH_LEDGER.md`** — what's been researched, how deep, from which sources, and what hasn't. Also a "corrections" table of claims made and later found wrong — don't repeat them.
8. **`docs/audit/07`–`12`** — the actual design documents (the "thinking"). `07` is the feature plan (F31–F68). `08` is the integration/honesty audit. `09` is the full-depth technical target (51.2 kHz sensing, the estimator hierarchy, active diagnosis). `10` is the red-team review (PS coverage, DRDO reality, SIH format). `11` is the software-only redesign of every PS clause (federated learning, edge AI, XAI, security, maintenance autonomy). `12` is the dataset plan.
9. **`docs/study/01`–`27`** — the original ground-up teaching course (sensors, CAN, vibration, RUL, digital twins...). Still broadly correct, **except** where a later doc explicitly corrects it (the 51.2 kHz sampling rate is the big one — see §5).
10. **`docs/IMPLEMENTATION_LOG.md`** — a running, dated log of every fix made, in "what was broken, what was done, what's still unproven" format. This is the ground truth for "is X actually built and tested," more reliable than any summary claim.

**Everything else** (`UpdatedReport/`, most of `docs/*.md` at the top level) is older, sometimes wrong, and superseded by the above. `UpdatedReport/31_VERIFICATION_AND_CORRECTIONS.md` itself documents this.

## 3. The one-sentence design philosophy

> **Measure the process, not the symptom. Estimate physical parameters, don't classify labels. Never let the thing you demo be a different thing from the thing you measure.**

Concretely, this cashes out as three standing rules (full detail in DECISIONS.md):

- **D03 — The twin is an estimator.** It should hold a live, uncertain estimate of *this specific engine's* physical health parameters (injector efficiency, cooling effectiveness, compression...), not output a class label from a lookup table.
- **D05 — One pipeline.** The code path that runs in the live demo and the code path that produces the evaluation numbers must be **the same object**. Today they are not (see §4).
- **D04 — Plant ≠ twin.** The thing that generates "what actually happened" (the plant/simulator) must be a different, independent model from the thing that predicts "what should happen" (the twin), or every accuracy number just measures self-agreement.

## 4. The single biggest structural fact about this repo

**There are two parallel systems, and only one of them runs in the demo.**

```
SYSTEM A — what the live demo runs
  engine_service.py → can_streamer.TelemetryStreamer (generates "actual" data
  FROM the twin's own equations — circular) → detection_pipeline.py (RF +
  hand-written rules on 14 residuals) → rul_estimator.py (hardcoded component
  lifetimes) → copilot/voice → React + Blender

SYSTEM B — what produces every real, defensible number
  plant/virtual_engine.py (a genuinely independent simulator) → crank-angle
  chain → twin/residual_detector.py → evaluation/* (conformal intervals, PHM
  metrics, damage accumulation) → mission/reliability.py
  — reachable ONLY from tests and evaluation/harness.py, NEVER from the demo
```

Of ~20,000 lines in `backend/`, a large fraction is System B: real, carefully-reasoned engineering (but **largely without committed tests** -- see trap 11) that **the demo never touches**. This is not "half-finished code," it's **finished-but-disconnected code**. See `docs/build/CURRENT_STATE.md`'s LIVE/HARNESS/ORPHAN table for the exact file-by-file breakdown, and `docs/audit/08` §1 for the original diagnosis.

**Closing this gap is backlog tier E1** ("one pipeline"). It is the highest-leverage unbuilt work in the entire project — more valuable than any new feature, because until it's closed, *nothing else that gets built will be demonstrated either*.

## 5. The 20 Hz → 51.2 kHz story (your specific example, resolved)

You asked specifically about this, so here is the precise timeline and the precise current state:

- **What was built (System A, live today):** telemetry at **20 Hz**. Vibration is a single scalar (`VIB_GEARBOX_RMS`), and `ml/spectral_analyser.py`'s own docstring admits its FFT can't resolve the frequencies it's looking for at this rate (Nyquist ceiling 10 Hz, target frequency ~103 Hz) — it silently falls back to a plain RMS threshold.
- **What was designed (System B / doc 09, not built at all):** a combustion-chamber acoustic resonance analysis (Draper modes, ~5.6–20 kHz for this bore class) that requires sampling accelerometers at **51.2 kHz** (2.56× the 20 kHz band), plus crank-tooth edges timestamped at nanosecond resolution, rail pressure at ≥30 kHz, and so on. Full derivation: `docs/audit/09_full_depth_architecture.md` §2.
- **Current code state: zero lines of 51.2 kHz code exist anywhere.** This is not a case of "old vs new version both present, pick the right one" — it's a case of "old version exists and runs, new version exists only as a design document." **Nothing to wire here yet; this is 100% new-build work**, tracked as backlog **E2** (waveform-grade simulation) and **E3** (the DSP core that consumes it).
- **The trap for a future agent:** seeing `GearboxSpectralAnalyser` in `ml/spectral_analyser.py` and assuming it's "the vibration analysis system, needs extending" — it is not. It is built on a premise (20 Hz vibration sampling) that the whole redesign replaced. **Do not extend it. Build the new `backend/dsp/` package from `docs/audit/09` §4 instead**, and retire `spectral_analyser.py` once the new one covers its one real use (the gearbox 3rd-harmonic early-warning check) — see `docs/build/SUPERSEDED_VS_CURRENT.md` entry S05.
- **Five other study documents still say "2–10 kHz"** (`study/02`, `study/06`, `study/24`, `study/26`, `study/proposal.md`) — this is a known, already-recorded correction (`docs/audit/09` §17), not a new problem, but it's exactly the kind of stale claim that could mislead a fresh read if you stop at the study docs and don't reach doc 09.

## 6. What's real vs aspirational, at a glance

| Layer | Real & checked (in simulation, ad-hoc) | Designed, not built |
|---|---|---|
| Combustion physics | SI (spark) Wiebe model, crank dynamics, per-cylinder work attribution — `crank_dynamics.py`, `crank_diagnostics.py` | CI (diesel/CRDi) combustion model: ignition delay, multi-injection, rail hydraulics (doc 09 §5.2) |
| Vibration | A single 20 Hz RMS scalar + a DFT that can't see its target (broken by construction) | 51.2 kHz angle-domain DSP: order tracking, envelope, cyclostationarity (doc 09 §4.2) |
| Plant/twin split | `plant/virtual_engine.py` is genuinely independent — but not wired into the live demo by default | — (this piece exists, just needs wiring — see SUPERSEDED_VS_CURRENT S01) |
| Fault taxonomy | 8 hand-picked, cylinder-hardcoded faults (`can_streamer.DRDO_FAULT_DEFINITIONS`) | 20 MIL-STD-1629A-derived modes with an isolability matrix (`reliability/fmeca.py`) — built, not wired (SUPERSEDED_VS_CURRENT S02) |
| RUL/prognostics | Hardcoded component lifetimes × stress multipliers (`rul_estimator.py`), live | Dual-path (physics-of-failure + data-driven) RUL with conformal intervals — the pieces exist (`damage_accumulation.py`, `conformal.py`, `prognostic_metrics.py`) but were never assembled into one estimator, and never wired (SUPERSEDED_VS_CURRENT S03) |
| Mission decision | A margin-check GO/CAUTION/NO_GO inside `rul_estimator.py` | A Monte Carlo mission-reliability engine with a Wilson interval (`mission/reliability.py`) — built, not wired (SUPERSEDED_VS_CURRENT S03) |
| Engine model | Hardcoded Rotax 912 iS constants at module level in `thermo_model.py`, ignores engine config entirely | 5 engine configs (912iS/914/915iS/AE300/VRDE-CRDi) with per-field provenance — built (`engine_config.py`), but `thermo_model.py` doesn't consume it yet (SUPERSEDED_VS_CURRENT S06) |
| Federated learning, edge runtime, active diagnosis, security layers, maintenance autonomy | Nothing | Fully designed in doc 09/11, zero lines of code |
| Real data | ACES (real Rotax 914 flight) — now correctly bound (B0.3); ~40 GB of public proxy datasets downloaded, uninspected by any loader yet | Loaders/experiments (`backend/datasets/`, `experiments/`) not written — backlog E7 |

## 7. Traps — read before touching code

1. **Don't assume more lines of code = more done.** ~20,000 lines exist; a large fraction is disconnected (§4). Measure by "is it on the live path" not "does the file exist."
2. **Don't assume a file with a plausible name is current.** `spectral_analyser.py`, `fault_classifier.py`, `rul_estimator.py`, `can_streamer.py` all sound like exactly what you'd want to extend. **Check `SUPERSEDED_VS_CURRENT.md` first** — several of these are the *old* half of a pair where the *new* half already exists elsewhere, unwired.
3. **Don't wire the old and new halves of a pair together and call it done.** E.g. don't patch `can_streamer.TelemetryStreamer` to "add" independence — `plant/virtual_engine.py` already *is* the independent version; the job is to redirect callers to it and retire the old one, not merge them.
4. **Don't treat "41/65 features implemented" (an old count in `IMPLEMENTATION_LOG.md`) as a completion percentage.** It measures whether a feature was *typed*, not whether it's *wired into the live path*. See `docs/audit/08` §1 for why this framing was itself flagged as misleading.
5. **Don't quote an ACES EGT/CHT number in °C.** The channel *binding* is fixed and verified (B0.3), but the *unit scale* is still unconfirmed — see `aces_loader.py`'s `ACES_PROVENANCE["unit_caveat"]`. Relative comparisons are fine; absolute Celsius claims are not, until the real ACES documentation PDF is obtained.
6. **Don't present an assumed engine constant as a fact.** Every engine config now has per-field `provenance` (PUBLIC/MANUAL/ASSUMED/PLACEHOLDER) — check it before quoting a number, especially for `vrde_jayem_2_2l.json` (mostly assumptions) and `rotax_915is.json` (public power/displacement/TBO, assumed everything else).
7. **Don't re-litigate a decision without reading `DECISIONS.md` first.** If you're about to decide "should the LLM default to X" or "should the twin be a classifier or an estimator," it's almost certainly already decided there, with the reasoning.
8. **Don't re-run broad research/brainstorming.** Per D26, the design phase is over. `RESEARCH_LEDGER.md` §2 shows the coverage is already deep (R2–R3 on nearly every topic). The task now is building `BACKLOG.md` items in order, not more design documents. (This document and `SUPERSEDED_VS_CURRENT.md` are the one justified exception — they're onboarding infrastructure, not new design.)
9. **Don't skip the test suite.** `pytest` from the repo root. It was at 129 passing before the 24 Sep session's fixes, 152 after. Any change that drops this number needs to be understood before it's committed.
10. **Don't assume the datasets are usable yet.** `Datasets/` (41 GB) is downloaded but has zero loader code (`docs/audit/12` §3, backlog E7). It's raw material, not a feature.

11. **Do not trust a name, a docstring or a test title -- read what the code does.** Found 24 Sep: a live method `get_conformal_rul()` documented as split-conformal with a coverage guarantee is a fixed 12 % margin, and its test only checked ordering. Also, most research modules that `IMPLEMENTATION_LOG` calls "verified" have **no pytest coverage** (ad-hoc runs only). Before wiring an orphaned module, write its characterization test (backlog B0.9) so you know it still does what the log says.

12. **This is currently a one-engine (Rotax 912 iS, 4-cylinder) simulator, not a universal platform.** There is no engine-selection path in the API or UI, and 286 fixed-cylinder / 78 brand / 37 model-number literals sit in modules that must become engine-agnostic. Do not add more (the ratchet test fails if you do); derive from the selected profile instead (decision D27). The trained ML models are dated 2 Sep and predate the whole redesign (D28) -- do not treat their accuracy as evidence.

13. **Do not run a cross-engine experiment on the plant and quote it as engine performance** - the plant is Rotax-shaped internally (F21). Fix it (R6) or label results 'indicative'. **Do not extend a scalar-only detector to cover injector faults** - they are invisible to scalars (F22); build the waveform channel. **Do not add a lever that edits a reading directly** (D30). **Do not call sklearn one row at a time** (11.5 ms). **Do not adopt a repo without a licence** (D35).

## 8. How to pick up work right now

1. Run `pytest` from the repo root. Confirm the count matches `CURRENT_STATE.md`'s header (it says the last-known-good count).
2. Read `SUPERSEDED_VS_CURRENT.md` fully — it's short and it's the map of landmines.
3. Open `BACKLOG.md`, find the first row without a ✅, check its `Deps` column is satisfied, and build it to its stated acceptance criteria.
4. Log what you did in `docs/IMPLEMENTATION_LOG.md` (append a dated session entry, "what was broken / what was done / verified / unproven" — follow the existing format exactly, it's load-bearing for the next person).
5. Update `CURRENT_STATE.md` and `BACKLOG.md`'s row for the item you just finished (mark ✅, update the "Action" column if a file's status changed).
6. Run `pytest` again. If the count didn't grow and you added a feature, you didn't add a test — add one.
7. Move to the next unblocked item.

That loop is the entire operating procedure. There is no step where you need to re-derive the architecture — it's already decided (`DECISIONS.md`) and specified (`INTERFACES.md`).

## 9. If you're an LLM whose context/quota is about to run out

Do these three things, in order, before you stop:

1. Make sure whatever you were mid-way through either (a) passes `pytest` in a committable state, or (b) is clearly marked incomplete in `BACKLOG.md` with what's left, so nobody assumes it's done.
2. Append your session to `docs/IMPLEMENTATION_LOG.md`, even if partial — "started X, got to Y, next step is Z" is far more useful than silence.
3. If you found a new superseded/current pair, a new trap, or a new wrong claim, add it to `SUPERSEDED_VS_CURRENT.md` §"traps" or `RESEARCH_LEDGER.md`'s corrections table respectively — don't let the next agent rediscover it from scratch.

---

*This document is itself a living artefact — if something here goes stale (a pair gets wired, a trap gets fixed), update it rather than letting it drift. It exists to save the next reader the archaeology this session did to reconstruct it.*
