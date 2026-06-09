from discord.ext import commands
from discord import app_commands
import discord

from services.ticket_check_service import is_ticket
from core.config import ConfigManager
from core.loggers import log_commands
from core.database import execute
from core.decorators import task


class Add(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client


    @task(action_name = "Check Blacklisted", log = False)
    async def check_blacklisted(self, interaction: discord.Interaction, user: discord.Member) -> bool:
        rows = execute(query = "SELECT 1 FROM blacklists WHERE user_id = %s LIMIT 1", params = (user.id,))
        if rows:
            if interaction.channel is None:
                log_commands.warning(msg = f"{interaction.user} ({interaction.user.id}) returned a NONE interaction.channel for 'Check Blacklisted' task")
                await interaction.response.send_message(content = "`❌` Failed! Unknown channel")
                return True
            if isinstance(interaction.channel, discord.DMChannel):
                log_commands.warning(msg = f"{interaction.user} ({interaction.user.id}) attempted to check blacklisted in a DM channel")
                await interaction.response.send_message(content = "`❌` Failed! This cannot be ran in a DM Channel")
                return True

            log_commands.warning(msg = f"Failed to add {user} ({user.id}) to #{interaction.channel.name} ({interaction.channel.id}) as they are ticket blacklisted")
            return True
        
        return False
    

    @task(action_name = "Check Timed Out", log = False)
    async def check_timed_out(self, interaction: discord.Interaction, user: discord.Member) -> bool:
        if user.is_timed_out():
            if interaction.channel is None:
                log_commands.warning(msg = f"{interaction.user} ({interaction.user.id}) returned a NONE interaction.channel for 'Check Timed Out' task")
                await interaction.response.send_message(content = "`❌` Failed! Unknown channel")
                return True
            if isinstance(interaction.channel, discord.DMChannel):
                log_commands.warning(msg = f"{interaction.user} ({interaction.user.id}) attempted to check timed out in a DM channel")
                await interaction.response.send_message(content = "`❌` Failed! This cannot be ran in a DM Channel")
                return True

            log_commands.warning(msg = f"Failed to add user {user} ({user.id}) to #{interaction.channel.name} ({interaction.channel.id}) as they are timed out")
            await interaction.response.send_message(content = "`❌` Failed! You cannot add this player to the ticket as they are currently timed out!", ephemeral = True)

    @task(action_name = "Set Permissions", log = False)
    async def set_permissions(self, channel: discord.TextChannel, user: discord.Member) -> None:
        perms = channel.overwrites_for(user)
        perms.view_channel = True
        perms.send_messages = True
        await channel.set_permissions(target = user, overwrite = perms)
    
    @task(action_name = "Send Embed", log = False)
    async def send_embed(self, interaction: discord.Interaction, user: discord.Member) -> None:
        if interaction.channel is None:
            log_commands.warning(msg = f"{interaction.user} ({interaction.user.id}) returned a NONE interaction.channel for 'Send Embed' task")
            await interaction.response.send_message(content = "`❌` Failed! Unknown channel")
            return 
        embed: discord.Embed = discord.Embed(
            color = discord.Color.from_str(value = ConfigManager.get(key = "EMBED_COLOR")),
            description = f"{interaction.user.mention} has added {user.mention} to the ticket {interaction.channel.mention}"
        )
        logo_url: str = self.client.app.embeds.get_logo_url(ConfigManager.get("LOGO")) #type: ignore
        embed.set_footer(text = ConfigManager.get(key = "FOOTER"), icon_url = logo_url)
        await interaction.response.send_message(embed = embed, file = discord.File("assets/Logo.png"))
    
    @is_ticket()
    @app_commands.guild_only()
    @app_commands.command(name = "add", description = "Adds a user to the ticket")
    @app_commands.describe(user = "The user to add to the ticket")
    async def add(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await self.add_command(interaction = interaction, user = user)
    
    @task(action_name = "Add Command", log = True)
    async def add_command(self, interaction: discord.Interaction, user: discord.Member) -> None:
        blacklisted: bool = await self.check_blacklisted(interaction = interaction, user = user)
        timed_out: bool = await self.check_timed_out(interaction = interaction, user = user)

        if not blacklisted and not timed_out:
            if not isinstance(interaction.channel, discord.TextChannel):
                log_commands.warning(msg = f"{interaction.user} ({interaction.user.id}) tried to run the add command NOT in a text channel")
                await interaction.response.send_message(content = "`❌` Failed! This command must be ran in a text channel")
                return 
            await self.set_permissions(channel = interaction.channel, user = user)
            await self.send_embed(interaction = interaction, user = user)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Add(client))