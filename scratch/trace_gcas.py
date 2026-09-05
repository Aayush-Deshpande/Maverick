import sys
import math
import traceback

sys.path.insert(0, r"E:\backup-llm\backup-no-llm\3d_engine\apps\blender_twin")
import standalone_canyon_flight_app as app

st = app.FlightState()
st.fault_overheat = True
st.tactical_dive_active = True
st.dive_phase = "SEEK_CANYON"
st.target_canyon_alt = 3950.0
st.dive_target_bearing = math.radians(app.NOMINAL_HEADING_DEG)
st.cht_c = 135.0

# Wrap gcas_active with a property to catch the exact write!
class InstrumentFlightState(app.FlightState):
    def __init__(self):
        super().__init__()
        self._gcas_active = False

    @property
    def gcas_active(self):
        return self._gcas_active

    @gcas_active.setter
    def gcas_active(self, val):
        if val and not self._gcas_active:
            print(f"\n[INTERCEPT] gcas_active set to TRUE at Alt={self.pos.z:.1f}m, Pitch={math.degrees(self.pitch_rad):.1f}°!")
            traceback.print_stack()
        self._gcas_active = val

st = InstrumentFlightState()
st.fault_overheat = True
st.tactical_dive_active = True
st.dive_phase = "SEEK_CANYON"
st.target_canyon_alt = 3950.0
st.dive_target_bearing = math.radians(app.NOMINAL_HEADING_DEG)
st.cht_c = 135.0

for tick in range(100):
    app.update_simulation(st)
