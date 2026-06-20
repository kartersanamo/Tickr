"""add.py — Add user to ticket."""

from discord.ext import commands
from discord import app_commands
import discord

from core.database import DatabasePool
from core.decorators import TaskDecorator
from core.loggers import log_commands
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color, optional_logo_file, set_embed_footer
from services.ticket_check_service import is_ticket


class Add(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client

    @TaskDecorator.task("Check Blacklisted", False)
    async def check_blacklisted(
        self, interaction: discord.Interaction, user: discord.Member, guild_id: int
    ) -> bool:
        rows = DatabasePool.execute(
            "SELECT 1 FROM blacklists WHERE guild_id = %s AND user_id = %s LIMIT 1",
            (guild_id, user.id),
        )
        if rows:
            log_commands.warning(
                f"Failed to add {user} ({user.id}) — ticket blacklisted"
            )
            await interaction.response.send_message(
                content="`❌` Failed! You cannot add this player to the ticket as they are currently ticket blacklisted!",
                ephemeral=True,
            )
            return True
        return False

    @TaskDecorator.task("Check Timed Out", False)
    async def check_timed_out(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> bool:
        if user.is_timed_out():
            await interaction.response.send_message(
                content="`❌` Failed! You cannot add this player to the ticket as they are currently timed out!",
                ephemeral=True,
            )
            return True
        return False

    @TaskDecorator.task("Set Permissions", False)
    async def set_permissions(
        self, channel: discord.TextChannel, user: discord.Member
    ) -> None:
        perms = channel.overwrites_for(user)
        perms.view_channel = True
        perms.send_messages = True
        await channel.set_permissions(user, overwrite=perms)

    @TaskDecorator.task("Send Embed", False)
    async def send_embed(
        self, interaction: discord.Interaction, user: discord.Member, cfg
    ) -> None:
        embed = discord.Embed(
            color=embed_color(cfg),
            description=f"{interaction.user.mention} has added {user.mention} to the ticket {interaction.channel.mention}",
        )
        set_embed_footer(embed, cfg)
        logo_file = optional_logo_file(cfg)
        if logo_file:
            await interaction.response.send_message(embed=embed, file=logo_file)
        else:
            await interaction.response.send_message(embed=embed)

    @is_ticket()
    @app_commands.guild_only()
    @app_commands.command(name="add", description="Adds a user to the ticket")
    @app_commands.describe(user="The user to add to the ticket")
    async def add(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await self.add_command(interaction, user)

    @TaskDecorator.task("Add Command", True)
    async def add_command(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        if interaction.guild_id is None or not isinstance(
            interaction.channel, discord.TextChannel
        ):
            return
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        blacklisted = await self.check_blacklisted(
            interaction, user, interaction.guild_id
        )
        timed_out = await self.check_timed_out(interaction, user)
        if not blacklisted and not timed_out:
            await self.set_permissions(interaction.channel, user)
            await self.send_embed(interaction, user, cfg)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Add(client))
