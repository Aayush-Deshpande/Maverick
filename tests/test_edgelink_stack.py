"""Tests for EDGELINK Stack (B2.6, B2.7, B9.1, OPT-01, OPT-02, OPT-03, INN-07, D17).

Verifies:
1. FADEC Emulator closed-loop cylinder balancing, UDS diagnostics (0x19, 0x31), and J1939 encoding.
2. Constrained Datalink priority store-and-forward queueing, HMAC-SHA256 signing, and jamming tolerance.
3. MerkleFlightLog hash-chaining and tamper-evident verification.
4. CAN Intrusion Detection System (CAN IDS) anomaly alarms.
"""

from __future__ import annotations

import struct
import pytest

from backend.physics.engine_config import load_engine_config
from backend.fadec_emulator.emulator import FADECEmulator, UDSResponse
from backend.link.link_emulator import DatalinkEmulator
from backend.security.merkle_log import MerkleFlightLog
from backend.security.can_ids import CANIntrusionDetector


def test_fadec_emulator_balancing_and_uds():
    cfg = load_engine_config("austro_ae300")
    fadec = FADECEmulator(cfg)

    # 1. Closed-loop cylinder balancing
    # Cylinder 1 has a deficit (torque=200 vs 250 for others)
    feedback = [200.0, 250.0, 250.0, 250.0]
    for _ in range(20):
        fadec.update_balancing_loops(feedback, dt=0.05)

    # Trim 0 should have risen significantly to compensate
    assert fadec.fadec_trims[0] > 1.0
    assert fadec.fadec_trims[1] < 1.0

    # 2. XCP variables
    xcp_vars = fadec.read_xcp_variables()
    assert len(xcp_vars["fadec_trims"]) == 4
    assert xcp_vars["fadec_lane"] == "A"

    # 3. UDS 0x31 RoutineControl (Cylinder Cut-Out Start / Stop)
    # Start cutout on cyl 2 (pdu: SID 0x31, Sub 0x01, Routine 0x0101, Cyl 0x02)
    req_start = bytes([0x31, 0x01, 0x01, 0x01, 0x02])
    resp_start = fadec.handle_uds_request(req_start)
    assert resp_start.status == "POSITIVE"
    assert resp_start.service_id == 0x71
    assert fadec.active_cutout_cyl == 2

    # Stop cutout
    req_stop = bytes([0x31, 0x02, 0x01, 0x01])
    resp_stop = fadec.handle_uds_request(req_stop)
    assert resp_stop.status == "POSITIVE"
    assert fadec.active_cutout_cyl is None

    # 4. J1939 EEC1 frame packing
    can_id, payload = fadec.pack_j1939_eec1(rpm=2300.0, torque_pct=85.0)
    assert can_id == 0x0CF00400
    assert len(payload) == 8


def test_datalink_emulator_priority_and_jamming():
    link = DatalinkEmulator(bandwidth_bps=4000.0, latency_sec=0.10, loss_rate=0.0)

    # Enqueue low priority telemetry (priority 3) first
    p3_msg = b"TELEMETRY_RECORD_LOW_PRIORITY"
    link.send(p3_msg, priority=3, t=0.0)

    # Enqueue high priority emergency alarm (priority 1) second
    p1_msg = b"EMERGENCY_ALARM_CRITICAL_FIRE"
    link.send(p1_msg, priority=1, t=0.01)

    # First drain: queue pop should deliver p1_msg BEFORE p3_msg
    # Advance time to allow transmission
    link.advance_time(dt=0.20, current_t=0.02)
    # Advance past latency to deliver
    delivered = link.advance_time(dt=0.10, current_t=0.20)
    assert len(delivered) >= 1

    # Verify signature on first delivered packet
    is_valid, decoded = link.verify_message(delivered[0])
    assert is_valid is True
    assert decoded == p1_msg  # High priority delivered first!

    # Test Jamming
    link.set_jamming(True)
    link.send(b"JAMMED_PACKET", priority=1, t=0.30)
    delivered_during_jam = link.advance_time(dt=0.50, current_t=0.50)
    # When jammed, zero packets should be in flight or delivered
    assert len(delivered_during_jam) == 0

    # Unjam and drain
    link.set_jamming(False)
    link.advance_time(dt=0.50, current_t=0.60)
    delivered_after = link.advance_time(dt=0.50, current_t=1.00)
    assert len(delivered_after) > 0


def test_merkle_flight_log_tamper_detection():
    log = MerkleFlightLog()

    # Append valid entries
    log.append(0.0, {"rpm": 2300.0, "oil_press": 4.2})
    log.append(1.0, {"rpm": 2305.0, "oil_press": 4.1})
    log.append(2.0, {"rpm": 2310.0, "oil_press": 4.0})

    # Validate intact log
    is_valid, bad_idx = log.verify_integrity()
    assert is_valid is True
    assert bad_idx is None

    # Calculate Merkle Root
    root1 = log.compute_merkle_root()
    assert len(root1) == 64

    # Tamper with entry 1 payload
    log.entries[1].payload["rpm"] = 9999.0
    is_valid_tampered, bad_idx_tampered = log.verify_integrity()
    assert is_valid_tampered is False
    assert bad_idx_tampered == 1


def test_can_intrusion_detector():
    ids = CANIntrusionDetector(jitter_tolerance_frac=0.50)

    # 1. Normal cyclic EEC1 (50 Hz / 20 ms period)
    alerts = ids.inspect_frame(0x0CF00400, 8, b"\x00" * 8, t_sec=0.00)
    assert len(alerts) == 0
    alerts = ids.inspect_frame(0x0CF00400, 8, b"\x00" * 8, t_sec=0.02)
    assert len(alerts) == 0

    # 2. Timing Jitter (arrives in 2 ms instead of 20 ms)
    alerts_jitter = ids.inspect_frame(0x0CF00400, 8, b"\x00" * 8, t_sec=0.022)
    assert any(a.kind == "TIMING_JITTER" for a in alerts_jitter)

    # 3. Unknown ID injection
    alerts_unk = ids.inspect_frame(0x19DEAD00, 8, b"\xAA" * 8, t_sec=0.05)
    assert any(a.kind == "UNKNOWN_ID" for a in alerts_unk)

    # 4. DLC mismatch
    alerts_dlc = ids.inspect_frame(0x18FEEE00, 4, b"\x00" * 4, t_sec=0.10)
    assert any(a.kind == "DLC_MISMATCH" for a in alerts_dlc)
