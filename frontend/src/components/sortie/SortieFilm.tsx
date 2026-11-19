import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowUpRight, Box, ChevronLeft, ChevronRight, Pause, Play, RotateCcw, Volume2, VolumeX } from 'lucide-react';
import { CHAPTERS, DIRECTIVE, GLIDE, INJECTION, OIL, STARTS, TOTAL, T_INJECT, chapterAt, oilExpected, oilMeasured, startOf } from './story';
import { INSERT, RADIO, RADIO_HOLD, T_CONFIRM, readout, type Readout } from './timeline';
import { NOMINAL_RAW, SCORERS, tier0 } from './detector';
import { reservoir, startReservoir } from './brain';
import { drawDetect, drawMemory, region } from './mind';
import { subsystemName, type ComponentMap } from './bay';
import type { Screen, SortieWorld } from './world';
import { SortieSound } from './sound';
import { warmEngineModels } from './warmup';
import './sortie.css';

interface Props {
  onRunDemo: () => void;
  onOpenConsole: () => void;
  onOpenTwin: () => void;
  /** Where "skip the film" takes the reader. */
  evidenceHref: string;
  /** False while the intro splash is still playing; the gate waits for it. */
  armed: boolean;
  /** Preview mode (?sortie=<seconds>): no gate, paused at that moment. */
  previewAt: number | null;
}

type Phase = 'gate' | 'insert' | 'play';

const BAY_IN = 0.17, BAY_OUT = 0.93, BAY_INJECT = 0.434;
const BAY_KEYS = ['oil', 'fuel', 'ignition', 'cooling', 'exhaust', 'gearbox', 'electrical', 'control'];
const SCORER_LABEL = { fly_bloom: 'Fly Bloom', mahalanobis: 'Mahalanobis', max_abs_z: 'max |z|' } as const;

const fmt = (v: number, d = 0) => v.toLocaleString('en-IN', { maximumFractionDigits: d, minimumFractionDigits: d });
const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const pad2 = (n: number) => String(Math.floor(n)).padStart(2, '0');
const sstep = (a: number, b: number, x: number) => { const k = Math.min(1, Math.max(0, (x - a) / (b - a))); return k * k * (3 - 2 * k); };
/** Sortie elapsed time: the film opens six hours into the eighteen-hour sortie. */
const missionClock = (t: number) => { const s = 6 * 3600 + 14 * 60 + 7 + t; return `T+${pad2(s / 3600)}:${pad2((s % 3600) / 60)}:${pad2(s % 60)}`; };
const radioAt = (t: number) => { for (let i = RADIO.length - 1; i >= 0; i--) if (t >= RADIO[i].at) return t < RADIO[i].at + RADIO_HOLD ? i : -1; return -1; };

/** Oil pressure, measured against what the twin expects, over the last 16 story seconds. */
function drawTrace(cv: HTMLCanvasElement, t: number, confirmed: boolean) {
  const dpr = Math.min(window.devicePixelRatio, 2);
  const w = cv.clientWidth, h = cv.clientHeight;
  if (!w || !h) return;
  if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const g = cv.getContext('2d')!;
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  const span = 16, lo = 0.4, hi = 4.7;
  const X = (k: number) => (k / span) * w;
  const Y = (v: number) => h - ((v - lo) / (hi - lo)) * h;
  g.strokeStyle = 'rgba(214, 236, 232, 0.10)'; g.lineWidth = 1;
  for (let v = 1; v < hi; v++) { g.beginPath(); g.moveTo(0, Y(v) + 0.5); g.lineTo(w, Y(v) + 0.5); g.stroke(); }
  g.setLineDash([4, 4]); g.strokeStyle = 'rgba(255, 92, 140, 0.75)';
  g.beginPath(); g.moveTo(0, Y(OIL.limit)); g.lineTo(w, Y(OIL.limit)); g.stroke(); g.setLineDash([]);
  const series = (f: (x: number) => number, color: string, width: number) => {
    g.strokeStyle = color; g.lineWidth = width; g.beginPath();
    for (let i = 0; i <= 120; i++) { const k = (i / 120) * span; const ts = t - span + k; const v = ts < 0 ? f(0) : f(ts); if (i) g.lineTo(X(k), Y(v)); else g.moveTo(X(k), Y(v)); }
    g.stroke();
  };
  series(oilExpected, 'rgba(88, 230, 242, 0.95)', 1.5);
  series(oilMeasured, confirmed ? '#ff5c8c' : '#f2f6f4', 1.8);
}

