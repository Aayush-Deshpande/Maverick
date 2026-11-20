"""Card M0-11 / T-M0-6: runtime output goes to var/ (or $ANUMAAN_VAR_DIR), never into tracked folders."""
import re
from pathlib import Path

from backend.runtime import paths

ROOT = Path(__file__).resolve().parents[1]
WRITERS = [
    "backend/server/engine_service.py",
    "backend/graph/mission_reporter.py",
    "backend/reports/report_dump_writer.py",
    "backend/telemetry/replay_engine.py",
    "apps/mission_graph_viewer/report_scanner.py",
]
# the old repo-root locations (a "report_dump" folder under var/ is fine)
OLD_LOCATIONS = re.compile(r"""data/graph_db/fleet_graph\.json["']|data/mission_reports["']|"""
                           r"""data/telemetry/live_sorties["']|["']\.\.["'],\s*["']report_dump["']|"""
                           r"""_repo_root\(\),\s*["']report_dump["']""")


def test_no_writer_hard_codes_a_tracked_runtime_location():
    hits = []
    for rel in WRITERS:
        for i, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            if OLD_LOCATIONS.search(line) and not line.lstrip().startswith("#"):
                hits.append(f"{rel}:{i}: {line.strip()}")
    assert not hits, "\n".join(hits)


def test_var_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.VAR_DIR_ENV, str(tmp_path / "v"))
    assert paths.var_path("graph_db") == (tmp_path / "v" / "graph_db").resolve()
    assert (tmp_path / "v" / "graph_db").is_dir()


def test_seeded_file_copies_once_and_never_touches_the_seed(tmp_path, monkeypatch):
    monkeypatch.setenv(paths.VAR_DIR_ENV, str(tmp_path / "v"))
    seed = tmp_path / "seed.json"
    seed.write_text('{"seed": 1}', encoding="utf-8")
    target = paths.seeded_file(seed, "graph_db", "fleet_graph.json")
    assert target.read_text(encoding="utf-8") == '{"seed": 1}'
    target.write_text('{"runtime": 2}', encoding="utf-8")
    assert paths.seeded_file(seed, "graph_db", "fleet_graph.json").read_text(encoding="utf-8") == '{"runtime": 2}'
    assert seed.read_text(encoding="utf-8") == '{"seed": 1}'


def test_default_var_dir_is_gitignored():
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert any(line.strip() in ("var/", "/var/") for line in ignore)
