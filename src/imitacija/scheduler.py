"""Independent acquisition groups, calendar protocols and immutable result creation."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Literal, Protocol

from .clock import Clock, timestamp
from .frequency import FREQUENCIES
from .models import AstronautProfile, Observation, Reading, Settings
from .physiology import DAY, crew_values, environment_values, startup_crew_values
from .registry import CHANNELS, Channel
from .units import convert


class Sink(Protocol):
    """Nonblocking enqueue interface; sampling never awaits a network request."""

    def submit(self, observation: Observation) -> None:
        """Accept a result into bounded transient delivery state."""
        ...


@dataclass(frozen=True)
class Rule:
    """Periodic or sparse protocol rule; paired channels share one acquisition rule."""

    group: str
    phase: float = 0
    interval: float | None = None
    points: tuple[float, ...] = ()
    repeat: float | None = None
    end: float | None = None
    active_only: bool = False
    burst_start: float | None = None

    def next_after(self, t: float) -> float | None:
        """Find a strictly later event in O(number of protocol points), without history."""
        if self.interval is not None:
            # Anchor to the group's phase instead of accumulating CPU/transport drift.
            step = max(0, math.floor((t - self.phase + 1e-8) / self.interval) + 1)
            result = self.phase + step * self.interval
            if self.burst_start is not None:
                burst_end = self.burst_start + 180
                burst_step = max(0, math.floor((t - self.burst_start + 1e-8) / 0.1) + 1)
                burst = self.burst_start + burst_step * 0.1
                if burst < burst_end - 1e-8:
                    result = min(result, burst)
            if self.active_only:
                # The healthy routine's Gaussian activity is >.05 only during this
                # daily interval. Skip resting time entirely; no 1Hz dry-patch polling.
                span = math.sqrt(-math.log(0.05))
                day = math.floor(result / DAY)
                lower = day * DAY + (17.5 - 0.4 * span) * 3600 + 1
                upper = day * DAY + (17.5 + 0.65 * span) * 3600
                if result < lower:
                    result = math.ceil(lower / self.interval) * self.interval
                elif result >= upper:
                    result = math.ceil((lower + DAY) / self.interval) * self.interval
            return result if self.end is None or result < self.end else None
        candidates: list[float] = []
        for point in self.points:
            candidate = point
            if self.repeat is not None and candidate <= t:
                candidate += (math.floor((t - point) / self.repeat) + 1) * self.repeat
            if candidate > t:
                candidates.append(candidate)
        return min(candidates) if candidates else None


def rules(settings: Settings) -> tuple[Rule, ...]:
    """Use NASA-informed demo schedules, not the superseded biochemical polling loop."""
    tests = tuple(
        sorted(
            {
                0.0,
                *(day * DAY + 17 * 3600 for day in settings.exercise_test_days),
                *(
                    day * DAY + 18 * 3600 + minute * 60
                    for day in settings.exercise_test_days
                    for minute in (5, 15, 30)
                ),
            }
        )
    )

    def periodic(group: str, phase: float = 0, *, active: bool = False) -> Rule:
        """Use the same matrix policy that supplies public dictionary metadata."""
        return Rule(group, phase=phase, interval=FREQUENCIES[group].interval_s, active_only=active)

    bp_end = (
        None
        if settings.bp_session_duration_s is None
        else settings.bp_session_start_s + settings.bp_session_duration_s
    )
    return (
        periodic("heart", 60),
        periodic("hrv", 61),
        periodic("respiration", 77),
        periodic("spo2", 0.2),
        periodic("temperature", 0.4),
        periodic("glucose", 343),
        periodic("sweat", active=True),
        periodic("sweat_summary", active=True),
        Rule(
            "bp",
            phase=settings.bp_session_start_s,
            interval=3600,
            end=bp_end,
            burst_start=settings.stand_test_start_s,
        ),
        Rule("troponin", points=settings.troponin_event_times_s),
        Rule("lactate", points=tests),
        Rule("vitamin", points=(0,), repeat=30 * DAY),
        Rule("cortisol", points=tuple(h * 3600 for h in (7, 11, 15, 19, 23)), repeat=DAY),
        Rule("il6", points=settings.il6_event_times_s),
        Rule("ntx", points=(7 * DAY,), repeat=7 * DAY),
        Rule("urine", points=(DAY,), repeat=DAY),
        Rule("mass", points=(7 * 3600, 18.5 * 3600), repeat=DAY),
        Rule("usg", points=(7 * 3600, 18.5 * 3600), repeat=DAY),
        Rule("saliva_pcr", points=(9 * 3600,), repeat=2 * DAY),
        Rule("urine_pcr", points=(10 * 3600,), repeat=2 * DAY),
        periodic("co2"),
        periodic("light", 0.6),
        Rule("radiation", interval=settings.radiation_interval_s),
        periodic("radiation_dose", 60),
        Rule("spe", phase=0.8, interval=settings.spe_heartbeat_s),
    )


@dataclass(order=True)
class Event:
    """Sequence breaks heap ties without comparing owner/model objects."""

    due: float
    order: int
    rule: Rule = field(compare=False)
    scope: Literal["crew", "environment"] = field(compare=False)
    owner: str = field(compare=False)


class Scheduler:
    """A single small heap owns collection clocks; HTTP cannot block acquisition."""

    def __init__(self, settings: Settings, clock: Clock, sink: Sink) -> None:
        self.settings, self.clock, self.sink = settings, clock, sink
        self.profiles = {p.id: p for p in settings.crew}
        self.enabled = set(settings.enabled_channels or CHANNELS)
        if settings.enabled_channels == ():
            self.enabled = set()
        if unknown := self.enabled - CHANNELS.keys():
            raise ValueError(f"unknown enabled channels: {sorted(unknown)}")
        self.events: list[Event] = []
        self.counter = 0
        self.sequences: dict[tuple[str, str], int] = {}
        self.generated = 0
        self.started = False
        for rule in rules(settings):
            members = [
                c for c in CHANNELS.values() if c.group == rule.group and c.id in self.enabled
            ]
            if not members:
                continue
            scope = members[0].scope
            owners = tuple(self.profiles) if scope == "crew" else (settings.environment.id,)
            for owner in owners:
                due = rule.next_after(0)
                if due is not None:
                    self._push(due, rule, scope, owner)

    def _push(
        self, due: float, rule: Rule, scope: Literal["crew", "environment"], owner: str
    ) -> None:
        """One next event per owner/group bounds schedule memory independently of run length."""
        self.counter += 1
        heapq.heappush(self.events, Event(due, self.counter, rule, scope, owner))

    def acquire(self, event: Event, instant: float) -> None:
        """Create result values at actual acquisition time; late polls coalesce, never replay."""
        profile: AstronautProfile | None = (
            self.profiles.get(event.owner) if event.scope == "crew" else None
        )
        values = (
            crew_values(event.rule.group, instant, profile, self.settings.seed)
            if profile is not None
            else environment_values(
                event.rule.group, instant, self.settings.environment, self.settings.seed
            )
        )
        for name, value in values.items():
            if name not in self.enabled:
                continue
            c = CHANNELS[name]
            # Rate and integrated dose share a latent radiation model but have
            # independent publication clocks. Never emit the sibling on this tick.
            if c.group != event.rule.group:
                continue
            self._publish(c, value, event.owner, event.scope, instant)

    def _publish(
        self,
        channel: Channel,
        value: float | bool,
        owner: str,
        scope: Literal["crew", "environment"],
        instant: float,
        *,
        startup: bool = False,
    ) -> None:
        """Convert once and enqueue immutable data with explicit sampling provenance."""
        key = (owner, channel.id)
        sequence = self.sequences.get(key, 0) + 1
        self.sequences[key] = sequence
        wire_value = (
            value if isinstance(value, bool) else convert(value, channel.factor, channel.offset)
        )
        reading = Reading(
            channel=channel.id,
            value=wire_value,
            unit=channel.unit,
            measured_at=timestamp(self.settings.start, instant),
        )
        # Startup fixtures are already available profile values, not a newly drawn
        # laboratory specimen. Communication delay still applies to their delivery.
        lab_delay = self.settings.lab_delay_s if channel.lab and not startup else 0
        self.sink.submit(
            Observation(
                reading=reading,
                scope=scope,
                owner=owner,
                sensor_id=f"{owner}:{channel.group}",
                sequence=sequence,
                acquired_s=instant,
                available_s=instant + lab_delay + self.settings.environment.comm_delay_s,
                window_s=0 if startup else channel.window_s,
                sample_kind="startup_baseline" if startup else "scheduled",
            )
        )
        self.generated += 1

    def initialize(self) -> None:
        """Emit exactly one baseline per enabled owner/channel, once per worker run.

        Normal rules are anchored to their original phases and skip time zero,
        so channels that already had a baseline event do not emit a duplicate.
        Resuming this same scheduler never repeats initialization.
        """
        if self.started:
            return
        self.started = True
        for profile in self.settings.crew:
            values = startup_crew_values(profile, self.settings.seed)
            for channel in CHANNELS.values():
                if channel.scope == "crew" and channel.id in self.enabled:
                    self._publish(channel, values[channel.id], profile.id, "crew", 0, startup=True)
        environment = self.settings.environment
        values = {}
        for group in ("co2", "light", "radiation", "spe"):
            values.update(environment_values(group, 0, environment, self.settings.seed))
        for channel in CHANNELS.values():
            if channel.scope == "environment" and channel.id in self.enabled:
                self._publish(
                    channel, values[channel.id], environment.id, "environment", 0, startup=True
                )

    async def run(self, until: float | None = None) -> None:
        """Acquire until a finite logical duration or cancellation (continuous default)."""
        self.initialize()
        while self.events:
            event = self.events[0]
            if until is not None and event.due > until:
                await self.clock.sleep_until(until)
                return
            heapq.heappop(self.events)
            await self.clock.sleep_until(event.due)
            actual = self.clock.now()
            if until is not None and actual > until:
                return
            # A missed finite cuff session must not produce a cuff reading after its end.
            if event.rule.end is None or actual < event.rule.end:
                self.acquire(event, actual)
            if (next_due := event.rule.next_after(actual)) is not None:
                self._push(next_due, event.rule, event.scope, event.owner)
        if until is not None:
            await self.clock.sleep_until(until)
