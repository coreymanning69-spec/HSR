"""
The resolver.

Every action walks the phase pipeline in order. At each phase, the effects
that act there are collected from attacker, defender, and environment, then
adjudicated.

WHY THIS MATTERS
----------------
Most "impossible vs impossible" fights are not collisions at all. A creature
immune to fire damage is denying at MAGNITUDE; a fire spell that also
restrains still restrains, because restraint lives at CONSEQUENCE. Something
that cannot be targeted never reaches DELIVERY, so an unblockable-delivery
affix is simply irrelevant against it. Two "absolutes" pass each other without
touching.

A real collision is same-phase, opposite-direction. Those resolve by lattice:

    1. TIER          -- higher authority wins outright.
    2. SPECIFICITY   -- narrower scope, then higher specificity, wins.
    3. DENY > GRANT  -- default when everything else ties.
    4. EXHAUSTION    -- charges are spent, so nothing loops forever.

The resolver reports WHICH PHASE stopped an action. That is the information
loop the crawler runs on: "damage doesn't work, try restraint" instead of
"nothing works."
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from hollowstar.rng import RunRNG

from hollowstar.actors import Actor
from hollowstar.effects import Effect
from hollowstar.phases import Direction, Phase, Scope, Tier


@dataclass
class ResolutionStep:
    phase: Phase
    passed: bool
    decided_by: Effect | None = None
    note: str = ""


@dataclass
class Resolution:
    """Structured outcome. The narrator reads this; it never invents facts."""

    attacker: str
    defender: str
    damage: int = 0
    stopped_at: Phase | None = None
    steps: list[ResolutionStep] = field(default_factory=list)
    statuses_applied: list[str] = field(default_factory=list)
    statuses_refused: list[str] = field(default_factory=list)
    tells_revealed: list[str] = field(default_factory=list)
    # Machine-readable evidence for adapters and audit tooling.  The legacy
    # fields above remain the compact compatibility view used by existing
    # callers; this bundle is additive and never becomes a second authority.
    evidence: dict = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.stopped_at is None

    def log(self) -> str:
        lines = []
        for s in self.steps:
            mark = "ok  " if s.passed else "STOP"
            who = f" <- {s.decided_by.name}" if s.decided_by else ""
            lines.append(f"  [{mark}] {s.phase.name}{who} {s.note}".rstrip())
        for status in self.statuses_refused:
            lines.append(f"  [----] CONSEQUENCE {status} refused")
        if self.succeeded:
            lines.append(f"  => {self.damage} damage")
        else:
            lines.append(f"  => blocked at {self.stopped_at.name}")
        return "\n".join(lines)


def select_stackable(effects: list[Effect]) -> tuple[list[Effect], list[dict]]:
    """Apply explicit stack groups while preserving legacy ungrouped effects.

    Existing effects have no ``stack_group`` and therefore retain their old
    additive behaviour.  Once content opts into a group, the highest-priority
    effect wins; specificity, tier, and declaration order make the result
    deterministic.  Suppressed rows are returned for public explanations.
    """
    selected: list[Effect] = []
    suppressed: list[dict] = []
    groups: dict[str, list[Effect]] = {}
    for effect in effects:
        group = str(effect.stack_group or "")
        if not group:
            selected.append(effect)
        else:
            groups.setdefault(group, []).append(effect)
    for group, rows in groups.items():
        _winner_index, winner = max(enumerate(rows), key=lambda pair: (
            int(pair[1].priority), int(pair[1].specificity), int(pair[1].tier), -pair[0]
        ))
        selected.append(winner)
        for effect in rows:
            if effect is winner:
                continue
            suppressed.append({
                "effect": effect.name,
                "stack_group": group,
                "reason": f"suppressed by {winner.name}",
            })
    return selected, suppressed


def evaluate_condition(cond: str, attacker: Actor, defender: Actor) -> bool:
    """Condition keys. Extend freely; unknown keys are treated as false."""
    if cond in ("", "always"):
        return True
    if cond == "enemy_full_hp":
        return defender.hp >= defender.max_hp
    if cond == "enemy_bloodied":
        return defender.hp <= defender.max_hp // 2
    if cond == "enemy_casting":
        return "CASTING" in defender.statuses
    if cond == "self_bloodied":
        return attacker.hp <= attacker.max_hp // 2
    if cond == "target_has_status":
        return bool(defender.statuses)
    return False


def _wins(a: Effect, b: Effect) -> Effect:
    """Lattice. Returns whichever effect governs."""
    if a.tier != b.tier:
        return a if a.tier > b.tier else b
    if a.scope != b.scope:
        return a if a.scope < b.scope else b  # narrower scope wins
    if a.specificity != b.specificity:
        return a if a.specificity > b.specificity else b
    if a.direction != b.direction:
        return a if a.direction is Direction.DENY else b
    return a


def _governing(effects: list[Effect]) -> Effect | None:
    if not effects:
        return None
    best = effects[0]
    for eff in effects[1:]:
        best = _wins(best, eff)
    return best


def collect(
    phase: Phase,
    attacker: Actor,
    defender: Actor,
    environment: list[Effect] | None = None,
) -> list[Effect]:
    pool = attacker.active_effects() + defender.active_effects() + list(environment or [])
    return [
        e
        for e in pool
        if e.phase is phase
        and not e.is_exhausted()
        and evaluate_condition(e.condition, attacker, defender)
    ]


def resolve_attack(
    attacker: Actor,
    defender: Actor,
    environment: list[Effect] | None = None,
    *,
    rng: RunRNG | None = None,
    advantage: bool = False,
    disadvantage: bool = False,
) -> Resolution:
    # Dice resolution is opt-in until all imported signatures are encoded.
    # Missing dice cannot silently stand in for fixed-damage or special crit laws.
    weapon = attacker.weapon()
    dice = None
    if rng is not None:
        if not attacker.alive or not defender.alive:
            raise ValueError("attacks require living participants")
        if not isinstance(advantage, bool) or not isinstance(disadvantage, bool):
            raise ValueError("advantage and disadvantage must be booleans")
        dice = re.fullmatch(r"([1-9]|[1-9][0-9]|100)d(4|6|8|10|12|20)", weapon.damage_dice) if weapon else None
        if dice is None:
            raise ValueError("weapon has no supported explicit damage dice; its signature remains deferred")
        if not isinstance(weapon.damage_modifier, int) or isinstance(weapon.damage_modifier, bool):
            raise ValueError("damage modifier must be an integer")
    critical = False
    res = Resolution(attacker=attacker.name, defender=defender.name)
    environment = environment or []
    res.evidence = {
        "actor": attacker.name,
        "target": defender.name,
        "legality": [],
        "advantage": advantage,
        "disadvantage": disadvantage,
        "target_ac": defender.armor_class,
        "attack": None,
        "damage": None,
        "critical": False,
        "statuses_applied": res.statuses_applied,
        "statuses_refused": res.statuses_refused,
    }

    # --- Gate check happens at PERMISSION, before anything else. -----------
    tags = attacker.offensive_tags()
    gate_ok = defender.gate.is_satisfied_by(tags)
    for eff in collect(Phase.PERMISSION, attacker, defender, environment):
        if eff.opens_gate and eff.opens_gate == defender.gate.name:
            gate_ok = True
    if not gate_ok:
        res.evidence["legality"].append({"phase": "PERMISSION", "passed": False})
        res.steps.append(
            ResolutionStep(Phase.PERMISSION, False, None, f"gate {defender.gate.name} unsatisfied")
        )
        res.stopped_at = Phase.PERMISSION
        if defender.gate.tell:
            res.tells_revealed.append(defender.gate.tell)
        return res
    res.evidence["legality"].append({"phase": "PERMISSION", "passed": True})
    res.steps.append(ResolutionStep(Phase.PERMISSION, True))

    # --- Blocking phases ---------------------------------------------------
    for phase in (Phase.TARGETING, Phase.DELIVERY, Phase.APPLICATION):
        acting = collect(phase, attacker, defender, environment)
        gov = _governing(acting)
        if gov and gov.direction is Direction.DENY:
            gov.spend()
            res.steps.append(ResolutionStep(phase, False, gov))
            res.stopped_at = phase
            if gov.tell:
                res.tells_revealed.append(gov.tell)
            res.evidence["legality"].append({"phase": phase.name, "passed": False, "decided_by": gov.name})
            return res
        res.evidence["legality"].append({"phase": phase.name, "passed": True, "decided_by": gov.name if gov else None})
        if phase is Phase.DELIVERY and rng is not None:
            rolls = [rng.d20()]
            if advantage != disadvantage:
                rolls.append(rng.d20())
            natural = max(rolls) if advantage and not disadvantage else min(rolls)
            total = natural + weapon.attack_bonus
            critical = natural == 20
            hit = natural != 1 and (critical or total >= defender.armor_class)
            res.evidence["attack"] = {
                "rolls": list(rolls), "natural": natural, "bonus": weapon.attack_bonus,
                "total": total, "target_ac": defender.armor_class, "hit": hit,
            }
            res.evidence["critical"] = critical
            note = f"d20 {rolls} + {weapon.attack_bonus} = {total} vs AC {defender.armor_class}"
            note += " (natural 20, critical)" if critical else " (natural 1, miss)" if natural == 1 else ""
            res.steps.append(ResolutionStep(phase, hit, gov, note))
            if not hit:
                res.stopped_at = phase
                return res
        else:
            res.steps.append(ResolutionStep(phase, True, gov))

    # --- MAGNITUDE ---------------------------------------------------------
    weapon = attacker.weapon()
    damage_note = "legacy fixed magnitude; no attack roll"
    if rng is not None:
        count, sides = map(int, dice.groups())
        rolled = [rng.randint(1, sides) for _ in range(count * (2 if critical else 1))]
        damage = float(max(0, sum(rolled) + weapon.damage_modifier))
        damage_note = f"{len(rolled)}d{sides} {rolled} + {weapon.damage_modifier} = {int(damage)}"
        res.evidence["damage"] = {
            "dice": f"{len(rolled)}d{sides}", "rolls": list(rolled),
            "modifier": weapon.damage_modifier, "density": weapon.density,
        }
    else:
        damage = float(weapon.base_damage if weapon else 1)
    if weapon:
        damage *= weapon.density

    # An effect with applies_to_tags only acts on sources carrying one of
    # those tags. Armour that halves slashing does nothing to a fire spell.
    incoming = attacker.offensive_tags()
    mag = [
        e
        for e in collect(Phase.MAGNITUDE, attacker, defender, environment)
        if not e.applies_to_tags or (e.applies_to_tags & incoming)
    ]
    mag, suppressed = select_stackable(mag)
    res.evidence["suppressed"] = suppressed
    res.evidence["contributors"] = [
        {"source": effect.name, "operation": effect.operation,
         "stat": effect.stat or "magnitude", "value": effect.flat_bonus,
         "stack_group": effect.stack_group or None}
        for effect in mag if effect.flat_bonus or effect.multiplier != 1
    ]
    for eff in mag:
        damage += eff.flat_bonus
        if eff.per_stack_bonus and eff.per_stack_source == "debuffs_on_target":
            damage += eff.per_stack_bonus * len(defender.statuses)
    for eff in mag:
        damage *= eff.multiplier

    damage = max(0, int(damage))
    res.damage = damage
    res.evidence["damage_total"] = damage
    res.steps.append(ResolutionStep(Phase.MAGNITUDE, True, _governing(mag), damage_note))

    # --- CONSEQUENCE: riders land even at zero damage. ---------------------
    # Condition immunity lives here, not at MAGNITUDE. A creature that takes
    # no fire damage can still be restrained by the same spell; a creature
    # immune to fear can still be set on fire. Collect the refusals first,
    # then let the riders try to land.
    conseq, consequence_suppressed = select_stackable(
        collect(Phase.CONSEQUENCE, attacker, defender, environment)
    )
    if consequence_suppressed:
        res.evidence.setdefault("suppressed", []).extend(consequence_suppressed)
    refused: dict[str, Effect] = {}
    for eff in conseq:
        if eff.direction is Direction.DENY:
            for status in eff.blocks_statuses:
                refused[status] = eff

    for eff in conseq:
        if eff.direction is Direction.DENY:
            continue
        if not eff.inflicts_status:
            continue
        blocker = refused.get(eff.inflicts_status)
        if blocker is not None:
            res.statuses_refused.append(eff.inflicts_status)
            if blocker.tell and blocker.tell not in res.tells_revealed:
                res.tells_revealed.append(blocker.tell)
            continue
        defender.statuses[eff.inflicts_status] = eff.status_duration
        res.statuses_applied.append(eff.inflicts_status)
        eff.spend()
    res.steps.append(ResolutionStep(Phase.CONSEQUENCE, True))

    defender.adjust_hp(-damage)
    res.evidence["state_changes"] = {
        "target_hp_before": defender.hp + damage,
        "target_hp_after": defender.hp,
        "statuses_applied": list(res.statuses_applied),
        "statuses_refused": list(res.statuses_refused),
    }
    return res
