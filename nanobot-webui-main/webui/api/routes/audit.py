"""Audit routes for session file preview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from webui.api.deps import get_current_user, get_services
from webui.api.gateway import ServiceContainer

router = APIRouter()


def _truncate(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


@router.get("/sessions")
async def get_audit_sessions(
    _user: Annotated[dict, Depends(get_current_user)],
    svc: Annotated[ServiceContainer, Depends(get_services)],
) -> dict[str, Any]:
    workspace = Path(svc.config.agents.defaults.workspace).expanduser()
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
        raw_lines = path.read_text(encoding="utf-8").splitlines()
        tail_lines = raw_lines[-20:]
        records: list[dict[str, Any]] = []
        session_key = ""
        created_at = ""
        updated_at = ""

        for index, raw in enumerate(tail_lines, start=max(1, len(raw_lines) - len(tail_lines) + 1)):
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                records.append(
                    {
                        "line_number": index,
                        "role": "invalid",
                        "timestamp": "",
                        "summary": _truncate(raw),
                        "raw": raw,
                    }
                )
                continue

            if item.get("_type") == "metadata":
                session_key = item.get("key", "")
                created_at = item.get("created_at", "")
                updated_at = item.get("updated_at", "")

            role = item.get("role") or item.get("_type") or "unknown"
            timestamp = item.get("timestamp") or item.get("updated_at") or item.get("created_at") or ""
            content = item.get("content") or ""
            if item.get("tool_calls"):
                tool_names = ", ".join(
                    call.get("function", {}).get("name", "tool")
                    for call in item.get("tool_calls", [])
                    if isinstance(call, dict)
                )
                content = f"[tool_calls] {tool_names}" if tool_names else "[tool_calls]"
            if role == "tool":
                content = item.get("name", "tool") + ": " + (item.get("content") or "")

            records.append(
                {
                    "line_number": index,
                    "role": role,
                    "timestamp": timestamp,
                    "summary": _truncate(content or raw),
                    "raw": item,
                }
            )

        files_payload.append(
            {
                "file_name": path.name,
                "session_type": path.name.split("_", 1)[0],
                "session_key": session_key,
                "created_at": created_at,
                "updated_at": updated_at,
                "line_count": len(raw_lines),
                "records": records,
            }
        )

    return {
        "workspace": str(workspace),
        "sessions_dir": str(sessions_dir),
        "exists": True,
        "files": files_payload,
    }
