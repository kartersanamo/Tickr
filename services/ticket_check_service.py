from __future__ import annotations

import discord
from discord import app_commands

from services.guild_config_service import GuildConfigService


class TicketCheckService:
    @staticmethod
    def ticket_only():
        async def predicate(interaction: discord.Interaction) -> bool:
            if interaction.guild_id is None:
                raise app_commands.CheckFailure(
                    "Failed! This command can only be ran inside of a ticket."
                )
            if not isinstance(interaction.channel, discord.TextChannel):
                raise app_commands.CheckFailure(
                    "Failed! This command can only be ran inside of a ticket."
                )
            if interaction.channel.category is None:
                raise app_commands.CheckFailure(
                    "Failed! This command can only be ran inside of a ticket."
                )
            cfg = await GuildConfigService.for_guild(interaction.guild_id)
            categories = cfg.get("TICKET_CATEGORIES", [])
            if interaction.channel.category.id not in categories:
                raise app_commands.CheckFailure(
                    "Failed! This command can only be ran inside of a ticket."
                )
            return True

        return app_commands.check(predicate)


is_ticket = TicketCheckService.ticket_only
