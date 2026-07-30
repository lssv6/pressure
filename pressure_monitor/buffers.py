"""Time-bounded storage for the samples shown on the plot."""

from __future__ import annotations

from collections import deque

import numpy as np

RATE_ESTIMATION_WINDOW_S = 2.0


class RollingBuffer:
    """Keeps the most recent ``retention_s`` seconds of a two channel signal.

    Values are held in kilopascals; timestamps are seconds from an arbitrary
    monotonic origin.
    """

    def __init__(self, retention_s: float) -> None:
        self.retention_s = retention_s
        self._t: deque[float] = deque()
        self._channels: tuple[deque[float], deque[float]] = (deque(), deque())

    def __len__(self) -> int:
        return len(self._t)

    def append(self, t: float, value_1: float, value_2: float) -> None:
        self._t.append(t)
        self._channels[0].append(value_1)
        self._channels[1].append(value_2)
        self._discard_older_than(t - self.retention_s)

    def clear(self) -> None:
        self._t.clear()
        for channel in self._channels:
            channel.clear()

    def set_retention(self, retention_s: float) -> None:
        self.retention_s = retention_s
        if self._t:
            self._discard_older_than(self._t[-1] - retention_s)

    def _discard_older_than(self, cutoff: float) -> None:
        while self._t and self._t[0] < cutoff:
            self._t.popleft()
            for channel in self._channels:
                channel.popleft()

    def arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        count = len(self._t)
        t = np.fromiter(self._t, dtype=float, count=count)
        channel_1 = np.fromiter(self._channels[0], dtype=float, count=count)
        channel_2 = np.fromiter(self._channels[1], dtype=float, count=count)
        return t, channel_1, channel_2

    def latest(self) -> tuple[float, float] | None:
        """The newest sample of each channel, or ``None`` while empty."""
        if not self._t:
            return None
        return self._channels[0][-1], self._channels[1][-1]

    def sample_rate(self) -> float:
        """Samples per second, measured over the last couple of seconds."""
        if len(self._t) < 2:
            return 0.0
        newest = self._t[-1]
        counted = 0
        for t in reversed(self._t):
            if newest - t > RATE_ESTIMATION_WINDOW_S:
                break
            counted += 1
        span = newest - self._t[-counted]
        if span <= 0:
            return 0.0
        return (counted - 1) / span
