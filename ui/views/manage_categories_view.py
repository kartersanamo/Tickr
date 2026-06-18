from typing import Any

import discord

from core.loggers import log_commands
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color
from services.ticket_types_store import load_raw, reload_tickets, save_raw


class ManageCategoriesView(discord.ui.View):
    def __init__(self, ticket_info, guild_id: int) -> None:
        super().__init__(timeout=None)
        self.ticket_info = ticket_info
        self.guild_id = guild_id
        from ui.views.manage_categories_select_view import ManageCategoriesSelect

        self.add_item(ManageCategoriesSelect(self.ticket_info, guild_id))

    async def update_embed(self, interaction: discord.Interaction):
        try:
            if interaction.guild_id is None:
                return
            self.ticket_info = await reload_tickets(interaction.guild_id)
            cfg = await GuildConfigService.for_guild(interaction.guild_id)
            main_menu_embed = discord.Embed(
                title="Main Menu",
                color=embed_color(cfg),
                description="Select Category",
            )
            for ticket_cat in list(self.ticket_info.keys()):
                if ticket_cat == "TOGGLE_STATUS":
                    continue
                val = ""
                for ticket_type in list(self.ticket_info.get(ticket_cat, {}).keys()):
                    val += f"\t `»` {ticket_type}\n"
                main_menu_embed.add_field(name=ticket_cat, value=val or "—")
            await interaction.edit_original_response(embed=main_menu_embed, content=None)
        except Exception as exc:
            log_commands.error(f"Failed to update the embed {exc}")

    @discord.ui.button(
        label="Toggle All Tickets",
        style=discord.ButtonStyle.red,
        custom_id="toggle_all_tickets",
        row=0,
    )
    async def toggle_all_tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer()
            if interaction.guild_id is None:
                return
            data = await load_raw(interaction.guild_id)
            data["TOGGLE_STATUS"] = "Disabled" if data.get("TOGGLE_STATUS") == "Enabled" else "Enabled"
            await save_raw(interaction.guild_id, data)
            log_commands.info(
                f"{interaction.user} toggled all tickets to {data['TOGGLE_STATUS']}"
            )
            await interaction.followup.send(
                content=f"`✅` Successfully toggled all tickets to `{data['TOGGLE_STATUS']}`",
                ephemeral=True,
            )
        except Exception as exc:
            log_commands.error(f"Failed to toggle all tickets: {exc}")
