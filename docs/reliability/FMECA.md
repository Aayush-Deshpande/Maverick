# FMECA — MALE UAV piston propulsion

Derived per MIL-STD-1629A. RPN = severity x occurrence x detection
difficulty; higher is more urgent. A row marked GAP has no channel or
no detection method and is an open finding.

| ID | Item | Failure mode | Sev | RPN | Signature | Channels | Detection | Implemented by |
|---|---|---|---|---|---|---|---|---|
| FM-19 | Sensor | Drift / bias | II | 252 | Slow divergence from redundant channels or physics expectation | CHT_n, EGT_n, MAP | Redundancy voting plus model-based bias estimation | backend/physics/sensor_validator.py (partial — G05 open) |
| FM-20 | Reduction gearbox | Gear tooth wear / micro-pitting | I | 180 | Sidebands around gear mesh frequency; Fe rise in oil | VIB, OIL_Fe_PPM | Sideband energy around GMF (planned F05); wear metals | backend/physics/oil_system.py (order analysis F05 planned) |
| FM-02 | Injector | Nozzle coking / IDID | II | 168 | Asymmetric per-cylinder torque deficit; Retarded effective injection; EGT imbalance | CRANK_OMEGA, EGT_n, INJ_n_DELIVERY | Injector bank imbalance metrics (asymmetric) | backend/physics/injector_faults.py |
| FM-07 | Cylinder head | Thermal fatigue cracking | I | 140 | Accumulated LCF damage fraction; Compression loss; Blow-by rise | CHT_n, BLOWBY | Rainflow + Miner damage accumulation | backend/evaluation/damage_accumulation.py |
| FM-16 | Fuel system | Wax formation / filter plugging (CFPP) | I | 120 | Fuel temperature approaching cloud point; Filter dP rise; Supply pressure fall | FUEL_TEMP_C, FUEL_FILTER_DP_KPA, FUEL_PRESSURE | Cloud-point / CFPP margin monitor | backend/physics/fuel_thermal.py |
| FM-09 | Cylinder bore / rings | Abrasive wear from ingested silica | II | 112 | Rising Si in oil; Blow-by rise; Oil consumption rise; Compression loss | OIL_Si_PPM, BLOWBY, OIL_CONSUMPTION_L_H | Wear-metal spectrum with Si attribution | backend/physics/oil_system.py + induction.py |
| FM-01 | Cylinder / ignition | Misfire (SI) | II | 105 | Torque deficit at that cylinder's firing angle; Raised cycle-to-cycle variation; EGT drop on affected cylinder | CRANK_OMEGA, EGT_n, VIB | Per-cylinder omega(theta) torque deficit | planned F02 (crank-angle chain) |
| FM-06 | Cooling system | Cooling degradation | II | 105 | CHT above physics expectation at same power/altitude; Coolant temperature rise | CHT_n, COOLANT_TEMP, OAT_C | Thermodynamic residual on CHT | backend/physics/thermo_model.py |
| FM-14 | Turbocharger | Bearing wear / overspeed | II | 105 | Compressor efficiency fall; Raised charge temperature for given PR; Shaft order vibration | TURBO_PRESSURE_RATIO, CHARGE_TEMP_C, VIB | Efficiency residual; order analysis planned | backend/physics/turbo_model.py |
| FM-11 | Main / big-end bearings | Bearing wear and spalling | I | 100 | Cu/Pb/Sn rise in oil; Large debris particles; Envelope-spectrum bearing defect tones | OIL_Cu_PPM, OIL_Pb_PPM, OIL_LARGE_DEBRIS, VIB | Wear-metal trend and debris count; envelope analysis planned | backend/physics/oil_system.py (envelope F06 planned) |
| FM-05 | Combustion | Combustion instability | III | 96 | Rising COV of per-cylinder work; Vibration at sub-harmonic orders | CRANK_OMEGA, VIB | COV of IMEP proxy | planned F03 |
| FM-12 | Lubricant | Oil degradation | III | 96 | Viscosity ratio fall; Oxidation index rise | OIL_VISCOSITY_RATIO, OIL_OXIDATION_INDEX, OIL_TEMP | Oil condition model | backend/physics/oil_system.py |
| FM-03 | Injector | Needle stick | I | 90 | Single-cylinder delivery collapse; Large asymmetric torque deficit | CRANK_OMEGA, EGT_n | Injector bank imbalance metrics | backend/physics/injector_faults.py |
| FM-08 | Air filter | Restriction from dust loading | III | 84 | MAP deficit at constant throttle and altitude; Filter dP rise | MAP, AIR_FILTER_DP_KPA, TPS, ALTITUDE_FT | MAP versus physics expectation | backend/physics/induction.py |
| FM-13 | Turbocharger | Wastegate stuck | II | 84 | MAP not tracking command; Wastegate position frozen | MAP, WASTEGATE_POS, TPS | MAP tracking residual | backend/physics/turbo_model.py |
| FM-15 | Turbocharger | Compressor surge | II | 84 | Surge margin collapse; MAP oscillation | TURBO_SURGE_MARGIN, MAP | Surge margin monitor | backend/physics/turbo_model.py |
| FM-17 | Alternator | Output degradation | I | 80 | Bus voltage fall under known load; Battery discharging in flight | BUS_VOLTAGE, BATTERY_CURRENT | Electrical power balance residual | planned F16 |
| FM-10 | Oil pump / gallery | Oil pressure loss | I | 60 | Oil pressure below expectation at RPM | OIL_PRESS, ENGINE_RPM | Threshold plus physics residual | backend/physics/thermo_model.py |
| FM-04 | High-pressure pump / rail | Rail pressure decay | II | 56 | Symmetric torque deficit across all cylinders; Rail pressure below command | RAIL_PRESSURE_BAR, CRANK_OMEGA | Symmetric deficit with low rail pressure | backend/physics/injector_faults.py |
| FM-18 | FADEC | Lane disagreement / lane failure | I | 40 | Lane A vs Lane B parameter divergence | FADEC_ACTIVE_LANE, MAP_LANE_A, MAP_LANE_B | Cross-lane disagreement monitor | planned F55 |

**20 modes** · 0 detectability gaps · 100% modelled or detected in code.