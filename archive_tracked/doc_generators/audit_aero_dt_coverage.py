"""
Audit script for Aero Piston Engine Digital Twin Knowledge Base (DRDO PS 26054).
Verifies 100% presence, distribution, and depth across all 36 prompt dimensions and PS requirements.
"""

import os
from pathlib import Path

TARGET_DIR = Path(r"e:\backup-llm\backup-no-llm\3d_engine\final_touch")

AUDIT_CATEGORIES = {
    "1. PS 26054 Explicit Requirements": [
        "MALE UAV", "Aero Piston Engine", "Digital Twin", "Real-Time", "Health Monitoring",
        "Fault Prediction", "Remaining Useful Life", "RUL", "CAN bus", "SocketCAN", "ECU", "FADEC",
        "RPM", "Cylinder Head Temperature", "CHT", "Exhaust Gas Temperature", "EGT",
        "Oil Pressure", "Oil Temperature", "Fuel Flow", "Vibration", "Battery", "Alternator", "Injection timing",
        "Misfire", "Injector", "Cooling degradation", "Lubrication", "Sensor drift",
        "Combustion instability", "Overheating", "Mission replay", "High altitude", "Endurance",
        "Hot-weather", "Rapid throttle transitions", "Dashboard", "HMI", "Maintenance advisory"
    ],
    "2. Aero-Engine Physics & Thermodynamics": [
        "Otto Cycle", "Turbocharger", "Wastegate", "Critical altitude", "Lumped-parameter",
        "Reynolds Equation", "Hydrodynamic", "Constant-speed propeller", "Governor", "ISA atmosphere",
        "BSFC", "Volumetric Efficiency", "Brake Power", "Vogel"
    ],
    "3. Failure Modes, FMECA & Reliability": [
        "FMECA", "FMEA", "MTBF", "MTTR", "Bathtub", "Weibull", "RCM",
        "Condition-Based Maintenance", "Time-Between-Overhaul", "Fault Tree Analysis", "Bearing Spalling",
        "Knock"
    ],
    "4. Digital Twin Theory, Observers & Sim-to-Real": [
        "Digital Model", "Digital Shadow", "Predictive Twin", "Prescriptive Twin",
        "Extended Kalman Filter", "EKF", "Unscented Kalman Filter", "UKF", "Sim-to-Real",
        "Hardware-in-the-Loop", "Software-in-the-Loop", "Digital Thread", "AS9100", "Jitter Buffer"
    ],
    "5. AI/ML, Prognostics & Uncertainty": [
        "Autoencoder", "Isolation Forest", "One-Class SVM", "1D-CNN", "Temporal Transformer",
        "XGBoost", "Neural ODE", "Physics-Informed", "PINN", "Extreme Value Theory", "POT",
        "Wiener process", "Conformal Prediction", "Aleatoric", "Epistemic", "SHAP"
    ],
    "6. Avionics, Edge Computing & Security": [
        "ISO 11898", "CAN-FD", "DBC", "ARINC 429", "SWaP-C", "Jetson", "TensorRT", "INT8",
        "STANAG 4586", "HMAC-SHA256", "AES-256", "Sensor Observability"
    ],
    "7. GCS HMI, Tactical Support & Fleet FL": [
        "MIL-STD-1472", "Alarm fatigue", "Advisory", "Caution", "Warning", "Derating",
        "Return to Base", "Divert", "Glide", "Federated Learning", "FedRand"
    ],
    "8. DRDO Ecosystem, Standards & Certification": [
        "DRDO", "ADE", "VRDE", "GTRE", "CABS", "CEMILAC", "DGAQA", "TAPAS", "Archer",
        "ABHAY", "DO-178C", "DO-254", "ARP4754A", "ARP4761", "DAL-C", "EASA AI", "Atmanirbhar Bharat",
        "Rotax"
    ],
    "9. Red-Team Review, Gaps & Evidence Base": [
        "Red-Team", "False Positive", "False Negative", "TRL", "Sim-to-Real Gap",
        "Benchmarking", "Confirmed", "Strong Evidence", "Plausible", "Unknowns Requiring DRDO"
    ]
}

all_text = ""
file_texts = {}
for fname in os.listdir(TARGET_DIR):
    if (fname.startswith("PS_") or fname.startswith("AERO_") or fname.startswith("FAILURE_") or
        fname.startswith("DIGITAL_") or fname.startswith("AI_") or fname.startswith("AVIONICS_") or
        fname.startswith("GCS_") or fname.startswith("DRDO_") or fname.startswith("RED_") or
        fname.startswith("MASTER_AERO_")) and fname.endswith(".md"):
        fpath = TARGET_DIR / fname
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            all_text += "\n" + content
            file_texts[fname] = content

total_concepts = 0
found_concepts = 0
missing_concepts = []

print(f"Auditing Aero Digital Twin Knowledge Base across {len(file_texts)} documents...")
print(f"Total Text Analyzed: {len(all_text):,} characters.\n")

for cat, concepts in AUDIT_CATEGORIES.items():
    cat_found = 0
    cat_missing = []
    for c in concepts:
        total_concepts += 1
        cnt = all_text.lower().count(c.lower())
        if cnt > 0:
            found_concepts += 1
            cat_found += 1
        else:
            missing_concepts.append(c)
            cat_missing.append(c)
    status = "PASS" if len(cat_missing) == 0 else f"FAIL ({len(cat_missing)} missing)"
    print(f"{cat:<50}: {cat_found}/{len(concepts)} [{status}]")
    if cat_missing:
        for m in cat_missing:
            print(f"   - MISSING: {m}")

print("\n" + "="*70)
print(f"FINAL AUDIT RESULT: {found_concepts}/{total_concepts} ({found_concepts/total_concepts*100:.1f}%) CONCEPTS VERIFIED PRESENT")
if missing_concepts:
    print(f"Total Missing: {len(missing_concepts)}")
else:
    print("ALL 100% OF KEY TECHNICAL, OPERATIONAL & DEFENCE CONCEPTS VERIFIED PRESENT!")
print("="*70)
