# Remaining Useful Life Estimation

Knowing that a component is degrading is different from knowing how much safe operating time remains. ANUMAAN answers
this in two layers. The first, *time to limit*, says when a reading will cross its engine-manual limit if the
present trend continues. The second, *remaining useful life* (RUL), says how many flight hours remain until a
wear process ends the engine's life, with a 95 % interval. Mission planning uses the lower end of that interval.

---

## Time to limit (in service now)

Before a full remaining-useful-life model, the twin answers a narrower question: *if this keeps going, when will a reading cross its engine-manual limit?*

- **What is trended.** The model-informed residual of each limited channel (coolant, oil and head temperatures, exhaust gas temperature, oil and fuel pressure), not the raw reading. A climb or a power change is explained by the engine model, so it does not look like a trend. Only drift the model cannot explain is extrapolated.
- **Slope.** Theil–Sen (the median of all pairwise slopes, robust to sensor spikes) over 10-minute and 1-hour windows, with its 95 % confidence interval. A trend is reported only when the whole interval points toward a limit.
- **Projection.** The gap is the limit minus the current value (a median of the last samples). A developing fault usually accelerates, for example a growing blockage. So when a quadratic fit of the window is accelerating it gives the point estimate; otherwise the straight line does. The interval spans both projections, the slope interval and the uncertainty of the current value. Nothing beyond 10 hours is reported.

**Measured (SIMULATION).** Slow faults (radiator blockage on the 914 and AE300, oil-cooler blockage on the 914) were ramped over 30 minutes at high power on a hot day, on test tails 1001 and 1002. A time-to-limit appeared before the limit was reached in every run. The true crossing time (the noise-free value) fell inside the predicted interval for **85 of 103 predictions (83 %)**; the acceptance target is 80 %.

## Remaining useful life (in service now)

**Why a simulated fleet.** No public run-to-failure data exists for aero piston engines, and engines are never run to
destruction in service. ANUMAAN therefore trains its RUL model on a *simulated* fleet in which the end of life is
known, and labels every result SIMULATION.

**The fleet.** Each trajectory is one tail with its own seed: its own build spread, sensor noise and wear-rate
multipliers.

- Slow wear processes (`backend/sim/wear.py`, `configs/wear.json`) drive registry faults: bearing wear, radiator and
  oil-cooler fouling, injector coking and turbo bearing wear, where they apply to the engine.
- Each tail draws a lognormal per-process rate multiplier, and the rate grows with load and oil temperature.
- The tail flies a cruise point (70 % lever, 8,000 ft). Each plant second stands for 2 flight hours of wear.
- End of life is the first wear process reaching full severity.
- The tail's residual detector is calibrated while healthy, exactly as in service.
- 200 tails per engine (seeds 5000 and up, disjoint from the signature tails 11/12 and the test tails 1001/1002).

**Features and model.** At every sample the model sees what the twin sees: the mean residual z-vector of the last
window and the flight hours so far. The label (hours to end of life) comes from the plant and is training data only;
it is never an input at runtime.

- The point estimate comes from gradient-boosted trees (`HistGradientBoostingRegressor`).
- The interval is *split conformal*. It is calibrated on whole trajectories held out from training, so the unit
  of exchangeability is the tail, not the sample (samples of one tail are strongly correlated).
- The interval half-width is q · scale(x), with a scale that grows with the predicted RUL, because far-from-failure
  predictions are less certain.
- The conformal guarantee holds only for tails drawn from the same distribution. Coverage is therefore *measured* on
  test tails the model never saw, never assumed.

**Measured (SIMULATION, 200 tails per engine, 3 random splits by tail, 40 test tails each, target 95 %).**

| Engine | Mean life (h) | RMSE (h) | Empirical coverage (mean, per split) | Mean interval width (h) |
|---|---|---|---|---|
| Austro AE300 | 974 | 199 | 95.3 % (95.9 / 95.9 / 93.9) | 935 |
| Rotax 912 iS | 1,011 | 225 | 94.2 % (95.4 / 94.6 / 92.6) | 962 |
| Rotax 914 | 937 | 166 | 95.2 % (96.8 / 92.2 / 96.5) | 875 |
| Rotax 915 iS | 924 | 172 | 93.5 % (95.6 / 89.1 / 95.9) | 798 |
| VRDE 2.2 L | 960 | 176 | 95.0 % (95.2 / 95.9 / 93.8) | 836 |

**What the numbers mean.**

- Coverage averages 93.5–95.3 % across the engines. Individual splits range from 89 % to 97 %.
- The 915 iS falls short: one of its three splits covered only 89.1 %, and its mean is 93.5 %. With 40 test tails
  per split, coverage moves by a few points between splits. The 915 is therefore reported as close to, but below,
  the 95 % target. It is not rounded up.
- The intervals are wide, about 85–95 % of the mean life. With residual evidence alone, a healthy engine early in
  life looks much like any other, so far from failure the model can honestly say little.
- The interval narrows as wear becomes visible in the residuals.
- These figures describe the simulated fleet only. They are not field accuracy.

**In service.** `backend/prognose/rul_service.py` loads the engine type's model from `var/models/rul_<engine>.pkl`
and builds the same features from the live residuals. Each tick it returns the point estimate, the lower and upper
bound, and the coverage target.

- Without a trained model the RUL is reported as **UNAVAILABLE**, with the command that trains it. It never shows an
  invented number.
- The console's time-to-limit card shows the RUL with its band.
- To retrain an engine's model and refresh its report, run
  `python -m backend.evaluation.sim_rul <engine_id> 200`; the report goes to
  `reports/evaluation/sim_rul_<engine>_<date>.json`.

**Not yet built.** There are two gaps:

- **A second, independent RUL path.** The plan calls for a physical damage-accumulation path next to the data path,
  with disagreement flagged to the engineer. Today only the data path runs.
- **Coverage per operating regime.** The fleet flies one cruise regime, so there is nothing yet to report per regime.

---

## Related Systems

- [Degradation Modeling and Wear Kinetics](13-degradation-modeling.md)
- [Mission Planning](16-mission-planning.md)
- [Mission Reliability Enhancement](17-mission-reliability.md)
- [Operator Ground Control Station](20-operator-gcs.md)
