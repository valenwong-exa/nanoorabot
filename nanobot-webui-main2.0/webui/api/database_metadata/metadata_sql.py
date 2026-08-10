"""SQL builders and tree metadata constants for Oracle metadata explorer."""

from __future__ import annotations

import re
import textwrap
from datetime import datetime, timezone

CONNECTION_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
SCHEMA_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,127}$")
OBJECT_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,127}$")

ICON_MAP: dict[str, str] = {
    "root": "oracle_connection.png",
    "connection": "connected_database.png",
    "connection_info": "connected_database.png",
    "connected_schema": "schema.png",
    "dbops_root": "scheduler_job.png",
    "selectai_root": "schema.png",
    "selectai_profile": "users.png",
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
    "dynamic_views_folder": "view.png",
    "dynamic_view": "view.png",
    "dictionary_table_folder": "table.png",
    "dictionary_table_item": "table.png",
    "useful_diagnoses_folder": "view.png",
    "useful_diagnosis": "view.png",
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

DBOPS_FOLDER_SPECS: list[dict[str, str]] = [
    {"key": "dynamic_views", "label": "DynamicViews", "folder_type": "dynamic_views_folder", "item_type": "dynamic_view"},
    {"key": "dictionary_table", "label": "DictionaryTables", "folder_type": "dictionary_table_folder", "item_type": "dictionary_table_item"},
    {"key": "useful_diagnoses", "label": "UsefulDiagnoses", "folder_type": "useful_diagnoses_folder", "item_type": "useful_diagnosis"},
]

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
    "dbops_root",
    "selectai_root",
    "schemas_root",
    "schema",
    "users_root",
    "user",
    *[spec["folder_type"] for spec in DBOPS_FOLDER_SPECS],
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


def validate_object_name(name: str) -> str:
    object_name = name.strip().upper()
    if not object_name or OBJECT_NAME_PATTERN.fullmatch(object_name) is None:
        raise ValueError("Invalid Oracle object name")
    return object_name


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
            "set long 10000000",
            "set longchunksize 10000000",
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


def build_connection_probe_sql() -> str:
    return wrap_sql(
        """
        select json_serialize(
                 json_object(
                   'status' value 'ok'
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


def build_selectai_profiles_sql() -> str:
    return (
        "\n".join(
            [
                "set heading off",
                "set feedback off",
                "set pagesize 0",
                "set linesize 32767",
                "set trimspool on",
                "set serveroutput on size unlimited",
                "set long 10000000",
                "set longchunksize 10000000",
                "declare",
                "    l_json clob := '[]';",
                "begin",
                "    begin",
                "        execute immediate q'~",
                "            select coalesce(",
                "                     json_serialize(",
                "                       json_arrayagg(",
                "                         json_object('name' value profile_name)",
                "                         order by profile_name",
                "                         returning clob",
                "                       ) returning clob",
                "                     ),",
                "                     to_clob('[]')",
                "                   )",
                "            from user_cloud_ai_profiles",
                "        ~' into l_json;",
                "    exception",
                "        when others then",
                "            if sqlcode = -942 then",
                "                l_json := '[]';",
                "            else",
                "                raise;",
                "            end if;",
                "    end;",
                "    dbms_output.put_line(l_json);",
                "end;",
                "/",
                "exit",
                "",
            ]
        )
    )


def folder_specs_for_node(node_type: str) -> list[dict[str, str]]:
    if node_type == "dbops_root":
        return DBOPS_FOLDER_SPECS
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


def build_accessible_object_names_query(object_names: list[str]) -> str:
    validated_names = [validate_object_name(name) for name in object_names]
    literals = ",\n".join(f"        '{escape_sql_literal(name)}'" for name in validated_names)
    return (
        "\n".join(
            [
                "set heading off",
                "set feedback off",
                "set pagesize 0",
                "set linesize 32767",
                "set trimspool on",
                "set serveroutput on size unlimited",
                "set long 10000000",
                "set longchunksize 10000000",
                "declare",
                "    type t_object_list is table of varchar2(128);",
                "    l_objects t_object_list := t_object_list(",
                literals,
                "    );",
                "    l_exists_count number;",
                "    l_dummy number;",
                "    l_sql varchar2(4000);",
                "    l_json clob := '[';",
                "    l_first boolean := true;",
                "begin",
                "    for i in 1 .. l_objects.count loop",
                "        select count(*)",
                "        into l_exists_count",
                "        from all_synonyms",
                "        where synonym_name = upper(l_objects(i))",
                "          and owner in ('PUBLIC', user);",
                "",
                "        if l_exists_count = 0 then",
                "            select count(*)",
                "            into l_exists_count",
                "            from all_objects",
                "            where object_name = upper(l_objects(i))",
                "              and object_type in ('VIEW', 'SYNONYM');",
                "        end if;",
                "",
                "        if l_exists_count > 0 then",
                "            begin",
                "                l_sql := 'select count(*) from ' || l_objects(i) || ' where rownum = 0';",
                "                execute immediate l_sql into l_dummy;",
                "                if not l_first then",
                "                    l_json := l_json || ',';",
                "                end if;",
                "                l_json := l_json || '{\"name\":\"' || l_objects(i) || '\"}';",
                "                l_first := false;",
                "            exception",
                "                when others then",
                "                    null;",
                "            end;",
                "        end if;",
                "    end loop;",
                "    l_json := l_json || ']';",
                "    dbms_output.put_line(l_json);",
                "end;",
                "/",
                "exit",
                "",
            ]
        )
    )


def build_dynamic_views_query(view_names: list[str]) -> str:
    return build_accessible_object_names_query(view_names)


def build_table_quick_ddl_sql(schema_name: str, table_name: str) -> str:
    owner = escape_sql_literal(validate_schema_name(schema_name))
    object_name = escape_sql_literal(validate_object_name(table_name))
    return (
        "\n".join(
            [
                "set heading off",
                "set feedback off",
                "set pagesize 0",
                "set linesize 32767",
                "set trimspool on",
                "set serveroutput on size unlimited",
                "set long 2000000",
                "set longchunksize 2000000",
                "set define off",
                "declare",
                "    l_ddl clob;",
                "    procedure print_clob(p_clob clob) is",
                "        l_offset integer := 1;",
                "        l_chunk varchar2(32767);",
                "    begin",
                "        if p_clob is null then",
                "            return;",
                "        end if;",
                "        while l_offset <= dbms_lob.getlength(p_clob) loop",
                "            l_chunk := dbms_lob.substr(p_clob, 32767, l_offset);",
                "            dbms_output.put_line(l_chunk);",
                "            l_offset := l_offset + 32767;",
                "        end loop;",
                "    end;",
                "",
                "    procedure print_dependent_ddl(p_object_type varchar2) is",
                "    begin",
                f"        l_ddl := dbms_metadata.get_dependent_ddl(p_object_type, '{object_name}', '{owner}');",
                "        if l_ddl is not null and dbms_lob.getlength(l_ddl) > 0 then",
                "            dbms_output.put_line('');",
                "            print_clob(l_ddl);",
                "        end if;",
                "    exception",
                "        when others then",
                "            if sqlcode != -31608 then",
                "                raise;",
                "            end if;",
                "    end;",
                "",
                "    function normalize_comment_text(p_text varchar2) return varchar2 is",
                "    begin",
                "        if p_text is null then",
                "            return null;",
                "        end if;",
                "        return replace(replace(replace(p_text, chr(13), ' '), chr(10), ' '), chr(9), ' ');",
                "    end;",
                "",
                "    procedure print_comment_ddls is",
                "        l_comment varchar2(4000);",
                "    begin",
                "        begin",
                "            select comments",
                "              into l_comment",
                "              from all_tab_comments",
                f"             where owner = '{owner}'",
                f"               and table_name = '{object_name}';",
                "            l_comment := normalize_comment_text(l_comment);",
                "            if l_comment is not null then",
                f"""                dbms_output.put_line('COMMENT ON TABLE "{owner}"."{object_name}" IS ''' || replace(l_comment, '''', '''''') || ''';');""",
                "            end if;",
                "        exception",
                "            when no_data_found then",
                "                null;",
                "        end;",
                "",
                "        for col_rec in (",
                "            select c.column_name, c.comments",
                "              from all_col_comments c",
                "              join all_tab_columns tc",
                "                on tc.owner = c.owner",
                "               and tc.table_name = c.table_name",
                "               and tc.column_name = c.column_name",
                f"             where c.owner = '{owner}'",
                f"               and c.table_name = '{object_name}'",
                "               and c.comments is not null",
                "             order by tc.column_id",
                "        ) loop",
                "            l_comment := normalize_comment_text(col_rec.comments);",
                "            if l_comment is not null then",
                f"""                dbms_output.put_line('COMMENT ON COLUMN "{owner}"."{object_name}"."' || col_rec.column_name || '" IS ''' || replace(l_comment, '''', '''''') || ''';');""",
                "            end if;",
                "        end loop;",
                "    end;",
                "begin",
                "    dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'SEGMENT_ATTRIBUTES', false);",
                "    dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'STORAGE', false);",
                "    dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'TABLESPACE', false);",
                "    dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'SQLTERMINATOR', true);",
                f"    l_ddl := dbms_metadata.get_ddl('TABLE', '{object_name}', '{owner}');",
                "    print_clob(l_ddl);",
                "    print_dependent_ddl('INDEX');",
                "    print_dependent_ddl('CONSTRAINT');",
                "    print_dependent_ddl('REF_CONSTRAINT');",
                "    print_comment_ddls;",
                "end;",
                "/",
                "exit",
                "",
            ]
        )
    )


def _compile_validation_output_lines(owner: str, object_name: str, object_type: str) -> list[str]:
    normalized_type = object_type.upper()
    if normalized_type not in {"VIEW", "PROCEDURE", "FUNCTION", "PACKAGE", "PACKAGE BODY", "TRIGGER"}:
        return []

    show_errors_target = normalized_type.lower()
    return [
        "",
        "prompt",
        "prompt __NB_OBJECT_STATUS_BEGIN__",
        "select status",
        "  from all_objects",
        f" where owner = '{owner}'",
        f"   and object_name = '{object_name}'",
        f"   and object_type = '{normalized_type}';",
        "prompt __NB_OBJECT_STATUS_END__",
        "prompt",
        "prompt __NB_COMPILE_ERRORS_BEGIN__",
        "select line, position, text",
        "  from all_errors",
        f" where owner = '{owner}'",
        f"   and name = '{object_name}'",
        f"   and type = '{normalized_type}'",
        " order by sequence;",
        "prompt __NB_COMPILE_ERRORS_END__",
        "prompt",
        "prompt __NB_SHOW_ERRORS_BEGIN__",
        f"show errors {show_errors_target} {owner}.{object_name}",
        "prompt __NB_SHOW_ERRORS_END__",
    ]


def _dbms_output_put_line_stmt(text: str) -> str:
    return f"    dbms_output.put_line('{escape_sql_literal(text)}');"


def build_source_object_quick_ddl_sql(schema_name: str, object_name: str, object_type: str, object_label: str) -> str:
    owner = escape_sql_literal(validate_schema_name(schema_name))
    validated_name = escape_sql_literal(validate_object_name(object_name))
    ddl_object_type = escape_sql_literal(object_type.upper())
    ddl_object_label = escape_sql_literal(object_label)
    validation_lines = _compile_validation_output_lines(owner, validated_name, ddl_object_type)
    validation_output = [_dbms_output_put_line_stmt(line) for line in validation_lines]
    return (
        "\n".join(
            [
                "set serveroutput on size unlimited",
                "set linesize 32767",
                "set pagesize 0",
                "set feedback off",
                "set verify off",
                "set trimspool on",
                "set long 2000000",
                "set longchunksize 2000000",
                "declare",
                f"    l_owner          varchar2(128) := '{owner}';",
                f"    l_object_name    varchar2(128) := '{validated_name}';",
                f"    l_object_type    varchar2(128) := '{ddl_object_type}';",
                f"    l_object_label   varchar2(128) := '{ddl_object_label}';",
                "    l_ddl            clob;",
                "",
                "    procedure print_clob(p_clob in clob) is",
                "        l_offset integer := 1;",
                "        l_length integer;",
                "        l_amount integer;",
                "        l_text   varchar2(32767);",
                "    begin",
                "        if p_clob is null then",
                "            return;",
                "        end if;",
                "",
                "        l_length := dbms_lob.getlength(p_clob);",
                "",
                "        while l_offset <= l_length loop",
                "            l_amount := least(30000, l_length - l_offset + 1);",
                "            l_text := dbms_lob.substr(p_clob, l_amount, l_offset);",
                "            dbms_output.put_line(l_text);",
                "            l_offset := l_offset + length(l_text);",
                "        end loop;",
                "    end;",
                "begin",
                "    l_owner := upper(l_owner);",
                "    l_object_name := upper(l_object_name);",
                "    dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'DEFAULT');",
                "    dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'PRETTY', true);",
                "    dbms_metadata.set_transform_param(dbms_metadata.session_transform, 'SQLTERMINATOR', false);",
                "    dbms_output.put_line('--------------------------------------------------------');",
                "    dbms_output.put_line('--  DDL for ' || l_object_label || ' ' || l_object_name);",
                "    dbms_output.put_line('--------------------------------------------------------');",
                "    dbms_output.put_line('set define off');",
                "    dbms_output.new_line;",
                "    l_ddl := dbms_metadata.get_ddl(",
                "        object_type => l_object_type,",
                "        name        => l_object_name,",
                "        schema      => l_owner",
                "    );",
                "    l_ddl := regexp_replace(l_ddl, '[[:space:]]*/[[:space:]]*$', '');",
                "    print_clob(l_ddl);",
                "    dbms_output.new_line;",
                "    dbms_output.put_line('/');",
                *validation_output,
                "end;",
                "/",
                "exit",
                "",
            ]
        )
    )


def build_plsql_source_object_sql(schema_name: str, object_name: str, object_type: str) -> str:
    owner = escape_sql_literal(validate_schema_name(schema_name))
    validated_name = escape_sql_literal(validate_object_name(object_name))
    source_object_type = escape_sql_literal(object_type.upper().replace("_", " "))
    validation_lines = _compile_validation_output_lines(owner, validated_name, source_object_type)
    validation_output = [_dbms_output_put_line_stmt(line) for line in validation_lines]
    return (
        "\n".join(
            [
                "set serveroutput on size unlimited",
                "set linesize 32767",
                "set pagesize 0",
                "set feedback off",
                "set verify off",
                "set trimspool on",
                "set define off",
                "declare",
                f"    l_owner          varchar2(128) := '{owner}';",
                f"    l_object_name    varchar2(128) := '{validated_name}';",
                f"    l_object_type    varchar2(128) := '{source_object_type}';",
                "    l_found          boolean := false;",
                "begin",
                "    for rec in (",
                "        select case",
                "                   when line = 1 then 'create or replace ' || text",
                "                   else text",
                "               end as text",
                "          from all_source",
                "         where owner = upper(l_owner)",
                "           and name = upper(l_object_name)",
                "           and type = upper(l_object_type)",
                "         order by line",
                "    ) loop",
                "        l_found := true;",
                "        dbms_output.put_line(rtrim(rec.text, chr(13) || chr(10)));",
                "    end loop;",
                "",
                "    if not l_found then",
                "        raise_application_error(",
                "            -20000,",
                "            'No ALL_SOURCE rows found for ' || l_object_type || ' ' || l_owner || '.' || l_object_name",
                "        );",
                "    end if;",
                "",
                "    dbms_output.put_line('/');",
                *validation_output,
                "end;",
                "/",
                "exit",
                "",
            ]
        )
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
    if node_type == "dynamic_views_folder":
        raise ValueError("dynamic_views_folder must be loaded via build_dynamic_views_query")
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
