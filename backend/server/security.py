"""Command security for every command endpoint (card M0-08, DECISIONS D52).

- Token: when the env var named in configs/runtime.json security.token_env is set, every command must carry it in the
  security.token_header header (constant-time compare). Read-only endpoints stay open.
- Rate limit: per client (token or remote address), max_commands per window_s, sliding window -> 429.
- Command log: every command attempt (accepted, rejected, failed) is logged with source, request_id and result, and
  kept in a bounded in-memory ring for /api/v1/commands.
- CORS origins: from the env var named in security.cors_origins_env, else the local dev origins. Never "*".
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, Iterator, List, Optional

from fastapi import HTTPException, Request

from backend.runtime.hub import load_runtime_settings

logger = logging.getLogger("anumaan.commands")

_SETTINGS = load_runtime_settings()["security"]


def cors_origins() -> List[str]:
    raw = os.environ.get(_SETTINGS["cors_origins_env"], "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if "*" in origins:
        raise ValueError(f"{_SETTINGS['cors_origins_env']} must list explicit origins, not '*' (D52)")
    return origins or list(_SETTINGS["cors_dev_origins"])


class RateLimiter:
    def __init__(self, max_commands: int, window_s: float) -> None:
        self.max_commands, self.window_s = max_commands, window_s
        self._hits: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window_s:
                hits.popleft()
            if len(hits) >= self.max_commands:
                return False
            hits.append(now)
            return True


RATE_LIMITER = RateLimiter(**_SETTINGS["command_rate_limit"])
COMMAND_LOG: Deque[Dict[str, Any]] = deque(maxlen=_SETTINGS["command_log_size"])


def _record(entry: Dict[str, Any]) -> None:
    COMMAND_LOG.append(entry)
    logger.info("command %s %s request_id=%s source=%s result=%s",
                entry["method"], entry["path"], entry.get("request_id"), entry.get("source"), entry["result"])


def check_command(method: str, path: str, client: str, given_token: Optional[str]) -> Dict[str, Any]:
    """Token + rate-limit check shared by REST and WebSocket commands. Logs and raises HTTPException on rejection."""
    expected = os.environ.get(_SETTINGS["token_env"])
    entry: Dict[str, Any] = {"t_wall": time.time(), "method": method, "path": path, "client": client,
                             "request_id": None, "source": None, "result": "PENDING"}
    if expected and not (given_token and hmac.compare_digest(given_token.encode(), expected.encode())):
        entry["result"] = "401 token missing or wrong"
        _record(entry)
        raise HTTPException(401, {"code": "UNAUTHORIZED",
                                  "message": f"command needs the {_SETTINGS['token_header']} header"})
    if not RATE_LIMITER.allow(client):
        entry["result"] = "429 rate limit"
        _record(entry)
        raise HTTPException(429, {"code": "RATE_LIMITED",
                                  "message": "too many commands; max {max_commands} per {window_s} s".format(
                                      **_SETTINGS["command_rate_limit"])})
    return entry


def finish_command(entry: Dict[str, Any], result: str) -> None:
    entry["result"] = result
    _record(entry)


def token_from(headers: Any, query: Any) -> Optional[str]:
    """Token from the header, or (WebSocket clients that cannot set headers) the 'token' query parameter."""
    return headers.get(_SETTINGS["token_header"]) or query.get("token")


def client_key(host: Optional[str], token: Optional[str]) -> str:
    if token:
        return "token:" + hashlib.sha256(token.encode()).hexdigest()[:8]   # never log the token itself
    return "addr:" + (host or "unknown")


def command_guard(request: Request) -> Iterator[Dict[str, Any]]:
    """FastAPI dependency for command endpoints. Yields the log entry; the endpoint may set request_id/source."""
    given = token_from(request.headers, request.query_params)
    entry = check_command(request.method, request.url.path,
                          client_key(request.client.host if request.client else None, given), given)
    try:
        yield entry
        entry["result"] = "OK"
    except HTTPException as exc:
        entry["result"] = f"{exc.status_code} {exc.detail}"
        raise
    except Exception as exc:  # logged, then re-raised: never swallowed
        entry["result"] = f"500 {type(exc).__name__}"
        raise
    finally:
        _record(entry)
