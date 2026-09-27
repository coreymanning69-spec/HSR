"""What the world notices about a figure, and what residents say about it.

Salience turns a figure's public look -- creator appearance, the presentation
block of every equipped item, visible condition -- into a short list of tags
("an enclosed helm", "a fire-touched weapon", "fresh wounds").  The rules and
the resident remarks live in content/salience.json, so both can grow without
code.  Because the tags come from item presentation, which the items module
derives from mechanics, a newly equipped relic is noticed with no new rule.

Flavour only.  A tag never touches a disposition, a price, a roll or the RNG;
remarks are picked from a stable hash of who is looking at what.
"""
from __future__ import annotations

import colorsys
import copy
import hashlib
import json
from functools import lru_cache
from pathlib import Path

SALIENCE_PATH = Path(__file__).with_name("content") / "salience.json"
SALIENCE_SCHEMA = "hollow-star-salience-1"


@lru_cache(maxsize=1)
def _content() -> dict:
    try:
        data = json.loads(SALIENCE_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) and data.get("schema") == SALIENCE_SCHEMA else {}


def hue_family(hex_value: object) -> str | None:
    """Coarse colour name for a '#rrggbb' value (red, blue, grey, ...)."""
    if not isinstance(hex_value, str) or len(hex_value) != 7 or not hex_value.startswith("#"):
        return None
    try:
        r, g, b = (int(hex_value[i:i + 2], 16) / 255 for i in (1, 3, 5))
    except ValueError:
        return None
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if v < .18:
        return "black"
    if s < .18:
        return "white" if v > .82 else "grey"
    deg = h * 360
    for limit, name in ((15, "red"), (42, "orange"), (68, "yellow"), (165, "green"), (255, "blue"), (335, "purple")):
        if deg < limit:
            return name
    return "red"


def gear_rows(actor: dict) -> list[dict]:
    """Presentation blocks for everything a figure visibly wears or carries."""
    from hollowstar.items import Item, item_presentation
    rows = []
    for item in list(actor.get("equipment") or []) + list(actor.get("costume") or []):
        if isinstance(item, Item):
            rows.append(item_presentation(item))
        elif isinstance(item, dict):
            block = item.get("presentation") if isinstance(item.get("presentation"), dict) else None
            if block is None and "silhouette" in item and "name" not in item:
                block = item                                   # already a presentation row (costume)
            if block is None:
                # A raw kit row (a class's starting equipment in a creator
                # preview): derive its presentation exactly as a saved item would.
                from hollowstar.profiles import ProfileError, _item
                try:
                    block = item_presentation(_item(item))
                except (ProfileError, KeyError, TypeError, ValueError):
                    continue
            # An unidentified Imprint is redacted to "unknown" and must not be read.
            if block.get("rarity") != "unknown":
                rows.append(block)
    return rows


def _matches(value, wanted) -> bool:
    wanted = wanted if isinstance(wanted, list) else [wanted]
    if isinstance(value, list):
        return any(str(v).lower() in wanted for v in value)
    return str(value).lower() in wanted if value is not None else False


def _condition(cond: dict, actor: dict, gear: list[dict]) -> bool:
    if not isinstance(cond, dict):
        return False
    appearance = actor.get("appearance") if isinstance(actor.get("appearance"), dict) else {}
    if "gear" in cond:
        return any(all(_matches(row.get(key), value) for key, value in cond["gear"].items()) for row in gear)
    if "appearance" in cond:
        return all(isinstance(appearance.get(field), dict) and _matches(appearance[field].get("id"), value)
                   for field, value in cond["appearance"].items())
    if "colour" in cond:
        spec = cond["colour"]
        entry = appearance.get(spec.get("field"))
        return isinstance(entry, dict) and _matches(hue_family(entry.get("hex")), spec.get("family"))
    if "race" in cond:
        return _matches(actor.get("race_id") or actor.get("species"), cond["race"])
    if "age" in cond:
        return actor.get("age") == cond["age"] or (cond["age"] == "child" and bool(actor.get("child")))
    if "hp_below" in cond:
        hp, top = actor.get("hp"), actor.get("max_hp")
        return isinstance(hp, (int, float)) and isinstance(top, (int, float)) and top > 0 and 0 < hp < top * float(cond["hp_below"])
    return False


def notice(actor: dict | None) -> list[str]:
    """Salience tags for one figure, most striking first."""
    if not isinstance(actor, dict):
        return []
    content = _content()
    gear = gear_rows(actor)
    # A champion's canon look (what its rig draws) is always noticed.
    fixed = set(content.get("champions", {}).get(str(actor.get("identity") or "").lower(), []))
    hits = []
    for index, rule in enumerate(content.get("rules", [])):
        if not isinstance(rule, dict):
            continue
        if rule["tag"] in fixed or any(_condition(cond, actor, gear) for cond in rule.get("any", [])):
            hits.append((-float(rule.get("weight", 0)), index, rule["tag"]))
    return [tag for _, _, tag in sorted(hits)][:int(content.get("max_tags", 6))]


def labels(tags: list[str]) -> list[str]:
    """Human-readable labels for tags, in the same order."""
    by_tag = {rule["tag"]: rule.get("label", rule["tag"]) for rule in _content().get("rules", []) if isinstance(rule, dict)}
    return [by_tag.get(tag, tag) for tag in tags]


def signature(tags: list[str]) -> str:
    """A stable key for 'this look': residents remark again only when it changes."""
    return "|".join(sorted(tags))


def remark(resident: dict, tags: list[str], lead_name: str, seed: str) -> dict | None:
    """One resident's remark about the most striking tag they have a line for."""
    if not isinstance(resident, dict) or not tags:
        return None
    reactions = _content().get("reactions", {})
    klass = str(resident.get("class", ""))
    if resident.get("child"):
        klass = "child"
    for tag in tags:
        lines = reactions.get(tag) or {}
        pool = lines.get(klass) or lines.get(str(resident.get("species", ""))) or lines.get("default")
        if not pool:
            continue
        digest = hashlib.sha256(f"{seed}|{resident.get('id')}|{tag}".encode("utf-8")).digest()
        line = pool[int.from_bytes(digest[:4], "big") % len(pool)]
        label = labels([tag])[0]
        text = line.format(name=resident.get("name", "Someone"), lead=lead_name, label=label)
        return {"by": resident.get("name"), "resident_id": resident.get("id"), "tag": tag, "label": label, "text": text}
    return None


def public_notice(actor: dict | None) -> list[str]:
    """Compact labels for the public view (bounded; rides in every turn)."""
    return copy.deepcopy(labels(notice(actor)))[:4]
