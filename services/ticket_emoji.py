"""Validate ticket panel emoji values (Unicode or Discord custom)."""

from __future__ import annotations

import re
import unicodedata

DISCORD_CUSTOM_EMOJI = re.compile(r"^<a?:[a-zA-Z0-9_]{2,32}:\d{17,20}>$")
KEYCAP_EMOJI = re.compile(r"^[0-9#*]\uFE0F?\u20E3$")

_EMOJI_RANGES: tuple[tuple[int, int], ...] = (
    (0x1F600, 0x1F64F),
    (0x1F300, 0x1F5FF),
    (0x1F680, 0x1F6FF),
    (0x1F900, 0x1F9FF),
    (0x1FA70, 0x1FAFF),
    (0x2600, 0x26FF),
    (0x2700, 0x27BF),
    (0x2300, 0x23FF),
    (0x2B50, 0x2B55),
    (0x1F1E6, 0x1F1FF),
)

_EMOJI_JOINERS = frozenset({0x200D, 0xFE0F, 0x20E3})
_SKIN_TONES = range(0x1F3FB, 0x1F400)


def _codepoint_in_emoji_range(codepoint: int) -> bool:
    if codepoint in _EMOJI_JOINERS:
        return True
    if codepoint in _SKIN_TONES:
        return True
    for start, end in _EMOJI_RANGES:
        if start <= codepoint <= end:
            return True
    name = unicodedata.name(chr(codepoint), "")
    return "EMOJI" in name


def is_valid_ticket_emoji(value: str) -> bool:
    text = value.strip()
    if not text or len(text) > 128:
        return False
    if DISCORD_CUSTOM_EMOJI.fullmatch(text):
        return True
    if KEYCAP_EMOJI.fullmatch(text):
        return True
    if re.search(r"[a-zA-Z]", text):
        return False
    has_emoji = False
    for char in text:
        codepoint = ord(char)
        if _codepoint_in_emoji_range(codepoint):
            if codepoint not in _EMOJI_JOINERS and codepoint not in _SKIN_TONES:
                has_emoji = True
            continue
        if 0x30 <= codepoint <= 0x39 or codepoint in (0x23, 0x2A):
            continue
        return False
    return has_emoji


def normalize_ticket_emoji(value: str, *, default: str = "🎫") -> str:
    text = value.strip()
    if not text:
        return default
    if not is_valid_ticket_emoji(text):
        raise ValueError(
            "Enter a valid emoji (Unicode emoji or Discord custom emoji like <:name:123>). "
            "Plain text is not allowed."
        )
    return text
