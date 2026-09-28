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

        # ---- capability tags (tactical.capable) ----
        # Each names one authored Doran rule so the combat engine asks
        # "can this actor brace?" instead of "is this Doran?".
        "dagger_mode": True,                  # weapon/dagger/cleaver mode routing + dagger visuals
        "dagger_bypass": True,                # dagger hits bypass resistance (not Cleaver)
        "dagger_structure_cut": True,         # daggers may cut force-construct structures
        "read_the_seam": True,                # Read the Seam feature; crit on 16 vs read target
        "stances": True,                      # planted / mobile / kite stances
        "steward_maneuvers": True,            # champion action rows in the action menu
        "innate_bonus_attack": True,          # bonus-action attack without a resource pool
        "parry": True,                        # reaction: Parry a hit (superiority die)
        "riposte": True,                      # reaction: Riposte / Deft Answer on a miss
        "brace": True,                        # reaction: Brace against a mover
        "entry_reaction": True,               # reacts to a foe entering reach
        "ignores_disengage": True,            # opportunity attacks ignore Disengage
        "opportunity_halts_movement": True,   # a landed opportunity attack stops the mover
        "critical_superiority_recovery": True,  # a crit returns a superiority die once a round
        "superiority_round_recovery": True,   # an empty superiority pool refills to 1
        "indomitable": True,                  # reroll a failed saving throw
        "maximized_healing": True,            # healing received is maximized
        "regeneration_ring": True,            # ring_heal bonus action
        "fixed_potion_heal": "30",            # potions heal a flat 30
        "daylight_glare": True,               # plate glare in daylight within 60 ft

        # ---- resource defaults ----
        # (Doran's resources are set on the Actor; nothing extra here)
    },

    "wren": {
        # ---- weapon / cast routing ----
        "weapon_identity": "wren",
        "staff_caster": True,                 # spells.cast() staff-caster gate
        "ranged_capable": True,               # can use ranged maneuver modes
        "innate_bonus_attack": True,          # bonus-action attack without a resource pool
        "shield_reaction": True,              # reaction: Shield against a hit
        "staff_weapon": True,                 # Staff of the Magi weapon routing (crown motes)
        "bonus_attack_menu": True,            # Attack offered on a bonus action alone
        "staff_utility": True,                # Staff of the Magi physical utility lane
        "spell_absorption": True,             # staff absorbs incoming spells
        "retributive_strike": True,           # staff retributive strike
        "unbound_save_conversion": True,      # converts an ally's failed save
        "flight": True,                       # Otherworldly Wings: fly / land / ascend
        "unearthly_recovery": True,           # bonus-action heal below half HP
        "ward_reset": True,                   # ward restored to 75 when a fight ends

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
