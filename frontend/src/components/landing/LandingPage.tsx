import React from 'react';
import { ArrowDown, ArrowRight, ArrowUpRight, Check, LockKeyhole } from 'lucide-react';
import { LandingNav } from './LandingNav';
import { LandingHero3D } from './LandingHero3D';
import { LandingFooter } from './LandingFooter';
import './landing.css';
import './landing-editorial.css';

interface LandingPageProps {
  onLaunchConsole?: (target?: 'runtime' | 'twin' | 'legacy') => void;
}

const Eyebrow = ({ children }: { children: React.ReactNode }) => (
  <p className="ae-eyebrow">{children}</p>
);

const SectionHeading = ({
  index,
  label,
  title,
  children,
}: {
  index: string;
  label: string;
  title: string;
  children?: React.ReactNode;
}) => (
  <div className="ae-section-heading">
    <Eyebrow>{index} / {label}</Eyebrow>
    <h2>{title}</h2>
    {children && <div className="ae-copy">{children}</div>}
  </div>
);

export const LandingPage: React.FC<LandingPageProps> = ({ onLaunchConsole }) => (
  <div className="ae-page">
    <LandingNav onLaunch={onLaunchConsole} />

    <main>
      <section id="hero" className="ae-hero">
        <div className="ae-hero-copy">
          <Eyebrow>ANUMAAN / DRDO SIH 26054</Eyebrow>
          <p className="ae-kicker"><span /> SIMULATED PROPULSION-HEALTH SYSTEM</p>
          <h1>The engine runs.<br /><em>The observer has to infer.</em></h1>
          <p className="ae-hero-lede">
            ANUMAAN couples a virtual aero-engine to a physics observer and a temporal detector. It injects controlled faults, keeps fault identity out of the detector's input, and traces how the engine's response changes.
          </p>
          <div className="ae-hero-actions">
            <a className="ae-button ae-button-dark" href="#problem">Follow the evidence <ArrowDown size={15} /></a>
            <button className="ae-button ae-button-quiet" onClick={() => onLaunchConsole?.('runtime')}>Open the runtime <ArrowUpRight size={15} /></button>
          </div>
          <p className="ae-honesty-note">Software simulation · seeded scenarios · advisory output</p>
        </div>

        <div className="ae-model-column">
          <div className="ae-model-heading"><span>INTERACTIVE ENGINE MODEL</span><span>SELECT · ROTATE · INSPECT</span></div>
          <div className="ae-model-frame">
            <LandingHero3D
              onLaunchConsole={() => onLaunchConsole?.('runtime')}
              onExploreTwin={() => onLaunchConsole?.('twin')}
            />
          </div>
          <p className="ae-model-note">A navigable model of the selected engine profile. The 3D view represents state; it is not the physics solver.</p>
        </div>
        <a className="ae-scroll-cue" href="#problem">Continue into the system <ArrowDown size={13} /></a>
      </section>

      <section id="problem" className="ae-section ae-comparison-section">
        <SectionHeading index="01" label="THE OPERATING POINT MATTERS" title="A threshold sees a number. An engine has a context.">
          <p>A fixed limit asks whether one reading crossed a line. ANUMAAN compares the measured response with what its physics reference expects for the current simulated conditions.</p>
        </SectionHeading>

        <div className="ae-comparison" aria-label="Fixed threshold compared with a physics reference">
          <article className="ae-comparison-row">
            <span className="ae-row-index">A</span>
            <div className="ae-row-copy">
              <h3>Fixed limit</h3>
              <p>Compare a sensor with one threshold. It is easy to understand, but it may only react after the reading has moved far from normal.</p>
            </div>
            <div className="ae-diagram ae-threshold-diagram" aria-label="A single fixed threshold line">
              <span className="ae-diagram-label">limit</span><i /><b />
            </div>
          </article>
          <article className="ae-comparison-row">
            <span className="ae-row-index">B</span>
            <div className="ae-row-copy">
              <h3>Physics reference</h3>
              <p>Estimate what the engine should be doing for the current altitude and operating point. Track the difference over time.</p>
            </div>
            <div className="ae-diagram ae-reference-diagram" aria-label="Measured engine response diverges from an expected response">
              <span className="ae-measured-label">measured</span><span className="ae-expected-label">expected</span>
              <i /><b /><em />
            </div>
          </article>
          <p className="ae-comparison-caption">The gap between measured and expected behaviour is called a residual. The name comes after the idea.</p>
        </div>
      </section>

      <section id="observer" className="ae-section ae-observer-section">
        <div className="ae-two-column-heading">
          <SectionHeading index="02" label="THE PHYSICS OBSERVER" title="The model makes the signal meaningful." />
          <div className="ae-copy ae-observer-copy">
            <p>The 3D engine is the visible object. The digital twin is the running mathematical estimate behind it: a thermodynamic model updated from engine inputs and simulated sensor readings.</p>
            <p>Its job is to provide an expected response at the current operating point. That reference gives the downstream detector context that a shared fleet-wide threshold cannot provide.</p>
          </div>
        </div>
        <div className="ae-observer-strip" aria-label="Engine inputs update a physics estimate that is compared with sensor readings">
          <div><span>INPUTS</span><strong>Profile · throttle · altitude</strong><small>Current simulated conditions</small></div>
          <b><ArrowRight size={17} /></b>
          <div><span>REFERENCE</span><strong>Expected engine response</strong><small>Physics-based estimate</small></div>
          <b><ArrowRight size={17} /></b>
          <div><span>OBSERVATION</span><strong>Sensor readings</strong><small>Measured response</small></div>
        </div>
      </section>

      <section id="flybrain" className="ae-section ae-flybrain-section">
        <div className="ae-two-column-heading">
          <SectionHeading index="03" label="TEMPORAL INFERENCE" title="A fault is a pattern that develops, not a single bad sample." />
          <div className="ae-copy">
            <p>FlyBrain is ANUMAAN's sparse, recurrent reservoir experiment for reading relationships across channels and time. The physics reference supplies context; the temporal model looks for combinations that persist or evolve together.</p>
            <p>The evaluation plan compares the connectome-inspired reservoir with rewired-graph and matched-random controls, plus windowed and static Random Forest baselines. That design tests whether the structure matters; it does not by itself establish a performance win.</p>
          </div>
        </div>
        <div className="ae-temporal-diagram" aria-label="Channels and time windows feed a recurrent reservoir whose output is checked as a pattern">
          <div className="ae-temporal-head"><span>CHANNEL HISTORY</span><span>MODEL UNDER TEST</span><span>OUTPUT</span></div>
          <div className="ae-temporal-flow">
            <div className="ae-channel-stack"><i /><i /><i /><i /><span>related engine channels</span></div>
            <b><ArrowRight size={17} /></b>
            <div className="ae-reservoir-mark"><span>FlyBrain</span><small>sparse recurrent reservoir</small><div><i /><i /><i /><i /><i /><i /></div></div>
            <b><ArrowRight size={17} /></b>
            <div className="ae-pattern-output"><strong>Candidate pattern</strong><small>evidence across channels and time</small></div>
          </div>
          <p className="ae-figure-note">A schematic of the experimental path, not a measured detection trace.</p>
        </div>
      </section>

      <section id="diagnosis" className="ae-section ae-diagnosis-section">
        <div className="ae-diagnosis-top">
          <div>
            <Eyebrow>04 / FROM SIGNAL TO ACTION</Eyebrow>
            <h2>A diagnosis should explain its evidence.</h2>
          </div>
          <div className="ae-copy">
            <p>ANUMAAN's diagnostic view can present a physical cause-and-effect chain: which signals moved, how they relate, what fault could explain them, and what should be checked next.</p>
            <p>The engineer can inspect that chain in the ground console. This landing page does not present an animated chart as live aircraft evidence.</p>
            <button className="ae-button ae-button-dark" onClick={() => onLaunchConsole?.('legacy')}>Open the ground console <ArrowRight size={15} /></button>
          </div>
        </div>
        <div className="ae-diagnosis-chain">
          <article><span>OBSERVED</span><strong>Signals diverge</strong><small>From the physics reference</small></article><b>→</b>
          <article><span>CHECKED</span><strong>Sensor or engine?</strong><small>Cross-channel consistency</small></article><b>→</b>
          <article><span>EXPLAINED</span><strong>Likely cause</strong><small>Evidence linked to a fault mode</small></article><b>→</b>
          <article><span>CONSIDERED</span><strong>Mission impact</strong><small>Constraints and next action</small></article>
        </div>
      </section>

      <section id="evidence" className="ae-section ae-evidence-section">
        <SectionHeading index="05" label="WHAT THE RECORDS SUPPORT" title="The experiment is part of the engineering.">
          <p>The project records describe comparisons and integration work. They identify how the detector and reservoir were tested; the materials reviewed do not establish a numeric performance advantage, flight accuracy, or operational RUL validation.</p>
        </SectionHeading>
        <div className="ae-evidence-list">
          <article><span>E17</span><div><h3>Detector comparison</h3><p>Universal and per-engine approaches with novelty and classical scorers across simulated profiles.</p></div><small>Methods and score fields indexed; no winning score claimed here.</small></article>
          <article><span>E19</span><div><h3>Reservoir controls</h3><p>Connectome-inspired reservoir compared with rewired and matched-random controls, plus static and windowed baselines.</p></div><small>Control design documented; outcome not asserted.</small></article>
          <article><span>E20</span><div><h3>Product-path integration</h3><p>RuntimeHub and EngineRuntime appear in the end-to-end integration trail.</p></div><small>Integration path identified; no real-aircraft validation implied.</small></article>
        </div>
      </section>

      <section id="runtime" className="ae-section ae-runtime-section">
        <div className="ae-two-column-heading">
          <SectionHeading index="06" label="INTERACT WITH THE PROTOTYPE" title="Set a condition. Inject a fault. Follow the response." />
          <div className="ae-copy">
            <p>The software runtime exposes virtual-engine conditions, supported fault injection, engine state, and telemetry. The 3D viewer makes a selected engine model inspectable; the ground console exposes the diagnostic path.</p>
            <p>These are controlled software scenarios. They are not live readings from an aircraft or physical engine.</p>
          </div>
        </div>
        <div className="ae-runtime-steps">
          <article><span>01</span><strong>Set conditions</strong><small>Choose profile and operating point</small></article><b><ArrowRight size={17} /></b>
          <article><span>02</span><strong>Inject a scenario</strong><small>Select a supported virtual fault</small></article><b><ArrowRight size={17} /></b>
          <article><span>03</span><strong>Inspect the response</strong><small>Channels · observer · detector</small></article>
        </div>
        <div className="ae-runtime-actions">
          <button className="ae-button ae-button-dark" onClick={() => onLaunchConsole?.('runtime')}>Open the engine runtime <ArrowUpRight size={15} /></button>
          <button className="ae-button ae-button-outline" onClick={() => onLaunchConsole?.('twin')}>Explore the 3D twin <ArrowUpRight size={15} /></button>
        </div>
      </section>

      <section id="engineering" className="ae-section ae-engineering-section">
        <SectionHeading index="07" label="UNDER THE DEMONSTRATION" title="One system, with different levels of maturity.">
          <p>ANUMAAN includes connected runtime code alongside separate research and legacy paths. The distinctions matter: a module in the repository is not automatically part of the live demonstration.</p>
        </SectionHeading>
        <div className="ae-engineering-grid">
          <article><span>INTEGRATED SOFTWARE</span><h3>EngineRuntime</h3><p>Profiled virtual engines, operating controls, supported fault injection, and telemetry state.</p></article>
          <article><span>RESEARCH PATH</span><h3>FlyBrain + fast signals</h3><p>Temporal reservoir and waveform work are research paths; complete live integration is not established by the demo.</p></article>
          <article><span>SEPARATE INTERFACE</span><h3>Legacy ground console</h3><p>An older Rotax-focused console exists alongside the multi-engine runtime.</p></article>
        </div>
        <details className="ae-technical-details">
          <summary>What the 3D twin represents <span>+</span></summary>
          <p>The viewer receives engine state for display and component highlighting. It is a visual representation of the selected model, not the thermodynamic solver or evidence of physical-engine calibration.</p>
        </details>
      </section>

      <section id="limits" className="ae-limit-section">
        <div><Eyebrow>08 / CURRENT BOUNDARIES</Eyebrow><h2>Show the prototype for what it is.</h2></div>
        <div className="ae-limit-list">
          <p><Check size={15} /> Controlled virtual-engine scenarios and software telemetry.</p>
          <p><Check size={15} /> A physics-referenced observer and experimental temporal detector.</p>
          <p><LockKeyhole size={15} /> No live aircraft bus, flight validation, certified diagnosis, or validated operational RUL claim.</p>
        </div>
      </section>
    </main>

    <LandingFooter onLaunch={onLaunchConsole} />
  </div>
);

export default LandingPage;
