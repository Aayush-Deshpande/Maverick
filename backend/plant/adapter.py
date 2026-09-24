"""
Independent-plant adapter — bridges VirtualEngine into the twin's data path.

`virtual_engine.py` fixed the design problem: it is a genuinely independent
plant, deliberately not the twin. This module is what was missing — the
thing that actually wires it into `EngineStateService`. Before this file
existed, `VirtualEngine` was built, correct, and never called from anywhere
in `backend/server/`.

Why this is a *blend*, not a full replacement
----------------------------------------------
`VirtualEngine.step()` returns a plain sensor-frame dict for the channels it
models: RPM, MAP, TPS, the four CHT/EGT pairs, oil pressure/temperature, fuel
flow, bus voltage, battery current. It does not yet model vibration,
injection-timing/BSFC/efficiency context fields, or DRDO faults 5-8
(gearbox vibration, isolated EGT imbalance, alternator, FADEC/MAP-sensor
drift) — those simply are not in its fault library yet.

A full swap of `TelemetryStreamer.generate_frame()` for `VirtualEngine.step()`
would therefore silently zero or drop fields the rest of the pipeline reads
(the spectral analyser's high-rate vibration burst, PROP_RPM, HEALTH_INDEX,
the HMS-11/VIS-07 injection-timing and efficiency fields), and would erase
the fault-5..8 deltas entirely, breaking every test and demo scenario that
exercises them.

So this adapter runs the *existing* streamer/twin pipeline first — that
still supplies every field, and every fault, exactly as before — and then,
only for the channels and faults `VirtualEngine` actually models (nominal
flight, and DRDO faults 1-4), overwrites those specific channels with the
plant's independently-computed values, and recomputes `expected` and
`residuals` from that independent RPM/TPS through the twin's own model.
Faults 5-8 are untouched and continue to run exactly as they did before this
file existed.

This is a scoped fix, not a full closure of G01. It closes it for the
channels and fault modes that matter most for the detection-accuracy and
RUL figures already published (thermal/pressure/RPM residuals, faults 1-4),
and it does so without touching a single line of the vibration, context, or
fault-5..8 code paths that are already tested and working.

Why it defaults to off
-----------------------
`backend/ml/models/model_metrics.json`'s published 0.9751 held-out accuracy
was measured against the *old* generator's residual distribution. Swapping
in an independently-computed `actual` for faults 1-4 changes that
distribution — the classifier may do better, worse, or the same, and nobody
knows which until it is retrained and re-evaluated against the new
distribution with the same mission-level group isolation the original
figure used. Flipping this on by default would silently invalidate a
published, cited number without a replacement number to put in its place.
That is exactly the kind of unverified claim this project's own evidence-
label discipline exists to prevent. Turn it on deliberately, retrain, and
publish the new figure alongside the old one — do not swap it silently.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from backend.physics.thermo_model import EnginePhysicalState, ResidualVector, RotaxThermoModel
from backend.plant.virtual_engine import VirtualEngine
from backend.telemetry.can_streamer import TelemetryStreamer

__all__ = ["IndependentPlantAdapter", "FAULT_TO_PLANT_MAPPING", "PLANT_MODELLED_FAULT_IDS"]

GEAR_REDUCTION_RATIO = 2.43

# Numeric DRDO fault id -> (plant fault name, cylinder). Derived by reading
# each fault's actual delta block in can_streamer.py, not guessed:
#   1 CYLINDER_2_CHT_OVERHEAT  -> plant has no per-cylinder cooling fault;
#       COOLING_DEGRADATION is the closest physical analogue (global cooling
#       effectiveness loss), documented here as coarser than the original.
#   2 FUEL_INJECTOR_1_CLOG     -> INJECTOR_COKING, cylinder 1 (exact match:
#       both are a nozzle-deposit delivery restriction on cylinder 1).
#   3 IGNITION_MISFIRE         -> MISFIRE, cylinder 2 (exact match: the
#       streamer's own fault-3 block drops EGT_2, i.e. cylinder 2).
#   4 OIL_PRESSURE_LOSS        -> OIL_PRESSURE_LOSS (exact match, global).
# Faults 5 (gearbox vibration), 6 (isolated EGT imbalance beyond misfire),
# 7 (alternator/electrical) and 8 (FADEC/MAP-sensor drift) have no current
# VirtualEngine equivalent and are intentionally left unmapped.
FAULT_TO_PLANT_MAPPING: Dict[int, Tuple[str, Optional[int]]] = {
    1: ("COOLING_DEGRADATION", None),
    2: ("INJECTOR_COKING", 1),
    3: ("MISFIRE", 2),
    4: ("OIL_PRESSURE_LOSS", None),
}

PLANT_MODELLED_FAULT_IDS = frozenset({0, *FAULT_TO_PLANT_MAPPING.keys()})

# Channels VirtualEngine.step() actually publishes and this adapter overwrites.
_SCALAR_FIELDS = ("ENGINE_RPM", "MAP", "OIL_PRESS", "OIL_TEMP", "FUEL_FLOW",
                  "BUS_VOLTAGE", "BATTERY_CURRENT")


class IndependentPlantAdapter:
    """Drop-in replacement for ``TelemetryStreamer.generate_frame()`` that sources
    the core thermodynamic truth from an independent :class:`VirtualEngine` for
    nominal flight and DRDO faults 1-4. See module docstring for exact scope.
    """

    def __init__(self, streamer: TelemetryStreamer, thermo_model: RotaxThermoModel,
                 config: str = "rotax_914", seed: Optional[int] = None) -> None:
        self._streamer = streamer
        self._thermo = thermo_model
        self._plant = VirtualEngine(config=config, seed=seed)
        self._plant_fault_applied: Optional[int] = None

    def generate_frame(
        self,
        throttle_cmd: Optional[float] = None,
        altitude_cmd: Optional[float] = None,
        oat_cmd: Optional[float] = None,
        dt_sec: float = 0.05,
    ) -> Tuple[EnginePhysicalState, EnginePhysicalState, ResidualVector]:
        # 1. Run the existing pipeline first. This alone still supplies every
        #    field and every fault exactly as before this adapter existed.
        if throttle_cmd is not None:
            actual, expected, residuals = self._streamer.generate_frame(
                throttle_cmd=throttle_cmd, altitude_cmd=altitude_cmd, oat_cmd=oat_cmd
            )
        else:
            actual, expected, residuals = self._streamer.generate_frame()

        fault_id = self._streamer.active_fault_id
        if fault_id not in PLANT_MODELLED_FAULT_IDS:
            # Fault 5-8, or an id outside 0-8 (should not happen): leave the
            # streamer's output untouched. Not this adapter's scope.
            return actual, expected, residuals

        # 2. (Re)inject the plant-side fault only when it has changed, so the
        #    plant's own ramp/inertia carries state across ticks correctly.
        if fault_id != self._plant_fault_applied:
            self._plant.clear_faults()
            mapped = FAULT_TO_PLANT_MAPPING.get(fault_id)
            if mapped is not None:
                name, cyl = mapped
                self._plant.inject_fault(
                    name, cylinder=cyl,
                    severity=getattr(self._streamer, "fault_severity", 1.0) or 0.6,
                    ramp_sec=getattr(self._streamer, "ramp_duration_sec", 6.0),
                )
            self._plant_fault_applied = fault_id

        # 3. Advance the independent plant with the same commanded inputs and
        #    overwrite only the channels it publishes.
        throttle_pct = throttle_cmd if throttle_cmd is not None else actual.TPS
        altitude_ft = altitude_cmd if altitude_cmd is not None else actual.ALTITUDE_FT
        oat_c = oat_cmd if oat_cmd is not None else actual.OAT_C

        frame = self._plant.step(dt_sec, throttle_pct=throttle_pct,
                                 altitude_ft=altitude_ft, oat_c=oat_c)

        actual.ENGINE_RPM = round(frame["ENGINE_RPM"], 1)
        actual.PROP_RPM = round(actual.ENGINE_RPM / GEAR_REDUCTION_RATIO, 1)
        actual.MAP = round(frame["MAP"], 2)
        actual.OIL_PRESS = round(max(0.1, frame["OIL_PRESS"]), 2)
        actual.OIL_TEMP = round(frame["OIL_TEMP"], 2)
        actual.FUEL_FLOW = round(max(0.0, frame["FUEL_FLOW"]), 2)
        actual.BUS_VOLTAGE = round(frame["BUS_VOLTAGE"], 2)
        actual.BATTERY_CURRENT = round(frame["BATTERY_CURRENT"], 2)

        n_cyl = self._plant.cfg.cylinder_count
        for i in range(1, n_cyl + 1):
            cht_key, egt_key = f"CHT_{i}", f"EGT_{i}"
            if cht_key in frame:
                setattr(actual, cht_key, round(frame[cht_key], 2))
            if egt_key in frame:
                setattr(actual, egt_key, round(frame[egt_key], 2))

        # 4. Recompute expected from the TWIN's own model, driven by the
        #    plant's independent RPM/TPS -- two different models now, not
        #    one model checked against itself.
        expected = self._thermo.compute_expected_state(
            altitude_ft=actual.ALTITUDE_FT, oat_c=actual.OAT_C,
            rpm=actual.ENGINE_RPM, tps=actual.TPS,
            tas_knots=actual.TAS_KNOTS, flight_phase=actual.FLIGHT_PHASE,
        )
        residuals = self._thermo.compute_residuals(actual, expected)

        return actual, expected, residuals

    def truth(self) -> Dict:
        """Evaluation-only access to the plant's hidden ground truth (see
        ``VirtualEngine.truth()``). Never call this from the detection/twin
        path -- it exists for test harnesses and the evaluation suite only.
        """
        return self._plant.truth()
