import { useEffect, useState } from 'react';
import { AnumaanSplash } from '../landing/AnumaanSplash';
import { ArrowUpRight, Menu, Play, X } from 'lucide-react';
import { EngineInset } from './EngineInset';
import { useLiveEngine } from './useLiveEngine';
import { posterFor } from './engineScene';
import { requestDemo } from '../../demoIntent';
import { SortieFilm } from '../sortie/SortieFilm';
import './survey.css';

type Workspace = 'runtime' | 'twin' | 'legacy' | 'tactical';
interface Props { serverUrl: string; onLaunchConsole?: (target?: Workspace) => void }

const ENGINES = [
  { id: 'rotax_912is', name: 'Rotax 912 iS Sport', family: 'Naturally aspirated · dual-lane EFI', power: 100, layout: 'Flat-four', note: 'Reference platform' },
  { id: 'rotax_914', name: 'Rotax 914 F', family: 'Turbocharged · automatic wastegate', power: 115, layout: 'Flat-four', note: 'Turbo fault set' },
  { id: 'rotax_915is', name: 'Rotax 915 iS', family: 'Turbocharged · intercooled · EFI', power: 141, layout: 'Flat-four', note: 'High-altitude profile' },
  { id: 'austro_ae300', name: 'Austro AE300', family: 'Heavy fuel · common-rail diesel', power: 168, layout: 'Inline-four', note: 'Compression ignition' },
  { id: 'vrde_jayem_2_2l', name: 'VRDE–Jayem 2.2L', family: 'Heavy fuel · turbocharged diesel', power: 180, layout: 'Inline-four', note: 'Indigenous · parameterised profile' },
];

const STAGES = [
  { name: 'Physics observer', text: 'A thermodynamic model of this engine predicts every channel at the current altitude, throttle and outside air; an unscented Kalman filter keeps its parameters honest.' },
  { name: 'Calibrated residuals', text: 'Measured minus expected, scaled per tail. Mahalanobis, max-|z| and Fly-Bloom scorers each carry a split-conformal threshold.' },
  { name: 'Persistence gate', text: 'A deviation has to hold before it becomes an alarm, so one noisy sample never pages the crew.' },
  { name: 'Sensor sanity', text: 'Frozen, drifting or physically impossible readings are quarantined and shielded, so a broken thermocouple is not mistaken for a sick engine.' },
  { name: 'Reservoir classifier', text: 'A 500-node echo-state reservoir, trained on this tail’s own simulated fault library, names the most likely fault.' },
  { name: 'Decision', text: 'An ATA-chapter maintenance directive, remaining life with a conformal interval, 18-hour mission reliability and the engine-out glide.' },
];

const fmt = (v: number | undefined, d = 0) => (typeof v === 'number' && Number.isFinite(v) ? v.toLocaleString('en-IN', { maximumFractionDigits: d, minimumFractionDigits: d }) : '—');
const titleCase = (s: string) => s.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());

