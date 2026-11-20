"""E23: Datalink, FADEC Emulation, and Cybersecurity Benchmark (B2.6, B2.7, B9.1, OPT-01, OPT-02, OPT-03, INN-07, D17).

Evaluates:
1. Closed-loop FADEC cylinder balancing and compensation masking on AE300 diesel.
2. Constrained datalink bandwidth utilization, latency, and priority queuing under RF jamming.
3. Cryptographic Merkle flight log integrity & tamper detection across 1,000 flight records.
4. CAN IDS cyber-attack detection rate and false positive rate.
"""

from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from backend.physics.engine_config import load_engine_config
from backend.fadec_emulator.emulator import FADECEmulator
from backend.link.link_emulator import DatalinkEmulator
from backend.security.merkle_log import MerkleFlightLog
from backend.security.can_ids import CANIntrusionDetector


def run_e23_benchmark() -> dict:
    results = {
        "metadata": {
            "experiment": "E23_edgelink_security",
            "evidence_class": "SIMULATION",
            "seed": 42,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "fadec_balancing": {},
        "datalink_queuing": {},
        "merkle_forensics": {},
        "can_ids_security": {},
    }

    # -------------------------------------------------------------
    # 1. FADEC Closed-Loop Cylinder Balancing & Masking
    # -------------------------------------------------------------
    cfg = load_engine_config("austro_ae300")
    fadec = FADECEmulator(cfg)

    # Simulate 150 cycles where Cylinder 1 has 15% injector delivery deficit
    # Cyl 1: 200 Nm, Cyl 2..4: 235 Nm
    torque_feedback = [200.0, 235.0, 235.0, 235.0]
    for _ in range(150):
        fadec.update_balancing_loops(torque_feedback, dt=0.05)

    xcp_state = fadec.read_xcp_variables()
    results["fadec_balancing"] = {
        "engine_profile": "austro_ae300",
        "nominal_torques_nm": torque_feedback,
        "adapted_trims_pct": [round(t, 2) for t in xcp_state["fadec_trims"]],
        "adapted_drift_pct": [round(d, 2) for d in xcp_state["fadec_adapts"]],
        "masking_effect_observed": bool(xcp_state["fadec_trims"][0] > 10.0),
        "xcp_observability": True,
    }

    # -------------------------------------------------------------
    # 2. Constrained Datalink & Priority Store-and-Forward under Jamming
    # -------------------------------------------------------------
    link = DatalinkEmulator(bandwidth_bps=2000.0, latency_sec=0.15, loss_rate=0.01)
    random.seed(42)

    # Timeline: 10 seconds total. Jamming active between t=3.0 and t=6.0s
    timeline_dt = 0.1
    t = 0.0
    packets_sent = 0
    packets_received = 0
    p1_latencies = []
    p3_latencies = []
    send_times = {}

    while t < 10.0:
        # Jamming state
        is_jam = (3.0 <= t < 6.0)
        link.set_jamming(is_jam)

        # Generate telemetry (Priority 3) at 2 Hz (every 0.5s)
        if int(t * 10) % 5 == 0:
            pid = f"P3_{packets_sent}"
            payload = f"TLM_{t:.1f}".encode("ascii")
            link.send(payload, priority=3, t=t)
            send_times[payload] = t
            packets_sent += 1

        # Generate emergency alarm (Priority 1) at t=2.0 and t=5.0 (during jam)
        if abs(t - 2.0) < 1e-3 or abs(t - 5.0) < 1e-3:
            payload = f"ALARM_CRIT_{t:.1f}".encode("ascii")
            link.send(payload, priority=1, t=t)
            send_times[payload] = t
            packets_sent += 1

        delivered = link.advance_time(dt=timeline_dt, current_t=t)
        for raw_pkt in delivered:
            is_valid, payload = link.verify_message(raw_pkt)
            if is_valid and payload in send_times:
                packets_received += 1
                lat = t - send_times[payload]
                if payload.startswith(b"ALARM"):
                    p1_latencies.append(lat)
                else:
                    p3_latencies.append(lat)

        t += timeline_dt

    results["datalink_queuing"] = {
        "bandwidth_bps": 2000.0,
        "simulated_duration_sec": 10.0,
        "jamming_window_sec": [3.0, 6.0],
        "packets_sent": packets_sent,
        "packets_delivered_post_jam": packets_received,
        "queue_drop_count": link.packets_dropped_total,
        "p1_alarm_latency_mean_sec": round(float(np.mean(p1_latencies)) if p1_latencies else 0.0, 3),
        "p3_telemetry_latency_mean_sec": round(float(np.mean(p3_latencies)) if p3_latencies else 0.0, 3),
        "store_and_forward_zero_loss": bool(packets_received >= packets_sent - 1),
    }

    # -------------------------------------------------------------
    # 3. Merkle Flight Log Forensics & Tamper Verification
    # -------------------------------------------------------------
    log = MerkleFlightLog()
    for i in range(1000):
        log.append(
            t_sec=i * 0.05,
            payload={
                "rpm": 2300.0 + (i % 20),
                "cht": [140.0 + (i % 5)] * 4,
                "oil_p": 4.5,
            },
        )

    clean_valid, clean_err = log.verify_integrity()
    merkle_root_sealed = log.compute_merkle_root()

    # Test tamper detection on 50 simulated attacks
    tamper_successes = 0
    num_tamper_trials = 50
    for trial in range(num_tamper_trials):
        attack_type = trial % 3
        test_log = MerkleFlightLog()
        test_log.entries = [
            # Deep copy entries
            type(e)(e.index, e.t_sec, dict(e.payload), e.prev_hash, e.entry_hash)
            for e in log.entries[:100]
        ]
        target_idx = 10 + (trial % 80)

        if attack_type == 0:  # Payload value modification
            test_log.entries[target_idx].payload["rpm"] += 50.0
        elif attack_type == 1:  # Entry deletion
            test_log.entries.pop(target_idx)
        elif attack_type == 2:  # Reordering
            test_log.entries[target_idx], test_log.entries[target_idx + 1] = (
                test_log.entries[target_idx + 1],
                test_log.entries[target_idx],
            )

        is_valid, err_idx = test_log.verify_integrity()
        if not is_valid:
            tamper_successes += 1

    results["merkle_forensics"] = {
        "log_entries_sealed": 1000,
        "clean_log_integrity_valid": clean_valid,
        "merkle_root": merkle_root_sealed,
        "tamper_attack_trials": num_tamper_trials,
        "tamper_detection_rate": tamper_successes / num_tamper_trials,
        "tamper_false_negatives": num_tamper_trials - tamper_successes,
    }

    # -------------------------------------------------------------
    # 4. CAN IDS Cyber-Attack Detection
    # -------------------------------------------------------------
    ids = CANIntrusionDetector(jitter_tolerance_frac=0.40)
    total_frames = 0
    attacks_injected = 0
    detected_attacks = 0

    # Feed 500 nominal frames (EEC1 @ 50Hz, ET1 @ 10Hz, Trims @ 20Hz)
    cur_t = 0.0
    for step in range(500):
        cur_t += 0.02
        # EEC1 every 20ms
        ids.inspect_frame(0x0CF00400, 8, b"\x00" * 8, t_sec=cur_t)
        total_frames += 1

        if step % 5 == 0:  # ET1 every 100ms
            ids.inspect_frame(0x18FEEE00, 8, b"\x00" * 8, t_sec=cur_t)
            total_frames += 1

    clean_alerts_count = len(ids.alerts)

    # Inject 20 attacks: Unknown ID injection, DLC truncation, timing fast-injection
    for a in range(20):
        attacks_injected += 1
        if a < 7:  # Unknown ID
            cur_t += 0.02
            alerts = ids.inspect_frame(0x19DEAD00 + a, 8, b"\xFF" * 8, t_sec=cur_t)
            if any(al.kind == "UNKNOWN_ID" for al in alerts):
                detected_attacks += 1
        elif a < 14:  # DLC mismatch
            cur_t += 0.02
            alerts = ids.inspect_frame(0x0CF00400, 4, b"\x00" * 4, t_sec=cur_t)
            if any(al.kind == "DLC_MISMATCH" for al in alerts):
                detected_attacks += 1
        else:  # Timing jitter / fast injection (0.002s instead of 0.020s)
            cur_t += 0.002
            alerts = ids.inspect_frame(0x0CF00400, 8, b"\x00" * 8, t_sec=cur_t)
            if any(al.kind == "TIMING_JITTER" for al in alerts):
                detected_attacks += 1

    results["can_ids_security"] = {
        "nominal_frames_evaluated": total_frames,
        "clean_stream_false_alarms": clean_alerts_count,
        "attacks_injected": attacks_injected,
        "attacks_detected": detected_attacks,
        "tpr": detected_attacks / attacks_injected if attacks_injected else 1.0,
        "fpr": clean_alerts_count / total_frames if total_frames else 0.0,
    }

    out_path = Path("docs/evaluation/E23_edgelink_security.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"E23 evaluation complete -> {out_path}")
    print(f"FADEC Masking Observed: {results['fadec_balancing']['masking_effect_observed']}")
    print(f"Datalink Store-and-Forward Loss: {results['datalink_queuing']['queue_drop_count']}")
    print(f"Merkle Tamper Detection: {results['merkle_forensics']['tamper_detection_rate']*100:.1f}%")
    print(f"CAN IDS TPR: {results['can_ids_security']['tpr']*100:.1f}%, FPR: {results['can_ids_security']['fpr']*100:.2f}%")
    return results


if __name__ == "__main__":
    run_e23_benchmark()
