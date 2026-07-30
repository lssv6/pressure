"""Main window: wires the acquisition thread to the plot and the controls."""

from __future__ import annotations

import time

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
)

from ..buffers import RollingBuffer
from ..calibration import Calibration
from ..reader import SampleReader
from ..sources import available_ports, create_source
from ..units import DEFAULT_UNIT, PressureUnit
from .control_panel import (
    DEFAULT_BAUD_RATE,
    DEFAULT_WINDOW_S,
    MAX_WINDOW_S,
    ControlPanel,
)
from .plot_panel import PlotPanel

REFRESH_INTERVAL_MS = 33
RETENTION_MARGIN_S = 5.0
"""Kept beyond the largest window so widening it reveals real history."""
CONTROL_PANEL_WIDTH = 320


class MainWindow(QMainWindow):
    def __init__(
        self,
        port: str | None = None,
        baud_rate: int | None = None,
        autoconnect: bool = False,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Dual HX710B Pressure Monitor")
        self.resize(1180, 660)

        self._settings = QSettings()
        self._calibration = Calibration()
        self._buffer = RollingBuffer(MAX_WINDOW_S + RETENTION_MARGIN_S)
        self._reader = SampleReader(self)
        self._latest_raw: tuple[float, float] | None = None

        self._plot = PlotPanel()
        self._controls = ControlPanel()
        self._controls.setMaximumWidth(CONTROL_PANEL_WIDTH + 40)
        self._controls.setMinimumWidth(CONTROL_PANEL_WIDTH - 40)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(self._plot)
        self._splitter.addWidget(self._controls)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        self._splitter.setSizes([880, CONTROL_PANEL_WIDTH])
        self.setCentralWidget(self._splitter)

        self._state_label = QLabel()
        self._metrics_label = QLabel()
        status = QStatusBar()
        status.addWidget(self._state_label, 1)
        status.addPermanentWidget(self._metrics_label)
        self.setStatusBar(status)

        self._connect_signals()
        self.refresh_ports()
        self._load_settings()

        if port:
            self._controls.select_port(port)
        if baud_rate:
            self._controls.select_baud_rate(baud_rate)
        self._apply_controls_to_view()
        self._set_state("Not connected")

        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_INTERVAL_MS)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

        if autoconnect:
            self.connect_to_source(
                self._controls.port(), self._controls.baud_rate()
            )

    def _connect_signals(self) -> None:
        self._controls.connect_requested.connect(self.connect_to_source)
        self._controls.disconnect_requested.connect(self.disconnect_source)
        self._controls.ports_refresh_requested.connect(self.refresh_ports)
        self._controls.unit_changed.connect(self._on_unit_changed)
        self._controls.window_changed.connect(self._on_window_changed)
        self._controls.span_changed.connect(self._on_span_changed)
        self._controls.tare_requested.connect(self.tare)
        self._controls.zero_reset_requested.connect(self.reset_zero)
        self._controls.clear_requested.connect(self.clear)

        self._reader.connected.connect(self._on_connected)
        self._reader.disconnected.connect(self._on_disconnected)
        self._reader.failed.connect(self._on_failed)

    # ------------------------------------------------------------ acquisition

    def connect_to_source(self, port: str, baud_rate: int) -> None:
        if self._reader.is_running or not port:
            return
        self.clear()
        self._controls.set_connected(False, busy=True)
        self._set_state(f"Connecting to {port}…")
        self._reader.start(create_source(port, baud_rate))

    def disconnect_source(self) -> None:
        self._reader.stop()

    def _on_connected(self, label: str) -> None:
        self._controls.set_connected(True)
        self._set_state(f"Connected — {label}")

    def _on_disconnected(self) -> None:
        self._controls.set_connected(False)
        self._set_state("Not connected")

    def _on_failed(self, message: str) -> None:
        self._controls.set_connected(False)
        self._set_state(message)
        QMessageBox.warning(self, "Connection problem", message)

    # ----------------------------------------------------------------- actions

    def refresh_ports(self) -> None:
        self._controls.set_ports(available_ports())

    def clear(self) -> None:
        self._buffer.clear()
        self._latest_raw = None
        self._plot.clear()
        self._controls.set_readings(None)
        self._metrics_label.clear()

    def tare(self) -> None:
        if self._latest_raw is None:
            self._set_state("Nothing to tare yet — connect and wait for a reading")
            return
        self._calibration.tare(self._latest_raw)
        self._set_state("Zero point set from the current readings")
        self._redraw()

    def reset_zero(self) -> None:
        self._calibration.reset_tare()
        self._set_state("Zero point reset to raw counts")
        self._redraw()

    def _on_unit_changed(self, unit: PressureUnit) -> None:
        self._plot.set_unit(unit)
        self._redraw()

    def _on_window_changed(self, seconds: int) -> None:
        self._plot.set_window(seconds)

    def _on_span_changed(self, counts_per_kpa: float) -> None:
        self._calibration.counts_per_kpa = counts_per_kpa
        self._redraw()

    # ---------------------------------------------------------------- refresh

    def _on_tick(self) -> None:
        samples = self._reader.drain()
        for sample in samples:
            self._buffer.append(sample.t, sample.raw_1, sample.raw_2)
        if samples:
            self._latest_raw = (samples[-1].raw_1, samples[-1].raw_2)
        if samples or self._reader.is_running:
            self._redraw()

    def _redraw(self) -> None:
        t, raw_1, raw_2 = self._buffer.arrays()
        self._plot.update_series(
            t,
            self._calibration.to_kpa(raw_1, 0),
            self._calibration.to_kpa(raw_2, 1),
            time.monotonic(),
        )
        if self._latest_raw is None:
            self._controls.set_readings(None)
            return
        self._controls.set_readings(
            (
                self._calibration.to_kpa(self._latest_raw[0], 0),
                self._calibration.to_kpa(self._latest_raw[1], 1),
            )
        )
        self._metrics_label.setText(
            f"{self._buffer.sample_rate():.1f} Hz · {len(self._buffer)} samples in view"
        )

    def _set_state(self, text: str) -> None:
        self._state_label.setText(text)

    def _apply_controls_to_view(self) -> None:
        self._plot.set_unit(self._controls.unit())
        self._plot.set_window(self._controls.window_seconds())
        self._calibration.counts_per_kpa = self._controls.span()
        self._controls.set_readings(None)

    # --------------------------------------------------------------- settings

    def _load_settings(self) -> None:
        settings = self._settings
        self._controls.select_unit(
            str(settings.value("display/unit", DEFAULT_UNIT.symbol))
        )
        self._controls.set_window_seconds(
            int(settings.value("display/window_s", DEFAULT_WINDOW_S))
        )
        self._controls.select_baud_rate(
            int(settings.value("serial/baud", DEFAULT_BAUD_RATE))
        )
        saved_port = str(settings.value("serial/port", ""))
        if saved_port:
            self._controls.select_port(saved_port)
        self._controls.set_span(
            float(settings.value("calibration/counts_per_kpa", self._controls.span()))
        )
        # The zero point deliberately is not restored: a stale tare from another
        # session silently offsets every reading, and taring again is one click.
        geometry = settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        splitter_state = settings.value("window/splitter")
        if splitter_state is not None:
            self._splitter.restoreState(splitter_state)

    def _save_settings(self) -> None:
        settings = self._settings
        settings.setValue("display/unit", self._controls.unit().symbol)
        settings.setValue("display/window_s", self._controls.window_seconds())
        settings.setValue("serial/baud", self._controls.baud_rate())
        settings.setValue("serial/port", self._controls.port())
        settings.setValue("calibration/counts_per_kpa", self._controls.span())
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/splitter", self._splitter.saveState())

    def closeEvent(self, event) -> None:
        self._timer.stop()
        self._reader.stop()
        self._save_settings()
        super().closeEvent(event)
