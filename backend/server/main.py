"""
FastAPI Real-Time Telemetry & Control Server
Rotax 912 iS MALE UAV Digital Twin — Laptop Backend Server
DRDO / iDEX Problem Statement ID: 26054

Exposes REST APIs and 20 Hz WebSockets for:
- Mobile Phone / Vercel Web Controller
- Blender 3D Digital Twin Visualization Client
"""

import asyncio
import base64
import json
import logging
import sys
import uuid
from dataclasses import asdict
from typing import Set, List, Optional
from contextlib import asynccontextmanager

# Forces UTF-8 stdout/stderr regardless of the launching console's code page. On Windows,
# a plain cmd.exe (the default if this is run directly rather than through
# launch_backend_server.bat, which sets PYTHONUTF8=1 before this module is even imported)
# resolves sys.stdout to the legacy ANSI code page (cp1252 on this machine) instead of
# UTF-8. Any print()/log of a non-ASCII character anywhere in the process (a manual title,
# an AI-generated reply with an em dash or checkmark - confirmed to occur in practice)
# then raises an uncaught UnicodeEncodeError. A bare print() lets that exception propagate;
# critically, that includes the one inside LocalKnowledgeStore's document-loading loop,
# which runs synchronously during EngineStateService.__init__() inside FastAPI's startup
# lifespan - crashing the entire server, telemetry included, before it ever binds a socket.
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from backend.server.schemas import (
    UnifiedTelemetryState,
    ControlCommand,
    ServerHealthResponse,
    VoiceConverseResponse,
)
from backend.server.engine_service import EngineStateService
from backend.telemetry.replay_engine import ReplayEngine
from backend.agent.llm_engine import LocalLLMEngine
from backend.voice.stt_engine import LocalWhisperSTT
from backend.voice.tts_engine import LocalKokoroTTS
from backend.voice.thinking_stream import THINKING_STREAM


class AIAskRequest(BaseModel):
    query: str


class VoiceResetRequest(BaseModel):
    session_id: str


class MaintenanceSignoffRequest(BaseModel):
    inspector: str


class FlightCommandRequest(BaseModel):
    text: str

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DigitalTwinServer")

# Client connection pools
active_web_sockets: Set[WebSocket] = set()
active_blender_sockets: Set[WebSocket] = set()

