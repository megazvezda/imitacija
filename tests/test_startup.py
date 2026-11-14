"""Run-start completeness, baseline provenance and preservation of normal cadences."""

from __future__ import annotations

import asyncio
from collections import Counter

from imitacija.clock import ManualClock
from imitacija.models import AstronautProfile, Environment, Observation, Settings
from imitacija.registry import CHANNELS
from imitacija.scheduler import Scheduler


class Collected:
    def __init__(self) -> None:
        self.items: list[Observation] = []

    def submit(self, observation: Observation) -> None:
        self.items.append(observation)


def test_every_metric_once_at_start_with_immediate_available_baselines() -> None:
    settings = Settings(lab_delay_s=86400, il6_event_times_s=(), troponin_event_times_s=())
    sink = Collected()
    asyncio.run(Scheduler(settings, ManualClock(), sink).run(0))
    assert Counter(o.reading.channel for o in sink.items) == Counter({name: 1 for name in CHANNELS})
    assert all(o.acquired_s == o.available_s == 0 for o in sink.items)
    assert all(o.reading.measured_at == settings.start for o in sink.items)
    assert all(o.window_s == 0 and o.sample_kind == "startup_baseline" for o in sink.items)
    assert all(
        o.sequence == 1 and o.reading.unit == CHANNELS[o.reading.channel].unit for o in sink.items
    )
    values = {o.reading.channel: o.reading.value for o in sink.items}
    assert values["bone_ntx_pct_baseline"] == 0
    assert values["urine_volume_24h"] == 0.0027
    assert values["ambient_integrated_dose"] == 0
    assert values["viral_ebv_detected"] is False


def test_startup_does_not_repeat_or_reset_sparse_and_regular_schedules() -> None:
    settings = Settings(
        enabled_channels=(
            "vitamin_d_25oh",
            "urinary_ntx",
            "urine_volume_24h",
            "heart_rate",
            "troponin_i",
        ),
        troponin_event_times_s=(0, 123),
        lab_delay_s=900,
    )
    sink = Collected()
    scheduler = Scheduler(settings, ManualClock(), sink)

    async def run_twice() -> None:
        await scheduler.run(0)
        await scheduler.run(61)
        # Remove the dense channel to test the mission calendar without thousands
        # of irrelevant minute samples; use a separate instance with the same policy.

    asyncio.run(run_twice())
    assert Counter(
        o.reading.channel for o in sink.items if o.sample_kind == "startup_baseline"
    ) == Counter({c: 1 for c in settings.enabled_channels})
    assert [o.acquired_s for o in sink.items if o.reading.channel == "heart_rate"] == [0, 60]
    sparse = Collected()
    enabled = tuple(name for name in settings.enabled_channels if name != "heart_rate")
    config = settings.model_copy(update={"enabled_channels": enabled})
    asyncio.run(Scheduler(config, ManualClock(), sparse).run(30 * 86400))
    for name, expected in (
        ("vitamin_d_25oh", [0, 30 * 86400]),
        ("urinary_ntx", [0, 7 * 86400, 14 * 86400, 21 * 86400, 28 * 86400]),
        ("troponin_i", [0, 123]),
    ):
        assert [o.acquired_s for o in sparse.items if o.reading.channel == name] == expected
    event = next(
        o
        for o in sparse.items
        if o.reading.channel == "troponin_i" and o.sample_kind == "scheduled"
    )
    assert event.available_s == 123 + 900
    volumes = [
        o
        for o in sparse.items
        if o.reading.channel == "urine_volume_24h" and o.sample_kind == "scheduled"
    ]
    assert volumes[0].acquired_s == volumes[0].window_s == 86400


def test_enabled_channels_and_crew_ownership_preserved_at_start() -> None:
    settings = Settings(
        enabled_channels=("body_mass", "ambient_ppco2"),
        crew=(AstronautProfile(id="a"), AstronautProfile(id="b")),
        environment=Environment(comm_delay_s=5),
    )
    sink = Collected()
    asyncio.run(Scheduler(settings, ManualClock(), sink).run(0))
    assert {(o.owner, o.reading.channel) for o in sink.items} == {
        ("a", "body_mass"),
        ("b", "body_mass"),
        ("iss_cabin", "ambient_ppco2"),
    }
    assert all(o.available_s == 5 for o in sink.items)
    empty = Collected()
    asyncio.run(Scheduler(Settings(enabled_channels=()), ManualClock(), empty).run(0))
    assert not empty.items
