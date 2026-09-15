# Canyon Tactical Flight Simulator — Logical & Technical Specification (v1)
**Scope:** `apps/blender_twin/standalone_canyon_flight_app.py`, launched via `launch_canyon_simulation.bat`
**Reference:** DRDO / iDEX Problem Statement 26054 — *AI-Enabled Real-Time Digital Twin for Health Monitoring, Fault Prediction and Mission Reliability Enhancement of Aero Piston Engines used in MALE UAVs*

This document describes how every subsystem of the canyon flight simulator **should** behave — logically (what decision each piece is making and why), technically (the formulas/state machines that implement it), and as an end-to-end expected experience. It reflects the design after the bug-fix pass performed on 2026-09-09 (undefined-variable crash, dead thermal banner, CHT step-function, RECLIMB deadlock, stale AGL telemetry — see git history / conversation log for the diffs), and is meant to be the reference for what "correct" looks like going forward.

---

## 1. Mission Framing

The aircraft is a scaled-up MQ-1 Predator-class MALE UAV (29.68 m wingspan, 2.02× the base mesh) flying a reconnaissance transit up the Nubra Valley (Ladakh) at 15,000 ft AMSL (4,572 m). The single Rotax-912-class piston engine is the mission's single point of failure — if Cylinder #2 CHT runs away in the cold, thin high-altitude air, the only remedy available to the aircraft (autonomously, or on operator command) is to **dive into the canyon**, where denser, cooler air below gives the engine convective relief, then climb back to cruise once the engine has recovered. Everything in the simulator exists in service of dramatizing that one physical idea — engine thermal health is *coupled* to a real 3D flight maneuver — while a military-grade terrain-avoidance system (Auto-GCAS) makes sure that maneuver doesn't kill the aircraft.

Two orthogonal state layers run every physics tick:
- **Safety layer** — Auto-GCAS: "are we about to hit the ground, and do I need to override the stick?"
- **Behavior layer** — either raw pilot input, or (during a triggered fault) the autonomous tactical-dive state machine.

The safety layer always outranks the behavior layer when `copilot_on == True`.

---

## 2. Terrain Sensing — `TacticalTerrainRadar`

**Purpose:** answer "what is the ground/rock distance along this ray?" for every subsystem that needs it (AGL, forward obstacle, wingtip clearance, camera clamping, autonomous corridor scans) — without ever touching Blender's `ray_cast` per-frame if it can be avoided.

**Two backends, selected by `RADAR_BACKEND`:**

| Backend | Data source | Cost | When used |
|---|---|---|---|
| `"heightfield"` (default) | `data/nubra_raw_crop.npz` — a raw DEM grid, bilinearly interpolated | ~2 µs per straight-down sample; a 25 m-stepped raymarch for angled rays | Always, if the npz exists |
| `"blender"` | The `Copernicus_DSM_COG_*` mesh object, BVH `ray_cast` | Much slower, one BVH query per ray | Fallback only, if the heightfield file is missing |

**Two query shapes inside the heightfield path:**
1. **Straight-down fast path** (`|dx|,|dy| < 0.01` and `dz < -0.99`): a single bilinear lookup of the grid at `(x, y)`, no marching. This is what the AGL probe uses, and it is *effectively free* — there is no technical reason to throttle it (see §7, correction applied).
2. **Arbitrary-direction raymarch**: steps the ray in 25 m increments out to `max_dist`, finds the first sample where the ray altitude drops below the terrain sample, then linearly refines the hit distance between the last two samples. This is what forward/lateral obstacle probes use, and it is genuinely non-trivial per-call cost — this is the one that legitimately benefits from staggering across frames.

**Surface normal** at any hit point is estimated from the local elevation gradient (central difference in `x` and `y`, `dz/dx`, `dz/dy` combined into `(-dz/dx, -dz/dy, 1)` normalized) — used for potential-field repulsion vectors and (not currently, but available for) shading/physics response.

**Expected behavior:** any caller — GCAS, wing-clearance checks, camera terrain clamp, the open-ground corridor scanner — gets a distance/hit-point/normal tuple that is accurate to within one grid cell (`dx`, `dy` computed from the npz bounds — typically a few meters), regardless of which backend is active. Callers must never assume a specific backend; `radar.raycast(origin, direction, max_dist)` is the only contract.

---

## 3. Flight Kinematics — orientation, wing envelope, integration

Every tick, the flight direction is derived purely from `heading_rad` and `pitch_rad` (never accumulated velocity/momentum vectors that could drift):

```
fwd_horiz = (sin(heading), cos(heading), 0)         # heading 0° = North (+Y), 90° = East (+X)
fwd_3d    = (fwd_horiz.x·cos(pitch), fwd_horiz.y·cos(pitch), sin(pitch))
```

This is a "velocity-vector-follows-attitude" model, not a full 6-DoF rigid body — appropriate for an arcade-realistic tactical sim, not a flight-dynamics research tool. Roll (`roll_rad`) only rotates the *visual* wing frame (for wingtip collision geometry and camera roll) and biases yaw rate during a turn; it does not itself produce a sideways force component. This is an intentional simplification, not a bug — do not "fix" it into a full aerodynamic side-force model without a specific reason, as it would destabilize all of the hand-tuned dive/GCAS timings.

**Tri-point wing envelope**: fuselage center ± `right_rolled · WING_SEMI_SPAN` (14.84 m) gives left/right wingtip world positions every tick, using the *rolled* right vector so a banked turn correctly dips the inside wingtip toward the terrain. This is the basis for wingtip-strike detection (§6).

**Position integration**: `pos += fwd_vel * speed_ms * dt`, i.e. explicit Euler integration at whatever `dt` the modal timer delivers (clamped to [1 ms, 100 ms] so a momentary frame hitch never produces a multi-hundred-meter position jump or a `dt=0` divide).

**Expected behavior:** at any instant, `heading_deg`, `pitch_rad`, `roll_rad`, and `speed_ms` alone are sufficient to reconstruct the aircraft's exact position delta for the tick — there is no hidden momentum state to desync from telemetry.

---

## 4. Propulsion & Aerodynamics — first-principles per-tick

This is a genuine (if simplified) point-mass performance model, not a lookup table:

