import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Mic,
  Loader2,
  Volume2,
  Trash2,
  Radio,
  AlertTriangle,
  Sparkles,
  User,
  Bot,
  Power,
  Ear,
  EarOff,
} from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';
import { AerospaceMarkdown } from './AerospaceMarkdown';

interface VoiceCopilotProps {
  state: UnifiedTelemetryState;
  serverUrl?: string;
}

type MicState =
  | 'idle'
  | 'capturing'
  | 'processing'
  | 'speaking'
  | 'denied'
  | 'unsupported';

interface VoiceMessage {
  role: 'user' | 'assistant';
  text: string;
  citations?: string[];
  ts: number;
}

interface EngineStatusPayload {
  status: 'DISABLED' | 'NOT_LOADED' | 'LOADING' | 'READY' | 'ERROR';
  error?: string | null;
  provider?: string;
}

const SESSION_STORAGE_KEY = 'rotax_voice_session_id';

// Continuous listening tuning. Kept as named constants (rather than inline magic numbers)
// because these are the knobs to turn if end-of-speech detection feels too twitchy or cuts
// people off — see captureCommandWithVad() and the continuous loop below.
const VAD_POLL_MS = 100; // how often we sample mic RMS while capturing a command
const VAD_SILENCE_RMS = 0.02; // below this = "silence" for VAD purposes
const VAD_MIN_SPEECH_MS = 400; // ignore silence until at least this much real speech happened
const VAD_SILENCE_STOP_MS = 1100; // this much continuous silence after speech = end of command
const VAD_MAX_CAPTURE_MS = 15000; // hard cap so a stuck VAD can't record forever

// Barge-in tuning: while the reply is speaking (continuous mode only), we keep monitoring the
// mic so the operator can talk over it. Threshold is higher and the confirm window shorter than
// the normal VAD above — higher because the reply audio itself can bleed into the mic if the
// browser's echo cancellation doesn't fully cancel it (worse on laptop speakers than headphones),
// shorter because we want the interruption to feel instant rather than waiting out a full
// "is this really a command" window.
const BARGE_IN_POLL_MS = 60;
const BARGE_IN_RMS = 0.05;
const BARGE_IN_CONFIRM_MS = 180;

function getOrCreateSessionId(): string {
  try {
    const existing = localStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;
    const fresh = crypto.randomUUID();
    localStorage.setItem(SESSION_STORAGE_KEY, fresh);
    return fresh;
  } catch {
    return `session-${Date.now()}`;
  }
}

function pickRecorderMimeType(): string | undefined {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
  for (const c of candidates) {
    if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported?.(c)) return c;
  }
  return undefined;
}

/**
 * Records a command with voice-activity-detection-based end-of-speech: starts capturing,
 * waits for real speech to begin, then stops automatically once the operator has gone quiet
 * for VAD_SILENCE_STOP_MS. `shouldAbort` is polled so the caller can cancel mid-capture (e.g.
 * continuous mode got switched off).
 */
