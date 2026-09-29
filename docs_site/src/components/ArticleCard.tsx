import React from 'react';
import { ArrowRight, ChevronDown, ExternalLink } from 'lucide-react';

export interface CardMetric {
  label: string;
  value: string;
  subtext: string;
}

export interface CardSpec {
  label: string;
  value: string;
}

export interface CardSource {
  title: string;
  meta: string;
  link?: string;
}

interface ArticleCardProps {
  category: string;
  title: string;
  description: string;
  slug: string;
  metrics?: [CardMetric, CardMetric];
  specs?: CardSpec[];
  sources?: CardSource[];
  onNavigate: (slug: string) => void;
  className?: string;
}

export const ArticleCard: React.FC<ArticleCardProps> = ({
  category,
  title,
  description,
  slug,
  metrics,
  specs,
  sources,
  onNavigate,
  className = '',
}) => {
  return (
    <article className={`extend-card-corner-dots group flex h-full min-w-0 flex-col gap-5 rounded-[2px] border border-stone-200/90 bg-white p-5 transition-colors hover:border-stone-300 ${className}`}>
      {/* Card Header & Category Pill */}
      <div className="flex min-w-0 flex-col gap-3.5 pt-1">
        <div className="flex items-center w-fit gap-2 rounded-[2px] border border-stone-300 text-stone-700 px-2 py-0.5 bg-stone-50">
          <div className="rounded-full size-1.5 bg-stone-900"></div>
          <span className="font-mono text-[9px] uppercase tracking-[0.1em] text-stone-700 font-semibold">{category}</span>
        </div>

        <div className="flex min-w-0 flex-col gap-2">
          <button
            onClick={() => onNavigate(slug)}
            className="inline-flex items-baseline gap-2.5 text-stone-900 text-left transition-colors hover:text-stone-600 group/title"
          >
            <h3 className="font-sans text-lg font-semibold text-stone-900 group-hover/title:underline underline-offset-4 leading-snug">
              {title}
            </h3>
            <ArrowRight size={15} className="shrink-0 transition-transform group-hover/title:translate-x-0.5 text-stone-500" />
          </button>
          <p className="text-xs text-stone-600 line-clamp-3 leading-relaxed">
            {description}
          </p>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex min-w-0 flex-1 flex-col gap-4">
        {/* Split Metrics Grid (Extend Style) */}
        {metrics && (
          <dl className="grid grid-cols-2 divide-x divide-stone-200 overflow-hidden rounded-xs border border-stone-200 bg-stone-50">
            <div className="min-w-0 px-3.5 py-3">
              <dt className="font-mono text-[9px] text-stone-500 uppercase tracking-[0.08em] truncate">{metrics[0].label}</dt>
              <dd className="mt-1 font-sans text-xl font-bold text-stone-900 tabular-nums">{metrics[0].value}</dd>
              <dd className="mt-0.5 text-stone-500 text-[10px] truncate">{metrics[0].subtext}</dd>
            </div>
            <div className="min-w-0 px-3.5 py-3">
              <dt className="font-mono text-[9px] text-stone-500 uppercase tracking-[0.08em] truncate">{metrics[1].label}</dt>
              <dd className="mt-1 font-sans text-xl font-bold text-stone-900 tabular-nums">{metrics[1].value}</dd>
              <dd className="mt-0.5 text-stone-500 text-[10px] truncate">{metrics[1].subtext}</dd>
            </div>
          </dl>
        )}

        {/* Collapsible Technical Specs Table */}
        {specs && specs.length > 0 && (
          <details className="group/details min-w-0 overflow-hidden rounded-xs border border-stone-200 bg-white">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 bg-stone-50 px-3.5 py-2.5 font-mono text-[10px] text-stone-600 uppercase tracking-[0.08em] transition-colors hover:bg-stone-100 hover:text-stone-900">
              <span>Technical Specification</span>
              <ChevronDown size={14} className="shrink-0 transition-transform group-open/details:rotate-180" />
            </summary>
            <div className="border-t border-stone-200">
              <table className="w-full table-fixed border-collapse text-left">
                <tbody>
                  {specs.map((spec, i) => (
                    <tr key={i} className="border-b border-stone-100 last:border-b-0">
                      <th className="w-[36%] px-3 py-2 align-top font-mono font-normal text-[10px] text-stone-500 uppercase tracking-[0.08em]">
                        {spec.label}
                      </th>
                      <td className="px-3 py-2 align-top text-xs text-stone-700">
                        {spec.value}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        )}

        {/* Sources / Evidence Links */}
        {sources && sources.length > 0 && (
          <div className="space-y-1.5 mt-auto pt-2">
            <h4 className="font-mono text-[9px] text-stone-500 uppercase tracking-[0.08em]">Evidence &amp; Sources</h4>
            <ul className="flex flex-col gap-px overflow-hidden rounded-xs border border-stone-200 bg-stone-200">
              {sources.map((src, i) => (
                <li key={i}>
                  <div className="flex items-center justify-between gap-2 bg-stone-50 px-3 py-1.5 text-stone-700">
                    <div className="min-w-0">
                      <span className="block font-mono text-[9px] uppercase tracking-[0.08em] text-stone-800 truncate">{src.title}</span>
                      <span className="block text-[11px] text-stone-500 font-mono truncate">{src.meta}</span>
                    </div>
                    <span className="text-[10px] font-mono text-stone-400 uppercase">REPO</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Read Article Action Button */}
        <button
          onClick={() => onNavigate(slug)}
          className="btn-extend-tactile w-full mt-3 group/btn"
        >
          <span>Read Technical Article</span>
          <ArrowRight size={12} className="transition-transform group-hover/btn:translate-x-1 text-stone-600" />
        </button>
      </div>
    </article>
  );
};
