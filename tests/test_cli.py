"""Test the actual worker against a local HTTP receiver without retaining telemetry."""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from imitacija.main import run
from imitacija.models import Settings


def test_real_http_worker_posts_to_local_backend(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    received: list[dict[str, object]] = []

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers["Content-Length"]))
            received.append(
                {
                    "path": self.path,
                    "body": json.loads(body),
                    "scope": self.headers["X-Simulation-Scope"],
                    "owner": self.headers["X-Owner-ID"],
                    "sample_kind": self.headers["X-Sample-Kind"],
                }
            )
            self.send_response(204)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            # The real backend owns storage. This test receiver is intentionally RAM-only.
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        asyncio.run(
            run(
                Settings(
                    base_url=f"http://127.0.0.1:{server.server_port}",
                    data_route="/api/data",
                    enabled_channels=("heart_rate", "ambient_ppco2", "troponin_i"),
                    lab_delay_s=86400,
                    speed=20,
                    duration_s=8,
                    shutdown_drain_wall_s=2,
                )
            )
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert len(received) >= 5
    assert {r["scope"] for r in received} == {"crew", "environment"}
    assert {r["path"] for r in received} == {"/api/data"}
    assert {(r["scope"], r["owner"]) for r in received} == {
        ("crew", "crew-1"),
        ("environment", "iss_cabin"),
    }
    startup = [r for r in received if r["sample_kind"] == "startup_baseline"]
    assert {r["body"]["channel"] for r in startup} == {"heart_rate", "ambient_ppco2", "troponin_i"}
    for result in received:
        assert set(result["body"]) == {"channel", "value", "unit", "measured_at"}
        assert result["body"]["unit"]

    assert list(tmp_path.iterdir()) == []  # Production worker creates no local telemetry files.
    logs = capsys.readouterr()
    assert logs.out == ""
    assert "measured_at" not in logs.err and "Authorization" not in logs.err


def test_preview_serves_json_without_backend_posts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from collections.abc import Iterator
    from contextlib import contextmanager

    import httpx

    import imitacija.main as cli
    from imitacija.delivery import HttpTransport
    from imitacija.preview import PreviewState, serve

    monkeypatch.chdir(tmp_path)
    states: list[PreviewState] = []

    @contextmanager
    def capture(settings: Settings, port: int) -> Iterator[PreviewState]:
        with serve(settings, port) as state:
            states.append(state)
            yield state

    async def forbidden_post(*args: object, **kwargs: object) -> None:
        raise AssertionError("preview attempted an outbound backend request")

    monkeypatch.setattr(cli, "serve", capture)
    monkeypatch.setattr(HttpTransport, "post", forbidden_post)

    async def scenario() -> None:
        worker = asyncio.create_task(
            cli.run(
                Settings(
                    enabled_channels=("heart_rate", "ambient_ppco2", "troponin_i"),
                    speed=200,
                    duration_s=400,
                    lab_delay_s=1000,
                    shutdown_drain_wall_s=0.01,
                ),
                preview_port=0,
            )
        )
        try:
            while not states:
                await asyncio.sleep(0.01)
            async with httpx.AsyncClient(trust_env=False) as client:
                root = await client.get(states[0].url)
                assert "application/json" in root.headers["Content-Type"]
                assert root.json()["mode"] == "preview"
                for removed in ("dashboard.js", "dashboard.css", "dashboard.html"):
                    assert (await client.get(states[0].url + "/" + removed)).status_code == 404
                response = await client.get(states[0].url + "/readings")
                assert response.status_code == 200
                assert response.headers["Cache-Control"] == "no-store"
                snapshot = response.json()
                assert snapshot["mode"] == "preview"
                for _ in range(50):
                    if len(snapshot["readings"]) >= 3:
                        break
                    await asyncio.sleep(0.02)
                    snapshot = (await client.get(states[0].url + "/readings")).json()
                entries = snapshot["readings"]
                assert {entry["reading"]["channel"] for entry in entries} == {
                    "heart_rate",
                    "ambient_ppco2",
                    "troponin_i",
                }  # Startup fixtures are available even when future lab results are delayed.
                troponin = next(e for e in entries if e["reading"]["channel"] == "troponin_i")
                assert troponin["sample_kind"] == "startup_baseline"
                assert troponin["window_s"] == 0
                assert {entry["scope"] for entry in entries} == {"crew", "environment"}
                assert snapshot["speed"] == 200
                assert snapshot["crew_ids"] == ["crew-1"]
                heart = next(e for e in entries if e["reading"]["channel"] == "heart_rate")
                assert heart["source_value"] == pytest.approx(heart["reading"]["value"] * 60)
                assert heart["source_unit"] == "bpm"
                assert heart["reading"]["unit"] == heart["unit"] == "s^-1"
                assert all(
                    set(entry["reading"]) == {"channel", "value", "unit", "measured_at"}
                    for entry in entries
                )
                metadata = (await client.get(states[0].url + "/dictionary")).json()
                assert len(metadata["channels"]) == 29
                assert (await client.get(states[0].url + "/missing")).status_code == 404
            await worker
        finally:
            if not worker.done():
                worker.cancel()
                await asyncio.gather(worker, return_exceptions=True)
        assert states[0].latest == {}
        assert list(tmp_path.iterdir()) == []

    asyncio.run(scenario())
