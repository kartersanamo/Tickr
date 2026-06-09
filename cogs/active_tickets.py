from discord.enums import SeparatorSpacing
from typing import List, Optional, Tuple
from discord.ext import commands
from discord import app_commands
import cachetools
import discord
import asyncio
import os

from core.config import ConfigManager
from core.decorators import task
from core.loggers import log_tasks


class ActiveTickets(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client

        cfg_entries: int = ConfigManager.get(key = 'ACTIVE_TICKETS_CACHE')['ENTRIES']
        cfg_min_to_expiry: int = ConfigManager.get(key = 'ACTIVE_TICKETS_CACHE')['MINUTES_TO_EXPIRE']
        self.cache = cachetools.TTLCache(maxsize = cfg_entries, ttl = 60 * cfg_min_to_expiry)

    @task(action_name = "Check User Messages", log = False)
    async def check_user_messages(self, user_id: int, channel: discord.TextChannel, tickets: list) -> None:
        cache_key: str = f"{user_id}-{channel.id}"
        if cache_key in self.cache:
            if self.cache[cache_key]:
                tickets.append((channel.mention, channel.category.name if channel.category else "Unknown"))
            return
    
        try:
            async for message in channel.history(limit = None):
                if message.author.id == user_id:
                    tickets.append((channel.mention, channel.category.name if channel.category else "Unknown"))
                    self.cache[cache_key] = True
                    return
            self.cache[cache_key] = False
        
        except Exception as exc:
            log_tasks.error(msg = f"Checking user messages error {exc}")
            self.cache[cache_key] = False
    
    @task(action_name = "Get Tickets", log = True)
    async def get_tickets_list(self, interaction: discord.Interaction) -> List[Tuple[str, str]]:
        tickets: List[Tuple[str, str]] = []
        if not interaction.guild:
                log_tasks.error(msg = "No guild attached to this interaction")
                return tickets
        
        for category_id in ConfigManager.get(key = "TICKET_CATEGORIES"):
            category = interaction.guild.get_channel(category_id)
            if not category:
                log_tasks.warning(msg = f"Category {category_id} could not be found")
                continue
            if not isinstance(category, discord.CategoryChannel):
                log_tasks.warning(msg = f"Category {category_id} is not a category (Type: {type(category)})")
                continue
            
            member: discord.Member | None = interaction.guild.get_member(interaction.user.id)
            if member is None:
                log_tasks.warning(msg = f"Initiating member could not be found in the guild's scope.")
                return tickets
            
            tasks = [asyncio.create_task(coro = self.check_user_messages(user_id = interaction.user.id, channel = ticket, tickets = tickets)) for ticket in category.text_channels if ticket.permissions_for(member).read_messages]
            await asyncio.gather(*tasks)
        return tickets
    
    @staticmethod
    def _chunk_line_blocks(lines: List[str], max_chunk: int) -> List[str]:
        blocks: List[str] = []
        cur: List[str] = []
        size: int = 0

        for line in lines:
            add = len(line) + (1 if cur else 0)
            if cur and size + add > max_chunk:
                blocks.append("\n".join(cur))
                cur = [line]
                size = len(line)
            else:
                cur.append(line)
                size += add
        
        if cur:
            blocks.append("\n".join(cur))
        return blocks
    
    def _build_active_tickets_layout(self, interaction: discord.Interaction, tickets: List[tuple[str, str]]) -> Tuple[discord.ui.LayoutView, List[discord.File]]:
        color: discord.Color = discord.Color.from_str(ConfigManager.get(key = "EMBED_COLOR"))
        logo_path: str = ConfigManager.get(key = "LOGO")
        logo_url: str = self.client.app.embeds.get_logo_url() # type: ignore
        logo_files: List[discord.File] = []

        view = discord.ui.LayoutView(timeout = None)
        inner: list = []

        title_block: str = (
            "# Active Tickets\n"
            f"Tickets where **{interaction.user.mention}** has sent at least one message."
        )

        if tickets:
            title_block += f"\n\n**{len(tickets)}** open channel{'s' if len(tickets) != 1 else ''}."
        else:
            title_block += "\n\n*You are not active in any ticket channels right now.*"

        thumb_desc: str = (ConfigManager.get(key = "FOOTER") or "Logo")[:256]
        use_section: bool = False
        thumb_media: Optional[str] = None

        if logo_url:
            if logo_url.startswith("attachment://") and logo_path and os.path.isfile(path = logo_path):
                fname: str = os.path.basename(p = logo_path)
                logo_files.append(discord.File(fp = logo_path, filename = fname))
                thumb_media = f"attachment://{fname}"
                use_section = True
            elif logo_url.startswith(("http://", "https://")):
                thumb_media = logo_url
                use_section = True
            
        if use_section and thumb_media:
            inner.append(
                discord.ui.Section(
                    discord.ui.TextDisplay(title_block),
                    accessory = discord.ui.Thumbnail(
                        media = thumb_media,
                        description = thumb_desc
                    )
                )
            )
        else:
            inner.append(discord.ui.TextDisplay(content = title_block))
        
        inner.append(discord.ui.Separator(visible = True, spacing = SeparatorSpacing.large))
        
        if tickets:
            lines: List[str] = []
            for mention, cat in tickets:
                safe_cat: str = cat.replace("`", "'")
                lines.append(f"- {mention} - `{safe_cat}`")
            for block in self._chunk_line_blocks(lines = lines, max_chunk = 3500):
                inner.append(discord.ui.TextDisplay(content = block))
        
        inner.append(discord.ui.Separator(visible = True, spacing = SeparatorSpacing.small))
        inner.append(discord.ui.TextDisplay(content = f"{ConfigManager.get('FOOTER')}"))
        
        container: discord.ui.Container = discord.ui.Container(*inner, accent_color = color)
        view.add_item(item = container)

        if view.content_length() > 4000:
            view = discord.ui.LayoutView(timeout = None)
            view.add_item(item = 
                discord.ui.Container(
                    discord.ui.TextDisplay(content = 
                        "# Active Tickets\n"
                        "Your ticket list is too long to display here. "
                        "Please narrow your open tickets or ask staff for help."
                    ),
                    accent_color = color
                )
            )
            return view, []
        return view, logo_files
    
    @task(action_name = "Send Active Tickets Response", log = False)
    async def send_active_tickets_response(self, interaction: discord.Interaction, tickets: List[Tuple[str, str]]) -> None:
        view, logo_files = self._build_active_tickets_layout(interaction = interaction, tickets = tickets)
        edit_kw: dict = {
            "content" : None,
            "embed": None,
            "view": view
        }
        if logo_files:
            edit_kw["attachments"] = logo_files
        await interaction.edit_original_response(**edit_kw)

    @app_commands.guild_only()
    @app_commands.command(name = "active-tickets", description = "Returns which tickets you are actively speaking in")
    async def active_tickets(self, interaction: discord.Interaction) -> None:
        await self.active_tickets_command(interaction = interaction)

    
    @task(action_name = "Active Tickets Command", log = True)
    async def active_tickets_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        tickets: List[Tuple[str, str]] = await self.get_tickets_list(interaction = interaction)
        await self.send_active_tickets_response(interaction = interaction, tickets = tickets)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(ActiveTickets(client))