# Historical mission replay (PRD F12) — stateless aside from its own internal per-mission
# caches, so a single process-lifetime instance is fine; no state_lock needed since it never
# touches EngineStateService's live sortie state.
_replay_engine = ReplayEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes the engine service and starts the async broadcast loop."""
    service = EngineStateService.get_instance()
    logger.info("[Server] Engine State Service initialized and running at 20 Hz.")
    
    # Start background broadcaster task
    broadcast_task = asyncio.create_task(broadcast_telemetry_loop(service))
    yield
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass
    logger.info("[Server] Shutdown complete.")


app = FastAPI(
    title="Rotax 912 iS MALE UAV Digital Twin Server",
    description="Authoritative real-time telemetry, physics, ML fault isolation, and diagnostic server (DRDO PS-26054)",
    version="2.0.0",
    lifespan=lifespan
)

# Enable permissive CORS for Vercel cloud and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def broadcast_telemetry_loop(service: EngineStateService):
    """Broadcasts unified 20 Hz state frames to all connected Web & Blender clients."""
    while True:
        try:
            state = service.get_latest_state()
            state_json = state.model_dump_json()

            # 1. Broadcast to Web/Mobile clients
            if active_web_sockets:
                dead_sockets = set()
                for ws in list(active_web_sockets):
                    try:
                        await ws.send_text(state_json)
                    except Exception:
                        dead_sockets.add(ws)
                active_web_sockets.difference_update(dead_sockets)

            # 2. Broadcast to Blender clients
            if active_blender_sockets:
                dead_blender = set()
                for ws in list(active_blender_sockets):
                    try:
                        await ws.send_text(state_json)
                    except Exception:
                        dead_blender.add(ws)
                active_blender_sockets.difference_update(dead_blender)

        except Exception as e:
            logger.error(f"[Broadcaster] Exception in broadcast loop: {e}")

        await asyncio.sleep(0.05)  # 20 Hz broadcast cycle, matching the engine's 20 Hz tick rate


# ──────────────────────────────────────────────────────────────────────────────
# REST Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "Rotax 912 iS MALE UAV Digital Twin Server",
        "drdo_ps_id": "26054",
        "status": "ONLINE",
        "endpoints": {
            "health": "/api/health",
            "state": "/api/state",
            "control": "/api/control",
            "ws_telemetry": "/ws/telemetry",
            "ws_blender": "/ws/blender",
            "ai_ask": "/api/ai/ask",
            "voice_converse": "/api/voice/converse",
            "voice_status": "/api/voice/status",
            "debrief": "/api/debrief",
            "cbm_fleet": "/api/cbm/fleet",
            "cbm_regions": "/api/cbm/regions",
            "cbm_maintenance": "/api/cbm/maintenance",
            "cbm_maintenance_signoff": "/api/cbm/maintenance/{action_id}/signoff",
            "copilot_flight_command": "/api/copilot/flight-command",
            "replay_manifests": "/api/replay/manifests",
            "replay_manifest": "/api/replay/{mission_id}/manifest",
            "replay_frame": "/api/replay/{mission_id}/frame?time_sec=..."
        }
    }


@app.get("/api/health", response_model=ServerHealthResponse)
def get_health():
    service = EngineStateService.get_instance()
    state = service.get_latest_state()
    return ServerHealthResponse(
        status="ONLINE",
        sortie_id=state.sortie_id,
        is_engine_running=state.is_engine_running,
        active_fault_id=state.active_commanded_fault_id,
        connected_web_clients=len(active_web_sockets),
        connected_blender_clients=len(active_blender_sockets),
        loop_frequency_hz=20.0
    )


@app.get("/api/state", response_model=UnifiedTelemetryState)
def get_current_state():
    """Returns the instant snapshot of the authoritative engine state."""
    service = EngineStateService.get_instance()
    return service.get_latest_state()


@app.post("/api/control")
def post_control_command(cmd: ControlCommand):
    """Executes an incoming engine/fault control command."""
    service = EngineStateService.get_instance()
    result = service.handle_command(cmd)
    if result.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@app.post("/api/debrief")
def export_cbm_debrief():
    """Triggers CBM post-flight debrief generation. Routed through handle_command() (same as
    the equivalent ControlCommand("EXPORT_DEBRIEF") path from the WebSocket/mobile controller)
    rather than calling service.export_debrief() directly, so this is covered by state_lock
    like every other mutation of the mission graph — export_debrief() itself is not safe to
    call unlocked, since it reads/mutates the same graph structures the 20 Hz tick writes to."""
    service = EngineStateService.get_instance()
    result = service.handle_command(ControlCommand(action="EXPORT_DEBRIEF"))
    return {"status": result.get("status", "SUCCESS"), "report_path": result.get("report_path")}


@app.get("/api/cbm/fleet")
def get_fleet_cbm_summary():
    """
    Fleet-wide Condition-Based Maintenance summary (doc01 §3 Pillar 4). Backed by
    MissionKnowledgeGraph's persist_path (data/graph_db/fleet_graph.json), so this reflects
    every sortie ever recorded — including sorties from before the current server process
    started — not just the currently-active one.
    """
    service = EngineStateService.get_instance()
    with service.state_lock:
        return service.graph.get_cbm_summary()


@app.get("/api/cbm/regions")
def get_region_comparison():
    """
    Cross-theater wear/anomaly comparison (e.g. Ladakh vs Thar Desert), aggregated across
    every persisted sortie in each region — grounds the PS-26054 "what-if environmental CBM"
    pillar in real cross-sortie history rather than a single in-memory session.
    """
    service = EngineStateService.get_instance()
    with service.state_lock:
        return service.graph.get_region_comparison()


@app.get("/api/replay/manifests")
def list_replay_manifests():
    """Lists every recorded sortie available to replay (PRD F12), newest first."""
    return {"manifests": _replay_engine.list_manifests()}


@app.get("/api/replay/{mission_id}/manifest")
def get_replay_manifest(mission_id: str):
    """Full manifest for one sortie, including event markers for the scrubber timeline."""
    manifest = _replay_engine.get_manifest(mission_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail=f"Unknown mission_id: {mission_id}")
    return manifest


@app.get("/api/replay/{mission_id}/frame")
def get_replay_frame(mission_id: str, time_sec: float):
    """Exact telemetry snapshot at-or-before `time_sec` for scrubbing/seeking."""
    frame = _replay_engine.get_frame(mission_id, time_sec)
    if frame is None:
        raise HTTPException(status_code=404, detail=f"No telemetry for mission_id: {mission_id}")
    return frame


@app.post("/api/copilot/flight-command")
def post_flight_command(body: FlightCommandRequest):
    """
    Natural-language tactical maneuver intent (PRD F10) — parses `text` into one of the six
    canonical flight-vector intents (final_tasks/01_DYNAMIC_TACTICAL_SIMULATION_AND_AUTOGCAS.md
    §5) and enqueues it for the running standalone_canyon_flight_app.py Blender process to pick
    up on its next command-poll tick. Does not touch EngineStateService/state_lock at all — the
    canyon flight sim is a separate process with its own FlightState, not the engine digital
    twin this server otherwise models, so this is intentionally the one endpoint in this file
    with no shared-state locking concern.
    """
    from backend.agent.flight_intent import handle_flight_command_text
    result = handle_flight_command_text(body.text)
    if result["status"] == "UNRECOGNIZED":
        raise HTTPException(status_code=422, detail=result["message"])
    return result


@app.get("/api/cbm/maintenance")
def list_maintenance_work_orders(status: Optional[str] = None):
    """Lists maintenance work orders (optionally filtered by ?status=OPEN or SIGNED_OFF),
    newest first — the ground-crew queue view backing sign-off."""
    service = EngineStateService.get_instance()
    with service.state_lock:
        return {"work_orders": service.graph.get_work_orders(status=status)}


@app.post("/api/cbm/maintenance/{action_id}/signoff")
def signoff_maintenance_action(action_id: str, body: MaintenanceSignoffRequest):
    """Closes a maintenance work order. A work order can only ever be signed off once —
    re-signing an already-closed order returns 409, not a silent no-op, so a ground crew
    can't accidentally paper over a real double-approval process error."""
    service = EngineStateService.get_instance()
    with service.state_lock:
        try:
            node = service.graph.sign_off_action(action_id, inspector=body.inspector)
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        if node is None:
            raise HTTPException(status_code=404, detail=f"Unknown maintenance action_id: {action_id}")
        return asdict(node)


