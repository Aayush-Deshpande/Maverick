"""FADEC Emulator with Cylinder Balancing, UDS Diagnostics, and XCP (B2.6, OPT-01/02, TEX-05, D09).

Implements:
1. Cylinder-balancing and drift-adaptation closed loop (masking injector faults from EGT).
2. ISO 14229 (UDS) diagnostic server:
   - 0x19: Read DTC information.
   - 0x31: RoutineControl (cylinder cut-out, rail step, SOI timing sweep).
3. ASAM MCD-1 (XCP) measurement interface exposing internal trims and adaptation tables.
4. J1939 CAN frame packing according to anumaan_fadec.dbc.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.core.frame import Frame
from backend.physics.engine_config import EngineConfig


@dataclass
class UDSResponse:
    service_id: int
    sub_function: int
    status: str       # POSITIVE | NEGATIVE
    data: bytes
    error_code: Optional[int] = None


class FADECEmulator:
    """Full-featured aero piston FADEC emulator."""

    def __init__(self, cfg: EngineConfig) -> None:
        self.cfg = cfg
        self.n_cyl = cfg.cylinder_count
        self.dtc_list: List[str] = []

        # Internal FADEC control variables (XCP-accessible)
        self.fadec_trims = [0.0] * self.n_cyl     # % cylinder balancing correction (-25% to +25%)
        self.fadec_adapts = [0.0] * self.n_cyl    # % long-term drift adaptation (-20% to +20%)
        self.active_lane = "A"                   # Dual-lane redundancy ("A" | "B")
        self.active_cutout_cyl: Optional[int] = None

    def update_balancing_loops(self, per_cyl_torque_feedback: List[float], dt: float = 0.05) -> None:
        """Cylinder-balancing closed loop: adjusts trims to equalize per-cylinder work.
        This reproduces FADEC masking: when cylinder i has an injector deficit,
        trim[i] automatically increases to compensate, keeping gross EGT/RPM normal.
        """
        if len(per_cyl_torque_feedback) != self.n_cyl:
            return

        mean_tq = float(np.mean(per_cyl_torque_feedback)) + 1e-9
        for i in range(self.n_cyl):
            tq_err = (mean_tq - per_cyl_torque_feedback[i]) / mean_tq
            # Proportional-integral trim adjustment
            self.fadec_trims[i] = float(np.clip(self.fadec_trims[i] + 15.0 * tq_err * dt, -25.0, 25.0))
            # Slow drift adaptation
            self.fadec_adapts[i] = float(np.clip(self.fadec_adapts[i] + 0.1 * tq_err * dt, -20.0, 20.0))

    def handle_uds_request(self, pdu: bytes) -> UDSResponse:
        """Process ISO 14229 UDS diagnostic request."""
        if len(pdu) < 1:
            return UDSResponse(0x00, 0x00, "NEGATIVE", b"", error_code=0x13)  # Incorrect message length

        sid = pdu[0]

        # 0x19: ReadDTCInformation
        if sid == 0x19:
            dtc_bytes = b"".join(d.encode("ascii") for d in self.dtc_list)
            return UDSResponse(0x59, pdu[1] if len(pdu) > 1 else 0x02, "POSITIVE", dtc_bytes)

        # 0x31: RoutineControl (0x01 = StartRoutine, 0x02 = StopRoutine)
        elif sid == 0x31:
            if len(pdu) < 4:
                return UDSResponse(0x7F, sid, "NEGATIVE", b"", error_code=0x13)
            sub_fn = pdu[1]
            routine_id = struct.unpack(">H", pdu[2:4])[0]

            if routine_id == 0x0101:  # Routine: Cylinder Cut-Out
                target_cyl = pdu[4] if len(pdu) > 4 else 1
                if sub_fn == 0x01:  # Start
                    self.active_cutout_cyl = target_cyl
                    return UDSResponse(0x71, sub_fn, "POSITIVE", struct.pack(">HB", routine_id, target_cyl))
                elif sub_fn == 0x02:  # Stop
                    self.active_cutout_cyl = None
                    return UDSResponse(0x71, sub_fn, "POSITIVE", struct.pack(">H", routine_id))

            elif routine_id == 0x0102:  # Routine: Rail Pressure Step
                return UDSResponse(0x71, sub_fn, "POSITIVE", struct.pack(">H", routine_id))

            elif routine_id == 0x0103:  # Routine: SOI Timing Sweep
                return UDSResponse(0x71, sub_fn, "POSITIVE", struct.pack(">H", routine_id))

            return UDSResponse(0x7F, sid, "NEGATIVE", b"", error_code=0x31)  # Request out of range

        return UDSResponse(0x7F, sid, "NEGATIVE", b"", error_code=0x11)  # Service not supported

    def read_xcp_variables(self) -> Dict[str, Any]:
        """Expose internal FADEC variables over ASAM MCD-1 XCP."""
        return {
            "fadec_lane": self.active_lane,
            "fadec_trims": list(self.fadec_trims),
            "fadec_adapts": list(self.fadec_adapts),
            "active_cutout": self.active_cutout_cyl,
        }

    def pack_j1939_eec1(self, rpm: float, torque_pct: float) -> Tuple[int, bytes]:
        """Pack J1939 EEC1 message (PGN 61444 / CAN ID 0x0CF00400)."""
        can_id = 0x0CF00400
        # Engine speed: 0.125 rpm/bit, 16 bits little-endian (bytes 3-4)
        raw_speed = min(65535, max(0, int(rpm / 0.125)))
        # Actual engine percent torque: 1 %/bit, offset -125 (byte 2)
        raw_tq = min(250, max(0, int(torque_pct + 125.0)))

        data = bytearray(8)
        data[0] = 0xF0  # Torque mode
        data[2] = raw_tq
        data[3] = raw_speed & 0xFF
        data[4] = (raw_speed >> 8) & 0xFF
        return can_id, bytes(data)
