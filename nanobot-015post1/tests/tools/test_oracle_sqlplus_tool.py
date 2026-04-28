from __future__ import annotations

from typing import Any

import pytest

from nanobot.agent.tools.oracle_sqlplus import OracleSqlplusTool


class _FakeProcess:
    def __init__(self, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0):
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self.stdin_payload: bytes | None = None

    async def communicate(self, data: bytes | None = None):
        self.stdin_payload = data
        return self._stdout, self._stderr

    def kill(self) -> None:
        return None

    async def wait(self) -> int:
        return self.returncode


def test_description_requires_explicit_sqlplus_request():
    tool = OracleSqlplusTool()

    assert "explicitly asks for sqlplus" in tool.description
    assert "Do not treat it as the default Oracle data access tool" in tool.description


@pytest.mark.asyncio
async def test_execute_applies_default_ai_settings_and_silent(monkeypatch):
    fake_process = _FakeProcess(stdout=b"COL1\nVALUE\n")
    captured: dict[str, Any] = {}

    async def fake_exec(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return fake_process

    monkeypatch.setattr(
        "nanobot.agent.tools.oracle_sqlplus.shutil.which",
        lambda name: "sqlplus.exe" if name in {"sqlplus", "sqlplus.exe"} else None,
    )
    monkeypatch.setattr(
        "nanobot.agent.tools.oracle_sqlplus.asyncio.create_subprocess_exec",
        fake_exec,
    )

    tool = OracleSqlplusTool()
    result = await tool.execute(connect_string="scott/tiger@orcl", sql="select * from dual")

    assert result == "COL1\nVALUE"
    assert captured["args"] == ("sqlplus.exe", "-s", "scott/tiger@orcl")
    payload = fake_process.stdin_payload.decode("utf-8")
    assert "set pagesize 50000" in payload
    assert "set linesize 32767" in payload
    assert "set serveroutput on size unlimited" in payload
    assert "select * from dual" in payload
    assert payload.rstrip().endswith("exit")


@pytest.mark.asyncio
async def test_execute_runs_script_with_quoted_path_and_custom_set_commands(monkeypatch, tmp_path):
    fake_process = _FakeProcess(stdout=b"done\n")

    async def fake_exec(*args, **kwargs):
        return fake_process

    monkeypatch.setattr(
        "nanobot.agent.tools.oracle_sqlplus.shutil.which",
        lambda name: "sqlplus" if name in {"sqlplus", "sqlplus.exe"} else None,
    )
    monkeypatch.setattr(
        "nanobot.agent.tools.oracle_sqlplus.asyncio.create_subprocess_exec",
        fake_exec,
    )

    script_path = tmp_path / "my report.sql"
    script_path.write_text("select 1 from dual;\n", encoding="utf-8")

    tool = OracleSqlplusTool()
    result = await tool.execute(
        connect_string="scott/tiger@orcl",
        script_path=str(script_path),
        set_commands=["set colsep |", "set pagesize 100"],
    )

    assert result == "done"
    payload = fake_process.stdin_payload.decode("utf-8")
    assert '@"' in payload
    assert str(script_path) in payload
    assert "set colsep |" in payload
    assert "set pagesize 100" in payload
