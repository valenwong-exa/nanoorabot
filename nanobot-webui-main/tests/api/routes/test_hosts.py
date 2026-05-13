import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from webui.api.routes import hosts


def _inventory_file(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    inventory_path = workspace / "skills" / "linux-inventory" / "linux-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    return workspace, inventory_path


@pytest.mark.asyncio
async def test_refresh_inventory_hosts_updates_runtime_status_and_persists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, inventory_path = _inventory_file(tmp_path)
    inventory_path.write_text(
        json.dumps(
            {
                "host_inventory": [
                    {
                        "host_name": "db1",
                        "ip": "10.0.0.1",
                        "databases": [
                            {"database_name": "AIDB"},
                            {"database_name": "VECTORDB"},
                        ],
                    },
                    {"host_name": "db2", "ip": "10.0.0.2", "databases": [{"database_name": "orcl"}]},
                    {"host_name": "db3", "ip": "10.0.0.3", "databases": [{"database_name": "orcl"}]},
                ]
            }
        ),
        encoding="utf-8",
    )

    async def fake_probe(host: dict[str, str], _workspace: Path) -> tuple[str, list[str]]:
        mapping = {
            "db1": (hosts.HOST_STATUS_RUNNING, ["RUNNING", hosts.DATABASE_STATUS_INVALID]),
            "db2": (hosts.HOST_STATUS_UNABLE_LOGIN, [hosts.DATABASE_STATUS_INVALID]),
            "db3": (hosts.HOST_STATUS_INVALID, [hosts.DATABASE_STATUS_INVALID]),
        }
        return mapping[host["host_name"]]

    monkeypatch.setattr(hosts, "_probe_host_runtime", fake_probe)

    refreshed = await hosts._refresh_inventory_hosts(workspace, inventory_path)

    assert [host["host_status"] for host in refreshed] == [
        hosts.HOST_STATUS_RUNNING,
        hosts.HOST_STATUS_UNABLE_LOGIN,
        hosts.HOST_STATUS_INVALID,
    ]
    assert refreshed[0]["databases"][0]["database_status"] == "RUNNING"
    assert refreshed[0]["databases"][1]["database_status"] == hosts.DATABASE_STATUS_INVALID
    assert [host["databases"][0]["database_status"] for host in refreshed[1:]] == [
        hosts.DATABASE_STATUS_INVALID,
        hosts.DATABASE_STATUS_INVALID,
    ]

    saved = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert [host["host_status"] for host in saved["host_inventory"]] == [
        hosts.HOST_STATUS_RUNNING,
        hosts.HOST_STATUS_UNABLE_LOGIN,
        hosts.HOST_STATUS_INVALID,
    ]
    assert saved["host_inventory"][0]["databases"][0]["database_status"] == "RUNNING"
    assert saved["host_inventory"][0]["databases"][1]["database_status"] == hosts.DATABASE_STATUS_INVALID
    assert [host["databases"][0]["database_status"] for host in saved["host_inventory"][1:]] == [
        hosts.DATABASE_STATUS_INVALID,
        hosts.DATABASE_STATUS_INVALID,
    ]


def test_normalise_hosts_adds_unknown_status_when_missing() -> None:
    payload = {
        "host_inventory": [
            {"host_name": "db1", "ip": "10.0.0.1", "databases": [{"database_name": "orcl"}]},
            {
                "host_name": "db2",
                "ip": "10.0.0.2",
                "host_status": hosts.HOST_STATUS_RUNNING,
                "databases": [{"database_name": "orcl", "database_status": "OPEN"}],
            },
        ]
    }

    normalised = hosts._normalise_hosts(payload)

    assert normalised[0]["host_status"] == hosts.HOST_STATUS_UNKNOWN
    assert normalised[1]["host_status"] == hosts.HOST_STATUS_RUNNING
    assert normalised[0]["databases"][0]["database_status"] == hosts.DATABASE_STATUS_UNKNOWN
    assert normalised[1]["databases"][0]["database_status"] == "OPEN"


@pytest.mark.asyncio
async def test_host_inventory_refresh_job_updates_config_and_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    persisted: dict[str, object] = {}

    monkeypatch.setattr(
        hosts,
        "get_host_inventory_refresh",
        lambda: {"enabled": False, "interval_minutes": 1},
    )
    monkeypatch.setattr(hosts, "set_host_inventory_refresh", lambda cfg: persisted.update(cfg))

    workspace, inventory_path = _inventory_file(tmp_path)
    inventory_path.write_text(json.dumps({"host_inventory": []}), encoding="utf-8")
    started = asyncio.Event()
    release = asyncio.Event()

    async def fake_refresh_inventory_hosts(_workspace: Path, _inventory_path: Path) -> list[dict]:
        started.set()
        await release.wait()
        return []

    monkeypatch.setattr(hosts, "_refresh_inventory_hosts", fake_refresh_inventory_hosts)

    svc = SimpleNamespace(
        config=SimpleNamespace(
            agents=SimpleNamespace(
                defaults=SimpleNamespace(workspace=str(workspace))
            )
        )
    )

    job = hosts.HostInventoryRefreshJob(svc)
    snapshot = await job.update_config(enabled=True, interval_minutes=5)

    assert persisted == {"enabled": True, "interval_minutes": 5}
    assert snapshot.enabled is True
    assert snapshot.intervalMinutes == 5

    refresh_task = asyncio.create_task(job.refresh_now())
    await started.wait()
    running_snapshot = job.snapshot()
    assert running_snapshot.isRunning is True

    release.set()
    await refresh_task

    await job.stop()
