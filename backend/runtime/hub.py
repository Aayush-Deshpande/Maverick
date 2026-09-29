"""RuntimeHub -- every engine profile runs concurrently; the dropdown selects which one gets the heavy tier
and the primary stream (R1, D29).  Deterministic: same seeds + same tick count => identical streams."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from backend.physics.engine_config import available_engines
from backend.runtime.engine_runtime import EngineRuntime, Tick


class RuntimeHub:
    def __init__(self, engines: Optional[List[str]] = None, seed: int = 0, warmup_ticks: int = 900) -> None:
        self.engines = engines or available_engines()
        self.runtimes: Dict[str, EngineRuntime] = {
            e: EngineRuntime(e, seed=seed + i, warmup_ticks=warmup_ticks) for i, e in enumerate(self.engines)}
        self.selected: str = self.engines[0]
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.latest: Dict[str, Tick] = {}
        self.tick_count = 0

    def calibrate_all(self, parallel: bool = True) -> None:
        if parallel:
            with ThreadPoolExecutor(max_workers=min(4, len(self.runtimes))) as ex:
                list(ex.map(lambda r: r.calibrate(), self.runtimes.values()))
        else:
            for r in self.runtimes.values():
                r.calibrate()

    def select(self, engine_id: str, warm_heavy: bool = True) -> None:
        if engine_id not in self.runtimes:
            raise KeyError(engine_id)
        self.selected = engine_id
        if warm_heavy:
            threading.Thread(target=self.runtimes[engine_id].ensure_heavy, daemon=True).start()

    def tick_all(self) -> Dict[str, Tick]:
        out = {}
        for e, r in self.runtimes.items():
            if r.ready:
                t = r.tick(heavy=(e == self.selected))
                out[e] = t
                if e == "rotax_912is":
                    try:
                        from backend.server.engine_service import EngineStateService
                        if EngineStateService._instance is not None:
                            EngineStateService._instance.sync_from_tick(t)
                    except Exception:
                        pass
        self.latest = out
        self.tick_count += 1
        return out

    def start(self, rate_hz: float = 20.0) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        def loop():
            period = 1.0 / rate_hz
            while not self._stop.is_set():
                t0 = time.perf_counter()
                self.tick_all()
                time.sleep(max(0.0, period - (time.perf_counter() - t0)))

        self._thread = threading.Thread(target=loop, daemon=True, name="runtime-hub")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def state(self) -> Dict[str, Any]:
        return {"selected": self.selected, "tick": self.tick_count,
                "engines": [r.profile() for r in self.runtimes.values()]}
