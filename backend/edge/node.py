"""EdgeNode -- persistence-gated scalar downlink with bandwidth, latency and power accounting (W4, D34).

Runs the tier-0 detector at the edge and decides what to send to the ground: a tiny heartbeat every
``heartbeat_s`` and a full feature packet only when the persistence gate confirms an anomaly.  All numbers
are ACCOUNTING on the machine running the test; the Raspberry Pi 5 profile applies a declared slowdown
factor and is labelled EMULATED until a board benchmark replaces it (backlog W9/S9).
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

from backend.core.frame import Frame
from backend.detect import ResidualDetector

WAVEFORM_HZ = 51200          # D-decision: 2.56 x 20 kHz combustion band
WAVEFORM_BYTES = 2           # 16-bit samples
HEARTBEAT = struct.Struct("<fBBf")                      # t, health flag, n_alarm_channels, max ratio
ALARM_HEAD = struct.Struct("<fBff")                      # t, top channel idx, top z, max ratio


@dataclass(frozen=True)
class EdgeProfile:
    name: str
    slowdown: float          # multiply measured host latency
    watts: float
    evidence: str            # EMULATED | MEASURED

PI5_EMULATED = EdgeProfile("raspberry_pi_5", slowdown=4.0, watts=6.0, evidence="EMULATED")
HOST = EdgeProfile("host", slowdown=1.0, watts=0.0, evidence="MEASURED")


class EdgeNode:
    def __init__(self, detector: ResidualDetector, profile: EdgeProfile = PI5_EMULATED,
                 heartbeat_s: float = 10.0) -> None:
        self.det = detector
        self.profile = profile
        self.heartbeat_s = heartbeat_s
        self.bytes_sent = 0
        self.frames = 0
        self.first_t: Optional[float] = None
        self.last_t = 0.0
        self._last_hb = -1e9
        self._lat_ms: list = []

    def process(self, frame: Frame) -> Optional[bytes]:
        """Returns the downlink message for this frame, or None if nothing needs to be sent."""
        t0 = time.perf_counter()
        res = self.det.score(frame)
        self._lat_ms.append((time.perf_counter() - t0) * 1000.0 * self.profile.slowdown)
        self.frames += 1
        self.first_t = frame.t if self.first_t is None else self.first_t
        self.last_t = frame.t
        ratio = max(res.ratios.values())
        msg = None
        if res.confirmed:
            names = self.det.cal.channel_names()
            ch, z = res.top_channels[0]
            msg = ALARM_HEAD.pack(frame.t, names.index(ch), z, ratio)
            msg += np.asarray(self.det.cal.features(self.det.cal.z(frame)), dtype=np.float16).tobytes()
        elif frame.t - self._last_hb >= self.heartbeat_s:
            msg = HEARTBEAT.pack(frame.t, 0, 0, ratio)
            self._last_hb = frame.t
        if msg:
            self.bytes_sent += len(msg)
        return msg

    def report(self) -> Dict:
        span = max(self.last_t - (self.first_t or 0.0), 1e-9)
        lat = np.array(self._lat_ms) if self._lat_ms else np.zeros(1)
        n_scalar = len(self.det.cal.channel_names())
        raw_scalar_bps = n_scalar * 4 * 8            # every calibrated channel, float32, 1 Hz
        raw_wave_bps = WAVEFORM_HZ * WAVEFORM_BYTES * 8
        sent_bps = self.bytes_sent * 8 / span
        return {
            "profile": self.profile.name, "evidence": self.profile.evidence,
            "frames": self.frames, "bytes_sent": self.bytes_sent, "sent_bps": sent_bps,
            "raw_scalar_bps": raw_scalar_bps, "raw_waveform_bps": raw_wave_bps,
            "reduction_vs_scalar": raw_scalar_bps / max(sent_bps, 1e-9),
            "reduction_vs_waveform": raw_wave_bps / max(sent_bps, 1e-9),
            "latency_ms_p50": float(np.percentile(lat, 50)), "latency_ms_p99": float(np.percentile(lat, 99)),
            "power_w_assumed": self.profile.watts,
        }
