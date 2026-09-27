---
id: DM041_B
title: "Wren — Machine-Readable Combat and Casting Mechanics"
type: reference
subtype: character-sheet-playable
load_priority: maintenance-only-for-wren-source-mechanics
canon: T+TR
verse: Divineverse
timeline: T537-current
beat_range: reference / TR3-SKT
arc: sanctum-next-generation-stewards
era:
  - post-t531
  - tr3-skt
status: hard-canon
authority: authoritative-for-wren-current-combat-casting-action-economy-and-standing-rules
updated: 2026-09-07
volatility: slow
arc_scope: storm-kings-thunder
derived_from: null
predecessor_file: DM041_A1
successor_file: DM041_B1

scope:
  covers:
    - compact machine-readable Wren combat and casting mechanics
    - current statistics, caps, actions, domains, signatures, senses, equipment IDs, and rule IDs
    - exact source values used to derive DM044_1
  use_case: maintenance authority for Wren mechanics and deterministic DM044_1 rebuilds
  not_for:
    - expanded spells, domain prose, metamagic catalog, gear provenance, doctrine, translation, gameplay gates (DM041_B1/B2)
    - current readiness after departure (active live ledger)
    - routine characterization (DM040_0)
    - live combat or simulation (DM044_0 + DM044_1 together)

xref_concepts:
  - wren
  - cleric-sorcerer-full-stack
  - portal-domain
  - liberation-domain
  - portal-shear
  - nivs-descent
  - glare
  - tr3-skt

canon_flags:
  - "GENDER LOCK: Wren is female; she/her."
  - "STEWARD STATUS LOCK: accepted at T537.0 as a full Tier-3 Sanctum field Steward, below the settled Tier-2 inner circle."
  - "CURRENT BUILD LOCK: Cleric 20 / Sorcerer 20 stacked chassis by divine uplift; campaign XP is no longer the advancement basis."
  - "MIND LOCK: categorically immune to all mind-altering effects; spatial effects still resolve normally."
  - "EDITION LOCK: the 2e or the 5e version of a spell may be used, chosen at the table. Neither edition is the sole authority."
  - "SPELL ACCESS LOCK: every normal published Cleric and Sorcerer/Divine Soul spell is known. Only wish, Karsus-origin magic, and individually NPC-exclusive spells are excluded. Named rows are examples, never a closed list."
  - "NO DIVINE INTERVENTION BUTTON: the Cleric 20 feature stays excluded. Her gods already sent and equipped her; asking them is narrative, not a percentile or a cooldown."
  - "STAFF INTERPOSITION LOCK: the indestructible staff may stop a weapon edge in a described moment, but the force still reaches her. Table adjudication, never standing AC or damage reduction."
  - "KIT PROVENANCE LOCK: Soliera personally remade the current kit; every object chains from its earlier form. Ember is not the maker."
  - "VISIBLE STATEMENT LOCK: Crown of Stars is permanently active, robe-granted, and slotless. No deniable field mode."
  - "PORTAL SHEAR REFLECTION LOCK: Reflective Carapace cannot reflect Portal Shear."
  - "LIBERATION DOMAIN LOCK: Wren's Liberation domain protects agency by ending coercion, imposed restraint, forced movement, and domination in others; its eventual personal dramatic expression remains an intentional open character beat, not an unimplemented mechanical feature."
  - "GLARE ROUTE: daylight is not sunlight; Doran's reflected-light resolution is RULE-GLARE at her DC 22."
  - "RUNTIME LOCK: DM044_0 and DM044_1 load together at combat start; the active live ledger owns current readiness."

purpose: >
  Compact structured authority for Wren's current mechanics. Expanded detail
  lives in DM041_B1; current readiness lives in the active live ledger; DM044_1 is the derived
  runtime for Wren and loads together with DM044_0.
---

# DM041_B — Wren — Machine-Readable Combat and Casting Mechanics

