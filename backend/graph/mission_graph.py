"""
Mission Knowledge Graph & Fleet Intelligence Engine — Phase J
DRDO / iDEX Problem Statement ID: 26054

Builds and maintains an air-gapped property graph of sorties, subsystem degradation histories,
anomaly events, and maintenance actions for fleet-wide Condition-Based Maintenance (CBM).

PS reference: doc01 §3 Pillar 4 — "Fleet Intelligence & Condition-Based Maintenance"
Operates 100% offline with zero external cloud dependencies.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Set
import os
import time
import json


@dataclass
class SortieNode:
    sortie_id: str
    region: str
    start_timestamp: float
    end_timestamp: Optional[float] = None
    flight_hours: float = 0.0
    final_health_index: float = 1.0
    status: str = "ACTIVE"  # "ACTIVE" | "COMPLETED" | "ABORTED"
    # Rich mission-record fields (doc04 §2 MISSION_xxx.md schema) — populated by
    # EngineStateService as the sortie progresses so the debrief can cite real
    # flight-envelope data instead of the placeholder values used before.
    uav_tail_number: str = "TAPAS-BH-201-AF01"
    start_health_index: float = 1.0
    min_oat_c: Optional[float] = None
    max_oat_c: Optional[float] = None
    min_altitude_ft: Optional[float] = None
    max_altitude_ft: Optional[float] = None
    telemetry_log_path: Optional[str] = None


@dataclass
class SubsystemNode:
    subsystem_id: str
    name: str
    ata_chapter: str
    target_mesh: str
    current_health: float = 1.0
    cumulative_stress_hours: float = 0.0
    last_inspected_epoch: float = 0.0


@dataclass
class AnomalyEventNode:
    event_id: str
    sortie_id: str
    subsystem_id: str
    timestamp_epoch: float
    fault_id: int
    fault_name: str
    severity: str
    anomaly_score: float
    ata_chapter: str
    recommended_action: str
    # Concurrent degradation-trend context at the moment of detection (from
    # DegradationTrendAnalyser via PrognosticsWorker), if one was active — grounds the
    # debrief's timeline in real drift-rate data instead of narrating it after the fact.
    trend_note: Optional[str] = None


@dataclass
class MaintenanceActionNode:
    action_id: str
    sortie_id: str
    subsystem_id: str
    ata_chapter: str
    description: str
    status: str = "OPEN"  # "OPEN" | "SIGNED_OFF"
    # Live RUL snapshot (ProbabilisticRULEstimator) at the moment this action was raised.
    rul_p10_hours: Optional[float] = None
    rul_p50_hours: Optional[float] = None
    limiting_component: Optional[str] = None
    # Ground-crew sign-off record (PS-26054 CBM lifecycle: a work order must be explicitly
    # closed by an inspector, not silently forgotten). Added as trailing Optional fields so
    # `MaintenanceActionNode(**v)` still loads pre-existing fleet_graph.json rows that predate
    # this field without any migration step.
    signoff_epoch: Optional[float] = None
    signoff_inspector: Optional[str] = None


class MissionKnowledgeGraph:
    """
    Knowledge graph storing multi-sortie engineering data, anomaly histories,
    and CBM lifecycle events — optionally persisted to disk (data/graph_db/)
    so subsystem wear and fleet history survive a server restart instead of
    resetting to a blank graph every process start.
    """

    def __init__(self, persist_path: Optional[str] = None):
        self.sorties: Dict[str, SortieNode] = {}
        self.subsystems: Dict[str, SubsystemNode] = {}
        self.anomalies: Dict[str, AnomalyEventNode] = {}
        self.maintenance_actions: Dict[str, MaintenanceActionNode] = {}

        # Edges
        self.sortie_anomalies: Dict[str, List[str]] = {}  # sortie_id -> [event_id]
        self.subsystem_anomalies: Dict[str, List[str]] = {}  # subsystem_id -> [event_id]
        self.sortie_actions: Dict[str, List[str]] = {}  # sortie_id -> [action_id]

        self._init_standard_subsystems()

        # If a persist_path is given and already holds a prior fleet history, load it now —
        # this overlays/replaces the freshly-initialised subsystems above with their real
        # accumulated health/stress-hours, and repopulates every past sortie/anomaly/action.
        self.persist_path = persist_path
        if self.persist_path and os.path.exists(self.persist_path):
            try:
                self.load(self.persist_path)
            except Exception:
                # Corrupt or unreadable store: keep the fresh in-memory graph rather than
                # crashing server startup over a damaged CBM history file.
                pass

    # ------------------------------------------------------------------
    # Persistence — JSON, no pickle, air-gapped-safe
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sorties": {k: asdict(v) for k, v in self.sorties.items()},
            "subsystems": {k: asdict(v) for k, v in self.subsystems.items()},
            "anomalies": {k: asdict(v) for k, v in self.anomalies.items()},
            "maintenance_actions": {k: asdict(v) for k, v in self.maintenance_actions.items()},
            "sortie_anomalies": self.sortie_anomalies,
            "subsystem_anomalies": self.subsystem_anomalies,
            "sortie_actions": self.sortie_actions,
        }

    def save(self, path: Optional[str] = None) -> None:
        """Persist the full fleet graph to a single JSON file.

        os.replace() is atomic on both POSIX and Windows -- readers never see a
        half-written store. What "atomic" does not mean on Windows: mandatory
        file locking means MoveFileEx (what os.replace uses under the hood)
        raises PermissionError/WinError 32 if another process has `target` open
        at that instant, even just for reading. On POSIX the same call would
        silently succeed. This is transient -- a concurrent reader's handle
        closes within milliseconds -- so a short bounded retry is the correct
        fix, not a design change. Discovered running the same server with two
        processes touching this file concurrently on Windows.
        """
        target = path or self.persist_path
        if not target:
            return
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        tmp = target + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

        last_err: Optional[OSError] = None
        for attempt in range(5):
            try:
                os.replace(tmp, target)
                return
            except PermissionError as e:
                last_err = e
                time.sleep(0.02 * (attempt + 1))
        # All retries exhausted: surface the failure rather than silently
        # dropping the write, but leave `tmp` in place so no data is lost --
        # the next successful save() overwrites it.
        raise last_err  # type: ignore[misc]

    def load(self, path: str) -> None:
        """Restore fleet state from a JSON file previously written by save()."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.sorties = {k: SortieNode(**v) for k, v in data.get("sorties", {}).items()}
        self.subsystems = {k: SubsystemNode(**v) for k, v in data.get("subsystems", {}).items()}
        self.anomalies = {k: AnomalyEventNode(**v) for k, v in data.get("anomalies", {}).items()}
        self.maintenance_actions = {
            k: MaintenanceActionNode(**v) for k, v in data.get("maintenance_actions", {}).items()
        }
        self.sortie_anomalies = data.get("sortie_anomalies", {})
        self.subsystem_anomalies = data.get("subsystem_anomalies", {})
        self.sortie_actions = data.get("sortie_actions", {})

    def _autosave(self) -> None:
        """Called after every meaningful mutation. No-op unless persist_path is configured."""
        if self.persist_path:
            self.save()

    def _init_standard_subsystems(self):
        """Initialise the canonical Rotax 912 iS subsystem nodes."""
        subsystems_data = [
            ("SUB_CYL_2", "Cylinder #2 Head Assembly", "ATA 72-00", "Covers_Theme_M_PlasticTheme_0"),
            ("SUB_FUEL_SYS", "Fuel Injection System & Rails", "ATA 73-10", "Rotax_912i_Base_M_PlasticGreen_0"),
            ("SUB_IGNITION", "Dual Ignition Harness & Coils", "ATA 74-20", "Wiring_Harness_M_Copper_0"),
            ("SUB_LUBRICATION", "Dry-Sump Lubrication Circuit", "ATA 79-00", "Oil_Tank_M_Steel_0"),
            ("SUB_GEARBOX", "Propeller Reduction Gearbox", "ATA 72-10", "Gearbox_Type_2_M_Steel_0"),
            # ATA chapters here must stay aligned with ROTAX_ATA_FAULT_DIRECTIVES in
            # backend/agent/diagnostic_agent.py (the authoritative, user-facing source cited
            # in AI diagnoses and checklists) - SUB_EXHAUST and SUB_FADEC previously disagreed
            # with it (78-00 vs 78-10, 73-20 vs 76-00), which is exactly the kind of citation
            # inconsistency that undermines an "ATA-grounded, explainable" system if a reviewer
            # cross-checks the CBM debrief against the live diagnostic directive for the same
            # fault.
            ("SUB_EXHAUST", "Exhaust Gas Manifold Runner #3", "ATA 78-10", "Exhaust_System_M_SteelDark_0"),
            ("SUB_ELECTRICAL", "Heavy-Duty Alternator & Power Bus", "ATA 24-00", "External_Alternator_M_Steel_0"),
            ("SUB_FADEC", "Dual Lane FADEC Engine Control Units", "ATA 76-00", "ECU_M_PlasticBlack_0"),
        ]
        for sid, name, ata, mesh in subsystems_data:
            self.subsystems[sid] = SubsystemNode(
                subsystem_id=sid,
                name=name,
                ata_chapter=ata,
                target_mesh=mesh,
            )
            self.subsystem_anomalies[sid] = []

    def start_sortie(self, sortie_id: str, region: str = "LADAKH",
                     uav_tail_number: str = "TAPAS-BH-201-AF01") -> SortieNode:
        """Register a new mission sortie."""
        node = SortieNode(
            sortie_id=sortie_id,
            region=region,
            start_timestamp=time.time(),
            uav_tail_number=uav_tail_number,
            start_health_index=1.0,
        )
        self.sorties[sortie_id] = node
        self.sortie_anomalies[sortie_id] = []
        self.sortie_actions[sortie_id] = []
        self._autosave()
        return node

    def update_sortie_envelope(self, sortie_id: str, oat_c: float, altitude_ft: float) -> None:
        """
        Widen the sortie's recorded ambient flight envelope (doc04 §2's
        ambient_environment.oat_range_celsius / density_altitude_ft). Called every tick
        from EngineStateService — cheap dict-field updates only, never autosaves (that
        would mean a disk write 20x/sec); persistence happens on the next meaningful
        mutation (anomaly, maintenance action, or sortie completion).
        """
        node = self.sorties.get(sortie_id)
        if node is None:
            return
        node.min_oat_c = oat_c if node.min_oat_c is None else min(node.min_oat_c, oat_c)
        node.max_oat_c = oat_c if node.max_oat_c is None else max(node.max_oat_c, oat_c)
        node.min_altitude_ft = altitude_ft if node.min_altitude_ft is None else min(node.min_altitude_ft, altitude_ft)
        node.max_altitude_ft = altitude_ft if node.max_altitude_ft is None else max(node.max_altitude_ft, altitude_ft)

    def set_telemetry_log_path(self, sortie_id: str, path: str) -> None:
        """Record the on-disk path of this sortie's live telemetry CSV, once it exists."""
        node = self.sorties.get(sortie_id)
        if node is not None:
            node.telemetry_log_path = path

    def record_anomaly(self, sortie_id: str, fault_id: int, fault_name: str,
                       severity: str, anomaly_score: float, ata_chapter: str,
                       recommended_action: str,
                       trend_note: Optional[str] = None) -> AnomalyEventNode:
        """Record an anomaly or fault event linked to a sortie and engine subsystem."""
        event_id = f"ANOM-{len(self.anomalies) + 1:04d}"

        # Determine affected subsystem
        subsystem_id = self._map_fault_to_subsystem(fault_id)

        node = AnomalyEventNode(
            event_id=event_id,
            sortie_id=sortie_id,
            subsystem_id=subsystem_id,
            timestamp_epoch=time.time(),
            fault_id=fault_id,
            fault_name=fault_name,
            severity=severity,
            anomaly_score=anomaly_score,
            ata_chapter=ata_chapter,
            recommended_action=recommended_action,
            trend_note=trend_note,
        )
        self.anomalies[event_id] = node

        if sortie_id in self.sortie_anomalies:
            self.sortie_anomalies[sortie_id].append(event_id)
        if subsystem_id in self.subsystem_anomalies:
            self.subsystem_anomalies[subsystem_id].append(event_id)

        # Degrade subsystem health
        if subsystem_id in self.subsystems:
            sub = self.subsystems[subsystem_id]
            sub.current_health = max(0.1, sub.current_health - 0.25)

        self._autosave()
        return node

    def record_maintenance_action(self, sortie_id: str, fault_id: int,
                                 ata_chapter: str, description: str,
                                 rul_p10_hours: Optional[float] = None,
                                 rul_p50_hours: Optional[float] = None,
                                 limiting_component: Optional[str] = None) -> MaintenanceActionNode:
        """Record an action order for ground crews."""
        action_id = f"MAINT-{len(self.maintenance_actions) + 1:04d}"
        subsystem_id = self._map_fault_to_subsystem(fault_id)

        node = MaintenanceActionNode(
            action_id=action_id,
            sortie_id=sortie_id,
            subsystem_id=subsystem_id,
            ata_chapter=ata_chapter,
            description=description,
            rul_p10_hours=rul_p10_hours,
            rul_p50_hours=rul_p50_hours,
            limiting_component=limiting_component,
        )
        self.maintenance_actions[action_id] = node
        if sortie_id in self.sortie_actions:
            self.sortie_actions[sortie_id].append(action_id)
        self._autosave()
        return node

    def complete_sortie(self, sortie_id: str, flight_hours: float,
                        final_health: float) -> Optional[SortieNode]:
        """Finalise a sortie and update subsystem stress hours."""
        if sortie_id not in self.sorties:
            return None
        node = self.sorties[sortie_id]
        node.end_timestamp = time.time()
        node.flight_hours = flight_hours
        node.final_health_index = final_health
        node.status = "COMPLETED"

        for sub in self.subsystems.values():
            sub.cumulative_stress_hours += flight_hours

        self._autosave()
        return node

    def sign_off_action(self, action_id: str, inspector: str) -> Optional[MaintenanceActionNode]:
        """Close a maintenance work order. Returns None if the action_id is unknown; raises
        ValueError if it is already signed off (re-signing a closed order silently would hide
        a real double-approval bug from whoever is calling this)."""
        node = self.maintenance_actions.get(action_id)
        if node is None:
            return None
        if node.status == "SIGNED_OFF":
            raise ValueError(f"{action_id} is already signed off by {node.signoff_inspector!r}")
        node.status = "SIGNED_OFF"
        node.signoff_epoch = time.time()
        node.signoff_inspector = inspector
        self._autosave()
        return node

    def get_work_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List maintenance actions (optionally filtered to 'OPEN' or 'SIGNED_OFF'), newest
        first, for a ground-crew work-order queue view."""
        actions = list(self.maintenance_actions.values())
        if status:
            actions = [a for a in actions if a.status == status]
        actions.sort(key=lambda a: a.action_id, reverse=True)
        return [asdict(a) for a in actions]

    def get_cbm_summary(self) -> Dict[str, Any]:
        """
        Fleet Condition-Based Maintenance status summary. With persist_path configured,
        this is genuinely fleet-wide: self.subsystems/anomalies accumulate across every
        sortie ever recorded (including past server restarts), not just the current
        in-memory session.
        """
        items = []
        for sid, sub in self.subsystems.items():
            anoms = self.subsystem_anomalies.get(sid, [])
            items.append({
                "subsystem": sub.name,
                "ata_chapter": sub.ata_chapter,
                "current_health": round(sub.current_health, 2),
                "cumulative_hours": round(sub.cumulative_stress_hours, 1),
                "total_anomalies": len(anoms),
                "action_required": sub.current_health < 0.75 or len(anoms) > 0,
            })
        return {
            "total_sorties": len(self.sorties),
            "total_anomalies": len(self.anomalies),
            "open_actions": sum(1 for a in self.maintenance_actions.values() if a.status == "OPEN"),
            "subsystems": items,
        }

    def get_region_comparison(self) -> Dict[str, Any]:
        """
        Cross-theater wear/anomaly comparison (PS-26054 doc01 §3 Pillar 4 — "harsh climate
        modeling ... maximizing UAV fleet readiness"), aggregated across every sortie this
        graph has ever recorded per region (e.g. Ladakh vs Thar Desert), not just the
        currently-active sortie.
        """
        regions: Dict[str, Dict[str, Any]] = {}
        for sortie in self.sorties.values():
            r = regions.setdefault(sortie.region, {
                "region": sortie.region,
                "sorties": 0,
                "total_flight_hours": 0.0,
                "_health_sum": 0.0,
                "_health_n": 0,
                "anomaly_counts_by_fault": {},
                "observed_oat_range_c": [None, None],
                "observed_altitude_range_ft": [None, None],
            })
            r["sorties"] += 1
            r["total_flight_hours"] += sortie.flight_hours
            if sortie.status == "COMPLETED":
                r["_health_sum"] += sortie.final_health_index
                r["_health_n"] += 1
            for bound_key, lo_attr, hi_attr in (
                ("observed_oat_range_c", "min_oat_c", "max_oat_c"),
                ("observed_altitude_range_ft", "min_altitude_ft", "max_altitude_ft"),
            ):
                lo, hi = getattr(sortie, lo_attr), getattr(sortie, hi_attr)
                if lo is not None:
                    cur_lo, cur_hi = r[bound_key]
                    r[bound_key] = [
                        lo if cur_lo is None else min(cur_lo, lo),
                        hi if cur_hi is None else max(cur_hi, hi),
                    ]
            for eid in self.sortie_anomalies.get(sortie.sortie_id, []):
                a = self.anomalies.get(eid)
                if a:
                    r["anomaly_counts_by_fault"][a.fault_name] = (
                        r["anomaly_counts_by_fault"].get(a.fault_name, 0) + 1
                    )

        result = []
        for r in regions.values():
            n = r.pop("_health_n")
            health_sum = r.pop("_health_sum")
            r["avg_final_health_index"] = round(health_sum / n, 3) if n else None
            r["total_flight_hours"] = round(r["total_flight_hours"], 2)
            result.append(r)
        return {"regions": result}

    def _map_fault_to_subsystem(self, fault_id: int) -> str:
        mapping = {
            1: "SUB_CYL_2",
            2: "SUB_FUEL_SYS",
            3: "SUB_IGNITION",
            4: "SUB_LUBRICATION",
            5: "SUB_GEARBOX",
            6: "SUB_EXHAUST",
            7: "SUB_ELECTRICAL",
            8: "SUB_FADEC",
        }
        return mapping.get(fault_id, "SUB_CYL_2")
