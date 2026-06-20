"""Guild config schema and CRUD routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth.permissions import can_manage_guild
from api.deps import SessionUser, get_current_user
from services.guild_config_fields import (
    CONFIG_CATEGORIES,
    CONFIG_FIELDS,
    FIELDS_BY_KEY,
    get_config_value,
    merge_defaults,
    validate_required,
)
from services.guild_config_service import GuildConfigService
from services.guild_helpers import normalize_embed_color

router = APIRouter(tags=["config"])


def _field_to_dict(field) -> dict[str, Any]:
    return {
        "key": field.key,
        "path": field.path,
        "label": field.label,
        "description": field.description,
        "fieldType": field.field_type,
        "required": field.required,
        "setup": field.setup,
        "category": field.category,
    }


@router.get("/guilds/{guild_id}/config/schema")
async def config_schema(
    guild_id: int, user: SessionUser = Depends(get_current_user)
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "categories": CONFIG_CATEGORIES,
        "fields": [_field_to_dict(f) for f in CONFIG_FIELDS],
    }


@router.get("/guilds/{guild_id}/config")
async def get_config(
    guild_id: int, user: SessionUser = Depends(get_current_user)
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    merged = merge_defaults(cfg.all())
    values: dict[str, Any] = {}
    for field in CONFIG_FIELDS:
        if field.path == "__system.tickets_global_enabled":
            values[field.key] = cfg.tickets_global_enabled
            continue
        values[field.key] = get_config_value(merged, field.path)
    return {
        "configured": cfg.configured,
        "missingRequired": validate_required(merged),
        "values": values,
        "config": merged,
    }


class ConfigPatchBody(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)


@router.patch("/guilds/{guild_id}/config")
async def patch_config(
    guild_id: int,
    body: ConfigPatchBody,
    user: SessionUser = Depends(get_current_user),
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    for key, value in body.updates.items():
        field = FIELDS_BY_KEY.get(key)
        if field is None:
            raise HTTPException(status_code=400, detail=f"Unknown field: {key}")
        if field.path == "__system.tickets_global_enabled":
            await GuildConfigService.set_tickets_global_enabled(guild_id, bool(value))
            continue
        if field.field_type == "color" and value:
            value = normalize_embed_color(str(value))
        if field.field_type in ("role_list", "category_list"):
            value = value or []
        if field.field_type == "integer":
            value = int(value) if value is not None else 0
        await GuildConfigService.patch_config(guild_id, field.path, value)
    cfg = await GuildConfigService.for_guild(guild_id)
    merged = merge_defaults(cfg.all())
    missing = validate_required(merged)
    if not missing:
        await GuildConfigService.set_configured(guild_id, True)
    GuildConfigService.invalidate(guild_id)
    return {
        "ok": True,
        "missingRequired": missing,
        "configured": cfg.configured or not missing,
    }
