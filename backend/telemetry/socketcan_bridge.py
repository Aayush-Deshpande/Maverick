"""
SocketCAN & SAE J1939 Telemetry Ingestion Bridge
DRDO / iDEX Problem Statement ID: 26054 — Defence GCS Ready Ingestion

Supports:
- Native Linux SocketCAN ('socketcan', e.g. vcan0 or can0)
- Cross-platform virtual bus ('virtual', 'virtual_ch0') for Windows/macOS testing
- Binary pack/unpack of SAE J1939 Parameter Group Numbers (PGNs)
- Integration with EnginePhysicalState & 20 Hz FastAPI State Service
"""

import time
import struct
import logging
from typing import Dict, Any, Optional, Iterator, Tuple

logger = logging.getLogger("SOCKETCAN_BRIDGE")

# Standard Aerospace / SAE J1939 PGNs for UAV Aero-Engines
PGN_EEC1 = 0x0CF00400  # PGN 61444: Electronic Engine Controller 1 (RPM, Torque)
PGN_ET1  = 0x18FEEE00  # PGN 65262: Engine Temperature 1 (CHT, Oil Temp)
PGN_EFL1 = 0x18FEEF00  # PGN 65263: Engine Fluid Level & Pressure (Oil Pressure)
PGN_EGT  = 0x18FE0800  # PGN 65032: Exhaust Gas Temperature
PGN_TURBO= 0x18FED900  # PGN 65241: Turbocharger / Boost Manifold Pressure
PGN_FUEL = 0x18FEF200  # PGN 65266: Fuel Economy & Common Rail Pressure


