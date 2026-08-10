"""Compatibility hook that restores legacy dangerous-tool blocking on main3."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nanobot.agent.hook import AgentHook, AgentHookContext, AgentTurnHookContext
from nanobot.session.manager import SessionManager
from nanobot.providers.base import ToolCallRequest

from webui.legacy_tool_policy import DangerousToolPolicy, ToolPolicyDecision
from webui.legacy_tool_approval import (
    approved_tool_call,
    clear_approved_tool_call,
    set_pending_tool_approval,
)


class LegacyToolPolicyHook(AgentHook):
    """Apply legacy dangerous-tool policy before tool execution."""

    def __init__(self, policy_path: Path, session_manager: SessionManager) -> None:
        super().__init__(reraise=True)
        self._policy = DangerousToolPolicy(policy_path)
        self._sessions = session_manager

    async def before_execute_tool(
        self,
        context: AgentHookContext,
        tool_call: ToolCallRequest,
        tool: Any,
        params: Any,
    ) -> None:
        if not isinstance(params, dict):
            return
        decision = self._policy.evaluate(tool_call.name, params)
        if decision is None:
            return
        session = (
            self._sessions.get_or_create(context.session_key)
            if context.session_key
            else None
        )
        if decision.action == "block":
            if session is not None:
                clear_approved_tool_call(session)
                self._sessions.save(session)
            raise RuntimeError(self._build_block_message(decision))
        if decision.action == "warn":
            if session is not None and self._is_approved_once(session, tool_call.name, params):
                clear_approved_tool_call(session)
                self._sessions.save(session)
                return
            if session is not None:
                set_pending_tool_approval(
                    session,
                    {
                        "tool_name": tool_call.name,
                        "arguments": dict(params),
                    },
                )
                clear_approved_tool_call(session)
                self._sessions.save(session)
            raise RuntimeError(self._build_warn_message(decision))

    @staticmethod
    def _is_approved_once(session, tool_name: str, params: dict[str, Any]) -> bool:
        payload = approved_tool_call(session)
        if not isinstance(payload, dict):
            return False
        approved_name = payload.get("tool_name")
        approved_args = payload.get("arguments")
        return approved_name == tool_name and approved_args == params

    @staticmethod
    def _build_block_message(decision: ToolPolicyDecision) -> str:
        return (
            "A risky tool call was blocked and not executed.\n"
            f"Tool: {decision.tool_name}\n"
            f"Matched rule: {decision.rule.command} ({decision.rule.scope}/{decision.rule.category})\n"
            f"Matched field: {decision.field_path}\n"
            f"Action: block\n"
            f"Reason: {decision.rule.note or 'High-risk operation'}\n"
            "To proceed, update the tool policy first and accept the risk yourself."
        )

    @staticmethod
    def _build_warn_message(decision: ToolPolicyDecision) -> str:
        return (
            "A risky tool call was detected and paused.\n"
            f"Tool: {decision.tool_name}\n"
            f"Matched rule: {decision.rule.command} ({decision.rule.scope}/{decision.rule.category})\n"
            f"Matched field: {decision.field_path}\n"
            f"Action: warn\n"
            f"Reason: {decision.rule.note or 'Manual confirmation is required'}\n"
            "Reply with `approve` or `同意执行` to continue, or `cancel` / `拒绝` to stop it."
        )


def create_legacy_tool_policy_hook_factory(
    policy_path: str | Path | None,
    session_manager: SessionManager,
):
    """Return a turn-hook factory for the given policy file."""
    resolved = Path(policy_path).expanduser().resolve(strict=False) if policy_path else None

    def _factory(context: AgentTurnHookContext) -> AgentHook | None:
        if resolved is None or not resolved.exists():
            return None
        return LegacyToolPolicyHook(resolved, session_manager)

    return _factory
