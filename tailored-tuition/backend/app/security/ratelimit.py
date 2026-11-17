"""In-memory sliding-window limiter for logins and sign-ups.

Single-process only (the MVP runs one backend process). With several
processes or servers, move this to the database or Redis.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindow:
    def __init__(self, limit: int, window_s: float):
        self.limit, self.window = limit, window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def blocked(self, key: str) -> float:
        """Seconds until `key` may try again (0 = allowed)."""
        now = time.monotonic()
        with self._lock:
            q = self._prune(key, now)
            if len(q) < self.limit:
                return 0.0
            return max(0.0, self.window - (now - q[0]))

    def hit(self, key: str) -> None:
        with self._lock:
            self._prune(key, time.monotonic()).append(time.monotonic())

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


# 10 failed logins per account per 15 minutes; 30 sign-ups per hour service-wide.
login_failures = SlidingWindow(limit=10, window_s=15 * 60)
signups = SlidingWindow(limit=30, window_s=60 * 60)
