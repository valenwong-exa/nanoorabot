from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

NANOBOT_ROOT = Path(__file__).resolve().parents[3] / "nanobot-main3.0"
if str(NANOBOT_ROOT) not in sys.path:
    sys.path.insert(0, str(NANOBOT_ROOT))

from nanobot.agent.hook import AgentHookContext, AgentTurnHookContext
from nanobot.agent.loop import AgentLoop
from nanobot.providers.base import ToolCallRequest
from nanobot.session.manager import SessionManager
from webui.__main__ import _agentloop_supports_init_kwarg
from webui.legacy_tool_policy_hook import create_legacy_tool_policy_hook_factory


def test_main3_hook_factory_support_survives_webui_monkey_patches() -> None:
    """The real WebUI import order must preserve main3's constructor contract."""
    parameters = inspect.signature(AgentLoop.__init__).parameters

    assert "hook_factories" in parameters
    assert _agentloop_supports_init_kwarg(AgentLoop, "hook_factories") is True


def test_agentloop_capability_check_accepts_kwargs_wrappers() -> None:
    """A future wrapper using **kwargs must not silently disable safety hooks."""

    class KwargsOnlyAgentLoop:
        def __init__(self, *args, **kwargs) -> None:
            pass

    assert _agentloop_supports_init_kwarg(KwargsOnlyAgentLoop, "hook_factories") is True


@pytest.mark.asyncio
async def test_sqlcl_truncate_is_blocked_before_tool_execution(tmp_path: Path) -> None:
    policy_path = tmp_path / "tool_policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "version": 1,
                "name": "dangerous_tool_policy",
                "rules": [
                    {
                        "command": "truncate table",
                        "matchType": "literal",
                        "regexFlags": "",
                        "category": "oracle",
                        "severity": "critical",
                        "mode": "block",
                        "scope": "SQL",
                        "note": "High-risk data clearing operation",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    session_manager = SessionManager(tmp_path / "workspace")
    factory = create_legacy_tool_policy_hook_factory(policy_path, session_manager)
    hook = factory(AgentTurnHookContext(session_key="web:test:truncate"))
    assert hook is not None

    tool_call = ToolCallRequest(
        id="tool-test-truncate",
        name="mcp_oracle-sqlcl_run-sql",
        arguments={
            "sql": "truncate table VALEN.TEST1;",
            "model": "DeepSeek",
        },
    )

    with pytest.raises(RuntimeError, match="blocked and not executed"):
        await hook.before_execute_tool(
            AgentHookContext(
                iteration=1,
                messages=[],
                session_key="web:test:truncate",
            ),
            tool_call,
            None,
            tool_call.arguments,
        )
