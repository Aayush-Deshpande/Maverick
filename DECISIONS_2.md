# DECISIONS_2.md: ANUMAAN binding decisions (Part 2: D70 onwards)

This file records binding architectural, domain, and workflow decisions starting from D70.
Precedence: `DECISIONS_2.md` > `DECISIONS.md` (Part 1: D1–D69) > `ANUMAAN_AI_COURSE_OF_ACTION.txt` > `ANUMAAN_ROADMAP_AND_PS_COVERAGE.txt` (P) > `ANUMAAN_COMPONENTS_ADDENDUM.txt` (A) > `ANUMAAN_AUDIT_REPORT.txt` (R).

Part 1 decisions D1 through D69 are preserved in [DECISIONS.md](DECISIONS.md).

| Decision | Date | Scope and rule | Rationale / context |
| :--- | :--- | :--- | :--- |
| D70 | 2026-11-22 | Multi-part documentation rotation: `DECISIONS_2.md` (D70 onwards) and `PROGRESS_2.txt` (Phase 8 onwards) established as the active continuation files for all future agent sessions. Preserves `DECISIONS.md` (D1–D69) and `PROGRESS.txt` (Phases 0–7) as immutable Part 1 archives to prevent context bloating while maintaining 100% rule traceability. | Prasad: "ALso now as hte decion and progress file is gotten too big lets make another on enad main tin it now on in future". |
| D71 | 2026-11-22 | Multi-Mode Aerospace 3D Engine Viewport (UX-01): `EngineViewer3D` provides 4 real-time selectable render modes: (1) Solid CAD PBR, (2) Physical X-Ray Glass (`MeshPhysicalMaterial`, transmission 0.92, IOR 1.48, thickness 0.8, clearcoat 1.0) revealing internal mechanical assemblies, (3) Dynamic FLIR Thermal Pyrometry (live 20 Hz thermodynamic CHT 1..4 and EGT 1..4 blackbody vertex incandescence, smoked obsidian casing, `ThermalLegend` HUD), (4) Holographic Twin Ghost. Diagnostic/anomaly highlights always retain absolute visual precedence across all modes. | User request: "Transparent X-Ray crankcase shader revealing internal pistons/valves, and per-cylinder thermal vertex heat-maps and shit But make sure for visualizations and stuff we value realism it should look so real that feels like CGI or something or actual real life shit". |
