"""Tests for repeated_workspace_violation throttle and signature."""

from __future__ import annotations

from nanobot.utils.runtime import (
    repeated_failed_file_edit_error,
    repeated_file_tool_loop_error,
    repeated_workspace_violation_error,
    workspace_violation_signature,
)


def test_signature_for_filesystem_tools_uses_path_argument():
    sig_a = workspace_violation_signature(
        "read_file", {"path": "/Users/x/Downloads/01.md"}
    )
    sig_b = workspace_violation_signature(
        "write_file", {"path": "/Users/x/Downloads/01.md"}
    )
    sig_c = workspace_violation_signature(
        "edit_file", {"file_path": "/Users/x/Downloads/01.md"}
    )

    assert sig_a is not None
    assert sig_a == sig_b == sig_c, (
        "the throttle must collapse equivalent paths across different tools "
        "so the LLM cannot bypass it by switching tool"
    )
    assert "/users/x/downloads/01.md" in sig_a


def test_signature_for_exec_extracts_first_absolute_path_in_command():
    sig = workspace_violation_signature(
        "exec",
        {"command": "cat /Users/x/Downloads/01.md && echo done"},
    )
    assert sig is not None
    assert "/users/x/downloads/01.md" in sig


def test_signature_collides_across_filesystem_and_exec_for_same_target():
    """LLM bypass loops jump tools (read_file -> exec cat). Throttle must
    treat both attempts as targeting the same outside resource."""
    fs_sig = workspace_violation_signature(
        "read_file", {"path": "/Users/x/Downloads/01.md"}
    )
    exec_sig = workspace_violation_signature(
        "exec", {"command": "cat /Users/x/Downloads/01.md"}
    )
    assert fs_sig == exec_sig


def test_signature_falls_back_to_working_dir_when_no_absolute_in_command():
    sig = workspace_violation_signature(
        "exec",
        {"command": "ls -la", "working_dir": "/etc"},
    )
    assert sig is not None
    assert "/etc" in sig


def test_signature_is_none_for_unknown_tool_with_no_path():
    assert workspace_violation_signature("web_search", {"query": "anything"}) is None
    assert workspace_violation_signature("exec", {"command": "echo hello"}) is None


def test_repeated_workspace_violation_returns_none_within_budget():
    counts: dict[str, int] = {}
    arguments = {"path": "/Users/x/Downloads/01.md"}

    assert repeated_workspace_violation_error("read_file", arguments, counts) is None
    assert repeated_workspace_violation_error("read_file", arguments, counts) is None


def test_repeated_workspace_violation_escalates_after_third_attempt():
    counts: dict[str, int] = {}
    arguments = {"path": "/Users/x/Downloads/01.md"}

    repeated_workspace_violation_error("read_file", arguments, counts)
    repeated_workspace_violation_error("read_file", arguments, counts)
    third = repeated_workspace_violation_error("read_file", arguments, counts)

    assert third is not None
    assert "refusing repeated workspace-bypass" in third
    assert "/users/x/downloads/01.md" in third
    assert "ask how they want to proceed" in third


def test_repeated_workspace_violation_independent_per_target():
    """Different outside paths must each get their own retry budget."""
    counts: dict[str, int] = {}

    repeated_workspace_violation_error(
        "read_file", {"path": "/Users/x/Downloads/01.md"}, counts,
    )
    repeated_workspace_violation_error(
        "read_file", {"path": "/Users/x/Downloads/01.md"}, counts,
    )
    # Different target, fresh budget.
    assert repeated_workspace_violation_error(
        "read_file", {"path": "/Users/x/Documents/notes.md"}, counts,
    ) is None


