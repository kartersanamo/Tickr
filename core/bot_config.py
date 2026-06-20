"""Bot-level configuration from environment (not per-guild)."""

from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()


class BotConfig:
    _instance: Optional["BotConfig"] = None

    def __init__(self) -> None:
        self.settings: dict[str, Any] = {
            "TOKEN": os.getenv("DISCORD_TOKEN"),
            "PRESENCE": os.getenv("BOT_PRESENCE", "Tickr Tickets"),
            "TRANSCRIPT_PASTE_URL": os.getenv("TRANSCRIPT_PASTE_URL", ""),
            "TRANSCRIPT_PASTE_SUFFIX": os.getenv(
                "TRANSCRIPT_PASTE_SUFFIX", "/documents"
            ),
            "DASHBOARD_URL": os.getenv("DASHBOARD_URL", "").rstrip("/"),
            "TICKETS_BOT_API_SECRET": os.getenv("TICKETS_BOT_API_SECRET")
            or os.getenv("CONTROL_API_SECRET"),
            "TICKETS_BOT_API_PORT": int(os.getenv("TICKETS_BOT_API_PORT", "8788")),
            "DEV_GUILD_ID": int(os.getenv("DISCORD_GUILD_ID", "0") or "0") or None,
            "DATABASE_CONFIG": self._db_config_from_env(),
        }

    @classmethod
    def get_instance(cls) -> "BotConfig":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        settings = cls.get_instance().settings
        if "." not in key:
            return settings.get(key, default)
        value: Any = settings
        for part in key.split("."):
            if not isinstance(value, dict):
                return default
            value = value.get(part)
            if value is None:
                return default
        return value

    @classmethod
    def all(cls) -> dict:
        return dict(cls.get_instance().settings)

    @classmethod
    def get_db_config(cls) -> dict:
        return cls.get_instance().settings["DATABASE_CONFIG"]

    @staticmethod
    def _db_config_from_env() -> dict:
        return {
            "host": os.getenv("DB_HOST", "127.0.0.1"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", ""),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "") or os.getenv("DB_DATABASE", ""),
            "autocommit": os.getenv("DB_AUTOCOMMIT", "true").lower()
            in ("1", "true", "yes"),
        }


__all__ = ["BotConfig"]
