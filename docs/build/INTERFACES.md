# Interface Contracts

*New here? Read [`MENTAL_MODEL.md`](MENTAL_MODEL.md) first. Implementation status of each schema: `Frame`/`TruthRecord` (§1–2) → `backend/core/frame.py`, see [`BACKLOG.md`](BACKLOG.md) B1.1.*

The data shapes every component must agree on. Field names, units and semantics here are **normative**. Where a structure already exists in code, the mapping is given. Version every schema (`schema_version`), and when a field is added, **append; never reorder or reuse**.

---

## 1. `Frame`: canonical low-rate telemetry

Replaces `EnginePhysicalState` (in [`thermo_model.py`](../../backend/physics/thermo_model.py)) as the pipeline's input. It is produced by every source adapter (plant, replay, MAVLink, CAN).

| Field | Type | Unit | Notes | Current `EnginePhysicalState` name |
|---|---|---|---|---|
| `schema_version` | str | — | `"frame/1"` | — |
| `t` | float64 | s | Monotonic, source clock | `TIMESTAMP_SEC` |
| `source` | enum | — | `PLANT` · `REPLAY` · `MAVLINK` · `CAN` · `SITL` | — |
| `tail_id`, `engine_serial`, `engine_config_id` | str | — | `engine_config_id` must name a file in `configs/engines/` | — |
| `rpm` | float | rpm | Crankshaft | `ENGINE_RPM` |
| `prop_rpm` | float | rpm | | `PROP_RPM` |
| `throttle` | float | % | | `TPS` |
| `map` | float | kPa abs | | `MAP` |
| `boost_target` | float | kPa abs | FADEC set-point | — |
| `cht[i]`, `egt[i]` | float[n_cyl] | °C | Index 0 = cylinder 1 | `CHT_1..4`, `EGT_1..4` |
| `coolant_t` | float | °C | Liquid-cooled engines | — |
| `oil_p` / `oil_t` | float | bar / °C | | `OIL_PRESS` / `OIL_TEMP` |
| `fuel_flow` | float | kg/h | **Mass flow**; convert at the adapter | `FUEL_FLOW` (L/h in the old code; fix at the adapter) |
| `fuel_t` | float | °C | | — |
| `rail_p` | float | bar | CRDi rail (SI: fuel pressure) | `FUEL_RAIL_P` |
| `soi_cmd[i]` | float[n_cyl] | ° BTDC | Commanded start of injection | `INJ_TIMING_BTDC` (scalar in old code) |
| `qty_cmd[i]` | float[n_cyl] | mm³/stroke | Commanded quantity | — (old: `INJ_PULSE_WIDTH_MS`) |
| `ign_cmd` | float | ° BTDC | SI only; `null` for CI | `IGN_TIMING_BTDC` |
| `fadec_trim[i]` | float[n_cyl] | % | **Cylinder-balancing correction** (via XCP) | — |
| `fadec_adapt[i]` | float[n_cyl] | % | **Drift-adaptation value** (via XCP) | — |
| `fadec_lane` | enum | — | `A` · `B` | `FADEC_ACTIVE_LANE` |
| `bus_v` / `bus_i` / `batt_i` | float | V / A / A | | `BUS_VOLTAGE` / — / `BATTERY_CURRENT` |
| `alt` | float | ft | Pressure altitude | `ALTITUDE_FT` |
| `oat` | float | °C | | `OAT_C` |
| `tas` | float | kt | | `TAS_KNOTS` |
| `phase` | enum | — | `GROUND` · `TAKEOFF` · `CLIMB` · `CRUISE` · `LOITER` · `DESCENT` · `LANDING` | `FLIGHT_PHASE` |
| `quality[channel]` | bitmask | — | Bits: stale, frozen, out-of-range, lane-disagree, shielded, interpolated | — |

**Forbidden in `Frame`:** `FAULT_ID`, `HEALTH_INDEX`, `RUL_HOURS`, and anything derived from ground truth or from the twin itself. Those are *outputs* (§6–§7) or *truth* (§2). A test must import every detector and assert that it never reads a forbidden name (backlog B0.1).

## 2. `TruthRecord`: evaluation-only stream

Written by the plant and read **only** by `backend/evaluation/` and `experiments/`.

