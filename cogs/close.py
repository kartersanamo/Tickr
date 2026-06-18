"""
close.py — Close ticket, transcript, logs (multi-guild).
"""
from discord.ext import commands

from core.analytics import logger as analytics
from discord import app_commands
import datetime
import requests
import discord
import asyncio
import time
import pytz

from core.bot_config import BotConfig
from core.database import DatabasePool
from core.decorators import TaskDecorator
from core.loggers import log_commands, log_tasks
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color, format_transcript_line, optional_logo_file, set_embed_footer
from services.statistics_service import is_found
from services.ticket_check_service import is_ticket


class Close(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client

    def convert_to_est(self, timestamp: str) -> str:
        try:
            est_time = datetime.datetime.fromtimestamp(
                int(float(timestamp)), tz=pytz.utc
            ).astimezone(pytz.timezone("US/Eastern"))
            return est_time.strftime("%a, %b %d, %Y, %I:%M:%S %p") + " EST"
        except Exception as error:
            log_commands.warning(f"Failed to convert the timestamp to EST {error}")
            return "N/A"

    @TaskDecorator.task("Get Transcript Link")
    async def return_link(self, content: str, cfg) -> str:
        base_url = cfg.transcript_paste_url(BotConfig.get("TRANSCRIPT_PASTE_URL", ""))
        suffix = BotConfig.get("TRANSCRIPT_PASTE_SUFFIX", "/documents")
        if not base_url:
            return ""
        url = f"{base_url.rstrip('/')}{suffix}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(url, headers=headers, data=content.encode("utf-8"), timeout=30)
        response_data = response.json()
        key = response_data["key"]
        return f"{base_url.rstrip('/')}/{key}"

    @TaskDecorator.task("Fetch All Messages")
    async def fetch_all_messages(self, channel: discord.TextChannel) -> list[discord.Message]:
        return [message async for message in channel.history(limit=None, oldest_first=True)]

    @TaskDecorator.task("Format Embed")
    async def format_embed_content(self, embed: discord.Embed) -> str:
        message_content = ""
        lengths = []
        dictionary = embed.to_dict()
        title = dictionary.get("title", "")
        description = dictionary.get("description", "")
        fields = dictionary.get("fields", [])
        footer = dictionary.get("footer", {}).get("text", "")

        if title:
            lengths.append(len(title))
        if description:
            for line in description.split("\n"):
                lengths.append(len(line))
        for field in fields:
            lengths.append(len(field.get("name", "")))
            lengths.append(len(field.get("value", "")))
        if footer:
            lengths.append(len(footer))

        if lengths:
            max_length = min(max(lengths), 100)
        else:
            return ""

        message_content += "/" + "-" * (int(max_length) + 2) + "\\\n"
        new_line = " "
        if title:
            message_content += f"| {title:{max_length}} |\n"
            message_content += f"| {new_line:{max_length}} |\n"
        if description:
            for line in description.split("\n"):
                substrings = []
                index = 0
                while index < len(line):
                    substrings.append(line[index : index + 100])
                    index += 100
                for sub in substrings:
                    message_content += f"| {sub:{max_length}} |\n"
            message_content += f"| {new_line:{max_length}} |\n"
        for field in fields:
            field_name = field.get("name", "")
            field_value = field.get("value", "")
            message_content += f"| {field_name:{max_length}} |\n{field_value:{max_length}} |\n"
        if footer:
            message_content += f"| {footer:{max_length}} |\n"
        message_content += "\\" + "-" * (int(max_length) + 2) + "/"
        return message_content

    @TaskDecorator.task("Generate Transcript Content")
    async def generate_transcript_content(
        self,
        messages: list[discord.Message],
        opened_string: str,
        ticket_type: str,
        ticket_number: str,
        owner: discord.User,
        owner_id: int,
        reason: str,
        closed_by: discord.Member,
        channel_id: int,
        closed_at_string: str,
        closed_by_id: int,
        footer_label: str,
    ) -> str:
        content = (
            f"{footer_label}: {ticket_type}\n"
            f"- Opened by: {owner} ({owner_id})\n"
            f"- Opened at: {opened_string}\n"
            f"- Channel ID: {channel_id}\n"
            f"- Ticket ID: {ticket_number}\n \n"
            "──────────────────────────────────────────────────────\n \n"
        )
        for message in messages:
            try:
                message_content: str = message.content
                for embed in message.embeds:
                    message_content += "\n" + await self.format_embed_content(embed)
                created_at = self.convert_to_est(str(message.created_at.timestamp()))
                content += f"[{created_at}]\n{message.author.name} : {message.author.id}"
                if message_content:
                    content += f"\n\t{message_content}"
                content += "\n\n"
            except Exception as error:
                log_tasks.warning(f"Failed logging message: {error}")

        content += (
            f"──────────────────────────────────────────────────────\n\n"
            f"- Closure Reason: {reason}\n"
            f"- Closed By: {closed_by} ({closed_by_id})\n"
            f"- Closed At: {closed_at_string}"
        )
        return content

    @TaskDecorator.task("Get Ticketlog Embed")
    async def get_ticket_log(
        self,
        cfg,
        reason: str,
        opened_timestamp,
        ticket_number: str,
        owner_mention: str,
        owner: discord.User,
        link: str,
        ticket_type: str,
        closed_at_timestamp: int,
        closed_by: discord.Member,
    ) -> discord.Embed:
        delta = "N/A"
        if opened_timestamp != "N/A":
            seconds = closed_at_timestamp - opened_timestamp
            delta = self.client.app.time_format.seconds_to_format(seconds)

        desc = (
            f"`🎫` **{ticket_type} #{ticket_number}** was closed by {closed_by}\n"
            f" **Reason:** {reason}\n **Owner:** {owner_mention} / {getattr(owner, 'name', owner)}\n"
            f" **Ticket Duration:** {delta}\n{format_transcript_line(link)}"
        )
        embed = discord.Embed(color=embed_color(cfg), description=desc)
        set_embed_footer(embed, cfg)
        return embed

    @TaskDecorator.task("Send Ticketlog", False)
    async def send_ticket_log(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        embed: discord.Embed,
        privated: str,
        cfg,
    ) -> None:
        channel_json_string = (
            "ADMIN_TICKET_LOGS_ID"
            if privated == "Admin"
            else "MANAGEMENT_TICKET_LOGS_ID"
            if privated == "Management"
            else "TICKET_LOGS_ID"
        )
        ticket_log_channel_id = cfg.get(f"CHANNEL_IDS.{channel_json_string}")
        if not ticket_log_channel_id:
            return
        ticket_log_channel = guild.get_channel(int(ticket_log_channel_id))
        if ticket_log_channel is None:
            return
        logo_file = optional_logo_file(cfg)
        if logo_file:
            await ticket_log_channel.send(embed=embed, file=logo_file)
        else:
            await ticket_log_channel.send(embed=embed)

        tasks = [
            overwrite.create_dm()
            for overwrite in channel.overwrites
            if isinstance(overwrite, discord.Member)
            and not overwrite.bot
            and channel.permissions_for(overwrite).view_channel
        ]
        try:
            dm_channels = await asyncio.gather(*tasks)
            for dm in dm_channels:
                if dm:
                    if logo_file:
                        await dm.send(embed=embed, file=optional_logo_file(cfg))
                    else:
                        await dm.send(embed=embed)
        except Exception as error:
            log_tasks.warning(f"Failed to send ticket log: {error}")

    @TaskDecorator.task("Update Database")
    async def update_database(
        self,
        guild_id: int,
        closed_by: discord.Member,
        reason: str,
        name: str,
        link: str,
        closed_at_timestamp: int,
        channel_id: int,
        closed_by_id: int,
    ) -> None:
        tickets_closed_stat = await is_found(guild_id, closed_by, "tickets_closed")
        new_ticket_closed_stat = tickets_closed_stat + 1

        DatabasePool.execute(
            "UPDATE tickets SET is_active = 0, closed_by_id = %s, closed_at = %s, reason = %s, name = %s, transcript = %s WHERE guild_id = %s AND channel_id = %s",
            (closed_by_id, closed_at_timestamp, reason, name, link, guild_id, channel_id),
        )
        DatabasePool.execute(
            "UPDATE staff_statistics SET tickets_closed = %s WHERE guild_id = %s AND user_id = %s",
            (new_ticket_closed_stat, guild_id, closed_by_id),
        )
        from services.active_ticket_cache import active_ticket_cache

        active_ticket_cache.unregister(guild_id, channel_id)
        if analytics:
            analytics.increment_total_stat(guild_id, str(closed_by_id), "tickets_closed", 1)

    @TaskDecorator.task("Fetch Ticket Info")
    async def fetch_ticket_info(self, guild_id: int, channel_id: int) -> tuple:
        bot_account = self.client.user
        info = (
            bot_account,
            bot_account.id if bot_account else 0,
            bot_account.mention if bot_account else "",
            0,
            "N/A",
            "0000",
            "Unknown",
            "",
            0,
            "N/A",
        )
        row = DatabasePool.execute(
            "SELECT number, opened_at, privated, type, owner_id FROM tickets WHERE guild_id = %s AND channel_id = %s",
            (guild_id, channel_id),
        )
        if row:
            row = row[0]
            opened_timestamp = int(float(row["opened_at"]))
            opened_string = self.convert_to_est(str(opened_timestamp))
            ticket_number = row["number"]
            privated = row["privated"] or ""
            ticket_type = row["type"]
            owner = await self.client.fetch_user(int(row["owner_id"]))
            owner_id = owner.id
            owner_mention = owner.mention
            closed_at_timestamp = int(time.time())
            closed_at_string = self.convert_to_est(str(closed_at_timestamp))
            info = (
                owner,
                owner_id,
                owner_mention,
                opened_timestamp,
                opened_string,
                ticket_number,
                ticket_type,
                privated,
                closed_at_timestamp,
                closed_at_string,
            )
        return info

    @TaskDecorator.task("Get Ticket Count")
    async def get_ticket_count(self, guild_id: int) -> int:
        row = DatabasePool.execute(
            "SELECT COUNT(*) AS cnt FROM tickets WHERE guild_id = %s AND is_active = 1",
            (guild_id,),
        )
        return int(row[0]["cnt"])

    @is_ticket()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.channel_id, i.user.id))
    @app_commands.command(name="close", description="Closes the ticket channel")
    @app_commands.describe(reason="The reason for closing the ticket")
    async def close(self, interaction: discord.Interaction, reason: str) -> None:
        await self.close_command(interaction, reason)

    @TaskDecorator.task("Close Command", False)
    async def close_command(self, interaction: discord.Interaction, reason: str) -> None:
        await interaction.response.defer()
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            return
        await self.close_ticket_channel(
            interaction.guild,
            interaction.channel,
            interaction.user,
            reason,
        )

    @TaskDecorator.task("Close Ticket Channel", False)
    async def close_ticket_channel(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        closed_by: discord.Member,
        reason: str,
    ) -> None:
        start = time.perf_counter()
        cfg = await GuildConfigService.for_guild(guild.id)
        messages = await self.fetch_all_messages(channel)
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
            closed_at_string,
        ) = await self.fetch_ticket_info(guild.id, channel_id)

        name = channel.name
        reason = reason.replace("'", " ")
        closed_by_id = closed_by.id
        content = await self.generate_transcript_content(
            messages,
            opened_string,
            ticket_type,
            ticket_number,
            owner,
            owner_id,
            reason,
            closed_by,
            channel_id,
            closed_at_string,
            closed_by_id,
            cfg.get("FOOTER", "Tickr Tickets"),
        )

        link = await self.return_link(content, cfg)

        embed = await self.get_ticket_log(
            cfg,
            reason,
            opened_timestamp,
            ticket_number,
            owner_mention,
            owner,
            link,
            ticket_type,
            closed_at_timestamp,
            closed_by,
        )
        await self.send_ticket_log(guild, channel, embed, privated, cfg)
        await self.update_database(
            guild.id,
            closed_by,
            reason,
            name,
            link,
            closed_at_timestamp,
            channel_id,
            closed_by_id,
        )

        await channel.delete()

        ticket_count = await self.get_ticket_count(guild.id)
        log_commands.info(
            f"Closed #{name} ({channel_id}) in {round((time.perf_counter() - start), 2)}s "
            f"by {closed_by} ({closed_by_id}) {ticket_count}"
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Close(client))
