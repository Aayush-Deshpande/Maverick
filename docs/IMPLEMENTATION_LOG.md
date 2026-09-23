# ANUMAAN Implementation Log

Running record of what was built against the plan in
[`audit/07_unoccupied_axes_and_ground_up_plan.md`](audit/07_unoccupied_axes_and_ground_up_plan.md).
Each entry states what was built, what was verified, and what is still unproven —
the last column matters most, because an entry with nothing in it is usually a
lie.

Feature IDs follow the plan: F01–F30 from [`audit/04_feature_spec.md`](audit/04_feature_spec.md),
F31–F68 from the ground-up plan.

---

## Session 1 — 2026-09-22

### Acquired (reference material, now in-repo)

| Asset | Location | Purpose |
|---|---|---|
| MIL-STD-1629A (54 pp) | `docs/reference/MIL-STD-1629A.pdf` | F33 FMECA derivation |
| Rotax 914 Installation Manual (200 pp) | `docs/reference/Rotax914_Installation_Manual.pdf` | F31/F32 — dimensions, turbo, mounting |
| Rotax 914 Operator's Manual (92 pp) | `docs/reference/Rotax914_Operators_Manual.pdf` | F13 operating limits, F07 performance data |
| NASA PrognosticsMetricsLibrary | `vendor/PrognosticsMetricsLibrary/` | F60 reference implementation (MATLAB) |
| NASA ACES — 16 granule archives, 140 `.mat` files, ~1 GB | `data/telemetry/nasa_aces/` | F48 real Rotax 914 flight telemetry |

ACES required Earthdata Login; files are served from `data.ghrc.earthdata.nasa.gov`
behind an EDL bearer-token redirect to CloudFront. The `ghrc.nsstc.nasa.gov`
documentation host is unreachable from this environment (TCP timeout, not auth).

---

### F36 / F37 — Physics-of-failure damage accumulation ✅

`backend/evaluation/damage_accumulation.py`

Rainflow cycle counting (ASTM E1049-85 three-point stack reduction) feeding
Palmgren-Miner linear damage, with two mechanisms: thermal LCF via a
Coffin-Manson power law, and shock cooling integrated on cooling *rate* — which
range-counting alone cannot see, because a fast and a slow ramp of equal
amplitude close the same cycle.

**Verified.** Textbook ASTM series `[0,-2,1,-3,5,-1,3,-4,4,-2,0]` counts to a
total of 5.0 cycles with the expected ranges. Flat temperature accrues exactly
zero damage; sinusoidal cycling accrues 4.7e-3. A fast CHT drop accrues
6.1e-3 shock damage where a slow drop of the same amplitude accrues zero.

**Unproven.** The Coffin-Manson constants (`C`, `m`, threshold) and the shock
cooling reference are **placeholders**, explicitly labelled as such in the
`source` field of each law. They are not traceable to any Rotax LCF
substantiation. Absolute life-consumed numbers are therefore meaningless today;
only *relative* comparisons between sorties are currently defensible. Replacing
these with OEM-traceable values is a blocking prerequisite before any damage
figure is shown outside the lab.

---

### F12 / F53 — Conformal prediction with real coverage ✅

`backend/evaluation/conformal.py`

Split conformal with the finite-sample corrected `ceil((n+1)(1-α))/n` quantile
(the plain empirical quantile under-covers on the few-dozen-sortie calibration
sets we actually have). Normalised scores supported, so interval width can track
per-sample difficulty rather than being constant across a life. `AdaptiveConformal`
implements ACI for distribution shift. `empirical_coverage()` and
`coverage_curve()` are the deliverables — claimed vs realised coverage.

**Verified.** On 300 calibration / 500 test synthetic samples at α=0.1:
empirical coverage **0.902** against nominal **0.900**, well within one binomial
standard error (0.0133).

**Unproven.** Not yet wired to the real RUL estimator, and never exercised on a
genuine distribution shift. Exchangeability is assumed and is exactly what a
degrading engine violates — that is what ACI is there for, but ACI is untested.

---

### F60 — Standard PHM prognostic metrics ✅

