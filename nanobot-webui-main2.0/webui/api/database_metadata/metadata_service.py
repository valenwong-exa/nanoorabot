"""Service layer for SQLcl-backed Oracle metadata tree browsing."""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from .dictionary_tables_config import ensure_dictionary_tables_config, load_dictionary_tables
from .dynamic_views_config import ensure_dynamic_views_config, load_dynamic_views
from .useful_diagnoses_config import ensure_useful_diagnoses_config, load_useful_diagnoses
from .metadata_sql import (
    DBOPS_FOLDER_SPECS,
    REFRESHABLE_NODE_TYPES,
    SCHEMA_FOLDER_SPECS,
    USER_FOLDER_SPECS,
    build_accessible_object_names_query,
    build_all_users_sql,
    build_connection_probe_sql,
    build_connection_info_sql,
    build_dynamic_views_query,
    build_folder_query,
    build_plsql_source_object_sql,
    build_selectai_profiles_sql,
    build_source_object_quick_ddl_sql,
    build_table_quick_ddl_sql,
    folder_specs_for_node,
    icon_for,
    utc_now_iso,
    validate_object_name,
    validate_schema_name,
    validate_sqlcl_connection_name,
)
from .sqlcl_runner import run_sqlcl, run_sqlcl_json
from .json_cache import cache_file_path, find_node_by_id, read_cache, write_cache

SOURCE_DDL_NODE_TYPE_CONFIG: dict[str, dict[str, str]] = {
    "index": {
        "fetch_mode": "get_ddl",
        "ddl_object_type": "INDEX",
        "label": "Index",
        "cache_folder": "Indexes",
        "operation": "metadata_index_ddl",
    },
    "view": {
        "fetch_mode": "get_ddl",
        "ddl_object_type": "VIEW",
        "label": "View",
        "cache_folder": "Views",
        "operation": "metadata_view_ddl",
    },
    "trigger": {
        "fetch_mode": "all_source",
        "source_object_type": "TRIGGER",
        "label": "Trigger",
        "cache_folder": "Triggers",
        "operation": "metadata_trigger_ddl",
    },
    "sequence": {
        "fetch_mode": "get_ddl",
        "ddl_object_type": "SEQUENCE",
        "label": "Sequence",
        "cache_folder": "Sequences",
        "operation": "metadata_sequence_ddl",
    },
    "procedure": {
        "fetch_mode": "all_source",
        "source_object_type": "PROCEDURE",
        "label": "Procedure",
        "cache_folder": "Procedures",
        "operation": "metadata_procedure_ddl",
    },
    "function": {
        "fetch_mode": "all_source",
        "source_object_type": "FUNCTION",
        "label": "Function",
        "cache_folder": "Functions",
        "operation": "metadata_function_ddl",
    },
    "package_spec": {
        "fetch_mode": "all_source",
        "source_object_type": "PACKAGE",
        "label": "Package Spec",
        "cache_folder": "Package Specs",
        "operation": "metadata_package_spec_ddl",
    },
    "package_body": {
        "fetch_mode": "all_source",
        "source_object_type": "PACKAGE BODY",
        "label": "Package Body",
        "cache_folder": "Package Bodies",
        "operation": "metadata_package_body_ddl",
    },
}


