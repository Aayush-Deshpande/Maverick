"""
Sensor Sanity & Plausibility Validator
DRDO / iDEX Problem Statement ID: 26054

Implements the sensor discrimination logic defined in doc02 §4:

    Physical Thermodynamic Ramp        vs     Electrical Sensor Artifact
    ──────────────────────────────────────────────────────────────────────
    dT/dt ≤ 1.5°C/s                           dT/dt > 10°C/s (unphysical)
    Correlated with adjacent sensors           Isolated single-channel spike
    Natural analog ripple ±0.2°C              Zero variance = frozen ADC

In military aviation a sensor failure (thermocouple open-circuit) must NEVER
be misdiagnosed as mechanical engine destruction.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import math

from .thermo_model import ResidualVector


# ──────────────────────────────────────────────────────────────────────────────
# Rate-of-change limits (doc02 §4, Rotax 912 iS thermal response data)
# Format: channel_name → (max_physical_rate_per_sec, flag_threshold_per_frame_50ms)
# ──────────────────────────────────────────────────────────────────────────────
RATE_LIMITS: Dict[str, Tuple[float, float]] = {
    # Thermal channels — °C/s
    "CHT_1":         (1.5,  10.0),   # max physical 1.5°C/s; sensor fault: >10°C in 50ms
    "CHT_2":         (1.5,  10.0),
    "CHT_3":         (1.5,  10.0),
    "CHT_4":         (1.5,  10.0),
    "EGT_1":         (8.0,  50.0),   # EGT responds faster to combustion changes
    "EGT_2":         (8.0,  50.0),
    "EGT_3":         (8.0,  50.0),
    "EGT_4":         (8.0,  50.0),
    "OIL_TEMP":      (2.0,  15.0),
    # Mechanical / fluid channels
    "OIL_PRESS":     (0.8,   4.0),   # bar/s; pump transient max 0.8 bar/s
    "FUEL_FLOW":     (5.0,  20.0),   # L/hr/s
    "MAP":           (5.0,  25.0),   # kPa/s — throttle transient
    "VIB_GEARBOX_RMS": (2.0, 10.0), # mm/s per second
    # Electrical channels — V/s
    "BUS_VOLTAGE":   (0.5,   3.0),   # max load switching 0.5V/s; fault: >3V jump
}

# Noise floor: if variance of last N readings is below this → frozen ADC suspected.
# Each floor must sit safely BELOW the true sample variance produced by that channel's
# calibrated sensor noise sigma (doc §2 "Sensor Noise Distributions"), so a healthy sensor
# never trips it: OIL_PRESS sigma=0.03 bar -> true variance ~0.0009 bar^2. The floor used to
# be 0.001 (ABOVE that true variance), so a perfectly nominal oil pressure sensor's rolling
# variance was, on average, already below the "frozen" threshold — a chronic false FROZEN_ADC
# alarm on a healthy channel, exactly what SensorSanityValidator exists to prevent.
NOISE_FLOOR_VARIANCE: Dict[str, float] = {
    "CHT_1": 0.01, "CHT_2": 0.01, "CHT_3": 0.01, "CHT_4": 0.01,
    "EGT_1": 0.25, "EGT_2": 0.25, "EGT_3": 0.25, "EGT_4": 0.25,
    "OIL_PRESS": 0.0002, "OIL_TEMP": 0.01,
    "BUS_VOLTAGE": 0.0001, "VIB_GEARBOX_RMS": 0.0001,
}

# Minimum frames needed before frozen-ADC check is valid
FREEZE_CHECK_MIN_FRAMES = 100  # 5 seconds at 20 Hz


@dataclass
class ChannelSanityStatus:
    """Per-channel sanity result."""
    channel: str
    valid: bool
    fault_type: Optional[str]       # "RATE_SPIKE" | "FROZEN_ADC" | None
    measured_rate: float            # abs(delta/dt) this frame
    max_physical_rate: float        # limit from RATE_LIMITS
    variance_recent: float          # variance of last N frames
    detail: str                     # human-readable explanation


@dataclass
class SanityReport:
    """
    Output of SensorSanityValidator.validate().
    Consumed by the detection pipeline before any anomaly scoring.
    """
    all_sensors_valid: bool
    drift_detected: bool                            # doc02 §3 JSON field
    failed_channels: List[str] = field(default_factory=list)
    channel_statuses: Dict[str, ChannelSanityStatus] = field(default_factory=dict)
    suppressed_anomaly: bool = False                # True if sensor failure masks real reading
    advisory: str = ""

    def to_dict(self) -> dict:
        return {
            "all_sensors_valid": self.all_sensors_valid,
            "drift_detected": self.drift_detected,
            "failed_channels": self.failed_channels,
            "suppressed_anomaly": self.suppressed_anomaly,
            "advisory": self.advisory,
        }


class SensorSanityValidator:
    """
    Stateful per-mission sensor validator.

    Call validate() once per telemetry frame (at 20 Hz).
    Maintains rolling history buffers per channel for frozen-ADC detection.
    """

    MONITORED_CHANNELS = list(RATE_LIMITS.keys())

    def __init__(self, history_len: int = 200):
        """
        Args:
            history_len: Number of recent frames to keep for variance analysis.
                         200 frames = 10 seconds at 20 Hz.
        """
        self._history: Dict[str, List[float]] = {ch: [] for ch in self.MONITORED_CHANNELS}
        self._history_len = history_len
        self._prev_values: Dict[str, Optional[float]] = {ch: None for ch in self.MONITORED_CHANNELS}

    def _extract(self, state: object) -> Dict[str, float]:
        """Pull monitored channel values from an EnginePhysicalState object."""
        mapping = {
            "CHT_1": state.CHT_1, "CHT_2": state.CHT_2,
            "CHT_3": state.CHT_3, "CHT_4": state.CHT_4,
            "EGT_1": state.EGT_1, "EGT_2": state.EGT_2,
            "EGT_3": state.EGT_3, "EGT_4": state.EGT_4,
            "OIL_PRESS": state.OIL_PRESS, "OIL_TEMP": state.OIL_TEMP,
            "FUEL_FLOW": state.FUEL_FLOW, "MAP": state.MAP,
            "VIB_GEARBOX_RMS": state.VIB_GEARBOX_RMS,
            "BUS_VOLTAGE": state.BUS_VOLTAGE,
        }
        return mapping

    def _variance(self, values: List[float]) -> float:
        if len(values) < 2:
            return float("inf")
        n = len(values)
        mean = sum(values) / n
        return sum((v - mean) ** 2 for v in values) / n

    def validate(self, curr_state: object, dt_sec: float) -> SanityReport:
        """
        Validates all monitored sensor channels for the current telemetry frame.

        Args:
            curr_state: EnginePhysicalState (current frame)
            dt_sec:     Time elapsed since previous frame (seconds)

        Returns:
            SanityReport with per-channel validity and aggregate status.
        """
        curr_values = self._extract(curr_state)
        statuses: Dict[str, ChannelSanityStatus] = {}
        failed: List[str] = []
        dt = max(dt_sec, 1e-6)  # guard against zero-division

        for ch in self.MONITORED_CHANNELS:
            curr_val = curr_values[ch]
            prev_val = self._prev_values[ch]
            hist = self._history[ch]

            # Update history buffer
            hist.append(curr_val)
            if len(hist) > self._history_len:
                hist.pop(0)

            max_phys_rate, flag_threshold = RATE_LIMITS[ch]

            # ── CHECK 1: Rate-of-change spike (instantaneous sensor artifact) ──
            rate_per_sec = 0.0
            if prev_val is not None:
                delta = abs(curr_val - prev_val)
                rate_per_sec = delta / dt
                if delta > flag_threshold:
                    # Unphysical jump in a single frame → sensor artifact
                    statuses[ch] = ChannelSanityStatus(
                        channel=ch, valid=False,
                        fault_type="RATE_SPIKE",
                        measured_rate=rate_per_sec,
                        max_physical_rate=max_phys_rate,
                        variance_recent=self._variance(hist),
                        detail=(
                            f"{ch} jumped {delta:.2f} units in {dt*1000:.0f}ms "
                            f"(max physical: {flag_threshold:.1f} units/frame). "
                            f"Likely thermocouple open-circuit or ADC glitch."
                        )
                    )
                    failed.append(ch)
                    self._prev_values[ch] = curr_val
                    continue

            # ── CHECK 2: Frozen ADC / flat-line detection ──
            variance = self._variance(hist)
            freeze_floor = NOISE_FLOOR_VARIANCE.get(ch, 0.001)
            if len(hist) >= FREEZE_CHECK_MIN_FRAMES and variance < freeze_floor:
                statuses[ch] = ChannelSanityStatus(
                    channel=ch, valid=False,
                    fault_type="FROZEN_ADC",
                    measured_rate=rate_per_sec,
                    max_physical_rate=max_phys_rate,
                    variance_recent=variance,
                    detail=(
                        f"{ch} variance={variance:.6f} over last {len(hist)} frames "
                        f"(floor={freeze_floor:.4f}). Suspected frozen ADC buffer "
                        f"or disconnected transducer. Real sensors have ≥±0.2°C ripple."
                    )
                )
                failed.append(ch)
                self._prev_values[ch] = curr_val
                continue

            # ── PASSED both checks ──
            statuses[ch] = ChannelSanityStatus(
                channel=ch, valid=True,
                fault_type=None,
                measured_rate=rate_per_sec,
                max_physical_rate=max_phys_rate,
                variance_recent=variance,
                detail="OK"
            )
            self._prev_values[ch] = curr_val

        # ── Cross-sensor correlation check for CHT spikes ──
        # A real CHT_2 rise should correlate with slight oil_temp and EGT adjacency.
        # An isolated CHT_2 spike with perfectly flat neighbours is a sensor artifact.
        # (Only applied when CHT_2 is showing a large positive rate but passed CHECK 1)
        if "CHT_2" in statuses and statuses["CHT_2"].valid:
            cht2_rate = statuses["CHT_2"].measured_rate
            cht2_max_phys, _ = RATE_LIMITS["CHT_2"]
            # Only trigger cross-sensor check for rates clearly above physical max
            # (must be > 1.1× max to avoid flagging legitimate fast thermal ramps)
            if cht2_rate > cht2_max_phys * 1.1:
                oil_rate  = statuses.get("OIL_TEMP", ChannelSanityStatus("OIL_TEMP", True, None, 0, 0, 0, "")).measured_rate
                egt2_rate = statuses.get("EGT_2",    ChannelSanityStatus("EGT_2",    True, None, 0, 0, 0, "")).measured_rate
                # Real CHT event: neighbours must also show some correlated movement
                # If CHT_2 spikes but oil_temp and EGT_2 are completely flat → artifact
                if oil_rate < 0.02 and egt2_rate < 0.2:
                    statuses["CHT_2"].valid = False
                    statuses["CHT_2"].fault_type = "ISOLATED_SPIKE"
                    statuses["CHT_2"].detail = (
                        f"CHT_2 rate {cht2_rate:.2f}°C/s (> {cht2_max_phys*1.1:.1f}°C/s limit) "
                        f"but OIL_TEMP rate {oil_rate:.3f}°C/s and EGT_2 rate {egt2_rate:.2f}°C/s. "
                        f"Real thermal event would show cross-sensor correlation. "
                        f"Suspected isolated thermocouple artifact."
                    )
                    if "CHT_2" not in failed:
                        failed.append("CHT_2")

        # ── CHECK 3: Statistical Sensor Drift Detection (FDP-06 / PS-26054) ──
        # Detects gradual calibration loss / transducer resistance drift over rolling window
        drift_detected = False
        DRIFT_LIMITS = {
            "CHT_1": 4.0, "CHT_2": 4.0, "CHT_3": 4.0, "CHT_4": 4.0,
            "EGT_1": 20.0, "EGT_2": 20.0, "EGT_3": 20.0, "EGT_4": 20.0,
            "OIL_PRESS": 0.35, "OIL_TEMP": 4.0, "FUEL_FLOW": 2.0,
            "MAP": 3.5, "BUS_VOLTAGE": 0.5
        }
        for ch, limit in DRIFT_LIMITS.items():
            hist = self._history[ch]
            if len(hist) >= 30 and ch not in failed:
                # Compare first quarter to fourth quarter of history window
                q_len = max(5, len(hist) // 4)
                mean_old = sum(hist[:q_len]) / q_len
                mean_new = sum(hist[-q_len:]) / q_len
                shift = mean_new - mean_old
                
                # If persistent single-channel shift exceeds drift threshold
                if abs(shift) > limit:
                    # Verify if it's isolated (uncorroborated by adjacent engine indicators)
                    is_isolated = True
                    if ch.startswith("CHT_"):
                        # Check if other CHTs shifted similarly
                        other_chts = [c for c in ["CHT_1", "CHT_2", "CHT_3", "CHT_4"] if c != ch]
                        other_shifts = [
                            abs(sum(self._history[c][-q_len:]) / q_len - sum(self._history[c][:q_len]) / q_len)
                            for c in other_chts if len(self._history[c]) >= 30
                        ]
                        if other_shifts and max(other_shifts) > limit * 0.6:
                            is_isolated = False # Engine-wide thermal shift, not transducer drift
                    
                    if is_isolated:
                        statuses[ch] = ChannelSanityStatus(
                            channel=ch, valid=False,
                            fault_type="SENSOR_DRIFT",
                            measured_rate=abs(shift) / (len(hist) * dt),
                            max_physical_rate=RATE_LIMITS[ch][0],
                            variance_recent=self._variance(hist),
                            detail=(
                                f"{ch} drifted {shift:+.2f} units across {len(hist)} frames "
                                f"(threshold: ±{limit:.1f}). Isolated transducer calibration bias."
                            )
                        )
                        failed.append(ch)
                        drift_detected = True

        all_valid = len(failed) == 0

        # Build advisory
        if not all_valid:
            fault_types = list(set(statuses[ch].fault_type for ch in failed if statuses[ch].fault_type))
            advisory = (
                f"SENSOR ALERT [{'/'.join(fault_types)}]: {len(failed)} channel(s) quarantined: "
                f"{', '.join(failed)}. Residual shielding active to isolate engine twin."
            )
        else:
            advisory = "All sensors valid."

        return SanityReport(
            all_sensors_valid=all_valid,
            drift_detected=drift_detected,
            failed_channels=failed,
            channel_statuses=statuses,
            suppressed_anomaly=not all_valid,
            advisory=advisory,
        )

    def reset(self) -> None:
        """Reset state for a new mission/sortie."""
        for ch in self.MONITORED_CHANNELS:
            self._history[ch].clear()
            self._prev_values[ch] = None


def apply_residual_shielding(
    residuals: ResidualVector,
    quarantined_channels: List[str]
) -> ResidualVector:
    """
    Gagguverse/F14 Residual Shielding:
    Zeroes residuals of quarantined (failed or drifting) sensors so corrupted
    measurements cannot contaminate the composite anomaly score or trigger false engine alarms.
    """
    if not quarantined_channels:
        return residuals

    res_dict = residuals.to_dict()
    channel_map = {
        "CHT_1": "d_CHT_1", "CHT_2": "d_CHT_2", "CHT_3": "d_CHT_3", "CHT_4": "d_CHT_4",
        "EGT_1": "d_EGT_1", "EGT_2": "d_EGT_2", "EGT_3": "d_EGT_3", "EGT_4": "d_EGT_4",
        "OIL_PRESS": "d_OIL_PRESS", "OIL_TEMP": "d_OIL_TEMP", "FUEL_FLOW": "d_FUEL_FLOW",
        "MAP": "d_MAP", "VIB_GEARBOX_RMS": "d_VIB_RMS", "BUS_VOLTAGE": "d_BUS_VOLTAGE",
    }

    for ch in quarantined_channels:
        field_name = channel_map.get(ch)
        if field_name and field_name in res_dict:
            res_dict[field_name] = 0.0

    # Recompute z-scores without quarantined noise
    z_scores = [
        abs(res_dict["d_CHT_1"]) / 4.0,
        abs(res_dict["d_CHT_2"]) / 4.0,
        abs(res_dict["d_CHT_3"]) / 4.0,
        abs(res_dict["d_CHT_4"]) / 4.0,
        abs(res_dict["d_EGT_1"]) / 15.0,
        abs(res_dict["d_EGT_2"]) / 15.0,
        abs(res_dict["d_EGT_3"]) / 15.0,
        abs(res_dict["d_EGT_4"]) / 15.0,
        abs(res_dict["d_OIL_PRESS"]) / 0.3,
        abs(res_dict["d_OIL_TEMP"]) / 5.0,
        abs(res_dict["d_FUEL_FLOW"]) / 1.5,
        abs(res_dict["d_MAP"]) / 3.0,
        abs(res_dict["d_VIB_RMS"]) / 0.25,
        abs(res_dict["d_BUS_VOLTAGE"]) / 0.35,
    ]
    rms_z = math.sqrt(sum(z ** 2 for z in z_scores) / len(z_scores))
    max_z = max(z_scores)
    composite_z = 0.65 * max_z + 0.35 * rms_z
    anomaly_score = round(1.0 - math.exp(-0.45 * composite_z), 4)
    is_anomaly = anomaly_score >= 0.65

    res_dict["anomaly_score"] = anomaly_score
    res_dict["is_anomaly"] = is_anomaly

    return ResidualVector(**res_dict)
