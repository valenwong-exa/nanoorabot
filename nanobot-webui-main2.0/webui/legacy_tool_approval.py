"""Shared helpers for legacy tool-approval state stored in session metadata."""

from __future__ import annotations

import json
from typing import Any

from nanobot.session.manager import Session

from webui.legacy_tool_policy import normalize_policy_text

PENDING_TOOL_APPROVAL_KEY = "pending_tool_approval"
APPROVED_TOOL_CALL_KEY = "approved_tool_call"


def pending_tool_approval(session: Session | None) -> dict[str, Any] | None:
    if session is None:
        return None
    payload = session.metadata.get(PENDING_TOOL_APPROVAL_KEY)
    return dict(payload) if isinstance(payload, dict) else None


def set_pending_tool_approval(session: Session, payload: dict[str, Any]) -> None:
    session.metadata[PENDING_TOOL_APPROVAL_KEY] = dict(payload)


def clear_pending_tool_approval(session: Session) -> None:
    session.metadata.pop(PENDING_TOOL_APPROVAL_KEY, None)


def approved_tool_call(session: Session | None) -> dict[str, Any] | None:
    if session is None:
        return None
    payload = session.metadata.get(APPROVED_TOOL_CALL_KEY)
    return dict(payload) if isinstance(payload, dict) else None


def set_approved_tool_call(session: Session, payload: dict[str, Any]) -> None:
    session.metadata[APPROVED_TOOL_CALL_KEY] = {
        "tool_name": payload.get("tool_name"),
        "arguments": dict(payload.get("arguments") or {}),
    }


def clear_approved_tool_call(session: Session) -> None:
    session.metadata.pop(APPROVED_TOOL_CALL_KEY, None)


def interpret_tool_approval_reply(raw: str) -> str | None:
    normalized = normalize_policy_text(raw)
    if normalized in {
        "同意",
        "同意执行",
        "授权",
        "授权执行",
        "批准",
        "批准执行",
        "approve",
        "approved",
        "yes",
        "y",
        "ok",
        "continue",
        "继续执行",
    }:
        return "approve"
    if normalized in {
        "拒绝",
        "取消",
        "不授权",
        "deny",
        "no",
        "n",
        "cancel",
        "stop",
    }:
        return "deny"
    return None


def build_approved_note(raw: str, payload: dict[str, Any]) -> str:
    return (
        f"{raw}\n\n"
        "[System note: The user explicitly approved the previously paused risky tool call. "
        "You may execute it now if it is still necessary.]\n"
        f"Approved tool: {payload.get('tool_name')}\n"
        "Approved arguments:\n"
        f"{json.dumps(payload.get('arguments', {}), ensure_ascii=False, indent=2)}"
    )
