"""Dangerous tool policy persistence helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RULES: list[dict[str, Any]] = [
    {
        "command": "truncate table",
        "matchType": "literal",
        "regexFlags": "",
        "category": "oracle",
        "severity": "critical",
        "mode": "block",
        "scope": "SQL",
        "note": "高风险数据清空操作",
    },
    {
        "command": "drop table",
        "matchType": "literal",
        "regexFlags": "",
        "category": "oracle",
        "severity": "critical",
        "mode": "block",
        "scope": "SQL",
        "note": "直接删除表结构与数据",
    },
    {
        "command": "delete from",
        "matchType": "literal",
        "regexFlags": "",
        "category": "oracle",
        "severity": "high",
        "mode": "warn",
        "scope": "SQL",
        "note": "大批量删除需要人工确认",
    },
    {
        "command": r"\bupdate\b[\s\S]*?\bset\b(?:(?!\bwhere\b)[\s\S])*$",
        "matchType": "regex",
        "regexFlags": "i",
        "category": "oracle",
        "severity": "high",
        "mode": "warn",
        "scope": "SQL",
        "note": "避免整表更新",
    },
    {
        "command": "rm -rf",
        "matchType": "literal",
        "regexFlags": "",
        "category": "filesystem",
        "severity": "critical",
        "mode": "block",
        "scope": "Shell",
        "note": "危险递归删除命令",
    },
    {
        "command": "shutdown -h now",
        "matchType": "literal",
        "regexFlags": "",
        "category": "linux",
        "severity": "critical",
        "mode": "block",
        "scope": "Shell",
        "note": "主机关机命令",
    },
    {
        "command": "reboot",
        "matchType": "literal",
        "regexFlags": "",
        "category": "linux",
        "severity": "high",
        "mode": "warn",
        "scope": "Shell",
        "note": "主机重启前要求提示",
    },
]


@dataclass(slots=True)
class ToolPolicyConfig:
    version: int
    name: str
    source: str
    description: str
    rules: list[dict[str, Any]]
    updated_at: str | None = None

    def to_storage_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "source": self.source,
            "description": self.description,
            "updated_at": self.updated_at,
            "rules": self.rules,
        }


DEFAULT_TOOL_POLICY = ToolPolicyConfig(
    version=1,
    name="dangerous_tool_policy",
    source="webui-defense-page",
    description="Initial dangerous command policy seeded from the WebUI Defense page demo rules.",
    rules=DEFAULT_RULES,
)


class ToolPolicyService:
    """Read and write the dangerous tool policy JSON file."""

    def __init__(self, policy_path: Path | None) -> None:
        self.policy_path = policy_path

    def ensure_available(self) -> Path:
        if self.policy_path is None:
            raise RuntimeError("Tool policy path is not configured")
        return self.policy_path

    def load(self) -> ToolPolicyConfig:
        path = self.ensure_available()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            config = self._with_timestamp(DEFAULT_TOOL_POLICY)
            self._write(path, config)
            return config

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid tool policy JSON: {exc}") from exc
        return self._from_payload(payload)

    def save(self, payload: dict[str, Any]) -> ToolPolicyConfig:
        path = self.ensure_available()
        path.parent.mkdir(parents=True, exist_ok=True)
        config = self._with_timestamp(self._from_payload(payload))
        self._write(path, config)
        return config

    def _from_payload(self, payload: dict[str, Any]) -> ToolPolicyConfig:
        version = payload.get("version", DEFAULT_TOOL_POLICY.version)
        name = str(payload.get("name", DEFAULT_TOOL_POLICY.name)).strip() or DEFAULT_TOOL_POLICY.name
        source = str(payload.get("source", DEFAULT_TOOL_POLICY.source)).strip() or DEFAULT_TOOL_POLICY.source
        description = str(payload.get("description", DEFAULT_TOOL_POLICY.description)).strip()
        updated_at = payload.get("updated_at") or payload.get("updatedAt")
        raw_rules = payload.get("rules", DEFAULT_RULES)

        try:
            version_num = int(version)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("Tool policy version must be a valid integer") from exc

        if not isinstance(raw_rules, list):
            raise RuntimeError("Tool policy rules must be a list")

        rules: list[dict[str, Any]] = []
        for index, item in enumerate(raw_rules):
            if not isinstance(item, dict):
                raise RuntimeError(f"Rule #{index + 1} must be an object")
            command = str(item.get("command", "")).strip()
            match_type = str(item.get("matchType") or item.get("match_type") or "literal").strip().lower()
            regex_flags = str(item.get("regexFlags") or item.get("regex_flags") or "").strip().lower()
            category = str(item.get("category", "")).strip()
            severity = str(item.get("severity", "")).strip()
            mode = str(item.get("mode", "")).strip()
            scope = str(item.get("scope", "")).strip()
            note = str(item.get("note", "")).strip()
            if not command:
                raise RuntimeError(f"Rule #{index + 1} command is required")
            if match_type not in {"literal", "regex"}:
                raise RuntimeError(f"Rule #{index + 1} matchType must be literal or regex")
            if any(flag not in {"i", "m", "s"} for flag in regex_flags):
                raise RuntimeError(f"Rule #{index + 1} regexFlags only supports i, m, s")
            if match_type == "regex":
                try:
                    import re

                    flags = 0
                    if "i" in regex_flags:
                        flags |= re.IGNORECASE
                    if "m" in regex_flags:
                        flags |= re.MULTILINE
                    if "s" in regex_flags:
                        flags |= re.DOTALL
                    re.compile(command, flags)
                except re.error as exc:
                    raise RuntimeError(f"Rule #{index + 1} regex is invalid: {exc}") from exc
            if not category:
                raise RuntimeError(f"Rule #{index + 1} category is required")
            if not severity:
                raise RuntimeError(f"Rule #{index + 1} severity is required")
            if not mode:
                raise RuntimeError(f"Rule #{index + 1} mode is required")
            if not scope:
                raise RuntimeError(f"Rule #{index + 1} scope is required")
            rules.append(
                {
                    "command": command,
                    "matchType": match_type,
                    "regexFlags": regex_flags,
                    "category": category,
                    "severity": severity,
                    "mode": mode,
                    "scope": scope,
                    "note": note,
                }
            )

        return ToolPolicyConfig(
            version=version_num,
            name=name,
            source=source,
            description=description or DEFAULT_TOOL_POLICY.description,
            rules=rules,
            updated_at=str(updated_at) if updated_at else None,
        )

    def _with_timestamp(self, config: ToolPolicyConfig) -> ToolPolicyConfig:
        return ToolPolicyConfig(
            version=config.version,
            name=config.name,
            source=config.source,
            description=config.description,
            rules=config.rules,
            updated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )

    def _write(self, path: Path, config: ToolPolicyConfig) -> None:
        path.write_text(
            json.dumps(config.to_storage_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
