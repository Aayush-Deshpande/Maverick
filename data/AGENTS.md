# data/: datasets, recorded missions, knowledge sources
Global rules: ../AGENTS.md and ../DECISIONS.md.

## What is here
- `telemetry/`: dataset manifests, `fused_master/`, `live_sorties/` (old sortie CSVs; they hold TIMESTAMP_SEC, not elapsed time, which is the replay bug in P N1), and `source2_nasa_benchmarks/` (C-MAPSS FD001, used in card M4-07).
- `missions/`: mission markdown (Ladakh, Thar).
- `mission_reports/`, `documents/`: knowledge-base sources.
- `graph_db/fleet_graph.json`: written by the running server. NEVER commit it. Card M0-11 moves runtime output to `var/` and adds a seed file.

## Rules
- The running app writes only to `var/` (D6), never into `data/`.
- Label every dataset: SIMULATION, PUBLIC_PROXY (e.g. C-MAPSS is a turbofan benchmark, not a piston engine) or REAL_FLIGHT. Adapters that synthesise data must not carry a public dataset's name (M4-07).
- Record source URL and licence for every external dataset in `data/README.txt` (card C-04).
- Old recordings are converted by the replay converter (M5-05). Never edit the original CSVs.
- `Datasets/` at the repo root merges into `data/` in card C-04 (moves only).
