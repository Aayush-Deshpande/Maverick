"""Sortie health report (card M5-06, P Part 4 Step 5.6, T-MIS-5). One self-contained HTML file per recording.

Built only from the recording (backend/recording): measured frames, the decision timeline and, when the API recorded
them, the published state messages. Sections (Step 5.6): summary; status timeline; limit exceedances with duration
(measured values against the engine-manual limits, configs/engines); alerts; hypotheses with evidence; fuel-flow and
temperature trends; prognostics (time-to-limit, mission reliability); maintenance raised; configuration provenance;
software version. Every number is computed here from the recording - nothing is typed in. Evidence class is printed
on the first line.
"""
from __future__ import annotations

import html
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.physics.engine_config import load_engine_config
from backend.recording.recorder import read_frames, read_states, read_timeline

ROOT = Path(__file__).resolve().parents[2]
SECTIONS = ("Summary", "Status timeline", "Limit exceedances", "Alerts", "Hypotheses and evidence", "Trends",
            "Prognostics", "Maintenance raised", "Configuration provenance", "Software version")
SPARK_W, SPARK_H = 360, 60
MAX_STATES = 1_000_000


def _git_version() -> str:
    try:
        return subprocess.run(["git", "describe", "--always", "--dirty"], cwd=ROOT, capture_output=True, text=True,
                              timeout=10).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError) as e:      # reported, not hidden
        return f"unavailable ({e.__class__.__name__})"


def _spark(values: List[Optional[float]]) -> str:
    v = [x for x in values if x is not None]
    if len(v) < 2:
        return "<em>no data</em>"
    lo, hi = min(v), max(v)
    span = (hi - lo) or 1.0
    step = SPARK_W / (len(values) - 1)
    pts = " ".join(f"{i * step:.1f},{SPARK_H - (x - lo) / span * SPARK_H:.1f}" for i, x in enumerate(values) if x is not None)
    return (f'<svg width="{SPARK_W}" height="{SPARK_H}" role="img"><polyline fill="none" stroke="#2563eb" '
            f'stroke-width="1.5" points="{pts}"/></svg> <small>{lo:.1f} - {hi:.1f}</small>')


