"""Low-token, deterministic local conversation and reaction-tree resolution for Floor One and tactical encounters."""
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


DISPOSITION_STEPS = ["hostile", "wary", "neutral", "warm", "allied"]


def shift_disposition(current: str, step: int) -> str:
    current = current.lower()
    if current not in DISPOSITION_STEPS:
        current = "neutral"
    idx = DISPOSITION_STEPS.index(current)
    new_idx = max(0, min(len(DISPOSITION_STEPS) - 1, idx + step))
    return DISPOSITION_STEPS[new_idx]


def options(target: dict) -> list[dict]:
    """Return the visible, deterministic dialogue and reaction tree for an NPC or enemy.

    The tree is a public affordance, not a leak of hidden state. The host resolves
    the chosen path through ``resolve`` so disposition, knowledge, and consequences
    remain authoritative.
    """
    target = target if isinstance(target, dict) else {}
    offers = target.get("offers") if isinstance(target.get("offers"), dict) else {}
    disposition = str(target.get("disposition", "neutral")).lower()
    traits = [str(t).lower().replace("_", "-") for t in target.get("traits", [])]
    motive = str(target.get("core_motive", "")).lower()

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
    if offers.get("shop") or offers.get("trade"):
        rows.append({"id": "trade-offer", "label": "Ask what they can trade", "mode": "trade",
                     "text": "What can you trade?"})
    if offers.get("identify"):
        rows.append({"id": "ask-identify", "label": "Ask about identification", "mode": "ask",
                     "text": "Can you identify anything unusual?"})

    # Trait-specific dialogue options
    if "greedy" in traits or motive == "greed" or "mercenary" in traits:
        rows.append({"id": "bribe-coin", "label": "Offer a purse of coin", "mode": "bribe",
                     "text": "Here is coin for your trouble. Let's speak plainly."})
    if "devout" in traits or motive == "faith":
        rows.append({"id": "ask-blessing", "label": "Invoke sacred rites", "mode": "persuade",
                     "text": "May the enduring light bless our exchange in peace."})
    if "curious" in traits or motive == "knowledge":
        rows.append({"id": "share-lore", "label": "Share a secret of the depths", "mode": "persuade",
                     "text": "We have seen the ancient seals below. Let us trade knowledge."})

    # De-escalation and surrender options
    if disposition in {"hostile", "wary"}:
        rows.append({"id": "de-escalate", "label": "Lower the temperature", "mode": "speak",
                     "text": "We are looking for information, not a fight."})
        rows.append({"id": "demand-yield", "label": "Demand surrender", "mode": "threaten",
                     "text": "Lower your weapons and yield now while you still draw breath."})
    else:
        rows.append({"id": "probe-rumors", "label": "Probe for rumors", "mode": "ask",
                     "text": "What secrets have strangers brought into these corridors?"})

    return rows


def resolve(target: dict, text: str = "", mode: str = "speak") -> dict:
    """Resolve a conversation/interaction through a trait-driven dynamic state machine."""
    words = _tokens(text)
    name = str(target.get("name", "resident"))
    disposition = str(target.get("disposition", "neutral")).lower()
    if disposition not in DISPOSITION_STEPS:
        disposition = "neutral"
    traits = [str(value).replace("_", " ") for value in target.get("traits", []) if isinstance(value, str)]
    offers = target.get("offers", [])
    tells = target.get("tells", [])
    relationships = target.get("relationships", {})
    motive = str(target.get("core_motive", "survival")).lower()

    hp = int(target.get("hp", 10))
    max_hp = int(target.get("max_hp", 10) or 10)
    hp_ratio = hp / max_hp if max_hp > 0 else 1.0
    surrender_threshold = float(target.get("surrender_hp_threshold", 0.35))

    surrender_offered = False
    truce_agreed = False

    # Check mode & words
    if mode in {"threaten", "insult"} or words & {"threat", "threaten", "hurt", "kill", "idiot", "yield", "surrender"}:
        if "cowardly" in traits or hp_ratio <= surrender_threshold or "flee" in words:
            response = f"{name} pales, hands trembling as they step back from violence. 'Hold! There is no need for bloodshed. I yield.'"
            next_disposition = "wary" if disposition == "hostile" else disposition
            reaction = "yielding to display of force"
            consequence = "surrender_offered"
            surrender_offered = True
        elif "proud" in traits or "fanatical" in traits:
            response = f"{name} bristles with fury at your words, jaw tightening as steel bare inches from their grip. 'You dare speak to me so? Draw, then!'"
            next_disposition = "hostile"
            reaction = "rejecting intimidation with defiance"
            consequence = "hostility_escalated"
        else:
            response = f"{name} stops treating this as a casual exchange and watches your hands."
            next_disposition = "hostile" if mode == "threaten" or "threaten" in words else "wary"
            reaction = "calling attention to your behavior"
            consequence = "local_tension"

    elif mode == "bribe" or words & {"coin", "bribe", "gold", "purse", "silver", "pay", "payment"}:
        if "greedy" in traits or "mercenary" in traits or motive == "greed":
            response = f"{name}'s eyes light up as they pocket the coin with practiced grace. 'Now you are speaking sense. Ask what you will.'"
            next_disposition = shift_disposition(disposition, 1)
            reaction = "accepting payment with enthusiasm"
            consequence = "bribe_accepted"
        elif "devout" in traits or motive in {"duty", "faith"}:
            response = f"{name} looks at the coin with cold disdain. 'Keep your silver. Oaths here are not bought and sold like market grain.'"
            next_disposition = shift_disposition(disposition, -1)
            reaction = "rejecting bribery with moral indignation"
            consequence = "bribe_rejected"
        else:
            response = f"{name} takes the coin after a cautious pause. 'Fair enough. I can share what I know.'"
            next_disposition = shift_disposition(disposition, 1)
            reaction = "accepting modest gratuity"
            consequence = "bribe_accepted"

    elif words & {"peace", "lower", "calm", "talk", "temperature", "fight"} and (mode == "speak" or "de-escalate" in text):
        if "fanatical" in traits:
            response = f"{name} remains unyielding, eyes burning with fervor. 'There is no peace between our paths.'"
            next_disposition = disposition
            reaction = "resisting de-escalation"
            consequence = "stalemate"
        else:
            response = f"{name} eases their posture slightly, blade remaining sheathed. 'Very well. Speak your piece, but keep your hands where I can see them.'"
            next_disposition = shift_disposition(disposition, 1) if disposition in {"hostile", "wary"} else disposition
            reaction = "relaxing posture"
            consequence = "temperature_lowered"
            truce_agreed = True

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
        if "watchful" in traits or "cynical" in traits:
            response = f"{name} narrows their eyes, catching the inconsistency at once. 'Do not take me for a fool. I know what lies sound like.'"
            next_disposition = shift_disposition(disposition, -1)
            reaction = "calling out deceit"
            consequence = "suspicion_recorded"
        else:
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
        "core_motive": motive,
        "surrender_offered": surrender_offered,
        "truce_agreed": truce_agreed,
        "relationship_count": len(relationships) if isinstance(relationships, dict) else 0,
        "public": True,
    }
