"""Slash command usage analytics."""

from __future__ import annotations

import discord
from discord.ext import commands

from core.analytics import logger as analytics


class CommandUsageCog(commands.Cog):
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction) -> None:
        if interaction.type != discord.InteractionType.application_command:
            return
        if not interaction.command or interaction.guild_id is None:
            return
        analytics.record_command(
            interaction.guild_id,
            str(interaction.client.user.id),
            interaction.command.qualified_name,
        )

    @staticmethod
    async def setup(client: commands.Bot) -> None:
        if any(isinstance(c, CommandUsageCog) for c in client.cogs.values()):
            return
        await client.add_cog(CommandUsageCog())
