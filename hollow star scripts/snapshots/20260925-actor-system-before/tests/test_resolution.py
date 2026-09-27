"""Phase 1 correctness seeds. Run: python3 -m pytest tests/ -q  (or plain python3)."""

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.combat import Encounter
from hollowstar.loader import forge, load_affixes, load_items, load_roster
from hollowstar.phases import Phase
from hollowstar.resolution import resolve_attack
from hollowstar.rng import RunRNG

AFFIXES = load_affixes()
ITEMS = load_items()


def fresh():
    return load_roster()


def test_gate_blocks_at_permission():
    r = fresh()
    a, spirit = r["Doran"], r["Wailing Spirit"]
    a.max_hp = a.hp = 100
    a.equipment = [ITEMS["longsword"]]
    res = resolve_attack(a, spirit)
    assert res.stopped_at is Phase.PERMISSION
    assert res.damage == 0
    assert res.tells_revealed, "a blocking gate must reveal a tell"


def test_blessed_prefix_opens_gate():
    r = fresh()
    a, spirit = r["Doran"], r["Wailing Spirit"]
    a.max_hp = a.hp = 100
    a.equipment = [forge(ITEMS["silvered dagger"], prefix=AFFIXES["Consecrated"])]
    res = resolve_attack(a, spirit)
    assert res.succeeded
    assert res.damage > 0


def test_targeting_denial_is_not_damage_immunity():
    """A TARGETING deny stops the action before MAGNITUDE ever runs."""
    r = fresh()
    a, t = r["Doran"], r["Townsperson"]
    a.max_hp = a.hp = 100
    a.equipment = [ITEMS["longsword"]]
    t.equipment = [forge(ITEMS["longsword"], suffix=AFFIXES["of the Unseen Step"])]
    res = resolve_attack(a, t)
    assert res.stopped_at is Phase.TARGETING


def test_charges_exhaust():
    r = fresh()
    a, t = r["Doran"], r["Townsperson"]
    a.max_hp = a.hp = 100
    a.equipment = [ITEMS["longsword"]]
    t.equipment = [forge(ITEMS["longsword"], suffix=AFFIXES["of the Unseen Step"])]
    resolve_attack(a, t)
    res = resolve_attack(a, t)
    assert res.succeeded, "one-charge denial must not loop forever"


def test_legacy_affix_math_preserved():
    """Ported sera affixes must produce the same magnitude behaviour."""
    r = fresh()
    a, t = r["Doran"], r["Townsperson"]
    a.max_hp = a.hp = 100
    t.max_hp = t.hp = 99
    a.equipment = [forge(ITEMS["longsword"], prefix=AFFIXES["Petty"])]
    res = resolve_attack(a, t)
    assert res.damage == 7, "longsword 5 + Petty 2 vs full-hp target"


def test_condition_gating():
    r = fresh()
    a, t = r["Doran"], r["Townsperson"]
    a.max_hp = a.hp = 100
    t.max_hp, t.hp = 99, 10  # not at full hp, so Petty must not fire
    a.equipment = [forge(ITEMS["longsword"], prefix=AFFIXES["Petty"])]
    res = resolve_attack(a, t)
    assert res.damage == 5


def test_consequence_riders_land():
    r = fresh()
    a, t = r["Doran"], r["Townsperson"]
    a.max_hp = a.hp = 100
    a.equipment = [forge(ITEMS["longsword"], suffix=AFFIXES["of Frostbite"])]
    res = resolve_attack(a, t)
    assert "SLOWED" in res.statuses_applied


def test_determinism():
    def run(seed):
        r = fresh()
        p = [r["Doran"], r["Wren"]]
        for x in p:
            x.max_hp = x.hp = 60
            x.equipment = [ITEMS["longsword"]]
        mob = []
        for i in range(3):
            t = copy.deepcopy(r["Townsperson"])
            t.name = f"T{i}"
            t.equipment = [ITEMS["longsword"]]
            mob.append(t)
        e = Encounter(party=p, opposition=mob, rng=RunRNG(seed))
        return e.run(), e.round_number, len(e.transcript)

    assert run("abc") == run("abc"), "same seed must replay identically"


def test_roster_flags_placeholders():
    r = fresh()
    assert r["Doran"].provenance.verified is False
    assert r["Wren"].provenance.verified is False
    assert r["Doran"].provenance.owner_file == "DM041_A"


def test_resolution_exposes_machine_readable_evidence():
    r = fresh()
    attacker, target = r["Doran"], r["Townsperson"]
    attacker.max_hp = attacker.hp = 100
    target.max_hp = target.hp = 100
    attacker.equipment = [copy.deepcopy(ITEMS["longsword"])]
    attacker.equipment[0].damage_dice = "1d8"
    result = resolve_attack(attacker, target, rng=RunRNG("evidence-seed"))
    assert result.evidence["actor"] == "Doran"
    assert result.evidence["target"] == "Townsperson"
    assert result.evidence["target_ac"] == target.armor_class
    assert result.evidence["attack"]["total"] == result.evidence["attack"]["natural"] + result.evidence["attack"]["bonus"]
    if result.succeeded:
        assert result.evidence["damage"]["rolls"]
        assert result.evidence["damage_total"] == result.damage
        assert result.evidence["state_changes"]["target_hp_after"] == target.hp


def test_generic_weapon_profile_exposes_equipment_math():
    actor = fresh()["Townsperson"]
    actor.set_ability_score("DEX", 16)
    actor.proficiency_bonus = 2
    weapon = copy.deepcopy(ITEMS["longsword"])
    weapon.damage_dice = "1d8"
    weapon.attack_ability = "DEX"
    weapon.reach, weapon.range_normal, weapon.range_long = 5, 20, 60
    actor.equipment = [weapon]
    profile = actor.weapon_profile()
    assert profile["ability_modifier"] == 3
    assert profile["attack_bonus"] == 5
    assert profile["range"] == {"normal": 20, "long": 60}


def test_generic_armor_profile_applies_dex_cap_and_bonuses():
    actor = fresh()["Townsperson"]
    actor.set_ability_score("DEX", 18)
    armor = copy.deepcopy(ITEMS["chain shirt"])
    armor.dex_cap = 2
    armor.shield_bonus = 2
    ring = copy.deepcopy(ITEMS["ring of protection"])
    ring.ac_bonus = 1
    actor.equipment = [armor, ring]
    profile = actor.armor_profile()
    assert profile["base_ac"] == 13
    assert profile["dex_modifier_raw"] == 4
    assert profile["dex_modifier_applied"] == 2
    assert profile["shield_bonus"] == 2
    assert profile["accessory_bonus"] == 1
    assert profile["total"] == 18


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} passed")
