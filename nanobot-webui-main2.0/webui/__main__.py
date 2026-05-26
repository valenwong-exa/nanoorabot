"""Entry point: ``python -m webui``

Starts nanobot gateway + FastAPI WebUI in a single asyncio process.
Zero modifications to any nanobot source files.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

from webui.patches import apply_all as _apply_all_patches

_patches_applied = False


def _apply_patches() -> None:
    """Apply all patches (idempotent — safe to call multiple times)."""
    global _patches_applied
    if _patches_applied:
        return
    _patches_applied = True
    _apply_all_patches()


_apply_patches()


def _normalize_agent_response_content(response: object) -> str | None:
    """Extract a serializable text response from AgentLoop results."""
    if response is None:
        return None

    content = getattr(response, "content", response)
    if content is None:
        return None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item) for item in content if item is not None)
    return str(content)


def _is_default_workspace(workspace: Path | None) -> bool:
    """Return whether a workspace resolves to nanobot's default workspace path."""
    current = workspace if workspace is not None else Path.home() / ".nanobot" / "workspace"
    default = Path.home() / ".nanobot" / "workspace"
    return current.resolve(strict=False) == default.resolve(strict=False)


async def main(
    web_port: int = 18780,
    web_host: str = "0.0.0.0",
    workspace: str | None = None,
    oracle_config: str | None = None,
    log_level: str = "DEBUG",
    webui_only: bool = False,
) -> None:
    import sys as _sys
    from loguru import logger

    logger.remove()
    logger.add(_sys.stderr, level=log_level.upper())

    from nanobot.agent.loop import AgentLoop
    from nanobot.bus.queue import MessageBus
    from nanobot.bus.events import OutboundMessage
    from nanobot.config.loader import load_config
    from nanobot.config.paths import get_cron_dir
    from nanobot.cron.service import CronService
    from nanobot.cron.types import CronJob
    from nanobot.heartbeat.service import HeartbeatService
    from nanobot.session.manager import SessionManager
    from nanobot.utils.helpers import sync_workspace_templates

    from webui.api.channel_ext import ExtendedChannelManager
    from webui.api.gateway import ServiceContainer, start_api_server
    from webui.oracle_config import OracleConfigService
    from webui.patches.provider import make_provider_patched
    from webui.utils.channel_compat import (
        is_webui_session_key,
        is_webui_transport_channel,
        normalize_transport_channel,
    )

    from nanobot.config.loader import get_config_path, save_config

    config = load_config()

    # Auto-initialize config on first run (equivalent to `nanobot onboard`).
    # This ensures config.json and workspace templates exist before we start.
    if not get_config_path().exists():
        save_config(config)
        logger.info("First run: created default config at {}", get_config_path())

    if workspace:
        config.agents.defaults.workspace = workspace
    sync_workspace_templates(config.workspace_path)

    bus = MessageBus()
    provider = make_provider_patched(config)
    from nanobot.providers.base import GenerationSettings
    provider.generation = GenerationSettings(
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        reasoning_effort=config.agents.defaults.reasoning_effort,
    )
    session_manager = SessionManager(config.workspace_path)

    # Migrate legacy global cron store to workspace-scoped path (one-time, default workspace only).
    if _is_default_workspace(config.workspace_path):
        legacy_path = get_cron_dir() / "jobs.json"
        new_path = config.workspace_path / "cron" / "jobs.json"
        if legacy_path.is_file() and not new_path.exists():
            new_path.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.move(str(legacy_path), str(new_path))

    cron_store_path = config.workspace_path / "cron" / "jobs.json"
    cron = CronService(cron_store_path)

    agent = AgentLoop.from_config(
        config,
        bus=bus,
        provider=provider,
        cron_service=cron,
        session_manager=session_manager,
    )

    # ------------------------------------------------------------------ cron
    async def on_cron_job(job: CronJob) -> str | None:
        from nanobot.agent.tools.cron import CronTool
        from nanobot.agent.tools.message import MessageTool

        reminder_note = (
            "[Scheduled Task] Timer finished.\n\n"
            f"Task '{job.name}' has been triggered.\n"
            f"Scheduled instruction: {job.payload.message}"
        )
        cron_tool = agent.tools.get("cron")
        cron_token = None
        if isinstance(cron_tool, CronTool):
            cron_token = cron_tool.set_cron_context(True)

        # WebUI-delivered jobs store the target session key in payload.to.
        # This can be a native WebUI session (``web:<user_id>:<hex>``) or any
        # other session the admin is currently viewing (for example ``cli:direct``).
        to = job.payload.to or ""
        delivery_channel = normalize_transport_channel(job.payload.channel) or "cli"
        is_web_delivery = is_webui_transport_channel(job.payload.channel) and bool(to)
        is_webui_target = is_web_delivery and is_webui_session_key(to)

        # Always execute in an isolated timestamped session so:
        #   1. Each run gets a clean LLM context
        #   2. The internal trigger message never pollutes the user's chat session
        exec_session_key = f"cron:{job.id}:{int(time.time() * 1000)}"
        try:
            response = await agent.process_direct(
                reminder_note,
                session_key=exec_session_key,
                channel=delivery_channel,
                chat_id=job.payload.to or "direct",
            )
        finally:
            if isinstance(cron_tool, CronTool) and cron_token is not None:
                cron_tool.reset_cron_context(cron_token)

        response_text = _normalize_agent_response_content(response)

        message_tool = agent.tools.get("message")
        if isinstance(message_tool, MessageTool) and message_tool._sent_in_turn:
            return response_text

        if job.payload.deliver and job.payload.to and response_text:
            await bus.publish_outbound(OutboundMessage(
                channel=delivery_channel,
                chat_id=job.payload.to,
                content=response_text,
            ))

        # For Web-delivered jobs: append only the final AI response to the
        # target session so the scheduled trigger message stays isolated in the
        # internal cron execution session.
        if is_web_delivery and response_text:
            from datetime import datetime

            orig_sess = agent.sessions.get_or_create(to)
            orig_sess.messages.append({
                "role": "assistant",
                "content": response_text,
            })
            orig_sess.updated_at = datetime.now()
            agent.sessions.save(orig_sess)

        # Push result to active WebSocket connections so the browser can
        # refresh the affected session without polling the cron execution session.
        if is_web_delivery and response_text:
            from webui.api.routes.ws import push_cron_result

            notify_session = to if is_webui_target else exec_session_key
            await push_cron_result(notify_session, {
                "type": "cron_result",
                "job_id": job.id,
                "job_name": job.name,
                "content": response_text,
                "session_key": notify_session,
            })
        return response_text

    cron.on_job = on_cron_job

    # --------------------------------------------------------------- channels
    channels = ExtendedChannelManager(config, bus)
    channels.webui_only = webui_only

    def _pick_heartbeat_target() -> tuple[str, str]:
        enabled = set(channels.enabled_channels)
        for item in session_manager.list_sessions():
            key = item.get("key") or ""
            if ":" not in key:
                continue
            channel, chat_id = key.split(":", 1)
            if channel in {"cli", "system", "web"}:
                continue
            if channel in enabled and chat_id:
                return channel, chat_id
        return "cli", "direct"

    # ------------------------------------------------------------- heartbeat
    async def on_heartbeat_execute(tasks: str) -> str:
        channel, chat_id = _pick_heartbeat_target()

        async def _silent(*_args: object, **_kwargs: object) -> None:
            pass

        return await agent.process_direct(
            tasks,
            session_key="heartbeat",
            channel=channel,
            chat_id=chat_id,
            on_progress=_silent,
        )

    async def on_heartbeat_notify(response: str) -> None:
        channel, chat_id = _pick_heartbeat_target()
        if channel == "cli":
            return
        await bus.publish_outbound(OutboundMessage(channel=channel, chat_id=chat_id, content=response))

    hb_cfg = config.gateway.heartbeat
    heartbeat = HeartbeatService(
        workspace=config.workspace_path,
        provider=provider,
        model=agent.model,
        on_execute=on_heartbeat_execute,
        on_notify=on_heartbeat_notify,
        interval_s=hb_cfg.interval_s,
        enabled=hb_cfg.enabled,
    )

    container = ServiceContainer(
        config=config,
        bus=bus,
        agent=agent,
        channels=channels,
        session_manager=session_manager,
        cron=cron,
        heartbeat=heartbeat,
        oracle_config=OracleConfigService(
            Path(oracle_config).expanduser().resolve(strict=False) if oracle_config else None
        ),
        make_provider=make_provider_patched,
        webui_only=webui_only,
    )

    if channels.enabled_channels:
        logger.info("Channels enabled: {}", ", ".join(channels.enabled_channels))
    else:
        logger.warning("No IM channels enabled")

    if webui_only:
        logger.info(
            "WebUI-only mode: IM channels / heartbeat will NOT be started. "
            "An external nanobot process is expected to handle IM traffic."
        )

    logger.info("Starting nanobot webui on http://{}:{}", web_host, web_port)

    async def run() -> None:
        try:
            await cron.start()
            if webui_only:
                await asyncio.gather(
                    agent.run(),
                    start_api_server(container, host=web_host, port=web_port),
                )
            else:
                await heartbeat.start()
                await asyncio.gather(
                    agent.run(),
                    channels.start_all(),
                    start_api_server(container, host=web_host, port=web_port),
                )
        except KeyboardInterrupt:
            logger.info("Shutting down…")
        finally:
            await agent.close_mcp()
            if not webui_only:
                heartbeat.stop()
            cron.stop()
            agent.stop()
            if not webui_only:
                await channels.stop_all()

    await run()


