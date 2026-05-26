"""SQL builders and tree metadata constants for Oracle metadata explorer."""

from __future__ import annotations

import re
import textwrap
from datetime import datetime, timezone

CONNECTION_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
SCHEMA_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,127}$")

ICON_MAP: dict[str, str] = {
    "root": "oracle_connection.png",
    "connection": "connected_database.png",
    "connection_info": "connected_database.png",
    "connected_schema": "schema.png",
    "schemas_root": "schema.png",
    "schema": "schema.png",
    "users_root": "users.png",
    "user": "users.png",
    "tables_folder": "table.png",
    "table": "table.png",
    "indexes_folder": "index.png",
    "index": "index.png",
    "views_folder": "view.png",
    "view": "view.png",
    "package_specs_folder": "package.png",
    "package_spec": "package.png",
    "package_bodies_folder": "package.png",
    "package_body": "package.png",
    "functions_folder": "function.png",
    "function": "function.png",
    "procedures_folder": "procedure.png",
    "procedure": "procedure.png",
    "queues_folder": "queue.png",
    "queue": "queue.png",
    "triggers_folder": "trigger.png",
    "trigger": "trigger.png",
    "types_folder": "types.png",
    "type": "types.png",
    "type_bodies_folder": "types.png",
    "type_body": "types.png",
    "sequences_folder": "sequence.png",
    "sequence": "sequence.png",
    "materialized_views_folder": "materialized_view.png",
    "materialized_view": "materialized_view.png",
    "synonyms_folder": "synonyms.png",
    "synonym": "synonyms.png",
    "db_links_folder": "db_links.png",
    "db_link": "db_links.png",
    "directories_folder": "directory.png",
    "directory": "directory.png",
    "java_objects_folder": "java.png",
    "java_object": "java.png",
    "scheduler_jobs_folder": "scheduler_job.png",
    "scheduler_job": "scheduler_job.png",
    "empty": "oracle_connection.png",
}

SCHEMA_FOLDER_SPECS: list[dict[str, str]] = [
    {"key": "tables", "label": "Tables", "folder_type": "tables_folder", "item_type": "table"},
    {"key": "indexes", "label": "Indexes", "folder_type": "indexes_folder", "item_type": "index"},
    {"key": "views", "label": "Views", "folder_type": "views_folder", "item_type": "view"},
    {"key": "package_specs", "label": "Package Specs", "folder_type": "package_specs_folder", "item_type": "package_spec"},
    {"key": "package_bodies", "label": "Package Bodies", "folder_type": "package_bodies_folder", "item_type": "package_body"},
    {"key": "functions", "label": "Functions", "folder_type": "functions_folder", "item_type": "function"},
    {"key": "procedures", "label": "Procedures", "folder_type": "procedures_folder", "item_type": "procedure"},
    {"key": "queues", "label": "Queues", "folder_type": "queues_folder", "item_type": "queue"},
    {"key": "triggers", "label": "Triggers", "folder_type": "triggers_folder", "item_type": "trigger"},
    {"key": "types", "label": "Types", "folder_type": "types_folder", "item_type": "type"},
    {"key": "type_bodies", "label": "Type Bodies", "folder_type": "type_bodies_folder", "item_type": "type_body"},
    {"key": "sequences", "label": "Sequences", "folder_type": "sequences_folder", "item_type": "sequence"},
    {
        "key": "materialized_views",
        "label": "Materialized Views",
        "folder_type": "materialized_views_folder",
        "item_type": "materialized_view",
    },
    {"key": "synonyms", "label": "Synonyms", "folder_type": "synonyms_folder", "item_type": "synonym"},
    {"key": "db_links", "label": "DB Links", "folder_type": "db_links_folder", "item_type": "db_link"},
    {"key": "directories", "label": "Directories", "folder_type": "directories_folder", "item_type": "directory"},
    {"key": "java_objects", "label": "Java Objects", "folder_type": "java_objects_folder", "item_type": "java_object"},
    {
        "key": "scheduler_jobs",
        "label": "Scheduler Jobs",
        "folder_type": "scheduler_jobs_folder",
        "item_type": "scheduler_job",
    },
]

USER_FOLDER_SPECS: list[dict[str, str]] = [
    {"key": "tables", "label": "Tables", "folder_type": "tables_folder", "item_type": "table"},
]

