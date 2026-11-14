"""Bounded transient POST delivery with immutable retries and aggregate-only diagnostics."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from typing import Protocol

import httpx

from .clock import Clock
from .models import Observation, Settings


class Transport(Protocol):
    """Small HTTP boundary supports an in-memory receiver in integration tests."""

    async def post(
        self, path: str, observation: Observation, headers: dict[str, str]
    ) -> httpx.Response:
        """Send exactly the four-field observation body."""
        ...


class HttpTransport:
    """HTTP connection pool owned by worker lifetime, with redirects deliberately disabled."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def post(
        self, path: str, observation: Observation, headers: dict[str, str]
    ) -> httpx.Response:
        """Pydantic serialization preserves booleans and ISO UTC measurement timestamps."""
        return await self.client.post(
            path, content=observation.reading.model_dump_json(), headers=headers
        )


@dataclass
class Counters:
    """No reading values, identifiers, credentials or request bodies appear in operational logs."""

    submitted: int = 0
    delivered: int = 0
    overflow: int = 0
    expired: int = 0
    failed: int = 0
    retries: int = 0
    shutdown_dropped: int = 0

    def as_json(self) -> str:
        """Safe aggregate diagnostic line for stderr."""
        return json.dumps(asdict(self), sort_keys=True)


@dataclass
class Pending:
    """An attempt counter and eligibility time accompany the immutable sampled result."""

    observation: Observation
    attempts: int = 0
    retry_after_wall: float = 0


class Delivery:
    """One in-flight request plus a bounded RAM queue; delayed labs do not block fresh vitals.

    Requests and backoff occur outside acquisition. Retrying requeues an immutable
    payload with the same idempotency key. The receiver must honor that key to deduplicate.
    Queue overflow discards the oldest pending acquisition, including delayed lab results.
    """

    def __init__(
        self, settings: Settings, clock: Clock, transport: Transport, run_id: str | None = None
    ) -> None:
        self.settings, self.clock, self.transport = settings, clock, transport
        self.run_id = run_id or uuid.uuid4().hex
        self.pending: deque[Pending] = deque()
        self.changed = asyncio.Event()
        self.counters = Counters()
        self.closed = False

    def submit(self, observation: Observation) -> None:
        """Never wait on capacity or network; account explicitly for each dropped result."""
        self.counters.submitted += 1
        if self.closed:
            self.counters.shutdown_dropped += 1
            return
        self._enqueue(Pending(observation))

    def _enqueue(self, item: Pending) -> None:
        """Retried items use the same finite capacity as fresh submissions."""
        if len(self.pending) >= self.settings.queue_capacity:
            oldest = min(self.pending, key=lambda pending: pending.observation.acquired_s)
            self.pending.remove(oldest)
            self.counters.overflow += 1
        self.pending.append(item)
        self.changed.set()

    def route(self) -> str:
        """Every crew and environment reading uses the same configured endpoint."""
        return self.settings.data_route

    def headers(self, observation: Observation) -> dict[str, str]:
        """Transport context preserves the fixed JSON contract and exposes simulation clocks."""
        return {
            "Content-Type": "application/json",
            "X-Simulation-Run": self.run_id,
            "Idempotency-Key": f"{self.run_id}:{observation.owner}:"
            f"{observation.reading.channel}:{observation.sequence}",
            "X-Simulation-Scope": observation.scope,
            "X-Owner-ID": observation.owner,
            "X-Sensor-ID": observation.sensor_id,
            "X-Sample-Kind": observation.sample_kind,
            "X-Window-Seconds": str(observation.window_s),
            "X-Simulation-Start": self.settings.start.isoformat(),
            "X-Simulation-Speed": str(self.settings.speed),
            "X-Result-Available-Seconds": str(observation.available_s),
            "X-Dictionary-Version": "1",
        }

    async def _send(self, item: Pending) -> None:
        """Retry transient failures only; never infer health from transport errors."""
        item.attempts += 1
        try:
            response = await self.transport.post(
                self.route(), item.observation, self.headers(item.observation)
            )
        except httpx.TransportError:
            retryable, retry_after = True, 0.0
        else:
            if 200 <= response.status_code < 300:
                self.counters.delivered += 1
                return
            retryable = response.status_code in {408, 425, 429, 500, 502, 503, 504}
            try:
                retry_after = min(60.0, max(0, float(response.headers.get("Retry-After", "0"))))
            except ValueError:
                retry_after = 0.0
        if retryable and item.attempts < self.settings.max_attempts:
            self.counters.retries += 1
            backoff = self.settings.backoff_wall_s * 2 ** (item.attempts - 1)
            item.retry_after_wall = asyncio.get_running_loop().time() + max(backoff, retry_after)
            self._enqueue(item)
        else:
            self.counters.failed += 1

    async def run(self) -> None:
        """Scan the bounded queue for eligible results rather than delaying behind a lab."""
        try:
            while True:
                self.changed.clear()
                now = self.clock.now()
                wall = asyncio.get_running_loop().time()
                ready: Pending | None = None
                wait = 30.0
                remaining: deque[Pending] = deque()
                while self.pending:
                    item = self.pending.popleft()
                    age = now - item.observation.acquired_s
                    if age > self.settings.max_age_s:
                        self.counters.expired += 1
                        continue
                    delay = max(
                        (item.observation.available_s - now) / self.settings.speed,
                        item.retry_after_wall - wall,
                        0,
                    )
                    if ready is None and delay == 0:
                        ready = item
                    else:
                        remaining.append(item)
                        wait = min(wait, max(0.001, delay))
                self.pending = remaining
                if ready is not None:
                    try:
                        await self._send(ready)
                    except asyncio.CancelledError:
                        self.counters.shutdown_dropped += 1
                        raise
                    continue
                if self.closed and not self.pending:
                    return
                try:
                    await asyncio.wait_for(self.changed.wait(), timeout=wait)
                except TimeoutError:
                    pass
        finally:
            self.counters.shutdown_dropped += len(self.pending)
            self.pending.clear()

    async def finish(self, task: asyncio.Task[None]) -> None:
        """Bounded drain after sampling stops; future lab results may be discarded at exit."""
        self.closed = True
        self.changed.set()
        try:
            await asyncio.wait_for(asyncio.shield(task), self.settings.shutdown_drain_wall_s)
        except TimeoutError:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
