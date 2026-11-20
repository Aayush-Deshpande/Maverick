"""Maintenance work orders (card M4-05, P Part 4 Step 4.5, T-PRG-4).

A work order is opened from evidence only:
  - an isolation hypothesis with posterior >= open_posterior (backend/diagnose/isolator.py), or
  - a significant time-to-limit trend inside the warning horizon (backend/prognose/trends.py).
Its content comes from the fault registry (configs/faults.json): ATA chapter, maintenance action with its source,
in-flight mitigation. No part numbers, costs or labour hours are invented: the registry does not hold them.
Life cycle OPEN -> IN_WORK -> SIGNED_OFF (sign-off needs a name), every transition recorded with wall time.
Storage: SQLite under var/maintenance/ (D6), so orders and sign-offs survive a restart.
"""
from __future__ import annotations

import datetime as _dt
import json
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.runtime.paths import var_path
from backend.sim.source import registry          # cached registry

ROOT = Path(__file__).resolve().parents[2]
TRANSITIONS = {"OPEN": ("IN_WORK", "SIGNED_OFF"), "IN_WORK": ("SIGNED_OFF",), "SIGNED_OFF": ()}
SCHEMA = """
CREATE TABLE IF NOT EXISTS work_orders (
  id TEXT PRIMARY KEY, engine_id TEXT NOT NULL, tail_id TEXT, trigger TEXT NOT NULL, fault_id TEXT,
  cylinder INTEGER, channel TEXT, title TEXT NOT NULL, ata_chapter TEXT, action TEXT, action_source TEXT,
  mitigation TEXT, evidence TEXT, status TEXT NOT NULL, opened_sim_t REAL, opened_wall TEXT NOT NULL,
  signed_by TEXT, signed_wall TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS work_order_events (
  wo_id TEXT NOT NULL, wall TEXT NOT NULL, from_status TEXT, to_status TEXT NOT NULL, by_whom TEXT, note TEXT);
"""


