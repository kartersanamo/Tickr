from __future__ import annotations

import json
import time
from typing import Any

from core.database import DatabasePool


class GuildRepository:
    def __init__(self, db: DatabasePool | None = None):
        self._db = db or DatabasePool.get()

    def find_by_id(self, guild_id: int) -> dict | None:
        rows = self._db.execute(
            "SELECT * FROM guilds WHERE guild_id = %s",
            (guild_id,),
        )
        if not rows:
            return None
        row = rows[0]
        return self._parse_row(row)

    def upsert(
        self,
        guild_id: int,
        config: dict,
        ticket_types: dict,
        configured: bool = False,
        tickets_global_enabled: bool = True,
    ) -> None:
        now = int(time.time())
        existing = self.find_by_id(guild_id)
        if existing:
            self._db.execute(
                """
                UPDATE guilds
                SET config = %s, ticket_types = %s, configured = %s,
                    tickets_global_enabled = %s, updated_at = %s
                WHERE guild_id = %s
                """,
                (
                    json.dumps(config),
                    json.dumps(ticket_types),
                    int(configured),
                    int(tickets_global_enabled),
                    now,
                    guild_id,
                ),
            )
        else:
            self._db.execute(
                """
                INSERT INTO guilds
                    (guild_id, configured, config, ticket_types, tickets_global_enabled, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    guild_id,
                    int(configured),
                    json.dumps(config),
                    json.dumps(ticket_types),
                    int(tickets_global_enabled),
                    now,
                    now,
                ),
            )

    def update_config(self, guild_id: int, config: dict) -> None:
        now = int(time.time())
        self._db.execute(
            "UPDATE guilds SET config = %s, updated_at = %s WHERE guild_id = %s",
            (json.dumps(config), now, guild_id),
        )

    def update_ticket_types(self, guild_id: int, ticket_types: dict) -> None:
        now = int(time.time())
        self._db.execute(
            "UPDATE guilds SET ticket_types = %s, updated_at = %s WHERE guild_id = %s",
            (json.dumps(ticket_types), now, guild_id),
        )

    def set_configured(self, guild_id: int, configured: bool) -> None:
        now = int(time.time())
        self._db.execute(
            "UPDATE guilds SET configured = %s, updated_at = %s WHERE guild_id = %s",
            (int(configured), now, guild_id),
        )

    def get_dashboard(self, guild_id: int) -> dict | None:
        rows = self._db.execute(
            "SELECT * FROM guild_dashboard WHERE guild_id = %s",
            (guild_id,),
        )
        return rows[0] if rows else None

    def upsert_dashboard(
        self,
        guild_id: int,
        notify_url: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        existing = self.get_dashboard(guild_id)
        if existing:
            self._db.execute(
                "UPDATE guild_dashboard SET notify_url = %s, api_secret = %s WHERE guild_id = %s",
                (notify_url, api_secret, guild_id),
            )
        else:
            self._db.execute(
                "INSERT INTO guild_dashboard (guild_id, notify_url, api_secret) VALUES (%s, %s, %s)",
                (guild_id, notify_url, api_secret),
            )

    @staticmethod
    def _parse_row(row: dict) -> dict:
        config = row.get("config")
        ticket_types = row.get("ticket_types")
        if isinstance(config, str):
            config = json.loads(config)
        if isinstance(ticket_types, str):
            ticket_types = json.loads(ticket_types)
        return {
            "guild_id": int(row["guild_id"]),
            "configured": bool(row.get("configured")),
            "config": config or {},
            "ticket_types": ticket_types or {},
            "tickets_global_enabled": bool(row.get("tickets_global_enabled", 1)),
        }