def _segments(timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    segs: List[Dict[str, Any]] = []
    for e in timeline:
        if segs and segs[-1]["level"] == e["level"]:
            segs[-1]["end"] = e["t"]
            segs[-1]["reasons"].update(e["reasons"])
        else:
            segs.append({"level": e["level"], "start": e["t"], "end": e["t"], "reasons": set(e["reasons"])})
    return segs


def _exceedances(frames: List[Dict[str, Any]], limits: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for ch, lim in limits.items():
        for side, key in (("above", "warning_high"), ("below", "warning_low")):
            if lim.get(key) is None:
                continue
            names = [ch] if not lim.get("per_cylinder") else None
            series: Dict[str, List[tuple]] = {}
            for f in frames:
                vals = {ch: f.get(ch)} if names else {f"{ch}[{i + 1}]": v for i, v in enumerate(f.get(ch) or [])}
                for n, v in vals.items():
                    if v is not None:
                        series.setdefault(n, []).append((f["t"], v))
            for n, pts in series.items():
                bad = [(t, v) for t, v in pts if (v > lim[key] if side == "above" else v < lim[key])]
                if bad:
                    dt = (pts[-1][0] - pts[0][0]) / max(len(pts) - 1, 1)
                    out.append({"channel": n, "limit": lim[key], "side": side, "seconds": round(len(bad) * dt, 1),
                                "worst": round(max(v for _, v in bad) if side == "above" else min(v for _, v in bad), 2),
                                "first_t": round(bad[0][0], 1), "ref": lim.get("ref")})
    return out


def build_report(sortie_dir: Path) -> str:
    meta = json.loads((sortie_dir / "meta.json").read_text(encoding="utf-8"))
    frames = list(read_frames(sortie_dir))
    timeline = read_timeline(sortie_dir)
    states = read_states(sortie_dir, 0, MAX_STATES) if (sortie_dir / "states.jsonl.gz").exists() else []
    states = [s for s in states if isinstance(s, dict) and "status" in s]
    cfg = load_engine_config(meta["engine_id"])
    e = html.escape
    parts = [f"<!doctype html><html><head><meta charset='utf-8'><title>Sortie {e(meta['sortie_id'])}</title>"
             "<style>body{font:14px system-ui;margin:24px;max-width:960px}table{border-collapse:collapse}"
             "td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}h2{margin-top:28px}</style></head><body>",
             f"<p><strong>Evidence class: {e(meta.get('evidence_class', 'SIMULATION'))}</strong></p>"]

    levels = Counter(x["level"] for x in timeline)
    dur = (timeline[-1]["t"] - timeline[0]["t"]) if len(timeline) > 1 else 0.0
    parts.append(f"<h2>Summary</h2><table><tr><th>Sortie</th><td>{e(meta['sortie_id'])}</td></tr>"
                 f"<tr><th>Engine / tail</th><td>{e(cfg.display_name if hasattr(cfg, 'display_name') else meta['engine_id'])}"
                 f" / {e(str(meta['tail_id']))}</td></tr><tr><th>Mission</th><td>{e(str(meta.get('mission_id') or 'manual'))}</td></tr>"
                 f"<tr><th>Duration (sim)</th><td>{dur / 60:.1f} min, {len(frames)} frames</td></tr>"
                 f"<tr><th>Time by status</th><td>{e(', '.join(f'{k}: {v} ticks' for k, v in levels.most_common()))}</td></tr></table>")

    rows = "".join(f"<tr><td>{s['start']:.0f}</td><td>{s['end']:.0f}</td><td>{e(str(s['level']))}</td>"
                   f"<td>{e(', '.join(sorted(s['reasons'])) or '-')}</td></tr>" for s in _segments(timeline))
    parts.append(f"<h2>Status timeline</h2><table><tr><th>from s</th><th>to s</th><th>level</th><th>reasons</th></tr>{rows}</table>")

    ex = _exceedances(frames, cfg.limits or {})
    rows = "".join(f"<tr><td>{e(x['channel'])}</td><td>{x['side']} {x['limit']}</td><td>{x['seconds']}</td>"
                   f"<td>{x['worst']}</td><td>{x['first_t']}</td><td>{e(str(x['ref'] or ''))}</td></tr>" for x in ex)
    parts.append("<h2>Limit exceedances</h2>" + (f"<table><tr><th>channel</th><th>limit</th><th>seconds</th><th>worst</th>"
                 f"<th>first at s</th><th>limit source</th></tr>{rows}</table>" if ex else "<p>None: every measured channel stayed inside its engine-manual limits.</p>"))

    alerts: Dict[str, Dict[str, Any]] = {}
    for s in states:
        for a in s.get("alerts", []):
            alerts[a["id"]] = a
    rows = "".join(f"<tr><td>{e(str(a.get('level')))}</td><td>{e(str(a.get('text')))}</td><td>{e(str(a.get('count')))}</td>"
                   f"<td>{e(str(a.get('action') or ''))}</td></tr>" for a in alerts.values())
    parts.append("<h2>Alerts</h2>" + (f"<table><tr><th>level</th><th>alert</th><th>count</th><th>operator action</th></tr>{rows}</table>"
                 if alerts else "<p>No alerts were published (or no state messages were recorded for this sortie).</p>"))

    hyp = Counter(tuple(h[:3]) for x in timeline for h in x["hypotheses"][:1] if h[0])
    best = {}
    for x in timeline:
        for h in x["hypotheses"][:1]:
            if h[0]:
                best[tuple(h[:3])] = max(best.get(tuple(h[:3]), 0.0), h[3])
    ev = {}
    for s in states:
        for h in s.get("hypotheses", [])[:1]:
            if h.get("fault_id"):
                ev[(h["fault_id"], h.get("cylinder"), h.get("channel"))] = h.get("supporting", [])
    rows = "".join(f"<tr><td>{e(k[0])}</td><td>{e(str(k[1] or k[2] or '-'))}</td><td>{n}</td><td>{best[k]:.2f}</td>"
                   f"<td>{e(', '.join(f'{x['channel']} {x['z']:+.1f}σ' for x in ev.get(k, [])) or '-')}</td></tr>" for k, n in hyp.most_common())
    parts.append("<h2>Hypotheses and evidence</h2>" + (f"<table><tr><th>fault</th><th>where</th><th>ticks leading</th><th>max posterior</th>"
                 f"<th>supporting channels</th></tr>{rows}</table>" if hyp else "<p>No fault hypothesis led during this sortie.</p>"))

    sample = frames[:: max(1, len(frames) // 200)]
    parts.append("<h2>Trends</h2><table>"
                 f"<tr><th>fuel flow kg/h</th><td>{_spark([f.get('fuel_flow') for f in sample])}</td></tr>"
                 f"<tr><th>oil temperature C</th><td>{_spark([f.get('oil_t') for f in sample])}</td></tr>"
                 f"<tr><th>max CHT C</th><td>{_spark([max(f['cht']) if f.get('cht') and None not in f['cht'] else None for f in sample])}</td></tr>"
                 f"<tr><th>max EGT C</th><td>{_spark([max(f['egt']) if f.get('egt') and None not in f['egt'] else None for f in sample])}</td></tr></table>")

    last = states[-1] if states else {}
    ttl = (last.get("prognostics") or {}).get("time_to_limit", [])
    rel = last.get("reliability") or {}
    parts.append("<h2>Prognostics</h2>" + (
        "<ul>" + "".join(f"<li>{e(x['channel'])} reaches {x['limit']} in about {x['time_to_limit_s'] / 60:.0f} min "
                          f"({x['low_s'] / 60:.0f}-{x['high_s'] / 60:.0f})</li>" for x in ttl) + "</ul>" if ttl else "<p>No significant trend toward a limit at the end of the sortie.</p>")
        + (f"<p>Mission reliability at the end: {rel.get('mission_reliability')} [{rel.get('ci_lower')}, {rel.get('ci_upper')}] "
           f"({e(str(rel.get('method', '')))}; hazard source: {e(str(rel.get('hazard_source', '')))})</p>" if rel else ""))

    orders = {w["id"]: w for s in states for w in s.get("maintenance", [])}
    rows = "".join(f"<tr><td>{e(w['id'])}</td><td>{e(str(w.get('ata_chapter') or '-'))}</td><td>{e(w['title'])}</td>"
                   f"<td>{e(str(w.get('action') or ''))}</td><td>{e(w['status'])}</td></tr>" for w in orders.values())
    parts.append("<h2>Maintenance raised</h2>" + (f"<table><tr><th>order</th><th>ATA</th><th>title</th><th>action</th><th>status</th></tr>{rows}</table>"
                 if orders else "<p>No work order was opened during this sortie.</p>"))

    parts.append(f"<h2>Configuration provenance</h2><p>Configuration hash {e(meta['config_hash'])} (engine, fault registry, "
                 f"detection and physics configs). Engine limits from: {e('; '.join(sorted({str(v.get('ref')) for v in (cfg.limits or {}).values() if v.get('ref')})))}.</p>")
    parts.append(f"<h2>Software version</h2><p>{e(_git_version())}</p></body></html>")
    return "".join(parts)


def write_report(sortie_dir: Path) -> Path:
    out = sortie_dir / "report.html"
    out.write_text(build_report(sortie_dir), encoding="utf-8")
    return out
