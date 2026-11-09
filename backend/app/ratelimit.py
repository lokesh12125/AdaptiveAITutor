"""Small in-process sliding-window limiter. Suitable for the single API process this project runs."""
import threading
import time
from collections import defaultdict, deque

from .errors import ApiError

_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def check(key: str, limit_per_minute: int) -> None:
    now = time.monotonic()
    with _lock:
        window = _hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= limit_per_minute:
            retry_after = max(1, int(60 - (now - window[0])))
            raise ApiError(
                429, "rate_limited", f"That was a lot of requests. Please wait {retry_after} seconds and try again.",
                details={"retry_after": retry_after}, headers={"Retry-After": str(retry_after)},
            )
        window.append(now)


def reset() -> None:
    with _lock:
        _hits.clear()
