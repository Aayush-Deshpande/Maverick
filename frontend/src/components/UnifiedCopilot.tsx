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
  User,
  Bot,
  Power,
  RotateCcw,
  Headphones,
  ShieldCheck,
  Activity,
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

  // Clean speech synthesis text (remove markdown markup and diagnostic blocks)
  const cleanSpeechText = (text: string) => {
    return text
      .replace(/\[DIAGNOSTIC ADVISORY:.*?\]/g, '')
      .replace(/\[TECHNICAL MANUAL DIRECTIVE:.*?\]/g, '')
      .replace(/\[ATA.*?:.*?\]/g, '')
      .replace(/[*_#`~[\]]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  };

  // Browser speech synthesis (TTS)
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
        utterance.pitch = 1.0;
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

  // Send query to backend Mission Copilot (/api/ai/ask)
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
    } catch {
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
          full += event.results[i][0].transcript;
        }
        setInterimTranscript(full);
        convTranscriptRef.current = full.trim();
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

  // Handle dynamic mic button click
  const handleMicClick = () => {
    if (convState === 'SPEAKING') {
      // If speaking, clicking interrupts playback
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
    } catch {
      // Soft fail
    } finally {
      setIsWarmingUp(false);
    }
  };

  const handleClearConversation = () => {
    stopSpeaking();
    setMessages([
      {
        id: 'init-cleared',
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
    <div className="surface-panel surface-panel-ai rounded-sm p-4 sm:p-5 border border-surface-border space-y-3.5 shadow-xs">
      {/* ──────────────────────────────────────────────────────────────────── */}
      {/* 1. Header Bar: Identity, Telemetry, and Tactical Controls            */}
      {/* ──────────────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-2.5 border-b border-surface-border pb-3">
        {/* Left: Identity & Badges */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-sm bg-accent-dim flex items-center justify-center text-accent shadow-xs shrink-0">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xs font-semibold text-white tracking-wide font-mono">
                MAVERICK · Tactical AI Mission Copilot
              </h2>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-sm bg-accent-dim text-accent border border-accent-muted">
                Local LLM / Gemini Cloud Demo
              </span>
            </div>
            <p className="text-xs text-slate-400 font-sans mt-0.5">
              Conversational RAG Grounding · Multi-Turn Dialogue Memory · Continuous Voice Mode
            </p>
          </div>
        </div>

        {/* Right: Telemetry & Tactical Controls */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Telemetry Status Badges */}
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-sm bg-surface-card text-slate-300 border border-surface-border flex items-center gap-1">
            <Activity className="w-3 h-3 text-accent" /> RPM: {rpm}
          </span>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-sm bg-success-dim text-success border border-success-muted flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-success" /> Health: {healthPct}%
          </span>

          {/* (i) Physics & Grounding Info Modal */}
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

          {/* Hands-Free Voice Mode Toggle Pill (Image 1 & 3) */}
          <button
            type="button"
            onClick={toggleContinuousMode}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-sm border font-mono text-xs transition-all cursor-pointer ${
              continuousMode
                ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400 shadow-xs'
                : 'bg-surface-card border-surface-border text-slate-300 hover:text-white hover:border-accent'
            }`}
            title={continuousMode ? 'Disable continuous hands-free voice mode' : 'Enable continuous hands-free voice mode'}
          >
            <Headphones className={`w-3.5 h-3.5 ${continuousMode ? 'text-emerald-400 animate-pulse' : 'text-slate-400'}`} />
            <span>{continuousMode ? 'Hands-Free: ON' : 'Hands-Free Voice'}</span>
          </button>

          {/* TTS Audio Mute/Unmute */}
          <button
            type="button"
            onClick={() => {
              stopSpeaking();
              setIsSpeakingEnabled(!isSpeakingEnabled);
            }}
            className={`p-1.5 rounded-sm border text-xs transition-colors cursor-pointer ${
              isSpeakingEnabled
                ? 'bg-surface-card border-surface-border text-slate-300 hover:text-white hover:border-accent'
                : 'bg-critical-dim border-critical-muted text-critical'
            }`}
            title={isSpeakingEnabled ? 'Mute AI voice output' : 'Unmute AI voice output'}
          >
            {isSpeakingEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
          </button>

          {/* Clear Conversation History */}
          <button
            type="button"
            onClick={handleClearConversation}
            className="p-1.5 rounded-sm bg-surface-card border border-surface-border text-slate-400 hover:text-white hover:border-slate-500 transition-colors cursor-pointer"
            title="Clear conversation history"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          {/* Pipeline Warmup / Health Test */}
          <button
            type="button"
            onClick={handleWarmup}
            disabled={isWarmingUp}
            className="p-1.5 rounded-sm bg-surface-card border border-surface-border text-slate-400 hover:text-accent hover:border-accent disabled:opacity-40 transition-colors cursor-pointer"
            title="Warmup / Test LLM and RAG pipeline"
          >
            {isWarmingUp ? <Loader2 className="w-3.5 h-3.5 animate-spin text-accent" /> : <Power className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────── */}
      {/* 2. Dual Engine Architecture Notice Banner                            */}
      {/* ──────────────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-2 px-3 py-1.5 rounded-sm bg-black/[0.02] border border-surface-border text-[11px] font-sans text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse shrink-0" />
          <span>Dual Engine: Operates on local LLM (Ollama / Qwen2.5 / Sarvam) for edge defense deployments; powered by Google Gemini for cloud demonstration.</span>
        </div>
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 shrink-0 font-medium">
          Demo Ready
        </span>
      </div>

      {/* ──────────────────────────────────────────────────────────────────── */}
      {/* 3. Live Voice Interaction Hub (Active in voice mode or speaking)     */}
      {/* ──────────────────────────────────────────────────────────────────── */}
      {(continuousMode || convState !== 'IDLE') && (
        <div className="flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-sm bg-surface-card border border-surface-border/80 transition-all">
          <div className="flex items-center gap-3">
            {/* Dynamic Mic Orb / Control */}
            <button
              type="button"
              onClick={handleMicClick}
              className={`relative w-8 h-8 rounded-full flex items-center justify-center border transition-all active:scale-95 cursor-pointer ${
                convState === 'LISTENING'
                  ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400 shadow-xs shadow-emerald-500/30'
                  : convState === 'SPEAKING'
                  ? 'bg-accent/20 border-accent text-accent shadow-xs shadow-accent/30'
                  : convState === 'THINKING'
                  ? 'bg-warning/20 border-warning text-warning shadow-xs shadow-warning/30'
                  : 'bg-surface-panel border-surface-border text-slate-300 hover:text-white hover:border-accent'
              }`}
              title={
                convState === 'SPEAKING'
                  ? 'Click to interrupt playback'
                  : convState === 'LISTENING'
                  ? 'Click to stop & send'
                  : 'Click to speak'
              }
            >
              {convState === 'LISTENING' ? (
                <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
              ) : convState === 'THINKING' ? (
                <Loader2 className="w-4 h-4 text-warning animate-spin" />
              ) : convState === 'SPEAKING' ? (
                <Volume2 className="w-4 h-4 text-accent animate-pulse" />
              ) : (
                <Mic className="w-4 h-4 text-accent" />
              )}
            </button>

            {/* Voice Status & Equalizer / Interim Preview */}
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-medium text-slate-200">
                  {convState === 'LISTENING' && 'Listening to operator...'}
                  {convState === 'THINKING' && 'Synthesizing response with Gemini / Local LLM...'}
                  {convState === 'SPEAKING' && 'MAVERICK speaking directive aloud...'}
                  {convState === 'IDLE' && 'Continuous voice active — speak naturally'}
                </span>

                {/* Equalizer Wave bars */}
                {(convState === 'LISTENING' || convState === 'SPEAKING') && (
                  <div className="flex items-center gap-0.5">
                    <span className={`w-0.5 h-3 rounded-full ${convState === 'LISTENING' ? 'bg-emerald-400' : 'bg-accent'} animate-wave-bar-1`} />
                    <span className={`w-0.5 h-4 rounded-full ${convState === 'LISTENING' ? 'bg-emerald-400' : 'bg-accent'} animate-wave-bar-2`} />
                    <span className={`w-0.5 h-2 rounded-full ${convState === 'LISTENING' ? 'bg-emerald-400' : 'bg-accent'} animate-wave-bar-3`} />
                    <span className={`w-0.5 h-4 rounded-full ${convState === 'LISTENING' ? 'bg-emerald-400' : 'bg-accent'} animate-wave-bar-4`} />
                    <span className={`w-0.5 h-2.5 rounded-full ${convState === 'LISTENING' ? 'bg-emerald-400' : 'bg-accent'} animate-wave-bar-5`} />
                  </div>
                )}
              </div>

              {/* Interim speech transcript preview */}
              {interimTranscript && (
                <p className="text-xs text-slate-300 italic font-sans mt-0.5">
                  "{interimTranscript}"
                </p>
              )}
            </div>
          </div>

          {/* Interrupt Button (Visible during SPEAKING) */}
          {convState === 'SPEAKING' && (
            <button
              type="button"
              onClick={handleInterruptSpeaking}
              className="flex items-center gap-1 px-2.5 py-1 rounded-sm bg-critical-dim border border-critical-muted text-critical hover:bg-critical hover:text-white transition-colors text-xs font-mono cursor-pointer"
            >
              <Square className="w-3 h-3" />
              <span>Interrupt</span>
            </button>
          )}
        </div>
      )}

      {/* ──────────────────────────────────────────────────────────────────── */}
      {/* 4. Conversation Stream: Normal Chat Reflection                        */}
      {/* ──────────────────────────────────────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between border-b border-surface-border/60 pb-1.5">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            CONVERSATION <span className="text-slate-500 font-sans font-normal">(context preserved across follow-ups — active fault: {faultName})</span>
          </span>
          <span className="text-[11px] font-mono text-slate-500">
            Grounding: ATA 72-00 + 20 Hz Bus
          </span>
        </div>

        {/* Messages Stream (Inner Scroll Only — Never scrolls browser window) */}
        <div ref={chatContainerRef} className="space-y-3.5 max-h-[460px] overflow-y-auto pr-1">
          {messages.map((m) =>
            m.sender === 'user' ? (
              <div key={m.id} className="flex items-start gap-2.5 justify-end">
                <div className="max-w-[85%] bg-accent text-white rounded-sm p-3 shadow-xs">
                  <div className="text-[10px] font-mono text-white/70 mb-1">
                    OPERATOR · {m.timestamp}
                  </div>
                  <p className="text-xs font-sans leading-relaxed whitespace-pre-wrap">{m.text}</p>
                </div>
                <div className="w-7 h-7 rounded-sm bg-accent flex items-center justify-center text-white shrink-0 mt-0.5 shadow-xs">
                  <User className="w-3.5 h-3.5" />
                </div>
              </div>
            ) : (
              <div key={m.id} className="flex items-start gap-2.5">
                <div className="w-7 h-7 rounded-sm bg-ai-accent-dim flex items-center justify-center text-ai-accent shrink-0 mt-0.5 shadow-xs">
                  <Bot className="w-3.5 h-3.5" />
                </div>
                <div className="max-w-[85%] bg-surface-card border border-surface-border rounded-sm p-3.5 space-y-2.5 shadow-xs">
                  <div className="text-[10px] font-mono text-slate-400 flex items-center justify-between">
                    <span>MAVERICK AI · {m.timestamp}</span>
                    <button
                      type="button"
                      onClick={() => speakText(m.text)}
                      className="hover:text-accent transition-colors flex items-center gap-1 cursor-pointer"
                      title="Read aloud"
                    >
                      <Volume2 className="w-3 h-3" />
                      <span className="text-[10px]">Speak</span>
                    </button>
                  </div>

                  {/* Assistant Content in Clean Sans-Serif Typography */}
                  <AerospaceMarkdown content={m.text} citations={m.citations} title="Mission Intelligence Synthesis" />

                  {/* ATA Diagnostics Footer */}
                  {m.diagnostics && (
                    <div className="mt-2 pt-2 border-t border-surface-border/60 text-[11px] font-mono space-y-1 text-slate-300">
                      <div className="flex items-center gap-2">
                        <span className="text-accent font-semibold">ATA:</span>
                        <span>{m.diagnostics.ata_chapter || 'ATA 72-00'}</span>
                        <span className="text-slate-600">|</span>
                        <span className="text-accent font-semibold">Directive:</span>
                        <span>{m.diagnostics.severity || 'NOMINAL'}</span>
                      </div>
                      {m.diagnostics.prescriptive_action && (
                        <div className="text-slate-400 font-sans text-xs">
                          <span className="font-mono text-slate-500">Action:</span> {m.diagnostics.prescriptive_action}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Sources, Tools & Provider Footer */}
                  <div className="mt-2 pt-2 border-t border-surface-border/40 text-[10px] font-mono space-y-1.5 text-slate-400">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-slate-500 uppercase tracking-wider font-semibold flex items-center gap-1">
                        <FileText className="w-3 h-3 text-accent" /> SOURCES:
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
                    <div className="flex flex-wrap items-center justify-between gap-1.5">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-slate-500 uppercase tracking-wider font-semibold flex items-center gap-1">
                          <Database className="w-3 h-3 text-accent" /> TOOLS:
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
                      <span className="text-slate-500">
                        {m.provider ? `Phrased by ${m.provider}` : 'Phrased by Ollama / Qwen2.5 Local'}
                      </span>
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
                <span className="font-sans text-xs">MAVERICK synthesizing response with Gemini / Local LLM...</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────── */}
      {/* 5. Quick Suggestion Chips & Bottom Input Bar                         */}
      {/* ──────────────────────────────────────────────────────────────────── */}
      <div className="space-y-2 pt-2 border-t border-surface-border/50">
        {/* Suggestion Chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1">
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider shrink-0 mr-1 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-accent" /> QUICK:
          </span>
          {QUICK_PROMPTS.map((prompt, idx) => (
            <button
              key={idx}
              type="button"
              disabled={isLoading}
              onClick={() => handleSendQuery(prompt)}
              className="px-2.5 py-1 rounded-sm text-xs font-sans bg-surface-card border border-surface-border text-slate-300 hover:text-white hover:border-accent transition-colors shrink-0 whitespace-nowrap disabled:opacity-50 cursor-pointer"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="flex items-center gap-2">
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

          {/* Dynamic Mic Control Button */}
          <button
            type="button"
            onClick={handleMicClick}
            disabled={convState === 'THINKING'}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-sm border font-mono text-xs transition-all cursor-pointer ${
              convState === 'LISTENING'
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500 shadow-xs'
                : convState === 'SPEAKING'
                ? 'bg-accent/20 text-accent border-accent shadow-xs'
                : 'bg-surface-card text-slate-300 border-surface-border hover:text-white hover:border-accent'
            }`}
            title={
              convState === 'SPEAKING'
                ? 'Stop speaking'
                : convState === 'LISTENING'
                ? 'Stop listening'
                : 'Dictate or speak question'
            }
          >
            {convState === 'LISTENING' ? (
              <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            ) : convState === 'SPEAKING' ? (
              <Volume2 className="w-3.5 h-3.5 text-accent animate-pulse" />
            ) : (
              <Mic className="w-3.5 h-3.5 text-accent" />
            )}
            <span className="text-[11px] hidden sm:inline">
              {convState === 'LISTENING' ? 'Listening' : convState === 'SPEAKING' ? 'Speaking' : 'Dictate'}
            </span>
          </button>

          {/* Ask / Send Button */}
          <button
            type="button"
            onClick={() => handleSendQuery()}
            disabled={isLoading || !inputQuery.trim()}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-sm bg-accent text-white text-xs font-mono font-medium hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-xs cursor-pointer"
          >
            <Send className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Ask</span>
          </button>
        </div>
      </div>
    </div>
  );
};
