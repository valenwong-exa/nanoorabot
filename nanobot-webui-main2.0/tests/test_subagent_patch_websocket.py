from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from webui.patches import subagent
from webui.api.routes import ws

NANOBOT_ROOT = Path(__file__).resolve().parents[2] / "nanobot-main3.0"
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


@pytest.mark.asyncio
async def test_apply_run_subagent_matches_current_manager_signature() -> None:
    from nanobot.agent.subagent import SubagentManager

    subagent.apply()
    manager = object.__new__(SubagentManager)
    manager.workspace = Path("e:/nanobot-main")
    manager.max_iterations = 3
    manager.max_tool_result_chars = 1024
    manager.fail_on_tool_error = True
    manager._llm_wall_timeout_for_session = None
    manager._build_tools = lambda workspace=None, tools_config=None: "tools"
    manager._build_subagent_prompt = lambda workspace=None: "system prompt"

    captured_spec: list[object] = []

    class _FakeRunner:
        async def run(self, spec):
            captured_spec.append(spec)
            return SimpleNamespace(
                messages=[
                    {"role": "assistant", "content": "数据库字符集已检查"},
                ],
                stop_reason="completed",
                tool_events=[],
                usage={},
                final_content="数据库字符集已检查",
                error=None,
            )

    manager.runner = _FakeRunner()

    announced: list[tuple[str, str]] = []

    async def _fake_announce_result(*args):
        announced.append((args[1], args[5]))

    manager._announce_result = _fake_announce_result

    runtime = SimpleNamespace()
    await manager._run_subagent(
        "task-1",
        "检查数据库字符集",
        "字符集检查",
        {"channel": "websocket", "chat_id": "web:42:abc12345", "session_key": "web:42:abc12345"},
        SimpleNamespace(phase="initializing", iteration=0, stop_reason=None, tool_events=[], usage={}),
        runtime,
        "msg-1",
        None,
    )

    assert len(captured_spec) == 1
    assert captured_spec[0].runtime is runtime
    assert captured_spec[0].workspace == Path("e:/nanobot-main")
    assert announced == [("字符集检查", "ok")]


def test_ws_subagent_callbacks_live_for_websocket_session(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(
        "webui.patches.subagent.register_progress",
        lambda chat_key, callback: calls.append(("register_progress", chat_key)),
    )
    monkeypatch.setattr(
        "webui.patches.subagent.register_save_turn",
        lambda chat_key, callback: calls.append(("register_save_turn", chat_key)),
    )
    monkeypatch.setattr(
        "webui.patches.subagent.register_announce",
        lambda chat_key, callback: calls.append(("register_announce", chat_key)),
    )
    monkeypatch.setattr(
        "webui.patches.subagent.unregister_progress",
        lambda chat_key: calls.append(("unregister_progress", chat_key)),
    )
    monkeypatch.setattr(
        "webui.patches.subagent.unregister_save_turn",
        lambda chat_key: calls.append(("unregister_save_turn", chat_key)),
    )
    monkeypatch.setattr(
        "webui.patches.subagent.unregister_announce",
        lambda chat_key: calls.append(("unregister_announce", chat_key)),
    )

    registered_keys: set[str] = set()
    chat_key = "websocket:web:42:abc12345"

    async def _noop(*args, **kwargs):
        return None

    ws._register_subagent_callbacks(registered_keys, chat_key, _noop, _noop, _noop)
    ws._register_subagent_callbacks(registered_keys, chat_key, _noop, _noop, _noop)

    assert registered_keys == {chat_key}
    assert calls == [
        ("register_progress", chat_key),
        ("register_save_turn", chat_key),
        ("register_announce", chat_key),
    ]

    ws._unregister_subagent_callbacks(registered_keys)

    assert registered_keys == set()
    assert calls[-3:] == [
        ("unregister_progress", chat_key),
        ("unregister_save_turn", chat_key),
        ("unregister_announce", chat_key),
    ]
