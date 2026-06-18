import discord

from repositories.statistics_repository import StatisticsRepository


class StatisticsService:
    def __init__(self, repository: StatisticsRepository | None = None):
        self._repo = repository or StatisticsRepository()

    async def get_statistic(self, guild_id: int, user: discord.Member, statistic: str):
        rows = self._repo.find_row(guild_id, user.id)
        if rows:
            return rows[0][statistic]
        self._repo.insert_default_row(guild_id, user.id)
        return 0


_default_statistics = StatisticsService()


async def is_found(guild_id: int, user: discord.Member, statistic: str):
    return await _default_statistics.get_statistic(guild_id, user, statistic)
