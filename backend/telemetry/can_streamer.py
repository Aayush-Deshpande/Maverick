"""
Rotax 912 iS Telemetry Streamer & DRDO Fault Injector
DRDO / iDEX Problem Statement ID: 26054

Generates 20 Hz continuous 27-parameter flight telemetry with realistic sensor jitter,
multi-regime flight profiles (Ladakh high-altitude, Thar desert heat),
and parameterized injection for all 8 DRDO canonical failure modes.
"""

import time
import random
import math
from typing import Dict, Any, Tuple, Optional, List
from backend.physics.thermo_model import RotaxThermoModel, EnginePhysicalState, ResidualVector


DRDO_FAULT_DEFINITIONS = {
    0: {
        "name": "NOMINAL_FLIGHT",
        "description": "All engine systems operating within nominal baseline envelope.",
        "target_mesh": "All",
        "severity": "NORMAL"
    },
    1: {
        "name": "CYLINDER_2_CHT_OVERHEAT",
        "description": "Baffle seal degradation causing localized cooling airflow restriction on Cyl #2.",
        "target_mesh": "Covers_Theme_M_PlasticTheme_0",
        "severity": "CRITICAL"
    },
    2: {
        "name": "FUEL_INJECTOR_1_CLOG",
        "description": "Electromagnetic injector nozzle deposit causing fuel starvation on Runner #1.",
        "target_mesh": "Rotax_912i_Base_M_PlasticGreen_0",
        "severity": "WARNING"
    },
    3: {
        "name": "IGNITION_MISFIRE",
        "description": "Secondary ignition lead insulation breakdown causing intermittent spark loss.",
        "target_mesh": "Wiring_Harness_M_Copper_0",
        "severity": "WARNING"
    },
    4: {
        "name": "OIL_PRESSURE_LOSS",
        "description": "Dry-sump scavenge line cavitation or pressure relief bypass spring fatigue.",
        "target_mesh": "Oil_Tank_M_Steel_0",
        "severity": "CRITICAL"
    },
    5: {
        "name": "GEARBOX_VIBRATION",
        "description": "Propeller reduction dog-clutch tooth micro-pitting & 3rd harmonic resonance.",
        "target_mesh": "Gearbox_Type_2_M_Steel_0",
        "severity": "WARNING"
    },
    6: {
        "name": "EXHAUST_EGT_IMBALANCE",
        "description": "Runner #3 air-fuel mixture imbalance causing high exhaust temperature delta.",
        "target_mesh": "Exhaust_System_M_SteelDark_0",
        "severity": "WARNING"
    },
    7: {
        "name": "ALTERNATOR_VOLTAGE_SAG",
        "description": "Alternator diode pack thermal sag or serpentine belt micro-slip under avionics load.",
        "target_mesh": "External_Alternator_M_Steel_0",
        "severity": "WARNING"
    },
    8: {
        "name": "DUAL_FADEC_ECU_DRIFT",
        "description": "Cross-channel disparity between Lane A and Lane B manifold pressure transducers.",
        "target_mesh": "ECU_M_Steel_0",
        "severity": "WARNING"
    }
}


