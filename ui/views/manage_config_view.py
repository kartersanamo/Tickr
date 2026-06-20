"""In-Discord guild configuration editor for /manage-config."""

from __future__ import annotations

import json
from typing import Any

import discord

from services.guild_config_fields import (
    CONFIG_CATEGORIES,
    FIELDS_BY_CATEGORY,
    FIELDS_BY_KEY,
    ConfigField,
    format_field_value,
    get_config_value,
    merge_defaults,
    validate_required,
)
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color, normalize_embed_color, set_embed_footer


async def _load_context(guild_id: int) -> tuple[dict, bool]:
    cfg = await GuildConfigService.for_guild(guild_id)
    return cfg.all(), cfg.tickets_global_enabled


def build_home_embed(
    guild: discord.Guild,
    config: dict,
    *,
    tickets_global_enabled: bool,
) -> discord.Embed:
    merged = merge_defaults(config)
    missing = validate_required(merged)
    embed = discord.Embed(
        title="Tickr Server Configuration",
        description=(
            "Browse and edit every Tickr setting for this server.\n"
            "Pick a **category** below to view and change values."
        ),
        color=embed_color(merged),
    )
    if missing:
        embed.add_field(
            name="Missing required settings",
            value="\n".join(f"• {label}" for label in missing),
            inline=False,
        )
    else:
        embed.add_field(name="Required settings", value="`All set`", inline=False)

    lines: list[str] = []
    for cat_key, cat_label in CONFIG_CATEGORIES.items():
        fields = FIELDS_BY_CATEGORY.get(cat_key, [])
        unset = 0
        for field in fields:
            if field.required:
                continue
            value = get_config_value(merged, field.path)
            if value in (None, "", []):
                unset += 1
        lines.append(f"**{cat_label}** — {len(fields)} setting(s)")
    embed.add_field(name="Categories", value="\n".join(lines) or "—", inline=False)
    embed.add_field(
        name="Tickets master switch",
        value="`Enabled`" if tickets_global_enabled else "`Disabled`",
        inline=True,
    )
    embed.add_field(
        name="Configured",
        value="`Yes`" if not missing else "`Incomplete`",
        inline=True,
    )
    set_embed_footer(embed, merged)
    return embed


def build_category_embed(
    guild: discord.Guild,
    category: str,
    config: dict,
    *,
    tickets_global_enabled: bool,
) -> discord.Embed:
    merged = merge_defaults(config)
    cat_label = CONFIG_CATEGORIES.get(category, category.title())
    embed = discord.Embed(
        title=f"Config — {cat_label}",
        description="Select a setting below to edit it.",
        color=embed_color(merged),
    )
    for field in FIELDS_BY_CATEGORY.get(category, []):
        value_text = format_field_value(
            guild,
            field,
            merged,
            tickets_global_enabled=tickets_global_enabled,
        )
        req = " *(required)*" if field.required else ""
        embed.add_field(
            name=f"{field.label}{req}",
            value=f"{field.description}\n\n**Current:** {value_text}"[:1024],
            inline=False,
        )
    set_embed_footer(embed, merged)
    return embed


class ManageConfigView(discord.ui.View):
    def __init__(self, guild_id: int, *, timeout: float = 900) -> None:
        super().__init__(timeout=timeout)
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            not getattr(interaction.user, "guild_permissions", None)
            or not interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                "Administrator permission required.",
                ephemeral=True,
            )
            return False
        return True


