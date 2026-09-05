"""
Rotax 912 iS High-Fidelity Physics-Correlated Time-Series Dataset Generator
DRDO / iDEX Problem Statement ID: 26054

Generates authentic, coupled, multi-parameter time-series datasets modeling
continuous differential equations, thermal capacitance lags, fluid dynamics,
and coherent fault progressions for all 8 DRDO failure modes across Indian operational theaters.

Supports strict Mission-Level Dataset Partitioning (Train, Validation, and Test isolation).
"""

import os
import csv
import json
import math
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional
from backend.physics.thermo_model import RotaxThermoModel, EnginePhysicalState, ResidualVector
from backend.telemetry.can_streamer import DRDO_FAULT_DEFINITIONS


class RotaxTimeSeriesGenerator:
    """
    High-fidelity time-series engine with coupled first-order differential equations:
    - Crankshaft rotational inertia & throttle coupling
    - Fluid manifold induction & air-fuel stoichiometry
    - Thermal capacitance & convective cooling dissipation (CHT & EGT)
    - Oil temperature-viscosity-pressure coupling
    - Propeller reduction 3rd harmonic spectral vibration
    - Dual FADEC electrical bus & battery charging balance
    """

    def __init__(self, output_dir: Optional[str] = None):
        if output_dir is None:
            self.output_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../../data/telemetry")
            )
        else:
            self.output_dir = output_dir

        self.train_dir = os.path.join(self.output_dir, "train")
        self.val_dir = os.path.join(self.output_dir, "val")
        self.test_dir = os.path.join(self.output_dir, "test")

        os.makedirs(self.train_dir, exist_ok=True)
        os.makedirs(self.val_dir, exist_ok=True)
        os.makedirs(self.test_dir, exist_ok=True)

        self.thermo_model = RotaxThermoModel()

    def generate_mission_sortie(
        self,
        mission_id: str,
        split_type: str = "TRAIN", # "TRAIN", "VAL", "TEST"
        theater: str = "LADAKH",
        duration_sec: float = 45.0,
        sample_rate_hz: float = 20.0,
        fault_id: int = 0,
        fault_start_sec: float = 15.0,
        fault_ramp_sec: float = 15.0,
        throttle_pattern: str = "SMOOTH_LOITER", # "SMOOTH_LOITER", "GUST_TRANSIENTS", "STEP_LOITER"
        alt_offset_ft: float = 0.0,
        oat_offset_c: float = 0.0,
        noise_multiplier: float = 1.0,
        seed: int = 42
    ) -> List[Dict[str, Any]]:
        """
        Generates an isolated, continuous time-series sortie with realistic parameter coupling.
        """
        random.seed(seed)
        dt = 1.0 / sample_rate_hz
        total_steps = int(duration_sec * sample_rate_hz)

        # Environmental baseline
        if theater == "LADAKH":
            base_alt = 20000.0 + alt_offset_ft   # 17k - 23k ft
            base_oat = -22.0 + oat_offset_c     # Sub-zero cold (-30 to -14°C)
            alt_drift = 250.0
        elif theater == "THAR_DESERT":
            base_alt = 3500.0 + alt_offset_ft    # 2k - 6k ft
            base_oat = 44.0 + oat_offset_c      # Extreme heat (+38 to +50°C)
            alt_drift = 120.0
        else: # COASTAL / DECCAN
            base_alt = 2500.0 + alt_offset_ft
            base_oat = 28.0 + oat_offset_c
            alt_drift = 80.0

        # State Variables (Initial Conditions)
        current_rpm = 5120.0 + random.gauss(0, 15.0)
        current_tps = 72.0
        current_map = 88.0
        current_cht = [
            (92.0 if theater == "LADAKH" else 106.0) + random.gauss(0, 0.5) for _ in range(4)
        ]
        current_egt = [780.0 + random.gauss(0, 2.0) for _ in range(4)]
        current_oil_temp = (88.0 if theater == "LADAKH" else 102.0) + random.gauss(0, 0.8)
        current_oil_press = 3.85
        current_vib = 0.48
        current_bus_v = 14.12
        current_bat_i = 3.5
        current_fuel_flow = 18.2
        current_rul = 450.0

        fault_active = False
        fault_severity = 0.0

        records = []

        for step in range(total_steps):
            t_sec = step * dt

            # 1. Flight Phase & Dynamic Throttle Pattern
            if t_sec < 4.0:
                phase = "CLIMB"
                target_tps = 84.0 + 2.0 * math.sin(t_sec * 0.5)
                target_tas = 92.0
                altitude = base_alt - 600.0 + (t_sec / 4.0) * 600.0
            elif t_sec < duration_sec - 6.0:
                phase = "CRUISE_LOITER"
                if throttle_pattern == "SMOOTH_LOITER":
                    target_tps = 72.0 + 2.5 * math.sin(t_sec * 0.15)
                    target_tas = 88.0 + 1.2 * math.cos(t_sec * 0.15)
                elif throttle_pattern == "GUST_TRANSIENTS":
                    # Unseen wind gusts causing rapid throttle hunting
                    target_tps = 72.0 + 4.5 * math.sin(t_sec * 0.45) + random.gauss(0, 1.2)
                    target_tas = 88.0 + 3.0 * math.cos(t_sec * 0.45)
                else: # STEP_LOITER
                    target_tps = 68.0 if (int(t_sec / 8.0) % 2 == 0) else 76.0
                    target_tas = 84.0 if (int(t_sec / 8.0) % 2 == 0) else 91.0

                altitude = base_alt + (alt_drift * math.sin(t_sec * 0.08))
            else:
                phase = "DESCENT_RECOVERY"
                target_tps = 56.0
                target_tas = 80.0
                altitude = base_alt - ((t_sec - (duration_sec - 6.0)) / 6.0) * 800.0

            # Ambient weather lapse
            oat = base_oat - (0.00198 * (altitude - base_alt)) + (0.15 * math.sin(t_sec * 0.2))
            p_amb, t_kelvin, rho_air = self.thermo_model.get_ambient_properties(altitude, oat)

            # 2. Coupled Throttle & Manifold Pressure Dynamics (tau_map = 0.15s)
            current_tps += (target_tps - current_tps) * (dt / 0.35)
            target_map = 35.0 + (p_amb - 38.0) * ((current_tps / 100.0) ** 0.85)
            current_map += (target_map - current_map) * (dt / 0.15) + random.gauss(0, 0.08 * noise_multiplier)

            # 3. Coupled Engine RPM Inertia Dynamics (tau_rpm = 0.4s)
            target_rpm = 4200.0 + (current_tps / 100.0) * 1600.0
            current_rpm += (target_rpm - current_rpm) * (dt / 0.40) + random.gauss(0, 4.5 * noise_multiplier)
            prop_rpm = current_rpm / 2.43

            # 4. Coupled Fuel Flow Stoichiometry (tau_ff = 0.2s)
            m_dot_air = 1.352 * (current_rpm / 120.0) * rho_air * (current_tps / 100.0)
            target_ff = (m_dot_air / (14.7 * 0.72)) * 3.6
            current_fuel_flow += (target_ff - current_fuel_flow) * (dt / 0.20) + random.gauss(0, 0.06 * noise_multiplier)

            # 5. Fault Onset & Dynamic Severity Ramp
            if fault_id > 0 and t_sec >= fault_start_sec:
                fault_active = True
                elapsed_fault = t_sec - fault_start_sec
                fault_severity = min(1.0, elapsed_fault / max(1.0, fault_ramp_sec))

            # Coherent Multi-Signal Fault Parameters
            cyl2_baffle_delta = 0.0
            cyl1_fuel_trim = 1.0
            misfire_rpm_flutter = 0.0
            oil_leak_factor = 0.0
            gearbox_wear_mult = 1.0
            egt3_runner_delta = 0.0
            alt_diode_sag = 0.0
            map_drift_error = 0.0

            if fault_active:
                if fault_id == 1:   # CYLINDER_2_CHT_OVERHEAT
                    cyl2_baffle_delta = 42.0 * fault_severity
                elif fault_id == 2: # FUEL_INJECTOR_1_CLOG
                    cyl1_fuel_trim = 1.0 - (0.24 * fault_severity)
                    current_fuel_flow *= (1.0 - 0.06 * fault_severity)
                elif fault_id == 3: # IGNITION_MISFIRE
                    misfire_rpm_flutter = random.gauss(0, 160.0 * fault_severity)
                    current_rpm += misfire_rpm_flutter
                elif fault_id == 4: # OIL_PRESSURE_LOSS
                    oil_leak_factor = 2.1 * fault_severity
                elif fault_id == 5: # GEARBOX_VIBRATION
                    gearbox_wear_mult = 1.0 + (5.8 * fault_severity)
                elif fault_id == 6: # EXHAUST_EGT_IMBALANCE
                    egt3_runner_delta = 85.0 * fault_severity
                elif fault_id == 7: # ALTERNATOR_VOLTAGE_SAG
                    alt_diode_sag = 1.85 * fault_severity
                elif fault_id == 8: # DUAL_FADEC_ECU_DRIFT
                    map_drift_error = 8.5 * fault_severity

            # 6. Coupled EGT Fast Dynamics (tau_egt = 0.35s)
            base_egt = 760.0 + 35.0 * math.sin((current_tps / 100.0) * math.pi) + (0.15 * oat)
            for i in range(4):
                target_cyl_egt = base_egt + random.gauss(0, 1.5 * noise_multiplier)
                if i == 0 and fault_id == 2:
                    target_cyl_egt += 75.0 * fault_severity
                elif i == 1 and fault_id == 3:
                    target_cyl_egt -= 115.0 * fault_severity
                elif i == 2 and fault_id == 6:
                    target_cyl_egt += egt3_runner_delta

                current_egt[i] += (target_cyl_egt - current_egt[i]) * (dt / 0.35)

            # 7. Coupled CHT Thermal Capacitance Dynamics (tau_cht = 6.5s)
            heat_gen = (current_fuel_flow / 18.5) * ((current_rpm / 5000.0) ** 1.1)
            cooling_dissipation = (0.75 * (rho_air / 1.225) * (target_tas / 85.0)) + 0.25
            base_cht = oat + 75.0 + (35.0 * (heat_gen / max(0.2, cooling_dissipation)))

            for i in range(4):
                target_cyl_cht = base_cht + random.gauss(0, 0.4 * noise_multiplier)
                if i == 1 and fault_id == 1:
                    target_cyl_cht += cyl2_baffle_delta

                current_cht[i] += (target_cyl_cht - current_cht[i]) * (dt / 6.5)

            # 8. Coupled Oil Temperature, Viscosity & Pressure (tau_oil = 35s)
            target_oil_t = 82.0 + 0.35 * (sum(current_cht) / 4.0 - 90.0) + (12.0 * (current_rpm / 5800.0) ** 2.0)
            if fault_id == 4:
                target_oil_t += 18.0 * fault_severity
            current_oil_temp += (target_oil_t - current_oil_temp) * (dt / 35.0) + random.gauss(0, 0.08 * noise_multiplier)

            viscosity_factor = math.exp(-0.015 * (current_oil_temp - 80.0))
            base_oil_p = 2.2 + 2.3 * (current_rpm / 5000.0) * viscosity_factor
            current_oil_press = max(1.2, base_oil_p - oil_leak_factor + random.gauss(0, 0.025 * noise_multiplier))

            # 9. Coupled Gearbox 3rd Harmonic Vibration
            base_vib = 0.38 + 0.32 * ((current_rpm / 5000.0) ** 2.0)
            current_vib = (base_vib * gearbox_wear_mult) + random.gauss(0, 0.035 * noise_multiplier)

            # 10. Alternator DC Bus Voltage & Battery Current Balance
            base_bus_v = 14.12 - (0.08 * (current_tps / 100.0))
            current_bus_v = max(11.8, base_bus_v - alt_diode_sag + random.gauss(0, 0.015 * noise_multiplier))
            if current_bus_v < 12.8:
                current_bat_i = -12.5 * ((12.8 - current_bus_v) / 0.8) + random.gauss(0, 0.2 * noise_multiplier)
            else:
                current_bat_i = 3.2 + random.gauss(0, 0.15 * noise_multiplier)

            # 11. Assembly & Residual Computation
            active_lane = "LANE_B" if (fault_id in [2, 3, 8] and fault_severity > 0.8) else "LANE_A"
            if fault_active:
                health_index = max(0.05, 1.0 - (0.85 * fault_severity))
                rul_min_map = {
                    1: 1.5,   # CHT Thermal Runaway
                    2: 5.0,   # Injector Clog
                    3: 8.0,   # Misfire
                    4: 0.8,   # Oil Pressure Loss
                    5: 12.0,  # Gearbox Tooth Pitting
                    6: 18.0,  # EGT Imbalance
                    7: 4.0,   # Alternator Sag
                    8: 24.0,  # FADEC MAP Drift
                }
                min_rul = rul_min_map.get(fault_id, 10.0)
                current_rul = round(max(min_rul, 450.0 - (450.0 - min_rul) * fault_severity), 1)
            else:
                health_index = 1.0
                current_rul = max(100.0, current_rul - (dt / 3600.0))

            # Ground truth fault label assignment
            assigned_fault = fault_id if (fault_active and fault_severity > 0.30) else 0

            actual_state = EnginePhysicalState(
                ENGINE_RPM=round(current_rpm, 1),
                PROP_RPM=round(prop_rpm, 1),
                TPS=round(current_tps, 1),
                CHT_1=round(current_cht[0], 2),
                CHT_2=round(current_cht[1], 2),
                CHT_3=round(current_cht[2], 2),
                CHT_4=round(current_cht[3], 2),
                EGT_1=round(current_egt[0], 2),
                EGT_2=round(current_egt[1], 2),
                EGT_3=round(current_egt[2], 2),
                EGT_4=round(current_egt[3], 2),
                OIL_PRESS=round(current_oil_press, 2),
                OIL_TEMP=round(current_oil_temp, 2),
                FUEL_FLOW=round(current_fuel_flow, 2),
                FUEL_RAIL_P=3.0,
                MAP=round(current_map + map_drift_error, 2),
                VIB_GEARBOX_RMS=round(current_vib, 3),
                BUS_VOLTAGE=round(current_bus_v, 2),
                BATTERY_CURRENT=round(current_bat_i, 2),
                FADEC_ACTIVE_LANE=active_lane,
                ALTITUDE_FT=round(altitude, 0),
                OAT_C=round(oat, 1),
                TAS_KNOTS=round(target_tas, 1),
                FLIGHT_PHASE=phase,
                HEALTH_INDEX=round(health_index, 3),
                FAULT_ID=assigned_fault,
                RUL_HOURS=round(current_rul, 1),
                TIMESTAMP_SEC=round(t_sec, 2)
            )

            expected_state = self.thermo_model.compute_expected_state(
                altitude_ft=actual_state.ALTITUDE_FT,
                oat_c=actual_state.OAT_C,
                rpm=actual_state.ENGINE_RPM,
                tps=actual_state.TPS,
                tas_knots=actual_state.TAS_KNOTS
            )
            residuals = self.thermo_model.compute_residuals(actual_state, expected_state)

            records.append({
                "actual": actual_state,
                "expected": expected_state,
                "residuals": residuals,
                "theater": theater,
                "mission_id": mission_id,
                "split_type": split_type
            })

        return records

    def export_mission_to_csv(self, records: List[Dict[str, Any]], filepath: str):
        """Writes sortie records to standard CSV with telemetry and residual features."""
        fieldnames = [
            "TIMESTAMP_SEC", "MISSION_ID", "SPLIT_TYPE", "THEATER", "FLIGHT_PHASE",
            "ENGINE_RPM", "PROP_RPM", "TPS",
            "CHT_1", "CHT_2", "CHT_3", "CHT_4",
            "EGT_1", "EGT_2", "EGT_3", "EGT_4",
            "OIL_PRESS", "OIL_TEMP", "FUEL_FLOW", "FUEL_RAIL_P", "MAP",
            "VIB_GEARBOX_RMS", "BUS_VOLTAGE", "BATTERY_CURRENT", "FADEC_ACTIVE_LANE",
            "ALTITUDE_FT", "OAT_C", "TAS_KNOTS",
            "HEALTH_INDEX", "FAULT_ID", "RUL_HOURS",
            # 14-D Residual Features (Instantaneous, Causal)
            "RES_d_CHT_1", "RES_d_CHT_2", "RES_d_CHT_3", "RES_d_CHT_4",
            "RES_d_EGT_1", "RES_d_EGT_2", "RES_d_EGT_3", "RES_d_EGT_4",
            "RES_d_OIL_PRESS", "RES_d_OIL_TEMP", "RES_d_FUEL_FLOW", "RES_d_MAP",
            "RES_d_VIB_RMS", "RES_d_BUS_VOLTAGE",
            "RES_ANOMALY_SCORE", "RES_IS_ANOMALY"
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                act: EnginePhysicalState = r["actual"]
                res: ResidualVector = r["residuals"]
                writer.writerow({
                    "TIMESTAMP_SEC": act.TIMESTAMP_SEC,
                    "MISSION_ID": r["mission_id"],
                    "SPLIT_TYPE": r.get("split_type", "TRAIN"),
                    "THEATER": r["theater"],
                    "FLIGHT_PHASE": act.FLIGHT_PHASE,
                    "ENGINE_RPM": act.ENGINE_RPM,
                    "PROP_RPM": act.PROP_RPM,
                    "TPS": act.TPS,
                    "CHT_1": act.CHT_1,
                    "CHT_2": act.CHT_2,
                    "CHT_3": act.CHT_3,
                    "CHT_4": act.CHT_4,
                    "EGT_1": act.EGT_1,
                    "EGT_2": act.EGT_2,
                    "EGT_3": act.EGT_3,
                    "EGT_4": act.EGT_4,
                    "OIL_PRESS": act.OIL_PRESS,
                    "OIL_TEMP": act.OIL_TEMP,
                    "FUEL_FLOW": act.FUEL_FLOW,
                    "FUEL_RAIL_P": act.FUEL_RAIL_P,
                    "MAP": act.MAP,
                    "VIB_GEARBOX_RMS": act.VIB_GEARBOX_RMS,
                    "BUS_VOLTAGE": act.BUS_VOLTAGE,
                    "BATTERY_CURRENT": act.BATTERY_CURRENT,
                    "FADEC_ACTIVE_LANE": act.FADEC_ACTIVE_LANE,
                    "ALTITUDE_FT": act.ALTITUDE_FT,
                    "OAT_C": act.OAT_C,
                    "TAS_KNOTS": act.TAS_KNOTS,
                    "HEALTH_INDEX": act.HEALTH_INDEX,
                    "FAULT_ID": act.FAULT_ID,
                    "RUL_HOURS": act.RUL_HOURS,
                    "RES_d_CHT_1": res.d_CHT_1,
                    "RES_d_CHT_2": res.d_CHT_2,
                    "RES_d_CHT_3": res.d_CHT_3,
                    "RES_d_CHT_4": res.d_CHT_4,
                    "RES_d_EGT_1": res.d_EGT_1,
                    "RES_d_EGT_2": res.d_EGT_2,
                    "RES_d_EGT_3": res.d_EGT_3,
                    "RES_d_EGT_4": res.d_EGT_4,
                    "RES_d_OIL_PRESS": res.d_OIL_PRESS,
                    "RES_d_OIL_TEMP": res.d_OIL_TEMP,
                    "RES_d_FUEL_FLOW": res.d_FUEL_FLOW,
                    "RES_d_MAP": res.d_MAP,
                    "RES_d_VIB_RMS": res.d_VIB_RMS,
                    "RES_d_BUS_VOLTAGE": res.d_BUS_VOLTAGE,
                    "RES_ANOMALY_SCORE": res.anomaly_score,
                    "RES_IS_ANOMALY": 1 if res.is_anomaly else 0
                })

    def generate_partitioned_dataset_suite(self) -> Dict[str, Any]:
        """
        Generates 3 strictly isolated partitions:
        - 10 Training Missions (Train Set)
        - 10 Validation Missions (Validation Set — distinct altitudes, thermal offsets, seeds)
        - 10 Test Missions (Test Set — gusty wind turbulence, distinct onset timings, unseen seeds)
        """
        partition_configs = [
            # --- 1. TRAINING MISSIONS (10 Sorties) ---
            ("TRAIN", [
                ("TRAIN_M01_LADAKH_NOMINAL", "LADAKH", 0, 0.0, 15.0, "SMOOTH_LOITER", 0.0, 0.0, 1.0, 101),
                ("TRAIN_M02_THAR_NOMINAL", "THAR_DESERT", 0, 0.0, 15.0, "SMOOTH_LOITER", 0.0, 0.0, 1.0, 102),
                ("TRAIN_M03_LADAKH_FAULT01_OVERHEAT", "LADAKH", 1, 12.0, 15.0, "SMOOTH_LOITER", 0.0, 0.0, 1.0, 103),
                ("TRAIN_M04_LADAKH_FAULT02_INJECTOR", "LADAKH", 2, 12.0, 15.0, "SMOOTH_LOITER", 0.0, 0.0, 1.0, 104),
                ("TRAIN_M05_LADAKH_FAULT03_MISFIRE", "LADAKH", 3, 12.0, 15.0, "SMOOTH_LOITER", 0.0, 0.0, 1.0, 105),
                ("TRAIN_M06_THAR_FAULT04_OIL_PRESS", "THAR_DESERT", 4, 12.0, 15.0, "SMOOTH_LOITER", 0.0, 0.0, 1.0, 106),
                ("TRAIN_M07_LADAKH_FAULT05_GEARBOX", "LADAKH", 5, 12.0, 15.0, "SMOOTH_LOITER", 0.0, 0.0, 1.0, 107),
                ("TRAIN_M08_LADAKH_FAULT06_EGT_IMBAL", "LADAKH", 6, 12.0, 15.0, "SMOOTH_LOITER", 0.0, 0.0, 1.0, 108),
                ("TRAIN_M09_THAR_FAULT07_ALT_SAG", "THAR_DESERT", 7, 12.0, 15.0, "SMOOTH_LOITER", 0.0, 0.0, 1.0, 109),
                ("TRAIN_M10_LADAKH_FAULT08_FADEC_DRIFT", "LADAKH", 8, 12.0, 15.0, "SMOOTH_LOITER", 0.0, 0.0, 1.0, 110),
            ]),
            # --- 2. VALIDATION MISSIONS (10 Sorties — Shifted Altitudes & Thermal Offsets) ---
            ("VAL", [
                ("VAL_M01_LADAKH_NOMINAL", "LADAKH", 0, 0.0, 15.0, "STEP_LOITER", 2200.0, -4.5, 1.2, 201),
                ("VAL_M02_THAR_NOMINAL", "THAR_DESERT", 0, 0.0, 15.0, "STEP_LOITER", -800.0, +3.5, 1.2, 202),
                ("VAL_M03_LADAKH_FAULT01_OVERHEAT", "LADAKH", 1, 16.0, 12.0, "STEP_LOITER", 1500.0, -3.0, 1.2, 203),
                ("VAL_M04_LADAKH_FAULT02_INJECTOR", "LADAKH", 2, 16.0, 12.0, "STEP_LOITER", 1800.0, -2.5, 1.2, 204),
                ("VAL_M05_LADAKH_FAULT03_MISFIRE", "LADAKH", 3, 16.0, 12.0, "STEP_LOITER", -1200.0, +2.0, 1.2, 205),
                ("VAL_M06_THAR_FAULT04_OIL_PRESS", "THAR_DESERT", 4, 16.0, 12.0, "STEP_LOITER", +900.0, +4.0, 1.2, 206),
                ("VAL_M07_LADAKH_FAULT05_GEARBOX", "LADAKH", 5, 16.0, 12.0, "STEP_LOITER", +2500.0, -5.0, 1.2, 207),
                ("VAL_M08_LADAKH_FAULT06_EGT_IMBAL", "LADAKH", 6, 16.0, 12.0, "STEP_LOITER", -1500.0, +1.5, 1.2, 208),
                ("VAL_M09_THAR_FAULT07_ALT_SAG", "THAR_DESERT", 7, 16.0, 12.0, "STEP_LOITER", +1100.0, +2.5, 1.2, 209),
                ("VAL_M10_LADAKH_FAULT08_FADEC_DRIFT", "LADAKH", 8, 16.0, 12.0, "STEP_LOITER", +1900.0, -3.8, 1.2, 210),
            ]),
            # --- 3. TEST MISSIONS (10 Sorties — Gusty Wind Transients, Distinct Onset Ramps) ---
            ("TEST", [
                ("TEST_M01_LADAKH_NOMINAL", "LADAKH", 0, 0.0, 15.0, "GUST_TRANSIENTS", -2000.0, +3.0, 1.5, 301),
                ("TEST_M02_THAR_NOMINAL", "THAR_DESERT", 0, 0.0, 15.0, "GUST_TRANSIENTS", +1500.0, -2.5, 1.5, 302),
                ("TEST_M03_LADAKH_FAULT01_OVERHEAT", "LADAKH", 1, 10.0, 20.0, "GUST_TRANSIENTS", +2800.0, -6.0, 1.5, 303),
                ("TEST_M04_LADAKH_FAULT02_INJECTOR", "LADAKH", 2, 10.0, 20.0, "GUST_TRANSIENTS", -2200.0, +4.0, 1.5, 304),
                ("TEST_M05_LADAKH_FAULT03_MISFIRE", "LADAKH", 3, 10.0, 20.0, "GUST_TRANSIENTS", +1600.0, -3.2, 1.5, 305),
                ("TEST_M06_THAR_FAULT04_OIL_PRESS", "THAR_DESERT", 4, 10.0, 20.0, "GUST_TRANSIENTS", -1000.0, +5.0, 1.5, 306),
                ("TEST_M07_LADAKH_FAULT05_GEARBOX", "LADAKH", 5, 10.0, 20.0, "GUST_TRANSIENTS", +3000.0, -7.0, 1.5, 307),
                ("TEST_M08_LADAKH_FAULT06_EGT_IMBAL", "LADAKH", 6, 10.0, 20.0, "GUST_TRANSIENTS", -1800.0, +3.5, 1.5, 308),
                ("TEST_M09_THAR_FAULT07_ALT_SAG", "THAR_DESERT", 7, 10.0, 20.0, "GUST_TRANSIENTS", +1400.0, +4.5, 1.5, 309),
                ("TEST_M10_LADAKH_FAULT08_FADEC_DRIFT", "LADAKH", 8, 10.0, 20.0, "GUST_TRANSIENTS", +2100.0, -4.2, 1.5, 310),
            ])
        ]

        manifest = {
            "splits": {},
            "train_dataset_path": os.path.join(self.output_dir, "rotax912_train_dataset.csv"),
            "val_dataset_path": os.path.join(self.output_dir, "rotax912_val_dataset.csv"),
            "test_dataset_path": os.path.join(self.output_dir, "rotax912_test_dataset.csv"),
        }

        for split_name, sorties in partition_configs:
            split_records = []
            split_dir = getattr(self, f"{split_name.lower()}_dir")
            manifest["splits"][split_name] = {"missions": [], "rows": 0}

            for mid, theater, fid, fstart, framp, pattern, alt_off, oat_off, nmult, seed in sorties:
                filename = f"{mid.lower()}.csv"
                filepath = os.path.join(split_dir, filename)

                records = self.generate_mission_sortie(
                    mission_id=mid,
                    split_type=split_name,
                    theater=theater,
                    duration_sec=45.0, # 45s @ 20 Hz = 900 rows
                    sample_rate_hz=20.0,
                    fault_id=fid,
                    fault_start_sec=fstart,
                    fault_ramp_sec=framp,
                    throttle_pattern=pattern,
                    alt_offset_ft=alt_off,
                    oat_offset_c=oat_off,
                    noise_multiplier=nmult,
                    seed=seed
                )
                self.export_mission_to_csv(records, filepath)
                split_records.extend(records)
                manifest["splits"][split_name]["missions"].append(mid)

            # Export combined partition CSV
            part_path = manifest[f"{split_name.lower()}_dataset_path"]
            self.export_mission_to_csv(split_records, part_path)
            manifest["splits"][split_name]["rows"] = len(split_records)

        # Export manifest
        manifest_path = os.path.join(self.output_dir, "mission_partition_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest
