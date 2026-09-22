# ANUMAAN — Documentation

**AI-Enabled Real-Time Digital Twin for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs**
DRDO · Smart India Hackathon · Problem Statement **26054**

This is the **primary** documentation set. Supporting and background material lives in [`../analysis/`](../analysis/README.md) and is superseded by anything here.

---

## Start here

| Read this | If you want |
|---|---|
| [`00_official_problem_statement.md`](00_official_problem_statement.md) | The official PS text, reproduced verbatim |
| [`01_problem_statement_breakdown.md`](01_problem_statement_breakdown.md) | Our plain-language reading of what it actually asks for |
| [`audit/README.md`](audit/README.md) | **Where we stand against the competition, and what to build.** The most decision-relevant document here |
| [`study/README.md`](study/README.md) | The 27-part technical course, from first principles |

---

## Contents

### Problem definition
- [`00_official_problem_statement.md`](00_official_problem_statement.md) — official text, OCR artifacts corrected, no requirement altered
- [`01_problem_statement_breakdown.md`](01_problem_statement_breakdown.md) — our engineering interpretation
- [`fun_req.md`](fun_req.md) — functional requirements

### [`audit/`](audit/README.md) — competitive and self assessment
21 competitor repositories found, 15 analysed in depth. Contains the scoring, who currently wins, an unsparing audit of our own code against its documentation, the strategic conclusion, and a 30-item feature specification with build order.

⚠️ Read [`audit/05_expanded_survey.md`](audit/05_expanded_survey.md) — it corrects two headline claims made in `audit/01`.

### [`study/`](study/README.md) — the technical course
Parts **I–XXIII** teach the domain from first principles: sensors, CAN/ECU, telemetry, edge AI, vibration analysis, anomaly detection, fault diagnosis, RUL, digital twins, mission simulation, datasets, architecture, stack, roadmap, evaluation.

Parts **XXIV–XXVII** are implementation-grade references added after the audit: combustion cycle and crank dynamics, misfire diagnostics, order tracking and envelope analysis, and conformal prediction for RUL.

Also: [`study/proposal.md`](study/proposal.md) (frequency and edge/ground split) and [`study/rnd_solution_report.md`](study/rnd_solution_report.md) (independent R&D report).

### Current state
- [`04_system_guide.md`](04_system_guide.md) — **the current system, read from source.** Architecture, the 9-stage pipeline, module reference, API surface, the 8 faults, and what is real vs synthetic. Start here for "how does it work today"
- [`02_comprehensive_audit_summary.md`](02_comprehensive_audit_summary.md) — implementation audit summary
- [`03_implemented_features_technical_deep_dive.md`](03_implemented_features_technical_deep_dive.md) — earlier feature deep-dive ⚠️ predates `04`; re-verify where they conflict
- [`gap_plan.md`](gap_plan.md) — gaps against the PS

### [`pitch/`](pitch/) — presentation material
### [`assets/`](assets/) — 3D asset program: audit, integration spec, rigging/animation, deliverables and acceptance

---

## Evidence labels

Every non-obvious claim in this documentation carries one of four labels. This convention is the reason the documentation can be trusted, and it should not be dropped.

| Label | Meaning |
|---|---|
| ✅ **VERIFIED** | Traceable to a cited public source |
| 🔶 **INFERENCE** | Engineering reasoning from verified facts |
| ⬜ **ASSUMPTION** | A design choice we made. Not required by the PS, not claimed to be what DRDO does |
| 🔒 **PROPRIETARY** | Genuinely not public. Do not guess, and never present a guess as fact |

⚠️ **The single most important rule:** DRDO does not publish the internals of TAPAS-BH-201's engine bus, its datalink waveform, or its health-monitoring parameter list. Anything we say about those is 🔶 or ⬜, never ✅.

---

## Repository layout

```
docs/          ← you are here. PRIMARY documentation
analysis/      ← background, as-built, earlier design reasoning
backend/       ← physics, ML, telemetry, server
frontend/      ← React GCS dashboard
apps/          ← Blender twin, desktop GCS, mission graph viewer
site/          ← standalone WebGL presentation site
Models/        ← engine and airframe 3D assets
Models_Images/ ← reference image libraries
Datasets/      ← dataset catalogue (metadata only; raw data untracked)
scripts/       ← build and asset-generation scripts
tests/         ← pytest suite
competitors/   ← cloned competitor repos for audit (gitignored)
```
