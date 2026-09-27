"""
The resolution vocabulary.

Every effect in the game -- an item's inherent property, a prefix, a suffix,
a monster's natural trait, a room law -- declares WHERE in the pipeline it
acts, WHICH DIRECTION it pushes, and WHAT AUTHORITY backs it.

That is the entire trick. "Absolute rule vs absolute rule" is almost never a
real collision; it is usually two effects acting at different phases, which
means they pass each other without touching. Real collisions are same-phase,
opposite-direction, and they resolve by the lattice in resolution.py.
"""

from __future__ import annotations

from enum import IntEnum


class Phase(IntEnum):
    """Ordered pipeline. Resolution walks these in numeric order."""

    PERMISSION = 10   # May this actor even attempt this?
    TARGETING = 20    # May this target be chosen?
    DELIVERY = 30     # Does the effect arrive?
    APPLICATION = 40  # Does it attach to this creature at all?
    MAGNITUDE = 50    # Resistance, conversion, amplification.
    CONSEQUENCE = 60  # Riders: conditions, movement, restraint, theft.
    PERSISTENCE = 70  # Does it stay attached, or fall off immediately?


class Direction(IntEnum):
    """What an effect does at its phase."""

    GRANT = 1   # Opens something that would otherwise be closed.
    MODIFY = 2  # Scales / converts / redirects. Never opens or closes.
    DENY = 3    # Closes something that would otherwise be open.


class Tier(IntEnum):
    """
    Authority ladder. Higher tier wins same-phase collisions outright.

    SPECIFICATION is reserved for environment law authored into a place at
    creation. Inside the Hollow Star Reliquary, room law is SPECIFICATION and
    therefore outranks anything carried in.
    """

    MUNDANE = 10
    MAGICAL = 20
    ARTIFACT = 30
    BLESSED = 40        # DM047_0 permission tier.
    SPECIFICATION = 50  # Authored into the environment itself.


class Scope(IntEnum):
    """
    Breadth of application. Narrower scope wins ties within the same tier --
    a one-use exception to a room law beats a broad standing rule.
    """

    SINGLE_ACTION = 10
    TARGET = 20
    ENCOUNTER = 30
    ROOM = 40
    FLOOR = 50
    RUN = 60
