from discord.ext import commands


class Private(commands.Cog):
    def __init__(self, client: commands.Bot) -> None:
        self.client: commands.Bot = client


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Private(client))