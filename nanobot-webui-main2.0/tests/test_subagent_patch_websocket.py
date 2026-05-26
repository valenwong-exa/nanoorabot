from pathlib import Path
import sys

import pytest

from webui.patches import subagent

NANOBOT_ROOT = Path(__file__).resolve().parents[2] / "nanobot-main2.0"
if str(NANOBOT_ROOT) not in sys.path:
    sys.path.insert(0, str(NANOBOT_ROOT))
def test_resolve_subagent_chat_key_keeps_websocket_session_scope() -> None:
    assert (
        subagent._resolve_subagent_chat_key("websocket", "web:42:abc12345")
        == "websocket:web:42:abc12345"
    )
    assert subagent._resolve_subagent_chat_key("web", "web:42:abc12345") == "web:42"


@pytest.mark.asyncio
async def test_apply_routes_websocket_subagent_result_to_direct_callback() -> None:
    from nanobot.agent.subagent import SubagentManager

    subagent.apply()
    received: list[str] = []
    chat_key = "websocket:web:42:abc12345"

    async def _capture(text: str) -> None:
        received.append(text)

    subagent.register_announce(chat_key, _capture)
    try:
        manager = object.__new__(SubagentManager)
        await manager._announce_result(
            "task-1",
            "Chart Demo",
            "build a chart demo",
            "任务已完成",
            {"channel": "websocket", "chat_id": "web:42:abc12345"},
            "ok",
        )
    finally:
        subagent.unregister_announce(chat_key)

    assert received == ["✅ **[Chart Demo]**\n\n任务已完成"]
