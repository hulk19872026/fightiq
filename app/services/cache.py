import time
from typing import Any

_store: dict[str, tuple[float, Any]] = {}


def cache_get(key: str, ttl: int = 300) -> Any | None:
    entry = _store.get(key)
    if entry is None:
        return None
    ts, value = entry
    if time.time() - ts > ttl:
        _store.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any):
    _store[key] = (time.time(), value)
