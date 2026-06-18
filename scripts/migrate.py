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


def _strip_sql_comments(stmt: str) -> str:
    lines = []
    for line in stmt.splitlines():
        if line.strip().startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _is_benign_migration_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        phrase in msg
        for phrase in (
            "duplicate column",
            "duplicate key name",
            "already exists",
        )
    )


def _ensure_database(cfg: dict) -> None:
    database = cfg["database"]
    if not database:
        raise ValueError("DB_NAME is not set in the environment.")
    conn = connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        autocommit=True,
    )
    cursor = conn.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{database}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.close()
    conn.close()


def run_migrations() -> None:
    cfg = BotConfig.get_db_config()
    _ensure_database(cfg)
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
            stmt = _strip_sql_comments(statement.strip())
            if not stmt:
                continue
            try:
                cursor.execute(stmt)
            except Exception as exc:
                if _is_benign_migration_error(exc):
                    print(f"  Skipping (already applied): {exc}")
                else:
                    raise
        print(f"  Done.")

    cursor.close()
    conn.close()
    print("Migrations complete.")


if __name__ == "__main__":
    run_migrations()
