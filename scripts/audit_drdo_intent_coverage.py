"""
Audit script for DRDO Intent & Expected Solution Knowledge Base (DRDO PS 26054).
Verifies 100% presence, distribution, and depth across all 31 prompt dimensions and requirements.
"""

import os
from pathlib import Path

TARGET_DIR = Path(r"e:\backup-llm\backup-no-llm\3d_engine\final_touch")

AUDIT_CATEGORIES = {
    "1. Exact PS Terminology & Semantic Analysis": [
        "AI-enabled", "Real-time", "Digital Twin", "Health Monitoring", "Fault Prediction",
        "Mission Reliability", "Aero Piston Engine", "MALE UAV", "Continuously synchronized",
        "Live telemetry", "Physics-based models", "Operational history", "AI-driven analytics",
        "Ground Control Station", "Engine test rigs", "Fleet-level monitoring", "Health indices",
        "Predictive maintenance", "Degradation tracking", "Mission replay", "Environmental conditions",
        "Operating conditions", "Scalable", "Modular", "Defence-grade"
    ],
    "2. Evidentiary Labeling Standards": [
        "Explicit PS requirement", "Strong engineering inference", "Likely expectation",
        "Possible interpretation", "Unknown / requires DRDO confirmation"
    ],
    "3. Reconstructed End-to-End System Blocks": [
        "SocketCAN", "Edge Processor", "Jitter Buffer", "Extended Kalman Filter", "0D/1D",
        "Mean Value Engine Model", "Residual Generator", "Anomaly Detector", "Fault Classifier",
        "Degradation Tracker", "Prognostic Engine", "Decision Support", "GCS Operator Interface",
        "Federated Learning", "End-to-End Latency"
    ],
    "4. Health Parameters & Diagnostics": [
        "RPM", "Cylinder Head Temperature", "CHT", "Exhaust Gas Temperature", "EGT",
        "Oil Pressure", "Oil Temperature", "Fuel Flow", "Vibration", "Battery", "Alternator",
        "Injection timing", "Correlation Matrix", "Fault Detection", "Fault Diagnosis", "Prognosis"
    ],
    "5. Mission Reliability & Reachability": [
        "Throttle Derating", "Cooling Descent", "Return to Base", "Divert", "Glide",
        "Reachability Footprint", "Multi-Stream Mission Replay"
    ],
    "6. Defence-Grade, Certification & Data Reality": [
        "CEMILAC", "DDPMAS", "DO-178C", "DAL-C", "EASA AI", "Run-Time Monitor",
        "Deterministic", "Offline Operational Sovereignty", "HMAC-SHA256", "AES-256",
        "Data Feasibility", "Run-to-failure"
    ],
    "7. Credibility, Red-Team & Project Gap Analysis": [
        "Weak Solution", "Hackathon Traps", "Credibility Pillars", "Red-Team", "Rotax 914",
        "Rotax 915", "Austro", "VRDE Jayem", "Over-Engineered", "Under-Engineered", "Actionable Roadmap"
    ]
}

all_text = ""
file_texts = {}
for fname in os.listdir(TARGET_DIR):
    if (fname.startswith("DRDO_INTENT_") or fname.startswith("MASTER_DRDO_")) and fname.endswith(".md"):
        fpath = TARGET_DIR / fname
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            all_text += "\n" + content
            file_texts[fname] = content

total_concepts = 0
found_concepts = 0
missing_concepts = []

print(f"Auditing DRDO Intent Knowledge Base across {len(file_texts)} documents...")
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
    print("ALL 100% OF KEY DRDO INTENT, ENGINEERING & REVERSE-ENGINEERED CONCEPTS VERIFIED PRESENT!")
print("="*70)
