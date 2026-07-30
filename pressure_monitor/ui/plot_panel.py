"""The rolling real-time plot."""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ..units import DEFAULT_UNIT, PressureUnit
from . import theme

CHANNEL_NAMES = ("Sensor 1", "Sensor 2")
MIN_Y_SPAN_KPA = 0.05
"""Smallest visible span, so a flat signal is not magnified into noise."""
Y_RANGE_PADDING = 0.12
Y_RANGE_SMOOTHING = 0.25
"""How far the y range moves towards its target each frame (0-1)."""


class PlotPanel(QWidget):
    """Draws both channels against a time axis whose right edge is 'now'."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._unit = DEFAULT_UNIT
        self._y_range: tuple[float, float] | None = None

        pg.setConfigOptions(antialias=True)
        self._plot = pg.PlotWidget(background=theme.PANEL)
        self._plot.showGrid(x=True, y=True, alpha=0.2)
        self._plot.setMenuEnabled(False)
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.hideButtons()
        self._plot.setLabel("bottom", "Time", units="s")
        self._plot.addLegend(offset=(-10, 10), labelTextColor=theme.TEXT)

        for axis_name in ("left", "bottom"):
            axis = self._plot.getAxis(axis_name)
            axis.setPen(pg.mkPen(theme.GRID))
            axis.setTextPen(pg.mkPen(theme.TEXT_MUTED))
            # Without this the axis rescales itself and labels a kPa plot "kkPa".
            axis.enableAutoSIPrefix(False)

        self._curves = [
            self._plot.plot(
                [],
                [],
                name=name,
                pen=pg.mkPen(color, width=2),
                autoDownsample=True,
                clipToView=True,
            )
            for name, color in zip(CHANNEL_NAMES, theme.CHANNEL_COLORS, strict=True)
        ]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 4, 8)
        layout.addWidget(self._plot)
        self.set_unit(DEFAULT_UNIT)

    def set_unit(self, unit: PressureUnit) -> None:
        self._unit = unit
        self._y_range = None
        self._plot.setLabel("left", "Pressure", units=unit.symbol)

    def set_window(self, seconds: float) -> None:
        # A sliver of headroom keeps the newest point off the right border.
        self._plot.setXRange(-seconds, seconds * 0.02, padding=0)

    def clear(self) -> None:
        for curve in self._curves:
            curve.setData([], [])
        self._y_range = None

    def update_series(
        self,
        t: np.ndarray,
        channel_1_kpa: np.ndarray,
        channel_2_kpa: np.ndarray,
        now: float,
    ) -> None:
        """Redraw with timestamps rewritten as seconds before ``now``."""
        elapsed = t - now
        channels = (
            self._unit.from_kpa(channel_1_kpa),
            self._unit.from_kpa(channel_2_kpa),
        )
        for curve, values in zip(self._curves, channels, strict=True):
            curve.setData(elapsed, values)
        self._update_y_range(channels)

    def _update_y_range(self, channels: tuple[np.ndarray, ...]) -> None:
        if not len(channels[0]):
            return

        low = min(float(values.min()) for values in channels)
        high = max(float(values.max()) for values in channels)
        # The floor is defined in kPa so it means the same pressure in every unit.
        min_padding = self._unit.from_kpa(MIN_Y_SPAN_KPA) / 2
        padding = max((high - low) * Y_RANGE_PADDING, min_padding)
        target = (low - padding, high + padding)

        if self._y_range is None:
            self._y_range = target
        else:
            # Easing towards the target avoids the axis twitching every frame.
            self._y_range = tuple(  # type: ignore[assignment]
                current + (goal - current) * Y_RANGE_SMOOTHING
                for current, goal in zip(self._y_range, target, strict=True)
            )
        self._plot.setYRange(*self._y_range, padding=0)
