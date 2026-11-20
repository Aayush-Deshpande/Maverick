"""
Master Builder for Aero Piston Engine Digital Twin Knowledge Base (DRDO PS 26054).
Compiles 10 exhaustive, peer-reviewed, defense-grade markdown volumes covering:
1. PS Deconstruction & Traceability Matrix
2. Aero-Engine Physics, Thermodynamics & UAV Systems
3. Failure Modes, FMECA & Reliability Engineering
4. Digital Twin Theory, State Estimation & Simulation
5. AI/ML Prognostics, RUL & Uncertainty Quantification
6. Avionics Hardware, Edge AI & System Interfaces
7. GCS HMI, Mission Decision Support & Fleet Federated Learning
8. DRDO Ecosystem, Certification, Airworthiness & Supply Chain
9. Red-Team Review, Gaps, Benchmarking & Evidence Base
10. Master Conceptual Synthesis & Architectural Portal

Outputs synchronized copies to:
- e:/backup-llm/backup-no-llm/3d_engine/final_touch/
- e:/backup-llm/backup-no-llm/3d_engine/final touch/
"""

import os
import sys
from pathlib import Path

# Add scripts directory to path to enable module imports
SCRIPTS_DIR = Path(__file__).resolve().parent
WORKSPACE = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dt_builder import (
    vol1_ps_deconstruction,
    vol2_engine_physics,
    vol3_failure_modes_fmeca,
    vol4_digital_twin_theory,
    vol5_ai_ml_prognostics,
    vol6_avionics_edge_interfaces,
    vol7_gcs_hmi_mission_fleet,
    vol8_drdo_certification_supply,
    vol9_red_team_gaps_evidence,
    vol10_master_portal,
)

FINAL_TOUCH = WORKSPACE / "final_touch"
FINAL_TOUCH_SPACE = WORKSPACE / "final touch"

FINAL_TOUCH.mkdir(parents=True, exist_ok=True)
FINAL_TOUCH_SPACE.mkdir(parents=True, exist_ok=True)

VOLUMES = [
    ("PS_DECONSTRUCTION_AND_TRACEABILITY_MATRIX.md", vol1_ps_deconstruction.CONTENT),
    ("AERO_ENGINE_PHYSICS_THERMODYNAMICS_AND_UAV_SYSTEMS.md", vol2_engine_physics.CONTENT),
    ("FAILURE_MODES_FMECA_AND_RELIABILITY_ENGINEERING.md", vol3_failure_modes_fmeca.CONTENT),
    ("DIGITAL_TWIN_THEORY_STATE_ESTIMATION_AND_SIMULATION.md", vol4_digital_twin_theory.CONTENT),
    ("AI_ML_PROGNOSTICS_RUL_AND_UNCERTAINTY.md", vol5_ai_ml_prognostics.CONTENT),
    ("AVIONICS_HARDWARE_EDGE_AI_AND_SYSTEM_INTERFACES.md", vol6_avionics_edge_interfaces.CONTENT),
    ("GCS_HMI_MISSION_DECISION_SUPPORT_AND_FLEET_FL.md", vol7_gcs_hmi_mission_fleet.CONTENT),
    ("DRDO_ECOSYSTEM_CERTIFICATION_AIRWORTHINESS_AND_SUPPLY_CHAIN.md", vol8_drdo_certification_supply.CONTENT),
    ("RED_TEAM_GAPS_BENCHMARKING_AND_EVIDENCE_BASE.md", vol9_red_team_gaps_evidence.CONTENT),
    ("MASTER_AERO_DIGITAL_TWIN_KNOWLEDGE_BASE.md", vol10_master_portal.CONTENT),
]

print("================================================================================")
print("BUILDING AERO PISTON ENGINE DIGITAL TWIN KNOWLEDGE BASE (DRDO PS 26054)")
print("================================================================================")

total_bytes = 0
for filename, content in VOLUMES:
    content_clean = content.strip() + "\n"
    byte_count = len(content_clean.encode("utf-8"))
    total_bytes += byte_count

    for target_dir in [FINAL_TOUCH, FINAL_TOUCH_SPACE]:
        filepath = target_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content_clean)

    print(f"Generated {filename:<55} : {byte_count:>8,} bytes")

print("--------------------------------------------------------------------------------")
print(f"Compilation Complete! Total Knowledge Base Size: {total_bytes:,} bytes across 10 volumes.")
print(f"Synchronized successfully into:\n  1. {FINAL_TOUCH}\n  2. {FINAL_TOUCH_SPACE}")
print("================================================================================")
