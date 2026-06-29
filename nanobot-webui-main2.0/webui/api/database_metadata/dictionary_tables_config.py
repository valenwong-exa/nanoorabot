"""Workspace-scoped JSON config for curated Oracle DBA dictionary views."""

from __future__ import annotations

import json
import re
from pathlib import Path

from loguru import logger

from .json_cache import oracle_ops_core_skill_dir

DEFAULT_DICTIONARY_TABLE_NAMES: tuple[str, ...] = (
    "DBA_OBJECTS",
    "DBA_TABLES",
    "DBA_TAB_COLUMNS",
    "DBA_TAB_COMMENTS",
    "DBA_COL_COMMENTS",
    "DBA_INDEXES",
    "DBA_IND_COLUMNS",
    "DBA_IND_EXPRESSIONS",
    "DBA_CONSTRAINTS",
    "DBA_CONS_COLUMNS",
    "DBA_DEPENDENCIES",
    "DBA_SEGMENTS",
    "DBA_EXTENTS",
    "DBA_LOBS",
    "DBA_PART_TABLES",
    "DBA_TAB_PARTITIONS",
    "DBA_TAB_SUBPARTITIONS",
    "DBA_IND_PARTITIONS",
    "DBA_IND_SUBPARTITIONS",
    "DBA_TABLESPACES",
    "DBA_DATA_FILES",
    "DBA_TEMP_FILES",
    "DBA_FREE_SPACE",
    "DBA_TABLESPACE_USAGE_METRICS",
    "DBA_TS_QUOTAS",
    "DBA_UNDO_EXTENTS",
    "DBA_USERS",
    "DBA_ROLES",
    "DBA_ROLE_PRIVS",
    "DBA_SYS_PRIVS",
    "DBA_TAB_PRIVS",
    "DBA_COL_PRIVS",
    "DBA_PROFILES",
    "DBA_PROXY_USERS",
    "DBA_TAB_STATISTICS",
    "DBA_IND_STATISTICS",
    "DBA_TAB_COL_STATISTICS",
    "DBA_TAB_HISTOGRAMS",
    "DBA_OPTSTAT_OPERATIONS",
    "DBA_OPTSTAT_OPERATION_TASKS",
    "DBA_SCHEDULER_JOBS",
    "DBA_SCHEDULER_JOB_RUN_DETAILS",
    "DBA_SCHEDULER_RUNNING_JOBS",
    "DBA_SCHEDULER_PROGRAMS",
    "DBA_SCHEDULER_SCHEDULES",
    "DBA_SCHEDULER_WINDOWS",
    "DBA_SCHEDULER_WINDOW_GROUPS",
    "DBA_AUTOTASK_CLIENT",
    "DBA_AUTOTASK_WINDOW_CLIENTS",
    "DBA_AUTOTASK_JOB_HISTORY",
    "DBA_ERRORS",
    "DBA_SOURCE",
    "DBA_PROCEDURES",
    "DBA_ARGUMENTS",
    "DBA_TRIGGERS",
    "DBA_RECYCLEBIN",
    "DBA_AUDIT_TRAIL",
    "DBA_FGA_AUDIT_TRAIL",
    "DBA_COMMON_AUDIT_TRAIL",
    "DBA_AUDIT_POLICIES",
    "DBA_STMT_AUDIT_OPTS",
    "DBA_PRIV_AUDIT_OPTS",
    "DBA_OBJ_AUDIT_OPTS",
    "DBA_DB_LINKS",
    "DBA_SYNONYMS",
    "DBA_DIRECTORIES",
    "DBA_EXTERNAL_TABLES",
    "DBA_EXTERNAL_LOCATIONS",
    "DBA_HIST_SNAPSHOT",
    "DBA_HIST_SQLSTAT",
    "DBA_HIST_SQLTEXT",
    "DBA_HIST_SQL_PLAN",
    "DBA_HIST_ACTIVE_SESS_HISTORY",
    "DBA_HIST_SYSTEM_EVENT",
    "DBA_HIST_SYSSTAT",
    "DBA_HIST_SEG_STAT",
    "DBA_HIST_TBSPC_SPACE_USAGE",
    "DBA_HIST_UNDOSTAT",
    "DBA_PDBS",
    "DBA_SERVICES",
)

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
OBJECT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,127}$")

DEFAULT_DICTIONARY_TABLES: tuple[dict[str, str], ...] = tuple(
    {
        "key": name.lower(),
        "label": name,
        "objectName": name,
        "sql": f"select * from {name} where rownum <= 100;",
    }
    for name in DEFAULT_DICTIONARY_TABLE_NAMES
)


def dictionary_tables_config_path(base_dir: Path | None = None) -> Path:
    root = base_dir if base_dir is not None else oracle_ops_core_skill_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root / "dictionary_tables.json"


def ensure_dictionary_tables_config(base_dir: Path | None = None) -> Path:
    path = dictionary_tables_config_path(base_dir)
    if path.exists():
        return path
    _write_dictionary_tables_config(path, list(DEFAULT_DICTIONARY_TABLES))
    return path


def load_dictionary_tables(base_dir: Path | None = None) -> list[dict[str, str]]:
    path = ensure_dictionary_tables_config(base_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(
            "Failed to read dictionary tables config, restoring defaults: config_file={} detail={}",
            path,
            exc,
        )
        _write_dictionary_tables_config(path, list(DEFAULT_DICTIONARY_TABLES))
        return [dict(item) for item in DEFAULT_DICTIONARY_TABLES]

    items = payload.get("items")
    if not isinstance(items, list):
        logger.warning("Invalid dictionary tables config structure, restoring defaults: config_file={}", path)
        _write_dictionary_tables_config(path, list(DEFAULT_DICTIONARY_TABLES))
        return [dict(item) for item in DEFAULT_DICTIONARY_TABLES]

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_key = item.get("key")
        raw_label = item.get("label")
        raw_object_name = item.get("objectName")
        raw_sql = item.get("sql")
        if not all(isinstance(value, str) for value in (raw_key, raw_label, raw_object_name, raw_sql)):
            continue
        key = raw_key.strip().lower()
        label = raw_label.strip()
        object_name = raw_object_name.strip().upper()
        sql = raw_sql.strip()
        if (
            not key
            or not label
            or not object_name
            or not sql
            or key in seen
            or KEY_PATTERN.fullmatch(key) is None
            or OBJECT_NAME_PATTERN.fullmatch(object_name) is None
        ):
            continue
        seen.add(key)
        normalized.append({"key": key, "label": label, "objectName": object_name, "sql": sql})
    return normalized


def _write_dictionary_tables_config(path: Path, items: list[dict[str, str]]) -> None:
    payload = {"items": items}
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
