"""Runtime-specific helper functions and constants."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.utils.helpers import stringify_text_blocks

_MAX_REPEAT_EXTERNAL_LOOKUPS = 2

# Third same-target workspace violation in a turn escalates to "stop retrying".
_MAX_REPEAT_WORKSPACE_VIOLATIONS = 2
_MAX_REPEAT_IDENTICAL_FILE_READS = 3
_FILE_EDIT_TOOL_NAMES = frozenset({"apply_patch", "edit_file", "write_file"})
_FILE_TOUCH_TOOL_NAMES = frozenset({"read_file"}) | _FILE_EDIT_TOOL_NAMES
_MAX_REPEAT_FAILED_FILE_EDITS = 3

EMPTY_FINAL_RESPONSE_MESSAGE = (
    "I completed the tool steps but couldn't produce a final answer. "
    "Please try again or narrow the task."
)

FINALIZATION_RETRY_PROMPT = (
    "Please provide your response to the user based on the conversation above."
)

BUDGET_EXHAUSTED_FINALIZATION_PROMPT = (
    "The tool-call budget for this turn is exhausted. Based only on the "
    "conversation and tool results above, provide a concise final response to "
    "the user. Do not call or request tools. Do not claim the task is complete "
    "unless the evidence above clearly shows it is complete. State what was "
    "done, what remains, and the best next step if anything is incomplete."
)

LENGTH_RECOVERY_PROMPT = (
    "Output limit reached. Continue exactly where you left off "
    "— no recap, no apology. Break remaining work into smaller steps if needed."
)

SUSTAINED_GOAL_CONTINUE_PROMPT = (
    "You have an active sustained goal. Please continue working toward the "
    "objective using your tools, or call complete_goal if the work is truly finished."
)


def empty_tool_result_message(tool_name: str) -> str:
    """Short prompt-safe marker for tools that completed without visible output."""
    return f"({tool_name} completed with no output)"


def ensure_nonempty_tool_result(tool_name: str, content: Any) -> Any:
    """Replace semantically empty tool results with a short marker string."""
    if content is None:
        return empty_tool_result_message(tool_name)
    if isinstance(content, str) and not content.strip():
        return empty_tool_result_message(tool_name)
    if isinstance(content, list):
        if not content:
            return empty_tool_result_message(tool_name)
        text_payload = stringify_text_blocks(content)
        if text_payload is not None and not text_payload.strip():
            return empty_tool_result_message(tool_name)
    return content


def is_blank_text(content: str | None) -> bool:
    """True when *content* is missing or only whitespace."""
    return content is None or not content.strip()


def build_finalization_retry_message() -> dict[str, str]:
    """A short no-tools-allowed prompt for final answer recovery."""
    return {"role": "user", "content": FINALIZATION_RETRY_PROMPT}


def build_budget_exhausted_finalization_message() -> dict[str, str]:
    """Prompt the model for a no-tools final response after budget exhaustion."""
    return {"role": "user", "content": BUDGET_EXHAUSTED_FINALIZATION_PROMPT}


def build_length_recovery_message() -> dict[str, str]:
    """Prompt the model to continue after hitting output token limit."""
    return {"role": "user", "content": LENGTH_RECOVERY_PROMPT}


def build_goal_continue_message(custom: str | None = None) -> dict[str, str]:
    """Prompt the model to continue when a sustained goal is still active."""
    return {"role": "user", "content": custom or SUSTAINED_GOAL_CONTINUE_PROMPT}


def external_lookup_signature(tool_name: str, arguments: Any) -> str | None:
    """Stable signature for repeated external lookups we want to throttle."""
    if not isinstance(arguments, dict):
        return None
    if tool_name == "web_fetch":
        url = str(arguments.get("url") or "").strip()
        if url:
            return f"web_fetch:{url.lower()}"
    if tool_name == "web_search":
        query = str(arguments.get("query") or arguments.get("search_term") or "").strip()
        if query:
            return f"web_search:{query.lower()}"
    return None


def repeated_external_lookup_error(
    tool_name: str,
    arguments: Any,
    seen_counts: dict[str, int],
) -> str | None:
    """Block repeated external lookups after a small retry budget."""
    signature = external_lookup_signature(tool_name, arguments)
    if signature is None:
        return None
    count = seen_counts.get(signature, 0) + 1
    seen_counts[signature] = count
    if count <= _MAX_REPEAT_EXTERNAL_LOOKUPS:
        return None
    logger.warning(
        "Blocking repeated external lookup {} on attempt {}",
        signature[:160],
        count,
    )
    return (
        "Error: repeated external lookup blocked. "
        "Use the results you already have to answer, or try a meaningfully different source."
    )


# Workspace-boundary violations are soft errors, with per-target throttling.

_OUTSIDE_PATH_PATTERN = re.compile(r"(?:^|[\s|>'\"])((?:/[^\s\"'>;|<]+)|(?:~[^\s\"'>;|<]+))")


def workspace_violation_signature(
    tool_name: str,
    arguments: Any,
) -> str | None:
    """Return a stable cross-tool signature for the outside-workspace target."""
    if not isinstance(arguments, dict):
        return None
    for key in ("path", "file_path", "target", "source", "destination"):
        val = arguments.get(key)
        if isinstance(val, str) and val.strip():
            return _normalize_violation_target(val.strip())

    if tool_name in {"exec", "shell"}:
        cmd = str(arguments.get("command") or "").strip()
        if cmd:
            match = _OUTSIDE_PATH_PATTERN.search(cmd)
            if match:
                return _normalize_violation_target(match.group(1))
        cwd = str(arguments.get("working_dir") or "").strip()
        if cwd:
            return _normalize_violation_target(cwd)

    return None


def _normalize_violation_target(raw: str) -> str:
    """Normalize *raw* path so that equivalent spellings collide on the same key."""
    try:
        normalized = Path(raw).expanduser().resolve().as_posix()
    except Exception:
        normalized = raw.replace("\\", "/")
    return f"violation:{normalized}".lower()


def repeated_workspace_violation_error(
    tool_name: str,
    arguments: Any,
    seen_counts: dict[str, int],
) -> str | None:
    """Return an escalated error after repeated bypass attempts."""
    signature = workspace_violation_signature(tool_name, arguments)
    if signature is None:
        return None
    count = seen_counts.get(signature, 0) + 1
    seen_counts[signature] = count
    if count <= _MAX_REPEAT_WORKSPACE_VIOLATIONS:
        return None
    logger.warning(
        "Escalating repeated workspace bypass attempt {} (attempt {})",
        signature[:160],
        count,
    )
    target = signature.split("violation:", 1)[1] if "violation:" in signature else signature
    return (
        "Error: refusing repeated workspace-bypass attempts.\n"
        f"You have tried to access '{target}' (or an equivalent path) "
        f"{count} times in this turn. This is a hard policy boundary -- "
        "switching tools, shell tricks, working_dir overrides, symlinks, "
        "or base64 piping will NOT change the answer. Stop retrying. "
        "If the user genuinely needs this resource, tell them you cannot "
        "access it and ask how they want to proceed (e.g. copy the file "
        "into the workspace, or disable restrict_to_workspace for this run)."
    )


def _normalize_file_target(raw: str) -> str:
    """Normalize file path spellings so equivalent targets share one budget."""
    try:
        normalized = Path(raw).expanduser().resolve(strict=False).as_posix()
    except Exception:
        normalized = raw.replace("\\", "/")
    return normalized.lower()


def _file_touch_targets(tool_name: str, arguments: Any) -> list[str]:
    """Return normalized file targets touched by a file-oriented tool call."""
    if tool_name not in _FILE_TOUCH_TOOL_NAMES or not isinstance(arguments, dict):
        return []
    if tool_name == "apply_patch":
        edits = arguments.get("edits")
        if not isinstance(edits, list):
            return []
        targets: list[str] = []
        for edit in edits:
            if not isinstance(edit, dict):
                continue
            path = edit.get("path")
            if isinstance(path, str) and path.strip():
                targets.append(_normalize_file_target(path.strip()))
        return list(dict.fromkeys(targets))

    for key in ("path", "file_path"):
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return [_normalize_file_target(value.strip())]
    return []


def _file_read_signature(tool_name: str, arguments: Any) -> str | None:
    """Stable signature for repeated identical read_file calls in a turn."""
    if tool_name != "read_file" or not isinstance(arguments, dict):
        return None
    path = arguments.get("path") or arguments.get("file_path")
    if not isinstance(path, str) or not path.strip():
        return None
    target = _normalize_file_target(path.strip())
    offset = arguments.get("offset", 1)
    limit = arguments.get("limit")
    pages = arguments.get("pages")
    force = bool(arguments.get("force"))
    return f"read:{target}|offset={offset}|limit={limit}|pages={pages}|force={force}"


def repeated_file_tool_loop_error(
    tool_name: str,
    arguments: Any,
    identical_read_counts: dict[str, int],
) -> tuple[str, str] | None:
    """Throttle repeated identical file reads within a single turn."""
    read_signature = _file_read_signature(tool_name, arguments)
    if read_signature is not None:
        read_count = identical_read_counts.get(read_signature, 0) + 1
        identical_read_counts[read_signature] = read_count
        if read_count > _MAX_REPEAT_IDENTICAL_FILE_READS:
            target = read_signature.split("|", 1)[0].removeprefix("read:")
            logger.warning(
                "Escalating repeated identical file read {} (attempt {})",
                target[:160],
                read_count,
            )
            return (
                "Error: repeated identical file read blocked.\n"
                f"You have already read '{target}' with the same range {read_count} times in this turn. "
                "Use the content you already have, read a different range, or set force=true only if the file has changed. "
                "Do not keep alternating read_file and apply_patch on the same unchanged snippet. "
                "Next step: choose a stable anchor, read a different surrounding region only if needed, then make one consolidated edit.",
                f"file_read_loop_escalated:{target}",
            )
    return None


def _is_file_edit_success(tool_name: str, text: str | None) -> bool:
    if tool_name not in _FILE_EDIT_TOOL_NAMES or not isinstance(text, str):
        return False
    stripped = text.strip()
    return (
        stripped.startswith("Successfully edited ")
        or stripped.startswith("Successfully wrote ")
        or stripped.startswith("Successfully created ")
        or stripped.startswith("Patch applied:")
    )


def _file_edit_failure_kind(tool_name: str, text: str | None) -> str | None:
    if tool_name not in _FILE_EDIT_TOOL_NAMES or not isinstance(text, str):
        return None
    lowered = text.lower()
    if "old_text appears" in lowered or "appears multiple times" in lowered:
        return "ambiguous"
    if "old_text not found" in lowered:
        return "not_found"
    if lowered.startswith("error editing file:") or lowered.startswith("error applying patch:"):
        return "tool_error"
    return None


def repeated_failed_file_edit_error(
    tool_name: str,
    arguments: Any,
    outcome_text: str | None,
    failed_counts: dict[str, int],
) -> tuple[str, str] | None:
    """Throttle only repeated no-progress file edits; reset after success."""
    targets = _file_touch_targets(tool_name, arguments)
    if not targets or tool_name not in _FILE_EDIT_TOOL_NAMES:
        return None
    if _is_file_edit_success(tool_name, outcome_text):
        for target in targets:
            failed_counts.pop(target, None)
        return None

    failure_kind = _file_edit_failure_kind(tool_name, outcome_text)
    if failure_kind is None:
        return None

    for target in targets:
        attempt_count = failed_counts.get(target, 0) + 1
        failed_counts[target] = attempt_count
        if attempt_count <= _MAX_REPEAT_FAILED_FILE_EDITS:
            continue
        logger.warning(
            "Escalating repeated failed file edit {} (kind={}, attempts={})",
            target[:160],
            failure_kind,
            attempt_count,
        )
        if failure_kind == "ambiguous":
            return (
                "Error: repeated ambiguous file edit attempts detected.\n"
                f"You have hit multiple matching anchors in '{target}' {attempt_count} times in this turn. "
                "Stop retrying the same replacement text. Read the competing regions, then retry with occurrence, line_hint, expected_replacements, or a larger apply_patch anchor that uniquely identifies the right block.",
                f"file_edit_ambiguous_escalated:{target}",
            )
        if failure_kind == "not_found":
            return (
                "Error: repeated file edit attempts without a matching anchor.\n"
                f"You have already failed to match text in '{target}' {attempt_count} times in this turn. "
                "The file likely changed or the anchor is too narrow. Re-read the exact target region, copy old_text exactly from read_file, and make one consolidated edit instead of retrying stale text.",
                f"file_edit_not_found_escalated:{target}",
            )
        return (
            "Error: repeated file edit attempts with no progress.\n"
            f"You have already tried to modify '{target}' {attempt_count} times in this turn without a successful write. "
            "Stop making tiny trial edits. Re-read a wider context, choose one stable anchor, and then make one final patch.",
            f"file_edit_loop_escalated:{target}",
        )
    return None
