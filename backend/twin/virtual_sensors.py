"""Virtual sensors (card M1-17, idea text section 15, I-01): quantities no sensor measures, estimated from the
measured Frame with the M1 model equations and calibrated constants. They never read plant truth (T-DYN-4) and
every input that is missing makes the output None (NO DATA), never a substituted number. Quality: VIRTUAL.

  Peak cylinder pressure (bar):
    p_comp = MAP * CR^n                                        (polytropic compression of the measured charge)
    dp_cv  = (gamma - 1) * m_burnt * LHV / V_c,  V_c = V_d / (CR - 1)
    m_burnt per cycle = min(fuel, air / AFR_stoich) from the measured fuel flow and speed-density air at MAP
    P_max  = p_comp + f_peak * dp_cv
  Turbine inlet temperature (C), turbo engines only:
    TIT = EGT_mean - f_manifold * (EGT_mean - T_amb)     (measured port EGTs, manifold heat loss)
    A turbo shaft-power balance cannot give TIT here: the wastegate bypasses an unknown share of the exhaust, and
    assuming full turbine flow put TIT 400-500 C below the measured port EGT (checked 20 Nov 2026).
  Minimum oil-film thickness (um) - Ocvirk short journal bearing:
    W = mu U L^3 / (4 c^2) * eps / (1 - eps^2)^2 * sqrt(pi^2 (1 - eps^2) + 16 eps^2),   h_min = c (1 - eps)
    W = peak gas force on one bearing, U = journal surface speed, mu = Vogel viscosity at the measured oil T
  Indicated power (kW): m_burnt * LHV * eta_i (eta_i CALIBRATED in backend/sim/engine.py).
Bearing geometry is ASSUMED (configs/physics virtual_sensors) and labelled as such.
"""
from __future__ import annotations

import math
from typing import Dict, Optional

from backend.core.frame import Frame
from backend.physics.engine_config import EngineConfig
from backend.sim.atmosphere import R_DRY
from backend.sim.engine import MeanValueEngine
from backend.sim.params import physics_values
from backend.sim.thermal import oil_viscosity_mpas

KELVIN = 273.15
PA_PER_BAR = 1e5
PA_PER_KPA = 1e3
S_PER_H = 3600.0


class VirtualSensorSynthesizer:
    def __init__(self, cfg: EngineConfig) -> None:
        self.cfg = cfg
        self.ph = physics_values(cfg.engine_id, "virtual_sensors")
        self.oil = physics_values(cfg.engine_id, "oil")
        model = MeanValueEngine(cfg)                     # calibrated constants only (eta_i, VE, fuel properties)
        self.eta_i = model.combustion.eta_i
        self.lhv = model.combustion.lhv_j_kg
        self.afr = model.combustion.stoich_afr
        self.eta_v = model.induction.eta_v
        self.eta_c = model.turbo.eta_c if model.turbo is not None else None
        self.n = cfg.cylinder_count
        self.cr = cfg.layout.compression_ratio
        self.vd_cyl = cfg.layout.displacement_cc * 1e-6 / self.n
        self.v_c = self.vd_cyl / (self.cr - 1.0)
        self.piston_area = math.pi * (cfg.layout.bore_mm / 2000.0) ** 2

    def synthesize(self, frame: Frame) -> Dict[str, Optional[float]]:
        out: Dict[str, Optional[float]] = {"P_max_bar": None, "TIT_degC": None, "h_min_um": None, "P_ind_kw": None}
        rpm, map_kpa, fuel = frame.rpm, frame.map_kpa, frame.fuel_flow
        if rpm is None or map_kpa is None or fuel is None or frame.oat is None or rpm <= 0:
            return out
        cycles = rpm / 120.0 * self.n                                         # cycles per second, all cylinders
        t_in = frame.oat + KELVIN
        map_pa = map_kpa * PA_PER_KPA
        air_cyc = self.eta_v * map_pa / (R_DRY * t_in) * self.vd_cyl          # speed-density air per cycle
        burnt = min(fuel / S_PER_H / cycles, air_cyc / self.afr)
        out["P_ind_kw"] = burnt * self.lhv * self.eta_i * cycles / 1000.0
        ph = self.ph
        p_comp = map_pa * self.cr ** ph["compression_polytropic_n"]
        dp = (ph["combustion_gamma"] - 1.0) * burnt * self.lhv / self.v_c
        p_max = p_comp + ph["peak_pressure_fraction"] * dp
        out["P_max_bar"] = p_max / PA_PER_BAR
        out["TIT_degC"] = self._tit(frame)
        out["h_min_um"] = self._h_min(frame, p_max, rpm)
        return out

    def _tit(self, frame: Frame) -> Optional[float]:
        if self.eta_c is None or not frame.egt or any(v is None for v in frame.egt) or frame.oat is None:
            return None                                                       # no turbine, or a port EGT missing
        egt = sum(frame.egt) / len(frame.egt)
        return egt - self.ph["manifold_heat_loss_fraction"] * (egt - frame.oat)

    def _h_min(self, frame: Frame, p_max_pa: float, rpm: float) -> Optional[float]:
        if frame.oil_t is None:
            return None
        ph = self.ph
        mu = oil_viscosity_mpas(frame.oil_t, self.oil["vogel_a_mpas"], self.oil["vogel_b"], self.oil["vogel_c"]) / 1e3
        d = ph["bearing_diameter_mm"] / 1e3
        length = ph["bearing_length_mm"] / 1e3
        c = ph["bearing_radial_clearance_um"] / 1e6
        k = mu * (math.pi * d * rpm / 60.0) * length ** 3 / (4.0 * c * c)
        w = ph["bearing_load_share"] * p_max_pa * self.piston_area

        def load(eps: float) -> float:
            return k * eps / (1 - eps * eps) ** 2 * math.sqrt(math.pi ** 2 * (1 - eps * eps) + 16 * eps * eps)

        lo, hi = 0.0, 0.999
        for _ in range(60):                                                   # load rises monotonically with eps
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if load(mid) < w else (lo, mid)
        return c * (1.0 - 0.5 * (lo + hi)) * 1e6