def test_repeated_workspace_violation_collapses_tool_switching():
    """LLM switches from read_file to exec cat then to python -c open(...)
    against the same path; the throttle must escalate on the third attempt."""
    counts: dict[str, int] = {}

    repeated_workspace_violation_error(
        "read_file", {"path": "/Users/x/Downloads/01.md"}, counts,
    )
    repeated_workspace_violation_error(
        "exec", {"command": "cat /Users/x/Downloads/01.md"}, counts,
    )
    third = repeated_workspace_violation_error(
        "exec",
        {"command": "python3 -c \"open('/Users/x/Downloads/01.md').read()\""},
        counts,
    )
    assert third is not None
    assert "refusing repeated workspace-bypass" in third


def test_repeated_identical_file_read_escalates_after_fourth_attempt():
    read_counts: dict[str, int] = {}
    arguments = {"path": "quickhealthcheck.sql", "offset": 1, "limit": 200}

    assert repeated_file_tool_loop_error(
        "read_file", arguments, read_counts,
    ) is None
    assert repeated_file_tool_loop_error(
        "read_file", arguments, read_counts,
    ) is None
    assert repeated_file_tool_loop_error(
        "read_file", arguments, read_counts,
    ) is None

    fourth = repeated_file_tool_loop_error(
        "read_file", arguments, read_counts,
    )
    assert fourth is not None
    message, detail = fourth
    assert "repeated identical file read blocked" in message
    assert detail.startswith("file_read_loop_escalated:")
    assert "quickhealthcheck.sql" in message


def test_repeated_ambiguous_file_edits_escalate_after_fourth_failure():
    failed_counts: dict[str, int] = {}
    arguments = {"path": "quickhealthcheck.sql", "old_text": "x", "new_text": "y"}
    outcome = "Warning: old_text appears 2 times at line 942, line 1067. Provide more context, set occurrence to choose one match, or set replace_all=true."

    assert repeated_failed_file_edit_error("edit_file", arguments, outcome, failed_counts) is None
    assert repeated_failed_file_edit_error("edit_file", arguments, outcome, failed_counts) is None
    assert repeated_failed_file_edit_error("edit_file", arguments, outcome, failed_counts) is None

    fourth = repeated_failed_file_edit_error("edit_file", arguments, outcome, failed_counts)
    assert fourth is not None
    message, detail = fourth
    assert "repeated ambiguous file edit attempts detected" in message
    assert "occurrence" in message
    assert detail.startswith("file_edit_ambiguous_escalated:")


def test_repeated_not_found_file_edits_escalate_after_fourth_failure():
    failed_counts: dict[str, int] = {}
    arguments = {
        "edits": [{"path": "quickhealthcheck.sql", "action": "replace", "old_text": "missing", "new_text": "new"}]
    }
    outcome = "Error applying patch: old_text not found in quickhealthcheck.sql"

    assert repeated_failed_file_edit_error("apply_patch", arguments, outcome, failed_counts) is None
    assert repeated_failed_file_edit_error("apply_patch", arguments, outcome, failed_counts) is None
    assert repeated_failed_file_edit_error("apply_patch", arguments, outcome, failed_counts) is None

    fourth = repeated_failed_file_edit_error("apply_patch", arguments, outcome, failed_counts)
    assert fourth is not None
    message, detail = fourth
    assert "without a matching anchor" in message
    assert "copy old_text exactly" in message.lower()
    assert detail.startswith("file_edit_not_found_escalated:")


def test_successful_file_edit_resets_failed_budget():
    failed_counts: dict[str, int] = {}
    arguments = {"path": "quickhealthcheck.sql", "old_text": "x", "new_text": "y"}
    ambiguous = "Warning: old_text appears 2 times at line 942, line 1067."

    assert repeated_failed_file_edit_error("edit_file", arguments, ambiguous, failed_counts) is None
    assert repeated_failed_file_edit_error("edit_file", arguments, ambiguous, failed_counts) is None
    assert repeated_failed_file_edit_error(
        "edit_file",
        arguments,
        "Successfully edited E:/nanobot-main/dba1/skills/ora-quick-healthcheck/quickhealthcheck.sql",
        failed_counts,
    ) is None
    assert failed_counts == {}
    assert repeated_failed_file_edit_error("edit_file", arguments, ambiguous, failed_counts) is None
