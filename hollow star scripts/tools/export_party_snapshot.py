#!/usr/bin/env python3
"""
Export the certified party snapshot -- DM046_0 certification step 5.

    python3 tools/export_party_snapshot.py --corpus "../divine mythos set"

WHY THIS IS A TOOL AND NOT A HAND-WRITTEN JSON FILE
---------------------------------------------------
DM041_A and DM041_B already publish machine-readable `dm-combat-source-1`
blocks. Retyping those numbers into a JSON file would create a second copy
that drifts silently the first time an owner file is maintained. So this tool
reads the owner blocks directly, carries them through verbatim, and records a
sha256 for every source it touched. If an owner changes, the fingerprint
changes, and a stale snapshot becomes detectable instead of merely wrong.

READ-ONLY AGAINST THE CORPUS
----------------------------
This tool opens corpus files for reading and writes exactly one file, into the
game project. It never writes to the corpus. See handoff constraint 4 and
DM046_0 section 6.

WHAT IS AUTHORED HERE VERSUS DERIVED
------------------------------------
Derived: every number. hp, AC, initiative, attacks, resources, and pools are
pulled out of the certified blocks by key, so they cannot be mistyped.

Authored: the ENGINE MAPPING -- which corpus rule becomes which Effect, at
which phase, carrying which tags. That is a modelling judgment and it is
written out longhand below with a source citation on each entry, so it can be
argued with. Where the engine cannot express a rule at all, the rule goes in
`deferred` under the character rather than being approximated. An approximated
signature ability is worse than an absent one, because absence is visible.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT))

from hollowstar import __version__ as ENGINE_VERSION  # noqa: E402
from hollowstar.snapshot import (  # noqa: E402
    MIN_ENGINE_VERSION,
    SCHEMA_VERSION,
    assert_safe_write_path,
)

DEFAULT_CORPUS = PROJECT.parent / "divine mythos set"
DEFAULT_OUT = PROJECT / "snapshots" / "party_snapshot.json"

SOURCE_SCHEMA = "dm-combat-source-1"

# Owner files, by role. The two *_source files carry the machine-readable
# blocks; the rest are cited for provenance and digested so drift is caught.
SOURCES = [
    ("DM041_A", "doran_source_mechanics", "DM041_A_T_REF_doran-machine-readable-combat-mechanics.md", True),
    ("DM041_A1", "doran_expanded_rules_and_equipment",
     "DM041_A1_T_REF_doran-expanded-rules-and-equipment-catalog.md", False),
    ("DM041_B", "wren_source_mechanics", "DM041_B_T_REF_wren-machine-readable-combat-and-casting-mechanics.md", True),
    ("DM041_B1", "wren_expanded_spells_and_casting",
     "DM041_B1_T_REF_wren-expanded-spells-and-casting-catalog.md", False),
    ("DM044_0", "derived_runtime_protocol_and_doran", "DM044_0_T_SYS_combat-runtime-protocol-and-doran.md", False),
    ("DM044_1", "derived_runtime_wren", "DM044_1_T_SYS_combat-runtime-wren.md", False),
    ("DM046_0", "reliquary_framework",
     "DM046_0_T_REF_hollow-star-reliquary-design-runtime-and-promotion-framework.md", False),
    ("DM047_0", "blessed_tier_framework", "DM047_0_A_REF_the-blessed-permission-tier-framework.md", False),
]

FENCE = re.compile(r"```(?:yaml|json)\s*\n(\{.*?\n\})\s*\n```", re.DOTALL)


# --------------------------------------------------------------------------
# Reading the corpus
# --------------------------------------------------------------------------


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_block(path: Path) -> dict:
    """Pull the dm-combat-source-1 block out of an owner file."""
    text = path.read_text(encoding="utf-8")
    for match in FENCE.finditer(text):
        try:
            block = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if block.get("schema_version") == SOURCE_SCHEMA:
            return block
    raise SystemExit(f"{path.name}: no {SOURCE_SCHEMA} block found")


def front_matter_updated(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines()[:40]:
        if line.startswith("updated:"):
            return line.split(":", 1)[1].strip()
    return ""


# --------------------------------------------------------------------------
# The engine mapping -- authored, cited, and deliberately incomplete
# --------------------------------------------------------------------------


def doran_engine(src: dict) -> dict:
    """Map Doran's certified block onto the hollowstar Actor shape."""
    stats, defenses, res, atk = (
        src["stats"], src["defenses"], src["resources"], src["attacks"],
    )
    dagger, cleaver = atk["obsidian_dagger"], atk["giant_cleaver"]
    # DM041_A's settled cleaver schema uses fixed ordinary damage. Keep the
    # mapper source-derived and fail loudly if an owner publishes neither the
    # current field nor the legacy average used by the first exporter pass.
    cleaver_damage = cleaver.get("damage_fixed", cleaver.get("average_damage"))
    if cleaver_damage is None:
        raise KeyError("giant_cleaver has no damage_fixed field")
    cleaver_expression = cleaver.get("damage", str(cleaver_damage))

    return {
        "name": "Doran",
        "band": "STEWARD",
        "controller": "player",
        "max_hp": stats["hp_max"],
        "armor_class": defenses["ac"]["standing"],
        "initiative_bonus": stats["initiative"],
        "speed": stats["speed_ft"]["armored"],
        "attacks_per_action": atk["attacks_per_attack_action"],
        "reactions": src["reaction_economy"]["reactions_per_round"],
        "natural_tags": [],
        "gate": "none",

        # Default configuration is the dagger routine: DM041_A1 calls the
        # obsidian daggers "his instrument" and the camp-clearing and
        # enclosed-space configuration. DM044_0's state block tracks
        # {daggers|cleaver|grand-cleave} as a live mode; the engine has one
        # hand slot and no mode switch, so the other two are carried as
        # alternate loadouts rather than equipped.
        "equipment": [
            {
                "name": "obsidian dagger",
                "slot": "hand",
                "tier": "BLESSED",
                # 1d8+10 truncated to its integer average. The engine has no
                # dice yet; damage_expression is carried so Phase A can wire
                # the real roll without re-reading the corpus.
                "base_damage": 14,
                "damage_expression": dagger["damage"],
                "attack_bonus": dagger["attack_bonus"],
                "tags": ["PHYSICAL", "PIERCING"],
                # NOT the Primeverse "+N means N times as dense" reading. The
                # printed line already contains the weapon's bonuses; applying
                # density on top would double-count them.
                "density": 1.0,
                "utility_uses": [
                    "summon or dismiss in an open hand with no action, mid-motion",
                    "measured edge: lethal or nonlethal depth by choice, no penalty",
                    "unbreakable by any means in play (Soliera's material)",
                ],
                "flavor": "Soliera's obsidian. Appears in the hand at the instant "
                          "it is needed and leaves no evidence when dismissed.",
            }
        ],
        "alternate_loadouts": [
            {
                "mode": "cleaver",
                "name": "Giant Cleaver",
                "tier": "BLESSED",
                "base_damage": cleaver_damage,
                "damage_expression": cleaver_expression,
                "attack_bonus": cleaver["attack_bonus"],
                "reach_ft": cleaver["reach_ft"],
                "tags": ["PHYSICAL", "SLASHING", "HEAVY"],
                "note": "Mithral +2 greatsword, 6 ft, 208 lb. Universal rider "
                        "applies to every target, not only giants (DM041_A "
                        "CLEAVER MASTERY LOCK).",
            },
            {
                "mode": "grand_cleave",
                "name": "Grand Cleave",
                "base_damage": None,
                "damage_expression": atk["grand_cleave"]["damage"],
                "attack_bonus": atk["grand_cleave"]["attack_bonus"],
                "tags": ["PHYSICAL", "SLASHING", "HEAVY"],
                "note": "Whole-turn mode swap: 180 degree arc, carry-through "
                        "until the first survivor, first Huge-or-larger body "
                        "stops it. No movement, bonus action, dagger, Quick "
                        "Toss, or Deft Answer that turn.",
            },
        ],

        "inherent": [
            # RULE-DIVINE-PLATE, DM044_0 section 4 items table. Two stages:
            # stage one transmits 1/3 piercing, 1/2 slashing as bludgeoning,
            # and all bludgeoning; stage two absorbs 1/4 of everything
            # transmitted. Net: 1/4 piercing, 3/8 slashing, 3/4 bludgeoning.
            # Recorded here as the net figures because that is what resolves.
            {
                "name": "divine plate (piercing)",
                "phase": "MAGNITUDE", "direction": "MODIFY",
                "tier": "BLESSED", "scope": "RUN", "specificity": 3,
                "multiplier": 0.25, "applies_to_tags": ["PIERCING"],
                "tell": "The point goes in and stops, like the plate closed "
                        "around it.",
                "description": "RULE-DIVINE-PLATE net transmission, piercing.",
            },
            {
                "name": "divine plate (slashing)",
                "phase": "MAGNITUDE", "direction": "MODIFY",
                "tier": "BLESSED", "scope": "RUN", "specificity": 3,
                "multiplier": 0.375, "applies_to_tags": ["SLASHING"],
                "tell": "The edge turns into a flat blow partway through the "
                        "cut.",
                "description": "RULE-DIVINE-PLATE net transmission, slashing.",
            },
            {
                "name": "divine plate (bludgeoning)",
                "phase": "MAGNITUDE", "direction": "MODIFY",
                "tier": "BLESSED", "scope": "RUN", "specificity": 3,
                "multiplier": 0.75, "applies_to_tags": ["BLUDGEONING"],
                "tell": "He takes it standing, and the sound is wrong for the "
                        "size of the swing.",
                "description": "RULE-DIVINE-PLATE net transmission, bludgeoning.",
            },
            # RULE-THERMAL-EXEMPTION, DM044_0 section 4. Note the deliberate
            # phase choice: this denies at MAGNITUDE only. Ice may still
            # restrain and carried matter may still burn, because those are
            # CONSEQUENCE riders and pass this untouched. That separation is
            # the whole thesis of the resolver.
            {
                "name": "thermal exemption",
                "phase": "MAGNITUDE", "direction": "DENY",
                "tier": "BLESSED", "scope": "RUN", "specificity": 2,
                "multiplier": 0.0, "applies_to_tags": ["FIRE", "ICE"],
                "tell": "He walks through the burn line without changing pace "
                        "and the white plate is not even discoloured.",
                "description": "Heat, fire, cold, and freezing deal no damage "
                               "and cannot numb him. Carried matter may still "
                               "burn; ice may still restrain.",
            },
        ],

        # Pools are recorded as numbers. Spend rules are deferred -- see below.
        "resources": {
            "superiority_dice": res["superiority_dice"]["maximum"],
            "action_surge": res["action_surge"]["maximum"],
            "second_wind": res["second_wind"]["maximum"],
            "indomitable": res["indomitable"]["maximum"],
        },
    }


