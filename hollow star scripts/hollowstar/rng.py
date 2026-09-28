"""Deterministic seeded RNG. Ported in spirit from sera/randomization.RunRNG.

Every run carries its seed so a disputed resolution can be replayed exactly
without exposing unopened rooms.
"""

from __future__ import annotations

import random


def clone_random(source: random.Random) -> random.Random:
    """Independent copy of a Mersenne Twister at the same position.

    ``copy.deepcopy`` reaches Random through ``__reduce__`` and then walks the
    625-int state tuple element by element; getstate/setstate copies it in C.
    """
    twin = type(source)(0)
    twin.setstate(source.getstate())
    return twin


class RunRNG:
    def __init__(self, seed: int | str):
        self.seed = seed
        self._r = random.Random(seed)
        self.calls = 0

    def random(self) -> float:
        self.calls += 1
        return self._r.random()

    def randint(self, a: int, b: int) -> int:
        self.calls += 1
        return self._r.randint(a, b)

    def choice(self, seq):
        self.calls += 1
        return self._r.choice(seq)

    def weighted_choice(self, population, weights):
        """Choose one entry from a validated, replayable weighted table."""
        population = list(population)
        weights = list(weights)
        if not population or len(population) != len(weights):
            raise ValueError("weighted choice requires equally sized, non-empty inputs")
        if any(isinstance(weight, bool) or not isinstance(weight, (int, float)) or weight < 0
               for weight in weights) or not any(weights):
            raise ValueError("weighted choice requires non-negative weights with a positive total")
        self.calls += 1
        return self._r.choices(population, weights=weights, k=1)[0]

    def d20(self) -> int:
        return self.randint(1, 20)

    def getstate(self):
        """Return the exact PRNG state for a resumable run save."""
        return self._r.getstate()

    def setstate(self, state) -> None:
        """Restore a state previously returned by :meth:`getstate`."""
        self._r.setstate(state)

    def fork(self, label: str) -> "RunRNG":
        """Sub-stream so room generation cannot perturb combat rolls."""
        return RunRNG(f"{self.seed}:{label}")
