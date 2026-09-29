import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { ZoomIn, ZoomOut, RotateCcw, Copy, Check } from 'lucide-react';

interface MermaidDiagramProps {
  chart: string;
  caption?: string;
  className?: string;
}

let mermaidInitialized = false;

function ensureMermaidInit() {
  if (!mermaidInitialized) {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'base',
      themeVariables: {
        background: '#ffffff',
        primaryColor: '#f5f5f4',
        primaryBorderColor: '#57534e',
        primaryTextColor: '#1c1917',
        lineColor: '#57534e',
        secondaryColor: '#fafaf9',
        tertiaryColor: '#ffffff',
        edgeLabelBackground: '#ffffff',
        fontFamily: 'Inter, -apple-system, sans-serif',
        fontSize: '12px',
        clusterBkg: '#fafaf9',
        clusterBorder: '#d6d3d1',
        titleColor: '#1c1917',
        nodeBorder: '#78716c',
        nodeTextColor: '#1c1917',
        mainBkg: '#ffffff',
      },
      flowchart: {
        curve: 'basis',
        htmlLabels: true,
        padding: 14,
        useMaxWidth: false,
      },
      securityLevel: 'loose',
    });
    mermaidInitialized = true;
  }
}

export const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ chart, caption, className = '' }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>('');
  const [zoom, setZoom] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const chartId = useRef(`mermaid-${Math.random().toString(36).substring(2, 9)}`);

  useEffect(() => {
    ensureMermaidInit();
    let isMounted = true;

    async function renderChart() {
      try {
        setError(null);
        // Clean up markdown fences or extraneous tokens if present and sanitize &
        const cleanChart = chart
          .replace(/^```mermaid\s*/i, '')
          .replace(/```\s*$/, '')
          .replace(/&(?![a-zA-Z0-9#]+;)/g, 'and')
          .trim();

        if (!cleanChart) return;

        const uniqueRenderId = `mmd-${Math.random().toString(36).substring(2, 9)}-${Date.now()}`;
        const { svg } = await mermaid.render(uniqueRenderId, cleanChart);
        if (isMounted) {
          setSvgContent(svg);
        }
      } catch (err: any) {
        console.warn('Mermaid render error:', err);
        if (isMounted) {
          setError('Failed to render diagram');
        }
      }
    }

    renderChart();
    return () => {
      isMounted = false;
    };
  }, [chart]);

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.15, 2.5));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.15, 0.5));
  const handleResetZoom = () => setZoom(1);

  const handleCopySvg = async () => {
    if (!svgContent) return;
    try {
      await navigator.clipboard.writeText(svgContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  };

  return (
    <figure className={`my-8 border border-stone-200 bg-white rounded-xs overflow-hidden ${className}`}>
      {/* Control Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-stone-200 bg-stone-50 text-stone-600 font-mono text-[11px]">
        <div className="flex items-center gap-2">
          <span className="inline-block size-1.5 rounded-full bg-stone-400"></span>
          <span className="uppercase tracking-wider font-medium text-stone-700">Architecture Diagram</span>
          <span className="text-stone-400">|</span>
          <span className="text-stone-500 font-sans text-xs">Monochrome Technical View</span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={handleZoomOut}
            title="Zoom Out"
            className="p-1.5 hover:bg-stone-200 rounded text-stone-600 hover:text-stone-900 transition-colors"
          >
            <ZoomOut size={13} />
          </button>
          <span className="text-[10px] tabular-nums text-stone-500 px-1">{Math.round(zoom * 100)}%</span>
          <button
            onClick={handleZoomIn}
            title="Zoom In"
            className="p-1.5 hover:bg-stone-200 rounded text-stone-600 hover:text-stone-900 transition-colors"
          >
            <ZoomIn size={13} />
          </button>
          <button
            onClick={handleResetZoom}
            title="Reset Zoom"
            className="p-1.5 hover:bg-stone-200 rounded text-stone-600 hover:text-stone-900 transition-colors"
          >
            <RotateCcw size={13} />
          </button>
          <div className="h-3 w-px bg-stone-200 mx-1" />
          <button
            onClick={handleCopySvg}
            title="Copy SVG code"
            className="p-1.5 hover:bg-stone-200 rounded text-stone-600 hover:text-stone-900 transition-colors flex items-center gap-1"
          >
            {copied ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
          </button>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div
        ref={containerRef}
        className="relative p-6 overflow-x-auto bg-white flex items-center justify-center min-h-[160px]"
      >
        {error ? (
          <div className="text-xs font-mono text-stone-500 p-4 border border-dashed border-stone-200 rounded">
            Diagram syntax: review console
          </div>
        ) : (
          <div
            style={{ transform: `scale(${zoom})`, transformOrigin: 'top center', transition: 'transform 0.15s ease' }}
            dangerouslySetInnerHTML={{ __html: svgContent }}
            className="mermaid-wrapper max-w-full"
          />
        )}
      </div>

      {caption && (
        <figcaption className="px-4 py-2.5 bg-stone-50 border-t border-stone-200 text-xs text-stone-600 font-sans italic text-center">
          {caption}
        </figcaption>
      )}
    </figure>
  );
};
