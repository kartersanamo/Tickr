#!/usr/bin/env python3
"""Import a Minecadia guild config from JSON files into Tickr guilds table."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(Path.cwd()))

from dotenv import load_dotenv

load_dotenv()

from services.guild_config_service import GuildConfigService


async def main(guild_id: int, config_path: Path, tickets_path: Path) -> None:
    with open(config_path, encoding="utf-8") as handle:
        config = json.load(handle)
    with open(tickets_path, encoding="utf-8") as handle:
        ticket_types = json.load(handle)
    config.pop("GUILD_ID", None)
    config.pop("TOKEN", None)
    config.pop("PRESENCE", None)
    if "CHANNEL_IDS" in config:
        channel_ids = config["CHANNEL_IDS"]
        if "ADMIN+_CHECK_ID" in channel_ids:
            channel_ids["ADMIN_PRIVATE_CATEGORY_ID"] = channel_ids.pop("ADMIN+_CHECK_ID")
        if "MANAGEMENT_CONTACT_ID" in channel_ids:
            channel_ids["MANAGEMENT_PRIVATE_CATEGORY_ID"] = channel_ids.pop("MANAGEMENT_CONTACT_ID")
    await GuildConfigService.create_guild(guild_id, config, ticket_types, configured=True)
    print(f"Imported guild {guild_id} as configured.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--guild-id", type=int, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tickets", type=Path, required=True)
    args = parser.parse_args()
    import asyncio

    asyncio.run(main(args.guild_id, args.config, args.tickets))
