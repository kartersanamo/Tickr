from core.database import DatabasePool


class TicketRepository:
    def __init__(self, db: DatabasePool | None = None):
        self._db = db or DatabasePool.get()

    def execute(self, query: str, params: tuple | None = None) -> list:
        return self._db.execute(query, params)

    def find_active_by_channel(self, guild_id: int, channel_id: int) -> list:
        return self._db.execute(
            "SELECT * FROM `tickets` WHERE `guild_id` = %s AND `channel_id` = %s AND `is_active` = 1",
            (guild_id, channel_id),
        )
