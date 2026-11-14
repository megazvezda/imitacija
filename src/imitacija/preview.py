"""Opt-in localhost JSON inspection using bounded latest-value state in RAM only."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import httpx

from .clock import Clock, timestamp
from .models import FrozenModel, Observation, Reading, Settings
from .registry import CHANNELS, dictionary


class PreviewEntry(FrozenModel):
    """Inspection context surrounds the exact four-field would-be POST body."""

    scope: str
    owner: str
    unit: str
    source_value: float | bool
    source_unit: str
    baseline_source_value: float | None = None
    window_s: float
    sample_kind: str
    reading: Reading


class Snapshot(FrozenModel):
    """A browser refresh returns current values, never an expanding history."""

    mode: str = "preview"
    readings: tuple[PreviewEntry, ...]
    run_id: str
    crew_ids: tuple[str, ...]
    simulation_time: datetime
    speed: float


class PreviewState:
    """Only one delivered result per owner/channel crosses the server-thread boundary."""

    def __init__(self, settings: Settings) -> None:
        self.lock = threading.Lock()
        self.run_id = uuid.uuid4().hex
        self.settings = settings
        self.clock: Clock | None = None
        self.latest: dict[tuple[str, str], Observation] = {}
        self.dictionary_json = (
            dictionary(settings.environment, settings.lab_delay_s, settings)
            .model_dump_json(indent=2)
            .encode()
        )
        self.url = ""

    def record(self, observation: Observation) -> None:
        """A late laboratory arrival must not replace a newer collection."""
        key = (observation.owner, observation.reading.channel)
        with self.lock:
            old = self.latest.get(key)
            if old is None or observation.acquired_s >= old.acquired_s:
                self.latest[key] = observation

    def baseline(self, observation: Observation) -> float | None:
        """Configured synthetic references; never infer total body water or edema."""
        profile = next((p for p in self.settings.crew if p.id == observation.owner), None)
        if observation.scope != "crew" or profile is None:
            return None
        references = {
            "body_mass": profile.mass_kg,
            "sweat_rate": profile.sweat_reference_rate_l_h,
            "sweat_sodium_concentration": profile.sweat_reference_sodium_mmol_l,
            "sweat_sodium_flux": profile.sweat_reference_rate_l_h
            * profile.sweat_reference_sodium_mmol_l,
        }
        return references.get(observation.reading.channel)

    def snapshot(self) -> bytes:
        """Copy a bounded immutable snapshot under the lock, then serialize outside it."""
        with self.lock:
            observations = tuple(self.latest.values())
        return (
            Snapshot(
                run_id=self.run_id,
                crew_ids=tuple(profile.id for profile in self.settings.crew),
                simulation_time=timestamp(
                    self.settings.start, self.clock.now() if self.clock else 0
                ),
                speed=self.settings.speed,
                readings=tuple(
                    PreviewEntry(
                        scope=o.scope,
                        owner=o.owner,
                        unit=o.reading.unit,
                        source_unit=CHANNELS[o.reading.channel].source_unit,
                        baseline_source_value=self.baseline(o),
                        source_value=(
                            o.reading.value
                            if isinstance(o.reading.value, bool)
                            else (o.reading.value - CHANNELS[o.reading.channel].offset)
                            / CHANNELS[o.reading.channel].factor
                        ),
                        window_s=o.window_s,
                        sample_kind=o.sample_kind,
                        reading=o.reading,
                    )
                    for o in sorted(
                        observations,
                        key=lambda item: (item.scope, item.owner, item.reading.channel),
                    )
                ),
            )
            .model_dump_json(indent=2)
            .encode()
        )


class PreviewTransport:
    """Replace outbound HTTP only when --preview is explicitly selected.

    Delivery still enforces specimen availability, communication delay and the bounded
    queue. A result becomes visible when it would become eligible for backend delivery.
    """

    def __init__(self, state: PreviewState) -> None:
        self.state = state

    async def post(
        self,
        path: str,
        observation: Observation,
        headers: dict[str, str],
    ) -> httpx.Response:
        """Accept a result locally without opening an outbound connection."""
        self.state.record(observation)
        return httpx.Response(204)


@contextmanager
def serve(settings: Settings, port: int) -> Iterator[PreviewState]:
    """Expose read-only JSON on IPv4 loopback for this preview process's lifetime."""
    state = PreviewState(settings)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            """Return latest readings or static dictionary; avoid browser/disk caching."""
            path = urlsplit(self.path).path
            content_type = "application/json; charset=utf-8"
            if path in {"/", "/readings", "/json"}:
                payload = state.snapshot()
            elif path == "/dictionary":
                payload = state.dictionary_json
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            """Browsing must not log measurement payloads or URLs."""

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    state.url = f"http://localhost:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)
        state.latest.clear()
