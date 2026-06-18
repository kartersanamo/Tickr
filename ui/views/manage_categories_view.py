import discord

from core.loggers import log_commands
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color
from services.manage_tickets_auth import require_ticket_editor
from services.ticket_types_editor import category_names, remove_category, ticket_type_names
from services.ticket_types_store import load_raw, reload_tickets, save_raw
from ui.views.manage_tickets_modals import AddCategoryModal, RenameCategoryModal


class ManageCategoriesSelect(discord.ui.Select):
    def __init__(self, ticket_info: dict, guild_id: int) -> None:
        self.ticket_info = ticket_info
        self.guild_id = guild_id
        labels = category_names(ticket_info)
        options = [discord.SelectOption(label=label) for label in labels[:25]]
        super().__init__(
            placeholder="Select a panel category to manage...",
            options=options,
            custom_id="manage_categories_pick",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            from ui.views.manage_tickets_view import ManageTicketsView

            category = self.values[0]
            await interaction.response.defer()
            data = await reload_tickets(self.guild_id)
            view = ManageTicketsView(data, category, self.guild_id)
            await view.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(view=view)
        except Exception as exc:
            log_commands.error(f"Failed to select ticket category: {exc}")


class RemoveCategorySelect(discord.ui.Select):
    def __init__(self, ticket_info: dict, guild_id: int) -> None:
        self.guild_id = guild_id
        labels = category_names(ticket_info)
        options = [
            discord.SelectOption(label=label, description="Delete this panel category", emoji="🗑️")
            for label in labels[:25]
        ]
        super().__init__(
            placeholder="Remove a panel category...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="manage_categories_remove",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        category = self.values[0]
        await interaction.response.edit_message(
            content=f"Delete panel category **{category}** and all ticket types inside it?",
            embed=None,
            view=ConfirmDeleteCategoryView(self.guild_id, category),
        )


class ConfirmDeleteCategoryView(discord.ui.View):
    def __init__(self, guild_id: int, category: str) -> None:
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.category = category

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.defer()
        try:
            data = await load_raw(self.guild_id)
            data = remove_category(data, self.category)
            await save_raw(self.guild_id, data)
            view = ManageCategoriesView(data, self.guild_id)
            await view.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(content=None, view=view)
            await interaction.followup.send(
                f"`✅` Removed panel category **{self.category}**.",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.followup.send(f"`❌` {exc}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        data = await reload_tickets(self.guild_id)
        view = ManageCategoriesView(data, self.guild_id)
        await view.update_embed(interaction)
        if interaction.message is not None:
            await interaction.message.edit(content=None, view=view)


class RenameCategorySelect(discord.ui.Select):
    def __init__(self, ticket_info: dict, guild_id: int) -> None:
        self.guild_id = guild_id
        labels = category_names(ticket_info)
        options = [discord.SelectOption(label=label, emoji="✏️") for label in labels[:25]]
        super().__init__(
            placeholder="Rename a panel category...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="manage_categories_rename",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.send_modal(
            RenameCategoryModal(self.guild_id, self.values[0])
        )


class ManageCategoriesView(discord.ui.View):
    def __init__(self, ticket_info: dict, guild_id: int) -> None:
        super().__init__(timeout=None)
        self.ticket_info = ticket_info
        self.guild_id = guild_id
        if category_names(ticket_info):
            self.add_item(ManageCategoriesSelect(ticket_info, guild_id))
            self.add_item(RenameCategorySelect(ticket_info, guild_id))
            self.add_item(RemoveCategorySelect(ticket_info, guild_id))

    async def update_embed(self, interaction: discord.Interaction) -> None:
        try:
            if interaction.guild_id is None:
                return
            self.ticket_info = await reload_tickets(interaction.guild_id)
            cfg = await GuildConfigService.for_guild(interaction.guild_id)
            global_status = self.ticket_info.get("TOGGLE_STATUS", "Enabled")
            names = category_names(self.ticket_info)
            main_menu_embed = discord.Embed(
                title="Ticket Type Manager",
                color=embed_color(cfg),
                description=(
                    f"**Global tickets:** `{global_status}`\n"
                    f"**Panel categories:** {len(names)}\n\n"
                    "Panel categories are the dropdown menus on your ticket panel. "
                    "Each category contains ticket types.\n\n"
                    "Use the menus and buttons below to add, remove, or edit everything."
                ),
            )
            if not names:
                main_menu_embed.add_field(
                    name="No categories yet",
                    value="Press **Add Category** to create your first panel category.",
                    inline=False,
                )
            else:
                for ticket_cat in names:
                    types = ticket_type_names(self.ticket_info, ticket_cat)
                    val = "\n".join(f"• {ticket_type}" for ticket_type in types) or "*(no ticket types yet)*"
                    main_menu_embed.add_field(name=ticket_cat, value=val[:1024], inline=False)
            await interaction.edit_original_response(embed=main_menu_embed, content=None)
        except Exception as exc:
            log_commands.error(f"Failed to update manage categories embed: {exc}")

    @discord.ui.button(
        label="Add Category",
        style=discord.ButtonStyle.green,
        custom_id="manage_add_category",
        row=3,
    )
    async def add_category(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.send_modal(AddCategoryModal(self.guild_id))

    @discord.ui.button(
        label="Toggle All Tickets",
        style=discord.ButtonStyle.red,
        custom_id="toggle_all_tickets",
        row=3,
    )
    async def toggle_all_tickets(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        try:
            if not await require_ticket_editor(interaction):
                return
            await interaction.response.defer()
            if interaction.guild_id is None:
                return
            data = await load_raw(interaction.guild_id)
            data["TOGGLE_STATUS"] = "Disabled" if data.get("TOGGLE_STATUS") == "Enabled" else "Enabled"
            await save_raw(interaction.guild_id, data)
            self.ticket_info = data
            await self.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(view=self)
            log_commands.info(f"{interaction.user} toggled all tickets to {data['TOGGLE_STATUS']}")
            await interaction.followup.send(
                content=f"`✅` Globally toggled tickets to `{data['TOGGLE_STATUS']}`.",
                ephemeral=True,
            )
        except Exception as exc:
            log_commands.error(f"Failed to toggle all tickets: {exc}")
