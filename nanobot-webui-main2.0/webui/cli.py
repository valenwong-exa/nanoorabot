"""
Inject a ``webui`` sub-command into the nanobot Typer CLI.

After installing nanobot-webui the user can run:

    nanobot webui                     # start webui + gateway on default ports
    nanobot webui --port 9090         # custom WebUI port
    nanobot webui --workspace ~/work  # override workspace

The original ``nanobot`` entry point is shadowed by this module so that the
webui sub-command appears alongside the built-in ones (gateway, agent, onboard).
All existing commands continue to work unchanged.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer

# ── Grab the canonical nanobot Typer app ─────────────────────────────────────
from nanobot.cli.commands import app, channels_app

# ── Daemon / process-tracking helpers ────────────────────────────────────────

def _pid_file() -> Path:
    return Path.home() / ".nanobot" / "webui.pid"


def _port_file() -> Path:
    return Path.home() / ".nanobot" / "webui.port"


def _log_file() -> Path:
    return Path.home() / ".nanobot" / "webui.log"


def _is_webui_running() -> tuple[bool, int | None]:
    """Return (is_running, pid).  Cleans up a stale PID file if found."""
    pf = _pid_file()
    if not pf.exists():
        return False, None
    try:
        pid = int(pf.read_text().strip())
        os.kill(pid, 0)   # signal 0 = just probe existence
        return True, pid
    except (ValueError, ProcessLookupError, PermissionError):
        pf.unlink(missing_ok=True)
        return False, None


# ── Override `status` to include WebUI process info ──────────────────────────

# Remove the built-in status command so we can replace it.
app.registered_commands = [
    c for c in app.registered_commands
    if not (
        c.name == "status"
        or (c.name is None and getattr(c.callback, "__name__", "") == "status")
    )
]


@app.command("status")
def status() -> None:
    """Show nanobot status (including WebUI)."""
    from nanobot import __logo__
    from nanobot.config.loader import get_config_path, load_config
    from rich.console import Console

    _con = Console()
    config_path = get_config_path()
    config = load_config()
    workspace = config.workspace_path

    _con.print(f"{__logo__} nanobot Status\n")

    # ── WebUI service status ──────────────────────────────────────────────────
    running, pid = _is_webui_running()
    if running:
        port_str = (
            _port_file().read_text().strip() if _port_file().exists() else "?"
        )
        _con.print(
            f"WebUI: [green]\u2713 running[/green] "
            f"(PID {pid} \u2022 http://localhost:{port_str})"
        )
        _con.print(f"Log  : {_log_file()}")
    else:
        _con.print("WebUI: [dim]not running[/dim]")

    _con.print()

    # ── nanobot core status (replicated from nanobot.cli.commands.status) ─────
    _OK = "[green]\u2713[/green]"
    _NG = "[red]\u2717[/red]"
    _DIM = "[dim]not set[/dim]"
    _con.print(f"Config: {config_path} {_OK if config_path.exists() else _NG}")
    _con.print(f"Workspace: {workspace} {_OK if workspace.exists() else _NG}")

    if config_path.exists():
        from nanobot.providers.registry import PROVIDERS

        _con.print(f"Model: {config.agents.defaults.model}")

        for spec in PROVIDERS:
            p = getattr(config.providers, spec.name, None)
            if p is None:
                continue
            if spec.is_oauth:
                _con.print(f"{spec.label}: [green]\u2713 (OAuth)[/green]")
            elif spec.is_local:
                if p.api_base:
                    _con.print(f"{spec.label}: [green]\u2713 {p.api_base}[/green]")
                else:
                    _con.print(f"{spec.label}: {_DIM}")
            else:
                _con.print(f"{spec.label}: {_OK if p.api_key else _DIM}")


# ── `webui` sub-app ─────────────────────────────────────────────────────────────

webui_app = typer.Typer(
    name="webui",
    help="Manage the nanobot WebUI.",
    no_args_is_help=True,
)
app.add_typer(webui_app, name="webui")


@webui_app.callback()
def _webui_group(ctx: typer.Context) -> None:
    """Manage the nanobot WebUI."""
    pass


@webui_app.command("start")
def webui_start(
    port: int = typer.Option(18780, "--port", "-p", help="WebUI HTTP port (default: 18780)"),
    host: str = typer.Option("0.0.0.0", "--host", help="Bind address for WebUI"),
    workspace: Optional[str] = typer.Option(
        None, "--workspace", "-w", help="Override workspace directory"
    ),
    oracle_config: Optional[str] = typer.Option(
        None, "--oracle-config", help="Path to Oracle DB connection JSON file"
    ),
    tool_policy: Optional[str] = typer.Option(
        None, "--tool-policy", help="Path to dangerous tool policy JSON file"
    ),
    oracle_audit: bool = typer.Option(
        False, "--oracle-audit", help="Enable async Oracle persistence for the audit table"
    ),
    oracle_memory: bool = typer.Option(
        False, "--oracle-memory", help="Enable async Oracle persistence for the memory table"
    ),
    config_path: Optional[str] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    daemon: bool = typer.Option(
        False, "--daemon", "-d",
        help="Run in the background and return immediately. "
             "PID written to ~/.nanobot/webui.pid, logs to ~/.nanobot/webui.log.",
    ),
    log_level: str = typer.Option(
        "DEBUG", "--log-level", "-l",
        help="Log level: DEBUG, INFO, WARNING, ERROR (default: DEBUG)",
    ),
    webui_only: bool = typer.Option(
        False, "--webui-only",
        help="Start only the WebUI HTTP server and agent (for WebSocket chat). "
             "IM channels and heartbeat are NOT started — use this when nanobot "
             "is already running as a separate process (e.g. systemd service).",
    ),
) -> None:
    """Start the nanobot WebUI (foreground by default; use -d for background)."""
    if daemon:
        _start_daemon(
            port=port,
            host=host,
            workspace=workspace,
            oracle_config=oracle_config,
            tool_policy=tool_policy,
            oracle_audit=oracle_audit,
            oracle_memory=oracle_memory,
            config_path=config_path,
            log_level=log_level,
            webui_only=webui_only,
        )
        return

    # Foreground mode
    from webui.__main__ import _apply_patches, main as _run_all
    _apply_patches()

    if config_path:
        from nanobot.config.loader import set_config_path
        set_config_path(Path(config_path).expanduser().resolve())

    asyncio.run(_run_all(
        web_port=port,
        web_host=host,
        workspace=workspace,
        oracle_config=oracle_config,
        tool_policy=tool_policy,
        oracle_audit=oracle_audit,
        oracle_memory=oracle_memory,
        log_level=log_level,
        webui_only=webui_only,
    ))


@webui_app.command("logs")
def webui_logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output (like tail -f)"),
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show (default: 50)"),
) -> None:
    """View the WebUI log file."""
    log = _log_file()
    if not log.exists():
        typer.echo(f"Log file not found: {log}")
        raise typer.Exit(1)

    if follow:
        import subprocess
        try:
            subprocess.run(["tail", "-f", "-n", str(lines), str(log)])
        except KeyboardInterrupt:
            pass
    else:
        import subprocess
        subprocess.run(["tail", "-n", str(lines), str(log)])


@webui_app.command("status")
def webui_status() -> None:
    """Show WebUI service status."""
    running, pid = _is_webui_running()
    if running:
        port_str = _port_file().read_text().strip() if _port_file().exists() else "?"
        typer.echo(f"\u2713 running  PID={pid}  http://localhost:{port_str}")
        typer.echo(f"  Log: {_log_file()}")
    else:
        typer.echo("\u2717 not running")


@webui_app.command("stop")
def webui_stop() -> None:
    """Stop the background WebUI process."""
    running, pid = _is_webui_running()
    if not running:
        typer.echo("nanobot WebUI is not running.")
        raise typer.Exit(0)

    import signal as _signal
    import time
    try:
        os.kill(pid, _signal.SIGTERM)
        for _ in range(30):
            time.sleep(0.2)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
        else:
            try:
                os.kill(pid, _signal.SIGKILL)
            except ProcessLookupError:
                pass
    except ProcessLookupError:
        pass

    _pid_file().unlink(missing_ok=True)
    _port_file().unlink(missing_ok=True)
    typer.echo(f"\u2713 nanobot WebUI stopped (PID {pid})")


@webui_app.command("restart")
def webui_restart(
    port: int = typer.Option(18780, "--port", "-p", help="WebUI HTTP port (default: 18780)"),
    host: str = typer.Option("0.0.0.0", "--host", help="Bind address"),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w", help="Override workspace directory"),
    oracle_config: Optional[str] = typer.Option(None, "--oracle-config", help="Path to Oracle DB connection JSON file"),
    tool_policy: Optional[str] = typer.Option(None, "--tool-policy", help="Path to dangerous tool policy JSON file"),
    oracle_audit: bool = typer.Option(False, "--oracle-audit", help="Enable async Oracle persistence for the audit table"),
    oracle_memory: bool = typer.Option(False, "--oracle-memory", help="Enable async Oracle persistence for the memory table"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
    log_level: str = typer.Option("DEBUG", "--log-level", "-l", help="Log level"),
) -> None:
    """Restart the background WebUI process (stop then start)."""
    running, _ = _is_webui_running()
    if running:
        # Reuse the currently recorded port unless the caller specified a different one
        if port == 18780 and _port_file().exists():
            try:
                port = int(_port_file().read_text().strip())
            except ValueError:
                pass
        webui_stop()
        import time
        time.sleep(0.5)
    _start_daemon(
        port=port,
        host=host,
        workspace=workspace,
        oracle_config=oracle_config,
        tool_policy=tool_policy,
        oracle_audit=oracle_audit,
        oracle_memory=oracle_memory,
        config_path=config_path,
        log_level=log_level,
    )


@webui_app.command("voice")
def webui_voice(
    list_devices: bool = typer.Option(
        False,
        "--list-devices",
        help="List available microphone devices using the current Python environment.",
    ),
    sensevoice_dir: Optional[str] = typer.Option(
        None,
        "--sensevoice-dir",
        help="Path to the external SenseVoice-main workspace. Defaults to ../SenseVoice-main.",
    ),
    duration: float = typer.Option(
        30.0,
        "--duration",
        help="Maximum recording duration in seconds while holding Ctrl+Z.",
    ),
    samplerate: int = typer.Option(
        16000,
        "--samplerate",
        help="Recording sample rate passed to mic_test.py.",
    ),
    language: str = typer.Option(
        "zh",
        "--language",
        help="Recognition language passed to mic_test.py.",
    ),
    device: str = typer.Option(
        "cuda:0",
        "--device",
        help="Inference device passed to mic_test.py, such as cuda:0 or cpu.",
    ),
    input_device: Optional[int] = typer.Option(
        None,
        "--input-device",
        help="Optional microphone device index.",
    ),
    keep_audio: bool = typer.Option(
        False,
        "--keep-audio",
        help="Keep the recorded wav file for troubleshooting.",
    ),
) -> None:
    """Run the external SenseVoice microphone tool from the WebUI environment."""

    from webui.voice import (
        SenseVoiceMicOptions,
        SenseVoiceService,
        get_voice_runtime_status,
    )

    status_payload = get_voice_runtime_status(sensevoice_dir=sensevoice_dir)
    if not status_payload["ok"]:
        typer.echo(f"[voice] {status_payload['reason']}")
        typer.echo("[voice] 请先按需安装 voice 依赖，例如: pip install \"nanobot-webui[voice]\"")
        raise typer.Exit(1)

    service = SenseVoiceService(sensevoice_dir=sensevoice_dir)
    typer.echo(f"[voice] SenseVoice 目录: {service.paths.root_dir}")
    typer.echo(f"[voice] Python 环境: {service.python_executable}")

    if list_devices:
        typer.echo(service.list_devices_text(), nl=False)
        return

    exit_code = service.run_microphone_capture(
        SenseVoiceMicOptions(
            duration=duration,
            samplerate=samplerate,
            language=language,
            device=device,
            input_device=input_device,
            keep_audio=keep_audio,
        )
    )
    raise typer.Exit(exit_code)


# ── Override `channels login` with PR #2348 generic behavior ─────────────────
# The installed nanobot only supports WhatsApp login; replace with a version
# that accepts a channel name and calls channel.login().

channels_app.registered_commands = [
    c for c in channels_app.registered_commands
    if not (
        c.name == "login"
        or (c.name is None and getattr(c.callback, "__name__", "") == "channels_login")
    )
]


@channels_app.command("login")
def channels_login(
    channel_name: str = typer.Argument(..., help="Channel name (e.g. weixin, whatsapp)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-authentication even if already logged in"),
) -> None:
    """Authenticate with a channel via QR code or other interactive login."""
    from nanobot.channels.registry import discover_all
    from nanobot.config.loader import load_config
    from rich.console import Console as _Console

    con = _Console()

    # Apply patches first so webui channels (e.g. weixin) are registered
    from webui.__main__ import _apply_patches
    _apply_patches()

    config = load_config()
    channel_cfg = getattr(config.channels, channel_name, None) or {}

    all_channels = discover_all()
    if channel_name not in all_channels:
        available = ", ".join(all_channels.keys())
        con.print(f"[red]Unknown channel: {channel_name}[/red] Available: {available}")
        raise typer.Exit(1)

    # Use the class from the registry directly — avoids hardcoded nanobot.channels.* import
    channel_cls = all_channels[channel_name]
    channel = channel_cls(channel_cfg, bus=None)

    success = asyncio.run(channel.login(force=force))
    if not success:
        con.print(f"[red]Login failed for channel: {channel_name}[/red]")
        raise typer.Exit(1)
    con.print(f"[green]✓ {channel_name} login successful[/green]")


# ── Daemon launcher ─────────────────────────────────────────────────────────

def _start_daemon(
    port: int,
    host: str,
    workspace: Optional[str],
    oracle_config: Optional[str],
    tool_policy: Optional[str],
    oracle_audit: bool,
    oracle_memory: bool,
    config_path: Optional[str],
    log_level: str = "DEBUG",
    webui_only: bool = False,
) -> None:
    """Spawn a detached nanobot-webui process and record its PID."""
    import shutil
    import subprocess

    # Check for an already-running instance
    running, old_pid = _is_webui_running()
    if running:
        old_port = _port_file().read_text().strip() if _port_file().exists() else "?"
        typer.echo(
            f"nanobot WebUI is already running (PID {old_pid}, "
            f"http://localhost:{old_port})"
        )
        typer.echo("Stop it first with:  kill " + str(old_pid))
        raise typer.Exit(1)

    # Build the child command — invoke `nanobot webui start` (foreground, no -d)
    nanobot_exe = shutil.which("nanobot") or sys.argv[0]
    cmd: list[str] = [nanobot_exe, "webui", "start", "--port", str(port), "--host", host]
    if workspace:
        cmd += ["--workspace", workspace]
    if oracle_config:
        cmd += ["--oracle-config", oracle_config]
    if tool_policy:
        cmd += ["--tool-policy", tool_policy]
    if oracle_audit:
        cmd += ["--oracle-audit"]
    if oracle_memory:
        cmd += ["--oracle-memory"]
    if config_path:
        cmd += ["--config", config_path]
    if log_level and log_level.upper() != "DEBUG":
        cmd += ["--log-level", log_level]
    if webui_only:
        cmd += ["--webui-only"]
    # Note: -d/--daemon is intentionally omitted so the child runs in the foreground

    log = _log_file()
    log.parent.mkdir(parents=True, exist_ok=True)

    with open(log, "a") as lf:
        proc = subprocess.Popen(
            cmd,
            stdout=lf,
            stderr=lf,
            stdin=subprocess.DEVNULL,
            start_new_session=True,   # detach from terminal / SIGHUP
        )

    _pid_file().write_text(str(proc.pid))
    _port_file().write_text(str(port))

    typer.echo(f"\u2713 nanobot WebUI started in background (PID {proc.pid})")
    typer.echo(f"  URL : http://localhost:{port}")
    typer.echo(f"  Log : {log}")
    typer.echo(f"  Stop: kill {proc.pid}")


# ── Entry points ─────────────────────────────────────────────────────────────

def run_nanobot() -> None:
    """Entry point for the ``nanobot`` command (with webui subcommand added)."""
    app()


def run_webui() -> None:
    """Entry point for the standalone ``nanobot-webui`` command."""
    parser = _make_standalone_parser()
    args = parser.parse_args()
    asyncio.run(
        _run_all_from_args(args)
    )


def _make_standalone_parser():
    import argparse
    p = argparse.ArgumentParser(
        prog="nanobot-webui",
        description="nanobot WebUI — start WebUI + gateway in one process",
    )
    p.add_argument("--port", type=int, default=18780, help="WebUI port (default: 18780)")
    p.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    p.add_argument("--workspace", default=None, help="Override workspace directory")
    p.add_argument("--oracle-config", default=None, dest="oracle_config",
                   help="Path to Oracle DB connection JSON file")
    p.add_argument("--tool-policy", default=None, dest="tool_policy",
                   help="Path to dangerous tool policy JSON file")
    p.add_argument("--oracle-audit", action="store_true", default=False, dest="oracle_audit",
                   help="Enable async Oracle persistence for the audit table")
    p.add_argument("--oracle-memory", action="store_true", default=False, dest="oracle_memory",
                   help="Enable async Oracle persistence for the memory table")
    p.add_argument("--config", default=None, dest="config_path",
                   help="Path to config file")
    p.add_argument("--log-level", default="DEBUG", dest="log_level",
                   metavar="LEVEL",
                   help="Log level: DEBUG, INFO, WARNING, ERROR (default: DEBUG)")
    return p


async def _run_all_from_args(args) -> None:
    from webui.__main__ import _apply_patches, main as _run_all
    _apply_patches()

    if args.config_path:
        from nanobot.config.loader import set_config_path
        from pathlib import Path
        set_config_path(Path(args.config_path).expanduser().resolve())

    await _run_all(
        web_port=args.port,
        web_host=args.host,
        workspace=args.workspace,
        oracle_config=getattr(args, "oracle_config", None),
        tool_policy=getattr(args, "tool_policy", None),
        oracle_audit=getattr(args, "oracle_audit", False),
        oracle_memory=getattr(args, "oracle_memory", False),
        log_level=getattr(args, "log_level", "DEBUG"),
    )
