"""Guild-scoped slash command sync for Tickr public bot."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from discord.ext import commands


class GuildCommandSync:
    _logger = logging.getLogger(__name__)

    @staticmethod
    def resolve_dev_guild_id() -> int | None:
        raw = os.getenv("DISCORD_GUILD_ID", "").strip()
        if raw.isdigit():
            return int(raw)
        return None

    @staticmethod
    def format_command_names(
        commands_list: list[discord.app_commands.AppCommand],
    ) -> str:
        parts: list[str] = []
        for command in commands_list:
            subs = getattr(command, "options", None) or []
            if subs:
                sub_names = ", ".join(getattr(o, "name", str(o)) for o in subs[:8])
                parts.append(f"{command.name}({sub_names})")
            else:
                parts.append(command.name)
        return ", ".join(parts)

    @classmethod
    async def _sync_global(
        cls,
        bot: "commands.Bot",
        warn: Callable[[str], None],
    ) -> list[discord.app_commands.AppCommand]:
        try:
            return await bot.tree.sync()
        except discord.HTTPException as exc:
            if exc.code == 50240:
                warn(
                    "Global command sync incomplete — Discord Activities Entry Point "
                    "must stay registered (50240)."
                )
                return []
            raise

    @classmethod
    async def sync_commands(
        cls,
        bot: "commands.Bot",
        *,
        log: logging.Logger | None = None,
    ) -> list[discord.app_commands.AppCommand]:
        info = log.info if log else cls._logger.info
        warn = log.warning if log else cls._logger.warning

        if not bot.application_id:
            warn("application_id not ready — skipping command sync")
            return []

        synced = await cls._sync_global(bot, warn)
        info(
            "Globally synced %s commands: %s",
            len(synced),
            cls.format_command_names(synced),
        )

        dev_guild_id = cls.resolve_dev_guild_id()
        if dev_guild_id is not None:
            guild = discord.Object(id=dev_guild_id)
            bot.tree.copy_global_to(guild=guild)
            guild_cmds = await bot.tree.sync(guild=guild)
            info(
                "Dev guild-synced %s commands to guild %s",
                len(guild_cmds),
                dev_guild_id,
            )

        return synced


sync_guild_commands = GuildCommandSync.sync_commands
