from __future__ import annotations

import json

import pytest

from nanobot.agent.memory import MemoryStore
from nanobot.agent.tools.memory_cleaner import MemoryCleanerTool
from nanobot.session.manager import (
    SESSION_CLEAR_ON_FINALIZE_KEY,
    SESSION_SKIP_PERSIST_ONCE_KEY,
    SessionManager,
)


@pytest.mark.asyncio
async def test_memory_cleaner_clear_session_deletes_files_and_marks_current_session(tmp_path) -> None:
    sessions = SessionManager(tmp_path)
    store = MemoryStore(tmp_path)
    tool = MemoryCleanerTool(sessions=sessions, store=store)
    tool.set_context("feishu", "chat-1", "feishu:chat-1")

    session = sessions.get_or_create("feishu:chat-1")
    session.add_message("user", "remember me")
    sessions.save(session)

    result = await tool.execute(action="clear_session")

    assert result == "Cleared current session (feishu:chat-1)."
    assert SESSION_SKIP_PERSIST_ONCE_KEY in session.metadata
    assert SESSION_CLEAR_ON_FINALIZE_KEY in session.metadata
    assert not (tmp_path / "sessions" / "feishu_chat-1.jsonl").exists()
    assert "feishu:chat-1" not in sessions._cache


@pytest.mark.asyncio
async def test_memory_cleaner_clear_long_term_clears_memory_history_and_cursors(tmp_path) -> None:
    sessions = SessionManager(tmp_path)
    store = MemoryStore(tmp_path)
    tool = MemoryCleanerTool(sessions=sessions, store=store)

    store.write_memory("important fact")
    store.append_history("event 1")
    store.set_last_dream_cursor(1)

    result = await tool.execute(action="clear_long_term")

    assert result == "Cleared long-term memory."
    assert store.read_memory() == ""
    assert store.read_unprocessed_history(since_cursor=0) == []
    assert json.loads(store._cursor_file.read_text(encoding="utf-8")) == 0
    assert json.loads(store._dream_cursor_file.read_text(encoding="utf-8")) == 0
