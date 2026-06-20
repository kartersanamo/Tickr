import discord

from core.loggers import log_tasks
from ui.modals.questions import Questions


class InfoButton(discord.ui.View):
    def __init__(self, ticket_type: str, ticket_info: dict, guild_id: int) -> None:
        super().__init__(timeout=None)
        self.ticket_type = ticket_type
        self.ticket_info = ticket_info
        self.guild_id = guild_id

    @discord.ui.button(
        label="Enter Information",
        style=discord.ButtonStyle.grey,
        custom_id="enter_information",
    )
    async def enter_information_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        try:
            guild_id = interaction.guild_id or self.guild_id
            await interaction.response.send_modal(
                Questions(self.ticket_type, self.ticket_info, guild_id)
            )
            log_tasks.info(
                f"Sent Questions modal to {interaction.user} ({interaction.user.id})"
            )
        except Exception as exc:
            log_tasks.error(f"Failed to send Questions modal: {exc}")