REFRESHABLE_NODE_TYPES = {
    "schemas_root",
    "schema",
    "users_root",
    "user",
    *[spec["folder_type"] for spec in SCHEMA_FOLDER_SPECS],
    *[spec["folder_type"] for spec in USER_FOLDER_SPECS],
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def icon_for(node_type: str) -> str:
    return ICON_MAP.get(node_type, ICON_MAP["empty"])


def validate_sqlcl_connection_name(name: str) -> str:
    connection_name = name.strip()
    if not connection_name or CONNECTION_NAME_PATTERN.fullmatch(connection_name) is None:
        raise ValueError("Invalid SQLcl saved connection name")
    return connection_name


def validate_schema_name(name: str) -> str:
    schema_name = name.strip().upper()
    if not schema_name or SCHEMA_NAME_PATTERN.fullmatch(schema_name) is None:
        raise ValueError("Invalid Oracle schema name")
    return schema_name


def escape_sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _sqlcl_prefix() -> str:
    return "\n".join(
        [
            "set heading off",
            "set feedback off",
            "set pagesize 0",
            "set linesize 32767",
            "set trimspool on",
            "set serveroutput off",
            "set long 1000000",
            "set longchunksize 1000000",
        ]
    )


def wrap_sql(sql_body: str) -> str:
    return f"{_sqlcl_prefix()}\n{sql_body.strip()};\nexit\n"


def build_connection_info_sql() -> str:
    return wrap_sql(
        """
        select json_serialize(
                 json_object(
                   'username' value user,
                   'connected_schema' value sys_context('USERENV', 'CURRENT_SCHEMA'),
                   'service_name' value sys_context('USERENV', 'SERVICE_NAME'),
                   'server_host' value sys_context('USERENV', 'SERVER_HOST'),
                   'db_name' value sys_context('USERENV', 'DB_NAME')
                   returning clob
                 ) returning clob
               )
        from dual
        """
    )


def build_all_users_sql() -> str:
    return wrap_sql(
        """
        select coalesce(
                 json_serialize(
                   json_arrayagg(
                     json_object('name' value username)
                     order by username
                     returning clob
                   ) returning clob
                 ),
                 to_clob('[]')
               )
        from all_users
        """
    )


def folder_specs_for_node(node_type: str) -> list[dict[str, str]]:
    if node_type == "schema":
        return SCHEMA_FOLDER_SPECS
    if node_type == "user":
        return USER_FOLDER_SPECS
    raise ValueError(f"Unsupported folder parent node type: {node_type}")


def build_folder_query(node_type: str, schema_name: str) -> str:
    owner = escape_sql_literal(validate_schema_name(schema_name))
    select_sql = textwrap.indent(_build_select_sql(node_type, owner).strip(), " " * 8)
    return wrap_sql(
        f"""
        select coalesce(
                 json_serialize(
                   json_arrayagg(
                     json_object('name' value name)
                     order by name
                     returning clob
                   ) returning clob
                 ),
                 to_clob('[]')
               )
        from (
{select_sql}
        ) metadata_rows
        """
    )


def _build_select_sql(node_type: str, owner: str) -> str:
    if node_type == "tables_folder":
        return f"""
            select table_name as name
            from all_tables
            where owner = '{owner}'
            order by table_name
        """
    if node_type == "indexes_folder":
        return f"""
            select index_name as name
            from all_indexes
            where owner = '{owner}'
            order by index_name
        """
    if node_type == "views_folder":
        return f"""
            select view_name as name
            from all_views
            where owner = '{owner}'
            order by view_name
        """
    if node_type == "package_specs_folder":
        return f"""
            select object_name as name
            from all_objects
            where owner = '{owner}'
              and object_type = 'PACKAGE'
            order by object_name
        """
    if node_type == "package_bodies_folder":
        return f"""
            select object_name as name
            from all_objects
            where owner = '{owner}'
              and object_type = 'PACKAGE BODY'
            order by object_name
        """
    if node_type == "functions_folder":
        return f"""
            select object_name as name
            from all_objects
            where owner = '{owner}'
              and object_type = 'FUNCTION'
            order by object_name
        """
    if node_type == "procedures_folder":
        return f"""
            select object_name as name
            from all_objects
            where owner = '{owner}'
              and object_type = 'PROCEDURE'
            order by object_name
        """
    if node_type == "queues_folder":
        return f"""
            select name
            from all_queues
            where owner = '{owner}'
            order by name
        """
    if node_type == "triggers_folder":
        return f"""
            select trigger_name as name
            from all_triggers
            where owner = '{owner}'
            order by trigger_name
        """
    if node_type == "types_folder":
        return f"""
            select type_name as name
            from all_types
            where owner = '{owner}'
            order by type_name
        """
    if node_type == "type_bodies_folder":
        return f"""
            select object_name as name
            from all_objects
            where owner = '{owner}'
              and object_type = 'TYPE BODY'
            order by object_name
        """
    if node_type == "sequences_folder":
        return f"""
            select sequence_name as name
            from all_sequences
            where sequence_owner = '{owner}'
            order by sequence_name
        """
    if node_type == "materialized_views_folder":
        return f"""
            select mview_name as name
            from all_mviews
            where owner = '{owner}'
            order by mview_name
        """
    if node_type == "synonyms_folder":
        return f"""
            select synonym_name as name
            from all_synonyms
            where owner = '{owner}'
            order by synonym_name
        """
    if node_type == "db_links_folder":
        return f"""
            select db_link as name
            from all_db_links
            where owner = '{owner}'
            order by db_link
        """
    if node_type == "directories_folder":
        return """
            select directory_name as name
            from all_directories
            order by directory_name
        """
    if node_type == "java_objects_folder":
        return f"""
            select object_name as name
            from all_objects
            where owner = '{owner}'
              and object_type like 'JAVA%%'
            order by object_name
        """
    if node_type == "scheduler_jobs_folder":
        return f"""
            select job_name as name
            from all_scheduler_jobs
            where owner = '{owner}'
            order by job_name
        """
    raise ValueError(f"Unsupported metadata folder node type: {node_type}")