class TelemetryStreamer:
    """
    Simulates real-time CAN / FADEC telemetry frames at 10-50 Hz
    with realistic physical modeling, noise, and on-demand fault injection.
    """
    
    def __init__(self, sample_rate_hz: float = 20.0):
        self.sample_rate_hz = sample_rate_hz
        self.dt = 1.0 / sample_rate_hz
        self.thermo_model = RotaxThermoModel()
        
        # Flight state variables
        self.time_sec = 0.0
        self.active_fault_id = 0
        self.fault_severity = 0.0
        self.fault_onset_time = 0.0
        self.ramp_duration_sec = 8.0
        self.region = "LADAKH"

        # ── Autonomous Dynamic Plant Model State (G01 Decoupled Plant) ──
        # Integrates differential lags independent of the digital twin
        self.plant_initialized = False
        self.plant_rpm = 5000.0
        self.plant_tps = 65.0
        self.plant_map = 88.0
        self.plant_fuel_flow = 16.5
        self.plant_cht_1 = 94.0
        self.plant_cht_2 = 96.5
        self.plant_cht_3 = 93.5
        self.plant_cht_4 = 96.0
        self.plant_egt_1 = 777.0
        self.plant_egt_2 = 782.0
        self.plant_egt_3 = 779.0
        self.plant_egt_4 = 782.0
        self.plant_oil_temp = 92.0
        self.plant_oil_press = 3.8
        self.plant_bus_voltage = 14.1
        self.plant_battery_current = 4.2
        self.plant_vib_rms = 0.65

        # High-rate vibration buffer for kHz spectral analysis (F07 / 2 kHz rate)
        self.high_rate_sample_rate = 2000.0
        self.high_rate_vib_buffer: List[float] = [0.0] * 256

    def set_fault(self, fault_id: int, severity: float = 1.0, ramp_duration_sec: float = 8.0):
        """Injects one of the 8 DRDO canonical fault modes with dynamic progressive ramp."""
        if fault_id not in DRDO_FAULT_DEFINITIONS:
            raise ValueError(f"Unknown fault ID: {fault_id}. Must be 0..8.")
        self.active_fault_id = fault_id
        self.fault_severity = max(0.0, min(1.0, severity))
        self.fault_onset_time = self.time_sec
        self.ramp_duration_sec = max(0.1, ramp_duration_sec)

    def reset_fault(self):
        """Clears active fault and returns to nominal operating state."""
        self.active_fault_id = 0
        self.fault_severity = 0.0

    def set_mission_regime(self, regime: str) -> None:
        """Configures one of the 4 canonical mission regimes (SIM-05..08)."""
        reg = regime.upper()
        self.active_regime = reg
        if "LADAKH" in reg:
            self.region = "LADAKH"
            self.altitude_cmd = 18500.0
            self.oat_cmd = -22.0
            self.throttle_cmd = 72.0
        elif "THAR" in reg:
            self.region = "THAR_DESERT"
            self.altitude_cmd = 4500.0
            self.oat_cmd = 44.0
            self.throttle_cmd = 68.0
        elif "ENDURANCE" in reg:
            self.region = "ENDURANCE_LOITER"
            self.altitude_cmd = 5000.0
            self.oat_cmd = 15.0
            self.throttle_cmd = 65.0
        elif "TRANSIENT" in reg or "RAPID" in reg:
            self.region = "RAPID_THROTTLE_TRANSIENTS"
            self.altitude_cmd = 7500.0
            self.oat_cmd = 10.0
            self.throttle_cmd = 85.0

    def get_flight_context(self, t_sec: float, region: str = "LADAKH") -> Tuple[float, float, float, float, float, str]:
        """
        Computes dynamic flight regime (Altitude, OAT, Airspeed, Throttle, RPM, Flight Phase)
        covering the 4 canonical mission regimes (SIM-05..SIM-08 / PS-26054).
        """
        reg_upper = (region or "LADAKH").upper()
        
        if "LADAKH" in reg_upper or "ALTITUDE" in reg_upper:
            # Regime 1: High Altitude loiter (SIM-05) - thin air, -22°C ambient
            base_alt = 18500.0 + 1500.0 * math.sin(t_sec * 0.005)
            base_oat = -22.0 - 0.002 * (base_alt - 18500.0)
            tas = 88.0 + 4.0 * math.sin(t_sec * 0.02)
            tps = 72.0 + 2.0 * math.sin(t_sec * 0.01)
            rpm = 5150.0 + 30.0 * math.sin(t_sec * 0.015)
            phase = "CRUISE_LOITER"
            
        elif "THAR" in reg_upper or "HEAT" in reg_upper or "HOT" in reg_upper:
            # Regime 2: Hot-Weather operation (SIM-07) - +44°C ambient thermal stress
            base_alt = 4500.0 + 1200.0 * math.sin(t_sec * 0.005)
            base_oat = 44.0 - 0.003 * (base_alt - 4500.0)
            tas = 95.0 + 6.0 * math.sin(t_sec * 0.02)
            tps = 68.0 + 3.0 * math.sin(t_sec * 0.01)
            rpm = 5050.0 + 25.0 * math.sin(t_sec * 0.015)
            phase = "CRUISE_LOITER"
            
        elif "ENDURANCE" in reg_upper:
            # Regime 3: Endurance mission (SIM-06) - steady efficient economy loiter
            base_alt = 12000.0 + 500.0 * math.sin(t_sec * 0.002)
            base_oat = -8.0 - 0.002 * (base_alt - 12000.0)
            tas = 84.0 + 2.0 * math.sin(t_sec * 0.008)
            tps = 62.0 + 1.5 * math.sin(t_sec * 0.005)
            rpm = 4850.0 + 20.0 * math.sin(t_sec * 0.008)
            phase = "ENDURANCE_LOITER"
            
        elif "TRANSIENT" in reg_upper or "THROTTLE" in reg_upper or "RAPID" in reg_upper:
            # Regime 4: Rapid throttle transitions (SIM-08) - cyclic step climbs / maneuvers
            cycle_time = t_sec % 14.0
            is_step_high = cycle_time < 7.0
            base_alt = 7500.0 + (1000.0 if is_step_high else -400.0) * math.sin(t_sec * 0.05)
            base_oat = 8.0 - 0.002 * (base_alt - 7500.0)
            tas = 98.0 if is_step_high else 78.0
            tps = 88.0 if is_step_high else 52.0
            rpm = 5500.0 if is_step_high else 4400.0
            phase = "RAPID_TRANSIENTS"
            
        else:
            # Standard Nominal Cruise
            base_alt = 10000.0
            base_oat = 5.0
            tas = 90.0
            tps = 65.0
            rpm = 5000.0
            phase = "CRUISE_LOITER"
            
        return base_alt, base_oat, tas, tps, rpm, phase

    def generate_frame(
        self,
        t_sec: Optional[float] = None,
        region: Optional[str] = None,
        throttle_cmd: Optional[float] = None,
        altitude_cmd: Optional[float] = None,
        oat_cmd: Optional[float] = None
    ) -> Tuple[EnginePhysicalState, EnginePhysicalState, ResidualVector]:
        """
        Generates a single synchronized telemetry time frame:
        Returns (Actual_Sensor_State, Expected_Physics_Baseline, Residual_Vector).
        Uses autonomous plant differential equations decoupled from the twin baseline.
        """
        if t_sec is not None:
            self.time_sec = t_sec
        else:
            self.time_sec += self.dt
            
        if region is not None:
            self.region = region

        # 1. Compute environmental context and commanded inputs
        alt_ft, oat_c, tas_kts, tps, base_rpm, phase = self.get_flight_context(self.time_sec, self.region)
        
        # Dynamic operator control overrides (G02)
        if throttle_cmd is not None:
            tps = max(0.0, min(100.0, throttle_cmd))
            base_rpm = 1800.0 + (tps / 100.0) * 4000.0
        if altitude_cmd is not None:
            alt_ft = max(0.0, min(30000.0, altitude_cmd))
        if oat_cmd is not None:
            oat_c = oat_cmd

        # 2. Compute theoretical nominal physics baseline (Digital Twin Reference)
        expected_state = self.thermo_model.compute_expected_state(
            altitude_ft=alt_ft,
            oat_c=oat_c,
            rpm=base_rpm,
            tps=tps,
            tas_knots=tas_kts,
            flight_phase=phase
        )
        expected_state.TIMESTAMP_SEC = self.time_sec

        # 3. Dynamic Engine Plant Integration (G01 Plant Independence)
        # If jumping in time (tests) or first initialization, snap plant to baseline equilibrium
        if not self.plant_initialized or (t_sec is not None and abs(t_sec - self.time_sec) > 0.5):
            self.plant_tps = tps
            self.plant_rpm = base_rpm
            self.plant_map = expected_state.MAP
            self.plant_fuel_flow = expected_state.FUEL_FLOW
            self.plant_cht_1 = expected_state.CHT_1
            self.plant_cht_2 = expected_state.CHT_2
            self.plant_cht_3 = expected_state.CHT_3
            self.plant_cht_4 = expected_state.CHT_4
            self.plant_egt_1 = expected_state.EGT_1
            self.plant_egt_2 = expected_state.EGT_2
            self.plant_egt_3 = expected_state.EGT_3
            self.plant_egt_4 = expected_state.EGT_4
            self.plant_oil_press = expected_state.OIL_PRESS
            self.plant_oil_temp = expected_state.OIL_TEMP
            self.plant_vib_rms = expected_state.VIB_GEARBOX_RMS
            self.plant_bus_voltage = expected_state.BUS_VOLTAGE
            self.plant_battery_current = expected_state.BATTERY_CURRENT
            self.plant_initialized = True
        else:
            # Step forward in time differential ODEs
            dt = self.dt
            self.plant_tps += (tps - self.plant_tps) * min(1.0, dt / 0.30)
            self.plant_map += (expected_state.MAP - self.plant_map) * min(1.0, dt / 0.15)
            self.plant_rpm += (base_rpm - self.plant_rpm) * min(1.0, dt / 0.40)
            self.plant_fuel_flow += (expected_state.FUEL_FLOW - self.plant_fuel_flow) * min(1.0, dt / 0.20)
            self.plant_cht_1 += (expected_state.CHT_1 - self.plant_cht_1) * min(1.0, dt / 6.0)
            self.plant_cht_2 += (expected_state.CHT_2 - self.plant_cht_2) * min(1.0, dt / 6.0)
            self.plant_cht_3 += (expected_state.CHT_3 - self.plant_cht_3) * min(1.0, dt / 6.0)
            self.plant_cht_4 += (expected_state.CHT_4 - self.plant_cht_4) * min(1.0, dt / 6.0)
            self.plant_egt_1 += (expected_state.EGT_1 - self.plant_egt_1) * min(1.0, dt / 1.2)
            self.plant_egt_2 += (expected_state.EGT_2 - self.plant_egt_2) * min(1.0, dt / 1.2)
            self.plant_egt_3 += (expected_state.EGT_3 - self.plant_egt_3) * min(1.0, dt / 1.2)
            self.plant_egt_4 += (expected_state.EGT_4 - self.plant_egt_4) * min(1.0, dt / 1.2)
            self.plant_oil_temp += (expected_state.OIL_TEMP - self.plant_oil_temp) * min(1.0, dt / 12.0)
            self.plant_oil_press += (expected_state.OIL_PRESS - self.plant_oil_press) * min(1.0, dt / 0.50)
            self.plant_vib_rms = expected_state.VIB_GEARBOX_RMS

        # 4. Synthesize High-Rate Vibration Waveform (F07 / kHz Vibration)
        f_mesh = (self.plant_rpm / 60.0 / 2.43) * 3.0
        vib_amp = self.plant_vib_rms
        if self.active_fault_id == 5:
            fault_elapsed = max(0.0, self.time_sec - self.fault_onset_time)
            ramp = min(1.0, fault_elapsed / self.ramp_duration_sec) * self.fault_severity
            vib_amp += 3.10 * ramp
            
        N_pts = len(self.high_rate_vib_buffer)
        dt_high = 1.0 / self.high_rate_sample_rate
        for i in range(N_pts):
            t_sample = self.time_sec + i * dt_high
            mesh_wave = vib_amp * (
                0.5 * math.sin(2 * math.pi * f_mesh * t_sample) +
                0.25 * math.sin(2 * math.pi * 2 * f_mesh * t_sample) +
                0.15 * math.sin(2 * math.pi * 3 * f_mesh * t_sample)
            ) + random.gauss(0.0, 0.05)
            self.high_rate_vib_buffer[i] = mesh_wave

        # 5. Create Actual State with realistic physical sensor noise
        actual_rpm = max(1000.0, self.plant_rpm + random.gauss(0.0, 10.0))
        actual_tps = max(0.0, min(100.0, self.plant_tps + random.gauss(0.0, 0.15)))

        actual_state = EnginePhysicalState(
            ENGINE_RPM=round(actual_rpm, 1),
            PROP_RPM=round(actual_rpm / 2.43, 1),
            TPS=round(actual_tps, 1),
            CHT_1=round(self.plant_cht_1 + random.gauss(0.0, 0.18), 2),
            CHT_2=round(self.plant_cht_2 + random.gauss(0.0, 0.18), 2),
            CHT_3=round(self.plant_cht_3 + random.gauss(0.0, 0.18), 2),
            CHT_4=round(self.plant_cht_4 + random.gauss(0.0, 0.18), 2),
            EGT_1=round(self.plant_egt_1 + random.gauss(0.0, 1.2), 2),
            EGT_2=round(self.plant_egt_2 + random.gauss(0.0, 1.2), 2),
            EGT_3=round(self.plant_egt_3 + random.gauss(0.0, 1.2), 2),
            EGT_4=round(self.plant_egt_4 + random.gauss(0.0, 1.2), 2),
            OIL_PRESS=round(self.plant_oil_press + random.gauss(0.0, 0.03), 2),
            OIL_TEMP=round(self.plant_oil_temp + random.gauss(0.0, 0.15), 2),
            FUEL_FLOW=round(self.plant_fuel_flow + random.gauss(0.0, 0.08), 2),
            FUEL_RAIL_P=round(3.0 + random.gauss(0.0, 0.02), 2),
            MAP=round(self.plant_map + random.gauss(0.0, 0.12), 2),
            VIB_GEARBOX_RMS=round(self.plant_vib_rms + random.gauss(0.0, 0.015), 3),
            BUS_VOLTAGE=round(self.plant_bus_voltage + random.gauss(0.0, 0.02), 2),
            BATTERY_CURRENT=round(self.plant_battery_current + random.gauss(0.0, 0.1), 2),
            FADEC_ACTIVE_LANE="LANE_A",
            ALTITUDE_FT=round(alt_ft, 0),
            OAT_C=round(oat_c, 1),
            TAS_KNOTS=round(tas_kts, 1),
            FLIGHT_PHASE=phase,
            HEALTH_INDEX=1.0,
            FAULT_ID=self.active_fault_id,
            RUL_HOURS=500.0,
            TIMESTAMP_SEC=self.time_sec
        )

        # Injection timing & performance metrics
        tps_norm = max(0.0, min(1.0, actual_tps / 100.0))
        actual_state.INJ_TIMING_BTDC = round(14.0 + 5.5 * (self.plant_rpm / 5800.0) + 1.5 * tps_norm + random.gauss(0.0, 0.1), 1)
        actual_state.INJ_PULSE_WIDTH_MS = round(2.0 + 4.8 * (actual_state.FUEL_FLOW / 25.0) * (5000.0 / max(1000.0, self.plant_rpm)) + random.gauss(0.0, 0.03), 2)
        actual_state.IGN_TIMING_BTDC = round(18.0 + 6.0 * (1.0 - tps_norm) + 4.0 * (self.plant_rpm / 5800.0) + random.gauss(0.0, 0.1), 1)
        actual_state.LAMBDA_AFR = round(1.0 - 0.12 * (tps_norm ** 2.0) + random.gauss(0.0, 0.01), 2)
        perf_act = self.thermo_model.lookup_performance_map(self.plant_rpm, self.plant_map, alt_ft)
        actual_power = perf_act["power_kw"]
        actual_state.POWER_KW = round(actual_power, 1)
        actual_state.BSFC_G_KWH = round((actual_state.FUEL_FLOW * 0.74 * 1000.0) / max(5.0, actual_power), 1)
        actual_state.THERMAL_EFFICIENCY = round(min(0.38, max(0.15, (actual_power * 3600.0) / max(1.0, actual_state.FUEL_FLOW * 0.74 * 43000.0))), 3)


        # 4. Inject Active DRDO Fault Dynamics if enabled
        if self.active_fault_id > 0:
            fault_elapsed = max(0.0, self.time_sec - self.fault_onset_time)
            # Progressive ramp onset over self.ramp_duration_sec
            ramp = min(1.0, fault_elapsed / self.ramp_duration_sec) * self.fault_severity
            
            if self.active_fault_id == 1:
                # FAULT 01: Cylinder #2 CHT Overheat (Cooling baffle leak)
                # Primary: Baffle seal displacement restricts cooling airflow past Cyl #2
                # Causal: CHT_2 surges -> heat conducts to oil -> EGT_2 climbs due to hotter chamber -> CHT_4 slight thermal bleed
                temp_rise = 40.0 * ramp
                actual_state.CHT_2 = round(actual_state.CHT_2 + temp_rise, 2)
                actual_state.OIL_TEMP = round(actual_state.OIL_TEMP + (10.5 * ramp), 2)
                actual_state.EGT_2 = round(actual_state.EGT_2 + (24.0 * ramp), 2)
                actual_state.CHT_4 = round(actual_state.CHT_4 + (4.0 * ramp), 2)
                actual_state.HEALTH_INDEX = round(max(0.2, 1.0 - 0.75 * ramp), 2)
                actual_state.RUL_HOURS = round(max(1.5, 500.0 - 480.0 * ramp), 1)

            elif self.active_fault_id == 2:
                # FAULT 02: Fuel Injector #1 Clog (Lean burn on Cyl 1, fuel drop)
                # Primary: Electromagnetic nozzle deposit restricts fuel delivery
                # Causal: Total FUEL_FLOW drops -> Cyl 1 severe lean spike on EGT_1 & CHT_1 -> torque imbalance drops RPM -> vibration rises
                actual_state.FUEL_FLOW = round(max(2.0, actual_state.FUEL_FLOW * (1.0 - 0.22 * ramp)), 2)
                actual_state.EGT_1 = round(actual_state.EGT_1 + (92.0 * ramp), 2)
                actual_state.CHT_1 = round(actual_state.CHT_1 + (16.0 * ramp), 2)
                actual_state.ENGINE_RPM = round(max(1200.0, actual_state.ENGINE_RPM - (85.0 * ramp) + random.gauss(0.0, 15.0 * ramp)), 1)
                actual_state.PROP_RPM = round(actual_state.ENGINE_RPM / 2.43, 1)
                actual_state.VIB_GEARBOX_RMS = round(actual_state.VIB_GEARBOX_RMS + (0.55 * ramp), 3)
                actual_state.HEALTH_INDEX = round(max(0.35, 1.0 - 0.60 * ramp), 2)
                actual_state.RUL_HOURS = round(max(5.0, 500.0 - 450.0 * ramp), 1)

            elif self.active_fault_id == 3:
                # FAULT 03: Ignition Misfire (Secondary spark lead breakdown)
                # Primary: Intermittent spark dropout on Cylinder #2
                # Causal: Unburnt fuel drops EGT_2 -> severe torque stroke pulsation -> high-variance RPM flutter -> gearbox shock vibration
                actual_state.EGT_2 = round(actual_state.EGT_2 - (125.0 * ramp), 2)
                misfire_flutter = random.uniform(-160.0, 160.0) * ramp
                actual_state.ENGINE_RPM = round(max(1200.0, actual_state.ENGINE_RPM - (120.0 * ramp) + misfire_flutter), 1)
                actual_state.PROP_RPM = round(actual_state.ENGINE_RPM / 2.43, 1)
                actual_state.VIB_GEARBOX_RMS = round(actual_state.VIB_GEARBOX_RMS + (1.45 * ramp), 3)
                actual_state.HEALTH_INDEX = round(max(0.4, 1.0 - 0.55 * ramp), 2)
                actual_state.RUL_HOURS = round(max(8.0, 500.0 - 420.0 * ramp), 1)

            elif self.active_fault_id == 4:
                # FAULT 04: Oil Pressure Decay (Dry-sump scavenge cavitation / relief spring fatigue)
                # Primary: Lubrication delivery pressure decays linearly
                # Causal: OIL_PRESS collapses -> hydrodynamic bearing friction surge -> OIL_TEMP surges -> all CHTs elevate -> mechanical drag sags RPM -> vibration rises
                decay_factor = 0.65 * ramp
                actual_state.OIL_PRESS = round(max(1.6, actual_state.OIL_PRESS * (1.0 - decay_factor)), 2)
                actual_state.OIL_TEMP = round(actual_state.OIL_TEMP + (28.0 * ramp), 2)
                actual_state.CHT_1 = round(actual_state.CHT_1 + (10.0 * ramp), 2)
                actual_state.CHT_2 = round(actual_state.CHT_2 + (11.0 * ramp), 2)
                actual_state.CHT_3 = round(actual_state.CHT_3 + (10.0 * ramp), 2)
                actual_state.CHT_4 = round(actual_state.CHT_4 + (11.0 * ramp), 2)
                actual_state.ENGINE_RPM = round(max(1200.0, actual_state.ENGINE_RPM - (65.0 * ramp)), 1)
                actual_state.PROP_RPM = round(actual_state.ENGINE_RPM / 2.43, 1)
                actual_state.VIB_GEARBOX_RMS = round(actual_state.VIB_GEARBOX_RMS + (0.60 * ramp), 3)
                actual_state.HEALTH_INDEX = round(max(0.1, 1.0 - 0.85 * ramp), 2)
                actual_state.RUL_HOURS = round(max(0.8, 500.0 - 495.0 * ramp), 1)

            elif self.active_fault_id == 5:
                # FAULT 05: Gearbox Vibration & Clutch Wear (Dog-clutch micro-pitting)
                # Primary: Propeller reduction dog-clutch tooth pitting & 3rd harmonic resonance
                # Causal: VIB_GEARBOX_RMS spikes -> mechanical parasitic drag sags RPM -> FADEC MAP compensation -> frictional heat raises OIL_TEMP
                actual_state.VIB_GEARBOX_RMS = round(actual_state.VIB_GEARBOX_RMS + (3.10 * ramp), 3)
                actual_state.ENGINE_RPM = round(max(1200.0, actual_state.ENGINE_RPM - (70.0 * ramp) + random.gauss(0.0, 10.0 * ramp)), 1)
                actual_state.PROP_RPM = round(actual_state.ENGINE_RPM / 2.43, 1)
                actual_state.MAP = round(actual_state.MAP + (3.4 * ramp), 2)
                actual_state.OIL_TEMP = round(actual_state.OIL_TEMP + (8.5 * ramp), 2)
                actual_state.HEALTH_INDEX = round(max(0.45, 1.0 - 0.50 * ramp), 2)
                actual_state.RUL_HOURS = round(max(12.0, 500.0 - 400.0 * ramp), 1)

            elif self.active_fault_id == 6:
                # FAULT 06: Exhaust EGT Imbalance (Runner #3 mixture disparity)
                # Primary: Runner #3 air-fuel mixture divergence
                # Causal: EGT_3 spikes -> Cyl 3 head CHT_3 warms up -> asymmetric exhaust scavenging sags RPM -> mild vibration rise
                actual_state.EGT_3 = round(actual_state.EGT_3 + (95.0 * ramp), 2)
                actual_state.CHT_3 = round(actual_state.CHT_3 + (18.0 * ramp), 2)
                actual_state.ENGINE_RPM = round(max(1200.0, actual_state.ENGINE_RPM - (40.0 * ramp)), 1)
                actual_state.PROP_RPM = round(actual_state.ENGINE_RPM / 2.43, 1)
                actual_state.VIB_GEARBOX_RMS = round(actual_state.VIB_GEARBOX_RMS + (0.35 * ramp), 3)
                actual_state.HEALTH_INDEX = round(max(0.5, 1.0 - 0.45 * ramp), 2)
                actual_state.RUL_HOURS = round(max(18.0, 500.0 - 350.0 * ramp), 1)

            elif self.active_fault_id == 7:
                # FAULT 07: Alternator Voltage Sag (Stator winding thermal sag / belt micro-slip)
                # Primary: Generator capacity degrades below avionics demand
                # Causal: BUS_VOLTAGE drops -> BATTERY_CURRENT swings to net discharge -> weak coil dwell sags RPM
                actual_state.BUS_VOLTAGE = round(actual_state.BUS_VOLTAGE - (1.85 * ramp), 2)
                actual_state.BATTERY_CURRENT = round(actual_state.BATTERY_CURRENT - (15.5 * ramp), 2)
                actual_state.ENGINE_RPM = round(max(1200.0, actual_state.ENGINE_RPM - (30.0 * ramp)), 1)
                actual_state.PROP_RPM = round(actual_state.ENGINE_RPM / 2.43, 1)
                actual_state.HEALTH_INDEX = round(max(0.55, 1.0 - 0.40 * ramp), 2)
                actual_state.RUL_HOURS = round(max(4.0, 500.0 - 460.0 * ramp), 1)

            elif self.active_fault_id == 8:
                # FAULT 08: Dual FADEC ECU Drift (MAP sensor cross-channel disparity)
                # Primary: Lane A MAP transducer drifts positive
                # Causal: High MAP reported -> speed-density over-fueling -> FUEL_FLOW rises -> rich mixture cools all EGTs -> power sags RPM
                actual_state.MAP = round(actual_state.MAP + (9.5 * ramp), 2)
                actual_state.FUEL_FLOW = round(actual_state.FUEL_FLOW + (3.2 * ramp), 2)
                actual_state.EGT_1 = round(actual_state.EGT_1 - (45.0 * ramp), 2)
                actual_state.EGT_2 = round(actual_state.EGT_2 - (45.0 * ramp), 2)
                actual_state.EGT_3 = round(actual_state.EGT_3 - (45.0 * ramp), 2)
                actual_state.EGT_4 = round(actual_state.EGT_4 - (45.0 * ramp), 2)
                actual_state.ENGINE_RPM = round(max(1200.0, actual_state.ENGINE_RPM - (55.0 * ramp)), 1)
                actual_state.PROP_RPM = round(actual_state.ENGINE_RPM / 2.43, 1)
                actual_state.HEALTH_INDEX = round(max(0.6, 1.0 - 0.35 * ramp), 2)
                actual_state.RUL_HOURS = round(max(24.0, 500.0 - 300.0 * ramp), 1)

        # 5. Compute the Residual Vector (Actual - Expected)
        actual_state.high_rate_vib_buffer = list(self.high_rate_vib_buffer)
        residual_vector = self.thermo_model.compute_residuals(actual_state, expected_state)
        residual_vector.fault_hypothesis_id = self.active_fault_id
        
        return actual_state, expected_state, residual_vector

    def generate_flight_log(
        self,
        duration_sec: float = 60.0,
        region: str = "LADAKH",
        fault_id: int = 0,
        fault_start_sec: float = 20.0,
        severity: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        Generates a full time-series sequence for mission log recording / replay.
        """
        records = []
        self.time_sec = 0.0
        self.reset_fault()
        
        total_steps = int(duration_sec * self.sample_rate_hz)
        for step in range(total_steps):
            current_t = step * self.dt
            if fault_id > 0 and current_t >= fault_start_sec and self.active_fault_id == 0:
                self.set_fault(fault_id, severity)
                
            actual, expected, residual = self.generate_frame(t_sec=current_t, region=region)
            record = {
                "timestamp_sec": current_t,
                "telemetry": actual.to_dict(),
                "physics_baseline": expected.to_dict(),
                "residuals": residual.to_dict()
            }
            records.append(record)
            
        return records
