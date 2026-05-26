"""Extended ChannelManager with hot-reload capabilities.

This is a non-invasive subclass — zero modifications to nanobot source.
"""

from __future__ import annotations

import asyncio

from loguru import logger

from nanobot.channels.manager import ChannelManager
from nanobot.config.schema import Config


class ExtendedChannelManager(ChannelManager):
    """
    Subclass of ChannelManager that adds hot-reload support.

    New methods:
      - update_config(new_config)        — update live config reference
      - reload_channel(name)             — gracefully restart one channel
      - reload_all(new_config)           — stop-all → update-config → start-all

    In webui_only mode the IM channels are not started by this process;
    get_status() derives ``running`` from the config's enabled state so the
    dashboard reflects what the external nanobot gateway should be running.
    """

    #: Set to True when webui is started with --webui-only.  Affects
    #: get_status() so the dashboard isn't stuck at 0/N.
    webui_only: bool = False

    def get_status(self) -> dict:  # type: ignore[override]
        """Return channel status dict.

        In normal mode delegates to the parent (checks channel.is_running).
        In webui_only mode the channels are managed by an external process, so
        we derive ``running`` from whether the channel is enabled in config.
        We iterate config directly (not self.channels) so channels that failed
        to instantiate are still reported correctly.
        """
        if not self.webui_only:
            return super().get_status()

        result: dict = {}
        for name, ch_dict in self.config.channels.model_dump().items():
            # Skip non-channel scalar fields (send_progress, send_tool_hints, …)
            if not isinstance(ch_dict, dict):
                continue
            if ch_dict.get("enabled", False):
                result[name] = {"enabled": True, "running": True}
        return result

    def update_config(self, new_config: Config) -> None:
        """Swap the config reference (does *not* restart any channels)."""
        self.config = new_config

    async def reload_channel(self, name: str) -> None:
        """Stop and restart a single channel in-place."""
        channel = self.channels.get(name)
        if channel:
            logger.info("Reloading channel: {}", name)
            try:
                await channel.stop()
            except Exception as exc:
                logger.error("Error stopping channel {} during reload: {}", name, exc)
            del self.channels[name]

        # Re-init all channels from current config into a temp dict, then
        # pull only the target channel from it.
        saved = dict(self.channels)
        self.channels.clear()
        try:
            self._init_channels()
        except SystemExit:
            # allow_from validation may fail for other channels; we only want
            # the channel we're reloading.
            pass
        refreshed = dict(self.channels)

        # Restore existing channels, add the freshly initialised target.
        self.channels = saved
        if name in refreshed:
            self.channels[name] = refreshed[name]
            asyncio.create_task(self._start_channel(name, self.channels[name]))
            logger.info("Channel {} reloaded successfully", name)
        else:
            logger.info("Channel {} is now disabled — not restarted", name)

    async def reload_all(self, new_config: Config) -> None:
        """Stop all channels, apply new config, and restart everything."""
        logger.info("Reloading all channels…")

        # Cancel the outbound dispatcher.
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
            self._dispatch_task = None

        # Stop every channel.
        for ch_name, channel in list(self.channels.items()):
            try:
                await channel.stop()
            except Exception as exc:
                logger.error("Error stopping channel {} during reload_all: {}", ch_name, exc)

        self.channels.clear()

        # Apply new config and re-initialise.
        self.update_config(new_config)
        self._init_channels()

        # Restart (start_all creates the dispatcher + channel tasks).
        await self.start_all()
        logger.info("All channels reloaded")
