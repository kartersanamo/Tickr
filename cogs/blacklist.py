from discord.ext import commands, tasks
from typing import Any, Literal
from discord import app_commands
from discord import Webhook
import datetime
import aiohttp
import discord
import types
import time

from core.loggers import log_commands, log_tasks
from core.config import ConfigManager
from core.database import execute
from core.decorators import task


class Blacklist(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client
        self.check_blacklists.start()

    def cog_unload(self) -> types.CoroutineType[Any, Any, None]:
        self.check_blacklists.stop()
        return self.cog_unload()
    
    @tasks.loop(minutes = 10)
    async def check_blacklists(self) -> None:
        current_time: int = int(time.time())
        rows: list = execute(
            "SELECT user_id FROM blacklists WHERE unblacklist_at < %s",
            (current_time,)
        )
        if rows:
            user_ids: list= [str(row['user_id']) for row in rows]
            log_tasks.info(msg = f"Removing ticket blacklists {user_ids}")
            await self.remove_blacklists(user_ids)
    
    @task(action_name = "Remove Blacklists", log = False)
    async def remove_blacklists(self, user_ids: list[str]) -> None:
        if not user_ids:
            return
        placeholders = ", ".join(["%s"] * len(user_ids))
        execute(f"DELETE FROM blacklists WHERE user_id IN ({placeholders})", tuple(user_ids))
    
    @task(action_name = "Get Unix", log = False)
    async def get_unix(self, length: str) -> int:
        current_unix: int = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        length_in_secs: int = int(length.split("d")[0]) * 86400
        return current_unix + length_in_secs
    
    @task(action_name = "Is Blacklisted", log = False)
    async def is_blacklisted(self, interaction: discord.Interaction, user: discord.Member) -> bool:
        existing_row = execute("SELECT * FROM blacklists WHERE user_id = %s", (user.id,))
        if existing_row:
            await self.remove_blacklists(user_ids = [str(user.id)])
            await self.send_embed(interaction = interaction, user = user, blacklisted = "unblacklisted")
            log_commands.info(msg = f"{user} ({user.id}) has been unblacklisted from creating tickets by a staff member")
            return True
        return False
    
    @task(action_name = "Blacklist User", log = False)
    async def blacklist_user(self, interaction: discord.Interaction, user: discord.Member, length: str, reason: str) -> None:
        unix = await self.get_unix(length = length)
        execute(
            "INSERT INTO blacklists (user_id, reason, staff_id, unblacklist_at, created_at) VALUES (%s, %s, %s, %s, %s)",
            (user.id, reason or "N/A", interaction.user.id, unix, int(__import__("time").time()))
        )
        log_commands.info(msg = f"Ticket blacklisted {user} ({user.id}) for {length}")

    @task(action_name = "Send Embed", log = False)
    async def send_embed(self, interaction: discord.Interaction, user: discord.Member, blacklisted: str) -> None:
        embed: discord.Embed = discord.Embed(
            description = f"{interaction.user.mention} has **{blacklisted}** {user.mention} from opening tickets",
            color = discord.Color.from_str(value = ConfigManager.get(key = "EMBED_COLOR"))
        )
        logo_url = self.client.app.embeds.get_logo_url(ConfigManager.get(key = "LOGO")) # type: ignore
        embed.set_footer(text = ConfigManager.get("FOOTER"), icon_url = logo_url)
        await interaction.response.send_message(embed = embed, file = discord.File("assets/Logo.png"))
    
    @task(action_name = "Send Webhook", log = False)
    async def send_webhook(self, interaction: discord.Interaction, user: discord.Member, length: str, reason: str) -> None:
        unix: int = await self.get_unix(length)
        embed: discord.Embed = discord.Embed(
            title = "Ticket Blacklist",
            color = discord.Color.from_str(value = ConfigManager.get(key = "EMBED_COLOR")),
            description = f"`IGN` {user.display_name}\n`Discord` {user}\n`Reason` {reason or 'N/A'}\n`Expires` <t:{unix}:R>",
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name = interaction.user.display_name, icon_url = interaction.user.avatar)

        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(ConfigManager.get(key = "TICKET_BLACKLIST_WEBHOOK"), session = session)
            await webhook.send(embed = embed, username = "Ticket Blacklists")
    
    @app_commands.guild_only()
    @app_commands.command(name = "blacklist", description = "Blacklists a member from opening tickets")
    @app_commands.describe(user = "The user to blacklist from opening tickets", length = "How long should this blacklist last?", reason = "The reason for blacklisting the user")
    async def blacklist(self, interaction: discord.Interaction, user: discord.Member, length: Literal["1d", "2d", "3d", "4d", "5d", "6d", "7d", "10d", "14d", "28d", "30d"], reason: str = None) -> None:
        await self.blacklist_command(interaction = interaction, user = user, length = length, reason = reason)
    
    @task(action_name = "Blacklist Command", log = True)
    async def blacklist_command(self, interaction: discord.Interaction, user: discord.Member, length: str, reason: str | None = None) -> None:
        is_blacklisted: bool = await self.is_blacklisted(interaction = interaction, user = user)
        if not is_blacklisted:
            await self.blacklist_user(interaction = interaction, user = user, length = length, reason = reason or "N/A")
            await self.send_embed(interaction = interaction, user = user, blacklisted = "blacklisted")
            await self.send_webhook(interaction = interaction, user = user, length = length, reason = reason or "N/A")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Blacklist(client))