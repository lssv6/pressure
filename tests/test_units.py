import pytest

from pressure_monitor.units import ATM, KPA, MMHG, UNITS, unit_by_symbol


def test_kilopascal_is_the_internal_unit():
    assert KPA.from_kpa(42.0) == 42.0
    assert KPA.to_kpa(42.0) == 42.0


def test_one_atmosphere_in_every_unit():
    one_atm_in_kpa = 101.325
    assert KPA.from_kpa(one_atm_in_kpa) == pytest.approx(101.325)
    assert MMHG.from_kpa(one_atm_in_kpa) == pytest.approx(760.0)
    assert ATM.from_kpa(one_atm_in_kpa) == pytest.approx(1.0)


@pytest.mark.parametrize("unit", UNITS)
def test_conversions_round_trip(unit):
    assert unit.to_kpa(unit.from_kpa(13.37)) == pytest.approx(13.37)


def test_formatting_uses_a_sensible_precision_per_unit():
    assert KPA.format(101.325) == "101.33"
    assert MMHG.format(101.325) == "760.0"
    assert ATM.format(101.325) == "1.00000"


def test_lookup_is_case_insensitive_and_falls_back_to_kilopascal():
    assert unit_by_symbol("mmhg") is MMHG
    assert unit_by_symbol(" ATM ") is ATM
    assert unit_by_symbol("psi") is KPA
