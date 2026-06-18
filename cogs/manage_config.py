"""manage_config.py — Full guild configuration editor."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from ui.views.manage_config_view import open_manage_config


class ManageConfig(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name="manage-config",
        description="Browse and edit all Tickr settings for this server",
    )
    async def manage_config(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None or interaction.guild is None:
            return
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Administrator permission required.",
                ephemeral=True,
            )
            return
        await open_manage_config(interaction, interaction.guild_id)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(ManageConfig(client))
