"""Workspace-scoped JSON config for curated SQL diagnoses."""

from __future__ import annotations

import json
import re
from pathlib import Path

from loguru import logger

from .json_cache import oracle_ops_core_skill_dir

DEFAULT_USEFUL_DIAGNOSES: tuple[dict[str, str], ...] = (
    {
        "key": "tablespace_usage",
        "label": "tablespace usage",
        "sql": (
            "select df.tablespace_name,\n"
            "       ts.status,\n"
            "       ts.contents,\n"
            "       round(df.total_bytes / 1024 / 1024 / 1024, 2) as total_gb,\n"
            "       round((df.total_bytes - nvl(fs.free_bytes, 0)) / 1024 / 1024 / 1024, 2) as used_gb,\n"
            "       round(nvl(fs.free_bytes, 0) / 1024 / 1024 / 1024, 2) as free_gb,\n"
            "       round(df.max_bytes / 1024 / 1024 / 1024, 2) as max_gb,\n"
            "       round((df.total_bytes - nvl(fs.free_bytes, 0)) / df.total_bytes * 100, 2) as used_pct,\n"
            "       round((df.total_bytes - nvl(fs.free_bytes, 0)) / df.max_bytes * 100, 2) as used_pct_max\n"
            "from (\n"
            "    select tablespace_name,\n"
            "           sum(bytes) as total_bytes,\n"
            "           sum(\n"
            "               case\n"
            "                   when autoextensible = 'YES' then maxbytes\n"
            "                   else bytes\n"
            "               end\n"
            "           ) as max_bytes\n"
            "    from dba_data_files\n"
            "    group by tablespace_name\n"
            ") df\n"
            "join dba_tablespaces ts\n"
            "  on df.tablespace_name = ts.tablespace_name\n"
            "left join (\n"
            "    select tablespace_name,\n"
            "           sum(bytes) as free_bytes\n"
            "    from dba_free_space\n"
            "    group by tablespace_name\n"
            ") fs\n"
            "  on df.tablespace_name = fs.tablespace_name\n"
            "order by used_pct_max desc;"
        ),
    },
    {
        "key": "redo_status",
        "label": "redo status",
        "sql": (
            "select l.inst_id,\n"
            "       l.thread#,\n"
            "       l.group#,\n"
            "       l.sequence#,\n"
            "       round(l.bytes / 1024 / 1024, 2) as bytes_mb,\n"
            "       l.status,\n"
            "       l.archived,\n"
            "       l.members,\n"
            "       to_char(l.first_time, 'yyyy-mm-dd hh24:mi:ss') as first_time\n"
            "from gv$log l\n"
            "order by l.inst_id,\n"
            "         l.thread#,\n"
            "         l.group#;"
        ),
    },
)

KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,127}$")
NON_KEY_CHARS_PATTERN = re.compile(r"[^a-z0-9]+")


def useful_diagnoses_config_path(base_dir: Path | None = None) -> Path:
    root = base_dir if base_dir is not None else oracle_ops_core_skill_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root / "useful_diagnoses.json"


def ensure_useful_diagnoses_config(base_dir: Path | None = None) -> Path:
    path = useful_diagnoses_config_path(base_dir)
    if path.exists():
        return path
    _write_useful_diagnoses_config(path, list(DEFAULT_USEFUL_DIAGNOSES))
    return path


def load_useful_diagnoses(base_dir: Path | None = None) -> list[dict[str, str]]:
    path = ensure_useful_diagnoses_config(base_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning(
            "Failed to read useful diagnoses config, restoring defaults: config_file={} detail={}",
            path,
            exc,
        )
        _write_useful_diagnoses_config(path, list(DEFAULT_USEFUL_DIAGNOSES))
        return [dict(item) for item in DEFAULT_USEFUL_DIAGNOSES]

    items = payload.get("items")
    if not isinstance(items, list):
        logger.warning("Invalid useful diagnoses config structure, restoring defaults: config_file={}", path)
        _write_useful_diagnoses_config(path, list(DEFAULT_USEFUL_DIAGNOSES))
        return [dict(item) for item in DEFAULT_USEFUL_DIAGNOSES]

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_key = item.get("key")
        raw_label = item.get("label")
        raw_sql = item.get("sql")
        if not isinstance(raw_key, str) or not isinstance(raw_label, str) or not isinstance(raw_sql, str):
            continue
        key = normalize_useful_diagnosis_key(raw_key)
        label = raw_label.strip()
        sql = raw_sql.strip()
        if not key or not label or not sql or key in seen:
            continue
        seen.add(key)
        normalized.append({"key": key, "label": label, "sql": sql})
    return normalized


def normalize_useful_diagnosis_key(raw_key: str) -> str:
    key = NON_KEY_CHARS_PATTERN.sub("_", raw_key.strip().lower()).strip("_")
    if not key:
        return ""
    if key[0].isdigit():
        key = f"item_{key}"
    key = key[:128].rstrip("_")
    if KEY_PATTERN.fullmatch(key) is None:
        return ""
    return key


def _write_useful_diagnoses_config(path: Path, items: list[dict[str, str]]) -> None:
    payload = {"items": items}
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
