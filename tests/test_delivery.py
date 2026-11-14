"""Verify HTTP contract, delayed availability, bounded memory and retry identity."""

from __future__ import annotations

import asyncio
import json

import httpx

from imitacija.clock import ManualClock
from imitacija.delivery import Delivery, HttpTransport
from imitacija.models import Observation, Reading, Settings
from imitacija.registry import CHANNELS
from imitacija.scheduler import Scheduler


def observation(
    channel: str = "heart_rate", acquired: float = 0, available: float = 0, sequence: int = 1
) -> Observation:
    return Observation(
        reading=Reading(
            channel=channel, value=1.1, unit=CHANNELS[channel].unit, measured_at=Settings().start
        ),
        scope="crew",
        owner="crew-1",
        sensor_id="crew-1:heart",
        sequence=sequence,
        acquired_s=acquired,
        available_s=available,
    )


def test_http_routing_retries_keep_timestamp_and_identity() -> None:
    async def scenario() -> None:
        requests: list[httpx.Request] = []

        async def receiver(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(503 if len(requests) == 1 else 204)

        settings = Settings(
            backoff_wall_s=0,
            shutdown_drain_wall_s=1,
            data_route="/custom/data",
        )
        async with httpx.AsyncClient(
            base_url="http://receiver", transport=httpx.MockTransport(receiver)
        ) as client:
            delivery = Delivery(settings, ManualClock(), HttpTransport(client), run_id="fixed")
            delivery.submit(observation())
            task = asyncio.create_task(delivery.run())
            await delivery.finish(task)
        assert delivery.counters.delivered == 1
        assert delivery.counters.retries == 1
        assert requests[0].content == requests[1].content
        assert json.loads(requests[1].content)["unit"] == "s^-1"
        assert requests[0].headers["Idempotency-Key"] == requests[1].headers["Idempotency-Key"]
        assert requests[1].url.path == "/custom/data"
        assert set(json.loads(requests[1].content)) == {
            "channel",
            "value",
            "unit",
            "measured_at",
        }

    asyncio.run(scenario())


def test_delayed_lab_does_not_block_vital_and_expires_from_acquisition() -> None:
    async def scenario() -> None:
        clock = ManualClock()
        received: list[str] = []

        async def receiver(request: httpx.Request) -> httpx.Response:
            received.append(json.loads(request.content)["channel"])
            return httpx.Response(200)

        settings = Settings(max_age_s=20, shutdown_drain_wall_s=0.05)
        async with httpx.AsyncClient(
            base_url="http://receiver", transport=httpx.MockTransport(receiver)
        ) as client:
            delivery = Delivery(settings, clock, HttpTransport(client))
            delivery.submit(observation("troponin_i", available=10))
            delivery.submit(observation())
            task = asyncio.create_task(delivery.run())
            await asyncio.sleep(0.01)
            assert received == ["heart_rate"]
            clock.instant = 10
            delivery.changed.set()
            await asyncio.sleep(0.01)
            assert received == ["heart_rate", "troponin_i"]
            clock.instant = 30
            delivery.submit(observation(sequence=2))
            await delivery.finish(task)
        assert delivery.counters.expired == 1

    asyncio.run(scenario())


def test_overflow_permanent_error_and_bounded_shutdown() -> None:
    async def scenario() -> None:
        async with httpx.AsyncClient(
            base_url="http://receiver", transport=httpx.MockTransport(lambda _: httpx.Response(401))
        ) as client:
            d = Delivery(
                Settings(queue_capacity=2, shutdown_drain_wall_s=0.02),
                ManualClock(),
                HttpTransport(client),
            )
            for sequence in range(4):
                d.submit(observation(sequence=sequence))
            assert len(d.pending) == 2 and d.counters.overflow == 2
            task = asyncio.create_task(d.run())
            await d.finish(task)
            assert d.counters.failed == 2 and d.counters.retries == 0
            assert not d.pending
            delayed = Delivery(
                Settings(shutdown_drain_wall_s=0.01), ManualClock(), HttpTransport(client)
            )
            delayed.submit(observation(available=99999))
            task = asyncio.create_task(delayed.run())
            await delayed.finish(task)
            assert delayed.counters.shutdown_dropped == 1
            assert not delayed.pending

    asyncio.run(scenario())


def test_sampling_continues_during_outage_with_bounded_queue() -> None:
    async def scenario() -> None:
        async def slow_receiver(request: httpx.Request) -> httpx.Response:
            await asyncio.sleep(0.01)
            raise httpx.ConnectError("offline", request=request)

        settings = Settings(
            enabled_channels=("ambient_ppco2",),
            queue_capacity=3,
            shutdown_drain_wall_s=0.05,
            backoff_wall_s=0,
            max_attempts=2,
        )
        clock = ManualClock()
        async with httpx.AsyncClient(
            base_url="http://receiver", transport=httpx.MockTransport(slow_receiver)
        ) as client:
            d = Delivery(settings, clock, HttpTransport(client))
            scheduler = Scheduler(settings, clock, d)
            task = asyncio.create_task(d.run())
            await scheduler.run(100)
            assert scheduler.generated == 101
            assert len(d.pending) <= 3
            assert d.counters.overflow > 40
            await d.finish(task)
            assert not d.pending
            fresh = Delivery(settings, clock, HttpTransport(client))
            assert not fresh.pending and fresh.run_id != d.run_id

    asyncio.run(scenario())
