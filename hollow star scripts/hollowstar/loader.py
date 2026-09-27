"""Content loading and the roster registry.

Character swapping is the point: any actor in the roster can be dropped into
any encounter. Band drives difficulty expression, not a separate dungeon.
"""

from __future__ import annotations

import copy
import functools
import json
from pathlib import Path

from hollowstar.actors import Actor, Band, Provenance
from hollowstar.effects import Affix, Effect
from hollowstar.items import Item
from hollowstar.phases import Direction, Phase, Scope, Tier
from hollowstar.tags import DamageTag, GATES

CONTENT = Path(__file__).parent / "content"
STAGED_ENDLESS_AFFIXES = CONTENT / "affixes_endless_engagement.json"


def _effect(d: dict) -> Effect:
    return Effect(
        name=d["name"],
        phase=Phase[d["phase"]],
        direction=Direction[d["direction"]],
        tier=Tier[d.get("tier", "MUNDANE")],
        scope=Scope[d.get("scope", "TARGET")],
        condition=d.get("condition", "always"),
        flat_bonus=d.get("flat_bonus", 0),
        multiplier=d.get("multiplier", 1.0),
        per_stack_bonus=d.get("per_stack_bonus", 0),
        per_stack_source=d.get("per_stack_source", ""),
        applies_to_tags={DamageTag[t] for t in d.get("applies_to_tags", [])},
        grants_tags={DamageTag[t] for t in d.get("grants_tags", [])},
        opens_gate=d.get("opens_gate", ""),
        closes_gate=d.get("closes_gate", ""),
        inflicts_status=d.get("inflicts_status", ""),
        status_duration=d.get("status_duration", 0),
        status_potency=d.get("status_potency", 1),
        save_ability=str(d.get("save_ability", "")).upper(),
        save_dc=int(d.get("save_dc", 0) or 0),
        blocks_statuses=set(d.get("blocks_statuses", [])),
        charges=d.get("charges"),
        tell=d.get("tell", ""),
        description=d.get("description", ""),
        operation=d.get("operation", "add"),
        stat=d.get("stat", ""),
        stack_group=d.get("stack_group", ""),
        source_id=d.get("source_id", ""),
        duration=d.get("duration", "permanent"),
        priority=d.get("priority", 0),
        public_summary=d.get("public_summary", ""),
        specificity=d.get("specificity", 0),
    )


@functools.lru_cache(maxsize=16)
def _load_affix_data(path: Path) -> dict[str, Affix]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for a in data["affixes"]:
        out[a["name"]] = Affix(
            name=a["name"],
            affix_type=a["affix_type"],
            description=a.get("description", ""),
            effects=[_effect(e) for e in a.get("effects", [])],
        )
    return out


def shared_affixes(path: Path | None = None) -> dict[str, Affix]:
    """Cached active affixes, NOT copied. Read-only: callers must never mutate."""
    return _load_affix_data((path or CONTENT / "affixes.json").resolve())


def load_affixes(path: Path | None = None) -> dict[str, Affix]:
    """Load active HSR affixes; staged predecessor content is opt-in."""
    resolved = (path or CONTENT / "affixes.json").resolve()
    return copy.deepcopy(_load_affix_data(resolved))


def load_staged_affixes(path: Path | None = None) -> dict[str, Affix]:
    """Load the Endless Engagement pool without activating it in gameplay."""
    resolved = (path or STAGED_ENDLESS_AFFIXES).resolve()
    return copy.deepcopy(_load_affix_data(resolved))


def affix_catalog(*, include_staged: bool = True) -> dict:
    """Return UI-safe active and staged affix definitions.

    Staged rows are presentation and design data only. Callers must explicitly
    attach an affix to an item before it can affect an existing resolver.
    """
    active = shared_affixes()
    staged = _load_affix_data(STAGED_ENDLESS_AFFIXES.resolve()) if include_staged else {}

    def public(affix: Affix, *, staged_row: bool) -> dict:
        effects = []
        for effect in affix.effects:
            effects.append({
                "name": effect.name,
                "phase": effect.phase.name,
                "direction": effect.direction.name,
                "tier": effect.tier.name,
                "scope": effect.scope.name,
                "condition": effect.condition,
                "flat_bonus": effect.flat_bonus,
                "multiplier": effect.multiplier,
                "per_stack_bonus": effect.per_stack_bonus,
                "per_stack_source": effect.per_stack_source,
                "tags": sorted(tag.name for tag in effect.grants_tags),
                "status": effect.inflicts_status or None,
                "status_duration": effect.status_duration,
                "status_potency": effect.status_potency,
            })
        return {
            "name": affix.name,
            "affix_type": affix.affix_type,
            "tooltip": affix.description,
            "tags": sorted(tag.name for effect in affix.effects for tag in effect.grants_tags),
            "options": {
                "detachable": affix.detachable,
                "staged": staged_row,
                "attachable": not staged_row,
            },
            "phase_effects": effects,
        }

    return {
        "schema": "hollow-star-affix-catalog-1",
        "activation": "staged-predecessor-import",
        "active": [public(affix, staged_row=False) for affix in active.values()],
        "staged": [public(affix, staged_row=True) for affix in staged.values()],
        "counts": {"active": len(active), "staged": len(staged)},
    }


