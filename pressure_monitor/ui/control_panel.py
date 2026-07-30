"""The control column: live readings, connection, display and calibration."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..calibration import DEFAULT_COUNTS_PER_KPA
from ..sources import SIMULATED_LABEL, SIMULATED_PORT, PortInfo
from ..units import UNITS, PressureUnit, unit_by_symbol
from . import theme
from .plot_panel import CHANNEL_NAMES

BAUD_RATES = (9600, 19200, 38400, 57600, 115200)
DEFAULT_BAUD_RATE = 115200
MIN_WINDOW_S = 10
MAX_WINDOW_S = 60
DEFAULT_WINDOW_S = 20
NO_READING = "––"


def _caption(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "caption")
    return label


def _group(title: str) -> tuple[QGroupBox, QVBoxLayout]:
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    layout.setSpacing(6)
    return box, layout


class _ReadingRow(QWidget):
    """One channel's current value, with a colour swatch matching its curve."""

    def __init__(self, name: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        swatch = QLabel()
        swatch.setFixedSize(10, 10)
        swatch.setStyleSheet(f"background-color: {color}; border-radius: 5px;")

        self._value = QLabel(NO_READING)
        self._value.setProperty("role", "reading")
        self._value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._unit = QLabel("")
        self._unit.setProperty("role", "unit")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(swatch)
        layout.addWidget(_caption(name))
        layout.addStretch(1)
        layout.addWidget(self._value)
        layout.addWidget(self._unit, 0, Qt.AlignmentFlag.AlignBottom)

    def set_value(self, text: str, unit_symbol: str) -> None:
        self._value.setText(text)
        self._unit.setText(unit_symbol)


class ControlPanel(QWidget):
    """Emits user intent; the main window owns the resulting state changes."""

    connect_requested = Signal(str, int)
    disconnect_requested = Signal()
    ports_refresh_requested = Signal()
    unit_changed = Signal(object)
    window_changed = Signal(int)
    span_changed = Signal(float)
    tare_requested = Signal()
    zero_reset_requested = Signal()
    clear_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self._build_readings())
        layout.addWidget(self._build_connection())
        layout.addWidget(self._build_display())
        layout.addWidget(self._build_calibration())
        layout.addStretch(1)

    # ------------------------------------------------------------------ build

    def _build_readings(self) -> QGroupBox:
        box, layout = _group("Live readings")
        self._readings = [
            _ReadingRow(name, color)
            for name, color in zip(CHANNEL_NAMES, theme.CHANNEL_COLORS, strict=True)
        ]
        for row in self._readings:
            layout.addWidget(row)
        return box

    def _build_connection(self) -> QGroupBox:
        box, layout = _group("Arduino")
        self._ports = QComboBox()
        self._ports.setToolTip("Serial port the Arduino is connected to")

        self._baud = QComboBox()
        for rate in BAUD_RATES:
            self._baud.addItem(f"{rate} baud", rate)
        self._baud.setCurrentIndex(BAUD_RATES.index(DEFAULT_BAUD_RATE))

        refresh = QPushButton("Refresh")
        refresh.setToolTip("Re-scan the available serial ports")
        refresh.clicked.connect(self.ports_refresh_requested)

        port_row = QHBoxLayout()
        port_row.setSpacing(6)
        port_row.addWidget(self._baud, 1)
        port_row.addWidget(refresh)

        self._connect = QPushButton("Connect")
        self._connect.setProperty("role", "primary")
        self._connect.clicked.connect(self._on_connect_clicked)

        layout.addWidget(_caption("Port"))
        layout.addWidget(self._ports)
        layout.addLayout(port_row)
        layout.addSpacing(2)
        layout.addWidget(self._connect)
        return box

    def _build_display(self) -> QGroupBox:
        box, layout = _group("Display")
        self._unit = QComboBox()
        for unit in UNITS:
            self._unit.addItem(f"{unit.symbol} — {unit.name}", unit.symbol)
        self._unit.currentIndexChanged.connect(
            lambda: self.unit_changed.emit(self.unit())
        )

        self._window = QSlider(Qt.Orientation.Horizontal)
        self._window.setRange(MIN_WINDOW_S, MAX_WINDOW_S)
        self._window.setValue(DEFAULT_WINDOW_S)
        self._window.setPageStep(5)
        self._window.setTickInterval(10)
        self._window.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._window.valueChanged.connect(self._on_window_changed)

        self._window_value = QLabel(f"{DEFAULT_WINDOW_S} s")
        self._window_value.setAlignment(Qt.AlignmentFlag.AlignRight)

        window_header = QHBoxLayout()
        window_header.addWidget(_caption("Time window"))
        window_header.addStretch(1)
        window_header.addWidget(self._window_value)

        clear = QPushButton("Clear plot")
        clear.clicked.connect(self.clear_requested)

        layout.addWidget(_caption("Pressure unit"))
        layout.addWidget(self._unit)
        layout.addSpacing(4)
        layout.addLayout(window_header)
        layout.addWidget(self._window)
        layout.addSpacing(2)
        layout.addWidget(clear)
        return box

    def _build_calibration(self) -> QGroupBox:
        box, layout = _group("Calibration")
        self._span = QDoubleSpinBox()
        self._span.setDecimals(3)
        self._span.setRange(0.001, 1_000_000.0)
        self._span.setValue(DEFAULT_COUNTS_PER_KPA)
        self._span.setKeyboardTracking(False)
        self._span.setToolTip(
            "Raw HX710B counts per kilopascal. Use 1 if the firmware already "
            "sends kilopascals."
        )
        self._span.valueChanged.connect(self.span_changed)

        tare = QPushButton("Tare")
        tare.setToolTip("Store the current readings as zero pressure")
        tare.clicked.connect(self.tare_requested)
        reset = QPushButton("Reset zero")
        reset.clicked.connect(self.zero_reset_requested)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        buttons.addWidget(tare, 1)
        buttons.addWidget(reset, 1)

        layout.addWidget(_caption("Counts per kPa"))
        layout.addWidget(self._span)
        layout.addSpacing(2)
        layout.addLayout(buttons)
        return box

    # ----------------------------------------------------------------- events

    def _on_connect_clicked(self) -> None:
        if self._connect.text() == "Connect":
            self.connect_requested.emit(self.port(), self.baud_rate())
        else:
            self.disconnect_requested.emit()

    def _on_window_changed(self, seconds: int) -> None:
        self._window_value.setText(f"{seconds} s")
        self.window_changed.emit(seconds)

    # ------------------------------------------------------------------ state

    def set_ports(self, ports: list[PortInfo]) -> None:
        """Rebuild the port list, keeping the current selection when possible."""
        previous = self.port()
        self._ports.blockSignals(True)
        self._ports.clear()
        for port in ports:
            self._ports.addItem(port.label, port.device)
        self._ports.addItem(SIMULATED_LABEL, SIMULATED_PORT)
        if previous:
            self.select_port(previous)
        else:
            self._ports.setCurrentIndex(0)
        self._ports.blockSignals(False)

    def port(self) -> str:
        return self._ports.currentData() or ""

    def select_port(self, device: str) -> None:
        """Select a port, listing it first if the scan did not report it.

        Ports named on the command line or restored from the previous session do
        not always show up in the scan, and silently connecting to some other
        board instead would be worse than offering one the user asked for.
        """
        if not device:
            return
        index = self._ports.findData(device)
        if index < 0:
            self._ports.insertItem(0, device, device)
            index = 0
        self._ports.setCurrentIndex(index)

    def baud_rate(self) -> int:
        return int(self._baud.currentData())

    def select_baud_rate(self, rate: int) -> None:
        index = self._baud.findData(rate)
        if index >= 0:
            self._baud.setCurrentIndex(index)

    def unit(self) -> PressureUnit:
        return unit_by_symbol(self._unit.currentData())

    def select_unit(self, symbol: str) -> None:
        index = self._unit.findData(unit_by_symbol(symbol).symbol)
        if index >= 0:
            self._unit.setCurrentIndex(index)

    def window_seconds(self) -> int:
        return self._window.value()

    def set_window_seconds(self, seconds: int) -> None:
        self._window.setValue(max(MIN_WINDOW_S, min(MAX_WINDOW_S, seconds)))

    def span(self) -> float:
        return self._span.value()

    def set_span(self, counts_per_kpa: float) -> None:
        self._span.setValue(counts_per_kpa)

    def set_connected(self, connected: bool, busy: bool = False) -> None:
        self._connect.setText("Disconnect" if connected or busy else "Connect")
        self._connect.setEnabled(not busy)
        self._connect.setProperty("role", "danger" if connected or busy else "primary")
        # Qt only re-reads dynamic properties in the stylesheet after a repolish.
        self._connect.style().unpolish(self._connect)
        self._connect.style().polish(self._connect)
        self._ports.setEnabled(not (connected or busy))
        self._baud.setEnabled(not (connected or busy))

    def set_readings(self, values_kpa: tuple[float, float] | None) -> None:
        unit = self.unit()
        for index, row in enumerate(self._readings):
            text = NO_READING if values_kpa is None else unit.format(values_kpa[index])
            row.set_value(text, unit.symbol)