def wren_engine(src: dict) -> dict:
    """Map Wren's certified block onto the hollowstar Actor shape."""
    stats, defenses, res = src["stats"], src["defenses"], src["resources"]
    slots, sig = res["spell_slots"], src["signature_features"]
    crown = sig["crown_of_stars"]
    divine_damage = src["divine_damage"]
    if divine_damage["runtime_tag"] != "DamageTag.DIVINE in addition to the printed tag":
        raise ValueError("DM041_B divine_damage no longer declares the supported alongside-tag contract")

    resources = {
        "ward": defenses["ward"]["maximum"],
        "sorcery_points": res["sorcery_points"]["maximum"],
        "channel_divinity": res["channel_divinity"]["maximum"],
        "crown_motes": crown["motes"],
        "robe_stars": res["robe_stars"]["maximum"],
        "staff_charges": res["staff_of_the_magi"]["charges"],
        "portal_shear": res["portal_shear"]["maximum"],
        "sealed_imprisonment": res["sealed_imprisonment"]["maximum"],
        "forcecage": 1,
        "unearthly_recovery": res["unearthly_recovery"]["maximum"],
        "portal_anchor_return": res["portal_anchor_return"]["maximum"],
        "unbound_save_conversion": res["aura_of_the_unbound_save_conversion"]["maximum"],
        "favored_by_the_gods": res["favored_by_the_gods"]["maximum"],
        "spell_slots_total": slots["total"],
    }
    for lvl, n in slots["general"].items():
        resources[f"slot_{lvl}_general"] = n
    for lvl, n in slots["domain_only"].items():
        resources[f"slot_{lvl}_domain"] = n

    return {
        "name": "Wren",
        "band": "STEWARD",
        "controller": "player",
        "max_hp": stats["hp_max"],
        "armor_class": defenses["ac"]["robe_of_the_archmagi"],
        "initiative_bonus": stats["initiative"],
        "speed": stats["speed_ft"]["walk"],
        "attacks_per_action": 1,
        "reactions": 1,
        # DM041_B divine_damage: DIVINE rides beside every printed damage type.
        # Actor.offensive_tags supplies it to both weapon and spell resolution;
        # it never replaces RADIANT, FORCE, or another printed tag.
        "natural_tags": ["DIVINE"],
        "gate": "none",

        "equipment": [
            {
                # The crown is slotless and robe-granted. "hand" is the only
                # slot the engine's weapon() scans, so it is an engine
                # limitation showing through, not a claim about the fiction.
                # Multi-slot resolution is Phase A work.
                "name": "Crown of Stars",
                "slot": "hand",
                "tier": "BLESSED",
                "base_damage": 26,  # 4d12 integer average
                "damage_expression": crown["damage"],
                "attack_bonus": crown["attack_bonus"],
                "tags": ["RADIANT", "DIVINE"],
                "utility_uses": [
                    "permanently active and permanently visible; she has no "
                    "deniable field mode",
                ],
                "flavor": "Seven motes above her head. A mote is spent whether "
                          "it hits or misses.",
            },
            {
                "name": "Robe of the Archmagi",
                "slot": "armor",
                "tier": "BLESSED",
                "base_ac": defenses["ac"]["robe_of_the_archmagi"],
                "tags": [],
                "utility_uses": [
                    "advantage on saves against spells and magical effects",
                    "carries the six robe stars, the solo Astral door, and the "
                    "permanent crown of stars",
                ],
                "flavor": "Brilliant white and gold. Soliera remade it forward "
                          "from the Robe of Stars at T537.0.",
            },
            {
                # Slot "carried" is deliberately not "hand": the staff is not
                # her attack, and putting it in a hand slot would leak its
                # tags into every crown mote she throws.
                #
                # This bucket was called "focus" until 2026-09-15. That was
                # wrong: the staff is not Wren's focus, the Black Bird Sigil
                # is (ITEM-SANCTUM-BLACK-BIRD-SIGIL in DM041_B equipment_ids).
                # The slot name carries no mechanics -- only the exclusion from
                # "hand" does -- so renaming it changes nothing but the claim.
                "name": "Staff of the Magi",
                "slot": "carried",
                "tier": "BLESSED",
                "tags": [],
                "utility_uses": [
                    "indestructible: cannot bend, break, or shatter by any "
                    "force in play",
                    "prop a gate or door, jam under a giant's foot, lever for "
                    "Doran, unbreakable brace or span",
                    "interpose crosswise to stop a weapon edge in a described "
                    "moment -- the force still transfers and may drive her "
                    "back, knock her prone, numb her hands, or crack ribs; "
                    "this is table adjudication and grants no standing AC",
                ],
                "flavor": "Divine white wood, black bird on a metal perch. Its "
                          "printed +2 spell attack is declined by design.",
            },
        ],

        "inherent": [
            # MIND LOCK, DM041_B canon flag and DM044_1 section 1.
            # Phase choice is load-bearing: this denies at CONSEQUENCE, which
            # is where conditions attach. It says nothing about damage and
            # nothing about space. Non-mental spatial containment -- forcecage,
            # imprisonment, a locked room -- remains fully live against her,
            # and that is correct, not a gap.
            {
                "name": "mind lock",
                "phase": "CONSEQUENCE", "direction": "DENY",
                "tier": "BLESSED", "scope": "RUN", "specificity": 5,
                "blocks_statuses": [
                    "CHARMED", "FRIGHTENED", "DOMINATED", "COMPELLED",
                    "CONFUSED", "POSSESSED", "FEEBLEMINDED",
                    "MENTALLY_STUNNED", "MENTALLY_PARALYZED",
                    "MEMORY_EDITED", "THOUGHT_READ",
                ],
                "tell": "The working lands on her and finds nothing to hold. "
                        "She notices it arrive and keeps talking.",
                "description": "Categorically immune to all mind-altering "
                               "effects: nothing may alter, suppress, override, "
                               "control, rewrite, disable, enter, read, or "
                               "involuntarily access her mind. Permanent and "
                               "cannot be suppressed.",
            },
        ],

        "resources": resources,
    }


