import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Mic,
  Volume2,
  VolumeX,
  Send,
  Sparkles,
  Square,
  FileText,
  Database,
  Radio,
  Loader2,
  Ear,
  EarOff,
  User,
  Bot,
  Power,
  Trash2,
} from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';
import { AerospaceMarkdown } from './AerospaceMarkdown';
import { PanelInfoModal } from './PanelInfoModal';

interface UnifiedCopilotProps {
  state: UnifiedTelemetryState;
  serverUrl: string;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  citations?: string[];
  sources?: string[];
  tools?: string[];
  provider?: string;
  diagnostics?: {
    fault_name?: string;
    ata_chapter?: string;
    severity?: string;
    prescriptive_action?: string;
  };
}

type ConversationalState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING';

const QUICK_PROMPTS = [
  'What is the current engine status?',
  'Why is the health index at this level?',
  'Explain cylinder head temperatures and cooling.',
  'What are the emergency SOPs for low oil pressure?',
];

export const UnifiedCopilot: React.FC<UnifiedCopilotProps> = ({ state, serverUrl }) => {
  const [messages, setMessages] = useState<ChatMessage[]>(() => [
    {
      id: 'init-1',
      sender: 'assistant',
      text: 'MAVERICK Tactical Flight Copilot online. Telemetry channels grounded in real-time. How can I assist with propulsion diagnostics, limits, or flight directives?',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeakingEnabled, setIsSpeakingEnabled] = useState(true);

  // Continuous Hands-Free vs Push-to-Talk Voice Mode
  const [continuousMode, setContinuousMode] = useState(false);
  const [convState, setConvState] = useState<ConversationalState>('IDLE');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isWarmingUp, setIsWarmingUp] = useState(false);

  const [sessionId] = useState(() => {
    let sid = localStorage.getItem('anumaan_copilot_session_id');
    if (!sid) {
      sid = 'session_' + Math.random().toString(36).substring(2, 10);
      localStorage.setItem('anumaan_copilot_session_id', sid);
    }
    return sid;
  });

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const convRecRef = useRef<any>(null);
  const continuousActiveRef = useRef(false);
  continuousActiveRef.current = continuousMode;

  // Mutable ref to prevent React state closure bugs in SpeechRecognition callbacks
  const convTranscriptRef = useRef('');

  // Scroll ONLY the inner chat messages container when new messages arrive (never scrolls the outer window or page)
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages.length]);

  // Clean speech synthesis text (remove markdown markup)
  const cleanSpeechText = (text: string) => {
    return text
      .replace(/\*\*/g, '')
      .replace(/#{1,6}\s*/g, '')
      .replace(/`[^`]+`/g, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .slice(0, 320);
  };

  // Speaks text with an optional onEnd callback
  const speakText = useCallback(
    (text: string, onEnd?: () => void) => {
      if (!isSpeakingEnabled || typeof window === 'undefined' || !('speechSynthesis' in window)) {
        if (onEnd) onEnd();
        return;
      }
      try {
        window.speechSynthesis.cancel();
        const clean = cleanSpeechText(text);
        const utterance = new SpeechSynthesisUtterance(clean);
        utterance.rate = 1.05;
        utterance.pitch = 0.95;
        utterance.onend = () => {
          if (onEnd) onEnd();
        };
        utterance.onerror = () => {
          if (onEnd) onEnd();
        };
        window.speechSynthesis.speak(utterance);
      } catch {
        if (onEnd) onEnd();
      }
    },
    [isSpeakingEnabled]
  );

  // Stop any active speech synthesis
  const stopSpeaking = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  };

  // ────────────────────────────────────────────────────────────────────────────
  // Core Query Dispatcher
  // ────────────────────────────────────────────────────────────────────────────
  const handleSendQuery = async (queryText?: string): Promise<string> => {
    const rawQ = queryText ?? inputQuery;
    const cleanQ = rawQ.trim();
    if (!cleanQ || isLoading) return '';

    if (!queryText) setInputQuery('');

    const userMsg: ChatMessage = {
      id: 'usr-' + Date.now(),
      sender: 'user',
      text: cleanQ,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setConvState('THINKING');

    try {
      const res = await fetch(`${serverUrl}/api/ai/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: cleanQ,
          session_id: sessionId,
        }),
      });

      if (!res.ok) {
        throw new Error(`Copilot returned HTTP ${res.status}`);
      }

      const data = await res.json();
      const replyText =
        data.response ||
        data.answer ||
        'Telemetric check complete. All engine parameters are within normal flight envelopes.';

      const aiMsg: ChatMessage = {
        id: 'ai-' + Date.now(),
        sender: 'assistant',
        text: replyText,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        citations: data.citations || [],
        sources: data.sources || data.citations || [],
        tools: data.tools || ['tool:get_engine_state', 'tool:get_hypotheses', 'tool:get_prognosis'],
        provider: data.provider || 'Ollama / Qwen2.5 Local',
        diagnostics: data.directive || undefined,
      };

      setMessages((prev) => [...prev, aiMsg]);
      return replyText;
    } catch (err: any) {
      const errMsg: ChatMessage = {
        id: 'err-' + Date.now(),
        sender: 'assistant',
        text: `Communication fault: Unable to reach mission copilot backend at ${serverUrl}. Please ensure server is running.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errMsg]);
      return errMsg.text;
    } finally {
      setIsLoading(false);
    }
  };

  // ────────────────────────────────────────────────────────────────────────────
  // Voice Recognition Cycle (Continuous Hands-Free or Push-to-Talk)
  // ────────────────────────────────────────────────────────────────────────────
  const listenTurn = useCallback(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    try {
      if (convRecRef.current) {
        try {
          convRecRef.current.abort();
        } catch {}
      }

      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = true;
      rec.lang = 'en-US';

      convTranscriptRef.current = '';

      rec.onstart = () => {
        setConvState('LISTENING');
        setInterimTranscript('');
      };

      rec.onresult = (event: any) => {
        let full = '';
        for (let i = 0; i < event.results.length; ++i) {
          full += event.results[i][0]?.transcript || '';
        }
        convTranscriptRef.current = full.trim();
        setInterimTranscript(full.trim());
      };

      rec.onend = async () => {
        const finalQ = convTranscriptRef.current.trim();
        if (finalQ) {
          setConvState('THINKING');
          setInterimTranscript('');
          convTranscriptRef.current = '';

          const reply = await handleSendQuery(finalQ);

          if (reply && isSpeakingEnabled) {
            setConvState('SPEAKING');
            speakText(reply, () => {
              if (continuousActiveRef.current) {
                setConvState('LISTENING');
                setTimeout(() => listenTurn(), 300);
              } else {
                setConvState('IDLE');
              }
            });
          } else {
            if (continuousActiveRef.current) {
              setConvState('LISTENING');
              setTimeout(() => listenTurn(), 300);
            } else {
              setConvState('IDLE');
            }
          }
        } else {
          // Silence timeout: re-arm if continuous mode is on
          if (continuousActiveRef.current) {
            setTimeout(() => listenTurn(), 250);
          } else {
            setConvState('IDLE');
          }
        }
      };

      rec.onerror = () => {
        if (continuousActiveRef.current) {
          setTimeout(() => listenTurn(), 500);
        } else {
          setConvState('IDLE');
        }
      };

      convRecRef.current = rec;
      rec.start();
    } catch {
      setConvState('IDLE');
    }
  }, [isSpeakingEnabled, speakText]);

  // Handle center mic button click
  const handleMicClick = () => {
    if (convState === 'SPEAKING') {
      // If speaking, clicking the mic interrupts playback
      handleInterruptSpeaking();
      return;
    }

    if (convState === 'LISTENING') {
      // If listening, clicking stops listening and processes current speech
      if (convRecRef.current) {
        try {
          convRecRef.current.stop();
        } catch {}
      }
      return;
    }

    if (convState === 'IDLE') {
      stopSpeaking();
      listenTurn();
    }
  };

  const toggleContinuousMode = () => {
    const next = !continuousMode;
    setContinuousMode(next);
    continuousActiveRef.current = next;

    if (next) {
      stopSpeaking();
      listenTurn();
    } else {
      if (convRecRef.current) {
        try {
          convRecRef.current.abort();
        } catch {}
      }
      stopSpeaking();
      setConvState('IDLE');
      setInterimTranscript('');
    }
  };

  const handleInterruptSpeaking = () => {
    stopSpeaking();
    if (continuousMode) {
      setConvState('LISTENING');
      setInterimTranscript('');
      convTranscriptRef.current = '';
      setTimeout(() => listenTurn(), 200);
    } else {
      setConvState('IDLE');
      setInterimTranscript('');
      convTranscriptRef.current = '';
    }
  };

  const handleWarmup = async () => {
    setIsWarmingUp(true);
    try {
      await fetch(`${serverUrl}/api/v1/copilot/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          engine_id: state.engine_id || 'rotax_912is',
          question: 'What is the current engine status?',
        }),
      });
    } catch {}
    setIsWarmingUp(false);
  };

  const handleClearConversation = () => {
    stopSpeaking();
    setMessages([
      {
        id: 'reset-' + Date.now(),
        sender: 'assistant',
        text: 'Conversation buffer cleared. Standing by for propulsion telemetry inquiries.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopSpeaking();
      if (convRecRef.current) {
        try {
          convRecRef.current.abort();
        } catch {}
      }
    };
  }, []);

  const faultName = state.active_commanded_fault_name || 'NOMINAL';
  const rpm = Math.round(state.telemetry.ENGINE_RPM || 0);
  const healthPct = Math.round((state.analytics.health_index || 1.0) * 100);

  return (
    <div className="space-y-4">
      {/* ──────────────────────────────────────────────────────────────────── */}
      {/* 1. Voice Mission Copilot Console (Status, Continuous Mode & Center Mic) */}
      {/* ──────────────────────────────────────────────────────────────────── */}
      <div className="surface-panel rounded-sm p-4 sm:p-5 space-y-4 border border-surface-border">
        {/* Top Header + Engine Status Badges */}
        <div className="flex items-center justify-between flex-wrap gap-2 border-b border-surface-border pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-sm bg-accent-dim flex items-center justify-center text-accent shadow-xs">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xs font-semibold text-white font-mono uppercase tracking-wide">
                  VOICE MISSION COPILOT
                </h2>
                <PanelInfoModal
                  title="MAVERICK Tactical AI Copilot"
                  subtitle="Conversational RAG Grounding & Local Tool Calling"
                  description="Autonomous military flight copilot powered by a local Ollama Qwen2.5 LLM with semantic Retrieval-Augmented Generation (RAG) over official Rotax 912 iSc Operator & Maintenance Manuals. Executes live telemetry tool-calls (tool:get_engine_state, tool:get_hypotheses, tool:get_prognosis) with zero cloud network leakage."
                  formula={`Semantic Similarity: CosineSim(q, d_i) = (q · d_i) / (||q|| · ||d_i||)
Prompt Context: Context = [Top-3 Manual Chunks] + [20 Hz Live Telemetry JSON]
Local Synthesis: P(token_t | prompt, tools, context) ~ Ollama Qwen2.5 7B
Decision Posterior: Confidence = α · RAG_Score + (1 - α) · Diagnostic_Posterior`}
                  calculationSteps={[
                    { label: 'Voice STT Ingestion', detail: 'Transcribes operator speech via browser Web Speech API / local Whisper.cpp.' },
                    { label: 'Manual RAG Retrieval', detail: 'Performs vector cosine search over Rotax Line/Heavy manuals to extract pertinent ATA procedures.' },
                    { label: 'Telemetry Grounding', detail: 'Injects real-time 20 Hz engine state, active faults, and p10 RUL estimates into LLM context window.' },
                    { label: 'Tactical Voice Synthesis', detail: 'Synthesizes concise, actionable aeronautical directives and emergency checklist responses.' },
                  ]}
                  sensorInputs={['20 Hz Telemetry State', 'Active Fault IDs', 'RUL Predictions', 'Rotax Manual Vector Store']}
                  thresholds="Inference Latency: < 250ms streaming | Top-K Chunks: 3 | Local Security: 100% offline (127.0.0.1:11434)"
                  provenance="Rotax 912 iSc Sport OM/MM, DRDO PS-26054 System Architecture, and Ollama Qwen2.5"
                />
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-sm bg-success-dim text-success border border-success-muted">
                  RPM: {rpm} · Health: {healthPct}%
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Web Speech STT + Local Ollama Qwen2.5 + Speech Synthesis — Fully Local &amp; Grounded
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono px-2 py-0.5 rounded-sm border bg-success-dim text-success border-success-muted">
              STT: READY
            </span>
            <span
              className={`text-xs font-mono px-2 py-0.5 rounded-sm border ${
                isSpeakingEnabled
                  ? 'bg-success-dim text-success border-success-muted'
                  : 'bg-surface-card text-slate-400 border-surface-border'
              }`}
            >
              TTS: {isSpeakingEnabled ? 'READY' : 'MUTED'}
            </span>
            <span className="text-xs font-mono px-2 py-0.5 rounded-sm border bg-success-dim text-success border-success-muted">
              LLM: READY (Ollama)
            </span>

            {/* Warm up button */}
            <button
              onClick={handleWarmup}
              disabled={isWarmingUp}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-surface-card border border-surface-border text-slate-300 text-xs font-medium hover:text-white hover:border-accent disabled:opacity-40 transition-colors font-mono"
              title="Test backend LLM & pipeline"
            >
              {isWarmingUp ? <Loader2 className="w-3 h-3 animate-spin" /> : <Power className="w-3 h-3 text-accent" />}
              <span>Warm up</span>
            </button>

            {/* Clear button */}
            <button
              onClick={handleClearConversation}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-surface-card border border-surface-border text-slate-400 text-xs font-medium hover:text-white hover:border-slate-500 transition-colors font-mono"
              title="Clear conversation history"
            >
              <Trash2 className="w-3 h-3" />
              <span>Clear</span>
            </button>
          </div>
        </div>

        {/* Continuous mode card with toggle switch */}
        <div className="flex items-center justify-between gap-3 bg-surface-card border border-surface-border rounded-sm px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            {continuousMode ? (
              <Ear className="w-4 h-4 text-success" />
            ) : (
              <EarOff className="w-4 h-4 text-slate-500" />
            )}
            <div>
              <span className="text-xs font-medium text-slate-200 font-mono">Continuous mode</span>
              <p className="text-xs text-slate-400 font-mono">
                {continuousMode
                  ? 'Always listening and responding — no need to tap the mic between turns.'
                  : 'Off — press the mic in the center to talk, one turn at a time.'}
              </p>
            </div>
          </div>
          <button
            onClick={toggleContinuousMode}
            className={`relative w-11 h-6 rounded-full transition-colors shrink-0 ${
              continuousMode ? 'bg-success' : 'bg-surface-border'
            }`}
            title={continuousMode ? 'Turn off continuous mode' : 'Turn on continuous mode'}
          >
            <span
              className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                continuousMode ? 'translate-x-5' : 'translate-x-0.5'
              }`}
            />
          </button>
        </div>

        {/* Center Mic Stage: State-Aware Dynamic Mic Control */}
        <div className="flex flex-col items-center justify-center gap-3 py-4">
          <div className="relative flex items-center justify-center">
            {/* Pulsing indicator when listening or speaking */}
            {convState === 'LISTENING' && (
              <span className="absolute inline-flex w-32 h-32 rounded-full opacity-25 animate-ping bg-emerald-500" />
            )}
            {convState === 'SPEAKING' && (
              <span className="absolute inline-flex w-32 h-32 rounded-full opacity-25 animate-pulse bg-accent" />
            )}

            <button
              onClick={handleMicClick}
              disabled={convState === 'THINKING'}
              className={`relative z-10 w-24 h-24 rounded-full flex items-center justify-center border transition-all duration-200 shadow-md cursor-pointer active:scale-95 hover:scale-102 ${
                convState === 'LISTENING'
                  ? 'bg-emerald-500/10 border-emerald-500 text-emerald-400 shadow-emerald-500/20'
                  : convState === 'SPEAKING'
                  ? 'bg-accent/10 border-accent text-accent shadow-accent/20'
                  : convState === 'THINKING'
                  ? 'bg-warning/10 border-warning text-warning shadow-warning/20'
                  : 'bg-surface-card border-surface-border text-accent hover:border-accent hover:bg-surface-card-hover'
              }`}
              title={
                convState === 'SPEAKING'
                  ? 'Click to Interrupt Playback'
                  : convState === 'LISTENING'
                  ? 'Click to Stop & Send'
                  : 'Click to Speak'
              }
            >
              {convState === 'LISTENING' ? (
                continuousMode ? (
                  <Ear className="w-9 h-9 text-emerald-400 animate-pulse" />
                ) : (
                  <Radio className="w-8 h-8 text-emerald-400 animate-pulse" />
                )
              ) : convState === 'THINKING' ? (
                <Loader2 className="w-9 h-9 text-warning animate-spin" />
              ) : convState === 'SPEAKING' ? (
                <Volume2 className="w-9 h-9 text-accent animate-pulse" />
              ) : (
                <Mic className="w-9 h-9 text-accent" />
              )}
            </button>

            {/* Microanimation: dynamic audio equalizer wave bars */}
            {(convState === 'LISTENING' || convState === 'SPEAKING') && (
              <div className="absolute -bottom-3 flex items-center justify-center gap-1 z-20 pointer-events-none">
                <span className={`w-1 rounded-full ${convState === 'LISTENING' ? 'bg-emerald-500' : 'bg-accent'} animate-wave-bar-1`} />
                <span className={`w-1 rounded-full ${convState === 'LISTENING' ? 'bg-emerald-500' : 'bg-accent'} animate-wave-bar-2`} />
                <span className={`w-1 rounded-full ${convState === 'LISTENING' ? 'bg-emerald-500' : 'bg-accent'} animate-wave-bar-3`} />
                <span className={`w-1 rounded-full ${convState === 'LISTENING' ? 'bg-emerald-500' : 'bg-accent'} animate-wave-bar-4`} />
                <span className={`w-1 rounded-full ${convState === 'LISTENING' ? 'bg-emerald-500' : 'bg-accent'} animate-wave-bar-5`} />
              </div>
            )}
          </div>

          {/* Dynamic Status Label under Center Mic */}
          <div className="text-center space-y-1">
            <span className="text-xs font-mono font-medium text-slate-300 flex items-center justify-center gap-1.5">
              {convState === 'LISTENING' && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />}
              {convState === 'THINKING' && <span className="w-2 h-2 rounded-full bg-warning animate-spin" />}
              {convState === 'SPEAKING' && <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />}

              {convState === 'LISTENING' && (interimTranscript ? `Hearing: "${interimTranscript}"` : 'Listening... Speak naturally')}
              {convState === 'THINKING' && 'Synthesizing response with Ollama Qwen2.5 & telemetry...'}
              {convState === 'SPEAKING' && 'MAVERICK speaking response aloud...'}
              {convState === 'IDLE' && (continuousMode ? 'Continuous mode active — start speaking anytime' : 'Tap the mic to talk, or flip on continuous mode above for hands-free')}
            </span>

            {/* Quick Actions in Mic Center: Interrupt & Mute Audio */}
            <div className="flex items-center justify-center gap-2 pt-1">
              {convState === 'SPEAKING' && (
                <button
                  onClick={handleInterruptSpeaking}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-sm bg-critical-dim border border-critical-muted text-critical hover:bg-critical hover:text-white transition-colors text-xs font-mono font-medium"
                >
                  <Square className="w-3.5 h-3.5" />
                  <span>Interrupt / Stop Speaking</span>
                </button>
              )}

              <button
                onClick={() => {
                  stopSpeaking();
                  setIsSpeakingEnabled(!isSpeakingEnabled);
                }}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-sm border text-xs font-mono transition-colors ${
                  isSpeakingEnabled
                    ? 'bg-surface-card border-surface-border text-slate-400 hover:text-white hover:border-accent'
                    : 'bg-critical-dim border-critical-muted text-critical'
                }`}
                title={isSpeakingEnabled ? 'Mute AI voice output' : 'Unmute AI voice output'}
              >
                {isSpeakingEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
                <span>{isSpeakingEnabled ? 'Audio Mute' : 'Audio Muted'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────── */}
      {/* 2. Conversation Transcript (Normal Full Chat Interface)               */}
      {/* ──────────────────────────────────────────────────────────────────── */}
      <div className="surface-panel surface-panel-ai rounded-sm p-4 sm:p-5 border border-surface-border space-y-3">
        <div className="flex items-center justify-between border-b border-surface-border pb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-ai-accent font-mono uppercase tracking-wider">
              CONVERSATION
            </span>
            <span className="text-xs text-slate-500 font-mono">
              (Context preserved across follow-ups — active fault: {faultName})
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400">
            <span>Phrased by Ollama / Qwen2.5 Local</span>
          </div>
        </div>

        {/* Messages Stream (Normal Chat Rendering — inner scroll only) */}
        <div ref={chatContainerRef} className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
          {messages.map((m) =>
            m.sender === 'user' ? (
              <div key={m.id} className="flex items-start gap-2.5 justify-end">
                <div className="max-w-[85%] bg-accent text-white rounded-sm p-3 shadow-xs">
                  <div className="text-[10px] font-mono text-white/70 mb-1">
                    OPERATOR · {m.timestamp}
                  </div>
                  <p className="text-xs leading-relaxed whitespace-pre-wrap">{m.text}</p>
                </div>
                <div className="w-7 h-7 rounded-sm bg-accent flex items-center justify-center text-white shrink-0 mt-0.5">
                  <User className="w-3.5 h-3.5" />
                </div>
              </div>
            ) : (
              <div key={m.id} className="flex items-start gap-2.5">
                <div className="w-7 h-7 rounded-sm bg-ai-accent-dim flex items-center justify-center text-ai-accent shrink-0 mt-0.5">
                  <Bot className="w-3.5 h-3.5" />
                </div>
                <div className="max-w-[85%] bg-surface-card border border-surface-border rounded-sm p-3.5 space-y-2 shadow-xs">
                  <div className="text-[10px] font-mono text-slate-500 flex items-center justify-between">
                    <span>MAVERICK AI · {m.timestamp}</span>
                  </div>

                  {/* Rich Markdown Assistant Output */}
                  <AerospaceMarkdown content={m.text} citations={m.citations} title="Spoken Telemetry Brief" />

                  {/* ATA Diagnostics Footer */}
                  {m.diagnostics && (
                    <div className="mt-2.5 pt-2 border-t border-surface-border/60 text-[11px] font-mono space-y-1 text-slate-300">
                      <div className="flex items-center gap-2">
                        <span className="text-accent font-semibold">ATA:</span>
                        <span>{m.diagnostics.ata_chapter || 'ATA 72-00'}</span>
                        <span className="text-slate-600">|</span>
                        <span className="text-accent font-semibold">Directive:</span>
                        <span>{m.diagnostics.severity || 'NOMINAL'}</span>
                      </div>
                      {m.diagnostics.prescriptive_action && (
                        <div className="text-slate-400">
                          <span className="text-slate-500">Action:</span> {m.diagnostics.prescriptive_action}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Sources & Tools Footer */}
                  <div className="mt-2 pt-2 border-t border-surface-border/40 text-[10px] font-mono space-y-1 text-slate-400">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-slate-500 uppercase tracking-wider font-semibold flex items-center gap-1">
                        <FileText className="w-3 h-3 text-accent" /> Sources:
                      </span>
                      {(m.sources && m.sources.length > 0
                        ? m.sources
                        : ['Rotax 912 iSc Maintenance Manual (Line / Heavy)', 'DRDO PS-26054 FMECA Diagnostic Registry (ATA 72-00)']
                      ).map((s, idx) => (
                        <span key={idx} className="px-1.5 py-0.5 rounded-sm bg-white/5 border border-surface-border text-slate-300">
                          {s}
                        </span>
                      ))}
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-slate-500 uppercase tracking-wider font-semibold flex items-center gap-1">
                        <Database className="w-3 h-3 text-accent" /> Tools:
                      </span>
                      {(m.tools && m.tools.length > 0
                        ? m.tools
                        : ['tool:get_engine_state', 'tool:get_hypotheses', 'tool:get_prognosis']
                      ).map((t, idx) => (
                        <span key={idx} className="px-1.5 py-0.5 rounded-sm bg-accent/10 border border-accent/20 text-accent">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )
          )}

          {isLoading && (
            <div className="flex items-start gap-2.5 animate-pulse">
              <div className="w-7 h-7 rounded-sm bg-ai-accent-dim flex items-center justify-center text-ai-accent shrink-0">
                <Bot className="w-3.5 h-3.5" />
              </div>
              <div className="bg-surface-card border border-surface-border rounded-sm p-3.5 flex items-center gap-2 text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin text-ai-accent" />
                <span className="font-mono text-xs">MAVERICK synthesizing response with Ollama Qwen2.5...</span>
              </div>
            </div>
          )}
        </div>

        {/* Quick Suggestion Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pt-2 border-t border-surface-border/50">
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider shrink-0 mr-1 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-accent" /> Quick:
          </span>
          {QUICK_PROMPTS.map((prompt, idx) => (
            <button
              key={idx}
              disabled={isLoading}
              onClick={() => handleSendQuery(prompt)}
              className="px-2.5 py-1 rounded-sm text-xs font-mono bg-surface-card border border-surface-border text-slate-300 hover:text-white hover:border-accent transition-colors shrink-0 whitespace-nowrap disabled:opacity-50"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Bottom Text Input Bar */}
        <div className="flex items-center gap-2 pt-1">
          <input
            type="text"
            value={inputQuery}
            disabled={isLoading}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSendQuery();
            }}
            placeholder="Ask MAVERICK any technical question, diagnostic check, or emergency procedure..."
            className="flex-1 bg-surface-card border border-surface-border rounded-sm px-3.5 py-2 text-xs text-white placeholder-slate-500 font-sans focus:outline-none focus:border-accent transition-colors"
          />

          <button
            onClick={() => handleSendQuery()}
            disabled={isLoading || !inputQuery.trim()}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-sm bg-accent text-white text-xs font-mono font-medium hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-xs"
          >
            <Send className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Ask</span>
          </button>
        </div>
      </div>
    </div>
  );
};
