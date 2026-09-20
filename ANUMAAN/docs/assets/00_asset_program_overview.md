# ANUMAAN 3D Asset Program — Overview & Scope

**Goal:** extend the ANUMAAN digital twin from a single engine + single airframe to a multi-platform MALE UAV fleet, at the quality and functional standard already set by the Rotax 912 iS Sport engine and the Bayraktar TB3 UCAV.

> **Status: SPECIFICATION ONLY. No modelling has started.** This document set defines what must be built and why. Read [01_current_state_audit.md](01_current_state_audit.md) before estimating any work — several assumptions about what "already exists" turn out to be wrong.

---

## Document Index

| Doc | Covers |
|---|---|
| **00 — this file** | Goal, scope, platform matrix, priorities, roadmap |
| [01_current_state_audit.md](01_current_state_audit.md) | What actually exists today: models, references, scripts, backend. Reuse/rebuild/acquire verdicts. Reference-material gaps |
| [02_quality_and_modelling_standards.md](02_quality_and_modelling_standards.md) | Modelling, topology, UV, PBR, naming, LOD and performance standards derived from the baseline |
| [03_twin_integration_spec.md](03_twin_integration_spec.md) | Digital-twin integration contract, telemetry binding, fault/degradation visualization |
| [04_rigging_animation_simulation_spec.md](04_rigging_animation_simulation_spec.md) | Rigging/animation requirements, per-engine behaviour & physics, mission simulation and replay |
| [05_deliverables_validation_acceptance.md](05_deliverables_validation_acceptance.md) | Output folder structure, validation/acceptance criteria, assumptions and limitations |

---

## 1. Scope — What Is Being Built

For each target platform, a **twin-integrated 3D asset**, meaning three things together:

1. **An airframe model** — the UAV, accurate to published dimensions, at the visual standard defined in doc 02.
2. **An engine model** — the specific powerplant that airframe actually flies with, with individually named, fault-addressable sub-components.
3. **A twin binding** — a manifest that maps engine sub-components to telemetry channels, fault IDs, and inspection camera poses, so the backend's detection pipeline can drive the visualization (doc 03).

**An asset without item 3 is not in scope.** A model that looks correct but cannot be driven by telemetry is a render, not a digital twin — see [01_problem_statement_breakdown.md §14](../01_problem_statement_breakdown.md) and §18 for why this distinction is the one judges will probe.

---

## 2. Platform Matrix — Required UAVs and Engines

Derived from the reference libraries present in `ANUMAAN/Models_Images/`. Engine pairings verified against the spec sheets in those folders.

| # | UAV | Engine | Engine cycle | Cooling | Why it matters |
|---|---|---|---|---|---|
| 0 | **Bayraktar TB3** | TEI PD170 | Turbodiesel, 2-stage turbo | Liquid | Existing airframe baseline ⚠️ currently linked to the *wrong* engine — see audit |
| 1 | **TAPAS BH-201 / Rustom-II** | Austro AE330 (verify — folder says "E4") | Diesel, turbo | Liquid | **India's own MALE UAV. Highest strategic value for a DRDO problem statement.** |
| 2 | **Bayraktar TB2** | Rotax 912 iS Sport | Spark-ignition, naturally aspirated boxer | Air/oil | Engine already modelled to production standard — cheapest complete platform |
| 3 | **MQ-1 Predator** | Rotax 914F | Spark-ignition, turbocharged boxer | Air/oil | Best-known MALE UAV; good airframe reference coverage |
| 4 | **IAI Heron Mk II** | Rotax 915 iS | Spark-ignition, turbocharged boxer | Air/oil | Raw engine geometry already acquired (FBX) |
| 5 | **TAI ANKA** | TEI PD170 | Turbodiesel, 2-stage turbo | Liquid | Shares engine with TB3 — engine work amortizes across two airframes |
| 6 | **CASC CH-4** | Lark HFE | Heavy-fuel diesel, turbo | Liquid | Shares the heavy-fuel fault taxonomy with PD170/AE330 |

**Engine count: 6 distinct engines** (PD170 serves both TB3 and ANKA). **Airframe count: 7.**

### 2.1 The finding that reshapes this program

The existing physics model (`backend/physics/thermo_model.py`) is a **naturally-aspirated, air-cooled, spark-ignition Otto-cycle model with Rotax 912 dimensions hardcoded at module level**. Of the six engines above:

- **3 are compression-ignition diesels** (PD170, AE330, Lark HFE) — Otto cycle does not apply, and neither does half the existing fault taxonomy (a diesel has no spark plugs to misfire).
- **2 are turbocharged** spark engines (914F, 915iS) — altitude behaviour is fundamentally different; a turbo holds sea-level power to its critical altitude instead of derating linearly.
- **Only 1** (912 iS) matches the current model.

Consequences are specified in [04_rigging_animation_simulation_spec.md](04_rigging_animation_simulation_spec.md). The short version: **this is not a modelling program with some physics attached. It is a physics-generalization program with modelling attached.** Treating it as "make 6 more pretty engines" will produce assets the twin cannot honestly drive.

---

## 3. Baseline Definition — What "Same Standard" Means

Two different baselines, because the two existing assets set two different standards:

| Baseline | Asset | Sets the standard for |
|---|---|---|
| **Visual / structural** | Bayraktar TB3 (`build_tb3_digital_twin.py`, 1500+ lines procedural) | Airframe geometry, PBR materials, collection hierarchy, display modes, mechanical rigging, camera sets |
| **Functional / twin** | Rotax 912 iS (`rotax_912_is_sport.blend` + `standalone_digital_twin_app.py`) | Fault→mesh binding, live telemetry HUD, ghost/emission fault highlighting, auto-camera focus, fault injection |

**Neither baseline is complete on its own**, and this is the central structural gap the program must close:

- The **TB3 airframe has no telemetry integration whatsoever** — its controller exposes display modes, subsystem isolation, wing fold, gear retract and cameras, but zero connection to `/api/state`, faults, or health.
- The **Rotax 912 twin has no airframe** — it is an engine floating in space with an excellent fault-visualization layer.

Every new platform must satisfy **both** baselines simultaneously. That combination does not yet exist for any platform, including the two baselines themselves.

---

## 4. Priorities

Ranked by (strategic value to a DRDO submission) ÷ (work remaining):

| Priority | Platform | Rationale | Biggest blocker |
|---|---|---|---|
| **P0** | **TAPAS BH-201 + Austro AE330** | Indian MALE UAV for an Indian defence PS. A DRDO panel will ask why an indigenous platform is absent. | **Zero airframe reference imagery exists.** All 71 files are engine photos. Also **believed twin-engine**, which contradicts the single-engine framing of the existing docs ([doc 05 U1](05_deliverables_validation_acceptance.md)). Both must be resolved before modelling. |
| **P1** | **Close the TB3 integration gap** | Cheapest path to a complete, demonstrable platform: the airframe already exists at baseline quality; it needs the twin binding and its correct engine (PD170). | PD170 engine model does not exist in any form |
| **P2** | **Bayraktar TB2 + Rotax 912 iS** | The engine is already production-grade and fault-bound. Only the airframe is missing, and TB2 has the best reference coverage of any platform. | Airframe modelling only — lowest-risk full platform |
| **P3** | **MQ-1 Predator + Rotax 914F** | Strong airframe references (66 exterior, 3 ortho); engine CAD already acquired as Parasolid | CAD→Blender conversion pipeline unproven |
| **P4** | **Heron Mk II + Rotax 915 iS** | Engine geometry acquired (FBX); airframe refs thin (0 ortho) | Reference acquisition |
| **P5** | **TAI ANKA + PD170** | Engine amortized from P1; airframe refs absent | Reference acquisition |
| **P6** | **CASC CH-4 + Lark HFE** | Lowest strategic relevance to an Indian defence submission | Everything |

### 4.1 Scope warning

One airframe at TB3 standard is a 1,500-line procedural build plus a texture pipeline plus rigging plus camera setup. Seven airframes and six engines at that standard is **not achievable at uniform quality** in a hackathon timeframe. Doc 02 therefore defines **three quality tiers**, and doc 05 makes tier assignment an explicit, acceptance-tested decision rather than something discovered late.

Recommended posture: **one hero platform at full baseline quality (P0 or P1), two at tier-2, the remainder at tier-3 or deferred.** A fleet of seven mediocre assets scores worse against PS-26054 than one platform that demonstrably detects, predicts, and visualizes faults end to end.

---

## 5. Roadmap

```text
PHASE 0 — Reference triage & acquisition            [BLOCKS EVERYTHING]
  ├─ Manually triage existing reference library (contamination confirmed — see audit §4)
  ├─ Acquire orthographic/airframe refs for TAPAS, ANKA, CH-4, Heron
  └─ Verify TAPAS engine designation (AE330 vs "E4") against DRDO sources

PHASE 1 — Generalize the twin backbone              [BLOCKS ALL NEW ENGINES]
  ├─ Parameterize thermo_model.py by engine (displacement/bore/stroke/cycle/aspiration)
  ├─ Add compression-ignition + turbocharged cycle paths
  ├─ Externalize FAULT_DATABASE into per-platform manifests (doc 03)
  └─ Define per-engine fault taxonomies (diesel ≠ spark)

PHASE 2 — Close the TB3 gap                         [PROVES THE PATTERN]
  ├─ Build TEI PD170 engine model
  ├─ Bind TB3 airframe + PD170 to telemetry (first fully integrated platform)
  └─ Replace the incorrect Rotax 912 linkage in build_tb3_digital_twin.py

PHASE 3 — Hero platform (TAPAS BH-201 + AE330)      [STRATEGIC CENTREPIECE]
PHASE 4 — Tier-2 platforms (TB2, MQ-1)
PHASE 5 — Tier-3 / deferred (Heron, ANKA, CH-4)
PHASE 6 — Fleet-level validation & demo integration
```

**Phases 0 and 1 are the real critical path.** Both are non-modelling work. Starting modelling before Phase 1 produces assets that must be re-bound later; starting before Phase 0 produces dimensionally wrong airframes.

---

## 6. Explicit Non-Goals

To protect the critical path, the following are **out of scope** for this program unless every acceptance criterion in doc 05 is already met:

- Photorealistic environment/terrain work beyond what already exists
- Cinematic camera choreography and flight animation sequences
- Weapons/payload variety beyond what a fault or health indicator actually references
- Interior cockpit-equivalent detail (GCS console modelling)
- Any airframe whose engine has no working physics model behind it

Rationale in [01_problem_statement_breakdown.md §15](../01_problem_statement_breakdown.md) — these fall in the "cosmetic" bucket and do not contribute to any scored PS-26054 requirement.
