"""Legacy dangerous tool policy loader reused by the compatibility WebUI."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

_WHITESPACE_RE = re.compile(r"\s+")
_ELLIPSIS_TOKEN = "__NANOBOT_POLICY_ELLIPSIS__"


def normalize_policy_text(value: str) -> str:
    """Collapse whitespace and lowercase so matching is case-insensitive."""
    return _WHITESPACE_RE.sub(" ", value).strip().lower()


def _iter_string_fields(value: Any, path: str = "arguments") -> list[tuple[str, str]]:
    if isinstance(value, str):
        text = value.strip()
        return [(path, text)] if text else []
    if isinstance(value, dict):
        found: list[tuple[str, str]] = []
        for key, item in value.items():
            child_path = f"{path}.{key}"
            found.extend(_iter_string_fields(item, child_path))
        return found
    if isinstance(value, list):
        found = []
        for index, item in enumerate(value):
            found.extend(_iter_string_fields(item, f"{path}[{index}]"))
        return found
    return []


@dataclass(slots=True)
class ToolPolicyRule:
    command: str
    category: str
    severity: str
    mode: str
    scope: str
    match_type: str = "literal"
    regex_flags: str = ""
    note: str = ""
    _normalized_command: str = field(init=False, repr=False)
    _pattern: re.Pattern[str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.match_type = (self.match_type or "literal").strip().lower()
        self.regex_flags = (self.regex_flags or "").strip().lower()
        normalized = normalize_policy_text(self.command)
        self._normalized_command = normalized
        if self.match_type == "regex":
            flags = 0
            if "i" in self.regex_flags or not self.regex_flags:
                flags |= re.IGNORECASE
            if "m" in self.regex_flags:
                flags |= re.MULTILINE
            if "s" in self.regex_flags:
                flags |= re.DOTALL
            self._pattern = re.compile(self.command, flags)
            return
        pattern_source = normalized.replace("...", _ELLIPSIS_TOKEN)
        pattern_source = re.escape(pattern_source)
        pattern_source = pattern_source.replace(re.escape(_ELLIPSIS_TOKEN), r".*?")
        pattern_source = pattern_source.replace(r"\ ", r"\s+")
        self._pattern = re.compile(pattern_source)

    def matches(self, value: str) -> bool:
        if self.match_type == "regex":
            return bool(value and self._pattern.search(value))
        normalized_value = normalize_policy_text(value)
        return bool(normalized_value and self._pattern.search(normalized_value))


@dataclass(slots=True)
class ToolPolicyDecision:
    action: str
    tool_name: str
    field_path: str
    matched_value: str
    rule: ToolPolicyRule


class DangerousToolPolicy:
    """Best-effort loader for dangerous tool policy rules."""

    def __init__(self, policy_path: str | Path | None = None) -> None:
        self.policy_path = Path(policy_path).expanduser().resolve(strict=False) if policy_path else None
        self._cached_rules: list[ToolPolicyRule] = []
        self._cached_mtime_ns: int | None = None
        self._last_error_key: str | None = None

    def evaluate(
        self,
        tool_name: str,
        params: dict[str, Any],
    ) -> ToolPolicyDecision | None:
        for field_path, value in _iter_string_fields(params):
            for rule in self._load_rules():
                if rule.matches(value):
                    return ToolPolicyDecision(
                        action=rule.mode,
                        tool_name=tool_name,
                        field_path=field_path,
                        matched_value=value,
                        rule=rule,
                    )
        return None

    def _load_rules(self) -> list[ToolPolicyRule]:
        path = self.policy_path
        if path is None or not path.exists():
            return []
        try:
            stat = path.stat()
        except OSError:
            return []
        if self._cached_mtime_ns == stat.st_mtime_ns:
            return self._cached_rules
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            raw_rules = payload.get("rules", [])
            if not isinstance(raw_rules, list):
                raise ValueError("rules must be a list")
            rules = [
                ToolPolicyRule(
                    command=str(item.get("command", "")).strip(),
                    match_type=str(item.get("matchType") or item.get("match_type") or "literal").strip().lower(),
                    regex_flags=str(item.get("regexFlags") or item.get("regex_flags") or "").strip().lower(),
                    category=str(item.get("category", "")).strip(),
                    severity=str(item.get("severity", "")).strip(),
                    mode=str(item.get("mode", "")).strip().lower(),
                    scope=str(item.get("scope", "")).strip(),
                    note=str(item.get("note", "")).strip(),
                )
                for item in raw_rules
                if isinstance(item, dict) and str(item.get("command", "")).strip()
            ]
        except Exception as exc:
            self._log_once(f"{path}:{type(exc).__name__}:{exc}", "Failed to load dangerous tool policy: {}", exc)
            return self._cached_rules
        self._cached_rules = rules
        self._cached_mtime_ns = stat.st_mtime_ns
        self._last_error_key = None
        return self._cached_rules

    def _log_once(self, key: str, message: str, *args: Any) -> None:
        if key == self._last_error_key:
            return
        self._last_error_key = key
        logger.error(message, *args)
