"""Host inventory routes."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shlex
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger

from webui.api.deps import get_current_user, get_services
from webui.api.gateway import ServiceContainer
from webui.api.models import (
    HostInventoryRefreshConfigRequest,
    HostInventoryRefreshConfigResponse,
)
from webui.utils.webui_config import (
    get_host_inventory_refresh,
    set_host_inventory_refresh,
)

router = APIRouter()

INVENTORY_RELATIVE_PATH = Path("skills") / "linux-inventory" / "linux-inventory.json"
HOST_STATUS_RUNNING = "Running"
HOST_STATUS_UNABLE_LOGIN = "unable login"
HOST_STATUS_INVALID = "invalid"
HOST_STATUS_UNKNOWN = "unknown"
DATABASE_STATUS_INVALID = "INVALID"
DATABASE_STATUS_UNKNOWN = "UNKNOWN"
DEFAULT_REFRESH_INTERVAL_MINUTES = 1
MIN_REFRESH_INTERVAL_MINUTES = 1
MAX_REFRESH_INTERVAL_MINUTES = 1440


def _truncate_log_text(value: str, limit: int = 200) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}...(truncated)"


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


def _database_shell_command(database_name: str, ssh_user: str) -> str:
    pmon_name = f"ora_pmon_{database_name.strip()}".lower()
    shell_script = f"ps -eo comm= | grep -i -x -- {shlex.quote(pmon_name)}"
    if ssh_user.lower() == "oracle":
        return f"bash -lc {shlex.quote(shell_script)}"
    return f"sudo -iu oracle bash -lc {shlex.quote(shell_script)}"


def _parse_database_status(ok: bool, stdout: str, stderr: str) -> str:
    combined = f"{stdout}\n{stderr}".strip()
    if not ok or not combined:
        return DATABASE_STATUS_INVALID
    return "RUNNING"


async def _probe_database_status(
    host: dict[str, Any],
    workspace: Path,
    database: dict[str, Any],
) -> str:
    database_name = str(database.get("database_name", "")).strip()
    if not database_name:
        return DATABASE_STATUS_INVALID
    ssh_user = str(host.get("default_user", "")).strip() or "oracle"
    remote_command = _database_shell_command(database_name, ssh_user)
    ok, stdout, stderr = await _run_ssh_command(host, workspace, remote_command, timeout=20.0)
    database_status = _parse_database_status(ok, stdout, stderr)
    logger.info(
        "Host inventory PMON check host='{}' db='{}' command={} ok={} status={} stdout={} stderr={}",
        host.get("host_name", ""),
        database_name,
        remote_command,
        ok,
        database_status,
        _truncate_log_text(stdout),
        _truncate_log_text(stderr),
    )
    return database_status


def _apply_database_status(host: dict[str, Any], database_statuses: list[str]) -> dict[str, Any]:
    updated = dict(host)
    databases = updated.get("databases", [])
    if not isinstance(databases, list):
        updated["databases"] = []
        return updated

    updated_databases: list[dict[str, Any]] = []
    for index, database in enumerate(databases):
        if isinstance(database, dict):
            db_item = dict(database)
            db_item["database_status"] = (
                database_statuses[index]
                if index < len(database_statuses)
                else DATABASE_STATUS_INVALID
            )
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


async def _probe_host_runtime(host: dict[str, Any], workspace: Path) -> tuple[str, list[str]]:
    host_status = await _probe_host_status(host, workspace)
    databases = host.get("databases", [])
    database_entries = [database for database in databases if isinstance(database, dict)]
    if host_status != HOST_STATUS_RUNNING:
        return host_status, [DATABASE_STATUS_INVALID] * len(database_entries)

    database_statuses: list[str] = []
    for database in database_entries:
        database_statuses.append(await _probe_database_status(host, workspace, database))
    return host_status, database_statuses


async def _refresh_inventory_hosts(workspace: Path, inventory_path: Path) -> list[dict[str, Any]]:
    payload = _load_inventory_payload(inventory_path)
    hosts = _normalise_hosts(payload)

    updated_hosts: list[dict[str, Any]] = []
    for host in hosts:
        updated = dict(host)
        host_status, database_statuses = await _probe_host_runtime(updated, workspace)
        updated["host_status"] = host_status
        updated = _apply_database_status(updated, database_statuses)
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


def _missing_inventory_response(workspace: Path, inventory_path: Path) -> dict[str, Any]:
    return {
        "workspace": str(workspace),
        "inventory_path": str(inventory_path),
        "exists": False,
        "hosts": [],
    }


def _current_workspace(svc: ServiceContainer) -> Path:
    return Path(svc.config.agents.defaults.workspace).expanduser()


def _sanitise_interval_minutes(value: int | None) -> int:
    if value is None:
        return DEFAULT_REFRESH_INTERVAL_MINUTES
    return max(MIN_REFRESH_INTERVAL_MINUTES, min(MAX_REFRESH_INTERVAL_MINUTES, int(value)))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HostInventoryRefreshJob:
    def __init__(self, svc: ServiceContainer) -> None:
        self._svc = svc
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._enabled = False
        self._interval_minutes = DEFAULT_REFRESH_INTERVAL_MINUTES
        self._last_run_at: str | None = None
        self._last_success_at: str | None = None
        self._last_error: str | None = None
        self._load_config()

    def _load_config(self) -> None:
        cfg = get_host_inventory_refresh()
        self._enabled = bool(cfg.get("enabled", False))
        self._interval_minutes = _sanitise_interval_minutes(cfg.get("interval_minutes"))

    def _persist_config(self) -> None:
        set_host_inventory_refresh(
            {
                "enabled": self._enabled,
                "interval_minutes": self._interval_minutes,
            }
        )

    def snapshot(self) -> HostInventoryRefreshConfigResponse:
        return HostInventoryRefreshConfigResponse(
            enabled=self._enabled,
            intervalMinutes=self._interval_minutes,
            isRunning=self._lock.locked(),
            lastRunAt=self._last_run_at,
            lastSuccessAt=self._last_success_at,
            lastError=self._last_error,
        )

    async def start(self) -> None:
        self._load_config()
        await self._restart_loop()

    async def stop(self) -> None:
        await self._cancel_task()

    async def update_config(
        self,
        *,
        enabled: bool | None = None,
        interval_minutes: int | None = None,
    ) -> HostInventoryRefreshConfigResponse:
        if enabled is not None:
            self._enabled = enabled
        if interval_minutes is not None:
            self._interval_minutes = _sanitise_interval_minutes(interval_minutes)
        self._persist_config()
        await self._restart_loop()
        return self.snapshot()

    async def refresh_now(self) -> dict[str, Any]:
        workspace = _current_workspace(self._svc)
        inventory_path = _inventory_path_for_workspace(workspace)
        if not inventory_path.exists():
            self._last_run_at = _utc_now_iso()
            self._last_success_at = self._last_run_at
            self._last_error = None
            return _missing_inventory_response(workspace, inventory_path)

        async with self._lock:
            self._last_run_at = _utc_now_iso()
            try:
                hosts = await _refresh_inventory_hosts(workspace, inventory_path)
            except Exception as exc:
                self._last_error = str(exc)
                raise
            self._last_success_at = _utc_now_iso()
            self._last_error = None
            return _build_inventory_response(workspace, inventory_path, hosts)

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.refresh_now()
            except Exception:
                # Keep the background loop alive and surface the latest error via snapshot().
                pass

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._interval_minutes * 60,
                )
            except TimeoutError:
                continue

    async def _restart_loop(self) -> None:
        await self._cancel_task()
        if not self._enabled:
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(
            self._run_loop(),
            name="host-inventory-refresh-job",
        )

    async def _cancel_task(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None


def _get_refresh_job(request: Request) -> HostInventoryRefreshJob | None:
    return getattr(request.app.state, "host_inventory_refresh_job", None)


@router.get("/inventory")
async def get_host_inventory(
    _user: Annotated[dict, Depends(get_current_user)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict[str, Any]:
    workspace = _current_workspace(svc)
    inventory_path = _inventory_path_for_workspace(workspace)

    if not inventory_path.exists():
        return _missing_inventory_response(workspace, inventory_path)

    payload = _load_inventory_payload(inventory_path)
    return _build_inventory_response(workspace, inventory_path, _normalise_hosts(payload))


@router.post("/inventory/refresh")
async def refresh_host_inventory(
    request: Request,
    _user: Annotated[dict, Depends(get_current_user)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict[str, Any]:
    refresh_job = _get_refresh_job(request)
    if refresh_job is not None:
        return await refresh_job.refresh_now()

    workspace = _current_workspace(svc)
    inventory_path = _inventory_path_for_workspace(workspace)

    if not inventory_path.exists():
        return _missing_inventory_response(workspace, inventory_path)

    hosts = await _refresh_inventory_hosts(workspace, inventory_path)
    return _build_inventory_response(workspace, inventory_path, hosts)


@router.get("/inventory/refresh-config", response_model=HostInventoryRefreshConfigResponse)
async def get_host_inventory_refresh_config(
    request: Request,
    _user: Annotated[dict, Depends(get_current_user)],
) -> HostInventoryRefreshConfigResponse:
    refresh_job = _get_refresh_job(request)
    if refresh_job is None:
        cfg = get_host_inventory_refresh()
        return HostInventoryRefreshConfigResponse(
            enabled=bool(cfg.get("enabled", False)),
            intervalMinutes=_sanitise_interval_minutes(cfg.get("interval_minutes")),
            isRunning=False,
            lastRunAt=None,
            lastSuccessAt=None,
            lastError=None,
        )
    return refresh_job.snapshot()


@router.put("/inventory/refresh-config", response_model=HostInventoryRefreshConfigResponse)
async def put_host_inventory_refresh_config(
    request: Request,
    body: HostInventoryRefreshConfigRequest,
    _user: Annotated[dict, Depends(get_current_user)],
) -> HostInventoryRefreshConfigResponse:
    refresh_job = _get_refresh_job(request)
    if refresh_job is None:
        current = get_host_inventory_refresh()
        enabled = body.enabled if body.enabled is not None else bool(current.get("enabled", False))
        interval_minutes = _sanitise_interval_minutes(
            body.intervalMinutes if body.intervalMinutes is not None else current.get("interval_minutes")
        )
        set_host_inventory_refresh(
            {
                "enabled": enabled,
                "interval_minutes": interval_minutes,
            }
        )
        return HostInventoryRefreshConfigResponse(
            enabled=enabled,
            intervalMinutes=interval_minutes,
            isRunning=False,
            lastRunAt=None,
            lastSuccessAt=None,
            lastError=None,
        )

    return await refresh_job.update_config(
        enabled=body.enabled,
        interval_minutes=body.intervalMinutes,
    )
