"""YAML cache helpers for database metadata trees."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - fallback path
    yaml = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def cache_dir(base_dir: Path | None = None) -> Path:
    root = base_dir or (_project_root() / "metadata_cache")
    root.mkdir(parents=True, exist_ok=True)
    return root


def cache_file_path(connection_id: str, base_dir: Path | None = None) -> Path:
    digest = hashlib.sha1(connection_id.encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", connection_id).strip("-.").lower() or "connection"
    return cache_dir(base_dir) / f"{slug}_{digest}.yaml"


def read_cache(connection_id: str, base_dir: Path | None = None) -> dict[str, Any] | None:
    path = cache_file_path(connection_id, base_dir)
    if not path.exists():
        return None
    return read_yaml_file(path)


def write_cache(connection_id: str, payload: dict[str, Any], base_dir: Path | None = None) -> Path:
    path = cache_file_path(connection_id, base_dir)
    write_yaml_file(path, payload)
    return path


def read_yaml_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid metadata cache format: {path}")
    return data


def write_yaml_file(path: Path, payload: dict[str, Any]) -> None:
    if yaml is not None:
        text = yaml.safe_dump(payload, allow_unicode=False, sort_keys=False)
    else:
        # JSON is a valid YAML subset and provides a safe no-dependency fallback.
        text = json.dumps(payload, ensure_ascii=True, indent=2)
    path.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")


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
