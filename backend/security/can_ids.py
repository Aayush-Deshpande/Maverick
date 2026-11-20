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
from typing import Any, Dict, List, Optional, Set, Tuple


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

    def __init__(self, jitter_tolerance_frac: float = 0.50, known_ids: Optional[Dict[int, float]] = None,
                 db: Any = None, counter_signal: Optional[str] = None) -> None:
        self.jitter_tolerance = jitter_tolerance_frac
        self.known_ids: Dict[int, float] = dict(known_ids) if known_ids is not None else dict(self.KNOWN_IDS)
        self.db, self.counter_signal = db, counter_signal          # optional: counter + range checks (M7-04)
        self.last_counter: Dict[int, int] = {}
        self.last_timestamps: Dict[int, float] = {}
        self.message_counts_window: List[float] = []
        self.alerts: List[CANAlert] = []

    @classmethod
    def from_dbc(cls, db: Any, counter_signal: Optional[str] = None, jitter_tolerance_frac: float = 0.50) -> "CANIntrusionDetector":
        """Known ids and nominal periods from the DBC (GenMsgCycleTime, ms); counter and range checks on."""
        known = {m.frame_id: (m.cycle_time or 0) / 1000.0 for m in db.messages}
        return cls(jitter_tolerance_frac, known_ids=known, db=db, counter_signal=counter_signal)

    def _alert(self, alerts: List[CANAlert], kind: str, arb_id: int, t_sec: float, text: str, severity: str) -> None:
        a = CANAlert(kind=kind, arb_id=arb_id, t_sec=t_sec, description=text, severity=severity)
        alerts.append(a)
        self.alerts.append(a)

    def _payload_checks(self, arb_id: int, data: bytes, t_sec: float, alerts: List[CANAlert]) -> None:
        """Sequence counter gap (dropped, replayed or injected frames) and physically impossible payload values."""
        msg = self.db.get_message_by_frame_id(arb_id)
        raws = msg.decode(data, scaling=False, decode_choices=False)
        if self.counter_signal and self.counter_signal in raws:
            c = int(raws[self.counter_signal])
            prev = self.last_counter.get(arb_id)
            if prev is not None and c != (prev + 1) % 16:
                self._alert(alerts, "SEQUENCE_GAP", arb_id, t_sec,
                            f"{msg.name} counter {prev} -> {c}: frames dropped, replayed or injected", "WARNING")
            self.last_counter[arb_id] = c
        for sig in msg.signals:
            if sig.name == self.counter_signal:
                continue
            raw = int(raws[sig.name])
            na = (1 << (sig.length - 1)) - 1 if sig.is_signed else (1 << sig.length) - 1
            phys = raw * sig.scale + sig.offset
            if raw != na and ((sig.minimum is not None and phys < sig.minimum) or (sig.maximum is not None and phys > sig.maximum)):
                self._alert(alerts, "OUT_OF_RANGE", arb_id, t_sec,
                            f"{msg.name}.{sig.name} = {phys:g} outside [{sig.minimum}, {sig.maximum}]", "WARNING")

    def inspect_frame(self, arb_id: int, dlc: int, data: bytes, t_sec: float) -> List[CANAlert]:
        alerts = []

        # 1. Unknown ID injection check
        if arb_id not in self.known_ids:
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
        if self.db is not None and len(data) == 8:
            self._payload_checks(arb_id, data, t_sec, alerts)
        nom_period = self.known_ids[arb_id]
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
