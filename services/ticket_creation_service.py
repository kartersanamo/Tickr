from __future__ import annotations

import os
import time

import aiohttp
import discord

from core.bot_config import BotConfig
from core.database import DatabasePool
from core.decorators import TaskDecorator
from core.loggers import log_tasks
from services.embed_service import EmbedService
from services.guild_config_service import GuildConfig, GuildConfigService
from services.guild_helpers import embed_color


class TicketCreationService:
    @TaskDecorator.task("Check Cooldown Bypass", False)
    async def has_ticket_cooldown_bypass(
        self, interaction: discord.Interaction, cfg: GuildConfig
    ) -> bool:
        role_ids = cfg.get("ROLE_IDS", {})
        bypass_ids = {
            int(role_ids.get("STAFF_TEAM_ROLE_ID", 0) or 0),
            int(role_ids.get("ADMINISTRATOR_PERMS_ROLE_ID", 0) or 0),
        }
        bypass_ids.discard(0)
        if not bypass_ids:
            return False
        user = interaction.user
        if not isinstance(user, discord.Member):
            return False
        member_role_ids = {int(r.id) for r in user.roles}
        return bool(member_role_ids & bypass_ids)

    async def notify_dashboard_new_ticket(
        self,
        channel: discord.TextChannel,
        number: int,
        ticket_type: str,
        owner_id: int,
        guild_id: int,
    ) -> None:
        base_url = BotConfig.get("DASHBOARD_URL", "")
        endpoint = os.getenv("DASHBOARD_TICKET_NOTIFY_URL", "").strip() or (
            f"{base_url}/api/tickets/live-events" if base_url else ""
        )
        secret = BotConfig.get("TICKETS_BOT_API_SECRET")
        if not endpoint or not secret:
            return

        payload = {
            "kind": "ticket_created",
            "guildId": str(guild_id),
            "channelId": str(channel.id),
            "ticketNumber": str(number),
            "ticketType": str(ticket_type),
            "ownerId": str(owner_id),
            "channelName": str(channel.name),
        }
        headers = {"X-Tickets-Key": secret, "Content-Type": "application/json"}
        timeout = aiohttp.ClientTimeout(total=2.5)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    endpoint, json=payload, headers=headers
                ) as resp:
                    if resp.status >= 400:
                        body = await resp.text()
                        log_tasks.warning(
                            f"Dashboard new-ticket notify failed ({resp.status}): {body[:200]}"
                        )
        except Exception as exc:
            log_tasks.warning(f"Dashboard new-ticket notify error: {exc}")

    @TaskDecorator.task("Get Ticket Count", False)
    async def get_ticket_count(self, guild_id: int) -> int:
        row = DatabasePool.execute(
            "SELECT COUNT(*) AS cnt FROM tickets WHERE guild_id = %s AND is_active = 1",
            (guild_id,),
        )
        return int(row[0]["cnt"])

    @TaskDecorator.task("Check Verified", False)
    async def check_verified(
        self, interaction: discord.Interaction, cfg: GuildConfig
    ) -> str | None:
        guild = interaction.guild
        if guild is None:
            return "`❌` You must be in a server to do this!"
        verified_id = cfg.get("ROLE_IDS.VERIFIED_ROLE_ID")
        if not verified_id:
            return None
        role = guild.get_role(int(verified_id))
        if role is None:
            return "`❌` The verified role was not found!"
        user = interaction.user
        if not isinstance(user, discord.Member):
            return "`❌` You must be a member of the server to do this!"
        if role not in user.roles:
            channel_id = cfg.get("CHANNEL_IDS.VERIFY_CHANNEL_ID")
            if channel_id is None:
                return "`❌` The verify channel was not found!"
            channel = guild.get_channel(int(channel_id))
            if channel is None:
                return "`❌` The verify channel was not found!"
            log_tasks.warning(
                f"{interaction.user} ({interaction.user.id}) is not verified and tried to open a ticket"
            )
            return f"`❌` You are not verified! Go to the {channel.mention} channel and verify yourself first."
        return None

    @TaskDecorator.task("Check 5 Tickets", False)
    async def check_5_tickets(
        self, interaction: discord.Interaction, guild_id: int
    ) -> str | None:
        row = DatabasePool.execute(
            "SELECT COUNT(*) AS open_ticket_count FROM tickets WHERE guild_id = %s AND owner_id = %s AND is_active = 1",
            (guild_id, interaction.user.id),
        )
        open_ticket_count = row[0]["open_ticket_count"]
        if open_ticket_count >= 5:
            log_tasks.warning(
                f"{interaction.user} ({interaction.user.id}) has 5 tickets open and tried to open a ticket"
            )
            return "`❌` Failed! You already have **5** tickets open!"
        return None

    @TaskDecorator.task("Check Blacklisted", False)
    async def check_blacklisted(
        self, interaction: discord.Interaction, guild_id: int
    ) -> str | None:
        row = DatabasePool.execute(
            "SELECT reason FROM blacklists WHERE guild_id = %s AND user_id = %s",
            (guild_id, interaction.user.id),
        )
        if row:
            blacklist_reason = row[0]["reason"]
            log_tasks.warning(
                f"{interaction.user} ({interaction.user.id}) is blacklisted from tickets"
            )
            return f"`❌` You are currently **blacklisted** from creating tickets for the following reason\n```{blacklist_reason}```"
        return None

    @TaskDecorator.task("Check Disabled", False)
    async def check_disabled(
        self, interaction: discord.Interaction, cfg: GuildConfig
    ) -> str | None:
        if not cfg.tickets_globally_enabled():
            log_tasks.warning(
                f"{interaction.user} ({interaction.user.id}) tried to open a ticket when tickets are disabled"
            )
            return "`❌` Tickets are currently unavailable, please check again shortly."

        data = interaction.data
        if data is None:
            return "`❌` The data was not found!"
        category_name = data.get("custom_id")
        if category_name is None:
            return "`❌` The category name was not found!"
        values = data.get("values")
        if values is None or not isinstance(values, list):
            return "`❌` The values were not found!"
        ticket_type = values[0]
        if ticket_type is None:
            return "`❌` The ticket type was not found!"
        tickets = cfg.tickets()
        category_data = tickets.get(category_name, {})
        ticket_data = category_data.get(ticket_type, {})

        if ticket_data.get("Status") == "Disabled":
            log_tasks.warning(
                f"{interaction.user} ({interaction.user.id}) tried to open a disabled {category_name} ticket"
            )
            return f"`❌` {category_name} tickets are currently unavailable, please check again shortly."
        return None

    @TaskDecorator.task("Check Recent Open", False)
    async def check_recent_open(
        self, interaction: discord.Interaction, guild_id: int, cfg: GuildConfig
    ) -> str | None:
        if await self.has_ticket_cooldown_bypass(interaction, cfg):
            return None
        row = DatabasePool.execute(
            """
            SELECT opened_at FROM tickets
            WHERE guild_id = %s AND owner_id = %s
            ORDER BY opened_at DESC
            LIMIT 1
            """,
            (guild_id, interaction.user.id),
        )

        if row:
            last_opened = float(row[0]["opened_at"])
            if time.time() - last_opened < 300:
                log_tasks.warning(
                    f"{interaction.user} ({interaction.user.id}) opened a ticket too recently"
                )
                return "`❌` You're opening tickets too fast! Please try again later."
        return None

    @TaskDecorator.task("Check Recent Closed", False)
    async def check_recent_closed(
        self, interaction: discord.Interaction, guild_id: int, cfg: GuildConfig
    ) -> str | None:
        if await self.has_ticket_cooldown_bypass(interaction, cfg):
            return None
        row = DatabasePool.execute(
            """
            SELECT closed_at FROM tickets
            WHERE guild_id = %s AND owner_id = %s AND is_active = 0
            ORDER BY closed_at DESC
            LIMIT 1
            """,
            (guild_id, interaction.user.id),
        )

        if row and row[0]["closed_at"]:
            last_closed = int(row[0]["closed_at"])
            if time.time() - last_closed < 120:
                log_tasks.warning(
                    f"{interaction.user} ({interaction.user.id}) had a recently closed ticket"
                )
                return "`❌` Your last ticket was just closed! Please try again later."
        return None

    @TaskDecorator.task("Check", False)
    async def check(
        self, interaction: discord.Interaction, cfg: GuildConfig
    ) -> str | None:
        guild_id = interaction.guild_id
        if guild_id is None:
            return "`❌` You must be in a server to do this!"

        check_functions = [
            lambda: self.check_verified(interaction, cfg),
            lambda: self.check_5_tickets(interaction, guild_id),
            lambda: self.check_blacklisted(interaction, guild_id),
            lambda: self.check_disabled(interaction, cfg),
            lambda: self.check_recent_open(interaction, guild_id, cfg),
            lambda: self.check_recent_closed(interaction, guild_id, cfg),
        ]

        for check_function in check_functions:
            error = await check_function()
            if error:
                return error
        return None

    @TaskDecorator.task("Get Ticket Number", False)
    async def get_number(self, guild_id: int) -> int:
        row = DatabasePool.execute(
            "SELECT COUNT(*) AS cnt FROM tickets WHERE guild_id = %s",
            (guild_id,),
        )
        return int(row[0]["cnt"]) + 1

    @TaskDecorator.task("Create Ticket", False)
    async def create_ticket(
        self, interaction: discord.Interaction, cfg: GuildConfig
    ) -> discord.TextChannel | None:
        data = interaction.data
        if data is None:
            return None
        custom_id = data.get("custom_id")
        if custom_id is None:
            return None
        values = data.get("values")
        if values is None or not isinstance(values, list) or not values:
            return None
        ticket_type_name = values[0]
        if not isinstance(ticket_type_name, str):
            return None
        tickets = cfg.tickets()
        category_tickets = tickets.get(custom_id)
        if not category_tickets:
            return None
        ticket_info = category_tickets.get(ticket_type_name)
        if ticket_info is None:
            return None
        ticket_type = f"{custom_id} ({ticket_type_name})"
        guild = interaction.guild
        if guild is None or interaction.guild_id is None:
            return None
        category_id = ticket_info.get("Category")
        if category_id is None:
            return None
        category = guild.get_channel(int(category_id))
        if not isinstance(category, discord.CategoryChannel):
            return None
        staff_id = cfg.get("ROLE_IDS.STAFF_TEAM_ROLE_ID")
        if not staff_id:
            return None
        staff = guild.get_role(int(staff_id))
        if staff is None:
            return None
        user = interaction.user
        if not isinstance(user, discord.Member):
            return None
        overwrites: dict[
            discord.Role | discord.Member | discord.Object,
            discord.PermissionOverwrite,
        ] = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=False),
            staff: discord.PermissionOverwrite(view_channel=False),
        }
        for role_id in ticket_info.get("Roles", []):
            role_obj = guild.get_role(int(role_id))
            if role_obj is not None:
                overwrites[role_obj] = discord.PermissionOverwrite(view_channel=True)
        number = await self.get_number(interaction.guild_id)
        channel = await guild.create_text_channel(
            name=f"{user.name}-ticket-{number}",
            category=category,
            overwrites=overwrites,
        )
        panel_channel = interaction.channel
        if isinstance(panel_channel, discord.TextChannel):
            await panel_channel.set_permissions(staff, view_channel=False)
        embed = discord.Embed(
            description=f"✅ You have successfully opened a ticket! {channel.mention}",
            color=embed_color(cfg),
        )
        await interaction.edit_original_response(embed=embed)
        description = (
            f"Hey {interaction.user.mention}!\n\n"
            "You have created a new ticket!\n"
            f"**Type:** {ticket_type}\n\n"
        )
        description += (
            ticket_info.get("Message", "")
            + "\n \n**One of our staff members will be with you shortly.**"
        )
        embed = discord.Embed(
            color=embed_color(cfg),
            description=description,
        )
        logo = cfg.get("LOGO")
        logo_url = EmbedService.get_logo_url(logo)
        embed.set_footer(text=cfg.get("FOOTER", "Tickr Tickets"), icon_url=logo_url)
        from ui.views.info_button import InfoButton

        send_kwargs: dict = {
            "embed": embed,
            "view": InfoButton(ticket_type, ticket_info, interaction.guild_id),
        }
        if (
            logo
            and isinstance(logo, str)
            and not logo.startswith(("http://", "https://"))
        ):
            import os.path

            if os.path.isfile(logo):
                send_kwargs["file"] = discord.File(logo)
        await channel.send(**send_kwargs)

        privated = ""
        private_mode = ticket_info.get("PrivateMode")
        if private_mode == "admin":
            privated = "Admin"
        elif private_mode == "management":
            privated = "Management"

        DatabasePool.execute(
            "INSERT INTO tickets (guild_id, channel_id, owner_id, type, opened_at, number, is_active, closed_by_id, closed_at, reason, name, transcript, privated) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, NULL, NULL, NULL, NULL, %s)",
            (
                interaction.guild_id,
                channel.id,
                interaction.user.id,
                category.name,
                int(time.time()),
                number,
                1,
                privated or None,
            ),
        )
        from services.active_ticket_cache import active_ticket_cache

        active_ticket_cache.register(
            interaction.guild_id, channel.id, interaction.user.id
        )
        await self.notify_dashboard_new_ticket(
            channel, number, ticket_type, interaction.user.id, interaction.guild_id
        )
        return channel

    @TaskDecorator.task(action_name="New Ticket")
    async def new_ticket(
        self, interaction: discord.Interaction, view: discord.ui.View
    ) -> None:
        if interaction.guild_id is None:
            return
        cfg = await GuildConfigService.for_guild(interaction.guild_id)
        if not cfg.configured:
            await interaction.response.send_message(
                "This server is not configured yet. Run `/setup` to configure Tickr.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            description=f"📖 Attempting to create a new ticket for {interaction.user.mention}",
            color=embed_color(cfg),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        start = time.perf_counter()

        if interaction.message:
            await interaction.message.edit(view=view)

        result = await self.check(interaction, cfg)
        if result:
            embed = discord.Embed(
                description=result,
                color=embed_color(cfg),
            )
            await interaction.edit_original_response(embed=embed)
            return

        channel = await self.create_ticket(interaction, cfg)
        if channel is None:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    description="`❌` Failed to create a ticket",
                    color=embed_color(cfg),
                )
            )
            return
        ticket_count = await self.get_ticket_count(interaction.guild_id)
        log_tasks.info(
            f"Created #{channel} ({channel.id}) in {round((time.perf_counter() - start), 2)}s "
            f"by {interaction.user} ({interaction.user.id}) {ticket_count}"
        )
