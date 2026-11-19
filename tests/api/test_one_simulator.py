"""Card M0-07: one simulator per engine (T-M0-5) and per-client engine selection.

- RuntimeHub never calls into the legacy EngineStateService (the 912 used to be written by two simulators).
- Every engine somebody subscribes to ticks at full rate; the idle divisor comes from configs/runtime.json.
"""
import ast
import json
from pathlib import Path

from backend.runtime.hub import RuntimeHub, load_runtime_settings

ROOT = Path(__file__).resolve().parents[2]


def test_hub_does_not_reference_the_legacy_service():  # T-M0-5
    tree = ast.parse((ROOT / "backend" / "runtime" / "hub.py").read_text(encoding="utf-8"))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | \
            {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    mods = {getattr(n, "module", "") or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert "sync_from_tick" not in names and "EngineStateService" not in names
    assert not any("engine_service" in m for m in mods)


def test_idle_divisor_comes_from_config():
    cfg = json.loads((ROOT / "configs" / "runtime.json").read_text(encoding="utf-8"))
    settings = load_runtime_settings()
    assert settings["idle_tick_divisor"] == cfg["idle_tick_divisor"]
    hub = RuntimeHub(engines=["rotax_912is", "rotax_914"], warmup_ticks=200)
    assert hub.idle_tick_divisor == cfg["idle_tick_divisor"]


def test_every_active_engine_ticks_at_full_rate():
    hub = RuntimeHub(engines=["rotax_912is", "rotax_914"])
    hub.calibrate_all(parallel=False)
    hub.select("rotax_912is", warm_heavy=False)
    hub.set_active({"rotax_914"})                     # another client watches the 914
    first = hub.tick_all()
    t0 = {e: first[e].frame.t for e in hub.engines}
    for _ in range(hub.idle_tick_divisor + 1):
        out = hub.tick_all(force_all=False)
    for e in ("rotax_912is", "rotax_914"):
        assert out[e].frame.t > t0[e]
    # both advanced every call: elapsed sim time is equal for selected and active engine
    assert abs((out["rotax_912is"].frame.t - t0["rotax_912is"]) - (out["rotax_914"].frame.t - t0["rotax_914"])) < 1e-6
