"""Validated immutable contracts, configuration, and transport-only observation context."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class FrozenModel(BaseModel):
    """Reject unknown configuration fields and accidental mutation of sampled values."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class Reading(FrozenModel):
    """The exact four-field body; acquisition time survives delays and retries."""

    channel: str
    value: float | bool
    unit: str = Field(min_length=1)
    measured_at: datetime

    @field_validator("measured_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        """Require an aware instant and normalize its representation to UTC."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("measured_at must include a timezone")
        return value.astimezone(UTC)


class AstronautProfile(FrozenModel):
    """Synthetic adult baseline, not an imported medical history."""

    id: str = Field(default="crew-1", pattern=r"^[A-Za-z0-9_-]+$")
    sex: Literal["male", "female"] = "male"
    postmenopausal: bool = False
    mass_kg: float = Field(default=75, ge=45, le=120)
    resting_hr_bpm: float = Field(default=66, ge=50, le=85)
    rmssd_ms: float = Field(default=40, ge=20, le=80)
    sbp_mmhg: float = Field(default=114, ge=100, lt=120)
    dbp_mmhg: float = Field(default=73, ge=60, lt=80)
    ntx_baseline: float = Field(default=45, ge=26, le=80)
    vitamin_d_ng_ml: float = Field(default=40, ge=35, le=45)
    # Local patch references are synthetic fixture values, not serum thresholds.
    # Compare like activity/collection conditions when interpreting their changes.
    sweat_reference_rate_l_h: float = Field(default=0.42 / 1800, gt=0, le=0.001)
    sweat_reference_sodium_mmol_l: float = Field(default=44, ge=10, le=100)

    @model_validator(mode="after")
    def coherent(self) -> AstronautProfile:
        """Sex-dependent assay metadata must describe the chosen fixture."""
        if self.postmenopausal and self.sex != "female":
            raise ValueError("postmenopausal applies to female assay profiles")
        return self


class Environment(FrozenModel):
    """Shared compartment configuration; dose is a monitor quantity, never career dose."""

    id: str = Field(default="iss_cabin", pattern=r"^[A-Za-z0-9_-]+$")
    gravity_g: float = Field(default=0, ge=0, le=2)
    comm_delay_s: float = Field(default=0, ge=0, le=3600)
    pressure_pa: float = Field(default=101325, gt=0)
    dose_rate_usv_h: float = Field(default=18, ge=0, le=35)
    initial_monitor_dose_msv: float = Field(default=0, ge=0)


class Settings(FrozenModel):
    """All timing is simulation seconds except explicitly named wall-clock fields."""

    start: datetime = datetime(2026, 11, 14, tzinfo=UTC)
    speed: float = Field(default=1, gt=0, le=1e7)
    duration_s: float | None = Field(default=None, gt=0)
    seed: int = 42
    crew: tuple[AstronautProfile, ...] = (AstronautProfile(),)
    environment: Environment = Environment()
    base_url: str = "http://127.0.0.1:8000"
    data_route: str = "/data"
    enabled_channels: tuple[str, ...] | None = None
    lab_delay_s: float = Field(default=3600, ge=0, le=30 * 86400)
    bp_session_start_s: float = Field(default=8 * 3600, ge=0)
    bp_session_duration_s: float | None = Field(default=None, gt=0)
    exercise_test_days: tuple[int, ...] = (0,)
    queue_capacity: int = Field(default=512, ge=1, le=100000)
    max_age_s: float = Field(default=86400 * 7, gt=0)
    max_attempts: int = Field(default=3, ge=1, le=10)
    timeout_wall_s: float = Field(default=5, gt=0, le=60)
    backoff_wall_s: float = Field(default=0.5, ge=0, le=10)
    shutdown_drain_wall_s: float = Field(default=5, ge=0, le=60)
    radiation_interval_s: float = Field(default=1, ge=1)
    spe_heartbeat_s: float = Field(default=1, ge=1)
    stand_test_start_s: float | None = Field(default=None, ge=0)
    il6_event_times_s: tuple[float, ...] = (0,)
    troponin_event_times_s: tuple[float, ...] = (0,)

    @field_validator("start")
    @classmethod
    def utc_start(cls, value: datetime) -> datetime:
        """Require explicit UTC mapping; host timezone must not change the run."""
        return Reading.utc_timestamp(value)

    @field_validator("base_url")
    @classmethod
    def http_destination(cls, value: str) -> str:
        """Only explicit HTTP destinations are valid; credentials belong in a header."""
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("base_url must be an HTTP(S) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("base_url cannot contain credentials, query or fragment")
        return value.rstrip("/")

    @model_validator(mode="after")
    def unique_owners(self) -> Settings:
        """Prevent duplicate crew streams and route errors before any network activity."""
        if len({p.id for p in self.crew}) != len(self.crew):
            raise ValueError("crew IDs must be unique")
        if any(day < 0 for day in self.exercise_test_days):
            raise ValueError("exercise test days cannot be negative")
        for instant in (*self.il6_event_times_s, *self.troponin_event_times_s):
            if not math.isfinite(instant) or instant < 0:
                raise ValueError("assay event times must be finite and nonnegative")
        if not self.data_route.startswith("/") or self.data_route.startswith("//"):
            raise ValueError("data_route must be a path beginning with one slash")
        if "{" in self.data_route or "}" in self.data_route:
            raise ValueError("data_route is shared by all readings and cannot contain placeholders")
        return self


class Observation(FrozenModel):
    """RAM-only delivery item; metadata is sent as headers, never added to the body."""

    reading: Reading
    scope: Literal["crew", "environment"]
    owner: str
    sensor_id: str
    sequence: int
    acquired_s: float
    available_s: float
    window_s: float = 0
    sample_kind: Literal["startup_baseline", "scheduled"] = "scheduled"

    @model_validator(mode="after")
    def timing(self) -> Observation:
        """Do not permit impossible result availability or non-finite model times."""
        for value in (self.acquired_s, self.available_s, self.window_s):
            if not math.isfinite(value) or value < 0:
                raise ValueError("observation times must be finite and nonnegative")
        if self.available_s < self.acquired_s:
            raise ValueError("result cannot precede collection")
        return self
