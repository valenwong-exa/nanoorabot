"""Browser-opening tool for local HTML files and web URLs."""

from __future__ import annotations

import asyncio
import os
import re
import sys
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from nanobot.agent.tools.base import tool_parameters
from nanobot.agent.tools.filesystem import _FsTool
from nanobot.agent.tools.schema import StringSchema, tool_parameters_schema


def _is_web_url(target: str) -> bool:
    parsed = urlparse(target)
    return parsed.scheme in {"http", "https"}


def _is_file_url(target: str) -> bool:
    return urlparse(target).scheme == "file"


def _file_url_to_path(target: str) -> Path:
    parsed = urlparse(target)
    if parsed.scheme != "file":
        raise ValueError(f"Unsupported URI scheme: {parsed.scheme or 'none'}")

    if parsed.netloc and parsed.netloc not in {"", "localhost"}:
        raw = f"//{parsed.netloc}{parsed.path}"
    else:
        raw = parsed.path
    raw = unquote(raw)

    if os.name == "nt" and re.match(r"^/[A-Za-z]:", raw):
        raw = raw[1:]

    return Path(raw)


@tool_parameters(
    tool_parameters_schema(
        target=StringSchema(
            "HTML file path, file:// URI, or http/https URL to open in the default browser"
        ),
        required=["target"],
    )
)
class OpenHtmlTool(_FsTool):
    """Open a local HTML file or URL using Python's webbrowser module."""
    _scopes = {"core", "subagent"}

    @property
    def name(self) -> str:
        return "open_html"

    @property
    def description(self) -> str:
        return (
            "Open a local HTML file or a http/https URL in the system default browser. "
            "Prefer this tool instead of using exec with cmd, PowerShell, start, or xdg-open "
            "when you need to preview generated HTML."
        )

    def _normalize_local_target(self, target: str) -> tuple[Path, str]:
        if _is_file_url(target):
            resolved = self._resolve(str(_file_url_to_path(target)))
        else:
            resolved = self._resolve(target)

        if not resolved.exists():
            raise FileNotFoundError(f"File not found: {target}")
        if not resolved.is_file():
            raise ValueError(f"Not a file: {target}")
        return resolved, resolved.as_uri()

    @staticmethod
    def _linux_desktop_ready() -> bool:
        if not sys.platform.startswith("linux"):
            return True
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    async def execute(
        self,
        target: str | None = None,
        path: str | None = None,
        url: str | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            chosen = target or path or url
            if not chosen:
                return "Error: Missing required parameter 'target'."

            if _is_web_url(chosen):
                open_target = chosen
                display_target = chosen
            else:
                local_path, open_target = self._normalize_local_target(chosen)
                display_target = str(local_path)

            if not self._linux_desktop_ready():
                return (
                    "Error: No Linux desktop browser session detected. "
                    "Set DISPLAY or WAYLAND_DISPLAY before using open_html."
                )

            opened = await asyncio.to_thread(webbrowser.open, open_target)
            if not opened:
                return (
                    "Error: Python webbrowser could not hand off the request to a browser. "
                    "Please confirm a default browser is available on this system."
                )

            return f"Opened in default browser: {display_target}"
        except PermissionError as e:
            return f"Error: {e}"
        except Exception as e:
            return f"Error: {e}"
