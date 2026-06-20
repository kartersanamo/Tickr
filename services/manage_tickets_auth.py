"""Permission checks for in-Discord ticket editors."""

from __future__ import annotations

import discord

from services.guild_config_service import GuildConfigService


async def require_ticket_editor(interaction: discord.Interaction) -> bool:
    if interaction.guild is None or interaction.guild_id is None:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "This can only be used in a server.",
                ephemeral=True,
            )
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    cfg = await GuildConfigService.for_guild(interaction.guild_id)
    star_id = cfg.get("ROLE_IDS.ADMINISTRATOR_PERMS_ROLE_ID")
    if not star_id:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Administrator permissions role is not configured. Use `/manage-config`.",
                ephemeral=True,
            )
        return False
    star_role = interaction.guild.get_role(int(star_id))
    if star_role is None:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Administrator permissions role not found in this server.",
                ephemeral=True,
            )
        return False
    member = (
        interaction.user
        if isinstance(interaction.user, discord.Member)
        else interaction.guild.get_member(interaction.user.id)
    )
    if member is None or star_role not in member.roles:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "You need the configured administrator permissions role to edit tickets.",
                ephemeral=True,
            )
        return False
    return True
