"""Card M0-01: engine data corrections with provenance (P Part 2, DECISIONS D7/D16/D46/D47).

Sources (local copies in docs/reference/; OEM/EASA PDFs in docs/reference/oem/ are gitignored, see SOURCES.txt):
  OM912i  = BRP-Rotax Operators Manual OM-912 i, Ed.2 Rev.1, 01 June 2019, pages 2-2..2-5
  E121    = EASA TCDS E.121 issue 17, 18 Dec 2023 (912 iSc Sport, 915 iSc A/C24), pages 22-24 + ratings
  E200    = EASA TCDS E.200 issue 12, 30 Jun 2020 (Austro E4 = AE300), pages 5-7
  OM914   = BRP-Rotax Operators Manual 914 (docs/reference/Rotax914_Operators_Manual.pdf), pages 2-2..2-4
  DRDO    = DRDO product page "180 hp diesel engine for UAV" + VRDE brochure summaries (P Part 11)
Prints an old -> new table. Existing flat operating_limits keys are kept (backend/core/limits.py and tests use them);
new limits go into the banded "limits" block.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CFG = os.path.join(ROOT, "configs", "engines")

OM912i = "BRP-Rotax OM-912 i Ed.2 Rev.1 (2019-06-01)"
E121 = "EASA TCDS E.121 issue 17 (2023-12-18)"
E200 = "EASA TCDS E.200 issue 12 (2020-06-30)"
OM914 = "BRP-Rotax Operators Manual 914 (docs/reference/Rotax914_Operators_Manual.pdf)"
DRDO = "DRDO product page '180 hp diesel engine for UAV' (drdo.gov.in) + VRDE brochure summaries"

CHANGES = {
    "rotax_912is": {
        "set": {
            "max_continuous_power_kw": (72.0, "MANUAL", f"{OM912i} p.2-2: 72 kW at 5500 rpm for 912 iS Sport / iSc (69 kW is the plain 912 iS); also {E121}"),
            "rated_power_kw": (73.5, "MANUAL", f"{OM912i} p.2-2: take-off 73.5 kW at 5800 rpm (max 5 min)"),
            "rated_rpm": (5800.0, "MANUAL", f"{OM912i} p.2-2"),
            "max_continuous_rpm": (5500.0, "MANUAL", f"{OM912i} p.2-2"),
            "idle_rpm": (1400.0, "MANUAL", f"{OM912i} p.2-2: idle speed min. 1400 rpm"),
            "rail_pressure_bar": (3.0, "MANUAL", f"{OM912i} p.2-4: fuel pressure at rail 2.8-3.2 bar (nominal = mid band); also {E121} p.23"),
            "oil_capacity_l": (3.0, "PUBLIC", f"{E121} p.24: oil capacity 3.0 l at max mark, 2.5 l at min mark"),
            "fuel_system": "PORT_INJECTION", "ignition_circuits": 2, "ecu_lanes": 2,
            "glow_plugs": False, "thermostat": False, "propeller_governor": False,
        },
        "limits_flat": {
            "egt_max_c": (950.0, "MANUAL", f"{OM912i} p.2-4: exhaust gas temperature max 950 C (was 850, unsourced)"),
            "oil_t_max_c": (130.0, "MANUAL", f"{OM912i} p.2-3; {E121} p.22"),
            "oil_p_min_bar": (0.8, "MANUAL", f"{OM912i} p.2-3: min 0.8 bar below 3500 rpm; normal 2.0-5.0 bar above 3500 rpm"),
            "cht_max_c": (135.0, "PUBLIC", f"{E121} p.22 gives CHT 135 C for the 912 S series only; OM-912 i lists COOLANT 120 C as the head limit. Kept for the legacy limit checker until the banded limits replace it (M2-01)"),
            "coolant_t_max_c": (120.0, "MANUAL", f"{OM912i} p.2-4; {E121} p.22"),
            "oil_p_max_bar": (7.0, "MANUAL", f"{OM912i} p.2-3: max 7 bar, short period at cold start"),
        },
        "limits": {
            "oil_p": {"unit": "bar", "warning_low": 0.8, "normal": [2.0, 5.0], "warning_high": 7.0,
                      "rpm_rule": {"above_rpm": 3500, "normal": [2.0, 5.0], "below_min": 0.8}, "ref": f"{OM912i} p.2-3"},
            "oil_t": {"unit": "C", "warning_low": 50.0, "normal": [90.0, 110.0], "warning_high": 130.0, "ref": f"{OM912i} p.2-3"},
            "coolant_t": {"unit": "C", "warning_high": 120.0, "ref": f"{OM912i} p.2-4"},
            "egt": {"unit": "C", "warning_high": 950.0, "per_cylinder": True, "ref": f"{OM912i} p.2-4"},
            "fuel_p": {"unit": "bar", "warning_low": 2.8, "normal": [2.8, 3.2], "warning_high": 3.2,
                       "transient": {"range": [2.5, 3.5], "max_s": 3, "only_after_power_change": True}, "ref": f"{OM912i} p.2-4; {E121} p.23"},
            "rpm": {"unit": "rpm", "normal": [1400.0, 5500.0], "time_limited": {"max": 5800.0, "max_s": 300}, "ref": f"{OM912i} p.2-2"},
            "manifold_t": {"unit": "C", "warning_high": 60.0, "ref": f"{OM912i} p.2-4: max 60 C manifold temperature in flight"},
        },
        "notes": {"variant": "Modelled engine is the 912 iS Sport (D47); its max continuous rating equals the 912 iSc (72 kW)."},
    },
    "rotax_914": {
        "set": {
            "nominal_inj_timing_btdc": (None, None, None),
            "rail_pressure_bar": (None, None, None),
            "fuel_system": "CARBURETTOR", "ignition_circuits": 2, "ecu_lanes": 0,
            "glow_plugs": False, "thermostat": False, "propeller_governor": False,
        },
        "turbo": {
            "critical_altitude_ft": (16000.0, "MANUAL", f"{OM914} p.2-3: continuous performance up to 4875 m (16,000 ft)"),
            "critical_altitude_takeoff_ft": (8000.0, "MANUAL", f"{OM914} p.2-3: take-off performance up to 2450 m (8,000 ft)"),
            "map_takeoff_max_kpa": (135.0, "MANUAL", f"{OM914} p.2-2: take-off max 1350 hPa"),
            "map_continuous_max_kpa": (120.0, "MANUAL", f"{OM914} p.2-2: max continuous max 1200 hPa"),
            "boost_control": "WASTEGATE",
        },
        "limits_flat": {
            "egt_max_c": (950.0, "MANUAL", f"{OM914} p.2-3: EGT max 950 C (was 850, unsourced)"),
            "cht_max_c": (135.0, "MANUAL", f"{OM914} p.2-4"),
            "coolant_t_max_c": (120.0, "MANUAL", f"{OM914} p.2-4 (coolant exit temperature)"),
            "oil_t_max_c": (130.0, "MANUAL", f"{OM914} p.2-3"),
            "oil_p_min_bar": (0.8, "MANUAL", f"{OM914} p.2-3 (below 3500 rpm)"),
        },
        "limits": {
            "map_kpa": {"unit": "kPa", "time_limited": {"max": 135.0, "max_s": 300}, "warning_high": 135.0, "normal_max": 120.0,
                        "note": "overshoot allowed if it settles within 2 s", "ref": f"{OM914} p.2-2"},
            "egt": {"unit": "C", "warning_high": 950.0, "per_cylinder": True, "ref": f"{OM914} p.2-3"},
            "cht": {"unit": "C", "warning_high": 135.0, "per_cylinder": True, "ref": f"{OM914} p.2-4"},
            "coolant_t": {"unit": "C", "warning_high": 120.0, "ref": f"{OM914} p.2-4"},
            "oil_t": {"unit": "C", "warning_low": 50.0, "normal": [90.0, 110.0], "warning_high": 130.0, "ref": f"{OM914} p.2-3"},
            "fuel_p": {"unit": "bar above airbox", "normal": [0.15, 0.35], "nominal": 0.25, "ref": f"{OM914} p.2-4"},
        },
        "notes": {"fuel": "Carburetted (2 constant-depression carburettors): no injection timing, no rail; injector faults F05-F09 do not apply, F12 carburettor icing does.",
                  "boost_failure": "With boost failure about 66 kW (88 hp) remains (OM914 p.4-2)."},
    },
    "rotax_915is": {
        "set": {
            "rated_power_kw": (104.0, "PUBLIC", f"{E121}: 915 iSc take-off 104 kW at 5800 rpm (max 5 min); was 105.1 (141 hp marketing value)"),
            "max_continuous_power_kw": (99.0, "PUBLIC", f"{E121}: max continuous 99 kW at 5500 rpm up to the critical altitude"),
            "rated_rpm": (5800.0, "PUBLIC", f"{E121}"),
            "max_continuous_rpm": (5500.0, "PUBLIC", f"{E121}"),
            "rail_pressure_bar": (3.05, "PUBLIC", f"{E121} p.23: 915 iSc fuel pressure 2.9-3.2 bar (nominal = mid band); was 0.35 (wrong)"),
            "oil_capacity_l": (3.0, "PUBLIC", f"{E121} p.24"),
            "fuel_system": "PORT_INJECTION", "ignition_circuits": 2, "ecu_lanes": 2,
            "glow_plugs": False, "thermostat": False, "propeller_governor": False,
        },
        "turbo": {
            "critical_altitude_ft": (15000.0, "PUBLIC", f"{E121}: max continuous 99 kW up to the critical altitude of 15,000 ft / 4,572 m"),
            "boost_control": "WASTEGATE",
        },
        "limits_flat": {
            "coolant_t_max_c": (120.0, "PUBLIC", f"{E121} p.22"),
            "oil_t_max_c": (130.0, "PUBLIC", f"{E121} p.22"),
            "oil_p_min_bar": (0.8, "PUBLIC", f"{E121} p.24 (below 3500 rpm)"),
        },
        "limits": {
            "oil_p": {"unit": "bar", "warning_low": 0.8, "normal": [2.0, 5.0], "warning_high": 7.0,
                      "rpm_rule": {"above_rpm": 3500, "normal": [2.0, 5.0], "below_min": 0.8}, "ref": f"{E121} p.24"},
            "oil_t": {"unit": "C", "warning_high": 130.0, "ref": f"{E121} p.22"},
            "coolant_t": {"unit": "C", "warning_high": 120.0, "ref": f"{E121} p.22"},
            "fuel_p": {"unit": "bar", "normal": [2.9, 3.2], "ref": f"{E121} p.23"},
        },
        "notes": {"egt_cht": "E121 gives no EGT/CHT limit for the 915 iSc; the existing egt_max_c/cht_max_c values stay ASSUMED until the 915 OM is obtained (AI-03a).",
                  "not_916": "Do not mix up with the 916 iSc (117 kW, critical altitude up to 23,000 ft)."},
    },
    "austro_ae300": {
        "set": {
            "rated_power_kw": (123.5, "PUBLIC", f"{E200} p.5: take-off 123.5 kW at 3880 rpm (2300 prop rpm)"),
            "rated_rpm": (3880.0, "PUBLIC", f"{E200} p.5"),
            "max_continuous_power_kw": (123.5, "PUBLIC", f"{E200} p.5 lists one rating for the E4 (AE300): 123.5 kW at 3880 rpm. The 126 kW at 3720 rpm max-continuous rating belongs to the E4P (AE330). Was 114 kW at 3600 rpm (unsourced)."),
            "max_continuous_rpm": (3880.0, "PUBLIC", f"{E200} p.5/7 (E4 continuous speed equals the take-off rating)"),
            "dry_mass_kg": (185.0, "PUBLIC", f"{E200} p.5: dry weight 185 kg"),
            "overspeed_rpm": (4220.0, "PUBLIC", f"{E200} p.7: maximum engine over-speed 4220 rpm (2500 prop rpm)"),
            "max_operating_altitude_ft": (18000.0, "PUBLIC", f"{E200} p.7: maximum altitude E4 5490 m (18,000 ft)"),
            "fuel_system": "COMMON_RAIL", "ignition_circuits": 0, "ecu_lanes": 2,
            "glow_plugs": True, "thermostat": True, "propeller_governor": True,
        },
        "turbo": {
            "critical_altitude_ft": (18000.0, "ASSUMED", f"No critical altitude is published; {E200} gives only the max operating altitude 18,000 ft. Held equal to it until a source is found."),
            "max_shaft_rpm": (172000.0, "PUBLIC", f"{E200} note 10: containment demonstrated for max turbocharger speed 172,000 rpm (E4); was 200,000"),
            "boost_control": "VGT",
        },
        "limits_flat": {
            "oil_t_max_c": (140.0, "PUBLIC", f"{E200} p.6: max oil temperature 140 C (normal 50-135 C)"),
            "oil_p_min_bar": (0.9, "PUBLIC", f"{E200} p.7: min oil pressure at idle 0.9 bar; min 2.5 bar at max continuous"),
            "coolant_t_max_c": (105.0, "PUBLIC", f"{E200} p.6: max cooling fluid temperature 105 C"),
            "gearbox_t_max_c": (120.0, "PUBLIC", f"{E200} p.6: max gearbox temperature 120 C"),
            "oil_p_max_bar": (6.5, "PUBLIC", f"{E200} p.7"),
        },
        "limits": {
            "oil_t": {"unit": "C", "warning_low": 50.0, "normal": [50.0, 135.0], "warning_high": 140.0, "ref": f"{E200} p.6"},
            "oil_p": {"unit": "bar", "warning_low": 0.9, "warning_high": 6.5,
                      "rpm_rule": {"at_idle_min": 0.9, "at_max_continuous_min": 2.5}, "ref": f"{E200} p.7"},
            "coolant_t": {"unit": "C", "min_before_full_power": 60.0, "warning_high": 105.0, "ref": f"{E200} p.6"},
            "gearbox_t": {"unit": "C", "warning_high": 120.0, "ref": f"{E200} p.6"},
            "fuel_p": {"unit": "bar (HP pump inlet)", "normal": [4.0, 7.0], "warning_low": 4.0, "warning_high": 7.0, "ref": f"{E200} p.7"},
            "fuel_t": {"unit": "C", "warning_low": -30.0, "ref": f"{E200} p.6 (jet fuel)"},
            "rpm": {"unit": "rpm", "warning_high": 4220.0, "ref": f"{E200} p.7"},
        },
        "notes": {"egt_cht": "The certified limits are coolant, oil, gearbox, oil pressure and fuel pressure. The flat cht_max_c/egt_max_c values stay PLACEHOLDER for the legacy checker only and must not be shown as certified limits.",
                  "geometry": "3D model is AE330-shaped (representative)."},
    },
    "vrde_jayem_2_2l": {
        "set": {
            "dry_mass_kg": (195.0, "PUBLIC", f"{DRDO}: dry weight about 195 kg (brochures say <195 / 195 kg)"),
            "fuel_system": "COMMON_RAIL", "ignition_circuits": 0, "ecu_lanes": 2,
            "glow_plugs": True, "thermostat": True, "propeller_governor": True,
        },
        "turbo": {
            "critical_altitude_ft": (11000.0, "PUBLIC", f"{DRDO}: take-off power 180 hp held constant up to 11,000 ft (was 20,000, unsourced)"),
            "boost_control": "WASTEGATE",
        },
        "limits_flat": {},
        "limits": {},
        "notes": {"rpm": "Later DRDO brochure gives a 3900 rpm maximum; rated_rpm stays ASSUMED.",
                  "bsfc": "Brochures give best-economy BSFC <210 g/kWh (early) and 220 g/kWh (later).",
                  "fadec": "FADEC with dual redundancy (DRDO); ecu_lanes=2 follows that statement.",
                  "geometry": "3D model is TEI PD170 geometry (representative)."},
    },
}


def main():
    table = []
    for eid, ch in CHANGES.items():
        path = os.path.join(CFG, f"{eid}.json")
        d = json.load(open(path, encoding="utf-8"))
        prov = d.setdefault("provenance", {})
        for k, v in ch.get("set", {}).items():
            if isinstance(v, tuple):
                val, status, ref = v
                table.append((eid, k, d.get(k), val, status or "-"))
                d[k] = val
                if status:
                    prov[k] = {"status": status, "ref": ref}
                else:
                    prov.pop(k, None)
            else:
                table.append((eid, k, d.get(k), v, "flag"))
                d[k] = v
        if ch.get("turbo"):
            t = d.get("turbo") or {}
            for k, v in ch["turbo"].items():
                if isinstance(v, tuple):
                    val, status, ref = v
                    table.append((eid, f"turbo.{k}", t.get(k), val, status))
                    t[k] = val
                    prov[f"turbo.{k}"] = {"status": status, "ref": ref}
                else:
                    table.append((eid, f"turbo.{k}", t.get(k), v, "flag"))
                    t[k] = v
            d["turbo"] = t
        lim = d.setdefault("operating_limits", {})
        for k, (val, status, ref) in ch.get("limits_flat", {}).items():
            table.append((eid, f"operating_limits.{k}", lim.get(k), val, status))
            lim[k] = val
            prov[f"operating_limits.{k}"] = {"status": status, "ref": ref}
        d["limits"] = ch.get("limits", {})
        d["notes"] = ch.get("notes", {})
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(d, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
    print(f"{'engine':16} {'field':38} {'old':>10} -> {'new':<10} status")
    for e, k, old, new, st in table:
        if old != new:
            print(f"{e:16} {k:38} {str(old):>10} -> {str(new):<10} {st}")


if __name__ == "__main__":
    main()
