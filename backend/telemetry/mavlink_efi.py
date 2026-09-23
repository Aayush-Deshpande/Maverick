"""
MAVLink EFI_STATUS ingestion — F46.

We invented a CAN schema. The world already has one, and it is the one actual
UAVs speak.

MAVLink message **EFI_STATUS (#225)** carries, as standard fields: engine speed,
cylinder head temperature, **ignition timing**, **injection time**, fuel flow,
fuel consumed, engine load, throttle position, barometric pressure, intake
manifold pressure and temperature, exhaust gas temperature, fuel pressure and
ECU health. That is very nearly the problem statement's monitored-parameter
list, already standardised, and ArduPilot has a first-class EFI subsystem with
drivers for real UAV ECUs (Currawong and others) publishing into it over CAN.

Consequences for this project:

  * "Real-time data ingestion capability" (PS §A, gap DTC-06) stops being a
    claim about our own generator and becomes ingestion from the autopilot
    stack Indian UAV programmes actually fly.
  * "Injection timing parameters" (PS §B, gap HMS-11) is satisfied **by standard
    message field**, not by a channel we invented.
  * The same path replays a recorded `.tlog`, so log-as-live costs nothing extra.

This module deliberately does not depend on pymavlink at import time. The
mapping and the scaling are the valuable part and must remain testable without
a MAVLink stack present; the parser is imported lazily inside the functions that
need it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

__all__ = [
    "EFI_STATUS_FIELDS",
    "EFIFrame",
    "efi_to_anumaan",
    "MAVLinkEFISource",
    "replay_tlog",
]

# EFI_STATUS (#225) field list, in the order the dialect defines them.
EFI_STATUS_FIELDS = (
    "health", "ecu_index", "rpm", "fuel_consumed", "fuel_flow", "engine_load",
    "throttle_position", "spark_dwell_time", "barometric_pressure",
    "intake_manifold_pressure", "intake_manifold_temperature",
    "cylinder_head_temperature", "ignition_timing", "injection_time",
    "exhaust_gas_temperature", "throttle_out", "pt_compensation",
    "ignition_voltage", "fuel_pressure",
)

# MAVLink -> ANUMAAN canonical channel, with the unit conversion each needs.
# MAVLink EFI temperatures are degrees Celsius in the current common dialect;
# pressures are kPa; fuel flow is grams per minute.
_FIELD_MAP = {
    "rpm": ("ENGINE_RPM", lambda v: float(v)),
    "cylinder_head_temperature": ("CHT_1", lambda v: float(v)),
    "exhaust_gas_temperature": ("EGT_1", lambda v: float(v)),
    "intake_manifold_pressure": ("MAP", lambda v: float(v)),
    "intake_manifold_temperature": ("CHARGE_TEMP_C", lambda v: float(v)),
    "barometric_pressure": ("AMBIENT_P_KPA", lambda v: float(v)),
    "throttle_position": ("TPS", lambda v: float(v)),
    "fuel_flow": ("FUEL_FLOW_G_MIN", lambda v: float(v)),
    "fuel_consumed": ("FUEL_CONSUMED_G", lambda v: float(v)),
    "fuel_pressure": ("FUEL_RAIL_P", lambda v: float(v)),
    "engine_load": ("ENGINE_LOAD_PCT", lambda v: float(v)),
    "ignition_timing": ("IGN_TIMING_BTDC", lambda v: float(v)),
    "injection_time": ("INJ_PULSE_WIDTH_MS", lambda v: float(v)),
    "ignition_voltage": ("BUS_VOLTAGE", lambda v: float(v)),
    "ecu_index": ("ECU_INDEX", lambda v: int(v)),
    "health": ("ECU_HEALTH", lambda v: int(v)),
}

# Fuel flow arrives as grams/minute; the rest of the stack works in litres/hour.
_AVGAS_DENSITY_G_PER_L = 720.0
_JETA1_DENSITY_G_PER_L = 804.0


@dataclass
class EFIFrame:
    """One decoded EFI_STATUS message in ANUMAAN canonical form."""

    t_sec: float
    channels: Dict[str, float] = field(default_factory=dict)
    ecu_index: int = 0
    healthy: bool = True
    source: str = "MAVLINK_EFI_STATUS"

    def as_dict(self) -> dict:
        d = dict(self.channels)
        d.update({"T_SEC": round(self.t_sec, 3), "ECU_INDEX": self.ecu_index,
                  "ECU_HEALTH_OK": self.healthy, "TELEM_SOURCE": self.source})
        return d


def efi_to_anumaan(msg: Any, t_sec: float = 0.0,
                   fuel_density_g_per_l: float = _AVGAS_DENSITY_G_PER_L) -> EFIFrame:
    """Convert an EFI_STATUS message (or any object with its fields) to canonical form.

    Accepts a pymavlink message, a plain object, or a dict, so the mapping can
    be tested without a MAVLink stack installed — which matters because the
    mapping is the part that carries engineering risk, not the parsing.
    """
    def get(name: str):
        if isinstance(msg, dict):
            return msg.get(name)
        return getattr(msg, name, None)

    channels: Dict[str, float] = {}
    for field_name, (canonical, convert) in _FIELD_MAP.items():
        raw = get(field_name)
        if raw is None:
            continue
        try:
            channels[canonical] = convert(raw)
        except (TypeError, ValueError):
            continue

    # Derived: litres/hour is what the physics model and the dashboard use.
    if "FUEL_FLOW_G_MIN" in channels:
        channels["FUEL_FLOW"] = (channels["FUEL_FLOW_G_MIN"] * 60.0
                                 / max(fuel_density_g_per_l, 1e-6))

    health = int(channels.pop("ECU_HEALTH", 1) or 0)
    ecu = int(channels.pop("ECU_INDEX", 0) or 0)
    return EFIFrame(t_sec=t_sec, channels=channels, ecu_index=ecu,
                    healthy=bool(health))


class MAVLinkEFISource:
    """Live EFI_STATUS ingestion from an autopilot or SITL instance.

    `connection` is any pymavlink connection string, so the same code reads a
    SITL instance ("udpin:127.0.0.1:14550"), a serial radio link
    ("/dev/ttyUSB0" or "COM5"), or a replayed log. The twin therefore runs
    identically against simulation and against hardware, which is the property
    the deployment roadmap needs and the one a bespoke generator cannot provide.
    """

    def __init__(self, connection: str = "udpin:127.0.0.1:14550",
                 fuel_density_g_per_l: float = _AVGAS_DENSITY_G_PER_L,
                 source_system: Optional[int] = None) -> None:
        self.connection_string = connection
        self.fuel_density = fuel_density_g_per_l
        self.source_system = source_system
        self._conn = None
        self._frames_seen = 0
        self._last_t: Optional[float] = None

    def connect(self) -> "MAVLinkEFISource":
        from pymavlink import mavutil  # imported lazily, see module docstring

        self._conn = mavutil.mavlink_connection(self.connection_string)
        return self

    def frames(self, timeout: float = 1.0) -> Iterator[EFIFrame]:
        """Yield canonical frames as EFI_STATUS messages arrive."""
        if self._conn is None:
            self.connect()
        while True:
            msg = self._conn.recv_match(type="EFI_STATUS", blocking=True,
                                        timeout=timeout)
            if msg is None:
                continue
            if (self.source_system is not None
                    and getattr(msg, "get_srcSystem", lambda: None)() != self.source_system):
                continue
            t = getattr(msg, "_timestamp", None)
            if t is None:
                t = (self._last_t or 0.0) + 0.05
            self._last_t = float(t)
            self._frames_seen += 1
            yield efi_to_anumaan(msg, t_sec=float(t),
                                 fuel_density_g_per_l=self.fuel_density)

    @property
    def frames_seen(self) -> int:
        return self._frames_seen

    def health(self) -> dict:
        """Ingestion health — frame count and staleness, for the GCS view."""
        return {
            "source": self.connection_string,
            "frames_seen": self._frames_seen,
            "last_frame_t": self._last_t,
            "connected": self._conn is not None,
        }


def replay_tlog(path: Path | str,
                fuel_density_g_per_l: float = _AVGAS_DENSITY_G_PER_L
                ) -> Iterator[EFIFrame]:
    """Log-as-live: stream EFI_STATUS out of a recorded telemetry log.

    The twin cannot tell this apart from a live link, which is the point — a
    recorded sortie replays through exactly the ingestion path a real one uses,
    so replay exercises the real code rather than a parallel implementation.
    """
    from pymavlink import mavutil

    conn = mavutil.mavlink_connection(str(path))
    while True:
        msg = conn.recv_match(type="EFI_STATUS", blocking=False)
        if msg is None:
            break
        t = float(getattr(msg, "_timestamp", 0.0) or 0.0)
        yield efi_to_anumaan(msg, t_sec=t, fuel_density_g_per_l=fuel_density_g_per_l)
