from __future__ import annotations

from discord.ext import commands, tasks
from typing import Optional, Any
import asyncio
import logging
import types

from core.database import aexecute

log = logging.getLogger(name = "Tasks")


class ActiveTicketCache:
    def __init__(self) -> None:
        self._channels: dict[int, str] = {}
        self._lock = asyncio.Lock()

    def get_owner(self, channel_id: int) -> Optional[str]:
        return self._channels.get(channel_id)

    def register(self, channel_id: int, owner_id: int | str) -> None:
        self._channels[int(channel_id)] = str(owner_id)
    
    def unregister(self, channel_id: int) -> None:
        self._channels.pop(int(channel_id), None)
    
    async def refresh(self) -> None:
        rows: list[dict] = await aexecute(
            "SELECT channel_id, owner_id FROM tickets WHERE is_active = %s",
            (1,)
        )
        parsed: dict[int, str] = {}
        for row in rows:
            try:
                parsed[int(row["channel_id"])] = str(row["owner_id"])
            except (KeyError, TypeError, ValueError):
                continue
        async with self._lock:
            self._channels = parsed

        log.debug(msg = f"Active ticket cache refreshed ({len(parsed)} channels)")


active_ticket_cache = ActiveTicketCache()


class ActiveTicketCacheCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client

    async def cog_load(self) -> None:
        await active_ticket_cache.refresh()
        if not self._refresh_loop.is_running():
            self._refresh_loop.start()
    
    def cog_unload(self) -> types.CoroutineType[Any, Any, None]: 
        self._refresh_loop.cancel()
        return self.cog_unload()

    @tasks.loop(minutes = 2)
    async def _refresh_loop(self) -> None:
        await active_ticket_cache.refresh()
    
    @_refresh_loop.before_loop
    async def _before_refresh(self) -> None:
        await self.client.wait_until_ready()


async def setup(client: commands.Bot) -> None:
    await client.add_cog(ActiveTicketCacheCog(client = client))
