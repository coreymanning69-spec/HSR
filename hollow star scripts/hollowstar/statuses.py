"""Status registry: what a status IS, and the hook points around applying it.

Data (name, category, decay policy) lives in ``content/statuses.json``.  Rules
that need engine state register here as functions, so adding a status or a
refusal rule never means editing an if-chain in ``tactical``:

    @statuses.refusal
    def _no_prone_when_planted(run, key, name, mental): ...

Events fired by tactical: ``apply`` (after a status lands), ``tick`` (each
turn-end decrement) and ``expire`` (when it reaches zero).  Hooks receive
``(run, key, name)`` and must not raise.  This module imports nothing from the
engine, so any module may import it without creating a cycle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

CONTENT = Path(__file__).parent / "content" / "statuses.json"


@dataclass(frozen=True)
class StatusDef:
    name: str
    category: str = "physical"
    incapacitating: bool = False      # applying it ends the holder's concentration
    decays: bool = True               # -1 per own turn end; False = managed elsewhere
    clears_on_turn_start: bool = False  # dropped when the holder's next turn begins


DEFS: dict[str, StatusDef] = {}
# Live views kept as plain sets so existing `name in CONDITIONS` call sites work.
CONDITIONS: set[str] = set()
MENTAL_CONDITIONS: set[str] = set()
INCAPACITATING: set[str] = set()
CONDITION_CATEGORIES: dict[str, str] = {}

_REFUSALS: list[Callable] = []
_HOOKS: dict[str, list[Callable]] = {"apply": [], "tick": [], "expire": []}


def register(defn: StatusDef) -> StatusDef:
    """Add or replace a status definition and refresh the derived views."""
    DEFS[defn.name] = defn
    CONDITIONS.add(defn.name)
    CONDITION_CATEGORIES[defn.name] = defn.category
    (MENTAL_CONDITIONS.add if defn.category == "mental" else MENTAL_CONDITIONS.discard)(defn.name)
    (INCAPACITATING.add if defn.incapacitating else INCAPACITATING.discard)(defn.name)
    return defn


def load(path: Path = CONTENT) -> None:
    for row in json.loads(path.read_text(encoding="utf-8"))["statuses"]:
        register(StatusDef(**row))


def get(name: str) -> StatusDef | None:
    return DEFS.get(name)


def decays(name: str) -> bool:
    d = DEFS.get(name)
    return d.decays if d else True


def turn_start_cleared() -> tuple[str, ...]:
    return tuple(n for n, d in DEFS.items() if d.clears_on_turn_start)


def refusal(fn: Callable) -> Callable:
    """Register ``fn(run, key, name, mental) -> dict | None``; first non-None wins."""
    _REFUSALS.append(fn)
    return fn


def first_refusal(run, key, name, mental=False):
    for fn in _REFUSALS:
        found = fn(run, key, name, mental)
        if found:
            return found
    return None


def hook(event: str) -> Callable:
    def add(fn: Callable) -> Callable:
        _HOOKS[event].append(fn)
        return fn
    return add


def fire(event: str, run, key, name) -> None:
    for fn in _HOOKS[event]:
        fn(run, key, name)


load()
