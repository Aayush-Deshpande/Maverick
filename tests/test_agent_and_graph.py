"""
Unit Tests for Plane 2 Diagnostic Agent and Mission Knowledge Graph
DRDO / iDEX Problem Statement ID: 26054
"""

import os
import sys
import unittest
import tempfile
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.agent.diagnostic_agent import DiagnosticAgent, DiagnosticDirective
from backend.graph.mission_graph import MissionKnowledgeGraph
from backend.graph.mission_reporter import MissionReporter


class TestDiagnosticAgent(unittest.TestCase):

    def setUp(self):
        self.agent = DiagnosticAgent()

    def test_ata_grounding_for_overheat(self):
        """Fault 1 returns ATA 72-00 citation and OEM emergency checklist."""
        d = self.agent.diagnose(fault_id=1, confidence=0.98)
        self.assertIsInstance(d, DiagnosticDirective)
        self.assertEqual(d.ata_chapter, "ATA 72-00")
        self.assertEqual(d.subsystem, "ENGINE_CORE_COOLING")
        self.assertIn("Step 1", d.emergency_checklist[0])
        self.assertEqual(d.target_3d_mesh, "Covers_Theme_M_PlasticTheme_0")
        self.assertEqual(d.severity, "CRITICAL")

    def test_ata_grounding_for_oil_pressure_loss(self):
        """Fault 4 returns ATA 79-00 citation for lubrication circuit."""
        d = self.agent.diagnose(fault_id=4, confidence=0.92)
        self.assertEqual(d.ata_chapter, "ATA 79-00")
        self.assertEqual(d.subsystem, "LUBRICATION_SYSTEM")
        self.assertEqual(d.severity, "CRITICAL")

    def test_unknown_fault_graceful_fallback(self):
        """Unrecognized fault ID falls back gracefully with valid structure."""
        d = self.agent.diagnose(fault_id=99, confidence=0.5)
        self.assertEqual(d.ata_chapter, "ATA 00-00")
        self.assertEqual(d.severity, "WARNING")