| Field | Type | Notes |
|---|---|---|
| `t` | float64 s | Aligns with `Frame.t` |
| `active_faults` | list of `{mode_id, location, severity 0..1, onset_t, rate}` | `mode_id` from `docs/reliability/fmeca.json`; `location` e.g. `cyl2`, `injector2`, `bearing_main_3`, `alternator` |
| `plant_params` | dict | Hidden build-variation and degradation parameters (the estimator's targets) |
| `failed` | bool + `failure_mode` | The plant destroyed itself (for lead-time measurement) |

## 3. `CycleBlock`: high-rate input for one engine cycle

| Field | Type | Unit |
|---|---|---|
| `cycle_id`, `t_start`, `t_end` | int, float64, float64 | s |
| `tooth_ts` | float64[] | s, crank-edge timestamps (≤ 25 ns resolution) |
| `cam_ts` | float64[] | s |
| `prop_ts` | float64[] | s, prop-shaft edges (optional) |
| `accel[ch]` | float32[n] per channel, with `fs` and `angle_tag[n]` | m/s², Hz, crank-angle ° |
| `rail_p_hr` | float32[n] with `fs` | bar |
| `bus_v_hr` | float32[n] with `fs` | V (alternator ripple, 10 §2.1) |

In software mode it is produced by the plant's high-rate path (`VirtualEngine.crank_signal()` extended) at the rates in [`DECISIONS.md`](DECISIONS.md) D08.

## 4. `CycleHealthVector` (v1): per-cycle DSP output

Emitted about 33 times per second at 4,000 rpm. Full definition and derivation are in [`audit/09`](../audit/09_full_depth_architecture.md) §4.7.

```
meta:      cycle_id, t_start, rpm_mean, load, phase, regime_bin(rpm_bin, load_bin, phase), quality
per_cyl[i]:
  imep [bar], work_peer_ratio [-], comp_index [-], soc [°ATDC], ca10/ca50/ca90 [°ATDC],
  pmax [bar], pmax_angle [°ATDC], dpdtheta_max [bar/°], ign_delay [°CA], resonance_idx [-],
  inj_window_energy [(m/s²)²], needle_close_energy, valve_ivc_energy, valve_ivc_angle, valve_evo_energy,
  valve_evo_angle, rail_drop [bar], rail_recovery [ms], fadec_trim [%], fadec_trim_rate [%/h],
  egt [°C], egt_peer_ratio [-]
engine:
  order_spectrum[80] (0.5-order resolution to order 40, amplitude), ofsc_indices[k],
  env_order_indices{bpfo,bpfi,bsf,ftf}, gear_ci{fm0,fm4,na4,nb4,sb_index}, twist_amp[orders],
  brake_torque [N·m], bsfc [g/kWh], fmep [bar],
  turbo{speed, sync, subsync, surge_idx}, map, boost_err,
  alt_ripple_orders[k], batt_r_int [mΩ] (on start)
embedding: z[256]
```

**Peer-referenced features:** `x_peer_ratio = x_i / median(x_j, j≠i)` within the same cycle.

## 5. `HealthFrame`: edge → ground downlink

**Exists** as `EdgeFeatureFrame` in [`backend/edge/compressor.py`](../../backend/edge/compressor.py). The fixed little-endian layout is **29 bytes for 4 cylinders**:

```
<f 6e      t_sec(f32), order_05, order_1, order_2, order_4, crest_factor, kurtosis (f16)
<B Ne      n_cyl(u8), per_cylinder_ratio[n_cyl] (f16)
<B e B     misfire_cylinder(u8, 0=none), misfire_rate(f16), verdict_code(u8)
```

**v2** keeps v1 byte-compatible and appends:

- `fadec_trim[n_cyl]` (f16)
- `soc_dev[n_cyl]` (f16)
- `top_hypothesis(u8)` + `p(u8, /255)`
- `novelty(u8)`
- `flags(u16)`

It is carried as a custom MAVLink 2 message (§11), signed.

## 6. Estimator outputs

```
ParameterEstimate:  name, location, mean, std, unit, t_updated, estimator(UKF|PF|EKF|LS), validity(NIS_ok, white_ok)
ValidityReport:     exists in backend/twin/validity.py (NOMINAL | MODEL_DRIFT | ENGINE_FAULT | OUT_OF_ENVELOPE)
```

Parameter names (initial set): `k_inj[i]`, `dsoi[i]`, `c_comp[i]`, `eta_cool[i]`, `eta_radiator`, `eta_oil_pump`, `eta_turbo_c`, `turbo_tau`, `rail_leak`, `bias_<channel>`, `batt_r_int`, `batt_soh`, `fmep`.

## 7. Diagnosis, prognosis and advisory outputs

```
Evidence:        detector(PARAM_CHANGE|PEER|NOVELTY|RECOGNISER|INTEGRITY|ORACLE_TEST), target, statistic, p_value|score,
                 threshold, t, explanation_ref
Hypothesis:      mode_id (FMECA), location, probability, ambiguity_group_id, supporting_evidence[], counter_evidence[]
TestRequest:     test_id (CUT_OUT|RAIL_STEP|SOI_SWEEP|WASTEGATE_STEP|THROTTLE_PERTURB|CRANK_COMPRESSION),
                 target, expected_info_gain_bits, allowed_phase, requires_approval=True
RULEstimate:     component, location, path(PHYSICS|DATA), median, lower, upper, coverage_nominal, units(FH|SORTIES), limit_def
Alarm (ISA-18.2): alarm_id, priority(1-4), cause, consequence, operator_action, time_to_respond_s, shelved, state
WorkPackage:     wp_id, tail_id, tasks[{task_id, ata_like_chapter, action}], expected_finding, confidence,
                 confirm_test, parts[], est_hours, evidence_refs[], approval_state
MissionReliability: profile_id, R_median, R_lower, R_upper, limiting_component, phase_distribution, recommendation
```

## 8. Engine config schema (`configs/engines/*.json`)

The existing keys are kept: `engine_id`, `display_name`, `manufacturer`, `platforms`, `ignition_mode`, `induction`, `fuel`, `cooling`, `layout{count, arrangement, firing_order, bore_mm, stroke_mm, displacement_cc, compression_ratio}`, `turbo{...}`, `rated_power_kw`, `rated_rpm`, `max_continuous_*`, `idle_rpm`, `gearbox_ratio`, `dry_mass_kg`, `tbo_hours`, `nominal_*`, `rail_pressure_bar`, `fuel_cloud_point_c`, `fuel_cfpp_c`, `source`.

**Add a per-field `provenance` map** (backlog B0.4), because a single `source` string cannot express mixed provenance:

```json
"provenance": {
  "rated_power_kw": {"status": "PUBLIC",  "ref": "Indian Defence News 2025-08 (180 hp at 11,000 ft)"},
  "layout.bore_mm": {"status": "ASSUMED", "ref": "typical 2.2 L inline-4 CRDi; replace with VRDE data"},
  "turbo.critical_altitude_ft": {"status": "PLACEHOLDER", "ref": "none"}
}
```

Status values: `PUBLIC` (cite a source), `MANUAL` (from `docs/reference/`), `ASSUMED` (engineering judgement), `PLACEHOLDER` (unknown). Report generators must print these statuses next to any number derived from them.

## 9. Dataset records (`backend/datasets/records.py`)

```
SignalRecord:   dataset, record_id, group_keys{unit|bearing|flight|machine|condition}, fs_hz,
                channels{name: float32[n]}, units{}, rpm (float|array|None), tach (array|None),
                label{...}, meta{}, provenance[{path, sha256}]
FeatureTable:   dataset, X (DataFrame), y (DataFrame), groups (Series), feature_units{}, provenance[]
RunToFailure:   dataset, unit_id, t or cycles (array), sensors (DataFrame), settings (DataFrame), rul (array|None),
                group_keys{}, provenance[]
CanLog:         dataset, t (float64[]), arb_id (u32[]), dlc (u8[]), data (bytes[]), label (int8[]),
                attack_type, provenance[]
```

The label is always a separate field from the inputs. Provenance hashes come from `Datasets/MANIFEST.json`.

## 10. Federated update envelope

```
FedUpdate: round_id, silo_id(base|lab|depot), object(PRIORS|FLY_FILTERS|MODEL|CONFORMAL|BN_COUNTS),
           payload(bytes, compressed), n_samples, classification_level, dp_epsilon|None,
           base_model_version, created_t, signature(ML-DSA or Ed25519)
Gate:      canary_suite_version, canary_pass(bool), coverage_check(bool), nonregression(bool) → PROMOTE|SHADOW|REJECT
```

## 11. External interfaces

| Interface | Standard | Content | Status |
|---|---|---|---|
| FADEC broadcast | CAN, SAE J1939-style PGNs, **our DBC** (`configs/can/anumaan_fadec.dbc`, to be created) | `Frame` channels | J1939 packing exists in [`socketcan_bridge.py`](../../backend/telemetry/socketcan_bridge.py); no DBC yet |
| FADEC diagnostics | **UDS, ISO 14229** | DTC read (0x19), routine control (0x31) for the tests in §7 `TestRequest` | To build (emulator + client) |
| FADEC measurement | **XCP, ASAM MCD-1** (on CAN) | Variables: `fadec_trim[i]`, `fadec_adapt[i]`, controller duties, rail-PCV duty | To build |
| Autopilot | MAVLink 2 `EFI_STATUS` (#225) | Standard engine fields | Decoder exists: [`mavlink_efi.py`](../../backend/telemetry/mavlink_efi.py) |
| Health downlink | MAVLink 2 custom `ANUMAAN_HEALTH` (dialect XML in `configs/mavlink/`, ID from the private range) | §5 v2 payload, signed | To build |
| GCS API | REST + WebSocket, as in [`docs/04_system_guide.md`](../04_system_guide.md) §5 | — | Exists |

## 12. Experiment result JSON (`docs/evaluation/*.json`)

```
{ "experiment_id": "E06", "schema_version": "result/1", "git_commit": "...", "run_utc": "...",
  "datasets": [{"name": "3500-DEFault", "files": [{"path": "...", "sha256": "..."}]}],
  "evidence_class": "SIMULATION|PUBLIC_PROXY|REAL_FLIGHT",
  "split": {"method": "group", "keys": ["noise_db"], "seed": 0},
  "contenders": [...], "metrics": {...}, "ci": {"method": "bootstrap", "level": 0.95},
  "ps_refs": ["FDP-03", "INN-06"], "notes": "..." }   // IDs from docs/fun_req.md
```

Report markdown is generated from these JSON files and is never hand-edited.
