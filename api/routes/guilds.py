"""Guild list and summary routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.auth.permissions import (
    bot_guild_ids,
    can_manage_guild,
    fetch_guild_info,
    oauth_guild_permissions,
)
from api.deps import SessionUser, get_current_user
from core.database import DatabasePool
from services.guild_config_fields import validate_required, merge_defaults
from services.guild_config_service import GuildConfigService

router = APIRouter(tags=["guilds"])


@router.get("/me/guilds")
async def list_manageable_guilds(user: SessionUser = Depends(get_current_user)) -> dict[str, Any]:
    installed = bot_guild_ids()
    results: list[dict[str, Any]] = []
    for guild_id in sorted(installed):
        if not await can_manage_guild(user, guild_id):
            continue
        info = await fetch_guild_info(guild_id)
        row = DatabasePool.execute(
            "SELECT configured FROM guilds WHERE guild_id = %s LIMIT 1",
            (guild_id,),
        )
        configured = bool(row[0]["configured"]) if row else False
        cfg = await GuildConfigService.for_guild(guild_id)
        missing = validate_required(merge_defaults(cfg.all()))
        icon = None
        name = f"Server {guild_id}"
        if info:
            name = info.get("name", name)
            icon_hash = info.get("icon")
            if icon_hash:
                ext = "gif" if str(icon_hash).startswith("a_") else "png"
                icon = f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.{ext}"
        results.append(
            {
                "id": str(guild_id),
                "name": name,
                "icon": icon,
                "configured": configured,
                "setupComplete": configured and not missing,
                "missingRequired": missing,
            }
        )
    return {"guilds": results}


@router.get("/guilds/{guild_id}")
async def guild_summary(guild_id: int, user: SessionUser = Depends(get_current_user)) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    merged = merge_defaults(cfg.all())
    missing = validate_required(merged)
    active_row = DatabasePool.execute(
        "SELECT COUNT(*) AS cnt FROM tickets WHERE guild_id = %s AND is_active = 1",
        (guild_id,),
    )
    closed_row = DatabasePool.execute(
        "SELECT COUNT(*) AS cnt FROM tickets WHERE guild_id = %s AND is_active = 0",
        (guild_id,),
    )
    info = await fetch_guild_info(guild_id)
    return {
        "id": str(guild_id),
        "name": info.get("name") if info else f"Server {guild_id}",
        "configured": cfg.configured,
        "setupComplete": cfg.configured and not missing,
        "missingRequired": missing,
        "ticketsGlobalEnabled": cfg.tickets_global_enabled,
        "ticketsToggleStatus": cfg.tickets_raw().get("TOGGLE_STATUS", "Enabled"),
        "activeTickets": int(active_row[0]["cnt"]) if active_row else 0,
        "closedTickets": int(closed_row[0]["cnt"]) if closed_row else 0,
        "permissions": oauth_guild_permissions(user, guild_id),
    }
