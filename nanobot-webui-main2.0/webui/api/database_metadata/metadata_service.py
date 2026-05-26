"""Service layer for SQLcl-backed Oracle metadata tree browsing."""

from __future__ import annotations

from typing import Any

from loguru import logger

from .metadata_sql import (
    REFRESHABLE_NODE_TYPES,
    SCHEMA_FOLDER_SPECS,
    USER_FOLDER_SPECS,
    build_all_users_sql,
    build_connection_info_sql,
    build_folder_query,
    folder_specs_for_node,
    icon_for,
    utc_now_iso,
    validate_schema_name,
    validate_sqlcl_connection_name,
)
from .sqlcl_runner import run_sqlcl_json
from .yaml_cache import cache_file_path, find_node_by_id, read_cache, write_cache


class DatabaseMetadataService:
    """Create, cache, load, and partially refresh Oracle metadata trees."""

    def __init__(self, *, cache_base_dir=None):
        self._cache_base_dir = cache_base_dir

    def open_connection(
        self,
        *,
        connection_id: str,
        sqlcl_connection_name: str,
        display_name: str,
    ) -> dict[str, Any]:
        connection_name = validate_sqlcl_connection_name(sqlcl_connection_name)
        cache_payload = read_cache(connection_id, self._cache_base_dir)
        if cache_payload is not None:
            return {
                "success": True,
                "fromCache": True,
                "connectionId": connection_id,
                "tree": cache_payload["tree"],
            }

        payload = self._build_initial_payload(
            connection_id=connection_id,
            sqlcl_connection_name=connection_name,
            display_name=display_name or connection_id,
        )
        write_cache(connection_id, payload, self._cache_base_dir)
        logger.info(
            "Initialized database metadata cache: connection_id={} sqlcl_connection={} cache_file={}",
            connection_id,
            connection_name,
            cache_file_path(connection_id, self._cache_base_dir),
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
        connection_name = validate_sqlcl_connection_name(sqlcl_connection_name)
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
        node["metadata"] = metadata
        payload["connection"]["updated_at"] = refreshed_at
        write_cache(connection_id, payload, self._cache_base_dir)

        refreshed_node = find_node_by_id(tree, node_id)
        logger.info(
            "Refreshed database metadata node: connection_id={} node_id={} node_type={} child_count={}",
            connection_id,
            node_id,
            node_type,
            len(children),
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
        connection_info = self._fetch_connection_info(sqlcl_connection_name)
        all_users = self._fetch_all_users(sqlcl_connection_name)
        current_schema = validate_schema_name(
            str(connection_info.get("connected_schema") or connection_info.get("username") or "PUBLIC")
        )
        if current_schema not in all_users:
            all_users.append(current_schema)
            all_users.sort()

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
            users=all_users,
        )
        return {
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

    def _build_root_tree(
        self,
        *,
        connection_id: str,
        display_name: str,
        sqlcl_connection_name: str,
        connection_label: str,
        connected_schema: str,
        users: list[str],
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
                        self._make_node(
                            node_id="users",
                            label="Users",
                            node_type="users_root",
                            path=f"{connection_path}/Users",
                            children=[
                                self._build_user_node(
                                    user_name=user_name,
                                    path=f"{connection_path}/Users/{user_name}",
                                )
                                for user_name in users
                            ],
                        ),
                    ],
                    metadata={"status": "connected", "connectionId": connection_id},
                )
            ],
            metadata={"connectionId": connection_id},
        )

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
        return self._make_node(
            node_id=f"{scope_prefix}:{owner_name}:{folder_spec['key']}",
            label=folder_spec["label"],
            node_type=folder_spec["folder_type"],
            path=path,
            children=[],
            loaded=False,
            metadata={"schemaName": owner_name, "itemType": folder_spec["item_type"]},
        )

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
        payload = run_sqlcl_json(sqlcl_connection_name, build_connection_info_sql())
        if not isinstance(payload, dict):
            raise RuntimeError("Unexpected SQLcl payload for connection info")
        return payload

    def _fetch_all_users(self, sqlcl_connection_name: str) -> list[str]:
        payload = run_sqlcl_json(sqlcl_connection_name, build_all_users_sql())
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
        payload = run_sqlcl_json(sqlcl_connection_name, build_folder_query(node_type, schema_name))
        if not isinstance(payload, list):
            raise RuntimeError(f"Unexpected SQLcl payload for node type: {node_type}")
        names = []
        for row in payload:
            if isinstance(row, dict) and isinstance(row.get("name"), str):
                names.append(row["name"])
        return names

    def _read_required_cache(self, connection_id: str) -> dict[str, Any]:
        payload = read_cache(connection_id, self._cache_base_dir)
        if payload is None:
            raise FileNotFoundError(f"Metadata cache does not exist for connection: {connection_id}")
        return payload
