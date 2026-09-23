"""
FMECA — failure mode, effects and criticality analysis — F33.

Our eight fault modes were *chosen*. They should be *derived*. MIL-STD-1629A
(vendored at docs/reference/MIL-STD-1629A.pdf) establishes the procedure for
systematically evaluating the impact of each failure on mission success, safety
and maintenance — and "mission success" is the phrase in the problem statement's
own title.

The output that matters is not the table, it is the **traceability matrix**:

    failure mode -> physical signature -> sensor channel -> detection method
                 -> severity/occurrence/detection -> criticality -> advisory

That chain answers the question no team in this field can currently answer:
*"why these faults, and what about the ones you left out?"* A fault mode with no
row is an admission; a fault mode with a row but no detecting channel is a
**detectability gap**, which is a finding in its own right and is reported as one.

Criticality here follows the RPN convention (severity x occurrence x detection)
because it is the form maintainers recognise, with MIL-STD-1629A severity
classes retained alongside it since RPN alone hides the difference between a
frequent nuisance and a rare catastrophe.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

__all__ = ["SeverityClass", "FailureMode", "FMECA", "build_default_fmeca"]


class SeverityClass:
    """MIL-STD-1629A severity classification."""

    CATASTROPHIC = "I_CATASTROPHIC"  # loss of aircraft
    CRITICAL = "II_CRITICAL"  # mission loss, possible aircraft damage
    MARGINAL = "III_MARGINAL"  # mission degradation
    MINOR = "IV_MINOR"  # maintenance burden only

    RANK = {CATASTROPHIC: 10, CRITICAL: 7, MARGINAL: 4, MINOR: 2}


@dataclass
class FailureMode:
    """One row of the FMECA."""

    mode_id: str
    item: str  # the component
    failure_mode: str  # how it fails
    cause: str  # why
    local_effect: str
    mission_effect: str
    severity_class: str

    # Physical signature and how we would see it
    signatures: List[str] = field(default_factory=list)
    channels: List[str] = field(default_factory=list)
    detection_method: str = ""

    # Criticality inputs, 1-10 each
    occurrence: int = 3  # 1 = remote, 10 = frequent
    detection_difficulty: int = 5  # 1 = certain to detect, 10 = undetectable

    compensating_provision: str = ""
    engine_classes: List[str] = field(default_factory=lambda: ["SI", "CI"])
    implemented_by: str = ""  # module that models or detects this

    @property
    def severity_rank(self) -> int:
        return SeverityClass.RANK.get(self.severity_class, 5)

    @property
    def rpn(self) -> int:
        """Risk priority number. High = fix first."""
        return self.severity_rank * self.occurrence * self.detection_difficulty

    @property
    def criticality(self) -> float:
        """Severity-weighted occurrence, independent of our ability to detect.

        Kept separate from RPN deliberately: improving detection lowers RPN but
        does not make the failure less likely or less severe, and conflating the
        two is how a hazard gets managed by instrumentation rather than by
        design.
        """
        return self.severity_rank * self.occurrence / 10.0

    @property
    def is_detectability_gap(self) -> bool:
        """True when nothing in the system can currently see this mode."""
        return not self.channels or not self.detection_method

    def as_dict(self) -> dict:
        d = asdict(self)
        d.update({
            "severity_rank": self.severity_rank,
            "rpn": self.rpn,
            "criticality": round(self.criticality, 2),
            "detectability_gap": self.is_detectability_gap,
        })
        return d


class FMECA:
    """The analysis, plus the queries that make it useful."""

    def __init__(self, modes: Optional[List[FailureMode]] = None,
                 system: str = "MALE UAV piston propulsion") -> None:
        self.system = system
        self.modes: List[FailureMode] = modes or []

    def add(self, mode: FailureMode) -> None:
        self.modes.append(mode)

    def for_engine_class(self, engine_class: str) -> List[FailureMode]:
        """Modes applicable to SI or CI. A diesel has no spark misfire."""
        return [m for m in self.modes if engine_class.upper() in
                [c.upper() for c in m.engine_classes]]

    def ranked_by_rpn(self, top: Optional[int] = None) -> List[FailureMode]:
        out = sorted(self.modes, key=lambda m: -m.rpn)
        return out[:top] if top else out

    def detectability_gaps(self) -> List[FailureMode]:
        """Modes we cannot currently see. Each one is an honest finding."""
        return [m for m in self.modes if m.is_detectability_gap]

    def channel_coverage(self) -> Dict[str, List[str]]:
        """Which sensor channel covers which failure modes.

        Read the other way, a channel appearing against many high-RPN modes is
        a single point of diagnostic failure — losing it blinds the system to
        several things at once, which is what F35 quantifies.
        """
        cov: Dict[str, List[str]] = {}
        for m in self.modes:
            for ch in m.channels:
                cov.setdefault(ch, []).append(m.mode_id)
        return dict(sorted(cov.items(), key=lambda kv: -len(kv[1])))

    def traceability_matrix(self) -> List[dict]:
        """The deliverable: mode -> signature -> channel -> method -> advisory."""
        rows = []
        for m in sorted(self.modes, key=lambda x: -x.rpn):
            rows.append({
                "mode_id": m.mode_id,
                "item": m.item,
                "failure_mode": m.failure_mode,
                "severity": m.severity_class,
                "rpn": m.rpn,
                "criticality": round(m.criticality, 2),
                "signature": "; ".join(m.signatures) or "NONE IDENTIFIED",
                "channels": ", ".join(m.channels) or "NONE",
                "detection": m.detection_method or "NOT DETECTED",
                "compensating_provision": m.compensating_provision,
                "implemented_by": m.implemented_by or "NOT IMPLEMENTED",
                "detectability_gap": m.is_detectability_gap,
            })
        return rows

    def summary(self) -> dict:
        gaps = self.detectability_gaps()
        by_sev: Dict[str, int] = {}
        for m in self.modes:
            by_sev[m.severity_class] = by_sev.get(m.severity_class, 0) + 1
        implemented = [m for m in self.modes if m.implemented_by]
        return {
            "system": self.system,
            "total_modes": len(self.modes),
            "by_severity": dict(sorted(by_sev.items())),
            "detectability_gaps": len(gaps),
            "gap_ids": [m.mode_id for m in gaps],
            "implemented": len(implemented),
            "implementation_coverage": (round(len(implemented) / len(self.modes), 3)
                                        if self.modes else 0.0),
            "highest_rpn": [(m.mode_id, m.rpn) for m in self.ranked_by_rpn(5)],
            "si_modes": len(self.for_engine_class("SI")),
            "ci_modes": len(self.for_engine_class("CI")),
        }

    def to_markdown(self) -> str:
        """Render the traceability matrix for the documentation set."""
        lines = [
            f"# FMECA — {self.system}",
            "",
            "Derived per MIL-STD-1629A. RPN = severity x occurrence x detection",
            "difficulty; higher is more urgent. A row marked GAP has no channel or",
            "no detection method and is an open finding.",
            "",
            "| ID | Item | Failure mode | Sev | RPN | Signature | Channels | Detection | Implemented by |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for r in self.traceability_matrix():
            flag = " **GAP**" if r["detectability_gap"] else ""
            lines.append(
                f"| {r['mode_id']} | {r['item']} | {r['failure_mode']} | "
                f"{r['severity'].split('_')[0]} | {r['rpn']} | {r['signature']} | "
                f"{r['channels']} | {r['detection']}{flag} | {r['implemented_by']} |"
            )
        s = self.summary()
        lines += [
            "",
            f"**{s['total_modes']} modes** · {s['detectability_gaps']} detectability "
            f"gaps · {s['implementation_coverage']:.0%} modelled or detected in code.",
        ]
        return "\n".join(lines)

    def save_json(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"summary": self.summary(), "modes": [m.as_dict() for m in self.modes]}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path


def build_default_fmeca() -> FMECA:
    """FMECA for a turbocharged piston UAV powerplant.

    Severity and occurrence are engineering judgement informed by the failure
    literature reviewed in docs/audit/07; they are not from fleet data and
    should be revised when it exists. The value delivered now is the *structure*
    — every fault the system claims to detect traces to a row, and every row
    without a detecting channel is visible as a gap.
    """
    f = FMECA()

    # --- Combustion / fuel injection ---
    f.add(FailureMode(
        "FM-01", "Cylinder / ignition", "Misfire (SI)", "Plug fouling, coil failure, lean limit",
        "Loss of combustion on one cylinder", "Power loss, vibration, possible abort",
        SeverityClass.CRITICAL,
        signatures=["Torque deficit at that cylinder's firing angle",
                    "Raised cycle-to-cycle variation", "EGT drop on affected cylinder"],
        channels=["CRANK_OMEGA", "EGT_n", "VIB"], detection_method="Per-cylinder omega(theta) torque deficit",
        occurrence=5, detection_difficulty=3,
        compensating_provision="FADEC dual ignition lanes",
        engine_classes=["SI"], implemented_by="planned F02 (crank-angle chain)"))

    f.add(FailureMode(
        "FM-02", "Injector", "Nozzle coking / IDID", "Deposit formation from thermal cycling of fuel",
        "Reduced and mistimed delivery, poor atomisation",
        "Rough running, hard start, progressive power loss", SeverityClass.CRITICAL,
        signatures=["Asymmetric per-cylinder torque deficit", "Retarded effective injection",
                    "EGT imbalance"],
        channels=["CRANK_OMEGA", "EGT_n", "INJ_n_DELIVERY"],
        detection_method="Injector bank imbalance metrics (asymmetric)",
        occurrence=6, detection_difficulty=4,
        compensating_provision="Fuel additive, injector service interval",
        engine_classes=["CI"], implemented_by="backend/physics/injector_faults.py"))

    f.add(FailureMode(
        "FM-03", "Injector", "Needle stick", "Deposits or contamination binding the needle",
        "Partial or total loss of delivery on one cylinder",
        "Severe power loss; multiple sticks can stop the engine", SeverityClass.CATASTROPHIC,
        signatures=["Single-cylinder delivery collapse", "Large asymmetric torque deficit"],
        channels=["CRANK_OMEGA", "EGT_n"], detection_method="Injector bank imbalance metrics",
        occurrence=3, detection_difficulty=3,
        compensating_provision="Fuel filtration",
        engine_classes=["CI"], implemented_by="backend/physics/injector_faults.py"))

    f.add(FailureMode(
        "FM-04", "High-pressure pump / rail", "Rail pressure decay", "Pump wear, leak-off",
        "Symmetric loss of delivery on all cylinders", "Progressive power loss",
        SeverityClass.CRITICAL,
        signatures=["Symmetric torque deficit across all cylinders", "Rail pressure below command"],
        channels=["RAIL_PRESSURE_BAR", "CRANK_OMEGA"],
        detection_method="Symmetric deficit with low rail pressure",
        occurrence=4, detection_difficulty=2,
        engine_classes=["CI"], implemented_by="backend/physics/injector_faults.py"))

    f.add(FailureMode(
        "FM-05", "Combustion", "Combustion instability", "Lean operation, EGR, poor mixing",
        "Cycle-to-cycle variability", "Rough running, accelerated wear",
        SeverityClass.MARGINAL,
        signatures=["Rising COV of per-cylinder work", "Vibration at sub-harmonic orders"],
        channels=["CRANK_OMEGA", "VIB"], detection_method="COV of IMEP proxy",
        occurrence=4, detection_difficulty=6,
        implemented_by="planned F03"))

    # --- Cooling / thermal ---
    f.add(FailureMode(
        "FM-06", "Cooling system", "Cooling degradation", "Baffle damage, coolant loss, radiator fouling",
        "Reduced heat rejection", "CHT rise, detonation margin loss, possible seizure",
        SeverityClass.CRITICAL,
        signatures=["CHT above physics expectation at same power/altitude",
                    "Coolant temperature rise"],
        channels=["CHT_n", "COOLANT_TEMP", "OAT_C"],
        detection_method="Thermodynamic residual on CHT",
        occurrence=5, detection_difficulty=3,
        implemented_by="backend/physics/thermo_model.py"))

    f.add(FailureMode(
        "FM-07", "Cylinder head", "Thermal fatigue cracking", "Repeated thermal cycling, shock cooling",
        "Head crack, compression loss", "Power loss, possible in-flight shutdown",
        SeverityClass.CATASTROPHIC,
        signatures=["Accumulated LCF damage fraction", "Compression loss", "Blow-by rise"],
        channels=["CHT_n", "BLOWBY"],
        detection_method="Rainflow + Miner damage accumulation",
        occurrence=2, detection_difficulty=7,
        compensating_provision="Descent CHT rate limits",
        implemented_by="backend/evaluation/damage_accumulation.py"))

    # --- Induction / environment ---
    f.add(FailureMode(
        "FM-08", "Air filter", "Restriction from dust loading", "Operation in high-particulate environment",
        "Reduced airflow", "Power loss, raised BSFC", SeverityClass.MARGINAL,
        signatures=["MAP deficit at constant throttle and altitude", "Filter dP rise"],
        channels=["MAP", "AIR_FILTER_DP_KPA", "TPS", "ALTITUDE_FT"],
        detection_method="MAP versus physics expectation",
        occurrence=7, detection_difficulty=3,
        compensating_provision="Bypass door; service interval",
        implemented_by="backend/physics/induction.py"))

    f.add(FailureMode(
        "FM-09", "Cylinder bore / rings", "Abrasive wear from ingested silica",
        "Filter breach or bypass in dusty operation",
        "Bore polishing, ring wear", "Compression loss, oil consumption, power loss",
        SeverityClass.CRITICAL,
        signatures=["Rising Si in oil", "Blow-by rise", "Oil consumption rise",
                    "Compression loss"],
        channels=["OIL_Si_PPM", "BLOWBY", "OIL_CONSUMPTION_L_H"],
        detection_method="Wear-metal spectrum with Si attribution",
        occurrence=4, detection_difficulty=4,
        implemented_by="backend/physics/oil_system.py + induction.py"))

    # --- Lubrication ---
    f.add(FailureMode(
        "FM-10", "Oil pump / gallery", "Oil pressure loss", "Pump wear, blockage, leak",
        "Loss of lubrication", "Bearing failure, engine seizure", SeverityClass.CATASTROPHIC,
        signatures=["Oil pressure below expectation at RPM"],
        channels=["OIL_PRESS", "ENGINE_RPM"], detection_method="Threshold plus physics residual",
        occurrence=3, detection_difficulty=2,
        implemented_by="backend/physics/thermo_model.py"))

    f.add(FailureMode(
        "FM-11", "Main / big-end bearings", "Bearing wear and spalling", "Contamination, oil degradation, overload",
        "Increasing clearance, debris generation", "Catastrophic failure if unchecked",
        SeverityClass.CATASTROPHIC,
        signatures=["Cu/Pb/Sn rise in oil", "Large debris particles",
                    "Envelope-spectrum bearing defect tones"],
        channels=["OIL_Cu_PPM", "OIL_Pb_PPM", "OIL_LARGE_DEBRIS", "VIB"],
        detection_method="Wear-metal trend and debris count; envelope analysis planned",
        occurrence=2, detection_difficulty=5,
        implemented_by="backend/physics/oil_system.py (envelope F06 planned)"))

    f.add(FailureMode(
        "FM-12", "Lubricant", "Oil degradation", "Thermal oxidation, fuel dilution, time in service",
        "Viscosity loss, reduced film strength", "Accelerated wear",
        SeverityClass.MARGINAL,
        signatures=["Viscosity ratio fall", "Oxidation index rise"],
        channels=["OIL_VISCOSITY_RATIO", "OIL_OXIDATION_INDEX", "OIL_TEMP"],
        detection_method="Oil condition model",
        occurrence=6, detection_difficulty=4,
        implemented_by="backend/physics/oil_system.py"))

    # --- Turbocharger ---
    f.add(FailureMode(
        "FM-13", "Turbocharger", "Wastegate stuck", "Actuator failure, coking, linkage seizure",
        "Loss of boost control", "Underboost (power loss) or overboost (detonation)",
        SeverityClass.CRITICAL,
        signatures=["MAP not tracking command", "Wastegate position frozen"],
        channels=["MAP", "WASTEGATE_POS", "TPS"], detection_method="MAP tracking residual",
        occurrence=4, detection_difficulty=3,
        implemented_by="backend/physics/turbo_model.py"))

    f.add(FailureMode(
        "FM-14", "Turbocharger", "Bearing wear / overspeed", "Hot shutdown coking, oil starvation, sustained high PR",
        "Efficiency loss, shaft imbalance", "Boost loss then turbine failure",
        SeverityClass.CRITICAL,
        signatures=["Compressor efficiency fall", "Raised charge temperature for given PR",
                    "Shaft order vibration"],
        channels=["TURBO_PRESSURE_RATIO", "CHARGE_TEMP_C", "VIB"],
        detection_method="Efficiency residual; order analysis planned",
        occurrence=3, detection_difficulty=5,
        compensating_provision="Cool-down period before shutdown",
        implemented_by="backend/physics/turbo_model.py"))

    f.add(FailureMode(
        "FM-15", "Turbocharger", "Compressor surge", "High PR at low corrected flow (rapid chop at altitude)",
        "Flow reversal", "Boost oscillation, mechanical damage", SeverityClass.CRITICAL,
        signatures=["Surge margin collapse", "MAP oscillation"],
        channels=["TURBO_SURGE_MARGIN", "MAP"], detection_method="Surge margin monitor",
        occurrence=2, detection_difficulty=6,
        implemented_by="backend/physics/turbo_model.py"))

    # --- Fuel system / environment ---
    f.add(FailureMode(
        "FM-16", "Fuel system", "Wax formation / filter plugging (CFPP)",
        "Prolonged cold soak at altitude on kerosene",
        "Filter blockage, supply starvation", "Power loss or flameout; restart not assured",
        SeverityClass.CATASTROPHIC,
        signatures=["Fuel temperature approaching cloud point", "Filter dP rise",
                    "Supply pressure fall"],
        channels=["FUEL_TEMP_C", "FUEL_FILTER_DP_KPA", "FUEL_PRESSURE"],
        detection_method="Cloud-point / CFPP margin monitor",
        occurrence=3, detection_difficulty=4,
        compensating_provision="Fuel heater, anti-icing additive",
        engine_classes=["CI"], implemented_by="backend/physics/fuel_thermal.py"))

    # --- Electrical ---
    f.add(FailureMode(
        "FM-17", "Alternator", "Output degradation", "Brush/regulator wear, bearing wear",
        "Falling bus voltage under load", "Battery depletion then FADEC loss",
        SeverityClass.CATASTROPHIC,
        signatures=["Bus voltage fall under known load", "Battery discharging in flight"],
        channels=["BUS_VOLTAGE", "BATTERY_CURRENT"],
        detection_method="Electrical power balance residual",
        occurrence=4, detection_difficulty=2,
        compensating_provision="Battery reserve, dual lanes",
        implemented_by="planned F16"))

    f.add(FailureMode(
        "FM-18", "FADEC", "Lane disagreement / lane failure", "Sensor or processor fault in one lane",
        "Loss of redundancy", "Degraded control; dual failure stops the engine",
        SeverityClass.CATASTROPHIC,
        signatures=["Lane A vs Lane B parameter divergence"],
        channels=["FADEC_ACTIVE_LANE", "MAP_LANE_A", "MAP_LANE_B"],
        detection_method="Cross-lane disagreement monitor",
        occurrence=2, detection_difficulty=2,
        compensating_provision="Dual-lane architecture",
        implemented_by="planned F55"))

    # --- Sensing ---
    f.add(FailureMode(
        "FM-19", "Sensor", "Drift / bias", "Ageing, thermal effects, connector degradation",
        "Measurement error", "Wrong diagnosis; unnecessary abort or missed fault",
        SeverityClass.CRITICAL,
        signatures=["Slow divergence from redundant channels or physics expectation"],
        channels=["CHT_n", "EGT_n", "MAP"],
        detection_method="Redundancy voting plus model-based bias estimation",
        occurrence=6, detection_difficulty=6,
        implemented_by="backend/physics/sensor_validator.py (partial — G05 open)"))

    # --- Gearbox / drivetrain ---
    f.add(FailureMode(
        "FM-20", "Reduction gearbox", "Gear tooth wear / micro-pitting",
        "Torsional vibration, lubrication breakdown",
        "Increasing mesh vibration", "Gearbox failure, loss of propulsion",
        SeverityClass.CATASTROPHIC,
        signatures=["Sidebands around gear mesh frequency", "Fe rise in oil"],
        channels=["VIB", "OIL_Fe_PPM"],
        detection_method="Sideband energy around GMF (planned F05); wear metals",
        occurrence=3, detection_difficulty=6,
        implemented_by="backend/physics/oil_system.py (order analysis F05 planned)"))

    return f
