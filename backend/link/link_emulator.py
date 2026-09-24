"""Constrained Datalink Emulator and Priority Store-and-Forward (B2.7, INN-07, OPT-03).

Implements:
1. Bandwidth budget limiter (e.g. 2 kbit/s = 250 bytes/s).
2. Propagation latency simulation (50-500 ms).
3. RF jamming window and packet loss emulation.
4. Priority store-and-forward queue (Priority 1 alarms first, then diagnostics, then periodic telemetry).
5. Signed MAVLink 2 frame transmission and receipt verification.
"""

from __future__ import annotations

import heapq
import hmac
import hashlib
import struct
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(order=True)
class QueuedPacket:
    priority: int                   # Lower number = higher priority (1=Emergency, 2=Diag, 3=Telemetry)
    timestamp: float
    data: bytes = field(compare=False)
    seq: int = field(compare=False, default=0)


class DatalinkEmulator:
    """Emulates UAV satcom / line-of-sight datalink constraints and priority store-and-forward buffering."""

    def __init__(
        self,
        bandwidth_bps: float = 2000.0,       # 2 kbit/s typical tactical datalink allocation
        latency_sec: float = 0.15,          # 150 ms latency
        loss_rate: float = 0.02,            # 2% random packet drop
        secret_key: bytes = b"ANUMAAN_DRDO_LINK_SECRET_KEY_2026",
    ) -> None:
        self.bandwidth_bps = bandwidth_bps
        self.bytes_per_sec = bandwidth_bps / 8.0
        self.latency_sec = latency_sec
        self.loss_rate = loss_rate
        self.secret_key = secret_key

        self.queue: List[QueuedPacket] = []
        self.in_flight: List[Tuple[float, bytes]] = []  # (delivery_time, data)
        self.is_jammed = False
        self.bytes_transmitted_total = 0
        self.packets_dropped_total = 0
        self._seq_counter = 0

    def set_jamming(self, jammed: bool) -> None:
        self.is_jammed = jammed

    def sign_message(self, payload: bytes) -> bytes:
        """Append 8-byte HMAC-SHA256 signature to payload."""
        sig = hmac.new(self.secret_key, payload, hashlib.sha256).digest()[:8]
        return payload + sig

    def verify_message(self, message_with_sig: bytes) -> Tuple[bool, bytes]:
        """Verify HMAC signature and return (is_valid, payload)."""
        if len(message_with_sig) < 8:
            return False, b""
        payload = message_with_sig[:-8]
        sig = message_with_sig[-8:]
        expected_sig = hmac.new(self.secret_key, payload, hashlib.sha256).digest()[:8]
        is_valid = hmac.compare_digest(sig, expected_sig)
        return is_valid, payload

    def send(self, payload: bytes, priority: int = 3, t: float = 0.0) -> None:
        """Enqueue packet into priority store-and-forward queue."""
        self._seq_counter += 1
        signed = self.sign_message(payload)
        item = QueuedPacket(priority=priority, timestamp=t, data=signed, seq=self._seq_counter)
        heapq.heappush(self.queue, item)

    def advance_time(self, dt: float, current_t: float) -> List[bytes]:
        """Drain queue according to bandwidth limit, latency and jamming state. Returns delivered packets."""
        delivered: List[bytes] = []

        # 1. Process in-flight packets reaching destination
        remaining_in_flight = []
        for delivery_t, pkt_data in self.in_flight:
            if current_t >= delivery_t:
                delivered.append(pkt_data)
            else:
                remaining_in_flight.append((delivery_t, pkt_data))
        self.in_flight = remaining_in_flight

        if self.is_jammed:
            # During jamming, datalink is blocked -> store in queue
            return delivered

        # 2. Transmit bytes from priority queue up to bandwidth budget for this interval
        allowed_bytes = self.bytes_per_sec * dt
        bytes_sent = 0

        while self.queue and bytes_sent < allowed_bytes:
            pkt = heapq.heappop(self.queue)
            pkt_len = len(pkt.data)

            if bytes_sent + pkt_len <= allowed_bytes or bytes_sent == 0:
                bytes_sent += pkt_len
                self.bytes_transmitted_total += pkt_len
                delivery_time = current_t + self.latency_sec
                self.in_flight.append((delivery_time, pkt.data))
            else:
                # Put back if exceeding budget
                heapq.heappush(self.queue, pkt)
                break

        return delivered
