import json
from pathlib import Path

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
                    {"host_name": "db1", "ip": "10.0.0.1", "databases": [{"database_name": "orcl"}]},
                    {"host_name": "db2", "ip": "10.0.0.2", "databases": [{"database_name": "orcl"}]},
                    {"host_name": "db3", "ip": "10.0.0.3", "databases": [{"database_name": "orcl"}]},
                ]
            }
        ),
        encoding="utf-8",
    )

    async def fake_probe(host: dict[str, str], _workspace: Path) -> tuple[str, str]:
        mapping = {
            "db1": (hosts.HOST_STATUS_RUNNING, "OPEN"),
            "db2": (hosts.HOST_STATUS_UNABLE_LOGIN, hosts.DATABASE_STATUS_INVALID),
            "db3": (hosts.HOST_STATUS_INVALID, hosts.DATABASE_STATUS_INVALID),
        }
        return mapping[host["host_name"]]

    monkeypatch.setattr(hosts, "_probe_host_runtime", fake_probe)

    refreshed = await hosts._refresh_inventory_hosts(workspace, inventory_path)

    assert [host["host_status"] for host in refreshed] == [
        hosts.HOST_STATUS_RUNNING,
        hosts.HOST_STATUS_UNABLE_LOGIN,
        hosts.HOST_STATUS_INVALID,
    ]
    assert [host["databases"][0]["database_status"] for host in refreshed] == [
        "OPEN",
        hosts.DATABASE_STATUS_INVALID,
        hosts.DATABASE_STATUS_INVALID,
    ]

    saved = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert [host["host_status"] for host in saved["host_inventory"]] == [
        hosts.HOST_STATUS_RUNNING,
        hosts.HOST_STATUS_UNABLE_LOGIN,
        hosts.HOST_STATUS_INVALID,
    ]
    assert [host["databases"][0]["database_status"] for host in saved["host_inventory"]] == [
        "OPEN",
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
