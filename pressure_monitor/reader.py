"""Background acquisition thread feeding the Qt event loop."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import NamedTuple

from PySide6.QtCore import QObject, Signal

from .sources import SampleSource, SourceError

QUEUE_CAPACITY = 20_000
"""Samples buffered between the reader thread and the next UI refresh."""


class Sample(NamedTuple):
    t: float
    raw_1: float
    raw_2: float


class SampleReader(QObject):
    """Reads a :class:`SampleSource` in a thread and queues what it produces.

    Samples are collected in a deque that the UI drains on a timer rather than
    being emitted one by one, so a fast sensor cannot flood the event loop.
    """

    connected = Signal(str)
    disconnected = Signal()
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._samples: deque[Sample] = deque(maxlen=QUEUE_CAPACITY)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, source: SampleSource) -> None:
        if self.is_running:
            raise RuntimeError("A source is already being read")
        self._samples.clear()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, args=(source,), name="pressure-reader", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout)

    def drain(self) -> list[Sample]:
        """Remove and return every sample queued since the last call."""
        samples = []
        while True:
            try:
                samples.append(self._samples.popleft())
            except IndexError:
                return samples

    def _run(self, source: SampleSource) -> None:
        try:
            source.open()
        except SourceError as error:
            self.failed.emit(str(error))
            return

        self.connected.emit(source.label)
        try:
            while not self._stop.is_set():
                reading = source.read()
                if reading is None:
                    continue
                self._samples.append(Sample(time.monotonic(), *reading))
        except SourceError as error:
            if not self._stop.is_set():
                self.failed.emit(str(error))
        finally:
            source.close()
            self.disconnected.emit()
