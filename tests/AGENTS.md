# tests/: pytest suite (43 files today)
Global rules: ../AGENTS.md and ../DECISIONS.md.

## Baseline on Beta (19 Nov 2026)
333 passed, 3 failed, 7 skipped, 1 xfailed, about 5 min. The 3 known failures:
- `test_engine_agnostic_ratchet.py::test_engine_specific_literals_never_increase` (real; fixed by M0-07 / M8-04)
- `test_runtime_hub.py::test_cpu_cost_is_small` (timing-sensitive; M8-04)
- `test_runtime_hub.py::test_all_five_engines_concurrent_load_and_isolation` (timing-sensitive; M8-04)

Any other failure is a regression.

## Guard tests that must never be weakened
- `test_no_truth_leak.py`: inference code must not read truth. Extend its package list when you add an inferring package.
- `test_engine_agnostic_ratchet.py` + `engine_agnostic_baseline.json`: engine literals may only go DOWN. Never raise the baseline.
- `test_engine_config_provenance.py`: every config number has provenance.

## Where new tests go (IDs from P Part 7)
| Folder | Tests |
|---|---|
| `tests/config/` | T-CFG (schemas, provenance, applicability) |
| `tests/dynamic/` | T-DYN-1..8 (static scan + `allowlist.txt`, frozen channel, perturbation, no-truth-leak import graph, add-an-engine, add-a-fault, determinism, no-silent-fallback) |
| `tests/sim/` | unit tests per `sim` module; T-PHY-1..11 |
| `tests/faults/` | T-FLT-1..4 (signature matrix: every applicable engine x fault moves its signature) |
| `tests/status/` | T-STS |
| `tests/detect/` | T-DET |
| `tests/prognose/` | T-PRG |
| `tests/api/` | T-API, T-WS, cross-client tests |
| `tests/missions/` | T-MIS |
| `tests/assets/` | manifest and GLB node tests (A section 8), T-REPO |

## Rules
- A new behaviour gets a test that fails without it. Show the failing run in the session report.
- Never: raise tolerances, add skip/xfail to hide a failure, delete asserts, or mock the physics in physics tests. Exception: T-DYN xfails listed in card M0-12, each naming the card that removes it.
- Fault tests run paired: the same seed with and without the fault, so every difference comes from the fault.
- Seeds: train/calibration seeds and test seeds are disjoint (test offset >= 1000).
- Timing tests measure relative cost, not absolute milliseconds.
- Tests must not write tracked files. Use `tmp_path` or `var/`.
