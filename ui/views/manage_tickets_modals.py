"""Modals for /manage-tickets CRUD actions."""
from __future__ import annotations

import discord

from services.guild_config_service import GuildConfigService
from services.manage_tickets_auth import require_ticket_editor
from services.ticket_types_editor import (
    add_category,
    add_question,
    add_ticket_type,
    duplicate_ticket_type,
    new_question,
    new_ticket_type,
    rename_category,
    rename_ticket_type,
)
from services.ticket_types_store import load_raw, save_raw


async def _save_and_refresh_categories(interaction: discord.Interaction, guild_id: int, data: dict) -> None:
    await save_raw(guild_id, data)
    from ui.views.manage_categories_view import ManageCategoriesView

    view = ManageCategoriesView(data, guild_id)
    await view.update_embed(interaction)
    if interaction.message is not None:
        await interaction.message.edit(view=view)


async def _save_and_refresh_types(
    interaction: discord.Interaction,
    guild_id: int,
    data: dict,
    category: str,
    *,
    type_name: str | None = None,
) -> None:
    await save_raw(guild_id, data)
    from ui.views.manage_tickets_view import ManageTicketsView
    from ui.views.manage_type_view import ManageTypeView

    if type_name:
        view = ManageTypeView(data, category, type_name)
        await view.update_embed(interaction)
    else:
        view = ManageTicketsView(data, category)
        await view.update_embed(interaction)
    if interaction.message is not None:
        await interaction.message.edit(view=view)


class AddCategoryModal(discord.ui.Modal, title="Add Panel Category"):
    name_input = discord.ui.TextInput(
        label="Category name",
        placeholder="Support",
        max_length=80,
        required=True,
    )

    def __init__(self, guild_id: int) -> None:
        super().__init__()
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.defer()
        try:
            data = await load_raw(self.guild_id)
            name = self.name_input.value.strip()
            data = add_category(data, name)
            await _save_and_refresh_categories(interaction, self.guild_id, data)
            await interaction.followup.send(f"`✅` Added panel category **{name}**.", ephemeral=True)
        except ValueError as exc:
            await interaction.followup.send(f"`❌` {exc}", ephemeral=True)


class RenameCategoryModal(discord.ui.Modal, title="Rename Panel Category"):
    name_input = discord.ui.TextInput(label="New category name", max_length=80, required=True)

    def __init__(self, guild_id: int, category: str) -> None:
        super().__init__()
        self.guild_id = guild_id
        self.category = category
        self.name_input.default = category

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.defer()
        try:
            data = await load_raw(self.guild_id)
            new_name = self.name_input.value.strip()
            data = rename_category(data, self.category, new_name)
            await _save_and_refresh_categories(interaction, self.guild_id, data)
            await interaction.followup.send(
                f"`✅` Renamed **{self.category}** → **{new_name}**.",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.followup.send(f"`❌` {exc}", ephemeral=True)


class AddTicketTypeModal(discord.ui.Modal, title="Add Ticket Type"):
    name_input = discord.ui.TextInput(label="Type name", max_length=80, required=True)
    description_input = discord.ui.TextInput(
        label="Description",
        placeholder="Shown in the ticket dropdown",
        max_length=100,
        required=True,
    )
    emoji_input = discord.ui.TextInput(label="Emoji", default="🎫", max_length=8, required=False)

    def __init__(self, guild_id: int, category: str) -> None:
        super().__init__()
        self.guild_id = guild_id
        self.category = category

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.defer()
        try:
            cfg = await GuildConfigService.for_guild(self.guild_id)
            cats = cfg.get("TICKET_CATEGORIES", []) or []
            staff = cfg.get("ROLE_IDS.STAFF_TEAM_ROLE_ID")
            template = new_ticket_type(
                description=self.description_input.value.strip(),
                emoji=self.emoji_input.value.strip() or "🎫",
                category_id=int(cats[0]) if cats else None,
                staff_role_id=int(staff) if staff else None,
            )
            data = await load_raw(self.guild_id)
            type_name = self.name_input.value.strip()
            data = add_ticket_type(data, self.category, type_name, template=template)
            await _save_and_refresh_types(interaction, self.guild_id, data, self.category)
            await interaction.followup.send(
                f"`✅` Added ticket type **{type_name}** to **{self.category}**.",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.followup.send(f"`❌` {exc}", ephemeral=True)


class DuplicateTicketTypeModal(discord.ui.Modal, title="Duplicate Ticket Type"):
    name_input = discord.ui.TextInput(label="New type name", max_length=80, required=True)

    def __init__(self, guild_id: int, category: str, source_type: str) -> None:
        super().__init__()
        self.guild_id = guild_id
        self.category = category
        self.source_type = source_type
        self.name_input.default = f"{source_type} Copy"[:80]

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.defer()
        try:
            data = await load_raw(self.guild_id)
            new_name = self.name_input.value.strip()
            data = duplicate_ticket_type(data, self.category, self.source_type, new_name)
            await _save_and_refresh_types(interaction, self.guild_id, data, self.category)
            await interaction.followup.send(
                f"`✅` Duplicated **{self.source_type}** as **{new_name}**.",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.followup.send(f"`❌` {exc}", ephemeral=True)


class RenameTicketTypeModal(discord.ui.Modal, title="Rename Ticket Type"):
    name_input = discord.ui.TextInput(label="New type name", max_length=80, required=True)

    def __init__(self, guild_id: int, category: str, type_name: str) -> None:
        super().__init__()
        self.guild_id = guild_id
        self.category = category
        self.type_name = type_name
        self.name_input.default = type_name

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.defer()
        try:
            data = await load_raw(self.guild_id)
            new_name = self.name_input.value.strip()
            data = rename_ticket_type(data, self.category, self.type_name, new_name)
            await _save_and_refresh_types(
                interaction, self.guild_id, data, self.category, type_name=new_name
            )
            await interaction.followup.send(
                f"`✅` Renamed **{self.type_name}** → **{new_name}**.",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.followup.send(f"`❌` {exc}", ephemeral=True)


class AddQuestionModal(discord.ui.Modal, title="Add Question"):
    label_input = discord.ui.TextInput(label="Question label", max_length=45, required=True)
    placeholder_input = discord.ui.TextInput(
        label="Placeholder",
        max_length=100,
        required=False,
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, guild_id: int, category: str, type_name: str) -> None:
        super().__init__()
        self.guild_id = guild_id
        self.category = category
        self.type_name = type_name

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not await require_ticket_editor(interaction):
            return
        await interaction.response.defer()
        try:
            question = new_question(
                label=self.label_input.value.strip(),
                placeholder=self.placeholder_input.value.strip(),
                length="Long",
            )
            data = await load_raw(self.guild_id)
            data = add_question(data, self.category, self.type_name, question)
            await _save_and_refresh_types(
                interaction, self.guild_id, data, self.category, type_name=self.type_name
            )
            await interaction.followup.send(
                f"`✅` Added question **{question['Label']}**.",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.followup.send(f"`❌` {exc}", ephemeral=True)
