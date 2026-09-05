"""
Rotax 912 iS Prognostics & Remaining Useful Life (RUL) Estimator
DRDO / iDEX Problem Statement ID: 26054

Tracks component degradation rates and provides pre-flight Mission Go/No-Go validation.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
import math
from backend.physics.thermo_model import EnginePhysicalState, ResidualVector


@dataclass
class MissionGoNoGoAdvisory:
    """Pre-flight / In-flight decision advisory based on RUL prognostics."""
    status: str                    # "GO", "CAUTION", "NO_GO"
    planned_sortie_hours: float
    estimated_rul_hours: float
    margin_hours: float
    limiting_subsystem: str
    advisory_text: str
    timestamp_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RULEstimator:
    """
    Prognostic degradation model tracking wear accumulation on:
    - Cylinder head thermal fatigue
    - Dry-sump oil pump & lubrication film
    - Reduction gearbox dog-clutch tooth fatigue
    - Ignition lead insulation breakdown
    """

    def __init__(self, base_component_lifetimes_hrs: Optional[Dict[str, float]] = None):
        self.component_rul: Dict[str, float] = base_component_lifetimes_hrs or {
            "Cylinder_Head_Assembly": 450.0,
            "Fuel_Injection_Rail": 600.0,
            "Ignition_Harness_Coils": 400.0,
            "Lubrication_Oil_Circuit": 350.0,
            "Reduction_Gearbox_Clutch": 500.0,
            "Alternator_Electrical_Bus": 800.0
        }
        self.health_history: List[float] = []

    def update_degradation(
        self,
        actual: EnginePhysicalState,
        residuals: ResidualVector,
        dt_sec: float = 0.05
    ) -> Dict[str, float]:
        """
        Updates cumulative component wear based on instantaneous thermal and mechanical stress.
        """
        hours_elapsed = dt_sec / 3600.0

        # 1. Thermal stress acceleration factor (Arrhenius exponential scaling above 115°C)
        max_cht = max(actual.CHT_1, actual.CHT_2, actual.CHT_3, actual.CHT_4)
        if max_cht > 115.0:
            thermal_stress_multiplier = math.exp((max_cht - 115.0) / 6.0)
        else:
            thermal_stress_multiplier = 1.0
        self.component_rul["Cylinder_Head_Assembly"] = max(
            0.5, self.component_rul["Cylinder_Head_Assembly"] - (hours_elapsed * thermal_stress_multiplier)
        )

        # 2. Lubrication stress factor (Low oil pressure accelerates bearing wear exponentially)
        if actual.OIL_PRESS < 2.5:
            oil_stress_multiplier = 1.0 + 15.0 * ((2.5 - actual.OIL_PRESS) ** 2.0)
        else:
            oil_stress_multiplier = 1.0
        self.component_rul["Lubrication_Oil_Circuit"] = max(
            0.2, self.component_rul["Lubrication_Oil_Circuit"] - (hours_elapsed * oil_stress_multiplier)
        )

        # 3. Gearbox mechanical fatigue (Vibration cubic power law)
        if actual.VIB_GEARBOX_RMS > 1.2:
            vib_stress_multiplier = (actual.VIB_GEARBOX_RMS / 0.8) ** 3.0
        else:
            vib_stress_multiplier = 1.0
        self.component_rul["Reduction_Gearbox_Clutch"] = max(
            1.0, self.component_rul["Reduction_Gearbox_Clutch"] - (hours_elapsed * vib_stress_multiplier)
        )

        # 4. If active fault is present, accelerate specific subsystem degradation
        if actual.FAULT_ID == 1:
            self.component_rul["Cylinder_Head_Assembly"] = max(1.0, self.component_rul["Cylinder_Head_Assembly"] - hours_elapsed * 50.0)
        elif actual.FAULT_ID == 4:
            self.component_rul["Lubrication_Oil_Circuit"] = max(0.5, self.component_rul["Lubrication_Oil_Circuit"] - hours_elapsed * 80.0)
        elif actual.FAULT_ID == 5:
            self.component_rul["Reduction_Gearbox_Clutch"] = max(1.0, self.component_rul["Reduction_Gearbox_Clutch"] - hours_elapsed * 40.0)

        return self.component_rul

    def get_overall_engine_rul(self) -> float:
        """Returns minimum remaining useful life across all critical engine subsystems."""
        return min(self.component_rul.values())

    def evaluate_mission_feasibility(
        self,
        planned_sortie_hours: float,
        safety_margin_hours: float = 2.0
    ) -> MissionGoNoGoAdvisory:
        """
        Pillar 1: Pre-flight Mission Go / No-Go Validation.
        Evaluates if engine has sufficient RUL to complete the planned sortie safely.
        """
        limiting_subsystem = min(self.component_rul, key=lambda k: self.component_rul[k])
        estimated_rul = self.component_rul[limiting_subsystem]
        margin = estimated_rul - planned_sortie_hours

        if margin < 0.0:
            status = "NO_GO"
            advisory = (
                f"🛑 MISSION NO-GO: Planned sortie ({planned_sortie_hours}h) exceeds estimated RUL ({estimated_rul:.1f}h) "
                f"on {limiting_subsystem.replace('_', ' ')}. Pre-emptive overhaul required."
            )
        elif margin < safety_margin_hours:
            status = "CAUTION"
            advisory = (
                f"⚠ CAUTION: Planned sortie ({planned_sortie_hours}h) has narrow safety margin ({margin:.1f}h) "
                f"on {limiting_subsystem.replace('_', ' ')}. Post-flight inspection mandatory."
            )
        else:
            status = "GO"
            advisory = (
                f"✅ MISSION GO: Propulsion system certified for {planned_sortie_hours}h sortie. "
                f"Min subsystem RUL: {estimated_rul:.1f}h ({limiting_subsystem.replace('_', ' ')})."
            )

        return MissionGoNoGoAdvisory(
            status=status,
            planned_sortie_hours=planned_sortie_hours,
            estimated_rul_hours=round(estimated_rul, 1),
            margin_hours=round(margin, 1),
            limiting_subsystem=limiting_subsystem,
            advisory_text=advisory
        )
