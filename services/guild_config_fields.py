"""Guild config field schema and helpers for setup / manage-config."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Literal

import discord

FieldType = Literal[
    "role",
    "channel_text",
    "channel_category",
    "channel_voice",
    "string",
    "url",
    "color",
    "role_list",
    "category_list",
    "integer",
    "json",
    "toggle",
    "dashboard_url",
    "dashboard_secret",
]


@dataclass(frozen=True)
class ConfigField:
    key: str
    path: str
    label: str
    description: str
    field_type: FieldType
    required: bool = False
    setup: bool = False
    category: str = "general"


CONFIG_CATEGORIES: dict[str, str] = {
    "core": "Core (Required)",
    "channels": "Channels",
    "roles": "Roles & Permissions",
    "tickets": "Ticket Categories",
    "branding": "Branding",
    "integrations": "Integrations",
    "system": "System",
    "advanced": "Advanced",
}

CONFIG_FIELDS: tuple[ConfigField, ...] = (
    ConfigField(
        "staff_role",
        "ROLE_IDS.STAFF_TEAM_ROLE_ID",
        "Staff Team Role",
        "Role that can manage tickets and gets pinged on new tickets.",
        "role",
        required=True,
        setup=True,
        category="core",
    ),
    ConfigField(
        "admin_perms_role",
        "ROLE_IDS.ADMINISTRATOR_PERMS_ROLE_ID",
        "Administrator Perms Role",
        "Role required to use `/manage-tickets`, `/manage-config`, and ticket editors.",
        "role",
        required=True,
        setup=True,
        category="core",
    ),
    ConfigField(
        "ticket_logs",
        "CHANNEL_IDS.TICKET_LOGS_ID",
        "Ticket Log Channel",
        "Where close transcripts for normal tickets are posted.",
        "channel_text",
        required=True,
        setup=True,
        category="core",
    ),
    ConfigField(
        "ticket_panel",
        "CHANNEL_IDS.TICKET_CHANNEL_ID",
        "Ticket Panel Channel",
        "Channel where `/send-tickets` posts the ticket menu.",
        "channel_text",
        required=True,
        setup=True,
        category="core",
    ),
    ConfigField(
        "ticket_categories",
        "TICKET_CATEGORIES",
        "Ticket Categories",
        "Discord category channels that count as ticket channels.",
        "category_list",
        required=True,
        setup=True,
        category="core",
    ),
    ConfigField(
        "admin_ticket_logs",
        "CHANNEL_IDS.ADMIN_TICKET_LOGS_ID",
        "Admin Ticket Logs",
        "Log channel for admin-private tickets (falls back to main logs if unset).",
        "channel_text",
        setup=True,
        category="channels",
    ),
    ConfigField(
        "management_ticket_logs",
        "CHANNEL_IDS.MANAGEMENT_TICKET_LOGS_ID",
        "Management Ticket Logs",
        "Log channel for management-private tickets.",
        "channel_text",
        setup=True,
        category="channels",
    ),
    ConfigField(
        "verify_channel",
        "CHANNEL_IDS.VERIFY_CHANNEL_ID",
        "Verify Channel",
        "Channel users must have read access to when verification is enforced.",
        "channel_text",
        setup=True,
        category="channels",
    ),
    ConfigField(
        "admin_private_category",
        "CHANNEL_IDS.ADMIN_PRIVATE_CATEGORY_ID",
        "Admin Private Category",
        "Category for admin-private tickets.",
        "channel_category",
        setup=True,
        category="channels",
    ),
    ConfigField(
        "management_private_category",
        "CHANNEL_IDS.MANAGEMENT_PRIVATE_CATEGORY_ID",
        "Management Private Category",
        "Category for management-private tickets.",
        "channel_category",
        setup=True,
        category="channels",
    ),
    ConfigField(
        "ticket_count_voice",
        "CHANNEL_IDS.TICKET_COUNT_VOICE_CHANNEL_ID",
        "Ticket Count Voice Channel",
        "Voice channel renamed with open ticket counts (if used).",
        "channel_voice",
        category="channels",
    ),
    ConfigField(
        "verified_role",
        "ROLE_IDS.VERIFIED_ROLE_ID",
        "Verified Role",
        "Members need this role to open tickets (when set).",
        "role",
        setup=True,
        category="roles",
    ),
    ConfigField(
        "admin_roles",
        "ADMIN_ROLES",
        "Admin Roles (Ticket Logs)",
        "Roles that can view private ticket log details.",
        "role_list",
        category="roles",
    ),
    ConfigField(
        "disregard_remove_roles",
        "DISREGARD_REMOVE_COMMAND_ROLE_IDS",
        "Remove Command Bypass Roles",
        "Roles that bypass hierarchy checks for `/remove`.",
        "role_list",
        category="roles",
    ),
    ConfigField(
        "blacklisted_move_categories",
        "BLACKLISTED_MOVE_CATEGORIES",
        "Blacklisted Move Categories",
        "Categories tickets cannot be moved into.",
        "category_list",
        category="tickets",
    ),
    ConfigField(
        "footer",
        "FOOTER",
        "Embed Footer",
        "Footer text shown on Tickr embeds.",
        "string",
        setup=True,
        category="branding",
    ),
    ConfigField(
        "embed_color",
        "EMBED_COLOR",
        "Embed Color",
        "Hex color for embeds (example: 0x5865F2).",
        "color",
        setup=True,
        category="branding",
    ),
    ConfigField(
        "logo",
        "LOGO",
        "Logo URL or Path",
        "Image URL or local path for embed footer/thumbnails.",
        "url",
        category="branding",
    ),
    ConfigField(
        "transcript_paste_url",
        "TRANSCRIPT_PASTE_URL",
        "Transcript Paste URL",
        "Base URL for transcript hosting (guild override).",
        "url",
        setup=True,
        category="integrations",
    ),
    ConfigField(
        "blacklist_webhook",
        "TICKET_BLACKLIST_WEBHOOK",
        "Blacklist Webhook",
        "Webhook URL for ticket blacklist notifications.",
        "url",
        category="integrations",
    ),
    ConfigField(
        "dashboard_notify_url",
        "__dashboard.notify_url",
        "Dashboard Notify URL",
        "Webhook/callback URL for dashboard ticket events.",
        "dashboard_url",
        category="integrations",
    ),
    ConfigField(
        "dashboard_api_secret",
        "__dashboard.api_secret",
        "Dashboard API Secret",
        "Shared secret for dashboard HTTP API.",
        "dashboard_secret",
        category="integrations",
    ),
    ConfigField(
        "tickets_enabled",
        "__system.tickets_global_enabled",
        "Tickets Globally Enabled",
        "Master switch for opening new tickets in this server.",
        "toggle",
        category="system",
    ),
    ConfigField(
        "cache_entries",
        "ACTIVE_TICKETS_CACHE.ENTRIES",
        "Active Ticket Cache Entries",
        "Max cached active-ticket lookups.",
        "integer",
        category="system",
    ),
    ConfigField(
        "cache_minutes",
        "ACTIVE_TICKETS_CACHE.MINUTES_TO_EXPIRE",
        "Active Ticket Cache TTL (minutes)",
        "Minutes before cache entries expire.",
        "integer",
        category="system",
    ),
    ConfigField(
        "role_hierarchy",
        "ROLE_HIERARCHY",
        "Role Hierarchy (JSON)",
        "JSON map of role ID strings to hierarchy numbers for `/remove`.",
        "json",
        category="advanced",
    ),
)

FIELDS_BY_KEY = {field.key: field for field in CONFIG_FIELDS}
FIELDS_BY_CATEGORY: dict[str, list[ConfigField]] = {}
for _field in CONFIG_FIELDS:
    FIELDS_BY_CATEGORY.setdefault(_field.category, []).append(_field)

SETUP_FIELDS = [field for field in CONFIG_FIELDS if field.setup]


def get_config_value(config: dict, path: str) -> Any:
    if path.startswith("__"):
        return None
    value: Any = config
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def set_config_value(config: dict, path: str, value: Any) -> dict:
    updated = copy.deepcopy(config)
    if path.startswith("__"):
        return updated
    parts = path.split(".")
    cursor = updated
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value
    return updated


def merge_defaults(config: dict) -> dict:
    from services.guild_config_service import GuildConfigService

    merged = copy.deepcopy(GuildConfigService._default_config())
    for key, value in config.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def validate_required(config: dict) -> list[str]:
    missing: list[str] = []
    merged = merge_defaults(config)
    for field in CONFIG_FIELDS:
        if not field.required:
            continue
        value = get_config_value(merged, field.path)
        if value is None or value == "" or value == []:
            missing.append(field.label)
    return missing


def format_field_value(
    guild: discord.Guild | None,
    field: ConfigField,
    config: dict,
    *,
    dashboard: dict | None = None,
    tickets_global_enabled: bool | None = None,
) -> str:
    if field.path == "__dashboard.notify_url":
        value = (dashboard or {}).get("notify_url")
    elif field.path == "__dashboard.api_secret":
        secret = (dashboard or {}).get("api_secret")
        return "`Set`" if secret else "`Not set`"
    elif field.path == "__system.tickets_global_enabled":
        if tickets_global_enabled is None:
            return "`Unknown`"
        return "`Enabled`" if tickets_global_enabled else "`Disabled`"
    else:
        value = get_config_value(config, field.path)

    if value is None or value == "" or value == []:
        return "`Not set`"

    if field.field_type == "role" and guild:
        role = guild.get_role(int(value))
        return role.mention if role else f"`{value}`"
    if (
        field.field_type in ("channel_text", "channel_category", "channel_voice")
        and guild
    ):
        channel = guild.get_channel(int(value))
        return channel.mention if channel else f"`{value}`"
    if field.field_type == "role_list" and guild:
        mentions = []
        for role_id in value[:10]:
            role = guild.get_role(int(role_id))
            mentions.append(role.mention if role else f"`{role_id}`")
        extra = len(value) - 10
        text = ", ".join(mentions)
        if extra > 0:
            text += f" (+{extra} more)"
        return text or "`Empty`"
    if field.field_type == "category_list" and guild:
        mentions = []
        for cat_id in value[:10]:
            channel = guild.get_channel(int(cat_id))
            mentions.append(channel.mention if channel else f"`{cat_id}`")
        extra = len(value) - 10
        text = ", ".join(mentions)
        if extra > 0:
            text += f" (+{extra} more)"
        return text or "`Empty`"
    if field.field_type == "json":
        import json

        text = json.dumps(value, indent=0)
        return f"```{text[:900]}{'...' if len(text) > 900 else ''}```"
    if field.field_type == "dashboard_secret":
        return "`Set`" if value else "`Not set`"
    return f"`{value}`"
