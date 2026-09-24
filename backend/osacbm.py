"""
OSA-CBM / ISO 13374 architecture mapping — F34.

Read the problem statement's structure back: data ingestion, signal processing,
detection of abnormal conditions, health indices, RUL and degradation trends,
maintenance advisory. That is not a novel decomposition. It is an unlabelled
restatement of **ISO 13374**, the international standard for condition
monitoring and diagnostics of machines, implemented as **MIMOSA OSA-CBM** with
six functional blocks:

    DA  Data Acquisition        sensors, ECU, CAN, MAVLink
    DM  Data Manipulation       signal processing, feature extraction
    SD  State Detection         comparison against expected values and limits
    HA  Health Assessment       health indices, fault diagnosis
    PA  Prognostic Assessment   RUL, degradation trends, mission reliability
    AG  Advisory Generation     maintenance and operator recommendations

Mapping our modules onto those blocks costs almost nothing and buys two things.
First, a certification-literate reviewer recognises the architecture instantly
rather than having to learn ours. Second — and more useful to us — the mapping
is enforceable: every module declares its layer, and a module that reaches
across layers in the wrong direction is a design error this file can detect.

The layering rule that actually matters is that information flows upward.
Advisory Generation may read a prognosis; Data Acquisition may not read a health
index. Violating that is how a system ends up with a sensor driver that behaves
differently depending on the diagnosis, which is untestable and uncertifiable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

__all__ = ["Layer", "ModuleRegistration", "OSACBM_REGISTRY", "architecture_markdown",
           "check_layering", "coverage"]


class Layer:
    """The six ISO 13374 / OSA-CBM functional blocks, in flow order."""

    DA = "DA_DATA_ACQUISITION"
    DM = "DM_DATA_MANIPULATION"
    SD = "SD_STATE_DETECTION"
    HA = "HA_HEALTH_ASSESSMENT"
    PA = "PA_PROGNOSTIC_ASSESSMENT"
    AG = "AG_ADVISORY_GENERATION"

    ORDER = [DA, DM, SD, HA, PA, AG]

    DESCRIPTION = {
        DA: "Access installed sensors and collect data",
        DM: "Single and multi-channel signal transforms and feature extraction",
        SD: "Compare features against expected values or limits; produce condition indicators",
        HA: "Assess current health of the monitored item and diagnose faults",
        PA: "Project health forward: remaining useful life and future risk",
        AG: "Generate recommended actions for operators and maintainers",
    }

    @classmethod
    def index(cls, layer: str) -> int:
        return cls.ORDER.index(layer)


@dataclass
class ModuleRegistration:
    module: str
    layer: str
    purpose: str
    ps_requirements: List[str] = field(default_factory=list)
    reads_from: List[str] = field(default_factory=list)  # layers it consumes
    implemented: bool = True

    def as_dict(self) -> dict:
        return {
            "module": self.module,
            "layer": self.layer,
            "purpose": self.purpose,
            "ps_requirements": self.ps_requirements,
            "reads_from": self.reads_from,
            "implemented": self.implemented,
        }


# The registry is the architecture. Keeping it in code rather than in a diagram
# means it cannot quietly diverge from what was built.
OSACBM_REGISTRY: List[ModuleRegistration] = [
    # --- DA: Data Acquisition ---
    ModuleRegistration(
        "backend.telemetry.mavlink_efi", Layer.DA,
        "Ingest MAVLink EFI_STATUS (#225) from autopilot, SITL or recorded tlog",
        ["DTC-06", "INT-01", "INT-06", "HMS-11"], []),
    ModuleRegistration(
        "backend.telemetry.can_streamer", Layer.DA,
        "Engine frame generation and transport (to be split into a separate plant, G01)",
        ["INT-01", "INT-06"], []),
    ModuleRegistration(
        "backend.telemetry.aces_loader", Layer.DA,
        "Real Rotax 914 flight telemetry from NASA ACES for physics validation",
        ["DEL-06"], []),
    ModuleRegistration(
        "backend.telemetry.replay_engine", Layer.DA,
        "Historical mission replay through the live ingestion path",
        ["CAP-10", "CAP-15", "SIM-03"], []),

    # --- DM: Data Manipulation ---
    ModuleRegistration(
        "backend.physics.thermo_model", Layer.DM,
        "Thermodynamic expected-state model and residual vector",
        ["INT-02", "INT-03", "INT-07", "CAP-11"], [Layer.DA]),
    ModuleRegistration(
        "backend.physics.turbo_model", Layer.DM,
        "Boosted induction: wastegate authority, lag, surge margin, charge temperature",
        ["INT-02", "SIM-05"], [Layer.DA]),
    ModuleRegistration(
        "backend.physics.induction", Layer.DM,
        "Air filter restriction and dust-ingestion wear chain",
        ["SIM-04", "INT-04"], [Layer.DA]),
    ModuleRegistration(
        "backend.physics.fuel_thermal", Layer.DM,
        "Fuel temperature, cloud point / CFPP margin, cold-soak delivery",
        ["SIM-04", "SIM-05"], [Layer.DA]),
    ModuleRegistration(
        "backend.physics.injector_faults", Layer.DM,
        "Per-cylinder injector condition and torque contribution",
        ["HMS-11", "FDP-03"], [Layer.DA]),
    ModuleRegistration(
        "backend.ml.spectral_analyser", Layer.DM,
        "Vibration spectral features (dormant until the kHz channel exists, F04)",
        ["HMS-09", "FDP-09"], [Layer.DA], implemented=False),

    # --- SD: State Detection ---
    ModuleRegistration(
        "backend.physics.sensor_validator", Layer.SD,
        "Sensor sanity: unphysical rate, spike, frozen channel",
        ["FDP-06"], [Layer.DM]),
    ModuleRegistration(
        "backend.twin.integrity", Layer.SD,
        "Physics-constrained telemetry integrity and spoof detection",
        ["INN-07"], [Layer.DM]),
    ModuleRegistration(
        "backend.evaluation.threshold_baseline", Layer.SD,
        "Conventional limit monitor, retained as the measured baseline",
        ["FDP-01"], [Layer.DM]),
    ModuleRegistration(
        "backend.ml.anomaly_detector", Layer.SD,
        "Unsupervised residual anomaly scoring",
        ["CAP-03", "CAP-12", "AIM-04"], [Layer.DM]),

    # --- HA: Health Assessment ---
    ModuleRegistration(
        "backend.ml.detection_pipeline", Layer.HA,
        "Nine-stage real-time detection and health indices",
        ["HMS-01", "HMS-02", "CAP-02"], [Layer.SD, Layer.DM]),
    ModuleRegistration(
        "backend.physics.oil_system", Layer.HA,
        "Wear-metal spectrum, debris and oil condition with source attribution",
        ["FDP-05"], [Layer.DM]),
    ModuleRegistration(
        "backend.twin.validity", Layer.HA,
        "Twin self-assessment; model drift vs engine fault vs sensor fault",
        ["CAP-11", "DTC-03"], [Layer.SD, Layer.DM]),
    ModuleRegistration(
        "backend.reliability.isolability", Layer.HA,
        "Which fault modes are physically distinguishable with the fitted sensors",
        ["FDP-01"], [Layer.SD]),

    # --- PA: Prognostic Assessment ---
    ModuleRegistration(
        "backend.evaluation.damage_accumulation", Layer.PA,
        "Rainflow + Miner physics-of-failure life consumption",
        ["CAP-05", "CAP-06", "CAP-13", "AIM-05"], [Layer.HA]),
    ModuleRegistration(
        "backend.ml.rul_estimator", Layer.PA,
        "Monte Carlo RUL and component-level prognosis",
        ["CAP-06", "AIM-05"], [Layer.HA]),
    ModuleRegistration(
        "backend.ml.trend_analyser", Layer.PA,
        "Degradation trend fitting",
        ["CAP-05", "CAP-13", "AIM-06"], [Layer.HA]),
    ModuleRegistration(
        "backend.evaluation.conformal", Layer.PA,
        "Distribution-free RUL intervals with reported empirical coverage",
        ["CAP-06"], [Layer.PA]),
    ModuleRegistration(
        "backend.physics.exposure", Layer.PA,
        "Environmental exposure accumulation and wear acceleration factors",
        ["INT-08"], [Layer.HA]),
    ModuleRegistration(
        "backend.mission.reliability", Layer.PA,
        "Mission completion probability with limiting-component attribution",
        ["SYS-01", "CAP-04", "CAP-14"], [Layer.PA, Layer.HA]),

    # --- AG: Advisory Generation ---
    ModuleRegistration(
        "backend.mission.prescriptive", Layer.AG,
        "Derate ladder and mission re-planning against a reliability requirement",
        ["AIM-03", "AIM-07", "VIS-08"], [Layer.PA]),
    ModuleRegistration(
        "backend.reports", Layer.AG,
        "Mission debriefs and mission-wise health reports",
        ["CAP-09", "VIS-09"], [Layer.PA, Layer.HA]),
    ModuleRegistration(
        "backend.graph", Layer.AG,
        "Fleet knowledge graph, work orders and maintenance history",
        ["INT-08", "AIM-03", "VIS-08"], [Layer.PA, Layer.HA]),
]


def check_layering() -> List[str]:
    """Report modules that consume a layer above their own.

    Information flows upward in OSA-CBM. A Data Acquisition module that reads a
    health index has coupled sensing to diagnosis, which makes both untestable
    in isolation and is a finding worth surfacing rather than a style opinion.
    """
    problems: List[str] = []
    for reg in OSACBM_REGISTRY:
        own = Layer.index(reg.layer)
        for src in reg.reads_from:
            if Layer.index(src) > own:
                problems.append(
                    f"{reg.module} ({reg.layer}) reads from {src}, which is above it")
    return problems


def coverage() -> Dict[str, dict]:
    """Per-layer module counts and implementation state."""
    out: Dict[str, dict] = {}
    for layer in Layer.ORDER:
        mods = [r for r in OSACBM_REGISTRY if r.layer == layer]
        done = [r for r in mods if r.implemented]
        reqs: List[str] = []
        for m in mods:
            reqs.extend(m.ps_requirements)
        out[layer] = {
            "description": Layer.DESCRIPTION[layer],
            "modules": len(mods),
            "implemented": len(done),
            "pending": [r.module for r in mods if not r.implemented],
            "ps_requirements": sorted(set(reqs)),
        }
    return out


def architecture_markdown() -> str:
    """Render the architecture document from the registry itself."""
    lines = [
        "# ANUMAAN architecture — ISO 13374 / MIMOSA OSA-CBM mapping",
        "",
        "The problem statement's structure — ingestion, processing, abnormal-condition",
        "detection, health indices, RUL and degradation, maintenance advisory — is an",
        "unlabelled restatement of ISO 13374. This document maps every module onto the",
        "standard's six functional blocks, and is generated from",
        "`backend/osacbm.py` so it cannot drift from the code.",
        "",
    ]
    cov = coverage()
    for layer in Layer.ORDER:
        info = cov[layer]
        code = layer.split("_")[0]
        lines += [
            f"## {code} — {layer.split('_', 1)[1].replace('_', ' ').title()}",
            "",
            f"*{info['description']}*",
            "",
            f"{info['implemented']}/{info['modules']} modules implemented. "
            f"PS requirements served: {', '.join(info['ps_requirements']) or '—'}",
            "",
            "| Module | Purpose | Reads | Status |",
            "|---|---|---|---|",
        ]
        for reg in [r for r in OSACBM_REGISTRY if r.layer == layer]:
            reads = ", ".join(s.split("_")[0] for s in reg.reads_from) or "—"
            status = "implemented" if reg.implemented else "**pending**"
            lines.append(f"| `{reg.module}` | {reg.purpose} | {reads} | {status} |")
        lines.append("")

    problems = check_layering()
    lines += ["## Layering check", ""]
    if problems:
        lines += ["Information must flow upward. The following violate that:", ""]
        lines += [f"- {p}" for p in problems]
    else:
        lines.append("No layering violations: every module reads only from its own "
                     "layer or below.")
    return "\n".join(lines)
