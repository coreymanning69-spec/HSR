"""Low-token, deterministic local conversation resolution for Floor One."""
from __future__ import annotations

import copy
import re


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", str(text).lower()))


def _first(values: object, default: str) -> str:
    if isinstance(values, list):
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()
    return default


def options(target: dict) -> list[dict]:
    """Return the visible, deterministic dialogue tree for one resident.

    The tree is a public affordance, not a leak of motives or relationship
    weights.  The host still resolves the selected line through ``resolve`` so
    disposition, knowledge, and consequences remain authoritative.
    """
    target = target if isinstance(target, dict) else {}
    offers = target.get("offers") if isinstance(target.get("offers"), dict) else {}
    disposition = str(target.get("disposition", "neutral"))
    rows = [
        {"id": "ask-town", "label": "Ask what is happening", "mode": "ask",
         "text": "What is happening in town?"},
        {"id": "ask-route", "label": "Ask about the well route", "mode": "ask",
         "text": "Where is the route to the well?"},
        {"id": "ask-self", "label": "Ask who they are", "mode": "ask",
         "text": "Who are you, and what do you do here?"},
    ]
    if offers.get("quest"):
        rows.append({"id": "ask-work", "label": "Ask what needs doing", "mode": "ask",
                     "text": "Is there work that needs doing?"})
    if offers.get("shop"):
        rows.append({"id": "trade-offer", "label": "Ask what they can trade", "mode": "trade",
                     "text": "What can you trade?"})
    if offers.get("identify"):
        rows.append({"id": "ask-identify", "label": "Ask about identification", "mode": "ask",
                     "text": "Can you identify anything unusual?"})
    if disposition in {"hostile", "wary"}:
        rows.append({"id": "de-escalate", "label": "Lower the temperature", "mode": "speak",
                     "text": "We are looking for information, not a fight."})
    return rows


def resolve(target: dict, text: str = "", mode: str = "speak") -> dict:
    """Resolve a conversation without a model call or hidden-state leakage."""
    words = _tokens(text)
    name = str(target.get("name", "resident"))
    disposition = str(target.get("disposition", "neutral"))
    traits = [str(value).replace("_", " ") for value in target.get("traits", []) if isinstance(value, str)]
    offers = target.get("offers", [])
    tells = target.get("tells", [])
    relationships = target.get("relationships", {})
    if mode in {"threaten", "insult"} or words & {"threat", "threaten", "hurt", "kill", "idiot"}:
        response = f"{name} stops treating this as a casual exchange and watches your hands."
        next_disposition = "hostile" if mode == "threaten" or "threaten" in words else "wary"
        reaction = "calling attention to your behavior"
        consequence = "local_tension"
    elif words & {"help", "route", "way", "where", "well", "waterwheel", "hatch", "door"}:
        clue = _first(tells, "The resident gives you a careful answer, but keeps one detail back.")
        response = f"{name} considers the question. {clue}"
        next_disposition = disposition
        reaction = "sharing a guarded local clue"
        consequence = "knowledge_shared"
    elif words & {"buy", "trade", "sell", "work", "price", "food", "room"} and offers:
        offer = _first(offers, "a practical arrangement")
        response = f"{name} gestures toward {offer}. The terms are plain enough to understand."
        next_disposition = disposition
        reaction = "offering a practical exchange"
        consequence = "offer_revealed"
    elif words & {"who", "what", "why", "know", "remember", "tell"}:
        trait = traits[0] if traits else "a guarded local"
        response = f"{name} answers as {trait}, measuring how much of the town you already understand."
        next_disposition = disposition
        reaction = "answering a direct question"
        consequence = "relationship_observed"
    elif mode == "lie":
        response = f"{name} listens without agreeing. The lie has been noticed, even if it has not been challenged."
        next_disposition = "wary" if disposition in {"warm", "helpful", "neutral"} else disposition
        reaction = "testing the visitor's story"
        consequence = "suspicion_recorded"
    else:
        response = f"{name} gives you the sort of answer people give when they expect to see you again."
        next_disposition = disposition
        reaction = "answering cautiously"
        consequence = "conversation_recorded"
    return {
        "text": response,
        "mode": mode,
        "disposition_before": disposition,
        "disposition_after": next_disposition,
        "reaction": reaction,
        "consequence": consequence,
        "visible_traits": traits[:3],
        "relationship_count": len(relationships) if isinstance(relationships, dict) else 0,
        "public": True,
    }
