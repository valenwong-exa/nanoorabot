import json
from pathlib import Path

import webui.api.database_metadata.metadata_service as metadata_service_module
from webui.api.database_metadata.dictionary_tables_config import dictionary_tables_config_path
from webui.api.database_metadata.dynamic_views_config import dynamic_views_config_path
from webui.api.database_metadata.json_cache import find_node_by_id, read_cache, update_node_children, write_cache
from webui.api.database_metadata.metadata_service import DatabaseMetadataService
from webui.api.database_metadata.useful_diagnoses_config import useful_diagnoses_config_path


def _service(tmp_path: Path) -> DatabaseMetadataService:
    return DatabaseMetadataService(cache_base_dir=tmp_path)


def test_open_connection_builds_json_cache_and_reuses_it(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path)
    probe_calls: list[str] = []

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
    monkeypatch.setattr(service, "_probe_connection", lambda name: probe_calls.append(name))

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
    connection_node = find_node_by_id(result["tree"], "conn:aidemo-test")
    assert connection_node is not None
    assert [child["label"] for child in connection_node["children"][2:5]] == [
        "DBOps",
        "SelectAI",
        "Schemas",
    ]
    dbops_node = find_node_by_id(result["tree"], "dbops")
    assert dbops_node is not None
    assert [child["label"] for child in dbops_node["children"]] == [
        "DynamicViews",
        "DictionaryTables",
        "UsefulDiagnoses",
    ]
    schema_node = find_node_by_id(result["tree"], "schema:VALEN")
    assert schema_node is not None
    labels = [child["label"] for child in schema_node["children"]]
    assert "DynamicViews" not in labels
    assert "DictionaryTables" not in labels
    assert "UsefulDiagnoses" not in labels
    assert dictionary_tables_config_path(tmp_path).exists()
    assert dynamic_views_config_path(tmp_path).exists()
    assert useful_diagnoses_config_path(tmp_path).exists()

    cached = service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="ignored-on-cache-hit",
    )
    assert cached["fromCache"] is True
    assert probe_calls == ["aidemo"]


def test_open_connection_upgrades_cached_connection_children_with_selectai(tmp_path: Path, monkeypatch) -> None:
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
    monkeypatch.setattr(service, "_probe_connection", lambda _name: None)

    service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )
    cache_payload = read_cache("aidemo-test", tmp_path)
    assert cache_payload is not None
    connection_node = find_node_by_id(cache_payload["tree"], "conn:aidemo-test")
    assert connection_node is not None
    connection_node["children"] = [
        child for child in connection_node["children"] if child["id"] != "selectai"
    ]
    write_cache("aidemo-test", cache_payload, tmp_path)

    result = service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )

    upgraded_connection_node = find_node_by_id(result["tree"], "conn:aidemo-test")
    assert upgraded_connection_node is not None
    assert [child["label"] for child in upgraded_connection_node["children"][2:5]] == [
        "DBOps",
        "SelectAI",
        "Schemas",
    ]
    assert find_node_by_id(result["tree"], "selectai") is not None


def test_load_node_populates_selectai_profiles(tmp_path: Path, monkeypatch) -> None:
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
    monkeypatch.setattr(service, "_fetch_selectai_profile_names", lambda _name: ["DEFAULT_PROFILE", "HR_ASSISTANT"])

    service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )

    result = service.load_node(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        node_id="selectai",
        node_type="selectai_root",
    )

    assert result["success"] is True
    assert result["fromCache"] is False
    assert result["node"]["loaded"] is True
    assert [child["label"] for child in result["node"]["children"]] == ["DEFAULT_PROFILE", "HR_ASSISTANT"]
    assert [child["type"] for child in result["node"]["children"]] == ["selectai_profile", "selectai_profile"]


def test_load_node_keeps_selectai_empty_when_view_missing(tmp_path: Path, monkeypatch) -> None:
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
    monkeypatch.setattr(service, "_fetch_selectai_profile_names", lambda _name: [])

    service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )

    result = service.load_node(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        node_id="selectai",
        node_type="selectai_root",
    )

    assert result["success"] is True
    assert result["fromCache"] is False
    assert result["node"]["loaded"] is True
    assert result["node"]["children"] == []


def test_fetch_selectai_profile_names_returns_empty_on_missing_view(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path)

    def _raise_missing_view(*_args, **_kwargs):
        raise RuntimeError("ORA-00942: table or view does not exist")

    monkeypatch.setattr(metadata_service_module, "run_sqlcl_json", _raise_missing_view)

    assert service._fetch_selectai_profile_names("aidemo") == []


