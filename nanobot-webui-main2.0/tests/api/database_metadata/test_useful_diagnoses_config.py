import json
from pathlib import Path

from webui.api.database_metadata.useful_diagnoses_config import (
    DEFAULT_USEFUL_DIAGNOSES,
    load_useful_diagnoses,
    normalize_useful_diagnosis_key,
    useful_diagnoses_config_path,
)


def test_load_useful_diagnoses_creates_default_config_when_missing(tmp_path: Path) -> None:
    path = useful_diagnoses_config_path(tmp_path)

    items = load_useful_diagnoses(tmp_path)

    assert path.exists()
    assert items == [dict(item) for item in DEFAULT_USEFUL_DIAGNOSES]
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["items"][0]["label"] == "tablespace usage"
    assert payload["items"][1]["label"] == "redo status"


def test_load_useful_diagnoses_filters_invalid_entries(tmp_path: Path) -> None:
    path = useful_diagnoses_config_path(tmp_path)
    path.write_text(
        json.dumps(
            {
                "items": [
                    {"key": "redo_status", "label": "redo status", "sql": "select 1 from dual"},
                    {"key": "redo_status", "label": "dup", "sql": "select 2 from dual"},
                    {"key": "Top CPU SQLs", "label": "top cpu sqls", "sql": "select 3 from dual"},
                    {"key": "2PC", "label": "2pc", "sql": "select 4 from dual"},
                    {"key": "tablespace_usage", "label": " ", "sql": "select 4 from dual"},
                ]
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    items = load_useful_diagnoses(tmp_path)

    assert items == [
        {"key": "redo_status", "label": "redo status", "sql": "select 1 from dual"},
        {"key": "top_cpu_sqls", "label": "top cpu sqls", "sql": "select 3 from dual"},
        {"key": "item_2pc", "label": "2pc", "sql": "select 4 from dual"},
    ]


def test_normalize_useful_diagnosis_key_converts_spaces_case_and_digits() -> None:
    assert normalize_useful_diagnosis_key("Top CPU SQLs") == "top_cpu_sqls"
    assert normalize_useful_diagnosis_key("2PC") == "item_2pc"
    assert normalize_useful_diagnosis_key("invalid object") == "invalid_object"
