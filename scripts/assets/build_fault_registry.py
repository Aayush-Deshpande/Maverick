"""One-off generator for configs/faults.json (card M0-02). Source: ANUMAAN_AUDIT_REPORT.txt section 22 (F01-F37, S01-S07),
ANUMAAN_COMPONENTS_ADDENDUM.txt section 5 (components), DECISIONS D9/D45. After generation configs/faults.json is
the source of truth; edit the JSON, not this script (re-running overwrites it).

Channel names follow backend/core/frame.py: rpm, prop_rpm, map_kpa, cht[{cyl}], egt[{cyl}], coolant_t, oil_p, oil_t,
fuel_flow, fuel_t, rail_p, ign_cmd, soi_cmd[{cyl}], bus_v, bus_i, batt_i, vibration_orders.<order>. Channels added
in M0-05: fuel_p, charge_t, turbo_rpm, gearbox_t, cov_imep, batt_soc, power_kw, lane_status, oil_qty.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "configs", "faults.json")

SI = {"field": "ignition_mode", "in": ["SPARK_IGNITION"]}
CI = {"field": "ignition_mode", "in": ["COMPRESSION_IGNITION"]}
TURBO = {"field": "induction", "in": ["TURBOCHARGED"]}
PORT_INJ = {"field": "fuel_system", "in": ["PORT_INJECTION"]}
RAIL = {"field": "fuel_system", "in": ["COMMON_RAIL"]}
CARB = {"field": "fuel_system", "in": ["CARBURETTOR"]}
INTERCOOLED = {"field": "turbo.intercooled", "in": [True]}
AIR_COOLED_PARTS = {"field": "cooling", "in": ["AIR_COOLED_BARRELS_LIQUID_HEADS"]}
CS_PROP = {"field": "propeller_governor", "in": [True]}
DUAL_LANE = {"field": "ecu_lanes", "in": [2]}
DUAL_IGNITION = {"field": "ignition_circuits", "in": [2]}
GLOW = {"field": "glow_plugs", "in": [True]}
THERMOSTAT = {"field": "thermostat", "in": [True]}
ALL = []


def sig(*items):
    return [{"channel": c, "direction": d, "min_delta": m, "unit": u} for c, d, m, u in items]


def fx(*items):
    return [{"component": c, "parameter": p, "op": op, "at_full_severity": v} for c, p, op, v in items]


def F(fid, name, scope, applies, effects, signature, window, status, ata, action, mitigation, explanation, ps,
      legacy_ids=(), plant_mode=None, severity=0.8, ramp=30.0, kind="PHYSICAL", channel_scope=None, desc=""):
    return {
        "id": fid, "name": name, "kind": kind, "scope": scope,
        "applies_when": applies, "legacy_ids": list(legacy_ids), "plant_mode_legacy": plant_mode,
        "parameter_effects": effects, "default_severity": severity, "default_ramp_s": ramp,
        "expected_signature": signature, "detect_window_s": window,
        "status_at_full_severity": status, "ata_chapter": ata,
        "maintenance_action": {"text": action, "source": "ANUMAAN-authored (audit R section 22)"},
        "mitigation_inflight": {"text": mitigation, "source": "ANUMAAN-authored; check against the engine OM abnormal-operation section"},
        "physics_explanation": explanation, "ps_categories": ps, "description": desc or name.replace("_", " ").lower(),
        "components": {}, "channel_scope": channel_scope,
    }


FAULTS = [
    F("F01", "IGNITION_MISFIRE", "CYLINDER", [SI], fx(("combustion", "quality[{cyl}]", "set", 0.0)),
      sig(("egt[{cyl}]", -1, 100, "C"), ("cht[{cyl}]", -1, 5, "C"), ("rpm", -1, 50, "rpm"),
          ("vibration_orders.0.5X", +1, 1.0, "mm/s")),
      30, "CAUTION", "74", "Check spark plugs, coil and lead of cylinder {cyl}; run a lane check.",
      "Reduce power, monitor EGT of the other cylinders, avoid prolonged high power.",
      "Cylinder {cyl} stops burning fuel: its torque contribution drops, so rpm falls and torque imbalance raises the half-order vibration; unburnt mixture lowers EGT {cyl}.",
      ["misfire"], legacy_ids=[3], plant_mode="MISFIRE", ramp=5.0),
    F("F02", "COMBUSTION_INSTABILITY", "CYLINDER", [], fx(("combustion", "cycle_variation[{cyl}]", "scale", 4.0)),
      sig(("cov_imep", +1, 2.0, "%"), ("vibration_orders.0.5X", +1, 0.5, "mm/s")),
      120, "ADVISORY", "73/74", "Inspect ignition (SI) or injector/injection pressure (CI) of cylinder {cyl}.",
      "Avoid lean operation and very low power; monitor roughness.",
      "Cycle-to-cycle combustion varies in cylinder {cyl}; mean values change little but rpm jitter, EGT noise and COV of IMEP rise.",
      ["combustion instability"]),
    F("F03", "DETONATION_KNOCK", "ENGINE", [SI], fx(("combustion", "knock_margin", "scale", 0.3)),
      sig(("cht[*]", +1, 5, "C"), ("vibration_orders.knock", +1, 0.5, "mm/s")),
      60, "CAUTION", "72/73", "Check fuel grade, cooling and ignition timing; inspect pistons if sustained.",
      "Reduce power and manifold pressure, enrich if possible, increase cooling airspeed.",
      "Reduced knock margin makes end-gas auto-ignite at high load: pressure spikes heat the heads and excite high-frequency vibration.",
      ["combustion instability", "overheating trends"]),
    F("F04", "IGNITION_LANE_FAILURE", "ENGINE", [SI, DUAL_IGNITION], fx(("ecu", "lane_b_ok", "set", 0.0)),
      sig(("rpm", -1, 50, "rpm"), ("egt[*]", +1, 15, "C"), ("lane_status", +1, 1, "state")),
      10, "CAUTION", "74/76", "Troubleshoot the failed ignition lane (wiring, coil, ECU lane).",
      "Continue on the remaining lane; land at the nearest suitable site per the flight manual.",
      "With one ignition circuit the flame front starts from one plug per cylinder: slower burn, later heat release, higher EGT and lower rpm.",
      ["misfire"]),
    F("F05", "INJECTOR_CLOG_SI", "CYLINDER", [SI, PORT_INJ], fx(("fuel", "injector_flow[{cyl}]", "scale", 0.6)),
      sig(("egt[{cyl}]", +1, 30, "C"), ("cht[{cyl}]", +1, 5, "C"), ("fuel_flow", -1, 0.2, "kg/h")),
      60, "CAUTION", "73", "Clean or replace injector {cyl}.",
      "Reduce power; watch EGT {cyl} and CHT {cyl} against their limits.",
      "Less fuel reaches cylinder {cyl}: the mixture goes lean, so EGT and head temperature rise while total fuel flow drops slightly.",
      ["injector abnormalities"], legacy_ids=[2]),
    F("F06", "INJECTOR_COKING_CI", "CYLINDER", [CI, RAIL], fx(("fuel", "injector_flow[{cyl}]", "scale", 0.7), ("combustion", "burn_duration[{cyl}]", "scale", 1.5)),
      sig(("egt[{cyl}]", +1, 30, "C"), ("vibration_orders.0.5X", +1, 0.5, "mm/s"), ("rpm", -1, 10, "rpm")),
      90, "CAUTION", "73", "Remove and test/replace injector {cyl}.",
      "Reduce power; avoid high-load climbs; monitor EGT {cyl}.",
      "Deposits reduce injector {cyl} flow and spoil atomisation: combustion is slower and later, so EGT {cyl} rises and the cylinder's torque falls.",
      ["injector abnormalities"], plant_mode="INJECTOR_COKING"),
    F("F07", "INJECTOR_STUCK_OPEN", "CYLINDER", [{"field": "fuel_system", "in": ["COMMON_RAIL", "PORT_INJECTION"]}],
      fx(("fuel", "injector_leak[{cyl}]", "add", 0.15)),
      sig(("egt[{cyl}]", +1, 60, "C"), ("fuel_flow", +1, 0.5, "kg/h"), ("rail_p", -1, 50, "bar")),
      20, "NO-GO", "73", "Replace injector {cyl}; inspect cylinder {cyl} and exhaust for damage.",
      "Reduce power immediately; land as soon as possible (fire and engine-damage risk).",
      "Injector {cyl} keeps delivering fuel: cylinder {cyl} runs rich and hot, fuel flow rises and the rail loses pressure through the open needle.",
      ["injector abnormalities"], severity=1.0, ramp=5.0),
    F("F08", "INJECTOR_STUCK_CLOSED", "CYLINDER", [CI, RAIL], fx(("fuel", "injector_flow[{cyl}]", "set", 0.0)),
      sig(("egt[{cyl}]", -1, 100, "C"), ("rpm", -1, 50, "rpm"), ("vibration_orders.0.5X", +1, 1.0, "mm/s")),
      30, "CAUTION", "73", "Replace injector {cyl} (needle stuck).",
      "Reduce power; expect rough running; land at the nearest suitable site.",
      "No fuel reaches cylinder {cyl}, so it behaves like a misfire on a diesel: torque imbalance and a cold exhaust on that cylinder.",
      ["misfire", "injector abnormalities"], plant_mode="INJECTOR_NEEDLE_STICK", ramp=5.0),
    F("F09", "RAIL_PRESSURE_DECAY", "ENGINE", [CI, RAIL], fx(("fuel", "hp_pump_health", "scale", 0.6)),
      sig(("rail_p", -1, 100, "bar"), ("egt[*]", +1, 15, "C")),
      60, "CAUTION", "73", "Check the HP pump, rail pressure-limiting valve and rail pressure sensor.",
      "Avoid high power demands; the FADEC may limit power.",
      "The HP pump delivers less or the relief valve leaks: rail pressure falls, injection takes longer and atomisation worsens, so EGT rises and full power is limited.",
      ["injector abnormalities"], plant_mode="RAIL_PRESSURE_DECAY"),
    F("F10", "FUEL_SUPPLY_LOW_PRESSURE", "ENGINE", ALL, fx(("fuel", "lp_supply_health", "scale", 0.5)),
      sig(("fuel_p", -1, 0.3, "bar"), ("power_kw", -1, 2, "kW")),
      60, "CAUTION", "28/73", "Check the fuel filter, low-pressure pumps and lines.",
      "Switch to the auxiliary pump if available; reduce power; plan to land.",
      "The low-pressure supply cannot keep up: inlet fuel pressure falls, at high power the delivered fuel is limited, so power falls (SI engines also run lean).",
      ["injector abnormalities"]),
    F("F11", "INJECTION_TIMING_DRIFT", "ENGINE", [{"field": "fuel_system", "in": ["COMMON_RAIL", "PORT_INJECTION"]}],
      fx(("ecu", "timing_offset_deg", "add", -6.0)),
      sig(("egt[*]", +1, 20, "C"), ("fuel_flow", +1, 0.2, "kg/h")),
      120, "ADVISORY", "73/76", "Check crank/cam sensors and ECU timing calibration.",
      "Monitor EGT; reduce power if EGT approaches the limit.",
      "Combustion is retarded: less of the fuel energy becomes work and more leaves with the exhaust, so EGT and fuel per unit power rise.",
      ["injection timing"], legacy_ids=[8]),
    F("F12", "CARBURETTOR_ICING", "ENGINE", [CARB], fx(("induction", "carb_throat_area", "scale", 0.7)),
      sig(("map_kpa", -1, 3, "kPa"), ("rpm", -1, 50, "rpm")),
      120, "CAUTION", "73", "Check carburettor heating; review icing conditions.",
      "Apply carburettor heat if fitted; change altitude out of the icing conditions.",
      "Ice narrows the carburettor throat: less air enters, manifold pressure and power fall gradually.",
      ["abnormal operating conditions"]),
    F("F13", "AIR_FILTER_BLOCKAGE", "ENGINE", ALL, fx(("induction", "filter_loss_coeff", "scale", 6.0)),
      sig(("map_kpa", -1, 3, "kPa"), ("power_kw", -1, 1, "kW")),
      300, "ADVISORY", "72", "Replace/clean the air filter; check the intake for obstructions.",
      "Expect reduced full power; avoid dusty low-level flight.",
      "The filter's pressure loss grows with clogging: manifold pressure and air mass flow drop, so full power drops (turbo engines compensate with more turbo work).",
      ["abnormal operating conditions"], plant_mode="AIR_FILTER_BLOCKAGE", ramp=300.0),
    F("F14", "BOOST_LEAK", "ENGINE", [TURBO], fx(("turbo", "charge_leak_fraction", "add", 0.15)),
      sig(("map_kpa", -1, 5, "kPa"), ("turbo_rpm", +1, 2000, "rpm")),
      120, "CAUTION", "81", "Inspect charge-air hoses, clamps and intercooler for leaks.",
      "Expect lower critical altitude; avoid high-altitude high-power segments.",
      "Charge air escapes between compressor and manifold: the controller spins the turbo harder, but manifold pressure stays below target and power falls earlier with altitude.",
      ["abnormal operating conditions"], plant_mode="BOOST_LEAK"),
    F("F15", "WASTEGATE_STUCK_OPEN", "ENGINE", [TURBO], fx(("turbo", "wastegate_position", "set", 1.0)),
      sig(("map_kpa", -1, 15, "kPa"), ("egt[*]", -1, 20, "C"), ("turbo_rpm", -1, 10000, "rpm")),
      60, "CAUTION", "81", "Inspect the wastegate/VGT actuator and linkage.",
      "Power is limited to roughly naturally-aspirated levels; descend if altitude cannot be held.",
      "Exhaust bypasses the turbine: turbo speed and boost collapse, manifold pressure falls towards ambient, fuel and EGT fall with power.",
      ["abnormal operating conditions"], plant_mode="WASTEGATE_STUCK_OPEN"),
    F("F16", "WASTEGATE_STUCK_CLOSED", "ENGINE", [TURBO], fx(("turbo", "wastegate_position", "set", 0.0)),
      sig(("map_kpa", +1, 10, "kPa"), ("egt[*]", +1, 20, "C")),
      30, "NO-GO", "81", "Inspect the wastegate/VGT actuator; check for engine over-boost damage.",
      "Reduce throttle to keep manifold pressure inside its limit; land as soon as practical.",
      "Boost is not relieved: manifold pressure rises above target, power and temperatures rise, with knock risk on spark-ignition engines.",
      ["abnormal operating conditions", "overheating trends"], severity=1.0),
    F("F17", "TURBO_BEARING_WEAR", "ENGINE", [TURBO], fx(("turbo", "bearing_friction", "scale", 3.0)),
      sig(("map_kpa", -1, 3, "kPa"), ("vibration_orders.turbo", +1, 0.3, "mm/s"), ("oil_t", +1, 2, "C")),
      600, "ADVISORY", "81", "Inspect the turbocharger bearings (shaft play, oil leakage).",
      "Avoid rapid throttle changes; monitor oil temperature.",
      "Higher bearing friction absorbs turbine power: slower spool-up, lower boost at high altitude, extra heat into the oil, and a turbo-speed vibration line.",
      ["abnormal vibration"], plant_mode="TURBO_BEARING_WEAR", ramp=600.0),
    F("F18", "INTERCOOLER_FOULING", "ENGINE", [TURBO, INTERCOOLED], fx(("turbo", "intercooler_effectiveness", "scale", 0.5)),
      sig(("charge_t", +1, 10, "C"), ("power_kw", -1, 1, "kW")),
      600, "ADVISORY", "81", "Clean the intercooler core and check its airflow.",
      "Avoid sustained full power in hot conditions.",
      "Lower intercooler effectiveness leaves the charge hotter and less dense: power falls and temperatures rise.",
      ["overheating trends"], ramp=600.0),
    F("F19", "COOLING_AIR_DEGRADATION", "CYLINDER", [AIR_COOLED_PARTS], fx(("thermal", "air_cooling_effectiveness[{cyl}]", "scale", 0.6)),
      sig(("cht[{cyl}]", +1, 10, "C"), ("oil_t", +1, 2, "C")),
      600, "CAUTION", "72/75", "Inspect cylinder baffles and cowling seals around cylinder {cyl}.",
      "Increase airspeed, reduce power, watch the temperature trend.",
      "Less cooling air reaches cylinder {cyl}: the heat balance shifts and its head temperature trends upward.",
      ["cooling degradation", "overheating trends"], legacy_ids=[1], plant_mode="COOLING_DEGRADATION", ramp=600.0),
    F("F20", "COOLANT_LOSS", "ENGINE", ALL, fx(("coolant", "pump_flow_health", "scale", 0.4)),
      sig(("coolant_t", +1, 10, "C"), ("cht[*]", +1, 5, "C")),
      300, "CAUTION", "75", "Check the coolant level, water pump and hoses for leaks.",
      "Reduce power; land before the coolant limit is reached.",
      "Less coolant flow removes less head heat: coolant and head temperatures rise quickly; oil temperature follows.",
      ["cooling degradation", "overheating trends"], ramp=300.0),
    F("F21", "RADIATOR_BLOCKAGE", "ENGINE", ALL, fx(("coolant", "radiator_effectiveness", "scale", 0.5)),
      sig(("coolant_t", +1, 8, "C")),
      600, "ADVISORY", "75", "Clean the radiator core; check the airflow path.",
      "Increase airspeed; avoid low-speed high-power segments in heat.",
      "The radiator rejects less heat, worst at low airspeed and high OAT: coolant temperature trends upward.",
      ["cooling degradation", "overheating trends"], ramp=600.0),
    F("F22", "THERMOSTAT_STUCK", "ENGINE", [THERMOSTAT], fx(("coolant", "thermostat_opening", "set", 1.0)),
      sig(("coolant_t", -1, 10, "C")),
      600, "ADVISORY", "75", "Replace the thermostat.",
      "On a stuck-open thermostat, respect the minimum coolant temperature before take-off power.",
      "The thermostat stays open: the coolant runs too cold (or too hot when stuck closed); oil temperature follows.",
      ["cooling degradation"]),
    F("F23", "OIL_PRESSURE_LOSS", "ENGINE", ALL, fx(("oil", "pump_health", "scale", 0.35)),
      sig(("oil_p", -1, 0.8, "bar"), ("oil_t", +1, 3, "C")),
      60, "NO-GO", "79", "Inspect the oil pump, pressure relief valve and oil lines; check bearings.",
      "Reduce power; land as soon as possible; prepare for engine failure if pressure keeps falling.",
      "Pump capacity falls (or the relief valve bypasses): oil pressure drops, bearing friction rises, oil heats and thins, which drops pressure further until the bearings seize.",
      ["lubrication issues"], legacy_ids=[4], plant_mode="OIL_PRESSURE_LOSS", severity=0.8, ramp=60.0),
    F("F24", "OIL_LEAK_LOW_QUANTITY", "ENGINE", ALL, fx(("oil", "leak_rate_l_per_h", "add", 0.5)),
      sig(("oil_qty", -1, 0.2, "l"), ("oil_p", -1, 0.3, "bar")),
      900, "CAUTION", "79", "Find and fix the oil leak; replenish oil.",
      "Monitor oil pressure; land before quantity falls below the minimum.",
      "Oil is lost steadily: quantity falls, then the pump starts to cavitate, so pressure fluctuates and falls while oil temperature rises.",
      ["lubrication issues"], ramp=1.0),
    F("F25", "OIL_COOLER_BLOCKAGE", "ENGINE", ALL, fx(("oil", "cooler_effectiveness", "scale", 0.4)),
      sig(("oil_t", +1, 8, "C"), ("oil_p", -1, 0.1, "bar")),
      900, "CAUTION", "79", "Clean the oil cooler and check its airflow.",
      "Reduce power; increase airspeed; watch the oil temperature trend.",
      "The oil cooler rejects less heat: oil temperature trends upward and the thinner oil gives slightly lower pressure.",
      ["lubrication issues", "overheating trends"], ramp=900.0),
    F("F26", "BEARING_WEAR", "ENGINE", ALL, fx(("oil", "bearing_clearance", "scale", 1.5)),
      sig(("oil_p", -1, 0.2, "bar"), ("vibration_orders.1X", +1, 0.3, "mm/s")),
      3600, "ADVISORY", "72", "Oil analysis (wear metals); inspect the bearings.",
      "No immediate action; plan maintenance before RUL runs out.",
      "Larger bearing clearances leak more oil: pressure is lower at hot idle, friction and the first-order vibration rise slowly.",
      ["lubrication issues", "abnormal vibration"], ramp=3600.0),
    F("F27", "GEARBOX_DAMAGE", "ENGINE", ALL, fx(("gearbox", "tooth_damage", "set", 1.0)),
      sig(("vibration_orders.gear_mesh", +1, 0.5, "mm/s"), ("gearbox_t", +1, 3, "C")),
      300, "CAUTION", "72/61", "Inspect the reduction gearbox (gear teeth, bearings, oil).",
      "Reduce power; avoid abrupt throttle changes.",
      "Damaged gear teeth excite the gear-mesh frequency and add friction, so the gearbox runs hotter.",
      ["abnormal vibration"], legacy_ids=[5]),
    F("F28", "PROPELLER_IMBALANCE", "ENGINE", ALL, fx(("rotor", "prop_imbalance", "set", 1.0)),
      sig(("vibration_orders.prop_1X", +1, 0.5, "mm/s")),
      60, "ADVISORY", "61", "Inspect and balance the propeller.",
      "Reduce rpm if vibration is high.",
      "A mass or aerodynamic imbalance of the propeller produces a once-per-propeller-revolution vibration; nothing thermal changes.",
      ["abnormal vibration"]),
    F("F29", "ENGINE_MOUNT_DEGRADATION", "ENGINE", ALL, fx(("vibration", "mount_transmissibility", "scale", 2.0)),
      sig(("vibration_orders.1X", +1, 0.3, "mm/s"), ("vibration_orders.2X", +1, 0.3, "mm/s")),
      600, "ADVISORY", "71", "Inspect the engine mounts and isolators.",
      "No immediate action; avoid high-vibration rpm bands.",
      "Worn mounts transmit more of every vibration order to the airframe sensors: all orders rise together.",
      ["abnormal vibration"]),
    F("F30", "COMPRESSION_LOSS", "CYLINDER", ALL, fx(("combustion", "compression_health[{cyl}]", "scale", 0.7)),
      sig(("vibration_orders.0.5X", +1, 0.5, "mm/s"), ("egt[{cyl}]", +1, 10, "C")),
      600, "ADVISORY", "72", "Compression / leak-down test of cylinder {cyl} (rings, valves).",
      "No immediate action; monitor roughness.",
      "Leakage past rings or valves lowers cylinder {cyl}'s compression and torque, creating torque imbalance; blow-by heats the oil.",
      ["combustion instability"]),
    F("F31", "EXHAUST_LEAK_EGT_IMBALANCE", "CYLINDER", ALL, fx(("exhaust", "leak[{cyl}]", "set", 1.0)),
      sig(("egt[{cyl}]", -1, 30, "C")),
      120, "ADVISORY", "78", "Inspect the exhaust manifold, gaskets and EGT probe of cylinder {cyl}.",
      "Monitor; check for exhaust smell / CO in crewed installations.",
      "Exhaust leaks at cylinder {cyl}: its EGT reading deviates and turbo engines lose some turbine energy.",
      ["combustion instability"], legacy_ids=[6]),
    F("F32", "ALTERNATOR_DEGRADATION", "ENGINE", ALL, fx(("electrical", "alternator_health", "scale", 0.3)),
      sig(("bus_v", -1, 0.5, "V"), ("batt_i", -1, 2, "A")),
      120, "CAUTION", "24", "Check the alternator/generator, regulator, belt and wiring.",
      "Shed non-essential electrical loads; check remaining battery endurance against the mission.",
      "The alternator cannot supply the load: the battery starts discharging, so battery current turns negative and bus voltage sags as charge falls.",
      ["battery/alternator health"], legacy_ids=[7]),
    F("F33", "VOLTAGE_REGULATOR_FAULT", "ENGINE", ALL, fx(("electrical", "regulator_setpoint_offset_v", "add", 1.5)),
      sig(("bus_v", +1, 0.8, "V")),
      30, "CAUTION", "24", "Replace the voltage regulator.",
      "Over-voltage: disconnect the alternator per procedure; shed loads.",
      "The regulator holds the wrong setpoint: the bus voltage sits steadily too high (or too low).",
      ["battery/alternator health"]),
    F("F34", "BATTERY_DEGRADATION", "ENGINE", ALL, fx(("electrical", "battery_capacity", "scale", 0.4), ("electrical", "battery_resistance", "scale", 2.5)),
      sig(("bus_v", -1, 0.3, "V")),
      600, "ADVISORY", "24", "Capacity-test or replace the battery.",
      "Avoid relying on battery endurance; keep the alternator online.",
      "Lower capacity and higher internal resistance: voltage drops more under load and charge falls faster.",
      ["battery/alternator health"]),
    F("F35", "GLOW_PLUG_FAILURE", "CYLINDER", [CI, GLOW], fx(("combustion", "glow_plug_ok[{cyl}]", "set", 0.0)),
      sig(("egt[{cyl}]", -1, 20, "C")),
      120, "ADVISORY", "74", "Replace glow plug {cyl}.",
      "Allow a longer warm-up before take-off.",
      "Only matters at cold start: cylinder {cyl} misfires and smokes until it is warm.",
      ["misfire"]),
    F("F36", "ECU_LANE_FAILURE", "ENGINE", [DUAL_LANE], fx(("ecu", "lane_a_ok", "set", 0.0)),
      sig(("lane_status", +1, 1, "state")),
      10, "CAUTION", "73/76", "Troubleshoot the failed ECU lane (power supply, wiring, ECU).",
      "Continue on the remaining lane; no dispatch until repaired.",
      "One control lane is offline; the engine runs on the other with less redundancy and small rpm/EGT changes.",
      ["sensor/control"]),
    F("F37", "PROP_GOVERNOR_FAULT", "ENGINE", [CS_PROP], fx(("rotor", "governor_gain", "scale", 4.0)),
      sig(("prop_rpm", 0, 30, "rpm")),
      60, "CAUTION", "61", "Inspect the propeller governor (PCU) and its oil supply.",
      "Avoid rapid power changes; watch for over-speed; set a fixed power if the rpm hunts.",
      "The governor loses control of blade pitch: propeller rpm hunts around the setpoint (direction 0 = oscillation) with over-speed risk.",
      ["abnormal operating conditions"]),
]

SENSOR_FAULTS = [
    ("S01", "SENSOR_STUCK", "freeze", "reading frozen at its last value", "SENSOR_STUCK"),
    ("S02", "SENSOR_BIAS", "bias", "constant offset", None),
    ("S03", "SENSOR_DRIFT", "drift", "offset growing over time (demo-visible rate)", "SENSOR_BIAS_DRIFT"),
    ("S04", "SENSOR_NOISE", "noise", "noise level increased", None),
    ("S05", "SENSOR_DROPOUT", "dropout", "no value / invalid flag", None),
    ("S06", "SENSOR_OUT_OF_RANGE", "out_of_range", "physically impossible value (short/open circuit)", None),
    ("S07", "SENSOR_LANE_DISAGREEMENT", "lane_split", "dual sensors disagree", None),
]
for sid, name, mode, desc, legacy in SENSOR_FAULTS:
    entry = F(sid, name, "CHANNEL", ALL, fx(("sensors", f"{{channel}}.{mode}", "set", 1.0)),
              sig(("{channel}", 0, 0, "channel unit")), 120, "ADVISORY", "77/79",
              "Replace or recalibrate the {channel} sensor and check its wiring.",
              "Treat {channel} as unavailable; use the twin's virtual value; if the channel is safety-critical (oil pressure, CHT/coolant) land as soon as practical.",
              "Only the {channel} measurement is wrong; the engine itself is healthy, so physically related channels do not move with it.",
              ["sensor drift/failure"], plant_mode=legacy, kind="SENSOR", desc=desc)
    entry["expected_signature"] = [{"channel": "{channel}", "direction": 0, "min_delta": 0, "unit": "channel unit",
                                    "note": "only this channel changes; related channels stay consistent"}]
    FAULTS.append(entry)

registry = {
    "schema_version": 1,
    "source": "ANUMAAN_AUDIT_REPORT.txt section 22; DECISIONS D9, D45",
    "channel_note": "Channels follow backend/core/frame.py. {cyl} = cylinder number, [*] = all cylinders, {channel} = the sensor channel chosen at injection. direction +1/-1 = up/down, 0 = oscillation or channel-only change.",
    "faults": FAULTS,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(registry, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
print(f"wrote {OUT}: {len(FAULTS)} faults")

# components come from the addendum NOW lists (card M0-03); keep them after a regeneration
import sys as _sys  # noqa: E402
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fill_fault_components  # noqa: E402
fill_fault_components.main()