def test_open_connection_with_cache_probes_only_without_refresh(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path)
    probe_calls: list[str] = []

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

    service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )

    def fail_refresh(*_args, **_kwargs):
        raise AssertionError("cached open should not rebuild metadata")

    monkeypatch.setattr(service, "_fetch_connection_info", fail_refresh)
    monkeypatch.setattr(service, "_fetch_all_users", fail_refresh)
    monkeypatch.setattr(service, "_probe_connection", lambda name: probe_calls.append(name))

    cached = service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="ignored-on-cache-hit",
    )

    assert cached["success"] is True
    assert cached["fromCache"] is True
    assert cached["tree"]["label"] == "Oracle Connections"
    assert probe_calls == ["aidemo"]


def test_open_connection_upgrades_cached_schema_folder_list(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path)
    probe_calls: list[str] = []

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
    monkeypatch.setattr(service, "_probe_connection", lambda name: probe_calls.append(name))

    service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )
    cache_payload = read_cache("aidemo-test", tmp_path)
    assert cache_payload is not None
    connection_node = find_node_by_id(cache_payload["tree"], "conn:aidemo-test")
    assert connection_node is not None
    schema_node = find_node_by_id(cache_payload["tree"], "schema:VALEN")
    assert schema_node is not None
    dbops_node = find_node_by_id(cache_payload["tree"], "dbops")
    assert dbops_node is not None
    schema_node["children"] = list(dbops_node["children"]) + list(schema_node["children"])
    connection_node["children"] = [child for child in connection_node["children"] if child["id"] != "dbops"]
    write_cache("aidemo-test", cache_payload, tmp_path)
    service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )

    upgraded_payload = read_cache("aidemo-test", tmp_path)
    assert upgraded_payload is not None
    upgraded_dbops_node = find_node_by_id(upgraded_payload["tree"], "dbops")
    assert upgraded_dbops_node is not None
    assert [child["label"] for child in upgraded_dbops_node["children"]] == [
        "DynamicViews",
        "DictionaryTables",
        "UsefulDiagnoses",
    ]
    assert any(child["type"] == "dynamic_views_folder" for child in upgraded_dbops_node["children"])
    assert any(child["type"] == "dictionary_table_folder" for child in upgraded_dbops_node["children"])
    assert any(child["type"] == "useful_diagnoses_folder" for child in upgraded_dbops_node["children"])
    upgraded_schema_node = find_node_by_id(upgraded_payload["tree"], "schema:VALEN")
    assert upgraded_schema_node is not None
    assert all(
        child["type"] not in {"dynamic_views_folder", "dictionary_table_folder", "useful_diagnoses_folder"}
        for child in upgraded_schema_node["children"]
    )
    assert probe_calls == ["aidemo"]


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


def test_load_node_populates_dynamic_views_folder_with_available_views(tmp_path: Path, monkeypatch) -> None:
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
    monkeypatch.setattr(service, "_fetch_dynamic_view_names", lambda _name: ["GV$SESSION", "V$SESSION"])

    service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )

    result = service.load_node(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        node_id="schema:VALEN:dynamic_views",
        node_type="dynamic_views_folder",
        schema_name="VALEN",
    )

    assert result["success"] is True
    assert result["fromCache"] is False
    assert result["node"]["loaded"] is True
    assert [child["label"] for child in result["node"]["children"]] == ["GV$SESSION", "V$SESSION"]
    assert [child["type"] for child in result["node"]["children"]] == ["dynamic_view", "dynamic_view"]

    cache_payload = read_cache("aidemo-test", tmp_path)
    assert cache_payload is not None
    cached_node = find_node_by_id(cache_payload["tree"], "schema:VALEN:dynamic_views")
    assert cached_node is not None
    assert cached_node["loaded"] is True
    assert len(cached_node["children"]) == 2


def test_load_node_populates_dictionary_table_folder_with_available_items(tmp_path: Path, monkeypatch) -> None:
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
        "_fetch_accessible_object_names",
        lambda _name, object_names, operation: [name for name in object_names if name in {"DBA_OBJECTS", "DBA_TABLES"}],
    )

    service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )

    result = service.load_node(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        node_id="schema:VALEN:dictionary_table",
        node_type="dictionary_table_folder",
        schema_name="VALEN",
    )

    assert result["success"] is True
    assert result["fromCache"] is False
    assert result["node"]["loaded"] is True
    assert [child["label"] for child in result["node"]["children"]] == ["DBA_OBJECTS", "DBA_TABLES"]
    assert [child["type"] for child in result["node"]["children"]] == ["dictionary_table_item", "dictionary_table_item"]
    assert "where rownum <= 100" in str(result["node"]["children"][0]["metadata"]["sqlText"]).lower()
    assert result["node"]["children"][0]["metadata"]["objectName"] == "DBA_OBJECTS"


