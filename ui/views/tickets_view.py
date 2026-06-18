import discord
from services.ticket_creation_service import TicketCreationService


def _build_select(category_name: str, category_info: dict) -> discord.ui.Select:
    select_options = [
        discord.SelectOption(
            label=option_name[:100],
            emoji=option_info.get("Emoji"),
            description=(option_info.get("Description") or "")[:100],
        )
        for option_name, option_info in category_info.items()
        if isinstance(option_info, dict)
    ]
    select = discord.ui.Select(
        custom_id=category_name,
        placeholder=category_name[:100],
        options=select_options[:25],
    )
    return select


class TicketsView(discord.ui.View):
    def __init__(self, tickets: dict | None = None, slice_start: int = 0, slice_end: int = 5) -> None:
        super().__init__(timeout=None)
        self.ticket_manager = TicketCreationService()
        self._tickets = tickets or {}
        for category_name, category_info in list(self._tickets.items())[slice_start:slice_end]:
            if not isinstance(category_info, dict):
                continue
            select = _build_select(category_name, category_info)
            select.callback = self.handle_selection
            self.add_item(select)

    @classmethod
    def for_guild(cls, tickets: dict) -> "TicketsView":
        return cls(tickets=tickets, slice_start=0, slice_end=5)

    @classmethod
    def persistent(cls, category_names: list[str]) -> "TicketsView":
        view = cls(tickets={}, slice_start=0, slice_end=0)
        for name in category_names:
            select = discord.ui.Select(
                custom_id=name,
                placeholder=name[:100],
                options=[discord.SelectOption(label="…", value="…")],
            )
            select.callback = view.handle_selection
            view.add_item(select)
        return view

    async def handle_selection(self, interaction: discord.Interaction):
        await self.ticket_manager.new_ticket(interaction, self)
