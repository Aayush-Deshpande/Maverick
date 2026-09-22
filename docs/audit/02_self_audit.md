# Self-Audit — ANUMAAN implementation

*What we actually have, read from the code rather than the documentation. Where the code is better than we claim, I say so. Where it is worse, I say that too.*

**Method:** read `backend/` module by module, checked claims in `docs/` against executing code, compared against the 11 competitor implementations in [`01_competitive_audit.md`](01_competitive_audit.md).

---

## 1. Inventory — what exists

| Module | Files | Lines | Assessment |
|---|---|---|---|
| `backend/ml` | 7 | 2,450 | Anomaly detector, fault classifier, RUL estimator, trend analyser, spectral analyser, detection pipeline. **Substantial and real** |
| `backend/agent` | 5 | 1,950 | LLM copilot. ⚠️ Largest module after ML, and not requested by the PS |
| `backend/telemetry` | 8 | 1,671 | Generation, framing, transport |
| `backend/server` | 4 | 1,492 | FastAPI + engine service |
| `backend/graph` | 3 | 681 | Mission graph + reporter |
| `backend/knowledge` | 9 | 582 | RAG store |
| `backend/reports` | 3 | 655 | Report generation |
| `backend/physics` | 3 | 577 | Thermo model + sensor validator. ⚠️ **Smallest core module** |
| `backend/voice` | 5 | 472 | ⚠️ Not in the PS at all |
| `tests/` | 11 files | — | Good coverage breadth |
| `frontend/src` | 18 files | — | React/TS |
| `apps/` | 3 apps | — | Blender twin, desktop GCS, mission graph viewer |

🔶 **The shape of this inventory is itself a finding.** `physics/` — the module the entire digital twin rests on — is the *smallest* core module at 577 lines, while `agent/` (an LLM copilot the PS never asks for) is 1,950. Competitors with weaker systems overall have deeper physics. That allocation is backwards for this problem statement.

---

## 2. The vibration finding — stated accurately

⚠️ I initially believed [`spectral_analyser.py`](../../backend/ml/spectral_analyser.py) committed an aliasing error, because [Part VI](../study/06_vibration_analysis.md) warns that spectral analysis on a 20 Hz channel is "a genuine, common, and serious error." **That accusation was wrong and I withdraw it.**

✅ **The code is Nyquist-aware and handles this correctly.** It computes:

```python
nyquist_hz = self._fs / 2.0
use_rms_fallback = target_hz > nyquist_hz   # True at 20 Hz prototype rate
```

and when the 3rd-harmonic target (≈103 Hz at 5,000 RPM, via the 2.43 reduction ratio) exceeds the 10 Hz Nyquist limit, it **declines to compute a meaningless DFT** and falls back to a window-RMS envelope proxy. The docstring states the limitation explicitly and unprompted. That is careful, honest engineering and it is better than what most of the field does.

### The actual, narrower finding

🔶 **At the prototype's configured 20 Hz rate, the DFT path never executes.** Every call takes the RMS fallback. Three consequences:

1. **The module's headline claim is not delivered by the running code.** The docstring argues that RMS "fires only when damage is already severe (~6.8× normal)" whereas "FFT spectral tracking fires at 3× normal — early warning before damage." But at 20 Hz we *are* the RMS path. The 3× vs 6.8× early-warning advantage — the module's entire reason to exist — is not active in the shipped configuration.
2. **Demo risk.** If anyone says "we do FFT-based vibration analysis" while demonstrating at 20 Hz, that statement is false in a way a signals-literate panel member can establish by reading forty lines of our own code. The code is honest; a careless claim about it would not be.
3. **We are graded 4/5 on vibration in the competitive audit for *infrastructure and honesty*, not for delivered capability.** The scaffolding is correct and the theory is the best in the field. The capability is dormant.

⬜ **Fix:** this is not a bug to patch, it is a capability to *switch on* — feed the analyser a genuine kHz vibration channel. That is precisely the thesis of [`03_the_actual_solution.md`](03_the_actual_solution.md), and it means the single largest opening in the field is one we are already 80% built for.

---

## 3. Where we are better than our documentation claims

⬜ Our own docs undersell us in three places. Each is a talking point we are currently wasting.

### 3.1 Evaluation methodology — best in field

`backend/ml/models/model_metrics.json` records:

- **"Strict Mission-Level Group Isolation (Train / Val / Test)"** — 30 missions, 10 per split, no mission spanning partitions. This is the correct defence against temporal leakage, and only two competitors do anything equivalent.
- **Validation 0.9931 / held-out test 0.9751**, reported *separately*. ✅ Publishing the ~1.8-point drop rather than quoting the flattering number is better practice than anything else I found in this field.
- **Per-fault precision / recall / F1 with support**, macro-F1, and a full 9×9 confusion matrix.
- Visible honesty in the numbers: FAULT_1 recall is 0.8359 against precision 1.0 — we under-detect fault 1 and the metrics say so plainly.

🔶 Competitors quote "98% accuracy" and "99.2% accuracy" as bare headline numbers on self-generated data. We publish the confusion matrix. **That difference is worth saying out loud and we currently say it nowhere.**

### 3.2 Sensor validation — genuinely strong

[`sensor_validator.py`](../../backend/physics/sensor_validator.py) implements physically-reasoned discrimination: per-channel rate-of-change limits derived from thermal response (CHT 1.5 °C/s physical vs >10 °C/50 ms artifact; EGT faster at 8.0 °C/s because combustion responds faster), frozen-ADC detection via variance floor, and cross-channel correlation. The noise-floor comment shows someone actually worked through why a naive threshold produced false positives on a healthy sensor.

⚠️ **But:** Gagguverse's *residual shielding* is a capability we lack. They detect a bad sensor **and zero its residual** so it cannot contaminate the health index. We detect and flag; we do not shield. That is a small, high-value gap.

### 3.3 Mission go/no-go — closer to the PS title than we realise

`RULEstimator` already emits `MissionGoNoGoAdvisory` with `planned_sortie_hours`, `margin_hours`, and **`limiting_subsystem`**. Component-level RUL across six named subsystems with Arrhenius thermal acceleration above 115 °C is more physically grounded than the field's typical "TBO × health^1.3".

⚠️ **But:** it is deterministic. There is no probability and no interval. The PS title says *Mission Reliability*; we produce a *margin*, not a *reliability*.

---

## 4. Where we are genuinely weak

| # | Weakness | Evidence | Severity |
|---|---|---|---|
| 1 | **Physics module is thinnest core component** | 577 lines vs 1,950 for the LLM copilot | **High** |
| 2 | **No calibrated uncertainty** | `grep conformal` → no matches. RUL emits point values + margins | **High** |
| 3 | **No comparison against the threshold baseline** | The PS's own framing invites it; we never measure it | **High** |
| 4 | **No ablation** | We assert the hybrid design; PRAHARI tested theirs | Medium |
| 5 | **No external validation** | All metrics on self-generated data. C-MAPSS catalogued but not used to validate methods | Medium |
| 6 | **Vibration capability dormant** | §2 | **High** (but see §2 — it is an opening) |
| 7 | **No per-tail calibration** | Generic Rotax model + live overlay, like everyone else | Medium |
| 8 | **Edge/ground split is architectural, not demonstrated** | Documented thoroughly in Parts V/XIII; no link-loss demo exists | **High** |
| 9 | **Scope sprawl** | voice (472) + agent (1,950) + knowledge (582) ≈ 3,000 lines outside the PS | Medium |
| 10 | **Repo hygiene** | `scratch/`, multiple `.backup_pre_*` files in `apps/blender_twin`, 33 MB site assets, Qwen3-4B weights in-tree | Low technically, **bad impression** if browsed |

### 4.1 On the 99.31% / 97.51% numbers

🔶 Even with correct group isolation, these are **self-graded on self-generated data**. The generator and the classifier share an author and a set of assumptions. High accuracy here demonstrates that the classifier learned the generator — which is necessary but proves nothing about a real engine.

⬜ We are better positioned than anyone to say this honestly, because our methodology *is* stronger. The line to use: *"97.5% on held-out missions, and we will tell you exactly what that number is worth: it proves the pipeline works, not that the engine is real. Here is what we did about that —"* followed by external validation. Nobody else in this field can afford to say that sentence.

---

## 5. Ledger

**Keep and amplify**
Evaluation methodology · sensor validator · component-level RUL with limiting subsystem · visualisation/Blender pipeline · the 23-part study course · dataset honesty · the Nyquist-aware spectral scaffolding.

**Fix**
Deepen `physics/` · add conformal intervals · add residual shielding · add threshold-baseline comparison · demonstrate the edge split · switch the vibration path on.

**Cut**
`backend/voice` (472 lines, not in PS). Constrain `backend/agent` to retrieval-with-citation. Clean `scratch/`, `.backup_pre_*`, and stray model weights before anyone browses the repo.

---

*Next: [`03_the_actual_solution.md`](03_the_actual_solution.md) — what to build given all of the above.*