function captureCommandWithVad(stream: MediaStream, shouldAbort: () => boolean): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const mimeType = pickRecorderMimeType();
    let recorder: MediaRecorder;
    try {
      recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    } catch (e) {
      reject(e);
      return;
    }
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };

    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    const audioCtx = new AudioCtx();
    const source = audioCtx.createMediaStreamSource(stream);
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 2048;
    source.connect(analyser);
    const dataArray = new Uint8Array(analyser.fftSize);

    let speechAccumulatedMs = 0;
    let silenceStartedAt: number | null = null;
    const startedAt = Date.now();
    let finished = false;

    const cleanupAndResolve = () => {
      if (finished) return;
      finished = true;
      clearInterval(pollHandle);
      try {
        analyser.disconnect();
        source.disconnect();
        audioCtx.close();
      } catch {
        // best-effort teardown
      }
      if (recorder.state !== 'inactive') {
        recorder.stop();
      }
    };

    recorder.onstop = () => resolve(new Blob(chunks, { type: mimeType || 'audio/webm' }));
    recorder.onerror = (e) => {
      cleanupAndResolve();
      reject(e);
    };

    const pollHandle = setInterval(() => {
      if (shouldAbort()) {
        cleanupAndResolve();
        return;
      }
      const elapsed = Date.now() - startedAt;
      if (elapsed > VAD_MAX_CAPTURE_MS) {
        cleanupAndResolve();
        return;
      }

      analyser.getByteTimeDomainData(dataArray);
      let sumSquares = 0;
      for (let i = 0; i < dataArray.length; i++) {
        const norm = (dataArray[i] - 128) / 128;
        sumSquares += norm * norm;
      }
      const rms = Math.sqrt(sumSquares / dataArray.length);

      if (rms > VAD_SILENCE_RMS) {
        speechAccumulatedMs += VAD_POLL_MS;
        silenceStartedAt = null;
      } else if (speechAccumulatedMs >= VAD_MIN_SPEECH_MS) {
        if (silenceStartedAt === null) silenceStartedAt = Date.now();
        else if (Date.now() - silenceStartedAt > VAD_SILENCE_STOP_MS) {
          cleanupAndResolve();
        }
      }
    }, VAD_POLL_MS);

    recorder.start();
  });
}

/** Short single-tone cue synthesized on the fly — plays when continuous mode goes back to
 * listening after a reply, so the operator knows it's their turn without watching the screen. */
function playReadyChime() {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    const ctx = new AudioCtx();
    const now = ctx.currentTime;
    [880].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0, now + i * 0.11);
      gain.gain.linearRampToValueAtTime(0.15, now + i * 0.11 + 0.02);
      gain.gain.linearRampToValueAtTime(0, now + i * 0.11 + 0.1);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now + i * 0.11);
      osc.stop(now + i * 0.11 + 0.12);
    });
    setTimeout(() => ctx.close(), 400);
  } catch {
    // Chime is a nicety, never let it break the actual voice flow.
  }
}

