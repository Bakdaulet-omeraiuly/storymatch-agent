"""
Narrative Taste Memory -- MVP version.

The research doc's stretch goal is Amazon Bedrock AgentCore Memory. For a
solo 24-48h build, a local JSON file gives the same *product* behavior
(the agent remembers what stories a user likes/dislikes across turns and
sessions) without needing AgentCore Memory provisioned before the demo.

Upgrade path (documented in README): swap `_load`/`_save` for AgentCore
Memory's client calls; `tools.py` doesn't need to change since it only
calls `get_taste_memory` / `update_taste_memory`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MEMORY_PATH = Path(__file__).resolve().parent.parent / "data" / "taste_memory.json"


def _load() -> dict[str, Any]:
    if not MEMORY_PATH.exists():
        return {}
    try:
        with open(MEMORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict[str, Any]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_profile(user_id: str) -> dict[str, list[str]]:
    data = _load()
    profile = data.get(user_id, {"likes": [], "dislikes": []})
    return {"likes": profile.get("likes", []), "dislikes": profile.get("dislikes", [])}


def update_profile(user_id: str, likes: list[str], dislikes: list[str]) -> dict[str, list[str]]:
    data = _load()
    profile = data.setdefault(user_id, {"likes": [], "dislikes": []})

    for tag in likes or []:
        tag = tag.strip().lower()
        if tag and tag not in profile["likes"]:
            profile["likes"].append(tag)
        if tag in profile.get("dislikes", []):
            profile["dislikes"].remove(tag)

    for tag in dislikes or []:
        tag = tag.strip().lower()
        if tag and tag not in profile["dislikes"]:
            profile["dislikes"].append(tag)
        if tag in profile.get("likes", []):
            profile["likes"].remove(tag)

    _save(data)
    return {"likes": profile["likes"], "dislikes": profile["dislikes"]}


def reset_profile(user_id: str) -> None:
    data = _load()
    data.pop(user_id, None)
    _save(data)
