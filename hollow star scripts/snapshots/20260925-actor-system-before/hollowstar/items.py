"""
Items.

An Item is a D&D base object -- longsword, chain shirt, ring of protection --
that already has INHERENT effects from the rules as written. Prefixes and
suffixes bolt on top. Sometimes one, sometimes both, sometimes neither.

    longsword                       -> inherent only
    Petty longsword                 -> inherent + prefix
    longsword of Ice                -> inherent + suffix
    Petty longsword of Ice          -> inherent + prefix + suffix

The Primeverse reading of the grammar is deliberately material rather than
numeric: a +3 dagger is three times as dense and hard, and "of Ice" is a
permanent material state, which is why it has uses outside a fight -- chill a
drink, drop a fever, cauterize. That is modelled as a PERSISTENCE effect with
listed `utility_uses`, not as a cold-damage rider.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hollowstar.effects import Affix, Effect
from hollowstar.phases import Tier
from hollowstar.tags import DamageTag


@dataclass
class Item:
    name: str
    slot: str = "hand"        # hand | armor | ring | neck | cloak | boots | head
    sprite_id: str = ""       # e.g. "longsword-1", "shield-iron"
    base_damage: int = 0
    attack_bonus: int = 0
    # Explicit dice specification for the d20 resolver; blank means unsupported.
    damage_dice: str = ""
    damage_modifier: int = 0
    reach: int = 5
    range_normal: int = 5
    range_long: int = 5
    critical_dice: str = ""
    alternate_modes: dict = field(default_factory=dict)
    base_ac: int = 0
    # Optional inputs for ordinary equipment math.  Certified Steward AC and
    # signature attacks remain source-authoritative overrides in their rules.
    dex_cap: int | None = None
    ac_bonus: int = 0
    shield_bonus: int = 0
    attack_ability: str = ""
    tier: Tier = Tier.MUNDANE

    tags: set[DamageTag] = field(default_factory=set)
    inherent: list[Effect] = field(default_factory=list)

    prefix: Affix | None = None
    suffix: Affix | None = None

    # Density multiplier. Primeverse reading of "+N": 3x dense, not "+3 hit".
    density: float = 1.0

    # Non-combat applications the material state permits.
    utility_uses: list[str] = field(default_factory=list)

    # Authored visual overrides.  Some items cannot be told apart by their
    # maths -- a Robe of the Archmagi and a leather jerkin have the same AC
    # profile -- so art may be stated outright.  Blank means "derive it".
    silhouette: str = ""
    material: str = ""
    # Presentation contract shared by the paperdoll and combat director.  The
    # values are descriptive only; legality, damage, and action economy still
    # come from the fields above and the tactical resolver.
    item_type: str = ""
    handedness: str = ""
    coverage: str = ""
    animation_profile: str = ""

    # Reliquary Imprints dissolve on exit; canonical gear does not.
    temporary: bool = False
    flavor: str = ""

    @property
    def display_name(self) -> str:
        parts = []
        if self.prefix:
            parts.append(self.prefix.name)
        parts.append(self.name)
        if self.suffix:
            parts.append(self.suffix.name)
        return " ".join(parts)

    def all_effects(self) -> list[Effect]:
        """Inherent first, then prefix, then suffix. Order is not precedence."""
        out = list(self.inherent)
        if self.prefix:
            out.extend(self.prefix.effects)
        if self.suffix:
            out.extend(self.suffix.effects)
        return out

    def all_tags(self) -> set[DamageTag]:
        tags = set(self.tags)
        for eff in self.all_effects():
            tags |= eff.grants_tags
        return tags

    def describe(self) -> str:
        lines = [f"{self.display_name}  ({self.slot}, {self.tier.name.lower()})"]
        if self.base_damage:
            lines.append(f"  base damage {self.base_damage}, density x{self.density:g}")
            lines.append(f"  attack bonus {self.attack_bonus:+d}")
        if self.base_ac:
            lines.append(f"  base AC {self.base_ac}")
        tags = ", ".join(sorted(t.name for t in self.all_tags()))
        if tags:
            lines.append(f"  tags: {tags}")
        for eff in self.all_effects():
            lines.append(f"  - {eff.name} [{eff.phase.name}/{eff.direction.name}]")
        if self.utility_uses:
            lines.append(f"  uses: {'; '.join(self.utility_uses)}")
        return "\n".join(lines)


# Visual projection.
#
# Every value below is derived from fields the item already authors for the
# resolver -- slot, dice, reach, AC, dex cap, tags, tier, density.  Nothing
# reads the item's NAME.  That matters twice over: a name regex mis-fires on
# "Hood of the Plate Captain", and deriving from mechanics means an upgraded
# item's picture tracks what actually changed about it, for free.

# Elemental tags worth drawing.  PHYSICAL and its three subtypes are the
# unmarked default and deliberately absent -- an ordinary sword gets no aura.
_FX_TAGS = {
    "FIRE": "ember", "ICE": "frost", "WATER": "tide", "AIR": "gale",
    "EARTH": "stone", "ARCANE": "arcane", "DIVINE": "hallow",
    "RADIANT": "radiant", "NECROTIC": "wither", "PSYCHIC": "mind",
    "SONIC": "resonant", "CORROSIVE": "acid", "FORCE": "force",
    "BLEED": "bleed", "ETHEREAL": "phase", "SILVER": "silver",
}

# Weapon silhouettes the paperdoll can draw.  Keep in step with the
# `weapon:*` entries in the client's SPRITE_LAYER_CATALOG.
_WEAPON_SILHOUETTES = ("sword", "staff", "wand", "bow", "shield", "dagger", "axe", "mace", "polearm")


def _silhouette(item: Item) -> str:
    """Which shape the figure should hold or wear."""
    if item.silhouette:
        return item.silhouette.lower()
    slot = (item.slot or "hand").lower()
    # Carried, but not wielded -- kept out of "hand" so its tags stay out of
    # the attack path. It is still a staff, so it is drawn as one.
    if slot == "carried":
        return "staff"
    if slot == "armor":
        return "armor"
    if slot == "head":
        return "helm"
    if slot == "cloak":
        return "cloak"
    if slot == "boots":
        return "boots"
    if slot in ("ring", "neck"):
        return "trinket"
    if slot != "hand":
        # An unrecognised slot is worn or carried, but we do not know as what.
        # "held" is deliberately neutral -- guessing "sword" is how a staff
        # ends up drawn as a blade.
        return "held"
    # Hand slot.  A shield bonus beats damage: a shield is a shield even when
    # it can be swung.
    if item.shield_bonus or (item.base_ac and not item.base_damage):
        return "shield"
    if item.range_normal > 20:
        return "bow"
    if (item.attack_ability or "").upper() in ("INT", "WIS", "CHA"):
        return "staff"
    tags = {tag.name for tag in item.all_tags()}
    if "BLUDGEONING" in tags and "SLASHING" not in tags:
        return "staff"
    if "PIERCING" in tags and "SLASHING" not in tags and item.reach <= 5:
        return "dagger"
    return "sword"


def _material(item: Item) -> str:
    """Body material, from the armour maths rather than the item's name.

    The dex cap is the honest tell: plate ignores Dexterity entirely, medium
    armour caps it, light armour does not touch it.  That is the same signal
    the AC resolver uses, so the picture cannot disagree with the rules.
    """
    if item.material:
        return item.material.lower()
    slot = (item.slot or "hand").lower()
    if slot == "armor":
        # The dex cap separates the three armour weights: plate ignores
        # Dexterity, medium armour caps it, light armour leaves it alone.
        if item.dex_cap == 0:
            return "plate"
        if item.dex_cap is not None:
            return "chain"
        # Uncapped armour is cloth or leather, and the AC magnitude tells them
        # apart: leather is weak (11-12) and tops out well below a warded robe,
        # which reaches 18 precisely because it is magical cloth rather than hide.
        if item.base_ac and item.base_ac >= 15:
            return "robe"
        if item.base_ac and item.base_ac >= 12:
            return "leather"
        return "robe"
    if slot == "cloak":
        return "cloth"
    if slot == "boots":
        return "leather"
    tags = {tag.name for tag in item.all_tags()}
    if "SILVER" in tags:
        return "silver"
    if slot in ("ring", "neck"):
        return "gold"
    if _silhouette(item) in ("staff", "wand", "bow"):
        return "wood"
    return "steel"


def _item_type(item: Item, silhouette: str) -> str:
    if item.item_type:
        return item.item_type.lower()
    if silhouette in _WEAPON_SILHOUETTES and silhouette != "shield":
        return "weapon"
    if silhouette == "shield":
        return "shield"
    if silhouette == "armor":
        return "armor"
    if silhouette == "helm":
        return "headgear"
    if silhouette == "cloak":
        return "cloak"
    if silhouette == "boots":
        return "boots"
    if silhouette == "trinket":
        return "accessory"
    if item.slot == "carried":
        return "carried"
    return "utility"


def _handedness(item: Item, silhouette: str) -> str:
    if item.handedness:
        return item.handedness.lower()
    if silhouette == "shield":
        return "off-hand"
    if silhouette in {"bow", "staff"}:
        return "two-handed"
    if silhouette in _WEAPON_SILHOUETTES:
        return "one-handed"
    return "none"


def _coverage(item: Item, silhouette: str) -> str:
    if item.coverage:
        return item.coverage.lower()
    if silhouette == "helm":
        return "partial"
    if silhouette == "armor":
        return "full-body"
    return "none"


def _animation_profile(item: Item, silhouette: str, handedness: str) -> str:
    if item.animation_profile:
        return item.animation_profile.lower()
    if silhouette == "shield":
        return "shield"
    if silhouette == "bow":
        return "bow"
    if silhouette in {"staff", "wand"}:
        return silhouette
    if silhouette == "dagger":
        return "dagger"
    if silhouette == "axe":
        return "axe-2h" if handedness == "two-handed" else "axe"
    if silhouette == "sword":
        return "sword-2h" if handedness == "two-handed" else "sword-1h"
    if silhouette == "helm" and _coverage(item, silhouette) == "full":
        return "armored-guard"
    if silhouette == "armor" and _material(item) == "plate":
        return "heavy-armor"
    return "neutral"


def item_presentation(item: Item) -> dict:
    """Public visual facts for one item.  Presentation only; never mechanics."""
    tags = {tag.name for tag in item.all_tags()}
    silhouette = _silhouette(item)
    handedness = _handedness(item, silhouette)
    fx = sorted({_FX_TAGS[name] for name in tags if name in _FX_TAGS})
    # Rarity earns its own treatment at artifact and above; density is the
    # Primeverse reading of "+N" and reads as heft, not as a glow.
    if item.tier >= Tier.ARTIFACT:
        fx.append("glow")
    if item.density >= 2:
        fx.append("dense")
    # Deliberately minimal.  `slot`, the affix names and the effect tells are
    # already on the public item, and this block rides in every turn payload --
    # design_turn is capped at 10k characters, so nothing gets duplicated here.
    return {
        "rarity": item.tier.name.lower(),
        "silhouette": silhouette,
        "material": _material(item),
        "fx": sorted(set(fx)),
        "item_type": _item_type(item, silhouette),
        "handedness": handedness,
        "coverage": _coverage(item, silhouette),
        "animation_profile": _animation_profile(item, silhouette, handedness),
    }


def public_item(item: Item) -> dict:
    """JSON-safe equipment presentation, derived from the equipped instance."""
    from dataclasses import asdict
    from enum import Enum

    def plain(value):
        if isinstance(value, Enum):
            return value.name
        if isinstance(value, dict):
            return {key: plain(val) for key, val in value.items()}
        if isinstance(value, (list, tuple)):
            return [plain(val) for val in value]
        if isinstance(value, set):
            return sorted(plain(val) for val in value)
        return value

    result = plain(asdict(item))
    result["display_name"] = item.display_name
    result["tags"] = sorted(tag.name for tag in item.all_tags())
    result["appearance"] = [effect.tell for effect in item.all_effects() if effect.tell]
    result["presentation"] = item_presentation(item)
    # Keep the raw effect fields for compatibility, while adding the shared
    # tooltip/examine projection used by graphical clients.
    from hollowstar.explanations import public_effect
    result["effect_explanations"] = [
        public_effect(effect, source={"kind": "item", "id": item.name, "name": item.display_name})
        for effect in result["inherent"]
    ]
    for affix_kind in ("prefix", "suffix"):
        affix = result.get(affix_kind)
        if isinstance(affix, dict):
            result["effect_explanations"].extend(
                public_effect(effect, source={"kind": "affix", "id": f"{item.name}:{affix_kind}",
                                               "name": affix.get("name", affix_kind.title())})
                for effect in affix.get("effects", [])
            )
    return result
