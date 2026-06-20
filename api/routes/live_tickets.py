"""Live ticket list and bot command proxy routes."""
from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth.permissions import can_manage_guild, fetch_guild_info
from api.deps import (
    DISCORD_BOT_TOKEN,
    TICKETS_BOT_API_SECRET,
    TICKETS_BOT_API_URL,
    SessionUser,
    get_current_user,
)
from core.database import DatabasePool

router = APIRouter(tags=["tickets"])


async def _channel_name(guild_id: int, channel_id: int) -> str:
    if not DISCORD_BOT_TOKEN:
        return str(channel_id)
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"https://discord.com/api/v10/channels/{channel_id}", headers=headers
        )
        if resp.status_code == 200:
            return resp.json().get("name", str(channel_id))
    return str(channel_id)


def _format_ticket_row(row: dict, channel_name: str) -> dict[str, Any]:
    opened = int(float(row["opened_at"]))
    now = int(time.time())
    return {
        "channelId": str(row["channel_id"]),
        "ownerId": str(row["owner_id"]),
        "type": row["type"],
        "number": row["number"],
        "name": row.get("name") or channel_name,
        "channelName": channel_name,
        "openedAt": opened,
        "durationSeconds": now - opened,
        "privated": row.get("privated") or "",
        "isActive": bool(row.get("is_active")),
        "reason": row.get("reason"),
        "transcript": row.get("transcript"),
        "closedAt": row.get("closed_at"),
    }


@router.get("/guilds/{guild_id}/tickets/active")
async def active_tickets(guild_id: int, user: SessionUser = Depends(get_current_user)) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    rows = DatabasePool.execute(
        "SELECT * FROM tickets WHERE guild_id = %s AND is_active = 1 ORDER BY opened_at DESC",
        (guild_id,),
    )
    tickets = []
    for row in rows:
        name = await _channel_name(guild_id, int(row["channel_id"]))
        tickets.append(_format_ticket_row(row, name))
    return {"tickets": tickets}


@router.get("/guilds/{guild_id}/tickets/recent")
async def recent_tickets(
    guild_id: int,
    limit: int = 25,
    user: SessionUser = Depends(get_current_user),
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    limit = max(1, min(limit, 100))
    rows = DatabasePool.execute(
        "SELECT * FROM tickets WHERE guild_id = %s AND is_active = 0 ORDER BY closed_at DESC LIMIT %s",
        (guild_id, limit),
    )
    tickets = []
    for row in rows:
        name = row.get("name") or str(row["channel_id"])
        tickets.append(_format_ticket_row(row, name))
    return {"tickets": tickets}


class CloseBody(BaseModel):
    reason: str = Field(min_length=2)


class CommandBody(BaseModel):
    command: str
    args: str = ""


async def _proxy_bot_api(path: str, payload: dict) -> dict[str, Any]:
    if not TICKETS_BOT_API_SECRET:
        raise HTTPException(status_code=503, detail="Bot API secret not configured")
    url = f"{TICKETS_BOT_API_URL}{path}"
    headers = {"X-Tickets-Key": TICKETS_BOT_API_SECRET, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        try:
            data = resp.json()
        except Exception:
            data = {"error": resp.text}
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=data.get("error", "Bot API error"))
        return data


@router.post("/guilds/{guild_id}/tickets/{channel_id}/close")
async def close_ticket(
    guild_id: int,
    channel_id: int,
    body: CloseBody,
    user: SessionUser = Depends(get_current_user),
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return await _proxy_bot_api(
        "/close-ticket",
        {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "closed_by_id": user.user_id,
            "reason": body.reason,
        },
    )


@router.post("/guilds/{guild_id}/tickets/{channel_id}/command")
async def ticket_command(
    guild_id: int,
    channel_id: int,
    body: CommandBody,
    user: SessionUser = Depends(get_current_user),
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return await _proxy_bot_api(
        "/ticket-command",
        {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "actor_id": user.user_id,
            "command": body.command,
            "args": body.args,
        },
    )
