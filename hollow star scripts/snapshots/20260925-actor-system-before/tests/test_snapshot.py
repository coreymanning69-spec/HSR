"""
Certification step 5 tests: the party snapshot contract.

Two things are being defended here.

First, the snapshot must fail CLOSED. A wrong schema, a too-old engine, a LIVE
seed mode, or a citation of the volatile state family all have to raise rather
than load a plausible-looking party. A silently-degraded import is worse than
a crash, because the numbers that come out of it look certified.

Second, `verified` must stay honest. It answers "did these numbers come from a
certified authority", and nothing else. The separate fidelity/deferred pair
carries "and how much of that sheet does the engine actually run", which for
both Stewards today is "not all of it, and here is the list".

Run: python3 tests/test_snapshot.py
"""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.actors import Band
from hollowstar.effects import Effect
from hollowstar.loader import load_items, load_roster, unverified
from hollowstar.phases import Direction, Phase, Scope, Tier
from hollowstar.resolution import resolve_attack
from hollowstar.snapshot import (
    CorpusWriteRefused,
    SnapshotError,
    assert_safe_write_path,
    import_party,
    load_snapshot,
    merge_into_roster,
    validate,
)
from hollowstar.tags import DamageTag

SNAP = json.loads(
    (Path(__file__).resolve().parents[1] / "snapshots" / "party_snapshot.json")
    .read_text(encoding="utf-8")
)


def _mutated(**changes):
    d = copy.deepcopy(SNAP)
    d.update(changes)
    return d


# --------------------------------------------------------------------------
# Fail-closed validation
# --------------------------------------------------------------------------


def test_shipped_snapshot_validates():
    validate(SNAP)


def test_schema_mismatch_is_fatal():
    try:
        validate(_mutated(schema_version="hollow-star-party-snapshot-99"))
    except SnapshotError:
        return
    raise AssertionError("a schema mismatch must not load")


def test_live_seed_mode_is_refused():
    """DM044_0 LIVE seeding reads DM038_L/LU directly. Not this engine's job."""
    try:
        validate(_mutated(seed_mode="LIVE"))
    except SnapshotError:
        return
    raise AssertionError("a LIVE-mode snapshot must be refused")


def test_citing_live_state_owner_is_refused():
    """A simulation must seed from full baselines, never campaign readiness."""
    d = copy.deepcopy(SNAP)
    d["sources"].append({
        "owner": "DM038_L", "role": "current_readiness", "file": "x.md",
        "sha256": "deadbeef", "source_schema": "prose+frontmatter",
    })
    try:
        validate(d)
    except SnapshotError:
        return
    raise AssertionError("citing the live-state family must be refused")


def test_future_engine_requirement_is_refused():
    d = copy.deepcopy(SNAP)
    d["engine_contract"]["min_engine_version"] = "99.0.0"
    try:
        validate(d)
    except SnapshotError:
        return
    raise AssertionError("a snapshot needing a newer engine must not load")


def test_sourceless_snapshot_is_refused():
    try:
        validate(_mutated(sources=[]))
    except SnapshotError:
        return
    raise AssertionError("an uncited snapshot must not be trusted")


def test_missing_snapshot_file_is_fatal():
    try:
        load_snapshot(Path("/nonexistent/party_snapshot.json"))
    except SnapshotError:
        return
    raise AssertionError("a missing snapshot must raise, not return empty")


# --------------------------------------------------------------------------
# The corpus write guard
# --------------------------------------------------------------------------


def test_corpus_write_is_refused():
    """Handoff constraint 4 / DM046_0 section 6. Never soften this."""
    for bad in (
        "/tmp/Soliera and Sera v8/divine mythos set/DM046_0.md",
        "/tmp/x/project context/TR3_SKT_ARCHIVE/thing.md",
    ):
        try:
            assert_safe_write_path(bad)
        except CorpusWriteRefused:
            continue
        raise AssertionError(f"write into the corpus was allowed: {bad}")


def test_run_save_path_is_allowed():
    assert_safe_write_path(".local/reliquary_runs/run-001.json")


# --------------------------------------------------------------------------
# Import produces certified actors
# --------------------------------------------------------------------------


def test_import_flips_stewards_to_certified():
    roster, report = import_party()
    assert set(roster) == {"Doran", "Wren"}
    for actor in roster.values():
        assert actor.provenance.verified is True
        assert actor.provenance.snapshot_version == SNAP["snapshot_version"]
        assert actor.band is Band.STEWARD
        assert actor.controller == "player"
    assert report.source_fingerprint == SNAP["source_fingerprint"]


