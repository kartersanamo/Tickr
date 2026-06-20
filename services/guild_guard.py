from __future__ import annotations

import functools
from typing import Callable

import discord

from services.guild_config_service import GuildConfigService


def guild_configured() -> Callable:
    """Require guild to be configured via /setup before running command."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(interaction: discord.Interaction, *args, **kwargs):
            if interaction.guild_id is None:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "Commands cannot be ran in DMs!",
                        ephemeral=True,
                    )
                return
            cfg = await GuildConfigService.for_guild(interaction.guild_id)
            if not cfg.configured:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "This server is not configured yet. Run `/setup` to configure Tickr.",
                        ephemeral=True,
                    )
                return
            return await func(interaction, *args, **kwargs)

        return wrapper

    return decorator


async def require_guild_configured(interaction: discord.Interaction) -> bool:
    """Return True if guild is configured; send ephemeral message otherwise."""
    if interaction.guild_id is None:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Commands cannot be ran in DMs!",
                ephemeral=True,
            )
        return False
    cfg = await GuildConfigService.for_guild(interaction.guild_id)
    if not cfg.configured:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "This server is not configured yet. Run `/setup` to configure Tickr.",
                ephemeral=True,
            )
        return False
    return True


async def guild_configured_check(interaction: discord.Interaction) -> bool:
    """app_commands.check predicate for configured guilds."""
    return await require_guild_configured(interaction)
