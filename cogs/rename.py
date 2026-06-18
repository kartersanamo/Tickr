"""rename.py — Rename ticket channel."""
from discord.ext import commands
from discord import app_commands
import asyncio
import discord

from core.decorators import TaskDecorator
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color, optional_logo_file, set_embed_footer
from services.ticket_check_service import is_ticket
from services.ticket_channel_ordering import TicketChannelOrdering


class Rename(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client

    @TaskDecorator.task("Send Embed", False)
    async def send_embed(
        self, interaction: discord.Interaction, old_name: str, new_name: str, cfg
    ) -> None:
        rename_embed = discord.Embed(
            description=(
                f"{interaction.user.mention} has changed the ticket name from "
                f"**{old_name}** to **{new_name}**."
            ),
            color=embed_color(cfg),
        )
        set_embed_footer(rename_embed, cfg)
        logo_file = optional_logo_file(cfg)
        kwargs = {"embed": rename_embed}
        if logo_file:
            kwargs["attachments"] = [logo_file]
        await interaction.edit_original_response(**kwargs)

    @is_ticket()
    @app_commands.guild_only()
    @app_commands.command(name="rename", description="Renames the ticket channel")
    @app_commands.describe(name="The name to rename the ticket to")
    async def rename(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        await self.rename_command(interaction, name)

    @TaskDecorator.task("Rename Command", True)
    async def rename_command(self, interaction: discord.Interaction, name: str) -> None:
        if interaction.guild_id is None or not isinstance(interaction.channel, discord.TextChannel):
            return
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        channel = interaction.channel
        old_name = channel.name
        channel = await asyncio.wait_for(channel.edit(name=name), timeout=5.0)
        if channel.category is not None:
            position = await asyncio.to_thread(
                TicketChannelOrdering.get_ticket_position,
                channel.category,
                channel,
            )
            if position != channel.position:
                channel = await asyncio.wait_for(channel.edit(position=position), timeout=5.0)
        await self.send_embed(interaction, old_name, name, cfg)

    async def edit_channel_name(self, guild_id: int, channel_id: int, name: str) -> None:
        guild = self.client.get_guild(guild_id)
        if guild is None:
            return
        channel = guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            await channel.edit(name=name)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Rename(client))
