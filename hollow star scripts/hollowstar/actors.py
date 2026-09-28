"""
Actors.

One shape for everybody: Stewards, champions, Primeverse crews, rivals,
townspeople, machines, dragons. The engine does not distinguish "player
character" from "monster" -- it distinguishes actors by BAND, which is a
difficulty term, and by CONTROLLER, which is who decides.

Provenance is mandatory and load-bearing. Every actor points at the corpus
file that owns its real mechanics, plus a version string. If `verified` is
False, the numbers in this row are PLACEHOLDERS and must not be used for
balance conclusions. That flag is the thing standing between a stub and a
certified snapshot.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import IntEnum

from hollowstar.effects import Effect
from hollowstar.items import Item
from hollowstar.tags import DamageTag, Gate, GATES


DND_ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


class Band(IntEnum):
    """
    Power band. Feeds the depth-pressure formula so the SAME floor expresses
    itself differently depending on who walked in. The town is a coordination
    puzzle for Stewards, a survival problem for a mortal crew, and scenery for
    a champion -- same generation rules, different resolution.
    """

    MORTAL = 10        # Primeverse ordinary, low-level D&D
    PEAK_MORTAL = 20   # Cassian, Veyren tier
    HEROIC = 30        # mid-level adventurers
    STEWARD = 40       # level-20 Doran / Wren
    CHAMPION = 50      # Chosen-tier antagonists
    # Nothing above CHAMPION. The divine are authors, not combatants.


@dataclass
class Provenance:
    """
    Where this actor's real mechanics live.

    Two INDEPENDENT axes, deliberately not collapsed into one flag:

      verified  -- are these numbers sourced from a certified authority?
                   False means placeholders. Do not tune balance on them.
      fidelity  -- how much of that certified sheet can the engine actually
                   express today? "complete" or "partial". A partial actor
                   has real numbers and missing behaviour, and `deferred`
                   names exactly what is missing.

    Collapsing these would hide the interesting failure: an actor whose hit
    points are certified and whose signature ability silently does nothing.
    """

    owner_file: str = ""       # e.g. "DM041_B"
    support_files: list[str] = field(default_factory=list)
    snapshot_version: str = "unversioned"
    verified: bool = False     # False => placeholder numbers, do not tune on it
    fidelity: str = "unknown"  # "complete" | "partial" | "unknown"
    deferred: list[str] = field(default_factory=list)
    note: str = ""


@dataclass
class Actor:
    name: str
    band: Band = Band.MORTAL
    controller: str = "npc"    # "player" | "npc"
    sprite_id: str = ""        # e.g. "sera-happy", "town-watch-1"

    max_hp: int = 10
    hp: int = 10
    armor_class: int = 10
    initiative_bonus: int = 0
    speed: int = 30

    # Action economy per turn.
    attacks_per_action: int = 1
    reactions: int = 1

    # D&D-style character sheet values. These are additive to the existing
    # runtime fields so certified snapshot actors remain load-compatible.
    ability_scores: dict[str, int] = field(
        default_factory=lambda: {ability: 10 for ability in DND_ABILITIES}
    )
    proficiency_bonus: int = 0
    skill_bonuses: dict[str, int] = field(default_factory=dict)

    natural_tags: set[DamageTag] = field(default_factory=set)
    gate: Gate = field(default_factory=lambda: GATES["none"])

    inherent: list[Effect] = field(default_factory=list)
    equipment: list[Item] = field(default_factory=list)

    resources: dict[str, int] = field(default_factory=dict)
    statuses: dict[str, int] = field(default_factory=dict)
    features: list[str] = field(default_factory=list)

    provenance: Provenance = field(default_factory=Provenance)

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def ability_score(self, ability: str) -> int:
        key = ability.upper()
        if key not in DND_ABILITIES:
            raise ValueError(f"unknown D&D ability: {ability}")
        return self.ability_scores.get(key, 10)

    def ability_modifier(self, ability: str) -> int:
        return (self.ability_score(ability) - 10) // 2

    def set_ability_score(self, ability: str, score: int) -> None:
        key = ability.upper()
        if key not in DND_ABILITIES:
            raise ValueError(f"unknown D&D ability: {ability}")
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 30:
            raise ValueError("ability scores must be integers from 1 through 30")
        self.ability_scores[key] = score

    def adjust_hp(self, amount: int) -> int:
        """Apply a bounded HP change and return the resulting HP."""
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValueError("HP change must be an integer")
        self.hp = max(0, min(self.max_hp, self.hp + amount))
        return self.hp

    def set_armor_class(self, armor_class: int) -> None:
        if not isinstance(armor_class, int) or isinstance(armor_class, bool) or armor_class < 0:
            raise ValueError("AC must be a non-negative integer")
        self.armor_class = armor_class

    def offensive_tags(self) -> set[DamageTag]:
        tags = set(self.natural_tags)
        for item in self.equipment:
            if item.slot == "hand":
                tags |= item.all_tags()
        return tags

    def active_effects(self) -> list[Effect]:
        out = list(self.inherent)
        for item in self.equipment:
            out.extend(item.all_effects())
        return [e for e in out if not e.is_exhausted()]

    def weapon(self) -> Item | None:
        for item in self.equipment:
            if item.slot == "hand":
                return item
        return None

    def _armor_entry(self) -> tuple | None:
        """Internal helper: resolve the best-worn armor piece and derived DEX/accessory values.

        Returns ``(worn, applied_dex, accessory_bonus)`` or ``None`` if no
        armor with a base AC is equipped.  Both public AC methods delegate to
        this so the formula lives in exactly one place.
        """
        armor = [item for item in self.equipment if item.slot == "armor" and item.base_ac]
        if not armor:
            return None
        worn = max(armor, key=lambda item: item.base_ac)
        raw_dex = self.ability_modifier("DEX")
        if worn.dex_cap == 0:
            applied_dex = 0
        elif worn.dex_cap is not None:
            applied_dex = min(raw_dex, worn.dex_cap)
        elif worn.base_ac >= 16:
            applied_dex = 0
        else:
            applied_dex = raw_dex
        accessories = [item for item in self.equipment if item is not worn]
        shield_bonus = sum(item.shield_bonus for item in accessories)
        accessory_bonus = sum(item.ac_bonus for item in accessories)
        return worn, raw_dex, applied_dex, shield_bonus, accessory_bonus

    def equipment_armor_class(self) -> int | None:
        """Calculate AC from equipped armor, shields, and AC-bearing accessories.

        This is the generic equipment path.  A source-authoritative actor may
        still carry a locked AC in ``armor_class`` and have runtime rules
        explicitly preserve it (as Doran and Wren do).
        """
        entry = self._armor_entry()
        if entry is None:
            return None
        worn, _raw_dex, applied_dex, shield_bonus, accessory_bonus = entry
        return worn.base_ac + applied_dex + worn.ac_bonus + worn.shield_bonus + shield_bonus + accessory_bonus

    def armor_profile(self) -> dict | None:
        """Return the generic AC formula as inspectable components."""
        entry = self._armor_entry()
        if entry is None:
            return None
        worn, raw_dex, applied_dex, shield_bonus, accessory_bonus = entry
        total = worn.base_ac + applied_dex + worn.ac_bonus + worn.shield_bonus + shield_bonus + accessory_bonus
        return {
            "armor": worn.display_name, "base_ac": worn.base_ac,
            "dex_modifier_raw": raw_dex, "dex_modifier_applied": applied_dex,
            "dex_cap": worn.dex_cap, "armor_bonus": worn.ac_bonus,
            "shield_bonus": worn.shield_bonus + shield_bonus,
            "accessory_bonus": accessory_bonus, "total": total,
        }


    def equipment_attack_bonus(self, ability: str = "STR") -> int | None:
        """Calculate a generic weapon attack bonus from proficiency and ability."""
        weapon = self.weapon()
        if weapon is None or not weapon.damage_dice:
            return None
        stat = weapon.attack_ability or ability
        return weapon.attack_bonus + self.ability_modifier(stat) + self.proficiency_bonus

    def weapon_profile(self, ability: str = "STR") -> dict | None:
        """Return one explicit, explainable generic weapon calculation."""
        weapon = self.weapon()
        if weapon is None:
            return None
        stat = weapon.attack_ability or ability
        return {
            "name": weapon.display_name, "ability": stat,
            "ability_modifier": self.ability_modifier(stat),
            "proficiency": self.proficiency_bonus,
            "item_attack_bonus": weapon.attack_bonus,
            "attack_bonus": self.equipment_attack_bonus(ability),
            "damage_dice": weapon.damage_dice,
            "damage_modifier": weapon.damage_modifier,
            "critical_dice": weapon.critical_dice or weapon.damage_dice,
            "reach": weapon.reach,
            "range": {"normal": weapon.range_normal, "long": weapon.range_long},
            "alternate_modes": weapon.alternate_modes,
        }

    def describe(self) -> str:
        if not self.provenance.verified:
            flag = "   [PLACEHOLDER]"
        elif self.provenance.fidelity == "partial":
            flag = f"   [CERTIFIED, {len(self.provenance.deferred)} deferred]"
        else:
            flag = "   [CERTIFIED]"
        head = f"{self.name} -- {self.band.name}, {self.hp}/{self.max_hp} hp, AC {self.armor_class}{flag}"
        stats = "  " + "  ".join(
            f"{ability} {self.ability_score(ability)} ({self.ability_modifier(ability):+d})"
            for ability in DND_ABILITIES
        )
        gear = [f"  {i.display_name}" for i in self.equipment]
        return "\n".join([head, stats] + gear)

    def fast_clone(self, memo: dict | None = None) -> Actor:
        """Explicit field copy; the transactional clone path's per-actor copy.

        Scalars are shared, owned containers are copied one level, and only
        effects/equipment (mutable objects with their own state) recurse.
        """
        return self.__deepcopy__({} if memo is None else memo)

    def __deepcopy__(self, memo: dict) -> Actor:
        copied = memo.get(id(self))
        if copied is not None:
            return copied
        a = Actor.__new__(Actor)
        a.name = self.name
        a.band = self.band
        a.controller = self.controller
        a.sprite_id = self.sprite_id
        a.max_hp = self.max_hp
        a.hp = self.hp
        a.armor_class = self.armor_class
        a.initiative_bonus = self.initiative_bonus
        a.speed = self.speed
        a.attacks_per_action = self.attacks_per_action
        a.reactions = self.reactions
        a.ability_scores = dict(self.ability_scores)
        a.proficiency_bonus = self.proficiency_bonus
        a.skill_bonuses = dict(self.skill_bonuses)
        a.natural_tags = set(self.natural_tags)
        a.gate = self.gate
        a.inherent = [copy.deepcopy(e, memo) for e in self.inherent]
        a.equipment = [copy.deepcopy(item, memo) for item in self.equipment]
        a.resources = dict(self.resources)
        a.statuses = dict(self.statuses)
        a.features = list(self.features)
        a.provenance = self.provenance
        memo[id(self)] = a
        return a
