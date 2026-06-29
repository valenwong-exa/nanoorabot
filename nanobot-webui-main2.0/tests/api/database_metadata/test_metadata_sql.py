from webui.api.database_metadata.metadata_sql import (
    build_accessible_object_names_query,
    build_all_users_sql,
    build_dynamic_views_query,
    build_folder_query,
    build_plsql_source_object_sql,
    build_source_object_quick_ddl_sql,
    build_table_quick_ddl_sql,
)


def test_build_all_users_sql_uses_clob_compatible_empty_fallback() -> None:
    sql = build_all_users_sql()

    assert "from all_users" in sql
    assert "to_clob('[]')" in sql


def test_build_folder_query_aliases_inline_view_for_tables() -> None:
    sql = build_folder_query("tables_folder", "VALEN")

    assert ") metadata_rows" in sql
    assert "to_clob('[]')" in sql


def test_build_folder_query_does_not_leave_blank_line_after_from_open_paren() -> None:
    sql = build_folder_query("tables_folder", "VALEN")

    assert "from (\n\n" not in sql
    assert "from (\n        select table_name as name" in sql


def test_build_folder_query_ends_statement_before_exit() -> None:
    sql = build_folder_query("tables_folder", "VALEN")

    assert "metadata_rows;" in sql
    assert sql.rstrip().endswith("exit")


def test_build_dynamic_views_query_checks_synonyms_and_access() -> None:
    sql = build_dynamic_views_query(["V$SESSION", "GV$SESSION"])

    assert "from all_synonyms" in sql
    assert "from all_objects" in sql
    assert "execute immediate l_sql into l_dummy" in sql
    assert "dbms_output.put_line(l_json)" in sql
    assert "'V$SESSION'" in sql
    assert "'GV$SESSION'" in sql


def test_build_accessible_object_names_query_supports_dba_dictionary_views() -> None:
    sql = build_accessible_object_names_query(["DBA_OBJECTS", "DBA_TABLES"])

    assert "from all_synonyms" in sql
    assert "from all_objects" in sql
    assert "'DBA_OBJECTS'" in sql
    assert "'DBA_TABLES'" in sql
    assert "select count(*) from ' || l_objects(i) || ' where rownum = 0" in sql


def test_build_source_object_quick_ddl_sql_keeps_get_ddl_wrapper_for_non_plsql_objects() -> None:
    sql = build_source_object_quick_ddl_sql("HR", "EMP_DETAILS_V", "VIEW", "View")

    assert "dbms_metadata.get_ddl(" in sql
    assert "'--------------------------------------------------------'" in sql
    assert "l_object_type    varchar2(128) := 'VIEW';" in sql
    assert "dbms_output.put_line('set define off');" in sql
    assert "dbms_output.put_line('prompt __NB_OBJECT_STATUS_BEGIN__');" in sql
    assert "dbms_output.put_line('prompt __NB_COMPILE_ERRORS_BEGIN__');" in sql
    assert "dbms_output.put_line('prompt __NB_SHOW_ERRORS_BEGIN__');" in sql
    assert "dbms_output.put_line('show errors view HR.EMP_DETAILS_V');" in sql
    assert 'dbms_output.put_line(" where owner = ' not in sql


def test_build_table_quick_ddl_sql_disables_substitution_variables() -> None:
    sql = build_table_quick_ddl_sql("HR", "EMP")

    assert "set define off" in sql
    assert "__NB_OBJECT_STATUS_BEGIN__" not in sql
    assert "show errors" not in sql


def test_build_plsql_source_object_sql_reads_all_source_in_line_order() -> None:
    sql = build_plsql_source_object_sql("HR", "ADD_JOB_HISTORY", "PROCEDURE")

    assert "from all_source" in sql
    assert "and type = upper(l_object_type)" in sql
    assert "order by line" in sql
    assert "when line = 1 then 'create or replace ' || text" in sql
    assert "dbms_output.put_line(rtrim(rec.text, chr(13) || chr(10)));" in sql
    assert "dbms_output.put_line('/');" in sql
    assert "dbms_metadata.get_ddl" not in sql
    assert "DDL for" not in sql
    assert "set define off" in sql
    assert "dbms_output.put_line('prompt __NB_OBJECT_STATUS_BEGIN__');" in sql
    assert "dbms_output.put_line('prompt __NB_COMPILE_ERRORS_BEGIN__');" in sql
    assert "dbms_output.put_line('prompt __NB_SHOW_ERRORS_BEGIN__');" in sql
    assert "dbms_output.put_line('show errors procedure HR.ADD_JOB_HISTORY');" in sql
    assert 'dbms_output.put_line(" where owner = ' not in sql


def test_build_plsql_source_object_sql_normalizes_package_body_object_type() -> None:
    sql = build_plsql_source_object_sql("HR", "EMP_MGMT", "PACKAGE_BODY")

    assert "l_object_type    varchar2(128) := 'PACKAGE BODY';" in sql
