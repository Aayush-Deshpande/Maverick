"""Card M0-03: fill configs/faults.json "components" per engine from ANUMAAN_COMPONENTS_ADDENDUM.txt section 5
(the NOW lists, valid for today's models). Phase 7 (card B-06) adds the TARGET lists after the Blender work.

Per fault and engine: {"now": [component ids, "{cyl}" allowed], "marker": bool, "marker_for": text}
marker=true means a part the fault points at does not exist in the model yet; the viewer shows a location marker
with the NOW parts (A section 5). Sensor faults use a channel -> component table instead.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REG = os.path.join(ROOT, "configs", "faults.json")
E912, E914, E915, AE, VR = "rotax_912is", "rotax_914", "rotax_915is", "austro_ae300", "vrde_jayem_2_2l"


def c(now, marker_for=None):
    return {"now": now, "marker": bool(marker_for), "marker_for": marker_for}


ROTAX_CYL = {E912: c(["wiring_harness"], "spark plug / coil of cylinder {cyl}"),
             E914: c(["cylinder_bank_unverified"], "cylinder {cyl} head and plugs"),
             E915: c(["main_engine_MERGED"], "cylinder {cyl}")}

MAP = {
    "F01": ROTAX_CYL,
    "F02": {**ROTAX_CYL, AE: c(["injector_{cyl}", "fuel_line_{cyl}"]), VR: c(["injector_{cyl}", "fuel_line_hp_{cyl}"])},
    "F03": {E912: c(["crankcase_cylinders_base"], "cylinder heads"), E914: c(["cylinder_bank_unverified"]),
            E915: c(["main_engine_MERGED"], "cylinder heads")},
    "F04": {E912: c(["ecu", "wiring_harness"]), E914: c([], "ignition CDI modules"), E915: c(["ecu", "fusebox"])},
    "F05": {E912: c(["fuel_pump"], "injector {cyl} / fuel rail"), E915: c(["main_engine_MERGED"], "injector {cyl}")},
    "F06": {AE: c(["injector_{cyl}", "fuel_line_{cyl}"]), VR: c(["injector_{cyl}", "fuel_line_hp_{cyl}"])},
    "F07": {AE: c(["injector_{cyl}", "common_rail"]), VR: c(["injector_{cyl}", "fuel_return"]),
            E912: c(["fuel_pump"], "injector {cyl} / fuel rail"), E915: c(["main_engine_MERGED"], "injector {cyl}")},
    "F08": {AE: c(["injector_{cyl}"]), VR: c(["injector_{cyl}"])},
    "F09": {AE: c(["hp_fuel_pump", "common_rail", "rail_pressure_valve", "sensor_fuel_rail_press"]),
            VR: c(["hp_fuel_pump", "common_rail", "rail_relief_valve", "rail_pressure_sensor"])},
    "F10": {E912: c(["fuel_pump"]), E914: c([], "fuel pump / carburettors"), E915: c([], "fuel pump"),
            AE: c(["fuel_metering_unit", "aux_fuel_pump", "sensor_fuel_low_press"]), VR: c(["fuel_filter"])},
    "F11": {E912: c(["ecu"]), E914: c([], "ignition CDI modules"), E915: c(["ecu"]),
            AE: c(["ecu_lane_a", "ecu_lane_b", "sensor_cam", "sensor_crank"]),
            VR: c(["sensor_crank_1", "sensor_crank_2", "wiring_harness"])},
    "F12": {E914: c(["intake_manifold"], "carburettors 1-2")},
    "F13": {E912: c([], "airbox / air filter"), E914: c(["intake_manifold"]), E915: c([], "airbox / air filter"),
            AE: c(["air_filter"]), VR: c(["intake_manifold"], "airbox / air filter")},
    "F14": {E914: c(["turbo_compressor", "intake_manifold"]), E915: c(["intercooler"]),
            AE: c(["boost_pipes", "intercooler"]), VR: c(["turbo_ducts", "intercooler"])},
    "F15": {E914: c(["turbo_turbine"], "wastegate (the 'wastegate' objects are missegmented)"),
            E915: c(["overboost_valve", "magneto_valve_block"]), AE: c(["turbocharger"], "VGT actuator"),
            VR: c(["wastegate"])},
    "F17": {E914: c(["turbo_compressor", "turbo_turbine"]), E915: c([], "turbocharger"),
            AE: c(["turbocharger", "turbo_oil_lines"]), VR: c(["turbo_hp", "turbo_lp", "turbo_oil_drain", "turbo_oil_feed"])},
    "F18": {E915: c(["intercooler"]), AE: c(["intercooler", "sensor_charge_air_temp"]),
            VR: c(["intercooler", "sensor_charge_air_temp"])},
    "F19": {E912: c(["cooling_air_baffle"]), E914: c(["cylinder_bank_unverified"], "baffles"), E915: c(["air_baffles"])},
    "F20": {E912: c(["coolant_hoses"]), E914: c(["coolant_lines"]), E915: c([], "coolant hoses / water pump"),
            AE: c(["water_pump", "coolant_hoses", "sensor_coolant_temp"]),
            VR: c(["water_pump", "coolant_hoses", "sensor_coolant_temp"])},
    "F21": {e: c([], "radiator") for e in (E912, E914, E915, AE, VR)},
    "F22": {AE: c([], "thermostat"), VR: c(["thermostat"])},
    "F23": {E912: c(["oil_tank"]), E914: c(["crankcase"], "oil tank / oil pump"), E915: c(["oil_tank"]),
            AE: c(["oil_sump", "oil_filter", "sensor_oil_press"]), VR: c(["oil_sump", "oil_filter", "sensor_oil_press"])},
    "F24": {E912: c(["oil_tank"]), E914: c(["crankcase"], "oil tank"), E915: c(["oil_tank"]),
            AE: c(["oil_sump", "crankcase_breather"]), VR: c(["oil_sump", "crankcase_breather"])},
    "F25": {E912: c([], "oil cooler"), E914: c([], "oil cooler"), E915: c([], "oil cooler"),
            AE: c(["oil_cooler", "sensor_oil_temp"]), VR: c(["oil_cooler", "sensor_oil_temp"])},
    "F26": {E912: c(["crankcase_cylinders_base"]), E914: c(["crankcase"]), E915: c(["main_engine_MERGED"]),
            AE: c(["engine_block", "oil_filter"]), VR: c(["engine_block", "oil_filter"])},
    "F27": {E912: c(["gearbox"]), E914: c(["gearbox"]), E915: c(["gearbox"]),
            AE: c(["gearbox", "sensor_gearbox_temp", "sensor_gearbox_press"]), VR: c(["gearbox", "sensor_gearbox_vibration"])},
    "F28": {E912: c([], "propeller flange"), E914: c(["prop_flange"]), E915: c([], "propeller flange"),
            AE: c(["prop_flange"]), VR: c(["prop_flange"])},
    "F29": {E912: c(["engine_mount"]), E914: c([], "engine mount"), E915: c([], "engine mount"),
            AE: c(["engine_mount"]), VR: c(["engine_mount"])},
    "F30": {E912: c(["crankcase_cylinders_base"], "cylinder {cyl}"), E914: c(["cylinder_bank_unverified"]),
            E915: c(["main_engine_MERGED"], "cylinder {cyl}"), AE: c(["cylinder_head"], "cylinder {cyl}"),
            VR: c(["cylinder_head"], "cylinder {cyl}")},
    "F31": {E912: c(["exhaust"]), E914: c(["exhaust"]), E915: c([], "exhaust"),
            AE: c(["exhaust", "sensor_egt_{cyl}"]), VR: c(["exhaust", "sensor_egt_{cyl}"])},
    "F32": {E912: c(["alternator"]), E914: c([], "alternator"), E915: c([], "alternator"),
            AE: c(["alternator", "belt_drive"]), VR: c(["alternator_1", "belt_drive", "alternator_wiring"])},
    "F33": {E912: c(["alternator", "wiring_harness"]), E914: c([], "voltage regulator"), E915: c(["fusebox"], "voltage regulator"),
            AE: c(["alternator", "wiring_harness"]), VR: c(["alternator_wiring", "wiring_harness"])},
    "F34": {E912: c(["starter", "starter_relay"], "battery (airframe-mounted; 2D panel)"),
            E914: c(["starter"], "battery (airframe-mounted; 2D panel)"), E915: c([], "battery (airframe-mounted; 2D panel)"),
            AE: c(["starter"], "battery (airframe-mounted; 2D panel)"), VR: c(["starter"], "battery (airframe-mounted; 2D panel)")},
    "F35": {AE: c(["glow_plugs", "glow_control_unit"], "glow plug {cyl} (all four are one object)"), VR: c(["glow_plug_{cyl}"])},
    "F36": {E912: c(["ecu"]), E915: c(["ecu", "fusebox"]), AE: c(["ecu_lane_a"]), VR: c(["ecu_lane_a"])},
    "F37": {AE: c(["prop_governor"]), VR: c(["prop_governor"])},
}
MAP["F16"] = MAP["F15"]

# Sensor faults S01-S07: channel -> component per engine (A section 5, last block)
SENSOR_MAP = {
    AE: {"egt[{cyl}]": ["sensor_egt_{cyl}"], "oil_p": ["sensor_oil_press"], "oil_t": ["sensor_oil_temp"],
         "coolant_t": ["sensor_coolant_temp"], "map_kpa": ["sensor_boost"], "fuel_flow": ["sensor_fuel_flow"],
         "fuel_p": ["sensor_fuel_low_press"], "rail_p": ["sensor_fuel_rail_press"], "rpm": ["sensor_rpm", "sensor_crank"],
         "charge_t": ["sensor_charge_air_temp"], "gearbox_t": ["sensor_gearbox_temp"], "fuel_t": ["sensor_fuel_temp"]},
    VR: {"egt[{cyl}]": ["sensor_egt_{cyl}"], "oil_p": ["sensor_oil_press"], "oil_t": ["sensor_oil_temp"],
         "coolant_t": ["sensor_coolant_temp"], "map_kpa": ["sensor_map", "sensor_boost"], "fuel_flow": ["sensor_fuel_flow"],
         "rail_p": ["rail_pressure_sensor"], "rpm": ["sensor_rpm", "sensor_crank_1"], "charge_t": ["sensor_charge_air_temp"],
         "vibration_orders.*": ["sensor_gearbox_vibration"]},
    E912: {"*": ["ecu"]},
    E915: {"*": ["ecu"]},
    E914: {"*": []},
}


def main():
    reg = json.load(open(REG, encoding="utf-8"))
    for f in reg["faults"]:
        if f["kind"] == "SENSOR":
            f["components"] = {e: {"by_channel": m, "marker": e in (E912, E914, E915),
                                   "marker_for": "sensor part (not modelled yet; label shows the channel)" if e in (E912, E914, E915) else None}
                               for e, m in SENSOR_MAP.items()}
        else:
            f["components"] = MAP.get(f["id"], {})
    with open(REG, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(reg, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("components filled for", sum(1 for f in reg["faults"] if f["components"]), "faults")


if __name__ == "__main__":
    main()
