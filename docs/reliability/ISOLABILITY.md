# Fault isolability — as-built vs proposed instrumentation

Derived from the FMECA in [FMECA.md](FMECA.md). A mode with no observable
signature is undetectable; modes sharing an identical signature set cannot be
separated by any algorithm, and the honest output for either is the group.

## As-built (current 20 Hz telemetry)

- 15/20 detectable (75%), 11/20 uniquely isolable (55%), 2 ambiguity group(s), 9 channels.
- Undetectable: FM-04, FM-09, FM-11, FM-12, FM-16

- Ambiguous: FM-01 == FM-03
- Ambiguous: FM-13 == FM-15

## Proposed (adds crank-angle, oil debris, fuel thermal, turbo channels)

- 19/20 detectable (95%), 19/20 uniquely isolable (95%), 0 ambiguity group(s), 21 channels.
- Undetectable: FM-12

## What the added channels buy

Detectability 75% -> 95%; isolability 55% -> 95%.

The two ambiguity groups that the as-built set cannot resolve are the argument
for the crank-angle channel, stated as a proof rather than a preference:
misfire and injector needle stick are the *same observation* on the current
sensors, as are a stuck wastegate and compressor surge.

## Full matrix

# Fault isolability analysis

19/20 detectable (95%), 19/20 uniquely isolable (95%), 0 ambiguity group(s), 21 channels.

## Signature matrix

| Mode | Observable signatures | Isolable |
|---|---|---|
| FM-01 | CYCLE_VARIABILITY, TORQUE_DEFICIT_ASYMMETRIC | unique |
| FM-02 | INJECTION_RETARD, TORQUE_DEFICIT_ASYMMETRIC | unique |
| FM-03 | TORQUE_DEFICIT_ASYMMETRIC | unique |
| FM-04 | RAIL_PRESSURE_LOW, TORQUE_DEFICIT_SYMMETRIC | unique |
| FM-05 | CYCLE_VARIABILITY, SIG_VIBRATION_AT_SUB-HARMONIC_ORDERS | unique |
| FM-06 | CHT_ABOVE_EXPECTATION, COOLANT_TEMP_RISE | unique |
| FM-07 | BLOWBY_RISE, COMPRESSION_LOSS, DAMAGE_FRACTION | unique |
| FM-08 | FILTER_DP_RISE, MAP_DEFICIT | unique |
| FM-09 | BLOWBY_RISE, COMPRESSION_LOSS, OIL_SI_RISE | unique |
| FM-10 | OIL_PRESSURE_LOW | unique |
| FM-11 | BEARING_DEFECT_TONES, OIL_BEARING_METALS | unique |
| FM-12 | — | UNDETECTABLE |
| FM-13 | MAP_TRACKING_ERROR, WASTEGATE_FROZEN | unique |
| FM-14 | SHAFT_ORDER_VIBRATION, TURBO_EFFICIENCY_LOSS | unique |
| FM-15 | MAP_TRACKING_ERROR, SURGE_MARGIN_LOSS | unique |
| FM-16 | FILTER_DP_RISE, FUEL_TEMP_NEAR_CLOUD | unique |
| FM-17 | BATTERY_DISCHARGING, BUS_VOLTAGE_LOW | unique |
| FM-18 | LANE_DIVERGENCE | unique |
| FM-19 | SLOW_DIVERGENCE_FROM_MODEL | unique |
| FM-20 | GEAR_MESH_SIDEBANDS, OIL_FE_RISE | unique |

## Undetectable modes

- FM-12