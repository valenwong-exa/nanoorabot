"""Host inventory routes."""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from webui.api.deps import get_current_user, get_services
from webui.api.gateway import ServiceContainer

router = APIRouter()

INVENTORY_RELATIVE_PATH = Path("skills") / "linux-inventory" / "linux-inventory.json"
HOST_STATUS_RUNNING = "Running"
HOST_STATUS_UNABLE_LOGIN = "unable login"
HOST_STATUS_INVALID = "invalid"
HOST_STATUS_UNKNOWN = "unknown"
DATABASE_STATUS_INVALID = "INVALID"
DATABASE_STATUS_UNKNOWN = "UNKNOWN"


def _inventory_path_for_workspace(workspace: Path) -> Path:
    return workspace / INVENTORY_RELATIVE_PATH


def _load_inventory_payload(inventory_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid linux inventory JSON: {exc}",
        ) from exc

    hosts = payload.get("host_inventory", [])
    if not isinstance(hosts, list):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid linux inventory structure: host_inventory must be a list",
        )
    return payload


def _normalise_hosts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    hosts = payload.get("host_inventory", [])
    result: list[dict[str, Any]] = []
    for host in hosts:
        if isinstance(host, dict):
            item = dict(host)
            item.setdefault("host_status", HOST_STATUS_UNKNOWN)
            databases = item.get("databases", [])
            if isinstance(databases, list):
                normalised_databases: list[dict[str, Any]] = []
                for database in databases:
                    if isinstance(database, dict):
                        db_item = dict(database)
                        db_item.setdefault("database_status", DATABASE_STATUS_UNKNOWN)
                        normalised_databases.append(db_item)
                item["databases"] = normalised_databases
            result.append(item)
    return result


def _write_inventory_payload(inventory_path: Path, payload: dict[str, Any]) -> None:
    inventory_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


async def _run_command(command: list[str], timeout: float) -> bool:
    ok, _, _ = await _run_command_capture(command, timeout=timeout)
    return ok


