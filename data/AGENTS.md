# data/: datasets, recorded missions, knowledge sources
Global rules: ../AGENTS.md and ../DECISIONS.md.

## What is here
- `telemetry/`: dataset manifests, `fused_master/`, `live_sorties/` (old sortie CSVs; they hold TIMESTAMP_SEC, not elapsed time, which is the replay bug in P N1), and `source2_nasa_benchmarks/` (C-MAPSS FD001, used in card M4-07).
- `missions/`: mission markdown (Ladakh, Thar).
- `mission_reports/`, `documents/`: knowledge-base sources.
- `graph_db/fleet_graph.seed.json`: tracked seed copied once to var/graph_db/fleet_graph.json (M0-11). `graph_db/fleet_graph.json` is the old runtime copy, no longer written; never commit its local changes.

## data/documents/ (RAG folder)
Empty since 19 Nov 2026 (card P0-04), except a .gitkeep. Its previous content was AI-generated text named like
Rotax/DRDO manuals, now in archive_tracked/synthetic_rag_corpus/ (D34, D44). Do not put README or notes files here:
local_store.py indexes every .md/.txt/.pdf/.docx it finds. The real corpus is filled in Phase 8b (AI-03/AI-03a).

## Rules
- The running app writes only to `var/` (D6), never into `data/`.
- Label every dataset: SIMULATION, PUBLIC_PROXY (e.g. C-MAPSS is a turbofan benchmark, not a piston engine) or REAL_FLIGHT. Adapters that synthesise data must not carry a public dataset's name (M4-07).
- Record source URL and licence for every external dataset in `data/README.txt` (card C-04).
- Old recordings are converted by the replay converter (M5-05). Never edit the original CSVs.
- `Datasets/` at the repo root merges into `data/` in card C-04 (moves only).
