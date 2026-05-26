from webui.api.database_metadata.metadata_sql import build_all_users_sql, build_folder_query


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
