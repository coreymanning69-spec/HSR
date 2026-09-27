---
id: DM041_A
title: "Doran — Machine-Readable Combat Mechanics"
type: reference
subtype: character-sheet-playable
load_priority: maintenance-only-for-doran-source-mechanics
canon: T+TR
verse: Divineverse
timeline: T537-current
beat_range: reference / TR3-SKT
arc: sanctum-next-generation-stewards
era:
  - post-t515
  - tr3-skt
status: hard-canon
authority: authoritative-for-doran-current-combat-mechanics-action-economy-and-standing-rules
updated: 2026-09-06
volatility: slow
arc_scope: storm-kings-thunder
derived_from: null
predecessor_file: DM041_E
successor_file: DM041_A1

scope:
  covers:
    - compact machine-readable Doran combat mechanics
    - current Fighter 20 statistics, caps, actions, modes, senses, equipment IDs, and rule IDs
    - exact source values used to derive DM044_0
  use_case: maintenance authority for Doran mechanics and deterministic DM044_0 rebuilds
  not_for:
    - expanded rule explanation, maneuver prose, equipment provenance, physical audit, or gameplay gates (use DM041_A1)
    - current readiness after departure (use the active live ledger)
    - routine characterization (use DM040_0)
    - live combat or simulation (use DM044_0)

xref_concepts:
  - doran
  - battle-master
  - action-economy
  - helm-vision
  - glare
  - grand-cleave
  - divine-plate
  - tr3-skt

canon_flags:
  - "GENDER LOCK: Doran is male; use he/him pronouns."
  - "STEWARD STATUS LOCK: Doran was accepted at T537.0 as a full Tier-3 Sanctum field Steward, below the settled Tier-2 inner circle."
  - "LEVEL-20 LOCK: Battle Master Fighter 20 by divine uplift, not XP accrual. Campaign XP remains 165,000 and is no longer the advancement basis."
  - "AC LOCK: AC is a flat 25. PLANTED, Dual Wielder, and ring-held haste no longer raise it. Deploying the kite still drops him to 21."
  - "PLANTED LOCK: PLANTED grants no AC at level 20. Its live effect is speed 0 plus immunity to displacement-based forced movement and displacement-based prone."
  - "HELM LOCK: Soliera's T537 remake grants always-on normal sight through magical and nonmagical darkness to 120 feet and supplies a breathable atmosphere while worn, including underwater and volcanic environments; Doran still requires oxygen and can suffocate without the helm or its support; no attunement; not truesight."
  - "GLARE LOCK: Doran's mirror-white armor emits no light; RULE-GLARE is a separate reflected-light house rule and daylight is not sunlight."
  - "RUNTIME LOCK: DM044_0 and DM044_1 load together as the combat/simulation runtime; the active live ledger owns current readiness."
  - "TIER SCALING: The DM045_DS1 Ordinant grows in power alongside the field Stewards rather than being left behind or outgrown. He remains a peer threat by definition."
  - "CLEAVER FINAL LOCK: Ordinary Cleaver attacks are +16, or +14 when choked, and deal 40 fixed damage at 10-foot or 5-foot reach; a critical hit deals 80. Grand Cleave is +19 for 120+4d20 in a 15-foot, 180-degree arc; a critical hit doubles the final total. These values supersede every earlier Cleaver formula."
  - "ENCLOSED COLLATERAL LOCK: Doran may use the Cleaver in human-scale construction at the printed tight-space penalty, but the room pays: the swing also damages struck walls, fixtures, and structure along its adjudicated arc."
  - "STRENGTH RESERVE: Current STR remains 27. STR 28 is banked as a future growth beat and is not a current-sheet value."
  - "KIT PROVENANCE LOCK: Soliera personally remade Doran's current white kit from its earlier Sera/Ember forms. The current armor, kite, helm, and Cleaver route to Soliera's hand; earlier gifts remain historical provenance."
  - "T550.3 CONFIRMATION: Giant Cleaver mass is 208 lb; Grand Cleave tip speed is roughly 1.7 times its ordinary swing; it requires planted sabaton spikes, or the rotation shears topsoil and the force bleeds out."
  - "T550.3 CONFIRMATION: Doran has killed thirty giants; his daggers are primary and permit thirteen attacks in roughly seven seconds. His insight/read is second only to Sera's, which timed her rather than out-speeding her."


