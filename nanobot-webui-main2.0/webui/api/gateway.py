"""Service container and API server coroutine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable

from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.config.schema import Config
from nanobot.cron.service import CronService
from nanobot.session.manager import SessionManager

from webui.api.channel_ext import ExtendedChannelManager
from webui.oracle_config import OracleConfigService
from webui.tool_policy import ToolPolicyService


class HeartbeatCompatService:
    """Minimal heartbeat adapter for nanobot 0.2.2 runtime."""

    def __init__(
        self,
        *,
        workspace: Path,
        provider: Any = None,
        model: str | None = None,
        on_execute: Callable[[str], Awaitable[str]] | None = None,
        on_notify: Callable[[str], Awaitable[None]] | None = None,
        interval_s: int = 30 * 60,
        enabled: bool = True,
    ) -> None:
        self.workspace = Path(workspace)
        self.provider = provider
        self.model = model
        self.on_execute = on_execute
        self.on_notify = on_notify
        self.interval_s = interval_s
        self.enabled = enabled

    async def start(self) -> None:
        """Keep the old lifecycle hook shape without spawning a legacy service."""
        return None

    def stop(self) -> None:
        """Keep the old lifecycle hook shape without spawning a legacy service."""
        return None


@dataclass
class ServiceContainer:
    """All live nanobot services, shared with FastAPI route handlers."""

    config: Config
    bus: MessageBus
    agent: AgentLoop
    channels: ExtendedChannelManager
    session_manager: SessionManager
    cron: CronService
    heartbeat: HeartbeatCompatService
    oracle_config: OracleConfigService
    tool_policy: ToolPolicyService
    make_provider: Callable = field(default=lambda cfg: None)
    webui_only: bool = False

    def reload_provider(self) -> None:
        """Hot-swap the LLM provider and all runtime settings on agent and heartbeat."""
        from nanobot.providers.base import GenerationSettings
        d = self.config.agents.defaults
        new_provider = self.make_provider(self.config)
        if new_provider is not None:
            self.agent.provider = new_provider
            self.heartbeat.provider = new_provider
        # Always sync model and other mutable settings
        self.agent.model = d.model
        self.agent.max_iterations = d.max_tool_iterations
        self.agent.context_window_tokens = d.context_window_tokens
        gen = GenerationSettings(
            temperature=d.temperature,
            max_tokens=d.max_tokens,
            reasoning_effort=d.reasoning_effort,
        )
        self.agent.provider.generation = gen
        self.heartbeat.provider.generation = gen


async def start_api_server(
    container: ServiceContainer,
    host: str = "0.0.0.0",
    port: int = 8080,
) -> None:
    """Start the FastAPI / uvicorn server as an asyncio coroutine.

    Designed to run inside ``asyncio.gather()`` alongside the nanobot
    channel tasks so everything shares the same event loop.
    """
    import uvicorn

    from webui.api.server import create_app

    app = create_app(container)
    server_cfg = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(server_cfg)
    await server.serve()
