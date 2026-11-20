"""RuntimeHub -- every engine profile runs concurrently; the dropdown selects which one gets the heavy tier
and the primary stream (R1, D29).  Deterministic: same seeds + same tick count => identical streams."""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from backend.physics.engine_config import available_engines
from backend.runtime.engine_runtime import EngineRuntime, Tick

RUNTIME_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "runtime.json"


def load_runtime_settings(path: Path = RUNTIME_CONFIG) -> Dict[str, Any]:
    """Runtime settings from configs/runtime.json (card M0-07). A missing or invalid file is an error, not a default."""
    data = json.loads(path.read_text(encoding="utf-8"))
    divisor = data.get("idle_tick_divisor")
    if not isinstance(divisor, int) or divisor < 1:
        raise ValueError(f"{path}: idle_tick_divisor must be an integer >= 1, got {divisor!r}")
    rate = data.get("tick_rate_hz")
    if not isinstance(rate, (int, float)) or rate <= 0:
        raise ValueError(f"{path}: tick_rate_hz must be a number > 0, got {rate!r}")
    return data


class RuntimeHub:
    def __init__(self, engines: Optional[List[str]] = None, seed: int = 0, warmup_ticks: int = 900) -> None:
        self.engines = engines or available_engines()
        self.runtimes: Dict[str, EngineRuntime] = {
            e: EngineRuntime(e, seed=seed + i, warmup_ticks=warmup_ticks) for i, e in enumerate(self.engines)}
        self.selected: str = self.engines[0]
        # engines some client is subscribed to (set by the /ws/v1 broadcaster); they tick at full rate
        self.active: Set[str] = set()
        settings = load_runtime_settings()
        self.idle_tick_divisor: int = settings["idle_tick_divisor"]
        self.tick_rate_hz: float = float(settings["tick_rate_hz"])
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

    def set_active(self, engines: Iterable[str]) -> None:
        """Engines with at least one subscriber. Unknown ids are ignored (the API validates them)."""
        self.active = {e for e in engines if e in self.runtimes}

    def tick_all(self, force_all: bool = True) -> Dict[str, Tick]:
        """Tick every ready engine. When force_all is False (the steady-state background loop), the selected
        engine and every engine with a subscriber tick every call; engines nobody watches tick every
        idle_tick_divisor-th call (configs/runtime.json) to save CPU/memory on small hosts.
        This hub is the only simulator: nothing here writes into the legacy EngineStateService (M0-07, T-M0-5)."""
        out = {}
        idle_turn = self.tick_count % self.idle_tick_divisor == 0
        for e, r in self.runtimes.items():
            if not r.ready:
                continue
            is_selected = e == self.selected
            if force_all or is_selected or e in self.active or idle_turn:
                out[e] = r.tick(heavy=is_selected)
            elif e in self.latest:
                out[e] = self.latest[e]
        self.latest = out
        self.tick_count += 1
        return out

    def start(self, rate_hz: Optional[float] = None) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        rate = rate_hz if rate_hz is not None else self.tick_rate_hz

        def loop():
            period = 1.0 / rate
            while not self._stop.is_set():
                t0 = time.perf_counter()
                self.tick_all(force_all=False)
                time.sleep(max(0.0, period - (time.perf_counter() - t0)))

        self._thread = threading.Thread(target=loop, daemon=True, name="runtime-hub")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def state(self) -> Dict[str, Any]:
        return {"selected": self.selected, "tick": self.tick_count,
                "engines": [r.profile() for r in self.runtimes.values()]}
