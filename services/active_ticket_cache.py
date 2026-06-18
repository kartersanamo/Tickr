from __future__ import annotations

import discord
from discord.ext import commands, tasks

from core.database import DatabasePool
from core.decorators import TaskDecorator


class ActiveTicketCache:
    def __init__(self) -> None:
        self._cache: dict[str, int] = {}

    @staticmethod
    def _key(guild_id: int, channel_id: int) -> str:
        return f"{guild_id}:{channel_id}"

    def register(self, guild_id: int, channel_id: int, owner_id: int) -> None:
        self._cache[self._key(guild_id, channel_id)] = owner_id

    def unregister(self, guild_id: int, channel_id: int) -> None:
        self._cache.pop(self._key(guild_id, channel_id), None)

    def get_owner(self, guild_id: int, channel_id: int) -> int | None:
        return self._cache.get(self._key(guild_id, channel_id))

    @TaskDecorator.task("Refresh Active Ticket Cache", False)
    async def refresh(self) -> None:
        rows = DatabasePool.execute(
            "SELECT guild_id, channel_id, owner_id FROM tickets WHERE is_active = 1"
        )
        self._cache.clear()
        for row in rows:
            self._cache[self._key(int(row["guild_id"]), int(row["channel_id"]))] = int(row["owner_id"])


active_ticket_cache = ActiveTicketCache()


class ActiveTicketCacheCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @tasks.loop(minutes=2)
    async def refresh_cache(self) -> None:
        await active_ticket_cache.refresh()

    @refresh_cache.before_loop
    async def before_refresh(self) -> None:
        await self.client.wait_until_ready()

    def cog_unload(self) -> None:
        self.refresh_cache.cancel()


async def setup(client: commands.Bot) -> None:
    cog = ActiveTicketCacheCog(client)
    await client.add_cog(cog)
    cog.refresh_cache.start()
