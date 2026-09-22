# ANUMAAN Compiled Textbook (`compiled_tb`)

The background knowledge behind Project ANUMAAN (DRDO PS-26054), written as a textbook. Read it to understand **why** the system exists, **what** physics and engineering it rests on, and **how** the code implements it, before changing anything.

## How to read

- New to the project: read Part I in order, then jump to whichever part matches your work.
- Working on the backend: Parts II–IV first, then the matching chapter in Part VI.
- Each chapter stands alone and links to the others where needed.

## Chapter format

Every chapter follows the same structure:

1. **Learning objectives**
2. Intuition first, then the formal treatment
3. Formulas with symbols, units and a worked example (Rotax 912 iS numbers where possible)
4. **Where this lives in ANUMAAN**: links to the actual code, and whether that code is correct
5. **Common misconceptions**
6. **Review questions**
7. **References**

### Evidence labels

| Label | Meaning |
|---|---|
| **[V]** | Verified from a primary or official source (manufacturer datasheet, government document, peer-reviewed paper) |
| **[N]** | Reported by news or secondary sources; treat as likely but not certain |
| **[A]** | Our own analysis or interpretation |

Real-world facts are dated. Anything about programmes, fleets or procurement is "as of" the chapter's research date and will age.

## Table of contents

| Part | # | Chapter | Status |
|---|---|---|---|
| **I. Context** | 1 | [The Problem & the Mission](01_the_problem_and_mission.md) | ✅ Draft (2026-09-17) |
| | 2 | Engine health monitoring in aviation today | Planned |
| | 3 | Digital twins in aerospace | Planned |
| | 4 | Competitive landscape & how to stand out | Planned |
| **II. The engine** | 5 | IC engine fundamentals | Planned |
| | 6 | Aero piston engines: Rotax 912 iS, turbocharging, heavy-fuel diesels | Planned |
| | 7 | Engine thermodynamics & heat transfer | Planned |
| | 8 | Sensors & instrumentation, and how they fail | Planned |
| | 9 | Engine control & data buses: FADEC, timing, CAN, datalinks | Planned |
| **III. Failure & reliability** | 10 | How aero piston engines fail | Planned |
| | 11 | Reliability engineering & maintenance strategy | Planned |
| | 12 | Vibration analysis | Planned |
| **IV. Data & AI** | 13 | Signal processing & sensor fusion | Planned |
| | 14 | Anomaly detection | Planned |
| | 15 | Fault diagnosis & evaluation pitfalls | Planned |
| | 16 | Prognostics & Remaining Useful Life | Planned |
| | 17 | Physics-informed & hybrid models, edge & adaptive learning | Planned |
| **V. The digital twin** | 18 | Digital twin architecture | Planned |
| | 19 | Simulation & mission modelling | Planned |
| | 20 | HMI & alarm management for ground stations | Planned |
| | 21 | Secure telemetry & deployment | Planned |
| **VI. ANUMAAN as built** | 22 | Architecture walkthrough | Planned |
| | 23 | Streaming & APIs | Planned |
| | 24 | The physics model, formula by formula | Planned |
| | 25 | The ML pipeline | Planned |
| | 26 | Known gaps & redesign | Planned |
| | 27 | Glossary & references | Planned |

## Related project documents

- [Official problem statement](../docs/00_official_problem_statement.md)
- [Problem statement breakdown](../docs/01_problem_statement_breakdown.md)
- [Explicit functional requirements](../docs/fun_req.md)
- [Implementation gap plan](../docs/gap_plan.md)
