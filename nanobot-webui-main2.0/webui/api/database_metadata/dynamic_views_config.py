"""Workspace-scoped JSON config for curated Oracle dynamic views."""

from __future__ import annotations

import json
import re
from pathlib import Path

from loguru import logger

from .json_cache import oracle_ops_core_skill_dir

DEFAULT_DYNAMIC_VIEWS: tuple[str, ...] = (
    "V$SESSION",
    "V$SESSION_WAIT",
    "V$SESSION_EVENT",
    "V$SESSION_LONGOPS",
    "V$PROCESS",
    "V$ACTIVE_SESSION_HISTORY",
    "V$SQL",
    "V$SQLAREA",
    "V$SQLSTATS",
    "V$SQL_PLAN",
    "V$SQL_PLAN_STATISTICS_ALL",
    "V$SQL_MONITOR",
    "V$SQL_BIND_CAPTURE",
    "V$SQL_SHARED_CURSOR",
    "V$SYSTEM_EVENT",
    "V$EVENT_NAME",
    "V$WAITCLASSMETRIC",
    "V$SYSTEM_WAIT_CLASS",
    "V$EVENT_HISTOGRAM",
    "V$SYSSTAT",
    "V$SESSTAT",
    "V$STATNAME",
    "V$SYSMETRIC",
    "V$SYSMETRIC_HISTORY",
    "V$SYS_TIME_MODEL",
    "V$SESS_TIME_MODEL",
    "V$OSSTAT",
    "V$FILESTAT",
    "V$DATAFILE",
    "V$TEMPFILE",
    "V$IOSTAT_FILE",
    "V$IOSTAT_FUNCTION",
    "V$TEMPSEG_USAGE",
    "V$SORT_SEGMENT",
    "V$SGA",
    "V$SGASTAT",
    "V$SGA_DYNAMIC_COMPONENTS",
    "V$MEMORY_DYNAMIC_COMPONENTS",
    "V$BUFFER_POOL_STATISTICS",
    "V$LIBRARYCACHE",
    "V$ROWCACHE",
    "V$PGASTAT",
    "V$PROCESS_MEMORY",
    "V$SQL_WORKAREA",
    "V$SQL_WORKAREA_ACTIVE",
    "V$PGA_TARGET_ADVICE",
    "V$DB_CACHE_ADVICE",
    "V$SHARED_POOL_ADVICE",
    "V$LOCK",
    "V$LOCKED_OBJECT",
    "V$TRANSACTION",
    "V$ENQUEUE_STAT",
    "V$LATCH",
    "V$LATCH_CHILDREN",
    "V$MUTEX_SLEEP",
    "V$MUTEX_SLEEP_HISTORY",
    "GV$SESSION",
    "GV$SQL",
    "GV$ACTIVE_SESSION_HISTORY",
    "GV$SYSTEM_EVENT",
    "GV$GES_BLOCKING_ENQUEUE",
    "GV$GLOBAL_BLOCKED_LOCKS",
    "GV$CACHE_TRANSFER",
    "GV$CR_BLOCK_SERVER",
    "GV$CURRENT_BLOCK_SERVER",
    "GV$SQL_MONITOR",
    "V$UNDOSTAT",
    "V$LOG",
    "V$LOGFILE",
    "V$LOG_HISTORY",
    "V$ARCHIVED_LOG",
    "V$LOGSTDBY_STATS",
    "V$DATAGUARD_STATS",
    "V$MANAGED_STANDBY",
    "V$ARCHIVE_DEST_STATUS",
    "V$SORT_USAGE",
    "V$TEMP_SPACE_HEADER",
)
OBJECT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,127}$")


def dynamic_views_config_path(base_dir: Path | None = None) -> Path:
    root = base_dir if base_dir is not None else oracle_ops_core_skill_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root / "dynamic_views.json"


def ensure_dynamic_views_config(base_dir: Path | None = None) -> Path:
    path = dynamic_views_config_path(base_dir)
    if path.exists():
        return path
    _write_dynamic_views_config(path, list(DEFAULT_DYNAMIC_VIEWS))
    return path


def load_dynamic_views(base_dir: Path | None = None) -> list[str]:
    path = ensure_dynamic_views_config(base_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read dynamic views config, restoring defaults: config_file={} detail={}", path, exc)
        _write_dynamic_views_config(path, list(DEFAULT_DYNAMIC_VIEWS))
        return list(DEFAULT_DYNAMIC_VIEWS)

    views = payload.get("views")
    if not isinstance(views, list):
        logger.warning("Invalid dynamic views config structure, restoring defaults: config_file={}", path)
        _write_dynamic_views_config(path, list(DEFAULT_DYNAMIC_VIEWS))
        return list(DEFAULT_DYNAMIC_VIEWS)

    normalized: list[str] = []
    seen: set[str] = set()
    for item in views:
        if not isinstance(item, str):
            continue
        name = item.strip().upper()
        if not name or name in seen or OBJECT_NAME_PATTERN.fullmatch(name) is None:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def _write_dynamic_views_config(path: Path, views: list[str]) -> None:
    payload = {"views": views}
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
