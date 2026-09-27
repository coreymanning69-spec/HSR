"""Named-gate registry for sourced champion-identity mechanics.

Engine modules query this registry instead of scattering lore-name string
comparisons (``if identity == "wren"``) through the resolution layer.

To add a third champion:
1.  Add an entry to CHAMPION_RULES keyed by the identity string.
2.  The engine picks it up automatically via ``rules()`` / ``flag()``.
   No other file changes are needed for basic identity routing.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Per-champion rule table.
# Keys are lowercase identity strings as stored in combat rules.
# ---------------------------------------------------------------------------

CHAMPION_RULES: dict[str, dict] = {
    "doran": {
        # ---- weapon / attack routing ----
        "weapon_identity": "doran",          # weapon_attack() mode routing
        "cleaver_flat_damage": "40",          # flat-damage expression for Cleaver mode
        "opportunity_attack_on_miss": True,   # offer OA window on a missed brace
        "lunge_available": True,              # maneuver: Lunging Attack eligible

        # ---- movement ----
        "jump_ceiling": 20,                   # max vertical movement in feet (tactical)

        # ---- defense ----
        "divine_plate": True,                 # divine-tag damage never bypasses plate
        "ac_locked": True,                    # runtime never recalculates Doran's AC

        # ---- initiative ----
        "alert": True,                        # cannot be surprised
        "vision_range": 120,

        # ---- resource defaults ----
        # (Doran's resources are set on the Actor; nothing extra here)
    },

    "wren": {
        # ---- weapon / cast routing ----
        "weapon_identity": "wren",
        "staff_caster": True,                 # spells.cast() staff-caster gate
        "ranged_capable": True,               # can use ranged maneuver modes

        # ---- saves ----
        "mental_save_advantage": True,        # magical saves have advantage

        # ---- conditions ----
        "mind_lock_immune": True,             # cannot receive MIND_LOCK condition
        "unshackled_host": True,              # host-override immunity

        # ---- view / UI ----
        "flight_arena": True,                 # view_model renders 3-D flight arena

        # ---- initiative ----
        "alert": True,
        "vision_range": 120,

        # ---- resource defaults (set during begin()) ----
        "default_resources": {
            "misty_step_free": 5,
            "simulacrum_cast": 1,
            "staff_charges": 50,
            "unbound_save_conversion": 1,
        },
        "default_anchor": [10, 10, 0],
    },

    # ---- Third-champion template ----
    # "soliera": {
    #     "weapon_identity": "soliera",
    #     ...
    # },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rules(identity: str | None) -> dict:
    """Return the full rules dict for a champion identity.

    Returns an empty dict for NPCs, monsters, or unknown identities so
    callers never need a ``None`` guard.
    """
    if not identity:
        return {}
    return CHAMPION_RULES.get(str(identity).lower(), {})


def flag(identity: str | None, key: str, default: object = False) -> object:
    """Convenience: read a single value from a champion's rules dict.

    >>> flag("wren", "staff_caster")
    True
    >>> flag("goblin", "staff_caster")
    False
    """
    return rules(identity).get(key, default)


def is_champion(identity: str | None) -> bool:
    """Return True if this identity has an authored champion entry."""
    if not identity:
        return False
    return str(identity).lower() in CHAMPION_RULES
