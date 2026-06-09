from discord.ext import commands

from services.ticket_check_service import TicketCheckService
from repositories.ticket_repository import TicketRepository
from services.time_format_service import TimeFormatService
from services.ticket_service import TicketService
from services.embed_service import EmbedService
from core.database import DatabasePool
from core.config import ConfigManager


class BotApp:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.settings = ConfigManager.all()
        self.db = DatabasePool.get()
        self.tickets_repo = TicketRepository(self.db)
        self.tickets = TicketService(self.tickets_repo, self.settings)
        self.ticket_checks = TicketCheckService()

    @classmethod
    def from_bot(cls, bot: commands.Bot) -> "BotApp":
        return cls(bot)