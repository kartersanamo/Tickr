import json
from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from assets.dashboard_http import DashboardHttp
from core.analytics.register import CommandTrackingRegistrar
from core.app import BotApp
from core.bot_config import BotConfig
from core.database import DatabasePool
from core.decorators import TaskDecorator
from core.errors.setup import ErrorSetup
from core.guild_command_sync import GuildCommandSync
from core.loggers import log_commands, log_tasks
from ui.views.ticket_logs_view import TicketLogs
from ui.views.tickets_view import TicketsView
from ui.views.tickets_view2_view import TicketsView2


class Client(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix=".", intents=discord.Intents.all())
        ErrorSetup.wire_bot(
            bot=self,
            bot_name="Tickr",
            log_commands=log_commands,
            log_tasks=log_tasks,
        )
        self.app: BotApp = BotApp.from_bot(self)
        self.bot: commands.Bot = self
        self._reload_command: app_commands.Command[Any, Any, Any] | None = None
        self.cog_files: list[str] = [
            path.stem.title()
            for path in Path("cogs").iterdir()
            if path.suffix == ".py" and not path.name.startswith("_")
        ]

    @TaskDecorator.task(action_name="Setup Hook")
    async def setup_hook(self) -> None:
        await ErrorSetup.wire_bot_async_setup(
            bot=self,
            bot_name="Tickr",
            log_tasks=log_tasks,
        )
        self.app = BotApp.from_bot(self)
        await self._register_reload_command()
        await self._setup_cogs()
        await self._register_analytics()
        await self._add_views()
        await self._setup_dashboard_http()

    @TaskDecorator.task(action_name="Register Reload Command")
    async def _register_reload_command(self) -> None:
        @app_commands.guild_only()
        @app_commands.describe(cog="The cog to reload")
        @app_commands.autocomplete(cog=self.cog_autocomplete)
        @self.tree.command(name="tickr-reload", description="Reloads a Tickr cog")
        async def tickr_reload_slash(
            interaction: discord.Interaction,
            cog: str,
        ) -> None:
            await self.tickr_reload_command(interaction, cog)

        self._reload_command = tickr_reload_slash

    @TaskDecorator.task(action_name="Setup Cogs")
    async def _setup_cogs(self) -> None:
        loaded: list[str] = []
        for ext in (
            "services.active_ticket_cache",
            *(f"cogs.{n.lower()}" for n in self.cog_files),
        ):
            try:
                await self.load_extension(ext)
                loaded.append(ext)
            except (
                commands.ExtensionNotFound,
                commands.ExtensionAlreadyLoaded,
                commands.NoEntryPointError,
                commands.ExtensionFailed,
            ):
                log_commands.error(f"Failed to load extension {ext}")
        log_tasks.info(f"Loaded {len(loaded)} extensions")

    @TaskDecorator.task(action_name="Register Analytics")
    async def _register_analytics(self) -> None:
        await CommandTrackingRegistrar.register_command_tracking(bot=self)

    @TaskDecorator.task(action_name="Add Views")
    async def _add_views(self) -> None:
        category_names: set[str] = set[str]()
        rows: list[dict[str, str]] = DatabasePool.execute("SELECT ticket_types FROM guilds")

        for row in rows:
            types: dict[str, str] = json.loads(row.get("ticket_types") or "{}")
            for name in types.keys():
                if name != "TOGGLE_STATUS":
                    category_names.add(name)

        names: list[str] = sorted(category_names)
        views: list[discord.ui.View] = [
            TicketsView.persistent(names),
            TicketsView2.persistent(names),
            TicketLogs(),
        ]
        for view in views:
            try:
                self.add_view(view)
            except ValueError as exc:
                log_tasks.error(f"Failed to add view {view.__class__.__name__}: {exc}")

    @TaskDecorator.task(action_name="Start Dashboard HTTP")
    async def _setup_dashboard_http(self) -> None:
        await DashboardHttp.start(client=self)

    @TaskDecorator.task(action_name="Logging in")
    async def on_ready(self) -> None:
        await self._update_presence()
        await self._remove_help()
        await self._sync_command_tree()
        if self.user:
            log_tasks.info(f"Logged in as {self.user} ({self.user.id})")
        else:
            log_tasks.error("Failed to log in: no user found")

    @TaskDecorator.task(action_name="Update Presence")
    async def _update_presence(self) -> None:
        presence = BotConfig.get("PRESENCE", "Tickr Tickets")
        await self.change_presence(activity=discord.Game(name=presence))

    @TaskDecorator.task(action_name="Remove Help")
    async def _remove_help(self) -> None:
        self.remove_command("help")

    @TaskDecorator.task(action_name="Sync Command Tree")
    async def _sync_command_tree(self) -> None:
        await GuildCommandSync.sync_commands(bot=self, log=log_tasks)

    @TaskDecorator.task(action_name="Tickr Reload Command", log=True)
    async def tickr_reload_command(
        self,
        interaction: discord.Interaction,
        cog: str,
    ) -> None:
        if cog not in self.cog_files:
            await interaction.response.send_message(f"Invalid cog **{cog}.py**", ephemeral=True)
            return
        try:
            await self.reload_extension(f"cogs.{cog.lower()}")
            await interaction.response.send_message(f"Reloaded **{cog}.py**", ephemeral=True)

        except (
            commands.ExtensionNotFound,
            commands.ExtensionAlreadyLoaded,
            commands.NoEntryPointError,
            commands.ExtensionFailed,
        ) as exc:
            log_commands.error(f"Reload failed for {cog}: {exc}")
            await interaction.response.send_message(
                f"Failed to reload **{cog}.py**", ephemeral=True
            )

    async def cog_autocomplete(
        self,
        _: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        return [
            app_commands.Choice(name=cog, value=cog)
            for cog in self.cog_files
            if current.lower() in cog.lower()
        ]


client: commands.Bot = Client()

TOKEN = BotConfig.get("TOKEN")
if not TOKEN:
    missing_env_message: str = "Set DISCORD_TOKEN in .env"
    raise ValueError(missing_env_message)

if __name__ == "__main__":
    client.run(token=TOKEN, log_handler=None)
