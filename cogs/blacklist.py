"""blacklist.py — Ticket blacklist management."""

from discord.ext import commands, tasks
from discord import app_commands
from discord import Webhook
from typing import Literal
import datetime
import aiohttp
import discord
import time

from core.database import DatabasePool
from core.decorators import TaskDecorator
from core.loggers import log_commands, log_tasks
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color, optional_logo_file, set_embed_footer


class Blacklist(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client
        self.check_blacklists.start()

    def cog_unload(self) -> None:
        self.check_blacklists.cancel()

    @tasks.loop(minutes=10)
    async def check_blacklists(self) -> None:
        current_time = int(time.time())
        rows = DatabasePool.execute(
            "SELECT guild_id, user_id FROM blacklists WHERE unblacklist_at < %s",
            (current_time,),
        )
        if rows:
            for row in rows:
                DatabasePool.execute(
                    "DELETE FROM blacklists WHERE guild_id = %s AND user_id = %s",
                    (row["guild_id"], row["user_id"]),
                )
            log_tasks.info(f"Removed expired ticket blacklists: {len(rows)}")

    @TaskDecorator.task("Get Unix", False)
    async def get_unix(self, length: str) -> int:
        current_unix = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        length_in_secs = int(length.split("d")[0]) * 86400
        return current_unix + length_in_secs

    @TaskDecorator.task("Check Blacklisted", False)
    async def check_blacklisted(
        self, interaction: discord.Interaction, user: discord.Member, guild_id: int
    ) -> bool:
        existing_row = DatabasePool.execute(
            "SELECT * FROM blacklists WHERE guild_id = %s AND user_id = %s",
            (guild_id, user.id),
        )
        if existing_row:
            DatabasePool.execute(
                "DELETE FROM blacklists WHERE guild_id = %s AND user_id = %s",
                (guild_id, user.id),
            )
            cfg = await GuildConfigService.for_guild(guild_id)
            await self.send_embed(interaction, user, "unblacklisted", cfg)
            log_commands.info(f"{user} ({user.id}) unblacklisted from tickets")
            return True
        return False

    @TaskDecorator.task("Blacklist User", False)
    async def blacklist_user(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        length: str,
        reason: str,
        guild_id: int,
    ) -> None:
        unix = await self.get_unix(length)
        DatabasePool.execute(
            "INSERT INTO blacklists (guild_id, user_id, reason, staff_id, unblacklist_at, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                guild_id,
                user.id,
                reason or "N/A",
                interaction.user.id,
                unix,
                int(time.time()),
            ),
        )
        log_commands.info(f"Ticket blacklisted {user} ({user.id}) for {length}")

    @TaskDecorator.task("Send Embed", False)
    async def send_embed(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        blacklisted: str,
        cfg,
    ) -> None:
        embed = discord.Embed(
            description=f"{interaction.user.mention} has **{blacklisted}** {user.mention} from opening tickets",
            color=embed_color(cfg),
        )
        set_embed_footer(embed, cfg)
        logo_file = optional_logo_file(cfg)
        if logo_file:
            await interaction.response.send_message(embed=embed, file=logo_file)
        else:
            await interaction.response.send_message(embed=embed)

    @TaskDecorator.task("Send Webhook", False)
    async def send_webhook(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        length: str,
        reason: str,
        cfg,
    ) -> None:
        webhook_url = cfg.get("TICKET_BLACKLIST_WEBHOOK")
        if not webhook_url:
            return
        unix = await self.get_unix(length)
        embed = discord.Embed(
            title="Ticket Blacklist",
            color=embed_color(cfg),
            description=f"`IGN` {user.display_name}\n`Discord` {user}\n`Reason` {reason or 'N/A'}\n`Expires` <t:{unix}:R>",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(webhook_url, session=session)
            await webhook.send(embed=embed, username="Ticket Blacklists")

    @app_commands.guild_only()
    @app_commands.command(
        name="blacklist", description="Blacklists a member from opening tickets"
    )
    @app_commands.describe(
        user="The user to blacklist from opening tickets",
        length="When this user should be unblacklisted from tickets",
        reason="The reason for blacklisting the user",
    )
    async def blacklist(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        length: Literal[
            "1d", "2d", "3d", "4d", "5d", "6d", "7d", "10d", "14d", "28d", "30d"
        ],
        reason: str = None,
    ) -> None:
        await self.blacklist_command(interaction, user, length, reason)

    @TaskDecorator.task("Blacklist Command", True)
    async def blacklist_command(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        length: str,
        reason: str = None,
    ) -> None:
        if interaction.guild_id is None:
            return
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        blacklisted = await self.check_blacklisted(
            interaction, user, interaction.guild_id
        )
        if not blacklisted:
            await self.blacklist_user(
                interaction, user, length, reason, interaction.guild_id
            )
            await self.send_embed(interaction, user, "blacklisted", cfg)
            await self.send_webhook(interaction, user, length, reason, cfg)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Blacklist(client))