def test_load_node_populates_useful_diagnoses_folder_with_configured_items(tmp_path: Path, monkeypatch) -> None:
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

    service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )

    result = service.load_node(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        node_id="schema:VALEN:useful_diagnoses",
        node_type="useful_diagnoses_folder",
        schema_name="VALEN",
    )

    assert result["success"] is True
    assert result["fromCache"] is False
    assert result["node"]["loaded"] is True
    assert [child["label"] for child in result["node"]["children"]] == ["tablespace usage", "redo status"]
    assert [child["type"] for child in result["node"]["children"]] == ["useful_diagnosis", "useful_diagnosis"]
    assert "dba_data_files" in str(result["node"]["children"][0]["metadata"]["sqlText"]).lower()
    assert "gv$log" in str(result["node"]["children"][1]["metadata"]["sqlText"]).lower()


def test_refresh_node_reloads_useful_diagnoses_config_with_normalized_keys(tmp_path: Path, monkeypatch) -> None:
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

    service.open_connection(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        display_name="aidemo-test",
    )
    service.load_node(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        node_id="schema:VALEN:useful_diagnoses",
        node_type="useful_diagnoses_folder",
        schema_name="VALEN",
    )

    useful_diagnoses_config_path(tmp_path).write_text(
        json.dumps(
            {
                "items": [
                    {"key": "Top CPU SQLs", "label": "top cpu sqls", "sql": "select 1 from dual"},
                    {"key": "2PC", "label": "2pc", "sql": "select 2 from dual"},
                ]
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    result = service.refresh_node(
        connection_id="aidemo-test",
        sqlcl_connection_name="aidemo",
        node_id="schema:VALEN:useful_diagnoses",
        node_type="useful_diagnoses_folder",
        schema_name="VALEN",
    )

    assert result["success"] is True
    assert result["fromCache"] is False
    assert [child["label"] for child in result["node"]["children"]] == ["top cpu sqls", "2pc"]
    assert [child["metadata"]["diagnosisKey"] for child in result["node"]["children"]] == [
        "top_cpu_sqls",
        "item_2pc",
    ]


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


def test_fetch_source_ddl_uses_all_source_builder_for_plsql_objects(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path)
    builder_calls: list[tuple[str, str, str]] = []
    run_calls: list[tuple[str, str, int, str]] = []

    monkeypatch.setattr(
        metadata_service_module,
        "build_plsql_source_object_sql",
        lambda schema_name, object_name, object_type: (
            builder_calls.append((schema_name, object_name, object_type)) or "plsql-builder-sql"
        ),
    )
    monkeypatch.setattr(
        metadata_service_module,
        "build_source_object_quick_ddl_sql",
        lambda *_args: (_ for _ in ()).throw(AssertionError("GET_DDL builder should not be used for PLSQL objects")),
    )
    monkeypatch.setattr(
        metadata_service_module,
        "run_sqlcl",
        lambda conn, sql_text, timeout, operation: (
            run_calls.append((conn, sql_text, timeout, operation)) or "create or replace procedure demo is\nbegin\nnull;\nend;\n/"
        ),
    )

    result = service._fetch_source_ddl(
        sqlcl_connection_name="aidemo",
        schema_name="HR",
        object_type="procedure",
        object_name="ADD_JOB_HISTORY",
    )

    assert result == "create or replace procedure demo is\nbegin\nnull;\nend;\n/"
    assert builder_calls == [("HR", "ADD_JOB_HISTORY", "PROCEDURE")]
    assert run_calls == [("aidemo", "plsql-builder-sql", 180, "metadata_procedure_ddl:HR.ADD_JOB_HISTORY")]


def test_fetch_source_ddl_keeps_get_ddl_builder_for_view_objects(tmp_path: Path, monkeypatch) -> None:
    service = _service(tmp_path)
    builder_calls: list[tuple[str, str, str, str]] = []
    run_calls: list[tuple[str, str, int, str]] = []

    monkeypatch.setattr(
        metadata_service_module,
        "build_plsql_source_object_sql",
        lambda *_args: (_ for _ in ()).throw(AssertionError("ALL_SOURCE builder should not be used for VIEW")),
    )
    monkeypatch.setattr(
        metadata_service_module,
        "build_source_object_quick_ddl_sql",
        lambda schema_name, object_name, object_type, label: (
            builder_calls.append((schema_name, object_name, object_type, label)) or "get-ddl-builder-sql"
        ),
    )
    monkeypatch.setattr(
        metadata_service_module,
        "run_sqlcl",
        lambda conn, sql_text, timeout, operation: (
            run_calls.append((conn, sql_text, timeout, operation)) or "create or replace view demo as select 1 as x from dual"
        ),
    )

    result = service._fetch_source_ddl(
        sqlcl_connection_name="aidemo",
        schema_name="HR",
        object_type="view",
        object_name="EMP_DETAILS_V",
    )

    assert result == "create or replace view demo as select 1 as x from dual"
    assert builder_calls == [("HR", "EMP_DETAILS_V", "VIEW", "View")]
    assert run_calls == [("aidemo", "get-ddl-builder-sql", 180, "metadata_view_ddl:HR.EMP_DETAILS_V")]
