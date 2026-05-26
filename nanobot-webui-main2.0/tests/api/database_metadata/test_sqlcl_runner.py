import subprocess

import pytest

from webui.api.database_metadata import sqlcl_runner


def test_build_sqlcl_command_wraps_batch_file_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sqlcl_runner, "_is_windows", lambda: True)
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")

    command = sqlcl_runner._build_sqlcl_command(r"C:\sqlcl\bin\sql.bat", "aidemo")

    assert command == [
        r"C:\Windows\System32\cmd.exe",
        "/d",
        "/c",
        r"C:\sqlcl\bin\sql.bat",
        "-S",
        "-name",
        "aidemo",
    ]


def test_build_sqlcl_command_keeps_exe_direct(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sqlcl_runner, "_is_windows", lambda: True)

    command = sqlcl_runner._build_sqlcl_command(r"C:\sqlcl\bin\sql.exe", "aidemo")

    assert command == [r"C:\sqlcl\bin\sql.exe", "-S", "-name", "aidemo"]


def test_resolve_sqlcl_executable_prefers_sql_exe_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sqlcl_runner, "_is_windows", lambda: True)
    monkeypatch.setattr(
        sqlcl_runner.shutil,
        "which",
        lambda name: r"E:\sqlcl\bin\sql.exe" if name == "sql.exe" else r"E:\sqlcl\bin\sql",
    )

    resolved = sqlcl_runner._resolve_sqlcl_executable()

    assert resolved == r"E:\sqlcl\bin\sql.exe"


def test_resolve_sqlcl_executable_uses_companion_exe_for_extensionless_launcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sqlcl_runner, "_is_windows", lambda: True)
    monkeypatch.setattr(
        sqlcl_runner.shutil,
        "which",
        lambda name: None if name == "sql.exe" else r"E:\sqlcl\bin\sql",
    )
    monkeypatch.setattr(sqlcl_runner.Path, "exists", lambda self: str(self) == r"E:\sqlcl\bin\sql.exe")

    resolved = sqlcl_runner._resolve_sqlcl_executable()

    assert resolved == r"E:\sqlcl\bin\sql.exe"


def test_run_sqlcl_raises_readable_error_when_process_start_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sqlcl_runner, "_resolve_sqlcl_executable", lambda: r"C:\sqlcl\bin\sql.exe")

    def fake_run(*args, **kwargs):
        raise OSError(193, "%1 is not a valid Win32 application")

    monkeypatch.setattr(sqlcl_runner.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="Failed to start SQLcl executable"):
        sqlcl_runner.run_sqlcl("aidemo", "select 1 from dual", timeout=10)


def test_run_sqlcl_uses_cmd_wrapper_for_batch_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sqlcl_runner, "_is_windows", lambda: True)
    monkeypatch.setattr(sqlcl_runner, "_resolve_sqlcl_executable", lambda: r"C:\sqlcl\bin\sql.bat")
    monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")

    captured: dict[str, object] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(sqlcl_runner.subprocess, "run", fake_run)

    output = sqlcl_runner.run_sqlcl("aidemo", "select 1 from dual", timeout=12)

    assert output == '{"ok":true}'
    assert captured["command"] == [
        r"C:\Windows\System32\cmd.exe",
        "/d",
        "/c",
        r"C:\sqlcl\bin\sql.bat",
        "-S",
        "-name",
        "aidemo",
    ]
    assert captured["kwargs"] == {
        "input": b"select 1 from dual",
        "capture_output": True,
        "timeout": 12,
        "check": False,
    }


def test_decode_process_output_handles_utf8_bytes_even_on_gbk_system() -> None:
    text = sqlcl_runner._decode_process_output('{"message":"¡Hola! 中文"}'.encode("utf-8"))

    assert text == '{"message":"¡Hola! 中文"}'


def test_run_sqlcl_raises_when_stdout_contains_ora_error_even_with_zero_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sqlcl_runner, "_resolve_sqlcl_executable", lambda: r"C:\sqlcl\bin\sql.exe")

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="ORA-00903: invalid table name\n[]",
            stderr="",
        )

    monkeypatch.setattr(sqlcl_runner.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="ORA-00903"):
        sqlcl_runner.run_sqlcl("aidemo", "select 1 from dual", timeout=10)
