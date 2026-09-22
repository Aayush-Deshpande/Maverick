# ⏪ Track 02: Historical Mission Replay & Scrubber Implementation Plan
**DRDO / iDEX Problem Statement ID: 26054**  
*Flight Data Recorder (FDR) Time-Series Player, Web GCS Timeline Scrubber & 3D Twin Synchronization*

---

## 📌 1. Module Overview & Goals

This module builds the **Flight Data Recorder (FDR) Replay Engine**, allowing operators, flight safety officers, and maintenance crews to load past UAV sorties, scrub through the flight timeline at variable speeds, and re-watch gauge movements, 3D camera sweeps, and AI diagnostic reasoning as they unfolded chronologically.

### Target Files & Scope
* **Frontend Scrubber Component:** `frontend/src/components/MissionReplayScrubber.tsx`
* **Frontend State Hook:** `frontend/src/hooks/useMissionReplay.ts`
* **Dashboard Integration:** `frontend/src/App.tsx`
* **Backend Replay Endpoint:** `backend/server/main.py` & `backend/server/engine_service.py`
* **Telemetry Log Files:** `data/telemetry/*.csv`, `data/telemetry/*.parquet`

---

## 🏗️ 2. Detailed Technical Architecture & Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                   HISTORICAL MISSION REPLAY DATA FLOW                  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│   [Historical Sortie Archive] (data/telemetry/sortie_ladakh_042.csv)   │
│                                │                                       │
│                                ▼                                       │
│   [Backend Replay Service / FastAPI Endpoint]                          │
│   • Parses time series at 10-50 Hz                                     │
│   • Streams frames sequentially or seeks to requested timestamp        │
│                                │                                       │
│                                ▼                                       │
│   [React Web GCS Replay Hook & Scrubber Component]                    │
│   • Interactive Timeline Slider (T+00:00 to T+18:00)                   │
│   • VCR Controls: Play, Pause, Speed (1x, 5x, 10x)                    │
│   • Event Markers on Track (Amber/Red dots at Anomaly Epochs)          │
│                                │                                       │
│                 ┌──────────────┴──────────────┐                        │
│                 ▼                             ▼                        │
│   [Live Dials & Gauges Update]   [3D Twin Camera Sweeps & Highlights] │
│   • RPM, CHT, OilP, EGT update   • At T+04:16:30 -> Camera sweeps to   │
│   • AI Diagnostic card updates     Cylinder #2 and pulses red          │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 3. Data Structures & Schema Design

### 3.1 Replay Frame Schema (`ReplayFramePayload`)
```typescript
export interface ReplayEventMarker {
  timestamp_epoch: number;
  mission_elapsed_sec: number;
  event_type: 'ANOMALY_ONSET' | 'PILOT_MITIGATION' | 'MAINTENANCE_ORDER';
  fault_id: number;
  fault_name: string;
  severity: 'NOMINAL' | 'ADVISORY' | 'WARNING' | 'CRITICAL';
  description: string;
}

export interface ReplayManifest {
  sortie_id: string;
  uav_tail_number: string;
  theater_region: 'LADAKH' | 'THAR_DESERT' | 'STANDARD';
  total_duration_sec: number;
  sample_rate_hz: number;
  total_frames: number;
  event_markers: ReplayEventMarker[];
}
```

---

## 🖥️ 4. Frontend Component Design (`MissionReplayScrubber.tsx`)

### UI Layout & Controls
1. **Sortie Selector Dropdown:** Pick past mission (e.g. `SORTIE-2026-LADAKH-042`).
2. **Main Timeline Bar:**
   * High-contrast scrub track with elapsed time / total time (e.g. `04:16:30 / 18:30:00`).
   * Color-coded event markers positioned at exact fractional timestamps:
     * Red pip at `04:16:30` (Cylinder #2 CHT Overheat onset).
     * Blue pip at `05:03:00` (Pilot throttle reduction & fuel enrichment).
3. **Playback Controls:**
   * `[⏪ -10s]` Step back 10 seconds.
   * `[▶ Play / ⏸ Pause]` Toggle continuous playback.
   * `[⏩ +10s]` Step forward 10 seconds.
   * Speed selector buttons: `[ 1x ]`, `[ 2x ]`, `[ 5x ]`, `[ 10x ]`.
4. **Synchronized State Push:**
   * When seeking, all dashboard gauges ($CHT_1–4, EGT_1–4, RPM, OilP, MAP$) update instantaneously.
   * The 3D viewport receives camera target commands via WebSocket (`target_part: "Covers_Theme_M_PlasticTheme_0"`).

---

## ⚙️ 5. Backend Replay Service (`backend/telemetry/replay_engine.py`)

### Responsibilities:
1. **Log Reader:** Ingests CSV or Parquet files from `data/telemetry/`.
2. **Fast Indexed Seeker:** Pre-indexes timestamp offsets for O(1) jump-to-time queries.
3. **REST & WebSocket Endpoints:**
   * `GET /api/replay/manifests` -> Returns list of recorded sorties.
   * `GET /api/replay/{sortie_id}/frame?time_sec=15390` -> Returns exact telemetry snapshot.
   * `POST /api/replay/control` -> Sets server playback mode (PLAY, PAUSE, SEEK, SPEED).

---

## 🛠️ 6. Step-by-Step Implementation Steps

1. **Step 1:** Create `backend/telemetry/replay_engine.py` to index and read time-series flight logs.
2. **Step 2:** Expose `/api/replay` endpoints in `backend/server/main.py`.
3. **Step 3:** Build `frontend/src/hooks/useMissionReplay.ts` with playback timer and state caching.
4. **Step 4:** Build `frontend/src/components/MissionReplayScrubber.tsx` with high-density timeline markers and VCR buttons.
5. **Step 5:** Integrate the scrubber into `frontend/src/App.tsx` (toggleable between LIVE and REPLAY modes).
6. **Step 6:** Hook replay timestamp events to 3D Blender viewport camera sweeps.
7. **Step 7:** Verify smooth scrubbing at 1x, 5x, and 10x speeds with zero frame drops.
