"""The live plant behind the PlantSource/Frame contract (card M1-14, P Step 1.4).

SimSource runs backend/sim (SimEngine + registry fault parameters + sensor layer) and emits (Frame, TruthRecord)
pairs, so the runtime, detectors and API keep their contract while the physics underneath is the M1 model.

Faults are registry faults (configs/faults.json ids). Each keeps its own t0, so adding or clearing one fault never
restarts another's ramp. The Frame carries only measured values (sensor layer applied); the TruthRecord carries the
active faults and plant state and goes to evaluation code only.
"""
from __future__ import annotations

import random
import zlib
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from backend.core.frame import FaultTruth, Frame, TruthRecord
from backend.faults.registry import FaultRejected, load_fault_registry
from backend.physics.engine_config import load_engine_config
from backend.sim.atmosphere import Atmosphere
from backend.sim.faults import FaultParameters
from backend.sim.params import physics_values
from backend.sim.plant import FAILED, PlantOutputs, SimEngine
from backend.sim.sensors import SensorLayer

_REGISTRY = None


def registry():
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = load_fault_registry()
    return _REGISTRY


def true_channels(o: PlantOutputs, ci: bool) -> Dict[str, Optional[float]]:
    """Plant outputs under the Frame/registry channel names (cht[n] numbered from 1)."""
    ch: Dict[str, Optional[float]] = {"rpm": o.rpm, "prop_rpm": o.prop_rpm, "map_kpa": o.map_kpa,
                                      "coolant_t": o.coolant_c, "oil_t": o.oil_c, "oil_p": o.oil_bar,
                                      "fuel_flow": o.fuel_kg_h, "bus_v": o.bus_v, "batt_i": o.battery_a,
                                      "alt_i": o.alternator_a, "gearbox_t": o.gearbox_c, "charge_t": o.charge_t_c}
    ch["rail_p" if ci else "fuel_p"] = o.fuel_bar
    if ci and o.supply_bar is not None:
        ch["fuel_p"] = o.supply_bar                    # CI: the low-pressure inlet sensor next to the rail sensor (D63)
    for i, (c, e) in enumerate(zip(o.cht, o.egt), start=1):
        ch[f"cht[{i}]"], ch[f"egt[{i}]"] = c, e
    return ch


