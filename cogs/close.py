from discord.ext import commands


class Close(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Close(client))