from __future__ import annotations

from types import SimpleNamespace

import pytest

from nanobot.agent.memory import MemoryStore
from nanobot.bus.events import InboundMessage
from nanobot.command.builtin import (
    build_help_text,
    cmd_forget_all,
    cmd_forget_history,
    cmd_forget_session,
    register_builtin_commands,
)
from nanobot.command.router import CommandContext, CommandRouter
from nanobot.session.manager import SessionManager


def _make_ctx(raw: str, tmp_path, *, key: str = "feishu:c1") -> CommandContext:
    msg = InboundMessage(channel="feishu", sender_id="u1", chat_id="c1", content=raw)
    sessions = SessionManager(tmp_path)
    memory = MemoryStore(tmp_path)
    loop = SimpleNamespace(
        sessions=sessions,
        context=SimpleNamespace(memory=memory),
    )
    session = sessions.get_or_create(key)
    return CommandContext(msg=msg, session=session, key=key, raw=raw, loop=loop)


@pytest.mark.asyncio
async def test_cmd_forget_session_clears_only_current_session(tmp_path) -> None:
    ctx = _make_ctx("/forget-session", tmp_path)
    ctx.session.add_message("user", "remember this")
    ctx.loop.sessions.save(ctx.session)

    other = ctx.loop.sessions.get_or_create("feishu:other")
    other.add_message("user", "keep this")
    ctx.loop.sessions.save(other)

    out = await cmd_forget_session(ctx)

    assert "Forgot current session memory" in out.content
    ctx.loop.sessions.invalidate("feishu:c1")
    ctx.loop.sessions.invalidate("feishu:other")
    assert ctx.loop.sessions.get_or_create("feishu:c1").messages == []
    assert len(ctx.loop.sessions.get_or_create("feishu:other").messages) == 1


@pytest.mark.asyncio
async def test_cmd_forget_history_clears_long_term_files(tmp_path) -> None:
    ctx = _make_ctx("/forget-history", tmp_path)
    ctx.loop.context.memory.write_memory("fact")
    ctx.loop.context.memory.append_history("event")
    ctx.loop.context.memory.set_last_dream_cursor(1)

    out = await cmd_forget_history(ctx)

    assert out.content == "Forgot long-term memory history."
    assert ctx.loop.context.memory.read_memory() == ""
    assert ctx.loop.context.memory.read_unprocessed_history(since_cursor=0) == []
    assert ctx.loop.context.memory.read_file(ctx.loop.context.memory._cursor_file).strip() == "0"
    assert ctx.loop.context.memory.read_file(ctx.loop.context.memory._dream_cursor_file).strip() == "0"


@pytest.mark.asyncio
async def test_cmd_forget_all_clears_session_and_history(tmp_path) -> None:
    ctx = _make_ctx("/forget-all", tmp_path)
    ctx.session.add_message("user", "remember this")
    ctx.loop.sessions.save(ctx.session)
    ctx.loop.context.memory.write_memory("fact")
    ctx.loop.context.memory.append_history("event")

    out = await cmd_forget_all(ctx)

    assert "cleared long-term history" in out.content
    ctx.loop.sessions.invalidate("feishu:c1")
    assert ctx.loop.sessions.get_or_create("feishu:c1").messages == []
    assert ctx.loop.context.memory.read_memory() == ""
    assert ctx.loop.context.memory.read_unprocessed_history(since_cursor=0) == []


def test_forget_commands_are_registered_as_exact_commands() -> None:
    router = CommandRouter()
    register_builtin_commands(router)

    assert "/forget-session" in router._exact
    assert "/forget-history" in router._exact
    assert "/forget-all" in router._exact
    assert router.is_priority("/forget-session") is False


@pytest.mark.asyncio
async def test_router_normalizes_please_call_forget_session_phrase(tmp_path) -> None:
    ctx = _make_ctx("请调用 /forget-session", tmp_path)
    ctx.session.add_message("user", "remember this")
    ctx.loop.sessions.save(ctx.session)

    router = CommandRouter()
    register_builtin_commands(router)
    out = await router.dispatch(ctx)

    assert out is not None
    assert "Forgot current session memory" in out.content
    ctx.loop.sessions.invalidate("feishu:c1")
    assert ctx.loop.sessions.get_or_create("feishu:c1").messages == []


def test_help_text_mentions_forget_commands() -> None:
    help_text = build_help_text()

    assert "/forget-session" in help_text
    assert "/forget-history" in help_text
    assert "/forget-all" in help_text
