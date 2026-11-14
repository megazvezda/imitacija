"""Behavioral checks for independent clocks, specimen windows and physical consistency."""

from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from imitacija.clock import ManualClock
from imitacija.models import (
    AstronautProfile,
    Environment,
    Observation,
    Reading,
    Settings,
)
from imitacija.physiology import DAY, crew_values, environment_values, heart_rate, rmssd
from imitacija.registry import CHANNELS, dictionary
from imitacija.scheduler import Scheduler
from imitacija.units import MMHG_TO_PA, co2_ppm


class Collector:
    """Test-only memory receiver; production uses a bounded queue instead."""

    def __init__(self) -> None:
        self.items: list[Observation] = []

    def submit(self, observation: Observation) -> None:
        self.items.append(observation)


def simulate(settings: Settings, duration: float) -> list[Observation]:
    sink = Collector()
    asyncio.run(Scheduler(settings, ManualClock(), sink).run(duration))
    return sink.items


def test_independent_timing_and_original_timestamp() -> None:
    items = simulate(Settings(enabled_channels=("heart_rate", "spo2", "respiratory_rate")), 120)
    assert [o.acquired_s for o in items if o.reading.channel == "heart_rate"] == [60, 120]
    assert [o.acquired_s for o in items if o.reading.channel == "spo2"] == pytest.approx(
        [0.2 + i for i in range(120)]
    )
    assert [o.acquired_s for o in items if o.reading.channel == "respiratory_rate"] == [77]
    for o in items:
        assert o.reading.measured_at == Settings().start + timedelta(seconds=o.acquired_s)


def test_pairing_si_contract_and_cuff_session() -> None:
    settings = Settings(
        enabled_channels=("bp_systolic", "bp_diastolic"),
        bp_session_start_s=10,
        bp_session_duration_s=7200,
    )
    items = simulate(settings, 8000)
    assert [o.acquired_s for o in items] == [10, 10, 3610, 3610]
    for systolic, diastolic in zip(items[::2], items[1::2], strict=True):
        assert systolic.reading.measured_at == diastolic.reading.measured_at
        assert systolic.reading.value > diastolic.reading.value
        assert float(systolic.reading.value) / MMHG_TO_PA == pytest.approx(114, abs=2)
        payload = json.loads(systolic.reading.model_dump_json())
        assert set(payload) == {"channel", "value", "unit", "measured_at"}
        assert payload["measured_at"].endswith("Z")


def test_all_sparse_lab_channels_and_completed_windows() -> None:
    names = tuple(c.id for c in CHANNELS.values() if c.lab or c.group in {"mass", "urine"})
    items = simulate(Settings(enabled_channels=names), 181 * DAY + 1)
    assert {o.reading.channel for o in items} == set(names)
    il6 = [o for o in items if o.reading.channel == "il6_serum"]
    assert [o.acquired_s / DAY for o in il6] == [0]
    volumes = [o for o in items if o.reading.channel == "urine_volume_24h"]
    assert [o.acquired_s / DAY for o in volumes] == list(range(1, 182))
    assert all(o.window_s == DAY and 0.0025 <= float(o.reading.value) <= 0.003 for o in volumes)
    assert all(o.available_s == o.acquired_s + 3600 for o in il6)
    ntx = {
        o.acquired_s: float(o.reading.value) for o in items if o.reading.channel == "urinary_ntx"
    }
    for o in items:
        if o.reading.channel == "bone_ntx_pct_baseline":
            assert float(o.reading.value) == pytest.approx(ntx[o.acquired_s] / (45e-6) - 1)
        if o.reading.channel.endswith("_detected"):
            assert o.reading.value is False
    assert len([o for o in items if o.reading.channel == "troponin_i"]) == 1


def test_environment_once_for_multiple_crew_and_reproducible() -> None:
    selected = (
        "heart_rate",
        "ambient_ppco2",
        "ambient_integrated_dose",
        "ambient_dose_rate",
        "spe_flag",
    )
    one = Settings(enabled_channels=selected)
    two = one.model_copy(update={"crew": (AstronautProfile(), AstronautProfile(id="crew-2"))})
    first = simulate(one, 300)
    second = simulate(two, 300)
    env1 = [o for o in first if o.scope == "environment"]
    env2 = [o for o in second if o.scope == "environment"]
    assert env1 == env2
    assert len([o for o in second if o.scope == "crew"]) == 2 * len(
        [o for o in first if o.scope == "crew"]
    )
    assert first == simulate(one, 300)
    assert all(o.owner == one.environment.id for o in env1)


