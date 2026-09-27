"""Procedural generation engine for NPCs, monsters, power systems, items, and lore descriptions.

Provides declarative generation of:
1. Cultural procedural names (Imperial, Frontier Goblin, Arcane Elven, Stoneforged Dwarven, Monster titles).
2. Personality matrices (traits, behavioral tells, core motives, and stance biases).
3. Monster power systems (threat tiers, elemental prefixes, tactical suffixes, known spells, and resource pools).
4. Procedural items with modular materialist lore assembly.
5. Resident dictionaries for Floor One life-sim and Actors for live tactical encounters.
"""

from __future__ import annotations

import copy
import functools
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hollowstar.actors import Actor, Band, Provenance
from hollowstar.effects import Affix, Effect
from hollowstar.items import Item
from hollowstar.loader import load_affixes, load_items, forge
from hollowstar.phases import Direction, Phase, Scope, Tier
from hollowstar.tags import DamageTag, GATES

CONTENT_DIR = Path(__file__).parent / "content"
PROCEDURAL_DATA_PATH = CONTENT_DIR / "procedural_generation.json"


@functools.lru_cache(maxsize=4)
def _procedural_data() -> dict[str, Any]:
    try:
        return json.loads(PROCEDURAL_DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to load procedural generation data from {PROCEDURAL_DATA_PATH}") from exc


def get_rng(seed: object = None) -> random.Random:
    if isinstance(seed, random.Random):
        return seed
    return random.Random(seed)


# ---------------------------------------------------------------------------
# Name Generation
# ---------------------------------------------------------------------------

def generate_name(culture: str = "imperial", gender: str = "neutral", *, rng: random.Random | None = None) -> str:
    """Generate an evocative name based on culture and gender."""
    rng = rng or random.Random()
    data = _procedural_data()["naming_pools"]
    culture = culture.lower()

    if culture in {"frontier_goblin", "goblin"}:
        pool = data["frontier_goblin"]
        first = rng.choice(pool["first_names"])
        if rng.random() < 0.6:
            clan = rng.choice(pool["clan_monikers"])
            return f"{first} {clan}"
        epithet = rng.choice(pool["epithets"])
        return f"{first} {epithet}"

    elif culture in {"arcane_elven", "elven", "elf"}:
        pool = data["arcane_elven"]
        first = rng.choice(pool["first_names"])
        if rng.random() < 0.65:
            house = rng.choice(pool["house_names"])
            return f"{first} {house}"
        epithet = rng.choice(pool["epithets"])
        return f"{first} {epithet}"

    elif culture in {"stoneforged_dwarven", "dwarven", "dwarf"}:
        pool = data["stoneforged_dwarven"]
        first = rng.choice(pool["first_names"])
        clan = rng.choice(pool["clan_names"])
        if rng.random() < 0.25:
            epithet = rng.choice(pool["epithets"])
            return f"{first} {clan} {epithet}"
        return f"{first} {clan}"

    elif culture in {"monster", "beast"}:
        pool = data["monster_titles"]
        prefix = rng.choice(pool["prefixes"])
        descriptor = rng.choice(pool["descriptors"])
        return f"{prefix} {descriptor}"

    else:  # imperial / common default
        pool = data["imperial"]
        if gender == "male":
            first = rng.choice(pool["first_male"])
        elif gender == "female":
            first = rng.choice(pool["first_female"])
        else:
            first = rng.choice(pool.get("first_neutral") or pool["first_male"])
        surname = rng.choice(pool["surnames"])
        if rng.random() < 0.2:
            epithet = rng.choice(pool["epithets"])
            return f"{first} {surname} {epithet}"
        return f"{first} {surname}"


# ---------------------------------------------------------------------------
# Personality & Motive Generation
# ---------------------------------------------------------------------------

@dataclass
class PersonalityProfile:
    traits: list[str]
    tells: list[str]
    core_motive: str
    motive_goal: str
    speech_tags: list[str]
    stance_modifiers: dict[str, int]
    surrender_hp_threshold: float
    flee_hp_threshold: float
    bribe_acceptance: float


def generate_personality(role: str = "townsfolk", *, trait_count: int = 2,
                         rng: random.Random | None = None) -> PersonalityProfile:
    """Generate a cohesive personality profile with sensory tells and motives."""
    rng = rng or random.Random()
    pdata = _procedural_data()["personality_matrix"]
    all_traits = list(pdata["traits"].keys())

    # Role-based trait bias
    role_biases: dict[str, list[str]] = {
        "trader": ["greedy", "mercenary", "cynical", "watchful"],
        "guard": ["watchful", "loyal", "stoic", "proud"],
        "labourer": ["stoic", "loyal", "cynical"],
        "clergy": ["devout", "fanatical", "loyal", "curious"],
        "bandit": ["greedy", "cowardly", "reckless", "cynical"],
        "goblin": ["cowardly", "greedy", "curious", "reckless"],
        "scholar": ["curious", "watchful", "stoic"],
    }
    bias = role_biases.get(role.lower(), [])
    chosen_traits: list[str] = []
    candidates = bias + [t for t in all_traits if t not in bias]
    for trait in candidates:
        if trait not in chosen_traits and (trait in bias or rng.random() < 0.4):
            chosen_traits.append(trait)
            if len(chosen_traits) >= trait_count:
                break

    while len(chosen_traits) < trait_count:
        t = rng.choice(all_traits)
        if t not in chosen_traits:
            chosen_traits.append(t)

    tells: list[str] = []
    speech_tags: list[str] = []
    stance_mods: dict[str, int] = {}
    for t_name in chosen_traits:
        t_info = pdata["traits"][t_name]
        tells.append(rng.choice(t_info["tells"]))
        speech_tags.extend(t_info.get("speech_tags", []))
        for mode, val in t_info.get("stance_mod", {}).items():
            stance_mods[mode] = stance_mods.get(mode, 0) + val

    all_motives = list(pdata["core_motives"].keys())
    motive_name = rng.choice(all_motives)
    m_info = pdata["core_motives"][motive_name]

    return PersonalityProfile(
        traits=chosen_traits,
        tells=list(dict.fromkeys(tells)),
        core_motive=motive_name,
        motive_goal=m_info["goal"],
        speech_tags=list(dict.fromkeys(speech_tags)),
        stance_modifiers=stance_mods,
        surrender_hp_threshold=float(m_info.get("surrender_hp_threshold", 0.2)),
        flee_hp_threshold=float(m_info.get("flee_hp_threshold", 0.1)),
        bribe_acceptance=float(m_info.get("bribe_acceptance", 0.5)),
    )


# ---------------------------------------------------------------------------
# Procedural Items & Modular Materialist Lore Assembly
# ---------------------------------------------------------------------------

def generate_procedural_item(
    base_item_name: str | None = None,
    prefix_name: str | None = None,
    suffix_name: str | None = None,
    *,
    category: str | None = None,
    tier: Tier | None = None,
    rng: random.Random | None = None,
) -> Item:
    """Generate or forge an item with composite materialist lore assembly."""
    rng = rng or random.Random()
    all_items = load_items()

    if base_item_name and base_item_name in all_items:
        base = copy.deepcopy(all_items[base_item_name])
    else:
        candidates = list(all_items.values())
        if category:
            filtered = [it for it in candidates if (it.category or "").lower() == category.lower()]
            if filtered:
                candidates = filtered
        base = copy.deepcopy(rng.choice(candidates))

    affix_catalog = load_affixes()
    prefix_affix: Affix | None = None
    suffix_affix: Affix | None = None
    prefix_lore = ""
    suffix_lore = ""

    # Monster affix kit definitions can also contribute prefix/suffix fragments
    monster_kits = _procedural_data().get("monster_affix_kits", {})
    kit_prefixes = monster_kits.get("prefixes", {})
    kit_suffixes = monster_kits.get("suffixes", {})

    if prefix_name:
        if prefix_name in affix_catalog:
            prefix_affix = copy.deepcopy(affix_catalog[prefix_name])
        elif prefix_name in kit_prefixes:
            k = kit_prefixes[prefix_name]
            tag = k.get("element", "PHYSICAL")
            prefix_affix = Affix(
                name=prefix_name,
                affix_type="prefix",
                description=k.get("tell", ""),
                effects=[Effect(
                    name=prefix_name,
                    phase=Phase.MAGNITUDE,
                    direction=Direction.GRANT,
                    grants_tags={DamageTag[tag]} if tag in DamageTag.__members__ else set(),
                    flat_bonus=k.get("stat_mods", {}).get("attack_bonus", 0),
                    tell=k.get("tell", ""),
                )]
            )
            prefix_lore = k.get("lore_fragment", "")

    if suffix_name:
        if suffix_name in affix_catalog:
            suffix_affix = copy.deepcopy(affix_catalog[suffix_name])
        elif suffix_name in kit_suffixes:
            s = kit_suffixes[suffix_name]
            tag = s.get("damage_type", "PHYSICAL")
            suffix_affix = Affix(
                name=suffix_name,
                affix_type="suffix",
                description=s.get("tell", ""),
                effects=[Effect(
                    name=suffix_name,
                    phase=Phase.MAGNITUDE,
                    direction=Direction.GRANT,
                    grants_tags={DamageTag[tag]} if tag in DamageTag.__members__ else set(),
                    flat_bonus=s.get("bonus_damage", 0),
                    tell=s.get("tell", ""),
                )]
            )
            suffix_lore = s.get("lore_fragment", "")

    forged = forge(base, prefix_affix, suffix_affix)
    if tier:
        forged.tier = tier

    # Modular materialist lore assembly:
    # Combine base craftsmanship lore + prefix physical origin + suffix environmental consequence
    lore_parts = []
    if base.lore:
        lore_parts.append(base.lore)
    if prefix_lore:
        lore_parts.append(prefix_lore)
    if suffix_lore:
        lore_parts.append(suffix_lore)

    if lore_parts:
        forged.lore = " ".join(lore_parts).strip()

    return forged


# ---------------------------------------------------------------------------
# Monster Power Affix System & Tiered Enemy Generation
# ---------------------------------------------------------------------------

@dataclass
class EnemyPowerKit:
    tier: str
    prefixes: list[str]
    suffixes: list[str]
    resistances: list[str]
    vulnerabilities: list[str]
    condition_immunities: list[str]
    known_spells: list[str]
    resource_pool: dict[str, int]
    tells: list[str]
    lore: str
    hp_multiplier: float
    ac_bonus: int
    attack_bonus: int
    attacks_per_action_bonus: int
    speed_bonus: int


def generate_enemy_power_kit(tier: str = "common", *, rng: random.Random | None = None) -> EnemyPowerKit:
    """Generate a power package scaling from common mob up to multi-affixed boss."""
    rng = rng or random.Random()
    kits = _procedural_data()["monster_affix_kits"]
    tiers = kits["threat_tiers"]
    tier_info = tiers.get(tier.lower(), tiers["common"])

    prefix_pool = kits["prefixes"]
    suffix_pool = kits["suffixes"]

    chosen_prefixes = rng.sample(list(prefix_pool.keys()), min(len(prefix_pool), tier_info["prefix_count"]))
    chosen_suffixes = rng.sample(list(suffix_pool.keys()), min(len(suffix_pool), tier_info["suffix_count"]))

    resistances: list[str] = []
    vulnerabilities: list[str] = []
    condition_immunities: list[str] = []
    known_spells: list[str] = []
    resource_pool: dict[str, int] = {}
    tells: list[str] = []
    lore_frags: list[str] = []

    hp_mult = float(tier_info.get("hp_multiplier", 1.0))
    ac_bonus = int(tier_info.get("ac_bonus", 0))
    atk_bonus = 0
    attacks_bonus = 0
    speed_bonus = 0

    for p_name in chosen_prefixes:
        p_data = prefix_pool[p_name]
        resistances.extend(p_data.get("resistances", []))
        vulnerabilities.extend(p_data.get("vulnerabilities", []))
        known_spells.extend(p_data.get("known_spells", []))
        for r_name, amt in p_data.get("resource_pool", {}).items():
            resource_pool[r_name] = resource_pool.get(r_name, 0) + amt
        if p_data.get("tell"):
            tells.append(p_data["tell"])
        if p_data.get("lore_fragment"):
            lore_frags.append(p_data["lore_fragment"])
        smods = p_data.get("stat_mods", {})
        hp_mult *= smods.get("hp_multiplier", 1.0)
        ac_bonus += smods.get("ac_bonus", 0)
        atk_bonus += smods.get("attack_bonus", 0)
        attacks_bonus += smods.get("attacks_per_action_bonus", 0)
        speed_bonus += smods.get("speed_bonus", 0)

    for s_name in chosen_suffixes:
        s_data = suffix_pool[s_name]
        condition_immunities.extend(s_data.get("condition_immunities", []))
        known_spells.extend(s_data.get("known_spells", []))
        for r_name, amt in s_data.get("resource_pool", {}).items():
            resource_pool[r_name] = resource_pool.get(r_name, 0) + amt
        if s_data.get("tell"):
            tells.append(s_data["tell"])
        if s_data.get("lore_fragment"):
            lore_frags.append(s_data["lore_fragment"])
        smods = s_data.get("stat_mods", {})
        hp_mult *= smods.get("hp_multiplier", 1.0)
        ac_bonus += smods.get("ac_bonus", 0)
        speed_bonus += smods.get("speed_bonus", 0)

    if tier_info.get("legendary_resilience"):
        condition_immunities.extend(["PARALYZED", "STUNNED"])
        resource_pool["legendary_resistance"] = 3

    return EnemyPowerKit(
        tier=tier.lower(),
        prefixes=chosen_prefixes,
        suffixes=chosen_suffixes,
        resistances=list(dict.fromkeys(resistances)),
        vulnerabilities=list(dict.fromkeys(vulnerabilities)),
        condition_immunities=list(dict.fromkeys(condition_immunities)),
        known_spells=list(dict.fromkeys(known_spells)),
        resource_pool=resource_pool,
        tells=tells,
        lore=" ".join(lore_frags).strip(),
        hp_multiplier=round(hp_mult, 2),
        ac_bonus=ac_bonus,
        attack_bonus=atk_bonus,
        attacks_per_action_bonus=attacks_bonus,
        speed_bonus=speed_bonus,
    )


def generate_enemy(
    base_spec: dict | None = None,
    species_name: str = "Town watch",
    tier: str = "common",
    *,
    index: int = 0,
    rng: random.Random | None = None,
) -> tuple[Actor, dict]:
    """Generate a fully realized procedural enemy Actor and its tactical rules dictionary."""
    rng = rng or random.Random()
    spec = copy.deepcopy(base_spec or {})
    power_kit = generate_enemy_power_kit(tier, rng=rng)

    base_hp = int(spec.get("hp", 20))
    final_hp = max(1, round(base_hp * power_kit.hp_multiplier))
    base_ac = int(spec.get("ac", 12)) + power_kit.ac_bonus
    speed = max(10, int(spec.get("speed", 30)) + power_kit.speed_bonus)
    attacks = int(spec.get("attacks", 1)) + power_kit.attacks_per_action_bonus

    # Construct the procedural name
    name_parts = []
    if power_kit.prefixes:
        name_parts.append(power_kit.prefixes[0])
    name_parts.append(spec.get("name", species_name))
    if power_kit.suffixes:
        name_parts.append(power_kit.suffixes[0])
    full_name = f"{' '.join(name_parts)} {index + 1}".strip()

    # Weapon & Equipment
    weapon_spec = spec.get("weapon") or {}
    weapon_name = weapon_spec.get("name") or "service blade"
    prefix_for_weapon = power_kit.prefixes[0] if power_kit.prefixes else None
    suffix_for_weapon = power_kit.suffixes[0] if power_kit.suffixes else None
    equipped_weapon = generate_procedural_item(
        base_item_name=weapon_name if weapon_name in load_items() else "longsword",
        prefix_name=prefix_for_weapon,
        suffix_name=suffix_for_weapon,
        rng=rng,
    )
    equipped_weapon.attack_bonus += power_kit.attack_bonus

    ability_scores = dict(spec.get("abilities", {
        "STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 11, "CHA": 10
    }))
    if power_kit.tier in {"champion", "boss"}:
        ability_scores["STR"] += 2
        ability_scores["CON"] += 2

    resources = dict(spec.get("pool") or {})
    if "name" in resources and "amount" in resources:
        resources = {resources["name"]: resources["amount"]}
    resources.update(power_kit.resource_pool)

    # Actor construction
    enemy_actor = Actor(
        name=full_name,
        max_hp=final_hp,
        hp=final_hp,
        armor_class=base_ac,
        band=Band(spec.get("band", 10)),
        speed=speed,
        initiative_bonus=2 + (2 if power_kit.tier in {"champion", "boss"} else 0),
        controller="npc",
        attacks_per_action=attacks,
        ability_scores=ability_scores,
        resources=resources,
        equipment=[equipped_weapon],
        provenance=Provenance(
            owner_file="hollowstar/npc_generator.py",
            snapshot_version="hsr-procedural-1",
            verified=False,
            fidelity="procedural",
            note=f"Tier: {power_kit.tier.upper()}. Prefixes: {power_kit.prefixes}, Suffixes: {power_kit.suffixes}"
        )
    )

    # Tactical rules dictionary
    damage_type = equipped_weapon.all_tags()
    tag_names = {t.name for t in damage_type}
    chosen_type = "SLASHING"
    for tag in ("PIERCING", "SLASHING", "BLUDGEONING", "FIRE", "ICE", "ARCANE", "NECROTIC"):
        if tag in tag_names:
            chosen_type = tag
            break

    rules: dict[str, Any] = {
        "damage_type": chosen_type,
        "range": [equipped_weapon.range_normal, equipped_weapon.range_long],
        "size": spec.get("size", "medium"),
        "resistances": list(dict.fromkeys(list(spec.get("resistances", [])) + power_kit.resistances)),
        "condition_immunities": list(dict.fromkeys(list(spec.get("condition_immunities", [])) + power_kit.condition_immunities)),
        "saves": dict(spec.get("saves", {})),
        "attacks": attacks,
        "base_ac": base_ac,
        "known_spells": list(dict.fromkeys(power_kit.known_spells)),
        "trait": f"{', '.join(power_kit.prefixes + power_kit.suffixes)}: {power_kit.lore}".strip(": "),
        "tells": power_kit.tells,
        "threat_tier": power_kit.tier,
    }

    return enemy_actor, rules


# ---------------------------------------------------------------------------
# Procedural Resident Generation (Life-Sim / Town)
# ---------------------------------------------------------------------------

def generate_resident(
    role: str = "townsfolk",
    culture: str = "imperial",
    location: str = "market",
    *,
    gender: str = "neutral",
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Generate a rich, persistent town resident matching floor_one_life.json schema."""
    rng = rng or random.Random()
    name = generate_name(culture=culture, gender=gender, rng=rng)
    resident_id = name.lower().replace(" ", "-").replace("'", "")
    personality = generate_personality(role=role, rng=rng)

    # Gear and possessions
    carried_item = generate_procedural_item(category="tool" if role == "labourer" else "weapon", rng=rng)
    possessions = [carried_item.name, f"pouch of {rng.randint(3, 24)} copper bits"]

    # Starting disposition base (-2 to +2)
    disp_base = rng.choice([-1, 0, 1, 2])
    if "greedy" in personality.traits:
        disp_base -= 1
    if "devout" in personality.traits or "loyal" in personality.traits:
        disp_base += 1

    return {
        "id": resident_id,
        "name": name,
        "role": role.title(),
        "faction": "town" if role in {"townsfolk", "guard", "labourer"} else role,
        "location": location,
        "schedule": [location, location, "tavern", "homes"],
        "hp": rng.randint(8, 16),
        "tell": personality.tells[0] if personality.tells else "Watches quietly.",
        "tier": "procedural",
        "species": "human" if culture == "imperial" else "goblin" if "goblin" in culture else "dwarf" if "dwarf" in culture else "elf",
        "class": role.lower(),
        "disposition_base": disp_base,
        "disposition": "neutral" if disp_base == 0 else "warm" if disp_base > 0 else "wary",
        "stances": {
            "bandit": -4,
            "guard": 1 if role != "bandit" else -3,
            "goblin": -2 if "goblin" not in culture else 3,
            "townsfolk": 2,
            "stranger": disp_base,
        },
        "traits": personality.traits,
        "relationships": [],
        "offers": {
            "quest": rng.random() < 0.35,
            "shop": role in {"trader", "merchant"} or rng.random() < 0.25,
            "identify": role in {"scholar", "clergy"} or rng.random() < 0.15,
        },
        "presence": {
            "morning": 1.0,
            "day": 1.0,
            "evening": 0.8,
            "night": 0.3,
        },
        "tells": personality.tells,
        "possessions": possessions,
        "core_motive": personality.core_motive,
        "motive_goal": personality.motive_goal,
        "surrender_hp_threshold": personality.surrender_hp_threshold,
        "flee_hp_threshold": personality.flee_hp_threshold,
        "bribe_acceptance": personality.bribe_acceptance,
        "child": False,
    }
