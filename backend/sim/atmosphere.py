"""ISA atmosphere with ISA deviation and humidity (card M1-02, R 21.4, P Part 4 Step 1.3a). Valid below 11 km."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

# Physical constants (ICAO Doc 7488 standard atmosphere)
T0_K = 288.15                 # sea-level standard temperature
P0_PA = 101325.0              # sea-level standard pressure
LAPSE_K_PER_M = 0.0065        # troposphere temperature lapse rate
PRESSURE_K = 2.25577e-5       # (lapse / T0), 1/m, in p = p0 * (1 - k h)^n
PRESSURE_N = 5.25588          # g / (R_dry * lapse)
R_DRY = 287.05                # J/(kg K), dry air
R_VAPOUR = 461.495            # J/(kg K), water vapour
FT_TO_M = 0.3048
TROPOPAUSE_M = 11000.0


def saturation_pressure_pa(t_c: float) -> float:
    """Magnus form (Alduchov-Eskridge constants), over water."""
    return 610.94 * math.exp(17.625 * t_c / (t_c + 243.04))


@dataclass(frozen=True)
class Atmosphere:
    altitude_m: float
    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    vapour_pressure_pa: float

    @classmethod
    def at(cls, altitude_ft: float, isa_dev_c: float = 0.0, humidity_pct: float = 0.0,
           oat_c: Optional[float] = None) -> "Atmosphere":
        h = altitude_ft * FT_TO_M
        if not -1000.0 <= h <= TROPOPAUSE_M:
            raise ValueError(f"altitude {altitude_ft} ft is outside the troposphere model (-1000 m .. 11 km)")
        t_isa = T0_K - LAPSE_K_PER_M * h
        t = oat_c + 273.15 if oat_c is not None else t_isa + isa_dev_c
        p = P0_PA * (1.0 - PRESSURE_K * h) ** PRESSURE_N
        rh = min(max(humidity_pct, 0.0), 100.0) / 100.0
        p_v = min(rh * saturation_pressure_pa(t - 273.15), p)
        rho = (p - p_v) / (R_DRY * t) + p_v / (R_VAPOUR * t)
        return cls(altitude_m=h, temperature_k=t, pressure_pa=p, density_kg_m3=rho, vapour_pressure_pa=p_v)