1. **ISA atmosphere** at current AMSL altitude: temperature lapses at 6.5 K/km, density follows the standard barometric formula, clamped to a 0.30 kg/m³ floor (representing an operational ceiling beyond which the model shouldn't be trusted).
2. **Engine RPM** target is a linear map of throttle (2,200 RPM idle → 5,800 RPM max), approached with first-order lag (`rate = 3.5·dt`) so RPM never jumps instantaneously — this is what makes throttle presets ([7]/[8]/[9]) feel like real spool-up rather than a snap.
3. **Available thrust**: shaft power scales with throttle and lapses with air density (`ρ/ρ₀`)^0.85 (accounts for reduced volumetric efficiency at altitude); thrust = `η_prop · P / v` (classic propeller thrust-from-power relation), floored at `v = 16 m/s` to avoid a division blow-up at very low/zero airspeed.
4. **Required lift coefficient** is solved *backward* from the load factor implied by the current bank angle (`L = W / cos(roll)`), then drag is the sum of parasite (`CD0`) and induced drag (`CL²/(π·e·AR)`) — this is why a hard bank costs airspeed: more lift required → more induced drag → net deceleration, exactly as a real aircraft behaves.
5. **Net longitudinal force** = thrust − drag − (weight component along the flight path from pitch, i.e. gravity assists a dive and opposes a climb) → acceleration → speed integrated forward, clamped to `[STALL_SPEED_MS, VNE_SPEED_MS]`.

**Expected behavior:** a sustained climb at high throttle should still bleed airspeed toward stall if held too long; a dive should accelerate toward VNE; a hard sustained bank should visibly cost speed. If any of these three qualitative behaviors are absent during manual play-testing, the aerodynamic block has regressed.

---

## 5. Thermodynamic Engine Twin — CHT / oil pressure

This is the direct embodiment of DRDO PS-26054's "engine health is coupled to the mission profile" requirement, and the single most narratively important subsystem in the sim.

**Heat balance each tick:**
```
q_in  = 22.0 · (rpm / 5200)^2.2  +  extra_heat        # combustion heat, grows superlinearly with RPM
q_cool = cool_coeff · (ρ/ρ₀) · v_factor · (CHT - T_amb)  # convective rejection
CHT  += ((q_in - q_cool) / 8.0) · dt, clamped to [88°C, 142°C]
```

**`canyon_blend`** — the *corrected* mechanism (was a hard 250 m-AGL step function; now continuous) — is the fraction of the *actual planned descent* the aircraft has completed:
```
canyon_blend = 1 − clamp((AGL − 150) / (DESIRED_CRUISE_AGL_M − 150), 0, 1)
```
i.e. `0` at cruise AGL (thin, poor cooling), ramping linearly to `1` right at the canyon-floor transition altitude (150 m AGL, the same threshold that flips `DESCENT → LEVEL_SPRINT`). Both `extra_heat` (22°C→4°C as the FADEC's mixture-quench engages) and `cool_coeff` (0.22→0.75, thin air → dense canyon air) are driven by this single blend, so there is exactly one physically-motivated curve driving the whole thermal arc of a dive, tied to the real geometry of the mission rather than an arbitrary absolute altitude.

**Why this matters (what "correct" looks like in a play session):** starting a dive from 15,000 ft cruise with Fault 01 (overheat) active, CHT should *continue climbing* for the first portion of the descent (thin air still dominates), peak somewhere in the middle third of the dive, then visibly and smoothly fall as the canyon narrows the gap to the 150 m floor — arriving at the canyon floor already well into recovery, not pinned at the 142°C ceiling. A verified headless trace of this exact scenario shows CHT peaking near 117–130°C mid-descent and returning to the 88°C floor by the time `LEVEL_SPRINT` begins — this is the expected shape of the curve; if a future change makes CHT sit flat at 142°C for more than a few seconds of a dive, that is a regression of the same class as the original bug.

**Oil pressure** is a simple derived quantity (`4.20 − 0.015·(CHT−104)`, clamped 3.5–5.0 bar) unless Fault 04 (scavenge pump loss) is active, in which case it decays linearly (`−0.35 bar/s`) toward a 1.4 bar floor, independent of CHT — this is intentionally a separate, uncoupled fault channel (it should never auto-recover; only the `[2]` toggle or `[0]` clear-all resets it).

**Fault injector jitter** (`fault_injector`): superimposes a `sin(22·t)·180 RPM` oscillation on top of the RPM target and fixes fuel flow to a lean 11.2 L/h — this is cosmetic/telemetry-only (does not currently perturb thrust/CHT) and is expected to just visibly "jitter" the RPM gauge and log an injector-clog message; it is not meant to be a flight-affecting fault the way overheat/oil-loss are.

---

## 6. Auto-GCAS Safety Gate

Three zones, driven by **Time-To-Impact** (`TTI = min(fwd_dist, forward-down dist) / closure_speed`) and **AGL**:

| Zone | Condition | Behavior |
|---|---|---|
| **Green** | `TTI > 6.0s` and `AGL > MIN_SAFE_AGL_M + 80` | Full operator/APF authority, zero intervention |
| **Amber (Warning)** | `TTI ≤ 6.0s` or `AGL ≤ MIN_SAFE_AGL_M + 80` | HUD flashes amber "TERRAIN PROXIMITY", pilot still has full authority |
| **Red (Critical / recovering)** | `TTI ≤ 3.0s` or `AGL ≤ MIN_SAFE_AGL_M (80m)` | GCAS seizes pitch (ramps to `MAX_PITCH_UP_RAD` at `RECOVERY_PULL_RADS`/s), levels wings, spools to 5,500 RPM, and steers laterally toward whichever side (`left_dist_m` vs `right_dist_m`) has more clearance. Stays latched (`gcas_clearing`) until AGL clears `MIN_SAFE_AGL_M+50` **and** TTI clears the amber threshold — a hysteresis band so it doesn't chatter in and out of recovery right at the boundary. |

This gate is **bypassed** whenever `tactical_dive_active` is true — the tactical-dive state machine (§7) has its own, purpose-built terrain logic for exactly this reason (a generic "pull up hard" reflex would fight the deliberate dive/climb maneuver). It is also bypassed when `copilot_on == False` — in that mode the same critical-proximity condition instead falls through to the collision/crash check (§8): the entire behavioral difference between "Copilot ON" and "Copilot OFF" is which of these two paths a critical-AGL/TTI event routes into.

**Known, accepted edge case:** if the operator holds pitch-down continuously with copilot ON, GCAS will pull up, immediately hand control back once clear, and the held input will immediately re-engage the dive — producing a stable oscillation between "WARNING" and "PULL-UP" a few tens of meters above the canyon floor, indefinitely, without ever crashing or ever reaching a stable cruise altitude. This was checked in a 5+ minute headless trace: it never terminates by crashing (good) and never fully "wins" against a sustained suicidal input either. This is the **correct** behavior for a system whose mandate is "prevent CFIT," not "override the pilot's will" — do not attempt to make GCAS force a climb-away against continuous manual pitch-down input; that would be a bigger behavioral change than a bug fix and should be a deliberate design decision if ever made.

---

## 7. Radar Probe Scheduling (performance vs. safety trade-off)

Not every ray needs to fire every tick. The design intent is:
- **Downward AGL probe**: fires **every tick**, unconditionally. On the heightfield backend this is an O(1) bilinear lookup — there is no performance reason to throttle it, and it is the single input every safety decision (GCAS zone, wing-clearance override, HUD AGL tape) depends on. (This was previously staggered to 1-in-12 ticks, which could let displayed/decision AGL lag the true value by up to ~80 ms during a fast dive — corrected.)
- **Forward-center, forward-down, and left/right lateral probes**: staggered across a 12-tick cycle (one of `{3, 6, 9}` mod 12), because these use the more expensive angled raymarch. Between probe ticks their values are simply held (not analytically re-derived, unlike AGL) — this is acceptable because obstacle distance changes far more slowly relative to frame time than AGL does during a steep dive over broken terrain.

**Expected behavior:** AGL-driven decisions (HUD tape, GCAS AGL zone, wing-clearance recovery) should track the true terrain within one physics tick at all times; forward/lateral obstacle-driven decisions (TTI, wall-avoidance nudges) are allowed roughly 12-tick (≈80 ms at 143 FPS) staleness. If AGL-driven behavior (e.g. GCAS firing late, or the wing-clearance override letting a wingtip get unrealistically close before reacting) is ever observed to lag visibly behind what the terrain under the aircraft actually looks like, check first whether this probe got re-throttled.

---

## 8. Collision & Wing-Envelope Protection

Runs on a separate 3-tick stagger (fuselage / left wingtip / right wingtip, one per tick) — a forward sweep (`sweep_dist` = this frame's travel distance + 8 m margin) plus a downward ground-clearance probe from each of the three points.

**Three distinct outcomes depending on mode**, all keyed off the same collision flags (`is_rock_collision`, `is_ground_collision`, `is_lw/rw_cliff_collision`, `is_lw/rw_ground_strike`):

1. **`copilot_on == False`** → any collision flag triggers `_trigger_crash_event`: freezes the aircraft at the impact point, snapshots full crash telemetry (airspeed, altitude, position, attitude, engine state), sets `is_crashed = True` (which halts `update_simulation` entirely on all subsequent ticks until `[R]` resets), and renders the high-visibility Crash Card HUD. **Verified**: a sustained manual nose-down dive with copilot off produces a clean CFIT crash with correct telemetry every time.
2. **`tactical_dive_active == True`** (copilot necessarily on in this branch): a collision is treated as "terrain came up faster than the state machine anticipated," not a crash — the aircraft is clamped to `max(ground/wingtip elevations) + MIN_SAFE_AGL_M (+30m margin during recovery)` and pitched up. **Critical rule, previously broken and now fixed:** this recovery branch must never force `dive_phase` back to `"LEVEL_SPRINT"` while the phase is `"RECLIMB"` — doing so previously created an infinite `RECLIMB ⇄ LEVEL_SPRINT` oscillation that could trap the aircraft near the canyon floor forever, so the dive sequence never reached cruise altitude again. The corrected rule downgrades to `LEVEL_SPRINT` only while genuinely still diving/sprinting; during `RECLIMB` a close-terrain event always resolves as "pitch up harder," never as "give up the climb."
3. **Copilot on, not tactical-diving** (i.e. cruising/manual with GCAS active) → same emergency-pull-up response as the GCAS red zone (§6); this is a second line of defense for a collision that TTI-based prediction didn't catch in time.

**Expected behavior:** it should be **structurally impossible** to see a CFIT crash while `copilot_on == True`, in any mode. Confirmed via extended headless stress-testing (dive + faults + manual override + turns, 12,000+ ticks) with `is_crashed` never becoming true while copilot stayed on.

---

## 9. Autonomous Tactical Dive — the `dive_phase` state machine

Triggered by `[1]` (toggles `fault_overheat` and, when turning it on, `tactical_dive_active = True`, `dive_phase = "SEEK_CANYON"`), or reachable at any time the overheat fault is otherwise raised.

```
SEEK_CANYON → DESCENT → LEVEL_SPRINT → RECLIMB → IDLE
```

| Phase | Entry condition | What it does every tick | Exit condition |
|---|---|---|---|
| **SEEK_CANYON** | Fault 01 triggered | Calls `find_open_ground_corridor()` once (on trigger) to pick a target bearing; each tick banks/turns toward that bearing at up to `2× TURN_RATE_RADS`, with roll proportional to heading error | `|heading error| < 25°` |
| **DESCENT** | Aligned with corridor | Ramps pitch toward −18° (`4·dt` first-order lag), throttles back to 35% (eco cooldown), keeps re-centering on the corridor bearing | `AGL ≤ 150 m` |
| **LEVEL_SPRINT** | Reached canyon floor band | Holds a shallow pitch band (±6–7°) tracking `ground_z + 80 m`, ramps throttle back up to 80%, actively balances left/right wall distance, tracks CHT via `basin_loiter_s` — must be **both** `CHT ≤ 100°C` **and** sustained there for `1.5 s` before allowing re-climb (prevents a premature climb on a transient dip) | `CHT ≤ 100°C` for `≥ 1.5s` continuously |
| **RECLIMB** | Thermal recovery confirmed | Ramps pitch toward +18°, throttle to 95% (full climb power), levels roll; §8's collision guard may push pitch even higher if a ridge intrudes, but will never demote the phase back to `LEVEL_SPRINT` | `altitude ≥ target_safe_cruise − 40 m` |
| **IDLE** | Cruise re-established | Clears `tactical_dive_active`, resets pitch/throttle to nominal cruise values, logs mission-resumed | (terminal — re-enters `SEEK_CANYON` only via a fresh `[1]` trigger) |

**Expected full-cycle timing** (validated headless, from 15,000 ft cruise / ~1,474 m AGL down to ~150 m AGL and back): roughly **165–175 simulated seconds** end-to-end for the whole `SEEK_CANYON → IDLE` cycle, dominated by the sheer vertical distance (~1,300 m each way) rather than any bug — this is a long, deliberate cinematic sequence, not a quick blip. If a future tuning pass wants a snappier demo cadence, the correct lever is either a steeper `DESCENT`/`RECLIMB` pitch target or a lower cruise AGL constant — not the thermal model, which is now decoupled from timing (§5).

**RECLIMB terrain risk (accepted, monitored)**: because the climb-out flies a fixed heading and a fixed pitch target rather than a lookahead-aware path planner, AGL can legitimately dip into the tens-of-meters range if a ridge rises faster than the aircraft can out-climb it — the §8 collision guard catches this and pitches up harder, and in verified traces the aircraft never crashes this way, but clearance margins as low as ~6–8 m AGL were observed before the guard's clearance buffer was widened (now 30 m instead of 10 m). If genuinely tighter margins are required, the correct fix is a forward-looking terrain profile check *during* RECLIMB (probe some seconds ahead along the current climb path and pre-emptively steepen pitch), not another reactive clamp.

---

## 10. Chase Camera — `update_chase_camera`

A spring-damper "hero chase cam," not a rigid parent-constraint:

1. **Ideal position** = `pos + tail_dir·CAM_DIST_BEHIND(26m) + up·CAM_HEIGHT_ABOVE(5.2m)`.
2. **Terrain clamp**: never let the *ideal* position dip below `terrain_z(camera_xy) + CAM_MIN_TERRAIN_CLR (10m)` — prevents the camera clipping through canyon walls on tight turns.
3. **Critically-damped follow**: `cam_world_pos = lerp(cam_world_pos, ideal_pos, 0.18)` per tick — this is what gives the camera inertia/lag rather than teleporting rigidly with the aircraft.
4. **Look-ahead target** 45 m ahead along the flight path, with pitch clamped to `[-35°, +20°]` so the camera can't whip to looking straight down/up during extreme aircraft attitudes; roll follows the aircraft's roll damped to 12% (`CAM_ROLL_DAMPING`) so the horizon stays mostly stable ("88% horizon stabilized").
5. **Speed-dependent buffet**: a small multi-frequency positional jitter (engine-RPM-frequency component + airspeed-frequency component) scaled by dynamic pressure `q`, toggled by `[B]`.
6. **Screen-space diagnostics**: every tick, projects the UAV mesh's bounding box through `world_to_camera_view` to report actual on-screen width/height percentage — this is what backs the camera diagnostic HUD panel (`[V]`), and is the objective way to verify "is the aircraft framed correctly" without eyeballing it.

**Expected behavior:** the aircraft should always stay within a roughly consistent screen-space envelope (the diagnostic panel is the way to check this quantitatively) regardless of terrain undulation or bank angle, with a barely-perceptible mechanical lag rather than being rigidly locked to the airframe.

---

## 11. HUD — `TacticalHUDDrawer`

Pure `gpu`/`blf` immediate-mode drawing every frame (no cached geometry), laid out as:

- **Top bar**: mission phase, heading, copilot status badge, color-coded AI status pill (red = critical/pull-up, amber = warning, green = nominal).
- **Center tapes**: airspeed (left, KIAS-dominant with km/h, m/s, and instantaneous acceleration as secondary readouts) and altitude (right, feet-AMSL-dominant with meters-MSL and color-coded AGL as secondary).
- **Boresight reticle** + radar/wing-clearance strip (forward distance, TTI, left/right wall clearance, minimum wingtip clearance — all color-shifted by the same GCAS thresholds used in the physics).
- **Propulsion telemetry panel** (throttle/thrust, RPM, CHT, oil pressure) with live-filling bar gauges.
- **Avionics log panel** — a rolling 4-line window onto `FlightState._logs` (deduped within 1.5 s so identical warnings don't spam every frame).
- **Thermal highlight banner** (§5's dramatization) — only visible when actively overheating, actively cooling, or the CHT rate-of-change exceeds ±0.4°C/s — this must be wired into `render()` for the thermal narrative to be visible at all (previously dead code; now called every frame and gated by its own activity check, so it doesn't clutter the screen during nominal cruise).
- **Camera diagnostic card** (`[V]` toggle) — lens/FOV, trail distance, screen-space occupancy.
- **Crash Card** — replaces the entire HUD when `is_crashed`, per the spec's high-visibility debrief layout.

**Expected behavior:** every color-coded threshold on the HUD (AGL, CHT, oil pressure, TTI) must match the actual threshold constant used by the physics/GCAS logic driving that same value — if a tuning pass changes `MIN_SAFE_AGL_M` or the CHT fault thresholds, the corresponding HUD color-break constants must move with them, or the display will visually lie about the aircraft's actual safety margin.

---

## 12. Controls & Modal Operator

`OT_CanyonTacticalFlightSim` is a standard Blender modal operator: a 143 Hz `event_timer` drives `update_simulation` + `update_chase_camera` on `'TIMER'` events, while all keyboard events are handled inline in `modal()`. Two categories of input:

- **Held/continuous** (`W/S`, `A/D`, `E/Q`): set boolean `inp_*` flags on press/release; the physics tick reads these flags rather than reacting to the discrete event, giving smooth continuous control independent of key-repeat timing.
- **Discrete triggers** (throttle presets `7/8/9`, camera zoom `[`/`]`, fault toggles `1/2/3/0`, `P`/`C` copilot, `R` reset, `V` diagnostics, `B` buffet, `SPACE` pause, `K` instant-crash for demos): fire once on `pressed`.

`invoke()` registers the draw handler and timer, resets the simulation to ingress state, **pre-warms** the DEM/BVH by firing one throwaway raycast (avoids a first-frame stutter from lazy-loading the heightfield or building the BVH mid-flight), and starts the (optional) mission recorder. `cancel()` is the single teardown path — it exports the mission report bundle *before* removing the timer/draw-handler, wrapped in a broad exception guard so a failed report export can never prevent the simulator window from closing cleanly.

**Expected behavior:** every keypress in the control list from the module docstring must map to exactly the behavior described there; if a hotkey is added or changed, the docstring, the `modal()` handler, and the HUD footer control legend (§11) must all be updated together — they are three independent copies of the same information today.

---

## 13. Mission Recorder (`flight_mission_recorder.py`)

Optional by explicit design (`FlightMissionRecorder = None` on import failure) — the simulator must fly identically whether or not this module is present; it only ever *adds* a `report_dump/mission_NNN/` bundle on exit (readings, faults, timeline, predictions, health, actions, mission summary). Sampling happens on the same `'TIMER'` tick as the physics update, at whatever internal rate the recorder itself decides (observed ~2 Hz), and crash events are logged immediately via `log_crash()`. Both the periodic `sample()` and the final `export()` are wrapped in broad exception handlers in the caller — a reporting failure must never be allowed to interrupt the crash HUD or block clean shutdown.

**Expected behavior:** deleting or renaming this file should never break `standalone_canyon_flight_app.py` — only silence the report-dump output. This contract was preserved and stress-tested (12,000-tick combined regression run with the recorder active, all fault types, dive cycle, manual override, and a crash+reset cycle, exporting cleanly at the end).

---

## 14. Summary — what "ideal" means for this simulator

1. **No exceptions, ever, in either draw or physics** — verified via headless stress runs; any future change must be re-validated the same way (see the probe scripts pattern used in this pass: import the module inside a `blender -b Models/terrain.blend --python <script>` invocation, drive `update_simulation`/`update_chase_camera` directly with a fixed `dt_override`, and assert on state, not just "it didn't print a traceback").
2. **Copilot ON is a hard safety guarantee** — CFIT should be structurally unreachable, only ever resolvable as a GCAS pull-up or a tactical-dive terrain-avoidance nudge.
3. **Copilot OFF is a hard risk guarantee** — the exact same terrain geometry that GCAS would have saved you from must instead produce a clean, telemetry-complete crash sequence.
4. **The thermal-dive narrative must be continuous and legible** — CHT should visibly climb, peak, and fall across a dive in a single smooth arc tied to real mission geometry, and the corresponding HUD banner must actually render.
5. **Every autonomous state machine must be able to reach its terminal state** — `SEEK_CANYON → ... → IDLE` must complete on its own without getting logically trapped between two phases, under any terrain the corridor scanner might pick.
6. **Telemetry accuracy tracks the update rate it's actually sampled at** — AGL (safety-critical, every tick) vs. forward/lateral obstacle distance (staggered, ~80 ms tolerance) is a deliberate, documented trade-off, not an oversight — any future perf optimization must preserve that AGL stays on the fast path.

---

# PART II — Product Requirements Document

**Product:** AI-Enabled Real-Time Digital Twin for Rotax-912-class MALE UAV Engines (DRDO / iDEX PS-26054)
**This document's scope:** what features the full product is expected to have, which of them exist today, and — for everything not yet done — exactly how it should be built. Part I (above) is the as-built spec for the one piece that is furthest along (the tactical canyon simulator); Part II is the product-level view across all three execution tracks in `final_tasks/00_MASTER_EXECUTION_PLAN.md`.

## 15. Problem & Users

MALE UAVs (TAPAS-BH-201, Rustom-II class) fly single-engine, 18–30+ hour ISR sorties over contested, remote terrain (Ladakh, Thar Desert). A single Rotax-912-class engine fault with no predictive warning means the aircraft is lost. Conventional monitoring is threshold-based (alarm only after damage has begun). The product must give three roles a materially earlier and more actionable signal:

| Persona | Needs from this product |
|---|---|
| **UAV Pilot / Operator (GCS console)** | Real-time cockpit-style awareness of engine health and terrain risk during the sortie; plain-language tactical commands; a safety net that prevents CFIT without taking away agency unless truly necessary. |
| **Flight Safety Officer / Debrief Analyst** | Post-flight ability to scrub back through exactly what happened, when, and why an anomaly fired — not just a chart, a *replay*. |
| **Maintenance / CBM Crew** | Fleet-level, cross-sortie, cross-region view of subsystem wear, with concrete, signed-off-able work orders — not raw sensor logs. |

## 16. Feature Inventory & Status

Status legend: ✅ Done and verified · 🟡 Partially built · ⬜ Not started.

**Revision note (2026-09-09, second pass):** the first version of this table under-counted what already existed, because it was written from a shallow directory listing rather than reading the actual backend code. A follow-up audit (Explore agent, file:line evidence) plus direct implementation work corrected it: F11, F13, F14 were already substantially done and are now marked as such; F10 and F15 were genuinely missing and have since been implemented and verified end-to-end (see their entries below and §17).

| # | Feature | Track | Status | Primary files |
|---|---|---|---|---|
| F1 | 3D DEM terrain radar (dual backend, zero self-intersection) | 1 | ✅ | `standalone_canyon_flight_app.py :: TacticalTerrainRadar` |
| F2 | First-principles flight kinematics & aerodynamics | 1 | ✅ | same file, `update_simulation()` §4 in Part I |
| F3 | Thermodynamic engine twin (CHT/oil coupled to altitude & fault state) | 1 | ✅ | same file, §5 in Part I |
| F4 | Auto-GCAS (3-zone TTI/AGL safety gate) | 1 | ✅ | same file, §6 in Part I |
| F5 | Autonomous tactical dive state machine | 1 | ✅ | same file, §9 in Part I |
| F6 | Center-screen Crash Card & CFIT sequence | 1 | ✅ | same file, `_trigger_crash_event`, `_render_crash_screen` |
| F7 | Cinematic chase camera w/ terrain clamp & buffet | 1 | ✅ | same file, `update_chase_camera()` |
| F8 | GPU tactical HUD (tapes, radar strip, thermal banner) | 1 | ✅ | same file, `TacticalHUDDrawer` |
| F9 | Post-mission report bundle export | 1 | ✅ | `flight_mission_recorder.py` |
| F10 | **Natural-language / voice copilot → flight-vector intent mapping into the running Blender sim** | 1 | ✅ **(implemented this pass)** | `backend/agent/flight_intent.py` (new), `POST /api/copilot/flight-command` in `backend/server/main.py`, `poll_flight_intent_command()`/`_apply_flight_intent()` in `standalone_canyon_flight_app.py`. Verified end-to-end via HTTP → file queue → Blender poll for all 6 canonical intents (see §17). |
| F11 | 8-fault diagnostic classifier + RUL estimator | — | ✅ (already existed; not this project's gap) | `backend/ml/fault_classifier.py::RotaxFaultClassifier` (rule/threshold-based, all 8 canonical faults), `backend/ml/rul_estimator.py` + `backend/ml/trend_analyser.py::ProbabilisticRULEstimator` (analytical degradation curve fits, not a trained black-box), `backend/ml/anomaly_detector.py::ResidualAutoencoder` (genuinely trained anomaly scorer). All analytical/rule-based rather than ML-trained end-to-end, which is *correct* per §17's original guidance to prefer a physically-grounded first implementation — no further work needed here. |
| F12 | Historical Mission Replay & Scrubber (Track 2) | 2 | ✅ **(implemented this pass)** | Backend: `backend/telemetry/replay_engine.py` (`ReplayEngine`, reuses the existing `report_dump/mission_NNN/` bundles rather than inventing a second CSV/Parquet data model) + `GET /api/replay/manifests`, `GET /api/replay/{mission_id}/manifest`, `GET /api/replay/{mission_id}/frame?time_sec=` in `main.py`. Frontend: `useMissionReplay.ts` (rAF-driven playback clock, throttled frame fetches, seek/step/speed controls) + `MissionReplayScrubber.tsx` (timeline with color-coded event markers, VCR controls, live dial readout), wired into `App.tsx` as a new "Mission replay" tab. Verified against all 38 real mission bundles already on disk (manifest listing, event markers, at-or-before frame seeking with correct clamping at both ends, 404s on unknown ids) and a clean `tsc`/`vite build`. |
| F13 | Persistent Mission Knowledge Graph | 3 | ✅ (JSON, not SQLite — and that's fine) | `backend/graph/mission_graph.py` persists to `data/graph_db/fleet_graph.json` with atomic tmp+`os.replace` writes and loads on startup — confirmed this **already satisfies** the real acceptance criterion ("restarting the server loses no data": verified by killing and restarting the live backend and confirming a sign-off survived, §17). The task doc's literal ask was SQLite specifically; seed a migration only if/when a genuine query-scale or concurrent-writer need shows up — rewriting working, atomic, already-tested persistence to satisfy a technology preference with no unmet requirement behind it would be scope creep, not a fix. |
| F14 | Cross-regional CBM analytics (Ladakh vs Thar) | 3 | ✅ (already existed) | `MissionKnowledgeGraph.get_region_comparison()` + `GET /api/cbm/regions`, confirmed live against real accumulated fleet data (18 prior Ladakh sorties, 182 anomaly events) during this pass's testing. |
| F15 | Automated maintenance work-order generation & sign-off | 3 | ✅ **(implemented this pass)** | Work-order *creation* already existed (`record_maintenance_action`); the missing half — closing one — is now `MissionKnowledgeGraph.sign_off_action()` + `GET /api/cbm/maintenance` + `POST /api/cbm/maintenance/{action_id}/signoff` in `backend/server/main.py`. Verified: sign-off succeeds once, a second sign-off attempt on the same order returns 409 (not a silent no-op), an unknown `action_id` returns 404, and the closed status survives a server restart. |

**Reading this table:** Part I of this document is the as-built spec for the tactical canyon simulator (F1–F9), already fully done. All six original PRD gaps (F10–F15) are now closed: F1–F11, F13, F14 were verified working (some already existed under different names than the original PRD assumed); F10, F12, and F15 were implemented and verified end-to-end in this pass. §17 below is kept in place as a record of the implementation approach and the reasoning behind it, not as an outstanding to-do list.

## 17. Feature Specifications — what's left to build

### F10 — Natural-Language / Voice Copilot Integration
**Why it matters:** `01_DYNAMIC_TACTICAL_SIMULATION_AND_AUTOGCAS.md` §2 Subsystem 1 and the master plan's verification checklist both explicitly require: *type/speak "Dive left into canyon" → verify dynamic turn into gorge*. Today that only works via the `[1]` hotkey; there is no text or voice path into the running Blender modal operator at all.

**Acceptance criteria**
- An operator can type (Whisper STT is optional/stretch) a command like *"take a dive to the left to cool the engine"* into a text field, and within one physics tick the aircraft begins turning toward the parsed heading offset and initiates the dive sequence — the same `tactical_dive_active`/`dive_phase` state machine from Part I §9, not a parallel implementation.
- All six intents in `01_DYNAMIC_TACTICAL_SIMULATION_AND_AUTOGCAS.md` §5 (`DIVE_CONVECTIVE_COOL`, `DIVE_LEFT_VALLEY`, `EVADE_RIGHT`, `RE_CLIMB_CRUISE`, `SET_COPILOT_ON`, `SET_COPILOT_OFF`) map to values consumed by `update_simulation()`, not by a separate script.
- Unrecognized/ambiguous input never crashes the modal operator or silently no-ops without a HUD log entry explaining why.

**How to implement it**
1. **Do not** re-implement intent parsing inside `standalone_canyon_flight_app.py`. `backend/agent/copilot.py` already owns this; the sim process should only *consume* its output.
2. Because Blender's Python is a separate, embedded interpreter with its own GIL and no asyncio-friendly socket loop guarantees, the cleanest coupling is a **local file or loopback-socket command queue**, not a direct import: `copilot.py` (running as, or called by, the existing backend server) writes a small JSON command (`{"intent": "DIVE_LEFT_VALLEY", "heading_offset_deg": -45.0, ...}`) to a well-known location (a local TCP port on `127.0.0.1`, or a polled JSON file under a `runtime/` scratch dir) — either is acceptable, but pick **one** and document it; do not build both.
3. Add a lightweight non-blocking poll inside the existing `'TIMER'` branch of `OT_CanyonTacticalFlightSim.modal()` (Part I §12) — e.g. `if st.tick_count % N == 0: check_for_intent_command()` — that reads at most one pending command per poll and translates it into the *same* state fields the hotkeys already set (`st.inp_turn_left`, `st.dive_target_bearing`, `st.tactical_dive_active`, `st.copilot_on`, …). This guarantees the NL path and the hotkey path are provably equivalent, because they write the same variables.
4. Log every accepted/rejected command to `st.add_log(...)` so the HUD avionics log panel (Part I §11) is the single source of truth for "what did the copilot just do," matching the spec's demo script (type a command, watch the HUD react).
5. Voice (Whisper STT) is additive on top of step 2–4: it only needs to produce the same JSON command shape; it must not require any change inside the Blender process.

### F11 — Fault Classifier & RUL Estimator
**Why it matters:** the problem statement's core differentiator over "threshold monitoring" (§1 of `01_problem_statement_and_analysis.md`) is a predictive horizon — detecting a drift *before* a hard limit is crossed and estimating time-to-failure, not just reacting to `CHT > 135°C`.

**Acceptance criteria**
- Given a stream of `(cht_c, cht_rate_c_s, oil_p_bar, rpm, fuel_flow_lh, agl_m)` samples, a classifier assigns one of the 8 canonical fault signatures from `01_problem_statement_and_analysis.md` §4 (or `NOMINAL`) with a confidence score, using the *rate/derivative* signatures in that table (e.g. `ΔCHT₂ > +25°C thermal runaway slope`), not just instantaneous thresholds.
- A RUL number (in minutes) is produced once a fault is flagged, and it must visibly count down/adjust as the aircraft's own mitigating action changes the underlying physical trend (e.g. RUL should extend once a dive begins cooling the engine) — RUL must derive from the same physical state Part I §5 already computes, not a separate synthetic model detached from what the pilot is looking at.
- False-positive rate on nominal cruise telemetry (no fault flags active) must be effectively zero — the existing sim already emits ground-truth fault labels (`st.fault_overheat`, etc.) which should be used as the training/validation label source in offline development, and as an online sanity check (never flag a fault the ground truth says isn't injected) during any in-sim demo.

**How to implement it**
1. Keep this **out of the Blender process**. Feature extraction (rolling CHT slope, RPM jitter FFT, etc.) and the classifier itself belong in `backend/` (a Python service that already has full numeric library access, unlike Blender's bundled interpreter) — `backend/agent/diagnostic_agent.py` looks like the intended home based on naming; verify before adding a new module.
2. The sim's only obligation is to keep emitting the fields the classifier needs at a stable rate — this is already covered by `mission_recorder.sample(st)` (Part I §13) at ~2 Hz; if the classifier needs a higher rate for the RPM-jitter FFT signature (Fault 03), add a second, higher-rate sample hook there rather than changing the physics tick rate.
3. Start with a rule-based/statistical detector (rolling-window slope + z-score against the 8 documented signatures) before reaching for a trained ML model — the problem statement's fault table is already expressed as explicit numeric thresholds/slopes, so a first correct implementation does not require training data. Reserve an actual learned classifier for a later iteration once real/simulated multi-sortie data exists to train and validate against (which is exactly what F13's persistent graph will accumulate).
4. RUL: use a simple physically-grounded extrapolation first (linear projection of the current CHT slope to the failure threshold, seconds-to-failure → minutes) rather than a black-box regression — this is directly checkable against the sim's own known formulas from Part I §5, which a black-box model is not.

### F12 — Historical Mission Replay & Scrubber
**Why it matters:** flight safety review requires re-watching a sortie, not just reading a log — per `02_HISTORICAL_MISSION_REPLAY_AND_SCRUBBER.md`.

**Acceptance criteria** (verbatim intent from the task file, restated as testable):
- Loading a past sortie's log and scrubbing to its recorded anomaly timestamp updates every gauge to the exact recorded values at that instant, sweeps the 3D viewport camera to the affected subsystem mesh, and updates the AI diagnostic card — all within one UI frame of releasing the scrub handle.
- Playback at 1×/5×/10× must not drop frames or desync gauges from the 3D view at any speed.
- Seeking to an arbitrary timestamp (not just an event marker) must be O(1)-ish, not a linear re-scan from t=0.

**How to implement it**
1. **Data source**: the mission report bundles this project already produces (`report_dump/mission_NNN/{readings,faults,timeline,...}`, produced by `flight_mission_recorder.py`, Part I §13) are the natural input — before building a new ingest path for `data/telemetry/*.csv`/`.parquet`, check whether the existing bundle schema can serve as the `ReplayManifest`/frame source directly, or needs only a thin adapter. Building both a bespoke CSV/Parquet ingester *and* keeping the existing report-dump format would duplicate a data model for no reason.
2. **Backend**: `backend/telemetry/replay_engine.py` (new) should build an index of `{timestamp → byte_offset}` (or just load small missions fully into memory — these are minutes-to-tens-of-minutes of sub-kHz telemetry, not big data) once per loaded sortie, so `GET /api/replay/{sortie_id}/frame?time_sec=...` is a dict/array lookup, never a scan.
3. **Frontend**: `MissionReplayScrubber.tsx` + `useMissionReplay.ts` — the hook owns a single `requestAnimationFrame`-driven clock when playing, converts elapsed-time × speed-multiplier into a target `time_sec`, and only ever *requests* a frame from the backend when the target crosses into a new sample bucket — this is what keeps 10× scrubbing smooth without flooding the API with per-render-frame requests.
4. **3D sync**: reuse whatever live command channel F10 introduces (a local socket/file command queue) to send `{"cmd": "camera_focus", "target_mesh": "Covers_Theme_M_PlasticTheme_0"}` — replay-driven camera control and NL-copilot-driven camera control are the same kind of "external command into the Blender process" problem and should share one transport, not grow two.
5. Do this **after** F13, or in parallel at most — the event markers on the scrubber timeline (`ReplayEventMarker[]`) are exactly the anomaly-event rows F13's SQLite schema already defines (`anomaly_events` table); building the marker data model twice would be the same duplication risk as point 1.

### F13 — Persistent SQLite Mission Knowledge Graph
**Why it matters:** the current `data/graph_db/fleet_graph.json` is a flat file with no query capability and (depending on how it's written) a real risk of being clobbered/corrupted by concurrent writes; F14 and F15 cannot be built on top of it as-is.

**Acceptance criteria**
- Restarting the backend server does not lose any sortie, subsystem, anomaly, or maintenance-action data (verification step already specified in `00_MASTER_EXECUTION_PLAN.md` §4: run 3 Ladakh + 3 Thar sorties, restart, confirm all graph nodes persist).
- The four tables in `03_PERSISTENT_MISSION_KNOWLEDGE_GRAPH_AND_CBM.md` §3 (`sorties`, `subsystems`, `anomaly_events`, `maintenance_actions`) exist with the specified foreign keys enforced.
- Existing `fleet_graph.json` content is migrated, not discarded — write a one-time import step, don't ship a schema change that silently drops history.

**How to implement it**
1. Use Python's stdlib `sqlite3` — no new dependency needed, keeps the "100% air-gapped/offline" system invariant (`00_MASTER_EXECUTION_PLAN.md` §3) trivially true.
2. Open the connection with `PRAGMA journal_mode=WAL` — the server is a long-running process issuing frequent small writes (one anomaly event at a time) interleaved with reads (dashboard queries); WAL mode avoids writer-blocks-reader stalls that would otherwise show up as GCS dashboard latency spikes.
3. Refactor `MissionKnowledgeGraph` (`backend/graph/mission_graph.py`) so every public "add" method (`add_sortie`, `add_anomaly_event`, `add_maintenance_action`, …) does its in-memory update **and** an `INSERT` in the same call, wrapped in a transaction — never let the in-memory graph and the on-disk graph diverge as two sources of truth that must be manually kept in sync.
4. Write a migration function that reads the existing `data/graph_db/fleet_graph.json` once at first startup after this change, inserts its contents into the new tables, then renames the JSON file (e.g. `.migrated`) rather than deleting it — cheap insurance against a migration bug losing data.
5. Add the two analytical query methods named in the task file (`get_regional_wear_comparison()`, `get_open_work_orders()`) as plain parameterized SQL (`GROUP BY region`, `WHERE status = 'OPEN'`) — this is a reporting query, not something that needs an ORM or graph-query language layered on top of SQLite.

### F14 — Cross-Regional CBM Analytics
**Depends on:** F13.
**Acceptance criteria:** `GET /api/cbm/regional-analysis` returns, per region (`LADAKH`, `THAR_DESERT`, `STANDARD`), aggregate thermal-drift-anomaly counts and oil-viscosity/pressure-decay statistics, computed from real rows in `anomaly_events`/`subsystems` — not hardcoded per-region constants standing in for "Ladakh runs hotter."
**How:** two SQL aggregate queries (`SELECT region, AVG(...), COUNT(...) FROM anomaly_events JOIN sorties ... GROUP BY region`) exposed via the REST endpoint in `backend/server/main.py`; the *only* engineering work here beyond F13 is picking the right `GROUP BY`/`WHERE fault_name IN (...)` splits to match the "thermal drift = Ladakh signature, oil viscosity = Thar signature" narrative in `03_PERSISTENT_MISSION_KNOWLEDGE_GRAPH_AND_CBM.md` §4 — validate the split by actually running simulated sorties in both regions (as the master plan's own verification step prescribes) rather than assuming the query is right.

### F15 — Automated Maintenance Work Orders & Sign-off
**Depends on:** F13.
**Acceptance criteria:** every `anomaly_event` above a severity threshold automatically creates a `maintenance_actions` row with `status='OPEN'`; `POST /api/cbm/maintenance/{action_id}/signoff` flips it to `SIGNED_OFF` with an inspector name and timestamp, and this state survives a restart (same durability guarantee as F13).
**How:** this is a straightforward CRUD endpoint once F13 exists — the only design decision worth calling out is that work-order *creation* should happen inside the same transaction as the anomaly-event insert (step 3 of F13's implementation), so it's structurally impossible to record an anomaly without a corresponding actionable item, which is the entire point of moving off passive threshold alarms per the problem statement's framing (§1 of `01_problem_statement_and_analysis.md`).

## 18. Non-Functional Requirements (apply to every feature above)

Carried over verbatim from `00_MASTER_EXECUTION_PLAN.md` §3 because they are binding constraints, not suggestions:

1. **100% air-gapped/offline** — no feature above may introduce a cloud API call or internet dependency on its hot path (an optional, clearly-isolated Whisper model download for F10 is a setup-time concern, not a runtime dependency, and must still work fully offline once installed).
2. **Performance budgets**: tactical sim loop 60–120 FPS (<16 ms/frame, already met — Part I); any new backend service loop ≤50 ms tick; the replay scrubber (F12) must scrub at 60 FPS with zero UI-thread blocking.
3. **No hardcoded flight coordinates or paths** — every pathfinding/avoidance/margin computation must derive from live mesh/DEM geometry and current vehicle energy state, matching the standard already met by Part I's corridor scanner and Auto-GCAS (this is why Part I explicitly calls out the harmless-but-inert hardcoded `5800.0` reference value in `find_open_ground_corridor()` as a candidate cleanup, even though it doesn't currently bias behavior).

## 19. Suggested Sequencing (superseded — kept for history)

Originally: F13 → F10 → F12 → F14/F15 → F11. In practice, once the codebase was actually read (not just listed), F11/F13/F14 turned out already done, and F10/F15 were small enough to implement and verify directly in one pass rather than sequence — see §16. **F12 (replay/scrubber) is the only item left**, and its implementation plan in §17 stands as written; F10's file-based command-queue transport (`backend/agent/flight_intent.py`) is the reusable piece §17 anticipated for F12's 3D-camera-sync requirement — reuse that transport rather than inventing a second one.
