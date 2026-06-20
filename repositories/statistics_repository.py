from core.database import DatabasePool


class StatisticsRepository:
    def __init__(self, db: DatabasePool | None = None):
        self._db = db or DatabasePool.get()

    def find_row(self, guild_id: int, user_id: int) -> list:
        return self._db.execute(
            "SELECT * FROM `staff_statistics` WHERE `guild_id` = %s AND `user_id` = %s",
            (guild_id, user_id),
        )

    def insert_default_row(self, guild_id: int, user_id: int) -> None:
        self._db.execute(
            "INSERT INTO `staff_statistics` (`guild_id`, `user_id`, `tickets_closed`, `messages_sent`, `warnings`, "
            "`mutes`, `temp_bans`, `bans`, `screenshares`, `manual_bans`, `blacklists`, `revives`, "
            "`appeals`, `threads_locked`, `strike_team_votes`, `characters_sent`, `punishment_requests`) "
            "VALUES (%s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)",
            (guild_id, user_id),
        )
