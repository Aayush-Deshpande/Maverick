import React, { useRef, useState, useEffect } from 'react';
import './hud-frame.css';

interface HudFrameProps {
  children: React.ReactNode;
  topLabel?: string;
  bottomLabel?: string;
  className?: string;
}

export const HudFrame: React.FC<HudFrameProps> = ({
  children,
  topLabel = 'PROJECT ANUMAAN // DRDO PS-26054',
  bottomLabel = 'K.1321 // Y.0704 // 20Hz TELEMETRY',
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({ width: 0, height: 0 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const updateDims = () => {
      const rect = el.getBoundingClientRect();
      setDimensions({
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      });
    };

    updateDims();
    const observer = new ResizeObserver(updateDims);
    observer.observe(el);

    return () => observer.disconnect();
  }, []);

  const { width: w, height: h } = dimensions;

  const isMobile = w > 0 && w < 580;
  const chamfer = isMobile ? 20 : 30;
  const topNotchW = Math.min(isMobile ? 180 : 260, Math.max(150, w * 0.34));
  const topNotchD = 14;
  const botNotchW = Math.min(isMobile ? 160 : 230, Math.max(140, w * 0.30));
  const botNotchD = 14;
  const sideNotchH = Math.min(isMobile ? 48 : 64, Math.max(38, h * 0.12));
  const sideNotchD = 14;

  let pathD = '';
  if (w > 0 && h > 0) {
    pathD = [
      `M ${chamfer} 0`,
      `L ${w / 2 - topNotchW / 2} 0`,
      `L ${w / 2 - topNotchW / 2} ${topNotchD}`,
      `L ${w / 2 + topNotchW / 2} ${topNotchD}`,
      `L ${w / 2 + topNotchW / 2} 0`,
      `L ${w - chamfer} 0`,
      `L ${w} ${chamfer}`,
      `L ${w} ${h / 2 - sideNotchH / 2}`,
      `L ${w - sideNotchD} ${h / 2 - sideNotchH / 2}`,
      `L ${w - sideNotchD} ${h / 2 + sideNotchH / 2}`,
      `L ${w} ${h / 2 + sideNotchH / 2}`,
      `L ${w} ${h - chamfer}`,
      `L ${w - chamfer} ${h}`,
      `L ${w / 2 + botNotchW / 2} ${h}`,
      `L ${w / 2 + botNotchW / 2} ${h - botNotchD}`,
      `L ${w / 2 - botNotchW / 2} ${h - botNotchD}`,
      `L ${w / 2 - botNotchW / 2} ${h}`,
      `L ${chamfer} ${h}`,
      `L 0 ${h - chamfer}`,
      `L 0 ${h / 2 + sideNotchH / 2}`,
      `L ${sideNotchD} ${h / 2 + sideNotchH / 2}`,
      `L ${sideNotchD} ${h / 2 - sideNotchH / 2}`,
      `L 0 ${h / 2 - sideNotchH / 2}`,
      `L 0 ${chamfer}`,
      'Z',
    ].join(' ');
  }

  return (
    <div ref={containerRef} className={`hud-frame-container ${className}`}>
      {/* Precision Scalable SVG HUD Frame */}
      {w > 0 && h > 0 && (
        <svg
          className="hud-frame-svg"
          width={w}
          height={h}
          viewBox={`0 0 ${w} ${h}`}
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          {/* Main heavy structural stroke */}
          <path
            d={pathD}
            fill="none"
            stroke="#0a0f14"
            strokeWidth="4"
            strokeLinejoin="miter"
            strokeMiterlimit="4"
          />

          {/* Top Notch: Solid Black Recessed Pocket Tab */}
          <polygon
            points={`
              ${w / 2 - topNotchW / 2},0 
              ${w / 2 - topNotchW / 2},${topNotchD} 
              ${w / 2 + topNotchW / 2},${topNotchD} 
              ${w / 2 + topNotchW / 2},0
            `}
            fill="#0a0f14"
          />
          <text
            x={w / 2}
            y={topNotchD - 3.5}
            fill="#f5f7fa"
            fontFamily="'PixelCode', 'JetBrains Mono', monospace"
            fontSize={isMobile ? "8" : "9.5"}
            fontWeight="700"
            letterSpacing="1.2"
            textAnchor="middle"
          >
            {topLabel}
          </text>

          {/* Bottom Notch: Solid Black Recessed Pocket Tab */}
          <polygon
            points={`
              ${w / 2 - botNotchW / 2},${h} 
              ${w / 2 - botNotchW / 2},${h - botNotchD} 
              ${w / 2 + botNotchW / 2},${h - botNotchD} 
              ${w / 2 + botNotchW / 2},${h}
            `}
            fill="#0a0f14"
          />
          <text
            x={w / 2}
            y={h - 3.5}
            fill="#a8b6c1"
            fontFamily="'PixelCode', 'JetBrains Mono', monospace"
            fontSize={isMobile ? "7.5" : "8.5"}
            fontWeight="600"
            letterSpacing="1"
            textAnchor="middle"
          >
            {bottomLabel}
          </text>

          {/* Left Inward Notch: Solid black geometric tab & accent bracket */}
          <rect
            x={0}
            y={h / 2 - sideNotchH / 2}
            width={sideNotchD}
            height={sideNotchH}
            fill="#0a0f14"
          />
          <path
            d={`M ${sideNotchD + 6} ${h / 2 - 14} h -4 v 28 h 4`}
            stroke="#0a0f14"
            strokeWidth="2"
            fill="none"
          />

          {/* Right Inward Notch: Solid black geometric tab & accent bracket */}
          <rect
            x={w - sideNotchD}
            y={h / 2 - sideNotchH / 2}
            width={sideNotchD}
            height={sideNotchH}
            fill="#0a0f14"
          />
          <path
            d={`M ${w - sideNotchD - 6} ${h / 2 - 14} h 4 v 28 h -4`}
            stroke="#0a0f14"
            strokeWidth="2"
            fill="none"
          />

          {/* Outer Chamfer Alignment Ticks (all 4 corners) */}
          <line x1={chamfer - 10} y1={-2} x2={-2} y2={chamfer - 10} stroke="#0a0f14" strokeWidth="2" />
          <line x1={w - chamfer + 10} y1={-2} x2={w + 2} y2={chamfer - 10} stroke="#0a0f14" strokeWidth="2" />
          <line x1={w + 2} y1={h - chamfer + 10} x2={w - chamfer + 10} y2={h + 2} stroke="#0a0f14" strokeWidth="2" />
          <line x1={-2} y1={h - chamfer + 10} x2={chamfer - 10} y2={h + 2} stroke="#0a0f14" strokeWidth="2" />

          {/* Precision Corner Crosshair Reticles */}
          <path
            d={`
              M ${chamfer - 6} ${chamfer + 2} h 6 m -3 -3 v 6 
              M ${w - chamfer + 6} ${chamfer + 2} h -6 m 3 -3 v 6
              M ${chamfer - 6} ${h - chamfer - 2} h 6 m -3 -3 v 6
              M ${w - chamfer + 6} ${h - chamfer - 2} h -6 m 3 -3 v 6
            `}
            stroke="rgba(10, 15, 20, 0.35)"
            strokeWidth="1.2"
            fill="none"
          />
        </svg>
      )}

      {/* Cyberpunk HUD Top Info Header */}
      <div className="hud-tech-meta-top" aria-hidden="true">
        <div className="hud-meta-left">
          <span className="hud-meta-wave">∿∿∿ ON</span>
          <span className="hud-meta-plus">+++</span>
          <span className="hud-meta-tag">&lt;AERO_TWIN: PROPULSION&gt;</span>
        </div>
        <div className="hud-meta-right">
          <span className="hud-meta-tag">SYS_STAT // NOMINAL</span>
          <span className="hud-meta-mode">TACTICAL HUD</span>
        </div>
      </div>

      {/* Inner Content Area */}
      <div className="hud-inner-content">
        {children}
      </div>
    </div>
  );
};
