from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from mysql.connector import pooling

from core.config import ConfigManager
from core.errors.db import DatabaseErrors
from core.loggers import log_tasks

log = logging.getLogger(name="Tasks")

_DB_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tickets-db")


class DatabasePool:
    _instance: DatabasePool | None = None
    _pool: pooling.MySQLConnectionPool | None = None

    @classmethod
    def get(cls) -> DatabasePool:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _pool_config(self) -> dict[str, Any]:
        cfg = ConfigManager.get_db_config()
        return {
            "host": cfg["host"],
            "port": cfg["port"],
            "user": cfg["user"],
            "password": cfg["password"],
            "database": cfg["database"],
            "autocommit": bool(cfg.get("autocommit", True)),
        }

    def _ensure_pool(self) -> pooling.MySQLConnectionPool:
        if self._pool is None:
            cfg = self._pool_config()
            self._pool = pooling.MySQLConnectionPool(
                pool_name="tickr_tickets",
                pool_size=8,
                pool_reset_session=True,
                **cfg,
            )
        return self._pool

    def _execute_query(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        connection = None
        try:
            connection = self._ensure_pool().get_connection()
            cursor = connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            if cursor.description:
                rows = cursor.fetchall()
            cursor.close()
        except Exception as error:
            DatabaseErrors.log_db_failure(logger=log_tasks, exc=error, query_hint=query)
        finally:
            if connection is not None:
                connection.close()
        return rows

    @staticmethod
    def execute(query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
        return DatabasePool.get()._execute_query(query, params)


def execute(query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    return DatabasePool.execute(query, params)


async def aexecute(query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_DB_EXECUTOR, execute, query, params)
