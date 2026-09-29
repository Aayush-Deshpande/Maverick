# Content map

How every published page in `docs_site/` connects to the homepage and to a sidebar, for whoever builds the actual website. This file is a build reference, not a published page.

## Top level

```
index.md (homepage)
├── Technical Documentation  -> technical/01-introducing-ps26054.md
└── Our SIH Journey          -> journey/01-the-engineering-story.md
```

## Sidebar: Technical Documentation

Suggested sidebar grouping and order. Group headers are for the sidebar only; they are not separate pages.

```
Technical Documentation
│
├── Orientation
│   ├── 01  SIH Problem Statement 26054            technical/01-introducing-ps26054.md
│   ├── 02  Understanding the Engineering Problem   technical/02-the-engineering-problem.md
│   └── 03  Introducing ANUMAAN                     technical/03-introducing-anumaan.md
│
├── System architecture
│   └── 04  System Architecture                     technical/04-system-architecture.md
│
├── Digital twin and physics
│   ├── 05  The Digital Twin Core                   technical/05-the-digital-twin.md
│   ├── 06  Engine Physics and Combustion Modeling  technical/06-engine-physics.md
│   ├── 07  Telemetry and Sensor Intelligence        technical/07-telemetry-and-sensors.md
│   └── 08  Residual Analysis                        technical/08-residual-analysis.md
│
├── AI and ML stack
│   ├── 09  The AI and ML Architecture                technical/09-ai-ml-architecture.md
│   ├── 10  Bio-Inspired Sparse Novelty Coding        technical/10-bio-inspired-sparse-novelty-coding.md
│   ├── 11  Fault Diagnosis                           technical/11-fault-diagnosis.md
│   ├── 12  Vibration Analysis                        technical/12-vibration-analysis.md
│   ├── 13  Degradation Modeling                      technical/13-degradation-modeling.md
│   └── 14  Remaining Useful Life Estimation          technical/14-remaining-useful-life.md
│
├── Data
│   └── 15  Dataset Strategy                          technical/15-dataset-strategy.md
│
├── Mission
│   ├── 16  Mission Planning                          technical/16-mission-planning.md
│   └── 17  Mission Reliability                       technical/17-mission-reliability.md
│
├── 3D and simulation
│   ├── 18  The 3D Digital Twin                       technical/18-3d-digital-twin.md
│   └── 19  Blender and the Simulation Environment    technical/19-blender-and-simulation-environment.md
│
├── Operator interface
│   └── 20  The Operator Ground Control Station       technical/20-operator-gcs.md
│
└── Validation and reference
    ├── 21  Validation and Experiments                 technical/21-validation-and-experiments.md
    ├── 22  End to End Demonstration                    technical/22-end-to-end-demonstration.md
    └── 23  Technology Stack                            technical/23-technology-stack.md
```

## Sidebar: Our SIH Journey

```
Our SIH Journey
│
├── 01  The Engineering Story        journey/01-the-engineering-story.md
└── 02  Preparing for Evaluation     journey/02-preparing-for-evaluation.md
```

Two chapters are published. `journey/index.md` states plainly that more chapters (research phase, physics layer, competitive audit, AI/ML experiments, 3D twin, mission planning, integration and testing, each as a separate page) are planned. When those are written, insert them between 01 and 02 in the sidebar, since 01-the-engineering-story.md currently narrates all of that content in one consolidated chapter, if the site later splits it out, that consolidated chapter should be trimmed to avoid duplicating the standalone chapters. `02-preparing-for-evaluation.md` stays as the closing chapter.

## Reading paths (for related-article rails, not the sidebar)

Three natural sequences readers actually follow, for a "next" or "related" rail distinct from the sidebar's strict numeric order:

**Physics to diagnosis**: 05 -> 06 -> 07 -> 08 -> 09 -> 10 -> 11

**Prognostics to mission**: 12 -> 13 -> 14 -> 17 -> 16

**System to demonstration**: 03 -> 04 -> 20 -> 22

Every article already ends with its own "Related systems" links, hand-placed per article rather than generated from this map; treat those in-article links as authoritative for cross-references and this map as authoritative for sidebar structure and grouping only.

## Verified corpus state

23 technical articles (01 through 23), 2 SIH Journey chapters plus a journey index, one homepage. Zero em dashes, zero dead internal links, confirmed by a full sweep of every Markdown file in this folder as of the most recent edit.
