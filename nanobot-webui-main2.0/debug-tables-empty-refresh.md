[CLOSED] tables-empty-refresh

## Symptom

- `Schemas -> <schema> -> Tables` expands to `(empty)`.
- Right-click `Refresh` on `Tables` still leaves the node empty.
- Expected: actual table children should be returned and rendered.

## Hypotheses

1. The SQLcl `tables_folder` query is returning no rows for the resolved schema.
2. SQLcl is returning rows, but the JSON extraction/parse layer drops them.
3. The resolved `schema_name` sent into the `tables_folder` query is wrong.
4. The backend builds table children correctly, but YAML cache update or frontend node replacement overwrites them with an empty node.

## Plan

1. Instrument the backend query path for `tables_folder` only.
2. Reproduce `Tables` expand/refresh and collect runtime evidence.
3. Confirm or reject each hypothesis from logs.
4. Apply the minimal fix only after evidence is clear.

## Evidence

- Hypothesis 1 confirmed: SQLcl raw output reported `ORA-00903: 表名无效` during the `tables_folder` query.
- Hypothesis 2 partially confirmed: the parser extracted `[]` from SQL text/output even though the query had failed, masking the SQL error as an empty result.
- Hypothesis 3 rejected: `schema_name` resolved to `VALEN`, which matches the user expectation.
- Hypothesis 4 rejected: refresh wrote exactly one child, and that child was `(empty)` because the upstream names list was empty.

## Root Cause

1. `build_folder_query()` generated an inline view without an alias, which Oracle rejected with `ORA-00903`.
2. `run_sqlcl()` trusted exit code `0`, while SQLcl emitted the Oracle error on stdout; `extract_json_payload()` then misread the literal `[]` fallback text as a valid empty JSON array.
3. SQLcl treated the blank line after `from (` as a statement break, so the outer aggregate failed while the inner `select table_name ...` ran separately.
4. After the statement-shape fix, Oracle exposed a type mismatch: `coalesce(..., '[]')` mixed `CLOB` output with a `CHAR` fallback.

## Fix Plan

1. Alias the inline view in `build_folder_query()`.
2. Treat `ORA-` / `SP2-` in SQLcl output as execution failure even when exit code is `0`.
3. Remove the blank line inside `from (...)` so SQLcl submits one intact statement.
4. Change the empty fallback from `'[]'` to `to_clob('[]')`.

## Verification

- Local direct SQLcl execution now returns 12 JSON rows for `VALEN` tables:
  - `ADB_CHAT_PROMPTS`
  - `ASK_ORACLE_AUTO_VISUAL_LOG`
  - `BACKLOG`
  - `CONVERSATION_TIME`
  - `DBTOOLS$MCP_LOG`
  - `LC_DEMO_CHUNKS`
  - `LC_DEMO_CHUNKS_BGE`
  - `LC_DEMO_DOCUMENTS`
  - `LC_DEMO_DOCUMENTS_BGE`
  - `PIN_CONVERSATIONS`
  - `PMTABLE`
  - `TIMECARD`
- Focused metadata SQL tests pass after the fix.

## Cleanup

- Removed temporary runtime instrumentation from `sqlcl_runner.py` and `metadata_service.py`.
- Debug session confirmed fixed by user: `Tables` now shows 12 tables and refresh works.
