"""
The one primitive.

An Effect is the smallest unit of "something changes." A monster's inherent
trait, a room law, a +3 prefix, and a suffix that grants a permanent material
state are ALL Effects. Same shape, same resolver, same collision rules.

That single-shape rule is what makes the rest cheap. Residents can trade
pieces, steal them, stack them, and lie about them, because there is only one
kind of thing to trade.

An Affix is a named bundle of Effects with an attachment style:
    prefix    -- detachable, goes in front of the item name
    suffix    -- detachable, goes after ("of Ice")
    inherent  -- NOT detachable; the thing's own nature
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from hollowstar.phases import Direction, Phase, Scope, Tier
from hollowstar.tags import DamageTag


@dataclass
class Effect:
    """One atomic rule."""

    name: str
    phase: Phase
    direction: Direction
    tier: Tier = Tier.MUNDANE
    scope: Scope = Scope.TARGET

    # Trigger condition key, evaluated by resolution.evaluate_condition.
    # "always" is the default and is always true.
    condition: str = "always"

    # --- MAGNITUDE payload (ported from the original Affix shape) ---
    flat_bonus: int = 0
    multiplier: float = 1.0
    per_stack_bonus: int = 0
    per_stack_source: str = ""

    # Restricts a MAGNITUDE effect to incoming sources carrying at least one
    # of these tags. Empty = applies to everything, which is the old
    # behaviour. This is what lets one suit of armour treat piercing,
    # slashing, and bludgeoning differently without three separate actors.
    applies_to_tags: set[DamageTag] = field(default_factory=set)

    # --- PERMISSION payload ---
    grants_tags: set[DamageTag] = field(default_factory=set)
    opens_gate: str = ""    # gate name this effect satisfies unconditionally
    closes_gate: str = ""   # gate name this effect imposes

    # --- CONSEQUENCE payload ---
    inflicts_status: str = ""
    status_duration: int = 0
    status_potency: int = 1
    # Optional D&D saving throw the target makes against the rider. Blank
    # ability means the rider attaches on a hit with no save (legacy rows).
    save_ability: str = ""
    save_dc: int = 0

    # Statuses this effect refuses to let attach. A CONSEQUENCE-phase DENY
    # carrying these is a condition immunity, which is a DIFFERENT thing
    # from a damage immunity at MAGNITUDE -- the whole point of the phase
    # split. Wren is categorically immune to mind-altering effects and
    # still fully subject to a forcecage.
    blocks_statuses: set[str] = field(default_factory=set)

    # --- Economy and legibility ---
    charges: int | None = None  # None = unlimited; ints deplete and exhaust.
    tell: str = ""              # Observable cue. Strong effects must have one.
    description: str = ""       # Flavor.

    # Public explanation metadata.  These fields are additive so existing
    # authored effects keep their old behaviour while clients gain a stable
    # source, stacking, duration, and "why did this apply?" vocabulary.
    operation: str = "add"       # add | multiply | override | advantage | disadvantage
    stat: str = ""               # public target, e.g. attack_roll or armor_class
    stack_group: str = ""        # blank means legacy additive behaviour
    source_id: str = ""          # stable authored/content source identifier
    duration: str = "permanent"  # equipped | turn | round | encounter | concentration | permanent
    priority: int = 0            # higher wins inside an explicit stack group
    public_summary: str = ""     # short tooltip copy; mechanics remain above

    # Higher = more specific. Breaks ties inside the same tier.
    specificity: int = 0

    def is_exhausted(self) -> bool:
        return self.charges is not None and self.charges <= 0

    def spend(self) -> None:
        if self.charges is not None:
            self.charges -= 1

    def is_strong(self) -> bool:
        """Effects that deny at an early phase are the ones that need tells."""
        return (
            self.direction is Direction.DENY
            and self.phase <= Phase.APPLICATION
        )

    def __deepcopy__(self, memo: dict) -> Effect:
        copied = memo.get(id(self))
        if copied is not None:
            return copied
        e = Effect.__new__(Effect)
        e.name = self.name
        e.phase = self.phase
        e.direction = self.direction
        e.tier = self.tier
        e.scope = self.scope
        e.condition = self.condition
        e.flat_bonus = self.flat_bonus
        e.multiplier = self.multiplier
        e.per_stack_bonus = self.per_stack_bonus
        e.per_stack_source = self.per_stack_source
        e.applies_to_tags = set(self.applies_to_tags)
        e.grants_tags = set(self.grants_tags)
        e.opens_gate = self.opens_gate
        e.closes_gate = self.closes_gate
        e.inflicts_status = self.inflicts_status
        e.status_duration = self.status_duration
        e.status_potency = self.status_potency
        e.save_ability = self.save_ability
        e.save_dc = self.save_dc
        e.blocks_statuses = set(self.blocks_statuses)
        e.charges = self.charges
        e.tell = self.tell
        e.description = self.description
        e.operation = self.operation
        e.stat = self.stat
        e.stack_group = self.stack_group
        e.source_id = self.source_id
        e.duration = self.duration
        e.priority = self.priority
        e.public_summary = self.public_summary
        e.specificity = self.specificity
        memo[id(self)] = e
        return e


@dataclass
class Affix:
    """A named, attachable bundle of Effects."""

    name: str
    affix_type: str  # "prefix" | "suffix" | "inherent"
    effects: list[Effect] = field(default_factory=list)
    description: str = ""

    @property
    def detachable(self) -> bool:
        return self.affix_type in ("prefix", "suffix")

    def describe(self) -> str:
        return f"[{self.affix_type.upper()}] {self.name}: {self.description}"

    def __deepcopy__(self, memo: dict) -> Affix:
        copied = memo.get(id(self))
        if copied is not None:
            return copied
        a = Affix.__new__(Affix)
        a.name = self.name
        a.affix_type = self.affix_type
        a.description = self.description
        a.effects = [copy.deepcopy(e, memo) for e in self.effects]
        memo[id(self)] = a
        return a