def load_maintenance_config() -> Dict[str, Any]:
    return json.loads((ROOT / "configs" / "maintenance.json").read_text(encoding="utf-8"))


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _fill(text: Optional[str], cylinder: Optional[int], channel: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return text.replace("{cyl}", str(cylinder) if cylinder else "(all)").replace("{channel}", channel or "(channel)")


class WorkOrderStore:
    def __init__(self, path: Optional[Path] = None, cfg: Optional[Dict[str, Any]] = None) -> None:
        c = cfg or load_maintenance_config()
        self.open_posterior = float(c["open_posterior"]["value"])
        self.ttl_horizon_s = float(c["time_to_limit_open_s"]["value"])
        self.stable_n = int(c["stable_evaluations"]["value"])
        self._streak: Dict[str, tuple] = {}                 # engine -> (leading hypothesis key, consecutive count)
        self.path = path or var_path("maintenance") / "maintenance.sqlite"
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)
        self._open_cache: Dict[str, List[Dict[str, Any]]] = {}     # engine -> open orders (state message, 20 Hz)

    # -- opening from evidence -----------------------------------------------------------------------------------
    def _open_exists(self, engine_id: str, fault_id: Optional[str], cylinder: Optional[int], channel: Optional[str]) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM work_orders WHERE engine_id=? AND status!='SIGNED_OFF' AND IFNULL(fault_id,'')=IFNULL(?,'') "
            "AND IFNULL(cylinder,-1)=IFNULL(?,-1) AND IFNULL(channel,'')=IFNULL(?,'')",
            (engine_id, fault_id, cylinder, channel)).fetchone()
        return row is not None

    def _insert(self, **kw: Any) -> Dict[str, Any]:
        wo = {"id": f"WO-{uuid.uuid4().hex[:10].upper()}", "status": "OPEN", "opened_wall": _now(), **kw}
        cols = ",".join(wo)
        self._db.execute(f"INSERT INTO work_orders ({cols}) VALUES ({','.join('?' * len(wo))})", tuple(wo.values()))
        self._db.execute("INSERT INTO work_order_events VALUES (?,?,?,?,?,?)",
                         (wo["id"], wo["opened_wall"], None, "OPEN", "system", kw.get("trigger")))
        self._db.commit()
        self._open_cache.pop(kw["engine_id"], None)
        return self.get(wo["id"])

    def open_from_hypotheses(self, engine_id: str, tail_id: str, hypotheses: List[Dict[str, Any]],
                             sim_t: float) -> List[Dict[str, Any]]:
        out = []
        with self._lock:
            lead = hypotheses[0] if hypotheses else None
            ok = lead is not None and lead["kind"] != "NOMINAL" and lead["posterior"] >= self.open_posterior
            key = (lead["fault_id"], lead.get("cylinder"), lead.get("channel")) if ok else None
            prev_key, n = self._streak.get(engine_id, (None, 0))
            n = n + 1 if key is not None and key == prev_key else (1 if key is not None else 0)
            self._streak[engine_id] = (key, n)
            if n < self.stable_n:
                return out
            for h in hypotheses[:1]:
                if self._open_exists(engine_id, h["fault_id"], h.get("cylinder"), h.get("channel")):
                    continue
                raw = registry().get(h["fault_id"]).raw
                cyl, ch = h.get("cylinder"), h.get("channel")
                act = raw.get("maintenance_action") or {}
                where = f" cylinder {cyl}" if cyl else (f" {ch}" if ch else "")
                out.append(self._insert(
                    engine_id=engine_id, tail_id=tail_id, trigger="HYPOTHESIS", fault_id=h["fault_id"], cylinder=cyl,
                    channel=ch, title=f"{h['fault_id']} {raw.get('description') or raw.get('name')}{where}",
                    ata_chapter=raw.get("ata_chapter"), action=_fill(act.get("text"), cyl, ch),
                    action_source=act.get("source"),
                    mitigation=_fill((raw.get("mitigation_inflight") or {}).get("text"), cyl, ch),
                    evidence=json.dumps({"posterior": h["posterior"], "severity": h.get("severity"),
                                         "supporting": h.get("supporting", [])}),
                    opened_sim_t=sim_t))
        return out

    def open_from_time_to_limit(self, engine_id: str, tail_id: str, items: List[Dict[str, Any]],
                                sim_t: float) -> List[Dict[str, Any]]:
        out = []
        with self._lock:
            for p in items:
                if p["time_to_limit_s"] > self.ttl_horizon_s or self._open_exists(engine_id, None, None, p["channel"]):
                    continue
                out.append(self._insert(
                    engine_id=engine_id, tail_id=tail_id, trigger="TIME_TO_LIMIT", fault_id=None, cylinder=None,
                    channel=p["channel"],
                    title=f"{p['channel']} trending to its limit {p['limit']} in about {p['time_to_limit_s'] / 60:.0f} min",
                    ata_chapter=None, action="Inspect the system behind this reading before the predicted crossing; "
                                             "see the isolation hypotheses for the likely cause.",
                    action_source="ANUMAAN rule (time-to-limit, backend/prognose/trends.py)", mitigation=None,
                    evidence=json.dumps(p), opened_sim_t=sim_t))
        return out

    # -- life cycle ----------------------------------------------------------------------------------------------
    def transition(self, wo_id: str, to: str, by: Optional[str], note: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            wo = self.get(wo_id)
            if wo is None:
                raise KeyError(wo_id)
            if to not in TRANSITIONS[wo["status"]]:
                raise ValueError(f"{wo['status']} -> {to} is not allowed")
            if to == "SIGNED_OFF" and not by:
                raise ValueError("sign-off needs the name of the person signing")
            wall = _now()
            if to == "SIGNED_OFF":
                self._db.execute("UPDATE work_orders SET status=?, signed_by=?, signed_wall=?, note=? WHERE id=?",
                                 (to, by, wall, note, wo_id))
            else:
                self._db.execute("UPDATE work_orders SET status=? WHERE id=?", (to, wo_id))
            self._db.execute("INSERT INTO work_order_events VALUES (?,?,?,?,?,?)", (wo_id, wall, wo["status"], to, by, note))
            self._db.commit()
            self._open_cache.pop(wo["engine_id"], None)
            return self.get(wo_id)

    # -- queries -------------------------------------------------------------------------------------------------
    def get(self, wo_id: str) -> Optional[Dict[str, Any]]:
        row = self._db.execute("SELECT * FROM work_orders WHERE id=?", (wo_id,)).fetchone()
        return None if row is None else {**dict(row), "evidence": json.loads(row["evidence"] or "null")}

    def list(self, engine_id: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        q, args = "SELECT id FROM work_orders WHERE 1=1", []
        if engine_id:
            q, args = q + " AND engine_id=?", args + [engine_id]
        if status:
            q, args = q + " AND status=?", args + [status]
        return [self.get(r["id"]) for r in self._db.execute(q + " ORDER BY opened_wall", args).fetchall()]

    def open_orders(self, engine_id: str) -> List[Dict[str, Any]]:
        """Orders not yet signed off for one engine (cached; rebuilt after any write)."""
        with self._lock:
            if engine_id not in self._open_cache:
                self._open_cache[engine_id] = [w for w in self.list(engine_id) if w["status"] != "SIGNED_OFF"]
            return list(self._open_cache[engine_id])

    def events(self, wo_id: str) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._db.execute("SELECT * FROM work_order_events WHERE wo_id=? ORDER BY wall",
                                                  (wo_id,)).fetchall()]

    def close(self) -> None:
        self._db.close()