`backend/evaluation/prognostic_metrics.py`

Prognostic Horizon, α-λ, Relative Accuracy and Convergence per Saxena/Goebel,
applied as the hierarchical waterfall the standard specifies — later metrics
return `None` when PH fails, so an algorithm that never settles inside the
accuracy cone cannot advertise a flattering mid-life RA. Dependency-free Python
translation of the vendored NASA MATLAB library.

**Verified.** A synthetic well-behaved trajectory returns PH 100.0, α-λ pass,
RA 0.925, convergence 50.1.

**Unproven.** Not yet run against our own RUL estimator, which is the only
result that matters.

---

### F13 — Threshold baseline ✅

`backend/evaluation/threshold_baseline.py`

The conventional limit monitor we claim to beat, built strong rather than as a
strawman: caution/warning levels and persistence debounce, so a single noisy
sample cannot raise an alarm. Rotax 914 limits sourced from the operator's
manual now in `docs/reference/`, with provenance recorded per limit.
`compare_detection()` emits lead time in seconds/minutes; `false_alarm_rate()`
emits alarms per flight hour.

**Verified.** A rising CHT ramp raises CAUTION at 127 °C then WARNING at 142 °C
with correct debounce. Lead-time and false-alarm arithmetic checked.

**Unproven.** No lead time has actually been measured yet, because the twin side
of the comparison is not connected. The headline claim of this project remains
unmeasured.

---

### F31 — Engine class as configuration ✅

`backend/physics/engine_config.py`, `configs/engines/*.json`

Engine identity, layout, ratings and fuel properties moved out of code into
three JSON configs:

| Config | Class | Induction | Fault modes |
|---|---|---|---|
| `rotax_912is` | Spark, AVGAS | Naturally aspirated | 16 |
| `rotax_914` | Spark, AVGAS | **Turbocharged** | 21 |
| `austro_ae300` | **Compression, Jet-A1** | Turbocharged, intercooled | 22 |

`applicable_fault_modes()` derives the fault list from the engine's own
architecture, so switching config cannot leave a spark-misfire classifier
running on a diesel. `dominant_order` exposes the firing order (2.0 for a
four-cylinder four-stroke) that the crank-angle chain must reproduce.

**Strategic note.** `rotax_914` is now the primary target, not `rotax_912is`.
It is the global MALE standard (MQ-1 Predator, IAI Heron, Hermes 900) *and* it
is the engine in the NASA ACES dataset, so model and real validation data are
now the same engine. `austro_ae300` is the TAPAS BH-201 engine and exists to
demonstrate architecture-independence.

**Verified.** All three load; fault-mode derivation differs correctly by class.

**Unproven.** `thermo_model.py` does not consume these configs yet — it still
carries Rotax 912 constants at module level. The configs describe engines the
twin cannot yet run.

---

### F32 — Turbocharged induction ✅

`backend/physics/turbo_model.py`

ISA atmosphere, boost control to a target manifold pressure, wastegate with
finite authority, first-order turbo lag, compressor outlet temperature from the
isentropic relation derated by efficiency, intercooler effectiveness, surge
margin, and shaft overspeed. Fault injection acts on *physical parameters*
(wastegate position, leak fraction, bearing wear, fouling) and never on the
output signal.

**Verified against the defining behaviour.**

| Altitude | MAP | Ambient | PR | Boost authority |
|---|---|---|---|---|
| 0 ft | 135.0 kPa | 101.3 | 1.33 | held |
| 8 000 ft | 135.0 kPa | 75.3 | 1.79 | held |
| 16 000 ft | 135.0 kPa | 54.9 | 2.46 | held (critical altitude) |
| 20 000 ft | 114.5 kPa | 46.6 | 2.46 | **lost** |
| 25 000 ft | 92.4 kPa | 37.6 | 2.46 | **lost** |

Boost holds flat to the 16 000 ft critical altitude then decays with ambient —
the physical meaning of the spec number. A 40→100 % throttle step ramps MAP
72.6 → 129.5 kPa over ~2 s rather than jumping. Wastegate-stuck-open drops MAP
from 135.0 to 69.7 kPa; bearing wear at 0.8 severity drops efficiency 0.72→0.55.