class SimSource:
    def __init__(self, engine_config_id: str, seed: Optional[int] = None, tail_id: str = "TAIL-PLANT",
                 engine_serial: str = "SN-PLANT", throttle_pct: float = 60.0) -> None:
        self.engine_config_id = engine_config_id
        self.tail_id, self.engine_serial = tail_id, engine_serial
        self.cfg = load_engine_config(engine_config_id)
        self.n_cylinders = self.cfg.cylinder_count
        self._ecu_lanes = int(getattr(self.cfg, "ecu_lanes", 0) or 0)      # the ECU reports its own lane state
        self.ci = bool(self.cfg.is_compression_ignition)
        self.plant = SimEngine(self.cfg)
        self.plant.warm_start(throttle_pct)
        self.variation = self._build_variation(int(seed or 0))
        self.params = FaultParameters(self.cfg, registry())
        self.sensors = SensorLayer(engine_config_id, int(seed or 0))
        self.faults: List[Any] = []
        self.last: Optional[PlantOutputs] = None
        self._sensor_faults: List[Dict[str, Any]] = []

    def _build_variation(self, seed: int) -> Dict[str, Any]:
        """This tail's manufacturing spread (configs/physics build_variation), applied as model parameters after
        calibration: the twin does not know it, which is why each tail needs its own nominal calibration (D31)."""
        sd = physics_values(self.engine_config_id, "build_variation")
        rng = random.Random(seed * 7919 + zlib.crc32(self.engine_config_id.encode()))
        g = lambda k: 1.0 + rng.gauss(0.0, sd[k])                                     # noqa: E731
        core, n = self.plant.core, self.n_cylinders
        v = {"volumetric_efficiency": g("volumetric_efficiency"), "friction": g("friction"),
             "head_cooling": [g("head_cooling") for _ in range(n)], "injector": [g("injector_trim") for _ in range(n)],
             "compressor_efficiency": g("compressor_efficiency")}
        core.induction.eta_v *= v["volumetric_efficiency"]
        core.fmep = tuple(x * v["friction"] for x in core.fmep)
        if core.turbo is not None:
            core.turbo.eta_c *= v["compressor_efficiency"]
        return v

    # -- faults (plant side only; nothing about them reaches the Frame) --------------------------------------
    def now(self) -> float:
        return float(self.plant.t)

    def apply(self, fault: Any) -> bool:
        """Add a registry fault (fault_id, cylinder, channel, severity, ramp_s, t0_s). Every registry fault is
        simulated: physical ones through parameter_effects, sensor ones through the sensor layer."""
        registry().get(fault.fault_id)
        self.faults.append(fault)
        return True

    def inject_fault(self, name: str, cylinder: Optional[int] = None, severity: float = 0.6,
                     ramp_sec: float = 300.0, channel: Optional[str] = None) -> Any:
        """Registry id (F01..S07) or a registry plant_mode_legacy name."""
        spec = self._resolve(name)
        if spec.kind == "SENSOR" and channel is None and cylinder is not None:
            channel = f"cht[{cylinder}]"
        f = SimpleNamespace(fault_id=spec.id, cylinder=cylinder if spec.scope == "CYLINDER" else None,
                            channel=channel, severity=float(severity), ramp_s=float(ramp_sec), t0_s=self.now())
        self.apply(f)
        return f

    def _resolve(self, name: str):
        reg = registry()
        try:
            return reg.get(name)
        except (KeyError, FaultRejected):
            pass
        matches = [s for s in reg.applicable(self.cfg) if s.raw.get("plant_mode_legacy") == name]
        if not matches:
            raise ValueError(f"{name!r} is not a registry fault for {self.engine_config_id}")
        return matches[0]

    def clear_faults(self) -> None:
        self.faults.clear()

    def start(self) -> None:
        self.plant.start()

    def stop(self) -> None:
        self.plant.stop()

    def reset(self) -> None:
        self.plant.reset()

    # -- stepping ---------------------------------------------------------------------------------------------
    def set_conditions(self, throttle_pct: float, altitude_ft: float, oat_c: Optional[float],
                       tas_kt: Optional[float]) -> None:
        lv = self.plant.levers
        lv.throttle_pct, lv.altitude_ft, lv.tas_kt = throttle_pct, altitude_ft, tas_kt
        if oat_c is not None:
            lv.isa_dev_c = oat_c - (Atmosphere.at(altitude_ft).temperature_k - 273.15)

    def advance(self, dt_sec: float, publish: bool = True) -> PlantOutputs:
        """One plant step with the active faults' parameters (no measurement). publish=False: an inner substep."""
        health, self._sensor_faults = self.params.health(self.faults, self.plant.t, self.plant.core.combustion)
        v = self.variation
        health["injector"] = [a * b for a, b in zip(health["injector"], v["injector"])]
        th = health["thermal"]
        th["head_conductance"] = v["head_cooling"]
        self.last = self.plant.step(dt_sec, health, publish=publish)
        return self.last

    def emit(self) -> Tuple[Frame, TruthRecord]:
        """Measure the latest plant outputs (sensor layer) into a Frame, plus the evaluation-only TruthRecord."""
        o = self.last
        true = true_channels(o, self.ci)
        true.update({f"vib[{k}]": v for k, v in o.vibration.items()})
        m = self.sensors.measure(true, o.t, self._sensor_faults)
        n = self.n_cylinders
        frame = Frame(t=o.t, source="PLANT", engine_config_id=self.engine_config_id, tail_id=self.tail_id,
                      engine_serial=self.engine_serial, rpm=m["rpm"], prop_rpm=m["prop_rpm"], throttle=o.throttle_pct,
                      map_kpa=m["map_kpa"], cht=[m[f"cht[{i}]"] for i in range(1, n + 1)],
                      egt=[m[f"egt[{i}]"] for i in range(1, n + 1)], coolant_t=m["coolant_t"], oil_p=m["oil_p"],
                      oil_t=m["oil_t"], fuel_flow=m["fuel_flow"], rail_p=m.get("rail_p"), fuel_p=m.get("fuel_p"),
                      gearbox_t=m["gearbox_t"], engine_state=o.state,
                      ecu_lanes_ok=(self._ecu_lanes - o.lanes_failed) if self._ecu_lanes else None,
                      ign_cmd=o.ign_timing_btdc, bus_v=m["bus_v"], bus_i=m["alt_i"], batt_i=m["batt_i"],
                      alt=o.altitude_ft, oat=o.oat_c, tas=o.tas_kt,
                      vibration_orders={k: m[f"vib[{k}]"] for k in o.vibration if m[f"vib[{k}]"] is not None},
                      lane_b={k[:-len(".lane_b")].replace("[", "_").replace("]", ""): v for k, v in m.items()
                              if k.endswith(".lane_b") and v is not None})
        truth = TruthRecord(t=o.t, failed=o.state == FAILED, failure_mode=o.failure,
                            active_faults=[FaultTruth(mode=f.fault_id, location=f.cylinder, severity=f.severity,
                                                      onset_t=f.t0_s, ramp_sec=f.ramp_s) for f in self.faults],
                            plant_params={"state": o.state, "power_kw": o.power_kw})
        return frame, truth

    def step(self, dt_sec: float, throttle_pct: float = 75.0, altitude_ft: float = 0.0,
             oat_c: Optional[float] = None, tas_kt: Optional[float] = None) -> Tuple[Frame, TruthRecord]:
        self.set_conditions(throttle_pct, altitude_ft, oat_c, tas_kt)
        self.advance(dt_sec)
        return self.emit()

    @property
    def has_failed(self) -> bool:
        return self.plant.state == FAILED