export function SurveyLanding({ serverUrl, onLaunchConsole }: Props) {
  const { frame } = useLiveEngine(serverUrl);
  const [engineIdx, setEngineIdx] = useState(0);
  // ?sortie=<seconds> opens the film paused at that moment, with no intro (for previews and stills)
  const [previewAt] = useState<number | null>(() => {
    const v = Number(new URLSearchParams(window.location.search).get('sortie'));
    return Number.isFinite(v) && v > 0 ? v : null;
  });
  // Every load starts clean: intro video, top of the page, film from the beginning. Nothing persists.
  const [introDone, setIntroDone] = useState(previewAt !== null);
  useEffect(() => {
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
    window.scrollTo(0, 0);
  }, []);
  const [menu, setMenu] = useState(false);
  const engine = ENGINES[engineIdx];

  const runDemo = () => { requestDemo(); onLaunchConsole?.('runtime'); };
  const openConsole = () => onLaunchConsole?.('runtime');
  const nav = [['#why', 'Why'], ['#how', 'How it infers'], ['#engines', 'Engines'], ['#decide', 'Decisions'], ['#flightline', 'Flight line']];

  return <div className="sv-page">
    {!introDone && <AnumaanSplash onComplete={() => setIntroDone(true)} />}
    <a className="sv-skip" href="#sv-main">Skip to content</a>
    <header className="sv-header">
      <a className="sv-brand" href="#top" aria-label="ANUMAAN, back to top"><span className="sv-brand-word">ANUMAAN</span><span className="sv-brand-hi" lang="hi">अनुमान</span></a>
      <nav className={menu ? 'sv-nav is-open' : 'sv-nav'} aria-label="Sections">
        {nav.map(([href, label]) => <a key={href} href={href} onClick={() => setMenu(false)}>{label}</a>)}
        <a href="https://anumaan-doc-1797.vercel.app/" target="_blank" rel="noreferrer">Engineering notes <ArrowUpRight size={13} aria-hidden /></a>
      </nav>
      <button type="button" className="sv-btn sv-btn-ink sv-header-cta" onClick={openConsole}>Open console <ArrowUpRight size={15} aria-hidden /></button>
      <button type="button" className="sv-menu" aria-label={menu ? 'Close sections' : 'Open sections'} aria-expanded={menu} onClick={() => setMenu(!menu)}>{menu ? <X size={20} /> : <Menu size={20} />}</button>
    </header>

    <main id="sv-main">
      <div id="top">
        <SortieFilm onRunDemo={runDemo} onOpenConsole={openConsole} onOpenTwin={() => onLaunchConsole?.('twin')} evidenceHref="#why" armed={introDone} previewAt={previewAt} />
      </div>

      <section id="why" className="sv-band sv-band-ice" aria-labelledby="sv-why">
        <div className="sv-wrap sv-split">
          <div>
            <h2 id="sv-why">A redline speaks last.</h2>
            <p className="sv-lede">A single-engine UAV over the Himalaya has no second engine and very few runways. An in-flight shutdown usually loses the airframe.</p>
            <p>A fixed limit fires only once a reading has already crossed it. ANUMAAN asks a better question every 50 milliseconds: what should this engine read right now, at this altitude, throttle and outside air, and how far is it from that?</p>
          </div>
          <figure className="sv-profile">
            <svg viewBox="0 0 640 300" role="img" aria-label="Schematic: measured oil pressure drifts away from the expected value long before it reaches the fixed limit.">
              <g className="sv-profile-grid">{[60, 120, 180, 240].map((y) => <line key={y} x1={40} x2={620} y1={y} y2={y} />)}</g>
              <line className="sv-profile-limit" x1={40} x2={620} y1={232} y2={232} />
              <text className="sv-profile-tag" x={612} y={252} textAnchor="end">fixed limit</text>
              <path className="sv-profile-expected" d="M40 92 C150 88 230 98 330 94 S520 90 620 96" />
              <path className="sv-profile-measured" d="M40 94 C150 90 230 100 300 104 C360 112 410 150 460 186 S560 228 620 238" />
              <line className="sv-profile-mark" x1={352} x2={352} y1={40} y2={268} />
              <text className="sv-profile-tag is-strong" x={358} y={54}>ANUMAAN flags the drift</text>
              <line className="sv-profile-mark is-late" x1={596} x2={596} y1={40} y2={268} />
              <text className="sv-profile-tag" x={590} y={54} textAnchor="end">redline trips</text>
              <text className="sv-profile-axis" x={40} y={290}>time →</text>
              <text className="sv-profile-axis" x={40} y={84}>expected</text>
            </svg>
            <figcaption>Schematic of the method, not a recorded trace. Run the demo to watch a real residual cross its threshold.</figcaption>
          </figure>
        </div>
      </section>

      <section id="how" className="sv-band sv-band-umber" aria-labelledby="sv-how">
        <div className="sv-wrap">
          <h2 id="sv-how">How it infers.</h2>
          <p className="sv-lede">The runtime streams all five engines at 20 Hz. Every frame passes through the same six stages.</p>
          <ol className="sv-route">
            {STAGES.map((s, i) => <li key={s.name} style={{ ['--i' as string]: i }}><span className="sv-wpt" aria-hidden>{String.fromCharCode(65 + i)}</span><h3>{s.name}</h3><p>{s.text}</p></li>)}
          </ol>
        </div>
      </section>

      <section id="engines" className="sv-band sv-band-sage" aria-labelledby="sv-engines">
        <div className="sv-wrap">
          <div className="sv-split sv-split-top">
            <div>
              <h2 id="sv-engines">Five engines. Every part modelled.</h2>
              <p className="sv-lede">Each profile carries its own physics, operating limits and fault set, and each is drawn from a full Blender CAD assembly, not a stand-in.</p>
            </div>
            <div className="sv-engine-stage">
              <EngineInset key={engine.id} engineId={engine.id} label={engine.name} />
            </div>
          </div>
          <div className="sv-index" role="tablist" aria-label="Engine profiles">
            {ENGINES.map((e, i) => <button key={e.id} role="tab" aria-selected={i === engineIdx} className={i === engineIdx ? 'is-on' : undefined} onClick={() => setEngineIdx(i)}>
              <img src={posterFor(e.id)} alt="" width={1200} height={900} loading="lazy" decoding="async" />
              <strong>{e.name}</strong>
              <span>{e.family}</span>
              <span className="sv-index-meta">{e.layout} · {e.power} hp · {e.note}</span>
            </button>)}
          </div>
        </div>
      </section>

      <section id="decide" className="sv-band sv-band-ice" aria-labelledby="sv-decide">
        <div className="sv-wrap">
          <h2 id="sv-decide">Detection is half the job.</h2>
          <p className="sv-lede">Every finding is carried through to the decision it supports. These are the deployed twin’s live values for the Rotax 912 iS right now; run the demo to watch them move.</p>
          <dl className="sv-key">
            <div><dt>Maintenance directive</dt><dd>{frame?.diagnosis ? (frame.diagnosis.ata_chapter === 'ATA 00-00' ? 'No action required' : titleCase(frame.diagnosis.fault_name)) : '—'}</dd><p>{frame?.diagnosis ? `${frame.diagnosis.ata_chapter} · ${frame.diagnosis.manual_reference ?? 'engine maintenance manual'}` : 'ATA-chapter directive with a work order and inspector sign-off.'}</p></div>
            <div><dt>Remaining useful life</dt><dd>{fmt(frame?.prognostics?.rul?.rul_point, 1)} h</dd><p>{frame?.prognostics?.rul ? `${fmt(frame.prognostics.rul.rul_p_lower, 1)}–${fmt(frame.prognostics.rul.rul_p_upper, 1)} h at ${Math.round(frame.prognostics.rul.nominal_coverage * 100)}% conformal coverage` : 'Palmgren–Miner damage with a split-conformal interval.'}</p></div>
            <div><dt>Mission reliability</dt><dd>{frame?.reliability ? `${(frame.reliability.mission_reliability * 100).toFixed(1)}%` : '—'}</dd><p>{frame?.reliability ? `${Math.round(frame.reliability.mission_hours)}-hour ISR profile · limiting part: ${titleCase(frame.reliability.limiting_component)}` : 'Survival of every component across an 18-hour ISR sortie.'}</p></div>
            <div><dt>Engine-out glide</dt><dd>{fmt(frame?.glide?.glide_range_nm)} nm</dd><p>{frame?.glide ? `${frame.glide.reachable_count} of ${frame.glide.airfields.length} Ladakh airfields in reach from ${fmt(frame.glide.altitude_ft)} ft` : 'Glide polar against Leh, Thoise and Kargil.'}</p></div>
          </dl>
        </div>
      </section>

      <section id="film" className="sv-band sv-band-ice sv-band-tight" aria-labelledby="sv-film">
        <div className="sv-wrap sv-split">
          <div>
            <h2 id="sv-film">Watch it catch one.</h2>
            <p className="sv-lede">A 28-second screen recording of the guided demo: an oil-pressure loss develops, the residual crosses its threshold, the persistence gate confirms it, and the console issues an ATA 79 directive.</p>
          </div>
          <figure className="sv-film">
            <video src="/survey/demo.mp4" poster="/survey/demo-poster.webp" controls muted playsInline preload="none" width={1280} height={720} />
            <figcaption>Recorded from the real console running the virtual plant. No edits beyond trimming.</figcaption>
          </figure>
        </div>
      </section>

      <section id="flightline" className="sv-band sv-band-ink" aria-labelledby="sv-flightline">
        <div className="sv-wrap sv-split">
          <div>
            <h2 id="sv-flightline">Built for the flight line, not the cloud.</h2>
            <p className="sv-lede">Everything in the loop runs on the ground station. Nothing waits on a network that a forward base may not have.</p>
          </div>
          <ul className="sv-legend-list">
            <li><svg viewBox="0 0 24 24" aria-hidden><rect x="4" y="4" width="16" height="16" /></svg><div><h3>Air-gapped by design</h3><p>Physics, detection, the engine-manual knowledge base and the copilot run locally; no cloud call sits in the telemetry loop.</p></div></li>
            <li><svg viewBox="0 0 24 24" aria-hidden><circle cx="12" cy="12" r="8" /></svg><div><h3>A copilot the crew can talk to</h3><p>Local speech-to-text and speech synthesis answer hands-free, grounded in the engine manuals.</p></div></li>
            <li><svg viewBox="0 0 24 24" aria-hidden><path d="M3 18L12 5L21 18Z" /></svg><div><h3>Speaks avionics</h3><p>CAN 2.0B decoding from a DBC, MAVLink EFI messages and a SocketCAN bridge sit in the ingest path.</p></div></li>
            <li><svg viewBox="0 0 24 24" aria-hidden><path d="M4 12H20M12 4V20" /></svg><div><h3>Tamper-evident sorties</h3><p>Each sortie’s record is sealed into a SHA-256 Merkle log; maintenance work packages close with inspector sign-off.</p></div></li>
          </ul>
        </div>
      </section>

      <section id="try" className="sv-band sv-band-magenta" aria-labelledby="sv-try">
        <div className="sv-wrap sv-try">
          <h2 id="sv-try">Sixty seconds. One fault. Follow it.</h2>
          <ol className="sv-steps">
            <li>An oil-pressure loss is injected into the Rotax 912 iS.</li>
            <li>The residual climbs past its calibrated threshold and the persistence gate confirms it.</li>
            <li>The console issues the directive, the remaining life and the glide to the nearest airfield.</li>
          </ol>
          <div className="sv-actions">
            <button type="button" className="sv-btn sv-btn-paper" onClick={runDemo}><Play size={16} aria-hidden /> Run the 60-second demo</button>
            <button type="button" className="sv-btn sv-btn-outline" onClick={() => onLaunchConsole?.('twin')}>Explore the 3D twin <ArrowUpRight size={15} aria-hidden /></button>
            <button type="button" className="sv-btn sv-btn-outline" onClick={() => onLaunchConsole?.('legacy')}>Tactical ground station <ArrowUpRight size={15} aria-hidden /></button>
          </div>
        </div>
      </section>
    </main>

    <footer className="sv-footer">
      <div className="sv-footer-video-strip">
        <a
          href="https://youtu.be/L97JAlS9Z7c"
          target="_blank"
          rel="noopener noreferrer"
          className="sv-footer-video-btn"
        >
          <span className="sv-video-badge">
            <Play size={12} fill="currentColor" />
          </span>
          <span className="sv-video-label">DEMONSTRATION VIDEO</span>
          <span className="sv-video-text">Watch the full ANUMAAN 3D digital twin &amp; flight deck walkthrough</span>
          <ArrowUpRight size={14} className="sv-video-arrow" />
        </a>
      </div>

      <span className="sv-brand-word">ANUMAAN</span>
      <span>Team Midnight Ciphers · DRDO SIH PS-26054</span>
      <a href="https://anumaan-doc-1797.vercel.app/" target="_blank" rel="noreferrer">Engineering notes <ArrowUpRight size={13} aria-hidden /></a>
      <span>Relief is schematic; airfield positions approximate.</span>
    </footer>
  </div>;
}

export default SurveyLanding;
