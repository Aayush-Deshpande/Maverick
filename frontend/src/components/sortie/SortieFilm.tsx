import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ArrowDown, ArrowUpRight, Box, ChevronLeft, ChevronRight, Pause, Play, RotateCcw, Volume2, VolumeX } from 'lucide-react';
import { CHAPTERS, DIRECTIVE, GLIDE, INJECTION, MOVEMENTS, OIL, STARTS, TOTAL, T_ASSESS, T_INJECT, chapterAt, gauges, oilExpected, oilMeasured, startOf } from './story';
import { INSERT, RADIO, RADIO_HOLD, T_CONFIRM, readout, type Readout } from './timeline';
import { NOMINAL_RAW, SCORERS, tier0 } from './detector';
import { reservoir, startReservoir } from './brain';
import { drawDetect, drawMemory, region } from './mind';
import { drawPipeline, drawUnseen, pipelineReach, type UnseenState } from './scenes';
import { subsystemName, type ComponentMap } from './bay';
import type { Screen, SortieWorld } from './world';
import { SortieSound } from './sound';
import { warmEngineModels } from './warmup';
import { preloader } from './preload';
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

const BAY_KEYS = ['oil', 'fuel', 'ignition', 'cooling', 'exhaust', 'gearbox', 'electrical', 'control'];
const ENGINE_LINEUP: Array<[string, string]> = [['rotax_912is', 'Rotax 912 iS'], ['rotax_914', 'Rotax 914 F'], ['rotax_915is', 'Rotax 915 iS'], ['austro_ae300', 'Austro AE300'], ['vrde_jayem_2_2l', 'VRDE–Jayem 2.2L']];
/** The order the assessment resolves the airfields: furthest first, the one that works last. */
const FIELD_ORDER = ['VIKG', 'VILH', 'VI82'];
const SCORER_LABEL = { fly_bloom: 'Fly Bloom', mahalanobis: 'Mahalanobis', max_abs_z: 'max |z|' } as const;

