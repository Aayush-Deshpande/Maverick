import React, { useState, useEffect, useRef } from 'react';
import { Search, X, FileText, ArrowRight } from 'lucide-react';
import { allArticles, DocArticle } from '../lib/content';

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectArticle: (slug: string) => void;
}

export const SearchModal: React.FC<SearchModalProps> = ({ isOpen, onClose, onSelectArticle }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const filteredArticles = query.trim() === ''
    ? allArticles.slice(0, 8)
    : allArticles.filter((art) => {
        const q = query.toLowerCase();
        return (
          art.title.toLowerCase().includes(q) ||
          art.abstract.toLowerCase().includes(q) ||
          art.category.toLowerCase().includes(q) ||
          art.headings.some((h) => h.text.toLowerCase().includes(q))
        );
      }).slice(0, 12);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredArticles.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredArticles.length) % Math.max(1, filteredArticles.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filteredArticles[selectedIndex]) {
        onSelectArticle(filteredArticles[selectedIndex].slug);
        onClose();
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-stone-900/40 backdrop-blur-xs pt-20 px-4">
      <div className="bg-white border border-stone-300 w-full max-w-2xl rounded-xs shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-100">
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-stone-200">
          <Search size={18} className="text-stone-400 mr-3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search ANUMAAN technical documentation, physics models, AI/ML, mission..."
            className="w-full text-stone-900 placeholder:text-stone-400 text-sm outline-none bg-transparent"
          />
          {query && (
            <button onClick={() => setQuery('')} className="p-1 text-stone-400 hover:text-stone-600 mr-2">
              <X size={14} />
            </button>
          )}
          <span className="font-mono text-[10px] text-stone-400 border border-stone-200 px-1.5 py-0.5 rounded bg-stone-50">
            ESC
          </span>
        </div>

        {/* Results List */}
        <div className="max-h-[380px] overflow-y-auto divide-y divide-stone-100 p-1">
          {filteredArticles.length === 0 ? (
            <div className="py-12 text-center text-stone-400 text-sm">
              No documentation articles match &ldquo;{query}&rdquo;
            </div>
          ) : (
            filteredArticles.map((art, idx) => (
              <div
                key={art.slug}
                onClick={() => {
                  onSelectArticle(art.slug);
                  onClose();
                }}
                onMouseEnter={() => setSelectedIndex(idx)}
                className={`flex items-start justify-between p-3 rounded cursor-pointer transition-colors ${
                  idx === selectedIndex ? 'bg-stone-100 text-stone-900' : 'text-stone-700 hover:bg-stone-50'
                }`}
              >
                <div className="flex items-start gap-3 min-w-0 pr-2">
                  <FileText size={16} className={`shrink-0 mt-0.5 ${idx === selectedIndex ? 'text-stone-800' : 'text-stone-400'}`} />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-stone-900 truncate">{art.title}</span>
                      <span className="font-mono text-[9px] uppercase tracking-wider text-stone-400 bg-stone-50 border border-stone-200 px-1.5 py-0.2 rounded">
                        {art.category}
                      </span>
                    </div>
                    {art.abstract && (
                      <p className="text-xs text-stone-500 line-clamp-1 mt-0.5">{art.abstract}</p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span className="font-mono text-[10px] text-stone-400">{art.readTime}</span>
                  <ArrowRight size={13} className={`transition-transform ${idx === selectedIndex ? 'translate-x-0.5 text-stone-800' : 'text-transparent'}`} />
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-stone-200 bg-stone-50 text-[11px] font-mono text-stone-500">
          <div className="flex items-center gap-3">
            <span><kbd className="font-semibold text-stone-700">↑↓</kbd> navigate</span>
            <span><kbd className="font-semibold text-stone-700">ENTER</kbd> select</span>
          </div>
          <span>ANUMAAN Knowledge Base</span>
        </div>
      </div>
    </div>
  );
};