**Unproven.** Not integrated with `thermo_model.py`, so charge temperature does
not yet drive CHT. Compressor map is a parameterised approximation, not a real
Rotax 914 map — the manual is in-repo and should replace it.

---

### F48 — NASA ACES real-telemetry loader ✅

`backend/telemetry/aces_loader.py`

Reads the ACES `.mat` granules (780 channels × 3601 samples at 1 Hz). The
channel-name matrix is a fixed-width char array that scipy returns with rows of
unequal length and embedded newlines; rows must be right-padded before reading
column-wise or every channel after the first short row misaligns. Canonical
channel names are resolved by fragment matching and then **checked against a
physical plausibility envelope**, so a name match that binds the wrong column is
refused rather than silently poisoning downstream validation.

`ACES_PROVENANCE` carries the caveat with the data: no fault labels, no
run-to-failure, all flights completed safely. Any anomaly found here is a
flight-envelope transient, not a failure.

**Verified.** 70 mechanical granules discovered; 18 canonical channels resolve
and pass plausibility on `M080001.mat`. Engine speed median **3184 rpm**, max
**5680 rpm** — correct Rotax 914 range, from real flight.

**Unproven / known issue.** Name-boundary fuzziness means some bindings are
suspect: `EGT_1` reads a median of 170 °C, which is too low for an EGT, while
`ENGINE_THERMO_2` reads 1035 °C, which looks like the real EGT. The plausibility
envelope for EGT is too wide to have caught this. Channel bindings must be
confirmed against the ACES dataset documentation PDF before any of these series
is used for physics validation.

---

## Session 2 — 2026-09-23

### F42 — Fuel thermal management / CFPP margin
`backend/physics/fuel_thermal.py`

Lumped fuel thermal mass with return-flow heating, cloud-point and CFPP margins,
wax fraction, filter blockage, cold-soak injector delivery loss, restart verdict.

**Verified.** A 6 h loiter at −45 °C OAT settles fuel at −37.9 °C (return-flow
heating balances the loss), cloud-point margin 4.1 °C, risk ADVISORY, restart
delivery 0.889 → DEGRADED_START. AVGAS at the same OAT correctly reports risk
NONE: gasoline does not wax.

**Unproven.** Equilibrium depends entirely on `return_flow_heat_w`, a guess. The
waxing path itself was never exercised, because equilibrium stayed above cloud
point.

### F43 — Induction and the dust chain
`backend/physics/induction.py`

Filter loading → dP → MAP deficit → silica ingress → bore wear → blow-by.

**Verified over 300 h.** TEMPERATE_INLAND: 5 % loaded, 5 619 h life left, bore
wear 0.0006. SEMI_ARID: 39 % loaded, 472 h left. DESERT_THAR: filter spent,
15 kPa MAP deficit, bore wear 0.086, blow-by 1.145×.

**Unproven.** The silica-to-wear coefficient is a labelled placeholder; an
earlier value saturated bore wear to 1.0 in 300 h and was corrected.

### F39 — Oil system: wear metals, debris, condition
`backend/physics/oil_system.py`

SOAP-style concentrations with per-element source attribution, debris counting,
oxidation and viscosity. An oil change resets concentration but not cumulative
wear.

**Verified.** 120 h at elevated bore wear flags Fe WARNING (202 ppm, 5.05×
caution), Al WARNING, Cr CAUTION, each correctly attributed to its component.

**Unproven.** Limits are representative fleet values, not Rotax or Austro data.
The Si → dust-ingress attribution was not exercised hard enough to dominate the
ranking.

### F40 — Environmental exposure accumulator
`backend/physics/exposure.py`

**Verified.** 240 h of desert/high-altitude operation gives cylinder bore 3.03×,
head 3.50×, turbo 1.60×, overall 2.71× fleet baseline (SEVERE).

**Corrected during development.** The first version averaged a 40× air-filter
factor into the overall number and reported 12.49× wear acceleration, which is
not credible. Filter loading genuinely is linear in dust concentration, but that
is a consumable service interval rather than engine wear; it is now reported
separately and excluded from `overall`.

