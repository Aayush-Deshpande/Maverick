import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Info } from 'lucide-react';

export interface InfoTooltipProps {
  title?: string;
  content: React.ReactNode;
  shortcut?: string;
  placement?: 'top' | 'bottom' | 'left' | 'right' | 'auto';
  className?: string;
  iconClassName?: string;
}

/**
 * Minimalist, production-grade aerospace info popover/tooltip.
 * Renders via React Portal directly into document.body to prevent any
 * overflow-hidden clipping or CSS transform coordinate bugs.
 * Automatically clamps to the viewport so text is NEVER cut off.
 */
export const InfoTooltip: React.FC<InfoTooltipProps> = ({
  title,
  content,
  shortcut,
  placement = 'auto',
  className = '',
  iconClassName = 'w-3 h-3 text-slate-400 hover:text-slate-800 transition-colors',
}) => {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<number | null>(null);

  const calculatePosition = () => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const width = 250;
    const padding = 12;

    let left = rect.left;
    let top = rect.top;

    if (placement === 'right' || (placement === 'auto' && rect.left < 300)) {
      // Position to the right of the trigger (ideal for left-aligned aside panels)
      left = rect.right + 8;
      top = rect.top - 10;
    } else if (placement === 'left' || (placement === 'auto' && rect.right > window.innerWidth - 300)) {
      // Position to the left of the trigger
      left = rect.left - width - 8;
      top = rect.top - 10;
    } else if (placement === 'bottom') {
      left = rect.left + rect.width / 2 - width / 2;
      top = rect.bottom + 6;
    } else {
      // Default top
      left = rect.left + rect.width / 2 - width / 2;
      top = rect.top - 90;
    }

    // Viewport clamping: ensures 0px cutoff on all sides
    left = Math.max(padding, Math.min(window.innerWidth - width - padding, left));
    top = Math.max(padding, Math.min(window.innerHeight - 150 - padding, top));

    setCoords({ top, left });
  };

  const handleMouseEnter = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    calculatePosition();
    timeoutRef.current = window.setTimeout(() => {
      calculatePosition();
      setOpen(true);
    }, 100);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = window.setTimeout(() => setOpen(false), 140);
  };

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    calculatePosition();
    setOpen((v) => !v);
  };

  // Close on outside click or Escape key
  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent | TouchEvent) => {
      const target = e.target as Node | null;
      if (
        popoverRef.current &&
        !popoverRef.current.contains(target) &&
        triggerRef.current &&
        !triggerRef.current.contains(target)
      ) {
        setOpen(false);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  return (
    <span
      className={`inline-flex items-center align-middle ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <button
        ref={triggerRef}
        type="button"
        onClick={handleClick}
        aria-label={title ?? 'Information'}
        className="inline-flex items-center justify-center p-0.5 rounded-full hover:bg-black/5 focus:outline-none transition-colors cursor-pointer"
      >
        <Info className={iconClassName} />
      </button>

      {open &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            ref={popoverRef}
            role="tooltip"
            onClick={(e) => e.stopPropagation()}
            onMouseEnter={() => {
              if (timeoutRef.current) clearTimeout(timeoutRef.current);
            }}
            onMouseLeave={handleMouseLeave}
            style={{ top: `${coords.top}px`, left: `${coords.left}px` }}
            className="fixed z-[120] w-[250px] max-w-[calc(100vw-2rem)] rounded-sm border border-surface-border-strong bg-[#fcfbf7] p-2.5 text-xs text-slate-800 shadow-card animate-fade-in pointer-events-auto text-left"
          >
            {title && (
              <div className="flex items-center justify-between gap-2 border-b border-surface-border/60 pb-1 mb-1.5">
                <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-slate-900">
                  {title}
                </span>
                {shortcut && (
                  <kbd className="inline-flex h-4 items-center rounded border border-surface-border bg-surface-card px-1 font-mono text-[9px] text-slate-600">
                    {shortcut}
                  </kbd>
                )}
              </div>
            )}

            <div className="font-sans text-[11px] leading-relaxed text-slate-700">
              {content}
            </div>
          </div>,
          document.body
        )}
    </span>
  );
};
export default InfoTooltip;
