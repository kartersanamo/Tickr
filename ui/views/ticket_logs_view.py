import discord

from core.database import DatabasePool
from core.decorators import TaskDecorator
from core.loggers import log_tasks
from services.guild_config_service import GuildConfigService
from services.guild_helpers import format_transcript_line
from ui.views.paginator import paginator_for_cfg


class TicketLogs(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(emoji="📨", style=discord.ButtonStyle.grey, custom_id="request_tickets_button")
    async def request(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.request_tickets(interaction, button)

    @TaskDecorator.task("Get Data", False)
    async def get_data(self, guild_id: int, user_id: int):
        rows = DatabasePool.execute(
            "SELECT opened_at, name, type, transcript, reason FROM tickets "
            "WHERE guild_id = %s AND owner_id = %s AND is_active = 0 ORDER BY opened_at",
            (guild_id, user_id),
        )
        data: list = []
        for row in rows:
            opened_at = int(float(row["opened_at"]))
            ticket_info = (
                f"`📖` **Ticket:** {row['name']} ({row['type']})\n"
                f"{format_transcript_line(row['transcript'])}\n"
                f" **Created At:** <t:{opened_at}:f>\n"
                f" **Closure Reason:** {row['reason']}\n"
            )
            data.append(ticket_info)
        if not data:
            data = ["No data found."]
        else:
            data.reverse()
        return data

    @TaskDecorator.task("Paginate Send", False)
    async def paginate_send(self, interaction: discord.Interaction, data: list[str]):
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        paginate = paginator_for_cfg(cfg)
        paginate.title = f"{interaction.user.name}'s Tickets"
        paginate.sep = 5
        paginate.data = data
        await paginate.send(interaction)

    @TaskDecorator.task("Request Tickets", False)
    async def request_tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild_id is None:
            return
        await interaction.response.send_message(content="...", ephemeral=True)
        data = await self.get_data(interaction.guild_id, interaction.user.id)
        await self.paginate_send(interaction, data)
        log_tasks.info(f"Sent ticket logs button to {interaction.user} ({interaction.user.id})")
