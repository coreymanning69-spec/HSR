"""Multi-actor combat loop.

The original engine was single-protagonist autobattle. Hollow Star needs a
party, so initiative spans every actor and each actor may hold several
attacks per action.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from hollowstar.actors import Actor
from hollowstar.effects import Effect
from hollowstar.resolution import Resolution, resolve_attack
from hollowstar.rng import RunRNG
from hollowstar.world import world_context


@dataclass
class Encounter:
    party: list[Actor]
    opposition: list[Actor]
    rng: RunRNG
    environment: list[Effect] = field(default_factory=list)
    round_number: int = 0
    transcript: list[Resolution] = field(default_factory=list)
    mode: str = "SIMULATION"
    # Public build identity and selected profile metadata, never unopened rooms.
    context: dict = field(default_factory=lambda: {"world": world_context()})

    def initiative(self) -> list[Actor]:
        actors = [a for a in self.party + self.opposition if a.alive]
        return sorted(
            actors,
            key=lambda a: (self.rng.d20() + a.initiative_bonus),
            reverse=True,
        )

    def enemies_of(self, actor: Actor) -> list[Actor]:
        side = self.opposition if actor in self.party else self.party
        return [a for a in side if a.alive]

    def take_turn(self, actor: Actor) -> None:
        self.start_turn(actor)
        if not actor.alive or self.is_incapacitated(actor):
            self.end_turn(actor)
            return
        for _ in range(actor.attacks_per_action):
            targets = self.enemies_of(actor)
            if not targets:
                return
            target = targets[0]
            res = resolve_attack(actor, target, self.environment)
            self.transcript.append(res)
        self.end_turn(actor)

    @staticmethod
    def is_incapacitated(actor: Actor) -> bool:
        return bool({"STUNNED", "PARALYZED", "INCAPACITATED", "UNCONSCIOUS"}.intersection(actor.statuses))

    def start_turn(self, actor: Actor) -> list[dict]:
        """Apply data-defined periodic effects before action validation."""
        events = []
        for effect in self.context.get("periodic_effects", {}).get(actor.name, []):
            status = effect.get("status")
            if status and status not in actor.statuses:
                continue
            before = actor.hp
            actor.adjust_hp(int(effect.get("healing", 0)) - int(effect.get("damage", 0)))
            events.append({"actor": actor.name, "status": status,
                           "damage": max(0, before - actor.hp),
                           "healing": max(0, actor.hp - before)})
        return events

    def end_turn(self, actor: Actor) -> list[str]:
        """Decrement statuses and purge expired flags after action execution."""
        expired = []
        for name in list(actor.statuses):
            actor.statuses[name] -= 1
            if actor.statuses[name] <= 0:
                expired.append(name)
                del actor.statuses[name]
        return expired

    def run_round(self) -> None:
        self.round_number += 1
        for actor in self.initiative():
            if actor.alive:
                self.take_turn(actor)

    def finished(self) -> bool:
        return not any(a.alive for a in self.party) or not any(
            a.alive for a in self.opposition
        )

    def run(self, max_rounds: int = 20) -> str:
        while not self.finished() and self.round_number < max_rounds:
            self.run_round()
        if not any(a.alive for a in self.opposition):
            return "party"
        if not any(a.alive for a in self.party):
            return "opposition"
        return "timeout"
