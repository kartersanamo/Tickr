"""Expanded first-time setup wizard views."""

from __future__ import annotations

from dataclasses import dataclass, field

import discord

from services.guild_config_fields import merge_defaults, validate_required
from services.guild_config_service import GuildConfigService


def _default_config() -> dict:
    from services.guild_config_service import GuildConfigService

    return GuildConfigService._default_config()


def _default_ticket_types() -> dict:
    from services.guild_config_service import GuildConfigService

    return GuildConfigService._default_ticket_types()


@dataclass
class SetupState:
    guild_id: int
    staff_role_id: int | None = None
    admin_perms_role_id: int | None = None
    log_channel_id: int | None = None
    panel_channel_id: int | None = None
    ticket_category_ids: list[int] = field(default_factory=list)
    admin_private_category_id: int | None = None
    management_private_category_id: int | None = None
    admin_ticket_logs_id: int | None = None
    management_ticket_logs_id: int | None = None
    verified_role_id: int | None = None
    verify_channel_id: int | None = None
    footer: str | None = None
    embed_color: str | None = None
    transcript_paste_url: str | None = None
    use_template: bool = True


class SetupView(discord.ui.View):
    def __init__(self, guild_id: int) -> None:
        super().__init__(timeout=900)
        self.state = SetupState(guild_id=guild_id)

    @discord.ui.button(label="Start Setup", style=discord.ButtonStyle.green)
    async def start(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Administrator permission required.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            "**Step 1/11 — Staff role**\nSelect the role that manages tickets and gets pinged:",
            view=StaffRoleView(self.state),
            ephemeral=True,
        )


class StaffRoleSelect(discord.ui.RoleSelect):
    async def callback(self, interaction: discord.Interaction) -> None:
        view: StaffRoleView = self.view  # type: ignore
        view.state.staff_role_id = self.values[0].id
        await interaction.response.send_message(
            "**Step 2/11 — Admin permissions role**\n"
            "Select the role allowed to use `/manage-tickets` and `/manage-config`:",
            view=AdminPermsRoleView(view.state),
            ephemeral=True,
        )


class StaffRoleView(discord.ui.View):
    def __init__(self, state: SetupState) -> None:
        super().__init__(timeout=900)
        self.state = state
        self.add_item(
            StaffRoleSelect(placeholder="Staff role...", min_values=1, max_values=1)
        )


class AdminPermsRoleSelect(discord.ui.RoleSelect):
    async def callback(self, interaction: discord.Interaction) -> None:
        view: AdminPermsRoleView = self.view  # type: ignore
        view.state.admin_perms_role_id = self.values[0].id
        await interaction.response.send_message(
            "**Step 3/11 — Ticket log channel**\nSelect where close transcripts are posted:",
            view=LogChannelView(view.state),
            ephemeral=True,
        )


class AdminPermsRoleView(discord.ui.View):
    def __init__(self, state: SetupState) -> None:
        super().__init__(timeout=900)
        self.state = state
        self.add_item(
            AdminPermsRoleSelect(
                placeholder="Admin perms role...", min_values=1, max_values=1
            )
        )


class LogChannelSelect(discord.ui.ChannelSelect):
    async def callback(self, interaction: discord.Interaction) -> None:
        view: LogChannelView = self.view  # type: ignore
        view.state.log_channel_id = self.values[0].id
        await interaction.response.send_message(
            "**Step 4/11 — Ticket panel channel**\nSelect where `/send-tickets` will post:",
            view=PanelChannelView(view.state),
            ephemeral=True,
        )


class LogChannelView(discord.ui.View):
    def __init__(self, state: SetupState) -> None:
        super().__init__(timeout=900)
        self.state = state
        self.add_item(
            LogChannelSelect(
                placeholder="Ticket log channel...",
                channel_types=[discord.ChannelType.text, discord.ChannelType.news],
                min_values=1,
                max_values=1,
            )
        )


class PanelChannelSelect(discord.ui.ChannelSelect):
    async def callback(self, interaction: discord.Interaction) -> None:
        view: PanelChannelView = self.view  # type: ignore
        view.state.panel_channel_id = self.values[0].id
        await interaction.response.send_message(
            "**Step 5/11 — Ticket categories**\nSelect one or more Discord categories for tickets:",
            view=TicketCategoriesView(view.state),
            ephemeral=True,
        )


class PanelChannelView(discord.ui.View):
    def __init__(self, state: SetupState) -> None:
        super().__init__(timeout=900)
        self.state = state
        self.add_item(
            PanelChannelSelect(
                placeholder="Ticket panel channel...",
                channel_types=[discord.ChannelType.text, discord.ChannelType.news],
                min_values=1,
                max_values=1,
            )
        )


class TicketCategoriesSelect(discord.ui.ChannelSelect):
    async def callback(self, interaction: discord.Interaction) -> None:
        view: TicketCategoriesView = self.view  # type: ignore
        view.state.ticket_category_ids = [channel.id for channel in self.values]
        await interaction.response.send_message(
            "**Step 6/11 — Private ticket categories (optional)**\n"
            "Select the **admin-private** category, or skip:",
            view=AdminPrivateCategoryView(view.state),
            ephemeral=True,
        )