### F41 — CI injector fault library
`backend/physics/injector_faults.py`

**Verified — and this is the diagnostic payoff.** Rail-pressure decay reads
`SYMMETRIC_DEFICIT` (mean 0.853, COV unchanged at 0.003); coking on cylinder 3
and needle stick on cylinder 2 read `ASYMMETRIC_DEFICIT` and name the cylinder.
That distinction decides which part gets replaced. Clearing a fault restores the
engine exactly.

**Bug found and fixed.** `delivery_fraction` was mutated in place on every
update, so the rail-pressure term compounded and drove a perfectly healthy engine
to zero delivery within ~100 steps. It is now recomputed from an immutable
per-injector baseline each step.

### F56 / F57 / F58 — Mission reliability and prescriptive advisory
`backend/mission/reliability.py`, `backend/mission/prescriptive.py`

Mission reliability as a computed probability over per-phase, per-component
hazard rates, with a Wilson interval, limiting-component attribution and a
failure-phase distribution. The prescriptive layer adds a derate ladder trading
damage rate against endurance, and re-planning over power → altitude → duration.

**Verified decision ladder** on an 18 h / 28 000 ft ISR profile:

| Damage | Result |
|---|---|
| healthy | R = 0.997 [0.995–0.998] → GO |
| 0.78 | R = 0.936 → GO as planned |
| 0.84 | R = 0.841 → **derate to 75 %: R 0.912, 29 min endurance penalty** |
| 0.92 | R = 0.094 → NO-GO, no achievable variation |

Attribution correctly identified `injector_2` as limiting and the 12.5 h loiter
as the dominant risk phase.

**Unproven, and it matters.** The base hazard rates are placeholders, tuned so a
healthy engine completes the sortie. Only the ranking of limiting components and
the relative effect of derating are defensible; the absolute probability is not.

### F33 / F35 — FMECA and fault isolability
`backend/reliability/`, `docs/reliability/`

20 failure modes per MIL-STD-1629A with severity class, RPN, criticality,
signature, channels, detection method and implementing module, tagged by engine
class. The signature matrix derives from the FMECA, so the two cannot drift.

**Headline result — as-built vs proposed instrumentation:**

