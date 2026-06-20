import random

import discord

from core.database import DatabasePool
from core.decorators import TaskDecorator
from core.loggers import log_tasks
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color, format_transcript_line, set_embed_footer


class Questions(discord.ui.Modal):
    def __init__(self, ticket_type: str, ticket_info: dict, guild_id: int) -> None:
        self.ticket_type = ticket_type[:45] if len(ticket_type) > 45 else ticket_type
        self.ticket_info = ticket_info
        self.guild_id = guild_id
        super().__init__(
            title=self.ticket_type,
            timeout=None,
            custom_id=str(random.randint(0, 50000000000)),
        )
        self._modal_field_headings: list = []
        self.add_items()

    def add_items(self):
        try:
            ign_label = "What is your in game name?"
            self.add_item(
                discord.ui.TextInput(
                    label=ign_label,
                    placeholder="My IGN is...",
                    style=discord.TextStyle.short,
                    custom_id=str(random.randint(0, 50000)),
                )
            )
            self._modal_field_headings.append(ign_label)
            for question in self.ticket_info.get("Questions", []):
                style = (
                    discord.TextStyle.short
                    if question.get("Length") == "Short"
                    else discord.TextStyle.long
                )
                q_label = question["Label"]
                self.add_item(
                    discord.ui.TextInput(
                        label=q_label,
                        placeholder=question.get("Placeholder", ""),
                        style=style,
                        custom_id=str(random.randint(0, 50000)),
                    )
                )
                self._modal_field_headings.append(q_label)
        except Exception as exc:
            log_tasks.error(f"Failed to add items to the Questions modal {exc}")

    @TaskDecorator.task("Get Previous Ticket", False)
    async def get_previous_ticket(
        self, guild_id: int, owner_id: int, cfg
    ) -> discord.Embed | None:
        rows = DatabasePool.execute(
            "SELECT name, number, reason, transcript, closed_at, closed_by_id, privated FROM tickets "
            "WHERE guild_id = %s AND owner_id = %s AND is_active = 0 ORDER BY closed_at DESC LIMIT 1",
            (guild_id, owner_id),
        )
        if not rows:
            return None
        row = rows[0]
        if row["privated"]:
            description = (
                f"Closed by <@{row['closed_by_id']}> on <t:{row['closed_at']}:f> "
                f"(<t:{row['closed_at']}:R>)\nReason: Privated Ticket"
            )
        else:
            description = (
                f"Closed by <@{row['closed_by_id']}> on <t:{row['closed_at']}:f> "
                f"(<t:{row['closed_at']}:R>)\nReason: {row['reason']}\n"
                f"{format_transcript_line(row['transcript'])}"
            )
        embed = discord.Embed(
            title=f"Recently Closed {row['name']}#{row['number']}",
            description=description,
            color=embed_color(cfg),
        )
        set_embed_footer(embed, cfg)
        return embed

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer()
            guild = interaction.guild
            channel = interaction.channel
            message = interaction.message
            user = interaction.user
            if (
                guild is None
                or interaction.guild_id is None
                or not isinstance(channel, discord.TextChannel)
                or not isinstance(user, discord.Member)
                or message is None
            ):
                return

            cfg = await GuildConfigService.for_guild(interaction.guild_id)
            roles = [
                role.mention
                for ping in self.ticket_info.get("Pings", [])
                if (role := guild.get_role(int(ping))) is not None
            ]
            tags = await channel.send(" ".join(roles))
            embed = message.embeds[0]
            if embed.description is None:
                await tags.delete()
                return

            split = embed.description.split("\n\n")
            new_description = f"{split[0]}\n \n{split[1]}\n \n"
            for heading, item in zip(self._modal_field_headings, self.children):
                if not isinstance(item, discord.ui.TextInput):
                    continue
                if heading == "What is your in game name?":
                    new_description += f"**{heading}**\n`{item.value}`\n \n"
                else:
                    new_description += f"**{heading}**\n{item.value}\n \n"
            new_description += "**One of our staff members will be with you shortly.**"
            embed = discord.Embed(description=new_description, color=embed_color(cfg))
            set_embed_footer(embed, cfg)

            previous_ticket = await self.get_previous_ticket(
                interaction.guild_id, user.id, cfg
            )
            if previous_ticket:
                await message.edit(embeds=[embed, previous_ticket], view=None)
            else:
                await message.edit(embed=embed, view=None)

            perms = channel.overwrites_for(user)
            perms.send_messages = perms.view_channel = True
            await channel.set_permissions(user, overwrite=perms)
            await tags.delete()

            rows = DatabasePool.execute(
                "SELECT number FROM tickets WHERE guild_id = %s AND channel_id = %s LIMIT 1",
                (interaction.guild_id, channel.id),
            )
            if rows:
                from services.ticket_creation_service import TicketCreationService

                await TicketCreationService().notify_dashboard_new_ticket(
                    channel=channel,
                    number=int(rows[0]["number"]),
                    ticket_type=self.ticket_type,
                    owner_id=user.id,
                    guild_id=interaction.guild_id,
                )
        except Exception as exc:
            log_tasks.error(f"Questions modal submit failed: {exc}")
