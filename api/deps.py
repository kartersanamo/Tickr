"""FastAPI dependencies for Tickr dashboard API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

JWT_SECRET = os.environ.get("DASHBOARD_INTERNAL_SECRET", "")
JWT_ALGORITHM = "HS256"
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN") or os.environ.get(
    "DISCORD_TOKEN", ""
)
TICKETS_BOT_API_URL = os.environ.get(
    "TICKETS_BOT_API_URL", "http://127.0.0.1:8788"
).rstrip("/")
TICKETS_BOT_API_SECRET = os.environ.get("TICKETS_BOT_API_SECRET") or os.environ.get(
    "CONTROL_API_SECRET", ""
)

_bearer = HTTPBearer(auto_error=False)


@dataclass
class SessionUser:
    user_id: int
    username: str
    avatar: str | None
    guilds: list[dict[str, Any]]


def _decode_token(token: str) -> dict[str, Any]:
    if not JWT_SECRET:
        raise HTTPException(status_code=503, detail="Dashboard auth not configured")
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid session token") from exc


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> SessionUser:
    token = None
    if credentials is not None:
        token = credentials.credentials
    if not token:
        token = request.headers.get("X-Dashboard-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    payload = _decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    return SessionUser(
        user_id=int(user_id),
        username=str(payload.get("username") or "User"),
        avatar=payload.get("avatar"),
        guilds=list(payload.get("guilds") or []),
    )