# ──────────────────────────────────────────────────────────────────────────────
# Local AI (pluggable LLM RAG reasoning layer -- see backend/agent/llm_engine.py) Endpoints
#
# All three routes are blocking/GPU-bound and are offloaded via asyncio.to_thread
# so they never stall this process's event loop — which also runs
# broadcast_telemetry_loop() and would otherwise freeze 20 Hz telemetry for every
# connected client for the entire duration of an LLM call (several seconds).
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/ai/status")
def get_ai_status():
    """Reports whether the configured local LLM provider (ANUMAAN_LLM_PROVIDER; DISABLED
    by default) is loaded, loading, or unavailable."""
    return LocalLLMEngine.get_instance().status_payload()


@app.post("/api/ai/warmup")
async def warmup_ai_engine():
    """Explicitly triggers the (slow, one-time) LLM load, instead of waiting for a fault. A
    no-op if no provider is configured (the default)."""
    engine = LocalLLMEngine.get_instance()
    ok = await asyncio.to_thread(engine.ensure_loaded)
    return {"status": "SUCCESS" if ok else "ERROR", **engine.status_payload()}


@app.post("/api/ai/ask")
async def ask_ai_copilot(req: AIAskRequest):
    """Free-text mission copilot query (guardrails + RAG retrieval + optional LLM synthesis)."""
    service = EngineStateService.get_instance()
    state = service.get_latest_state()
    result = await asyncio.to_thread(
        service.copilot.ask,
        req.query,
        state.model_dump(),
        state.analytics.diagnosed_fault_id or None,
    )
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Voice Interface Endpoints (STT -> Mission Copilot -> TTS)
#
# Same offload rationale as the /api/ai/* routes above: whisper.cpp transcription,
# LLM generation, and Kokoro synthesis are all blocking, CPU/GPU-bound calls that
# would otherwise stall broadcast_telemetry_loop() for every connected client for
# the duration of a voice turn (can be several seconds end-to-end).
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/api/voice/status")
def get_voice_status():
    """Reports whether the local STT (whisper.cpp), TTS (Kokoro), and LLM engines
    are loaded. The LLM is included here even though it's also covered by /api/ai/status
    because a voice turn is unusable — falls back to templated answers — without it."""
    return {
        "stt": LocalWhisperSTT.get_instance().status_payload(),
        "tts": LocalKokoroTTS.get_instance().status_payload(),
        "llm": LocalLLMEngine.get_instance().status_payload(),
    }


