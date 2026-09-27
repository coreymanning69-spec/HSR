"""Named gates for sourced identity mechanics.

Generic combat code can ask these predicates instead of scattering lore-name
comparisons through the resolution layer.
"""

from __future__ import annotations


def is_doran(identity: str | None) -> bool:
    return str(identity or "").lower() == "doran"


def is_wren(identity: str | None) -> bool:
    return str(identity or "").lower() == "wren"


def is_tarrasque(identity: str | None) -> bool:
    return str(identity or "").lower() == "tarrasque"
