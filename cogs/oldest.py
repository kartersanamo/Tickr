"""oldest.py — Display oldest open tickets."""

from discord.ext import commands
from discord import app_commands
import discord

from core.database import DatabasePool
from core.decorators import TaskDecorator
from core.loggers import log_tasks
from services.guild_config_service import GuildConfigService
from ui.views.paginator import paginator_for_cfg


class Oldest(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client

    @TaskDecorator.task("Get Data", False)
    async def get_data_list(
        self,
        interaction: discord.Interaction,
        guild_id: int,
        category: discord.CategoryChannel = None,
    ) -> list[str]:
        data: list = []
        bad_channels: list = []
        rows = DatabasePool.execute(
            "SELECT channel_id, opened_at FROM tickets WHERE guild_id = %s AND is_active = 1 ORDER BY opened_at",
            (guild_id,),
        )
        for row in rows:
            channel = interaction.guild.get_channel(int(row["channel_id"]))
            if channel:
                if category is None or channel.category_id == category.id:
                    data.append(
                        f"{channel.mention} <t:{int(float(row['opened_at']))}:R>"
                    )
            else:
                bad_channels.append(row["channel_id"])

        if bad_channels:
            from services.active_ticket_cache import active_ticket_cache

            placeholders = ", ".join(["%s"] * len(bad_channels))
            DatabasePool.execute(
                f"UPDATE tickets SET is_active = 0 WHERE guild_id = %s AND channel_id IN ({placeholders})",
                (guild_id, *bad_channels),
            )
            for channel_id in bad_channels:
                active_ticket_cache.unregister(guild_id, int(channel_id))
            log_tasks.warning(f"{len(bad_channels)} invalid channel IDs cleaned up")

        return data or ["No data found."]

    @TaskDecorator.task("Send Paginator", False)
    async def send_paginator(
        self,
        interaction: discord.Interaction,
        data: list[str],
        category: discord.CategoryChannel = None,
    ) -> None:
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        paginate = paginator_for_cfg(cfg)
        paginate.title = (
            f"Oldest Tickets in {category.name}" if category else "Oldest Tickets"
        )
        paginate.sep = 15
        paginate.category = category
        paginate.data = data
        paginate.count = True
        await paginate.send(interaction)

    @app_commands.guild_only()
    @app_commands.command(
        name="oldest", description="Displays the oldest tickets that are currently open"
    )
    @app_commands.describe(category="The category of tickets to display")
    async def oldest(
        self, interaction: discord.Interaction, category: discord.CategoryChannel = None
    ) -> None:
        await self.oldest_command(interaction, category)

    @TaskDecorator.task("Oldest Command", True)
    async def oldest_command(
        self, interaction: discord.Interaction, category: discord.CategoryChannel
    ) -> None:
        if interaction.guild_id is None:
            return
        await interaction.response.defer()
        data = await self.get_data_list(interaction, interaction.guild_id, category)
        await self.send_paginator(interaction, data, category)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Oldest(client))
