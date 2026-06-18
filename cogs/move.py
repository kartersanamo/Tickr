"""move.py — Move ticket to another category."""
from discord.ext import commands
from discord import app_commands
import discord
import asyncio

from core.database import DatabasePool
from core.decorators import TaskDecorator
from core.loggers import log_commands
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color, set_embed_footer
from services.ticket_check_service import is_ticket
from services.ticket_channel_ordering import TicketChannelOrdering


class Move(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client

    @TaskDecorator.task("Defer Response", False)
    async def defer_response(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

    @TaskDecorator.task("Check Blacklisted", False)
    async def check_blacklisted_category(
        self, interaction: discord.Interaction, category: discord.CategoryChannel, cfg
    ) -> bool:
        if category.id in cfg.get("BLACKLISTED_MOVE_CATEGORIES", []):
            await interaction.response.send_message(
                content="`❌` Failed! You cannot move a ticket to this category!", ephemeral=True
            )
            return True
        return False

    @TaskDecorator.task("Check Category", False)
    async def check_ticket_category(
        self, interaction: discord.Interaction, category: discord.CategoryChannel, cfg
    ) -> bool:
        if category.id not in cfg.get("TICKET_CATEGORIES", []):
            await interaction.response.send_message(
                content="`❌` Failed! That is not a ticket category!", ephemeral=True
            )
            return True
        return False

    @TaskDecorator.task("Move Categories", False)
    async def move_categories(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            return
        position = TicketChannelOrdering.get_ticket_position(category, interaction.channel)
        await interaction.channel.edit(category=category, position=position)

    @TaskDecorator.task("Update Database", False)
    async def update_database(
        self, guild_id: int, category: discord.CategoryChannel, channel_id: int, cfg
    ) -> None:
        private_mode = cfg.private_mode_for_category(category.id)
        if private_mode == "Admin":
            DatabasePool.execute(
                "UPDATE tickets SET type = %s, privated = 'Admin' WHERE guild_id = %s AND channel_id = %s",
                (category.name, guild_id, channel_id),
            )
        elif private_mode == "Management":
            DatabasePool.execute(
                "UPDATE tickets SET type = %s, privated = 'Management' WHERE guild_id = %s AND channel_id = %s",
                (category.name, guild_id, channel_id),
            )
        else:
            DatabasePool.execute(
                "UPDATE tickets SET type = %s, privated = '' WHERE guild_id = %s AND channel_id = %s",
                (category.name, guild_id, channel_id),
            )

    @TaskDecorator.task("Set Permissions", False)
    async def set_permissions(self, interaction: discord.Interaction, new_category_id: int, cfg) -> None:
        if not isinstance(interaction.channel, discord.TextChannel) or interaction.guild is None:
            return
        permissions = interaction.channel.overwrites.items()
        while interaction.channel.category and interaction.channel.category.id != new_category_id:
            await asyncio.sleep(0.5)
        await interaction.channel.edit(sync_permissions=True)
        for key, value in permissions:
            if isinstance(key, discord.Member) or key == interaction.guild.default_role:
                await interaction.channel.set_permissions(key, overwrite=value)
        staff_id = cfg.get("ROLE_IDS.STAFF_TEAM_ROLE_ID")
        if staff_id:
            staff_team = interaction.guild.get_role(int(staff_id))
            if staff_team:
                await interaction.channel.set_permissions(staff_team, view_channel=False)

    @TaskDecorator.task("Send Embed", False)
    async def send_embed(self, interaction: discord.Interaction, category_name: str, cfg) -> None:
        confirmation_embed = discord.Embed(
            description=f"{interaction.user.mention} has moved this ticket to **{category_name}**",
            color=embed_color(cfg),
        )
        set_embed_footer(confirmation_embed, cfg)
        await interaction.edit_original_response(embed=confirmation_embed)

    @is_ticket()
    @app_commands.guild_only()
    @app_commands.command(name="move", description="Moves a ticket to a new category")
    @app_commands.describe(category="The category to move the ticket to")
    async def move(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        await self.move_command(interaction, category)

    @TaskDecorator.task("Move Command", True)
    async def move_command(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        if interaction.guild_id is None:
            return
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        blacklisted = await self.check_blacklisted_category(interaction, category, cfg)
        not_ticket = await self.check_ticket_category(interaction, category, cfg)
        if not blacklisted and not not_ticket:
            await self.defer_response(interaction)
            await self.move_categories(interaction, category)
            await self.update_database(interaction.guild_id, category, interaction.channel.id, cfg)
            await self.set_permissions(interaction, category.id, cfg)
            await self.send_embed(interaction, category.name, cfg)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Move(client))
