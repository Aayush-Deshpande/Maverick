import React, { useState, useRef, useEffect } from 'react';
import { Info } from 'lucide-react';

export interface InfoTooltipProps {
  title?: string;
  content: React.ReactNode;
  shortcut?: string;
  placement?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
  iconClassName?: string;
}

/**
 * Minimalist, production-grade aerospace info popover/tooltip.
 * Works seamlessly on desktop (hover) and mobile/touch (tap to toggle).
 * Never takes over the full page, ensuring quick, non-intrusive explanations.
 */
export const InfoTooltip: React.FC<InfoTooltipProps> = ({
  title,
  content,
  shortcut,
  placement = 'top',
  className = '',
  iconClassName = 'w-3 h-3 text-slate-400 hover:text-slate-800 transition-colors',
}) => {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<number | null>(null);

  const handleMouseEnter = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = window.setTimeout(() => setOpen(true), 120);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = window.setTimeout(() => setOpen(false), 150);
  };

  // Close on Escape or click outside
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

  // Position classes
  const placementClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-1.5',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-1.5',
    left: 'right-full top-1/2 -translate-y-1/2 mr-1.5',
    right: 'left-full top-1/2 -translate-y-1/2 ml-1.5',
  }[placement];

  return (
    <span
      className={`relative inline-flex items-center align-middle ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <button
        ref={triggerRef}
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        aria-label={title ?? 'Information'}
        className="inline-flex items-center justify-center p-0.5 rounded-full hover:bg-black/5 focus:outline-none transition-colors cursor-pointer"
      >
        <Info className={iconClassName} />
      </button>

      {open && (
        <div
          ref={popoverRef}
          role="tooltip"
          onClick={(e) => e.stopPropagation()}
          className={`absolute z-50 w-64 max-w-[calc(100vw-2rem)] rounded-sm border border-surface-border-strong bg-[#fcfbf7] p-2.5 text-xs text-slate-800 shadow-card animate-fade-in pointer-events-auto text-left ${placementClasses}`}
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
        </div>
      )}
    </span>
  );
};
export default InfoTooltip;
