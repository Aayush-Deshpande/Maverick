"""Runtime output location (card M0-11, DECISIONS D6).

Everything the running system writes (fleet graph, mission reports, sortie bundles, live telemetry logs) goes under
ONE folder: $ANUMAAN_VAR_DIR, else <repo>/var (gitignored). Nothing at runtime writes into tracked folders.
Tracked seed files (e.g. data/graph_db/fleet_graph.seed.json) are copied in on first use and never written back.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VAR_DIR_ENV = "ANUMAAN_VAR_DIR"
DEFAULT_VAR_DIR = REPO_ROOT / "var"


def var_dir() -> Path:
    raw = os.environ.get(VAR_DIR_ENV)
    path = Path(raw).expanduser().resolve() if raw else DEFAULT_VAR_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def var_path(*parts: str) -> Path:
    """A folder under var/ (created). For a file, pass its folder parts and join the name yourself."""
    path = var_dir().joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def seeded_file(seed: Path, *parts: str) -> Path:
    """Path of a runtime file under var/ that starts as a copy of a tracked seed file (copied once, if missing)."""
    *folders, name = parts
    target = var_path(*folders) / name
    if not target.exists() and seed.exists():
        shutil.copyfile(seed, target)
    return target