class TestMissionKnowledgeGraphAndReporter(unittest.TestCase):

    def setUp(self):
        self.graph = MissionKnowledgeGraph()
        self.temp_dir = tempfile.mkdtemp()
        self.reporter = MissionReporter(output_dir=self.temp_dir)

    def test_sortie_lifecycle(self):
        """Sortie start, anomaly recording, and completion update graph state."""
        sid = "SORTIE-TEST-001"
        self.graph.start_sortie(sid, region="LADAKH")
        
        # Record anomaly
        event = self.graph.record_anomaly(
            sortie_id=sid,
            fault_id=1,
            fault_name="Cylinder #2 CHT Overheat",
            severity="CRITICAL",
            anomaly_score=0.88,
            ata_chapter="ATA 72-00",
            recommended_action="Enrich fuel trim +12%"
        )
        self.assertEqual(event.subsystem_id, "SUB_CYL_2")
        self.assertIn(event.event_id, self.graph.sortie_anomalies[sid])

        # Record maintenance action
        act = self.graph.record_maintenance_action(
            sortie_id=sid,
            fault_id=1,
            ata_chapter="ATA 72-00",
            description="Inspect Cylinder #2 baffle seal for tears or dislodgement."
        )
        self.assertEqual(act.status, "OPEN")

        # Complete sortie
        node = self.graph.complete_sortie(sid, flight_hours=2.5, final_health=0.65)
        self.assertEqual(node.status, "COMPLETED")
        self.assertEqual(node.flight_hours, 2.5)

        # Check CBM summary
        cbm = self.graph.get_cbm_summary()
        self.assertEqual(cbm["total_sorties"], 1)
        self.assertEqual(cbm["total_anomalies"], 1)
        self.assertEqual(cbm["open_actions"], 1)

    def test_report_generation(self):
        """Mission debrief file is generated with valid Markdown and YAML frontmatter."""
        sid = "SORTIE-TEST-002"
        self.graph.start_sortie(sid, region="THAR_DESERT")
        self.graph.record_anomaly(
            sortie_id=sid,
            fault_id=4,
            fault_name="Oil Pressure Loss",
            severity="CRITICAL",
            anomaly_score=0.92,
            ata_chapter="ATA 79-00",
            recommended_action="Reduce throttle to 4,200 RPM"
        )
        self.graph.complete_sortie(sid, flight_hours=1.8, final_health=0.25)

        path = self.reporter.generate_report(self.graph, sid)
        self.assertTrue(os.path.exists(path))

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check YAML frontmatter presence — doc04 §2 MISSION_xxx.md schema
        self.assertTrue(content.startswith("---"))
        self.assertIn('sortie_id: "SORTIE-TEST-002"', content)
        self.assertIn('uav_tail_number:', content)
        self.assertIn('theater_region: "THAR_DESERT"', content)
        self.assertIn("## 1. Environmental & Operational Context", content)
        self.assertIn("## 2. Chronological Timeline & Anomaly Events", content)
        self.assertIn("## 3. Post-Flight Maintenance Directives", content)
        self.assertIn("## 4. Condition-Based Maintenance (CBM) Work Orders", content)
        self.assertIn("ATA 79-00", content)

    def test_graph_persistence_round_trip(self):
        """A saved graph reloads with identical sortie/anomaly/subsystem-health state."""
        import tempfile as _tempfile
        persist_dir = _tempfile.mkdtemp()
        persist_path = os.path.join(persist_dir, "fleet_graph.json")

        g1 = MissionKnowledgeGraph(persist_path=persist_path)
        g1.start_sortie("SORTIE-PERSIST-001", region="LADAKH")
        g1.update_sortie_envelope("SORTIE-PERSIST-001", oat_c=-25.0, altitude_ft=21000.0)
        g1.record_anomaly(
            sortie_id="SORTIE-PERSIST-001", fault_id=5, fault_name="Gearbox Vibration",
            severity="WARNING", anomaly_score=0.7, ata_chapter="ATA 72-10",
            recommended_action="Limit rapid RPM transients",
        )
        g1.complete_sortie("SORTIE-PERSIST-001", flight_hours=3.0, final_health=0.7)

        # A fresh graph instance pointed at the same file should recover the exact state,
        # including subsystem wear accumulated by the "previous process".
        g2 = MissionKnowledgeGraph(persist_path=persist_path)
        self.assertIn("SORTIE-PERSIST-001", g2.sorties)
        self.assertEqual(g2.sorties["SORTIE-PERSIST-001"].flight_hours, 3.0)
        self.assertEqual(g2.subsystems["SUB_GEARBOX"].current_health,
                         g1.subsystems["SUB_GEARBOX"].current_health)
        self.assertEqual(len(g2.anomalies), 1)

    def test_region_comparison_aggregates_across_sorties(self):
        """get_region_comparison() aggregates multiple sorties in the same theater."""
        g = MissionKnowledgeGraph()
        g.start_sortie("S-LADAKH-A", region="LADAKH")
        g.complete_sortie("S-LADAKH-A", flight_hours=5.0, final_health=0.9)
        g.start_sortie("S-LADAKH-B", region="LADAKH")
        g.complete_sortie("S-LADAKH-B", flight_hours=4.0, final_health=0.8)
        g.start_sortie("S-THAR-A", region="THAR_DESERT")
        g.complete_sortie("S-THAR-A", flight_hours=2.0, final_health=1.0)

        comparison = g.get_region_comparison()
        regions = {r["region"]: r for r in comparison["regions"]}
        self.assertEqual(regions["LADAKH"]["sorties"], 2)
        self.assertAlmostEqual(regions["LADAKH"]["total_flight_hours"], 9.0)
        self.assertEqual(regions["THAR_DESERT"]["sorties"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
