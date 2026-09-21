# Vibration — general machine-signal anomaly datasets

Proxy tier. Machine condition signals for developing unsupervised detection methods.

Bearing-specific datasets live in [`../Bearing/`](../Bearing/README.md).

---

## MIMII — Malfunctioning Industrial Machine Investigation and Inspection

| Field | Value |
|---|---|
| **Source** | Hitachi, Ltd. |
| **Download** | https://zenodo.org/records/3384388 |
| **Paper** | https://arxiv.org/abs/1909.09347 |
| **Type** | Audio recordings of industrial machines |
| **Machines** | Valves, pumps, fans, slide rails — 7 product models each |
| **Volume** | 5,000–10,000 s normal, ~1,000 s anomalous per model |
| **Anomalies** | Contamination, leakage, rotating unbalance, rail damage |
| **Licence** | **CC BY-SA 4.0** (ShareAlike — note the obligation) |
| **Relevance** | ★★ method |

### Variants

| Variant | Focus | URL |
|---|---|---|
| **MIMII DUE** | Domain shift from operational/environmental changes | https://zenodo.org/records/4740355 |
| **MIMII DG** | Domain generalisation | https://zenodo.org/records/6529888 |

**MIMII DUE is the interesting one for us.** Domain shift from changing operating conditions is precisely our altitude/temperature problem in another form. Methods that survive MIMII DUE's domain shift are the ones likely to survive a climb from sea level to 25,000 ft.

### Use for ANUMAAN

Develop the unsupervised anomaly detection approach on real machine signals with a genuine normal/anomalous split and realistic class imbalance. Acoustic rather than vibration, but the spectral methods are the same.

⚠️ CC BY-SA 4.0 requires attribution **and** share-alike on derivatives. Check before redistributing anything derived from it.

---

## SKAB — Skoltech Anomaly Benchmark

| Field | Value |
|---|---|
| **Source** | Skolkovo Institute of Science and Technology |
| **URL** | https://github.com/waico/SKAB |
| **Type** | Multivariate time series, labelled |
| **System** | Water-pump circuit |
| **Features** | 8 sensors |
| **Anomalies** | Induced via controlled valve switching |
| **Character** | **Highly imbalanced**, precisely labelled |
| **Relevance** | ★★★ method |

### Why it suits us

Multivariate, imbalanced, precisely labelled time series from a real physical system — the same statistical shape as engine telemetry. Good for testing:

- Mahalanobis and PCA-residual methods
- Isolation Forest and autoencoders on multivariate input
- **False-alarm rate measurement** under realistic imbalance
- Detection latency with known onset times

### Use for ANUMAAN

Primary benchmark for the multivariate anomaly stack from [Part VII](../../ANUMAAN/docs/study/07_anomaly_detection.md), before applying it to engine residuals.

---

## Other curated lists

| Resource | URL |
|---|---|
| Industrial ML datasets (curated) | https://github.com/nicolasj92/industrial-ml-datasets |
| Awesome industrial datasets | https://github.com/jonathanwvd/awesome-industrial-datasets |

Useful for finding additional proxies. Verify licence and provenance for anything sourced from a curated list rather than the original publisher.

---

## Signal-processing methods these validate

See [Part VI](../../ANUMAAN/docs/study/06_vibration_analysis.md) for the theory. These datasets let us confirm that our implementations are correct on real data:

| Technique | Validated by |
|---|---|
| FFT, PSD, windowing | Any of these |
| STFT / spectrogram | MIMII |
| Envelope analysis | [`../Bearing/`](../Bearing/README.md) — CWRU, Paderborn |
| Order tracking | Requires a tach signal — synthetic data primarily |
| Time-domain statistics | All |
| Unsupervised anomaly scoring | MIMII, SKAB |

**Order tracking is the gap.** Most public vibration datasets are constant-speed and do not include a tach channel, so our angular-resampling implementation can only be validated on synthetic data where we control the speed profile. Worth stating as a limitation.
