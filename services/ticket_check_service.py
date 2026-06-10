from discord import app_commands
import discord

from core.config import ConfigManager


class TicketCheckService:
    @staticmethod
    def ticket_only():
        async def predicate(interaction: discord.Interaction) -> bool:
            if (
                not interaction.channel 
                or not isinstance(interaction.channel, discord.TextChannel)
                or not interaction.channel.category
                or interaction.channel.category.id not in ConfigManager.get(key = "TICKET_CATEGORIES")
            ):
                raise app_commands.CheckFailure("`❌` Failed! This command can only be ran inside of a ticket.")
            return True
        return app_commands.check(predicate = predicate)
    
    
is_ticket = TicketCheckService.ticket_only