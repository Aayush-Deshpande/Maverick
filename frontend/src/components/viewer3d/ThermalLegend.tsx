import { useMemo } from 'react';
import { getBlackbodyColor } from '../../utils/engineShaders';

export type RawReadingValue = number | { value?: number | null } | null | undefined;

type Props = {
  readings?: Record<string, RawReadingValue> | null;
  chtMax?: number;
  egtMax?: number;
  className?: string;
};

export function getReadingVal(r: RawReadingValue): number | null {
  if (typeof r === 'number') return r;
  if (r && typeof r === 'object' && typeof r.value === 'number') return r.value;
  return null;
}

export default function ThermalLegend({
  readings,
  chtMax = 135,
  egtMax = 950,
  className = '',
}: Props) {
  // Extract live CHTs
  const chts = useMemo(() => {
    const list: Array<{ id: string; label: string; val: number | null }> = [];
    for (let c = 1; c <= 4; c++) {
      const v = getReadingVal(readings?.[`CHT_${c}`] ?? (c === 1 ? readings?.['CHT'] : null));
      list.push({
        id: `cyl_${c}`,
        label: `CYL ${c}`,
        val: typeof v === 'number' ? v : null,
      });
    }
    return list;
  }, [readings]);

  // Extract max EGT
  const egt = useMemo(() => {
    let maxEgt: number | null = null;
    for (let c = 1; c <= 4; c++) {
      const v = getReadingVal(readings?.[`EGT_${c}`]);
      if (typeof v === 'number') {
        maxEgt = maxEgt === null ? v : Math.max(maxEgt, v);
      }
    }
    if (maxEgt === null) {
      const single = getReadingVal(readings?.['EGT']);
      if (typeof single === 'number') maxEgt = single;
    }
    return maxEgt;
  }, [readings]);

  return (
    <div
      className={`surface-panel rounded-sm border border-surface-border p-2.5 sm:p-3 text-xs font-mono bg-[#f7f6f0] text-slate-800 shadow-md ${className}`}
    >
      <div className="flex items-center justify-between gap-3 border-b border-surface-border pb-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-rose-600 animate-pulse" />
          <span className="font-bold tracking-wider text-slate-900 uppercase">
            Thermal Pyrometry (FLIR)
          </span>
        </div>
        <span className="text-[10px] text-slate-600 font-mono">
          20 Hz Dynamic
        </span>
      </div>

      {/* Cylinder CHT Grid */}
      <div className="mt-2.5 grid grid-cols-2 sm:grid-cols-4 gap-1.5">
        {chts.map((c) => {
          const color =
            c.val !== null ? getBlackbodyColor(c.val, 50, chtMax, false) : null;
          const hex = color ? `#${color.getHexString()}` : '#475569';
          const isOverheat = c.val !== null && c.val >= chtMax;

          return (
            <div
              key={c.id}
              className={`rounded-sm border px-2 py-1.5 flex flex-col justify-between ${
                isOverheat
                  ? 'border-rose-400 bg-rose-50 text-rose-950 shadow-2xs'
                  : 'border-surface-border bg-white text-slate-900 shadow-2xs'
              }`}
            >
              <div className="flex items-center justify-between text-[10px] text-slate-600">
                <span className="font-medium">{c.label}</span>
                <span
                  className="w-2 h-2 rounded-full border border-black/10"
                  style={{ backgroundColor: hex }}
                />
              </div>
              <div className="mt-1 font-bold text-sm text-slate-900">
                {c.val !== null ? `${c.val.toFixed(1)}°C` : 'NO DATA'}
              </div>
            </div>
          );
        })}
      </div>

      {/* Exhaust & Gradient Bar */}
      <div className="mt-2.5 pt-2 border-t border-surface-border flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-[11px]">
          <span className="text-slate-600 font-medium">HOT SECTION / EGT:</span>
          <span className="font-bold text-slate-900 font-mono">
            {egt !== null ? `${egt.toFixed(1)}°C` : 'NO DATA'}
          </span>
          <span className="text-[10px] text-slate-500">
            (Limit: {egtMax}°C)
          </span>
        </div>

        {/* FLIR Incandescence Color Gradient Bar */}
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] text-slate-600 font-mono">40°C</span>
          <div
            className="w-24 sm:w-32 h-2 rounded-xs border border-surface-border"
            style={{
              background:
                'linear-gradient(to right, #334155, #0d9488, #10b981, #f59e0b, #ef4444, #f43f5e, #ffffff)',
            }}
            title="FLIR Thermal Spectrum: Slate (<60°C) -> Teal (85°C) -> Green (100°C) -> Amber (120°C) -> Red (>135°C) -> Incandescent White (>900°C)"
          />
          <span className="text-[9px] text-slate-600 font-mono">950°C</span>
        </div>
      </div>
    </div>
  );
}
