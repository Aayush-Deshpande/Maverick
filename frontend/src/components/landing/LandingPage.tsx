import React from 'react';
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Check,
  CircleHelp,
  LockKeyhole,
  Radio,
  Waves,
  Zap,
} from 'lucide-react';
import { LandingNav } from './LandingNav';
import { LandingFooter } from './LandingFooter';
import './landing.css';

interface LandingPageProps {
  onLaunchConsole?: (target?: 'runtime' | 'twin' | 'legacy') => void;
}

const Eyebrow = ({ children }: { children: React.ReactNode }) => (
  <p className="an-eyebrow">{children}</p>
);

export const LandingPage: React.FC<LandingPageProps> = ({ onLaunchConsole }) => (
  <div className="an-page an-investigation-page">
    <LandingNav onLaunch={onLaunchConsole} />

    <main>
      <section id="hero" className="ani-opening">
        <div className="ani-opening-copy">
          <Eyebrow>ANUMAAN / DRDO SIH 26054</Eyebrow>
          <div className="ani-status"><span /> SIMULATED ENGINE-HEALTH PROTOTYPE</div>
          <h1>An engine fault is injected. The detector has to infer it.</h1>
          <p className="ani-opening-lede">
            ANUMAAN connects a virtual aero-engine to a separate physics observer and a residual-based detector. The detector receives telemetry; the injected fault identity is reserved for evaluation.
          </p>
          <div className="ani-actions">
            <a className="an-button an-button-primary" href="#signal">Follow the test <ArrowDown size={15} /></a>
            <button className="an-button an-button-outline" onClick={() => onLaunchConsole?.('runtime')}>
              Open engine runtime <ArrowUpRight size={15} />
            </button>
          </div>
          <p className="ani-honesty-line">Software simulation · controlled fault injection · advisory output</p>
        </div>

        <div className="ani-opening-visual" aria-label="Simulated engine telemetry flows to an independent observer and detector">
          <div className="ani-visual-head"><span>THE BUILT PATH</span><span>01 / SIMULATION</span></div>
          <div className="ani-path-node">
            <span className="ani-path-icon"><Waves size={17} /></span>
            <div><small>PLANT</small><strong>Virtual engine</strong><p>Conditions + injected fault</p></div>
            <span className="ani-path-code">G01</span>
          </div>
          <div className="ani-path-connector"><i /></div>
          <div className="ani-path-node">
            <span className="ani-path-icon"><Radio size={17} /></span>
            <div><small>OBSERVED INPUT</small><strong>Telemetry frame</strong><p>Sensor channels seen by the detector</p></div>
            <span className="ani-path-code">FRAME</span>
          </div>
          <div className="ani-path-connector"><i /></div>
          <div className="ani-path-node ani-path-node-final">
            <span className="ani-path-icon"><Check size={17} /></span>
            <div><small>INFERENCE</small><strong>Physics observer + detector</strong><p>Expected response, residual evidence, persistence gate</p></div>
            <span className="ani-path-code">GCS</span>
          </div>
          <div className="ani-path-foot"><span className="ani-live-dot" /> A software test path, not aircraft telemetry</div>
        </div>
        <a className="ani-scroll-cue" href="#signal">Continue through the test <ArrowDown size={13} /></a>
      </section>

      <section id="signal" className="ani-section ani-signal-section">
        <div className="ani-section-head">
          <div><Eyebrow>01 / WHY THE REFERENCE MATTERS</Eyebrow><h2>A reading needs its operating point.</h2></div>
          <div className="ani-copy">
            <p>A fixed limit asks whether a value crossed a line. ANUMAAN’s intended health signal asks whether the engine response differs from what the physics observer expects under the current simulated conditions.</p>
            <p>The gap between measured and expected behavior is the residual. The model is partial; this comparison is a prototype method, not a calibrated operational engine twin.</p>
          </div>
        </div>

        <figure className="ani-signal-figure">
          <div className="ani-figure-label"><span>MODEL-REFERENCED COMPARISON</span><span>SCHEMATIC · NOT RUNTIME DATA</span></div>
          <svg className="ani-signal-svg" viewBox="0 0 1000 300" role="img" aria-labelledby="signal-title signal-desc">
            <title id="signal-title">Measured channel diverges from expected engine response</title>
            <desc id="signal-desc">A conceptual trace showing measured and expected responses separating after an injected fault. No measured values are represented.</desc>
            <path className="ani-grid-line" d="M50 50H970M50 100H970M50 150H970M50 200H970M50 250H970" />
            <path className="ani-axis-line" d="M50 270H970M50 30V270" />
            <path className="ani-expected-line" d="M60 205 C180 198 260 203 360 195 S540 190 640 194 S830 187 960 190" />
            <path className="ani-measured-line" d="M60 205 C180 198 260 203 360 195 S500 191 610 193 C690 192 700 162 750 150 S850 125 960 105" />
            <path className="ani-residual-bracket" d="M820 132V185M812 132H828M812 185H828" />
            <circle className="ani-fault-point" cx="690" cy="192" r="6" />
            <text className="ani-svg-label" x="58" y="22">ENGINE RESPONSE OVER A TEST RUN</text>
            <text className="ani-svg-label ani-label-orange" x="704" y="84">injected change</text>
            <text className="ani-svg-label ani-label-orange" x="837" y="154">residual</text>
            <text className="ani-svg-legend" x="60" y="293">— measured channel</text>
            <text className="ani-svg-legend ani-legend-muted" x="250" y="293">— expected response</text>
          </svg>
          <figcaption>Concept diagram only. It explains the comparison; it does not show a recorded engine run or a measured detection result.</figcaption>
        </figure>
      </section>

      <section id="boundary" className="ani-section ani-boundary-section">
        <div className="ani-section-head">
          <div><Eyebrow>02 / A FAIR TEST NEEDS A BOUNDARY</Eyebrow><h2>The evaluator knows the fault. The detector does not.</h2></div>
          <div className="ani-copy">
            <p>The simulated plant can inject a known fault. The detector’s observed frame carries sensor channels, while the fault identity and severity are kept on a separate evaluation path.</p>
            <p>That separation is what makes a seeded simulation test meaningful: the detector must infer from its inputs instead of reading the answer key.</p>
          </div>
        </div>

        <div className="ani-boundary-diagram">
          <div className="ani-lane-label"><span>INFERENCE PATH</span><small>available during detection</small></div>
          <div className="ani-lane-flow">
            <div><small>GENERATE</small><strong>Virtual plant</strong><span>conditions + fault</span></div><b><ArrowRight size={17} /></b>
            <div><small>OBSERVE</small><strong>Telemetry frame</strong><span>sensor channels</span></div><b><ArrowRight size={17} /></b>
            <div><small>ESTIMATE</small><strong>Observer + detector</strong><span>residual evidence</span></div>
          </div>
          <div className="ani-evaluator-lane">
            <div className="ani-lane-label"><span><LockKeyhole size={13} /> EVALUATION ONLY</span><small>not an inference input</small></div>
            <div className="ani-evaluator-card"><strong>TruthRecord</strong><span>Fault identity + severity</span><small>held aside for scoring</small></div>
            <div className="ani-evaluator-note">Same run · separate data path</div>
          </div>
          <p className="ani-boundary-foot"><CircleHelp size={14} /> This protects the experiment from label leakage; it does not turn simulated ground truth into physical-engine validation.</p>
        </div>
      </section>

      <section id="evidence" className="ani-section ani-evidence-section">
        <div className="ani-section-head">
          <div><Eyebrow>03 / WHAT THE RECORDS CAN SUPPORT</Eyebrow><h2>Experiments are listed. The result values are not here.</h2></div>
          <div className="ani-copy"><p>The project has comparison and integration experiments. The evidence material reviewed for this page identifies their methods and output fields, but does not provide the values needed to claim a winning model or measured system performance.</p></div>
        </div>
        <div className="ani-evidence-list">
          <article className="ani-evidence-row">
            <span className="ani-evidence-id">E17</span>
            <div><h3>Detector bakeoff</h3><p>Simulated multi-engine comparison: universal vs per-engine detectors, with novelty and classical scorers.</p></div>
            <div className="ani-evidence-status"><span className="ani-status-indexed">RECORD INDEXED</span><small>Macro-F1, novelty and latency fields; values not surfaced in this evidence set.</small></div>
          </article>
          <article className="ani-evidence-row">
            <span className="ani-evidence-id">E19</span>
            <div><h3>Connectome reservoir controls</h3><p>Simulation comparison against a rewired graph, matched random ESN, windowed RF and static RF.</p></div>
            <div className="ani-evidence-status"><span className="ani-status-indexed">METHOD DOCUMENTED</span><small>Matched-control design is described; no comparative result is established here.</small></div>
          </article>
          <article className="ani-evidence-row">
            <span className="ani-evidence-id">E20</span>
            <div><h3>Product-path integration</h3><p>End-to-end experiment is described through RuntimeHub and EngineRuntime, rather than an isolated experiment script.</p></div>
            <div className="ani-evidence-status"><span className="ani-status-indexed">PATH IDENTIFIED</span><small>Integration intent is indexed; no benchmark outcome is claimed.</small></div>
          </article>
        </div>
        <div className="ani-evidence-note"><span className="ani-live-dot" /><p><strong>What can be shown now:</strong> a controlled software scenario running through the prototype. <strong>What cannot be claimed from these records:</strong> detector superiority, field accuracy, calibrated RUL, or aircraft-level timing.</p></div>
      </section>

      <section id="demo" className="ani-section ani-demo-section">
        <div className="ani-demo-head">
          <div><Eyebrow>04 / INTERACT WITH THE PROTOTYPE</Eyebrow><h2>Set a condition. Inject a fault. Follow the evidence.</h2></div>
          <p>The engine runtime exposes virtual-plant controls, profile-valid fault injection, detector output, and simulated telemetry. The 3D twin is a view of engine state, not the physics solver.</p>
        </div>
        <div className="ani-demo-steps">
          <div><span>01</span><strong>Set conditions</strong><small>Throttle · altitude · outside air</small></div><b><ArrowRight size={16} /></b>
          <div><span>02</span><strong>Inject a scenario</strong><small>Choose a supported virtual fault</small></div><b><ArrowRight size={16} /></b>
          <div><span>03</span><strong>Inspect the response</strong><small>Channels · residuals · detector state</small></div>
        </div>
        <div className="ani-demo-actions">
          <button className="an-button an-button-primary" onClick={() => onLaunchConsole?.('runtime')}><Zap size={15} /> Open engine runtime <ArrowUpRight size={15} /></button>
          <button className="ani-secondary-action" onClick={() => onLaunchConsole?.('twin')}>Inspect the 3D view <ArrowUpRight size={14} /></button>
          <span>Virtual plant data · manual scenarios · advisory output</span>
        </div>
      </section>

      <section id="depth" className="ani-section ani-depth-section">
        <div className="ani-section-head">
          <div><Eyebrow>05 / UNDER THE DEMONSTRATION</Eyebrow><h2>One project, several maturity levels.</h2></div>
          <div className="ani-copy"><p>The project includes connected runtime code, separate research paths, and older interfaces. The distinctions matter: the presence of a module does not mean it participates in the live trace.</p></div>
        </div>
        <div className="ani-depth-grid">
          <article><span className="ani-depth-mark ani-mark-built">01 / RUNTIME</span><h3>Multi-engine software path</h3><p>RuntimeHub and EngineRuntime expose configured virtual engines, state, levers, fault injection, and telemetry streams.</p><small>Integrated software prototype</small></article>
          <article><span className="ani-depth-mark ani-mark-separate">02 / PARALLEL PATH</span><h3>Legacy Rotax GCS</h3><p>A separate older engine service and GCS path coexist with the multi-engine runtime. They should not be presented as one unified service.</p><small>Separate implementation path</small></article>
          <article><span className="ani-depth-mark ani-mark-research">03 / RESEARCH</span><h3>Reservoir + waveform work</h3><p>Temporal reservoir and high-rate sensor processing are described as research or emulation paths; their complete integration into the live trace is not established.</p><small>Prototype / separate path</small></article>
        </div>
        <details className="ani-technical-note">
          <summary>Runtime details and data boundaries <span>+</span></summary>
          <div className="ani-technical-content">
            <p><strong>Telemetry timing:</strong> the UI describes a 20 Hz stream, while the runtime documentation says a tick can represent one simulated second. A UI refresh rate is not a physical-engine real-time measurement.</p>
            <p><strong>Engine profiles:</strong> multiple configurations are listed, but a profile is not evidence of calibration against that physical engine.</p>
            <p><strong>3D twin:</strong> receives state for display and highlighting; it is not the thermodynamic model.</p>
          </div>
        </details>
      </section>

      <section id="limits" className="ani-section ani-limits-section">
        <div className="ani-section-head">
          <div><Eyebrow>06 / WHAT THIS DEMONSTRATION DOES NOT PROVE</Eyebrow><h2>Prototype boundaries, stated plainly.</h2></div>
          <div className="ani-copy"><p>The project’s own gap reviews are clear that important deployment and validation steps remain. Those limits define how to read the demo and its experiment records.</p></div>
        </div>
        <div className="ani-limit-list">
          <div><span>NOT SHOWN</span><p>Live telemetry from a physical engine, aircraft, ECU, or flight bus.</p></div>
          <div><span>NOT VALIDATED</span><p>Operational RUL coverage on representative run-to-failure engine data.</p></div>
          <div><span>NOT COMPLETE</span><p>Analytical parity isolation of sensor faults, glide reachability, and certification evidence.</p></div>
          <div><span>NOT A CLAIM</span><p>Aircraft control, airworthiness approval, or field-ready diagnostic instructions.</p></div>
        </div>
        <div className="ani-bottom-actions"><span>ANUMAAN · controlled software prototype</span><button onClick={() => onLaunchConsole?.('runtime')}>Open the simulated runtime <ArrowUpRight size={15} /></button></div>
      </section>
    </main>

    <LandingFooter onLaunch={onLaunchConsole} />
  </div>
);

export default LandingPage;
