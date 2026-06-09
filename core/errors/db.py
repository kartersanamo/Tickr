from __future__ import annotations
from typing import TypeVar
import logging

from core.errors.exceptions import ExternalServiceError
from core.errors.logging import log_exception

T = TypeVar(name = "T")

try:
    import aiomysql
except ImportError:
    aiomysql = None


def is_db_operational_error(exc: BaseException) -> bool:
    if aiomysql and isinstance(exc, aiomysql.OperationalError):
        return True
    name = type(exc).__name__.lower()
    return "operational" in name or "database" in name or "mysql" in name


def raise_if_db_unavailable(exc: BaseException) -> None:
    if is_db_operational_error(exc):
        raise ExternalServiceError(log_message = str(exc)) from exc
    

def log_db_failure(logger: logging.Logger, exc: BaseException, *, query_hint: str = "") -> None:
    log_exception(
        logger = logger,
        exc = exc,
        component = "database",
        extra = {"query": query_hint[:200]} if query_hint else None
    )


def log_query_failure(logger: logging.Logger, exc: BaseException, query: str) -> None:
    log_db_failure(logger = logger, exc = exc, query_hint = query)