| Sensor set | Detectable | Uniquely isolable | Ambiguity groups |
|---|---|---|---|
| As-built (9 channels, today's 20 Hz) | 75 % | **55 %** | 2 |
| Proposed (21 channels) | 95 % | **95 %** | 0 |

Undetectable today: rail-pressure decay, abrasive bore wear, bearing wear, oil
degradation, fuel waxing. **Indistinguishable today: misfire ≡ injector needle
stick, and wastegate-stuck ≡ compressor surge.**

That converts the crank-angle instrumentation argument from a preference into a
proof — on current sensors those pairs are literally the same observation, and no
classifier can separate them.

**Bug found and fixed.** `from_fmeca` keyed each signature by its own mode ID,
making every mode unique by construction and reporting a meaningless 100 %
isolability for *any* system. Signatures now map to a canonical observation
vocabulary so physically identical observations collide.

**Unproven.** Severity and occurrence are engineering judgement, not fleet data.
The isolability result is only as good as the signature assignments, which were
written per mode; a more adversarial assignment would likely find more ambiguity.

### F51 / F52 — Twin validity monitoring
`backend/twin/validity.py`

NIS against χ² bounds, Ljung-Box residual whiteness, per-channel bias, and
operating-envelope checks, producing a three-way attribution.

**Verified.** Healthy twin: NOMINAL, confidence 1.00, NIS 4.0 within bounds.
Biased and autocorrelated residuals with no independent fault indication:
**MODEL_DRIFT** (NIS 13.4 outside [0.5, 11.1], autocorrelation 0.91). *Identical
statistics* with the detector flagging a fault: **ENGINE_FAULT**.
Out-of-envelope operation: OUT_OF_ENVELOPE.

That discrimination is the whole point — a monitor that cannot make it will
recalibrate away a real fault.

**Unproven.** `expected_sigma` per channel is currently set by hand; it must come
from calibration flights or NIS is meaningless. Never run against the real
detection stack.

### F54 / F55 — Physics-constrained telemetry integrity
`backend/twin/integrity.py`

Seven physical constraints with conformal-calibrated thresholds, plus
stale/frozen channel detection and dual-lane FADEC disagreement.

**Verified.** Genuine telemetry: NOMINAL. A spoofed MAP value breaks two
constraints at once → SUSPECTED_SPOOF. A single broken constraint →
SENSOR_FAULT, since one bad sensor is the more parsimonious explanation. Lane
disagreement → SENSOR_FAULT.

**Unproven.** Constraint coefficients are deliberately loose approximations, and
were tested only against synthetic frames built from those same relationships,
which is circular. Needs testing against ACES.

### F46 — MAVLink EFI_STATUS ingestion
`backend/telemetry/mavlink_efi.py`

Decodes EFI_STATUS (#225) into canonical channels, with live, SITL and `.tlog`
replay paths behind one interface.

**Verified against a real pymavlink-constructed message** (85 bytes on the wire):
16 channels mapped including **ignition timing and injection time**, satisfying
PS HMS-11 *by standard message field* rather than by an invented channel, and
closing part of DTC-06.

**Unproven.** Never run against an actual SITL instance or hardware — only
against a message built in-process. The fuel-flow conversion assumes g/min,
which matches the current dialect but should be confirmed per ECU driver.

### F34 — OSA-CBM / ISO 13374 architecture mapping
`backend/osacbm.py`, `docs/ARCHITECTURE_OSACBM.md`

All 28 modules registered against the six standard functional blocks, with the
PS requirements each serves and an enforceable upward-flow layering rule.

**Verified.** 27/28 modules implemented across DA/DM/SD/HA/PA/AG, **47 distinct
PS requirements** served, **no layering violations**. The one pending module is
`spectral_analyser`, dormant until the kHz vibration channel exists (F04). The
architecture document is generated from the registry, so it cannot drift from
the code.

---

## Status against the plan

**65 features in scope · 25 implemented (38 %)**

F01–F30 from [`audit/04_feature_spec.md`](audit/04_feature_spec.md) (F09–F11 do
not exist; the spec jumps F08 → F12) plus F31–F68 from the ground-up plan.

| Tier | Features | Done |
|---|---|---|
| Crank-angle chain (F01–F08) | 8 | **0** |
| Credibility (F12–F18) | 7 | 2 — F12, F13 |
| Visualisation (F19–F24) | 6 | 0 |
| Slack (F25–F30) | 6 | 0 |
| A — Strategic reframe (F31–F35) | 5 | 5 |
| B — Physics-of-failure life (F36–F40) | 5 | 4 — F38 open |
| C — HFE + environment (F41–F45) | 5 | 3 — F44, F45 open |
| D — Real interfaces (F46–F49) | 4 | 2 — F47, F49 open |
| E — Twin validity (F50–F53) | 4 | 3 — F50 open |
| F — Security as physics (F54–F55) | 2 | 2 |
| G — Mission reliability (F56–F59) | 4 | 3 — F59 open |
| H — Evaluation (F60–F63) | 4 | 1 — F61–F63 open |
| I — HMI (F64–F66) | 3 | 0 |
| J — Edge systems (F67–F68) | 2 | 0 |

### What still blocks the headline claims

1. **G01 — the plant and the twin are still one model.** Everything above is
   scaffolding until an independent virtual engine exists.
2. **G03 — no lead time has been measured.** F13 provides the baseline; nothing
   has been run through it against the twin.
3. **F01–F08, the crank-angle chain, is entirely unbuilt** — and F35 has now
   *proved* it is load-bearing rather than merely desirable.

### Cross-cutting caveat

Every damage law, hazard rate, wear coefficient and oil limit in this
implementation is a **labelled placeholder**. Relative comparisons — this
environment versus that one, this derate versus none — are defensible. No
absolute number is, until these are replaced with OEM or fleet-traceable values.