def test_hrv_windows_and_healthy_exercise_dynamics() -> None:
    p = AstronautProfile()
    items = simulate(Settings(enabled_channels=("hrv_rmssd",)), 600)
    assert [o.acquired_s for o in items] == list(range(61, 601, 60))
    with pytest.raises(ValueError):
        rmssd(59, p, 42)
    assert rmssd(3600, p, 42) == pytest.approx(p.rmssd_ms, rel=0.08)
    assert heart_rate(17.5 * 3600, p, 42) > heart_rate(12 * 3600, p, 42) + 35
    assert rmssd(17.5 * 3600, p, 42) < rmssd(12 * 3600, p, 42)
    assert (
        crew_values("glucose", 8.65 * 3600, p, 42)["glucose"]
        > crew_values("glucose", 6 * 3600, p, 42)["glucose"]
    )
    assert (
        crew_values("cortisol", 7.5 * 3600, p, 42)["cortisol_saliva"]
        > crew_values("cortisol", 23 * 3600, p, 42)["cortisol_saliva"]
    )


def test_sweat_dry_gating_and_matching_flow_flux() -> None:
    p = AstronautProfile()
    assert crew_values("sweat", 8 * 3600, p, 42) == {}
    assert crew_values("sweat_summary", 8 * 3600, p, 42) == {}
    point = 17.5 * 3600
    samples = [crew_values("sweat", point - 60 + i + 1, p, 42) for i in range(60)]
    expected = (
        sum(float(s["sweat_rate"]) * float(s["sweat_sodium_concentration"]) for s in samples) / 60
    )
    assert crew_values("sweat_summary", point, p, 42)["sweat_sodium_flux"] == pytest.approx(
        expected
    )
    items = simulate(
        Settings(
            enabled_channels=("sweat_rate", "sweat_sodium_flux", "sweat_sodium_concentration")
        ),
        DAY,
    )
    raw = [o for o in items if o.reading.channel == "sweat_rate"]
    flux = [o for o in items if o.reading.channel == "sweat_sodium_flux"]
    assert raw and flux
    assert all(16 * 3600 < o.acquired_s < 19 * 3600 for o in items)
    assert all(b.acquired_s - a.acquired_s == 1 for a, b in zip(raw, raw[1:], strict=False))
    assert all(b.acquired_s - a.acquired_s == 60 for a, b in zip(flux, flux[1:], strict=False))
    assert all(o.window_s == 1 for o in raw) and all(o.window_s == 60 for o in flux)


def test_radiation_integral_and_ppm_pressure() -> None:
    env = Environment()
    previous = 0.0
    for t in range(0, 86401, 60):
        values = environment_values("radiation", t, env, 42)
        assert values["ambient_integrated_dose"] >= previous
        previous = float(values["ambient_integrated_dose"])
    t, delta = 5000, 0.1
    left = environment_values("radiation", t - delta, env, 42)
    right = environment_values("radiation", t + delta, env, 42)
    middle = environment_values("radiation", t, env, 42)
    derivative = (
        float(right["ambient_integrated_dose"]) - float(left["ambient_integrated_dose"])
    ) / (2 * delta)
    assert derivative == pytest.approx(float(middle["ambient_dose_rate"]) / 3_600_000, rel=1e-6)
    assert co2_ppm(3 * MMHG_TO_PA, 760 * MMHG_TO_PA) == pytest.approx(3947.3684)
    assert co2_ppm(400, 50000) == 8000


def test_registry_dictionary_and_invalid_inputs() -> None:
    d = dictionary(Environment(), 3600)
    assert len(CHANNELS) == len(d.channels) == 29
    assert all(c.unit and c.method and c.citations for c in d.channels)
    assert all(c.body_regions == () for c in d.channels if c.scope == "environment")
    assert all("evaluation_basis" not in c.model_dump() for c in d.channels)
    assert set(Reading.model_fields) == {"channel", "value", "unit", "measured_at"}
    with pytest.raises(ValidationError):
        Reading.model_validate(
            {
                "channel": "glucose",
                "value": 5.0,
                "measured_at": Settings().start,
                "evaluation": "normal",
            }
        )
    for invalid in (
        {"speed": 0},
        {"speed": math.nan},
        {"start": datetime(2026, 1, 1)},
        {"crew": [{"id": "x"}, {"id": "x"}]},
        {"data_route": "https://other"},
        {"data_route": "/data/{owner}"},
    ):
        with pytest.raises(ValidationError):
            Settings.model_validate(invalid)
    with pytest.raises(ValidationError):
        Reading(
            channel="glucose",
            value=math.inf,
            unit="mol/m^3",
            measured_at=Settings().start,
        )
    with pytest.raises(ValueError):
        Scheduler(Settings(enabled_channels=("sleep_stage",)), ManualClock(), Collector())