def main_cli() -> None:
    """Entry point for the ``nanobot-webui`` console script."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="nanobot-webui",
        description="nanobot WebUI — start WebUI + gateway in one process",
    )
    parser.add_argument("--port", type=int, default=18780, help="WebUI port (default: 18780)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--workspace", default=None, help="Override workspace directory")
    parser.add_argument("--oracle-config", default=None, dest="oracle_config",
                        help="Path to Oracle DB connection JSON file")
    parser.add_argument("--config", default=None, dest="config_path",
                        help="Path to config file")
    parser.add_argument("--daemon", "-d", action="store_true", default=False,
                        help="Run in the background (PID → ~/.nanobot/webui.pid)")
    parser.add_argument("--log-level", default="DEBUG", dest="log_level",
                        metavar="LEVEL",
                        help="Log level: DEBUG, INFO, WARNING, ERROR (default: DEBUG)")
    parser.add_argument("--webui-only", action="store_true", default=False,
                        dest="webui_only",
                        help="Start only the WebUI HTTP server (no IM channels / heartbeat). "
                             "Use this when nanobot is already running as a separate process.")
    args = parser.parse_args()

    if args.daemon:
        from webui.cli import _start_daemon
        _start_daemon(
            port=args.port,
            host=args.host,
            workspace=args.workspace,
            oracle_config=args.oracle_config,
            config_path=args.config_path,
        )
        return

    if args.config_path:
        from nanobot.config.loader import set_config_path
        set_config_path(Path(args.config_path).expanduser().resolve())

    asyncio.run(main(
        web_port=args.port,
        web_host=args.host,
        workspace=args.workspace,
        oracle_config=args.oracle_config,
        log_level=args.log_level,
        webui_only=args.webui_only,
    ))


if __name__ == "__main__":
    main_cli()
