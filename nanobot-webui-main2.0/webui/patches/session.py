"""[Session] patches — keep WebUI-only roles out of LLM history."""

from __future__ import annotations


def apply() -> None:
    """Filter the synthetic ``sub_tool`` role before history reaches the LLM."""
    from nanobot.session import manager as _session_manager

    # --- sub_tool filter --------------------------------------------------
    # "sub_tool" is a synthetic role stored in session JSONL purely for UI
    # display (SubAgent tool-call chains).  The LLM only needs the final
    # assistant result — sub_tool entries are dropped from get_history().
    # The "system" bridge message is kept so there is no consecutive-
    # assistant sequence (main agent ends with assistant, SubAgent result
    # is also assistant — the system line separates them).
    _orig_get_history = _session_manager.Session.get_history

    def _get_history_patched(
        self,
        max_messages: int = 500,
        *,
        max_tokens: int = 0,
        include_timestamps: bool = False,
        extend_to_user: bool = False,
    ):  # type: ignore[override]
        history = _orig_get_history(
            self,
            max_messages=max_messages,
            max_tokens=max_tokens,
            include_timestamps=include_timestamps,
            extend_to_user=extend_to_user,
        )
        return [m for m in history if m.get("role") != "sub_tool"]

    _session_manager.Session.get_history = _get_history_patched  # type: ignore[method-assign]
