"""Tickr dashboard FastAPI application."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.dashboard")

from api.routes import config, discord_meta, guilds, live_tickets, ticket_types

app = FastAPI(title="Tickr Dashboard API", version="1.0.0")

origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(guilds.router)
app.include_router(config.router)
app.include_router(ticket_types.router)
app.include_router(discord_meta.router)
app.include_router(live_tickets.router)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
