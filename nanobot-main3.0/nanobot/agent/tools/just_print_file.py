"""Direct-print file tool that returns file content as the final user reply."""

from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nanobot.agent.tools.filesystem import ReadFileTool, _is_blocked_device
from nanobot.utils.helpers import detect_image_mime


@dataclass(slots=True)
class DirectToolResponse:
    """Structured result instructing the runner to bypass another LLM turn."""

    content: str
    source_path: str
    history_content: str | None = None
    tool_name: str = "just_print_file"


class JustPrintFileTool(ReadFileTool):
    """Read a file and ask the runner to send its contents directly to the user."""

    _scopes = {"core", "subagent"}

    @property
    def name(self) -> str:
        return "just_print_file"

    @property
    def description(self) -> str:
        return (
            "Read a target file and return its text directly to the user as the final reply. "
            "Use this when the user explicitly wants the file contents shown verbatim, such as "
            "requests mentioning /print_file or 'read and display the file directly'. "
            "Only use it after you have already identified or generated the exact file to print. "
            "Do not use it for summaries or explanations."
        )

    def _validate_direct_path(self, path: str | None) -> Path | str:
        if not path:
            return "Error reading file: Unknown path"
        if _is_blocked_device(path):
            return f"Error: Reading {path} is blocked (device path that could hang or produce infinite output)."
        fp = self._resolve(path)
        if _is_blocked_device(fp):
            return f"Error: Reading {fp} is blocked (device path that could hang or produce infinite output)."
        if not fp.exists():
            return f"Error: File not found: {path}"
        if not fp.is_file():
            return f"Error: Not a file: {path}"
        return fp

    @staticmethod
    def _decode_text_content(raw: bytes, path: str) -> str:
        try:
            text_content = raw.decode("utf-8")
        except UnicodeDecodeError:
            mime = detect_image_mime(raw) or mimetypes.guess_type(path)[0]
            if mime and mime.startswith("image/"):
                return f"Error: Image content should be handled before text decoding: {path}"
            return (
                f"Error: Cannot read binary file {path} (MIME: {mime or 'unknown'}). "
                "Only UTF-8 text and images are supported."
            )

        return text_content.replace("\r\n", "\n")

    def _format_plain_text(self, text_content: str) -> str:
        if len(text_content) <= self._MAX_CHARS:
            return text_content
        return text_content[: self._MAX_CHARS] + "\n\n[Content truncated at ~128K chars]"

    async def execute(
        self,
        path: str | None = None,
        pages: str | None = None,
        force: bool = False,
        **kwargs: Any,
    ) -> Any:
        del force  # The direct-print path always returns fresh content.

        validated = self._validate_direct_path(path)
        if isinstance(validated, str):
            return validated
        fp = validated

        if fp.suffix.lower() == ".pdf":
            result = self._read_pdf(fp, pages)
        elif fp.suffix.lower() in {".docx", ".xlsx", ".pptx"}:
            result = self._read_office_doc(fp)
        else:
            raw = fp.read_bytes()
            if not raw:
                result = ""
            else:
                mime = detect_image_mime(raw) or mimetypes.guess_type(path)[0]
                if mime and mime.startswith("image/"):
                    return (
                        "Error: just_print_file only supports text-like file output. "
                        "Use read_file for images or other multimodal content."
                    )
                text_content = self._decode_text_content(raw, path)
                if text_content.startswith("Error:"):
                    return text_content
                result = self._format_plain_text(text_content)

        if isinstance(result, str) and not result.startswith("Error"):
            try:
                resolved = str(fp.resolve(strict=False))
            except Exception:
                resolved = str(path)
            return DirectToolResponse(
                content=result,
                source_path=resolved,
                history_content=f"[Direct file response from {resolved}]",
            )
        return result