purpose: >
  Compact structured authority for Doran's current mechanics. Expanded detail
  lives in DM041_A1; current readiness lives in the active live ledger; DM044_0 and DM044_1 are
  the combat and simulation runtime derived from this owner and DM041_B.
---

# DM041_A — Doran — Machine-Readable Combat Mechanics

```yaml
{
  "schema_version": "dm-combat-source-1",
  "owner": "DM041_A",
  "character": {
    "id": "doran",
    "name": "Doran",
    "role": "sanctum_steward",
    "accepted_at": "T537.0",
    "gender": "male",
    "pronouns": ["he", "him"],
    "ancestry": "human_variant",
    "classes": [{"class": "fighter", "subclass": "battle_master", "level": 20}],
    "effective_campaign_level": 20,
    "campaign_xp": 165000,
    "advancement_basis": "divine_uplift",
    "xp_is_advancement_basis": false
  },
  "routing": {
    "current_state_owner": "DM038_L",
    "expanded_support": "DM041_A1",
    "compact_routine": "DM040_0",
    "derived_combat_runtime": "DM044_0",
    "automatic_combat_load": false
  },
  "stats": {
    "hp_max": 370,
    "hit_dice": "20d10",
    "proficiency_bonus": 6,
    "speed_ft": {"armored": 30, "unarmored": 40, "flight_conversion_max": 20},
    "size": "large",
    "space_ft": 10,
    "initiative": 21,
    "initiative_basis": {"insight": 16, "alert": 5},
    "passive_perception": 20,
    "abilities": {"str": 27, "dex": 16, "con": 18, "int": 16, "wis": 18, "cha": 16},
    "future_growth": {"str_28": "banked_not_current"},
    "saves": {"str": 15, "dex": 4, "con": 11, "int": 10, "wis": 11, "cha": 4},
    "save_proficiencies": ["str", "con", "wis", "int"],
    "skills": {"insight": 16, "athletics": 14, "perception": 10, "survival": 10, "persuasion": 9}
  },
  "defenses": {
    "ac": {"standing": 25, "planted": 25, "both_daggers": 25, "kite_deployed": 21},
    "ac_locked_flat": true,
    "ac_riders_retired": ["planted_plus_2", "dual_wielder_plus_1", "haste_plus_2"],
    "haste_overlay": {"ac_bonus": 0, "speed_multiplier": 2, "dex_save_advantage": true, "restricted_extra_action": true},
    "thermal_immunity": true,
    "armor_emits_light": false,
    "regeneration": {"per_round": 16, "requires_hp_at_least": 1},
    "healing_received": "maximized"
  },
  "senses": {
    "helm_vision": {
      "mode": "normal_sight",
      "range_ft": 120,
      "works_in": ["magical_darkness", "nonmagical_darkness"],
      "always_on": true,
      "attunement_required": false,
      "truesight": false,
      "grantor": "soliera_t537_remake",
      "filters": ["air", "water", "poison"]
    }
  },
  "resources": {
    "superiority_dice": {"maximum": 16, "die": "d12", "save_dc": 22, "recovery": ["short_rest", "long_rest", "one_on_critical_hit_max_once_per_round"]},
    "action_surge": {"maximum": 2, "recovery": "short_rest"},
    "second_wind": {"maximum": 1, "healing": 30, "recovery": "short_rest"},
    "indomitable": {"maximum": 3, "recovery": "long_rest"},
    "relentless": {"initiative_with_zero_superiority_dice_regains": 1}
  },
  "action_economy": {
    "action": ["attack_4", "action_surge", "dodge", "grapple", "shove"],
    "bonus_action": ["read_the_seam", "quick_toss", "two_weapon_dagger", "second_wind", "ring_regeneration"],
    "reaction": ["deft_answer", "riposte", "opportunity_attack"],
    "movement_rider": ["bait_and_switch"],
    "free": ["summon_or_dismiss_either_obsidian_dagger", "ordinary_object_interaction"]
  },
  "attacks": {
    "attacks_per_attack_action": 4,
    "obsidian_dagger": {"attack_bonus": 16, "damage": "1d8+10", "range_ft": [30, 70], "summon_action": "none", "resistance_bypass": true, "measured_edge": true},
    "giant_cleaver": {"attack_bonus": 16, "damage_fixed": 40, "critical_damage_fixed": 80, "reach_ft": 10, "hands": [1, 2], "carry_through": "parts_targets_at_or_below_actual_damage_and_stops_at_first_survivor"},
    "giant_cleaver_enclosed": {"attack_bonus": 14, "damage_fixed": 40, "critical_damage_fixed": 80, "reach_ft": 5, "room_pays": true},
    "grand_cleave": {"attack_bonus": 19, "damage": "120+4d20", "critical": "double_final_total", "arc_degrees": 180, "reach_ft": 15, "medium_unit_capacity": 7, "large_unit_cost": 2, "medium_large_auto_parted": true, "huge_plus": "takes_damage_and_stops_blade", "whole_turn": true, "movement_allowed": false, "bonus_action_allowed": false, "both_hands": true, "reaction_available": true, "ally_safe": false, "action_surge_repeat": false},
    "peak_attacks": {"normal": 13, "ring_hasted": 14, "composition": "attack_4 + action_surge_4 + action_surge_4 + quick_toss_1"}
  },
  "signature_features": {
    "read_the_seam": {"activation": "bonus_action", "check": "insight_plus_16_vs_target_ac", "success_critical_range": "16-20", "ends_when": "target_hits_doran"},
    "deft_answer": {"activation": "reaction_when_creature_misses_doran", "attack": "one_free_dagger_attack", "superiority_die_cost": 0},
    "grand_cleave": {"mode_swap": true, "expanded_rule": "DM041_A1#grand-cleave"}
  },
  "advancement_16_to_20": {
    "basis": "divine_uplift",
    "l16_feat": "resilient_int",
    "l17": ["action_surge_second_use", "indomitable_third_use", "proficiency_bonus_6"],
    "l18": "improved_combat_superiority_d12",
    "l19_uplift": {"type": "across_the_board_ability_boost", "amount": 2, "scope": "all_six_abilities", "replaces_feat": true},
    "l20": "extra_attack_3_fourth_attack",
    "feat_package": ["resilient_wis", "skill_expert", "alert", "dual_wielder", "mobile", "sentinel", "resilient_int"],
    "feat_count": 7
  },
  "reaction_economy": {
    "reactions_per_round": 1,
    "competing_options": ["opportunity_attack_sentinel", "deft_answer", "riposte"],
    "note": "deft_answer and riposte share the on-miss trigger; action economy scaled to 13 attacks while reaction economy stayed flat. Known asymmetry, intentionally unpatched."
  },
  "equipment_ids": ["ITEM-OBSIDIAN-DAGGERS", "ITEM-GIANT-CLEAVER", "ITEM-HELM", "divine_plate", "gauntlet_shield", "deployable_kite", "ring_of_regeneration", "cloak_of_protection"],
  "rule_ids": ["RULE-DAGGER-SUMMONING", "RULE-DAGGER-RESISTANCE-BYPASS", "RULE-DAGGER-WARD-BYPASS", "RULE-GRAND-CLEAVE", "RULE-ENCLOSED-SPACE", "RULE-CLEAVER-HAND-GATE", "RULE-CONFIGURATION-COMPETENCE-GATE", "RULE-DIVINE-PLATE", "RULE-THERMAL-EXEMPTION", "RULE-VISION", "RULE-GLARE"],
  "glare": {"rule_id": "RULE-GLARE", "save_dc": 22, "dc_basis": "wrens_spell_save_dc", "daylight_is_sunlight": false, "armor_emits_light": false, "trigger": "external_bright_light_reflected_by_mirror_white_armor", "wren_route": "DM041_B"},
  "open_gates": ["str_28_growth_beat", "gameplay_discovered_residuals"],
  "retired_gates": ["helm_grantor_resolved_to_soliera_t537_remake", "int_save_seam_closed_by_resilient_int_at_plus_10", "later_mastery_details_resolved_at_fighter_20"]
}
```


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM041_A -->
