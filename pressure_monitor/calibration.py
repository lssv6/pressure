"""Conversion of raw HX710B counts into kilopascals.

The HX710B is a 24-bit bridge ADC, so a sensor reading only becomes a pressure
once a zero point and a span are known:

    kPa = (raw - offset) / counts_per_kpa

Each channel keeps its own offset (the two modules never sit at exactly the
same zero) while the span is shared, since both channels use the same sensor
model. Firmware that already converts to kilopascals can be used by leaving the
span at 1 count per kPa.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_COUNTS_PER_KPA = 1000.0
"""Span used by the built-in simulator and as the starting point for the UI."""


@dataclass
class Calibration:
    counts_per_kpa: float = DEFAULT_COUNTS_PER_KPA
    offsets: list[float] = field(default_factory=lambda: [0.0, 0.0])

    @property
    def span(self) -> float:
        """The span, guarded so a stray zero cannot produce infinite pressures."""
        if not self.counts_per_kpa:
            return 1.0
        return self.counts_per_kpa

    def to_kpa(self, raw: float, channel: int) -> float:
        """Convert one count, or a whole array of them, to kilopascals."""
        return (raw - self.offsets[channel]) / self.span

    def tare(self, raw_values: tuple[float, float]) -> None:
        """Make the supplied raw readings the new zero pressure point."""
        self.offsets = [float(raw_values[0]), float(raw_values[1])]

    def reset_tare(self) -> None:
        self.offsets = [0.0, 0.0]
