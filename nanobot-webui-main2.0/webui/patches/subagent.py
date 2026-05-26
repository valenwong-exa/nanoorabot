"""[SubAgent] patches — push SubAgent tool-call progress to WebUI / external channels.

Strategy
────────
SubagentManager._run_subagent() runs as a background asyncio.Task with no link
back to any WebSocket or on_progress callback.

Two patches are applied:

1. _run_subagent → emit progress before every tool call:
   • channel in {"websocket", "web"} → _progress_registry[chat_key](text, tool_hint=True)
                                      ws.py sends WS frame {type: "subagent_progress", ...}
   • other channels                  → bus.publish_outbound(_progress=True, _tool_hint=True)
                                      ChannelManager forwards to Telegram / DingTalk / etc.

2. _announce_result (final SubAgent result):
   • channel in {"websocket", "web"} → _announce_registry[chat_key](result_text)
                                      ws.py sends WS frame {type: "done", ...}  (new bubble)
                                      *** skips bus.publish_inbound to avoid Unknown channel:web/websocket mismatches ***
   • other channels                  → original behaviour (bus → main agent → channel.send)

Public API (used by webui/api/routes/ws.py)
───────────────────────────────────────────
  register_progress(chat_key, callback)   — SubAgent tool-hint stream
  unregister_progress(chat_key)
  register_announce(chat_key, callback)   — SubAgent final result
  unregister_announce(chat_key)
"""

from __future__ import annotations

import json
from typing import Any, Awaitable, Callable

from loguru import logger
from webui.utils.channel_compat import (
    is_webui_transport_channel,
    resolve_webui_callback_key,
)

# chat_key ("web:{user_id}") → callback(text, *, tool_hint=True)
_progress_registry: dict[str, Callable[..., Awaitable[None]]] = {}

# chat_key ("web:{user_id}") → callback(result_text: str)
_announce_registry: dict[str, Callable[[str], Awaitable[None]]] = {}

# chat_key ("web:{user_id}") → callback(all_messages: list)
# Called with the full SubAgent messages list (including tool_calls + results + final
# assistant message) so ws.py can persist them via AgentLoop._save_turn.
_save_turn_registry: dict[str, Callable[[list], Awaitable[None]]] = {}

_NO_FINAL_RESPONSE_TEXT = "Task completed but no final response was generated."


def register_progress(chat_key: str, callback: Callable[..., Awaitable[None]]) -> None:
    """Register a SubAgent tool-hint progress callback for the given chat key."""
    _progress_registry[chat_key] = callback


def unregister_progress(chat_key: str) -> None:
    _progress_registry.pop(chat_key, None)


def register_announce(chat_key: str, callback: Callable[[str], Awaitable[None]]) -> None:
    """Register a callback to receive the SubAgent's final result for the given chat key."""
    _announce_registry[chat_key] = callback


def unregister_announce(chat_key: str) -> None:
    _announce_registry.pop(chat_key, None)


def register_save_turn(chat_key: str, callback: Callable[[list], Awaitable[None]]) -> None:
    """Register a callback to persist the SubAgent's full messages list to the session."""
    _save_turn_registry[chat_key] = callback


def unregister_save_turn(chat_key: str) -> None:
    _save_turn_registry.pop(chat_key, None)


def _resolve_subagent_chat_key(channel: str, chat_id: str) -> str:
    """Normalize the registry key used by web-channel subagent callbacks.

    Current WebUI sessions use the native ``websocket`` channel and register
    callbacks as ``websocket:<session_key>``. We still accept the legacy
    ``web`` channel shape for backward compatibility with older patches.
    """
    return resolve_webui_callback_key(channel, chat_id)


