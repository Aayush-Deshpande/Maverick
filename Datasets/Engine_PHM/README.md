# Engine_PHM — Turbofan degradation datasets

Proxy tier. **These are turbofans, not piston engines.** They validate RUL *methods*, not our engine.

---

## NASA C-MAPSS — Turbofan Engine Degradation Simulation

| Field | Value |
|---|---|
| **Source** | NASA Ames Prognostics Center of Excellence (PCoE) |
| **Landing page** | https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ |
| **Direct download** | https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip |
| **Type** | Simulated run-to-failure multivariate time series |
| **Size** | ~12 MB zipped |
| **Licence** | US Government work — verify current terms on the NASA page |
| **Relevance** | ★★★★ method · ★ machine |

### Structure

26 columns per row, space-delimited, no header:

```
1      unit number (engine ID)
2      time, in cycles
3–5    operational settings 1–3  (altitude, Mach number, throttle resolver angle)
6–26   sensor measurements 1–21  (temperatures, pressures, shaft speeds)
```

### Subsets

| File | Operating conditions | Fault modes | Train units | Test units |
|---|---|---|---|---|
| FD001 | 1 | 1 | 100 | 100 |
| FD002 | **6** | 1 | 260 | 259 |
| FD003 | 1 | **2** | 100 | 100 |
| FD004 | **6** | **2** | 248 | 249 |

Files per subset: `train_FDxxx.txt`, `test_FDxxx.txt`, `RUL_FDxxx.txt`.

Training data runs to failure. Test data is truncated before failure, with true RUL supplied separately.

### Standard practice

- Min-max normalisation to [0, 1], fit on training data only
- Piecewise-linear RUL target, capped at **125** cycles
- Sliding-window sequence generation for recurrent models
- Report RMSE **and** the asymmetric score (late predictions penalised more)

```
d = RUL_pred − RUL_true
d < 0:  s = exp(−d/13) − 1      (early)
d ≥ 0:  s = exp( d/10) − 1      (late — steeper)
```

### What it is good for

- Developing the entire RUL pipeline before we have our own data
- Benchmarking against a large published literature (LSTM, CNN-LSTM+attention, Transformers, GNNs)
- Demonstrating multi-condition handling via FD002/FD004
- Learning the asymmetric scoring convention

### What it is not

- ❌ **A turbofan, not a piston engine.** No reciprocating dynamics, no per-cylinder structure, no vibration channel
- ❌ Simulated — lacks real sensor noise, dropouts, installation effects
- ❌ Turbofan-specific sensors that do not map onto CHT/EGT/oil

### Use for ANUMAAN

Build and validate the RUL pipeline here. Report C-MAPSS numbers as **method** evidence alongside, never instead of, our piston-engine results.

---

## N-CMAPSS

Higher-fidelity successor with more realistic flight profiles. Same PCoE repository. Use if C-MAPSS proves too easy, or to demonstrate the method on harder data.

---

## Acquisition

```bash
cd Datasets/Engine_PHM
curl -L -o cmapss.zip "https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip"
unzip cmapss.zip
```

Or use the helper: `python Datasets/fetch.py --dataset cmapss`

---

## Citation

Saxena, A., Goebel, K., Simon, D., & Eklund, N. (2008). *Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation.* International Conference on Prognostics and Health Management.
