"""Sample sources: a real serial port, plus a simulator for hardware-free use."""

from __future__ import annotations

import math
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

import serial
from serial.tools import list_ports

from .calibration import DEFAULT_COUNTS_PER_KPA
from .protocol import parse_sample_line

READ_TIMEOUT_S = 0.5
ARDUINO_RESET_DELAY_S = 1.5
"""Boards that reset when the port is opened need a moment before they talk."""

SIMULATED_PORT = "__simulator__"
SIMULATED_LABEL = "Simulator (no hardware)"


class SourceError(RuntimeError):
    """Raised when a source cannot be opened or dies while streaming."""


class SampleSource(ABC):
    """A stream of raw sensor pairs, read from a background thread."""

    label: str = ""

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def read(self) -> tuple[float, float] | None:
        """Return the next raw pair, or ``None`` if none arrived in time."""

    @abstractmethod
    def close(self) -> None: ...


class SerialSampleSource(SampleSource):
    def __init__(self, port: str, baudrate: int) -> None:
        self.port = port
        self.baudrate = baudrate
        self.label = f"{port} @ {baudrate} baud"
        self._serial: serial.Serial | None = None

    def open(self) -> None:
        try:
            self._serial = serial.Serial(
                self.port, self.baudrate, timeout=READ_TIMEOUT_S
            )
        except (serial.SerialException, OSError, ValueError) as error:
            raise SourceError(f"Could not open {self.port}: {error}") from error
        time.sleep(ARDUINO_RESET_DELAY_S)
        self._serial.reset_input_buffer()

    def read(self) -> tuple[float, float] | None:
        if self._serial is None:
            raise SourceError("Serial port is not open")
        try:
            raw_line = self._serial.readline()
        except (serial.SerialException, OSError) as error:
            raise SourceError(f"Lost connection to {self.port}: {error}") from error
        if not raw_line:
            return None
        return parse_sample_line(raw_line.decode("ascii", errors="ignore"))

    def close(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None


@dataclass(frozen=True)
class _SimulatedChannel:
    """A synthetic pressure signal, in kPa, built from two sine components."""

    baseline: float
    amplitude: float
    frequency: float
    ripple: float
    ripple_frequency: float
    noise: float

    def kpa_at(self, t: float) -> float:
        return (
            self.baseline
            + self.amplitude * math.sin(2 * math.pi * self.frequency * t)
            + self.ripple * math.sin(2 * math.pi * self.ripple_frequency * t)
            + random.gauss(0.0, self.noise)
        )


class SimulatedSampleSource(SampleSource):
    """Generates plausible HX710B counts so the UI can run without a board.

    The counts are produced with the default span and no raw offset, i.e. as if
    the sensors had already been tared, so the app shows sensible pressures out
    of the box.
    """

    label = SIMULATED_LABEL

    CHANNELS = (
        _SimulatedChannel(5.0, 2.0, 0.25, 0.3, 1.0, 0.02),
        _SimulatedChannel(12.0, 1.2, 0.18, 0.8, 1.4, 0.03),
    )

    def __init__(self, rate_hz: float = 20.0, zero_counts: float = 0.0) -> None:
        self.rate_hz = rate_hz
        self.zero_counts = zero_counts
        self._start = 0.0
        self._next_sample = 0.0

    def open(self) -> None:
        self._start = time.monotonic()
        self._next_sample = self._start

    def read(self) -> tuple[float, float] | None:
        self._next_sample += 1.0 / self.rate_hz
        delay = self._next_sample - time.monotonic()
        if delay > 0:
            time.sleep(min(delay, READ_TIMEOUT_S))
        t = time.monotonic() - self._start
        return tuple(  # type: ignore[return-value]
            self.zero_counts + channel.kpa_at(t) * DEFAULT_COUNTS_PER_KPA
            for channel in self.CHANNELS
        )

    def close(self) -> None:
        pass


@dataclass(frozen=True)
class PortInfo:
    device: str
    description: str

    @property
    def label(self) -> str:
        if self.description and self.description != "n/a":
            return f"{self.device} — {self.description}"
        return self.device


_LIKELY_BOARD_HINTS = ("arduino", "ch340", "ch910", "cp210", "ft232", "usb serial", "wch")


def _looks_like_a_board(port: PortInfo) -> bool:
    haystack = f"{port.device} {port.description}".lower()
    if any(hint in haystack for hint in _LIKELY_BOARD_HINTS):
        return True
    return "ttyacm" in haystack or "ttyusb" in haystack or "usbmodem" in haystack


def available_ports() -> list[PortInfo]:
    """Serial ports on this machine, with likely Arduino boards listed first."""
    ports = [
        PortInfo(port.device, (port.description or "").strip())
        for port in list_ports.comports()
    ]
    ports.sort(key=lambda port: (not _looks_like_a_board(port), port.device))
    return ports


def create_source(port: str, baudrate: int) -> SampleSource:
    if port == SIMULATED_PORT:
        return SimulatedSampleSource()
    return SerialSampleSource(port, baudrate)