class DatabaseMetadataService:
    """Create, cache, load, and partially refresh Oracle metadata trees."""

    def __init__(self, *, cache_base_dir=None, config_base_dir=None):
        self._cache_base_dir = cache_base_dir
        self._config_base_dir = config_base_dir if config_base_dir is not None else cache_base_dir

    def get_table_ddl(
        self,
        *,
        connection_id: str,
        sqlcl_connection_name: str,
        schema_name: str,
        table_name: str,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        connection_name = validate_sqlcl_connection_name(sqlcl_connection_name)
        owner = validate_schema_name(schema_name)
        table = validate_object_name(table_name)
        cache_path = self._table_ddl_cache_path(
            sqlcl_connection_name=connection_name,
            schema_name=owner,
            table_name=table,
        )

        if not force_refresh and cache_path.exists():
            sql_text = cache_path.read_text(encoding="utf-8").strip()
            logger.info(
                "TABLE DDL cache hit: connection_id={} sqlcl_connection={} schema_name={} table_name={} cache_file={} elapsed_ms={:.1f}",
                connection_id,
                connection_name,
                owner,
                table,
                cache_path,
                (time.perf_counter() - started_at) * 1000,
            )
            return {
                "success": True,
                "connectionId": connection_id,
                "sqlText": sql_text,
                "cachePath": str(cache_path),
                "cacheHit": True,
            }

        sql_text = self._fetch_table_ddl(
            sqlcl_connection_name=connection_name,
            schema_name=owner,
            table_name=table,
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_sql = sql_text.strip()
        cache_path.write_text(normalized_sql + "\n", encoding="utf-8")
        logger.info(
            "TABLE DDL refreshed: connection_id={} sqlcl_connection={} schema_name={} table_name={} cache_file={} elapsed_ms={:.1f}",
            connection_id,
            connection_name,
            owner,
            table,
            cache_path,
            (time.perf_counter() - started_at) * 1000,
        )
        return {
            "success": True,
            "connectionId": connection_id,
            "sqlText": normalized_sql,
            "cachePath": str(cache_path),
            "cacheHit": False,
        }

    def get_procedure_ddl(
        self,
        *,
        connection_id: str,
        sqlcl_connection_name: str,
        schema_name: str,
        procedure_name: str,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        connection_name = validate_sqlcl_connection_name(sqlcl_connection_name)
        owner = validate_schema_name(schema_name)
        procedure = validate_object_name(procedure_name)
        cache_path = self._procedure_ddl_cache_path(
            sqlcl_connection_name=connection_name,
            schema_name=owner,
            procedure_name=procedure,
        )

        if not force_refresh and cache_path.exists():
            sql_text = cache_path.read_text(encoding="utf-8").strip()
            logger.info(
                "PROCEDURE DDL cache hit: connection_id={} sqlcl_connection={} schema_name={} procedure_name={} cache_file={} elapsed_ms={:.1f}",
                connection_id,
                connection_name,
                owner,
                procedure,
                cache_path,
                (time.perf_counter() - started_at) * 1000,
            )
            return {
                "success": True,
                "connectionId": connection_id,
                "sqlText": sql_text,
                "cachePath": str(cache_path),
                "cacheHit": True,
            }

        sql_text = self._fetch_procedure_ddl(
            sqlcl_connection_name=connection_name,
            schema_name=owner,
            procedure_name=procedure,
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_sql = sql_text.strip()
        cache_path.write_text(normalized_sql + "\n", encoding="utf-8")
        logger.info(
            "PROCEDURE DDL refreshed: connection_id={} sqlcl_connection={} schema_name={} procedure_name={} cache_file={} elapsed_ms={:.1f}",
            connection_id,
            connection_name,
            owner,
            procedure,
            cache_path,
            (time.perf_counter() - started_at) * 1000,
        )
        return {
            "success": True,
            "connectionId": connection_id,
            "sqlText": normalized_sql,
            "cachePath": str(cache_path),
            "cacheHit": False,
        }

    def get_source_ddl(
        self,
        *,
        connection_id: str,
        sqlcl_connection_name: str,
        schema_name: str,
        object_type: str,
        object_name: str,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        connection_name = validate_sqlcl_connection_name(sqlcl_connection_name)
        owner = validate_schema_name(schema_name)
        resolved_type, _config = self._resolve_source_ddl_type(object_type)
        validated_name = validate_object_name(object_name)
        cache_path = self._source_ddl_cache_path(
            sqlcl_connection_name=connection_name,
            schema_name=owner,
            object_type=resolved_type,
            object_name=validated_name,
        )

        if not force_refresh and cache_path.exists():
            sql_text = cache_path.read_text(encoding="utf-8").strip()
            logger.info(
                "SOURCE DDL cache hit: connection_id={} sqlcl_connection={} schema_name={} object_type={} object_name={} cache_file={} elapsed_ms={:.1f}",
                connection_id,
                connection_name,
                owner,
                resolved_type,
                validated_name,
                cache_path,
                (time.perf_counter() - started_at) * 1000,
            )
            return {
                "success": True,
                "connectionId": connection_id,
                "sqlText": sql_text,
                "cachePath": str(cache_path),
                "cacheHit": True,
            }

        sql_text = self._fetch_source_ddl(
            sqlcl_connection_name=connection_name,
            schema_name=owner,
            object_type=resolved_type,
            object_name=validated_name,
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_sql = sql_text.strip()
        cache_path.write_text(normalized_sql + "\n", encoding="utf-8")
        logger.info(
            "SOURCE DDL refreshed: connection_id={} sqlcl_connection={} schema_name={} object_type={} object_name={} cache_file={} elapsed_ms={:.1f}",
            connection_id,
            connection_name,
            owner,
            resolved_type,
            validated_name,
            cache_path,
            (time.perf_counter() - started_at) * 1000,
        )
        return {
            "success": True,
            "connectionId": connection_id,
            "sqlText": normalized_sql,
            "cachePath": str(cache_path),
            "cacheHit": False,
        }

    def open_connection(
        self,
        *,
        connection_id: str,
        sqlcl_connection_name: str,
        display_name: str,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        connection_name = validate_sqlcl_connection_name(sqlcl_connection_name)
        logger.info(
            "OPEN metadata tree start: connection_id={} sqlcl_connection={} display_name={}",
            connection_id,
            connection_name,
            display_name,
        )
        ensure_dictionary_tables_config(self._config_base_dir)
        ensure_dynamic_views_config(self._config_base_dir)
        ensure_useful_diagnoses_config(self._config_base_dir)
        cache_payload = read_cache(connection_id, self._cache_base_dir)
        if cache_payload is not None:
            if self._upgrade_static_folder_nodes(cache_payload["tree"]):
                write_cache(connection_id, cache_payload, self._cache_base_dir)
            logger.info(
                "OPEN metadata tree cache hit: connection_id={} sqlcl_connection={} cache_file={}",
                connection_id,
                connection_name,
                cache_file_path(connection_id, self._cache_base_dir),
            )
            self._probe_connection(connection_name)
            logger.info(
                "OPEN metadata tree returned cached tree without refresh: connection_id={} sqlcl_connection={} elapsed_ms={:.1f}",
                connection_id,
                connection_name,
                (time.perf_counter() - started_at) * 1000,
            )
            return {
                "success": True,
                "fromCache": True,
                "connectionId": connection_id,
                "tree": cache_payload["tree"],
            }

        logger.info(
            "OPEN metadata tree cache miss: connection_id={} sqlcl_connection={} - building initial payload",
            connection_id,
            connection_name,
        )
        payload = self._build_initial_payload(
            connection_id=connection_id,
            sqlcl_connection_name=connection_name,
            display_name=display_name or connection_id,
        )
        write_cache(connection_id, payload, self._cache_base_dir)
        logger.info(
            "OPEN metadata tree initialized cache: connection_id={} sqlcl_connection={} cache_file={} elapsed_ms={:.1f}",
            connection_id,
            connection_name,
            cache_file_path(connection_id, self._cache_base_dir),
            (time.perf_counter() - started_at) * 1000,
        )
        return {
            "success": True,
            "fromCache": False,
            "connectionId": connection_id,
            "tree": payload["tree"],
        }

    def load_node(
        self,
        *,
        connection_id: str,
        sqlcl_connection_name: str,
        node_id: str,
        node_type: str,
        schema_name: str | None = None,
    ) -> dict[str, Any]:
        payload = self._read_required_cache(connection_id)
        tree = payload["tree"]
        node = find_node_by_id(tree, node_id)
        if node is None:
            raise ValueError(f"Metadata tree node not found: {node_id}")
        if node.get("type") != node_type:
            raise ValueError(f"Node type mismatch for {node_id}: expected {node.get('type')} got {node_type}")
        if node.get("loaded") is True:
            return {
                "success": True,
                "fromCache": True,
                "connectionId": connection_id,
                "node": node,
            }
        return self.refresh_node(
            connection_id=connection_id,
            sqlcl_connection_name=sqlcl_connection_name,
            node_id=node_id,
            node_type=node_type,
            schema_name=schema_name,
        )

    def refresh_node(
        self,
        *,
        connection_id: str,
        sqlcl_connection_name: str,
        node_id: str,
        node_type: str,
        schema_name: str | None = None,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        connection_name = validate_sqlcl_connection_name(sqlcl_connection_name)
        logger.info(
            "REFRESH metadata node start: connection_id={} node_id={} node_type={} schema_name={}",
            connection_id,
            node_id,
            node_type,
            schema_name,
        )
        payload = self._read_required_cache(connection_id)
        tree = payload["tree"]
        node = find_node_by_id(tree, node_id)
        if node is None:
            raise ValueError(f"Metadata tree node not found: {node_id}")
        if node.get("type") != node_type:
            raise ValueError(f"Node type mismatch for {node_id}: expected {node.get('type')} got {node_type}")
        if node_type not in REFRESHABLE_NODE_TYPES:
            raise ValueError(f"Node type does not support refresh: {node_type}")

        refreshed_at = utc_now_iso()
        children = self._build_children_for_node(
            payload=payload,
            node=node,
            sqlcl_connection_name=connection_name,
            schema_name=schema_name,
        )
        node["children"] = children
        node["loaded"] = True
        metadata = node.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["last_refreshed_at"] = refreshed_at
        if node_type == "selectai_root":
            metadata["profileListLoaded"] = True
        node["metadata"] = metadata
        payload["connection"]["updated_at"] = refreshed_at
        write_cache(connection_id, payload, self._cache_base_dir)

        refreshed_node = find_node_by_id(tree, node_id)
        logger.info(
            "REFRESH metadata node success: connection_id={} node_id={} node_type={} child_count={} elapsed_ms={:.1f}",
            connection_id,
            node_id,
            node_type,
            len(children),
            (time.perf_counter() - started_at) * 1000,
        )
        return {
            "success": True,
            "fromCache": False,
            "connectionId": connection_id,
            "node": refreshed_node,
        }

    def _build_initial_payload(
        self,
        *,
        connection_id: str,
        sqlcl_connection_name: str,
        display_name: str,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        logger.info(
            "Building initial metadata payload: connection_id={} sqlcl_connection={} display_name={}",
            connection_id,
            sqlcl_connection_name,
            display_name,
        )
        connection_info = self._fetch_connection_info(sqlcl_connection_name)
        current_schema = validate_schema_name(
            str(connection_info.get("connected_schema") or connection_info.get("username") or "PUBLIC")
        )

        created_at = utc_now_iso()
        username = str(connection_info.get("username") or current_schema).upper()
        server_host = str(connection_info.get("server_host") or "").strip() or "database"
        service_name = str(connection_info.get("service_name") or connection_info.get("db_name") or "").strip()
        connect_string = f"{server_host}/{service_name}" if service_name else server_host
        connection_label = (
            f"{username.lower()}@{connect_string}"
            if connect_string
            else f"{username.lower()}@{sqlcl_connection_name}"
        )

        tree = self._build_root_tree(
            connection_id=connection_id,
            display_name=display_name,
            sqlcl_connection_name=sqlcl_connection_name,
            connection_label=connection_label,
            connected_schema=current_schema,
        )
        payload = {
            "connection": {
                "id": connection_id,
                "display_name": display_name,
                "sqlcl_connection_name": sqlcl_connection_name,
                "username": username,
                "connect_string": connect_string or sqlcl_connection_name,
                "connected_schema": current_schema,
                "created_at": created_at,
                "updated_at": created_at,
            },
            "tree": tree,
        }
        logger.info(
            "Built initial metadata payload: connection_id={} sqlcl_connection={} connected_schema={} elapsed_ms={:.1f}",
            connection_id,
            sqlcl_connection_name,
            current_schema,
            (time.perf_counter() - started_at) * 1000,
        )
        return payload

    def _build_root_tree(
        self,
        *,
        connection_id: str,
        display_name: str,
        sqlcl_connection_name: str,
        connection_label: str,
        connected_schema: str,
    ) -> dict[str, Any]:
        root_path = "Oracle Connections"
        connection_path = f"{root_path}/{display_name}"
        return self._make_node(
            node_id="root",
            label="Oracle Connections",
            node_type="root",
            path=root_path,
            children=[
                self._make_node(
                    node_id=f"conn:{connection_id}",
                    label=display_name,
                    node_type="connection",
                    path=connection_path,
                    children=[
                        self._make_node(
                            node_id=f"conn-info:{connection_id}",
                            label=connection_label,
                            node_type="connection_info",
                            path=f"{connection_path}/{connection_label}",
                            children=[],
                            metadata={"status": "connected", "sqlclConnectionName": sqlcl_connection_name},
                        ),
                        self._make_node(
                            node_id=f"connected-to:{connected_schema}",
                            label=f"Connected to {connected_schema}",
                            node_type="connected_schema",
                            path=f"{connection_path}/Connected to {connected_schema}",
                            children=[],
                            metadata={"schemaName": connected_schema},
                        ),
                        self._make_node(
                            node_id="dbops",
                            label="DBOps",
                            node_type="dbops_root",
                            path=f"{connection_path}/DBOps",
                            children=self._build_dbops_children(
                                connected_schema=connected_schema,
                                path=f"{connection_path}/DBOps",
                            ),
                            metadata={"schemaName": connected_schema},
                        ),
                        self._make_node(
                            node_id="selectai",
                            label="SelectAI",
                            node_type="selectai_root",
                            path=f"{connection_path}/SelectAI",
                            children=[],
                            loaded=False,
                            metadata={"schemaName": connected_schema},
                        ),
                        self._make_node(
                            node_id="schemas",
                            label="Schemas",
                            node_type="schemas_root",
                            path=f"{connection_path}/Schemas",
                            children=[
                                self._build_schema_node(
                                    scope_prefix="schema",
                                    schema_name=connected_schema,
                                    path=f"{connection_path}/Schemas/{connected_schema}",
                                )
                            ],
                            metadata={"connectedSchema": connected_schema},
                        ),
                    ],
                    metadata={"status": "connected", "connectionId": connection_id},
                )
            ],
            metadata={"connectionId": connection_id},
        )

    def _build_dbops_children(self, *, connected_schema: str, path: str) -> list[dict[str, Any]]:
        return [
            self._make_folder_node(
                scope_prefix="schema",
                owner_name=connected_schema,
                folder_spec=spec,
                path=f"{path}/{spec['label']}",
            )
            for spec in DBOPS_FOLDER_SPECS
        ]

    def _build_schema_node(self, *, scope_prefix: str, schema_name: str, path: str) -> dict[str, Any]:
        children = [
            self._make_folder_node(
                scope_prefix=scope_prefix,
                owner_name=schema_name,
                folder_spec=spec,
                path=f"{path}/{spec['label']}",
            )
            for spec in SCHEMA_FOLDER_SPECS
        ]
        return self._make_node(
            node_id=f"{scope_prefix}:{schema_name}",
            label=schema_name,
            node_type="schema",
            path=path,
            children=children,
            metadata={"schemaName": schema_name},
        )

    def _build_user_node(self, *, user_name: str, path: str) -> dict[str, Any]:
        children = [
            self._make_folder_node(
                scope_prefix="user",
                owner_name=user_name,
                folder_spec=spec,
                path=f"{path}/{spec['label']}",
            )
            for spec in USER_FOLDER_SPECS
        ]
        return self._make_node(
            node_id=f"user:{user_name}",
            label=user_name,
            node_type="user",
            path=path,
            children=children,
            metadata={"schemaName": user_name},
        )

    def _make_folder_node(
        self,
        *,
        scope_prefix: str,
        owner_name: str,
        folder_spec: dict[str, str],
        path: str,
    ) -> dict[str, Any]:
        loaded = False
        return self._make_node(
            node_id=f"{scope_prefix}:{owner_name}:{folder_spec['key']}",
            label=folder_spec["label"],
            node_type=folder_spec["folder_type"],
            path=path,
            children=[],
            loaded=loaded,
            metadata={"schemaName": owner_name, "itemType": folder_spec["item_type"]},
        )

    def _upgrade_static_folder_nodes(self, tree: dict[str, Any]) -> bool:
        changed = False

        def visit(node: dict[str, Any]) -> None:
            nonlocal changed
            node_type = str(node.get("type") or "")
            if node_type == "connection":
                if self._upgrade_connection_children(node):
                    changed = True
            elif node_type == "dbops_root":
                if self._upgrade_folder_children_for_parent(node, scope_prefix="schema", owner_key="schemaName"):
                    changed = True
            elif node_type == "schema":
                if self._upgrade_folder_children_for_parent(node, scope_prefix="schema", owner_key="schemaName"):
                    changed = True
            elif node_type == "user":
                if self._upgrade_folder_children_for_parent(node, scope_prefix="user", owner_key="schemaName"):
                    changed = True
            for child in node.get("children", []) or []:
                if isinstance(child, dict):
                    visit(child)

        visit(tree)
        return changed

    def _upgrade_connection_children(self, node: dict[str, Any]) -> bool:
        existing_children = [child for child in (node.get("children") or []) if isinstance(child, dict)]
        existing_by_type = {str(child.get("type") or ""): child for child in existing_children}
        connected_schema_node = existing_by_type.get("connected_schema")
        schemas_root = existing_by_type.get("schemas_root")
        users_root = existing_by_type.get("users_root")
        if connected_schema_node is None or schemas_root is None:
            return False
        schema_name = str((connected_schema_node.get("metadata") or {}).get("schemaName") or "").strip().upper()
        if not schema_name:
            return False
        connection_path = str((node.get("metadata") or {}).get("nodePath") or node.get("label") or node.get("id"))
        dbops_root = existing_by_type.get("dbops_root")
        if dbops_root is None:
            dbops_root = self._make_node(
                node_id="dbops",
                label="DBOps",
                node_type="dbops_root",
                path=f"{connection_path}/DBOps",
                children=[],
                metadata={"schemaName": schema_name},
            )
        else:
            dbops_root_metadata = dbops_root.get("metadata")
            if not isinstance(dbops_root_metadata, dict):
                dbops_root_metadata = {}
            dbops_root_metadata["schemaName"] = schema_name
            dbops_root["metadata"] = dbops_root_metadata
        selectai_root = existing_by_type.get("selectai_root")
        if selectai_root is None:
            selectai_root = self._make_node(
                node_id="selectai",
                label="SelectAI",
                node_type="selectai_root",
                path=f"{connection_path}/SelectAI",
                children=[],
                metadata={"schemaName": schema_name},
            )
        else:
            selectai_root_metadata = selectai_root.get("metadata")
            if not isinstance(selectai_root_metadata, dict):
                selectai_root_metadata = {}
            selectai_root_metadata["schemaName"] = schema_name
            selectai_root["metadata"] = selectai_root_metadata
            if not selectai_root_metadata.get("profileListLoaded") and not selectai_root.get("children"):
                selectai_root["loaded"] = False
        dbops_existing_children = [
            child for child in (dbops_root.get("children") or []) if isinstance(child, dict)
        ]

        schema_node = next(
            (
                child
                for child in (schemas_root.get("children") or [])
                if isinstance(child, dict) and str(child.get("id") or "") == f"schema:{schema_name}"
            ),
            None,
        )
        if schema_node is not None:
            schema_children = [child for child in (schema_node.get("children") or []) if isinstance(child, dict)]
            existing_dbops_children = {
                str(child.get("type") or ""): child
                for child in (dbops_root.get("children") or [])
                if isinstance(child, dict)
            }
            for spec in DBOPS_FOLDER_SPECS:
                moved_child = next(
                    (child for child in schema_children if str(child.get("type") or "") == spec["folder_type"]),
                    None,
                )
                if moved_child is not None and spec["folder_type"] not in existing_dbops_children:
                    existing_dbops_children[spec["folder_type"]] = moved_child
            dbops_root["children"] = [
                existing_dbops_children.get(spec["folder_type"])
                or self._make_folder_node(
                    scope_prefix="schema",
                    owner_name=schema_name,
                    folder_spec=spec,
                    path=f"{connection_path}/DBOps/{spec['label']}",
                )
                for spec in DBOPS_FOLDER_SPECS
            ]
        dbops_changed = [child.get("id") for child in (dbops_root.get("children") or [])] != [
            child.get("id") for child in dbops_existing_children
        ]

        ordered_children: list[dict[str, Any]] = []
        for child_type in ("connection_info", "connected_schema", "dbops_root", "selectai_root", "schemas_root"):
            child = {
                "connection_info": existing_by_type.get("connection_info"),
                "connected_schema": connected_schema_node,
                "dbops_root": dbops_root,
                "selectai_root": selectai_root,
                "schemas_root": schemas_root,
            }[child_type]
            if child is not None:
                ordered_children.append(child)

        remaining_children = [
            child
            for child in existing_children
            if child not in ordered_children and str(child.get("type") or "") != "users_root"
        ]
        if remaining_children:
            ordered_children.extend(remaining_children)

        changed = [child.get("id") for child in ordered_children] != [child.get("id") for child in existing_children]
        if users_root is not None:
            changed = True
        if changed:
            node["children"] = ordered_children
        elif dbops_changed:
            node["children"] = ordered_children
            changed = True
        elif dbops_root is not existing_by_type.get("dbops_root"):
            node["children"] = ordered_children
            changed = True
        return changed

    def _upgrade_folder_children_for_parent(
        self,
        node: dict[str, Any],
        *,
        scope_prefix: str,
        owner_key: str,
    ) -> bool:
        metadata = node.get("metadata") or {}
        owner_name = metadata.get(owner_key)
        if not isinstance(owner_name, str) or not owner_name.strip():
            return False

        existing_children = [child for child in (node.get("children") or []) if isinstance(child, dict)]
        existing_by_id = {
            str(child.get("id")): child
            for child in existing_children
            if str(child.get("type") or "").endswith("_folder")
        }
        path = str(metadata.get("nodePath") or node.get("label") or node.get("id"))
        next_children: list[dict[str, Any]] = []
        changed = False

        for spec in folder_specs_for_node(str(node["type"])):
            expected_id = f"{scope_prefix}:{owner_name}:{spec['key']}"
            child = existing_by_id.get(expected_id)
            if child is None:
                child = self._make_folder_node(
                    scope_prefix=scope_prefix,
                    owner_name=owner_name,
                    folder_spec=spec,
                    path=f"{path}/{spec['label']}",
                )
                changed = True
            elif spec["folder_type"] in {"dictionary_table_folder", "useful_diagnoses_folder"} and not child.get("children"):
                if child.get("loaded") is True:
                    child["loaded"] = False
                    changed = True
            next_children.append(child)

        other_children = [
            child
            for child in existing_children
            if not str(child.get("type") or "").endswith("_folder")
        ]
        if other_children:
            next_children.extend(other_children)

        if len(next_children) != len(existing_children):
            changed = True
        elif [child.get("id") for child in next_children] != [child.get("id") for child in existing_children]:
            changed = True

        if changed:
            node["children"] = next_children
        return changed

    def _make_object_children(
        self,
        *,
        node: dict[str, Any],
        schema_name: str,
        object_names: list[str],
    ) -> list[dict[str, Any]]:
        metadata = node.get("metadata") or {}
        item_type = str(metadata.get("itemType") or "empty")
        parent_path = str(metadata.get("nodePath") or node.get("label") or node.get("id"))
        scope_prefix = "schema" if str(node["id"]).startswith("schema:") else "user"
        if not object_names:
            return [
                self._make_node(
                    node_id=f"{node['id']}:empty",
                    label="(empty)",
                    node_type="empty",
                    path=f"{parent_path}/(empty)",
                    children=[],
                )
            ]
        return [
            self._make_node(
                node_id=f"{scope_prefix}:{schema_name}:{item_type}:{object_name}",
                label=object_name,
                node_type=item_type,
                path=f"{parent_path}/{object_name}",
                children=[],
                metadata={"schemaName": schema_name, "objectName": object_name},
            )
            for object_name in object_names
        ]

    def _make_node(
        self,
        *,
        node_id: str,
        label: str,
        node_type: str,
        path: str,
        children: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
        loaded: bool = True,
    ) -> dict[str, Any]:
        node_metadata = dict(metadata or {})
        node_metadata.setdefault("nodePath", path)
        return {
            "id": node_id,
            "label": label,
            "type": node_type,
            "icon": icon_for(node_type),
            "loaded": loaded,
            "children": children,
            "metadata": node_metadata,
        }

    def _build_children_for_node(
        self,
        *,
        payload: dict[str, Any],
        node: dict[str, Any],
        sqlcl_connection_name: str,
        schema_name: str | None,
    ) -> list[dict[str, Any]]:
        node_type = str(node["type"])
        if node_type == "dbops_root":
            connected_schema = self._resolve_schema_name(node, schema_name)
            path = str((node.get("metadata") or {}).get("nodePath") or node["label"])
            return self._build_dbops_children(connected_schema=connected_schema, path=path)
        if node_type == "schemas_root":
            connected_schema = validate_schema_name(payload["connection"]["connected_schema"])
            path = str((node.get("metadata") or {}).get("nodePath") or node["label"])
            return [
                self._build_schema_node(
                    scope_prefix="schema",
                    schema_name=connected_schema,
                    path=f"{path}/{connected_schema}",
                )
            ]
        if node_type == "selectai_root":
            return self._build_selectai_profile_children(node=node, sqlcl_connection_name=sqlcl_connection_name)
        if node_type == "users_root":
            path = str((node.get("metadata") or {}).get("nodePath") or node["label"])
            return [
                self._build_user_node(user_name=user_name, path=f"{path}/{user_name}")
                for user_name in self._fetch_all_users(sqlcl_connection_name)
            ]
        if node_type == "schema":
            resolved_schema = self._resolve_schema_name(node, schema_name)
            path = str((node.get("metadata") or {}).get("nodePath") or node["label"])
            return [
                self._make_folder_node(
                    scope_prefix="schema",
                    owner_name=resolved_schema,
                    folder_spec=spec,
                    path=f"{path}/{spec['label']}",
                )
                for spec in folder_specs_for_node("schema")
            ]
        if node_type == "user":
            resolved_schema = self._resolve_schema_name(node, schema_name)
            path = str((node.get("metadata") or {}).get("nodePath") or node["label"])
            return [
                self._make_folder_node(
                    scope_prefix="user",
                    owner_name=resolved_schema,
                    folder_spec=spec,
                    path=f"{path}/{spec['label']}",
                )
                for spec in folder_specs_for_node("user")
            ]
        if node_type == "dynamic_views_folder":
            resolved_schema = self._resolve_schema_name(node, schema_name)
            object_rows = self._fetch_dynamic_view_names(sqlcl_connection_name)
            return self._make_object_children(node=node, schema_name=resolved_schema, object_names=object_rows)
        if node_type == "dictionary_table_folder":
            resolved_schema = self._resolve_schema_name(node, schema_name)
            return self._build_dictionary_table_children(
                node=node,
                schema_name=resolved_schema,
                sqlcl_connection_name=sqlcl_connection_name,
            )
        if node_type == "useful_diagnoses_folder":
            resolved_schema = self._resolve_schema_name(node, schema_name)
            return self._build_useful_diagnosis_children(node=node, schema_name=resolved_schema)
        resolved_schema = self._resolve_schema_name(node, schema_name)
        object_rows = self._fetch_metadata_object_names(
            sqlcl_connection_name=sqlcl_connection_name,
            node_type=node_type,
            schema_name=resolved_schema,
        )
        return self._make_object_children(node=node, schema_name=resolved_schema, object_names=object_rows)

    def _resolve_schema_name(self, node: dict[str, Any], schema_name: str | None) -> str:
        if schema_name:
            return validate_schema_name(schema_name)
        metadata = node.get("metadata") or {}
        candidate = metadata.get("schemaName")
        if isinstance(candidate, str) and candidate.strip():
            return validate_schema_name(candidate)
        parts = str(node.get("id", "")).split(":")
        if len(parts) >= 2:
            return validate_schema_name(parts[1])
        raise ValueError("Schema name is required for this node")

    def _fetch_connection_info(self, sqlcl_connection_name: str) -> dict[str, Any]:
        payload = run_sqlcl_json(
            sqlcl_connection_name,
            build_connection_info_sql(),
            operation="metadata_connection_info",
        )
        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected SQLcl payload for connection info")
        return payload

    def _probe_connection(self, sqlcl_connection_name: str) -> None:
        logger.info("Probing metadata connection: sqlcl_connection={}", sqlcl_connection_name)
        payload = run_sqlcl_json(
            sqlcl_connection_name,
            build_connection_probe_sql(),
            operation="metadata_connection_probe",
        )
        if not isinstance(payload, dict) or payload.get("status") != "ok":
            raise RuntimeError("Unexpected SQLcl payload for connection probe")
        logger.info("Metadata connection probe succeeded: sqlcl_connection={}", sqlcl_connection_name)

    def _fetch_all_users(self, sqlcl_connection_name: str) -> list[str]:
        payload = run_sqlcl_json(
            sqlcl_connection_name,
            build_all_users_sql(),
            operation="metadata_all_users",
        )
        if not isinstance(payload, list):
            raise RuntimeError("Unexpected SQLcl payload for users list")
        users = []
        for row in payload:
            if isinstance(row, dict) and isinstance(row.get("name"), str):
                users.append(validate_schema_name(row["name"]))
        return sorted(dict.fromkeys(users))

    def _fetch_metadata_object_names(
        self,
        *,
        sqlcl_connection_name: str,
        node_type: str,
        schema_name: str,
    ) -> list[str]:
        payload = run_sqlcl_json(
            sqlcl_connection_name,
            build_folder_query(node_type, schema_name),
            operation=f"metadata_{node_type}:{schema_name}",
        )
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected SQLcl payload for node type: {node_type}")
        names = []
        for row in payload:
            if isinstance(row, dict) and isinstance(row.get("name"), str):
                names.append(row["name"])
        return names

    def _build_useful_diagnosis_children(self, *, node: dict[str, Any], schema_name: str) -> list[dict[str, Any]]:
        parent_path = str((node.get("metadata") or {}).get("nodePath") or node.get("label") or node.get("id"))
        items = load_useful_diagnoses(self._config_base_dir)
        if not items:
            return [
                self._make_node(
                    node_id=f"{node['id']}:empty",
                    label="(empty)",
                    node_type="empty",
                    path=f"{parent_path}/(empty)",
                    children=[],
                )
            ]
        return [
            self._make_node(
                node_id=f"schema:{schema_name}:useful_diagnosis:{item['key']}",
                label=item["label"],
                node_type="useful_diagnosis",
                path=f"{parent_path}/{item['label']}",
                children=[],
                metadata={
                    "schemaName": schema_name,
                    "diagnosisKey": item["key"],
                    "sqlText": item["sql"],
                },
            )
            for item in items
        ]

    def _build_selectai_profile_children(
        self,
        *,
        node: dict[str, Any],
        sqlcl_connection_name: str,
    ) -> list[dict[str, Any]]:
        parent_path = str((node.get("metadata") or {}).get("nodePath") or node.get("label") or node.get("id"))
        profile_names = self._fetch_selectai_profile_names(sqlcl_connection_name)
        return [
            self._make_node(
                node_id=f"selectai:profile:{profile_name}",
                label=profile_name,
                node_type="selectai_profile",
                path=f"{parent_path}/{profile_name}",
                children=[],
                metadata={"profileName": profile_name},
            )
            for profile_name in profile_names
        ]

    def _build_dictionary_table_children(
        self,
        *,
        node: dict[str, Any],
        schema_name: str,
        sqlcl_connection_name: str,
    ) -> list[dict[str, Any]]:
        parent_path = str((node.get("metadata") or {}).get("nodePath") or node.get("label") or node.get("id"))
        items = load_dictionary_tables(self._config_base_dir)
        if not items:
            return [
                self._make_node(
                    node_id=f"{node['id']}:empty",
                    label="(empty)",
                    node_type="empty",
                    path=f"{parent_path}/(empty)",
                    children=[],
                )
            ]
        available_names = set(
            self._fetch_accessible_object_names(
                sqlcl_connection_name,
                [item["objectName"] for item in items],
                operation="metadata_dictionary_tables",
            )
        )
        filtered_items = [item for item in items if item["objectName"] in available_names]
        if not filtered_items:
            return [
                self._make_node(
                    node_id=f"{node['id']}:empty",
                    label="(empty)",
                    node_type="empty",
                    path=f"{parent_path}/(empty)",
                    children=[],
                )
            ]
        return [
            self._make_node(
                node_id=f"schema:{schema_name}:dictionary_table:{item['key']}",
                label=item["label"],
                node_type="dictionary_table_item",
                path=f"{parent_path}/{item['label']}",
                children=[],
                metadata={
                    "schemaName": schema_name,
                    "dictionaryKey": item["key"],
                    "objectName": item["objectName"],
                    "sqlText": item["sql"],
                },
            )
            for item in filtered_items
        ]

    def _fetch_dynamic_view_names(self, sqlcl_connection_name: str) -> list[str]:
        configured_views = load_dynamic_views(self._config_base_dir)
        if not configured_views:
            return []
        return self._fetch_accessible_object_names(
            sqlcl_connection_name,
            configured_views,
            operation="metadata_dynamic_views",
        )

    def _fetch_selectai_profile_names(self, sqlcl_connection_name: str) -> list[str]:
        try:
            payload = run_sqlcl_json(
                sqlcl_connection_name,
                build_selectai_profiles_sql(),
                operation="metadata_selectai_profiles",
            )
        except RuntimeError as exc:
            detail = str(exc)
            if "ORA-00942" in detail or "table or view does not exist" in detail.lower():
                return []
            raise
        if not isinstance(payload, list):
            raise RuntimeError("Unexpected SQLcl payload for SelectAI profiles")
        profile_names: list[str] = []
        for row in payload:
            if isinstance(row, dict) and isinstance(row.get("name"), str):
                profile_name = row["name"].strip()
                if profile_name:
                    profile_names.append(profile_name)
        return list(dict.fromkeys(profile_names))

    def _fetch_accessible_object_names(
        self,
        sqlcl_connection_name: str,
        object_names: list[str],
        *,
        operation: str,
    ) -> list[str]:
        payload = run_sqlcl_json(
            sqlcl_connection_name,
            build_accessible_object_names_query(object_names),
            operation=operation,
        )
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected SQLcl payload for accessible object list: {operation}")
        names = []
        for row in payload:
            if isinstance(row, dict) and isinstance(row.get("name"), str):
                names.append(row["name"])
        return names

    def _table_ddl_cache_path(
        self,
        *,
        sqlcl_connection_name: str,
        schema_name: str,
        table_name: str,
    ):
        root = self._cache_base_dir
        if root is None:
            raise RuntimeError("Metadata cache base directory is not configured")
        return root / sqlcl_connection_name / schema_name / "Tables" / f"{table_name}.sql"

    def _procedure_ddl_cache_path(
        self,
        *,
        sqlcl_connection_name: str,
        schema_name: str,
        procedure_name: str,
    ):
        root = self._cache_base_dir
        if root is None:
            raise RuntimeError("Metadata cache base directory is not configured")
        return root / sqlcl_connection_name / schema_name / "Procedures" / f"{procedure_name}.sql"

    def _source_ddl_cache_path(
        self,
        *,
        sqlcl_connection_name: str,
        schema_name: str,
        object_type: str,
        object_name: str,
    ):
        _, config = self._resolve_source_ddl_type(object_type)
        root = self._cache_base_dir
        if root is None:
            raise RuntimeError("Metadata cache base directory is not configured")
        return root / sqlcl_connection_name / schema_name / config["cache_folder"] / f"{object_name}.sql"

    def _fetch_table_ddl(
        self,
        *,
        sqlcl_connection_name: str,
        schema_name: str,
        table_name: str,
    ) -> str:
        sql_text = run_sqlcl(
            sqlcl_connection_name,
            build_table_quick_ddl_sql(schema_name, table_name),
            timeout=180,
            operation=f"metadata_table_ddl:{schema_name}.{table_name}",
        )
        normalized = sql_text.replace("\r\n", "\n").strip()
        if not normalized:
            raise RuntimeError(f"SQLcl returned empty DDL for {schema_name}.{table_name}")
        return normalized

    def _fetch_procedure_ddl(
        self,
        *,
        sqlcl_connection_name: str,
        schema_name: str,
        procedure_name: str,
    ) -> str:
        return self._fetch_source_ddl(
            sqlcl_connection_name=sqlcl_connection_name,
            schema_name=schema_name,
            object_type="procedure",
            object_name=procedure_name,
        )

    def _fetch_source_ddl(
        self,
        *,
        sqlcl_connection_name: str,
        schema_name: str,
        object_type: str,
        object_name: str,
    ) -> str:
        resolved_type, config = self._resolve_source_ddl_type(object_type)
        fetch_mode = config.get("fetch_mode", "get_ddl")
        if fetch_mode == "all_source":
            sql_builder = build_plsql_source_object_sql(
                schema_name,
                object_name,
                config["source_object_type"],
            )
        else:
            sql_builder = build_source_object_quick_ddl_sql(
                schema_name,
                object_name,
                config["ddl_object_type"],
                config["label"],
            )
        sql_text = run_sqlcl(
            sqlcl_connection_name,
            sql_builder,
            timeout=180,
            operation=f"{config['operation']}:{schema_name}.{object_name}",
        )
        normalized = sql_text.replace("\r\n", "\n").strip()
        if not normalized:
            raise RuntimeError(f"SQLcl returned empty DDL for {schema_name}.{object_name} ({resolved_type})")
        return normalized

    def _resolve_source_ddl_type(self, object_type: str) -> tuple[str, dict[str, str]]:
        normalized = (object_type or "").strip().lower()
        config = SOURCE_DDL_NODE_TYPE_CONFIG.get(normalized)
        if config is None:
            raise ValueError(f"Unsupported source DDL object type: {object_type}")
        return normalized, config

    def _read_required_cache(self, connection_id: str) -> dict[str, Any]:
        payload = read_cache(connection_id, self._cache_base_dir)
        if payload is None:
            raise FileNotFoundError(f"Metadata cache does not exist for connection: {connection_id}")
        return payload
