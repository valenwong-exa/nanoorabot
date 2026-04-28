import pytest

from nanobot.agent.tools.open_html import OpenHtmlTool


def _enable_linux_desktop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPLAY", ":0")


@pytest.mark.asyncio
async def test_open_local_html_path_uses_file_uri(tmp_path, monkeypatch):
    html_file = tmp_path / "chartjs_demo.html"
    html_file.write_text("<html><body>ok</body></html>", encoding="utf-8")
    opened: list[str] = []

    _enable_linux_desktop(monkeypatch)
    monkeypatch.setattr(
        "nanobot.agent.tools.open_html.webbrowser.open",
        lambda target: opened.append(target) or True,
    )

    tool = OpenHtmlTool(workspace=tmp_path, allowed_dir=tmp_path)
    result = await tool.execute(target="chartjs_demo.html")

    assert opened == [html_file.resolve().as_uri()]
    assert "Opened in default browser" in result


@pytest.mark.asyncio
async def test_open_file_uri_normalizes_to_local_file_uri(tmp_path, monkeypatch):
    html_file = tmp_path / "demo.html"
    html_file.write_text("<html></html>", encoding="utf-8")
    opened: list[str] = []

    _enable_linux_desktop(monkeypatch)
    monkeypatch.setattr(
        "nanobot.agent.tools.open_html.webbrowser.open",
        lambda target: opened.append(target) or True,
    )

    tool = OpenHtmlTool(workspace=tmp_path, allowed_dir=tmp_path)
    result = await tool.execute(target=html_file.resolve().as_uri())

    assert opened == [html_file.resolve().as_uri()]
    assert str(html_file) in result


@pytest.mark.asyncio
async def test_open_http_url_passes_through(monkeypatch):
    opened: list[str] = []

    _enable_linux_desktop(monkeypatch)
    monkeypatch.setattr(
        "nanobot.agent.tools.open_html.webbrowser.open",
        lambda target: opened.append(target) or True,
    )

    tool = OpenHtmlTool()
    result = await tool.execute(target="https://example.com/report")

    assert opened == ["https://example.com/report"]
    assert "https://example.com/report" in result


@pytest.mark.asyncio
async def test_open_html_reports_headless_linux(monkeypatch):
    monkeypatch.setattr("nanobot.agent.tools.open_html.sys.platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr(
        "nanobot.agent.tools.open_html.webbrowser.open",
        lambda target: (_ for _ in ()).throw(AssertionError("browser should not be called")),
    )

    tool = OpenHtmlTool()
    result = await tool.execute(target="https://example.com")

    assert "No Linux desktop browser session detected" in result