def test_late_scheduler_coalesces_without_backdating() -> None:
    class SlowClock(ManualClock):
        async def sleep_until(self, instant: float) -> None:
            self.instant = max(self.instant, instant) + 10

    sink = Collector()
    asyncio.run(Scheduler(Settings(enabled_channels=("heart_rate",)), SlowClock(), sink).run(150))
    assert [o.acquired_s for o in sink.items] == [70, 130]


def test_two_day_stream_has_bounded_state_and_channel_coverage() -> None:
    class SummarySink:
        def __init__(self) -> None:
            self.count = 0
            self.channels: set[str] = set()
            self.previous: dict[tuple[str, str], float] = {}

        def submit(self, observation: Observation) -> None:
            self.count += 1
            self.channels.add(observation.reading.channel)
            key = (observation.owner, observation.reading.channel)
            assert observation.acquired_s > self.previous.get(key, -1)
            self.previous[key] = observation.acquired_s

    sink = SummarySink()
    scheduler = Scheduler(Settings(), ManualClock(), sink)
    asyncio.run(scheduler.run(2 * DAY))
    assert sink.count > 86400
    # Retained scheduler state scales with owners/channels, never total readings.
    assert len(scheduler.events) <= 22
    assert len(scheduler.sequences) <= len(CHANNELS)
    sparse_names = tuple(c.id for c in CHANNELS.values() if c.lab or c.group in {"mass", "urine"})
    sparse = simulate(Settings(enabled_channels=sparse_names), 181 * DAY)
    assert sink.channels | {o.reading.channel for o in sparse} == set(CHANNELS)


def test_matrix_minute_outputs_and_one_hz_environment() -> None:
    selected = ("heart_rate", "respiratory_rate", "ambient_integrated_dose", "ambient_dose_rate")
    items = simulate(Settings(enabled_channels=selected), 180)
    for name, expected in (
        ("heart_rate", [60, 120, 180]),
        ("respiratory_rate", [77, 137]),
        ("ambient_integrated_dose", [60, 120, 180]),
        ("ambient_dose_rate", list(range(181))),
    ):
        assert [o.acquired_s for o in items if o.reading.channel == name] == expected
    respiratory = [o for o in items if o.reading.channel == "respiratory_rate"]
    assert all(o.window_s == 60 for o in respiratory)
    dose = [float(o.reading.value) for o in items if o.reading.channel == "ambient_integrated_dose"]
    assert all(b >= a for a, b in zip(dose, dose[1:], strict=False))


def test_preview_hydration_references_preserve_source_and_wire_units() -> None:
    from imitacija.preview import PreviewState

    settings = Settings()
    state = PreviewState(settings)
    point = 17.5 * 3600
    for group, channels in (
        ("mass", ("body_mass",)),
        ("sweat", ("sweat_rate", "sweat_sodium_concentration")),
        ("sweat_summary", ("sweat_sodium_flux",)),
    ):
        values = crew_values(group, point, settings.crew[0], settings.seed)
        for name in channels:
            meta = CHANNELS[name]
            source = float(values[name])
            state.record(
                Observation(
                    reading=Reading(
                        channel=name,
                        value=source * meta.factor + meta.offset,
                        unit=meta.unit,
                        measured_at=settings.start,
                    ),
                    scope="crew",
                    owner="crew-1",
                    sensor_id=group,
                    sequence=1,
                    acquired_s=point,
                    available_s=point,
                )
            )
    data = json.loads(state.snapshot())
    entries = {entry["reading"]["channel"]: entry for entry in data["readings"]}
    assert entries["body_mass"]["baseline_source_value"] == 75
    assert entries["body_mass"]["source_value"] < 75
    rate = entries["sweat_rate"]
    assert rate["source_value"] == pytest.approx(rate["reading"]["value"] * 3_600_000)
    assert entries["sweat_sodium_flux"]["baseline_source_value"] == pytest.approx(
        rate["baseline_source_value"]
        * entries["sweat_sodium_concentration"]["baseline_source_value"]
    )
