from typing import Any
import discord

from core.loggers import log_commands
class ManageCategoriesSelect(discord.ui.Select):
    def __init__(self, ticket_info, guild_id: int) -> None:
        self.ticket_info = ticket_info
        self.guild_id = guild_id
        labels = [
            category_name
            for category_name in ticket_info.keys()
            if category_name != "TOGGLE_STATUS"
        ]
        options = [discord.SelectOption(label=label) for label in labels[:25]]
        super().__init__(placeholder="Select a ticket category to manage...", options=options)
    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            from ui.views.manage_tickets_view import ManageTicketsView

            category = self.values[0]
            await interaction.response.defer()
            view = ManageTicketsView(self.ticket_info, category)
            await view.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(view = view)
        except Exception as e:
            log_commands.error(f"{interaction.user} ({interaction.user.id}) has failed to select a ticket category {e}")
