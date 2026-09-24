"""CycleBlock (INTERFACES Sec 3): high-rate telemetry representation for one 720-degree engine cycle.

Emitted once per cycle (e.g. ~33 Hz at 4000 RPM). Carries high-resolution crank tooth
timestamps (<= 25 ns resolution), acoustic/structural acceleration waveforms (51.2 kHz),
and high-rate common-rail pressure traces (>= 30 kHz).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np


@dataclass
class WaveformChannel:
    name: str
    fs_hz: float
    data: np.ndarray             # float32 array of samples
    angle_deg: Optional[np.ndarray] = None  # crank-angle tags 0..720 deg


@dataclass
class CycleBlock:
    cycle_id: int
    t_start: float               # monotonic seconds
    t_end: float                 # monotonic seconds
    engine_config_id: str
    tail_id: str = "TAIL-UNKNOWN"
    mean_rpm: float = 4000.0

    # High-rate edge timestamps (seconds)
    tooth_ts: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    cam_ts: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    prop_ts: Optional[np.ndarray] = None

    # High-rate waveforms
    accel: Dict[str, WaveformChannel] = field(default_factory=dict)
    rail_p_hr: Optional[WaveformChannel] = None
    bus_v_hr: Optional[WaveformChannel] = None

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.t_end - self.t_start)

    @property
    def num_teeth(self) -> int:
        return len(self.tooth_ts)