async def _run_command_capture(command: list[str], timeout: float) -> tuple[bool, str, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError:
        return False, "", ""

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        return False, "", ""
    return proc.returncode == 0, stdout.decode("utf-8", errors="ignore"), stderr.decode("utf-8", errors="ignore")


async def _ping_host(ip: str) -> bool:
    if not ip:
        return False
    if sys.platform.startswith("win"):
        command = ["ping", "-n", "1", "-w", "3000", ip]
    else:
        command = ["ping", "-c", "1", "-W", "3", ip]
    return await _run_command(command, timeout=5.0)


def _resolve_ssh_executable() -> str | None:
    openssh_home = os.environ.get("OPENSSH_HOME", "").strip()
    if openssh_home:
        ssh_path = Path(openssh_home).expanduser() / "ssh.exe"
        if ssh_path.exists():
            return str(ssh_path)
    return shutil.which("ssh")


def _build_ssh_command(host: dict[str, Any], workspace: Path, remote_command: str) -> list[str] | None:
    ssh_exec = _resolve_ssh_executable()
    ip = str(host.get("ip", "")).strip()
    user = str(host.get("default_user", "")).strip()
    key_value = str(host.get("ssh_key", "")).strip()
    if not ssh_exec or not ip or not user or not key_value:
        return None

    key_path = Path(key_value).expanduser()
    if not key_path.is_absolute():
        key_path = (workspace / key_path).resolve()
    if not key_path.exists():
        return None

    return [
        ssh_exec,
        "-i",
        str(key_path),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null" if not sys.platform.startswith("win") else "UserKnownHostsFile=NUL",
        "-o",
        "ConnectTimeout=5",
        f"{user}@{ip}",
        remote_command,
    ]


async def _run_ssh_command(host: dict[str, Any], workspace: Path, remote_command: str, timeout: float) -> tuple[bool, str, str]:
    command = _build_ssh_command(host, workspace, remote_command)
    if command is None:
        return False, "", ""
    return await _run_command_capture(command, timeout=timeout)


async def _ssh_date_check(host: dict[str, Any], workspace: Path) -> bool:
    ok, _, _ = await _run_ssh_command(host, workspace, "date", timeout=10.0)
    return ok


def _database_shell_command(ssh_user: str) -> str:
    sql_script = (
        "printf 'set heading off\n"
        "set feedback off\n"
        "set pagesize 0\n"
        "set verify off\n"
        "set echo off\n"
        "select status from v$instance;\n"
        "exit\n' | sqlplus -s '/ as sysdba' | xargs"
    )
    if ssh_user.lower() == "oracle":
        return f"bash -lc {shlex.quote(sql_script)}"
    return f"sudo -iu oracle bash -lc {shlex.quote(sql_script)}"


def _parse_database_status(ok: bool, stdout: str, stderr: str) -> str:
    combined = f"{stdout}\n{stderr}".strip()
    lowered = combined.lower()
    if not ok or not combined:
        return DATABASE_STATUS_INVALID
    if "ora-" in lowered or "sp2-" in lowered or "idle instance" in lowered or "error" in lowered:
        return DATABASE_STATUS_INVALID

    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        return DATABASE_STATUS_INVALID
    return lines[-1].upper()


async def _probe_database_status(host: dict[str, Any], workspace: Path) -> str:
    ssh_user = str(host.get("default_user", "")).strip() or "oracle"
    remote_command = _database_shell_command(ssh_user)
    ok, stdout, stderr = await _run_ssh_command(host, workspace, remote_command, timeout=20.0)
    return _parse_database_status(ok, stdout, stderr)


def _apply_database_status(host: dict[str, Any], database_status: str) -> dict[str, Any]:
    updated = dict(host)
    databases = updated.get("databases", [])
    if not isinstance(databases, list):
        updated["databases"] = []
        return updated

    updated_databases: list[dict[str, Any]] = []
    for database in databases:
        if isinstance(database, dict):
            db_item = dict(database)
            db_item["database_status"] = database_status
            updated_databases.append(db_item)
    updated["databases"] = updated_databases
    return updated


async def _probe_host_status(host: dict[str, Any], workspace: Path) -> str:
    ip = str(host.get("ip", "")).strip()
    if not await _ping_host(ip):
        return HOST_STATUS_INVALID
    if await _ssh_date_check(host, workspace):
        return HOST_STATUS_RUNNING
    return HOST_STATUS_UNABLE_LOGIN


async def _probe_host_runtime(host: dict[str, Any], workspace: Path) -> tuple[str, str]:
    host_status = await _probe_host_status(host, workspace)
    if host_status != HOST_STATUS_RUNNING:
        return host_status, DATABASE_STATUS_INVALID
    return host_status, await _probe_database_status(host, workspace)


async def _refresh_inventory_hosts(workspace: Path, inventory_path: Path) -> list[dict[str, Any]]:
    payload = _load_inventory_payload(inventory_path)
    hosts = _normalise_hosts(payload)

    updated_hosts: list[dict[str, Any]] = []
    for host in hosts:
        updated = dict(host)
        host_status, database_status = await _probe_host_runtime(updated, workspace)
        updated["host_status"] = host_status
        updated = _apply_database_status(updated, database_status)
        updated_hosts.append(updated)

    payload["host_inventory"] = updated_hosts
    _write_inventory_payload(inventory_path, payload)
    return updated_hosts


def _build_inventory_response(workspace: Path, inventory_path: Path, hosts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "workspace": str(workspace),
        "inventory_path": str(inventory_path),
        "exists": True,
        "hosts": hosts,
    }


@router.get("/inventory")
async def get_host_inventory(
    _user: Annotated[dict, Depends(get_current_user)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict[str, Any]:
    workspace = Path(svc.config.agents.defaults.workspace).expanduser()
    inventory_path = _inventory_path_for_workspace(workspace)

    if not inventory_path.exists():
        return {
            "workspace": str(workspace),
            "inventory_path": str(inventory_path),
            "exists": False,
            "hosts": [],
        }

    payload = _load_inventory_payload(inventory_path)
    return _build_inventory_response(workspace, inventory_path, _normalise_hosts(payload))


@router.post("/inventory/refresh")
async def refresh_host_inventory(
    _user: Annotated[dict, Depends(get_current_user)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict[str, Any]:
    workspace = Path(svc.config.agents.defaults.workspace).expanduser()
    inventory_path = _inventory_path_for_workspace(workspace)

    if not inventory_path.exists():
        return {
            "workspace": str(workspace),
            "inventory_path": str(inventory_path),
            "exists": False,
            "hosts": [],
        }

    hosts = await _refresh_inventory_hosts(workspace, inventory_path)
    return _build_inventory_response(workspace, inventory_path, hosts)
