import discord
from ui.views.tickets_view import TicketsView


class TicketsView2(TicketsView):
    @classmethod
    def for_guild(cls, tickets: dict) -> "TicketsView2":
        return cls(tickets=tickets, slice_start=5, slice_end=100)

    @classmethod
    def persistent(cls, category_names: list[str]) -> "TicketsView2":
        view = cls(tickets={}, slice_start=0, slice_end=0)
        for name in category_names[5:]:
            select = discord.ui.Select(
                custom_id=name,
                placeholder=name[:100],
                options=[discord.SelectOption(label="…", value="…")],
            )
            select.callback = view.handle_selection
            view.add_item(select)
        return view
