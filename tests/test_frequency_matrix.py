"""Protocol-level timing tests against the project's frequency matrix requirements."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError

from imitacija.clock import ManualClock
from imitacija.models import Environment, Observation, Settings
from imitacija.registry import CHANNELS, dictionary
from imitacija.scheduler import Scheduler


class Samples:
    def __init__(self) -> None:
        self.items: list[Observation] = []

    def submit(self, value: Observation) -> None:
        self.items.append(value)


def acquire(settings: Settings, until: float) -> list[Observation]:
    sink = Samples()
    asyncio.run(Scheduler(settings, ManualClock(), sink).run(until))
    return sink.items


def test_all_scalar_one_hz_streams_have_independent_phases() -> None:
    selected = (
        "spo2",
        "body_temperature",
        "ambient_ppco2",
        "ambient_light_lux",
        "ambient_dose_rate",
        "spe_flag",
    )
    items = acquire(Settings(enabled_channels=selected), 3.9)
    first: set[float] = set()
    for name in selected:
        times = [o.acquired_s for o in items if o.reading.channel == name]
        assert len(times) == 4
        assert [b - a for a, b in zip(times, times[1:], strict=False)] == pytest.approx([1, 1, 1])
        first.add(times[0])
    assert len(first) > 1


def test_stand_test_burst_is_optional_bounded_and_does_not_duplicate_cuff() -> None:
    names = ("bp_systolic", "bp_diastolic")
    settings = Settings(enabled_channels=names, bp_session_start_s=0, stand_test_start_s=100)
    items = acquire(settings, 3600)
    systolic = [o for o in items if o.reading.channel == "bp_systolic"]
    diastolic = [o for o in items if o.reading.channel == "bp_diastolic"]
    burst = [o for o in systolic if 100 <= o.acquired_s < 280]
    assert len(burst) == 1800  # 10Hz for exactly three minutes.
    assert [
        b.acquired_s - a.acquired_s for a, b in zip(burst, burst[1:], strict=False)
    ] == pytest.approx([0.1] * 1799)
    assert [o.acquired_s for o in systolic if not 100 <= o.acquired_s < 280] == [0, 3600]
    assert [o.acquired_s for o in systolic] == [o.acquired_s for o in diastolic]
    normal = acquire(Settings(enabled_channels=names, bp_session_start_s=0), 3600)
    assert len(normal) == 4  # Burst does not run unless explicitly configured.


def test_daily_hydration_weekly_ntx_and_waking_cortisol() -> None:
    names = (
        "body_mass",
        "urine_specific_gravity",
        "urinary_ntx",
        "bone_ntx_pct_baseline",
        "cortisol_saliva",
        "urine_volume_24h",
    )
    items = acquire(Settings(enabled_channels=names), 8 * 86400)
    for name in ("body_mass", "urine_specific_gravity"):
        times = [o.acquired_s for o in items if o.reading.channel == name]
        assert times[:4] == [7 * 3600, 18.5 * 3600, 31 * 3600, 42.5 * 3600]
    assert [o.acquired_s for o in items if o.reading.channel == "urinary_ntx"] == [7 * 86400]
    assert [o.acquired_s for o in items if o.reading.channel == "cortisol_saliva"][:5] == [
        h * 3600 for h in (7, 11, 15, 19, 23)
    ]
    assert [o.acquired_s for o in items if o.reading.channel == "urine_volume_24h"] == [
        d * 86400 for d in range(1, 9)
    ]
    assert all(o.window_s == 0 for o in items if o.reading.channel == "urine_specific_gravity")
    assert CHANNELS["urine_specific_gravity"].specimen == "spot urine"


def test_explicit_assay_gates_and_48_hour_viral_sessions() -> None:
    names = ("il6_serum", "troponin_i", "viral_ebv_detected", "viral_cmv_detected")
    items = acquire(
        Settings(enabled_channels=names, il6_event_times_s=(123, 456), troponin_event_times_s=()),
        3 * 86400,
    )
    assert [o.acquired_s for o in items if o.reading.channel == "il6_serum"] == [123, 456]
    assert not [o for o in items if o.reading.channel == "troponin_i"]
    for name, hour in (("viral_ebv_detected", 9), ("viral_cmv_detected", 10)):
        assert [o.acquired_s for o in items if o.reading.channel == name] == [
            hour * 3600,
            (48 + hour) * 3600,
        ]
    with pytest.raises(ValidationError):
        Settings(il6_event_times_s=(-1,))


def test_dictionary_exposes_raw_tier_separately_from_publication() -> None:
    channels = {c.channel: c for c in dictionary(Environment(), 3600).channels}
    assert channels["heart_rate"].raw_acquisition_hz == 100
    assert channels["heart_rate"].window_s == channels["hrv_rmssd"].window_s == 60
    assert channels["glucose"].raw_acquisition_hz == 0.2
    assert channels["glucose"].window_s == 300
    assert channels["sweat_rate"].raw_acquisition_hz == 1
    assert channels["sweat_sodium_flux"].window_s == 60
    assert all(c.frequency_basis == "docs/frequency_table.md" for c in channels.values())
