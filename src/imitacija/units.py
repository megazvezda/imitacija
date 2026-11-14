"""Source-to-wire conversions; source units remain visible in the channel dictionary."""

from __future__ import annotations

MMHG_TO_PA = 133.322387415


def convert(value: float, factor: float = 1, offset: float = 0) -> float:
    """Convert an absolute reading (temperature needs an offset, intervals do not)."""
    return value * factor + offset


def co2_ppm(ppco2_pa: float, pressure_pa: float) -> float:
    """CO2 ppm depends on actual total pressure, not a fixed sea-level conversion."""
    if pressure_pa <= 0:
        raise ValueError("total pressure must be positive")
    return ppco2_pa / pressure_pa * 1e6
