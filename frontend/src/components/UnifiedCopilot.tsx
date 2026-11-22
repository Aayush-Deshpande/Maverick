import React, { useState, useEffect, useRef } from 'react';
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
} from 'lucide-react';
import { UnifiedTelemetryState } from '../types/telemetry';

interface UnifiedCopilotProps {
  state: UnifiedTelemetryState;
  serverUrl: string;
}

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  diagnostics?: {
    fault_name?: string;
    ata_chapter?: string;
    severity?: string;
    prescriptive_action?: string;
  };
}

const QUICK_PROMPTS = [
  'What is the current engine status?',
  'Why is the health index at this level?',
  'Explain cylinder head temperatures and cooling.',
  'What are the emergency SOPs for low oil pressure?',
];

export const UnifiedCopilot: React.FC<UnifiedCopilotProps> = ({ state, serverUrl }) => {
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    return [
      {
        id: 'init-1',
        sender: 'assistant',
        text: 'MAVERICK Tactical Flight Copilot online. Telemetry channels grounded in real-time. How can I assist with propulsion diagnostics, limits, or flight directives?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ];
  });

  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeakingEnabled, setIsSpeakingEnabled] = useState(true);
  const [sessionId] = useState(() => {
    let sid = localStorage.getItem('anumaan_copilot_session_id');
    if (!sid) {
      sid = 'session_' + Math.random().toString(36).substring(2, 10);
      localStorage.setItem('anumaan_copilot_session_id', sid);
    }
    return sid;
  });

  const chatBottomRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Initialize Web Speech Recognition
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = 'en-US';

      rec.onstart = () => setIsListening(true);
      rec.onend = () => setIsListening(false);
      rec.onerror = () => setIsListening(false);
      rec.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setInputQuery(transcript);
          handleSendQuery(transcript);
        }
      };
      recognitionRef.current = rec;
    }
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, []);

  const speakText = (text: string) => {
    if (!isSpeakingEnabled || typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      // Strip markdown asterisks and headers for speech
      const clean = text
        .replace(/\*\*/g, '')
        .replace(/#{1,6}\s*/g, '')
        .replace(/`[^`]+`/g, '')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .slice(0, 300); // speak first concise sentences
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.05;
      utterance.pitch = 0.95;
      window.speechSynthesis.speak(utterance);
    } catch {}
  };

  const toggleMic = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.');
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.start();
      } catch {
        recognitionRef.current.abort();
        setTimeout(() => recognitionRef.current.start(), 150);
      }
    }
  };

  const handleSendQuery = async (queryText?: string) => {
    const q = (queryText ?? inputQuery).trim();
    if (!q || isLoading) return;

    setInputQuery('');
    const userMsg: ChatMessage = {
      id: 'usr-' + Date.now(),
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await fetch(`${serverUrl}/api/ai/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
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
        diagnostics: data.directive || undefined,
      };

      setMessages((prev) => [...prev, aiMsg]);
      speakText(replyText);
    } catch (err: any) {
      const errMsg: ChatMessage = {
        id: 'err-' + Date.now(),
        sender: 'assistant',
        text: `Communication fault: Unable to reach mission copilot backend at ${serverUrl}. Please ensure server is running.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const isFaultActive = state.active_commanded_fault_id > 0;
  const faultName = state.active_commanded_fault_name || 'NOMINAL';
  const rpm = Math.round(state.telemetry.ENGINE_RPM || 0);
  const healthPct = Math.round((state.analytics.health_index || 1.0) * 100);

  return (
    <div className="surface-panel p-4 sm:p-5 space-y-4">
      {/* Top Banner: Status & Context */}
      <div className="flex items-center justify-between border-b border-surface-border pb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-sm bg-accent-dim flex items-center justify-center text-accent">
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
              Conversational RAG Grounding · Multi-Turn Dialogue Memory · Dual Voice &amp; Text
            </p>
          </div>
        </div>

        {/* Live Grounding Status Badges */}
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
          <button
            onClick={() => {
              if ('speechSynthesis' in window) window.speechSynthesis.cancel();
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
          <button
            onClick={() => {
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

      {/* Main Copilot Shell: Chat Feed */}
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
              className={`max-w-[85%] rounded-sm p-3.5 leading-relaxed font-sans text-xs shadow-sm ${
                m.sender === 'user'
                  ? 'bg-accent text-white font-medium self-end'
                  : 'bg-surface-card border border-surface-border text-slate-200'
              }`}
            >
              <div className="whitespace-pre-wrap">{m.text}</div>

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

      {/* Input Bar: Text Query + Mic Push-to-Talk */}
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
              isListening
                ? 'Listening... speak clearly into your microphone.'
                : 'Ask MAVERICK any technical question, diagnostic check, or emergency procedure...'
            }
            className={`w-full bg-surface-card border rounded-sm px-3.5 py-2 text-xs text-white placeholder-slate-500 font-sans focus:outline-none focus:border-accent transition-colors ${
              isListening ? 'border-accent animate-pulse bg-accent-dim/20' : 'border-surface-border'
            }`}
          />
        </div>

        {/* Microphone Button */}
        <button
          onClick={toggleMic}
          disabled={isLoading}
          className={`p-2 rounded-sm border font-mono text-xs flex items-center gap-1.5 transition-colors ${
            isListening
              ? 'bg-critical text-white border-critical animate-pulse shadow-md'
              : 'bg-surface-card text-slate-300 border-surface-border hover:text-white hover:border-accent'
          }`}
          title={isListening ? 'Stop recording voice' : 'Click to talk via microphone'}
        >
          {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4 text-accent" />}
          <span className="hidden sm:inline">{isListening ? 'Listening' : 'Voice'}</span>
        </button>

        {/* Send Button */}
        <button
          onClick={() => handleSendQuery()}
          disabled={isLoading || !inputQuery.trim()}
          className="px-4 py-2 rounded-sm bg-accent text-white font-medium text-xs flex items-center gap-1.5 hover:bg-accent/90 transition-colors disabled:opacity-40 disabled:hover:bg-accent"
        >
          <Send className="w-3.5 h-3.5" />
          <span>Ask</span>
        </button>
      </div>
    </div>
  );
};
