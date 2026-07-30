import pytest

from pressure_monitor.sources import SIMULATED_PORT, PortInfo
from pressure_monitor.ui.control_panel import (
    MAX_WINDOW_S,
    MIN_WINDOW_S,
    NO_READING,
    ControlPanel,
)


@pytest.fixture
def panel(qapp):
    widget = ControlPanel()
    widget.set_ports([PortInfo("/dev/ttyACM0", "Arduino Uno")])
    return widget


def _reading_texts(panel):
    return [row._value.text() for row in panel._readings]


def test_the_simulator_is_always_offered(panel):
    devices = [panel._ports.itemData(i) for i in range(panel._ports.count())]
    assert devices == ["/dev/ttyACM0", SIMULATED_PORT]


def test_an_unlisted_port_is_added_rather_than_ignored(panel):
    panel.select_port("/dev/pts/3")
    assert panel.port() == "/dev/pts/3"


def test_a_rescan_keeps_the_selected_port_even_if_it_vanished(panel):
    panel.select_port("/dev/pts/3")
    panel.set_ports([PortInfo("/dev/ttyACM0", "Arduino Uno")])
    assert panel.port() == "/dev/pts/3"


def test_a_rescan_keeps_a_still_present_port_selected(panel):
    panel.select_port(SIMULATED_PORT)
    panel.set_ports([PortInfo("/dev/ttyUSB0", "CH340")])
    assert panel.port() == SIMULATED_PORT


def test_connect_and_disconnect_are_the_same_button(panel):
    requested = []
    panel.connect_requested.connect(lambda port, baud: requested.append((port, baud)))
    panel.disconnect_requested.connect(lambda: requested.append("disconnect"))

    panel._connect.click()
    panel.set_connected(True)
    panel._connect.click()

    assert requested == [("/dev/ttyACM0", 115200), "disconnect"]


def test_the_port_cannot_be_changed_while_connected(panel):
    panel.set_connected(True)
    assert not panel._ports.isEnabled()
    assert not panel._baud.isEnabled()

    panel.set_connected(False)
    assert panel._ports.isEnabled()


def test_the_time_window_is_clamped_to_the_supported_range(panel):
    panel.set_window_seconds(5)
    assert panel.window_seconds() == MIN_WINDOW_S

    panel.set_window_seconds(120)
    assert panel.window_seconds() == MAX_WINDOW_S


def test_moving_the_time_window_announces_the_new_value(panel):
    seen = []
    panel.window_changed.connect(seen.append)
    panel.set_window_seconds(35)

    assert seen == [35]
    assert panel._window_value.text() == "35 s"


def test_readings_follow_the_selected_unit(panel):
    panel.select_unit("kPa")
    panel.set_readings((101.325, 1.0))
    assert _reading_texts(panel) == ["101.33", "1.00"]

    panel.select_unit("mmHg")
    panel.set_readings((101.325, 1.0))
    assert _reading_texts(panel) == ["760.0", "7.5"]


def test_readings_are_blanked_when_there_is_no_data(panel):
    panel.set_readings((1.0, 2.0))
    panel.set_readings(None)
    assert _reading_texts(panel) == [NO_READING, NO_READING]
