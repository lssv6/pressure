"""Pressure units and conversions.

Samples are always stored internally in kilopascals and converted only when
they are displayed, so switching units never discards history.
"""

from __future__ import annotations

from dataclasses import dataclass

# 1 atm is defined as exactly 101.325 kPa and 760 mmHg.
_KPA_PER_ATM = 101.325
_MMHG_PER_ATM = 760.0


@dataclass(frozen=True)
class PressureUnit:
    """A display unit expressed as a multiple of one kilopascal."""

    name: str
    symbol: str
    per_kpa: float
    decimals: int

    def from_kpa(self, kpa: float) -> float:
        return kpa * self.per_kpa

    def to_kpa(self, value: float) -> float:
        return value / self.per_kpa

    def format(self, kpa: float) -> str:
        return f"{self.from_kpa(kpa):.{self.decimals}f}"


KPA = PressureUnit("Kilopascal", "kPa", 1.0, 2)
MMHG = PressureUnit("Millimetre of mercury", "mmHg", _MMHG_PER_ATM / _KPA_PER_ATM, 1)
ATM = PressureUnit("Standard atmosphere", "atm", 1.0 / _KPA_PER_ATM, 5)

UNITS: tuple[PressureUnit, ...] = (KPA, MMHG, ATM)
DEFAULT_UNIT = KPA


def unit_by_symbol(symbol: str) -> PressureUnit:
    """Look up a unit by its symbol, falling back to kPa for unknown input."""
    for unit in UNITS:
        if unit.symbol.lower() == symbol.strip().lower():
            return unit
    return DEFAULT_UNIT
