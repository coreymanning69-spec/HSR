"""Event-driven Sera and Ember commentary for Wren/Doran Reliquary runs.

This module is presentation-only. It never rolls, changes rewards, resolves
combat, or reveals sealed room state.
"""
from __future__ import annotations

import copy

from hollowstar import divine_voice, doran_voice


COOLDOWNS = {
    "entry": 2,
    "combat": 1,
    "reward": 1,
    "upgrade": 1,
    "danger": 2,
    "terminal": 0,
}


# Sera/Ember line pools live in hollowstar/divine_voice.py.


# Onomatopoeia pool. Presentation cue only — the client may print or play it.
SFX = {
    "entry": ["creeeak", "clunk", "drip... drip", "hsssh", "thud-thud", "skree"],
    "combat": ["SHNK!", "CLANG!", "THWACK!", "WHOOSH", "KSSH!", "THUD!", "SWISH", "KRAK!", "CHNK!", "WHUMP!"],
    "critical": ["KRA-KOOM!", "SHHRAAK!", "CRUNCH!", "SPLAT!", "KA-CHUNK!", "BWAMM!"],
    "blocked": ["TINK!", "CLNK", "SKRRT", "DONK", "PING!", "THNK"],
    "reward": ["clink-clink", "jingle", "ka-ching!", "shhk", "plink"],
    "upgrade": ["tak-tak-tak", "shiiing", "hsss", "clank", "zzzing!"],
    "danger": ["rrrumble", "hisssss", "CRACK", "tick... tick...", "wub-wub-wub", "grrrk"],
    "terminal": ["fwoomp", "thuuum", "...", "clap. clap."],
}


def _pick(pool: list, turn: int, salt: int = 0):
    return pool[(turn + salt) % len(pool)] if pool else None


def _has_steward(run) -> bool:
    selectors = run.context.get("party_selectors", [])
    names = {str(value).lower().split(":", 1)[-1] for value in selectors}
    return bool(names & {"doran", "wren"}) or any(
        actor.name.lower() in {"doran", "wren"} for actor in run.party
    )


def _classify(action_type: str, event: dict) -> str | None:
    action_type = str(action_type or "").lower()
    event_type = str(event.get("type", "")).lower()
    nested = event.get("combat") if isinstance(event.get("combat"), dict) else None
    if nested:
        nested_type = str(nested.get("type", "")).lower()
        if nested.get("critical") or nested.get("overkill"):
            return "critical"
        if nested_type in {"attack", "permission_blocked", "conflict"}:
            return "combat" if nested_type != "permission_blocked" else "blocked"
    if action_type in {"design_start", "enter"} or event_type in {"entered_room", "room_entered"}:
        return "entry"
    if event_type in {"permission_blocked", "blocked", "immunity", "resistance_blocked"}:
        return "blocked"
    if event_type in {"attack", "conflict", "combat", "night_patrol"} or action_type in {"attack", "fight", "cast"}:
        if event.get("critical") or event.get("overkill"):
            return "critical"
        return "combat"
    if event_type in {"room_resolved", "purchase"} or "reward" in event:
        return "reward"
    if action_type in {"craft", "upgrade"} or event_type in {"craft", "upgrade"}:
        return "upgrade"
    if event_type in {"cocoon_cracked", "cocoon_opened", "hazard", "avoidance_failed"}:
        return "danger"
    if event_type in {"ended", "run_ended"}:
        return "terminal"
    return None


def _casts(event: dict) -> list[dict]:
    """Spell/feature events inside this event, outermost first."""
    found = []
    for candidate in (event, event.get("combat"), *(event.get("events") or [])):
        if isinstance(candidate, dict) and (candidate.get("type") == "cast" or candidate.get("feature")):
            found.append(candidate)
    return found


def attach(run, action_type: str, event: dict) -> dict:
    """Attach Sera/Ember commentary, a Doran line and an SFX cue to an event.

    Sera/Ember keep their per-kind cooldowns. Doran is independent: he reacts
    to the specific situation or, while exploring, sometimes thinks aloud.
    """
    if not isinstance(event, dict) or not _has_steward(run):
        return event
    # Dungeon runs keep commentary state with the dungeon (it rides its
    # snapshots); arena/boss rehearsals without one keep it on the run context.
    dungeon = run.context.get("dungeon")
    holder = dungeon if isinstance(dungeon, dict) else run.context
    key = "commentary" if holder is dungeon else "commentary_state"
    state = holder.setdefault(key, {"enabled": True, "turn": 0, "last": {}})
    if state.get("enabled", True) is False:
        return event
    turn = int(state.get("turn", 0)) + 1
    state["turn"] = turn
    kind = _classify(action_type, event)
    lines = []
    last = state.setdefault("last", {})
    seed = run.context.get("seed") or run.context.get("run_seed") or ""
    if kind is not None and turn - int(last.get(kind, -10_000)) > COOLDOWNS.get(kind, 1):
        last[kind] = turn
        lines = divine_voice.general(kind, turn, state, seed)
        sfx = _pick(SFX.get(kind, []), turn, 3)
        if sfx:
            nested = event.get("combat") if isinstance(event.get("combat"), dict) else event
            event["sfx"] = {"text": sfx, "trigger": kind, "target": nested.get("target")}
    # Wren's divine spells get answered every time, independent of cooldowns.
    for cast in _casts(event):
        caster = getattr(doran_voice._roster(run).get(cast.get("actor")), "name", None)
        answer = divine_voice.divine(run, cast, turn, state, caster, seed)
        if answer:
            # A prayer answered is the moment; drop generic chatter and SFX.
            lines = answer
            event.pop("sfx", None)
            break
    doran = doran_voice.react(run, action_type, event, kind, turn, state)
    if doran:
        lines.append(doran)
    if lines:
        event["commentary"] = lines
        state["last_event"] = copy.deepcopy(lines)
    return event
