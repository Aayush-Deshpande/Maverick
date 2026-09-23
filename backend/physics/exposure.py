"""
Environmental exposure accumulator — F40.

The problem statement asks the twin to use "operational history". Sortie records
and anomaly logs are history of *events*; this is history of *conditions*, and
it is the part that changes future predictions.

Two engines with identical hours are not identically worn. One that flew 240 h
over the Thar in summer has loaded filters faster, accumulated more abrasive
bore wear, and run closer to its cooling limit than one that flew the same hours
over water in winter. Without exposure accounting, a fleet health comparison is
comparing hours, which is exactly the time-based maintenance the problem
statement asks us to move away from.

What this accumulates per airframe/engine:

  * dust-hours, weighted by concentration — drives filter life and bore wear
  * cold-soak cycles and time below the fuel cloud point — drives F42 risk
  * hot-shutdown events — turbo coking, the classic turbocharger killer
  * thermal cycles and time at high CHT — feeds the F36 damage model
  * salt exposure hours — maritime ISR corrosion
  * altitude-hours above the turbo critical altitude — sustained high PR

The output is a set of *acceleration factors*: multipliers on nominal wear rates
that make "this tail is ageing 1.8x faster than fleet baseline" a computed
statement rather than an impression.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Optional

__all__ = ["ExposureRecord", "ExposureAccumulator"]


@dataclass
class ExposureRecord:
    """Cumulative environmental exposure for one engine serial."""

    engine_serial: str = "UNKNOWN"
    total_hours: float = 0.0

    # Particulate
    dust_hours_weighted: float = 0.0  # hours x (concentration / baseline)
    brownout_events: int = 0

    # Cold
    cold_soak_hours: float = 0.0  # OAT below -20 C
    hours_below_cloud_point: float = 0.0
    cold_start_cycles: int = 0

    # Heat
    hot_shutdown_events: int = 0  # shutdown with turbo hot
    hours_above_cht_caution: float = 0.0
    thermal_cycles: int = 0

    # Marine / corrosion
    salt_exposure_hours: float = 0.0

    # Altitude
    hours_above_critical_altitude: float = 0.0
    max_altitude_ft: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)


class ExposureAccumulator:
    """Streaming exposure accounting with derived wear-acceleration factors."""

    BASELINE_DUST_MG_M3 = 0.15  # TEMPERATE_INLAND — the reference environment
    COLD_SOAK_THRESHOLD_C = -20.0
    CHT_CAUTION_C = 120.0
    HOT_SHUTDOWN_EGT_C = 400.0

    def __init__(self, engine_serial: str = "UNKNOWN",
                 record: Optional[ExposureRecord] = None) -> None:
        self.record = record or ExposureRecord(engine_serial=engine_serial)
        self._prev_running: Optional[bool] = None
        self._prev_cht: Optional[float] = None
        self._cycle_low: Optional[float] = None

    def update(
        self,
        dt_sec: float,
        dust_mg_m3: float = 0.15,
        oat_c: float = 15.0,
        cht_c: float = 110.0,
        egt_c: float = 700.0,
        altitude_ft: float = 0.0,
        critical_altitude_ft: float = 16000.0,
        fuel_temp_c: Optional[float] = None,
        fuel_cloud_point_c: Optional[float] = None,
        over_water: bool = False,
        engine_running: bool = True,
    ) -> ExposureRecord:
        r = self.record
        dt_h = max(0.0, dt_sec) / 3600.0
        if engine_running:
            r.total_hours += dt_h

        # Particulate, weighted so one hour in brownout is not one hour in clean air.
        r.dust_hours_weighted += dt_h * (dust_mg_m3 / self.BASELINE_DUST_MG_M3)
        if dust_mg_m3 >= 30.0:
            r.brownout_events += 1 if dt_h > 0 else 0

        # Cold
        if oat_c <= self.COLD_SOAK_THRESHOLD_C:
            r.cold_soak_hours += dt_h
        if (fuel_temp_c is not None and fuel_cloud_point_c is not None
                and fuel_temp_c <= fuel_cloud_point_c):
            r.hours_below_cloud_point += dt_h

        # Heat
        if cht_c >= self.CHT_CAUTION_C:
            r.hours_above_cht_caution += dt_h

        # Start / shutdown transitions
        if self._prev_running is not None and self._prev_running != engine_running:
            if engine_running:
                if oat_c <= 5.0:
                    r.cold_start_cycles += 1
            else:
                if egt_c >= self.HOT_SHUTDOWN_EGT_C:
                    r.hot_shutdown_events += 1
        self._prev_running = engine_running

        # Thermal cycles: count a cycle when CHT recovers after a large excursion.
        if self._prev_cht is not None:
            if self._cycle_low is None or cht_c < self._cycle_low:
                self._cycle_low = cht_c
            if self._cycle_low is not None and (cht_c - self._cycle_low) > 60.0:
                r.thermal_cycles += 1
                self._cycle_low = cht_c
        self._prev_cht = cht_c

        # Marine
        if over_water:
            r.salt_exposure_hours += dt_h

        # Altitude
        if altitude_ft > critical_altitude_ft:
            r.hours_above_critical_altitude += dt_h
        r.max_altitude_ft = max(r.max_altitude_ft, altitude_ft)
        return r

    # -- derived ------------------------------------------------------------

    def acceleration_factors(self) -> Dict[str, float]:
        """Multipliers on nominal wear rates implied by accumulated exposure.

        1.0 means "as the fleet baseline assumes". These are the numbers that
        let a maintenance interval be adjusted per tail rather than per fleet.
        """
        r = self.record
        hours = max(r.total_hours, 1e-6)

        dust_ratio = r.dust_hours_weighted / hours  # 1.0 at baseline dust
        # Filter loading really is ~linear in concentration: 40x the dust is 40x
        # the loading rate, i.e. 1/40th the filter life. That is a consumable
        # service interval, NOT engine wear, so it is reported separately and
        # deliberately excluded from `overall` below.
        filter_accel = max(1.0, dust_ratio)
        # Abrasive engine wear saturates: the filter still removes most of the
        # dust, so bore wear grows sub-linearly with concentration.
        bore_accel = max(1.0, 1.0 + 0.55 * math.log1p(max(0.0, dust_ratio - 1.0)))

        cold_fraction = r.cold_soak_hours / hours
        fuel_system_accel = 1.0 + 1.2 * cold_fraction
        start_system_accel = 1.0 + 0.02 * r.cold_start_cycles

        hot_fraction = r.hours_above_cht_caution / hours
        head_accel = 1.0 + 2.5 * hot_fraction
        turbo_accel = 1.0 + 0.05 * r.hot_shutdown_events + 0.6 * (
            r.hours_above_critical_altitude / hours)

        corrosion_accel = 1.0 + 0.8 * (r.salt_exposure_hours / hours)

        return {
            "air_filter": round(filter_accel, 3),
            "cylinder_bore": round(bore_accel, 3),
            "fuel_system": round(fuel_system_accel, 3),
            "starting_system": round(start_system_accel, 3),
            "cylinder_head": round(head_accel, 3),
            "turbocharger": round(turbo_accel, 3),
            "corrosion": round(corrosion_accel, 3),
            # `overall` covers engine wear only. air_filter is a consumable
            # interval and would otherwise dominate the average meaninglessly.
            "overall": round((bore_accel + head_accel + turbo_accel) / 3.0, 3),
        }

    def summary(self) -> dict:
        factors = self.acceleration_factors()
        overall = factors["overall"]
        if overall >= 1.6:
            severity = "SEVERE"
        elif overall >= 1.25:
            severity = "ELEVATED"
        elif overall >= 1.05:
            severity = "MILD"
        else:
            severity = "BASELINE"
        return {
            "exposure": self.record.as_dict(),
            "acceleration_factors": factors,
            "severity": severity,
            "interpretation": (
                f"Engine {self.record.engine_serial} has accumulated "
                f"{self.record.total_hours:.1f} h with an overall wear acceleration "
                f"of {overall:.2f}x fleet baseline ({severity})."
            ),
        }

    # -- persistence --------------------------------------------------------

    def save(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.record.as_dict(), indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path | str) -> "ExposureAccumulator":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(record=ExposureRecord(**data))