class SocketCANBridge:
    """
    Bidirectional SocketCAN bridge for MALE UAV Ground Control Stations.
    Transmits and ingests standardized binary CAN frames.
    """

    def __init__(self, channel: str = "vcan0", bustype: Optional[str] = None):
        self.channel = channel
        self.bustype = bustype
        self.bus = None
        self._connected = False
        self._frames_tx = 0
        self._frames_rx = 0
        self._last_rx_telemetry: Dict[str, float] = {}

    def connect(self) -> bool:
        """Attempts connection to SocketCAN or falls back to virtual interface."""
        try:
            import can
            if self.bustype is None:
                # Detect platform: on Linux use socketcan, on Windows/macOS use virtual
                import sys
                self.bustype = "socketcan" if sys.platform.startswith("linux") else "virtual"
                if self.bustype == "virtual" and self.channel == "vcan0":
                    self.channel = "virtual_ch0"

            self.bus = can.interface.Bus(channel=self.channel, bustype=self.bustype)
            self._connected = True
            logger.info(f"SocketCAN attached: channel={self.channel}, bustype={self.bustype}")
            return True
        except Exception as e:
            logger.warning(f"Could not initialize CAN interface ({self.channel}, {self.bustype}): {e}")
            self._connected = False
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def pack_frames(self, telem: Dict[str, float]) -> list:
        """Packs engineering units into standardized 8-byte CAN 2.0B frames."""
        import can
        frames = []

        rpm = float(telem.get("ENGINE_RPM", telem.get("rpm", 5200.0)))
        cht = float(telem.get("CHT_1", telem.get("cht", 135.0)))
        egt = float(telem.get("EGT_1", telem.get("egt", 750.0)))
        oil_p = float(telem.get("OIL_PRESSURE", telem.get("oil_pressure", 4.8)))
        oil_t = float(telem.get("OIL_TEMP", telem.get("oil_temp", 95.0)))
        map_kpa = float(telem.get("MAP", telem.get("manifold_pressure", 102.0)))
        fuel_flow = float(telem.get("FUEL_FLOW", telem.get("fuel_flow", 22.0)))

        # 1. PGN 61444 (EEC1) - Engine Speed (0.125 rpm/bit, uint16)
        rpm_raw = int(min(65535, max(0, rpm / 0.125)))
        eec1_bytes = struct.pack("<BBHBBBB", 0xF0, 0x7D, rpm_raw, 0xFF, 0xFF, 0xFF, 0xFF)
        frames.append(can.Message(arbitration_id=PGN_EEC1, data=eec1_bytes, is_extended_id=True))

        # 2. PGN 65262 (ET1) - CHT (offset -40°C, 1°C/bit) & Oil Temp
        cht_raw = int(min(255, max(0, cht + 40.0)))
        oil_t_raw = int(min(255, max(0, oil_t + 40.0)))
        et1_bytes = struct.pack("<BBBBBBBB", cht_raw, 0xFF, oil_t_raw, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF)
        frames.append(can.Message(arbitration_id=PGN_ET1, data=et1_bytes, is_extended_id=True))

        # 3. PGN 65263 (EFL1) - Oil Pressure (4 kPa/bit)
        oil_p_kpa = oil_p * 100.0  # bar to kPa
        oil_p_raw = int(min(255, max(0, oil_p_kpa / 4.0)))
        efl1_bytes = struct.pack("<BBBBBBBB", 0xFF, 0xFF, 0xFF, oil_p_raw, 0xFF, 0xFF, 0xFF, 0xFF)
        frames.append(can.Message(arbitration_id=PGN_EFL1, data=efl1_bytes, is_extended_id=True))

        # 4. PGN 65032 (EGT) - Exhaust Gas Temp (0.03125 °C/bit, offset -273°C)
        egt_raw = int(min(65535, max(0, (egt + 273.0) / 0.03125)))
        egt_bytes = struct.pack("<HBBBBBB", egt_raw, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF)
        frames.append(can.Message(arbitration_id=PGN_EGT, data=egt_bytes, is_extended_id=True))

        # 5. PGN 65241 (TURBO) - Boost / MAP Pressure (2 kPa/bit)
        map_raw = int(min(255, max(0, map_kpa / 2.0)))
        turbo_bytes = struct.pack("<BBBBBBBB", map_raw, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF)
        frames.append(can.Message(arbitration_id=PGN_TURBO, data=turbo_bytes, is_extended_id=True))

        return frames

    def send_telemetry(self, telem: Dict[str, float]) -> int:
        """Sends all telemetry frames on the bus."""
        if not self._connected or self.bus is None:
            return 0
        frames = self.pack_frames(telem)
        count = 0
        for f in frames:
            try:
                self.bus.send(f)
                count += 1
                self._frames_tx += 1
            except Exception as e:
                logger.error(f"CAN frame send failed: {e}")
        return count

    def decode_frame(self, msg) -> Optional[Tuple[str, float]]:
        """Decodes raw CAN frame to canonical engineering parameter."""
        data = bytes(msg.data)
        arb_id = msg.arbitration_id

        if arb_id == PGN_EEC1 and len(data) >= 4:
            rpm_raw = struct.unpack("<H", data[2:4])[0]
            rpm = rpm_raw * 0.125
            return ("ENGINE_RPM", round(rpm, 1))

        elif arb_id == PGN_ET1 and len(data) >= 3:
            cht = float(data[0]) - 40.0
            oil_t = float(data[2]) - 40.0
            self._last_rx_telemetry["OIL_TEMP"] = oil_t
            return ("CHT_1", round(cht, 1))

        elif arb_id == PGN_EFL1 and len(data) >= 4:
            oil_p_kpa = float(data[3]) * 4.0
            oil_p_bar = oil_p_kpa / 100.0
            return ("OIL_PRESSURE", round(oil_p_bar, 2))

        elif arb_id == PGN_EGT and len(data) >= 2:
            egt_raw = struct.unpack("<H", data[0:2])[0]
            egt = (egt_raw * 0.03125) - 273.0
            return ("EGT_1", round(egt, 1))

        elif arb_id == PGN_TURBO and len(data) >= 1:
            map_kpa = float(data[0]) * 2.0
            return ("MAP", round(map_kpa, 1))

        return None

    def read_telemetry(self, timeout: float = 0.05) -> Dict[str, float]:
        """Reads incoming frames up to timeout and updates state dictionary."""
        if not self._connected or self.bus is None:
            return dict(self._last_rx_telemetry)

        t_start = time.time()
        while time.time() - t_start < timeout:
            msg = self.bus.recv(timeout=0.01)
            if msg is None:
                break
            self._frames_rx += 1
            decoded = self.decode_frame(msg)
            if decoded:
                key, val = decoded
                self._last_rx_telemetry[key] = val

        return dict(self._last_rx_telemetry)

    def stats(self) -> dict:
        return {
            "channel": self.channel,
            "bustype": self.bustype,
            "connected": self._connected,
            "frames_tx": self._frames_tx,
            "frames_rx": self._frames_rx,
            "active_channels": list(self._last_rx_telemetry.keys())
        }
