from __future__ import annotations

from nanobot.agent.loop import _augment_direct_print_request


def test_augment_direct_print_request_adds_hint_for_print_file_marker():
    result = _augment_direct_print_request("write a file and /print_file it to me")

    assert "/print_file" in result
    assert "just_print_file" in result
    assert "direct file output" in result


def test_augment_direct_print_request_leaves_normal_text_unchanged():
    text = "please summarize the file"
    assert _augment_direct_print_request(text) == text
