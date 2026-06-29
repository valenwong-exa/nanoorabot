from __future__ import annotations

import pytest

from nanobot.agent.tools.just_print_file import DirectToolResponse, JustPrintFileTool


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
