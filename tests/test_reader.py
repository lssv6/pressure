import time

import pytest

from pressure_monitor.calibration import DEFAULT_COUNTS_PER_KPA
from pressure_monitor.reader import SampleReader
from pressure_monitor.sources import SampleSource, SimulatedSampleSource, SourceError


class FakeSource(SampleSource):
    """Replays a fixed script of readings, then blocks until stopped."""

    label = "fake"

    def __init__(self, readings, fail_with=None):
        self.readings = list(readings)
        self.fail_with = fail_with
        self.closed = False

    def open(self):
        pass

    def read(self):
        if self.readings:
            return self.readings.pop(0)
        if self.fail_with:
            raise SourceError(self.fail_with)
        time.sleep(0.01)
        return None

    def close(self):
        self.closed = True


def _drain_until(reader, count, timeout=2.0):
    samples = []
    deadline = time.monotonic() + timeout
    while len(samples) < count and time.monotonic() < deadline:
        samples.extend(reader.drain())
        time.sleep(0.005)
    return samples


def test_readings_reach_the_consumer_with_timestamps():
    reader = SampleReader()
    source = FakeSource([(1.0, 2.0), (3.0, 4.0)])
    reader.start(source)

    samples = _drain_until(reader, 2)
    reader.stop()

    assert [(s.raw_1, s.raw_2) for s in samples] == [(1.0, 2.0), (3.0, 4.0)]
    assert samples[0].t <= samples[1].t
    assert source.closed


def test_drain_returns_each_sample_once():
    reader = SampleReader()
    reader.start(FakeSource([(1.0, 2.0)]))

    _drain_until(reader, 1)
    assert reader.drain() == []
    reader.stop()


def test_stop_ends_the_thread():
    reader = SampleReader()
    reader.start(FakeSource([]))
    assert reader.is_running

    reader.stop()
    assert not reader.is_running


def test_starting_twice_is_refused():
    reader = SampleReader()
    reader.start(FakeSource([]))
    try:
        with pytest.raises(RuntimeError):
            reader.start(FakeSource([]))
    finally:
        reader.stop()


def test_a_dying_source_is_closed_and_the_thread_exits():
    reader = SampleReader()
    source = FakeSource([], fail_with="cable unplugged")
    reader.start(source)

    deadline = time.monotonic() + 2.0
    while reader.is_running and time.monotonic() < deadline:
        time.sleep(0.005)

    assert not reader.is_running
    assert source.closed


def test_the_simulator_produces_readings_in_a_plausible_range():
    source = SimulatedSampleSource(rate_hz=200.0)
    source.open()
    try:
        readings = [source.read() for _ in range(20)]
    finally:
        source.close()

    for raw_1, raw_2 in readings:
        for raw in (raw_1, raw_2):
            kpa = (raw - source.zero_counts) / DEFAULT_COUNTS_PER_KPA
            assert 0.0 < kpa < 20.0
