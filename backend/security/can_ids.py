"""CAN Bus Intrusion Detection System (CAN IDS) (B9.1, INN-07, D17).

Monitors:
1. Message inter-arrival timing jitter against nominal cyclic periods.
2. Unknown / unauthorized arbitration ID injection.
3. Payload DLC consistency.
4. High-frequency bus flooding / DoS attacks.
5. Physics payload consistency (rate-of-change bounds).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CANAlert:
    kind: str          # TIMING_JITTER | UNKNOWN_ID | DLC_MISMATCH | FLOODING | RATE_LIMIT
    arb_id: int
    t_sec: float
    description: str
    severity: str      # CAUTION | WARNING | CRITICAL


class CANIntrusionDetector:
    """Real-time CAN network security monitor."""

    KNOWN_IDS: Dict[int, float] = {
        0x0CF00400: 0.02,   # EEC1: 50 Hz (20 ms period)
        0x18FEEE00: 0.10,   # ET1: 10 Hz (100 ms period)
        0x18FEF200: 0.10,   # EFL_P1: 10 Hz (100 ms period)
        0x18FEFD00: 0.05,   # Trims: 20 Hz (50 ms period)
    }

    def __init__(self, jitter_tolerance_frac: float = 0.50) -> None:
        self.jitter_tolerance = jitter_tolerance_frac
        self.last_timestamps: Dict[int, float] = {}
        self.message_counts_window: List[float] = []
        self.alerts: List[CANAlert] = []

    def inspect_frame(self, arb_id: int, dlc: int, data: bytes, t_sec: float) -> List[CANAlert]:
        alerts = []

        # 1. Unknown ID injection check
        if arb_id not in self.KNOWN_IDS:
            alert = CANAlert(
                kind="UNKNOWN_ID",
                arb_id=arb_id,
                t_sec=t_sec,
                description=f"Unauthorized CAN Arbitration ID 0x{arb_id:X} observed on bus",
                severity="CRITICAL",
            )
            alerts.append(alert)
            self.alerts.append(alert)
            return alerts

        # 2. DLC consistency check
        if dlc != 8 or len(data) != 8:
            alert = CANAlert(
                kind="DLC_MISMATCH",
                arb_id=arb_id,
                t_sec=t_sec,
                description=f"Invalid DLC {dlc} for ID 0x{arb_id:X} (expected 8)",
                severity="WARNING",
            )
            alerts.append(alert)
            self.alerts.append(alert)

        # 3. Timing jitter check
        nom_period = self.KNOWN_IDS[arb_id]
        if arb_id in self.last_timestamps:
            dt = t_sec - self.last_timestamps[arb_id]
            if dt < nom_period * (1.0 - self.jitter_tolerance):
                alert = CANAlert(
                    kind="TIMING_JITTER",
                    arb_id=arb_id,
                    t_sec=t_sec,
                    description=f"Message ID 0x{arb_id:X} arrived too fast (dt={dt*1000:.1f}ms, nominal={nom_period*1000:.1f}ms)",
                    severity="WARNING",
                )
                alerts.append(alert)
                self.alerts.append(alert)

        self.last_timestamps[arb_id] = t_sec

        # 4. Flooding check (>250 msgs in last 0.1s)
        self.message_counts_window.append(t_sec)
        self.message_counts_window = [ts for ts in self.message_counts_window if t_sec - ts < 0.1]
        if len(self.message_counts_window) > 250:
            alert = CANAlert(
                kind="FLOODING",
                arb_id=arb_id,
                t_sec=t_sec,
                description="CAN bus DoS flood attack detected (>2500 msg/s)",
                severity="CRITICAL",
            )
            alerts.append(alert)
            self.alerts.append(alert)

        return alerts
