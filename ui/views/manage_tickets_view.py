import discord

from core.loggers import log_commands
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color
from services.manage_tickets_auth import require_ticket_editor
from services.ticket_types_editor import remove_ticket_type, ticket_type_names
from services.ticket_types_store import load_raw, reload_tickets, save_raw
from ui.views.manage_tickets_modals import AddTicketTypeModal, DuplicateTicketTypeModal
from ui.views.manage_tickets_support import ManageTicketsSupport


class ManageTicketsSelect(discord.ui.Select):
    def __init__(self, ticket_info: dict, ticket_category: str) -> None:
        self.ticket_info = ticket_info
        self.ticket_category = ticket_category
        labels = ticket_type_names(ticket_info, ticket_category)
        options = [discord.SelectOption(label=label) for label in labels[:25]]
        super().__init__(
            placeholder="Select a ticket type to manage...",
            options=options,
            custom_id="manage_ticket_type_pick",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            from ui.views.manage_type_view import ManageTypeView

            ticket = self.values[0]
            await interaction.response.defer()
            data = await reload_tickets(interaction.guild_id or 0)
            view = ManageTypeView(data, self.ticket_category, ticket)
            await view.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(view=view)
        except Exception as exc:
            log_commands.error(f"Failed to select ticket type: {exc}")


class RemoveTicketTypeSelect(discord.ui.Select):
    def __init__(self, ticket_info: dict, category: str, guild_id: int) -> None:
        self.category = category
        self.guild_id = guild_id
        labels = ticket_type_names(ticket_info, category)
        options = [
            discord.SelectOption(
                label=label, description="Delete this ticket type", emoji="🗑️"
            )
            for label in labels[:25]
        ]
        super().__init__(
            placeholder="Remove a ticket type...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="manage_ticket_type_remove",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        type_name = self.values[0]
        await interaction.response.edit_message(
            content=f"Delete ticket type **{type_name}** from **{self.category}**?",
            embed=None,
            view=ConfirmDeleteTicketTypeView(self.guild_id, self.category, type_name),
        )


class DuplicateTicketTypeSelect(discord.ui.Select):
    def __init__(self, ticket_info: dict, category: str, guild_id: int) -> None:
        self.category = category
        self.guild_id = guild_id
        labels = ticket_type_names(ticket_info, category)
        options = [
            discord.SelectOption(label=label, emoji="📋") for label in labels[:25]
        ]
        super().__init__(
            placeholder="Duplicate a ticket type...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="manage_ticket_type_duplicate",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.send_modal(
            DuplicateTicketTypeModal(self.guild_id, self.category, self.values[0])
        )


class ConfirmDeleteTicketTypeView(discord.ui.View):
    def __init__(self, guild_id: int, category: str, type_name: str) -> None:
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.category = category
        self.type_name = type_name

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.defer()
        try:
            data = await load_raw(self.guild_id)
            data = remove_ticket_type(data, self.category, self.type_name)
            await save_raw(self.guild_id, data)
            view = ManageTicketsView(data, self.category, self.guild_id)
            await view.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(content=None, view=view)
            await ManageTicketsSupport.update_msg(interaction)
            await interaction.followup.send(
                f"`✅` Removed ticket type **{self.type_name}**.",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.followup.send(f"`❌` {exc}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.defer()
        data = await reload_tickets(self.guild_id)
        view = ManageTicketsView(data, self.category, self.guild_id)
        await view.update_embed(interaction)
        if interaction.message is not None:
            await interaction.message.edit(content=None, view=view)


class ManageTicketsView(discord.ui.View):
    def __init__(self, ticket_info: dict, category: str, guild_id: int) -> None:
        super().__init__(timeout=None)
        self.ticket_info = ticket_info
        self.category = category
        self.guild_id = guild_id
        self.status_to_emoji = {"Enabled": "✅", "Disabled": "❌"}
        types = ticket_type_names(ticket_info, category)
        if types:
            self.add_item(ManageTicketsSelect(ticket_info, category))
            self.add_item(DuplicateTicketTypeSelect(ticket_info, category, guild_id))
            self.add_item(RemoveTicketTypeSelect(ticket_info, category, guild_id))

    async def update_embed(self, interaction: discord.Interaction) -> None:
        try:
            self.ticket_info = await reload_tickets(
                interaction.guild_id or self.guild_id
            )
            category_info = self.ticket_info.get(self.category, {})
            cfg = await GuildConfigService.for_guild(
                interaction.guild_id or self.guild_id
            )
            category_embed = discord.Embed(
                title="Category Editor",
                color=embed_color(cfg),
                description=(
                    f"**Panel category:** {self.category}\n\n"
                    "Ticket types appear as options inside this dropdown on the ticket panel."
                ),
            )
            types = ticket_type_names(self.ticket_info, self.category)
            if not types:
                category_embed.add_field(
                    name="No ticket types",
                    value="Press **Add Type** to create one.",
                    inline=False,
                )
            for ticket_type in types:
                ticket_info = category_info.get(ticket_type, {})
                category_embed.add_field(
                    name=f"{self.status_to_emoji.get(ticket_info.get('Status'), '❔')} {ticket_type}",
                    value=f"» {ticket_info.get('Description', '—')}\n» Status: {ticket_info.get('Status', '—')}",
                    inline=False,
                )
            await interaction.edit_original_response(embed=category_embed, content=None)
        except Exception as exc:
            log_commands.error(f"Failed to update category embed: {exc}")

    @discord.ui.button(
        label="|<", style=discord.ButtonStyle.red, custom_id="go_back_category", row=4
    )
    async def go_back_category(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            from ui.views.manage_categories_view import ManageCategoriesView

            await interaction.response.defer()
            data = await reload_tickets(self.guild_id)
            view = ManageCategoriesView(data, self.guild_id)
            await view.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(view=view)
        except Exception as exc:
            log_commands.error(f"Failed to go back to categories: {exc}")

    @discord.ui.button(
        label="Add Type",
        style=discord.ButtonStyle.green,
        custom_id="manage_add_type",
        row=4,
    )
    async def add_type(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.send_modal(
            AddTicketTypeModal(self.guild_id, self.category)
        )

    @discord.ui.button(
        label="Toggle Category",
        style=discord.ButtonStyle.grey,
        custom_id="toggle_category",
        row=4,
    )
    async def toggle_category(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            if not await require_ticket_editor(interaction):
                return
            await interaction.response.defer()
            info = await load_raw(self.guild_id)
            output = "Toggled ticket types in this category:\n"
            for ticket_type in ticket_type_names(info, self.category):
                status = info[self.category][ticket_type]["Status"]
                new_status = "Enabled" if status == "Disabled" else "Disabled"
                info[self.category][ticket_type]["Status"] = new_status
                output += f"\n`{self.status_to_emoji.get(new_status)}` **{ticket_type}** → {new_status}"
            await save_raw(self.guild_id, info)
            self.ticket_info = info
            view = ManageTicketsView(info, self.category, self.guild_id)
            await view.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(view=view)
            await interaction.followup.send(content=output, ephemeral=True)
            await ManageTicketsSupport.update_msg(interaction)
        except Exception as exc:
            log_commands.error(f"Failed to toggle category: {exc}")
