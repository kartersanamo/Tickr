"""Setup wizard for new guilds."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from core.decorators import TaskDecorator
from services.guild_config_service import GuildConfigService


def _default_config() -> dict:
    with open("assets/default_guild_config.json", encoding="utf-8") as handle:
        return json.load(handle)


def _default_ticket_types() -> dict:
    with open("assets/default_ticket_types.json", encoding="utf-8") as handle:
        return json.load(handle)


class SetupView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.staff_role_id: int | None = None
        self.log_channel_id: int | None = None
        self.panel_channel_id: int | None = None
        self.category_id: int | None = None
        self.use_template = True

    @discord.ui.button(label="Start Setup", style=discord.ButtonStyle.green)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Administrator permission required.", ephemeral=True)
            return
        await interaction.response.send_message(
            "Select the **staff role** for ticket management:",
            view=StaffRoleView(self.guild_id, self),
            ephemeral=True,
        )


class StaffRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Staff role...", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        view: StaffRoleView = self.view  # type: ignore
        view.parent.staff_role_id = self.values[0].id
        await interaction.response.send_message(
            "Select the **ticket log channel** (close transcripts):",
            view=LogChannelView(view.guild_id, view.parent),
            ephemeral=True,
        )


class StaffRoleView(discord.ui.View):
    def __init__(self, guild_id: int, parent: SetupView):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.parent = parent
        self.add_item(StaffRoleSelect())


class LogChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Ticket log channel...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        view: LogChannelView = self.view  # type: ignore
        view.parent.log_channel_id = self.values[0].id
        await interaction.response.send_message(
            "Select the **panel channel** where `/send-tickets` will post:",
            view=PanelChannelView(view.guild_id, view.parent),
            ephemeral=True,
        )


class LogChannelView(discord.ui.View):
    def __init__(self, guild_id: int, parent: SetupView):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.parent = parent
        self.add_item(LogChannelSelect())


class PanelChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Ticket panel channel...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        view: PanelChannelView = self.view  # type: ignore
        view.parent.panel_channel_id = self.values[0].id
        await interaction.response.send_message(
            "Select a **ticket category** (Discord category channel):",
            view=CategoryView(view.guild_id, view.parent),
            ephemeral=True,
        )


class PanelChannelView(discord.ui.View):
    def __init__(self, guild_id: int, parent: SetupView):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.parent = parent
        self.add_item(PanelChannelSelect())


class CategorySelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Ticket category...",
            channel_types=[discord.ChannelType.category],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        view: CategoryView = self.view  # type: ignore
        view.parent.category_id = self.values[0].id
        await interaction.response.send_message(
            "Choose how to seed ticket types:",
            view=TemplateView(view.guild_id, view.parent),
            ephemeral=True,
        )


class CategoryView(discord.ui.View):
    def __init__(self, guild_id: int, parent: SetupView):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.parent = parent
        self.add_item(CategorySelect())


class TemplateView(discord.ui.View):
    def __init__(self, guild_id: int, parent: SetupView):
        super().__init__(timeout=600)
        self.guild_id = guild_id
        self.parent = parent

    @discord.ui.button(label="Use Default Template", style=discord.ButtonStyle.primary)
    async def use_template(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parent.use_template = True
        await finish_setup(interaction, self.guild_id, self.parent)

    @discord.ui.button(label="Start Empty", style=discord.ButtonStyle.secondary)
    async def start_empty(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.parent.use_template = False
        await finish_setup(interaction, self.guild_id, self.parent)


async def finish_setup(interaction: discord.Interaction, guild_id: int, state: SetupView) -> None:
    if not all([state.staff_role_id, state.log_channel_id, state.panel_channel_id, state.category_id]):
        await interaction.response.send_message("Setup incomplete.", ephemeral=True)
        return

    config = _default_config()
    config["CHANNEL_IDS"]["TICKET_LOGS_ID"] = state.log_channel_id
    config["CHANNEL_IDS"]["TICKET_CHANNEL_ID"] = state.panel_channel_id
    config["ROLE_IDS"]["STAFF_TEAM_ROLE_ID"] = state.staff_role_id
    config["TICKET_CATEGORIES"] = [state.category_id]

    if state.use_template:
        ticket_types = _default_ticket_types()
        for _cat, types in ticket_types.items():
            if _cat == "TOGGLE_STATUS":
                continue
            if isinstance(types, dict):
                for type_data in types.values():
                    if isinstance(type_data, dict):
                        type_data["Category"] = state.category_id
                        type_data["Roles"] = [state.staff_role_id]
                        type_data["Pings"] = [state.staff_role_id]
    else:
        ticket_types = {"TOGGLE_STATUS": "Enabled"}

    await GuildConfigService.create_guild(guild_id, config, ticket_types, configured=True)
    await GuildConfigService.set_configured(guild_id, True)

    embed = discord.Embed(
        title="Tickr Setup Complete",
        description=(
            f"**Staff role:** <@&{state.staff_role_id}>\n"
            f"**Log channel:** <#{state.log_channel_id}>\n"
            f"**Panel channel:** <#{state.panel_channel_id}>\n"
            f"**Ticket category:** <#{state.category_id}>\n\n"
            "Run `/send-tickets` in the panel channel to post the ticket menu.\n"
            "Use `/manage-tickets` to customize ticket types."
        ),
        color=discord.Color.green(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


class Setup(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        try:
            owner = guild.owner
            if owner:
                await owner.send(
                    f"Thanks for adding **Tickr** to **{guild.name}**!\n"
                    "Run `/setup` in your server (Administrator required) to configure tickets."
                )
        except discord.HTTPException:
            pass

    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(name="setup", description="Configure Tickr for this server")
    async def setup(self, interaction: discord.Interaction) -> None:
        if interaction.guild_id is None:
            return
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        if cfg.configured:
            await interaction.response.send_message(
                "This server is already configured. Use `/manage-tickets` to edit ticket types.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            "Welcome to **Tickr** setup! This wizard configures the minimum required settings.",
            view=SetupView(interaction.guild_id),
            ephemeral=True,
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Setup(client))
