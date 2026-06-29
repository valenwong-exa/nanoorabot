"""JSON cache helpers for database metadata trees."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from loguru import logger


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def oracle_ops_core_skill_dir(workspace: Path | None = None) -> Path:
    base_workspace = workspace if workspace is not None else _project_root()
    root = base_workspace / "skills" / "oracle_ops_core"
    root.mkdir(parents=True, exist_ok=True)
    return root


def ora_ops_metadata_dir(workspace: Path | None = None) -> Path:
    base_workspace = workspace if workspace is not None else _project_root()
    root = base_workspace / "ora-ops-metadata"
    root.mkdir(parents=True, exist_ok=True)
    return root


def default_cache_dir(workspace: Path | None = None) -> Path:
    return ora_ops_metadata_dir(workspace) / "metadata_cache"


def cache_dir(base_dir: Path | None = None) -> Path:
    root = base_dir or default_cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    return root


def cache_file_path(connection_id: str, base_dir: Path | None = None) -> Path:
    digest = hashlib.sha1(connection_id.encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", connection_id).strip("-.").lower() or "connection"
    return cache_dir(base_dir) / f"{slug}_{digest}.json"


def legacy_cache_file_path(connection_id: str, base_dir: Path | None = None) -> Path:
    digest = hashlib.sha1(connection_id.encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", connection_id).strip("-.").lower() or "connection"
    return cache_dir(base_dir) / f"{slug}_{digest}.yaml"


def read_cache(connection_id: str, base_dir: Path | None = None) -> dict[str, Any] | None:
    path = cache_file_path(connection_id, base_dir)
    if path.exists():
        return read_json_file(path)

    legacy_path = legacy_cache_file_path(connection_id, base_dir)
    if not legacy_path.exists():
        return None

    return _migrate_legacy_cache(legacy_path, path)


def write_cache(connection_id: str, payload: dict[str, Any], base_dir: Path | None = None) -> Path:
    path = cache_file_path(connection_id, base_dir)
    write_json_file(path, payload)
    return path


def read_json_file(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid metadata cache format: {path}")
    return data


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    path.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")


def _migrate_legacy_cache(legacy_path: Path, json_path: Path) -> dict[str, Any] | None:
    try:
        payload = read_json_file(legacy_path)
    except Exception as exc:
        logger.warning(
            "Ignoring legacy metadata cache that is not valid JSON: legacy_cache_file={} detail={}",
            legacy_path,
            exc,
        )
        return None

    try:
        write_json_file(json_path, payload)
    except Exception as exc:
        logger.warning(
            "Failed to rewrite legacy metadata cache as JSON: legacy_cache_file={} cache_file={} detail={}",
            legacy_path,
            json_path,
            exc,
        )
        return payload

    try:
        legacy_path.unlink()
    except OSError as exc:
        logger.warning(
            "Migrated legacy metadata cache to JSON but could not delete old file: legacy_cache_file={} cache_file={} detail={}",
            legacy_path,
            json_path,
            exc,
        )
    else:
        logger.info(
            "Migrated legacy metadata cache to JSON: legacy_cache_file={} cache_file={}",
            legacy_path,
            json_path,
        )
    return payload


def find_node_by_id(tree: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    if tree.get("id") == node_id:
        return tree
    for child in tree.get("children", []) or []:
        if isinstance(child, dict):
            found = find_node_by_id(child, node_id)
            if found is not None:
                return found
    return None


def update_node_children(tree: dict[str, Any], node_id: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    node = find_node_by_id(tree, node_id)
    if node is None:
        raise KeyError(f"Tree node not found: {node_id}")
    metadata = node.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    node["children"] = children
    node["loaded"] = True
    node["metadata"] = metadata
    return tree
