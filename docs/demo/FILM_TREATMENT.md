# ANUMAAN — the film

A director's treatment. Running time about 2 min 45 s. One aircraft, one flight, one fault, told so that the
story *is* the pitch: the problem is felt before it is explained, the solution is revealed by the camera
rather than by captions, and every technical claim on screen is computed or is the system's own output.

## The rules of this film

1. **The camera only cuts when the information changes place.** Air to ground, engine to data, the present to a
   possible future. Everything else is one continuous move. A cut means "look, somewhere else matters now".
2. **We go inside things to explain them.** We never put a diagram next to the aircraft; we fly into the aircraft
   until the diagram is what we are looking at.
3. **Sound arrives before picture.** Every movement opens on sound; the picture catches up.
4. **Silence is the loudest moment.** Used twice: when the gate confirms, and when the engine-out future is shown.
5. **Text is for numbers and names, never for adjectives.** If a line of copy could be on any team's slide, cut it.
6. **The crew decides.** ANUMAAN advises; it never flies the aircraft (backend/mission/prescriptive.py). The film
   shows the advisory, the human acceptance, and then the turn.
7. **Honest by construction.** The flight is a dramatised simulation and says so once, at the start. Everything
   inside the machine (detector, reservoir, forest, fleet merge, seal) is computed live in the browser.

---

## COLD OPEN — "One engine" (0:00 – 0:14)

**Sound first.** Black. A single four-cylinder firing rhythm fades in, close and dry, like a heartbeat heard through
a stethoscope. Under it, wind.

**Shot 1 — the hub.** Extreme close-up of the propeller hub, blades a blur, dusk light catching the spinner. The
camera begins a slow, unbroken pull-back: spinner → pusher engine cowling → the whole airframe → the valley → the
range. Twelve seconds, never cutting, the aircraft shrinking to a speck against the Karakoram.

**On screen, as the scale opens:** `Ladakh · 18,000 ft · hour six of eighteen` and then, alone:
**One engine.**

*Purpose:* the stakes in one shot. Everything that follows hangs on that single rotating part.

## MOVEMENT I — The problem (0:14 – 0:40)

**Shot 2 — chase.** The camera settles behind and above the aircraft as it threads the valley. The sortie clock
runs in the letterbox.

**Shot 3 — the old way.** A classic round oil-pressure gauge fades in over the frame, needle steady in the green.
Copy: **A redline speaks last.**

**Shot 4 — flash-forward (cut, silence).** Two seconds, desaturated: the same aircraft, propeller stopped, gliding
over a ridge with nothing below but rock. No music, only wind. Copy: `What a late warning looks like.`

**Shot 5 — back (cut, sound returns).** The chase resumes as if nothing happened. The needle is still in the green.

*Purpose:* the problem is shown, not stated: a gauge that is still green is not the same thing as an engine that is
well, and by the time it is not green the airframe is already committed.

## MOVEMENT II — The twin (0:40 – 1:08)

**Shot 6 — the second engine.** A cyan shell of the aircraft slides in from the right and locks onto the real one.
Copy: **A second engine flies alongside, in software.** `Physics model · this tail · this altitude, throttle, outside air`

