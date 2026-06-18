"""ticket_count.py — Display open ticket counts."""
from discord.ext import commands
from discord import app_commands
from typing import Literal
import discord

from core.database import DatabasePool
from core.decorators import TaskDecorator
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color


class TicketCount(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client

    async def get_active_list(self, guild_id: int) -> list[dict]:
        return DatabasePool.execute(
            "SELECT type, COUNT(*) as count FROM tickets WHERE guild_id = %s AND is_active = 1 GROUP BY type ORDER BY count DESC",
            (guild_id,),
        )

    async def get_total_list(self, guild_id: int) -> list[dict]:
        return DatabasePool.execute(
            "SELECT type, COUNT(*) as count FROM tickets WHERE guild_id = %s GROUP BY type ORDER BY count DESC",
            (guild_id,),
        )

    async def get_debug_embeds(
        self, cfg, active_list: list[dict], active_count: int, total_list: list[dict], total_count: int
    ) -> list[discord.Embed]:
        color = embed_color(cfg)
        active_embed = discord.Embed(
            title="Active Tickets By Category",
            description="\n".join(
                f"> **{row.get('count', 0)}** {row.get('type', 'Unknown')} ({round(row.get('count', 0) / max(active_count, 1) * 100, 2)}%)"
                for row in active_list
            )
            or "No active tickets.",
            color=color,
        )
        active_embed.set_footer(text=f"There are {active_count:,} tickets open!")
        history_embed = discord.Embed(
            title="Total Ticket History",
            description="\n".join(
                f"> **{row.get('count', 0)}** {row.get('type', 'Unknown')} ({round(row.get('count', 0) / max(total_count, 1) * 100, 2)}%)"
                for row in total_list
            )
            or "No ticket history.",
            color=color,
        )
        history_embed.set_footer(text=f"There have been {total_count:,} total tickets!")
        return [active_embed, history_embed]

    @app_commands.guild_only()
    @app_commands.command(name="ticket-count", description="Sends the number of currently opened tickets")
    async def ticketcount(self, interaction: discord.Interaction, debug: Literal["Yes"] = None):
        await self.ticket_count_command(interaction, debug)

    @TaskDecorator.task("Ticket Count Command", True)
    async def ticket_count_command(self, interaction: discord.Interaction, debug: str) -> None:
        if interaction.guild_id is None:
            return
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        active_list = await self.get_active_list(interaction.guild_id)
        active_count = sum(row.get("count", 0) for row in active_list)
        total_list = await self.get_total_list(interaction.guild_id)
        total_count = sum(row.get("count", 0) for row in total_list)

        if not debug:
            embed = discord.Embed(
                title=f"There are **{active_count}** tickets open!",
                color=embed_color(cfg),
            )
            embed.set_footer(text=f"There have been {total_count:,} total tickets!")
            await interaction.response.send_message(embeds=[embed])
        else:
            embeds = await self.get_debug_embeds(cfg, active_list, active_count, total_list, total_count)
            await interaction.response.send_message(embeds=embeds)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(TicketCount(client))
