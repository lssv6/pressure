import numpy as np
import pytest

from pressure_monitor.calibration import Calibration


def test_counts_are_scaled_by_the_span():
    calibration = Calibration(counts_per_kpa=1000.0)
    assert calibration.to_kpa(2500.0, 0) == pytest.approx(2.5)


def test_a_span_of_one_passes_kilopascals_through():
    calibration = Calibration(counts_per_kpa=1.0)
    assert calibration.to_kpa(12.5, 1) == pytest.approx(12.5)


def test_tare_zeroes_each_channel_independently():
    calibration = Calibration(counts_per_kpa=100.0)
    calibration.tare((8_388_608.0, 8_390_000.0))

    assert calibration.to_kpa(8_388_608.0, 0) == pytest.approx(0.0)
    assert calibration.to_kpa(8_390_000.0, 1) == pytest.approx(0.0)
    assert calibration.to_kpa(8_388_708.0, 0) == pytest.approx(1.0)


def test_reset_tare_restores_raw_counts():
    calibration = Calibration(counts_per_kpa=1.0)
    calibration.tare((10.0, 20.0))
    calibration.reset_tare()
    assert calibration.to_kpa(10.0, 0) == pytest.approx(10.0)


def test_a_zero_span_cannot_produce_infinities():
    calibration = Calibration(counts_per_kpa=0.0)
    assert calibration.to_kpa(5.0, 0) == pytest.approx(5.0)


def test_conversion_works_on_arrays():
    calibration = Calibration(counts_per_kpa=10.0, offsets=[5.0, 0.0])
    converted = calibration.to_kpa(np.array([5.0, 15.0, 25.0]), 0)
    assert converted == pytest.approx([0.0, 1.0, 2.0])
