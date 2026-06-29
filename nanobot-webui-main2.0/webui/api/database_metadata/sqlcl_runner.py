"""Helpers for calling SQLcl and parsing JSON-style output safely."""

from __future__ import annotations

import json
import locale
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from loguru import logger

from .metadata_sql import validate_sqlcl_connection_name


def _is_windows() -> bool:
    return os.name == "nt"


def _resolve_sqlcl_executable() -> str | None:
    if _is_windows():
        sql_executable = shutil.which("sql.exe")
        if sql_executable:
            return sql_executable

    sql_executable = shutil.which("sql")
    if not sql_executable:
        return None

    if _is_windows():
        executable_path = Path(sql_executable)
        companion_exe = executable_path.with_suffix(".exe")
        if executable_path.suffix == "" and companion_exe.exists():
            return str(companion_exe)

    return sql_executable


def _build_sqlcl_command(sql_executable: str, connection_name: str) -> list[str]:
    executable_path = Path(sql_executable)
    if _is_windows() and executable_path.suffix.lower() in {".bat", ".cmd"}:
        cmd_executable = os.environ.get("COMSPEC") or r"C:\Windows\System32\cmd.exe"
        return [cmd_executable, "/d", "/c", sql_executable, "-S", "-name", connection_name]
    return [sql_executable, "-S", "-name", connection_name]


def _contains_sqlcl_error(stdout: str, stderr: str) -> bool:
    combined = "\n".join(part for part in (stdout, stderr) if part)
    return re.search(r"\b(?:ORA|SP2)-\d+\b", combined) is not None


def _decode_process_output(raw: bytes | str | None) -> str:
    if not raw:
        return ""
    if isinstance(raw, str):
        return raw

    encodings: list[str] = ["utf-8", "utf-8-sig"]
    preferred = locale.getpreferredencoding(False)
    if preferred and preferred.lower() not in {encoding.lower() for encoding in encodings}:
        encodings.append(preferred)
    for encoding in ("gbk", "cp936"):
        if encoding.lower() not in {item.lower() for item in encodings}:
            encodings.append(encoding)

    for encoding in encodings:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def run_sqlcl(
    sqlcl_connection_name: str,
    sql_text: str,
    *,
    timeout: int = 60,
    operation: str = "sqlcl",
) -> str:
    """Run SQL against a SQLcl saved connection and return stdout."""
    connection_name = validate_sqlcl_connection_name(sqlcl_connection_name)
    sql_executable = _resolve_sqlcl_executable()
    if not sql_executable:
        raise RuntimeError("SQLcl executable 'sql' was not found in PATH")

    command = _build_sqlcl_command(sql_executable, connection_name)
    started_at = time.perf_counter()
    logger.info(
        "SQLcl start: operation={} connection={} timeout={}s executable={}",
        operation,
        connection_name,
        timeout,
        command[0],
    )
    try:
        completed = subprocess.run(
            command,
            input=sql_text.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.warning(
            "SQLcl timeout: operation={} connection={} elapsed_ms={:.1f} timeout={}s",
            operation,
            connection_name,
            elapsed_ms,
            timeout,
        )
        raise RuntimeError(f"SQLcl timed out after {timeout} seconds") from exc
    except OSError as exc:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.exception(
            "SQLcl start failed: operation={} connection={} elapsed_ms={:.1f}",
            operation,
            connection_name,
            elapsed_ms,
        )
        raise RuntimeError(f"Failed to start SQLcl executable '{sql_executable}': {exc}") from exc
    stdout = _decode_process_output(completed.stdout)
    stderr = _decode_process_output(completed.stderr)
    if completed.returncode != 0 or _contains_sqlcl_error(stdout, stderr):
        detail = stderr.strip() or stdout.strip() or f"SQLcl exited with code {completed.returncode}"
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.warning(
            "SQLcl failed: operation={} connection={} elapsed_ms={:.1f} exit_code={} stdout_chars={} stderr_chars={}",
            operation,
            connection_name,
            elapsed_ms,
            completed.returncode,
            len(stdout),
            len(stderr),
        )
        raise RuntimeError(detail)
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        "SQLcl success: operation={} connection={} elapsed_ms={:.1f} stdout_chars={} stderr_chars={}",
        operation,
        connection_name,
        elapsed_ms,
        len(stdout),
        len(stderr),
    )
    return stdout


def run_sqlcl_json(
    sqlcl_connection_name: str,
    sql_text: str,
    *,
    timeout: int = 60,
    operation: str = "sqlcl_json",
) -> Any:
    """Run SQLcl and parse the first JSON object/array in its output."""
    output = run_sqlcl(sqlcl_connection_name, sql_text, timeout=timeout, operation=operation)
    return extract_json_payload(output)


def extract_json_payload(text: str) -> Any:
    """Extract the first JSON object or array found in a noisy SQLcl output."""
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            payload, _end = decoder.raw_decode(text[index:])
            return payload
        except json.JSONDecodeError:
            continue
    cleaned = text.strip()
    if not cleaned:
        raise RuntimeError("SQLcl returned no output")
    raise RuntimeError(f"Failed to parse SQLcl JSON payload: {cleaned[:500]}")
