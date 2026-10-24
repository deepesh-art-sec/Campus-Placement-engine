"""
In-memory Rate Limiter for Authentication Endpoints.
Prevents brute-force credential stuffing and password guessing on college LAN.
"""

from __future__ import annotations

import collections
import datetime
import threading


class LoginRateLimiter:
    """Sliding-window rate limiter per identifier (IP or username)."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 60) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, collections.deque[datetime.datetime]] = collections.defaultdict(collections.deque)
        self._lock = threading.Lock()

    def is_rate_limited(self, key: str) -> bool:
        """Returns True if the identifier has exceeded the maximum attempts in the window."""
        with self._lock:
            now = datetime.datetime.utcnow()
            cutoff = now - datetime.timedelta(seconds=self.window_seconds)
            history = self._attempts[key]

            # Prune expired timestamps
            while history and history[0] < cutoff:
                history.popleft()

            return len(history) >= self.max_attempts

    def record_attempt(self, key: str) -> None:
        """Records a failed authentication attempt."""
        with self._lock:
            now = datetime.datetime.utcnow()
            cutoff = now - datetime.timedelta(seconds=self.window_seconds)
            history = self._attempts[key]

            while history and history[0] < cutoff:
                history.popleft()

            history.append(now)

    def reset(self, key: str) -> None:
        """Resets rate limiting history on successful authentication."""
        with self._lock:
            if key in self._attempts:
                self._attempts[key].clear()


# Global login rate limiter instance
login_rate_limiter = LoginRateLimiter(max_attempts=5, window_seconds=60)
