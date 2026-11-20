"""Card M0-01: engine configs validate against configs/schema/engine.schema.json and carry the sourced data
(P Part 2, DECISIONS D46). Values pinned here come from OM-912 i, EASA TCDS E.121/E.200, the Rotax 914 OM and DRDO."""
import json
from pathlib import Path

import jsonschema
import pytest

from backend.physics.engine_config import available_engines, load_engine_config

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "configs" / "schema" / "engine.schema.json").read_text(encoding="utf-8"))


def _raw(engine_id):
    return json.loads((ROOT / "configs" / "engines" / f"{engine_id}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("engine_id", available_engines())
def test_engine_config_matches_schema(engine_id):
    jsonschema.validate(_raw(engine_id), SCHEMA)


@pytest.mark.parametrize("engine_id", available_engines())
def test_every_operating_limit_and_banded_limit_has_a_source(engine_id):
    cfg = load_engine_config(engine_id)
    assert not cfg.unlabelled_limits(), cfg.unlabelled_limits()
    for channel, band in cfg.limits.items():
        assert band.get("ref"), f"{engine_id}.limits.{channel} has no ref"


def test_carburetted_914_has_no_injection_timing_or_rail():
    cfg = load_engine_config("rotax_914")
    assert cfg.fuel_system == "CARBURETTOR"
    assert cfg.nominal_inj_timing_btdc is None
    assert cfg.rail_pressure_bar is None
    assert cfg.turbo.critical_altitude_takeoff_ft == 8000.0
    assert cfg.turbo.critical_altitude_ft == 16000.0


def test_912_is_sport_matches_om_912i():
    cfg = load_engine_config("rotax_912is")
    assert cfg.rated_power_kw == 73.5 and cfg.max_continuous_power_kw == 72.0
    assert cfg.operating_limits["egt_max_c"] == 950.0
    assert cfg.operating_limits["coolant_t_max_c"] == 120.0
    assert cfg.limits["oil_p"]["rpm_rule"]["above_rpm"] == 3500
    assert cfg.provenance_status("max_continuous_power_kw") == "MANUAL"


def test_915_is_matches_tcds_e121():
    cfg = load_engine_config("rotax_915is")
    assert (cfg.rated_power_kw, cfg.max_continuous_power_kw) == (104.0, 99.0)
    assert cfg.turbo.critical_altitude_ft == 15000.0
    assert 2.9 <= cfg.rail_pressure_bar <= 3.2


def test_ae300_uses_certified_limits_from_tcds_e200():
    cfg = load_engine_config("austro_ae300")
    assert cfg.overspeed_rpm == 4220.0
    assert cfg.max_operating_altitude_ft == 18000.0
    assert cfg.operating_limits["coolant_t_max_c"] == 105.0
    assert cfg.operating_limits["oil_t_max_c"] == 140.0
    assert cfg.operating_limits["gearbox_t_max_c"] == 120.0
    assert cfg.turbo.boost_control == "VGT"
    assert cfg.provenance_status("turbo.critical_altitude_ft") == "ASSUMED"


def test_vrde_flat_rated_to_11000_ft_per_drdo():
    cfg = load_engine_config("vrde_jayem_2_2l")
    assert cfg.turbo.critical_altitude_ft == 11000.0
    assert cfg.provenance_status("turbo.critical_altitude_ft") == "PUBLIC"


def test_hardware_flags_needed_by_fault_applicability_are_present():
    for engine_id in available_engines():
        raw = _raw(engine_id)
        for flag in ("fuel_system", "ignition_circuits", "ecu_lanes", "glow_plugs", "thermostat", "propeller_governor"):
            assert flag in raw, f"{engine_id} missing {flag}"
