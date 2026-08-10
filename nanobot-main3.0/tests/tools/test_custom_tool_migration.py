from __future__ import annotations

from types import SimpleNamespace

import pytest

from nanobot.agent.tools.context import ToolContext
from nanobot.agent.tools.just_print_file import DirectToolResponse, JustPrintFileTool
from nanobot.agent.tools.loader import ToolLoader
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.open_html import OpenHtmlTool
from nanobot.agent.tools.win_ssh_linux import WinSshLinuxTool
from nanobot.config.schema import ToolsConfig


def test_tool_loader_discovers_migrated_custom_tools():
    discovered = {cls.__name__ for cls in ToolLoader().discover()}

    assert "JustPrintFileTool" in discovered
    assert "OpenHtmlTool" in discovered
    assert "WinSshLinuxTool" in discovered


def test_tool_loader_registers_migrated_custom_tools(tmp_path):
    ctx = ToolContext(
        config=ToolsConfig(),
        workspace=str(tmp_path),
        subagent_manager=SimpleNamespace(
            get_running_count=lambda: 0,
            max_concurrent_subagents=4,
        ),
        timezone="UTC",
    )
    registry = ToolRegistry()

    ToolLoader().load(ctx, registry)

    assert registry.has("just_print_file")
    assert registry.has("open_html")
    assert registry.has("win_ssh_linux")


@pytest.mark.asyncio
async def test_just_print_file_returns_direct_response_for_text(tmp_path):
    target = tmp_path / "love.txt"
    target.write_text("first line\nsecond line\n", encoding="utf-8")

    tool = JustPrintFileTool(workspace=tmp_path)
    result = await tool.execute(path=str(target))

    assert isinstance(result, DirectToolResponse)
    assert result.content == "first line\nsecond line\n"
    assert result.source_path.endswith("love.txt")
    assert "Direct file response" in (result.history_content or "")


@pytest.mark.asyncio
async def test_just_print_file_preserves_markdown_source(tmp_path):
    target = tmp_path / "story.md"
    target.write_text("# Title\n\n- one\n- two\n", encoding="utf-8")

    tool = JustPrintFileTool(workspace=tmp_path)
    result = await tool.execute(path=str(target))

    assert isinstance(result, DirectToolResponse)
    assert result.content == "# Title\n\n- one\n- two\n"
    assert "1|" not in result.content
    assert "End of file" not in result.content


@pytest.mark.asyncio
async def test_open_html_requires_target():
    result = await OpenHtmlTool(workspace=".").execute()

    assert result == "Error: Missing required parameter 'target'."


@pytest.mark.asyncio
async def test_win_ssh_linux_reports_missing_openssh_home(monkeypatch):
    monkeypatch.delenv("OPENSSH_HOME", raising=False)
    monkeypatch.setattr("os.path.exists", lambda path: False)

    result = await WinSshLinuxTool().execute(
        mode="ssh_exec",
        host="127.0.0.1",
        username="tester",
        keyName="missing.key",
        command="hostname",
    )

    assert "OPENSSH_HOME is not configured" in result
