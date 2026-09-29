import React, { useState } from 'react';
import { ArrowUpRight, Menu, X } from 'lucide-react';

const DOCS_URL = 'https://anumaan-docs.vercel.app';

const links = [
  ['#hero', 'The system'],
  ['#problem', 'The operating point'],
  ['#observer', 'Physics observer'],
  ['#flybrain', 'Temporal inference'],
  ['#diagnosis', 'Diagnosis'],
  ['#evidence', 'Experiments'],
  ['#runtime', 'Live prototype'],
  ['#engineering', 'Engineering depth'],
  ['#limits', 'Boundaries'],
];

export const LandingNav: React.FC<{ onLaunch?: (target?: 'runtime' | 'twin' | 'legacy') => void }> = ({ onLaunch }) => {
  const [open, setOpen] = useState(false);
  const launch = () => {
    setOpen(false);
    onLaunch?.('legacy');
  };

  return (
    <header className="ae-nav">
      <a href="#hero" className="ae-wordmark" aria-label="ANUMAAN home">
        <img className="ae-logo" src="/images/anumaan-mark-editorial.png" alt="" />
        <span className="ae-brand-name">ANUMAAN</span>
        <span className="ae-brand-tooltip" aria-hidden="true">ANUMAAN</span>
      </a>
      <nav aria-label="Landing page sections" className={open ? 'ae-nav-links is-open' : 'ae-nav-links'}>
        {links.map(([href, label]) => (
          <a href={href} key={href} aria-label={label} onClick={() => setOpen(false)}>
            <span className="ae-nav-dash" aria-hidden="true">-</span>
            <span className="ae-nav-tooltip" aria-hidden="true">{label}</span>
          </a>
        ))}
        <a href={DOCS_URL} target="_blank" rel="noopener noreferrer" aria-label="Documentation" onClick={() => setOpen(false)}>
          <span className="ae-nav-dash" aria-hidden="true">-</span>
          <span className="ae-nav-tooltip" aria-hidden="true">Documentation</span>
        </a>
        <button className="ae-nav-launch" aria-label="Open ground console" onClick={launch}>
          <span className="ae-nav-dash" aria-hidden="true">-</span>
          <span className="ae-nav-tooltip" aria-hidden="true">Ground console</span>
          <ArrowUpRight size={13} aria-hidden="true" />
        </button>
      </nav>
      <button className="ae-menu-toggle" aria-label={open ? 'Close menu' : 'Open menu'} onClick={() => setOpen(!open)}>
        {open ? <X size={19} /> : <Menu size={19} />}
      </button>
    </header>
  );
};

export default LandingNav;
