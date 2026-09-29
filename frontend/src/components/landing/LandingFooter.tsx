import React from 'react';
import { ArrowUp } from 'lucide-react';

interface LandingFooterProps {
  onLaunchConsole?: () => void;
  onOpenTwin?: () => void;
  onOpenLegacy?: () => void;
  onLaunch?: (target?: 'runtime' | 'twin' | 'legacy') => void;
}

export const LandingFooter: React.FC<LandingFooterProps> = ({
  onLaunchConsole,
  onOpenTwin,
  onOpenLegacy,
  onLaunch,
}) => {
  const handleLaunchConsole = () => {
    if (onLaunchConsole) onLaunchConsole();
    else if (onLaunch) onLaunch('runtime');
  };
  const handleOpenTwin = () => {
    if (onOpenTwin) onOpenTwin();
    else if (onLaunch) onLaunch('twin');
  };
  const handleOpenLegacy = () => {
    if (onOpenLegacy) onOpenLegacy();
    else if (onLaunch) onLaunch('legacy');
  };
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <footer className="an-footer">
      <a href="#hero" className="an-footer-brand"><span className="an-mark">अ</span><span>ANUMAAN<small>Aero-propulsion health</small></span></a>
      <p>DRDO SIH 26054<br />Simulated propulsion-health prototype.</p>
      <div className="an-footer-links">
        <button onClick={handleLaunchConsole}>Engine runtime <ArrowUp className="an-footer-arrow" size={14} /></button>
        <button onClick={handleOpenTwin}>3D engine twin <ArrowUp className="an-footer-arrow" size={14} /></button>
        <button onClick={handleOpenLegacy}>Ground console <ArrowUp className="an-footer-arrow" size={14} /></button>
      </div>
      <small className="an-footer-copy">© 2026 Project ANUMAAN</small>
      <button className="an-back-top" onClick={scrollToTop}>Back to top <ArrowUp size={14} /></button>
    </footer>
  );
};
