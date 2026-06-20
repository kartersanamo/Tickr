"""CRUD helpers for guild ticket_types JSON."""

from __future__ import annotations

import copy
from typing import Any

RESERVED_KEYS = frozenset({"TOGGLE_STATUS"})


def category_names(data: dict) -> list[str]:
    return [
        key
        for key in data.keys()
        if key not in RESERVED_KEYS and isinstance(data.get(key), dict)
    ]


def ticket_type_names(data: dict, category: str) -> list[str]:
    block = data.get(category, {})
    if not isinstance(block, dict):
        return []
    return [name for name, info in block.items() if isinstance(info, dict)]


def new_question(*, label: str, placeholder: str = "", length: str = "Long") -> dict:
    return {
        "Label": label[:45],
        "Placeholder": placeholder[:100],
        "Length": "Short" if length == "Short" else "Long",
    }


def new_ticket_type(
    *,
    description: str = "New ticket type",
    emoji: str = "🎫",
    category_id: int | None = None,
    staff_role_id: int | None = None,
    message: str = "Please describe your issue in detail.",
) -> dict:
    roles = [staff_role_id] if staff_role_id else []
    return {
        "Status": "Enabled",
        "Emoji": emoji or "🎫",
        "Description": description[:100],
        "Category": category_id,
        "PrivateMode": None,
        "Message": message,
        "Roles": roles.copy(),
        "Pings": roles.copy(),
        "Questions": [
            new_question(
                label="Details",
                placeholder="Describe your issue...",
                length="Long",
            )
        ],
    }


def add_category(data: dict, name: str) -> dict:
    clean = name.strip()
    if not clean:
        raise ValueError("Category name cannot be empty.")
    if clean in RESERVED_KEYS:
        raise ValueError(f"'{clean}' is a reserved name.")
    if clean in data:
        raise ValueError(f"Category '{clean}' already exists.")
    updated = copy.deepcopy(data)
    updated[clean] = {}
    return updated


def remove_category(data: dict, name: str) -> dict:
    if name in RESERVED_KEYS:
        raise ValueError(f"Cannot remove '{name}'.")
    updated = copy.deepcopy(data)
    if name not in updated:
        raise ValueError(f"Category '{name}' not found.")
    del updated[name]
    return updated


def rename_category(data: dict, old_name: str, new_name: str) -> dict:
    clean = new_name.strip()
    if not clean:
        raise ValueError("Category name cannot be empty.")
    if clean in RESERVED_KEYS:
        raise ValueError(f"'{clean}' is a reserved name.")
    if old_name not in data or old_name in RESERVED_KEYS:
        raise ValueError(f"Category '{old_name}' not found.")
    if clean != old_name and clean in data:
        raise ValueError(f"Category '{clean}' already exists.")
    updated = copy.deepcopy(data)
    updated[clean] = updated.pop(old_name)
    return updated


def add_ticket_type(
    data: dict,
    category: str,
    type_name: str,
    *,
    template: dict | None = None,
) -> dict:
    clean = type_name.strip()
    if not clean:
        raise ValueError("Ticket type name cannot be empty.")
    if category not in data or category in RESERVED_KEYS:
        raise ValueError(f"Category '{category}' not found.")
    block = data[category]
    if not isinstance(block, dict):
        raise ValueError(f"Category '{category}' is invalid.")
    if clean in block:
        raise ValueError(f"Ticket type '{clean}' already exists in '{category}'.")
    updated = copy.deepcopy(data)
    updated[category][clean] = copy.deepcopy(template or new_ticket_type())
    return updated


def remove_ticket_type(data: dict, category: str, type_name: str) -> dict:
    if category not in data or category in RESERVED_KEYS:
        raise ValueError(f"Category '{category}' not found.")
    block = data[category]
    if not isinstance(block, dict) or type_name not in block:
        raise ValueError(f"Ticket type '{type_name}' not found.")
    updated = copy.deepcopy(data)
    del updated[category][type_name]
    return updated


