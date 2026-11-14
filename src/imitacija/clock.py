"""Injectable monotonic scheduling and explicit UTC simulation-time mapping."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    """Minimum interface used by acquisition; delivery speed is independently scaled."""

    def now(self) -> float:
        """Return seconds elapsed in this simulation run."""
        ...

    async def sleep_until(self, instant: float) -> None:
        """Wait until a simulation instant without changing acquisition timestamps."""
        ...


class RealClock:
    """Map monotonic elapsed wall time onto an accelerated simulation clock."""

    def __init__(self, speed: float) -> None:
        self.speed = speed
        self.origin = time.monotonic()

    def now(self) -> float:
        """Wall-clock adjustments cannot move the scheduler backwards."""
        return (time.monotonic() - self.origin) * self.speed

    async def sleep_until(self, instant: float) -> None:
        """Long waits are cancellable and let the worker report progress regularly."""
        while (remaining := (instant - self.now()) / self.speed) > 0:
            await asyncio.sleep(min(remaining, 30))


class ManualClock:
    """Deterministic test clock: waiting advances logical time and yields to asyncio."""

    def __init__(self) -> None:
        self.instant = 0.0

    def now(self) -> float:
        """Return the last explicitly advanced instant."""
        return self.instant

    async def sleep_until(self, instant: float) -> None:
        """Never reverse time, even when a test requests an already-due event."""
        self.instant = max(self.instant, instant)
        await asyncio.sleep(0)


def timestamp(start: datetime, elapsed: float) -> datetime:
    """UTC acquisition mapping shared by all owners in one declared run."""
    return start + timedelta(seconds=elapsed)
