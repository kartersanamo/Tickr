"""Ticket types CRUD routes."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth.permissions import can_manage_guild
from api.deps import SessionUser, get_current_user
from services import ticket_types_editor as editor
from services.guild_config_service import GuildConfigService

router = APIRouter(tags=["ticket-types"])


@router.get("/guilds/{guild_id}/ticket-types")
async def get_ticket_types(guild_id: int, user: SessionUser = Depends(get_current_user)) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    return {"data": cfg.tickets_raw(), "categories": editor.category_names(cfg.tickets_raw())}


class TicketTypesReplaceBody(BaseModel):
    data: dict[str, Any]


@router.put("/guilds/{guild_id}/ticket-types")
async def replace_ticket_types(
    guild_id: int,
    body: TicketTypesReplaceBody,
    user: SessionUser = Depends(get_current_user),
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    await GuildConfigService.save_ticket_types(guild_id, body.data)
    GuildConfigService.invalidate(guild_id)
    return {"ok": True}


class NameBody(BaseModel):
    name: str


class RenameBody(BaseModel):
    newName: str


class DuplicateBody(BaseModel):
    newName: str


class QuestionBody(BaseModel):
    label: str
    placeholder: str = ""
    length: str = "Long"


class TypeUpdateBody(BaseModel):
    data: dict[str, Any]


async def _save_types(guild_id: int, data: dict) -> dict:
    await GuildConfigService.save_ticket_types(guild_id, data)
    GuildConfigService.invalidate(guild_id)
    return data


@router.post("/guilds/{guild_id}/ticket-types/categories")
async def add_category(
    guild_id: int, body: NameBody, user: SessionUser = Depends(get_current_user)
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    try:
        updated = editor.add_category(cfg.tickets_raw(), body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _save_types(guild_id, updated)
    return {"ok": True, "categories": editor.category_names(updated)}


@router.delete("/guilds/{guild_id}/ticket-types/categories/{category}")
async def delete_category(
    guild_id: int, category: str, user: SessionUser = Depends(get_current_user)
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    try:
        updated = editor.remove_category(cfg.tickets_raw(), category)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _save_types(guild_id, updated)
    return {"ok": True}


@router.patch("/guilds/{guild_id}/ticket-types/categories/{category}/rename")
async def rename_category(
    guild_id: int, category: str, body: RenameBody, user: SessionUser = Depends(get_current_user)
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    try:
        updated = editor.rename_category(cfg.tickets_raw(), category, body.newName)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _save_types(guild_id, updated)
    return {"ok": True}


@router.post("/guilds/{guild_id}/ticket-types/categories/{category}/types")
async def add_type(
    guild_id: int, category: str, body: NameBody, user: SessionUser = Depends(get_current_user)
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    staff_role = cfg.get("ROLE_IDS.STAFF_TEAM_ROLE_ID")
    try:
        updated = editor.add_ticket_type(
            cfg.tickets_raw(),
            category,
            body.name,
            template=editor.new_ticket_type(staff_role_id=int(staff_role) if staff_role else None),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _save_types(guild_id, updated)
    return {"ok": True}


@router.delete("/guilds/{guild_id}/ticket-types/categories/{category}/types/{type_name}")
async def delete_type(
    guild_id: int, category: str, type_name: str, user: SessionUser = Depends(get_current_user)
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    try:
        updated = editor.remove_ticket_type(cfg.tickets_raw(), category, type_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _save_types(guild_id, updated)
    return {"ok": True}


@router.patch("/guilds/{guild_id}/ticket-types/categories/{category}/types/{type_name}/rename")
async def rename_type(
    guild_id: int,
    category: str,
    type_name: str,
    body: RenameBody,
    user: SessionUser = Depends(get_current_user),
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    try:
        updated = editor.rename_ticket_type(cfg.tickets_raw(), category, type_name, body.newName)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _save_types(guild_id, updated)
    return {"ok": True}


@router.post("/guilds/{guild_id}/ticket-types/categories/{category}/types/{type_name}/duplicate")
async def duplicate_type(
    guild_id: int,
    category: str,
    type_name: str,
    body: DuplicateBody,
    user: SessionUser = Depends(get_current_user),
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    try:
        updated = editor.duplicate_ticket_type(cfg.tickets_raw(), category, type_name, body.newName)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _save_types(guild_id, updated)
    return {"ok": True}


@router.put("/guilds/{guild_id}/ticket-types/categories/{category}/types/{type_name}")
async def update_type(
    guild_id: int,
    category: str,
    type_name: str,
    body: TypeUpdateBody,
    user: SessionUser = Depends(get_current_user),
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    data = cfg.tickets_raw()
    if category not in data or type_name not in data.get(category, {}):
        raise HTTPException(status_code=404, detail="Ticket type not found")
    updated = dict(data)
    updated[category] = dict(updated[category])
    updated[category][type_name] = body.data
    await _save_types(guild_id, updated)
    return {"ok": True}


@router.post("/guilds/{guild_id}/ticket-types/categories/{category}/types/{type_name}/questions")
async def add_question(
    guild_id: int,
    category: str,
    type_name: str,
    body: QuestionBody,
    user: SessionUser = Depends(get_current_user),
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    question = editor.new_question(label=body.label, placeholder=body.placeholder, length=body.length)
    try:
        updated = editor.add_question(cfg.tickets_raw(), category, type_name, question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _save_types(guild_id, updated)
    return {"ok": True}


@router.delete("/guilds/{guild_id}/ticket-types/categories/{category}/types/{type_name}/questions/{label}")
async def delete_question(
    guild_id: int,
    category: str,
    type_name: str,
    label: str,
    user: SessionUser = Depends(get_current_user),
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    try:
        updated = editor.remove_question(cfg.tickets_raw(), category, type_name, label)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _save_types(guild_id, updated)
    return {"ok": True}


class ToggleBody(BaseModel):
    status: str


@router.patch("/guilds/{guild_id}/ticket-types/toggle-global")
async def toggle_global(
    guild_id: int, body: ToggleBody, user: SessionUser = Depends(get_current_user)
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    data = cfg.tickets_raw()
    data["TOGGLE_STATUS"] = body.status
    await _save_types(guild_id, data)
    return {"ok": True}


@router.patch("/guilds/{guild_id}/ticket-types/categories/{category}/types/{type_name}/private-mode")
async def cycle_private_mode(
    guild_id: int,
    category: str,
    type_name: str,
    user: SessionUser = Depends(get_current_user),
) -> dict[str, Any]:
    if not await can_manage_guild(user, guild_id):
        raise HTTPException(status_code=403, detail="Access denied")
    cfg = await GuildConfigService.for_guild(guild_id)
    data = cfg.tickets_raw()
    current = data.get(category, {}).get(type_name, {}).get("PrivateMode")
    new_mode = editor.cycle_private_mode(current)
    try:
        updated = editor.set_private_mode(data, category, type_name, new_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _save_types(guild_id, updated)
    return {"ok": True, "privateMode": new_mode}
