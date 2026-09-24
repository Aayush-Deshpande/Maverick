"""WaveformSource and WaveformRecorder (W3, SIM-03): High-rate CycleBlock acquisition and .npz recording/replay.

Provides:
1. WaveformSource: produces high-rate CycleBlock instances (51.2 kHz vibration, 30 kHz rail pressure,
   <=25 ns crank tooth timestamps) with injected physical faults.
2. WaveformRecorder: records and bit-exact replays CycleBlocks to/from compressed .npz archives with
   SHA-256 provenance manifests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

from backend.core.cycle_block import CycleBlock, WaveformChannel
from backend.physics.combustion_ci import CICombustionModel, CICombustionParams
from backend.physics.engine_config import EngineConfig, load_engine_config
from backend.physics.rail import CommonRailHydraulics, RailConfig
from backend.physics.structure import StructuralAcoustics
from backend.plant.sensors_hr import HighRateSensorChain


class WaveformSource:
    """Generates high-rate CycleBlock telemetry for an engine profile."""

    def __init__(self, engine_id: str, seed: int = 42, tail_id: Optional[str] = None) -> None:
        self.engine_id = engine_id
        self.cfg: EngineConfig = load_engine_config(engine_id)
        self.tail_id = tail_id or f"TAIL-{engine_id}-{seed}"
        self.seed = seed

        self.combustion = CICombustionModel(self.cfg)
        self.rail = CommonRailHydraulics(RailConfig())
        self.acoustics = StructuralAcoustics(self.cfg, seed=seed)
        self.sensors = HighRateSensorChain(seed=seed)

        self.cycle_count = 0
        self.current_t = 0.0

        # Injected high-rate fault states
        self.bearing_fault: Optional[str] = None
        self.bearing_severity: float = 0.0
        self.turbo_whirl_severity: float = 0.0
        self.coking_factors = [1.0] * self.cfg.cylinder_count
        self.needle_stick_cyls: List[int] = []
        self.rail_leak_bar_s: float = 0.0

    def inject_fault(self, mode: str, cylinder: Optional[int] = None, severity: float = 0.8) -> None:
        if mode == "INJECTOR_COKING_IDID":
            cyl = (cylinder or 1) - 1
            if 0 <= cyl < len(self.coking_factors):
                self.coking_factors[cyl] = max(0.2, 1.0 - 0.7 * severity)
        elif mode == "INJECTOR_NEEDLE_STICK":
            cyl = cylinder or 1
            if cyl not in self.needle_stick_cyls:
                self.needle_stick_cyls.append(cyl)
        elif mode == "RAIL_PRESSURE_DECAY":
            self.rail_leak_bar_s = 40.0 * severity
        elif mode == "TURBO_BEARING_WEAR":
            self.turbo_whirl_severity = severity
        elif mode in ("BEARING_WEAR", "BEARING_BPFO"):
            self.bearing_fault = "BPFO"
            self.bearing_severity = severity

    def clear_faults(self) -> None:
        self.bearing_fault = None
        self.bearing_severity = 0.0
        self.turbo_whirl_severity = 0.0
        self.coking_factors = [1.0] * self.cfg.cylinder_count
        self.needle_stick_cyls.clear()
        self.rail_leak_bar_s = 0.0

    def next_cycle(self, rpm: float = 4000.0, throttle_pct: float = 70.0, map_kpa: float = 180.0) -> CycleBlock:
        """Synthesise the next 720-degree CycleBlock."""
        self.cycle_count += 1
        cycle_dur_s = (720.0 / 360.0) * (60.0 / max(100.0, rpm))
        t_start = self.current_t
        t_end = t_start + cycle_dur_s
        self.current_t = t_end

        n_cyl = self.cfg.cylinder_count
        fire_interval = 720.0 / n_cyl
        firing_angles = [i * fire_interval for i in range(n_cyl)]

        # 1. Crank tooth timestamps with 60-2 errors (25 ns quantisation)
        tooth_ts = self.sensors.generate_crank_tooth_timestamps(rpm, t_start, num_cycles=1)

        # 2. In-cylinder combustion and dp/dtheta for each cylinder
        fuel_mg = 25.0 * (throttle_pct / 100.0)
        dp_dtheta_list = []
        for i in range(n_cyl):
            # Apply coking reduction
            eff_fuel = fuel_mg * self.coking_factors[i]
            _, _, dp_dt = self.combustion.simulate_cycle_pressure(
                rpm=rpm,
                map_kpa=map_kpa,
                t_charge_k=340.0,
                fuel_mg_per_stroke=eff_fuel,
            )
            dp_dtheta_list.append(dp_dt)

        # 3. High-rate vibration waveform (51.2 kHz)
        t_v, angle_v, raw_accel = self.acoustics.synthesize_cycle_vibration(
            rpm=rpm,
            dp_dtheta_per_cyl=dp_dtheta_list,
            firing_angles_deg=firing_angles,
            fs_hz=51200.0,
            bearing_fault=self.bearing_fault,
            bearing_severity=self.bearing_severity,
            turbo_whirl_severity=self.turbo_whirl_severity,
        )
        dig_accel = self.sensors.digitize_accelerometer(raw_accel, fs_hz=51200.0)
        accel_chan = WaveformChannel(name="accel_block", fs_hz=51200.0, data=dig_accel, angle_deg=angle_v)

        # 4. High-rate rail pressure waveform (30 kHz)
        rail_chan = None
        if self.cfg.is_compression_ignition:
            inj_qtys = [fuel_mg] * n_cyl
            t_r, p_rail = self.rail.simulate_cycle_rail_pressure(
                rpm=rpm,
                target_p_bar=1600.0,
                inj_quantities_mm3=inj_qtys,
                inj_angles_deg=firing_angles,
                coking_factors=self.coking_factors,
                needle_stick_cyls=self.needle_stick_cyls,
                rail_leak_bar_s=self.rail_leak_bar_s,
                fs_hz=30000.0,
            )
            rail_chan = WaveformChannel(name="rail_pressure", fs_hz=30000.0, data=p_rail)

        return CycleBlock(
            cycle_id=self.cycle_count,
            t_start=t_start,
            t_end=t_end,
            engine_config_id=self.engine_id,
            tail_id=self.tail_id,
            mean_rpm=rpm,
            tooth_ts=tooth_ts,
            accel={"block": accel_chan},
            rail_p_hr=rail_chan,
        )


class WaveformRecorder:
    """Records and bit-exactly replays CycleBlocks via compressed .npz archives."""

    @staticmethod
    def save_cycle(block: CycleBlock, file_path: Path | str) -> str:
        """Save a CycleBlock to .npz with SHA-256 hash."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        arrays = {
            "tooth_ts": block.tooth_ts,
            "meta": np.array([block.cycle_id, block.t_start, block.t_end, block.mean_rpm], dtype=np.float64),
        }
        if "block" in block.accel:
            arrays["accel_block"] = block.accel["block"].data
            if block.accel["block"].angle_deg is not None:
                arrays["accel_angle"] = block.accel["block"].angle_deg

        if block.rail_p_hr is not None:
            arrays["rail_p"] = block.rail_p_hr.data

        np.savez_compressed(path, **arrays)

        # Compute SHA-256
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest_path = path.with_suffix(".json")
        manifest_path.write_text(json.dumps({
            "cycle_id": block.cycle_id,
            "engine_id": block.engine_config_id,
            "sha256": sha,
            "t_start": block.t_start,
            "t_end": block.t_end,
        }, indent=2), encoding="utf-8")
        return sha

    @staticmethod
    def load_cycle(file_path: Path | str, engine_config_id: str) -> CycleBlock:
        """Load CycleBlock from .npz."""
        path = Path(file_path)
        npz = np.load(path)
        meta = npz["meta"]
        cid, t0, t1, rpm = int(meta[0]), float(meta[1]), float(meta[2]), float(meta[3])
        tooth_ts = npz["tooth_ts"]

        accel_dict = {}
        if "accel_block" in npz:
            angle = npz["accel_angle"] if "accel_angle" in npz else None
            accel_dict["block"] = WaveformChannel(name="accel_block", fs_hz=51200.0, data=npz["accel_block"], angle_deg=angle)

        rail_chan = None
        if "rail_p" in npz:
            rail_chan = WaveformChannel(name="rail_pressure", fs_hz=30000.0, data=npz["rail_p"])

        return CycleBlock(
            cycle_id=cid,
            t_start=t0,
            t_end=t1,
            engine_config_id=engine_config_id,
            mean_rpm=rpm,
            tooth_ts=tooth_ts,
            accel=accel_dict,
            rail_p_hr=rail_chan,
        )
