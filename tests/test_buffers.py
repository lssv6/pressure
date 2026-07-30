import pytest

from pressure_monitor.buffers import RollingBuffer


def test_samples_older_than_the_retention_are_dropped():
    buffer = RollingBuffer(retention_s=10.0)
    for i in range(30):
        buffer.append(float(i), float(i), float(-i))

    t, channel_1, channel_2 = buffer.arrays()
    assert t[0] == pytest.approx(19.0)
    assert t[-1] == pytest.approx(29.0)
    assert channel_1[-1] == pytest.approx(29.0)
    assert channel_2[-1] == pytest.approx(-29.0)


def test_shrinking_the_retention_trims_immediately():
    buffer = RollingBuffer(retention_s=60.0)
    for i in range(60):
        buffer.append(float(i), 0.0, 0.0)

    buffer.set_retention(10.0)
    assert len(buffer) == 11


def test_latest_reports_both_channels():
    buffer = RollingBuffer(retention_s=10.0)
    assert buffer.latest() is None

    buffer.append(1.0, 2.0, 3.0)
    assert buffer.latest() == (2.0, 3.0)


def test_clear_empties_the_buffer():
    buffer = RollingBuffer(retention_s=10.0)
    buffer.append(1.0, 2.0, 3.0)
    buffer.clear()
    assert len(buffer) == 0
    assert buffer.arrays()[0].size == 0


def test_sample_rate_is_measured_over_recent_samples():
    buffer = RollingBuffer(retention_s=10.0)
    for i in range(100):
        buffer.append(i * 0.05, 0.0, 0.0)

    assert buffer.sample_rate() == pytest.approx(20.0, rel=0.05)


def test_sample_rate_is_zero_until_there_are_two_samples():
    buffer = RollingBuffer(retention_s=10.0)
    assert buffer.sample_rate() == 0.0
    buffer.append(0.0, 0.0, 0.0)
    assert buffer.sample_rate() == 0.0