def _normalize_text_content(content: Any) -> str:
    """Best-effort conversion for provider/message content into display text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [_normalize_text_content(item) for item in content]
        return "\n".join(part for part in parts if part).strip()
    if isinstance(content, dict):
        for key in ("text", "content", "value", "output", "result", "message"):
            text = _normalize_text_content(content.get(key))
            if text:
                return text
        try:
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return str(content)
    return str(content).strip()


def _extract_response_text(response: Any) -> str:
    """Extract final text from provider responses that are not plain strings."""
    if response is None:
        return ""
    for attr in ("final_content", "content", "text", "output_text", "result", "message"):
        if not hasattr(response, attr):
            continue
        text = _normalize_text_content(getattr(response, attr))
        if text:
            return text
    return _normalize_text_content(response)


def _extract_final_assistant_text(messages: list[dict[str, Any]]) -> str:
    """Read the latest assistant text from an in-memory transcript."""
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        text = _normalize_text_content(message.get("content"))
        if text:
            return text
    return ""


async def _save_sub_tool_to_session(
    subagent_mgr: Any,
    session_key: str,
    messages: list,
    label: str = "SubAgent",
) -> None:
    """Save a brief SubAgent summary to the session (not the full tool chain).

    Stored as ``role: "sub_tool"`` so the WebUI renders them with the
    distinctive indigo SubAgent card instead of a regular user bubble.
    The ``name`` field carries the SubAgent label (e.g. "正方一辩").

    ``sub_tool`` entries are automatically stripped from the LLM history by
    the ``session.py`` ``get_history()`` patch, so they never reach the
    provider and cannot cause "invalid role" 400 errors.
    """
    from datetime import datetime

    session_mgr = getattr(subagent_mgr, "_session_manager", None)
    if session_mgr is None:
        return
    try:
        session = session_mgr.get_or_create(session_key)
        # Extract only the final assistant message as a brief summary.
        final_text = ""
        tools_called: list[str] = []
        for m in messages:
            if m.get("role") == "assistant":
                text = _normalize_text_content(m.get("content"))
                if text:
                    final_text = text
            if m.get("role") == "tool":
                tools_called.append(m.get("name", "?"))

        summary = f"[SubAgent completed] Tools: {', '.join(tools_called[-6:])}."
        if final_text and final_text != _NO_FINAL_RESPONSE_TEXT:
            snippet = final_text[:200] + ("…" if len(final_text) > 200 else "")
            summary += f"\nResult: {snippet}"

        # Save as "sub_tool" role — filtered from LLM history by session patch,
        # but rendered as a SubAgent card in the WebUI.
        session.messages.append({
            "role": "sub_tool",
            "content": summary,
            "name": label,
            "timestamp": datetime.now().isoformat(),
        })
        session.updated_at = datetime.now()
        session_mgr.save(session)
        logger.debug("SubAgent summary saved to session {}", session_key)
    except Exception as exc:
        logger.warning("Failed to save SubAgent summary to session {}: {}", session_key, exc)


def _extract_interaction_log(messages: list) -> str:
    """Extract inter-agent communication from a subagent's message history.

    Looks for:
    - send_to_agent tool calls (outgoing messages)
    - [Message from agent ...] user messages (incoming messages)

    Returns a formatted log string, or "" if no interactions found.
    """
    entries: list[str] = []
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")

        # Incoming messages from other agents
        if role == "user" and isinstance(content, str) and content.startswith("[Message from agent "):
            entries.append(f"📨 收到: {content}")

        # Outgoing send_to_agent tool calls
        if role == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                func = tc.get("function", {})
                if func.get("name") == "send_to_agent":
                    try:
                        args = func.get("arguments", "")
                        if isinstance(args, str):
                            import json as _json
                            args = _json.loads(args)
                        msg_content = args.get("content", "")
                        recipient = args.get("recipient", "?")
                        entries.append(f"📤 发送给 {recipient}: {msg_content}")
                    except Exception:
                        entries.append("📤 发送消息 (解析失败)")

    if not entries:
        return ""

    return "**💬 Agent 交流记录：**\n" + "\n".join(entries)


def _format_tool_hint(tool_calls: list[Any]) -> str:
    """Format a compact progress summary for the current tool batch."""
    hints: list[str] = []
    for tool_call in tool_calls:
        args = tool_call.arguments
        if isinstance(args, list):
            args = args[0] if args else {}
        value = next(iter(args.values()), None) if isinstance(args, dict) and args else None
        if isinstance(value, str) and value:
            preview = value[:40] + "…" if len(value) > 40 else value
            hints.append(f'{tool_call.name}("{preview}")')
        else:
            hints.append(tool_call.name)
    return ", ".join(hints)


def apply() -> None:
    """Monkey-patch SubagentManager to emit progress events.

    The v0.2.0 runtime moved subagent execution onto ``AgentRunner.run()``,
    so this patch now keeps the native runner/checkpoint flow and only layers
    WebUI-specific progress pushes and direct WebSocket delivery on top.
    """
    from nanobot.agent.runner import AgentRunSpec
    from nanobot.agent.subagent import SubagentManager, _SubagentHook
    from nanobot.bus.events import OutboundMessage

    _original_announce_result = SubagentManager._announce_result

    class _WebUISubagentHook(_SubagentHook):
        """Native subagent hook plus WebUI tool-hint pushes."""

        def __init__(
            self,
            task_id: str,
            status: Any,
            emit_progress: Callable[[str], Awaitable[None]],
        ) -> None:
            super().__init__(task_id, status)
            self._emit_progress = emit_progress

        async def before_execute_tools(self, context: Any) -> None:
            await super().before_execute_tools(context)
            if not context.tool_calls:
                return
            await self._emit_progress(_format_tool_hint(list(context.tool_calls)))
            for tool_call in context.tool_calls:
                if tool_call.name != "send_to_agent":
                    continue
                args = tool_call.arguments
                if isinstance(args, list):
                    args = args[0] if args else {}
                if not isinstance(args, dict):
                    continue
                recipient = args.get("recipient", "?")
                content = _normalize_text_content(args.get("content"))
                preview = content[:80]
                await self._emit_progress(f"📤 向 agent {recipient} 发送: {preview}")

    # -----------------------------------------------------------------------
    # Patch 1: _run_subagent — add progress tracking + WebUI progress push
    # -----------------------------------------------------------------------
    async def _run_subagent_patched(
        self: SubagentManager,
        task_id: str,
        task: str,
        label: str,
        origin: dict[str, str],
        status: Any = None,
        origin_message_id: str | None = None,
    ) -> None:
        """Augmented _run_subagent using the native v0.2.0 runner flow."""

        channel = origin.get("channel", "")
        chat_id = str(origin.get("chat_id", ""))
        chat_key = _resolve_subagent_chat_key(channel, chat_id)
        # For cron sessions, the session_key (e.g. "cron:abc123") differs from
        # chat_key ("cli:direct").  Use origin["session_key"] when available so
        # sub-agent messages are persisted under the correct session.
        save_session_key = origin.get("session_key") or chat_key

        async def _emit_progress(hint: str) -> None:
            """Push a tool-hint progress event via the appropriate path."""
            text = f"[↳ {label}] {hint}"
            if is_webui_transport_channel(channel):
                cb = _progress_registry.get(chat_key)
                if cb:
                    try:
                        await cb(text, tool_hint=True)
                    except Exception:
                        pass
            else:
                try:
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=channel,
                        chat_id=chat_id,
                        content=text,
                        metadata={"_progress": True, "_tool_hint": True, "_subagent_hint": True},
                    ))
                except Exception:
                    pass

        logger.info("Subagent [{}] starting task: {}", task_id, label)

        try:
            tools = self._build_tools()
            system_prompt = self._build_subagent_prompt()
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task},
            ]

            sess_key = origin.get("session_key")
            llm_timeout = (
                self._llm_wall_timeout_for_session(sess_key)
                if self._llm_wall_timeout_for_session
                else None
            )
            result = await self.runner.run(AgentRunSpec(
                initial_messages=messages,
                tools=tools,
                model=self.model,
                max_iterations=self.max_iterations,
                max_tool_result_chars=self.max_tool_result_chars,
                hook=_WebUISubagentHook(task_id, status, _emit_progress),
                max_iterations_message=_NO_FINAL_RESPONSE_TEXT,
                error_message=None,
                fail_on_tool_error=True,
                checkpoint_callback=_on_checkpoint,
                session_key=sess_key,
                llm_timeout_s=llm_timeout,
            ))
            messages = list(result.messages)
            if status is not None:
                status.phase = "done"
                status.stop_reason = result.stop_reason
                status.tool_events = list(result.tool_events)
                status.usage = dict(result.usage)

            if result.stop_reason == "tool_error":
                final_result = self._format_partial_progress(result)
                announce_status = "error"
            elif result.stop_reason == "error":
                final_result = result.error or "Error: subagent execution failed."
                announce_status = "error"
            else:
                final_result = result.final_content or _NO_FINAL_RESPONSE_TEXT
                announce_status = "ok"

            if announce_status == "ok":
                logger.info("Subagent [{}] completed successfully", task_id)
            else:
                logger.warning("Subagent [{}] finished with stop_reason={}", task_id, result.stop_reason)

            # Extract inter-agent communication log
            interaction_log = _extract_interaction_log(messages)

            has_meaningful_final = bool(final_result and final_result != _NO_FINAL_RESPONSE_TEXT)
            enriched_result = final_result if has_meaningful_final else ""
            if interaction_log:
                enriched_result = (
                    f"{interaction_log}\n\n---\n\n**最终输出：**\n{enriched_result}"
                    if enriched_result
                    else interaction_log
                )

            # Persist to session (web channel uses registered callback)
            if is_webui_transport_channel(channel):
                save_cb = _save_turn_registry.get(chat_key)
                if save_cb:
                    try:
                        await save_cb(messages)
                    except Exception:
                        pass

            # Call _announce_result — our patch below handles web vs non-web routing.
            await self._announce_result(
                task_id,
                label,
                task,
                enriched_result or final_result,
                origin,
                announce_status,
                origin_message_id,
            )

        except Exception as e:
            error_msg = f"Error: {e}"
            logger.error("Subagent [{}] failed: {}", task_id, e)
            if status is not None:
                status.phase = "error"
                status.error = str(e)
            await self._announce_result(
                task_id, label, task, error_msg, origin, "error", origin_message_id,
            )

    # -----------------------------------------------------------------------
    # Patch 2: _announce_result — for web channel, bypass the bus (which goes
    # through main agent → OutboundMessage(channel="web") → Unknown channel)
    # and push the result directly to the registered callback.
    # -----------------------------------------------------------------------
    async def _announce_result_patched(
        self: SubagentManager,
        task_id: str,
        label: str,
        task: str,
        result: str,
        origin: dict[str, str],
        status: str,
        origin_message_id: str | None = None,
    ) -> None:
        channel = origin.get("channel", "")
        chat_id = str(origin.get("chat_id", ""))
        chat_key = _resolve_subagent_chat_key(channel, chat_id)

        if is_webui_transport_channel(channel):
            normalized_result = _normalize_text_content(result)
            if not normalized_result or normalized_result == _NO_FINAL_RESPONSE_TEXT:
                logger.debug("Subagent [{}] produced no user-facing final result for {}", task_id, chat_key)
                return
            cb = _announce_registry.get(chat_key)
            if cb:
                status_icon = "✅" if status == "ok" else "❌"
                content = f"{status_icon} **[{label}]**\n\n{normalized_result}"
                try:
                    await cb(content)
                    logger.debug(
                        "Subagent [{}] result pushed directly to WebSocket for {}",
                        task_id, chat_key,
                    )
                    return  # Skip bus path entirely for web channel
                except Exception as exc:
                    logger.warning("Subagent announce to WebSocket failed: {}", exc)
            # Fallback: if no callback registered, use original path
            await _original_announce_result(
                self, task_id, label, task, result, origin, status, origin_message_id,
            )
        else:
            # Non-web channels: use a custom InboundMessage with _subagent_label
            # metadata so the patched _process_message can save the incoming
            # message as role="sub_tool" instead of role="user".
            from nanobot.bus.events import InboundMessage as _IB

            status_text = "completed successfully" if status == "ok" else "failed"
            content = (
                f"[Subagent '{label}' {status_text}]\n\nTask: {task}\n\n"
                f"Result:\n{result}\n\n"
                "Summarize this naturally for the user. Keep it brief (1-2 sentences). "
                "Do not mention technical details like \"subagent\" or task IDs."
            )
            override = origin.get("session_key") or f"{origin['channel']}:{origin['chat_id']}"
            metadata: dict[str, Any] = {
                "_subagent_label": label,
                "injected_event": "subagent_result",
                "subagent_task_id": task_id,
            }
            if "session_key" in origin:
                metadata["session_key"] = origin["session_key"]
            if origin_message_id:
                metadata["origin_message_id"] = origin_message_id
            msg = _IB(
                channel="system", sender_id="subagent",
                chat_id=f"{origin['channel']}:{origin['chat_id']}",
                content=content,
                session_key_override=override,
                metadata=metadata,
            )
            await self.bus.publish_inbound(msg)

    SubagentManager._run_subagent = _run_subagent_patched  # type: ignore[method-assign]
    SubagentManager._announce_result = _announce_result_patched  # type: ignore[method-assign]
    logger.debug("SubagentManager patched: _run_subagent + _announce_result")

    # -----------------------------------------------------------------------
    # Patch 3: AgentLoop.__init__ — inject self.sessions into the SubagentManager
    # so _run_subagent_patched can save sub_tool messages for non-web channels.
    # -----------------------------------------------------------------------
    try:
        from nanobot.agent.loop import AgentLoop
        _original_loop_init = AgentLoop.__init__

        def _agent_loop_init_patched(self, *args, **kwargs) -> None:  # type: ignore[override]
            _original_loop_init(self, *args, **kwargs)
            self.subagents._session_manager = self.sessions  # type: ignore[attr-defined]

        AgentLoop.__init__ = _agent_loop_init_patched  # type: ignore[method-assign]
        logger.debug("AgentLoop.__init__ patched: _session_manager injected into SubagentManager")
    except Exception as exc:
        logger.warning("Failed to patch AgentLoop.__init__: {}", exc)

    # -----------------------------------------------------------------------
    # Patch 4: AgentLoop._process_message — when the incoming message
    # originates from a subagent (sender_id=="subagent" with _subagent_label
    # metadata), retroactively change the persisted "user" message to
    # "sub_tool" after _save_turn runs.  This means:
    #   • The LLM still sees the announcement as role="user" (valid).
    #   • The session JSONL stores it as role="sub_tool" with name=<label>,
    #     so the WebUI renders it as a SubAgent card.
    # -----------------------------------------------------------------------
    try:
        from nanobot.agent.loop import AgentLoop
        _original_process_message = AgentLoop._process_message

        async def _process_message_patched(self, msg, session_key=None, on_progress=None, **kwargs):
            result = await _original_process_message(self, msg, session_key=session_key, on_progress=on_progress, **kwargs)

            # After original _process_message completed (which already called
            # _save_turn + sessions.save), check if this was a subagent announcement.
            subagent_label = (msg.metadata or {}).get("_subagent_label")
            if msg.channel == "system" and msg.sender_id == "subagent" and subagent_label:
                key = (msg.metadata or {}).get("session_key") or ""
                if not key:
                    if ":" in msg.chat_id:
                        key = msg.chat_id.split(":", 1)[0] + ":" + msg.chat_id.split(":", 1)[1]
                    else:
                        key = f"cli:{msg.chat_id}"
                try:
                    session = self.sessions.get_or_create(key)
                    # Walk backwards through session.messages to find the user
                    # message that contains the subagent announcement content.
                    announce_prefix = f"[Subagent '{subagent_label}'"
                    for m in reversed(session.messages):
                        content = m.get("content", "")
                        if isinstance(content, str) and m.get("role") == "user" and content.startswith(announce_prefix):
                            m["role"] = "sub_tool"
                            m["name"] = subagent_label
                            break
                    self.sessions.save(session)
                except Exception as exc:
                    logger.warning("Failed to reclassify subagent message in session: {}", exc)

            return result

        AgentLoop._process_message = _process_message_patched  # type: ignore[method-assign]
        logger.debug("AgentLoop._process_message patched: subagent messages reclassified as sub_tool")
    except Exception as exc:
        logger.warning("Failed to patch AgentLoop._process_message: {}", exc)
