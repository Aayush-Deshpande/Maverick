"""Engine telemetry over a CAN bus (cards M7-01/M7-02, P Part 4 M7, T-CAN-1).

A Frame is encoded into the ANUMAAN v2 messages (configs/can/anumaan_engine_v2.dbc, channel map in
configs/can/channel_map.json), sent on a python-can bus (interface "virtual" on Windows/CI, "socketcan" with vcan0/can0
on Linux), received, checked by the CAN intrusion detector, and decoded back into a Frame. So the twin can run on what
actually crossed the bus: values are quantised to each signal's resolution, a reading the engine does not measure is
sent as NOT AVAILABLE (all-ones raw, J1939 convention) and comes back as null, never as a number.

Libraries (D39, checked 20 Nov 2026): python-can 4.6.1 (can.Bus(interface=..., channel=...), Bus.send/recv,
can.Message(arbitration_id, is_extended_id, data)), cantools 45.2.0 (database.load_file, Message.signals,
Message.cycle_time, Signal.start/length/scale/offset/is_signed, encode/decode with scaling=False).
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.security.can_ids import CANAlert, CANIntrusionDetector

ROOT = Path(__file__).resolve().parents[2]
CHANNEL_MAP = ROOT / "configs" / "can" / "channel_map.json"


def _get(frame: Any, path: str) -> Optional[float]:
    name, _, key = path.partition(".")
    value = getattr(frame, name, None)
    if not key:
        return value
    if isinstance(value, dict):
        return value.get(key)
    idx = int(key)
    return value[idx] if isinstance(value, list) and idx < len(value) else None


def _set(frame: Any, path: str, value: Optional[float]) -> None:
    name, _, key = path.partition(".")
    if not key:
        setattr(frame, name, value)
        return
    cur = getattr(frame, name)
    if isinstance(cur, dict):
        if value is None:
            cur.pop(key, None)
        else:
            cur[key] = value
        return
    idx = int(key)
    if idx < len(cur):
        cur[idx] = value


@dataclass
class _Sig:
    path: str
    message: Any
    signal: Any

    @property
    def not_available(self) -> int:
        return (1 << (self.signal.length - 1)) - 1 if self.signal.is_signed else (1 << self.signal.length) - 1

    def raw(self, value: Optional[float]) -> int:
        if value is None:
            return self.not_available
        r = round((value - self.signal.offset) / self.signal.scale)
        lo = -(1 << (self.signal.length - 1)) if self.signal.is_signed else 0
        return max(lo, min(self.not_available - 1, r))        # saturate below the NOT AVAILABLE code

    def physical(self, raw: int) -> Optional[float]:
        return None if raw == self.not_available else raw * self.signal.scale + self.signal.offset


class CanLink:
    def __init__(self, channel: str, interface: str = "virtual", map_path: Path = CHANNEL_MAP) -> None:
        import can
        import cantools
        cfg = json.loads(map_path.read_text(encoding="utf-8"))
        self.db = cantools.database.load_file(str(ROOT / cfg["dbc"]))
        self.counter_name = cfg["counter_signal"]
        self.sigs = [_Sig(path, self.db.get_message_by_name(m), self.db.get_message_by_name(m).get_signal_by_name(s))
                     for path, (m, s) in cfg["signals"].items()]
        self.counters: Dict[str, int] = {m.name: 0 for m in self.db.messages}
        self.tx = can.Bus(interface=interface, channel=channel, receive_own_messages=False)
        self.rx = can.Bus(interface=interface, channel=channel, receive_own_messages=False)
        self.ids = CANIntrusionDetector.from_dbc(self.db, self.counter_name)
        self.alerts: List[CANAlert] = []
        self.bytes_sent = 0
        self.recent_frames: List[Dict[str, Any]] = []

    def encode(self, frame: Any) -> List[Tuple[Any, bytes]]:
        out = []
        for msg in self.db.messages:
            raw = {s.signal.name: s.raw(_get(frame, s.path)) for s in self.sigs if s.message is msg}
            raw[self.counter_name] = self.counters[msg.name]
            self.counters[msg.name] = (self.counters[msg.name] + 1) % 16
            out.append((msg, msg.encode(raw, scaling=False, strict=False)))
        return out

    def roundtrip(self, frame: Any) -> Any:
        """Send the frame's messages on the bus, receive them, and return the frame rebuilt from what arrived."""
        import can
        encoded = self.encode(frame)
        recent = []
        for msg, data in encoded:
            self.tx.send(can.Message(arbitration_id=msg.frame_id, is_extended_id=msg.is_extended_frame, data=data,
                                     timestamp=float(frame.t)))
            self.bytes_sent += len(data)
            recent.append({
                "name": msg.name,
                "arbitration_id": f"0x{msg.frame_id:08X}",
                "cycle_time_ms": msg.cycle_time or 50,
                "dlc": len(data),
                "data_hex": data.hex().upper(),
                "counter": (self.counters[msg.name] - 1) % 16
            })
        self.recent_frames = recent
        received: Dict[int, bytes] = {}
        for _ in range(len(self.db.messages)):
            m = self.rx.recv(timeout=1.0)
            if m is None:
                break
            self.alerts += self.ids.inspect_frame(m.arbitration_id, m.dlc, bytes(m.data), float(frame.t))
            received[m.arbitration_id] = bytes(m.data)
        out = copy.deepcopy(frame)
        out.source = "CAN"                                      # what the twin sees came off the bus
        for s in self.sigs:
            data = received.get(s.message.frame_id)
            raws = s.message.decode(data, scaling=False, decode_choices=False) if data is not None else None
            _set(out, s.path, s.physical(int(raws[s.signal.name])) if raws is not None else None)
        return out

    def inject_spoof(self, kind: str = "UNKNOWN_ID", t_sec: float = 0.0) -> List[CANAlert]:
        """Inject an anomalous or rogue CAN frame on the bus to test CAN IDS in real time (M7-04)."""
        import can
        new_alerts: List[CANAlert] = []
        if kind == "UNKNOWN_ID":
            fake_id = 0x18FF99FF  # Rogue 29-bit sender ID not in DBC
            data = bytes([0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0x00, 0x00, 0x00])
            self.tx.send(can.Message(arbitration_id=fake_id, is_extended_id=True, data=data, timestamp=t_sec))
            m = self.rx.recv(timeout=0.2)
            if m is not None:
                new_alerts = self.ids.inspect_frame(m.arbitration_id, m.dlc, bytes(m.data), t_sec)
        elif kind == "SEQUENCE_GAP":
            msg = self.db.get_message_by_name("ANU_SPEED")
            curr_c = self.counters[msg.name]
            skipped = msg.encode({"EngineSpeed": 5000, "PropSpeed": 2500, "ManifoldPressure": 100, "Throttle": 80,
                                  self.counter_name: (curr_c + 5) % 16}, scaling=False)
            self.tx.send(can.Message(arbitration_id=msg.frame_id, is_extended_id=msg.is_extended_frame, data=skipped, timestamp=t_sec))
            m = self.rx.recv(timeout=0.2)
            if m is not None:
                new_alerts = self.ids.inspect_frame(m.arbitration_id, m.dlc, bytes(m.data), t_sec)
        elif kind == "OUT_OF_RANGE":
            msg = self.db.get_message_by_name("ANU_FLUID")
            curr_c = self.counters[msg.name]
            impossible = msg.encode({"OilPressure": 300, "OilTemperature": 1300, "CoolantTemperature": 4000, "FuelFlow": 1742,
                                     self.counter_name: curr_c}, scaling=False, strict=False)
            self.tx.send(can.Message(arbitration_id=msg.frame_id, is_extended_id=msg.is_extended_frame, data=impossible, timestamp=t_sec))
            m = self.rx.recv(timeout=0.2)
            if m is not None:
                new_alerts = self.ids.inspect_frame(m.arbitration_id, m.dlc, bytes(m.data), t_sec)
        self.alerts += new_alerts
        return new_alerts

    def close(self) -> None:
        self.tx.shutdown()
        self.rx.shutdown()
