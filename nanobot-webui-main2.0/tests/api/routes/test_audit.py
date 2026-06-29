import json
from pathlib import Path

from webui.api.routes import audit


def test_read_session_file_returns_all_jsonl_rows_and_search_text(tmp_path: Path, monkeypatch) -> None:
    session_file = tmp_path / "web_audit-demo.jsonl"
    session_file.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "_type": "metadata",
                        "key": "web:user-1:demo",
                        "created_at": "2026-06-11T10:00:00",
                        "updated_at": "2026-06-11T10:05:00",
                        "metadata": {"title": "demo"},
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "role": "user",
                        "timestamp": "2026-06-11T10:01:00",
                        "content": "请检查 drop table 风险",
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "role": "assistant",
                        "timestamp": "2026-06-11T10:02:00",
                        "tool_calls": [{"function": {"name": "run_sql"}}],
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    {
                        "role": "tool",
                        "timestamp": "2026-06-11T10:03:00",
                        "name": "run_sql",
                        "content": [{"type": "text", "text": "DROP TABLE demo_users"}],
                    },
                    ensure_ascii=False,
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(audit, "classify_session_type", lambda session_key, prefix: f"{prefix}:{session_key}")

    payload = audit._read_session_file(session_file)

    assert payload["file_name"] == "web_audit-demo.jsonl"
    assert payload["session_key"] == "web:user-1:demo"
    assert payload["created_at"] == "2026-06-11T10:00:00"
    assert payload["updated_at"] == "2026-06-11T10:05:00"
    assert payload["line_count"] == 4
    assert payload["session_type"] == "web:web:user-1:demo"
    assert [record["role"] for record in payload["records"]] == ["metadata", "user", "assistant", "tool"]
    assert payload["records"][0]["summary"].startswith("[metadata]")
    assert "drop table" in payload["records"][1]["search_text"].lower()
    assert payload["records"][2]["summary"] == "[tool_calls] run_sql"
    assert "drop table demo_users" in payload["records"][3]["search_text"].lower()


def test_read_session_file_marks_invalid_jsonl_lines(tmp_path: Path) -> None:
    session_file = tmp_path / "broken.jsonl"
    session_file.write_text('{"_type":"metadata","key":"demo"}\nnot-json\n', encoding="utf-8")

    payload = audit._read_session_file(session_file)

    assert payload["line_count"] == 2
    assert payload["records"][1]["role"] == "invalid"
    assert payload["records"][1]["summary"] == "not-json"
