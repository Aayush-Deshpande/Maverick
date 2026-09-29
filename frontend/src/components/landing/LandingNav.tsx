import React, { useState } from 'react';
import { ArrowUpRight, Menu, X } from 'lucide-react';

const links = [
  ['#hero', '3D Twin'],
  ['#problem', 'Pitch'],
  ['#pillars', '6 Pillars'],
  ['#twin', 'Observer'],
  ['#detection', 'Anomaly'],
  ['#prognosis', 'RUL Bounds'],
  ['#theatres', 'Theatres'],
  ['#fleet', 'Fleet'],
  ['#architecture', 'Stack'],
  ['#matrix', 'DRDO Specs'],
  ['#gcs', 'Cockpit'],
];

export const LandingNav: React.FC<{ onLaunch?: (target?: 'runtime' | 'twin' | 'legacy') => void }> = ({ onLaunch }) => {
  const [open, setOpen] = useState(false);
  const launch = (target: 'runtime' | 'twin' | 'legacy' = 'runtime') => {
    setOpen(false);
    onLaunch?.(target);
  };
  return (
    <header className="an-nav bg-[#080d12]/95 backdrop-blur-md border-b border-white/10 sticky top-0 z-50">
      <a href="#hero" className="an-wordmark" aria-label="ANUMAAN home">
        <span className="an-mark">अ</span>
        <span>
          PROJECT ANUMAAN <span className="text-[#d67658] font-normal text-xs ml-1">अनुमान</span>
          <small className="text-slate-400">DRDO SIH 26054 // AERO-PISTON DIGITAL TWIN</small>
        </span>
      </a>
      <nav className={open ? 'an-nav-links is-open' : 'an-nav-links'}>
        {links.map(([href, label]) => (
          <a href={href} key={href} onClick={() => setOpen(false)}>
            {label}
          </a>
        ))}
        <button className="an-nav-launch" onClick={() => launch('legacy')}>
          GCS Cockpit <ArrowUpRight size={13} />
        </button>
      </nav>
      <button className="an-menu-toggle" aria-label={open ? 'Close menu' : 'Open menu'} onClick={() => setOpen(!open)}>
        {open ? <X size={20} /> : <Menu size={20} />}
      </button>
    </header>
  );
};

export default LandingNav;