export const VoiceCopilot: React.FC<VoiceCopilotProps> = ({
  state,
  serverUrl = 'http://127.0.0.1:8000',
}) => {
  const [micState, setMicState] = useState<MicState>('idle');
  const [continuousMode, setContinuousMode] = useState(false);
  const [messages, setMessages] = useState<VoiceMessage[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [sttStatus, setSttStatus] = useState<EngineStatusPayload | null>(null);
  const [ttsStatus, setTtsStatus] = useState<EngineStatusPayload | null>(null);
  const [llmStatus, setLlmStatus] = useState<EngineStatusPayload | null>(null);
  const [isWarmingUp, setIsWarmingUp] = useState(false);
  const [thinkingText, setThinkingText] = useState('');

  const sessionIdRef = useRef<string>(getOrCreateSessionId());
  const continuousModeRef = useRef(false); // mirrors state, read inside the async continuous loop
  const manualInterruptRef = useRef(false); // tap-to-interrupt fallback, see handleMicClick
  const persistentStreamRef = useRef<MediaStream | null>(null);
  const singleShotRecorderRef = useRef<MediaRecorder | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const refreshEngineStatus = useCallback(async () => {
    try {
      const res = await fetch(`${serverUrl}/api/voice/status`, {
        headers: { 'ngrok-skip-browser-warning': '69420' },
      });
      if (res.ok) {
        const data = await res.json();
        setSttStatus(data.stt);
        setTtsStatus(data.tts);
        setLlmStatus(data.llm);
      }
    } catch {
      // Non-fatal: status badges just stay unknown until the next successful poll.
    }
  }, [serverUrl]);

  useEffect(() => {
    refreshEngineStatus();
    // Keeps polling for as long as this tab is mounted (App.tsx only mounts VoiceCopilot
    // while the Voice Copilot tab is active, so this naturally stops when the operator
    // navigates away). Without this, opening the tab while Whisper/Kokoro/LLM are still
    // loading in the background (the normal case right after server startup) left the
    // STT/TTS/LLM badges frozen on whatever the single initial fetch read - LOADING
    // forever, with no visible sign anything was still happening, until the operator
    // either clicked "Warm up" or reloaded the page.
    const intervalId = window.setInterval(refreshEngineStatus, 2000);
    return () => window.clearInterval(intervalId);
  }, [refreshEngineStatus]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const handleWarmup = async () => {
    setIsWarmingUp(true);
    try {
      const res = await fetch(`${serverUrl}/api/voice/warmup`, {
        method: 'POST',
        headers: { 'ngrok-skip-browser-warning': '69420' },
      });
      if (res.ok) {
        const data = await res.json();
        setSttStatus(data.stt);
        setTtsStatus(data.tts);
        setLlmStatus(data.llm);
      }
    } catch (err: any) {
      setErrorMsg(`Warmup failed: ${err?.message || err}`);
    } finally {
      setIsWarmingUp(false);
    }
  };

  /**
   * Plays the reply audio. In continuous mode, simultaneously monitors the still-open mic
   * stream for the operator talking over it — if sustained speech-level audio is detected,
   * playback is stopped immediately and this resolves 'interrupted' instead of 'ended', so the
   * continuous loop can skip straight back into capturing rather than waiting out the reply.
   * `stream` is null in manual push-to-talk mode (no persistent mic to monitor), so playback
   * there is always a plain, uninterruptible listen-to-the-end.
   */
  const playReplyAudioInterruptible = (
    audioBase64: string,
    stream: MediaStream | null
  ): Promise<'ended' | 'interrupted'> => {
    return new Promise((resolve) => {
      try {
        const binary = atob(audioBase64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const blob = new Blob([bytes], { type: 'audio/wav' });
        const url = URL.createObjectURL(blob);

        if (!audioElRef.current) {
          audioElRef.current = new Audio();
        }
        const audioEl = audioElRef.current;
        audioEl.src = url;
        setMicState('speaking');

        let settled = false;
        let pollHandle: number | null = null;
        let audioCtx: AudioContext | null = null;
        let analyser: AnalyserNode | null = null;
        let source: MediaStreamAudioSourceNode | null = null;

        const cleanup = () => {
          URL.revokeObjectURL(url);
          if (pollHandle !== null) clearInterval(pollHandle);
          try {
            source?.disconnect();
            analyser?.disconnect();
            audioCtx?.close();
          } catch {
            // best-effort teardown
          }
        };

        const finish = (result: 'ended' | 'interrupted') => {
          if (settled) return;
          settled = true;
          cleanup();
          resolve(result);
        };

        audioEl.onended = () => finish('ended');
        audioEl.onerror = () => finish('ended');

        if (stream && continuousModeRef.current) {
          try {
            const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
            audioCtx = new AudioCtx();
            source = audioCtx.createMediaStreamSource(stream);
            analyser = audioCtx.createAnalyser();
            analyser.fftSize = 2048;
            source.connect(analyser);
            const dataArray = new Uint8Array(analyser.fftSize);
            let speechMs = 0;

            pollHandle = window.setInterval(() => {
              if (!continuousModeRef.current || manualInterruptRef.current) {
                manualInterruptRef.current = false;
                audioEl.pause();
                finish('interrupted');
                return;
              }
              analyser!.getByteTimeDomainData(dataArray);
              let sumSquares = 0;
              for (let i = 0; i < dataArray.length; i++) {
                const norm = (dataArray[i] - 128) / 128;
                sumSquares += norm * norm;
              }
              const rms = Math.sqrt(sumSquares / dataArray.length);
              if (rms > BARGE_IN_RMS) {
                speechMs += BARGE_IN_POLL_MS;
                if (speechMs >= BARGE_IN_CONFIRM_MS) {
                  audioEl.pause();
                  finish('interrupted');
                }
              } else {
                speechMs = 0;
              }
            }, BARGE_IN_POLL_MS);
          } catch {
            // Barge-in monitoring is a nicety; if it fails to set up, playback just runs normally.
          }
        }

        audioEl.play().catch(() => finish('ended'));
      } catch {
        resolve('ended');
      }
    });
  };

  /** Polls the backend's live "thinking" preview for the current session while a turn is
   * generating, so the operator sees the reply being composed instead of a silent wait —
   * the same idea as a coding CLI agent streaming its output. Started/stopped around the
   * /api/voice/converse call in sendTurn(); harmless no-op once that call resolves. */
  const startThinkingPoll = (): number => {
    return window.setInterval(async () => {
      try {
        const res = await fetch(`${serverUrl}/api/voice/thinking/${sessionIdRef.current}`, {
          headers: { 'ngrok-skip-browser-warning': '69420' },
        });
        if (res.ok) {
          const data = await res.json();
          setThinkingText(data.text || '');
        }
      } catch {
        // Best-effort preview — a missed poll just means a stale preview for one tick.
      }
    }, 300);
  };

  /** Full turn: send captured command audio, show transcript/reply, speak it. Resolves with
   * how playback ended so the continuous loop can react (e.g. skip the chime on a barge-in). */
  const sendTurn = async (blob: Blob): Promise<'ended' | 'interrupted' | 'no_audio' | 'error'> => {
    setMicState('processing');
    setErrorMsg(null);
    setThinkingText('');
    const thinkingPollHandle = startThinkingPoll();
    // Without a timeout, a stalled turn (Ollama busy/crashed, Kokoro hung) leaves the mic
    // stuck on "THINKING..." forever with no way to recover except reloading the page - the
    // fetch never rejects on its own. 60s (vs. 45s for the text-chat path in DiagnosticCard)
    // since a voice turn stacks STT + RAG + LLM + TTS sequentially, not just the LLM call.
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);
    try {
      const form = new FormData();
      form.append('audio', blob, 'operator_turn.webm');
      form.append('session_id', sessionIdRef.current);

      const res = await fetch(`${serverUrl}/api/voice/converse`, {
        method: 'POST',
        headers: { 'ngrok-skip-browser-warning': '69420' },
        body: form,
        signal: controller.signal,
      });

      if (!res.ok) {
        setErrorMsg(`Server returned status ${res.status}`);
        return 'error';
      }

      const data = await res.json();
      const now = Date.now();

      if (data.transcript) {
        setMessages((prev) => [...prev, { role: 'user', text: data.transcript, ts: now }]);
      }
      if (data.response) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', text: data.response, citations: data.citations || [], ts: now + 1 },
        ]);
      }

      if (data.audio_base64) {
        return await playReplyAudioInterruptible(data.audio_base64, persistentStreamRef.current);
      }
      return 'no_audio';
    } catch (err: any) {
      const message = err?.name === 'AbortError' ? 'Request timed out after 60s — the voice pipeline may be overloaded or unreachable.' : (err?.message || err);
      setErrorMsg(`Connection error: ${message}`);
      return 'error';
    } finally {
      clearTimeout(timeoutId);
      clearInterval(thinkingPollHandle);
      setThinkingText('');
    }
  };

  // ── Continuous listen/respond loop (no wake word) ─────────────────────────────────────
  // While continuous mode is on: capture whatever the operator says (VAD-bounded), send it,
  // speak the reply, chime, and immediately start listening again — repeat until they flip
  // the toggle off. Turning it off drops back to explicit push-to-talk (see handleMicClick).
  const runContinuousLoop = useCallback(async () => {
    while (continuousModeRef.current) {
      const stream = persistentStreamRef.current;
      if (!stream) break;

      setMicState('capturing');
      let commandBlob: Blob;
      try {
        commandBlob = await captureCommandWithVad(stream, () => !continuousModeRef.current);
      } catch {
        break;
      }
      if (!continuousModeRef.current) break;

      if (commandBlob.size > 800) {
        const outcome = await sendTurn(commandBlob);
        if (!continuousModeRef.current) break;
        if (outcome === 'interrupted') {
          // The operator started talking over the reply — skip the chime/pause and go
          // straight back into capturing so we don't miss the rest of what they're saying.
          continue;
        }
      }
      if (!continuousModeRef.current) break;

      playReadyChime();
      // Brief pause after the chime so it doesn't sound like it's still mid-word before the
      // next capture window opens.
      await new Promise((r) => setTimeout(r, 250));
    }
    setMicState('idle');
  }, [serverUrl]);

  const enableContinuousMode = async () => {
    setErrorMsg(null);
    if (!voiceReady) {
      setErrorMsg('Voice engines are still warming up - please wait for STT and TTS to show READY.');
      return;
    }
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setMicState('unsupported');
      return;
    }
    try {
      // Echo cancellation matters more here than in manual mode: the mic stays open and
      // monitored (for barge-in) while the reply plays out of the same device's speakers, so
      // without it the assistant's own voice can bleed back in and look like an interruption.
      // Deliberately NOT requesting noiseSuppression/autoGainControl: AGC continuously
      // renormalizes the mic level toward a target loudness, which fights the fixed-RMS-
      // threshold VAD used everywhere in this file — silence gets boosted until it reads as
      // "speech," so captureCommandWithVad() never sees a quiet enough window to stop on, and
      // barge-in's own threshold gets thrown off the same way. Reported directly: recording
      // would start but never auto-stop, and speaking over a reply didn't interrupt it.
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true },
      });
      stream.getAudioTracks()[0].onended = () => {
        // Permission revoked or device unplugged mid-session — fall back cleanly.
        disableContinuousMode();
      };
      persistentStreamRef.current = stream;
      continuousModeRef.current = true;
      setContinuousMode(true);
      runContinuousLoop();
    } catch {
      setMicState('denied');
      setErrorMsg('Microphone access denied. Grant microphone permission to enable continuous mode.');
    }
  };

  const disableContinuousMode = () => {
    continuousModeRef.current = false;
    setContinuousMode(false);
    persistentStreamRef.current?.getTracks().forEach((t) => t.stop());
    persistentStreamRef.current = null;
    audioElRef.current?.pause();
    setMicState('idle');
  };

  const toggleContinuousMode = () => {
    if (continuousMode) disableContinuousMode();
    else enableContinuousMode();
  };

  // ── Manual push-to-talk (works independently of continuous mode) ─────────────────────
  const startManualRecording = async () => {
    setErrorMsg(null);
    if (!voiceReady) {
      setErrorMsg('Voice engines are still warming up - please wait for STT and TTS to show READY.');
      return;
    }
    if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setMicState('unsupported');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = pickRecorderMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      singleShotRecorderRef.current = recorder;
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunks, { type: mimeType || 'audio/webm' });
        if (blob.size > 500) sendTurn(blob).then(() => setMicState('idle'));
        else setMicState('idle');
      };

      recorder.start();
      setMicState('capturing');
    } catch {
      setMicState('denied');
      setErrorMsg('Microphone access denied.');
    }
  };

  const handleMicClick = () => {
    if (continuousMode) {
      if (micState === 'speaking') {
        // Manual barge-in fallback: the automatic RMS-based detector in
        // playReplyAudioInterruptible() can miss real speech depending on mic/speaker
        // acoustics, so tapping the mic while it's talking always works as a guaranteed
        // way to cut in — interrupts the reply and goes straight back to listening,
        // without fully stopping continuous mode.
        manualInterruptRef.current = true;
        return;
      }
      // Any other state: acts as an emergency stop for the whole continuous-listening flow.
      disableContinuousMode();
      return;
    }
    if (micState === 'idle' || micState === 'denied' || micState === 'unsupported') {
      startManualRecording();
    } else if (micState === 'capturing') {
      singleShotRecorderRef.current?.stop();
    } else if (micState === 'speaking') {
      audioElRef.current?.pause();
      setMicState('idle');
    }
  };

  useEffect(() => {
    return () => {
      continuousModeRef.current = false;
      persistentStreamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const handleClearConversation = async () => {
    setMessages([]);
    try {
      await fetch(`${serverUrl}/api/voice/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': '69420' },
        body: JSON.stringify({ session_id: sessionIdRef.current }),
      });
    } catch {
      // Local transcript is already cleared; server-side history will just be re-primed next turn.
    }
  };

  const engineReady = sttStatus?.status === 'READY' && ttsStatus?.status === 'READY' && llmStatus?.status === 'READY';
  const engineLoading = sttStatus?.status === 'LOADING' || ttsStatus?.status === 'LOADING' || llmStatus?.status === 'LOADING';
  // STT and TTS are hard requirements for a voice turn - unlike the LLM (which fails soft into
  // a fast deterministic fallback inside ask_voice() if Ollama is unavailable), there is no
  // fallback path if whisper.cpp or Kokoro aren't loaded yet. Gating only on these two (not
  // requiring LLM===READY) lets voice work immediately via the grounded fallback when Ollama
  // simply isn't running, while still blocking the one scenario that actually hangs: starting
  // a turn before STT/TTS have finished their one-time cold load. Confirmed by direct repro -
  // Kokoro's first load alone measured 24.4s on this project's own dev machine, stacking with
  // whatever else is still warming up inline into the request instead of finishing in the
  // background first, which is exactly what produced the ~40-60s "request timed out" error
  // this gate exists to prevent.
  const voiceReady = sttStatus?.status === 'READY' && ttsStatus?.status === 'READY';

  const micLabel =
    micState === 'capturing'
      ? continuousMode
        ? 'LISTENING — SPEAK ANYTIME'
        : 'RECORDING — TAP TO STOP'
      : micState === 'processing'
      ? 'THINKING...'
      : micState === 'speaking'
      ? continuousMode
        ? 'SPEAKING — JUST TALK TO INTERRUPT'
        : 'SPEAKING — TAP TO INTERRUPT'
      : micState === 'denied'
      ? 'MICROPHONE BLOCKED'
      : micState === 'unsupported'
      ? 'VOICE NOT SUPPORTED IN THIS BROWSER'
      : sttStatus?.status === 'ERROR' || ttsStatus?.status === 'ERROR'
      ? 'VOICE ENGINE ERROR — SEE STATUS ABOVE'
      : !voiceReady
      ? 'WARMING UP VOICE ENGINES...'
      : continuousMode
      ? 'STARTING CONTINUOUS LISTENING...'
      : 'TAP TO TALK, OR ENABLE CONTINUOUS MODE';

  const statusBadgeClasses = (status?: EngineStatusPayload['status']) =>
    status === 'READY'
      ? 'bg-success-dim text-success border-success-muted'
      : status === 'LOADING'
      ? 'bg-warning-dim text-warning border-warning-muted animate-pulse'
      : status === 'ERROR'
      ? 'bg-critical-dim text-critical border-critical-muted'
      : 'bg-surface text-slate-500 border-surface-border';

  return (
    <div className="space-y-4">
      {/* Header + engine status */}
      <div className="surface-panel rounded-sm p-4 sm:p-5 space-y-4 border border-surface-border">
        <div className="flex items-center justify-between flex-wrap gap-2 border-b border-surface-border pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-sm flex items-center justify-center bg-ai-accent-dim text-ai-accent">
              <Sparkles className="w-3.5 h-3.5" />
            </div>
            <div>
              <h2 className="text-xs font-semibold text-white font-mono uppercase tracking-wide">
                Voice Mission Copilot
              </h2>
              <p className="text-[11px] text-slate-400 font-mono">
                Whisper.cpp STT + local LLM RAG + Kokoro TTS — fully local, conversational
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-[10px] font-mono px-2 py-1 rounded-sm border ${statusBadgeClasses(sttStatus?.status)}`}>
              STT: {sttStatus?.status || 'UNKNOWN'}
            </span>
            <span className={`text-[10px] font-mono px-2 py-1 rounded-sm border ${statusBadgeClasses(ttsStatus?.status)}`}>
              TTS: {ttsStatus?.status || 'UNKNOWN'}
            </span>
            <span
              className={`text-[10px] font-mono px-2 py-1 rounded-sm border ${statusBadgeClasses(llmStatus?.status)}`}
              title={llmStatus?.status === 'ERROR' ? llmStatus?.error || '' : (llmStatus?.provider && llmStatus.provider !== 'none' ? `${llmStatus.provider} reasoning engine` : 'No LLM provider configured (disabled by default)')}
            >
              LLM: {llmStatus?.status || 'UNKNOWN'}
            </span>
            {!engineReady && (
              <button
                onClick={handleWarmup}
                disabled={isWarmingUp || engineLoading}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-ai-accent-dim border border-ai-accent-muted text-ai-accent text-[11px] font-medium hover:bg-ai-accent-dim/70 disabled:opacity-40 transition-colors font-mono"
              >
                {isWarmingUp || engineLoading ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <Power className="w-3 h-3" />
                )}
                <span>Warm up</span>
              </button>
            )}
            <button
              onClick={handleClearConversation}
              disabled={messages.length === 0}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-surface-card border border-surface-border text-slate-400 text-[11px] font-medium hover:text-white hover:bg-surface-card-hover disabled:opacity-30 transition-colors font-mono"
              title="Clear conversation history"
            >
              <Trash2 className="w-3 h-3" />
              <span>Clear</span>
            </button>
          </div>
        </div>

        {/* Continuous listen/respond toggle */}
        <div className="flex items-center justify-between gap-3 bg-white/[0.02] border border-surface-border rounded-sm px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            {continuousMode ? (
              <Ear className="w-4 h-4 text-success" />
            ) : (
              <EarOff className="w-4 h-4 text-slate-500" />
            )}
            <div>
              <span className="text-xs font-medium text-slate-200 font-mono">Continuous mode</span>
              <p className="text-[11px] text-slate-400 font-mono">
                {continuousMode
                  ? 'Always listening and responding — no need to tap the mic between turns.'
                  : 'Off — press the mic to talk, one turn at a time.'}
              </p>
            </div>
          </div>
          <button
            onClick={toggleContinuousMode}
            disabled={!voiceReady && !continuousMode}
            className={`relative w-11 h-6 rounded-full transition-colors shrink-0 disabled:opacity-40 disabled:cursor-not-allowed ${
              continuousMode ? 'bg-success' : 'bg-white/10'
            }`}
          >
            <span
              className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                continuousMode ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>

        {/* Mic control */}
        <div className="flex flex-col items-center justify-center gap-3 py-4">
          <button
            onClick={handleMicClick}
            disabled={micState === 'processing' || (!voiceReady && micState === 'idle')}
            className={`relative w-24 h-24 rounded-full flex items-center justify-center border transition-colors ${
              micState === 'capturing'
                ? continuousMode
                  ? 'bg-success-dim border-success-muted'
                  : 'bg-critical-dim border-critical-muted'
                : micState === 'speaking'
                ? 'bg-ai-accent-dim border-ai-accent-muted'
                : micState === 'processing'
                ? 'bg-warning-dim border-warning-muted/60'
                : micState === 'denied' || micState === 'unsupported'
                ? 'bg-white/5 border-surface-border'
                : !voiceReady
                ? 'bg-white/5 border-surface-border opacity-50 cursor-not-allowed'
                : 'bg-accent-dim border-accent-muted hover:bg-accent-dim/70'
            }`}
          >
            {micState === 'capturing' && (
              <span
                className={`absolute inline-flex h-full w-full rounded-full opacity-20 animate-ping ${
                  continuousMode ? 'bg-success' : 'bg-critical'
                }`}
              />
            )}
            {micState === 'processing' ? (
              <Loader2 className="w-8 h-8 text-warning animate-spin" />
            ) : micState === 'speaking' ? (
              <Volume2 className="w-8 h-8 text-ai-accent" />
            ) : micState === 'capturing' ? (
              continuousMode ? (
                <Ear className="w-8 h-8 text-success" />
              ) : (
                <Radio className="w-7 h-7 text-critical" />
              )
            ) : micState === 'denied' || micState === 'unsupported' ? (
              <AlertTriangle className="w-7 h-7 text-slate-500" />
            ) : (
              <Mic className="w-8 h-8 text-accent" />
            )}
          </button>
          <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5 font-mono">
            {micState === 'capturing' && !continuousMode && <Radio className="w-3 h-3 text-critical animate-pulse" />}
            {micLabel}
          </span>
          {micState === 'processing' && thinkingText && (
            <div className="w-full max-w-md bg-white/[0.02] border border-surface-border rounded-sm px-3 py-2 max-h-28 overflow-y-auto">
              <p className="text-[10px] font-mono text-slate-400 leading-relaxed whitespace-pre-wrap">
                {thinkingText}
                <span className="animate-pulse">▋</span>
              </p>
            </div>
          )}
          {errorMsg && (
            <p className="text-[11px] text-critical bg-critical-dim border border-critical-muted rounded-sm px-3 py-1.5 max-w-md text-center font-mono">
              {errorMsg}
            </p>
          )}
        </div>
      </div>

      {/* Conversation transcript */}
      <div className="surface-panel surface-panel-ai rounded-sm p-4 sm:p-5 border border-surface-border">
        <div className="flex items-center gap-2 border-b border-surface-border pb-2 mb-3">
          <span className="text-[11px] font-medium text-ai-accent font-mono uppercase tracking-wider">
            Conversation
          </span>
          <span className="text-[10px] text-slate-500 font-mono">
            (context preserved across follow-ups — active fault: {state.analytics.diagnosed_fault_name})
          </span>
        </div>

        <div ref={scrollRef} className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
          {messages.length === 0 && (
            <p className="text-xs text-slate-500 py-6 text-center font-mono">
              {continuousMode
                ? 'Just start talking — no wake word needed. It\'ll answer, then listen again automatically.'
                : 'Tap the mic and ask something, or flip on continuous mode above for hands-free.'}
            </p>
          )}
          {messages.map((m, idx) =>
            m.role === 'user' ? (
              <div key={idx} className="flex items-start gap-2.5 justify-end">
                <div className="max-w-[80%] bg-accent-dim border border-accent-muted/40 rounded-sm px-3.5 py-2.5">
                  <p className="text-xs text-slate-100 leading-relaxed">{m.text}</p>
                </div>
                <div className="w-7 h-7 rounded-sm bg-accent-dim flex items-center justify-center text-accent shrink-0">
                  <User className="w-3.5 h-3.5" />
                </div>
              </div>
            ) : (
              <div key={idx} className="flex items-start gap-2.5">
                <div className="w-7 h-7 rounded-sm bg-ai-accent-dim flex items-center justify-center text-ai-accent shrink-0">
                  <Bot className="w-3.5 h-3.5" />
                </div>
                <div className="max-w-[80%] bg-white/[0.02] border border-surface-border rounded-sm px-3.5 py-2.5">
                  <AerospaceMarkdown content={m.text} citations={m.citations} title="Spoken Reply" />
                </div>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
};