const fmt = (v: number, d = 0) => v.toLocaleString('en-IN', { maximumFractionDigits: d, minimumFractionDigits: d });
const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const pad2 = (n: number) => String(Math.floor(n)).padStart(2, '0');
const sstep = (a: number, b: number, x: number) => { const k = Math.min(1, Math.max(0, (x - a) / (b - a))); return k * k * (3 - 2 * k); };
/** Sortie elapsed time: the film opens six hours into the eighteen-hour sortie. */
const missionClock = (t: number) => { const s = 6 * 3600 + 14 * 60 + 7 + t; return `T+${pad2(s / 3600)}:${pad2((s % 3600) / 60)}:${pad2(s % 60)}`; };
const mb = (b: number) => (b / 1e6).toFixed(1);
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
  const [flash, setFlash] = useState(false);
  const [forceBegin, setForceBegin] = useState(false);
  // the loading dialog: polled while it is on screen
  const [load, setLoad] = useState(() => ({ ...preloader.summary(), tasks: preloader.tasks.map((t) => ({ ...t })), ready: preloader.ready, failed: preloader.anyFailed }));
  useEffect(() => {
    if (previewAt !== null) return;
    const id = window.setInterval(() => {
      setLoad({ ...preloader.summary(), tasks: preloader.tasks.map((t) => ({ ...t })), ready: preloader.ready, failed: preloader.anyFailed });
      if (preloader.ready) window.clearInterval(id);
    }, 200);
    return () => window.clearInterval(id);
  }, [previewAt]);

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
    preloader.start();
    void startReservoir().then((res) => preloader.step('reservoir', !res));
    const el = host.current, section = root.current, mind = mindRef.current;
    if (!el || !section || !mind) return;
    let raf = 0, disposed = false, last = performance.now(), lastUi = 0, lastGateFrame = 0;
    let lastCi = -1, lastRadio = -1, wasActive = true, lastFlash = false;
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
        setStatus('nogl'); clock.current.ready = true; preloader.step('scene', true); preloader.step('aircraft', true); preloader.step('bay', true); return;
      }
      world.current = w;
      w.resize();
      ro = new ResizeObserver(() => w.resize()); ro.observe(el);
      w.loadAircraft().then(() => preloader.step('aircraft'), () => preloader.step('aircraft', true)).finally(async () => {
        if (disposed) return;
        clock.current.ready = true; setStatus('ready');
        const v = insertVid.current;
        if (v && !v.src) { v.preload = 'auto'; v.src = INSERT.src; v.load(); }
        // the engine bay (the real CAD and the shared component map), then the engine section's models
        try {
          const raw = await preloader.bytes('/twin/component_map.json');
          const map = (raw ? JSON.parse(new TextDecoder().decode(raw)) : await (await fetch('/twin/component_map.json')).json()) as ComponentMap;
          await w.loadBay(map);
          preloader.step('bay');
          if (!disposed) setBayInfo({ ready: true, meshes: w.bay?.meshCount ?? 0 });
        } catch { preloader.step('bay', true); /* the Inside chapter falls back to the Blender renders */ }
        void warmEngineModels();
      });

      const loop = (now: number) => {
        raf = requestAnimationFrame(loop);
        const c = clock.current;
        const dt = Math.min(0.25, (now - last) / 1000); last = now;
        const active = c.visible && !document.hidden;
        if (active !== wasActive) { wasActive = active; sound.current?.setActive(active); }
        if (!active) return;
        if (c.phase === 'gate') {
          // behind the dialog: one frame every half second; the first one compiles the shaders
          if (now - lastGateFrame > 500) { lastGateFrame = now; w.frame(c.t, c.real, 0.016); preloader.step('scene'); }
          return;
        }
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
        const aDetect = id === 'detect' && c.t < T_CONFIRM ? sstep(0, 0.1, k) : 0;
        const aMemory = id === 'memory' ? sstep(0, 0.08, k) * (1 - sstep(0.94, 1, k)) : 0;
        drawDetect(g, R, c.t, aDetect);
        drawMemory(g, R, c.t, startOf('memory'), res, aMemory);
        const fade = (x: number) => sstep(0, 0.07, x) * (1 - sstep(0.95, 1, x));
        drawPipeline(g, R, c.t, k, res, id === 'pipeline' ? fade(k) : 0);
        const unseen: UnseenState | null = drawUnseen(g, R, k, res, id === 'beyond' ? fade(k) : 0);
        // the engine is measured: points on the real geometry, their lines gathering into one bundle
        if (screen.bay) {
          const bx = W * (screen.bay.split > 0 ? 0.97 : 0.9), by = H * 0.52;
          screen.bay.sensors.forEach((sn) => {
            if (!sn.on) return;
            g.strokeStyle = sn.hot ? 'rgba(255, 140, 70, 0.75)' : 'rgba(88, 230, 242, 0.45)'; g.lineWidth = sn.hot ? 1.6 : 1;
            g.beginPath(); g.moveTo(sn.x, sn.y); g.bezierCurveTo(sn.x + (bx - sn.x) * 0.5, sn.y, bx - 40, by, bx, by); g.stroke();
            g.fillStyle = sn.hot ? 'rgba(255, 140, 70, 1)' : 'rgba(88, 230, 242, 1)';
            g.beginPath(); g.arc(sn.x, sn.y, 4, 0, Math.PI * 2); g.fill();
            g.font = '600 11px "JetBrains Mono", monospace'; g.textAlign = 'left';
            g.fillStyle = 'rgba(238, 246, 243, 0.85)'; g.fillText(sn.channels, sn.x + 9, sn.y - 8);
          });
        }
        // the assessment: lines from the aircraft to each field, resolving one at a time
        if (id === 'decide' && screen.aircraft.on) {
          FIELD_ORDER.forEach((fid, n) => {
            const at = T_ASSESS + 1.4 + n * 1.3;
            if (c.t < at - 0.9) return;
            const f = screen.fields.find((x) => x.id === fid); const spec = GLIDE.fields.find((x) => x.id === fid);
            if (!f || !spec || !f.on) return;
            const done = c.t >= at, grow = Math.min(1, (c.t - (at - 0.9)) / 0.9);
            g.setLineDash(done ? [] : [6, 6]);
            g.strokeStyle = done ? (spec.reach ? 'rgba(88, 230, 242, 0.95)' : 'rgba(255, 79, 139, 0.85)') : 'rgba(238, 246, 243, 0.5)';
            g.lineWidth = done && spec.reach ? 2 : 1.2;
            g.beginPath(); g.moveTo(screen.aircraft.x, screen.aircraft.y);
            g.lineTo(screen.aircraft.x + (f.x - screen.aircraft.x) * grow, screen.aircraft.y + (f.y - screen.aircraft.y) * grow); g.stroke();
            g.setLineDash([]);
          });
        }
        sound.current?.update({
          t: c.t, r: rd, ci: i, playing: running, dt, listener: w.listener, bay: !!screen.bay,
          winners: id === 'detect' ? d0.winners : null,
          stage: id === 'pipeline' ? pipelineReach(k) : null,
          unseen,
          memory: id === 'memory' && res ? res.act.subarray(memF * res.show, (memF + 1) * res.show) : null,
          flash: screen.flash,
        });
        if (screen.flash !== lastFlash) { lastFlash = screen.flash; setFlash(screen.flash); }

        // the dissolve into and out of the engine bay
        if (flashRef.current) {
          const bump = (x: number, at: number, w2: number) => Math.max(0, 1 - Math.abs(x - at) / w2);
          void bump;
          // dissolves through light: into the engine, and out of it into the data
          const op = id === 'approach' ? sstep(0.86, 0.98, k) : id === 'inside' ? 1 - sstep(0, 0.07, k)
            : id === 'signal' ? sstep(0.88, 0.99, k) : id === 'pipeline' ? 1 - sstep(0, 0.06, k) : 0;
          flashRef.current.style.opacity = String(op * 0.95);
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
          const lab = screen.bay?.labels.find((b) => b.key === key);
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

  const canBegin = load.ready || forceBegin;
  useEffect(() => { if (armed && phase === 'gate' && canBegin) gateBtn.current?.focus({ preventScroll: true }); }, [armed, phase, canBegin]);
  // the site behind the dialog does not scroll until the film begins
  useEffect(() => {
    if (previewAt !== null || phase !== 'gate') return;
    document.documentElement.classList.add('so-locked');
    return () => document.documentElement.classList.remove('so-locked');
  }, [phase, previewAt]);

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
  const inBay = (id === 'inside' || id === 'signal') && bayInfo.ready;
  const signalHot = id === 'signal' && progress > 0.18;
  const split = id === 'signal' && progress > 0.46 && progress < 0.78;
  const showInstruments = id === 'twin' || (id === 'signal' && progress < 0.44);
  const afterConfirm = r.t >= T_CONFIRM;
  const locked = (id === 'detect' && afterConfirm) || (id === 'decide' && progress < 0.33);
  const resolved = (fid: string) => r.t >= T_ASSESS + 1.4 + FIELD_ORDER.indexOf(fid) * 1.3;
  const showFieldMark = (fid: string) => (id === 'decide' && resolved(fid)) || id === 'divert' || id === 'land';
  const showGlide = (id === 'decide' && resolved('VI82')) || id === 'divert';
  const gated = phase === 'gate';
  const mindOn = id === 'pipeline' || (id === 'detect' && !afterConfirm) || id === 'memory' || id === 'beyond';
  const line = radio >= 0 ? RADIO[radio] : null;
  const movement = ch.movement;
  const mStart = STARTS[CHAPTERS.findIndex((c) => c.movement === movement)];
  const mEnd = (() => { const last = CHAPTERS.map((c, i) => [c, i] as const).filter(([c]) => c.movement === movement).pop()!; return STARTS[last[1]] + last[0].dur; })();
  const mProgress = Math.min(1, Math.max(0, (r.t - mStart) / (mEnd - mStart)));
  const oilAtConfirm = gauges(T_CONFIRM).oilP;
  const copy = id === 'detect' && afterConfirm
    ? { title: `Confirmed ${(T_CONFIRM - T_INJECT).toFixed(1)} s after onset.`, body: `Oil pressure is still ${fmt(oilAtConfirm, 2)} bar; the fixed limit is ${OIL.limit}. The gauge never left the green.` }
    : { title: ch.title, body: ch.body };
  const showCopy = !!copy.title && !flash && !(id === 'cold' && progress < 0.42) && !(id === 'signal' && split);
  const needle = -120 + 240 * Math.min(1, Math.max(0, r.oilP / 6)); // 0..6 bar across 240 degrees
  const confirmAfter = (T_CONFIRM - T_INJECT).toFixed(1);

  return (
    <section ref={root} className={`so-film is-${id}${status === 'nogl' ? ' is-nogl' : ''}${ci >= CHAPTERS.findIndex((x) => x.id === 'decide') ? ' is-imax' : ''}${flash ? ' is-flash' : ''}${gated ? ' is-gated' : ''}${ended ? ' is-ended' : ''}${mindOn ? ' is-mind' : ''}${inBay ? ' is-bay' : ''}`} aria-labelledby="so-title" aria-roledescription="film">
      <div className="so-stage" ref={host} aria-hidden />
      <div className="so-shade" aria-hidden />
      <canvas ref={mindRef} className="so-mind" aria-hidden />
      <div ref={flashRef} className="so-flash" aria-hidden />
      {opening > 0 && <div key={opening} className="so-fadein" aria-hidden />}

      <h1 id="so-title" className="so-sr">ANUMAAN: a real-time digital twin that catches an engine fault early, names it, and brings the aircraft home</h1>

      <div ref={boxRef} className={`so-box${locked ? ' is-locked' : ''}`} aria-hidden>
        <i /><i /><i /><i />
        <span className="so-box-tag">{locked ? `Fault confirmed · ${DIRECTIVE.fault}` : 'Residual rising'}</span>
      </div>

      {GLIDE.fields.map((f) => (
        <div key={f.id} ref={(n) => { markRefs.current[f.id] = n; }} className={`so-mark${f.reach ? ' is-reach' : ''}${showFieldMark(f.id) ? ' is-shown' : ''}`} aria-hidden>
          <svg viewBox="0 0 24 24" width="22" height="22"><path d="M12 2 L22 12 L12 22 L2 12 Z" /><path d="M12 7v10M7 12h10" /></svg>
          <span><strong>{f.name}</strong>{f.reach ? `in reach · +${fmt(f.marginFt)} ft` : `${fmt(-f.marginFt)} ft short`}</span>
        </div>
      ))}

      {/* engine bay: subsystem callouts on the real geometry */}
      {BAY_KEYS.map((key) => (
        <div key={key} ref={(n) => { bayRefs.current[key] = n; }} className={`so-callout${key === 'oil' && signalHot ? ' is-fault' : ''}`} aria-hidden>
          <i /><span>{subsystemName(key)}</span>
        </div>
      ))}
      <div className={`so-baytag${inBay && id === 'inside' ? ' is-shown' : ''}`} aria-hidden={!(inBay && id === 'inside')}>
        <strong>Rotax 912 iS</strong>
        <span>{bayInfo.ready ? `${bayInfo.meshes} named components` : '109 named components'} · from assets/blender/rotax_912_is_sport.blend</span>
      </div>
      <figure className={`so-blender${split ? ' is-shown' : ''}`} aria-hidden={!split}>
        <img src="/survey/blender/rotax_912is_oil_pressure_loss.webp" alt="" width={1200} height={675} loading="lazy" decoding="async" />
        <figcaption><b>Blender</b> · the same fault, the same component map, the diagnostic app's own materials</figcaption>
      </figure>
      <p className={`so-webtag${split ? ' is-shown' : ''}`} aria-hidden><b>Web</b> · live render of /models/rotax_912is.glb</p>
      {(id === 'inside' || id === 'signal') && !bayInfo.ready && (
        <figure className="so-blender is-shown"><img src="/survey/blender/rotax_912is_nominal.webp" alt="" width={1200} height={675} /><figcaption><b>Blender</b> · Rotax 912 iS, 109 named components</figcaption></figure>
      )}

      {/* the old way: a gauge that is still green */}
      <figure className={`so-gauge${id === 'problem' && progress > 0.18 && !flash ? ' is-shown' : ''}`} aria-hidden>
        <svg viewBox="0 0 200 200" width="200" height="200">
          <circle cx="100" cy="100" r="92" fill="rgba(6,12,14,0.78)" stroke="rgba(238,246,243,0.35)" strokeWidth="2" />
          <path d="M 35.6 137.2 A 74 74 0 0 1 38.2 59.1" fill="none" stroke="#ff4f8b" strokeWidth="8" />
          <path d="M 38.2 59.1 A 74 74 0 0 1 164.4 137.2" fill="none" stroke="#3fbf7f" strokeWidth="8" />
          {[0, 1, 2, 3, 4, 5, 6].map((v) => { const a2 = ((-120 + v * 40) - 90) * Math.PI / 180; return <g key={v}><line x1={100 + 64 * Math.cos(a2)} y1={100 + 64 * Math.sin(a2)} x2={100 + 56 * Math.cos(a2)} y2={100 + 56 * Math.sin(a2)} stroke="rgba(238,246,243,0.8)" strokeWidth="2" /><text x={100 + 44 * Math.cos(a2)} y={104 + 44 * Math.sin(a2)} fill="rgba(238,246,243,0.75)" fontSize="12" textAnchor="middle" fontFamily="JetBrains Mono, monospace">{v}</text></g>; })}
          <line x1="100" y1="100" x2={100 + 70 * Math.cos((needle - 90) * Math.PI / 180)} y2={100 + 70 * Math.sin((needle - 90) * Math.PI / 180)} stroke="#f4f6f5" strokeWidth="3" strokeLinecap="round" />
          <circle cx="100" cy="100" r="6" fill="#f4f6f5" />
          <text x="100" y="150" fill="rgba(238,246,243,0.7)" fontSize="11" textAnchor="middle" fontFamily="Sofia Sans Condensed, sans-serif" letterSpacing="2">OIL PRESS · BAR</text>
        </svg>
      </figure>
      <p className={`so-flashcap${flash ? ' is-shown' : ''}`} aria-hidden>What a late warning looks like.</p>

      {/* the decision, in the system's own words (backend/mission/prescriptive.py) */}
      <aside className={`so-options${id === 'decide' ? ' is-shown' : ''}`} aria-label="Decision support">
        <p className="so-opt-head">ATA 79 · {DIRECTIVE.fault} · RUL {fmt(r.rul, 1)} h ({fmt(r.rulLo, 1)}–{fmt(r.rulHi, 1)})</p>
        <ol>
          <li className={progress > 0.06 ? 'is-in' : undefined}><b>Continue as planned</b><span>18 h reliability {fmt(r.missionRel * 100, 0)}%</span></li>
          <li className={progress > 0.15 ? 'is-in' : undefined}><b>Derate to 85%</b><span>damage rate −40% · still not achievable</span></li>
          <li className={`${progress > 0.24 ? 'is-in' : ''}${resolved('VI82') ? ' is-pick' : ''}`}><b>{resolved('VI82') ? 'Divert Thoise' : 'Divert'}</b><span>{resolved('VI82') ? 'in glide reach · +1,600 ft' : 'assessing reach…'}</span></li>
        </ol>
      </aside>

      <figure className={`so-engines${id === 'pipeline' ? ' is-shown' : ''}`} aria-hidden={id !== 'pipeline'}>
        <ul>{ENGINE_LINEUP.map(([eid, name]) => <li key={eid}><img src={`/survey/posters/${eid}.webp`} alt="" width={1200} height={900} loading="lazy" decoding="async" /><small>{name}</small></li>)}</ul>
        <figcaption>One pipeline, five engine profiles, calibrated per aircraft. E17 (simulation): Mahalanobis AUROC 0.973 on an engine it had never seen.</figcaption>
      </figure>

      {showCopy && (
        <div className={`so-copy is-${id}`} key={`${ch.id}-${opening}-${afterConfirm && id === 'detect' ? 'c' : ''}`}>
          {id === 'cold' ? <><p className="so-place">{copy.body}</p><h2 className="so-one">{copy.title}</h2></> : <><h2>{copy.title}</h2><p>{copy.body}</p></>}
        </div>
      )}

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

      <aside className={`so-glide${showGlide ? ' is-shown' : ''}`} aria-label="Engine-out glide">
        <header><strong>Engine-out glide</strong><span>L/D {GLIDE.ld} · from {fmt(GLIDE.altFt)} ft</span></header>
        <ul>{GLIDE.fields.map((f) => <li key={f.id} className={f.reach ? 'is-reach' : undefined}><span>{f.name}<small>{f.id} · {f.nm} nm</small></span><span>{f.reach ? `+${fmt(f.marginFt)} ft` : `${fmt(-f.marginFt)} ft short`}</span></li>)}</ul>
        <p>Altitude now <output>{fmt(Math.round(r.altFt / 10) * 10)} ft</output></p>
      </aside>

      <div className="so-bars" aria-hidden><i /><i /></div>
      <div className="so-grain" aria-hidden />

      <div className="so-top">
        <p className="so-note" aria-hidden>{status === 'loading' ? 'Loading the airframe…' : 'A dramatised simulated sortie · everything inside the machine computed live'}</p>
        <p className="so-radio" aria-live="polite">{line && <span key={radio}><b>{line.who}</b>{line.line}</span>}</p>
        <p className="so-clock" aria-hidden><span>Sortie 26054</span><span ref={clockRef}>{missionClock(previewAt ?? 0)}</span></p>
      </div>

      <nav className="so-controls" aria-label="Film chapters">
        <button type="button" className="so-icon" onClick={toggle} aria-label={ended ? 'Replay the film' : playing ? 'Pause the film' : 'Play the film'}>
          {ended ? <RotateCcw size={16} /> : playing ? <Pause size={16} /> : <Play size={16} />}
        </button>
        <button type="button" className="so-icon" onClick={() => goTo(CHAPTERS.findIndex((c) => c.movement === Math.max(0, movement - (r.t - mStart > 2 ? 0 : 1))))} disabled={ci === 0} aria-label="Previous movement"><ChevronLeft size={18} /></button>
        <ol className="so-rail" style={{ gridTemplateColumns: `repeat(${MOVEMENTS.length}, minmax(0, 1fr))` }}>
          {MOVEMENTS.map((m, mi) => (
            <li key={m}>
              <button type="button" onClick={() => goTo(CHAPTERS.findIndex((c) => c.movement === mi))} aria-current={mi === movement ? 'step' : undefined} className={mi < movement ? 'is-done' : mi === movement ? 'is-now' : undefined}>
                <span className="so-rail-fill" style={mi === movement ? { transform: `scaleX(${mProgress})` } : undefined} />
                <span className="so-rail-label">{m}</span>
              </button>
            </li>
          ))}
        </ol>
        <button type="button" className="so-icon" onClick={() => goTo(CHAPTERS.findIndex((c) => c.movement === movement + 1))} disabled={movement >= MOVEMENTS.length - 1} aria-label="Next movement"><ChevronRight size={18} /></button>
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
            <li><b>How it was tested.</b> The fault in this film, like every fault in the console, was injected into the plant model through the console's own API: <code>{INJECTION.method} {INJECTION.path}</code>.</li>
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

      {/* the gate, over the whole site: assets load first (with progress and time left), then a click,
          which is the only way a browser allows sound */}
      {previewAt === null && gated && typeof document !== 'undefined' && createPortal(
        <div className={`so-gate${armed ? ' is-shown' : ''}`} role="dialog" aria-modal="true" aria-labelledby="so-gate-title">
          {armed && (canBegin ? (
            <div className="so-gate-inner" key="ready">
              <p id="so-gate-title" className="so-gate-title">What we built, running</p>
              <p className="so-gate-lede">Two and a half minutes. One aircraft, one engine, one fault: caught while every gauge was green, traced through the real system, and brought home. Everything inside the machine is computed live in your browser.</p>
              {load.failed && <p className="so-gate-warn">Some assets did not load; the film will use stills where it has to.</p>}
              <div className="so-gate-actions">
                <button ref={gateBtn} type="button" className="so-btn so-btn-light" onClick={() => begin(true)}><Volume2 size={17} aria-hidden /> Begin with sound</button>
                <button type="button" className="so-btn so-btn-ghost" onClick={() => begin(false)}>Watch without sound</button>
              </div>
              <button type="button" className="so-gate-skip" onClick={() => { begin(false); document.querySelector(evidenceHref)?.scrollIntoView(); }}>Or skip to the evidence <ArrowDown size={14} aria-hidden /></button>
            </div>
          ) : (
            <div className="so-gate-inner so-loading" key="loading" aria-live="polite">
              <p id="so-gate-title" className="so-gate-title">Please wait · loading assets</p>
              <div className="so-load-bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(load.progress * 100)}>
                <span style={{ transform: `scaleX(${load.progress})` }} />
              </div>
              <p className="so-load-figs">
                <output>{Math.round(load.progress * 100)}%</output>
                <span>{mb(load.loaded)} of {mb(load.total)} MB</span>
                <span>{load.eta === null ? 'estimating time…' : load.eta < 1 ? 'almost there' : `about ${Math.ceil(load.eta)} s left`}</span>
              </p>
              <ul className="so-load-list">
                {load.tasks.map((task) => (
                  <li key={task.id} className={task.failed ? 'is-failed' : task.done ? 'is-done' : undefined}>
                    <span className="so-load-mark" aria-hidden>{task.failed ? '!' : task.done ? '✓' : ''}</span>
                    <span>{task.label}</span>
                    <small>{task.kind === 'bytes' ? (task.done ? `${mb(task.total)} MB` : `${Math.round((task.loaded / Math.max(1, task.total)) * 100)}%`) : task.done ? 'done' : ''}</small>
                  </li>
                ))}
              </ul>
              {load.elapsed > 20 && <button type="button" className="so-gate-skip" onClick={() => setForceBegin(true)}>Continue without waiting</button>}
            </div>
          ))}
        </div>,
        document.body,
      )}
    </section>
  );
}

export default SortieFilm;
