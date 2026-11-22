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
  X,
  Radio,
  Loader2,
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

  // Mode 2: Conversational Live Voice Mode (Hands-free voice dialogue)
  const [isConversationalActive, setIsConversationalActive] = useState(false);
  const [convState, setConvState] = useState<ConversationalState>('IDLE');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [activeVoiceSubtitle, setActiveVoiceSubtitle] = useState('');

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
        dictationRecRef.current.abort();
      }
      const rec = new SpeechRecognition();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = 'en-US';

      rec.onstart = () => setIsDictating(true);
      rec.onend = () => setIsDictating(false);
      rec.onerror = () => setIsDictating(false);

      rec.onresult = (event: any) => {
        let finalTrans = '';
        let interimTrans = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTrans += event.results[i][0].transcript;
          } else {
            interimTrans += event.results[i][0].transcript;
          }
        }
        if (finalTrans) {
          setInputQuery((prev) => (prev ? prev + ' ' + finalTrans.trim() : finalTrans.trim()));
        } else if (interimTrans) {
          setInputQuery((prev) => {
            const base = prev.split(' [dictating:')[0];
            return base ? `${base} [dictating: ${interimTrans}]` : `[dictating: ${interimTrans}]`;
          });
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
      dictationRecRef.current.stop();
    }
    setIsDictating(false);
    // Clean any trailing interim placeholder text
    setInputQuery((prev) => prev.replace(/\s*\[dictating:.*\]/, '').trim());
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
    const cleanQ = rawQ.replace(/\s*\[dictating:.*\]/, '').trim();
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
  // Mode 2: Conversational Live Voice Loop (Hands-free, like ChatGPT voice mode)
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

      rec.onstart = () => {
        if (!convActiveRef.current) return;
        setConvState('LISTENING');
        setInterimTranscript('');
      };

      rec.onresult = (event: any) => {
        let text = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          text += event.results[i][0].transcript;
        }
        setInterimTranscript(text);
      };

      rec.onend = async () => {
        if (!convActiveRef.current) return;
        const finalQ = interimTranscript.trim();
        if (finalQ) {
          setConvState('THINKING');
          setActiveVoiceSubtitle(finalQ);
          const reply = await handleSendQuery(finalQ);
          if (!convActiveRef.current) return;

          if (reply) {
            setConvState('SPEAKING');
            setActiveVoiceSubtitle(reply);
            speakText(reply, () => {
              if (convActiveRef.current) {
                // Short pause before listening again for seamless natural dialogue
                setTimeout(() => {
                  listenNextConversationalTurn();
                }, 350);
              }
            });
          } else {
            listenNextConversationalTurn();
          }
        } else {
          // If silence timeout, restart listening loop if still active
          if (convActiveRef.current && convState === 'LISTENING') {
            setTimeout(() => {
              listenNextConversationalTurn();
            }, 300);
          }
        }
      };

      rec.onerror = () => {
        if (convActiveRef.current) {
          setTimeout(() => {
            listenNextConversationalTurn();
          }, 600);
        }
      };

      convRecRef.current = rec;
      rec.start();
    } catch {
      if (convActiveRef.current) {
        setTimeout(() => {
          listenNextConversationalTurn();
        }, 1000);
      }
    }
  }, [interimTranscript, convState, speakText]);

  const startConversationalMode = () => {
    stopDictation();
    stopSpeaking();
    setIsConversationalActive(true);
    setConvState('LISTENING');
    setActiveVoiceSubtitle('Standing by... speak naturally.');
    setInterimTranscript('');
    setTimeout(() => {
      listenNextConversationalTurn();
    }, 200);
  };

  const stopConversationalMode = () => {
    convActiveRef.current = false;
    setIsConversationalActive(false);
    setConvState('IDLE');
    setInterimTranscript('');
    setActiveVoiceSubtitle('');
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
    setActiveVoiceSubtitle('Interrupted. Listening to operator...');
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
              Conversational RAG Grounding · Multi-Turn Dialogue Memory · Dual Voice Modes
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

          {/* ChatGPT-style Conversational Live Voice Mode Button */}
          <button
            onClick={isConversationalActive ? stopConversationalMode : startConversationalMode}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-sm border font-mono text-xs transition-all shadow-sm ${
              isConversationalActive
                ? 'bg-critical-dim text-critical border-critical-muted hover:bg-critical hover:text-white'
                : 'bg-accent-dim text-accent border-accent-muted hover:bg-accent hover:text-white'
            }`}
            title="Start ChatGPT-style Hands-Free Conversational Voice Mode"
          >
            <Headphones className={`w-3.5 h-3.5 ${isConversationalActive ? 'animate-bounce' : ''}`} />
            <span>{isConversationalActive ? 'Exit Voice Mode' : 'Live Voice Mode'}</span>
          </button>

          {/* Voice Mute Toggle */}
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
            title={isSpeakingEnabled ? 'Mute AI voice output' : 'Enable AI voice output'}
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
      {/* ChatGPT-style Interactive Conversational Voice Stage (Mode 2 Overlay) */}
      {/* ──────────────────────────────────────────────────────────────────── */}
      {isConversationalActive ? (
        <div className="relative h-[440px] bg-gradient-to-b from-[#0a1215] to-[#101b20] rounded-sm border border-accent/40 p-6 flex flex-col items-center justify-between shadow-2xl overflow-hidden">
          {/* Top Status Bar in Voice Mode */}
          <div className="w-full flex items-center justify-between text-xs font-mono border-b border-surface-border/60 pb-3">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-accent animate-ping" />
              <span className="text-accent uppercase tracking-wider font-semibold">
                TACTICAL CONVERSATIONAL VOICE MODE // MAVERICK
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-slate-400 text-[11px]">
                {convState === 'LISTENING' && 'LISTENING TO OPERATOR...'}
                {convState === 'THINKING' && 'SYNTHESIZING TELEMETRY...'}
                {convState === 'SPEAKING' && 'MAVERICK TRANSMITTING...'}
              </span>
              <button
                onClick={stopConversationalMode}
                className="p-1 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
                title="Close voice mode"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Center Orb & Animated Tactical Waveform */}
          <div className="flex flex-col items-center justify-center space-y-6 my-auto">
            <div className="relative flex items-center justify-center">
              {/* Outer Pulsing Wave Rings */}
              <div
                className={`absolute w-36 h-36 rounded-full transition-all duration-700 ${
                  convState === 'SPEAKING'
                    ? 'bg-accent/20 animate-ping opacity-60'
                    : convState === 'LISTENING'
                    ? 'bg-emerald-500/10 animate-pulse'
                    : 'bg-warning/10 animate-pulse'
                }`}
              />
              <div
                className={`absolute w-28 h-28 rounded-full border border-dashed transition-all duration-1000 ${
                  convState === 'THINKING'
                    ? 'border-warning animate-spin'
                    : convState === 'SPEAKING'
                    ? 'border-accent animate-pulse scale-110'
                    : 'border-emerald-500/50'
                }`}
              />

              {/* Main Glowing Center Sphere */}
              <button
                onClick={convState === 'SPEAKING' ? handleInterruptSpeaking : undefined}
                className={`relative z-10 w-20 h-20 rounded-full flex items-center justify-center transition-all duration-500 shadow-lg ${
                  convState === 'SPEAKING'
                    ? 'bg-accent text-black scale-105 shadow-cyan-500/50 cursor-pointer'
                    : convState === 'THINKING'
                    ? 'bg-warning text-black shadow-amber-500/40'
                    : 'bg-emerald-500 text-black shadow-emerald-500/40'
                }`}
                title={convState === 'SPEAKING' ? 'Tap to Interrupt' : 'Tactical Audio Core'}
              >
                {convState === 'SPEAKING' ? (
                  <Radio className="w-8 h-8 animate-pulse" />
                ) : convState === 'THINKING' ? (
                  <Loader2 className="w-8 h-8 animate-spin" />
                ) : (
                  <Mic className="w-8 h-8 animate-pulse" />
                )}
              </button>
            </div>

            {/* Simulated 7-Bar Audio Waveform Equalizer */}
            <div className="flex items-center gap-1.5 h-10">
              {[40, 75, 55, 95, 65, 80, 45].map((h, i) => (
                <div
                  key={i}
                  className={`w-1 rounded-full transition-all duration-200 ${
                    convState === 'SPEAKING'
                      ? 'bg-accent animate-pulse'
                      : convState === 'LISTENING'
                      ? 'bg-emerald-400'
                      : 'bg-slate-600'
                  }`}
                  style={{
                    height:
                      convState === 'SPEAKING'
                        ? `${Math.max(12, Math.round(h * Math.random()))}px`
                        : convState === 'LISTENING'
                        ? '14px'
                        : '8px',
                  }}
                />
              ))}
            </div>

            {/* Status Text / Hint */}
            <div className="text-center">
              <span
                className={`text-xs font-mono uppercase tracking-wider font-semibold ${
                  convState === 'SPEAKING'
                    ? 'text-accent'
                    : convState === 'THINKING'
                    ? 'text-warning'
                    : 'text-emerald-400'
                }`}
              >
                {convState === 'SPEAKING' && '• Speaking — Tap orb or button to interrupt'}
                {convState === 'THINKING' && '• Reasoning over engine state...'}
                {convState === 'LISTENING' && '• Listening — Speak naturally...'}
              </span>
            </div>
          </div>

          {/* Live Subtitle Transcript Card */}
          <div className="w-full max-w-xl bg-black/40 border border-surface-border rounded-sm p-3.5 text-center font-sans">
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-1">
              Live Voice Subtitles
            </div>
            <p className="text-xs text-slate-200 leading-relaxed font-medium italic">
              "{interimTranscript || activeVoiceSubtitle || 'Speak into your microphone. MAVERICK will reply automatically.'}"
            </p>
          </div>

          {/* Bottom Control Actions */}
          <div className="flex items-center gap-3 pt-3">
            {convState === 'SPEAKING' && (
              <button
                onClick={handleInterruptSpeaking}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm bg-critical-dim border border-critical-muted text-critical hover:bg-critical hover:text-white transition-colors text-xs font-mono font-medium"
              >
                <Square className="w-3.5 h-3.5" />
                <span>Tap to Interrupt</span>
              </button>
            )}

            <button
              onClick={stopConversationalMode}
              className="px-4 py-1.5 rounded-sm bg-surface-card border border-surface-border text-slate-300 hover:text-white hover:border-slate-500 transition-colors text-xs font-mono font-medium"
            >
              Exit to Text Chat
            </button>
          </div>
        </div>
      ) : (
        /* ────────────────────────────────────────────────────────────────── */
        /* Normal Chat Feed Mode (Rich Markdown Rendered)                     */
        /* ────────────────────────────────────────────────────────────────── */
        <div className="h-[420px] overflow-y-auto space-y-3 p-3 bg-black/20 rounded-sm border border-surface-border font-sans text-xs">
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
      )}

      {/* Quick Action Suggestion Chips (Visible when not in full voice mode) */}
      {!isConversationalActive && (
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
      )}

      {/* Input Bar: Text Query + Dictation Mode Button */}
      {!isConversationalActive && (
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
                  ? 'Dictation active... speak and your words will appear here.'
                  : 'Ask MAVERICK any technical question, diagnostic check, or emergency procedure...'
              }
              className={`w-full bg-surface-card border rounded-sm px-3.5 py-2 text-xs text-white placeholder-slate-500 font-sans focus:outline-none focus:border-accent transition-colors ${
                isDictating ? 'border-accent bg-accent-dim/20 animate-pulse' : 'border-surface-border'
              }`}
            />
            {isDictating && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 text-[10px] font-mono text-accent">
                <span className="w-1.5 h-1.5 rounded-full bg-accent animate-ping" />
                <span>Dictating</span>
              </span>
            )}
          </div>

          {/* Mode 1: Dictation Mic Button (Writes what you speak into input bar) */}
          <button
            onClick={toggleDictation}
            disabled={isLoading}
            className={`p-2 rounded-sm border transition-all ${
              isDictating
                ? 'bg-critical-dim text-critical border-critical-muted animate-pulse shadow-sm shadow-red-500/20'
                : 'bg-surface-card text-slate-400 border-surface-border hover:text-white hover:border-accent'
            }`}
            title={isDictating ? 'Stop dictation' : 'Normal Voice Mode: Dictate into input box'}
          >
            {isDictating ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
          </button>

          {/* Send Text Query Button */}
          <button
            onClick={() => handleSendQuery()}
            disabled={isLoading || !inputQuery.trim()}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-sm bg-accent text-white text-xs font-mono font-medium hover:bg-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Send</span>
          </button>
        </div>
      )}
    </div>
  );
};