def test_import_preserves_certified_dnd_sheet_values():
    roster, _ = import_party()
    assert roster["Doran"].ability_scores == {
        "STR": 27, "DEX": 16, "CON": 18, "INT": 16, "WIS": 18, "CHA": 16
    }
    assert roster["Doran"].proficiency_bonus == 6
    assert roster["Doran"].skill_bonuses["athletics"] == 14
    assert roster["Wren"].ability_scores == {
        "STR": 10, "DEX": 13, "CON": 16, "INT": 16, "WIS": 17, "CHA": 20
    }


def test_certified_numbers_match_the_owner_files():
    """Spot-check against DM041_A / DM041_B rather than against ourselves."""
    roster, _ = import_party()
    doran, wren = roster["Doran"], roster["Wren"]

    assert (doran.max_hp, doran.armor_class) == (370, 25)
    assert doran.initiative_bonus == 21
    assert doran.attacks_per_action == 4
    assert doran.resources["superiority_dice"] == 16
    assert doran.resources["action_surge"] == 2

    assert (wren.max_hp, wren.armor_class) == (220, 18)
    assert wren.resources["ward"] == 75
    assert wren.resources["sorcery_points"] == 50
    assert wren.resources["spell_slots_total"] == 150
    assert DamageTag.DIVINE in wren.natural_tags
    assert {DamageTag.RADIANT, DamageTag.DIVINE}.issubset(wren.weapon().tags)
    # 132 general + 18 domain, per DM041_B and DM044_1.
    general = sum(v for k, v in wren.resources.items() if k.endswith("_general"))
    domain = sum(v for k, v in wren.resources.items() if k.endswith("_domain"))
    assert (general, domain) == (132, 18)


def test_engine_values_are_derived_not_retyped():
    """
    Every mapped number must be traceable to the certified block carried in
    the same file. If someone hand-edits the engine block, this catches it.
    """
    for cid, key in (("doran", "hp_max"), ("wren", "hp_max")):
        entry = SNAP["characters"][cid]
        assert entry["engine"]["max_hp"] == entry["certified"]["stats"][key]

    d = SNAP["characters"]["doran"]
    assert d["engine"]["armor_class"] == d["certified"]["defenses"]["ac"]["standing"]
    w = SNAP["characters"]["wren"]
    assert w["engine"]["resources"]["ward"] == w["certified"]["defenses"]["ward"]["maximum"]


def test_fidelity_is_reported_separately_from_verified():
    """Certified numbers plus unimplemented behaviour must be visible as such."""
    roster, report = import_party()
    assert all(actor.provenance.verified is True for actor in roster.values())
    assert roster["Doran"].provenance.fidelity == "complete"
    assert not roster["Doran"].provenance.deferred
    assert roster["Wren"].provenance.fidelity == "complete"
    assert not roster["Wren"].provenance.deferred
    assert all("[CERTIFIED" in actor.describe() for actor in roster.values())
    assert not report.deferred


def test_no_divine_characters_in_the_snapshot():
    """Soliera, Sera, Ember, and Deashi are authors, not combatants."""
    roster, _ = import_party()
    forbidden = {"soliera", "sera", "ember", "deashi"}
    assert not forbidden & {n.lower() for n in roster}
    for actor in roster.values():
        assert actor.band <= Band.CHAMPION


def test_merge_promotes_stubs_and_leaves_the_rest_alone():
    """
    The DM046_0 step-5 milestone, stated as an assertion: after the merge,
    loader.unverified() has nothing left to report. Nothing in the roster is
    a placeholder any more.
    """
    base = load_roster()
    assert set(unverified(base)) == {"Doran", "Wren"}
    assert base["Doran"].max_hp != 370, "the JSON roster is still a stub"

    merged, _ = merge_into_roster(base)
    assert unverified(merged) == [], "step 5 clears the placeholder audit"
    assert merged["Doran"].max_hp == 370

    # Generated content is untouched and keeps its own identity. It was never
    # a placeholder -- procedural residents have no upstream owner file to be
    # pending on -- so the merge must not rewrite it in either direction.
    for name in ("Townsperson", "Wailing Spirit"):
        assert merged[name] is base[name]


# --------------------------------------------------------------------------
# The two resolver extensions the snapshot needed
# --------------------------------------------------------------------------


def test_divine_plate_discriminates_by_damage_subtype():
    """One suit of armour, three transmission rates, one MAGNITUDE phase."""
    roster, _ = import_party()
    doran = roster["Doran"]
    items = load_items()

    def hit_with(tag: DamageTag, base: int) -> int:
        attacker = copy.deepcopy(roster["Wren"])
        weapon = copy.deepcopy(items["longsword"])
        weapon.base_damage = base
        weapon.tags = {tag}
        attacker.equipment = [weapon]
        target = copy.deepcopy(doran)
        return resolve_attack(attacker, target).damage

    assert hit_with(DamageTag.PIERCING, 100) == 25      # 1/4
    assert hit_with(DamageTag.SLASHING, 100) == 37      # 3/8, truncated
    assert hit_with(DamageTag.BLUDGEONING, 100) == 75   # 3/4
    # A tag the plate says nothing about passes through at full value.
    assert hit_with(DamageTag.PSYCHIC, 100) == 100


