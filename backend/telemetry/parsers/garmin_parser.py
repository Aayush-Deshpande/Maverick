"""
Garmin G3X & G1000 Flight Data Log Parser (Source 1)
DRDO / iDEX Problem Statement ID: 26054

Parses standard General Aviation Garmin G3X/G1000 CSV flight logs
and normalizes column headers to the canonical 27-parameter data dictionary.
"""

import csv
import os
from typing import List, Dict, Any, Optional
from backend.physics.thermo_model import EnginePhysicalState


class GarminG3XParser:
    """
    Ingests and normalizes real-world Garmin G3X and G1000 flight data logs.
    Handles standard Garmin column naming conventions (e.g. 'E1 CHT1', 'E1 OilP').
    """

    # Garmin G3X standard column mapping to canonical parameter dictionary
    HEADER_MAPPING = {
        "E1 RPM": "ENGINE_RPM",
        "RPM": "ENGINE_RPM",
        "E1 CHT1": "CHT_1",
        "CHT1": "CHT_1",
        "E1 CHT2": "CHT_2",
        "CHT2": "CHT_2",
        "E1 CHT3": "CHT_3",
        "CHT3": "CHT_3",
        "E1 CHT4": "CHT_4",
        "CHT4": "CHT_4",
        "E1 EGT1": "EGT_1",
        "EGT1": "EGT_1",
        "E1 EGT2": "EGT_2",
        "EGT2": "EGT_2",
        "E1 EGT3": "EGT_3",
        "EGT3": "EGT_3",
        "E1 EGT4": "EGT_4",
        "EGT4": "EGT_4",
        "E1 OilP": "OIL_PRESS",
        "OilP": "OIL_PRESS",
        "OILP": "OIL_PRESS",
        "E1 OilT": "OIL_TEMP",
        "OilT": "OIL_TEMP",
        "OILT": "OIL_TEMP",
        "E1 FFlow": "FUEL_FLOW",
        "FFlow": "FUEL_FLOW",
        "FFLOW": "FUEL_FLOW",
        "E1 MAP": "MAP",
        "MAP": "MAP",
        "AltB": "ALTITUDE_FT",
        "AltMSL": "ALTITUDE_FT",
        "ALT": "ALTITUDE_FT",
        "OAT": "OAT_C",
        "IAS": "TAS_KNOTS",
        "TAS": "TAS_KNOTS",
        "Volt1": "BUS_VOLTAGE",
        "Volts": "BUS_VOLTAGE",
        "Amp1": "BATTERY_CURRENT",
        "Amps": "BATTERY_CURRENT",
        "VibRMS": "VIB_GEARBOX_RMS"
    }

    def __init__(self):
        pass

    def parse_csv_file(self, filepath: str) -> List[EnginePhysicalState]:
        """
        Parses a Garmin G3X flight CSV file into a list of EnginePhysicalState objects.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Garmin log file not found: {filepath}")

        records: List[EnginePhysicalState] = []
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            
            # Skip any preliminary comment lines (e.g. #airframe, #date)
            header_row = None
            for row in reader:
                if row and not row[0].startswith("#") and any("RPM" in col or "CHT" in col for col in row):
                    header_row = [col.strip() for col in row]
                    break

            if not header_row:
                raise ValueError(f"Could not find valid Garmin avionics header row in {filepath}")

            # Map column indices to canonical dictionary keys
            col_map: Dict[int, str] = {}
            for idx, col_name in enumerate(header_row):
                clean_name = col_name.strip()
                if clean_name in self.HEADER_MAPPING:
                    col_map[idx] = self.HEADER_MAPPING[clean_name]

            # Parse data rows
            time_counter = 0.0
            for row in reader:
                if not row or len(row) < len(col_map):
                    continue

                state_dict: Dict[str, Any] = {}
                for idx, key in col_map.items():
                    if idx < len(row):
                        try:
                            val_str = row[idx].strip()
                            if val_str:
                                state_dict[key] = float(val_str)
                        except ValueError:
                            pass

                # Apply default fills for missing avionics fields
                rpm = state_dict.get("ENGINE_RPM", 5000.0)
                prop_rpm = rpm / 2.43
                
                # Temperature conversion check: if oil temp > 150, it's in Fahrenheit -> convert to Celsius
                oil_temp = state_dict.get("OIL_TEMP", 90.0)
                if oil_temp > 150.0:
                    oil_temp = (oil_temp - 32.0) * 5.0 / 9.0
                    
                cht_1 = state_dict.get("CHT_1", 95.0)
                if cht_1 > 160.0: # Fahrenheit
                    cht_1 = (cht_1 - 32.0) * 5.0 / 9.0
                cht_2 = state_dict.get("CHT_2", 95.0)
                if cht_2 > 160.0:
                    cht_2 = (cht_2 - 32.0) * 5.0 / 9.0
                cht_3 = state_dict.get("CHT_3", 95.0)
                if cht_3 > 160.0:
                    cht_3 = (cht_3 - 32.0) * 5.0 / 9.0
                cht_4 = state_dict.get("CHT_4", 95.0)
                if cht_4 > 160.0:
                    cht_4 = (cht_4 - 32.0) * 5.0 / 9.0

                time_counter += 1.0 # Standard Garmin 1 Hz sample interval

                record = EnginePhysicalState(
                    ENGINE_RPM=round(rpm, 1),
                    PROP_RPM=round(prop_rpm, 1),
                    TPS=round(state_dict.get("TPS", 68.0), 1),
                    CHT_1=round(cht_1, 2),
                    CHT_2=round(cht_2, 2),
                    CHT_3=round(cht_3, 2),
                    CHT_4=round(cht_4, 2),
                    EGT_1=round(state_dict.get("EGT_1", 780.0), 2),
                    EGT_2=round(state_dict.get("EGT_2", 780.0), 2),
                    EGT_3=round(state_dict.get("EGT_3", 780.0), 2),
                    EGT_4=round(state_dict.get("EGT_4", 780.0), 2),
                    OIL_PRESS=round(state_dict.get("OIL_PRESS", 3.8), 2),
                    OIL_TEMP=round(oil_temp, 2),
                    FUEL_FLOW=round(state_dict.get("FUEL_FLOW", 18.5), 2),
                    FUEL_RAIL_P=3.0,
                    MAP=round(state_dict.get("MAP", 90.0), 2),
                    VIB_GEARBOX_RMS=round(state_dict.get("VIB_GEARBOX_RMS", 0.55), 3),
                    BUS_VOLTAGE=round(state_dict.get("BUS_VOLTAGE", 14.1), 2),
                    BATTERY_CURRENT=round(state_dict.get("BATTERY_CURRENT", 3.5), 2),
                    FADEC_ACTIVE_LANE="LANE_A",
                    ALTITUDE_FT=round(state_dict.get("ALTITUDE_FT", 8500.0), 0),
                    OAT_C=round(state_dict.get("OAT_C", 12.0), 1),
                    TAS_KNOTS=round(state_dict.get("TAS_KNOTS", 92.0), 1),
                    FLIGHT_PHASE="CRUISE_LOITER",
                    HEALTH_INDEX=1.0,
                    FAULT_ID=0,
                    RUL_HOURS=500.0,
                    TIMESTAMP_SEC=time_counter
                )
                records.append(record)

        return records
