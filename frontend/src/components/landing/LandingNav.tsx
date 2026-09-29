import React, { useState } from 'react';
import { ArrowUpRight, Menu, X } from 'lucide-react';

const links = [
  ['#signal', 'The test'], ['#boundary', 'Fairness'], ['#evidence', 'Evidence'], ['#demo', 'Run it'], ['#limits', 'Limits'],
];

export const LandingNav: React.FC<{ onLaunch?: (target?: 'runtime' | 'twin' | 'legacy') => void }> = ({ onLaunch }) => {
  const [open, setOpen] = useState(false);
  const launch = () => { setOpen(false); onLaunch?.('runtime'); };
  return <header className="an-nav"><a href="#hero" className="an-wordmark" aria-label="ANUMAAN home"><span className="an-mark">अ</span><span>ANUMAAN<small>Simulated propulsion health</small></span></a><nav className={open ? 'an-nav-links is-open' : 'an-nav-links'}>{links.map(([href, label]) => <a href={href} key={href} onClick={() => setOpen(false)}>{label}</a>)}<button className="an-nav-launch" onClick={launch}>Open runtime <ArrowUpRight size={15} /></button></nav><button className="an-menu-toggle" aria-label={open ? 'Close menu' : 'Open menu'} onClick={() => setOpen(!open)}>{open ? <X size={20} /> : <Menu size={20} />}</button></header>;
};

export default LandingNav;