class ConfigCategorySelect(discord.ui.Select):
    def __init__(self, guild_id: int) -> None:
        self.guild_id = guild_id
        options = [
            discord.SelectOption(
                label=label, value=key, description=f"Edit {label.lower()}"
            )
            for key, label in CONFIG_CATEGORIES.items()
        ]
        super().__init__(
            placeholder="Choose a config category...",
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id="manage_config_category",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        category = self.values[0]
        config, enabled = await _load_context(self.guild_id)
        embed = build_category_embed(
            interaction.guild,
            category,
            config,
            tickets_global_enabled=enabled,
        )
        view = ManageConfigCategoryView(self.guild_id, category)
        await interaction.response.edit_message(embed=embed, view=view)


class ManageConfigHomeView(ManageConfigView):
    def __init__(self, guild_id: int) -> None:
        super().__init__(guild_id)
        self.add_item(ConfigCategorySelect(guild_id))


class ConfigFieldSelect(discord.ui.Select):
    def __init__(self, guild_id: int, category: str) -> None:
        self.guild_id = guild_id
        self.category = category
        fields = FIELDS_BY_CATEGORY.get(category, [])
        options = [
            discord.SelectOption(
                label=field.label, value=field.key, description=field.description[:100]
            )
            for field in fields[:25]
        ]
        super().__init__(
            placeholder="Choose a setting to edit...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"manage_config_field_{category}",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        field = FIELDS_BY_KEY[self.values[0]]
        config, enabled = await _load_context(self.guild_id)
        merged = merge_defaults(config)
        current = get_config_value(merged, field.path)
        view = ManageConfigFieldView(
            self.guild_id,
            self.category,
            field,
            current=current,
            tickets_global_enabled=enabled,
        )
        embed = discord.Embed(
            title=f"Edit — {field.label}",
            description=(
                f"{field.description}\n\nUse the controls below to update this value."
            ),
            color=embed_color(merged),
        )
        await interaction.response.edit_message(embed=embed, view=view)


class BackToCategoriesButton(discord.ui.Button):
    def __init__(self, guild_id: int) -> None:
        super().__init__(
            label="Back to Categories", style=discord.ButtonStyle.secondary, row=4
        )
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        config, enabled = await _load_context(self.guild_id)
        embed = build_home_embed(
            interaction.guild,
            config,
            tickets_global_enabled=enabled,
        )
        await interaction.response.edit_message(
            embed=embed, view=ManageConfigHomeView(self.guild_id)
        )


class BackToCategoryButton(discord.ui.Button):
    def __init__(self, guild_id: int, category: str) -> None:
        super().__init__(
            label="Back to Category", style=discord.ButtonStyle.secondary, row=4
        )
        self.guild_id = guild_id
        self.category = category

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        config, enabled = await _load_context(self.guild_id)
        embed = build_category_embed(
            interaction.guild,
            self.category,
            config,
            tickets_global_enabled=enabled,
        )
        await interaction.response.edit_message(
            embed=embed, view=ManageConfigCategoryView(self.guild_id, self.category)
        )


class ManageConfigCategoryView(ManageConfigView):
    def __init__(self, guild_id: int, category: str) -> None:
        super().__init__(guild_id)
        self.category = category
        if FIELDS_BY_CATEGORY.get(category):
            self.add_item(ConfigFieldSelect(guild_id, category))
        self.add_item(BackToCategoriesButton(guild_id))


class ClearFieldButton(discord.ui.Button):
    def __init__(self, guild_id: int, category: str, field: ConfigField) -> None:
        super().__init__(label="Clear Value", style=discord.ButtonStyle.danger, row=3)
        self.guild_id = guild_id
        self.category = category
        self.field = field

    async def callback(self, interaction: discord.Interaction) -> None:
        await _save_field(interaction, self.guild_id, self.category, self.field, None)


class ToggleTicketsButton(discord.ui.Button):
    def __init__(
        self, guild_id: int, category: str, field: ConfigField, enabled: bool
    ) -> None:
        label = "Disable Tickets" if enabled else "Enable Tickets"
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=0)
        self.guild_id = guild_id
        self.category = category
        self.field = field
        self.enabled = enabled

    async def callback(self, interaction: discord.Interaction) -> None:
        await GuildConfigService.set_tickets_global_enabled(
            self.guild_id, not self.enabled
        )
        await _refresh_field_view(
            interaction, self.guild_id, self.category, self.field, saved=True
        )


class OpenTextModalButton(discord.ui.Button):
    def __init__(
        self, guild_id: int, category: str, field: ConfigField, current: Any
    ) -> None:
        super().__init__(label="Edit Value", style=discord.ButtonStyle.primary, row=0)
        self.guild_id = guild_id
        self.category = category
        self.field = field
        self.current = current

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(
            ConfigTextModal(self.guild_id, self.category, self.field, self.current)
        )


async def _save_field(
    interaction: discord.Interaction,
    guild_id: int,
    category: str,
    field: ConfigField,
    value: Any,
) -> None:
    if field.field_type in ("role_list", "category_list"):
        await GuildConfigService.patch_config(guild_id, field.path, value or [])
    elif field.field_type == "integer":
        await GuildConfigService.patch_config(
            guild_id,
            field.path,
            int(value) if value is not None else 0,
        )
    elif field.field_type == "json":
        await GuildConfigService.patch_config(guild_id, field.path, value or {})
    elif field.field_type == "color" and value:
        await GuildConfigService.patch_config(
            guild_id,
            field.path,
            normalize_embed_color(str(value)),
        )
    elif field.field_type == "color" and value is None:
        from services.guild_config_fields import DEFAULT_EMBED_COLOR

        await GuildConfigService.patch_config(guild_id, field.path, DEFAULT_EMBED_COLOR)
    else:
        await GuildConfigService.patch_config(guild_id, field.path, value)

    merged = merge_defaults((await GuildConfigService.for_guild(guild_id)).all())
    missing = validate_required(merged)
    if not missing:
        await GuildConfigService.set_configured(guild_id, True)

    if interaction.response.is_done():
        await _refresh_field_view(interaction, guild_id, category, field, saved=True)
    else:
        await interaction.response.defer()
        await _refresh_field_view(interaction, guild_id, category, field, saved=True)


async def _refresh_field_view(
    interaction: discord.Interaction,
    guild_id: int,
    category: str,
    field: ConfigField,
    *,
    saved: bool = False,
) -> None:
    if interaction.guild is None:
        return
    config, enabled = await _load_context(guild_id)
    merged = merge_defaults(config)
    current = get_config_value(merged, field.path)
    current_display = format_field_value(
        interaction.guild,
        field,
        merged,
        tickets_global_enabled=enabled,
    )
    description = f"{field.description}\n\n**Current:** {current_display}"
    if saved:
        description = f"`Saved.`\n\n{description}"
    embed = discord.Embed(
        title=f"Edit — {field.label}",
        description=description,
        color=embed_color(merged),
    )
    view = ManageConfigFieldView(
        guild_id,
        category,
        field,
        current=current,
        tickets_global_enabled=enabled,
    )
    if interaction.response.is_done():
        await interaction.edit_original_response(embed=embed, view=view)
    else:
        await interaction.response.edit_message(embed=embed, view=view)


class ConfigTextModal(discord.ui.Modal):
    def __init__(
        self, guild_id: int, category: str, field: ConfigField, current: Any
    ) -> None:
        super().__init__(title=field.label[:45])
        self.guild_id = guild_id
        self.category = category
        self.field = field
        default = ""
        if field.field_type == "json" and current:
            default = json.dumps(current, indent=2)
        elif current not in (None, "", []):
            default = str(current)
        self.value_input = discord.ui.TextInput(
            label=field.label[:45],
            default=default[:4000] if default else None,
            required=field.required,
            style=discord.TextStyle.paragraph
            if field.field_type in ("json", "url")
            else discord.TextStyle.short,
            max_length=4000 if field.field_type == "json" else 512,
        )
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if (
            not getattr(interaction.user, "guild_permissions", None)
            or not interaction.user.guild_permissions.administrator
        ):
            await interaction.response.send_message(
                "Administrator permission required.",
                ephemeral=True,
            )
            return
        raw = self.value_input.value.strip()
        value: Any = raw or None
        if self.field.field_type == "integer":
            try:
                value = int(raw)
            except ValueError:
                await interaction.response.send_message(
                    "Enter a whole number.", ephemeral=True
                )
                return
        elif self.field.field_type == "json":
            try:
                value = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                await interaction.response.send_message("Invalid JSON.", ephemeral=True)
                return
        await interaction.response.defer()
        await _save_field(interaction, self.guild_id, self.category, self.field, value)


def _role_select(
    field: ConfigField, guild_id: int, category: str
) -> discord.ui.RoleSelect:
    class _Select(discord.ui.RoleSelect):
        def __init__(self) -> None:
            super().__init__(
                placeholder=f"Select {field.label.lower()}...",
                min_values=0 if not field.required else 1,
                max_values=25 if field.field_type == "role_list" else 1,
            )
            self.guild_id = guild_id
            self.category = category
            self.field = field

        async def callback(self, interaction: discord.Interaction) -> None:
            if self.field.field_type == "role_list":
                value = [role.id for role in self.values]
            elif self.values:
                value = self.values[0].id
            else:
                value = None
            await _save_field(
                interaction, self.guild_id, self.category, self.field, value
            )

    return _Select()


def _channel_select(
    field: ConfigField, guild_id: int, category: str
) -> discord.ui.ChannelSelect:
    if field.field_type == "channel_category" or field.field_type == "category_list":
        channel_types = [discord.ChannelType.category]
        max_values = 25 if field.field_type == "category_list" else 1
    elif field.field_type == "channel_voice":
        channel_types = [discord.ChannelType.voice]
        max_values = 1
    else:
        channel_types = [discord.ChannelType.text, discord.ChannelType.news]
        max_values = 1

    class _Select(discord.ui.ChannelSelect):
        def __init__(self) -> None:
            super().__init__(
                placeholder=f"Select {field.label.lower()}...",
                channel_types=channel_types,
                min_values=0 if not field.required else 1,
                max_values=max_values,
            )
            self.guild_id = guild_id
            self.category = category
            self.field = field

        async def callback(self, interaction: discord.Interaction) -> None:
            if self.field.field_type == "category_list":
                value = [channel.id for channel in self.values]
            elif self.values:
                value = self.values[0].id
            else:
                value = None
            await _save_field(
                interaction, self.guild_id, self.category, self.field, value
            )

    return _Select()


class ManageConfigFieldView(ManageConfigView):
    def __init__(
        self,
        guild_id: int,
        category: str,
        field: ConfigField,
        *,
        current: Any = None,
        tickets_global_enabled: bool = True,
    ) -> None:
        super().__init__(guild_id)
        self.category = category
        self.field = field

        if field.field_type == "toggle":
            self.add_item(
                ToggleTicketsButton(guild_id, category, field, tickets_global_enabled)
            )
        elif field.field_type in ("role", "role_list"):
            self.add_item(_role_select(field, guild_id, category))
            if not field.required:
                self.add_item(ClearFieldButton(guild_id, category, field))
        elif field.field_type in (
            "channel_text",
            "channel_category",
            "channel_voice",
            "category_list",
        ):
            self.add_item(_channel_select(field, guild_id, category))
            if not field.required:
                self.add_item(ClearFieldButton(guild_id, category, field))
        else:
            self.add_item(OpenTextModalButton(guild_id, category, field, current))
            if not field.required:
                self.add_item(ClearFieldButton(guild_id, category, field))

        self.add_item(BackToCategoryButton(guild_id, category))
        self.add_item(BackToCategoriesButton(guild_id))


async def open_manage_config(interaction: discord.Interaction, guild_id: int) -> None:
    if interaction.guild is None:
        return
    config, enabled = await _load_context(guild_id)
    embed = build_home_embed(
        interaction.guild,
        config,
        tickets_global_enabled=enabled,
    )
    await interaction.response.send_message(
        embed=embed,
        view=ManageConfigHomeView(guild_id),
    )
