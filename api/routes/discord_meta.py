"""Discord guild metadata for config pickers."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException

from api.auth.permissions import can_manage_guild
from api.deps import DISCORD_BOT_TOKEN, SessionUser, get_current_user

router = APIRouter(tags=["discord"])


@router.get("/guilds/{guild_id}/discord/meta")
async def discord_meta(
    guild_id: int, user: SessionUser = Depends(get_current_user)
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    if not DISCORD_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Bot token not configured")
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        roles_resp = await client.get(
            f"https://discord.com/api/v10/guilds/{guild_id}/roles", headers=headers
        )
        channels_resp = await client.get(
            f"https://discord.com/api/v10/guilds/{guild_id}/channels", headers=headers
        )
        if roles_resp.status_code == 404 or channels_resp.status_code == 404:
            raise HTTPException(status_code=404, detail="Guild not found")
        roles_resp.raise_for_status()
        channels_resp.raise_for_status()
        roles_data = roles_resp.json()
        channels_data = channels_resp.json()
    roles = [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "color": r.get("color", 0),
            "position": r.get("position", 0),
        }
        for r in sorted(roles_data, key=lambda x: x.get("position", 0), reverse=True)
        if r.get("name") != "@everyone"
    ]
    text_channels = []
    categories = []
    voice_channels = []
    for ch in channels_data:
        ctype = ch.get("type", 0)
        entry = {
            "id": str(ch["id"]),
            "name": ch.get("name", ""),
            "parentId": ch.get("parent_id"),
        }
        if ctype == 4:
            categories.append(entry)
        elif ctype in (0, 5):
            text_channels.append(entry)
        elif ctype == 2:
            voice_channels.append(entry)
    return {
        "roles": roles,
        "textChannels": text_channels,
        "categories": categories,
        "voiceChannels": voice_channels,
    }
