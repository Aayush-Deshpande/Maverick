# 04. Execution Quirks, Mathematical Formulas & Technical Debt

## 1. Core Mathematical & Algorithmic Foundations

### A. 1D Thermodynamic Otto-Cycle Plant (`backend/physics/thermo_model.py`)
1. **International Standard Atmosphere (ISA) Derating:**
   $$T(h) = T_0 - L \cdot h, \quad P(h) = P_0 \left(1 - \frac{L \cdot h}{T_0}\right)^{\frac{g_0}{R_{\text{air}} L}}, \quad \rho(h) = \frac{P(h)}{R_{\text{air}} T(h)}$$
   *Where $T_0 = 288.15\text{ K}$, $P_0 = 101.325\text{ kPa}$, $L = 0.0065\text{ K/m}$, $R_{\text{air}} = 287.05\text{ J/(kg}\cdot\text{K)}$.*
2. **Otto-Cycle Thermal Efficiency:**
   $$\eta_{\text{th}} = 1 - \frac{1}{r_c^{\gamma - 1}}$$
   *With compression ratio $r_c = 10.8$ and specific heat ratio $\gamma = 1.35$ for burned hydrocarbons, baseline thermal efficiency is $\approx 56.6\%$.*
3. **Per-Cylinder First-Order Thermal Lag:**
   $$\tau_{\text{thermal}} \frac{d T_{\text{CHT}}}{dt} = T_{\text{steady}}(N, \text{MAP}, \dot{m}_f, \text{OAT}) - T_{\text{CHT}}$$
   *Prevents false alarms during rapid throttle advancement by modeling the physical thermal inertia ($\tau \approx 8.5\text{ s}$) of the aluminum cylinder heads.*
4. **Arrhenius Thermal Damage Acceleration Factor:**
   $$AF(T) = \exp\left[\frac{E_a}{k_B} \left(\frac{1}{T_{\text{nominal}}} - \frac{1}{T_{\text{actual}}}\right)\right] \quad \text{for } T_{\text{actual}} > 115^\circ\text{C}$$
   *Accelerates component degradation exponentially once cylinder temperatures breach safe operational margins.*

---

### B. Distribution-Free Conformal Prediction (`backend/evaluation/conformal.py`)
1. **Split-Conformal RUL Interval Formulation:**
   Given exchangeable calibration nonconformity scores $s_i = |y_i - \hat{\mu}(x_i)|$, the $(1-\alpha)$ empirical quantile $\hat{q}$ guarantees finite-sample coverage:
   $$\mathbb{P}\left(Y_{n+1} \in \left[\hat{\mu}(X_{n+1}) - \hat{q}, \;\hat{\mu}(X_{n+1}) + \hat{q}\right]\right) \ge 1 - \alpha$$
2. **Adaptive Conformal Inference (ACI) under Distribution Shift (Gibbs & Candes 2021):**
   When ambient environmental regimes change (e.g. sea-level desert to high-altitude Ladakh cold-soak), exchangeability fails. The nominal miscoverage level $\alpha_t$ is updated dynamically:
   $$\alpha_{t+1} = \alpha_t + \gamma (\alpha - \text{err}_t), \quad \text{where } \text{err}_t = \mathbb{I}(y_t \notin C_t(x_t))$$
   *Tracks nominal coverage over long missions regardless of engine aging or environmental drift.*

---

