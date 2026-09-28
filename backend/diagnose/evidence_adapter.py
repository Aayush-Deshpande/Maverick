"""Evidence Adapter (Phase 6, FDP-02..09, AIM-02).

Extracts formal Bayesian Evidence from real-time DetectionResults,
residual channel anomalies, and thermodynamic Frame telemetry.
"""

from __future__ import annotations

from typing import List, Optional
from backend.core.frame import Frame
from backend.detect import DetectionResult
from backend.diagnose.bn import Evidence
from backend.physics.engine_config import EngineConfig


def build_evidence(
    detection: Optional[DetectionResult],
    frame: Frame,
    cfg: EngineConfig,
) -> List[Evidence]:
    """Convert detector ratios, residuals, and frame state into Bayesian evidence."""
    evidence_list: List[Evidence] = []
    seen_targets = set()

    # 1. Evidence from detector top anomalous channels
    if detection is not None:
        for item in detection.top_channels:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                chan, z_val = item[0], float(item[1])
            elif isinstance(item, str):
                chan, z_val = item, 2.5
            else:
                continue

            target: Optional[str] = None
            loc: Optional[str] = None
            c_upper = str(chan).upper()

            if "CHT" in c_upper:
                target = "cht"
                # Locate specific cylinder if indexed
                for i in range(1, cfg.cylinder_count + 1):
                    if f"_{i}" in c_upper or f" {i}" in c_upper or c_upper.endswith(str(i)):
                        loc = f"cylinder_{i}"
                        break
            elif "EGT" in c_upper:
                target = "egt"
                for i in range(1, cfg.cylinder_count + 1):
                    if f"_{i}" in c_upper or f" {i}" in c_upper or c_upper.endswith(str(i)):
                        loc = f"cylinder_{i}"
                        break
            elif "OIL_P" in c_upper or "OIL_PRESS" in c_upper:
                target = "oil_p"
            elif "OIL_T" in c_upper:
                target = "oil_t"
            elif "MAP" in c_upper or "BOOST" in c_upper:
                target = "map_kpa"
            elif "COOLANT" in c_upper:
                target = "coolant_t"
            elif "RAIL" in c_upper:
                target = "rail_drop"
            elif "RPM" in c_upper or "OMEGA" in c_upper or "TORQUE" in c_upper:
                target = "crank_torque"
            elif "VIB" in c_upper or "TURBO" in c_upper:
                target = "turbo_whirl"

            if target and target not in seen_targets:
                seen_targets.add(target)
                evidence_list.append(Evidence(
                    detector="RESIDUAL",
                    target=target,
                    statistic=abs(z_val),
                    threshold=1.5,
                    location=loc,
                    t=float(getattr(frame, "t", 0.0))
                ))

    # 2. Physics check: CHT spread / head over-temperature
    if hasattr(frame, "cht") and frame.cht and "cht" not in seen_targets:
        max_cht = max(frame.cht)
        min_cht = min(frame.cht)
        spread = max_cht - min_cht
        limit_cht = cfg.operating_limits.get("cht_max_c", 130.0)
        if max_cht > limit_cht or spread > 28.0:
            seen_targets.add("cht")
            max_idx = frame.cht.index(max_cht) + 1
            evidence_list.append(Evidence(
                detector="PARAM_CHANGE",
                target="cht",
                statistic=max_cht,
                threshold=limit_cht,
                location=f"cylinder_{max_idx}",
                t=float(getattr(frame, "t", 0.0))
            ))

    # 3. Physics check: EGT cylinder drop (misfire symptom)
    if hasattr(frame, "egt") and frame.egt and "egt" not in seen_targets:
        max_egt = max(frame.egt)
        min_egt = min(frame.egt)
        if max_egt > 600.0 and (max_egt - min_egt) > 90.0:
            seen_targets.add("egt")
            min_idx = frame.egt.index(min_egt) + 1
            evidence_list.append(Evidence(
                detector="PARAM_CHANGE",
                target="egt",
                statistic=max_egt - min_egt,
                threshold=75.0,
                location=f"cylinder_{min_idx}",
                t=float(getattr(frame, "t", 0.0))
            ))

    # 4. Physics check: Oil pressure loss
    channels = frame.channels() if hasattr(frame, "channels") else {}
    oil_p = channels.get("oil_p_bar", channels.get("oil_p"))
    if oil_p is not None and "oil_p" not in seen_targets:
        min_oil_p = cfg.operating_limits.get("oil_p_min_bar", 1.8)
        if oil_p < min_oil_p:
            seen_targets.add("oil_p")
            evidence_list.append(Evidence(
                detector="INTEGRITY",
                target="oil_p",
                statistic=float(oil_p),
                threshold=min_oil_p,
                location="oil_circuit",
                t=float(getattr(frame, "t", 0.0))
            ))

    return evidence_list
