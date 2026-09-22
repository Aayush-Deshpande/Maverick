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

## Status against the plan

| Tier | Features | State |
|---|---|---|
| A — Strategic reframe | F31 ✅, F32 ✅, F33 ⬜, F34 ⬜, F35 ⬜ | 2/5 |
| B — Physics-of-failure life | F36 ✅, F37 ✅, F38 ⬜, F39 ⬜, F40 ⬜ | 2/5 |
| C — HFE + environment faults | F41–F45 ⬜ | 0/5 |
| D — Real interfaces | F46 ⬜, F47 ⬜, F48 ✅, F49 ⬜ | 1/4 |
| E — Twin validity | F50–F53 | F53 ✅ (partial) |
| F — Security as physics | F54, F55 ⬜ | 0/2 |
| G — Mission reliability | F56–F59 ⬜ | 0/4 |
| H — Evaluation & honesty | F60 ✅, F61 ⬜, F62 ⬜, F63 ⬜ | 1/4 |
| I — HMI | F64–F66 ⬜ | 0/3 |
| J — Edge systems | F67, F68 ⬜ | 0/2 |

**The two structural gaps from `gap_plan.md` remain open and block the headline
claims:** the plant and the twin are still one model (G01), and no lead time has
been measured (G03). Everything above is scaffolding until those close.
