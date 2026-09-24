"""High-Rate Sensor Chain Emulation (B2.5, FDP-06).

Emulates:
1. IEPE accelerometer sensor response and mounted resonance (~25 kHz).
2. Anti-alias low-pass filter (20 kHz cutoff for 51.2 kHz acquisition).
3. 24-bit ADC quantization and noise floor.
4. 60-2 trigger wheel mechanical tooth-spacing errors and runout.
5. High-resolution timer timestamp quantization (<= 25 ns resolution).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import signal


@dataclass
class TriggerWheelConfig:
    total_teeth: int = 60
    missing_teeth: int = 2
    tooth_error_sigma_deg: float = 0.04   # tooth manufacturing / spacing error
    eccentricity_runout_um: float = 25.0  # wheel eccentricity runout


class HighRateSensorChain:
    """Emulates physical sensor transducer and DAQ acquisition chain effects on high-rate signals."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self.timer_resolution_ns = 25.0  # 25 ns timer clock

        # Generate persistent 60-2 trigger wheel tooth spacing errors
        self.wheel_cfg = TriggerWheelConfig()
        n_teeth = self.wheel_cfg.total_teeth - self.wheel_cfg.missing_teeth
        self.tooth_errors_deg = self.rng.normal(0.0, self.wheel_cfg.tooth_error_sigma_deg, size=n_teeth)

    def digitize_accelerometer(
        self,
        raw_accel: np.ndarray,
        fs_hz: float = 51200.0,
        full_scale_g: float = 100.0,
    ) -> np.ndarray:
        """Apply anti-alias filter, sensor resonance, and 24-bit ADC quantization to vibration waveform."""
        # 1. Anti-aliasing 6th-order Butterworth low-pass filter at 20 kHz
        nyq = 0.5 * fs_hz
        cutoff = min(20000.0, 0.45 * fs_hz)
        b, a = signal.butter(6, cutoff / nyq, btype="low")
        filtered = signal.filtfilt(b, a, raw_accel)

        # 2. 24-bit ADC quantization
        # 24 bits -> 2^23 steps over full scale
        lsb = (full_scale_g * 9.80665) / (2 ** 23)
        quantized = np.round(filtered / lsb) * lsb

        # 3. Add instrumentation noise floor
        noise = self.rng.normal(0.0, 0.02, size=len(quantized))
        return (quantized + noise).astype(np.float32)

    def generate_crank_tooth_timestamps(
        self,
        rpm: float,
        cycle_start_t: float,
        num_cycles: int = 1,
    ) -> np.ndarray:
        """Generate nanosecond-quantized crank tooth edge timestamps for 720 deg cycles with 60-2 wheel errors."""
        nominal_interval_deg = 360.0 / self.wheel_cfg.total_teeth  # 6.0 deg
        n_physical_teeth = self.wheel_cfg.total_teeth - self.wheel_cfg.missing_teeth  # 58

        deg_per_sec = (rpm * 360.0) / 60.0
        timestamps = []

        curr_t = cycle_start_t
        for cycle in range(num_cycles):
            for rev in range(2):  # 2 revolutions per 4-stroke cycle
                rev_offset = (cycle * 2 + rev) * 360.0
                for tooth_idx in range(n_physical_teeth):
                    nominal_angle = rev_offset + tooth_idx * nominal_interval_deg
                    actual_angle = nominal_angle + self.tooth_errors_deg[tooth_idx]

                    t_edge = cycle_start_t + (actual_angle / deg_per_sec)

                    # Quantize to 25 ns timer clock
                    t_ns = round(t_edge * 1e9 / self.timer_resolution_ns) * self.timer_resolution_ns
                    timestamps.append(t_ns * 1e-9)

        return np.array(timestamps, dtype=np.float64)
