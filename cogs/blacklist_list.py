"""blacklist_list.py — List ticket blacklisted users."""

from discord.ext import commands
from discord import app_commands
import discord

from core.database import DatabasePool
from core.decorators import TaskDecorator
from services.guild_config_service import GuildConfigService
from ui.views.paginator import paginator_for_cfg


class BlacklistList(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client

    @TaskDecorator.task("Send Paginator")
    async def send_paginator(
        self, interaction: discord.Interaction, data: list
    ) -> None:
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        paginate = paginator_for_cfg(cfg)
        paginate.title = "Blacklisted Users"
        paginate.data = data
        paginate.sep = 5
        await paginate.send(interaction)

    @TaskDecorator.task("Get Blacklist Data")
    async def get_blacklist_data(
        self, interaction: discord.Interaction, rows: list
    ) -> list:
        blacklist_data: list = []
        for row in rows:
            user_id = int(row["user_id"])
            staff_id = int(row["staff_id"])
            reason = row["reason"]
            user = interaction.guild.get_member(user_id)
            staff = interaction.guild.get_member(staff_id)
            user_name = user.display_name if user else f"`{user_id}`"
            staff_mention = staff.mention if staff else f"`{staff_id}`"
            user_info = f"{user_name} ({user_id})"
            reason_info = (
                f"`Staff` {staff_mention}\n`Reason` {reason}\n"
                f"`Unblacklisted` <t:{int(row['unblacklist_at'])}:R>"
            )
            blacklist_data.append(f"**{user_info}**\n{reason_info}\n")
        return blacklist_data or ["No data found."]

    @app_commands.guild_only()
    @app_commands.command(
        name="blacklist-list", description="Shows all users blacklisted from tickets"
    )
    async def blacklistlist(self, interaction: discord.Interaction) -> None:
        await self.blacklistlist_command(interaction)

    @TaskDecorator.task("Blacklist List Command", True)
    async def blacklistlist_command(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            return
        rows = DatabasePool.execute(
            "SELECT user_id, staff_id, unblacklist_at, reason FROM blacklists WHERE guild_id = %s",
            (interaction.guild_id,),
        )
        blacklist_data = await self.get_blacklist_data(interaction, rows)
        await self.send_paginator(interaction, blacklist_data)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(BlacklistList(client))
