import { lazy, Suspense, useState } from 'react';
import { ArrowUpRight, ArrowRight, ArrowDown, Activity, Box, RotateCcw, Pause, Play, X, Menu, Radio, ScanLine, Layers3 } from 'lucide-react';
import './studio.css';

const EngineStage = lazy(() => import('./EngineStage'));
export const engines = [
  { id: 'rotax_912is', short: '912 iS', name: 'Rotax 912 iS Sport', family: 'Naturally aspirated · Electronic injection', power: '100', unit: 'hp', architecture: 'Flat-four', detail: 'The reference platform. Four cylinders, dual electronic injection and a distinctly compact boxer architecture.', note: 'Original Rotax CAD source · presentation LOD' },
  { id: 'rotax_914', short: '914 F', name: 'Rotax 914 F', family: 'Turbocharged · Automatic wastegate', power: '115', unit: 'hp', architecture: 'Flat-four', detail: 'A turbocharged boxer with exposed intake plumbing, cylinder assemblies and a compact reduction gearbox.', note: 'Original Rotax CAD source · presentation LOD' },
  { id: 'rotax_915is', short: '915 iS', name: 'Rotax 915 iS', family: 'Turbocharged · Intercooled · EFI', power: '141', unit: 'hp', architecture: 'Flat-four', detail: 'Forced induction meets electronic control. Inspect the charge-air routing and tightly packaged propulsion assembly.', note: 'Original Rotax CAD source · presentation LOD' },
  { id: 'austro_ae300', short: 'AE300', name: 'Austro AE300', family: 'Heavy fuel · Common-rail diesel', power: '168', unit: 'hp', architecture: 'Inline-four', detail: 'A different propulsion architecture, with an upright cylinder block, common-rail fuel system and turbocharging.', note: 'AE330-derived illustrative geometry · AE300 profile' },
  { id: 'vrde_jayem_2_2l', short: 'VRDE 2.2', name: 'VRDE–Jayem 2.2L', family: 'Heavy fuel · Parameterised profile', power: '180', unit: 'hp', architecture: 'Inline-four', detail: 'An illustrative heavy-fuel engine assembly for investigating a parameterised indigenous propulsion profile.', note: 'Illustrative geometry · assumed profile parameters' },
];

