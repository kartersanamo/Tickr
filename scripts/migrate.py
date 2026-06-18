#!/usr/bin/env python3
"""Run SQL migrations against the configured database."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(Path.cwd()))

from dotenv import load_dotenv

load_dotenv()

from core.bot_config import BotConfig
from mysql.connector import connect


def run_migrations() -> None:
    cfg = BotConfig.get_db_config()
    migrations_dir = Path("migrations")
    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        print("No migration files found.")
        return

    conn = connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        autocommit=True,
    )
    cursor = conn.cursor()

    for path in files:
        print(f"Running {path.name}...")
        sql = path.read_text(encoding="utf-8")
        for statement in sql.split(";"):
            stmt = statement.strip()
            if not stmt or stmt.startswith("--"):
                continue
            try:
                cursor.execute(stmt)
            except Exception as exc:
                msg = str(exc).lower()
                if "duplicate column" in msg or "already exists" in msg:
                    print(f"  Skipping (already applied): {exc}")
                else:
                    raise
        print(f"  Done.")

    cursor.close()
    conn.close()
    print("Migrations complete.")


if __name__ == "__main__":
    run_migrations()
