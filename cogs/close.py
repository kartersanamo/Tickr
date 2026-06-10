from collections.abc import Awaitable
from discord.ext import commands
from discord import app_commands
from typing import Any
import datetime
import requests
import discord
import asyncio
import time
import pytz

from services.active_ticket_cache import active_ticket_cache
from services.ticket_check_service import is_ticket
from core.loggers import log_commands, log_tasks
from core.config import ConfigManager
from core.database import execute
from core.decorators import task


SEPARATOR: str = "──────────────────────────────────────────────────────"


class Close(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client
    
    @task(action_name = "Convert to EST", log = False)
    def convert_to_est(self, timestamp: float) -> str:
        try:
            est_time: datetime.date = datetime.datetime.fromtimestamp(timestamp = int(float(timestamp)), tz = pytz.utc).astimezone(tz = pytz.timezone(zone = "US/Eastern"))
            return est_time.strftime("%a, %b, %d, %y, %I:%M:%S %p") + " EST"
        
        except Exception as exc:
            log_commands.warning(msg = f"Failed to convert the timestamp to EST {exc}")
            return str(timestamp)
    
    @task(action_name = "Get Transcript Link", log = False)
    async def return_link(self, content: str) -> str:
        base_url: str = "https://paste.minecadia.com" # TODO: add to config
        post_suffix: str = "/documents" # TODO: add to config
        headers: dict[str, str] = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        response: requests.Response = requests.post(
            url = base_url + post_suffix,
            headers = headers,
            data = content
        )
        response_data: Any = response.json()
        key: str = response_data['key']
        return base_url + "/" + key

    @task(action_name = "Fetch All Messages", log = False)
    async def fetch_all_messages(self, channel: discord.TextChannel) -> list[discord.Message]:
        return [message async for message in channel.history(limit = None, oldest_first = True)]

    @task(action_name = "Format Embed", log = False)
    async def format_embed_content(self, embed: discord.Embed) -> str:
        parts: list = []
        lengths: list = []
        dictionary = embed.to_dict() # I don't know how to type hint this
        title: str = dictionary.get(k = "title", default = "")
        description: str = dictionary.get(k = "description", default = "")
        fields: list = dictionary.get(k = "fields", default = [])
        footer: str = dictionary.get(k = "footer", default = {}).get("text","")

        if title:
            lengths.append(len(title))
        if description:
            for line in description.split(sep = "\n"):
                lengths.append(len(line))
        for field in fields:
            field_name: str = field.get(k = "name", default = "")
            field_value: str = field.get(k = "value", default = "")
            lengths.append(len(field_name))
            lengths.append(len(field_value))
        if footer:
            lengths.append(len(footer))

        if lengths:
            max_length = min(max(lengths), 100)
        else:
            return ""
        
        parts.append("/" + ("-" * (int(max_length) + 2) + "\\\n"))
        new_line: str = " " * max_length

        if title:
            parts.append(f"| {title:{max_length}} |\n")
            parts.append(f"| {new_line} |\n")

        if description:
            for line in description.split(sep = "\n"):
                substrings: list[str] = []
                index: int = 0
                while index < len(line):
                    substrings.append(line[index : index + 100])
                    index += 100
                for sub in substrings:
                    parts.append(f"| {sub:{max_length}} |\n")
            parts.append(f"| {new_line} |\n")
        
        for field in fields:
            field_name: str = field.get(k = "name", default = "")
            field_value: str = field.get(k = "value", default = "")
            parts.append(f"| {field_name:{max_length}} |\n{field_value:{max_length}} |\n")
        
        if footer:
            parts.append(f"| {footer:{max_length}} |\n")
        
        parts.append("\\" + ("-" * (int(max_length) + 2)) + "/")

        return "".join(parts)

    @task(action_name = "Generate Transcript Content", log = False)
    async def generate_transcript_content(self,
        messages: list[discord.Message],
        opened_string: str,
        ticket_type: str,
        ticket_number: str,
        owner: discord.Member | discord.User,
        owner_id: int,
        reason: str,
        closed_by: discord.Member | discord.User,
        channel_id: int,
        closed_at_string: str,
        closed_by_id: int
    ) -> str:
        content_parts: list[str] = [
            f"{self.client.user}: {ticket_type}",
             f"- Opened by: {owner} ({owner_id})",
             f"- Opened at: {opened_string}",
             f"- Channel ID: {channel_id}",
             f"- Ticket ID: {ticket_number}",
             f"",
             f"{SEPARATOR}",
             f""
        ]
        for message in messages:
            try:
                message_content: str = message.content
                for embed in message.embeds:
                    embed_content: str = await self.format_embed_content(embed = embed)
                    content_parts.append(embed_content)
                created_at: str = self.convert_to_est(timestamp = message.created_at.timestamp())
                content_parts.append(f"[{created_at}]")
                content_parts.append(f"{message.author.name} : {message.author.id}")
                if message_content:
                    content_parts.append(f"\t{message_content}")
                content_parts.append("")
            
            except Exception as exc:
                log_tasks.warning(msg = f"Failed logging message {message.author} ({message.author.id}): {message.content} {exc}")

        content_parts.append(SEPARATOR)
        content_parts.append("")
        content_parts.append(f"- Closure Reason: {reason}")
        content_parts.append(f"- Closed By: {closed_by} ({closed_by_id})")
        content_parts.append(f"- Closed At: {closed_at_string}")

        return "\n".join(content_parts)

    @task(action_name = "Get Ticket Log Embed", log = False)
    async def get_ticket_log_embed(self,
        reason: str,
        opened_timestamp: int,
        ticket_number: str,
        owner_mention: str,
        owner: discord.Member | discord.User,
        link: str,
        ticket_type: str,
        closed_at_timestamp: int,
        closed_by: discord.Member | discord.User
    ) -> discord.Embed:
        delta: str = "N/A"
        if opened_timestamp != "N/A":
            seconds: int = closed_at_timestamp - opened_timestamp
            delta: str = self.client.app.time_format.seconds_to_format(seconds) #type: ignore

        description: str = (
            f"`🎫` **{ticket_type} #{ticket_number}** was closed by {closed_by}"
            f" **Reason:** {reason}"
            f" **Owner:** {owner_mention} / {owner.name}"
            f" **Ticket Duration:** {delta}"
            f"[Ticket Transcript]({link})"
        )

        embed: discord.Embed = discord.Embed(
            color = discord.Color.from_str(value = ConfigManager.get(key = "EMBED_COLOR")),
            description = description
        )

        logo_url = self.client.app.embeds.get_logo_url(ConfigManager.get(key = "LOGO")) # type: ignore
        embed.set_footer(text = ConfigManager.get(key = "FOOTER"), icon_url = logo_url)

        return embed

    @task(action_name = "Send Ticket Log", log = False)
    async def send_ticket_log(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        embed: discord.Embed,
        privated: str
    ) -> None:
        channel_json_string = (
            "ADMIN_TICKET_LOGS_ID"
            if privated == "Admin"
            else "MANAGEMENT_TICKET_LOGS_ID"
            if privated == "Management"
            else "TICKET_LOGS_ID"
        )
        ticket_log_channel_id: int = ConfigManager.get(key = "CHANNEL_IDS")[channel_json_string]
        ticket_log_channel: discord.abc.GuildChannel | None = guild.get_channel(ticket_log_channel_id)
        if not ticket_log_channel or not isinstance(ticket_log_channel, discord.TextChannel):
            log_commands.warning(msg = "Failed to get the ticket logs channel. Please ensure that it is a TextChannel")
            return
        
        await ticket_log_channel.send(embed = embed, file = discord.File("assets/Logo.png"))

        tasks: list[Awaitable[discord.DMChannel]] = [
            overwrite.create_dm()
            for overwrite in channel.overwrites
            if isinstance(overwrite, discord.Member)
            and not overwrite.bot
            and channel.permissions_for(overwrite).view_channel
        ]

        try:
            dm_channels = await asyncio.gather(*tasks)
            send_tasks = [
                dm.send(embed = embed, file = discord.File("assets/Logo.png"))
                for dm in dm_channels
                if dm
            ]
            await asyncio.gather(*send_tasks)
        except Exception as exc:
            log_tasks.warning(msg = f"Failed to send ticket log: {exc}")

    @task(action_name = "Update Database")
    async def update_database(
        self,
        reason: str,
        name: str,
        link: str,
        closed_at_timestamp: int,
        channel_id: int,
        closed_by_id: int
    ) -> None:
        execute(
            "UPDATE tickets SET is_active = 0, closed_by_id = %s, closed_at = %s, reason = %s, name = %s, transcript = %s WHERE channel_id = %s",
            (closed_by_id, closed_at_timestamp, reason, name, link, channel_id)
        )
        active_ticket_cache.unregister(channel_id)
    
    @task(action_name = "Fetch Ticket Info")
    async def fetch_ticket_info(self, channel_id: int) -> tuple:
        if self.client.user is None:
            log_tasks.error(msg = f"self.client.user resolved None")
            return ()
        
        bot_account: discord.ClientUser = self.client.user
        info = (bot_account, bot_account.id, bot_account.mention, 0, "N/A", "0000", "Unknown", "", 0, "")
        rows: list[dict] = execute(
            "SELECT number, opened_at, privated, type, owner_id FROM tickets WHERE channel_id = %s",
            (channel_id,)
        )
        if not rows:
            log_tasks.error(msg = f"Failed to fetch ticket information from databse for channel {channel_id}")
            return info
        
        row: dict = rows[0]
        opened_timestamp: int = int(float(row["opened_at"]))
        opened_string: str = self.convert_to_est(timestamp = opened_timestamp)
        ticket_number: str = row["number"]
        privated: str = row["privated"]
        ticket_type: str = row["type"]
        owner: discord.User= await self.client.fetch_user(int(row["owner_id"]))
        owner_id: int = owner.id
        owner_mention: str = owner.mention
        closed_at_timestamp: int = int(time.time())
        closed_at_string: str = self.convert_to_est(timestamp = closed_at_timestamp)
        info = (
            info, owner_id, owner_mention, opened_timestamp,
            opened_string, ticket_number, ticket_type, privated,
            closed_at_timestamp, closed_at_string
        )

        return info

    @task(action_name = "Get Ticket Count", log = False)
    async def get_ticket_count(self) -> int:
        rows: list[dict] = execute("SELECT COUNT(*) from tickets WHERE is_active = 1")
        if not rows:
            log_tasks.error(msg = f"Failed to fetch ticket count from database")
            return -1

        row: dict = rows[0]
        return int(row['COUNT(*)'])
    
    @is_ticket()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(rate = 1, per = 10.0, key = lambda i: (i.channel_id, i.user.id))
    @app_commands.command(name = "close", description = "Closes the ticket channel")
    @app_commands.describe(reason = "The reason for closing the ticket")
    async def close(self, interaction: discord.Interaction, reason: str) -> None:
        await self.close_command(interaction = interaction, reason = reason)
    
    @task(action_name = "Close Command", log = False)
    async def close_command(self, interaction: discord.Interaction, reason: str) -> None:
        await interaction.response.defer()
        if interaction.guild is None:
            log_commands.warning(msg = "Interaction guild was not found")
            return
        
        if not isinstance(interaction.channel, discord.TextChannel):
            log_commands.warning(msg = "Interaction channel was not a text channel")
            return
        
        
        
        await self.close_ticket_channel(
            guild = interaction.guild,
            channel = interaction.channel,
            closed_by = interaction.user,
            close_reason = reason
        )

    @task(action_name = "Close Ticket Channel", log = False)
    async def close_ticket_channel(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        closed_by: discord.Member | discord.User,
        close_reason: str
    ) -> None:
        start: float = time.perf_counter()
        messages: list[discord.Message] = await self.fetch_all_messages(channel = channel)
        channel_id = channel.id
        (
            owner,
            owner_id,
            owner_mention,
            opened_timestamp,
            opened_string,
            ticket_number,
            ticket_type,
            privated,
            closed_at_timestamp,
            closed_at_string
        ) = await self.fetch_ticket_info(channel_id = channel_id)

        name: str = channel.name
        reason: str = close_reason.replace("'", " ")
        closed_by_id: int = closed_by.id
        content: str = await self.generate_transcript_content(
            messages = messages,
            opened_string = opened_string,
            ticket_type = ticket_type,
            ticket_number = ticket_number,
            owner = owner,
            owner_id = owner_id,
            reason = reason,
            closed_by = closed_by,
            channel_id = channel_id,
            closed_at_string = closed_at_string,
            closed_by_id = closed_by_id
        )

        link: str = await self.return_link(content = content)

        embed: discord.Embed = await self.get_ticket_log_embed(
            reason = reason,
            opened_timestamp = opened_timestamp,
            ticket_number = ticket_number,
            owner_mention = owner_mention,
            owner = owner,
            link = link,
            ticket_type = ticket_type,
            closed_at_timestamp = closed_at_timestamp,
            closed_by = closed_by
        )

        await self.send_ticket_log(guild = guild, channel = channel, embed = embed, privated = privated)
        await self.update_database(
            reason = reason,
            name = name,
            link = link,
            closed_at_timestamp = closed_at_timestamp,
            channel_id = channel_id,
            closed_by_id = closed_by_id
        )

        await channel.delete()

        ticket_count = await self.get_ticket_count()
        log_commands.info(msg = f"Closed #{name} ({channel_id}) in {str(round((time.perf_counter() - start), 2))}s by {closed_by} ({closed_by_id}) {ticket_count}")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Close(client))