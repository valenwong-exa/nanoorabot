import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from webui.api.routes import hosts


def _inventory_file(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    inventory_path = workspace / "skills" / "linux-inventory" / "linux-inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    return workspace, inventory_path


@pytest.mark.asyncio
async def test_refresh_inventory_payload_updates_host_and_database_runtime_status_and_persists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace, inventory_path = _inventory_file(tmp_path)
    inventory_path.write_text(
        json.dumps(
            {
                "database_inventory": [
                    {"database_name": "AIDB", "sqlcl_saveconnname": "aidemo"},
                    {"database_name": "ORCL", "sqlcl_saveconnname": "19cdb"},
                ],
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
    monkeypatch.setattr(
        hosts,
        "_refresh_database_inventory_entries",
        lambda databases: asyncio.sleep(0, result=[
            {**databases[0], "database_status": hosts.DATABASE_STATUS_RUNNING, "probe_output": "2026-05-22 10:00:54", "last_checked_at": "2026-05-22T10:00:54+00:00"},
            {**databases[1], "database_status": hosts.DATABASE_STATUS_INVALID, "last_checked_at": "2026-05-22T10:00:55+00:00"},
        ]),
    )

    refreshed_hosts, refreshed_databases = await hosts._refresh_inventory_payload(workspace, inventory_path)

    assert [host["host_status"] for host in refreshed_hosts] == [
        hosts.HOST_STATUS_RUNNING,
        hosts.HOST_STATUS_UNABLE_LOGIN,
        hosts.HOST_STATUS_INVALID,
    ]
    assert refreshed_hosts[0]["databases"][0]["database_status"] == "RUNNING"
    assert refreshed_hosts[0]["databases"][1]["database_status"] == hosts.DATABASE_STATUS_INVALID
    assert [host["databases"][0]["database_status"] for host in refreshed_hosts[1:]] == [
        hosts.DATABASE_STATUS_INVALID,
        hosts.DATABASE_STATUS_INVALID,
    ]
    assert [database["database_status"] for database in refreshed_databases] == [
        hosts.DATABASE_STATUS_RUNNING,
        hosts.DATABASE_STATUS_INVALID,
    ]
    assert refreshed_databases[0]["probe_output"] == "2026-05-22 10:00:54"

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
    assert [database["database_status"] for database in saved["database_inventory"]] == [
        hosts.DATABASE_STATUS_RUNNING,
        hosts.DATABASE_STATUS_INVALID,
    ]
    assert saved["database_inventory"][0]["probe_output"] == "2026-05-22 10:00:54"


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


def test_normalise_database_inventory_adds_unknown_status_when_missing() -> None:
    payload = {
        "database_inventory": [
            {"database_name": "AIDB", "sqlcl_saveconnname": "aidemo"},
            {"database_name": "ORCL", "database_status": hosts.DATABASE_STATUS_RUNNING},
        ]
    }

    normalised = hosts._normalise_database_inventory(payload)

    assert normalised[0]["database_status"] == hosts.DATABASE_STATUS_UNKNOWN
    assert normalised[1]["database_status"] == hosts.DATABASE_STATUS_RUNNING


@pytest.mark.asyncio
async def test_probe_saved_connection_database_uses_sqlcl_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hosts, "_build_sqlcl_probe_command", lambda connection_name: ["cmd", "/c", "sqlcl2db.bat", connection_name])

    async def fake_run_command_capture(_command: list[str], timeout: float) -> tuple[bool, str, str]:
        assert timeout == hosts.SQLCL_PROBE_TIMEOUT_SECONDS
        return True, "\n2026-05-22 10:00:54\n", ""

    monkeypatch.setattr(hosts, "_run_command_capture", fake_run_command_capture)

    status, output = await hosts._probe_saved_connection_database(
        {"database_name": "AIDB", "sqlcl_saveconnname": "aidemo"}
    )

    assert status == hosts.DATABASE_STATUS_RUNNING
    assert output == "2026-05-22 10:00:54"


@pytest.mark.asyncio
async def test_probe_saved_connection_database_marks_non_sysdate_output_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(hosts, "_build_sqlcl_probe_command", lambda connection_name: ["cmd", "/c", "sqlcl2db.bat", connection_name])

    async def fake_run_command_capture(_command: list[str], timeout: float) -> tuple[bool, str, str]:
        assert timeout == hosts.SQLCL_PROBE_TIMEOUT_SECONDS
        return True, "连接失败\n", ""

    monkeypatch.setattr(hosts, "_run_command_capture", fake_run_command_capture)

    status, output = await hosts._probe_saved_connection_database(
        {"database_name": "ORCL", "sqlcl_saveconnname": "19cdb"}
    )

    assert status == hosts.DATABASE_STATUS_INVALID
    assert output == "连接失败"


@pytest.mark.asyncio
async def test_open_monitored_database_uses_sqlcl_saved_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_probe_saved_connection_database(database: dict[str, str]) -> tuple[str, str | None]:
        assert database["sqlcl_saveconnname"] == "aidemo"
        assert database["database_name"] == "AIDB"
        return hosts.DATABASE_STATUS_RUNNING, "2026-05-25 10:00:00"

    monkeypatch.setattr(hosts, "_probe_saved_connection_database", fake_probe_saved_connection_database)

    result = await hosts.open_monitored_database(
        hosts.DatabaseOpenProbeRequest(sqlcl_saveconnname="aidemo", database_name="AIDB"),
        _user={"username": "admin"},
    )

    assert result.success is True
    assert result.status == hosts.DATABASE_STATUS_RUNNING
    assert result.connectionName == "aidemo"
    assert result.databaseName == "AIDB"
    assert result.probeOutput == "2026-05-25 10:00:00"


@pytest.mark.asyncio
async def test_open_monitored_database_requires_saved_connection_name() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await hosts.open_monitored_database(
            hosts.DatabaseOpenProbeRequest(sqlcl_saveconnname="   ", database_name="AIDB"),
            _user={"username": "admin"},
        )

    assert exc_info.value.status_code == 400


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

    async def fake_refresh_inventory_payload(_workspace: Path, _inventory_path: Path) -> tuple[list[dict], list[dict]]:
        started.set()
        await release.wait()
        return [], []

    monkeypatch.setattr(hosts, "_refresh_inventory_payload", fake_refresh_inventory_payload)

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
