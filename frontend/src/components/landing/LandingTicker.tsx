import React, { useState, useEffect } from 'react';

export const LandingTicker: React.FC = () => {
  const [tickerData, setTickerData] = useState({
    rpm: 2350,
    map: 1.95,
    cht3: 139.1,
    egt3: 684.0,
    oilTemp: 92.4,
    oilPress: 4.25,
    rail: 1610,
    rul: 450.0,
    residual: 0.03,
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setTickerData(() => ({
        rpm: Math.round(2350 + (Math.random() - 0.5) * 16),
        map: Number((1.95 + (Math.random() - 0.5) * 0.02).toFixed(2)),
        cht3: Number((139.1 + (Math.random() - 0.5) * 0.4).toFixed(1)),
        egt3: Number((684.0 + (Math.random() - 0.5) * 1.2).toFixed(1)),
        oilTemp: Number((92.4 + (Math.random() - 0.5) * 0.2).toFixed(1)),
        oilPress: Number((4.25 + (Math.random() - 0.5) * 0.04).toFixed(2)),
        rail: Math.round(1610 + (Math.random() - 0.5) * 8),
        rul: 450.0,
        residual: Number((0.03 + (Math.random() - 0.5) * 0.008).toFixed(3)),
      }));
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full bg-[#05070c] border-b border-white/[0.08] text-[10px] font-mono py-1.5 px-4 overflow-x-auto select-none z-50 relative flex items-center justify-between text-slate-400 gap-6 whitespace-nowrap shadow-sm">
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-1.5 text-cyan-400 font-bold">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
          <span>TWIN SYNC ACTIVE</span>
        </div>
        <div className="flex items-center gap-1 text-slate-300">
          <span className="text-slate-500">RPM:</span>
          <span className="text-cyan-300 font-semibold">{tickerData.rpm.toLocaleString()}</span>
        </div>
        <div className="flex items-center gap-1 text-slate-300">
          <span className="text-slate-500">MAP:</span>
          <span className="text-cyan-300 font-semibold">{tickerData.map} bar</span>
        </div>
        <div className="flex items-center gap-1 text-slate-300">
          <span className="text-slate-500">CHT3:</span>
          <span className="text-cyan-300 font-semibold">{tickerData.cht3}°C</span>
        </div>
        <div className="flex items-center gap-1 text-slate-300">
          <span className="text-slate-500">EGT3:</span>
          <span className="text-cyan-300 font-semibold">{tickerData.egt3}°C</span>
        </div>
        <div className="flex items-center gap-1 text-slate-300">
          <span className="text-slate-500">OIL:</span>
          <span className="text-cyan-300 font-semibold">{tickerData.oilTemp}°C / {tickerData.oilPress} bar</span>
        </div>
        <div className="flex items-center gap-1 text-slate-300">
          <span className="text-slate-500">RAIL:</span>
          <span className="text-cyan-300 font-semibold">{tickerData.rail} bar</span>
        </div>
        <div className="flex items-center gap-1 text-slate-300">
          <span className="text-slate-500">RUL (P50):</span>
          <span className="text-cyan-300 font-semibold">{tickerData.rul} h</span>
        </div>
        <div className="flex items-center gap-1 text-slate-300">
          <span className="text-slate-500">RESIDUAL:</span>
          <span className="text-cyan-300 font-semibold">{tickerData.residual} σ</span>
        </div>
      </div>

      <div className="hidden lg:flex items-center gap-3 text-[9px] text-slate-500 font-mono">
        <span>STANAG-4586 LINK</span>
        <span>•</span>
        <span>20 Hz SYNCHRONOUS</span>
      </div>
    </div>
  );
};