def rename_ticket_type(data: dict, category: str, old_name: str, new_name: str) -> dict:
    clean = new_name.strip()
    if not clean:
        raise ValueError("Ticket type name cannot be empty.")
    if category not in data:
        raise ValueError(f"Category '{category}' not found.")
    block = data[category]
    if old_name not in block:
        raise ValueError(f"Ticket type '{old_name}' not found.")
    if clean != old_name and clean in block:
        raise ValueError(f"Ticket type '{clean}' already exists.")
    updated = copy.deepcopy(data)
    updated[category][clean] = updated[category].pop(old_name)
    return updated


def duplicate_ticket_type(
    data: dict, category: str, type_name: str, new_name: str
) -> dict:
    if category not in data or type_name not in data.get(category, {}):
        raise ValueError("Ticket type not found.")
    clone = copy.deepcopy(data[category][type_name])
    return add_ticket_type(data, category, new_name, template=clone)


def add_question(data: dict, category: str, type_name: str, question: dict) -> dict:
    if category not in data or type_name not in data.get(category, {}):
        raise ValueError("Ticket type not found.")
    updated = copy.deepcopy(data)
    questions = updated[category][type_name].setdefault("Questions", [])
    label = question.get("Label", "").strip()
    if not label:
        raise ValueError("Question label is required.")
    if any(q.get("Label") == label for q in questions):
        raise ValueError(f"Question '{label}' already exists.")
    if len(questions) >= 5:
        raise ValueError("Discord modals allow at most 5 questions per ticket type.")
    questions.append(question)
    return updated


def remove_question(
    data: dict, category: str, type_name: str, question_label: str
) -> dict:
    if category not in data or type_name not in data.get(category, {}):
        raise ValueError("Ticket type not found.")
    updated = copy.deepcopy(data)
    questions = updated[category][type_name].get("Questions", [])
    filtered = [q for q in questions if q.get("Label") != question_label]
    if len(filtered) == len(questions):
        raise ValueError(f"Question '{question_label}' not found.")
    updated[category][type_name]["Questions"] = filtered
    return updated


def update_question(
    data: dict,
    category: str,
    type_name: str,
    question_label: str,
    *,
    new_label: str | None = None,
    placeholder: str | None = None,
    length: str | None = None,
) -> dict:
    if category not in data or type_name not in data.get(category, {}):
        raise ValueError("Ticket type not found.")
    updated = copy.deepcopy(data)
    questions = updated[category][type_name].get("Questions", [])
    index = next(
        (i for i, q in enumerate(questions) if q.get("Label") == question_label),
        None,
    )
    if index is None:
        raise ValueError(f"Question '{question_label}' not found.")
    question = questions[index]
    if new_label is not None:
        clean = new_label.strip()[:45]
        if not clean:
            raise ValueError("Question label cannot be empty.")
        if clean != question_label and any(q.get("Label") == clean for q in questions):
            raise ValueError(f"Question '{clean}' already exists.")
        question["Label"] = clean
    if placeholder is not None:
        question["Placeholder"] = placeholder[:100]
    if length is not None:
        question["Length"] = "Short" if length == "Short" else "Long"
    return updated


def set_ticket_emoji(
    data: dict, category: str, type_name: str, emoji: str
) -> dict:
    if category not in data or type_name not in data.get(category, {}):
        raise ValueError("Ticket type not found.")
    updated = copy.deepcopy(data)
    updated[category][type_name]["Emoji"] = emoji.strip() or "🎫"
    return updated


def set_private_mode(
    data: dict, category: str, type_name: str, mode: str | None
) -> dict:
    if category not in data or type_name not in data.get(category, {}):
        raise ValueError("Ticket type not found.")
    updated = copy.deepcopy(data)
    if mode not in (None, "admin", "management"):
        raise ValueError("Private mode must be admin, management, or cleared.")
    updated[category][type_name]["PrivateMode"] = mode
    return updated


def cycle_private_mode(current: Any) -> str | None:
    order: list[str | None] = [None, "admin", "management"]
    try:
        idx = order.index(current if current in order else None)
    except ValueError:
        idx = 0
    return order[(idx + 1) % len(order)]
