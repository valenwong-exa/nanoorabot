"""Tool for clearing session or long-term memory."""

from __future__ import annotations

from typing import Any

from nanobot.agent.memory import MemoryStore
from nanobot.agent.tools.base import Tool, tool_parameters
from nanobot.agent.tools.schema import StringSchema, tool_parameters_schema
from nanobot.session.manager import (
    SESSION_CLEAR_ON_FINALIZE_KEY,
    SESSION_SKIP_PERSIST_ONCE_KEY,
    SessionManager,
)


@tool_parameters(
    tool_parameters_schema(
        action=StringSchema(
            "What to clear: current session, long-term memory, or both.",
            enum=["clear_session", "clear_long_term", "clear_all"],
        ),
        session_key=StringSchema(
            "Optional explicit session key. Defaults to the current conversation session.",
            nullable=True,
        ),
        required=["action"],
    )
)
class MemoryCleanerTool(Tool):
    """Clear current session memory and/or long-term memory files."""

    def __init__(self, sessions: SessionManager, store: MemoryStore):
        self._sessions = sessions
        self._store = store
        self._channel = "cli"
        self._chat_id = "direct"
        self._session_key = "cli:direct"

    def set_context(self, channel: str, chat_id: str, session_key: str | None = None) -> None:
        """Capture the current routing/session context for default clearing."""
        self._channel = channel
        self._chat_id = chat_id
        if session_key is not None:
            self._session_key = session_key

    @property
    def name(self) -> str:
        return "memory_cleaner"

    @property
    def description(self) -> str:
        return (
            "Forget memory on request. "
            "Use clear_session when the user asks to forget or clear the current conversation memory. "
            "Use clear_long_term when the user asks to forget history or long-term memory; "
            "this clears memory/MEMORY.md, memory/history.jsonl, and related cursors. "
            "Use clear_all to do both."
        )

    @property
    def exclusive(self) -> bool:
        return True

    async def execute(
        self,
        action: str,
        session_key: str | None = None,
        **_kwargs: Any,
    ) -> str:
        target_key = session_key or self._session_key
        cleared_parts: list[str] = []

        if action in {"clear_session", "clear_all"}:
            session = self._sessions.get_or_create(target_key)
            session.clear_state()
            session.metadata[SESSION_SKIP_PERSIST_ONCE_KEY] = True
            session.metadata[SESSION_CLEAR_ON_FINALIZE_KEY] = True
            self._sessions.invalidate(target_key)
            self._sessions.delete_files(target_key)
            cleared_parts.append(f"current session ({target_key})")

        if action in {"clear_long_term", "clear_all"}:
            self._store.clear_long_term_memory()
            cleared_parts.append("long-term memory")

        if not cleared_parts:
            return f"Error: Unknown action '{action}'"

        return "Cleared " + " and ".join(cleared_parts) + "."
