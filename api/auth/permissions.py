"""Guild access checks for the web dashboard."""

from __future__ import annotations

from typing import Any

import httpx

from api.deps import DISCORD_BOT_TOKEN, SessionUser
from core.database import DatabasePool
from services.guild_config_service import GuildConfigService

ADMINISTRATOR = 0x8
MANAGE_GUILD = 0x20


def bot_guild_ids() -> set[int]:
    rows = DatabasePool.execute("SELECT guild_id FROM guilds")
    return {int(row["guild_id"]) for row in rows}


def oauth_guild_permissions(user: SessionUser, guild_id: int) -> int | None:
    for guild in user.guilds:
        if int(guild.get("id", 0)) == guild_id:
            try:
                return int(guild.get("permissions", 0))
            except (TypeError, ValueError):
                return 0
    return None


def has_discord_admin(perms: int | None) -> bool:
    if perms is None:
        return False
    return bool(perms & ADMINISTRATOR or perms & MANAGE_GUILD)


async def fetch_member_role_ids(guild_id: int, user_id: int) -> list[int]:
    if not DISCORD_BOT_TOKEN:
        return []
    url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}"
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        data = response.json()
        return [int(r) for r in data.get("roles", [])]


async def can_manage_guild(user: SessionUser, guild_id: int) -> bool:
    if guild_id not in bot_guild_ids():
        return False
    perms = oauth_guild_permissions(user, guild_id)
    if has_discord_admin(perms):
        return True
    cfg = await GuildConfigService.for_guild(guild_id)
    star_id = cfg.get("ROLE_IDS.ADMINISTRATOR_PERMS_ROLE_ID")
    if not star_id:
        return False
    role_ids = await fetch_member_role_ids(guild_id, user.user_id)
    return int(star_id) in role_ids


async def require_guild_access(user: SessionUser, guild_id: int) -> None:
    from fastapi import HTTPException

    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="You cannot manage this server")


async def fetch_guild_info(guild_id: int) -> dict[str, Any] | None:
    if not DISCORD_BOT_TOKEN:
        return None
    url = f"https://discord.com/api/v10/guilds/{guild_id}?with_counts=true"
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            return None
        return response.json()
