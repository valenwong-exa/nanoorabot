"""[OraclePersistence] restore Oracle audit/memory persistence on main3."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import time
from typing import Any


def _usage_dict(usage: dict[str, Any] | None) -> dict[str, int]:
    if not usage:
        return {}
    result: dict[str, int] = {}
    for key, value in usage.items():
        try:
            result[key] = int(value or 0)
        except (TypeError, ValueError):
            continue
    return result


def _channel_chat_from_session_key(session_key: str | None) -> tuple[str | None, str | None]:
    if not session_key:
        return None, None
    if ":" not in session_key:
        return session_key, None
    channel, chat_id = session_key.split(":", 1)
    return channel or None, chat_id or None


def _publish_oracle_audit(
    runner: object,
    spec: object,
    *,
    request_messages: list[dict[str, Any]],
    request_tools: list[dict[str, Any]] | None,
    request_options: dict[str, Any],
    response: object | None,
    iteration_no: int,
    request_phase: str,
    request_started_at: float,
) -> None:
    sink = getattr(runner, "oracle_memory_sink", None)
    if sink is None or not getattr(sink, "audit_enabled", False):
        return

    usage = _usage_dict(getattr(response, "usage", None))
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")
    if total_tokens is None and (prompt_tokens is not None or completion_tokens is not None):
        total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

    session_key = getattr(spec, "session_key", None)
    channel, chat_id = _channel_chat_from_session_key(session_key)
    llm_call_seq = int(getattr(runner, "_oracle_audit_call_seq", 0)) + 1
    setattr(runner, "_oracle_audit_call_seq", llm_call_seq)
    payload = {
        "session_key": session_key or f"{channel or 'internal'}:{chat_id or 'default'}",
        "turn_id": (
            f"{session_key or channel or 'sessionless'}:{llm_call_seq}:{int(request_started_at * 1000)}"
        ),
        "iteration_no": iteration_no,
        "llm_call_seq": llm_call_seq,
        "attempt_no": 1,
        "request_phase": request_phase,
        "channel": channel,
        "chat_id": chat_id,
        "provider_name": type(getattr(getattr(spec, "runtime", None), "provider", object())).__name__,
        "model_name": getattr(getattr(spec, "runtime", None), "model", None),
        "model_preset": getattr(getattr(spec, "runtime", None), "model_preset", None),
        "request_started_at": datetime.fromtimestamp(request_started_at, tz=timezone.utc),
        "response_ended_at": datetime.now(timezone.utc),
        "latency_ms": max(0, int((time.time() - request_started_at) * 1000)),
        "finish_reason": getattr(response, "finish_reason", None) if response is not None else "error",
        "stop_reason": None,
        "error_kind": getattr(response, "error_kind", None) if response is not None else None,
        "error_type": getattr(response, "error_type", None) if response is not None else None,
        "error_code": getattr(response, "error_code", None) if response is not None else None,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "tool_count": len(request_tools or []),
        "request_messages_json": deepcopy(request_messages),
        "request_tools_json": deepcopy(request_tools),
        "request_options_json": deepcopy(request_options),
        "response_json": None if response is None else {
            "content": getattr(response, "content", None),
            "finish_reason": getattr(response, "finish_reason", None),
            "usage": usage,
            "retry_after": getattr(response, "retry_after", None),
            "reasoning_content": getattr(response, "reasoning_content", None),
            "thinking_blocks": getattr(response, "thinking_blocks", None),
            "tool_calls": [
                tool_call.to_openai_tool_call()
                for tool_call in getattr(response, "tool_calls", []) or []
            ],
            "error_kind": getattr(response, "error_kind", None),
            "error_type": getattr(response, "error_type", None),
            "error_code": getattr(response, "error_code", None),
        },
        "error_message": (
            getattr(response, "content", None)
            if response is not None and getattr(response, "finish_reason", None) == "error"
            else None
        ),
    }
    sink.publish_audit(payload)


def apply() -> None:
    from loguru import logger
    from nanobot.agent.loop import AgentLoop
    from nanobot.agent.runner import AgentRunner

    if getattr(AgentLoop, "_webui_oracle_persistence_patch_applied", False):
        return

    _orig_save_turn = AgentLoop._save_turn

    def _save_turn_patched(
        self,
        session,
        messages,
        skip,
        *,
        turn_latency_ms=None,
    ):
        before = len(session.messages)
        _orig_save_turn(
            self,
            session,
            messages,
            skip,
            turn_latency_ms=turn_latency_ms,
        )
        sink = getattr(self, "oracle_memory", None)
        if sink is None or not getattr(sink, "memory_enabled", False):
            return
        for offset, message in enumerate(session.messages[before:], start=before + 1):
            message.setdefault("message_seq", offset)
            message.setdefault("message_id", f"{session.key}:{offset}")
            try:
                sink.publish_session_message(session.key, message)
            except Exception:
                logger.exception("Failed to enqueue Oracle memory payload")

    AgentLoop._save_turn = _save_turn_patched

    _orig_persist_user_message_early = AgentLoop._persist_user_message_early

    def _persist_user_message_early_patched(
        self,
        msg,
        session,
        runtime_context_blocks=None,
        **kwargs,
    ):
        persisted = _orig_persist_user_message_early(
            self,
            msg,
            session,
            runtime_context_blocks=runtime_context_blocks,
            **kwargs,
        )
        if not persisted or not session.messages:
            return persisted
        sink = getattr(self, "oracle_memory", None)
        if sink is None or not getattr(sink, "memory_enabled", False):
            return persisted
        latest = session.messages[-1]
        latest.setdefault("message_seq", len(session.messages))
        latest.setdefault("message_id", f"{session.key}:{len(session.messages)}")
        self.sessions.save(session)
        try:
            sink.publish_session_message(session.key, latest)
        except Exception:
            logger.exception("Failed to enqueue Oracle memory payload")
        return persisted

    AgentLoop._persist_user_message_early = _persist_user_message_early_patched

    _orig_request_model = AgentRunner._request_model

    async def _request_model_patched(
        self,
        spec,
        messages,
        hook,
        context,
        *,
        malformed_retry=False,
        conversation_state,
        provider_context=None,
    ):
        request_started_at = time.time()
        kwargs = self._build_request_kwargs(
            spec,
            messages,
            tools=spec.tools.get_definitions(),
        )
        request_messages = deepcopy(messages)
        request_tools = deepcopy(kwargs.get("tools"))
        wants_streaming = hook.wants_streaming()
        progress_callback = spec.progress_callback
        wants_progress_streaming = (
            not wants_streaming
            and spec.stream_progress_deltas
            and progress_callback is not None
            and getattr(spec.runtime.provider, "supports_progress_deltas", False) is True
        )
        request_options = {
            "model": kwargs.get("model"),
            "max_tokens": kwargs.get("max_tokens"),
            "temperature": kwargs.get("temperature"),
            "reasoning_effort": kwargs.get("reasoning_effort"),
            "retry_mode": kwargs.get("retry_mode"),
            "streaming": wants_streaming or wants_progress_streaming,
        }
        response = await _orig_request_model(
            self,
            spec,
            messages,
            hook,
            context,
            malformed_retry=malformed_retry,
            conversation_state=conversation_state,
            provider_context=provider_context,
        )
        try:
            _publish_oracle_audit(
                self,
                spec,
                request_messages=request_messages,
                request_tools=request_tools,
                request_options=request_options,
                response=response,
                iteration_no=getattr(context, "iteration", 0),
                request_phase="main",
                request_started_at=request_started_at,
            )
        except Exception:
            logger.exception("Failed to enqueue Oracle audit payload")
        return response

    AgentRunner._request_model = _request_model_patched

    _orig_request_no_tools = AgentRunner._request_no_tools

    async def _request_no_tools_patched(
        self,
        spec,
        messages,
        *,
        provider_context=None,
    ):
        request_started_at = time.time()
        kwargs = self._build_request_kwargs(spec, messages, tools=None)
        request_messages = deepcopy(messages)
        request_options = {
            "model": kwargs.get("model"),
            "max_tokens": kwargs.get("max_tokens"),
            "temperature": kwargs.get("temperature"),
            "reasoning_effort": kwargs.get("reasoning_effort"),
            "retry_mode": kwargs.get("retry_mode"),
            "streaming": False,
        }
        response = await _orig_request_no_tools(
            self,
            spec,
            messages,
            provider_context=provider_context,
        )
        try:
            _publish_oracle_audit(
                self,
                spec,
                request_messages=request_messages,
                request_tools=None,
                request_options=request_options,
                response=response,
                iteration_no=-1,
                request_phase="no_tools",
                request_started_at=request_started_at,
            )
        except Exception:
            logger.exception("Failed to enqueue Oracle audit payload")
        return response

    AgentRunner._request_no_tools = _request_no_tools_patched
    AgentLoop._webui_oracle_persistence_patch_applied = True
