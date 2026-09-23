"""
Oil system health: wear-metal spectrum, debris, blow-by — F39.

The problem statement names "Lubrication issues" as a fault target. Every
implementation in this field, ours included, models oil *pressure*. That is the
symptom of a failure already in progress.

The actual technique, used by the US military on aircraft engines since the
early 1960s, is SOAP — Spectrometric Oil Analysis Program — which measures wear
metals in the lubricant to determine wear quantity, rate **and source**. Modern
practice adds online debris sensors (inductive, capacitive, optical) because
periodic sampling cannot catch abrupt wear events.

The reason this is a diagnostic rather than a scalar is that the element
identifies the wearing component:

    Fe  -> rings, liner, camshaft, gears
    Al  -> pistons
    Cu  -> bearings, bushings, oil cooler
    Pb  -> bearing overlay
    Cr  -> rings, plated surfaces
    Si  -> INGESTED DUST — confirms an air filter breach (see induction.py)
    Ag  -> specific bearing types
    Sn  -> bearing overlay

That silicon row is what closes the dust chain: a rising Si trend distinguishes
"the engine is wearing because it ate desert dust" from "the engine is wearing
because a bearing is failing". No competitor can make that distinction, because
none of them model the oil as anything but a pressure.

Oil is also the only channel that gives a **direct measurement of material
loss** rather than an inference from temperature. Concentrations are tracked in
ppm against an oil charge that is diluted at each oil change, which is why a
change resets concentration but not cumulative wear.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

__all__ = [
    "WEAR_METAL_SOURCES",
    "WearMetalLimits",
    "OilState",
    "OilSystemModel",
]

WEAR_METAL_SOURCES: Dict[str, str] = {
    "Fe": "rings / liner / camshaft / gears",
    "Al": "pistons",
    "Cu": "bearings / bushings / oil cooler",
    "Pb": "bearing overlay",
    "Cr": "rings / plated surfaces",
    "Si": "ingested dust — air filter breach",
    "Ag": "bearings (silver-plated)",
    "Sn": "bearing overlay",
}


@dataclass(frozen=True)
class WearMetalLimits:
    """Caution/warning concentrations in ppm.

    Piston-aero SOAP limits are engine-specific and are normally set from fleet
    statistics rather than from first principles; these are representative
    starting values and are labelled as such. The correct long-term source is
    the operator's own fleet trend, which is exactly what the knowledge graph
    already accumulates.
    """

    caution_ppm: Dict[str, float] = field(default_factory=lambda: {
        "Fe": 40.0, "Al": 15.0, "Cu": 20.0, "Pb": 25.0,
        "Cr": 8.0, "Si": 15.0, "Ag": 3.0, "Sn": 10.0,
    })
    warning_ppm: Dict[str, float] = field(default_factory=lambda: {
        "Fe": 75.0, "Al": 30.0, "Cu": 40.0, "Pb": 50.0,
        "Cr": 18.0, "Si": 30.0, "Ag": 8.0, "Sn": 22.0,
    })
    source: str = "representative fleet-statistical values — replace with operator data"


@dataclass
class OilState:
    hours_on_oil: float = 0.0
    oil_charge_l: float = 3.0
    concentrations_ppm: Dict[str, float] = field(default_factory=dict)
    rates_ppm_per_hour: Dict[str, float] = field(default_factory=dict)
    cumulative_wear_mg: Dict[str, float] = field(default_factory=dict)
    debris_count: int = 0  # online debris sensor: particles above threshold
    large_debris_count: int = 0  # > ~200 micron; indicates spalling, not wear
    oil_consumption_l_per_hour: float = 0.0
    viscosity_ratio: float = 1.0  # vs fresh oil; <1 = sheared/fuel-diluted
    oxidation_index: float = 0.0  # 0 = fresh
    verdict: str = "NORMAL"
    flagged: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "OIL_HOURS": round(self.hours_on_oil, 2),
            **{f"OIL_{k}_PPM": round(v, 3) for k, v in sorted(self.concentrations_ppm.items())},
            **{f"OIL_{k}_RATE_PPM_H": round(v, 4) for k, v in sorted(self.rates_ppm_per_hour.items())},
            "OIL_DEBRIS_COUNT": self.debris_count,
            "OIL_LARGE_DEBRIS": self.large_debris_count,
            "OIL_CONSUMPTION_L_H": round(self.oil_consumption_l_per_hour, 4),
            "OIL_VISCOSITY_RATIO": round(self.viscosity_ratio, 4),
            "OIL_OXIDATION_INDEX": round(self.oxidation_index, 4),
            "OIL_VERDICT": self.verdict,
            "OIL_FLAGGED_ELEMENTS": list(self.flagged),
        }


class OilSystemModel:
    """Wear-metal generation, debris, dilution and oil condition.

    Wear rates are driven by the same physical state the rest of the twin
    already tracks — bore wear from ingested silica, bearing condition, oil
    temperature — so the oil spectrum is a *consequence* of modelled damage
    rather than an independently invented signal.
    """

    # Baseline healthy generation, mg per hour, at rated load.
    _BASE_MG_PER_HOUR = {
        "Fe": 1.10, "Al": 0.28, "Cu": 0.22, "Pb": 0.18,
        "Cr": 0.09, "Si": 0.05, "Ag": 0.02, "Sn": 0.06,
    }

    def __init__(
        self,
        oil_charge_l: float = 3.0,
        limits: Optional[WearMetalLimits] = None,
        oil_density_kg_l: float = 0.86,
    ) -> None:
        self.limits = limits or WearMetalLimits()
        self.oil_density_kg_l = oil_density_kg_l
        self.state = OilState(oil_charge_l=oil_charge_l)
        self.state.concentrations_ppm = {k: 0.0 for k in self._BASE_MG_PER_HOUR}
        self.state.cumulative_wear_mg = {k: 0.0 for k in self._BASE_MG_PER_HOUR}
        self.state.rates_ppm_per_hour = {k: 0.0 for k in self._BASE_MG_PER_HOUR}
        self._prev_conc: Dict[str, float] = dict(self.state.concentrations_ppm)

    def update(
        self,
        dt_hours: float,
        load_fraction: float = 1.0,
        oil_temp_c: float = 95.0,
        bore_wear_index: float = 0.0,
        silica_ingress_g: float = 0.0,
        bearing_wear: float = 0.0,
        fuel_dilution_fraction: float = 0.0,
    ) -> OilState:
        s = self.state
        if dt_hours <= 0:
            return s
        s.hours_on_oil += dt_hours
        load = max(0.05, load_fraction)

        # Arrhenius-style acceleration of wear and oxidation with oil temperature.
        thermal = math.exp((oil_temp_c - 95.0) / 28.0)

        for element, base in self._BASE_MG_PER_HOUR.items():
            rate = base * load * thermal
            if element in ("Fe", "Cr"):
                rate *= 1.0 + 9.0 * bore_wear_index  # ring/liner abrasion
            if element in ("Cu", "Pb", "Ag", "Sn"):
                rate *= 1.0 + 12.0 * bearing_wear
            if element == "Al":
                rate *= 1.0 + 5.0 * bore_wear_index
            if element == "Si":
                # Silicon is ingested, not generated: it tracks dust directly.
                rate = base * load + silica_ingress_g * 1000.0 * 0.06
            mg = rate * dt_hours
            s.cumulative_wear_mg[element] += mg

            oil_mass_kg = max(s.oil_charge_l * self.oil_density_kg_l, 1e-6)
            delta_ppm = mg / (oil_mass_kg * 1000.0) * 1000.0
            s.concentrations_ppm[element] += delta_ppm
            s.rates_ppm_per_hour[element] = (
                (s.concentrations_ppm[element] - self._prev_conc[element]) / dt_hours
            )
        self._prev_conc = dict(s.concentrations_ppm)

        # Online debris sensor. Bearing spalling produces large particles;
        # abrasive wear produces many small ones. The distinction matters —
        # one is a maintenance advisory, the other is a flight safety issue.
        s.debris_count += int(max(0.0, 40.0 * bore_wear_index * load * dt_hours))
        s.large_debris_count += int(max(0.0, 12.0 * (bearing_wear ** 2) * load * dt_hours))

        # Condition: oxidation with temperature-time, viscosity loss from
        # shear and fuel dilution.
        s.oxidation_index = min(1.0, s.oxidation_index + 0.004 * thermal * dt_hours)
        s.viscosity_ratio = max(0.4, 1.0 - 0.25 * s.oxidation_index - 1.6 * fuel_dilution_fraction)

        # Consumption rises with bore wear (blow-by past the rings).
        s.oil_consumption_l_per_hour = 0.02 * load * (1.0 + 6.0 * bore_wear_index)

        s.flagged, s.verdict = self._assess(s)
        return s

    def _assess(self, s: OilState) -> tuple[List[str], str]:
        flagged: List[str] = []
        verdict = "NORMAL"
        for element, ppm in s.concentrations_ppm.items():
            warn = self.limits.warning_ppm.get(element)
            caut = self.limits.caution_ppm.get(element)
            if warn is not None and ppm >= warn:
                flagged.append(f"{element}:WARNING")
                verdict = "WARNING"
            elif caut is not None and ppm >= caut:
                flagged.append(f"{element}:CAUTION")
                if verdict == "NORMAL":
                    verdict = "CAUTION"
        if s.large_debris_count > 0 and verdict != "WARNING":
            verdict = "CAUTION"
        if s.large_debris_count > 20:
            verdict = "WARNING"
        return flagged, verdict

    def diagnose_source(self) -> List[dict]:
        """Attribute elevated elements to components — the SOAP payoff.

        Returns entries ordered by severity so the maintainer sees the dominant
        wear source first, with the silicon case called out explicitly because
        it changes the corrective action from "inspect the engine" to "inspect
        the air filter".
        """
        out: List[dict] = []
        for element, ppm in sorted(self.state.concentrations_ppm.items(),
                                   key=lambda kv: -kv[1]):
            caut = self.limits.caution_ppm.get(element, float("inf"))
            if ppm < caut * 0.6:
                continue
            severity = ppm / caut if caut else 0.0
            entry = {
                "element": element,
                "ppm": round(ppm, 2),
                "caution_ppm": caut,
                "severity_ratio": round(severity, 3),
                "rate_ppm_per_hour": round(self.state.rates_ppm_per_hour.get(element, 0.0), 4),
                "likely_source": WEAR_METAL_SOURCES.get(element, "unknown"),
            }
            if element == "Si":
                entry["action"] = (
                    "Inspect air filter and induction sealing — silicon indicates "
                    "ingested dust, not internal component wear"
                )
            out.append(entry)
        return out

    def change_oil(self, new_charge_l: Optional[float] = None) -> None:
        """Oil change: concentrations reset, cumulative wear does not."""
        s = self.state
        if new_charge_l is not None:
            s.oil_charge_l = new_charge_l
        s.hours_on_oil = 0.0
        s.concentrations_ppm = {k: 0.0 for k in self._BASE_MG_PER_HOUR}
        s.rates_ppm_per_hour = {k: 0.0 for k in self._BASE_MG_PER_HOUR}
        s.debris_count = 0
        s.large_debris_count = 0
        s.oxidation_index = 0.0
        s.viscosity_ratio = 1.0
        s.verdict = "NORMAL"
        s.flagged = []
        self._prev_conc = dict(s.concentrations_ppm)
