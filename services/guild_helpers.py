from __future__ import annotations

import os
from typing import Any

import discord

from services.embed_service import EmbedService

DEFAULT_EMBED_COLOR = "0x5865F2"

# Legacy Minecadia / discord.py gold-yellow embed accents
_LEGACY_EMBED_COLOR_INTS = frozenset(
    {
        0xF1C40F,  # discord.Color.gold()
        0xFFFF00,  # discord.Color.yellow()
        0xFFD700,
        0xFFCC00,
        0xFFBC00,
        0xFAA61A,
        0xE8B923,
        0xEEB211,
        0xD4A017,
    }
)


def normalize_embed_color(raw: str | None) -> str:
    if not raw:
        return DEFAULT_EMBED_COLOR
    text = str(raw).strip()
    if not text.lower().startswith("0x"):
        text = f"0x{text}"
    try:
        if discord.Color.from_str(text).value in _LEGACY_EMBED_COLOR_INTS:
            return DEFAULT_EMBED_COLOR
    except ValueError:
        return DEFAULT_EMBED_COLOR
    return text


def embed_color(cfg: Any) -> discord.Color:
    raw = cfg.get("EMBED_COLOR", DEFAULT_EMBED_COLOR) if hasattr(cfg, "get") else DEFAULT_EMBED_COLOR
    return discord.Color.from_str(normalize_embed_color(raw))


def embed_color_int(cfg: Any) -> int:
    return embed_color(cfg).value


def set_embed_footer(embed: discord.Embed, cfg: Any) -> None:
    logo = cfg.get("LOGO") if hasattr(cfg, "get") else None
    logo_url = EmbedService.get_logo_url(logo)
    footer = cfg.get("FOOTER", "Tickr Tickets") if hasattr(cfg, "get") else "Tickr Tickets"
    embed.set_footer(text=footer, icon_url=logo_url)


def optional_logo_file(cfg: Any) -> discord.File | None:
    logo = cfg.get("LOGO") if hasattr(cfg, "get") else None
    if logo and isinstance(logo, str) and not logo.startswith(("http://", "https://")):
        if os.path.isfile(logo):
            return discord.File(logo)
    return None