@app.post("/api/voice/warmup")
async def warmup_voice_engines():
    """Explicitly triggers the (slow, one-time) STT + TTS + LLM model loads. The LLM is usually
    already loading in the background since server startup (see EngineStateService.__init__),
    so this mostly just waits on it rather than starting it cold."""
    stt = LocalWhisperSTT.get_instance()
    tts = LocalKokoroTTS.get_instance()
    llm = LocalLLMEngine.get_instance()
    stt_ok, tts_ok, llm_ok = await asyncio.gather(
        asyncio.to_thread(stt.ensure_loaded),
        asyncio.to_thread(tts.ensure_loaded),
        asyncio.to_thread(llm.ensure_loaded),
    )
    all_ok = stt_ok and tts_ok and llm_ok
    any_ok = stt_ok or tts_ok or llm_ok
    return {
        "status": "SUCCESS" if all_ok else "PARTIAL" if any_ok else "ERROR",
        "stt": stt.status_payload(),
        "tts": tts.status_payload(),
        "llm": llm.status_payload(),
    }


@app.post("/api/voice/reset")
def reset_voice_session(req: VoiceResetRequest):
    """Clears a conversation session's dialogue history (e.g. operator hit 'clear chat')."""
    service = EngineStateService.get_instance()
    service.copilot.voice_conversations.reset(req.session_id)
    return {"status": "SUCCESS", "session_id": req.session_id}


@app.post("/api/voice/converse", response_model=VoiceConverseResponse)
async def voice_converse(
    audio: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    voice: Optional[str] = Form(None),
):
    """
    One full spoken turn: operator audio in, spoken Mission Copilot reply out.
    1. STT (whisper.cpp) transcribes the uploaded clip (any container ffmpeg can demux).
    2. The transcript is routed through the existing Mission Copilot RAG/diagnostic
       pipeline in conversational voice mode (guardrails, retrieval, deterministic
       grounding, multi-turn history) — same physics/ML ground truth as the text chat.
    3. TTS (Kokoro) synthesizes the reply to speech.
    """
    session_id = session_id or str(uuid.uuid4())
    stt = LocalWhisperSTT.get_instance()
    tts = LocalKokoroTTS.get_instance()
    service = EngineStateService.get_instance()

    audio_bytes = await audio.read()

    try:
        transcript = await asyncio.to_thread(stt.transcribe, audio_bytes)
    except Exception as e:
        logger.warning(f"[Voice] STT failed: {e}")
        return VoiceConverseResponse(
            status="ERROR", session_id=session_id,
            response="I couldn't process that audio. The speech recognition engine reported an error.",
        )

    # Belt-and-braces against a silent/noise-only clip: LocalWhisperSTT.transcribe() already
    # strips whisper's non-speech markers and returns "" for them, but this must never reach
    # ask_voice() — a phantom turn gets answered, spoken, and written into the session's
    # dialogue history, where it skews every following turn. Returning here happens before
    # ask_voice(), so nothing is recorded.
    if not transcript or len(transcript.strip()) < 2:
        return VoiceConverseResponse(
            status="EMPTY_AUDIO", session_id=session_id,
            response="I didn't catch that. Could you try again?",
        )

    state = service.get_latest_state()
    THINKING_STREAM.start(session_id)
    try:
        result = await asyncio.to_thread(
            service.copilot.ask_voice,
            transcript,
            session_id,
            state.model_dump(),
            state.analytics.diagnosed_fault_id or None,
            lambda delta: THINKING_STREAM.append(session_id, delta),
        )
    finally:
        THINKING_STREAM.finish(session_id)

    audio_base64 = None
    try:
        reply_audio = await asyncio.to_thread(tts.synthesize, result["response"], voice)
        audio_base64 = base64.b64encode(reply_audio).decode("ascii")
    except Exception as e:
        logger.warning(f"[Voice] TTS failed: {e}")

    return VoiceConverseResponse(
        status=result["status"],
        session_id=session_id,
        transcript=transcript,
        response=result["response"],
        audio_base64=audio_base64,
        citations=result.get("citations", []),
        active_fault=result.get("active_fault"),
    )


