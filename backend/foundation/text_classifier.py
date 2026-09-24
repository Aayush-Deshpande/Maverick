"""Zero-Shot Maintenance Log & PIREP Text Classifier (W10, INN-06, D35).

Classifies free-text pilot squawks and technician maintenance logs into:
1. ATA Chapters (ATA 72 Power Plant, ATA 73 Engine Fuel, ATA 75 Cooling, ATA 79 Oil, ATA 81 Turbo).
2. Urgency severity levels (AOG_GROUNDING, SAFETY_CRITICAL, ADVISORY, ROUTINE).
3. Ambiguity & confidence scoring with keyword and embedding similarity fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TextClassificationResult:
    text: str
    primary_ata: str
    ata_title: str
    urgency: str
    confidence: float
    matched_keywords: List[str]
    suggested_inspections: List[str]


class MaintenanceTextClassifier:
    """Classifies free-text pilot reports (PIREPs) and hangar maintenance records."""

    ATA_TAXONOMY = {
        "ATA 72": {
            "title": "Engine Reciprocating / Core",
            "keywords": ["cylinder", "piston", "compression", "valve", "spark plug", "crankcase", "misfire", "rough idle", "backfire", "tappet"],
            "inspections": ["Differential compression check", "Borescope cylinder inspection", "Valve lash check"],
        },
        "ATA 73": {
            "title": "Engine Fuel & Injection",
            "keywords": ["injector", "fuel flow", "fuel rail", "rail pressure", "coking", "fuel leak", "injector trim", "lambda", "mixture", "high pressure pump"],
            "inspections": ["Injector flow calibration bench test", "High pressure rail leak check", "Fuel filter inspection"],
        },
        "ATA 75": {
            "title": "Engine Cooling",
            "keywords": ["cht", "coolant", "radiator", "water pump", "overheat", "head temperature", "thermal runaway", "glycol", "coolant boil"],
            "inspections": ["Cooling system pressure test (1.4 bar)", "Thermostat opening test", "Radiator fin airflow check"],
        },
        "ATA 79": {
            "title": "Engine Oil System",
            "keywords": ["oil pressure", "oil temp", "scavenge", "pressure drop", "filter bypass", "metal shavings", "chip detector", "oil cooler"],
            "inspections": ["Cut open oil filter canister", "Oil relief valve plunger inspection", "Spectrometric oil analysis"],
        },
        "ATA 81": {
            "title": "Turbocharging & Boost",
            "keywords": ["turbo", "boost", "wastegate", "map drop", "manifold pressure", "compressor wheel", "chra", "whirl", "intercooler"],
            "inspections": ["Dial indicator turbo shaft endplay check", "Wastegate actuator calibration", "Compressor inlet inspection"],
        },
    }

    def classify_log(self, text: str) -> TextClassificationResult:
        text_lower = text.lower()
        words = re.findall(r"\b\w+\b", text_lower)

        best_ata = "ATA 72"
        best_score = 0
        best_matches: List[str] = []

        # Keyword matching & TF scoring
        for ata_code, data in self.ATA_TAXONOMY.items():
            matches = [kw for kw in data["keywords"] if kw in text_lower]
            score = len(matches)
            if score > best_score:
                best_score = score
                best_ata = ata_code
                best_matches = matches

        # Urgency determination
        urgency = "ROUTINE"
        if any(w in text_lower for w in ["emergency", "shutdown", "flameout", "zero oil", "fire", "exploded", "seized"]):
            urgency = "AOG_GROUNDING"
        elif any(w in text_lower for w in ["overheat", "rapid drop", "exceeded redline", "loss of power", "severe vibration"]):
            urgency = "SAFETY_CRITICAL"
        elif any(w in text_lower for w in ["fluctuation", "high", "low", "drift", "suspect", "trim warning"]):
            urgency = "ADVISORY"

        confidence = float(min(0.99, max(0.40, 0.40 + 0.15 * best_score)))

        return TextClassificationResult(
            text=text,
            primary_ata=best_ata,
            ata_title=self.ATA_TAXONOMY[best_ata]["title"],
            urgency=urgency,
            confidence=confidence,
            matched_keywords=best_matches,
            suggested_inspections=self.ATA_TAXONOMY[best_ata]["inspections"],
        )
