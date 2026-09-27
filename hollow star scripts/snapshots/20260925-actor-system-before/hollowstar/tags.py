"""
Conceptual tags and gates.

Ported from sera/tags.py, which already had the core idea right:

    Damage isn't physics. It's Concept.
    If the weapon can't conceptually threaten the enemy, it deals nothing.

Extended here in two ways:
  1. Gates are data, not a fixed enum of REQUIRES_X cases. A gate names the
     set of tags that satisfy it, so "divine OR ethereal" needs no special
     case, and new gates need no code change.
  2. Gates carry a `tell` -- something observable that lets a player infer the
     gate without being told. Blind play protects future rooms; it never
     excuses an unlearnable wall.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class DamageTag(Enum):
    """What a source IS, conceptually."""

    PHYSICAL = auto()
    # The three D&D physical subtypes. Imported sheets need them because
    # real armour discriminates between them -- Doran's divine plate
    # transmits piercing, slashing, and bludgeoning at three different
    # rates. PHYSICAL remains the umbrella for anything that does not
    # care which of the three it is.
    PIERCING = auto()
    SLASHING = auto()
    BLUDGEONING = auto()
    HEAVY = auto()
    DIVINE = auto()
    ETHEREAL = auto()
    SILVER = auto()
    CORROSIVE = auto()
    FIRE = auto()
    AIR = auto()
    WATER = auto()
    ICE = auto()
    EARTH = auto()
    ARCANE = auto()
    BLEED = auto()
    SONIC = auto()
    PSYCHIC = auto()
    RADIANT = auto()
    NECROTIC = auto()
    FORCE = auto()


@dataclass(frozen=True)
class Gate:
    """
    A conceptual requirement. Satisfied if the source carries ANY tag in
    `satisfied_by`. An empty set means "anything works" -- basic trash.
    """

    name: str
    satisfied_by: frozenset[DamageTag] = field(default_factory=frozenset)
    tell: str = ""

    def is_satisfied_by(self, tags: set[DamageTag]) -> bool:
        if not self.satisfied_by:
            return True
        return bool(self.satisfied_by & tags)


# --- Standard gate library -------------------------------------------------
# These reproduce the original EnemyVulnerability cases as data.

GATES: dict[str, Gate] = {
    "none": Gate("none", frozenset(), ""),
    "requires_divine": Gate(
        "requires_divine",
        frozenset({DamageTag.DIVINE}),
        "Blows land and pass through with no sound of contact.",
    ),
    "requires_ethereal": Gate(
        "requires_ethereal",
        frozenset({DamageTag.ETHEREAL}),
        "The edge leaves a cold seam in the air where the body should be.",
    ),
    "requires_divine_or_ethereal": Gate(
        "requires_divine_or_ethereal",
        frozenset({DamageTag.DIVINE, DamageTag.ETHEREAL}),
        "It flinches from lantern-light but not from steel.",
    ),
    "requires_silver": Gate(
        "requires_silver",
        frozenset({DamageTag.SILVER}),
        "Cuts close instantly, faster than the wound was made.",
    ),
    "requires_heavy": Gate(
        "requires_heavy",
        frozenset({DamageTag.HEAVY, DamageTag.CORROSIVE}),
        "Points skate off the plate; nothing bites.",
    ),
    "requires_fire": Gate(
        "requires_fire",
        frozenset({DamageTag.FIRE}),
        "Severed tissue reaches back toward the stump.",
    ),
    "requires_arcane": Gate(
        "requires_arcane",
        frozenset({DamageTag.ARCANE}),
        "Mundane force sloughs off a half-inch from the surface.",
    ),
}
