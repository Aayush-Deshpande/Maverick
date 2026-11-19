# Demo rework: audit and plan (2026-11-19)

Brief: `task.md`. Rule for every scene: show what the code does, with the code's own names and numbers.
Claims are limited to recorded evidence (E17, E19, E20 in `docs/build/FINDINGS.md`), all SIMULATION.

## 1. What the brief's names map to (verified in code)

| Brief says | Actually is | Where | What it really does |
|---|---|---|---|
| "Flap Blue" | **Fly Bloom** scorer | `backend/detect/scorers.py` `FlyBloomScorer` | FlyHash code of each calibrated feature vector, scored against a *frequency memory* of nominal activations. One of three tier-0 scorers. |
| "Martha Hash" / "fly hash" | **FlyHash** encoder | `backend/ml/flyhash_novelty.py` | Expand-and-sparsify: 13 features → 260 units (each samples 6 inputs, signed) → keep the top 5% (13 winners). Dasgupta et al. 2017; the docstring itself says the algorithm is not ours, the input is. |
| "Reserve Voice" | **Reservoir** (echo-state network) | `backend/detect/reservoir.py`, `EngineRuntime.ensure_heavy` | 500-node frozen sparse recurrent network (12 links/node, spectral radius 0.9, leak 0.3) + closed-form ridge readout trained per tail on a simulated fault library. Tier-1, runs on the selected engine. |
| "DeepMind-inspired fly brain" | maleCNS fly-connectome initialiser for the reservoir | `reservoir.py from_connectome`, `mk-jev-fly-brain/` | E19: connectome init **ties** degree-shuffled and random controls. The gain is the reservoir, not the biology. We do not claim the biology. |

## 2. Memory: what the system actually retains (answers to brief §7)

- **Reservoir state** `x_t = 0.7·x_{t-1} + 0.3·tanh(W·x_{t-1} + W_in·u_t)`: each new frame is read *in the context of the trajectory before it*. Fading memory over tens of frames. This is why it can name a fault from how a drift *develops*, not from one snapshot.
- **Fly Bloom frequency memory**: what nominal flight looked like for this tail, learned at calibration, mergeable across a fleet without moving raw data (`merge`, W12).
- **Persistence gate**: last 5 raw decisions; confirm at 3 of 5.
- **Thermofluid UKF**: recursive state and parameter estimates (e.g. cooling efficiency with a confidence interval), updated at 4 Hz from every frame.
- **Damage ledger** (Palmgren–Miner) accumulates over the sortie.
- **Not true:** the reservoir readout does **not** learn online; it is fitted in closed form and frozen in flight. State is per sortie (reset on a new sortie). We say "remembers", not "learns in flight".
- **Measured benefit (E19, SIM, 2 engines, 3 seeds):** reservoir beats windowed Random Forest by ~4–5 macro-F1 points.

## 3. Component-level twin: Blender vs web (brief §6)

| Engine | Named meshes in web GLB | Blender fault app | Web twin profile | Web fault→component map |
|---|---|---|---|---|
| Rotax 912 iS | 109 (same names as Blender) | yes, 8 faults → meshes, X-ray ghost + pulsing emission | yes | legacy 8-fault ids only |
| Rotax 914 F | 1180 | – | yes | runtime faults ✓ |
| Rotax 915 iS | 30 | – | yes | runtime faults ✓ |
| Austro AE300 (diesel) | 328 (common rail, HP pump, injectors, boost pipes, 20+ named sensors) | – | **missing** | **missing → no fault injection in the twin at all** |
| VRDE–Jayem 2.2L (diesel, indigenous) | 729 (Fuel_Line_HP_Cyl1–4, Injector 1–4, Glow_Plug_Cyl1–4, twin turbo, sensors) | – | **missing** | **missing** |

The geometry was never the problem: compression kept every component name. The break is the missing
mapping. Also missing everywhere: the **pipeline** (the ordered path a fault travels, e.g. rail → HP line →
injector) and the **evidence sensor** (the channel the detector actually read).

## 4. What the current film shows vs. what it should

Current film: a dramatised story of the problem, numbers on a HUD. It never shows the CAD, the
component map, fault injection, the detector internals, or the memory. Black act cards break the flow;
the landing double-hits (camera jolt + two-burst screech, terrain noise over the runway).

## 5. Revised film (one continuous camera, ~95 s)

| # | Scene | What is on screen (all real) | Transition in |
|---|---|---|---|
| 1 | Sortie | Valley flight, sortie clock, radio | fade up from black (only black in the film) |
| 2 | The twin | Twin shell docks; live instruments | chase move |
| 3 | Inside | Push into the nacelle; airframe goes X-ray; the **real Rotax 912 iS CAD (109 components)** resolves in place; subsystem callouts; **fault injected** with the real API call; oil system turns hot with the Blender app's own materials; **Blender render vs web render side by side** | push-in + X-ray dissolve |
| 4 | Drift | Back in flight; measured leaves expected inside limits | pull-out |
| 5 | Detect | World dims; the **tier-0 detector computed live in the browser**: 13 calibrated features → FlyHash 260 units → 13 winners → Fly Bloom familiarity; Mahalanobis and max\|z\| against split-conformal thresholds (α = 0.01); persistence gate 3 of 5 → confirmed. Cross-cut to the real console. | world dims under the overlay |
| 6 | Memory | **500-node reservoir** stepping live; its state trajectory with a fading trail; readout scores move from NOMINAL to OIL_PRESSURE_LOSS. Honest captions (frozen readout, E19, connectome tie). | overlay morphs |
| 7 | Decide | ATA directive, RUL interval, mission reliability | world returns |
| 8 | Glide | Footprint, fields in reach | bars open (IMAX) |
| 9 | Recover | Physically plausible landing | continuous |
| End | Evidence | E20 numbers + actions | hard cut to title |

## 6. Work items, in priority order

1. **Single source of truth for components** (`frontend/public/twin/component_map.json`): per engine → subsystems, sensors per detector channel, fault → components + ordered pipeline + evidence sensors. Every name validated against the GLB by a test.
2. **Web twin**: add Austro AE300 and VRDE–Jayem profiles; drive fault highlighting from the map, light the pipeline in order, mark the evidence sensor.
3. **Film**: scenes 3, 5, 6 (new), remove act cards, retime the story, fix the landing.
4. **Blender renders**: headless render of `rotax_912_is_sport.blend` with the diagnostic app's highlight materials, for the side-by-side.
5. **Sound**: layered beds, convolution space, stereo placement from the camera, sync to events.

Out of scope here (not built, will not be shown as built): waveform-tier detection of injector/rail/turbo-bearing faults (not scalar-visible by design), live hardware.
