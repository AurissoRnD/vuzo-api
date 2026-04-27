"""
In-memory store mapping CardTransaction request_code -> user details.
Fallback for the callback handler if meta_data doesn't come back from get-request-code.
Entries auto-expire after 24 hours.
"""

import time
import threading
from typing import Optional

_TTL_SECONDS = 24 * 60 * 60
_store: dict[str, dict] = {}
_lock = threading.Lock()


def save_pending(request_code: str, details: dict) -> None:
    with _lock:
        _store[request_code] = {**details, "_created_at": time.time()}
        _cleanup_expired_locked()


def get_pending(request_code: str) -> Optional[dict]:
    with _lock:
        entry = _store.get(request_code)
        if entry is None:
            return None
        if time.time() - entry["_created_at"] > _TTL_SECONDS:
            _store.pop(request_code, None)
            return None
        return {k: v for k, v in entry.items() if k != "_created_at"}


def remove_pending(request_code: str) -> None:
    with _lock:
        _store.pop(request_code, None)


def _cleanup_expired_locked() -> None:
    now = time.time()
    expired = [k for k, v in _store.items() if now - v["_created_at"] > _TTL_SECONDS]
    for k in expired:
        _store.pop(k, None)