**Shot 7 — the approach (the user's example, built out).** The camera leaves the chase and travels along the fuselage
toward the tail. As it nears the nacelle, the cowling's panel lines trace in cyan, the skin turns to X-ray, and the
engine silhouette appears inside the airframe. The camera does not stop: it passes through the cowling.

**Shot 8 — the reveal (black stage).** We arrive in the engine bay: the full Rotax 912 iS CAD in darkness, lit from one
side. A slow orbit. Subsystems ignite one at a time, each with its name: oil, fuel, ignition, cooling, exhaust,
gearbox, dual-lane ECU. Copy: `109 named components · the same parts as the Blender assembly`

**Shot 9 — the senses.** Points of light appear where the engine is measured: cylinder heads, exhaust, oil, fuel,
manifold, crank. Thin lines leave each one and gather into a single bundle that runs out of frame. Copy:
`13 channels · 20 times a second`

*Purpose:* the twin is not a dashboard; it is this engine, part by part, and it knows where every number comes from.

## MOVEMENT III — The signal (1:08 – 1:50)

**Shot 10 — it begins.** The oil system pulses amber, faintly. Nothing on any gauge has moved. A low string cluster
enters under the organ. Copy: **Oil pressure slips. Nothing is red yet.**

**Shot 11 — follow the data (match move).** The camera dives into the bundle of sensor lines and rides one frame of
telemetry out of the engine. The bay dissolves into the pipeline: twelve stations in the dark, the frame passing
through each and leaving its value behind (ingest, sensor sanity, physics twin, calibration, scorers, gate,
reservoir, diagnosis, prognosis, mission, seal). Copy: `One frame. Twelve stages. Every 50 ms.`

**Shot 12 — inside the scorer (push-in).** The camera pushes into station 6. It opens into the detector: 13 features
fan out into 260 sparse units; the 13 that fire light up, each wired to its six inputs. Three scorers against their
calibrated thresholds. The persistence gate fills, one frame at a time: one… two… three of five.

**Shot 13 — silence (cut to ground).** All sound stops. Cut to the ground station at Leh: the real console recording,
the detector card turning to **Fault confirmed**. One alert tone. Hold.

**Shot 14 — the hit (cut back).** Low brass and the full organ chord as we return to the aircraft, now boxed in rose.
Copy: `Confirmed 33 s after onset · oil pressure still 3.8 bar · the limit is 0.8`

*Purpose:* early is the product. The audience has watched the system act while the gauge was still green.

## MOVEMENT IV — The decision (1:50 – 2:30)

**Shot 15 — memory.** Brief: the reservoir's state path drawn over the aircraft, the moment it bent toward
"oil pressure loss" ringed. Copy: **It reads the path, not the snapshot.**

**Shot 16 — the options (overlay on the flight, not a panel).** Three options appear in the letterbox, one at a time,
in the system's own words (backend/mission/prescriptive.py):
`Continue as planned — 18 h reliability 41 %`
`Derate to 85 % — damage rate −40 %, still not achievable`
`Divert — assessing reach…`

**Shot 17 — the assessment (crane up).** The camera rises until the terrain becomes a map. A glide footprint sweeps
out from the aircraft like a radar return. Lines reach to each airfield in turn; each resolves: Kargil `6,190 ft
short`, Leh `1,770 ft short`, Thoise `in reach · +1,600 ft`.

**Shot 18 — the human.** Radio, the only voice-like line in the film: `ANUMAAN: recommend divert Thoise.` A beat.
`Leh: Copy. Diverting.` Copy: **ANUMAAN advises. The crew decides.**

**Shot 19 — the turn.** From the high map view, a new flight path draws itself from the aircraft to Thoise. The
camera descends to a three-quarter chase as the aircraft banks into a calculated 25° turn, leaves the valley it
was following and settles onto the new heading. Power comes back (the engine note drops: derated).

**Shot 20 — the approach and landing.** One continuous shot: final approach down the glide slope, flare, main
wheels, suspension, nose wheel, roll-out. The camera stops beside the runway as the aircraft rolls past and slows.
The organ resolves to F major as the wheels touch.

*Purpose:* detection becomes a decision, the decision belongs to a human, and the aircraft comes home.

## MOVEMENT V — Beyond this flight (2:30 – 2:45)

**Shot 21 — the question.** On the runway at dusk, the camera rises. Copy: **And if it had been something no one had
ever seen?**

**Shot 22 — the open world (brief).** The closed-set forest names a known fault and is wrong; the one-class tier,
trained on normal flight only, says *abnormal*. Copy: `A forest can only name what it was taught.`

**Shot 23 — the fleet.** Three aircraft at three bases on the map, each with its own 260-number memory; they merge.
Copy: `Every flight makes the fleet sharper. No telemetry leaves the aircraft.`

## END — Title (2:45)

Hard cut to black. **ANUMAAN** · अनुमान · inference. Beneath it, the evidence (E20, simulation), the prototype
boundary in one line, and three actions: run the demo, open the 3D twin, open the console.

---

## Sound, by movement

| Movement | Score | Design |
|---|---|---|
| Cold open | none | firing rhythm, wind, the propeller close |
| I Problem | organ drone, D minor | the flash-forward is wind only |
| II Twin | strings enter; organ opens | inside the cowling: muffled engine, metal resonance |
| III Signal | spiccato ostinato tightening with the residual; bells as the frame passes each stage and as units fire | total silence on the confirm; the console's alert; then brass and full organ |
| IV Decision | the reservoir as eight organ pipes; then the glide progression | engine note drops on derate; one tyre chirp, suspension, roll-out; F major at touchdown |
| V Beyond | a minor-second rub while the forest is wrong; a bright fifth when the open tier flags | quiet, wide |

## What is real and what is dramatised

| On screen | Status |
|---|---|
| The flight, terrain, airfield distances and margins, RUL and reliability figures | dramatised simulation, labelled once at the start |
| The CAD, part names, fault → component mapping | real assets and the shared, tested component map |
| The twelve stages and their modules | real modules; values computed live from the film's sensor stream |
| FlyHash, scorers, conformal thresholds, gate, reservoir, forest, NoveltyGate, fleet merge | computed live in the browser with the backend's algorithms and parameters |
| The ground-station shot | real console recording |
| Derate / replan / divert options | wording and structure from backend/mission/prescriptive.py; figures dramatised |

## Build notes (new work this needs)

- Propeller hub opener and continuous pull-back (camera path keyed to the model's prop position).
- Nacelle approach: panel-line trace and X-ray transition on the airframe around the engine bay, then the existing
  bay reveal.
- Sensor points and line bundle in the bay; the match move from the bundle into the pipeline scene.
- Flash-forward: same world, prop stopped, desaturated grade, silence.
- Options overlay; reachability sweep with per-field resolution; the divert path as a real branch off the valley
  route with a banked turn; a derate cue in the engine sound.
- Restructured timeline: the fault starts on its own in the bay (the injection moves to the evidence card as the
  test method: "every fault shown was injected into the plant through the console's API").

---

## Revision 2 — pitch the idea, not the build status

The film now argues the architecture in `docs/study/22_final_recommendation.md`, `docs/audit/03_the_actual_solution.md`
and `docs/audit/08_deployable_system_blueprint.md`: *the digital twin that listens to the engine*.

| Change | Why |
|---|---|
| **The engine is mounted in the nacelle.** The real Rotax CAD sits in the rear fuselage, gearbox aft; the skin goes X-ray and the lens closes on it. The bay shot opens from the same angle (computed from the mount), so the cut into the engine is a match. | The viewer sees where the engine is before going inside it. |
| **"On board" replaces the twelve-card pipeline.** Three beats, one number each: 10 kHz vibration → locked to crank angle, every cylinder, every cycle (order tracking) → 160 kbit/s raw against 22 kbit/s spare, so only a 29-byte frame goes down (690× smaller). | The bandwidth argument is the load-bearing reason for the edge split (`backend/edge/compressor.py`). |
| **The fruit fly is named.** A two-row analogy above the live detector: 50 receptors → 2,000 neurons → top 5% vs 13 features → 260 units → top 13. | Judges have to be told it is a fly circuit, not just shown a hash. |
| **"Beyond" is two verdicts.** A trained model's confident wrong name against "ABNORMAL"; then three aircraft memories merging into one. | One comparison, read in a second. |
| **The end card is the architecture in six lines.** Listens to the crankshaft · thinks on board · keeps working when jammed · knows the unknown · the fleet learns, the data stays · advises, never flies. First rung: VRDE's test cell. | The pitch, not a test report. |
| **Copy is one line per shot.** | Judges do not read paragraphs over moving pictures. |
| **Camera continuity.** A target that jumps between two frames is a cut, never a swoop; the mind scenes share one dolly; detect → decide and divert → land pick up where the previous shot left off; the bay's two shots are one orbit. Verified by stepping the whole film at 60 fps and measuring the camera against the aircraft. | The "bugs in how the video moves". |
