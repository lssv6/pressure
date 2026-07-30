"""Parsing of the serial line protocol spoken by the Arduino.

The firmware emits one text line per acquisition::

    <raw_sensor_1><separator><raw_sensor_2>

Separators may be commas, semicolons or whitespace, and an optional leading
field (such as a millis() timestamp) is tolerated: the two *last* numeric
fields of a line are used. Lines that are not made up entirely of numbers are
treated as firmware chatter and ignored.
"""

from __future__ import annotations

import re

_SEPARATORS = re.compile(r"[,;\s]+")


def parse_sample_line(line: str) -> tuple[float, float] | None:
    """Return the two sensor readings in a line, or ``None`` if there are none."""
    text = line.strip().strip("\x00")
    if not text or text.startswith("#"):
        return None

    values = []
    for token in _SEPARATORS.split(text):
        if not token:
            continue
        try:
            values.append(float(token))
        except ValueError:
            return None

    if len(values) < 2:
        return None
    return values[-2], values[-1]
