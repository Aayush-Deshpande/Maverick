import unittest
import math
import sys
import os

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.physics.thermo_model import RotaxThermoModel, EnginePhysicalState, ResidualVector
from backend.telemetry.can_streamer import TelemetryStreamer, DRDO_FAULT_DEFINITIONS


class TestRotaxPhysicsAndTelemetry(unittest.TestCase):
    
    def setUp(self):
        self.thermo_model = RotaxThermoModel()
        self.streamer = TelemetryStreamer(sample_rate_hz=20.0)

    def test_ambient_properties_ladakh(self):
        """Test barometric pressure and density calculation at Ladakh altitude (20,000 ft)."""
        p_amb, t_k, rho_amb = self.thermo_model.get_ambient_properties(altitude_ft=20000.0, oat_c=-20.0)
        # Sea level is 101.3 kPa; at 20,000 ft pressure should be ~46-48 kPa
        self.assertGreater(p_amb, 40.0)
        self.assertLess(p_amb, 55.0)
        # Density should be lower than sea level (1.225 kg/m^3)
        self.assertLess(rho_amb, 0.85)
        self.assertGreater(rho_amb, 0.55)

    def test_ambient_properties_thar(self):
        """Test barometric pressure and density in Thar Desert heat (+45°C)."""
        p_amb, t_k, rho_amb = self.thermo_model.get_ambient_properties(altitude_ft=2000.0, oat_c=45.0)
        # Temperature in Kelvin should be 318.15 K
        self.assertAlmostEqual(t_k, 318.15, places=1)
        # Hot air is less dense
        self.assertLess(rho_amb, 1.15)

    def test_nominal_physics_baseline_generation(self):
        """Verify nominal physics baseline generates valid, non-negative values for all parameters."""
        state = self.thermo_model.compute_expected_state(
            altitude_ft=18000.0,
            oat_c=-15.0,
            rpm=5100.0,
            tps=70.0
        )
        self.assertGreaterEqual(len(state.to_dict()), 28) # 27 base params + injection/efficiency + timestamp
        self.assertGreater(state.INJ_TIMING_BTDC, 10.0) # HMS-11 injection timing
        self.assertGreater(state.BSFC_G_KWH, 200.0)     # VIS-07 BSFC efficiency
        self.assertGreater(state.POWER_KW, 20.0)        # INT-03 performance map power
        self.assertGreater(state.CHT_1, 50.0)
        self.assertLess(state.CHT_1, 130.0)
        self.assertGreater(state.OIL_PRESS, 2.0)
        self.assertLess(state.OIL_PRESS, 5.0)
        self.assertGreater(state.FUEL_FLOW, 10.0)
        self.assertAlmostEqual(state.PROP_RPM, 5100.0 / 2.43, delta=1.0)

    def test_nominal_residual_vector_near_zero(self):
        """Verify that in healthy flight, the residual vector remains near zero despite sensor noise."""
        actual, expected, residual = self.streamer.generate_frame(t_sec=10.0, region="LADAKH")
        
        # Residuals in nominal flight should be minimal (mostly sensor noise)
        self.assertLess(abs(residual.d_CHT_1), 1.5)
        self.assertLess(abs(residual.d_CHT_2), 1.5)
        self.assertLess(abs(residual.d_OIL_PRESS), 0.2)
        self.assertLess(residual.anomaly_score, 0.25)
        self.assertFalse(residual.is_anomaly)

    def test_fault_01_cylinder_2_overheat(self):
        """Verify Fault 01 (CHT #2 Overheat) triggers significant d_CHT_2 residual."""
        self.streamer.set_fault(fault_id=1, severity=1.0)
        # Advance time by 35 seconds to allow full fault ramp
        actual, expected, residual = self.streamer.generate_frame(t_sec=40.0, region="LADAKH")
        
        self.assertGreater(residual.d_CHT_2, 25.0) # > 25°C thermal drift
        self.assertLess(abs(residual.d_CHT_1), 2.0) # Cyl 1 remains nominal
        self.assertGreater(residual.anomaly_score, 0.70)
        self.assertTrue(residual.is_anomaly)
        self.assertEqual(actual.FAULT_ID, 1)

    def test_fault_02_injector_clog(self):
        """Verify Fault 02 (Fuel Injector Clog) drops fuel flow and raises EGT_1."""
        self.streamer.set_fault(fault_id=2, severity=1.0)
        actual, expected, residual = self.streamer.generate_frame(t_sec=40.0, region="LADAKH")
        
        self.assertLess(residual.d_FUEL_FLOW, -2.0) # Noticeable fuel flow drop
        self.assertGreater(residual.d_EGT_1, 40.0) # Lean burn EGT rise
        self.assertTrue(residual.is_anomaly)

    def test_fault_04_oil_pressure_loss(self):
        """Verify Fault 04 (Oil Pressure Loss) drops oil pressure below critical 2.0 bar."""
        self.streamer.set_fault(fault_id=4, severity=1.0)
        actual, expected, residual = self.streamer.generate_frame(t_sec=40.0, region="LADAKH")
        
        self.assertLess(actual.OIL_PRESS, 2.2)
        self.assertLess(residual.d_OIL_PRESS, -1.5)
        self.assertTrue(residual.is_anomaly)
        self.assertLess(actual.RUL_HOURS, 10.0)

    def test_fault_05_gearbox_vibration(self):
        """Verify Fault 05 (Gearbox Vibration) spikes vibration RMS."""
        self.streamer.set_fault(fault_id=5, severity=1.0)
        actual, expected, residual = self.streamer.generate_frame(t_sec=40.0, region="LADAKH")
        
        self.assertGreater(actual.VIB_GEARBOX_RMS, 2.5) # Critical threshold is 1.8 mm/s
        self.assertGreater(residual.d_VIB_RMS, 2.0)
        self.assertTrue(residual.is_anomaly)

    def test_fault_07_alternator_voltage_sag(self):
        """Verify Fault 07 (Alternator Sag) drops bus voltage below 12.8V."""
        self.streamer.set_fault(fault_id=7, severity=1.0)
        actual, expected, residual = self.streamer.generate_frame(t_sec=40.0, region="LADAKH")
        
        self.assertLess(actual.BUS_VOLTAGE, 12.8)
        self.assertLess(actual.BATTERY_CURRENT, 0.0) # Discharging
        self.assertTrue(residual.is_anomaly)

    def test_full_flight_log_generation(self):
        """Verify time-series flight log generation for 10 seconds (200 frames)."""
        log = self.streamer.generate_flight_log(duration_sec=10.0, region="THAR_DESERT", fault_id=0)
        self.assertEqual(len(log), 200) # 10s * 20 Hz
        self.assertIn("telemetry", log[0])
        self.assertIn("physics_baseline", log[0])
        self.assertIn("residuals", log[0])
        self.assertEqual(log[0]["telemetry"]["FLIGHT_PHASE"], "CRUISE_LOITER")


if __name__ == '__main__':
    unittest.main()