@functools.lru_cache(maxsize=16)
def _load_item_data(path: Path) -> dict[str, Item]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for i in data["items"]:
        out[i["name"]] = Item(
            name=i["name"],
            slot=i.get("slot", "hand"),
            base_damage=i.get("base_damage", 0),
            attack_bonus=i.get("attack_bonus", 0),
            damage_dice=i.get("damage_dice", ""),
            damage_modifier=i.get("damage_modifier", 0),
            reach=i.get("reach", 5), range_normal=i.get("range_normal", 5),
            range_long=i.get("range_long", 5), critical_dice=i.get("critical_dice", ""),
            alternate_modes=dict(i.get("alternate_modes", {})),
            base_ac=i.get("base_ac", 0),
            tier=Tier[i.get("tier", "MUNDANE")],
            tags={DamageTag[t] for t in i.get("tags", [])},
            inherent=[_effect(e) for e in i.get("inherent", [])],
            density=i.get("density", 1.0),
            utility_uses=i.get("utility_uses", []),
            temporary=i.get("temporary", False),
            ac_bonus=i.get("ac_bonus", 0),
            shield_bonus=i.get("shield_bonus", 0),
            dex_cap=i.get("dex_cap"),
            attack_ability=i.get("attack_ability", ""),
            flavor=i.get("flavor", ""),
            lore=i.get("lore", ""),
            sprite_id=i.get("sprite_id", ""),
            silhouette=i.get("silhouette", ""),
            material=i.get("material", ""),
            item_type=i.get("item_type", ""),
            handedness=i.get("handedness", ""),
            coverage=i.get("coverage", ""),
            animation_profile=i.get("animation_profile", ""),
            weight=float(i.get("weight", 1.0)),
            category=i.get("category", ""),
        )
    return out


def load_items(path: Path | None = None) -> dict[str, Item]:
    resolved = (path or CONTENT / "items.json").resolve()
    return copy.deepcopy(_load_item_data(resolved))


@functools.lru_cache(maxsize=16)
def _load_roster_data(path: Path) -> dict[str, Actor]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for a in data["actors"]:
        p = a.get("provenance", {})
        actor = Actor(
            name=a["name"],
            band=Band[a.get("band", "MORTAL")],
            controller=a.get("controller", "npc"),
            max_hp=a.get("max_hp", 10),
            hp=a.get("max_hp", 10),
            armor_class=a.get("armor_class", 10),
            initiative_bonus=a.get("initiative_bonus", 0),
            speed=a.get("speed", 30),
            attacks_per_action=a.get("attacks_per_action", 1),
            reactions=a.get("reactions", 1),
            ability_scores={
                ability: int(a.get("ability_scores", {}).get(ability, 10))
                for ability in ("STR", "DEX", "CON", "INT", "WIS", "CHA")
            },
            proficiency_bonus=a.get("proficiency_bonus", 0),
            skill_bonuses=dict(a.get("skill_bonuses", {})),
            resources=dict(a.get("resources", {})),
            natural_tags={DamageTag[t] for t in a.get("natural_tags", [])},
            gate=GATES.get(a.get("gate", "none"), GATES["none"]),
            features=list(a.get("features", [])),
            equipment=[Item(
                name=item["name"], slot=item.get("slot", "hand"),
                base_damage=item.get("base_damage", 0),
                attack_bonus=item.get("attack_bonus", 0),
                damage_dice=item.get("damage_dice", ""),
                damage_modifier=item.get("damage_modifier", 0),
                reach=item.get("reach", 5),
                range_normal=item.get("range_normal", 5),
                range_long=item.get("range_long", 5),
                base_ac=item.get("base_ac", 0),
                dex_cap=item.get("dex_cap"),
                ac_bonus=item.get("ac_bonus", 0),
                attack_ability=item.get("attack_ability", ""),
                tags={DamageTag[t] for t in item.get("tags", [])},
                flavor=item.get("flavor", ""),
                lore=item.get("lore", ""),
                silhouette=item.get("silhouette", ""),
                material=item.get("material", ""),
                item_type=item.get("item_type", ""),
                handedness=item.get("handedness", ""),
                coverage=item.get("coverage", ""),
                animation_profile=item.get("animation_profile", ""),
            ) for item in a.get("equipment", [])],
            provenance=Provenance(
                owner_file=p.get("owner_file", ""),
                support_files=p.get("support_files", []),
                snapshot_version=p.get("snapshot_version", "unversioned"),
                verified=p.get("verified", False),
                fidelity=p.get("fidelity", "unknown"),
                deferred=p.get("deferred", []),
                note=p.get("note", ""),
            ),
        )
        out[actor.name] = actor
    return out


def load_roster(path: Path | None = None) -> dict[str, Actor]:
    resolved = (path or CONTENT / "actors.json").resolve()
    return copy.deepcopy(_load_roster_data(resolved))


def forge(item: Item, prefix: Affix | None = None, suffix: Affix | None = None) -> Item:
    """Attach a prefix and/or suffix to a base item. Inherent stays untouched."""
    import copy

    made = copy.deepcopy(item)
    if prefix:
        made.prefix = copy.deepcopy(prefix)
    if suffix:
        made.suffix = copy.deepcopy(suffix)
    return made


def unverified(roster: dict[str, Actor]) -> list[str]:
    """Audit helper. Anything listed here is a stub, not a balance source."""
    return [n for n, a in roster.items() if not a.provenance.verified]
