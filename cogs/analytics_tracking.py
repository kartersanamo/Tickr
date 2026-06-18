"""Ticket message analytics."""
from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from core.analytics import logger as analytics
from services.active_ticket_cache import active_ticket_cache
from services.guild_config_service import GuildConfigService


class TicketAnalytics(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    async def _is_staff(self, member: discord.Member, guild_id: int) -> bool:
        cfg = await GuildConfigService.for_guild(guild_id)
        staff_id = cfg.get("ROLE_IDS.STAFF_TEAM_ROLE_ID")
        if staff_id:
            role = member.guild.get_role(int(staff_id))
            if role and role in member.roles:
                return True
        return member.guild_permissions.manage_messages

    def _record_message(self, guild_id: int, channel_id: int, *, is_staff: bool) -> None:
        analytics.record_ticket_message(guild_id, str(channel_id), is_staff=is_staff)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.guild or message.author.bot:
            return
        owner_id = active_ticket_cache.get_owner(message.guild.id, message.channel.id)
        if owner_id is None:
            return
        is_staff = await self._is_staff(message.author, message.guild.id)
        if message.author.id == owner_id:
            is_staff = False
        asyncio.create_task(
            asyncio.to_thread(
                self._record_message,
                message.guild.id,
                message.channel.id,
                is_staff=is_staff,
            ),
            name=f"ticket-analytics-{message.channel.id}",
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(TicketAnalytics(client))
