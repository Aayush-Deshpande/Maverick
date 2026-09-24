"""Automated Maintenance Work Package Generation and Opportunistic Scheduler (B10.1, B10.2, INN-06).

Implements:
1. ATA iSpec 2200 compliant maintenance task definitions.
2. Mapping from diagnostic hypotheses, active DTCs, and RUL limits to concrete WorkPackages.
3. Spares, tooling, and labor hour estimation.
4. Opportunistic task bundling (co-locating impending tasks during an active teardown).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.diagnose.bn import Hypothesis
from backend.prognose.rul import RULEstimate


@dataclass
class SparePart:
    part_number: str
    description: str
    quantity: int
    unit_cost_usd: float = 0.0


@dataclass
class MaintenanceTask:
    task_id: str
    ata_chapter: str
    title: str
    description: str
    estimated_labor_hours: float
    required_spares: List[SparePart]
    required_tools: List[str]
    signoff_steps: List[str]
    trigger_reason: str
    criticality: str = "SCHEDULED"  # AOG_CRITICAL | NEXT_WINDOW | OPPORTUNISTIC


@dataclass
class WorkPackage:
    package_id: str
    tail_id: str
    engine_profile: str
    created_at_flight_hours: float
    tasks: List[MaintenanceTask]
    criticality: str = "NEXT_WINDOW"

    @property
    def total_labor_hours(self) -> float:
        return sum(t.estimated_labor_hours for t in self.tasks)

    @property
    def total_spares_cost_usd(self) -> float:
        return sum(s.unit_cost_usd * s.quantity for t in self.tasks for s in t.required_spares)

    def summary(self) -> Dict[str, Any]:
        return {
            "package_id": self.package_id,
            "tail_id": self.tail_id,
            "engine_profile": self.engine_profile,
            "flight_hours": self.created_at_flight_hours,
            "criticality": self.criticality,
            "num_tasks": len(self.tasks),
            "total_labor_hours": self.total_labor_hours,
            "total_spares_cost_usd": self.total_spares_cost_usd,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "ata_chapter": t.ata_chapter,
                    "title": t.title,
                    "labor_hrs": t.estimated_labor_hours,
                    "trigger": t.trigger_reason,
                }
                for t in self.tasks
            ],
        }


class WorkPackageGenerator:
    """Generates structured maintenance work packages from diagnostic and prognostic outputs."""

    # Standard ATA task catalog template
    TASK_CATALOG = {
        "INJECTOR_COKING": {
            "task_id": "TASK-73-10-04",
            "ata": "ATA 73-10",
            "title": "Fuel Injector Ultrasonic Cleaning and Flow Calibration",
            "hours": 3.0,
            "spares": [
                SparePart("INJ-SEAL-04", "Injector Copper Crush Washer Kit", 4, 15.0),
                SparePart("INJ-ORING-04", "FKM High-Temp O-Ring Set", 4, 12.0),
            ],
            "tools": ["Ultrasonic Bath", "Injector Test Stand", "Torque Wrench 30Nm"],
            "steps": [
                "De-energize high pressure fuel rail and verify 0 bar residual pressure",
                "Remove harness connectors and fuel lines for suspect injector",
                "Perform ultrasonic clean cycle (30 min at 60 deg C)",
                "Mount on flow bench, test spray cone angle and 5-point volume delivery",
                "Reinstall with new crush washers and torque to spec",
            ],
        },
        "COOLING_DEGRADATION": {
            "task_id": "TASK-75-20-02",
            "ata": "ATA 75-20",
            "title": "Coolant Radiator Flush, Thermostat Inspection, and Pressure Test",
            "hours": 2.5,
            "spares": [
                SparePart("COOL-5050-5L", "Aero Waterless / Glycol Coolant 5L", 1, 45.0),
                SparePart("THERM-GSK-01", "Thermostat Housing Gasket", 1, 8.0),
            ],
            "tools": ["Cooling System Pressure Tester (1.5 bar)", "Refractometer"],
            "steps": [
                "Drain coolant into clean recovery vessel; inspect for particulate/oil sheen",
                "Remove thermostat; check opening temperature in calibrated water bath",
                "Reverse flush radiator core with low-pressure wash",
                "Refill coolant, bleed air from cylinder head bleed screws",
                "Pressure test system at 1.4 bar for 15 minutes; zero pressure drop allowed",
            ],
        },
        "OIL_PRESSURE_LOSS": {
            "task_id": "TASK-79-20-01",
            "ata": "ATA 79-20",
            "title": "Oil Pressure Relief Valve Inspection and Oil Filter Teardown",
            "hours": 2.0,
            "spares": [
                SparePart("OIL-FLTR-AERO", "Engine Oil Filter Element", 1, 28.0),
                SparePart("OIL-15W50-4L", "Semi-Synthetic Aero Engine Oil 4L", 1, 55.0),
            ],
            "tools": ["Oil Filter Canister Cutter", "Micrometer", "Magnetic Chip Detector Kit"],
            "steps": [
                "Cut open oil filter canister and inspect pleats for ferrous/bronze particles",
                "Remove pressure relief valve plunger and spring; measure spring free length",
                "Inspect pressure relief valve seat for scoring or debris contamination",
                "Replace filter, fill fresh oil, and perform 5-minute ground idle leak check",
            ],
        },
        "TURBO_BEARING_WEAR": {
            "task_id": "TASK-81-10-01",
            "ata": "ATA 81-10",
            "title": "Turbocharger Cartridge (CHRA) Radial / Axial Play Inspection",
            "hours": 4.5,
            "spares": [
                SparePart("TURBO-CHRA-01", "Center Housing Rotating Assembly", 1, 1450.0),
                SparePart("TURBO-GSK-KIT", "Exhaust Flange & Oil Line Gasket Kit", 1, 38.0),
            ],
            "tools": ["Dial Indicator with Magnetic Base", "Torx Sockets"],
            "steps": [
                "Remove compressor intake duct and exhaust downpipe",
                "Mount dial indicator to compressor nose; measure axial shaft endplay (<0.08mm)",
                "Measure radial shaft play (<0.40mm) and spin wheel by hand; verify zero housing contact",
                "If play exceeds limits, replace CHRA cartridge and prime oil feed line before restart",
            ],
        },
        "PERIODIC_100HR": {
            "task_id": "TASK-05-20-01",
            "ata": "ATA 05-20",
            "title": "100-Flight-Hour Scheduled Airframe / Engine Inspection",
            "hours": 6.0,
            "spares": [
                SparePart("SPARK-PLUG-08", "Aero Spark Plug Set", 4, 90.0),
                SparePart("OIL-FLTR-AERO", "Engine Oil Filter Element", 1, 28.0),
                SparePart("OIL-15W50-4L", "Semi-Synthetic Aero Engine Oil 4L", 1, 55.0),
            ],
            "tools": ["Differential Compression Tester", "Feeler Gauges", "Spark Plug Gapping Tool"],
            "steps": [
                "Perform hot differential compression check on all cylinders (min 70/80 psi)",
                "Inspect spark plug electrode gap and ceramic insulator condition",
                "Check valve clearances; adjust shims if out of tolerance",
                "Inspect exhaust headers for cracking or hot gas staining",
            ],
        },
    }

    def generate_work_package(
        self,
        tail_id: str,
        engine_profile: str,
        flight_hours: float,
        hypotheses: List[Hypothesis],
        ruls: Dict[str, RULEstimate],
        horizon_hours: float = 25.0,
    ) -> WorkPackage:
        tasks: List[MaintenanceTask] = []
        is_aog = False

        # 1. Add tasks from diagnostic hypotheses (top probability > 0.40)
        for hyp in hypotheses:
            if hyp.probability >= 0.40:
                cat = self.TASK_CATALOG.get(hyp.mode_id)
                if cat:
                    crit = "AOG_CRITICAL" if hyp.probability > 0.75 else "NEXT_WINDOW"
                    if crit == "AOG_CRITICAL":
                        is_aog = True
                    tasks.append(
                        MaintenanceTask(
                            task_id=cat["task_id"],
                            ata_chapter=cat["ata"],
                            title=cat["title"],
                            description=f"Triggered by diagnostic finding: {hyp.mode_id} (confidence {hyp.probability*100:.1f}%)",
                            estimated_labor_hours=cat["hours"],
                            required_spares=cat["spares"],
                            required_tools=cat["tools"],
                            signoff_steps=cat["steps"],
                            trigger_reason=f"Diagnostic hypothesis {hyp.mode_id} (P={hyp.probability:.2f})",
                            criticality=crit,
                        )
                    )

        # 2. Add tasks from RUL limits (RUL < horizon)
        for comp_name, rul_est in ruls.items():
            if rul_est.rul_hours_median <= horizon_hours:
                # Check if component already addressed
                cat_key = None
                if "injector" in comp_name.lower() or "fuel" in comp_name.lower():
                    cat_key = "INJECTOR_COKING"
                elif "cool" in comp_name.lower() or "radiator" in comp_name.lower():
                    cat_key = "COOLING_DEGRADATION"
                elif "oil" in comp_name.lower():
                    cat_key = "OIL_PRESSURE_LOSS"
                elif "turbo" in comp_name.lower() or "bearing" in comp_name.lower():
                    cat_key = "TURBO_BEARING_WEAR"

                if cat_key and cat_key in self.TASK_CATALOG:
                    cat = self.TASK_CATALOG[cat_key]
                    # Avoid duplicate task
                    if not any(t.task_id == cat["task_id"] for t in tasks):
                        crit = "AOG_CRITICAL" if rul_est.rul_hours_median < 10.0 else "NEXT_WINDOW"
                        if crit == "AOG_CRITICAL":
                            is_aog = True
                        tasks.append(
                            MaintenanceTask(
                                task_id=cat["task_id"],
                                ata_chapter=cat["ata"],
                                title=cat["title"],
                                description=f"Triggered by RUL limit: {comp_name} RUL p50={rul_est.rul_hours_median:.1f}h",
                                estimated_labor_hours=cat["hours"],
                                required_spares=cat["spares"],
                                required_tools=cat["tools"],
                                signoff_steps=cat["steps"],
                                trigger_reason=f"Prognostic RUL threshold {rul_est.rul_hours_median:.1f}h <= {horizon_hours}h",
                                criticality=crit,
                            )
                        )

        # 3. Opportunistic bundling: if we are already grounding the UAV, check 100-hr interval proximity
        hours_to_100 = 100.0 - (flight_hours % 100.0)
        if tasks and hours_to_100 <= horizon_hours:
            cat = self.TASK_CATALOG["PERIODIC_100HR"]
            if not any(t.task_id == cat["task_id"] for t in tasks):
                tasks.append(
                    MaintenanceTask(
                        task_id=cat["task_id"],
                        ata_chapter=cat["ata"],
                        title=cat["title"] + " (Opportunistic Bundle)",
                        description=f"Bundled with active maintenance teardown (due in {hours_to_100:.1f}h)",
                        estimated_labor_hours=cat["hours"],
                        required_spares=cat["spares"],
                        required_tools=cat["tools"],
                        signoff_steps=cat["steps"],
                        trigger_reason=f"Opportunistic bundling (due in {hours_to_100:.1f}h <= {horizon_hours}h)",
                        criticality="OPPORTUNISTIC",
                    )
                )

        pkg_id = f"WP-{tail_id}-{int(flight_hours):04d}-{uuid.uuid4().hex[:6].upper()}"
        overall_crit = "AOG_CRITICAL" if is_aog else ("NEXT_WINDOW" if tasks else "NOMINAL")

        return WorkPackage(
            package_id=pkg_id,
            tail_id=tail_id,
            engine_profile=engine_profile,
            created_at_flight_hours=flight_hours,
            tasks=tasks,
            criticality=overall_crit,
        )
