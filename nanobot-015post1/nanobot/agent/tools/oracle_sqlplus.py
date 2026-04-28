"""Oracle SQL*Plus tool."""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool, tool_parameters
from nanobot.agent.tools.schema import ArraySchema, BooleanSchema, IntegerSchema, StringSchema, tool_parameters_schema

_DEFAULT_SQLPLUS_SET_COMMANDS = [
    "whenever sqlerror exit sql.sqlcode",
    "set echo off",
    "set feedback on",
    "set heading on",
    "set pagesize 50000",
    "set linesize 32767",
    "set long 200000",
    "set longchunksize 200000",
    "set trimspool on",
    "set tab off",
    "set verify off",
    "set serveroutput on size unlimited",
    "set sqlblanklines on",
]


@tool_parameters(
    tool_parameters_schema(
        connectString=StringSchema(
            "Oracle connect string, for example scott/tiger@host:1521/service_name"
        ),
        sql=StringSchema(
            "Optional SQL or PL/SQL text to execute. Use this for ad hoc queries in SQL*Plus.",
            nullable=True,
        ),
        scriptPath=StringSchema(
            "Optional SQL script file path to run with @script. Useful only when the user explicitly wants SQL*Plus.",
            nullable=True,
        ),
        silent=BooleanSchema(
            description="Run sqlplus in silent mode (-s). Default true for cleaner AI-readable output.",
            default=True,
        ),
        setCommands=ArraySchema(
            StringSchema("One SQL*Plus SET or control command"),
            description="Optional extra SQL*Plus formatting commands. Default AI-friendly SET commands are applied unless disabled.",
        ),
        useDefaultAiSettings=BooleanSchema(
            description="Apply built-in AI-friendly SQL*Plus SET commands before the query or script. Default true.",
            default=True,
        ),
        extraArgs=ArraySchema(
            StringSchema("Additional sqlplus argument"),
            description="Optional additional sqlplus command line arguments.",
        ),
        timeout=IntegerSchema(
            120,
            description="Optional timeout in seconds",
            minimum=1,
        ),
        required=["connectString"],
    )
)
class OracleSqlplusTool(Tool):
    """Execute Oracle SQL*Plus commands and scripts."""

    def __init__(self, timeout: int = 120, max_output_chars: int = 20000):
        self.timeout = timeout
        self.max_output_chars = max_output_chars

    @property
    def name(self) -> str:
        return "oracle_sqlplus"

    @property
    def description(self) -> str:
        return (
            "Specialized Oracle SQL*Plus tool. Use this only when the user explicitly asks for sqlplus or SQL*Plus behavior. "
            "Do not treat it as the default Oracle data access tool. "
            "Runs SQL text or @script through sqlplus from the existing system PATH and applies AI-friendly SET formatting by default."
        )

    async def execute(
        self,
        connect_string: str | None = None,
        sql: str | None = None,
        script_path: str | None = None,
        silent: bool = True,
        set_commands: list[str] | None = None,
        use_default_ai_settings: bool = True,
        extra_args: list[str] | None = None,
        timeout: int | None = None,
        **kwargs: Any,
    ) -> str:
        connect_string = connect_string or kwargs.get("connectString")
        script_path = script_path or kwargs.get("scriptPath")
        if set_commands is None:
            set_commands = kwargs.get("setCommands")
        if extra_args is None:
            extra_args = kwargs.get("extraArgs")
        use_default_ai_settings = kwargs.get("useDefaultAiSettings", use_default_ai_settings)
        silent = kwargs.get("silent", silent)

        if connect_string is None:
            return "Error: Missing required parameter 'connectString'."
        if sql and script_path:
            return "Error: Provide either 'sql' or 'scriptPath', not both."
        if not sql and not script_path:
            return "Error: Provide 'sql' or 'scriptPath'."

        executable = self._resolve_sqlplus_path()
        if not executable:
            return "Error: sqlplus was not found in PATH."

        args: list[str] = [executable]
        if silent:
            args.append("-s")
        if extra_args:
            args.extend(str(a) for a in extra_args if str(a).strip())
        args.append(connect_string)

        stdin_data = self._build_stdin_data(
            sql=sql,
            script_path=script_path,
            set_commands=set_commands,
            use_default_ai_settings=use_default_ai_settings,
        )
        run_timeout = timeout or self.timeout

        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy(),
            )
        except FileNotFoundError:
            return "Error: sqlplus executable not found in PATH."
        except Exception as e:
            return f"Error: Failed to start sqlplus: {e}"

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(stdin_data), timeout=run_timeout)
        except asyncio.TimeoutError:
            process.kill()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
            return f"Error: sqlplus timed out after {run_timeout} seconds"

        out_text = stdout.decode("utf-8", errors="replace").replace("\r\n", "\n").strip()
        err_text = stderr.decode("utf-8", errors="replace").replace("\r\n", "\n").strip()

        parts: list[str] = []
        if out_text:
            parts.append(out_text)
        if err_text:
            parts.append(f"STDERR:\n{err_text}")
        if process.returncode not in (0, None):
            parts.append(f"Exit code: {process.returncode}")

        result = "\n\n".join(parts) if parts else "(no output)"
        if len(result) > self.max_output_chars:
            extra = len(result) - self.max_output_chars
            result = result[: self.max_output_chars] + f"\n... (truncated, {extra} more chars)"
        return result

    @staticmethod
    def _resolve_sqlplus_path() -> str | None:
        return shutil.which("sqlplus") or shutil.which("sqlplus.exe")

    @staticmethod
    def _format_script_ref(script_path: str) -> str:
        expanded = str(Path(script_path).expanduser())
        return f'@"{expanded}"'

    def _build_stdin_data(
        self,
        *,
        sql: str | None,
        script_path: str | None,
        set_commands: list[str] | None,
        use_default_ai_settings: bool,
    ) -> bytes:
        commands: list[str] = []
        if use_default_ai_settings:
            commands.extend(_DEFAULT_SQLPLUS_SET_COMMANDS)
        if set_commands:
            commands.extend(str(cmd).strip() for cmd in set_commands if str(cmd).strip())

        body = sql.rstrip() if sql else self._format_script_ref(script_path or "")
        script = "\n".join([*commands, body, "exit"])
        return (script.rstrip() + "\n").encode("utf-8")
