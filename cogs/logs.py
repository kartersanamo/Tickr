"""Command usage logging."""

from discord.ext import commands
import discord

from core.loggers import log_commands


class Logs(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:
            name = f"/{interaction.command.name}"
            try:
                for option in interaction.data.get("options") or []:
                    name += f" {option['name']}:'{option['value']}'"
            except (KeyError, TypeError):
                pass
            log_commands.info(
                f"{interaction.user} ({interaction.user.id}) ran {name} "
                f"in #{interaction.channel} ({getattr(interaction.channel, 'id', None)})"
            )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Logs(client))
