"""
Rotax 912 iS Sport 1D Thermodynamic Physics Model & Residual Calculator
DRDO / iDEX Problem Statement ID: 26054

Implements first-principles thermodynamic equations for the 4-stroke Otto cycle,
ambient density derating, and continuous physics baseline / residual computation.
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple

# Physical & Geometric Constants for Rotax 912 iS Sport
DISPLACEMENT_CC = 1352.0       # 1,352 cm^3 (4-cylinder boxer)
BORE_MM = 84.0                 # 84 mm
STROKE_MM = 61.0               # 61 mm
COMPRESSION_RATIO = 10.8       # 10.8 : 1
GEAR_REDUCTION_RATIO = 2.43    # Crankshaft to Propeller reduction ratio (i = 2.43)
MAX_TAKEOFF_RPM = 5800.0       # Max takeoff RPM (5 min limit)
MAX_CONTINUOUS_RPM = 5500.0    # Max continuous cruise RPM
NOMINAL_CRUISE_RPM = 5000.0    # Standard loiter cruise RPM
R_AIR = 287.05                 # Specific gas constant for dry air (J/(kg*K))
SEA_LEVEL_P_KPA = 101.325      # Standard Sea Level atmospheric pressure (kPa)
SEA_LEVEL_T_K = 288.15         # Standard Sea Level temperature (15°C in Kelvin)
SEA_LEVEL_RHO = 1.225          # Standard Sea Level air density (kg/m^3)


@dataclass
class EnginePhysicalState:
    """The complete 27-parameter flight telemetry & engine health state."""
    # 1. Kinematics
    ENGINE_RPM: float = 5000.0
    PROP_RPM: float = 2057.6
    TPS: float = 65.0              # Throttle Position (0-100 %)
    
    # 2. Thermal State
    CHT_1: float = 95.0            # °C
    CHT_2: float = 95.0            # °C
    CHT_3: float = 95.0            # °C
    CHT_4: float = 95.0            # °C
    EGT_1: float = 780.0           # °C
    EGT_2: float = 780.0           # °C
    EGT_3: float = 780.0           # °C
    EGT_4: float = 780.0           # °C
    
    # 3. Fluids & Pressures
    OIL_PRESS: float = 3.8         # bar
    OIL_TEMP: float = 92.0         # °C
    FUEL_FLOW: float = 18.5        # L/hr
    FUEL_RAIL_P: float = 3.0       # bar
    MAP: float = 90.0              # kPa (Manifold Absolute Pressure)
    
    # 4. Mechanical & Electrical
    VIB_GEARBOX_RMS: float = 0.65  # mm/s
    BUS_VOLTAGE: float = 14.1      # Volts
    BATTERY_CURRENT: float = 4.2   # Amps
    FADEC_ACTIVE_LANE: str = "LANE_A"
    
    # 5. Environmental Context
    ALTITUDE_FT: float = 10000.0   # Feet MSL
    OAT_C: float = 0.0             # Outside Air Temp (°C)
    TAS_KNOTS: float = 85.0        # True Airspeed (knots)
    FLIGHT_PHASE: str = "CRUISE_LOITER"
    
    # 6. ML Labels & Metadata
    HEALTH_INDEX: float = 1.0      # 1.0 (New) -> 0.0 (Failed)
    FAULT_ID: int = 0              # 0 = Nominal, 1..8 = Faults
    RUL_HOURS: float = 500.0       # Remaining Useful Life
    TIMESTAMP_SEC: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResidualVector:
    """The normalized residual vector: delta = Actual - Physics Expected."""
    d_CHT_1: float = 0.0
    d_CHT_2: float = 0.0
    d_CHT_3: float = 0.0
    d_CHT_4: float = 0.0
    d_EGT_1: float = 0.0
    d_EGT_2: float = 0.0
    d_EGT_3: float = 0.0
    d_EGT_4: float = 0.0
    d_OIL_PRESS: float = 0.0
    d_OIL_TEMP: float = 0.0
    d_FUEL_FLOW: float = 0.0
    d_MAP: float = 0.0
    d_VIB_RMS: float = 0.0
    d_BUS_VOLTAGE: float = 0.0
    
    anomaly_score: float = 0.0     # 0.0 to 1.0 composite anomaly score
    is_anomaly: bool = False
    fault_hypothesis_id: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RotaxThermoModel:
    """1D Thermodynamic Virtual Physics Shadow for Rotax 912 iS."""
    
    def __init__(self):
        self.reduction_ratio = GEAR_REDUCTION_RATIO

    @staticmethod
    def get_ambient_properties(altitude_ft: float, oat_c: float) -> Tuple[float, float, float]:
        """
        Calculates ambient pressure (kPa), temperature (K), and air density (kg/m^3).
        Uses ISA barometric formula adjusted for local OAT.
        """
        alt_m = altitude_ft * 0.3048
        # Standard lapse pressure
        p_amb = SEA_LEVEL_P_KPA * math.pow(1.0 - (0.0065 * alt_m / 288.15), 5.25588)
        p_amb = max(10.0, p_amb)
        
        t_kelvin = oat_c + 273.15
        t_kelvin = max(200.0, t_kelvin)
        
        rho_amb = (p_amb * 1000.0) / (R_AIR * t_kelvin)
        return p_amb, t_kelvin, rho_amb

    def compute_expected_state(
        self,
        altitude_ft: float,
        oat_c: float,
        rpm: float,
        tps: float,
        tas_knots: float = 85.0,
        flight_phase: str = "CRUISE_LOITER"
    ) -> EnginePhysicalState:
        """
        Solves 1D thermodynamic equations to produce theoretical expected parameters.
        """
        p_amb, t_kelvin, rho_amb = self.get_ambient_properties(altitude_ft, oat_c)
        density_ratio = rho_amb / SEA_LEVEL_RHO
        throttle_norm = max(0.0, min(1.0, tps / 100.0))
        
        # 1. Propeller RPM (Mechanical reduction)
        prop_rpm = rpm / self.reduction_ratio
        
        # 2. Expected Manifold Absolute Pressure (MAP in kPa)
        # MAP depends on ambient pressure and throttle blade opening
        # Idle = ~35 kPa, WOT = p_amb - small intake pressure drop
        map_expected = 35.0 + (p_amb - 38.0) * (throttle_norm ** 0.85)
        map_expected = min(p_amb, max(30.0, map_expected))
        
        # 3. Volumetric & Air Mass Flow Rate (kg/hr)
        rpm_norm = max(1000.0, rpm) / 5000.0
        volumetric_efficiency = 0.82 + 0.08 * (throttle_norm ** 0.5)
        air_mass_flow = (DISPLACEMENT_CC * 1e-6) * (rpm / 120.0) * rho_amb * volumetric_efficiency * 3600.0 # kg/hr
        
        # 4. Expected Fuel Flow (L/hr)
        # Air-Fuel Ratio target ~ 14.7 for cruise, ~ 12.8 for high power/takeoff
        target_afr = 14.7 - 1.9 * (throttle_norm ** 2.0)
        fuel_mass_flow_kg_hr = air_mass_flow / target_afr
        fuel_density_kg_l = 0.74 # Aviation gasoline density ~0.74 kg/L
        fuel_flow_expected = max(4.0, fuel_mass_flow_kg_hr / fuel_density_kg_l)
        
        # 5. Expected Cylinder Head Temperature (CHT in °C)
        # Thermal equilibrium: Heat generated (proportional to Fuel Flow) vs Heat dissipated by airflow (convection)
        cooling_mass_flow = density_ratio * (max(20.0, tas_knots) / 85.0)
        heat_generated_index = (fuel_flow_expected / 18.5) * (rpm_norm ** 1.1)
        heat_dissipation_factor = max(0.5, 0.75 * cooling_mass_flow + 0.25)
        
        base_cht = oat_c + 75.0 + (35.0 * heat_generated_index / heat_dissipation_factor)
        cht_expected = max(50.0, min(130.0, base_cht))
        
        # Individual cylinder distribution (Rotax rear cylinders run ~2°C warmer)
        cht_1 = cht_expected - 1.0
        cht_2 = cht_expected + 1.5
        cht_3 = cht_expected - 1.5
        cht_4 = cht_expected + 1.0
        
        # 6. Expected Exhaust Gas Temperature (EGT in °C)
        # EGT peaks around stoichiometric (~790°C), drops rich at takeoff (~740°C) or lean loiter
        base_egt = 760.0 + 35.0 * math.sin(throttle_norm * math.pi) + (oat_c * 0.15)
        egt_1 = base_egt - 3.0
        egt_2 = base_egt + 2.0
        egt_3 = base_egt - 1.0
        egt_4 = base_egt + 2.0
        
        # 7. Lubrication System (Oil Press & Temp)
        # Oil Temp equilibrates with engine block
        oil_temp_expected = oat_c + 60.0 + (28.0 * heat_generated_index / heat_dissipation_factor)
        oil_temp_expected = max(55.0, min(115.0, oil_temp_expected))
        
        # Oil Pressure: higher at high RPM, slightly drops with high oil temp (lower viscosity)
        oil_press_expected = 2.2 + (2.3 * rpm_norm) - (0.015 * (oil_temp_expected - 80.0))
        oil_press_expected = max(2.0, min(5.0, oil_press_expected))
        
        # 8. Electrical Bus Voltage & Battery
        bus_voltage_expected = 14.10
        battery_current_expected = 3.5 + 2.0 * (1.0 - throttle_norm)
        
        # 9. Gearbox Vibration RMS (mm/s)
        vib_expected = 0.35 + 0.35 * (rpm_norm ** 2.0)
        
        return EnginePhysicalState(
            ENGINE_RPM=round(rpm, 1),
            PROP_RPM=round(prop_rpm, 1),
            TPS=round(tps, 1),
            CHT_1=round(cht_1, 2),
            CHT_2=round(cht_2, 2),
            CHT_3=round(cht_3, 2),
            CHT_4=round(cht_4, 2),
            EGT_1=round(egt_1, 2),
            EGT_2=round(egt_2, 2),
            EGT_3=round(egt_3, 2),
            EGT_4=round(egt_4, 2),
            OIL_PRESS=round(oil_press_expected, 2),
            OIL_TEMP=round(oil_temp_expected, 2),
            FUEL_FLOW=round(fuel_flow_expected, 2),
            FUEL_RAIL_P=3.0,
            MAP=round(map_expected, 2),
            VIB_GEARBOX_RMS=round(vib_expected, 3),
            BUS_VOLTAGE=round(bus_voltage_expected, 2),
            BATTERY_CURRENT=round(battery_current_expected, 2),
            FADEC_ACTIVE_LANE="LANE_A",
            ALTITUDE_FT=round(altitude_ft, 0),
            OAT_C=round(oat_c, 1),
            TAS_KNOTS=round(tas_knots, 1),
            FLIGHT_PHASE=flight_phase,
            HEALTH_INDEX=1.0,
            FAULT_ID=0,
            RUL_HOURS=500.0
        )

    def compute_residuals(
        self,
        actual: EnginePhysicalState,
        expected: EnginePhysicalState
    ) -> ResidualVector:
        """
        Computes the normalized residual vector: Delta = Actual - Expected.
        """
        d_cht_1 = actual.CHT_1 - expected.CHT_1
        d_cht_2 = actual.CHT_2 - expected.CHT_2
        d_cht_3 = actual.CHT_3 - expected.CHT_3
        d_cht_4 = actual.CHT_4 - expected.CHT_4
        
        d_egt_1 = actual.EGT_1 - expected.EGT_1
        d_egt_2 = actual.EGT_2 - expected.EGT_2
        d_egt_3 = actual.EGT_3 - expected.EGT_3
        d_egt_4 = actual.EGT_4 - expected.EGT_4
        
        d_oil_p = actual.OIL_PRESS - expected.OIL_PRESS
        d_oil_t = actual.OIL_TEMP - expected.OIL_TEMP
        d_ff = actual.FUEL_FLOW - expected.FUEL_FLOW
        d_map = actual.MAP - expected.MAP
        d_vib = actual.VIB_GEARBOX_RMS - expected.VIB_GEARBOX_RMS
        d_bus_v = actual.BUS_VOLTAGE - expected.BUS_VOLTAGE
        
        # Individual channel normalized standard deviations (z-scores)
        z_scores = [
            abs(d_cht_1) / 4.0,
            abs(d_cht_2) / 4.0,
            abs(d_cht_3) / 4.0,
            abs(d_cht_4) / 4.0,
            abs(d_egt_1) / 15.0,
            abs(d_egt_2) / 15.0,
            abs(d_egt_3) / 15.0,
            abs(d_egt_4) / 15.0,
            abs(d_oil_p) / 0.3,
            abs(d_oil_t) / 5.0,
            abs(d_ff) / 1.5,
            abs(d_map) / 3.0,
            abs(d_vib) / 0.25,
            abs(d_bus_v) / 0.35,
        ]
        
        rms_z = math.sqrt(sum(z ** 2 for z in z_scores) / len(z_scores))
        max_z = max(z_scores)
        
        # Combined anomaly index (captures both multi-sensor drift and acute single-sensor failure)
        composite_z = 0.65 * max_z + 0.35 * rms_z
        anomaly_score = round(1.0 - math.exp(-0.45 * composite_z), 4)
        # Matches the documented anomaly regime: [0, 0.35) nominal, [0.35, 0.65) early
        # drift, [0.65, 1.0] fault/critical (majority-voting gate territory).
        is_anomaly = anomaly_score >= 0.65
        
        return ResidualVector(
            d_CHT_1=round(d_cht_1, 2),
            d_CHT_2=round(d_cht_2, 2),
            d_CHT_3=round(d_cht_3, 2),
            d_CHT_4=round(d_cht_4, 2),
            d_EGT_1=round(d_egt_1, 2),
            d_EGT_2=round(d_egt_2, 2),
            d_EGT_3=round(d_egt_3, 2),
            d_EGT_4=round(d_egt_4, 2),
            d_OIL_PRESS=round(d_oil_p, 2),
            d_OIL_TEMP=round(d_oil_t, 2),
            d_FUEL_FLOW=round(d_ff, 2),
            d_MAP=round(d_map, 2),
            d_VIB_RMS=round(d_vib, 3),
            d_BUS_VOLTAGE=round(d_bus_v, 2),
            anomaly_score=anomaly_score,
            is_anomaly=is_anomaly
        )
