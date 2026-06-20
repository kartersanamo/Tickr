"""Backward-compatible alias for bot-level configuration."""

from core.bot_config import BotConfig


class ConfigManager:
    @classmethod
    def get_instance(cls) -> BotConfig:
        return BotConfig.get_instance()

    @classmethod
    def get(cls, key: str, default=None):
        return BotConfig.get(key, default)

    @classmethod
    def all(cls) -> dict:
        return BotConfig.all()

    @classmethod
    def get_db_config(cls) -> dict:
        return BotConfig.get_db_config()


__all__ = ["ConfigManager"]
