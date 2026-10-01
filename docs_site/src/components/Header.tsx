import React, { useState } from 'react';
import { Search, Box, Menu, X, Compass, Layers, Database, BookOpen } from 'lucide-react';

interface HeaderProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  onOpenSearch: () => void;
  onOpenModelViewer: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentPath,
  onNavigate,
  onOpenSearch,
  onOpenModelViewer,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: 'Overview', path: 'home' },
    { label: 'Technical Docs', path: 'technical/01-introducing-ps26054' },
    { label: 'Our SIH Journey', path: 'journey' },
    { label: 'Datasets', path: 'technical/15-dataset-strategy' },
    { label: 'Architecture', path: 'technical/04-system-architecture' },
    { label: 'Mission Reliability', path: 'technical/17-mission-reliability' },
  ];

  const handleLinkClick = (path: string) => {
    onNavigate(path);
    setMobileMenuOpen(false);
  };

  const isActive = (path: string) => {
    if (path === 'home') return currentPath === 'home' || currentPath === '';
    return currentPath.startsWith(path);
  };

  return (
    <header className="sticky top-0 z-40 w-full border-b border-stone-200 bg-[#f6f5f3]">
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 sm:border-x border-stone-200/90 bg-[#fafaf9]/95 backdrop-blur-xs">
        <div className="flex items-center justify-between h-14 sm:h-16">
          {/* Logo & Technical Indicator */}
          <div className="flex items-center gap-4">
            <button
              onClick={() => handleLinkClick('home')}
              className="flex items-center gap-2.5 text-left group"
            >
              <div className="size-7 bg-stone-900 text-white font-mono font-bold text-xs flex items-center justify-center rounded-xs tracking-tighter">
                AN
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-stone-950 uppercase tracking-wider group-hover:text-stone-700 transition-colors">
                    ANUMAAN
                  </span>
                  <span className="font-mono text-[9px] bg-stone-200 text-stone-700 px-1.5 py-0.5 rounded uppercase font-semibold">
                    PS-26054
                  </span>
                </div>
                <span className="block font-mono text-[10px] text-stone-500 uppercase tracking-widest leading-none mt-0.5">
                  DRDO SIH · DIGITAL TWIN
                </span>
              </div>
            </button>
          </div>

          {/* Desktop Nav Links */}
          <nav className="hidden lg:flex items-center gap-1">
            {navLinks.map((link) => (
              <button
                key={link.path}
                onClick={() => handleLinkClick(link.path)}
                className={`px-3 py-1.5 rounded font-mono text-[11px] uppercase tracking-wider transition-colors ${
                  isActive(link.path)
                    ? 'bg-stone-200 text-stone-950 font-semibold'
                    : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
                }`}
              >
                {link.label}
              </button>
            ))}
          </nav>

          {/* Right Action Tools */}
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            {/* Search Trigger */}
            <button
              onClick={onOpenSearch}
              className="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-2.5 py-1.5 rounded-sm border border-stone-300 bg-white text-stone-600 hover:text-stone-950 hover:border-stone-400 transition-colors text-xs font-mono"
              title="Search documentation (Cmd+K)"
            >
              <Search size={14} className="text-stone-500" />
              <span className="hidden sm:inline text-stone-500 font-sans text-xs">Search docs</span>
              <kbd className="hidden sm:inline font-mono text-[10px] text-stone-400 border border-stone-200 px-1.5 py-0.2 rounded bg-stone-50">
                ⌘K
              </kbd>
            </button>

            {/* Link to the main ANUMAAN landing page / live console */}
            <a
              href="https://anumaan-7421.vercel.app"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden md:flex items-center gap-1.5 px-2.5 py-1.5 rounded-sm border border-stone-300 bg-white text-stone-700 hover:text-stone-950 hover:border-stone-400 transition-colors font-mono text-[11px] uppercase tracking-wider"
              title="Open the ANUMAAN live console"
            >
              Live Console
            </a>

            {/* 3D Model Twin Inspector Trigger (desktop/tablet) */}
            <button
              onClick={onOpenModelViewer}
              className="hidden sm:flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-sm border border-stone-700 bg-stone-900 text-white hover:bg-stone-800 transition-colors font-mono text-[11px] uppercase tracking-wider"
              title="Inspect 3D Twin GLB Models"
            >
              <Box size={14} />
              <span className="hidden md:inline">3D Twin</span>
            </button>

            {/* Mobile Menu Button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 text-stone-600 hover:text-stone-900 lg:hidden rounded border border-stone-200 bg-white"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-stone-200 bg-white px-4 pt-3 pb-5 space-y-2">
          {navLinks.map((link) => (
            <button
              key={link.path}
              onClick={() => handleLinkClick(link.path)}
              className={`block w-full text-left px-3 py-2 rounded font-mono text-xs uppercase tracking-wider ${
                isActive(link.path)
                  ? 'bg-stone-100 text-stone-950 font-bold'
                  : 'text-stone-600 hover:bg-stone-50 hover:text-stone-950'
              }`}
            >
              {link.label}
            </button>
          ))}
          <div className="pt-2 border-t border-stone-100 flex flex-col gap-2">
            <button
              onClick={() => {
                onOpenModelViewer();
                setMobileMenuOpen(false);
              }}
              className="flex items-center justify-center gap-2 w-full py-2 bg-stone-900 text-white rounded font-mono text-xs uppercase tracking-wider"
            >
              <Box size={14} />
              <span>Inspect 3D Engine Twin</span>
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
