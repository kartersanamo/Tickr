"""Persist guild ticket types to database."""
from __future__ import annotations

from services.guild_config_service import GuildConfigService


async def load_raw(guild_id: int) -> dict:
    cfg = await GuildConfigService.for_guild(guild_id)
    return cfg.tickets_raw()


async def reload_tickets(guild_id: int) -> dict:
    return await GuildConfigService.reload_tickets(guild_id)


async def save_raw(guild_id: int, data: dict) -> None:
    await GuildConfigService.save_ticket_types(guild_id, data)
