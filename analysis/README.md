# Analysis — supporting and background material

**This is secondary material. The primary documentation is [`../docs/`](../docs/README.md).**

Everything here predates or supports the ANUMAAN documentation set. It is kept because it contains real information about the current codebase, earlier design reasoning, and domain research — but where this folder and `../docs/` disagree, **`../docs/` wins**.

---

## What is in here

| Folder | What it is | When to read it |
|---|---|---|
| [`engineering/`](engineering/README.md) | **As-built documentation of the current codebase** — an 8-part suite covering problem context, dual-plane architecture, data flow, backend modules, physics/ML, RAG & copilot, frontend, and operations. Plus `claude_analysis.md`, a module-level audit of `backend/agent`, `backend/graph` and `backend/knowledge` | When you need to know **how the code works today** |
| [`strategy/`](strategy/) | **Strategic engineering analysis** — 5 parts: problem statement analysis, architecture & AI boundaries, telemetry/physics/dataset strategy, mission records & knowledge graph, and a master end-to-end build guide | When you need the **reasoning behind a design decision** |
| [`insider/`](insider/) | **Domain research** — MALE UAV background and per-pillar deep technical breakdowns, implementation audits, data-flow notes and required fixes | Background on the **problem domain**, not our code |
| [`tasks/`](tasks/) | **Execution plans and feature specs** — master execution plan, tactical simulation & Auto-GCAS, mission replay & scrubber, persistent mission knowledge graph & CBM, plus the simulation scope spec | When picking up a **planned feature** |

---

## Why this folder was restructured

These documents were previously spread across `docs/guide/`, `docs/insider/` and `final_tasks/` at the repository root. Two problems:

1. **`docs/` is now the ANUMAAN primary documentation set**, so the old contents had to move.
2. **`docs/guide/` contained two different document series interleaved in one folder**, with colliding numbering — two `01_`, two `02_`, two `03_`, two `04_` and two `05_` files. They were an as-built engineering suite and a strategic analysis series that had been merged by accident. They are now separated into `engineering/` and `strategy/`.

⚠️ Absolute `file:///e:/...` links throughout these documents were broken before the move — several pointed at a stale `e:/TalentForge/Clay/` path that no longer exists. They have been converted to working relative links.

---

## Relationship to the primary docs

```
docs/                    ← PRIMARY. Problem statement, study course (I–XXVII),
                           competitive audit, pitch, asset program
    ↑
    │  supersedes on any conflict
    │
analysis/                ← THIS FOLDER. Background, as-built, earlier reasoning
```

⚠️ **Known staleness:** material here was written before the [competitive audit](../docs/audit/README.md). Where it describes the voice interface, the LLM copilot scope, or the vibration pipeline, read [`../docs/audit/02_self_audit.md`](../docs/audit/02_self_audit.md) alongside it — several of those components are recommended for cutting or constraining.
