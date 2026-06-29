import json
from pathlib import Path

from webui.api.database_metadata.dynamic_views_config import (
    DEFAULT_DYNAMIC_VIEWS,
    dynamic_views_config_path,
    load_dynamic_views,
)


def test_load_dynamic_views_creates_default_config_when_missing(tmp_path: Path) -> None:
    path = dynamic_views_config_path(tmp_path)

    views = load_dynamic_views(tmp_path)

    assert path.exists()
    assert views == list(DEFAULT_DYNAMIC_VIEWS)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["views"][:3] == list(DEFAULT_DYNAMIC_VIEWS[:3])


def test_load_dynamic_views_normalizes_and_deduplicates_entries(tmp_path: Path) -> None:
    path = dynamic_views_config_path(tmp_path)
    path.write_text(
        json.dumps({"views": [" v$session ", "GV$SESSION", "v$session", "", 123]}, ensure_ascii=True),
        encoding="utf-8",
    )

    views = load_dynamic_views(tmp_path)

    assert views == ["V$SESSION", "GV$SESSION"]
