import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)

import discord
from discord.ext import commands
from discord import app_commands

from core.guild_command_sync import sync_guild_commands
from core.loggers import log_commands, log_tasks
from core.config import ConfigManager
from core.decorators import task
from core.app import BotApp


COG_FILES = [file.split(".")[0].title() for file in os.listdir("cogs/") if file.endswith(".py")]


class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix = '.', intents = discord.Intents().all())
        self.app: BotApp
    
    @task("Setup Cogs")
    async def setup_cogs(self):
        if COG_FILES is None:
            log_tasks.warning("No cog files to load, skipping.")
        for ext in COG_FILES:
            await self.load_extension("cogs." + ext.lower())
            log_tasks.info(f"Loaded cog {ext}.py")
    
    @task("Add Views")
    async def add_views(self):
        views: list[discord.ui.View] = []
        if views is None:
            log_tasks.warning("No views to add, skipping.")
        for view in views:
            self.add_view(view)
            log_tasks.info(f"Added view {view.__class__.__name__}")
    
    @task("Update Presence")
    async def update_presence(self):
        presence = ConfigManager.get("PRESENCE")
        await client.change_presence(activity = discord.Game(name = presence))
        log_tasks.info(f"Updated the bot's presence to {presence}")
    
    @task("Remove Help")
    async def remove_help(self):
        client.remove_command("help")
    
    @task("Sync Command Tree")
    async def sync_command_tree(self):
        await sync_guild_commands(
            self,
            config_guild_id = ConfigManager.get("GUILD_ID"),
            log = log_tasks
        )
    
    @task("Setup Hook")
    async def setup_hook(self):
        self.app = BotApp.from_bot(self)
        await self.setup_cogs()
        await self.add_views()
    
    @task("Logging in")
    async def on_ready(self):
        await self.update_presence()
        await self.remove_help()
        await self.sync_command_tree()
        if self.user:
            log_tasks.info(f"Logged in as {self.user} ({self.user.id})")


client: commands.Bot = Client()


@task("Tickr Reload Command", True)
async def tickr_reload_command(interaction: discord.Interaction, cog: str):
    if interaction.guild is None:
        return await interaction.response.send_message(content = "Commands cannot be ran in DMs!", ephemeral = True)
    if cog not in COG_FILES:
        return await interaction.response.send_message(content = f"Invalid cog name **cog.py**", ephemeral = True)

    await client.reload_extension(f"cogs.{cog.lower()}")
    await interaction.response.send_message(content = f"Successfully reloaded **{cog}.py**", ephemeral = True)

async def cog_autocomplete(_: discord.Interaction, current: str) -> list[app_commands.Choice]:
    return [
        app_commands.Choice(name = cog, value = cog)
        for cog in COG_FILES if current.lower() in cog.lower()
    ]

@client.tree.command(name = "tickr-reload", description = "Reloads a Tickr Cog Class")
@app_commands.autocomplete(cog = cog_autocomplete)
async def tickrreload(interaction: discord.Interaction, cog: str):
    await tickr_reload_command(interaction = interaction, cog = cog)

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Set DISCORD_TOKEN in .env")

if __name__ == "__main__":
    client.run(token = TOKEN)