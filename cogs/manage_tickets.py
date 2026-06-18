"""manage_tickets.py — In-Discord ticket type editor."""
from discord.ext import commands
from discord import app_commands
import discord

from services.guild_config_service import GuildConfigService
from services.guild_guard import guild_configured_check
from ui.views.manage_categories_view import ManageCategoriesView


class ManageTickets(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @app_commands.guild_only()
    @app_commands.command(
        name="manage-tickets",
        description="Fully manage panel categories, ticket types, and questions",
    )
    @app_commands.check(guild_configured_check)
    async def manage_tickets(self, interaction: discord.Interaction):
        if interaction.guild_id is None:
            return
        await interaction.response.send_message(content="Fetching the manage tickets menu...")
        ticket_info = await GuildConfigService.reload_tickets(interaction.guild_id)
        view = ManageCategoriesView(ticket_info, interaction.guild_id)
        await view.update_embed(interaction)
        await interaction.edit_original_response(view=view)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(ManageTickets(client))
