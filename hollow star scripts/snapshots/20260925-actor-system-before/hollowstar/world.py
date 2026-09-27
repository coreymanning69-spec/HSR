"""Shared, public setting contract; no live chronology or divine dialogue."""
from copy import deepcopy

_WORLD = {
    "schema_version": "hollow-star-world-1",
    "setting": "Divine Mythos / D&D world",
    "dungeon": "Hollow Star Reliquary",
    "creator": "Soliera",
    "creation_authority": "God; divine specification makes the dungeon laws real",
    "conceived_by": ["Ember", "Sera"],
    "purpose": "Adventure, curiosity, entertainment, and shared enjoyment",
    "social_context": {
        "community": "The Sanctum and its friends",
        "interested_adventurers": ["Wren", "Doran", "Letha"],
        "note": "Interest in new experiences is not an automatic party assignment or mechanical roster certification",
    },
    "premise": "Soliera creates a real dungeon in their D&D world from Ember and Sera's imagined design.",
    "local_laws": "Rooms, resets, temporary rewards, and other dungeon rules are Soliera's authored environmental laws.",
    "authority": "DM046_0 sections 1, 2, 3, 7, 12; Corey implementation direction 2026-09-05",
    "chronology": "Design premise; gateway, first entry, and witnesses require authored play",
    "narration": "Report resolved events and visible consequences; divine dialogue remains Corey's",
}


def world_context() -> dict:
    """Return an isolated view, so callers cannot rewrite the shared premise."""
    return deepcopy(_WORLD)