### C. Bio-Inspired FlyHash Sparse Coding (`backend/ml/flyhash_novelty.py`)
Modeled on the *Drosophila melanogaster* olfactory circuit (Dasgupta et al. 2017):
1. **Input Representation:** Fuses 14 physics residuals with spectral order features ($x \in \mathbb{R}^{27}$).
2. **Sparse Random Expansion:** Projects $x$ into $m = 540$ Kenyon cells using a sparse binary matrix $M \in \{0, 1\}^{m \times 27}$ with fixed fan-in (6 projection neurons per cell).
3. **Winner-Take-All Sparsification:** Silences 95% of lowest activations, preserving the top $k = 27$ bits (5% density) as binary fingerprint $h(x) \in \{0, 1\}^m$.
4. **Novelty Score:**
   $$\text{Score}_{\text{novelty}} = \frac{\sum_{i=1}^m h_i(x) \cdot (1 - \text{SeenNominal}_i)}{\sum_{i=1}^m h_i(x)}$$
   *Catches compound, unprecedented failures zero-shot at the edge without neural retraining.*

---

### D. Crank-Angle Order Tracking & Work Estimation (`backend/ml/crank_diagnostics.py`)
1. **Tach-Synchronous Angular Resampling:** Resamples time-series crank angular velocity $\omega(t)$ onto a uniform angular displacement grid $\Delta \theta = 0.5^\circ$, removing engine speed variance.
2. **Per-Cylinder Work Attribution:**
   $$W_{\text{cyl}} = \int_{\theta_{\text{TDC}}}^{\theta_{\text{BDC}}} T_{\text{indicated}}(\theta) \, d\theta \approx \frac{1}{2} I_{\text{flywheel}} \left(\omega_{\text{BDC}}^2 - \omega_{\text{TDC}}^2\right)$$
3. **Combustion Instability Metric:**
   $$\text{COV}_{\text{work}} = \frac{\sigma(W_{\text{cyl}})}{\mu(W_{\text{cyl}})} \times 100\% \quad (\text{Threshold: } >8\% \implies \text{unstable combustion})$$

---

## 2. Execution Quirks, Gotchas & Architectural Debt

### 1. Windows Code Page Trap (cp1252 vs UTF-8)
* **Location:** `backend/server/main.py:23-36`
* **Quirk:** On Windows, launching Python outside of `launch_backend_server.bat` defaults `sys.stdout` to `cp1252`. When `LocalKnowledgeStore` loads manuals containing UTF-8 glyphs (em-dashes, checkmarks), it raises an unhandled `UnicodeEncodeError` during synchronous startup lifespan, silently killing the server before it binds port 8000.
* **Resolution:** Handled via runtime stream reconfiguration (`sys.stdout.reconfigure(encoding="utf-8")`) and explicit environment setting `PYTHONUTF8=1`.

### 2. Mesh Identifier Mismatch in 3D CAD Assets
* **Location:** `backend/server/engine_service.py:40-80`
* **Quirk:** In `rotax_912_is_sport.blend`, there is no distinct sub-mesh for Fuel Injector #1. Attempting to highlight it by name in Blender logs warnings.
* **Resolution:** Handled by mapping Fault 2 to an empty target list (`FAULT_TARGET_PARTS[2] = []`) while the Three.js client draws a spatial coordinate marker instead.

### 3. G01 Independent Plant Benchmark Decoupling
* **Location:** `backend/plant/adapter.py`
* **Quirk:** Running with `ANUMAAN_USE_INDEPENDENT_PLANT=1` introduces authentic physical parameter mismatch (different bore clearances, sensor bias, thermal delays). However, published Random Forest classifier weights (`rotax_random_forest.joblib`) were trained against the original synthetic generator.
* **Status:** Off by default; must be explicitly enabled for benchmark stress testing.

### 4. High-Rate Crank Signal Disconnection
* **Location:** `backend/ml/crank_diagnostics.py` vs `backend/telemetry/can_streamer.py`
* **Quirk:** `crank_diagnostics.py` contains full order-tracking algorithms, but the live 20 Hz CAN stream operates at cycle averages ($20\text{ Hz} = 50\text{ ms}$, whereas a 5000 RPM 4-stroke cycle takes $24\text{ ms}$).
* **Status:** Crank-angle diagnostics run standalone in test suites (`tests/test_crank_diagnostics.py`) and require high-frequency encoder telemetry streams for live in-flight execution.
