# Documentation Website — Content & Diagram Specification

## Homepage

The homepage should visually borrow the **information architecture** of the reference benchmark page:

- large technical headline,
- short project explanation,
- two prominent documentation cards,
- compact facts / metrics,
- featured technical artifact,
- and a source / evidence mindset.

Do not copy the reference site's text, branding, assets, or exact content.

### Card 1 — Technical Documentation

**Title:** Technical Documentation

**Description:** Architecture, Digital Twin, physics, AI/ML, mission planning, 3D simulation, validation, and engineering limitations.

### Card 2 — SIH Journey

**Title:** Our SIH Journey

**Description:** A factual record of the problem, research, build process, integration, testing, demonstration, and lessons learned.

## Optional homepage facts row

Use only verified project facts, for example:

- SIH PS: 26054
- Reference engine: Rotax 912 iS
- Telemetry loop: 20 Hz where currently implemented
- Architecture: physics + analytics + mission layer
- Visualization: Three.js / Blender

Do not invent performance claims.

## Diagram rules

1. Mermaid only for system diagrams.
2. Theme: neutral / grayscale.
3. Prefer `flowchart LR` or `flowchart TB`.
4. Avoid huge node labels.
5. Maximum ~10–12 nodes per diagram.
6. Use dashed subgraph boundaries for architecture layers.
7. Use one semantic accent at most; default should remain monochrome.
8. No neon, rainbow, gradient, or “AI startup” diagram styling.
9. Diagram titles should explain the engineering question being answered.
10. Every diagram should be understandable without reading source code.

## Required diagrams

### Diagram A — System overview

Telemetry → validation → physics → residuals → AI/ML → prognostics → mission consequence → GCS

### Diagram B — Edge / ground split

Deterministic low-latency path vs asynchronous cognitive path.

### Diagram C — Digital Twin

Operating context + physics model + telemetry → state / residuals.

### Diagram D — AI stack

Residuals → sparse novelty coding → diagnosis → degradation → conformal RUL → explanation.

### Diagram E — Mission loop

Mission profile + environment + engine health → simulation → reliability → operator options.

### Diagram F — 3D coupling

Authoritative runtime state → Three.js / Blender / simulation consumers.

### Diagram G — Evidence loop

Claim → source → test → result → documentation.

### Diagram H — SIH journey

Problem → research → architecture → build → integration → validation → demo → lessons.
