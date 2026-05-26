#!/usr/bin/env sh

if [ -z "${1:-}" ]; then
  echo "Usage:"
  echo "  $(basename "$0") connection_name"
  echo
  echo "Example:"
  echo "  $(basename "$0") aidemo"
  exit 1
fi

CONN_NAME="$1"
SQL_FILE="${TMPDIR:-/tmp}/sqlcl_sysdate_$$.sql"

trap 'rm -f "$SQL_FILE"' EXIT INT TERM

cat >"$SQL_FILE" <<'EOF'
set heading off
set feedback off
set pagesize 0
set linesize 200
set sqlformat default
select to_char(sysdate,'YYYY-MM-DD HH24:MI:SS') from dual;
exit
EOF

sql -S -name "$CONN_NAME" @"$SQL_FILE"
