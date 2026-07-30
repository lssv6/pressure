import os

import pytest

from pressure_monitor import sources
from pressure_monitor.sources import PortInfo, SerialSampleSource, SourceError

pytestmark = pytest.mark.skipif(
    not hasattr(os, "openpty"), reason="needs POSIX pseudo-terminals"
)


@pytest.fixture
def fake_board(monkeypatch):
    """A pseudo-terminal standing in for an Arduino, and a way to write to it."""
    monkeypatch.setattr(sources, "ARDUINO_RESET_DELAY_S", 0.0)
    master, slave = os.openpty()
    source = SerialSampleSource(os.ttyname(slave), 115200)
    source.open()

    def send(text):
        os.write(master, text.encode("ascii"))

    try:
        yield source, send
    finally:
        source.close()
        os.close(master)
        os.close(slave)


def test_reads_a_line_from_the_port(fake_board):
    source, send = fake_board
    send("1234,-5678\r\n")
    assert source.read() == (1234.0, -5678.0)


def test_skips_firmware_chatter_without_dropping_the_next_reading(fake_board):
    source, send = fake_board
    send("# dual HX710B ready\n1,2\n")

    assert source.read() is None
    assert source.read() == (1.0, 2.0)


def test_returns_none_when_the_board_is_silent(fake_board):
    source, _ = fake_board
    assert source.read() is None


def test_opening_a_missing_port_reports_the_port_and_a_concise_reason():
    source = SerialSampleSource("/dev/definitely-not-a-serial-port", 115200)
    with pytest.raises(SourceError) as failure:
        source.open()

    message = str(failure.value)
    assert message.startswith("Could not open /dev/definitely-not-a-serial-port: ")
    assert "No such file or directory" in message
    # pyserial's own nesting of the same message must not leak through.
    assert "Errno" not in message
    assert "could not open port" not in message


def test_reading_before_opening_is_an_error():
    with pytest.raises(SourceError, match="not open"):
        SerialSampleSource("/dev/null", 115200).read()


def test_likely_boards_are_offered_first(monkeypatch):
    class Comport:
        def __init__(self, device, description):
            self.device = device
            self.description = description

    monkeypatch.setattr(
        sources.list_ports,
        "comports",
        lambda: [
            Comport("/dev/ttyS0", "n/a"),
            Comport("/dev/ttyACM0", "Arduino Uno"),
        ],
    )

    assert sources.available_ports() == [
        PortInfo("/dev/ttyACM0", "Arduino Uno"),
        PortInfo("/dev/ttyS0", "n/a"),
    ]


def test_a_port_without_a_description_is_labelled_by_device():
    assert PortInfo("/dev/ttyUSB0", "n/a").label == "/dev/ttyUSB0"
    assert PortInfo("/dev/ttyUSB0", "CH340").label == "/dev/ttyUSB0 — CH340"
