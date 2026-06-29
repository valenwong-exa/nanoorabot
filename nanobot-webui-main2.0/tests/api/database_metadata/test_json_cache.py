from pathlib import Path

from webui.api.database_metadata.json_cache import (
    cache_file_path,
    default_cache_dir,
    legacy_cache_file_path,
    read_cache,
    read_json_file,
    write_json_file,
)


def test_write_json_file_round_trips_metadata_payload(tmp_path: Path) -> None:
    path = tmp_path / "metadata.json"
    payload = {
        "connection": {"id": "aidemo-test", "sqlcl_connection_name": "aidemo"},
        "tree": {"id": "root", "label": "Oracle Connections", "children": []},
    }

    write_json_file(path, payload)

    written = path.read_text(encoding="utf-8")
    assert written.lstrip().startswith("{")
    assert read_json_file(path) == payload


def test_read_cache_migrates_legacy_json_backed_yaml_file(tmp_path: Path) -> None:
    payload = {
        "connection": {"id": "aidemo-test", "sqlcl_connection_name": "aidemo"},
        "tree": {"id": "root", "label": "Oracle Connections", "children": []},
    }
    legacy_path = legacy_cache_file_path("aidemo-test", tmp_path)
    json_path = cache_file_path("aidemo-test", tmp_path)

    write_json_file(legacy_path, payload)

    assert read_cache("aidemo-test", tmp_path) == payload
    assert json_path.exists()
    assert not legacy_path.exists()


def test_default_cache_dir_uses_workspace_ora_ops_metadata(tmp_path: Path) -> None:
    cache_path = default_cache_dir(tmp_path)

    assert cache_path == tmp_path / "ora-ops-metadata" / "metadata_cache"
    assert cache_path.parent.exists()
    assert cache_file_path("aidemo-test", tmp_path).suffix == ".json"