```yaml
{
  "schema_version": "dm-combat-source-1",
  "owner": "DM041_B",
  "character": {"id": "wren", "name": "Wren", "role": "sanctum_steward", "accepted_at": "T537.0", "gender": "female", "pronouns": ["she", "her"], "ancestry": "half_elf", "classes": [{"class": "cleric", "level": 20}, {"class": "sorcerer", "subclass": "divine_soul", "level": 20}], "effective_campaign_level": 20, "campaign_xp": 165000, "advancement_basis": "divine_uplift", "xp_is_advancement_basis": false},
  "routing": {"current_state_owner": "DM038_L", "expanded_support": "DM041_B1", "compact_routine": "DM040_0", "derived_combat_runtime": "DM044_1", "paired_runtime": "DM044_0", "automatic_combat_load": false},
  "stats": {"hp_max": 220, "hit_dice": ["20d8", "20d6"], "proficiency_bonus": 6, "speed_ft": {"walk": 30, "otherworldly_wings_fly": 60}, "initiative": 6, "initiative_basis": {"dex": 1, "alert": 5}, "passive_perception": 19, "spell_save_dc": 22, "spell_attack_bonus": 14, "abilities": {"str": 10, "dex": 13, "con": 16, "int": 16, "wis": 17, "cha": 20}, "saves": {"str": 3, "dex": 10, "con": 12, "int": 12, "wis": 18, "cha": 14}, "save_proficiencies": ["wis", "cha", "con", "dex"], "save_advantage_vs": "spells_and_magical_effects_from_robe_of_the_archmagi", "skills": {"arcana": 9, "history": 9, "investigation": 9, "nature": 9, "perception": 9, "insight": 7, "survival": 9, "persuasion": 11, "stealth": 7}, "skill_proficiencies_retained": true, "tools": ["calligraphers_supplies"], "languages": ["common", "draconic", "elvish", "gnomish", "infernal", "orc", "undercommon"]},
  "defenses": {"ac": {"robe_of_the_archmagi": 18, "with_shield_spell": 23}, "mage_armor_redundant": true, "ward": {"maximum": 75, "damage_types": "all", "overflow_rule": "if_damage_exceeds_remaining_ward_nullify_entire_instance_and_riders_then_set_zero", "recharge": "end_of_combat"}, "mind_altering_immunity": {"permanent": true, "cannot_be_suppressed": true, "scope": "all_effects_that_alter_suppress_override_control_rewrite_disable_enter_read_or_involuntarily_access_mind"}, "spatial_effects_resolve_normally": true, "concentration_save_advantage": true},
  "resources": {
    "sorcery_points": {"maximum": 50, "recovery_short_rest": 4, "recovery_source": "sorcerous_restoration_sorcerer_20"},
    "spell_slots": {"general": {"1": 20, "2": 16, "3": 16, "4": 16, "5": 20, "6": 12, "7": 10, "8": 14, "9": 8}, "domain_only": {"1": 2, "2": 2, "3": 2, "4": 2, "5": 2, "6": 2, "7": 2, "8": 2, "9": 2}, "general_total": 132, "domain_total": 18, "total": 150},
    "channel_divinity": {"maximum": 3, "recovery": "rest"},
    "favored_by_the_gods": {"maximum": 1, "recovery": "rest"},
    "portal_shear": {"maximum": 1, "recovery": "long_rest"},
    "sealed_imprisonment": {"maximum": 1, "recovery": "long_rest"},
    "sigil_force_lane": {"maximum_each": 1, "recovery": "long_rest", "spells": ["wall_of_force", "bigbys_hand", "otilukes_resilient_sphere", "mordenkainens_private_sanctum", "forcecage", "otilukes_freezing_sphere"]},
    "crown_of_stars": {"maximum": 7, "permanently_active": true, "no_slot_required": true},
    "staff_of_the_magi": {"charges": 50, "daily_regain": "4d6+2", "grants_spell_attack_bonus": false},
    "robe_stars": {"maximum": 6, "recharge": "daily_at_dusk"},
    "unearthly_recovery": {"maximum": 1, "recovery": "long_rest", "effect": "bonus_action_below_half_hp_regain_110"},
    "portal_anchor_return": {"maximum": 1, "recovery": "long_rest"},
    "aura_of_the_unbound_save_conversion": {"maximum": 1, "recovery": "long_rest"}
  },
  "spell_access": {"normal_published": ["cleric", "sorcerer", "divine_soul"], "known": "every_normal_published_spell", "named_rows": "examples_not_closed_list"},
  "settled_added_spells": {"3": ["fireball"], "7": ["simulacrum"], "8": ["demiplane", "sunburst", "feeblemind"]},
  "ninth_level_spells": ["gate", "time_stop", "mass_heal", "true_resurrection", "meteor_swarm"],
  "ninth_level_spell_list_role": "examples only; spell_access governs the complete list",
  "excluded_spells": {"wish": "excluded", "karsus_origin_magic": "excluded", "individually_npc_exclusive_spells": "excluded"},
  "action_economy": {"action": ["cast_spell", "channel_divinity", "robe_star", "astral_entry_or_return", "staff_of_the_magi", "dodge", "help", "use_object"], "bonus_action": ["quickened_spell", "crown_of_stars_mote", "healing_word", "spiritual_weapon", "font_of_magic", "portal_misty_step", "unearthly_recovery"], "reaction": ["shield", "absorb_elements", "counterspell", "war_caster_opportunity_spell", "staff_spell_absorption", "portal_anchor_return", "aura_of_the_unbound_save_conversion"], "free": ["manifest_or_dismiss_otherworldly_wings"], "movement": ["walk_30", "fly_60_with_otherworldly_wings"]},
  "casting": {"ability": "charisma", "cleric_list": "fully_live_without_preparation", "edition_permission": "2e_or_5e_version_of_any_spell_may_be_used_chosen_at_the_table", "material_components_required": false, "costly_components_required": false, "focus_required": false, "silent_still": {"elective": true, "cost": 0, "source": "left_ring", "excluded_from_turn_tax": true}, "personal_concentration_max": 1, "ring_concentration": {"independent": true, "default_spell": "haste_on_doran", "swap": "long_rest_or_explicit_safe_equivalent", "damage_checks": false, "printed_duration_applies": false}, "doran_only_healing_maximization": true},
  "domains": {
    "portal": {
      "channel_divinity": "dimensional_shift",
      "dimensional_shift": {"activation": "action", "targets": "self_plus_6_willing_within_30ft", "destination": "any_visible_point_or_any_place_physically_stood_within_24h", "range_miles": 1, "concentration": false, "provokes": false},
      "l14_unbarred": {"teleport_cannot_be_blocked_below_spell_level": 9, "detects_teleport_wards": true, "free_misty_step_per_long_rest": 5, "misty_step_activation": "bonus_action"},
      "l17_the_open_door": {"anchor": {"set": "end_of_long_rest_at_current_location", "window_hours": 24, "activation": "reaction", "usable_while": ["restrained", "grappled", "incapacitated", "at_0_hp"], "requires": "wren_alive", "carries": "self_plus_willing_within_30ft", "uses_per_long_rest": 1}, "toll": {"radius_ft": 60, "save": "cha_vs_spell_save_dc", "on_fail": "teleport_fails_and_is_wasted", "applies_to": "entry_and_exit", "wren_chooses_exemptions": true}},
      "signature": "portal_shear"
    },
    "liberation": {"channel_divinity": "indomitable_spirit", "indomitable_spirit": {"activation": "action", "radius_ft": 30, "ends_and_blocks": ["charmed", "frightened", "paralyzed", "restrained", "stunned", "grappled", "incapacitated", "petrified"], "duration_minutes": 1, "forced_movement_fails": true}, "l14_unshackled_host": {"freedom_of_movement_aura_ft": 30, "concentration": false, "slot_cost": 0, "ally_at_zero_hp_reaction_move": "full_speed_without_provoking"}, "l17_aura_of_the_unbound": {"radius_ft": 30, "allies_gain": "advantage_on_all_saving_throws", "save_conversion": {"activation": "reaction", "effect": "ally_failed_save_becomes_success", "includes_save_or_die": true, "uses_per_long_rest": 1}}}
  },
  "signature_features": {
    "portal_shear": {"nickname": "the_eraser", "activation": "entire_turn", "range_ft": 50, "distant_range_ft": 100, "line_radius_cm": 1, "save": "con_dc_22_binary", "damage": "8d20_force_teleportation_per_crossed_target", "pierces_intervening_matter": true, "threshold_death": {"damage_fraction_current_hp": 0.65, "flat_con_dc": 25, "modifiers": false}, "level_10_capstone": {"status": "specified_not_acquired_not_runtime_available", "shape": "one_4cm_by_200ft_wave", "save": "one_con_dc_22_zero_on_success", "damage_on_failure": 960, "metamagics": ["split_ray", "twin", "enhanced", "maximize", "empower", "extend", "careful", "distant"], "cost": "40_sp_plus_the_days_portal_shear", "ordinary_portal_shear_recovery": "long_rest"}},
    "portal_slash": {"nickname": "slash", "lane": "own_top_level_lane_not_a_shear_mode_and_not_the_capstone; supersedes nanowire_whip", "status": "specified_not_acquired_not_runtime_available", "learn_gate": "narrative_unlock_no_level_or_mechanical_trigger", "activation": "action", "shape": "facing_dependent_cone_horizontal_whip_arc", "geometry": {"ranks_in_squares": [2, 3, 4, 5, 6, 7, 8], "total_squares": 35, "widest_at": "far_end", "narrow_at_origin": true}, "cut_height": "uncontrolled", "architecture_capable": true, "save": "dex_dc_22_binary", "damage": "8d20_force_teleportation_per_crossed_target", "inherits_from_base": ["pierces_intervening_matter", "teleportation_immunity_or_resistance_is_the_only_block", "threshold_death_check_65pct_current_hp_flat_con_dc_25"], "cost": "spends_the_days_portal_shear"},
    "nivs_descent": {"spell_level": 5, "activation": "full_turn", "control_radius_ft": 20, "wave_radius_ft": 30, "damage_or_healing": "8d6_elemental"},
    "crown_of_stars": {"permanently_active": true, "motes": 7, "activation": "bonus_action", "attack_bonus": 14, "damage": "4d12_radiant", "mote_spent_hit_or_miss": true, "narrative_note": "visible_always_showy"},
    "simulacrum": {
      "spell_level": 7,
      "activation": "entire_turn",
      "uses_per_long_rest": 1,
      "copy": "autonomous_exact_wren_except_hp_spell_slots_and_sorcery_points_halve_round_down_per_tier_each_generation",
      "initiative": "independent",
      "reaction_economy": "independent",
      "creation_state": "copies_current_ward_channel_divinity_portal_shear_and_working_gear_resources; born_flying_if_wren_is_flying",
      "sustained_per_body": 1,
      "global_active_copy_cap": 4,
      "persists_through_long_rest": true,
      "survives_parent_death": true,
      "death_awareness": "original_wren_feels_each_descendant_copy_death_without_last_thoughts_moments_cause_replay_sensory_transfer_or_forensic_detail",
      "cascade": {"generation_1": {"hp": 110, "slots_total": 75, "sorcery_points": 25}, "generation_2": {"hp": 55, "slots_total": 32, "sorcery_points": 12}, "generation_3": {"hp": 27, "slots_total": 14, "sorcery_points": 6}, "generation_4": {"hp": 13, "slots_total": 5, "sorcery_points": 3, "seventh_level_slots": 0}}
    }
  },
  "divine_damage": {"scope": "every_spell_and_every_attack", "mode": "rides_alongside_printed_type_never_replaces_it", "cleric_source": "embers_ability", "divine_soul_source": "soliera_herself", "runtime_tag": "DamageTag.DIVINE in addition to the printed tag", "theology_route": ["DM042_0", "DM047_0"]},
  "metamagic": {"turn_tax": {"one": "sorcery_points_only", "two": "sorcery_points_plus_bonus_action", "three_or_more": "sorcery_points_plus_entire_turn_no_movement_bonus_action_or_reaction"}, "quicken": {"cost": 4, "maximum_per_round": 1, "exclusive": true, "permits_action_and_bonus_action_leveled_spells": true}, "catalog_owner": "DM041_B1"},
  "feats": ["war_caster", "skilled", "alert", "resilient_dex"],
  "advancement_16_to_20": {"basis": "divine_uplift", "cleric_18": "channel_divinity_third_use", "cleric_20": "divine_intervention_improved_excluded_by_canon", "cleric_14_and_17": ["portal_unbarred", "portal_the_open_door", "liberation_unshackled_host", "liberation_aura_of_the_unbound"], "sorcerer_18": "unearthly_recovery", "sorcerer_20": "sorcerous_restoration", "sorcerer_16_and_19_feats": ["alert", "resilient_dex"], "new_tier": "ninth_level_slots_and_spells"},
  "equipment_ids": ["ITEM-SANCTUM-BLACK-BIRD-SIGIL", "ITEM-RING-OF-CONCENTRATION", "ITEM-ROBE-OF-THE-ARCHMAGI", "ITEM-STAFF-OF-THE-MAGI", "elective_silent_still_ring", "weave_sight_glasses", "cloak_of_protection"],
  "retired_equipment_ids": ["ITEM-ROBE-OF-STARS", "wand_of_fireball"],
  "items": {
    "robe_of_the_archmagi": {"color": "brilliant_white_and_gold", "ac_formula": "15_plus_dex_when_unarmored", "spell_save_dc_bonus": 2, "spell_attack_bonus": 2, "save_advantage_vs_spells_and_magical_effects": true, "absorbed_from_robe_of_stars": ["six_stars_per_day_at_seven_darts", "solo_astral_entry_and_return", "plus_1_all_saves"], "also_grants": "crown_of_stars_permanently_active"},
    "staff_of_the_magi": {"material": "divine_white_wood", "finial": "black_bird_on_a_metal_perch", "indestructible": true, "cannot_bend_break_or_shatter": true, "sole_exception": "retributive_strike_by_wren_choice", "charges": 50, "daily_regain": "4d6+2", "spell_attack_bonus_granted": 0, "spell_attack_bonus_declined_by_design": true, "spell_absorption": {"activation": "reaction", "scope": "spell_targeting_only_wren", "gains_charges": true}, "retributive_strike": {"damage": "16d6", "radius_ft": 30, "destroys_staff": true, "requires_wren_intent": true}, "physical_utility_and_interposition": "prop, jam, lever, brace, interpose; table adjudication -- prose owner DM041_B2 / DM044_1"}
  },
  "rule_ids": ["RULE-WREN-TURN-TAX", "RULE-WREN-QUICKEN", "RULE-WREN-SIMULACRUM", "RULE-NIVS-DESCENT", "RULE-PORTAL-SHEAR", "RULE-PORTAL-SLASH", "RULE-WREN-DIVINE-DAMAGE", "RULE-IRON-FLASK-DIVINATION", "RULE-GLARE", "RULE-WREN-EDITION-CHOICE", "RULE-PORTAL-TOLL", "RULE-UNBOUND-AURA", "THREAD-SOLIERA-TELEPORT"],
  "senses": {"weave_sight": {"extended_darkvision": true, "truesight": false, "magical_darkness": "reads_shapes_but_does_not_see_normally", "invisibility": "shape_location_and_count_without_identity"}},
  "glare_route": {"rule_owner": "DM041_A", "rule_id": "RULE-GLARE", "daylight_is_sunlight": false, "doran_armor_emits_light": false, "save_dc": 22, "dc_basis": "wrens_spell_save_dc", "interaction": "daylight_or_other_bright_light_can_trigger_reflected_glare_only_under_RULE_GLARE"},
  "pair_doctrine": {"doran_holds": true, "wren_leaves_and_is_hurt": true, "simulacrum": "second_soft_body_and_extraction_asset_with_its_own_reactions", "wren_is_dorans_exit": "gate_demiplane_time_stop_dimensional_shift_and_staff_plane_shift_answer_the_no_exit_lane_only_as_a_pair"},
  "open_gates": ["upper_tier_spell_grants", "gameplay_discovered_residuals"],
  "retired_gates": ["dimensional_shift_first_use_now_defined", "indomitable_spirit_first_use_now_defined"]
}
```


<!-- CORPUS REVISION: 9.0 -->
<!-- END DM041_B -->
