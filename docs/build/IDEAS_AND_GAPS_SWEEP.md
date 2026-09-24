# Ideas & Gaps Sweep — What the Existing Docs Contain That the Backlog Missed

*Sweep of `docs/gap_plan.md` (G01–G22), `docs/audit/04_feature_spec.md` and `07` (F01–F68), `docs/fun_req.md` (114 PS requirement rows), `docs/audit/10` (red-team), `docs/COMPETITOR_ARCHITECTURE_BREAKDOWN.md`, and the live-runtime audit of 24 September 2026. Method: list every planned feature/gap, check whether a `BACKLOG.md` row covers it, and record the ones that do not. Everything below is now a backlog row (IDs in the last column) — see `BACKLOG.md` tiers E11–E14.*

## 1. Planned in the docs, absent from the backlog

| Source | Idea | Why it matters | Backlog |
|---|---|---|---|
| gap_plan **G07** / PS **INT-03 (MUST)** | **Engine performance maps** (power, BSFC, boost vs rpm/throttle/altitude) per profile, with provenance, refined per tail | PS "MUST integrate… engine performance maps" — *no backlog row existed*; also the basis for efficiency trends (VIS-07) | **R9** |
| gap_plan **G02** | Operator levers must drive physics with first-order dynamics | Live levers are cosmetic today (verified) | **R3** |
| gap_plan **G12** | **Multi-phase mission profiles** (taxi/climb/cruise/loiter/descent) with phase-conditioned baselines | PS SIM-02/06; a single flight phase makes every "mission" scenario a lie | **R10** |
| gap_plan **G21** (⚠ not verified) | **Operational history** feeding health/RUL (exposure, past faults, maintenance) | PS INT-08 "synchronized using operational history" | **R11** (with B4.5) |
| gap_plan **G05** (⚠ not re-verified) | Sensor-drift detection is "hardcoded off" — confirm and enable | PS FDP-06 | check in **B5.6** |
| audit/07 **F45** | Mass-flow-limited cooling (hot-and-high coupling) | Two PS scenarios interact physically | folded into **R6** |
| audit/07 **F49** / PS **SYS-08** | **Test-rig / HIL mode**: a source that reads a dyno/test-cell logger and a crank/cam signal emulator that drives the real edge code | The PS's second named deployment context; also the honest path to a Raspberry Pi hardware test | **W9** |
| audit/07 **F61** | **Zero-shot time-series foundation model** control | Kills "you only beat your own simulator" | **W8** |
| audit/04 **F19–F24** | The **visual set**: per-cylinder *residual* heat map on the 3D engine · firing-order animation with the misfiring cylinder visibly skipping · live order-spectrum waterfall · sensor-trust overlay · degradation ghost · bandwidth meter | The most legible outputs of the whole system; nothing like it in any competitor | **V1–V6** |
| audit/10 §2.9 | **Impact/economics model** (parametrised ranges, sensitivity chart, never a single invented figure) | SIH scores "scale of impact"; DRDO funds with a cost case | **V7** |
| audit/10 §2.10 | **Portable ground diagnostic kit** mode (cut-out test, cranking compression, battery test, vibration signature in ~15 min, no flight clearance) | The realistic first adoption step (VRDE test cell / flight line) | **V8** |

## 2. Competitor features worth matching (from the architecture breakdown)

| Competitor | Feature | Our answer | Backlog |
|---|---|---|---|
| Dronanetra | What-if mission sandbox (loiter hours, altitude, OAT, payload, fuel sliders → thermal margins, burn profile) | Levers L1 + mission reliability (B6.2), shown live per engine | **V9** |
| Dronanetra | Fleet command view across several UAVs | `WS /ws/fleet` with all engines live | **R4** |
| Dronanetra | RBAC roles | D17 layer 7 | B9.1 |
| Aeronex | **Interactive component inspector** — click a mesh → sensor ID, value, health, specs, corrective action | Asset manifests already carry `components` with inspect poses and `sensors→mesh`; join to estimator output | **V10** |
| Vikram Sharma | One-click fault injector toggles | The L2 registry, filtered per engine — better | **R2** |
| Nirvanaa | Observed vs physics-expected dual trace with residual | Have it; show *calibrated z-residual* per channel | V-tier polish |

## 3. New ideas from this session's analysis

| Idea | Basis | Backlog |
|---|---|---|
| **N calibrations, not N detectors** — per-tail nominal calibration + one universal detector | E17: universal 0.974 vs per-engine 0.976 vs new-engine 0.973 AUROC | **W1** |
| **Classifier registry with fallback** — universal RF by default, per-engine override once labelled data exists | E17: +3–5 points per-engine; universal only −6 on a new engine | **W2** |
| **Waveform recorder + regression corpus** — every experiment/demo run can be recorded (`.npz` + manifest with fault truth and origin) and replayed bit-exactly | reproducibility; edge testing | **W3** |
| **Edge emulation with a Pi-5 profile** (4 cores, memory cap, slowdown factor) with a persistence-gated scalar downlink | user direction + D23 | **W4** |
| **Injector-fault demonstration**: scalar detectors silent, waveform channel alarms | probe: injector faults change nothing on 13 scalar channels | **W6** |
| **Trap guard**: never call sklearn one row at a time; gate + batch or compile trees | measured 11.5 ms/row | note in W2 |
| **KPI exclusion of manual levers** via `TruthRecord.origin` | keeps demos from polluting evidence | **R2** |
| **Plant class-awareness**: rpm map, thermal targets and limits from the config; fix diesel EGT/rpm | F21 | **R6** |
| **Licence gate for third-party code** (`ffbf` has none; `fbfc` MIT) | D35 | policy |
| **Reachability audit as a progress meter** | `scripts/tools/audit_reachability.py` | **B0.10** |

## 4. Where the docs were already consistent (no action)

F01–F08 crank chain, F12–F18 credibility instruments, F31–F43 physics, F46 MAVLink, F50–F58 twin/mission, F60/F62/F63 evaluation, F67/F68 edge accounting — implemented as modules (unwired, untested — see FINDINGS F10). F64–F66 (alarms, causal explanation, case retrieval) are in B6.3, B5.5, B10.1.
