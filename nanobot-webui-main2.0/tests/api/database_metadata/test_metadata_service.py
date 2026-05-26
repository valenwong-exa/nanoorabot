from pathlib import Path

from webui.api.database_metadata.metadata_service import DatabaseMetadataService
from webui.api.database_metadata.yaml_cache import find_node_by_id, read_cache, update_node_children


def _service(tmp_path: Path) -> DatabaseMetadataService:
    return DatabaseMetadataService(cache_base_dir=tmp_path)


def test_open_connection_builds_yaml_cache_and_reuses_it(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path)

    monkeypatch.setattr(
        service,
        "_fetch_connection_info",
        lambda _name: {
            "username": "VALEN",
            "connected_schema": "VALEN",
            "server_host": "192.168.56.101",
            "service_name": "aidemo_pdb",
            "db_name": "AIDEMO",
        },
    )
    monkeypatch.setattr(service, "_fetch_all_users", lambda _name: ["AGENT", "VALEN"])

    result = service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )

    assert result["success"] is True
    assert result["fromCache"] is False
    assert result["tree"]["label"] == "Oracle Connections"

    cache_payload = read_cache("aidemo-test", tmp_path)
    assert cache_payload is not None
    assert cache_payload["connection"]["sqlcl_connection_name"] == "aidemo"
    assert cache_payload["connection"]["connected_schema"] == "VALEN"

    cached = service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="ignored-on-cache-hit",
    )
    assert cached["fromCache"] is True


def test_load_node_populates_unloaded_tables_folder(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path)

    monkeypatch.setattr(
        service,
        "_fetch_connection_info",
        lambda _name: {
            "username": "VALEN",
            "connected_schema": "VALEN",
            "server_host": "192.168.56.101",
            "service_name": "aidemo_pdb",
            "db_name": "AIDEMO",
        },
    )
    monkeypatch.setattr(service, "_fetch_all_users", lambda _name: ["AGENT", "VALEN"])
    monkeypatch.setattr(
        service,
        "_fetch_metadata_object_names",
        lambda **_kwargs: ["AGENT_ACTIONS", "AGENT_ACTION_CATALOG"],
    )

    service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )

    result = service.load_node(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        node_id="schema:VALEN:tables",
        node_type="tables_folder",
        schema_name="VALEN",
    )

    assert result["success"] is True
    assert result["fromCache"] is False
    assert result["node"]["loaded"] is True
    assert [child["label"] for child in result["node"]["children"]] == [
        "AGENT_ACTIONS",
        "AGENT_ACTION_CATALOG",
    ]

    cache_payload = read_cache("aidemo-test", tmp_path)
    assert cache_payload is not None
    cached_node = find_node_by_id(cache_payload["tree"], "schema:VALEN:tables")
    assert cached_node is not None
    assert cached_node["loaded"] is True
    assert len(cached_node["children"]) == 2


def test_update_node_children_replaces_only_target_node() -> None:
    tree = {
        "id": "root",
        "children": [
            {
                "id": "schema:VALEN:tables",
                "label": "Tables",
                "children": [],
                "loaded": False,
                "metadata": {"nodePath": "Oracle Connections/aidemo/Schemas/VALEN/Tables"},
            },
            {
                "id": "schema:VALEN:indexes",
                "label": "Indexes",
                "children": [],
                "loaded": False,
                "metadata": {"nodePath": "Oracle Connections/aidemo/Schemas/VALEN/Indexes"},
            },
        ],
    }

    update_node_children(
        tree,
        "schema:VALEN:tables",
        [{"id": "schema:VALEN:table:TEST1", "label": "TEST1", "children": []}],
    )

    tables = find_node_by_id(tree, "schema:VALEN:tables")
    indexes = find_node_by_id(tree, "schema:VALEN:indexes")
    assert tables is not None and tables["loaded"] is True
    assert tables["children"][0]["label"] == "TEST1"
    assert indexes is not None and indexes["children"] == []
