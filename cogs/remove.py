"""remove.py — Remove user from ticket."""

from discord.ext import commands
from discord import app_commands
import discord

from core.decorators import TaskDecorator
from core.loggers import log_commands
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color, optional_logo_file, set_embed_footer
from services.ticket_check_service import is_ticket


class Remove(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client = client

    async def get_role_level(self, role_id: int, hierarchy: dict) -> int:
        for level, roles in enumerate(hierarchy.values()):
            if role_id in roles:
                return level
        return -1

    async def is_higher_rank(
        self, role_id1: int, role_id2: int, hierarchy: dict
    ) -> bool:
        level1 = await self.get_role_level(role_id1, hierarchy)
        level2 = await self.get_role_level(role_id2, hierarchy)
        return level1 > level2

    @TaskDecorator.task("Remove Permissions", False)
    async def remove_permissions(
        self, channel: discord.TextChannel, user: discord.Member
    ) -> None:
        perms = channel.overwrites_for(user)
        perms.view_channel = False
        await channel.set_permissions(user, overwrite=perms)

    @TaskDecorator.task("Send Embed", False)
    async def send_embed(
        self, interaction: discord.Interaction, user: discord.Member, cfg
    ) -> None:
        embed = discord.Embed(
            color=embed_color(cfg),
            description=f"{interaction.user.mention} has removed {user.mention} from the ticket {interaction.channel.mention}",
        )
        set_embed_footer(embed, cfg)
        logo_file = optional_logo_file(cfg)
        if logo_file:
            await interaction.response.send_message(embed=embed, file=logo_file)
        else:
            await interaction.response.send_message(embed=embed)

    @TaskDecorator.task("Check Higher Rank", False)
    async def check_higher_rank(
        self, interaction: discord.Interaction, user: discord.Member, cfg
    ) -> bool:
        staff_id = cfg.get("ROLE_IDS.STAFF_TEAM_ROLE_ID")
        if not staff_id or interaction.guild is None:
            return False
        staff_team_role = interaction.guild.get_role(int(staff_id))
        if staff_team_role and staff_team_role in user.roles:
            hierarchy = cfg.get("ROLE_HIERARCHY", {})
            if not hierarchy:
                return False
            disregard = cfg.get("DISREGARD_REMOVE_COMMAND_ROLE_IDS", [])
            role_id_1 = (
                user.top_role.id
                if user.top_role.id not in disregard
                else user.roles[-2].id
            )
            role_id_2 = (
                interaction.user.top_role.id
                if interaction.user.top_role.id not in disregard
                else interaction.user.roles[-2].id
            )
            if await self.is_higher_rank(role_id_1, role_id_2, hierarchy):
                log_commands.warning(
                    f"{interaction.user} tried to remove higher rank {user}"
                )
                await interaction.response.send_message(
                    content="You cannot remove a staff member who is higher than you!",
                    ephemeral=True,
                )
                return True
        return False

    @is_ticket()
    @app_commands.guild_only()
    @app_commands.command(name="remove", description="Removes a user from the ticket")
    @app_commands.describe(user="The user to remove from the ticket")
    async def remove(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        await self.remove_command(interaction, user)

    @TaskDecorator.task("Remove Command", True)
    async def remove_command(
        self, interaction: discord.Interaction, user: discord.Member
    ) -> None:
        if interaction.guild_id is None or not isinstance(
            interaction.channel, discord.TextChannel
        ):
            return
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        removing_higher = await self.check_higher_rank(interaction, user, cfg)
        if not removing_higher:
            await self.remove_permissions(interaction.channel, user)
            await self.send_embed(interaction, user, cfg)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Remove(client))
