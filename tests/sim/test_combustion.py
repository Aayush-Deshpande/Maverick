"""M1-05 fuels + combustion (P Part 4 Step 1.3d): per-cylinder indicated work, lambda/timing efficiency, knock, smoke, COV."""
import pytest

from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.combustion import Combustion, load_fuel

SI = [e for e in available_engines() if load_engine_config(e).ignition_mode == "SPARK_IGNITION"]
CI = [e for e in available_engines() if load_engine_config(e).ignition_mode == "COMPRESSION_IGNITION"]


@pytest.mark.parametrize("engine_id", available_engines())
def test_fuel_properties_come_from_the_table(engine_id):
    cfg = load_engine_config(engine_id)
    f = load_fuel(cfg.fuel)
    c = Combustion.for_engine(cfg)
    assert c.lhv_j_kg == pytest.approx(f["lhv_mj_kg"] * 1e6)
    assert 14.0 < c.stoich_afr < 15.5


@pytest.mark.parametrize("engine_id", SI)
def test_si_rich_mixture_releases_only_the_air_limited_energy(engine_id):
    c = Combustion.for_engine(load_engine_config(engine_id))
    m_f = 1e-4
    stoich = c.indicated_work_j(m_f, 1.0)
    assert c.indicated_work_j(m_f, 0.8) == pytest.approx(0.8 * stoich, rel=0.02)     # oxygen-limited


@pytest.mark.parametrize("engine_id", SI)
def test_si_timing_and_misfire(engine_id):
    c = Combustion.for_engine(load_engine_config(engine_id))
    w = c.indicated_work_j(1e-4, 1.0)
    assert 0.94 < c.indicated_work_j(1e-4, 1.0, timing_error_deg=10) / w < 0.98      # MBT curve ~4 %
    assert c.indicated_work_j(1e-4, 1.0, quality=0.0) == 0.0                          # F01 misfire
    assert c.indicated_work_j(1e-4, 1.6) == 0.0                                       # beyond the lean misfire limit


@pytest.mark.parametrize("engine_id", CI)
def test_ci_smoke_limit_caps_fuel(engine_id):
    c = Combustion.for_engine(load_engine_config(engine_id))
    m_air = 1e-3
    demand = m_air / c.stoich_afr                     # would be lambda 1.0
    assert c.deliverable_fuel(demand, m_air) == pytest.approx(m_air / (c.stoich_afr * c.smoke_lambda_min))
    assert c.deliverable_fuel(demand * 0.5, m_air) == pytest.approx(demand * 0.5)


def test_cov_rises_lean_low_load_and_weak_ignition():
    c = Combustion.for_engine(load_engine_config(SI[0]))
    base = c.cov_imep_pct(1.0, load_fraction=0.8)
    assert base < c.cov_limit_pct
    assert c.cov_imep_pct(1.35, load_fraction=0.8) > base
    assert c.cov_imep_pct(1.0, load_fraction=0.1) > base
    assert c.cov_imep_pct(1.0, load_fraction=0.8, ignition_energy=0.5) > base        # one lane lost (F04)


def test_knock_index_rises_with_map_charge_temperature_and_advance():
    c = Combustion.for_engine(load_engine_config(SI[0]))
    ref = c.knock_index(101.3e3, 313.15, 0.0)
    assert ref == pytest.approx(1.0)
    assert c.knock_index(150e3, 313.15, 0.0) > ref
    assert c.knock_index(101.3e3, 353.15, 0.0) > ref
    assert c.knock_index(101.3e3, 313.15, 5.0) > ref
