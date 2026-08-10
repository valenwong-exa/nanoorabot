from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.runner_helpers import make_run_spec
from nanobot.agent.runner import AgentRunner
from nanobot.agent.tools.base import Tool
from nanobot.agent.tools.just_print_file import DirectToolResponse
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.config.schema import AgentDefaults
from nanobot.providers.base import LLMResponse, ToolCallRequest

_MAX_TOOL_RESULT_CHARS = AgentDefaults().max_tool_result_chars


class _DirectPrintTool(Tool):
    @property
    def name(self) -> str:
        return "just_print_file"

    @property
    def description(self) -> str:
        return "direct print"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    @property
    def read_only(self) -> bool:
        return True

    async def execute(self, **kwargs):
        return DirectToolResponse(
            content="1| once upon a time",
            source_path="temp/love.txt",
            history_content="[Direct file response from temp/love.txt]",
        )


@pytest.mark.asyncio
async def test_runner_short_circuits_on_direct_tool_response():
    provider = MagicMock()
    provider.chat_with_retry = AsyncMock(
        return_value=LLMResponse(
            content="",
            tool_calls=[ToolCallRequest(id="call_1", name="just_print_file", arguments={})],
            usage={},
        )
    )

    tools = ToolRegistry()
    tools.register(_DirectPrintTool())

    result = await AgentRunner().run(
        make_run_spec(
            provider,
            initial_messages=[{"role": "user", "content": "print the file"}],
            tools=tools,
            model="test-model",
            max_iterations=3,
            max_tool_result_chars=_MAX_TOOL_RESULT_CHARS,
        )
    )

    assert result.final_content == "1| once upon a time"
    assert result.stop_reason == "direct_tool_response"
    assert provider.chat_with_retry.await_count == 1
    assert any(
        msg.get("role") == "tool" and msg.get("name") == "just_print_file"
        for msg in result.messages
    )
