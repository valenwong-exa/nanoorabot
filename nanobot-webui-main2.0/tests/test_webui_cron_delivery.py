from __future__ import annotations

import sys
from pathlib import Path

import pytest

NANOBOT_ROOT = Path(__file__).resolve().parents[2] / "nanobot-main3.0"
if str(NANOBOT_ROOT) not in sys.path:
    sys.path.insert(0, str(NANOBOT_ROOT))

from nanobot.cron.types import CronJob, CronPayload
from webui.__main__ import _bound_websocket_cron_target, _push_bound_websocket_cron_result


def test_bound_websocket_cron_target_prefers_session_key() -> None:
    job = CronJob(
        id="job-1",
        name="Ping monitor",
        payload=CronPayload(
            message="ping host",
            session_key="web:42:abc12345",
            origin_channel="websocket",
            origin_chat_id="web:42:abc12345",
        ),
    )

    assert _bound_websocket_cron_target(job) == "web:42:abc12345"


def test_bound_websocket_cron_target_supports_admin_viewed_non_web_session() -> None:
    job = CronJob(
        id="job-2",
        name="Ping monitor",
        payload=CronPayload(
            message="ping host",
            session_key="cli:direct",
            origin_channel="websocket",
            origin_chat_id="cli:direct",
        ),
    )

    assert _bound_websocket_cron_target(job) == "cli:direct"


@pytest.mark.asyncio
async def test_push_bound_websocket_cron_result_uses_bound_session_key(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, dict]] = []

    async def _fake_push(target_key: str, payload: dict) -> None:
        captured.append((target_key, payload))

    monkeypatch.setattr("webui.api.routes.ws.push_cron_result", _fake_push)

    job = CronJob(
        id="job-3",
        name="Ping monitor",
        payload=CronPayload(
            message="ping host",
            session_key="web:42:abc12345",
            origin_channel="websocket",
            origin_chat_id="web:42:abc12345",
        ),
    )

    await _push_bound_websocket_cron_result(job, "host is reachable")

    assert captured == [
        (
            "web:42:abc12345",
            {
                "type": "cron_result",
                "job_id": "job-3",
                "job_name": "Ping monitor",
                "content": "host is reachable",
                "session_key": "web:42:abc12345",
            },
        )
    ]


@pytest.mark.asyncio
async def test_push_bound_websocket_cron_result_skips_non_websocket_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[str, dict]] = []

    async def _fake_push(target_key: str, payload: dict) -> None:
        captured.append((target_key, payload))

    monkeypatch.setattr("webui.api.routes.ws.push_cron_result", _fake_push)

    job = CronJob(
        id="job-4",
        name="External notify",
        payload=CronPayload(
            message="ping host",
            session_key="telegram:123",
            origin_channel="telegram",
            origin_chat_id="123",
        ),
    )

    await _push_bound_websocket_cron_result(job, "host is reachable")

    assert captured == []
