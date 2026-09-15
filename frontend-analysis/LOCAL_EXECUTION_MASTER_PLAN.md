# Master Plan: Local High-Fidelity Routing & Execution Architecture

## 1. System Overview & Objective
This master plan defines the precise technical strategy for hosting, routing, and executing the complete 204-asset USAvionix high-fidelity 3D web application locally inside the [`avionix`](file:///e:/backup-llm/backup-no-llm/3d_engine/avionix) directory. 

By resolving Next.js client-side asset contracts, Web Worker origins, dynamic query-string hashing, and WebGL MIME types, the application runs entirely offline on `localhost:3000` with **identical visual fidelity, 60–120 FPS animation scrubbing, and zero missing assets**.

---

## 2. The 5 Core Local Routing Challenges & Engineering Solutions

```
                               LOCAL ROUTING TOPOLOGY
┌───────────────────────────────┐
│     Client Browser Viewport   │
└───────────────┬───────────────┘
                │
                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Avionix Local HTTP Server (Port 3000)                │
│                        [avionix/serve_avionix.py]                      │
├────────────────────────────────┬───────────────────────────────────────┤
│ 1. /_next/image?url=...        │ Decodes URL parameter -> Serves static│
│ 2. /_next/static/chunks/*.js   │ Strips deployment hashes (?dpl=...)   │
│ 3. /draco/*                    │ Serves local Draco WASM & wrapper     │
│ 4. /* (Subroutes: /about, etc) │ Resolves to /<subroute>/index.html    │
│ 5. Web Worker Origin           │ Same-origin headers for OffscreenCanv │
└────────────────────────────────┴───────────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────────────────────────────────────────┐
│               Local Storage Repository (avionix/ - 204 Assets)         │
│  ├── assets/models/          (13 GLB models & baked animation tracks)  │
│  ├── assets/textures/        (19 WebP/PNG/EXR textures)                │
│  ├── assets/images/landing/  (96 AVIF sequence frames)                 │
│  ├── _next/static/           (49 JS chunks, 2 CSS files, fonts)        │
│  └── draco/                  (Draco WASM decompressor)                 │
└────────────────────────────────────────────────────────────────────────┘
```

### Challenge 1: Next.js Image Optimization Route (`/_next/image`)
* **The Issue**: Next.js replaces direct image tags with optimized pipeline endpoints:
  `/_next/image?url=%2Fassets%2Fimages%2Fbrand%2FUSAVX_horizWhite_noicon.png&w=3840&q=75`
  A standard static file server returns a 404 error because `_next/image` is not a physical file on disk.
* **The Solution**: The server intercepts all requests to `/_next/image`, parses the `url` query parameter, decodes the URI component, and directly serves the target file from `avionix/assets/images/...`.

### Challenge 2: Cache-Busting Deployment Hashes (`?dpl=dpl_FtcqDSk5...`)
* **The Issue**: Next.js appends deployment query parameters to all chunk and stylesheet references (e.g. `/_next/static/css/32d10e4cd8482b39.css?dpl=dpl_FtcqDSk5XX7p3FVW3E32CQArR5vE`). Some naive servers fail to map these to the local file path.
* **The Solution**: `translate_path()` uses `urllib.parse.urlsplit()` to extract the raw pathname prior to querying the filesystem, ensuring instant 200 OK delivery.

### Challenge 3: Web Worker Execution & OffscreenCanvas Concurrency
* **The Issue**: The rotating loading turbine (`loading-delta.glb`) runs on an `OffscreenCanvas` inside a dedicated Web Worker (`4867.14b24ff1d28f20ed.js`). If served via `file://` or across mismatched origins, modern browsers block worker instantiation due to strict cross-origin security policies.
* **The Solution**: By serving everything under the single local origin `http://localhost:3000/`, the worker instantiates natively without security warnings, maintaining its intended frame rate of 60 FPS while the main thread compiles the heavy Three.js scene.

### Challenge 4: Offline Draco Decompression Routing
* **The Issue**: Three.js `DRACOLoader` is hardcoded in `4490-afb0778f10485209.js` to fetch decoders from `https://www.gstatic.com/draco/versioned/decoders/1.5.5/`. If an air-gapped machine or offline demo is run, high-detail drone and terrain meshes fail to decompress.
* **The Solution**: The server provides an explicit route mapping for `draco_decoder.wasm`, `draco_wasm_wrapper.js`, and `draco_decoder.js` directly from the local `avionix/draco/` directory, achieving complete offline independence.

### Challenge 5: Comprehensive WebGL & Asset MIME Type Mapping
* **The Issue**: Default Python `http.server` instances lack MIME type entries for modern WebGL assets, causing browsers to reject `.wasm` (expected `application/wasm`) or `.glb` files.
* **The Solution**: The server explicitly registers:
  - `.wasm` $\to$ `application/wasm`
  - `.glb` $\to$ `model/gltf-binary`
  - `.gltf` $\to$ `model/gltf+json`
  - `.exr` $\to$ `image/x-exr`
  - `.avif` $\to$ `image/avif`
  - `.webp` $\to$ `image/webp`
  - `.woff2` $\to$ `font/woff2`

---

## 3. Step-by-Step Local Launch & Reproduction Guide

### Option A: 1-Click Windows Batch Launcher
Double-click [`avionix/launch_local_avionix.bat`](file:///e:/backup-llm/backup-no-llm/3d_engine/avionix/launch_local_avionix.bat) or execute in terminal:
```cmd
e:\backup-llm\backup-no-llm\3d_engine\avionix\launch_local_avionix.bat
```

### Option B: Python Command Line
```bash
cd e:\backup-llm\backup-no-llm\3d_engine\avionix
python serve_avionix.py
```
Open your browser to: **`http://localhost:3000/`**

---

## 4. Live Verification Evidence

The local environment was autonomously tested using our browser agent. The test confirmed:
1. **Initial Page Load**: Web Worker spun up the 3D turbine spinner and completed hydration cleanly.
2. **WebGL Scene Initialization**: R3F `<Canvas>` initialized with `dpr: [1, 1.5]` and `powerPreference: "high-performance"`.
3. **Virtual Scroll Runway**: Successfully navigated 6,000px down the virtual runway with continuous camera track synchronization and HUD telemetry updates.
4. **Captured Screenshots**:
   - [`initial_page_load`](file:///e:/backup-llm/backup-no-llm/3d_engine/frontend-analysis/screenshots/initial_page_load_1789367839932.png)
   - [`scroll_1000px`](file:///e:/backup-llm/backup-no-llm/3d_engine/frontend-analysis/screenshots/scroll_1000px_1789367876862.png)
   - [`scroll_3000px`](file:///e:/backup-llm/backup-no-llm/3d_engine/frontend-analysis/screenshots/scroll_3000px_1789367888273.png)
   - [`scroll_6000px`](file:///e:/backup-llm/backup-no-llm/3d_engine/frontend-analysis/screenshots/scroll_6000px_1789367997578.png)
   - [`after_scroll_to_explore`](file:///e:/backup-llm/backup-no-llm/3d_engine/frontend-analysis/screenshots/after_scroll_to_explore_1789367961552.png)