/** A small tile of film grain, generated once. */
function grainTile() {
  const c = document.createElement('canvas'); c.width = c.height = 160;
  const g = c.getContext('2d')!; const img = g.createImageData(160, 160);
  for (let i = 0; i < img.data.length; i += 4) { const v = Math.random() * 255; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
  g.putImageData(img, 0, 0);
  return c.toDataURL('image/png');
}

export function SortieFilm({ onRunDemo, onOpenConsole, onOpenTwin, evidenceHref, armed, previewAt }: Props) {
  const root = useRef<HTMLElement>(null);
  const host = useRef<HTMLDivElement>(null);
  const mindRef = useRef<HTMLCanvasElement>(null);
  const trace = useRef<HTMLCanvasElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const flashRef = useRef<HTMLDivElement>(null);
  const clockRef = useRef<HTMLSpanElement>(null);
  const insertVid = useRef<HTMLVideoElement>(null);
  const gateBtn = useRef<HTMLButtonElement>(null);
  const markRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const bayRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const world = useRef<SortieWorld | null>(null);
  const sound = useRef<SortieSound | null>(null);
  const clock = useRef({
    t: previewAt ?? 0, real: 0, visible: true, ready: false,
    playing: previewAt === null && !reducedMotion(),
    phase: (previewAt === null ? 'gate' : 'play') as Phase,
    phaseEnd: 0,
  });
  const [ci, setCi] = useState(() => chapterAt(previewAt ?? 0));
  const [r, setR] = useState<Readout>(() => readout(previewAt ?? 0));
  const [playing, setPlaying] = useState(clock.current.playing);
  const [phase, setPhase] = useState<Phase>(clock.current.phase);
  const [radio, setRadio] = useState(-1);
  const [ended, setEnded] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'loading' | 'ready' | 'nogl'>('loading');
  const [bayInfo, setBayInfo] = useState<{ ready: boolean; meshes: number }>({ ready: false, meshes: 0 });
  const [muted, setMuted] = useState(true);
  const [opening, setOpening] = useState(0);

  const enterPhase = useCallback((p: Phase, seconds = 0) => {
    const c = clock.current;
    c.phase = p; c.phaseEnd = performance.now() + seconds * 1000; setPhase(p);
  }, []);
  const backToAir = useCallback(() => {
    if (clock.current.phase !== 'insert') return;
    enterPhase('play');
    sound.current?.cut();
  }, [enterPhase]);
  const startInsert = useCallback(() => {
    const v = insertVid.current;
    if (!v || reducedMotion()) return false;
    enterPhase('insert', INSERT.dur);
    try { v.currentTime = 0; void v.play().catch(() => {}); } catch { /* the cut still happens */ }
    sound.current?.ground(INSERT.dur, 2.35);
    return true;
  }, [enterPhase]);

  useEffect(() => {
    void startReservoir();
    const el = host.current, section = root.current, mind = mindRef.current;
    if (!el || !section || !mind) return;
    let raf = 0, disposed = false, last = performance.now(), lastUi = 0, lastGateFrame = 0;
    let lastCi = -1, lastRadio = -1, wasActive = true;
    const io = new IntersectionObserver(([e]) => { clock.current.visible = e.intersectionRatio > 0.25; }, { threshold: [0, 0.25, 0.5] });
    io.observe(section);
    const onVis = () => sound.current?.setActive(!document.hidden && clock.current.visible);
    document.addEventListener('visibilitychange', onVis);
    let lb = 0;
    const frameBars = () => {
      const w = section.clientWidth, h = section.clientHeight;
      lb = w / h > 1.3 ? Math.max(0, (h - w / 2.39) / 2) : 0;
      section.style.setProperty('--lb', `${Math.round(lb)}px`);
      const dpr = Math.min(window.devicePixelRatio, 2);
      mind.width = Math.round(w * dpr); mind.height = Math.round(h * dpr);
    };
    const sro = new ResizeObserver(frameBars); sro.observe(section); frameBars();
    section.style.setProperty('--grain', `url(${grainTile()})`);
    let ro: ResizeObserver | null = null;

    (async () => {
      let w: SortieWorld;
      try {
        const mod = await import('./world');
        if (disposed) return;
        w = new mod.SortieWorld(el);
      } catch {
        setStatus('nogl'); clock.current.ready = true; return;
      }
      world.current = w;
      w.resize();
      ro = new ResizeObserver(() => w.resize()); ro.observe(el);
      w.loadAircraft().catch(() => {}).finally(async () => {
        if (disposed) return;
        clock.current.ready = true; setStatus('ready');
        const v = insertVid.current;
        if (v && !v.src) { v.preload = 'auto'; v.src = INSERT.src; v.load(); }
        // the engine bay (the real CAD and the shared component map), then the engine section's models
        try {
          const res = await fetch('/twin/component_map.json', { cache: 'force-cache' });
          const map = (await res.json()) as ComponentMap;
          await w.loadBay(map);
          if (!disposed) setBayInfo({ ready: true, meshes: w.bay?.meshCount ?? 0 });
        } catch { /* the Inside chapter falls back to the Blender renders */ }
        void warmEngineModels();
      });

      const loop = (now: number) => {
        raf = requestAnimationFrame(loop);
        const c = clock.current;
        const dt = Math.min(0.25, (now - last) / 1000); last = now;
        const active = c.visible && !document.hidden;
        if (active !== wasActive) { wasActive = active; sound.current?.setActive(active); }
        if (!active) return;
        if (c.phase === 'gate') { if (now - lastGateFrame > 500) { lastGateFrame = now; w.frame(c.t, c.real, 0.016); } return; }
        if (c.phase === 'insert' && now >= c.phaseEnd) backToAir();
        const running = c.phase === 'play' && c.playing && c.ready;
        const prev = c.t;
        if (running) {
          const next = Math.min(TOTAL, c.t + dt);
          if (c.t < INSERT.at && next >= INSERT.at && startInsert()) c.t = INSERT.at;
          else c.t = next;
          c.real += dt;
        } else if (c.ready) c.real += dt;
        const screen: Screen = w.frame(c.t, c.real, running ? dt : 0.016);
        const i = chapterAt(c.t);
        const id = CHAPTERS[i].id;
        const k = (c.t - STARTS[i]) / CHAPTERS[i].dur;
        if (i !== lastCi) { lastCi = i; setCi(i); }
        const rd = readout(c.t);
        const d0 = tier0(c.t);
        const res = reservoir();
        const memF = res ? Math.min(res.frames - 1, Math.floor(c.t / 0.5)) : 0;
        sound.current?.update({
          t: c.t, r: rd, ci: i, playing: running, dt, listener: w.listener, bay: !!screen.bay,
          winners: id === 'detect' ? d0.winners : null,
          memory: id === 'memory' && res ? res.act.subarray(memF * res.show, (memF + 1) * res.show) : null,
        });
        const ri = radioAt(c.t);
        if (ri !== lastRadio) {
          if (ri >= 0 && running && prev < RADIO[ri].at && c.t - prev < 1) sound.current?.radio();
          lastRadio = ri; setRadio(ri);
        }
        if (clockRef.current) clockRef.current.textContent = missionClock(c.t);
        if (trace.current) drawTrace(trace.current, c.t, rd.confirmed);

        // the detector's head: drawn over the dimmed world in Detect and Memory
        const g = mind.getContext('2d')!;
        const dpr = Math.min(window.devicePixelRatio, 2);
        g.setTransform(dpr, 0, 0, dpr, 0, 0);
        const W = section.clientWidth, H = section.clientHeight;
        g.clearRect(0, 0, W, H);
        const R = region(W, H, lb);
        const aDetect = id === 'detect' ? sstep(0, 0.1, k) * (1 - sstep(0.94, 1, k)) : 0;
        const aMemory = id === 'memory' ? sstep(0, 0.08, k) * (1 - sstep(0.94, 1, k)) : 0;
        drawDetect(g, R, c.t, aDetect);
        drawMemory(g, R, c.t, startOf('memory'), res, aMemory);

        // the dissolve into and out of the engine bay
        if (flashRef.current) {
          const bump = (x: number, at: number, w2: number) => Math.max(0, 1 - Math.abs(x - at) / w2);
          flashRef.current.style.opacity = id === 'inside' ? String(Math.max(bump(k, BAY_IN, 0.035), bump(k, BAY_OUT, 0.035)) * 0.92) : '0';
        }
        const box = boxRef.current;
        if (box) {
          const pad = 16, bw = Math.max(64, screen.box.w + pad * 2), bh = Math.max(44, screen.box.h + pad * 2);
          box.style.transform = `translate(${screen.box.x + screen.box.w / 2 - bw / 2}px, ${screen.box.y + screen.box.h / 2 - bh / 2}px)`;
          box.style.width = `${bw}px`; box.style.height = `${bh}px`;
          box.dataset.on = String(screen.box.on);
        }
        for (const f of screen.fields) {
          const m = markRefs.current[f.id];
          if (m) { m.style.transform = `translate(${f.x}px, ${f.y}px)`; m.dataset.on = String(f.on); }
        }
        for (const key of BAY_KEYS) {
          const el2 = bayRefs.current[key]; if (!el2) continue;
          const lab = screen.bay?.find((b) => b.key === key);
          el2.dataset.on = String(!!lab?.on);
          if (lab) el2.style.transform = `translate(${lab.x}px, ${lab.y}px)`;
        }
        if (now - lastUi > 100) {
          lastUi = now;
          setR(rd);
          setProgress(k);
          setEnded(c.t >= TOTAL);
        }
      };
      raf = requestAnimationFrame(loop);
    })();

    return () => {
      disposed = true; cancelAnimationFrame(raf); io.disconnect(); sro.disconnect(); ro?.disconnect();
      document.removeEventListener('visibilitychange', onVis);
      world.current?.dispose(); world.current = null;
      sound.current?.dispose(); sound.current = null;
    };
  }, [startInsert, backToAir]);

  // development only: let tests place the clock just before an event
  useEffect(() => {
    if (!import.meta.env.DEV) return;
    (window as unknown as { __sortie?: unknown }).__sortie = { clock: clock.current };
  }, []);

  useEffect(() => { if (armed && phase === 'gate') gateBtn.current?.focus({ preventScroll: true }); }, [armed, phase]);

  /** Must run inside the click: Safari only lets audio start in the same task as the gesture. */
  const soundOn = useCallback(() => {
    try {
      if (!sound.current) sound.current = new SortieSound();
      void sound.current.resume();
      sound.current.setMuted(false);
      setMuted(false);
    } catch { /* no Web Audio: the film plays silent */ }
  }, []);

  const begin = useCallback((withSound: boolean) => {
    const c = clock.current;
    if (withSound) soundOn();
    c.t = 0; c.playing = !reducedMotion(); setPlaying(c.playing);
    world.current?.cut();
    enterPhase('play');
    setOpening((n) => n + 1); // one fade up from black: the only black in the film
  }, [soundOn, enterPhase]);

  const toggleSound = useCallback(() => {
    if (muted) soundOn();
    else { sound.current?.setMuted(true); setMuted(true); }
  }, [muted, soundOn]);

  const goTo = useCallback((i: number) => {
    const c = clock.current;
    if (c.phase === 'gate') return;
    const idx = Math.max(0, Math.min(CHAPTERS.length - 1, i));
    c.t = STARTS[idx];
    world.current?.cut();
    insertVid.current?.pause();
    if (!reducedMotion()) { c.playing = true; setPlaying(true); }
    setCi(idx); setR(readout(c.t)); setProgress(0); setEnded(false);
    enterPhase('play'); sound.current?.cut();
  }, [enterPhase]);
  const toggle = useCallback(() => {
    const c = clock.current;
    if (c.t >= TOTAL) { goTo(0); return; }
    c.playing = !c.playing; setPlaying(c.playing);
  }, [goTo]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const c = clock.current;
      if (!c.visible || c.phase === 'gate' || e.altKey || e.ctrlKey || e.metaKey) return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (e.key === 'ArrowRight') { e.preventDefault(); goTo(chapterAt(c.t) + 1); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); goTo(chapterAt(c.t) - 1); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [goTo]);

  const ch = CHAPTERS[ci];
  const id = ch.id;
  const u = id === 'inside' ? (progress - BAY_IN) / (BAY_OUT - BAY_IN) : -1;
  const inBay = u >= 0 && u < 1;
  const injected = inBay && u >= BAY_INJECT;
  const split = inBay && u >= 0.7;
  const showInstruments = id === 'twin' || id === 'drift';
  const worst = Math.max(...SCORERS.map((s) => r.ratios[s]));
  const tracking = id === 'drift' && worst >= 0.6 && !r.confirmed;
  const locked = id === 'decide' && r.confirmed;
  const showFields = id === 'glide' || id === 'land';
  const gated = phase === 'gate';
  const mindOn = id === 'detect' || id === 'memory';
  const line = radio >= 0 ? RADIO[radio] : null;
  const confirmAfter = (T_CONFIRM - T_INJECT).toFixed(1);

  return (
    <section ref={root} className={`so-film is-${id}${status === 'nogl' ? ' is-nogl' : ''}${ci >= 7 ? ' is-imax' : ''}${gated ? ' is-gated' : ''}${ended ? ' is-ended' : ''}${mindOn ? ' is-mind' : ''}${inBay ? ' is-bay' : ''}`} aria-labelledby="so-title" aria-roledescription="film">
      <div className="so-stage" ref={host} aria-hidden />
      <div className="so-shade" aria-hidden />
      <canvas ref={mindRef} className="so-mind" aria-hidden />
      <div ref={flashRef} className="so-flash" aria-hidden />
      {opening > 0 && <div key={opening} className="so-fadein" aria-hidden />}

      <h1 id="so-title" className="so-sr">ANUMAAN: a real-time digital twin that catches an engine fault early, names it, and brings the aircraft home</h1>

      <div ref={boxRef} className={`so-box${locked ? ' is-locked' : tracking ? ' is-tracking' : ''}`} aria-hidden>
        <i /><i /><i /><i />
        <span className="so-box-tag">{locked ? `Fault confirmed · ${DIRECTIVE.fault}` : 'Residual rising'}</span>
      </div>

      {GLIDE.fields.map((f) => (
        <div key={f.id} ref={(n) => { markRefs.current[f.id] = n; }} className={`so-mark${f.reach ? ' is-reach' : ''}${showFields ? ' is-shown' : ''}`} aria-hidden>
          <svg viewBox="0 0 24 24" width="22" height="22"><path d="M12 2 L22 12 L12 22 L2 12 Z" /><path d="M12 7v10M7 12h10" /></svg>
          <span><strong>{f.name}</strong>{f.reach ? `in reach · +${fmt(f.marginFt)} ft` : `${fmt(-f.marginFt)} ft short`}</span>
        </div>
      ))}

      {/* engine bay: subsystem callouts on the real geometry */}
      {BAY_KEYS.map((key) => (
        <div key={key} ref={(n) => { bayRefs.current[key] = n; }} className={`so-callout${key === 'oil' && injected ? ' is-fault' : ''}`} aria-hidden>
          <i /><span>{subsystemName(key)}</span>
        </div>
      ))}
      <div className={`so-baytag${inBay ? ' is-shown' : ''}`} aria-hidden={!inBay}>
        <strong>Rotax 912 iS</strong>
        <span>{bayInfo.ready ? `${bayInfo.meshes} named components` : '109 named components'} · from assets/blender/rotax_912_is_sport.blend</span>
      </div>
      <div className={`so-inject${injected ? ' is-shown' : ''}`} aria-hidden={!injected}>
        <p className="so-inject-line"><b>{INJECTION.method}</b> {INJECTION.path}</p>
        <p className="so-inject-body">{INJECTION.body}</p>
        <p className="so-inject-map">component_map.json · OIL_PRESSURE_LOSS → Oil_Tank · read by oil_p, oil_t</p>
      </div>
      <figure className={`so-blender${split || (inBay && !bayInfo.ready) ? ' is-shown' : ''}`} aria-hidden={!split}>
        <img src={injected || !inBay ? '/survey/blender/rotax_912is_oil_pressure_loss.webp' : '/survey/blender/rotax_912is_nominal.webp'} alt="" width={1200} height={675} loading="lazy" decoding="async" />
        <figcaption><b>Blender</b> · the diagnostic app's materials, driven by the same map</figcaption>
      </figure>
      <p className={`so-webtag${split && bayInfo.ready ? ' is-shown' : ''}`} aria-hidden><b>Web</b> · live three.js render of /models/rotax_912is.glb · tests/test_component_map.py</p>

      <div className="so-copy" key={`${ch.id}-${opening}`}>
        {id === 'open' && <p className="so-word"><span>ANUMAAN</span><span lang="hi">अनुमान</span></p>}
        <h2>{ch.title}</h2>
        <p>{ch.body}</p>
      </div>

      <aside className={`so-inst${showInstruments ? ' is-shown' : ''}`} aria-label="Engine telemetry, Rotax 912 iS">
        <header><strong>Rotax 912 iS</strong><span className={r.confirmed ? 'is-alarm' : r.raw ? 'is-warn' : undefined}>Twin {r.confirmed ? 'alarm' : r.raw ? 'deviation' : 'nominal'}</span></header>
        <div className="so-trace">
          <div className="so-trace-key"><span className="is-meas">Oil pressure, measured</span><span className="is-exp">Twin expects</span><span className="is-lim">Fixed limit</span></div>
          <canvas ref={trace} aria-label={`Oil pressure ${fmt(r.oilP, 2)} bar measured, ${fmt(r.oilPExp, 2)} bar expected, limit ${OIL.limit} bar`} role="img" />
        </div>
        <dl className="so-read">
          <div><dt>Oil pressure</dt><dd className={r.confirmed ? 'is-alarm' : undefined}>{fmt(r.oilP, 2)}<small>bar</small></dd></div>
          <div><dt>Oil temp</dt><dd>{fmt(r.oilT, 0)}<small>°C</small></dd></div>
          <div><dt>Hottest CHT</dt><dd>{fmt(r.cht, 0)}<small>°C</small></dd></div>
          <div><dt>Engine speed</dt><dd>{fmt(r.rpm, 0)}<small>rpm</small></dd></div>
        </dl>
        {SCORERS.map((s) => (
          <div className="so-meter" key={s}>
            <div className="so-meter-head"><span>{SCORER_LABEL[s]}</span><output>{fmt(r.ratios[s], 2)}× threshold</output></div>
            <div className="so-bar"><span style={{ transform: `scaleX(${Math.min(1, r.ratios[s] / 2.5)})` }} className={r.ratios[s] > 1 ? 'is-over' : undefined} /><i style={{ left: '40%' }} title="Split-conformal threshold" /></div>
          </div>
        ))}
        <p className="so-sanity is-shown">Computed live in this browser by the ported tier-0 detector</p>
      </aside>

      <aside className={`so-decide${id === 'decide' ? ' is-shown' : ''}`} aria-label="Decision support">
        <div className="so-dec-row is-wide"><span>Maintenance directive</span><strong>{DIRECTIVE.ata} · {DIRECTIVE.fault}</strong><p>{DIRECTIVE.action}. Named by the reservoir readout; confirmed by the gate {confirmAfter} s after injection.</p></div>
        <div className="so-dec-row"><span>Remaining useful life</span><strong>{fmt(r.rul, 1)} h</strong><p>{fmt(r.rulLo, 1)}–{fmt(r.rulHi, 1)} h, conformal interval</p></div>
        <div className="so-dec-row"><span>This sortie</span><strong>{fmt(r.missionRel * 100, 0)}%</strong><p>odds of completing the 18 h ISR profile</p></div>
      </aside>

      <aside className={`so-glide${showFields ? ' is-shown' : ''}`} aria-label="Engine-out glide">
        <header><strong>Engine-out glide</strong><span>L/D {GLIDE.ld} · from {fmt(GLIDE.altFt)} ft</span></header>
        <ul>{GLIDE.fields.map((f) => <li key={f.id} className={f.reach ? 'is-reach' : undefined}><span>{f.name}<small>{f.id} · {f.nm} nm</small></span><span>{f.reach ? `+${fmt(f.marginFt)} ft` : `${fmt(-f.marginFt)} ft short`}</span></li>)}</ul>
        <p>Altitude now <output>{fmt(Math.round(r.altFt / 10) * 10)} ft</output></p>
      </aside>

      <div className="so-bars" aria-hidden><i /><i /></div>
      <div className="so-grain" aria-hidden />

      <div className="so-top">
        <p className="so-note" aria-hidden>{status === 'loading' ? 'Loading the airframe…' : 'Simulated sortie · detector and reservoir computed live · schematic terrain'}</p>
        <p className="so-radio" aria-live="polite">{line && <span key={radio}><b>{line.who}</b>{line.line}</span>}</p>
        <p className="so-clock" aria-hidden><span>Sortie 26054</span><span ref={clockRef}>{missionClock(previewAt ?? 0)}</span></p>
      </div>

      <nav className="so-controls" aria-label="Film chapters">
        <button type="button" className="so-icon" onClick={toggle} aria-label={ended ? 'Replay the film' : playing ? 'Pause the film' : 'Play the film'}>
          {ended ? <RotateCcw size={16} /> : playing ? <Pause size={16} /> : <Play size={16} />}
        </button>
        <button type="button" className="so-icon" onClick={() => goTo(ci - 1)} disabled={ci === 0} aria-label="Previous chapter"><ChevronLeft size={18} /></button>
        <ol className="so-rail">
          {CHAPTERS.map((c, i) => (
            <li key={c.id}>
              <button type="button" onClick={() => goTo(i)} aria-current={i === ci ? 'step' : undefined} className={i < ci ? 'is-done' : i === ci ? 'is-now' : undefined}>
                <span className="so-rail-fill" style={i === ci ? { transform: `scaleX(${Math.min(1, progress)})` } : undefined} />
                <span className="so-rail-label">{c.rail}</span>
              </button>
            </li>
          ))}
        </ol>
        <button type="button" className="so-icon" onClick={() => goTo(ci + 1)} disabled={ci === CHAPTERS.length - 1} aria-label="Next chapter"><ChevronRight size={18} /></button>
        <button type="button" className="so-icon" onClick={toggleSound} aria-label={muted ? 'Turn sound on' : 'Turn sound off'} aria-pressed={!muted}>
          {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
        </button>
        <a className="so-skip" href={evidenceHref}>Skip to the evidence <ArrowDown size={14} aria-hidden /></a>
      </nav>

      <div className={`so-insert${phase === 'insert' ? ' is-shown' : ''}`} aria-hidden={phase !== 'insert'}>
        <p className="so-insert-tag">Ground control · Leh</p>
        <video ref={insertVid} muted playsInline preload="none" disablePictureInPicture tabIndex={-1} />
        <p className="so-insert-note">Recorded from the real console</p>
      </div>

      <div className={`so-final${ended && phase === 'play' ? ' is-shown' : ''}`} aria-hidden={!ended}>
        <div className="so-final-inner">
          <p className="so-final-word">ANUMAAN</p>
          <p className="so-final-hi"><span lang="hi">अनुमान</span> · inference</p>
          <ul className="so-final-facts">
            <li><b>Computed, not animated.</b> The detector you watched was the backend's tier-0 algorithm running in this browser: it confirmed the fault {confirmAfter} s after injection, and its gate held back {NOMINAL_RAW} raw false alarm{NOMINAL_RAW === 1 ? '' : 's'} before the fault existed.</li>
            <li><b>In the runtime</b> (simulation, five engines × three tails, experiment E20): every scalar-visible fault detected, zero confirmed false alarms in 300 nominal ticks, oil-pressure loss confirmed 7–10 s after injection.</li>
          </ul>
          <div className="so-final-actions">
            <button type="button" className="so-btn so-btn-hot" onClick={onRunDemo} tabIndex={ended ? 0 : -1}><Play size={16} aria-hidden /> Run the 60-second demo</button>
            <button type="button" className="so-btn so-btn-ghost" onClick={onOpenTwin} tabIndex={ended ? 0 : -1}><Box size={16} aria-hidden /> Inject a fault in the 3D twin</button>
            <button type="button" className="so-btn so-btn-ghost" onClick={onOpenConsole} tabIndex={ended ? 0 : -1}>Open the live console <ArrowUpRight size={15} aria-hidden /></button>
          </div>
          <div className="so-final-more">
            <button type="button" onClick={() => goTo(0)} tabIndex={ended ? 0 : -1}><RotateCcw size={14} aria-hidden /> Watch again</button>
            <a href={evidenceHref} tabIndex={ended ? 0 : -1}>See the evidence <ArrowDown size={14} aria-hidden /></a>
          </div>
        </div>
      </div>

      <div className={`so-gate${gated && armed ? ' is-shown' : ''}`} role="dialog" aria-modal="false" aria-labelledby="so-gate-title" hidden={!gated}>
        {armed && (
          <div className="so-gate-inner">
            <p id="so-gate-title" className="so-gate-title">What we built, running</p>
            <p className="so-gate-lede">Ninety seconds. A fault injected into the real CAD, caught by our detector computed live in your browser, named from memory, and the airframe brought home.</p>
            <div className="so-gate-actions">
              <button ref={gateBtn} type="button" className="so-btn so-btn-light" onClick={() => begin(true)}><Volume2 size={17} aria-hidden /> Begin with sound</button>
              <button type="button" className="so-btn so-btn-ghost" onClick={() => begin(false)}>Watch without sound</button>
            </div>
            <a className="so-gate-skip" href={evidenceHref}>Or skip to the evidence <ArrowDown size={14} aria-hidden /></a>
          </div>
        )}
      </div>
    </section>
  );
}

export default SortieFilm;
