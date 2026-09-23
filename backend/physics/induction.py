"""
Induction path: air filter restriction and the dust-ingestion wear chain — F43.

The problem statement asks for "environmental condition simulation" and every
team implements it as a slider that scales a number. Physically, dust is not a
slider — it is a degradation driver with memory, and it produces the single most
India-relevant failure chain available in this problem:

    dust exposure (Thar, desert forward operating strips, brownout)
        -> filter media loading -> dP across filter rises
        -> manifold pressure deficit at constant throttle     [observable]
        -> power and fuel-efficiency loss
    and, once the filter is breached or bypassed:
        -> silica reaches the cylinders
        -> abrasive bore and ring wear
        -> blow-by rises, oil consumption rises, compression falls  [observable]
        -> Si appears in the oil wear-metal spectrum           [confirmatory]

Desert operations are known to be brutal on engines — rotary-wing desert
deployments have reported engine reliability reduced by as much as half, and
inertial separators cannot remove sub-10-micron particles, which are the ones
that do the abrasive damage.

The important design property here is that filter restriction is **observable
without a dedicated sensor**: MAP deficit at a known throttle and altitude is
already in the telemetry. A dP sensor improves confidence but is not required,
which matters for retrofit onto an existing airframe.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

__all__ = ["DustEnvironment", "InductionState", "InductionModel", "DUST_ENVIRONMENTS"]


@dataclass(frozen=True)
class DustEnvironment:
    """Airborne particulate concentration for an operating environment."""

    name: str
    concentration_mg_m3: float
    fine_fraction: float  # fraction below ~10 microns (defeats inertial separators)
    description: str = ""


DUST_ENVIRONMENTS = {
    "CLEAN_MARITIME": DustEnvironment("CLEAN_MARITIME", 0.02, 0.30,
                                      "Over-water ISR; salt aerosol, little mineral dust"),
    "TEMPERATE_INLAND": DustEnvironment("TEMPERATE_INLAND", 0.15, 0.45, "Baseline inland operation"),
    "SEMI_ARID": DustEnvironment("SEMI_ARID", 1.2, 0.55, "Deccan / scrubland in dry season"),
    "DESERT_THAR": DustEnvironment("DESERT_THAR", 6.0, 0.62,
                                   "Thar desert summer; persistent suspended mineral dust"),
    "BROWNOUT": DustEnvironment("BROWNOUT", 45.0, 0.70,
                                "Unprepared strip takeoff/landing; short duration, extreme load"),
}


@dataclass
class InductionState:
    filter_loading: float = 0.0  # 0 = new, 1 = fully blocked
    filter_dp_kpa: float = 0.5
    map_deficit_kpa: float = 0.0  # manifold pressure lost to restriction
    volumetric_efficiency_factor: float = 1.0
    filter_breached: bool = False
    silica_ingress_g: float = 0.0  # cumulative mass past the filter
    bore_wear_index: float = 0.0  # 0..1 proxy for abrasive cylinder wear
    blowby_factor: float = 1.0  # multiple of nominal crankcase blow-by
    compression_loss_fraction: float = 0.0
    remaining_filter_hours: Optional[float] = None

    def as_dict(self) -> dict:
        return {
            "AIR_FILTER_LOADING": round(self.filter_loading, 4),
            "AIR_FILTER_DP_KPA": round(self.filter_dp_kpa, 3),
            "INDUCTION_MAP_DEFICIT_KPA": round(self.map_deficit_kpa, 3),
            "VOLUMETRIC_EFF_FACTOR": round(self.volumetric_efficiency_factor, 4),
            "AIR_FILTER_BREACHED": self.filter_breached,
            "SILICA_INGRESS_G": round(self.silica_ingress_g, 5),
            "BORE_WEAR_INDEX": round(self.bore_wear_index, 5),
            "BLOWBY_FACTOR": round(self.blowby_factor, 4),
            "COMPRESSION_LOSS_FRAC": round(self.compression_loss_fraction, 5),
            "FILTER_REMAINING_HOURS": (None if self.remaining_filter_hours is None
                                       else round(self.remaining_filter_hours, 1)),
        }


class InductionModel:
    """Filter loading, restriction, and the abrasive wear it eventually permits."""

    def __init__(
        self,
        filter_capacity_g: float = 180.0,
        nominal_dp_kpa: float = 0.5,
        breach_threshold: float = 0.95,
        engine_airflow_m3_s: float = 0.075,
        bypass_fitted: bool = True,
    ) -> None:
        self.filter_capacity_g = filter_capacity_g
        self.nominal_dp_kpa = nominal_dp_kpa
        self.breach_threshold = breach_threshold
        self.engine_airflow_m3_s = engine_airflow_m3_s
        # A bypass door protects against starvation but is exactly what lets
        # unfiltered air — and silica — reach the engine.
        self.bypass_fitted = bypass_fitted
        self.state = InductionState()
        self._captured_g = 0.0

    def update(
        self,
        dt_sec: float,
        environment: DustEnvironment | str = "TEMPERATE_INLAND",
        engine_rpm: float = 5000.0,
        rated_rpm: float = 5800.0,
        manifold_pressure_kpa: float = 100.0,
    ) -> InductionState:
        env = (DUST_ENVIRONMENTS[environment] if isinstance(environment, str) else environment)
        s = self.state

        # Mass of dust presented to the filter this step.
        flow = self.engine_airflow_m3_s * max(0.1, engine_rpm / max(rated_rpm, 1.0))
        presented_g = env.concentration_mg_m3 * 1e-3 * flow * dt_sec

        # Capture efficiency falls as the fine fraction rises — the physical
        # reason desert dust is more damaging than its mass alone suggests.
        capture_eff = 0.995 - 0.35 * env.fine_fraction
        captured = presented_g * capture_eff
        passed = presented_g - captured

        self._captured_g += captured
        s.filter_loading = min(1.0, self._captured_g / max(self.filter_capacity_g, 1e-6))

        # Restriction rises non-linearly with loading.
        s.filter_dp_kpa = self.nominal_dp_kpa * (1.0 + 30.0 * s.filter_loading ** 2.5)
        s.map_deficit_kpa = s.filter_dp_kpa - self.nominal_dp_kpa
        s.volumetric_efficiency_factor = max(
            0.55, 1.0 - 0.9 * (s.map_deficit_kpa / max(manifold_pressure_kpa, 1.0))
        )

        # Breach / bypass: once open, essentially everything gets through.
        s.filter_breached = s.filter_loading >= self.breach_threshold
        if s.filter_breached and self.bypass_fitted:
            passed += captured * 0.85

        s.silica_ingress_g += passed
        # Abrasive wear accrues with ingested silica mass and with load.
        load = max(0.1, engine_rpm / max(rated_rpm, 1.0))
        # NOTE: coefficient is a CALIBRATION PLACEHOLDER. It sets how much
        # abrasive wear a gram of ingested silica causes and is not traceable to
        # any wear test; only relative comparisons between environments are
        # currently defensible.
        s.bore_wear_index = min(1.0, s.bore_wear_index + passed * 4.0e-4 * load)
        s.blowby_factor = 1.0 + 4.5 * s.bore_wear_index ** 1.4
        s.compression_loss_fraction = min(0.45, 0.35 * s.bore_wear_index ** 1.2)

        # Remaining filter life at the current loading rate.
        rate_per_sec = captured / max(dt_sec, 1e-9)
        if rate_per_sec > 0:
            remaining_g = max(0.0, self.filter_capacity_g - self._captured_g)
            s.remaining_filter_hours = remaining_g / rate_per_sec / 3600.0
        else:
            s.remaining_filter_hours = None
        return s

    def expected_map(self, unrestricted_map_kpa: float) -> float:
        """What MAP should read given current restriction — the detection hook.

        Comparing measured MAP against this at a known throttle and altitude is
        how filter loading is detected without a dedicated dP sensor.
        """
        return unrestricted_map_kpa - self.state.map_deficit_kpa

    def service_filter(self) -> None:
        """Maintenance action: new filter. Bore wear is NOT reset — it is permanent."""
        self._captured_g = 0.0
        self.state.filter_loading = 0.0
        self.state.filter_dp_kpa = self.nominal_dp_kpa
        self.state.map_deficit_kpa = 0.0
        self.state.filter_breached = False
        self.state.volumetric_efficiency_factor = 1.0