type Workspace = 'runtime' | 'twin' | 'legacy' | 'tactical';
export function StudioLanding({ onLaunchConsole }: { onLaunchConsole?: (target?: Workspace) => void }) {
  const [selected, setSelected] = useState(0);
  const [interactive, setInteractive] = useState(false);
  const [rotate, setRotate] = useState(true);
  const [reset, setReset] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [status, setStatus] = useState('');
  const engine = engines[selected];
  const selectEngine = (index: number) => {
    if (index !== selected) { setSelected(index); setStatus(''); }
  };
  const navigate = () => setMenuOpen(false);
  return <div className="studio-page">
    <a className="studio-skip" href="#studio-content">Skip to content</a>
    <header className="studio-header">
      <a className="studio-brand" href="#top" aria-label="ANUMAAN home"><span className="studio-brand-mark">a<span>·</span></span><span>ANUMAAN<small>PROPULSION INTELLIGENCE</small></span></a>
      <nav className={menuOpen ? 'studio-navigation is-open' : 'studio-navigation'} aria-label="Main navigation">
        <a href="#platforms" onClick={navigate}>The engines</a><a href="#intelligence" onClick={navigate}>The intelligence</a><a href="#mission" onClick={navigate}>The mission</a>
        <a href="https://anumaan-doc-1797.vercel.app/" target="_blank" rel="noreferrer" onClick={navigate}>Field notes <ArrowUpRight size={13}/></a>
      </nav>
      <button className="studio-console-link" onClick={() => onLaunchConsole?.('runtime')}>Open console <ArrowUpRight size={15}/></button>
      <button className="studio-menu" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X/> : <Menu/>}</button>
    </header>

    <main id="studio-content">
      <section className="studio-hero" id="top">
        <div className="studio-hero-copy">
          <div className="studio-eyebrow"><span className="studio-status-dot"/> ENGINE HEALTH, SEEN DIFFERENTLY</div>
          <h1>Beyond<br/>the <em>redline.</em></h1>
          <p>An engine tells a story before it trips an alarm.<br className="studio-desktop-break"/> ANUMAAN helps you read it.</p>
          <div className="studio-hero-actions"><button className="studio-primary" onClick={() => onLaunchConsole?.('runtime')}>Enter the health console <ArrowUpRight size={18}/></button><a className="studio-text-link" href="#intelligence">Follow the signal <ArrowDown size={16}/></a></div>
          <div className="studio-hero-footnote"><Radio size={14}/><span>SIMULATED ENGINES. REAL ENGINEERING QUESTIONS.</span></div>
        </div>

        <div className="studio-engine-stage" aria-label={`${engine.name} engine showcase`}>
          <div className="studio-orbit studio-orbit-outer"/><div className="studio-orbit studio-orbit-inner"/>
          <div className="studio-stage-top"><span>ENGINE / 0{selected + 1}</span><span><span className="studio-live-dot"/> {interactive ? 'INTERACTIVE MODEL' : 'STUDIO VIEW'}</span></div>
          <div className="studio-quick-pick" aria-label="Select showcase engine">{engines.map((item,index)=><button key={item.id} aria-pressed={index===selected} onClick={()=>selectEngine(index)}>{item.short}</button>)}</div>
          <div className="studio-stage-visual">
            {!interactive && <img key={engine.id} className="studio-engine-poster" src={`/studio/images/${engine.id}.webp`} alt={`${engine.name}, original engine model in a cobalt and lime studio`} loading="eager" width="1200" height="900"/>}
            {interactive && <Suspense fallback={<img className="studio-engine-poster" src={`/studio/images/${engine.id}.webp`} alt={`${engine.name} studio preview`}/>}><EngineStage engineId={engine.id} rotate={rotate} reset={reset} poster={`/studio/images/${engine.id}.webp`} onStatus={setStatus}/></Suspense>}
          </div>
          <div className="studio-model-tag"><span className="studio-tag-line"/><div><span>{engine.architecture.toUpperCase()}</span><strong>{engine.name}</strong></div></div>
          <div className="studio-stage-tools">
            <button className={!interactive ? 'is-selected' : ''} aria-pressed={!interactive} onClick={() => setInteractive(false)}>Studio</button>
            <button className={interactive ? 'is-selected' : ''} aria-pressed={interactive} onClick={() => setInteractive(true)}><Box size={13}/> Inspect in 3D</button>
            {interactive && <><button aria-label={rotate ? 'Pause rotation' : 'Rotate engine'} aria-pressed={rotate} onClick={() => setRotate(!rotate)}>{rotate ? <Pause size={13}/> : <Play size={13}/>}</button><button aria-label="Reset engine camera" onClick={() => setReset(v => v + 1)}><RotateCcw size={13}/></button></>}
          </div>
          <span className="studio-loader-note" role="status" aria-live="polite">{interactive ? status : 'A closer look at the machinery behind the mission.'}</span>
        </div>
        <div className="studio-hero-bottom"><span>DRDO SIH / PS–26054</span><span>FIVE ENGINE PROFILES · ONE OBSERVATION FRAMEWORK</span><a href="#platforms" aria-label="Explore engine platforms"><ArrowDown size={18}/></a></div>
      </section>

      <section className="studio-platforms" id="platforms">
        <div className="studio-section-caption"><span>01 / THE MACHINERY</span><span>SELECT A POWERPLANT</span></div>
        <div className="studio-engine-tabs" role="tablist" aria-label="Engine platforms">{engines.map((item, index) => <button key={item.id} id={`engine-tab-${item.id}`} role="tab" aria-selected={index === selected} aria-controls="studio-engine-detail" onClick={() => selectEngine(index)} className={selected === index ? 'is-selected' : ''}><span>0{index + 1}</span><strong>{item.short}</strong><small>{item.architecture}</small><ArrowUpRight size={16}/></button>)}</div>
        <div className="studio-platform-detail" id="studio-engine-detail" role="tabpanel" aria-labelledby={`engine-tab-${engine.id}`}><div><h2>{engine.name}</h2><p>{engine.detail}</p><small>{engine.note}</small></div><div className="studio-power"><strong>{engine.power}<span>{engine.unit}</span></strong><small>PROFILE RATED POWER</small></div><div className="studio-platform-type"><Layers3 size={22}/><span>{engine.family}</span></div></div>
      </section>

      <section className="studio-intelligence" id="intelligence">
        <div className="studio-section-caption"><span>02 / THE INTELLIGENCE</span><span>FROM SIGNAL TO UNDERSTANDING</span></div>
        <div className="studio-section-heading"><h2>Small deviations.<br/><em>Bigger picture.</em></h2><p>Temperature, pressure, vibration. Individually, they're readings. Together, and in context, they become evidence.</p></div>
        <div className="studio-signal-story">
          <article><div className="studio-feature-index">01 <ScanLine size={20}/></div><h3>Know what to expect.</h3><p>A physics reference sets the context for the selected engine and operating conditions.</p><div className="studio-trace" aria-label="Schematic measured and expected signal comparison"><svg viewBox="0 0 360 90" role="img" aria-label="Measured signal diverging from a dashed expected baseline"><path className="trace-guide" d="M0 65H360M0 30H360"/><path className="trace-expected" d="M0 60 C45 60 45 40 90 40 S135 55 180 55 S225 32 270 32 S315 42 360 42"/><path className="trace-measured" d="M0 61 C45 61 45 42 90 42 S135 53 180 53 S225 26 270 20 S315 8 360 7"/></svg><span>EXPECTED <i/> OBSERVED</span></div></article>
          <article><div className="studio-feature-index">02 <Activity size={20}/></div><h3>Notice what changes.</h3><p>Residual scores and persistence separate a developing pattern from a single unusual sample.</p><div className="studio-persistence" aria-label="Schematic persistence gate"><span/><span/><span/><span/><span/><span className="active"/><span className="active"/><span className="active"/><span className="active"/><span className="active"/></div><div className="studio-figure-caption">A PATTERN, HELD OVER TIME</div></article>
          <article><div className="studio-feature-index">03 <Layers3 size={20}/></div><h3>See the evidence.</h3><p>Move from an engine overview to individual channels, component views and diagnostic reasoning.</p><div className="studio-evidence-stack"><span>ENGINE RESPONSE <ArrowRight size={13}/></span><span>RESIDUAL EVIDENCE <ArrowRight size={13}/></span><span>ENGINEERING REVIEW <ArrowUpRight size={13}/></span></div></article>
        </div><p className="studio-schematic-note">Illustrations explain the method. They are not live aircraft traces.</p>
      </section>

      <section className="studio-mission" id="mission"><div className="studio-mission-orb"/><div><div className="studio-eyebrow">03 / THE MISSION</div><h2>Understand the engine.<br/><em>Before the next decision.</em></h2><p>Explore controlled fault scenarios, inspect the response and interrogate the evidence in one simulation workspace.</p><button className="studio-primary" onClick={() => onLaunchConsole?.('runtime')}>Launch ANUMAAN <ArrowUpRight size={18}/></button><a className="studio-text-link" href="https://anumaan-doc-1797.vercel.app/" target="_blank" rel="noreferrer">Read the engineering notes <ArrowUpRight size={15}/></a></div><div className="studio-mission-boundary"><span>THE PROTOTYPE BOUNDARY</span><p>Software simulation. Advisory outputs.<br/>No aircraft connection or flight-validation claim.</p></div></section>
    </main>
    <footer className="studio-footer"><a href="#top" className="studio-brand">ANUMAAN<span className="studio-wordmark-dot">·</span></a><span>TEAM MIDNIGHT CIPHERS / SIH PS–26054</span><span>Built to question. Engineered to understand.</span><a href="#top">Back to top ↑</a></footer>
  </div>;
}
