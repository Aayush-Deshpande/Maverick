import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { ZoomIn, ZoomOut, RotateCcw, Copy, Check, Maximize2, Minimize2, X } from 'lucide-react';

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
        primaryColor: '#fafaf9',
        primaryBorderColor: '#78716c',
        primaryTextColor: '#1c1917',
        lineColor: '#57534e',
        secondaryColor: '#f5f5f4',
        tertiaryColor: '#ffffff',
        edgeLabelBackground: '#ffffff',
        fontFamily: 'Inter, -apple-system, sans-serif',
        fontSize: '13px',
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
        padding: 16,
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
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  useEffect(() => {
    ensureMermaidInit();
    let isMounted = true;

    async function renderChart() {
      try {
        setError(null);
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

  const toolbar = (
    <div className="flex items-center justify-between px-3.5 py-2 border-b border-stone-200 bg-stone-50 text-stone-600 font-mono text-[11px]">
      <div className="flex items-center gap-2">
        <span className="size-1.5 rounded-full bg-blue-600"></span>
        <span className="uppercase tracking-wider font-semibold text-stone-800">System Architecture Diagram</span>
        <span className="text-stone-300 hidden sm:inline">|</span>
        <span className="text-stone-500 font-sans text-xs hidden sm:inline">Interactive Blueprint</span>
      </div>

      <div className="flex items-center gap-1">
        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          className="p-1.5 hover:bg-stone-200 rounded text-stone-600 hover:text-stone-900 transition-colors"
        >
          <ZoomOut size={13} />
        </button>
        <span className="text-[10px] tabular-nums text-stone-500 px-1 font-mono">{Math.round(zoom * 100)}%</span>
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
        <button
          onClick={() => setIsFullscreen(!isFullscreen)}
          title={isFullscreen ? "Close Fullscreen" : "Fullscreen View"}
          className="p-1.5 hover:bg-stone-200 rounded text-stone-600 hover:text-stone-900 transition-colors ml-0.5"
        >
          {isFullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
        </button>
      </div>
    </div>
  );

  const canvas = (
    <div
      ref={containerRef}
      className="relative p-6 overflow-x-auto bg-white flex items-center justify-center min-h-[180px] custom-scrollbar"
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
  );

  return (
    <>
      <figure className={`my-8 border border-stone-200 bg-white rounded-lg shadow-xs overflow-hidden ${className}`}>
        {toolbar}
        {canvas}
        {caption && (
          <figcaption className="px-4 py-2.5 bg-stone-50 border-t border-stone-200 text-xs text-stone-600 font-sans italic text-center">
            {caption}
          </figcaption>
        )}
      </figure>

      {/* Fullscreen Expand Overlay */}
      {isFullscreen && (
        <div className="fixed inset-0 z-50 bg-stone-950/80 backdrop-blur-xs flex flex-col p-4 sm:p-8">
          <div className="flex-1 bg-white rounded-lg border border-stone-200 flex flex-col overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between px-4 py-3 border-b border-stone-200 bg-stone-50">
              <span className="font-mono text-xs uppercase tracking-wider font-bold text-stone-800">
                Fullscreen Architecture Inspector
              </span>
              <button
                onClick={() => setIsFullscreen(false)}
                className="p-1.5 hover:bg-stone-200 rounded text-stone-700 transition-colors"
                title="Close [Esc]"
              >
                <X size={16} />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-8 flex items-center justify-center custom-scrollbar">
              <div
                style={{ transform: `scale(${zoom * 1.3})`, transformOrigin: 'center center' }}
                dangerouslySetInnerHTML={{ __html: svgContent }}
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
};
