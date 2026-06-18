"""Setup wizard for new guilds."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from services.guild_config_service import GuildConfigService
from ui.views.setup_wizard_views import SetupView


class Setup(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        try:
            owner = guild.owner
            if owner:
                await owner.send(
                    f"Thanks for adding **Tickr** to **{guild.name}**!\n"
                    "Run `/setup` in your server (Administrator required) to configure tickets."
                )
        except discord.HTTPException:
            pass

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="setup", description="Configure Tickr for this server")
    async def setup(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            return
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        if cfg.configured:
            await interaction.response.send_message(
                "This server is already configured. Use `/manage-config` to edit settings "
                "or `/manage-tickets` for ticket types.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            "Welcome to **Tickr** setup! This wizard configures required settings and "
            "recommended optional ones.\n\nPress **Start Setup** when ready.",
            view=SetupView(interaction.guild_id),
            ephemeral=True,
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Setup(client))
