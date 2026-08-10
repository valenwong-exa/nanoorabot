"""[ToolApproval] restore legacy warn/approve/cancel flow on main3."""

from __future__ import annotations

import dataclasses


def apply() -> None:
    from nanobot.agent.loop import AgentLoop
    from nanobot.bus.events import OutboundMessage

    from webui.legacy_tool_approval import (
        approved_tool_call,
        build_approved_note,
        clear_approved_tool_call,
        clear_pending_tool_approval,
        interpret_tool_approval_reply,
        pending_tool_approval,
        set_pending_tool_approval,
        set_approved_tool_call,
    )

    if getattr(AgentLoop, "_webui_tool_approval_patch_applied", False):
        return

    AgentLoop._pending_tool_approval = staticmethod(pending_tool_approval)
    AgentLoop._set_pending_tool_approval = staticmethod(set_pending_tool_approval)
    AgentLoop._clear_pending_tool_approval = staticmethod(clear_pending_tool_approval)
    AgentLoop._approved_tool_call = staticmethod(approved_tool_call)
    AgentLoop._set_approved_tool_call = staticmethod(set_approved_tool_call)
    AgentLoop._clear_approved_tool_call = staticmethod(clear_approved_tool_call)
    AgentLoop._interpret_tool_approval_reply = staticmethod(interpret_tool_approval_reply)

    _orig_dispatch_command = AgentLoop._dispatch_command

    async def _dispatch_command_patched(self, ctx):
        session = ctx.require_session()
        raw = ctx.msg.content.strip()
        pending = self._pending_tool_approval(session)
        if pending is not None:
            decision = self._interpret_tool_approval_reply(raw)
            if decision == "approve":
                self._set_approved_tool_call(session, pending)
                self._clear_pending_tool_approval(session)
                self.sessions.save(session)
                ctx.msg = dataclasses.replace(
                    ctx.msg,
                    content=build_approved_note(raw, pending),
                )
            elif decision == "deny":
                self._clear_pending_tool_approval(session)
                self._clear_approved_tool_call(session)
                self.sessions.save(session)
                ctx.outbound = OutboundMessage(
                    channel=ctx.msg.channel,
                    chat_id=ctx.msg.chat_id,
                    content="The risky tool call was canceled. No dangerous command was executed.",
                    metadata=dict(ctx.msg.metadata or {}),
                )
                return True
            else:
                ctx.outbound = OutboundMessage(
                    channel=ctx.msg.channel,
                    chat_id=ctx.msg.chat_id,
                    content=(
                        "A risky tool call is waiting for your approval.\n"
                        "To continue, reply with `approve` or `同意执行`. "
                        "To reject it, reply with `cancel` or `拒绝`."
                    ),
                    metadata=dict(ctx.msg.metadata or {}),
                )
                return True
        return await _orig_dispatch_command(self, ctx)

    AgentLoop._dispatch_command = _dispatch_command_patched
    AgentLoop._webui_tool_approval_patch_applied = True
