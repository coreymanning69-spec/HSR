"""Deterministic parser for commands about the HSR session itself.

Gameplay intent belongs in :mod:`hollowstar.intent`.  This module handles the
outer shell: starting or loading a run, selecting a mode, inspecting the
current presentation, and changing UI/session preferences.  It deliberately
returns no gameplay action and never guesses a run identifier.
"""

from __future__ import annotations

import re


class SessionIntentError(ValueError):
    """The input resembles a session request but cannot be completed safely."""


def vocabulary() -> dict:
    """Public, UI-neutral vocabulary shared by terminal and HSR Interface."""
    return {
        "schema": "hsr-session-vocabulary-1",
        "start": ["start the game", "start a run", "new game", "I am new here", "this is my first time"],
        "character": ["make a character", "create a character", "start character creation"],
        "navigation": ["show me the options", "back", "wrong option", "I am stuck", "save and quit"],
        "inspection": ["look around", "show my equipment", "show character", "show room"],
        "social": ["talk to <resident>", "ask <resident> about the room", "thank <resident>"],
        "note": "These phrases select a host route; gameplay and NPC consequences remain HSRHost-owned.",
    }


def parse_session_intent(text: str) -> dict | None:
    """Translate a clear session-level phrase into a small command envelope.

    ``None`` means the text is not a session command and should be offered to
    the gameplay intent parser.  The result is intentionally UI-neutral so the
    terminal, CLI, MCP, and future visual clients can share it.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    raw = re.sub(r"\s+", " ", text.strip().lower())
    compact = re.sub(r"[^a-z0-9 ]+", "", raw)

    if compact in {"quit", "exit", "close the game", "save and quit"}:
        return {"type": "quit", "save": compact == "save and quit"}
    if compact in {"help", "show help", "what can i do", "what can i do here", "show me the options", "show options", "options", "im not sure what to do", "i am not sure what to do"}:
        return {"type": "options"}
    if compact in {"im stuck", "i am stuck", "im bugged", "i am bugged", "help im stuck", "help i am stuck", "recover", "return to the previous room"}:
        return {"type": "recover_previous_room"}
    if compact in {"back", "go back", "wrong option", "i didnt mean to hit that", "i did not mean to hit that", "thats wrong", "that is wrong"}:
        return {"type": "back"}
    if compact in {"full help", "full reference", "command reference", "commands", "command help"}:
        return {"type": "help"}
    if compact in {"save", "save the game", "save my run"}:
        return {"type": "save"}
    if compact in {"show gear", "show equipment", "show my gear", "show my equipment"}:
        return {"type": "show", "target": "equipment"}
    if compact in {"show character", "show character sheet", "show my character", "show status", "character", "character sheet"}:
        return {"type": "show", "target": "character"}
    if compact in {"show room", "look around", "observe", "what do i see", "look", "room"}:
        return {"type": "show", "target": "room"}
    if compact in {"auto", "turn on auto", "enable auto", "auto mode"}:
        return {"type": "set_auto", "enabled": True}
    if compact in {"manual", "turn off auto", "disable auto", "manual mode"}:
        return {"type": "set_auto", "enabled": False}
    if compact in {
        "start", "start the game", "new game", "start a new game", "start a run",
        "lets start a run", "begin a run", "begin the run", "new run",
        "i am new here", "im new here", "this is my first time", "im a new player", "i am a new player",
    }:
        return {"type": "start", "mode": "DESIGN"}
    if compact in {
        "make a character", "create a character", "make my character", "new character",
        "lets start cc", "lets start character creation", "start character creation",
        "lets make a dude", "make a dude", "lets start a character", "start a character",
    }:
        return {"type": "start", "mode": "DESIGN", "lead": "custom"}
    if compact in {"begin with a level three character", "lets begin with a level three character"}:
        return {"type": "start", "mode": "DESIGN", "lead": "custom", "level": 3}
    if compact in {"play a premade", "pick a premade", "choose a premade", "load a premade character"}:
        return {"type": "start", "mode": "DESIGN", "lead": "premade"}
    if compact in {"sandbox", "start sandbox", "start a sandbox", "lets do a sandbox", "let's do a sandbox"}:
        return {"type": "start", "mode": "SANDBOX"}
    if compact in {
        "load", "load a run", "load my run", "load my saved run", "continue",
        "continue my run", "continue the run", "resume my run", "resume",
    }:
        return {"type": "load"}

    if "sandbox" in compact and any(word in compact for word in ("start", "do", "play", "enter")):
        return {"type": "start", "mode": "SANDBOX"}
    choice = re.fullmatch(r"(?:lets do|i pick|itll be|it will be) (.+)", compact)
    if choice and choice.group(1).strip():
        return {"type": "select", "choice": choice.group(1).strip()}
    return None