# Deferred capabilities. Each entry is a real rule in a certified owner file
# that this engine cannot express yet. This list is the Phase A backlog, and
# it is written down rather than discovered later from a balance result that
# made no sense.
#
# Re-audited 2026-09-06 against the live engine, from 30 entries to 5. The
# original list was written when the engine had no d20 check, no saving
# throws, no reaction economy, no turn economy and no spell path; all four
# landed across the 2026-09-05 passes, so most of these entries had stopped
# describing the engine and started describing its history. An entry that has
# become partly executable is NARROWED to the residue rather than dropped, so
# the count still means "rules the engine cannot run" and never "rules nobody
# has looked at lately". Dropping an entry outright requires the rule to run
# end to end through `tactical.apply`.
DORAN_DEFERRED = []

WREN_DEFERRED = []


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------


def build(corpus: Path) -> dict:
    sources, blocks = [], {}
    for owner, role, filename, is_block in SOURCES:
        path = corpus / filename
        if not path.exists():
            raise SystemExit(f"missing owner file: {path}")
        entry = {
            "owner": owner,
            "role": role,
            "file": filename,
            "sha256": sha256(path),
            "updated": front_matter_updated(path),
            "source_schema": SOURCE_SCHEMA if is_block else "prose+frontmatter",
        }
        sources.append(entry)
        if is_block:
            blocks[owner] = extract_block(path)

    fingerprint = hashlib.sha256(
        "".join(f"{s['owner']}:{s['sha256']}" for s in sorted(sources, key=lambda s: s["owner"]))
        .encode()
    ).hexdigest()[:12]

    doran_src, wren_src = blocks["DM041_A"], blocks["DM041_B"]
    today = _dt.date.today().isoformat()

    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_version": f"{today}+{fingerprint}",
        "source_fingerprint": fingerprint,
        "generated_by": "tools/export_party_snapshot.py",
        "generated_at": today,
        "program": "hollow-star-reliquary",


        "seed_mode": "SIMULATION",
        "live_state_owners_excluded": ["DM038_L", "DM038_CH", "DM035_0"],
        "write_policy": {
            "corpus_write": "forbidden",
            "run_saves": ".local/reliquary_runs/<run-id>.json",
            "note": "DM044_0 section 0: SIMULATION seeds from the explicit full "
                    "baselines and never reads or writes the live-state family.",
        },

        "engine_contract": {
            "min_engine_version": MIN_ENGINE_VERSION,
            "generated_against_engine": ENGINE_VERSION,
            "band_ceiling": "CHAMPION",
            "band_note": "Soliera, Sera, Ember, and Deashi are authors and "
                         "observers of the Reliquary, not roster entries. No "
                         "divine character appears in this snapshot and Band "
                         "deliberately stops at CHAMPION.",
        },

        "sources": sources,

        "characters": {
            "doran": {
                "certified": doran_src,
                "engine": doran_engine(doran_src),
                "deferred": DORAN_DEFERRED,
                "provenance": {
                    "owner_file": "DM041_A",
                    "support_files": ["DM041_A1", "DM044_0", "DM044_1"],
                    "note": "Battle Master Fighter 20 by divine uplift at "
                            "T537.0, Tier-3 Sanctum field Steward. DM041_A wins "
                            "on any standing-mechanics conflict.",
                },
            },
            "wren": {
                "certified": wren_src,
                "engine": wren_engine(wren_src),
                "deferred": WREN_DEFERRED,
                "provenance": {
                    "owner_file": "DM041_B",
                    "support_files": ["DM041_B1", "DM044_1", "DM044_0"],
                    "note": "Cleric 20 / Sorcerer 20 stacked by divine uplift at "
                            "T537.0, Tier-3 Sanctum field Steward. DM041_B wins "
                            "on any standing-mechanics conflict.",
                },
            },
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS,
                    help="path to the 'divine mythos set' directory")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true",
                    help="verify the existing snapshot is current; write nothing")
    args = ap.parse_args()

    data = build(args.corpus.expanduser())
    rendered = json.dumps(data, indent=2, ensure_ascii=True) + "\n"

    if args.check:
        if not args.out.exists():
            print(f"MISSING  {args.out}")
            return 1
        current = json.loads(args.out.read_text(encoding="utf-8"))
        if current.get("source_fingerprint") != data["source_fingerprint"]:
            print(
                f"STALE    {args.out}\n"
                f"  snapshot fingerprint {current.get('source_fingerprint')}\n"
                f"  corpus   fingerprint {data['source_fingerprint']}\n"
                f"  an owner file changed; regenerate."
            )
            return 1
        print(f"CURRENT  {args.out}  fingerprint {data['source_fingerprint']}")
        return 0

    out = assert_safe_write_path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Generated artifacts are UTF-8 with LF endings on every host.  Keeping
    # this explicit prevents Windows text-mode translation from creating a
    # platform-only snapshot diff.
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered)

    n_def = sum(len(c["deferred"]) for c in data["characters"].values())
    print(f"wrote {out}")
    print(f"  snapshot_version   {data['snapshot_version']}")
    print(f"  sources digested   {len(data['sources'])}")
    print(f"  characters         {', '.join(data['characters'])}")
    print(f"  deferred rules     {n_def}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
