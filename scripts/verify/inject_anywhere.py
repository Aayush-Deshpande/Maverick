"""Inject-anywhere acceptance check (P Part 7 T-M0-2, T-STS-1, T-DET-1/2, T-3D-1/2 in one chain; Prasad 20 Nov:
"inject from anywhere -> live telemetry -> detected -> the correct part highlighted").

For every engine and every applicable PHYSICAL fault, inject through one of the real entry points, rotating:
  console  POST /api/v1/engines/{id}/faults              (React console, copilot-free path)
  twin     POST /api/engines/{id}/faults {mode}           (3D twin page, legacy mode names)
  gcs      POST /api/control SET_FAULT {legacy id}        (Tactical GCS, Rotax 912 legacy ids)
then advance the simulation (1 s per tick) through ramp + detection window, building the SAME state message every
client receives, and record: shown in active_faults, status left GO, fault in the top-3 hypotheses, and whether the
3D highlight equals the registry components for that engine when it is the top hypothesis. Between faults: clear,
acknowledge, cool down. Evidence class SIMULATION. Output: docs/verification/inject_anywhere_<date>.csv + summary.

Run: python scripts/verify/inject_anywhere.py [engine_id ...]   (about 20-40 min for all five engines)
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI                                     # noqa: E402
from fastapi.testclient import TestClient                       # noqa: E402

import backend.server.api_v1 as api_v1                          # noqa: E402
import backend.server.engine_api as legacy_api                  # noqa: E402
from backend.runtime.hub import RuntimeHub                      # noqa: E402

RAMP_S = 30                     # short ramp so the check exercises detection, not patience
COOL_S = 300                    # simulated cool-down between faults
TOP_K = 3


def main(engines: list[str]) -> int:
    hub = RuntimeHub(engines or None, seed=0, warmup_ticks=600)
    hub.calibrate_all()
    legacy_api._hub = hub
    api_v1._services = api_v1.Services(hub)
    app = FastAPI()
    app.include_router(legacy_api.router)
    app.include_router(api_v1.router)
    from backend.server.legacy_adapter import legacy_command
    from backend.server.schemas import ControlCommand

    @app.post("/api/control")                                   # the Tactical GCS route, as backend/server/main.py
    def control(cmd: ControlCommand):
        return legacy_command(cmd)
    client = TestClient(app)
    reg = {f["id"]: f for f in json.loads((ROOT / "configs" / "faults.json").read_text(encoding="utf-8"))["faults"]}
    svc = api_v1.services()
    queue = {e: [f["id"] for f in client.get("/api/v1/faults", params={"engine": e}).json()["faults"]
                 if f.get("kind") == "PHYSICAL"] for e in hub.engines}
    twin_modes = {p["engine_id"]: {f["mode"] for f in p["faults"]} for p in client.get("/api/engines").json()["engines"]}
    gcs_engine = "rotax_912is"                                   # /api/control drives the legacy 912 only
    rows, surface_turn = [], 0
    for _ in range(max(len(q) for q in queue.values())):
        live = {}
        for e in hub.engines:
            if not queue[e]:
                continue
            fid = queue[e].pop(0)
            f = reg[fid]
            cyl = 2 if f["scope"] == "CYLINDER" else None
            options = ["console"]
            if f.get("plant_mode_legacy") in twin_modes.get(e, set()):
                options.append("twin")
            if e == gcs_engine and f.get("legacy_ids"):
                options.append("gcs")
            surface = options[surface_turn % len(options)]
            surface_turn += 1
            if surface == "console":
                r = client.post(f"/api/v1/engines/{e}/faults", json={"fault_id": fid, "cylinder": cyl, "severity": 1.0,
                                "ramp_s": RAMP_S, "source": "console", "request_id": f"acc-{e}-{fid}"})
            elif surface == "twin":
                body = {"mode": f["plant_mode_legacy"], "severity": 1.0, "ramp_sec": RAMP_S}
                if cyl:
                    body["cylinder"] = cyl
                r = client.post(f"/api/engines/{e}/faults", json=body)
            else:
                r = client.post("/api/control", json={"action": "SET_FAULT", "fault_id": f["legacy_ids"][0],
                                                      "severity": 1.0, "ramp_duration_sec": RAMP_S})
            comps = (f.get("components") or {}).get(e, {}).get("now") or []
            want = {c.replace("{cyl}", str(cyl or "")) for c in comps}
            live[e] = {"engine": e, "fault": fid, "surface": surface, "accepted": r.status_code == 200,
                       "reject": "" if r.status_code == 200 else r.text[:120], "shown_active": False,
                       "status_left_go": False, "detected_top3": False, "detect_s": None, "top1": "",
                       "expected_parts": " ".join(sorted(want)), "lit_parts": "", "highlight_ok": False,
                       "window_s": RAMP_S + float(f["detect_window_s"])}
        horizon = int(max((v["window_s"] for v in live.values()), default=0)) + 1
        for t in range(horizon):
            hub.tick_all()
            for e, row in live.items():
                msg = svc.build_message(e)
                if not msg or t > row["window_s"]:
                    continue
                st = json.loads(msg)
                row["shown_active"] |= any(a.get("fault_id") == row["fault"] for a in st.get("active_faults") or [])
                row["status_left_go"] |= (st.get("status") or {}).get("level") not in (None, "GO")
                hyps = [h.get("fault_id") for h in st.get("hypotheses") or [] if h.get("fault_id")]
                if row["fault"] in hyps[:TOP_K] and not row["detected_top3"]:
                    row["detected_top3"], row["detect_s"] = True, t
                if hyps:
                    row["top1"] = hyps[0]
                if hyps and hyps[0] == row["fault"]:
                    lit = {h["component_id"] for h in st.get("highlights") or [] if h.get("level") != "INJECTED"}
                    if lit:
                        row["lit_parts"] = " ".join(sorted(lit))
                        row["highlight_ok"] |= bool(row["expected_parts"]) and lit == set(row["expected_parts"].split())
        for e, row in live.items():
            client.delete(f"/api/v1/engines/{e}/faults")
            client.post(f"/api/v1/engines/{e}/status/acknowledge", json={})
            rows.append(row)
            print(f"{e:16s} {row['fault']} via {row['surface']:7s} accepted={row['accepted']} active={row['shown_active']} "
                  f"not-GO={row['status_left_go']} top3={row['detected_top3']} ({row['detect_s']}s) top1={row['top1']} "
                  f"highlight={'OK' if row['highlight_ok'] else row['lit_parts'] or '-'}", flush=True)
        for _ in range(COOL_S):
            hub.tick_all()
        for e in live:
            client.post(f"/api/v1/engines/{e}/status/acknowledge", json={})
            svc.build_message(e)
    out = ROOT / "docs" / "verification" / f"inject_anywhere_{dt.date.today():%Y-%m-%d}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    n = len(rows)
    count = lambda k: sum(1 for r in rows if r[k])                    # noqa: E731
    with_parts = [r for r in rows if r["expected_parts"]]
    print(f"\n{n} engine-fault checks (SIMULATION): accepted {count('accepted')}, shown live {count('shown_active')}, "
          f"left GO {count('status_left_go')}, top-3 {count('detected_top3')}, "
          f"highlight exact {sum(1 for r in with_parts if r['highlight_ok'])}/{len(with_parts)} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
