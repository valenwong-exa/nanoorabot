import json
from pathlib import Path

from webui.api.database_metadata.dictionary_tables_config import (
    DEFAULT_DICTIONARY_TABLES,
    dictionary_tables_config_path,
    load_dictionary_tables,
)


def test_load_dictionary_tables_creates_default_config_when_missing(tmp_path: Path) -> None:
    path = dictionary_tables_config_path(tmp_path)

    items = load_dictionary_tables(tmp_path)

    assert path.exists()
    assert items == [dict(item) for item in DEFAULT_DICTIONARY_TABLES]
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["items"][0]["label"] == "DBA_OBJECTS"
    assert payload["items"][0]["sql"] == "select * from DBA_OBJECTS where rownum <= 100;"


def test_load_dictionary_tables_filters_invalid_entries(tmp_path: Path) -> None:
    path = dictionary_tables_config_path(tmp_path)
    path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "key": "dba_objects",
                        "label": "DBA_OBJECTS",
                        "objectName": "DBA_OBJECTS",
                        "sql": "select * from DBA_OBJECTS where rownum <= 100;",
                    },
                    {
                        "key": "dba_objects",
                        "label": "dup",
                        "objectName": "DBA_TABLES",
                        "sql": "select * from DBA_TABLES where rownum <= 100;",
                    },
                    {
                        "key": "bad-key",
                        "label": "bad",
                        "objectName": "DBA_TABLES",
                        "sql": "select * from DBA_TABLES where rownum <= 100;",
                    },
                ]
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    items = load_dictionary_tables(tmp_path)

    assert items == [
        {
            "key": "dba_objects",
            "label": "DBA_OBJECTS",
            "objectName": "DBA_OBJECTS",
            "sql": "select * from DBA_OBJECTS where rownum <= 100;",
        }
    ]
