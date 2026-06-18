from __future__ import annotations

import os

import discord

from services.embed_service import EmbedService
from services.guild_config_service import GuildConfig


def embed_color(cfg: GuildConfig) -> discord.Color:
    return discord.Color.from_str(cfg.get("EMBED_COLOR", "0x5865F2"))


def set_embed_footer(embed: discord.Embed, cfg: GuildConfig) -> None:
    logo = cfg.get("LOGO")
    logo_url = EmbedService.get_logo_url(logo)
    embed.set_footer(text=cfg.get("FOOTER", "Tickr Tickets"), icon_url=logo_url)


def optional_logo_file(cfg: GuildConfig) -> discord.File | None:
    logo = cfg.get("LOGO")
    if logo and isinstance(logo, str) and not logo.startswith(("http://", "https://")):
        if os.path.isfile(logo):
            return discord.File(logo)
    return None
