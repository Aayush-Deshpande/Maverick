"""
Engine-agnosticism ratchet (docs/build/UNIVERSALITY_AUDIT.md, decision D27).

The system is meant to work for whichever engine is selected from configs/engines/
(and later for other MALE propulsion classes), not for one Rotax. Today it does not:
the twin, pipeline, validators, RUL model and UI hardcode a 4-cylinder Rotax 912 iS.
Fixing that is a multi-step refactor (backlog tier E12). Until it is finished, this
test is a **ratchet**: it counts engine-specific literals in the modules that are
supposed to become engine-agnostic and fails if any count goes UP. Refactors lower
the counts; run ``python tests/test_engine_agnostic_ratchet.py --update`` afterwards
to lock the lower baseline in (the updater refuses to raise a number).

What is counted (regexes over source text, comments included -- a comment that says
"Rotax" in an inference module is also a smell):
  * cyl   -- fixed cylinder-index channel names  CHT_1..4 / EGT_1..4 / cht_1 ...
  * brand -- the word Rotax / Austro (as a name, not a config id)
  * model -- the numbers 912 / 914 / 915 used as an engine model
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASELINE = Path(__file__).with_name("engine_agnostic_baseline.json")

# Modules that must become engine-agnostic (inference, twin, live service, UI).
# Deliberately NOT included: configs/, engine-specific manifests, tests, docs, the
# engine_config loader itself, and per-engine plant physics.
GUARDED = [
    "backend/physics/thermo_model.py",
    "backend/physics/sensor_validator.py",
    "backend/ml/detection_pipeline.py",
    "backend/ml/rul_estimator.py",
    "backend/ml/fault_classifier.py",
    "backend/ml/anomaly_detector.py",
    "backend/ml/spectral_analyser.py",
    "backend/telemetry/can_streamer.py",
    "backend/server/engine_service.py",
    "backend/server/schemas.py",
    "backend/agent/diagnostic_agent.py",
    "backend/agent/copilot.py",
    "backend/core/frame.py",
    "backend/sources/plant_source.py",
    "frontend/src/components/ReadingsPanel.tsx",
    "frontend/src/components/PropulsionEngineerPanel.tsx",
    "frontend/src/components/CalculationsPanel.tsx",
    "frontend/src/components/DiagnosticCard.tsx",
    "frontend/src/components/SubsystemHealthCard.tsx",
]

PATTERNS = {
    "cyl": re.compile(r"\b(?:CHT|EGT|cht|egt)_[1-4]\b"),
    "brand": re.compile(r"Rotax|Austro|AE300|AE330", re.IGNORECASE),
    "model": re.compile(r"\b91[245]\b"),
}


def count_file(rel: str) -> dict:
    path = REPO / rel
    if not path.exists():
        return {k: 0 for k in PATTERNS}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {k: len(rx.findall(text)) for k, rx in PATTERNS.items()}


def current_counts() -> dict:
    return {rel: count_file(rel) for rel in GUARDED}


def _load_baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def test_engine_specific_literals_never_increase():
    base = _load_baseline()
    now = current_counts()
    regressions = []
    for rel, counts in now.items():
        allowed = base.get(rel)
        if allowed is None:
            regressions.append(f"{rel}: new guarded file has no baseline (run --update once)")
            continue
        for kind, n in counts.items():
            if n > allowed.get(kind, 0):
                regressions.append(f"{rel}: '{kind}' literals rose {allowed.get(kind, 0)} -> {n}")
    assert not regressions, (
        "Engine-specific hardcoding increased in modules that must become engine-agnostic "
        "(docs/build/UNIVERSALITY_AUDIT.md). Derive it from the selected EngineConfig/profile "
        "instead of writing a literal:\n  " + "\n  ".join(regressions)
    )


def test_baseline_is_not_stale_upward():
    """A baseline that is far above reality hides regressions; keep it tight."""
    base = _load_baseline()
    now = current_counts()
    loose = [f"{rel}.{k}: baseline {base[rel][k]} vs actual {n}"
             for rel, c in now.items() if rel in base
             for k, n in c.items() if base[rel].get(k, 0) > n]
    assert not loose, ("Baseline is higher than actual -- lock in the improvement with "
                       "`python tests/test_engine_agnostic_ratchet.py --update`:\n  " + "\n  ".join(loose))


def _update() -> int:
    now = current_counts()
    old = _load_baseline() if BASELINE.exists() else None
    if old:
        for rel, c in now.items():
            for k, n in c.items():
                if rel in old and n > old[rel].get(k, 0):
                    print(f"REFUSING: {rel} '{k}' rose {old[rel][k]} -> {n}; a baseline may only go down")
                    return 1
    BASELINE.write_text(json.dumps(now, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    total = {k: sum(c[k] for c in now.values()) for k in PATTERNS}
    print("baseline written:", total)
    return 0


if __name__ == "__main__":
    if "--update" in sys.argv:
        sys.exit(_update())
    now = current_counts()
    for rel, c in sorted(now.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"{sum(c.values()):4d}  {c}  {rel}")
    print("TOTAL", {k: sum(c[k] for c in now.values()) for k in PATTERNS})
