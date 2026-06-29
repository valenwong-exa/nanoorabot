"""Audit routes for session file preview."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from webui.api.deps import get_current_user, get_services
from webui.api.gateway import ServiceContainer
from webui.utils.channel_compat import classify_session_type

router = APIRouter()


def _truncate(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                value = block.get("text")
                if isinstance(value, str) and value.strip():
                    parts.append(value)
        return "\n".join(parts)
    if isinstance(content, dict):
        try:
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return str(content)
    return ""


def _tool_names(tool_calls: Any) -> str:
    if not isinstance(tool_calls, Iterable) or isinstance(tool_calls, (str, bytes, dict)):
        return ""
    names: list[str] = []
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        function = call.get("function")
        if isinstance(function, dict) and isinstance(function.get("name"), str):
            names.append(function["name"])
    return ", ".join(names)


def _record_payload(item: dict[str, Any], raw_line: str, line_number: int) -> dict[str, Any]:
    role = str(item.get("role") or item.get("_type") or "unknown")
    timestamp = str(item.get("timestamp") or item.get("updated_at") or item.get("created_at") or "")

    if item.get("_type") == "metadata":
        metadata = item.get("metadata")
        summary_text = f"[metadata] key={item.get('key', '')}".strip()
        if isinstance(metadata, dict) and isinstance(metadata.get("title"), str) and metadata["title"].strip():
            summary_text += f" title={metadata['title'].strip()}"
    elif item.get("tool_calls"):
        names = _tool_names(item.get("tool_calls"))
        summary_text = f"[tool_calls] {names}" if names else "[tool_calls]"
    elif role == "tool":
        tool_name = str(item.get("name") or "tool")
        tool_content = _content_to_text(item.get("content"))
        summary_text = f"{tool_name}: {tool_content}".strip(": ")
    else:
        summary_text = _content_to_text(item.get("content"))

    search_text = " ".join(
        part
        for part in [
            role,
            timestamp,
            str(item.get("name") or ""),
            str(item.get("key") or ""),
            summary_text,
            raw_line,
        ]
        if part
    )

    return {
        "line_number": line_number,
        "role": role,
        "timestamp": timestamp,
        "summary": _truncate(summary_text or raw_line, limit=240),
        "search_text": " ".join(search_text.split()),
    }


def _read_session_file(path: Path) -> dict[str, Any]:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict[str, Any]] = []
    session_key = ""
    created_at = ""
    updated_at = ""

    for index, raw in enumerate(raw_lines, start=1):
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            records.append(
                {
                    "line_number": index,
                    "role": "invalid",
                    "timestamp": "",
                    "summary": _truncate(raw),
                    "search_text": raw,
                }
            )
            continue

        if item.get("_type") == "metadata":
            session_key = str(item.get("key") or session_key)
            created_at = str(item.get("created_at") or created_at)
            updated_at = str(item.get("updated_at") or updated_at)

        records.append(_record_payload(item, raw, index))

    return {
        "file_name": path.name,
        "session_type": classify_session_type(session_key, path.name.split("_", 1)[0]),
        "session_key": session_key,
        "created_at": created_at,
        "updated_at": updated_at,
        "line_count": len(raw_lines),
        "records": records,
    }


@router.get("/sessions")
async def get_audit_sessions(
    _user: Annotated[dict, Depends(get_current_user)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict[str, Any]:
    workspace = Path(svc.config.workspace_path).expanduser()
    sessions_dir = workspace / "sessions"

    if not sessions_dir.exists():
        return {
            "workspace": str(workspace),
            "sessions_dir": str(sessions_dir),
            "exists": False,
            "files": [],
        }

    files_payload: list[dict[str, Any]] = []
    for path in sorted(sessions_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        files_payload.append(_read_session_file(path))

    return {
        "workspace": str(workspace),
        "sessions_dir": str(sessions_dir),
        "exists": True,
        "files": files_payload,
    }