def test_thermal_exemption_denies_damage_but_not_riders():
    """
    The thesis, in one test. Fire deals him nothing at MAGNITUDE, and the
    restraint riding the same attack still lands at CONSEQUENCE, because
    those are different phases and never touch.
    """
    roster, _ = import_party()
    doran = copy.deepcopy(roster["Doran"])
    items = load_items()

    attacker = copy.deepcopy(roster["Wren"])
    weapon = copy.deepcopy(items["longsword"])
    weapon.base_damage = 200
    weapon.tags = {DamageTag.FIRE}
    weapon.inherent = [
        Effect(
            name="cinder-lock",
            phase=Phase.CONSEQUENCE,
            direction=Direction.GRANT,
            inflicts_status="RESTRAINED",
            status_duration=2,
        )
    ]
    attacker.equipment = [weapon]

    res = resolve_attack(attacker, doran)
    assert res.damage == 0, "thermal exemption denies at MAGNITUDE"
    assert "RESTRAINED" in res.statuses_applied, "riders live at CONSEQUENCE"
    assert res.succeeded, "a zero-damage attack is not a blocked attack"


def test_mind_lock_refuses_mental_conditions_only():
    """
    Wren is categorically immune to mind-altering effects and completely
    subject to spatial containment. Condition immunity is not damage immunity
    and it is not universal immunity.
    """
    roster, _ = import_party()
    items = load_items()

    def strike(status: str):
        attacker = copy.deepcopy(roster["Doran"])
        weapon = copy.deepcopy(items["longsword"])
        weapon.inherent = [
            Effect(
                name=f"rider:{status}",
                phase=Phase.CONSEQUENCE,
                direction=Direction.GRANT,
                tier=Tier.ARTIFACT,
                scope=Scope.TARGET,
                inflicts_status=status,
                status_duration=3,
            )
        ]
        attacker.equipment = [weapon]
        return resolve_attack(attacker, copy.deepcopy(roster["Wren"]))

    refused = strike("DOMINATED")
    assert "DOMINATED" in refused.statuses_refused
    assert "DOMINATED" not in refused.statuses_applied
    assert refused.tells_revealed, "a refusal the party can see must have a tell"

    landed = strike("RESTRAINED")
    assert "RESTRAINED" in landed.statuses_applied, "spatial effects stay live"
    assert landed.damage > 0, "a condition immunity is not a damage immunity"


def test_blessed_tier_loses_to_specification():
    """
    Room law inside the Reliquary is SPECIFICATION and outranks anything
    carried in, including Blessed-tier divine kit. This is what makes the
    dungeon able to threaten level-20 Stewards without confiscating them.
    """
    roster, _ = import_party()
    doran = copy.deepcopy(roster["Doran"])
    items = load_items()

    attacker = copy.deepcopy(roster["Wren"])
    weapon = copy.deepcopy(items["longsword"])
    weapon.base_damage = 100
    weapon.tags = {DamageTag.FIRE}
    attacker.equipment = [weapon]

    room_law = [
        Effect(
            name="the reliquary permits the burn",
            phase=Phase.MAGNITUDE,
            direction=Direction.GRANT,
            tier=Tier.SPECIFICATION,
            scope=Scope.ROOM,
            multiplier=1.0,
            applies_to_tags={DamageTag.FIRE},
            tell="The air here holds heat the way water holds a stone.",
        )
    ]
    plate = [e for e in doran.inherent if e.name == "thermal exemption"][0]
    from hollowstar.resolution import _wins

    assert _wins(plate, room_law[0]) is room_law[0], (
        "SPECIFICATION room law must outrank BLESSED equipment"
    )


# --------------------------------------------------------------------------
# Drift detection
# --------------------------------------------------------------------------


def test_snapshot_records_a_digest_for_every_source():
    for src in SNAP["sources"]:
        assert len(src["sha256"]) == 64, f"{src['owner']} has no usable digest"
    owners = {s["owner"] for s in SNAP["sources"]}
    # The two machine-readable owners and the paired runtime must all be cited.
    assert {"DM041_A", "DM041_B", "DM044_0", "DM044_1"} <= owners


def test_fingerprint_covers_the_sources():
    import hashlib

    expected = hashlib.sha256(
        "".join(
            f"{s['owner']}:{s['sha256']}"
            for s in sorted(SNAP["sources"], key=lambda s: s["owner"])
        ).encode()
    ).hexdigest()[:12]
    assert SNAP["source_fingerprint"] == expected


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
