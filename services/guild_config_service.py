from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from cachetools import TTLCache

from core.database import aexecute
from repositories.guild_repository import GuildRepository


class GuildConfig:
    """Per-guild configuration wrapper."""

    def __init__(
        self,
        guild_id: int,
        config: dict,
        ticket_types: dict,
        configured: bool,
        tickets_global_enabled: bool,
    ) -> None:
        self.guild_id = guild_id
        self._config = config
        self._ticket_types = ticket_types
        self.configured = configured
        self.tickets_global_enabled = tickets_global_enabled

    def get(self, key: str, default: Any = None) -> Any:
        if "." not in key:
            return self._config.get(key, default)
        value: Any = self._config
        for part in key.split("."):
            if not isinstance(value, dict):
                return default
            value = value.get(part)
            if value is None:
                return default
        return value

    def all(self) -> dict:
        return copy.deepcopy(self._config)

    def tickets(self) -> dict:
        data = copy.deepcopy(self._ticket_types)
        data.pop("TOGGLE_STATUS", None)
        return data

    def tickets_raw(self) -> dict:
        return copy.deepcopy(self._ticket_types)

    def tickets_globally_enabled(self) -> bool:
        if not self.tickets_global_enabled:
            return False
        status = str(self._ticket_types.get("TOGGLE_STATUS", "Enabled")).lower()
        return status != "disabled"

    def transcript_paste_url(self, bot_default: str = "") -> str:
        return str(self.get("TRANSCRIPT_PASTE_URL") or bot_default or "").rstrip("/")

    def private_mode_for_category(self, category_id: int | None) -> str | None:
        if category_id is None:
            return None
        admin_cat = self.get("CHANNEL_IDS.ADMIN_PRIVATE_CATEGORY_ID")
        mgmt_cat = self.get("CHANNEL_IDS.MANAGEMENT_PRIVATE_CATEGORY_ID")
        if admin_cat and int(admin_cat) == int(category_id):
            return "Admin"
        if mgmt_cat and int(mgmt_cat) == int(category_id):
            return "Management"
        for _category, types in self.tickets().items():
            if not isinstance(types, dict):
                continue
            for type_data in types.values():
                if not isinstance(type_data, dict):
                    continue
                if type_data.get("Category") == category_id:
                    mode = type_data.get("PrivateMode")
                    if mode == "admin":
                        return "Admin"
                    if mode == "management":
                        return "Management"
        return None


class GuildConfigService:
    _cache: TTLCache = TTLCache(maxsize=500, ttl=60)
    _repo = GuildRepository()

    @classmethod
    def _default_config(cls) -> dict:
        path = Path("assets/default_guild_config.json")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    @classmethod
    def _default_ticket_types(cls) -> dict:
        path = Path("assets/default_ticket_types.json")
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    @classmethod
    async def for_guild(cls, guild_id: int) -> GuildConfig:
        cached = cls._cache.get(guild_id)
        if cached is not None:
            return cached
        row = await aexecute("SELECT * FROM guilds WHERE guild_id = %s", (guild_id,))
        if not row:
            cfg = cls._default_config()
            types = cls._default_ticket_types()
            await cls.create_guild(guild_id, cfg, types, configured=False)
            guild_cfg = GuildConfig(guild_id, cfg, types, False, True)
        else:
            parsed = GuildRepository._parse_row(row[0])
            guild_cfg = GuildConfig(
                parsed["guild_id"],
                parsed["config"],
                parsed["ticket_types"],
                parsed["configured"],
                parsed["tickets_global_enabled"],
            )
        cls._cache[guild_id] = guild_cfg
        return guild_cfg

    @classmethod
    async def create_guild(
        cls,
        guild_id: int,
        config: dict,
        ticket_types: dict,
        configured: bool = False,
    ) -> GuildConfig:
        import asyncio

        await asyncio.to_thread(
            cls._repo.upsert,
            guild_id,
            config,
            ticket_types,
            configured,
        )
        guild_cfg = GuildConfig(guild_id, config, ticket_types, configured, True)
        cls._cache[guild_id] = guild_cfg
        return guild_cfg

    @classmethod
    async def save_config(cls, guild_id: int, config: dict) -> GuildConfig:
        import asyncio

        await asyncio.to_thread(cls._repo.update_config, guild_id, config)
        current = await cls.for_guild(guild_id)
        guild_cfg = GuildConfig(
            guild_id,
            config,
            current.tickets_raw(),
            current.configured,
            current.tickets_global_enabled,
        )
        cls._cache[guild_id] = guild_cfg
        return guild_cfg

    @classmethod
    async def save_ticket_types(cls, guild_id: int, ticket_types: dict) -> GuildConfig:
        import asyncio

        await asyncio.to_thread(cls._repo.update_ticket_types, guild_id, ticket_types)
        current = await cls.for_guild(guild_id)
        guild_cfg = GuildConfig(
            guild_id,
            current.all(),
            ticket_types,
            current.configured,
            current.tickets_global_enabled,
        )
        cls._cache[guild_id] = guild_cfg
        return guild_cfg

    @classmethod
    async def set_configured(cls, guild_id: int, configured: bool) -> None:
        import asyncio

        await asyncio.to_thread(cls._repo.set_configured, guild_id, configured)
        cls.invalidate(guild_id)

    @classmethod
    async def reload_tickets(cls, guild_id: int) -> dict:
        cls.invalidate(guild_id)
        cfg = await cls.for_guild(guild_id)
        return cfg.tickets()

    @classmethod
    def invalidate(cls, guild_id: int) -> None:
        cls._cache.pop(guild_id, None)


async def get_guild_cfg(interaction) -> GuildConfig:
    """Helper to load guild config from an interaction."""
    if interaction.guild_id is None:
        raise ValueError("Guild context required")
    return await GuildConfigService.for_guild(interaction.guild_id)