class TicketCategoriesView(discord.ui.View):
    def __init__(self, state: SetupState) -> None:
        super().__init__(timeout=900)
        self.state = state
        self.add_item(
            TicketCategoriesSelect(
                placeholder="Ticket categories...",
                channel_types=[discord.ChannelType.category],
                min_values=1,
                max_values=10,
            )
        )


class AdminPrivateCategorySelect(discord.ui.ChannelSelect):
    async def callback(self, interaction: discord.Interaction) -> None:
        view: AdminPrivateCategoryView = self.view  # type: ignore
        view.state.admin_private_category_id = self.values[0].id
        await _goto_management_private(interaction, view.state)


class AdminPrivateCategoryView(discord.ui.View):
    def __init__(self, state: SetupState) -> None:
        super().__init__(timeout=900)
        self.state = state
        self.add_item(
            AdminPrivateCategorySelect(
                placeholder="Admin private category...",
                channel_types=[discord.ChannelType.category],
                min_values=1,
                max_values=1,
            )
        )

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, row=1)
    async def skip(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await _goto_management_private(interaction, self.state)


async def _goto_management_private(
    interaction: discord.Interaction, state: SetupState
) -> None:
    await interaction.response.send_message(
        "**Step 7/11 — Management private category (optional)**",
        view=ManagementPrivateCategoryView(state),
        ephemeral=True,
    )


class ManagementPrivateCategorySelect(discord.ui.ChannelSelect):
    async def callback(self, interaction: discord.Interaction) -> None:
        view: ManagementPrivateCategoryView = self.view  # type: ignore
        view.state.management_private_category_id = self.values[0].id
        await _goto_verified_role(interaction, view.state)


class ManagementPrivateCategoryView(discord.ui.View):
    def __init__(self, state: SetupState) -> None:
        super().__init__(timeout=900)
        self.state = state
        self.add_item(
            ManagementPrivateCategorySelect(
                placeholder="Management private category...",
                channel_types=[discord.ChannelType.category],
                min_values=1,
                max_values=1,
            )
        )

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, row=1)
    async def skip(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await _goto_verified_role(interaction, self.state)


async def _goto_verified_role(
    interaction: discord.Interaction, state: SetupState
) -> None:
    await interaction.response.send_message(
        "**Step 8/11 — Verified role (optional)**\n"
        "Require a role before members can open tickets:",
        view=VerifiedRoleView(state),
        ephemeral=True,
    )


class VerifiedRoleSelect(discord.ui.RoleSelect):
    async def callback(self, interaction: discord.Interaction) -> None:
        view: VerifiedRoleView = self.view  # type: ignore
        view.state.verified_role_id = self.values[0].id
        await interaction.response.send_message(
            "**Step 9/11 — Verify channel**\n"
            "Select the channel verified members must be able to read:",
            view=VerifyChannelView(view.state),
            ephemeral=True,
        )


class VerifiedRoleView(discord.ui.View):
    def __init__(self, state: SetupState) -> None:
        super().__init__(timeout=900)
        self.state = state
        self.add_item(
            VerifiedRoleSelect(
                placeholder="Verified role...", min_values=1, max_values=1
            )
        )

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, row=1)
    async def skip(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await _goto_branding(interaction, self.state)


class VerifyChannelSelect(discord.ui.ChannelSelect):
    async def callback(self, interaction: discord.Interaction) -> None:
        view: VerifyChannelView = self.view  # type: ignore
        view.state.verify_channel_id = self.values[0].id
        await _goto_branding(interaction, view.state)


class VerifyChannelView(discord.ui.View):
    def __init__(self, state: SetupState) -> None:
        super().__init__(timeout=900)
        self.state = state
        self.add_item(
            VerifyChannelSelect(
                placeholder="Verify channel...",
                channel_types=[discord.ChannelType.text, discord.ChannelType.news],
                min_values=1,
                max_values=1,
            )
        )


async def _goto_branding(interaction: discord.Interaction, state: SetupState) -> None:
    await interaction.response.send_modal(SetupBrandingModal(state))


class SetupBrandingModal(discord.ui.Modal, title="Step 10/11 — Branding"):
    footer_input = discord.ui.TextInput(
        label="Embed footer text",
        default="Tickr Tickets",
        required=False,
        max_length=128,
    )
    color_input = discord.ui.TextInput(
        label="Embed color (hex)",
        default="0x5865F2",
        required=False,
        max_length=16,
    )
    transcript_input = discord.ui.TextInput(
        label="Transcript paste URL (optional)",
        required=False,
        max_length=256,
        placeholder="https://paste.example.com",
    )

    def __init__(self, state: SetupState) -> None:
        super().__init__()
        self.state = state

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.state.footer = self.footer_input.value.strip() or None
        self.state.embed_color = self.color_input.value.strip() or None
        self.state.transcript_paste_url = self.transcript_input.value.strip() or None
        await interaction.response.send_message(
            "**Step 11/11 — Ticket types**\nChoose how to seed ticket types:",
            view=TemplateView(self.state),
            ephemeral=True,
        )


class TemplateView(discord.ui.View):
    def __init__(self, state: SetupState) -> None:
        super().__init__(timeout=900)
        self.state = state

    @discord.ui.button(label="Use Default Template", style=discord.ButtonStyle.primary)
    async def use_template(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.state.use_template = True
        await finish_setup(interaction, self.state)

    @discord.ui.button(label="Start Empty", style=discord.ButtonStyle.secondary)
    async def start_empty(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.state.use_template = False
        await finish_setup(interaction, self.state)


async def finish_setup(interaction: discord.Interaction, state: SetupState) -> None:
    required = [
        state.staff_role_id,
        state.admin_perms_role_id,
        state.log_channel_id,
        state.panel_channel_id,
        state.ticket_category_ids,
    ]
    if not all(required):
        await interaction.response.send_message("Setup incomplete.", ephemeral=True)
        return

    config = _default_config()
    config["CHANNEL_IDS"]["TICKET_LOGS_ID"] = state.log_channel_id
    config["CHANNEL_IDS"]["TICKET_CHANNEL_ID"] = state.panel_channel_id
    config["ROLE_IDS"]["STAFF_TEAM_ROLE_ID"] = state.staff_role_id
    config["ROLE_IDS"]["ADMINISTRATOR_PERMS_ROLE_ID"] = state.admin_perms_role_id
    config["TICKET_CATEGORIES"] = state.ticket_category_ids

    if state.admin_private_category_id:
        config["CHANNEL_IDS"]["ADMIN_PRIVATE_CATEGORY_ID"] = (
            state.admin_private_category_id
        )
    if state.management_private_category_id:
        config["CHANNEL_IDS"]["MANAGEMENT_PRIVATE_CATEGORY_ID"] = (
            state.management_private_category_id
        )
    if state.admin_ticket_logs_id:
        config["CHANNEL_IDS"]["ADMIN_TICKET_LOGS_ID"] = state.admin_ticket_logs_id
    else:
        config["CHANNEL_IDS"]["ADMIN_TICKET_LOGS_ID"] = state.log_channel_id
    if state.management_ticket_logs_id:
        config["CHANNEL_IDS"]["MANAGEMENT_TICKET_LOGS_ID"] = (
            state.management_ticket_logs_id
        )
    else:
        config["CHANNEL_IDS"]["MANAGEMENT_TICKET_LOGS_ID"] = state.log_channel_id
    if state.verified_role_id:
        config["ROLE_IDS"]["VERIFIED_ROLE_ID"] = state.verified_role_id
    if state.verify_channel_id:
        config["CHANNEL_IDS"]["VERIFY_CHANNEL_ID"] = state.verify_channel_id
    if state.footer:
        config["FOOTER"] = state.footer
    if state.embed_color:
        from services.guild_helpers import normalize_embed_color

        config["EMBED_COLOR"] = normalize_embed_color(state.embed_color)
    if state.transcript_paste_url:
        config["TRANSCRIPT_PASTE_URL"] = state.transcript_paste_url

    primary_category = state.ticket_category_ids[0]
    staff_role = state.staff_role_id

    if state.use_template:
        ticket_types = _default_ticket_types()
        for _cat, types in ticket_types.items():
            if _cat == "TOGGLE_STATUS":
                continue
            if isinstance(types, dict):
                for type_data in types.values():
                    if isinstance(type_data, dict):
                        type_data["Category"] = primary_category
                        type_data["Roles"] = [staff_role]
                        type_data["Pings"] = [staff_role]
    else:
        ticket_types = {"TOGGLE_STATUS": "Enabled"}

    await GuildConfigService.create_guild(
        state.guild_id, config, ticket_types, configured=True
    )
    await GuildConfigService.set_configured(state.guild_id, True)

    missing = validate_required(merge_defaults(config))
    categories_text = ", ".join(f"<#{cat_id}>" for cat_id in state.ticket_category_ids)

    embed = discord.Embed(
        title="Tickr Setup Complete",
        description=(
            f"**Staff role:** <@&{state.staff_role_id}>\n"
            f"**Admin perms role:** <@&{state.admin_perms_role_id}>\n"
            f"**Log channel:** <#{state.log_channel_id}>\n"
            f"**Panel channel:** <#{state.panel_channel_id}>\n"
            f"**Ticket categories:** {categories_text}\n\n"
            "Run `/send-tickets` in the panel channel to post the ticket menu.\n"
            "Use `/manage-tickets` for ticket types and `/manage-config` for all other settings."
        ),
        color=discord.Color.green(),
    )
    if missing:
        embed.add_field(name="Still missing", value=", ".join(missing), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)
