"""send_tickets.py — Post ticket panel messages."""

from discord.ext import commands
from discord import app_commands
from typing import Literal
import discord

from core.decorators import TaskDecorator
from services.guild_config_service import GuildConfigService
from services.guild_guard import guild_configured_check
from services.guild_helpers import embed_color
from ui.views.ticket_logs_view import TicketLogs
from ui.views.tickets_view import TicketsView
from ui.views.tickets_view2_view import TicketsView2


class TicketsSend(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client

    @app_commands.guild_only()
    @app_commands.command(
        name="send-tickets", description="Sends the ticket panel messages"
    )
    @app_commands.describe(
        option="The message that you'd wish to send",
        channel="Channel to post the panel in (defaults to current channel)",
    )
    @app_commands.check(guild_configured_check)
    async def send_tickets(
        self,
        interaction: discord.Interaction,
        option: Literal["Tickets"],
        channel: discord.TextChannel = None,
    ) -> None:
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Invalid channel.", ephemeral=True)
            return
        await self.send_tickets_command(interaction, option, target)

    @TaskDecorator.task("SendTickets Command", True)
    async def send_tickets_command(
        self,
        interaction: discord.Interaction,
        option: str,
        channel: discord.TextChannel,
    ) -> None:
        if interaction.guild_id is None:
            return
        if not interaction.response.is_done():
            await interaction.response.send_message(
                content="`🔃` Sending your message...", ephemeral=True
            )

        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        tickets = cfg.tickets()
        color = embed_color(cfg)

        embeds = {
            "Tickets": [
                {
                    "embed": discord.Embed(
                        color=color,
                        description=(
                            "**Select a category that best represents your ticket reasoning**:\n\n"
                            "**-** Be as specific and detailed as possible in your ticket.\n"
                            "**-** A staff member will be with you as soon as possible."
                        ),
                    ),
                    "view": TicketsView.for_guild(tickets),
                    "image": None,
                },
                {
                    "embed": None,
                    "view": TicketsView2.for_guild(tickets)
                    if len(tickets) > 5
                    else None,
                    "image": None,
                },
                {
                    "embed": discord.Embed(
                        color=color,
                        description="**Want to see your previous tickets? Click the envelope down below!**",
                    ),
                    "view": TicketLogs(),
                    "image": None,
                },
            ]
        }
        chosen_message = embeds.get(option, [])
        for message in chosen_message:
            if message["view"] is None:
                continue
            embed = message["embed"]
            if embed and message["image"]:
                embed.set_image(url=message["image"])
            if embed:
                await channel.send(embed=embed, view=message["view"])
            else:
                await channel.send(view=message["view"])

        await interaction.edit_original_response(
            content="`✅` Successfully sent your message prompt!"
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(TicketsSend(client))
