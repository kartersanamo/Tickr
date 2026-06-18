"""private.py — Private / management ticket categories."""
from discord.ext import commands
from discord import app_commands
import discord
import asyncio

from core.database import DatabasePool
from core.decorators import TaskDecorator
from core.loggers import log_tasks
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color, optional_logo_file, set_embed_footer
from services.ticket_check_service import is_ticket


class Private(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client

    @TaskDecorator.task("Change Category", False)
    async def change_category(self, channel: discord.TextChannel, category: discord.CategoryChannel) -> None:
        await channel.edit(category=category)

    @TaskDecorator.task("Update Database", False)
    async def update_database(self, guild_id: int, channel_id: int, privated_str: str) -> None:
        DatabasePool.execute(
            "UPDATE tickets SET privated = %s WHERE guild_id = %s AND channel_id = %s",
            (privated_str, guild_id, channel_id),
        )

    @TaskDecorator.task("Update Permissions", False)
    async def update_permissions(
        self, channel: discord.TextChannel, guild: discord.Guild, permissions, default_role: discord.Role, cfg
    ) -> None:
        await channel.edit(sync_permissions=True)
        for key, value in permissions:
            if isinstance(key, discord.Member) or key == default_role:
                await channel.set_permissions(key, overwrite=value)
        staff_id = cfg.get("ROLE_IDS.STAFF_TEAM_ROLE_ID")
        if staff_id:
            staff_team = guild.get_role(int(staff_id))
            if staff_team:
                await channel.set_permissions(staff_team, view_channel=False)

    @TaskDecorator.task("Send Embed", False)
    async def send_embed(self, interaction: discord.Interaction, description: str, cfg) -> None:
        embed = discord.Embed(
            color=embed_color(cfg),
            description=f"{interaction.user.mention} {description}",
        )
        set_embed_footer(embed, cfg)
        logo_file = optional_logo_file(cfg)
        if logo_file:
            await interaction.followup.send(embed=embed, file=logo_file)
        else:
            await interaction.followup.send(embed=embed)

    async def _move_private(
        self,
        interaction: discord.Interaction,
        category_key: str,
        privated: str,
        description: str,
    ) -> None:
        if interaction.guild_id is None or not isinstance(interaction.channel, discord.TextChannel):
            return
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        category_id = cfg.get(f"CHANNEL_IDS.{category_key}")
        if not category_id:
            await interaction.followup.send(
                "`❌` Private category not configured. Set it in `/setup` or guild config.",
                ephemeral=True,
            )
            return
        category = interaction.guild.get_channel(int(category_id))
        if not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send("`❌` Private category not found.", ephemeral=True)
            return

        await self.change_category(interaction.channel, category)
        await self.update_database(interaction.guild_id, interaction.channel.id, privated)

        def check(before, after):
            return after.id == interaction.channel.id and after.category == category

        try:
            await interaction.client.wait_for("guild_channel_update", check=check, timeout=5)
        except asyncio.TimeoutError:
            if interaction.channel.category and interaction.channel.category.id != category.id:
                log_tasks.warning("Timeout waiting for category update.")
                await interaction.followup.send(
                    "`❌` Timeout Error! The bot could not change the channel's category.",
                    ephemeral=True,
                )
                return

        await self.update_permissions(
            interaction.channel,
            interaction.guild,
            interaction.channel.overwrites.items(),
            interaction.guild.default_role,
            cfg,
        )
        await self.send_embed(interaction, description, cfg)

    @is_ticket()
    @app_commands.guild_only()
    @app_commands.command(
        name="private",
        description="Privates the ticket channel so that only Admins can view it",
    )
    async def private(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await self._move_private(
            interaction, "ADMIN_PRIVATE_CATEGORY_ID", "Admin", "has turned this channel private."
        )

    @is_ticket()
    @app_commands.guild_only()
    @app_commands.command(
        name="management",
        description="Privates the channel so that only Management can view it",
    )
    async def management(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await self._move_private(
            interaction,
            "MANAGEMENT_PRIVATE_CATEGORY_ID",
            "Management",
            "has made this channel for management.",
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Private(client))
