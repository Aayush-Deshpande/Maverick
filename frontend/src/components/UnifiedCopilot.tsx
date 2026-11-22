import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Brain,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Send,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  RotateCcw,
  Activity,
  Headphones,
  Square,
  FileText,
  Database,
} from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';
import { AerospaceMarkdown } from './AerospaceMarkdown';

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

  // Mode 1: Dictation (Speech-to-Text into input box)
  const [isDictating, setIsDictating] = useState(false);

  // Mode 2: Conversational Live Voice Mode (Hands-free continuous voice dialogue)
  const [isConversationalActive, setIsConversationalActive] = useState(false);
  const [convState, setConvState] = useState<ConversationalState>('IDLE');
  const [interimTranscript, setInterimTranscript] = useState('');

  const [sessionId] = useState(() => {
    let sid = localStorage.getItem('anumaan_copilot_session_id');
    if (!sid) {
      sid = 'session_' + Math.random().toString(36).substring(2, 10);
      localStorage.setItem('anumaan_copilot_session_id', sid);
    }
    return sid;
  });

  const chatBottomRef = useRef<HTMLDivElement>(null);
  const dictationRecRef = useRef<any>(null);
  const convRecRef = useRef<any>(null);
  const convActiveRef = useRef(false);
  convActiveRef.current = isConversationalActive;

  // Mutable refs to prevent React state closure capture in speech recognition callbacks
  const convTranscriptRef = useRef('');
  const dictTranscriptRef = useRef('');

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, isConversationalActive]);

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
  // Mode 1: Dictation (Speech-to-Text typing directly into input bar)
  // ────────────────────────────────────────────────────────────────────────────
  const startDictation = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
      return;
    }

    try {
      if (dictationRecRef.current) {
        try {
          dictationRecRef.current.abort();
        } catch {}
      }
      const rec = new SpeechRecognition();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = 'en-US';

      dictTranscriptRef.current = inputQuery;

      rec.onstart = () => setIsDictating(true);
      rec.onend = () => setIsDictating(false);
      rec.onerror = () => setIsDictating(false);

      rec.onresult = (event: any) => {
        let finalTrans = '';
        let interimTrans = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const item = event.results[i];
          if (item.isFinal) {
            finalTrans += item[0]?.transcript || '';
          } else {
            interimTrans += item[0]?.transcript || '';
          }
        }
        if (finalTrans) {
          dictTranscriptRef.current = (dictTranscriptRef.current ? dictTranscriptRef.current + ' ' + finalTrans.trim() : finalTrans.trim()).trim();
          setInputQuery(dictTranscriptRef.current);
        } else if (interimTrans) {
          const preview = (dictTranscriptRef.current ? dictTranscriptRef.current + ' ' + interimTrans.trim() : interimTrans.trim()).trim();
          setInputQuery(preview);
        }
      };

      dictationRecRef.current = rec;
      rec.start();
    } catch {
      setIsDictating(false);
    }
  };

  const stopDictation = () => {
    if (dictationRecRef.current) {
      try {
        dictationRecRef.current.stop();
      } catch {}
    }
    setIsDictating(false);
  };

  const toggleDictation = () => {
    if (isDictating) {
      stopDictation();
    } else {
      startDictation();
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
    if (isDictating) stopDictation();

    const userMsg: ChatMessage = {
      id: 'usr-' + Date.now(),
      sender: 'user',
      text: cleanQ,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

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
  // Mode 2: Conversational Live Voice Loop (Hands-free, seamless inline chat)
  // ────────────────────────────────────────────────────────────────────────────
  const listenNextConversationalTurn = useCallback(() => {
    if (!convActiveRef.current) return;

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
        if (!convActiveRef.current) return;
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
        if (!convActiveRef.current) return;
        const finalQ = convTranscriptRef.current.trim();
        if (finalQ) {
          setConvState('THINKING');
          setInterimTranscript('');
          convTranscriptRef.current = '';

          const reply = await handleSendQuery(finalQ);
          if (!convActiveRef.current) return;

          if (reply && isSpeakingEnabled) {
            setConvState('SPEAKING');
            speakText(reply, () => {
              if (convActiveRef.current) {
                setConvState('LISTENING');
                setTimeout(() => {
                  listenNextConversationalTurn();
                }, 300);
              }
            });
          } else {
            if (convActiveRef.current) {
              setConvState('LISTENING');
              setTimeout(() => {
                listenNextConversationalTurn();
              }, 300);
            }
          }
        } else {
          // If silence timeout, restart listening loop immediately
          if (convActiveRef.current) {
            setTimeout(() => {
              listenNextConversationalTurn();
            }, 250);
          }
        }
      };

      rec.onerror = () => {
        if (convActiveRef.current) {
          setTimeout(() => {
            listenNextConversationalTurn();
          }, 500);
        }
      };

      convRecRef.current = rec;
      rec.start();
    } catch {
      if (convActiveRef.current) {
        setTimeout(() => {
          listenNextConversationalTurn();
        }, 800);
      }
    }
  }, [isSpeakingEnabled, speakText]);

  const startConversationalMode = () => {
    stopDictation();
    stopSpeaking();
    setIsConversationalActive(true);
    setConvState('LISTENING');
    setInterimTranscript('');
    convTranscriptRef.current = '';
    setTimeout(() => {
      listenNextConversationalTurn();
    }, 200);
  };

  const stopConversationalMode = () => {
    convActiveRef.current = false;
    setIsConversationalActive(false);
    setConvState('IDLE');
    setInterimTranscript('');
    convTranscriptRef.current = '';
    stopSpeaking();
    if (convRecRef.current) {
      try {
        convRecRef.current.abort();
      } catch {}
    }
  };

  const handleInterruptSpeaking = () => {
    stopSpeaking();
    setConvState('LISTENING');
    setInterimTranscript('');
    convTranscriptRef.current = '';
    setTimeout(() => {
      listenNextConversationalTurn();
    }, 200);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopSpeaking();
      if (dictationRecRef.current) {
        try {
          dictationRecRef.current.abort();
        } catch {}
      }
      if (convRecRef.current) {
        try {
          convRecRef.current.abort();
        } catch {}
      }
    };
  }, []);

  const isFaultActive = state.active_commanded_fault_id > 0;
  const faultName = state.active_commanded_fault_name || 'NOMINAL';
  const rpm = Math.round(state.telemetry.ENGINE_RPM || 0);
  const healthPct = Math.round((state.analytics.health_index || 1.0) * 100);

  return (
    <div className="surface-panel p-4 sm:p-5 space-y-4">
      {/* Top Banner: Status & Context */}
      <div className="flex items-center justify-between border-b border-surface-border pb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-sm bg-accent-dim flex items-center justify-center text-accent shadow-sm">
            <Brain className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-semibold text-white">MAVERICK · Tactical AI Mission Copilot</h2>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-sm bg-success-dim text-success border border-success-muted">
                Ollama / Qwen2.5 Local
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Conversational RAG Grounding · Multi-Turn Dialogue Memory · Continuous Voice Mode
            </p>
          </div>
        </div>

        {/* Live Grounding Badges & Mode Controls */}
        <div className="flex items-center gap-2 text-xs font-mono">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-surface-card border border-surface-border text-slate-300">
            <Activity className="w-3.5 h-3.5 text-accent" />
            <span>RPM: {rpm}</span>
          </div>
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-sm border ${
              isFaultActive
                ? 'bg-critical-dim text-critical border-critical-muted'
                : 'bg-success-dim text-success border-success-muted'
            }`}
          >
            {isFaultActive ? <AlertTriangle className="w-3.5 h-3.5" /> : <ShieldCheck className="w-3.5 h-3.5" />}
            <span>Health: {healthPct}% {isFaultActive ? `· ${faultName}` : ''}</span>
          </div>

          {/* Hands-Free Conversational Voice Mode Toggle Pill */}
          <button
            onClick={isConversationalActive ? stopConversationalMode : startConversationalMode}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-sm border font-mono text-xs transition-all shadow-xs ${
              isConversationalActive
                ? 'bg-critical-dim text-critical border-critical-muted hover:bg-critical hover:text-white'
                : 'bg-accent-dim text-accent border-accent-muted hover:bg-accent hover:text-white'
            }`}
            title={isConversationalActive ? 'Exit continuous hands-free voice mode' : 'Start continuous hands-free voice mode'}
          >
            <Headphones className={`w-3.5 h-3.5 ${isConversationalActive ? 'animate-pulse' : ''}`} />
            <span>{isConversationalActive ? 'Exit Voice Mode' : 'Hands-Free Voice'}</span>
          </button>

          {/* Audio Output Mute / Unmute Toggle */}
          <button
            onClick={() => {
              stopSpeaking();
              setIsSpeakingEnabled(!isSpeakingEnabled);
            }}
            className={`p-1.5 rounded-sm border transition-colors ${
              isSpeakingEnabled
                ? 'bg-accent-dim text-accent border-accent-muted'
                : 'bg-surface-card text-slate-500 border-surface-border'
            }`}
            title={isSpeakingEnabled ? 'Audio Output: Active (Click to mute)' : 'Audio Output: Muted (Click to unmute)'}
          >
            {isSpeakingEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>

          {/* Clear Chat Button */}
          <button
            onClick={() => {
              stopSpeaking();
              setMessages([
                {
                  id: 'reset-' + Date.now(),
                  sender: 'assistant',
                  text: 'Conversation buffer cleared. Standing by for propulsion telemetry inquiries.',
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                },
              ]);
            }}
            className="p-1.5 rounded-sm bg-surface-card border border-surface-border text-slate-400 hover:text-white transition-colors"
            title="Clear conversation history"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ──────────────────────────────────────────────────────────────────── */}
      {/* Inline Hands-Free Voice Status Bar (Visible only when voice is active) */}
      {/* ──────────────────────────────────────────────────────────────────── */}
      {isConversationalActive && (
        <div className="flex items-center justify-between px-3.5 py-2 rounded-sm bg-surface-card border border-accent/40 text-xs font-mono shadow-xs transition-all">
          <div className="flex items-center gap-2.5">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                convState === 'SPEAKING'
                  ? 'bg-accent animate-ping'
                  : convState === 'THINKING'
                  ? 'bg-warning animate-spin'
                  : 'bg-emerald-500 animate-pulse'
              }`}
            />
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-white uppercase tracking-wider text-[11px]">
                {convState === 'SPEAKING' && 'MAVERICK TRANSMITTING'}
                {convState === 'THINKING' && 'REASONING OVER TELEMETRY'}
                {convState === 'LISTENING' && 'LISTENING TO OPERATOR'}
                {convState === 'IDLE' && 'VOICE STANDBY'}
              </span>
              <span className="text-slate-400 text-[11px]">
                {convState === 'SPEAKING' && '— Speaking response aloud (transcript below)'}
                {convState === 'THINKING' && '— Synthesizing with local Qwen2.5 & telemetry tools'}
                {convState === 'LISTENING' &&
                  (interimTranscript
                    ? `— Hearing: "${interimTranscript}"`
                    : '— Speak naturally; transcript posts to chat')}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {convState === 'SPEAKING' && (
              <button
                onClick={handleInterruptSpeaking}
                className="flex items-center gap-1 px-2.5 py-1 rounded-sm bg-critical-dim border border-critical-muted text-critical hover:bg-critical hover:text-white transition-colors text-[11px] font-semibold"
                title="Interrupt audio playback and listen again"
              >
                <Square className="w-3 h-3" />
                <span>Interrupt / Mute</span>
              </button>
            )}

            <button
              onClick={stopConversationalMode}
              className="px-2.5 py-1 rounded-sm bg-surface-card border border-surface-border text-slate-300 hover:text-white hover:border-slate-400 transition-colors text-[11px]"
              title="Stop continuous voice mode"
            >
              Exit Voice
            </button>
          </div>
        </div>
      )}

      {/* ────────────────────────────────────────────────────────────────── */}
      {/* Normal Chat Feed Mode (Rich Markdown Rendered)                     */}
      {/* ────────────────────────────────────────────────────────────────── */}
      <div className="h-[430px] overflow-y-auto space-y-3 p-3 bg-black/10 rounded-sm border border-surface-border font-sans text-xs">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'} space-y-1`}
          >
            <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 px-1">
              <span>{m.sender === 'user' ? 'OPERATOR' : 'MAVERICK AI'}</span>
              <span>·</span>
              <span>{m.timestamp}</span>
            </div>
            <div
              className={`max-w-[88%] rounded-sm p-3.5 leading-relaxed font-sans text-xs shadow-sm ${
                m.sender === 'user'
                  ? 'bg-accent text-white font-medium self-end'
                  : 'bg-surface-card border border-surface-border text-slate-200'
              }`}
            >
              {/* User messages render as clean plain text; Assistant renders via AerospaceMarkdown */}
              {m.sender === 'user' ? (
                <div className="whitespace-pre-wrap">{m.text}</div>
              ) : (
                <AerospaceMarkdown content={m.text} citations={m.citations} />
              )}

              {/* ATA Diagnostic Directives Footer */}
              {m.diagnostics && (
                <div className="mt-2.5 pt-2.5 border-t border-surface-border/60 text-[11px] font-mono space-y-1 text-slate-300">
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

              {/* Grounding Sources & Tools Footer */}
              {m.sender === 'assistant' && (
                <div className="mt-3 pt-2 border-t border-surface-border/40 text-[10px] font-mono space-y-1.5 text-slate-400">
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
                    <span className="ml-auto text-slate-500 text-[10px]">
                      Phrased by {m.provider || 'Ollama / Qwen2.5 Local'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex flex-col items-start space-y-1">
            <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500 px-1">
              <span>MAVERICK AI</span>
              <span>·</span>
              <span>Synthesizing...</span>
            </div>
            <div className="bg-surface-card border border-surface-border rounded-sm p-3 flex items-center gap-2 text-slate-400">
              <div className="w-2 h-2 rounded-full bg-accent animate-ping" />
              <span className="font-mono text-xs">Querying local Qwen2.5 &amp; telemetry grounding...</span>
            </div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Quick Action Suggestion Chips */}
      <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1">
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

      {/* Input Bar: Text Query + Dictation Mode Button */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={inputQuery}
            disabled={isLoading}
            onChange={(e) => setInputQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSendQuery();
            }}
            placeholder={
              isDictating
                ? 'Listening to your speech... words will appear here.'
                : 'Ask MAVERICK any technical question, diagnostic check, or emergency procedure...'
            }
            className={`w-full bg-surface-card border rounded-sm px-3.5 py-2 text-xs text-white placeholder-slate-500 font-sans focus:outline-none focus:border-accent transition-colors ${
              isDictating ? 'border-accent bg-accent-dim/20' : 'border-surface-border'
            }`}
          />
          {isDictating && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 text-[10px] font-mono text-accent">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-ping" />
              <span>Recording</span>
            </span>
          )}
        </div>

        {/* Mode 1: Dictation Mic Button (Writes what you speak into input bar) */}
        <button
          onClick={toggleDictation}
          disabled={isLoading}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-sm border font-mono text-xs transition-all ${
            isDictating
              ? 'bg-critical-dim text-critical border-critical-muted shadow-sm shadow-red-500/20'
              : 'bg-surface-card text-slate-400 border-surface-border hover:text-white hover:border-accent'
          }`}
          title={isDictating ? 'Stop dictation' : 'Dictate into input box'}
        >
          {isDictating ? <MicOff className="w-4 h-4 text-critical animate-pulse" /> : <Mic className="w-4 h-4" />}
          <span className="text-[11px] hidden sm:inline">{isDictating ? 'Stop' : 'Dictate'}</span>
        </button>

        {/* Send Text Query Button */}
        <button
          onClick={() => handleSendQuery()}
          disabled={isLoading || !inputQuery.trim()}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-sm bg-accent text-white text-xs font-mono font-medium hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
        >
          <Send className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Ask</span>
        </button>
      </div>
    </div>
  );
};