@app.get("/api/voice/thinking/{session_id}")
def get_voice_thinking(session_id: str):
    """
    Live preview of the reply currently being generated for a session's in-flight
    /api/voice/converse turn — polled by the frontend (every few hundred ms while the mic
    is in "processing" state) to show the answer being composed, instead of a silent wait.
    `done` is true once generation for that turn has finished (or if there was never an
    in-flight turn for this session_id at all — an unknown id just reads as already-done).
    """
    text, done = THINKING_STREAM.read(session_id)
    return {"text": text, "done": done}


# ──────────────────────────────────────────────────────────────────────────────
# WebSocket Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """
    Bidirectional WebSocket for Mobile Phone / Vercel Web Controller.
    Receives 20 Hz state stream; accepts incoming control commands as JSON.
    """
    await websocket.accept()
    active_web_sockets.add(websocket)
    logger.info(f"[WebSocket] Mobile/Web client connected. Total web clients: {len(active_web_sockets)}")
    
    service = EngineStateService.get_instance()
    # Send immediate initial state
    await websocket.send_text(service.get_latest_state().model_dump_json())

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                cmd = ControlCommand(**msg)
                res = service.handle_command(cmd)
                await websocket.send_text(json.dumps({"type": "COMMAND_RESULT", **res}))
            except Exception as e:
                await websocket.send_text(json.dumps({"type": "ERROR", "message": str(e)}))
    except WebSocketDisconnect:
        active_web_sockets.discard(websocket)
        logger.info(f"[WebSocket] Web client disconnected. Remaining: {len(active_web_sockets)}")
    except Exception as e:
        active_web_sockets.discard(websocket)
        logger.warning(f"[WebSocket] Client connection error: {e}")


@app.websocket("/ws/blender")
async def websocket_blender_endpoint(websocket: WebSocket):
    """
    High-speed WebSocket endpoint for Blender Standalone 3D Client.
    Pushes continuous 20 Hz state stream.
    """
    await websocket.accept()
    active_blender_sockets.add(websocket)
    logger.info(f"[WebSocket] Blender client connected! Total Blender clients: {len(active_blender_sockets)}")

    service = EngineStateService.get_instance()
    await websocket.send_text(service.get_latest_state().model_dump_json())

    try:
        while True:
            # Blender might send heartbeat or control requests
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if "action" in msg:
                    cmd = ControlCommand(**msg)
                    res = service.handle_command(cmd)
                    await websocket.send_text(json.dumps({"type": "COMMAND_RESULT", **res}))
            except Exception:
                pass
    except WebSocketDisconnect:
        active_blender_sockets.discard(websocket)
        logger.info(f"[WebSocket] Blender client disconnected. Remaining: {len(active_blender_sockets)}")
    except Exception as e:
        active_blender_sockets.discard(websocket)
        logger.warning(f"[WebSocket] Blender connection error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
