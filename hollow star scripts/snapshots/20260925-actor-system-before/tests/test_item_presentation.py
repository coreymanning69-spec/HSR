"""Public equipment must preserve real affixes and conceal unknown Runes."""
import copy
import json
from hollowstar.items import Item, item_presentation, public_item
from hollowstar.phases import Tier
from hollowstar.tags import DamageTag
from hollowstar.loader import load_items, load_affixes
from hollowstar.view_model import build_public_view
from hollowstar.profiles import actor_sheet
from hollowstar.actors import Actor


def test_item_instance_affixes_are_json_safe_and_do_not_mutate_engine():
    item = load_items()["longsword"]
    affixes = load_affixes()
    item.prefix, item.suffix = affixes["Petty"], affixes["of Ice"]
    for prefix, suffix, expected in [(None,None,"longsword"),(affixes["Petty"],None,"Petty longsword"),(None,affixes["of Ice"],"longsword of Ice"),(affixes["Petty"],affixes["of Ice"],"Petty longsword of Ice")]:
        item.prefix, item.suffix = prefix, suffix
        assert public_item(item)["display_name"] == expected
    original = copy.deepcopy(item)
    public = json.loads(json.dumps(public_item(item)))
    assert public["display_name"] == "Petty longsword of Ice"
    assert public["base_damage"] == item.base_damage == 5
    assert public["prefix"]["effects"][0]["flat_bonus"] == 2
    assert public["prefix"]["effects"][0]["condition"] == "enemy_full_hp"
    assert public["suffix"]["effects"][0]["phase"] == "PERSISTENCE"
    assert "ICE" in public["tags"] and public["appearance"]
    public["prefix"]["effects"][0]["flat_bonus"] = 999
    assert item == original
    actor = Actor(name="Test", equipment=[item])
    assert actor_sheet(actor, selector="test", kind="custom")["equipment"][0]["display_name"] == "Petty longsword of Ice"


def test_every_weapon_in_the_loot_table_has_a_working_generic_profile():
    """Every items.json entry with a base_damage must carry damage_dice, a
    reachable reach and a valid range band -- otherwise a custom-identity
    wielder's Actor.weapon_profile()/tactical.weapon_attack() has nothing to
    attack with and raises 'weapon dice are not implemented'."""
    for name, item in load_items().items():
        if not item.base_damage:
            continue
        assert item.damage_dice, f"{name} has base_damage but no damage_dice"
        assert item.reach >= 5, f"{name} has an unreachable reach"
        assert item.range_long >= item.range_normal, f"{name} range_long below range_normal"
        actor = Actor(name="Wielder", equipment=[item])
        profile = actor.weapon_profile()
        assert profile["damage_dice"] == item.damage_dice
        assert profile["reach"] == item.reach
        assert profile["range"] == {"normal": item.range_normal, "long": item.range_long}


def test_loader_wires_through_authored_presentation_overrides():
    """load_items() must not silently drop an authored silhouette/handedness
    override. Dropping it is what made a warhammer render as a spellcaster's
    staff -- its BLUDGEONING-only tag falls into _silhouette()'s caster-
    implement heuristic, which is right for a mace/quarterstaff wielded by an
    INT/WIS/CHA caster and wrong for a STR martial hammer."""
    items = load_items()
    assert item_presentation(items["warhammer"])["silhouette"] == "axe"
    assert item_presentation(items["battleaxe"])["silhouette"] == "axe"
    assert item_presentation(items["rapier"])["silhouette"] == "sword"
    assert item_presentation(items["greatsword"])["handedness"] == "two-handed"
    assert item_presentation(items["glaive"])["handedness"] == "two-handed"
    assert item_presentation(items["hunting bow"])["silhouette"] == "bow"


def test_glaive_has_polearm_reach_and_ranged_weapons_carry_real_range_bands():
    items = load_items()
    assert items["glaive"].reach == 10
    assert items["hand crossbow"].range_normal == 30 and items["hand crossbow"].range_long == 120
    assert items["hunting bow"].range_normal == 150 and items["hunting bow"].range_long == 600
    assert items["silvered dagger"].range_long == 60  # thrown, not just melee


def test_projection_keeps_one_combat_actor_and_redacts_unknown_item_details():
    secret = {"id":"r1", "kind":"imprint", "identified":False, "name":"Secret", "true_name":"Secret", "prefix":{"name":"Hidden"}, "suffix":{"name":"Secret"}, "modifiers":[{"effect":"damage", "value":99}], "unidentified_descriptor":"Cloudy Rune"}
    actor = {"id":"p0", "name":"Test", "controller":"player", "equipment":[secret], "hp":5}
    state = {"combat":{"actors":{"p0":actor}}, "party":[actor], "inventory":[secret], "imprints":{"p0":{"ring_1":"r1"}}}
    before = copy.deepcopy(state)
    view = build_public_view(state)
    assert len(view["party"]) == 1
    assert view["inventory"][0]["name"] == "Cloudy Rune"
    dumped = json.dumps(view)
    assert "Secret" not in dumped
    assert '"modifiers":' not in dumped  # exact key, not a substring of "ability_modifiers"
    view["imprints"]["p0"]["ring_1"] = "changed"
    view["party"][0]["equipment"][0]["name"] = "changed"
    assert state == before


def test_staged_endless_engagement_catalog_preserves_phase_contract():
    from hollowstar.loader import affix_catalog, load_staged_affixes

    staged = load_staged_affixes()
    catalog = affix_catalog()
    assert len(staged) == 37
    assert catalog["schema"] == "hollow-star-affix-catalog-1"
    assert catalog["counts"] == {"active": 10, "staged": 37}
    blazing = next(row for row in catalog["staged"] if row["name"] == "Blazing")
    assert blazing["options"]["staged"] is True
    assert "FIRE" in blazing["tags"]
    assert {effect["phase"] for effect in blazing["phase_effects"]} == {"MAGNITUDE", "PERMISSION", "CONSEQUENCE"}
    assert next(row for row in catalog["active"] if row["name"] == "Petty")["options"]["attachable"] is True


def test_visual_presentation_is_derived_from_mechanics_not_item_names():
    """A name regex mis-reads this; the slot does not."""
    hood = Item(name="Hood of the Plate Captain", slot="head")
    assert item_presentation(hood)["silhouette"] == "helm"
    assert item_presentation(hood)["material"] != "plate"


def test_armour_weight_comes_from_the_dex_cap_and_ac_magnitude():
    # The dex cap separates the three weights the AC resolver already knows.
    assert item_presentation(Item(name="p", slot="armor", base_ac=18, dex_cap=0))["material"] == "plate"
    assert item_presentation(Item(name="c", slot="armor", base_ac=13, dex_cap=2))["material"] == "chain"
    # Uncapped armour splits on strength: leather is weak, a warded robe is not.
    assert item_presentation(Item(name="l", slot="armor", base_ac=12))["material"] == "leather"
    assert item_presentation(Item(name="r", slot="armor", base_ac=18))["material"] == "robe"


def test_weapon_silhouettes_cover_the_drawable_shapes():
    def shape(**kwargs):
        return item_presentation(Item(name="w", slot="hand", **kwargs))["silhouette"]

    assert shape(base_damage=8, tags={DamageTag.SLASHING}) == "sword"
    assert shape(base_damage=4, tags={DamageTag.PIERCING}) == "dagger"
    assert shape(base_damage=8, range_normal=150) == "bow"
    assert shape(base_damage=6, attack_ability="INT") == "staff"
    assert shape(base_ac=2, shield_bonus=2) == "shield"


def test_a_carried_item_is_drawn_as_itself_and_unknown_slots_stay_neutral():
    # Wren's staff sits in "carried" rather than "hand" so its tags stay out of
    # her attack path -- but it is still a staff and is drawn as one. Her focus
    # is the Black Bird Sigil; no item claims that slot.
    assert item_presentation(Item(name="Staff of the Magi", slot="carried"))["silhouette"] == "staff"
    # An unrecognised slot must not be guessed into a blade.
    assert item_presentation(Item(name="odd", slot="banner"))["silhouette"] == "held"


def test_authored_visuals_override_derivation():
    item = Item(name="x", slot="hand", base_damage=5, silhouette="staff", material="wood")
    presented = item_presentation(item)
    assert presented["silhouette"] == "staff"
    assert presented["material"] == "wood"


def test_rarity_and_fx_track_tier_tags_and_density():
    plain = item_presentation(Item(name="sword", slot="hand", base_damage=8))
    assert plain["rarity"] == "mundane" and plain["fx"] == []

    legendary = item_presentation(Item(
        name="flametongue", slot="hand", base_damage=8, density=3.0,
        tier=Tier.ARTIFACT, tags={DamageTag.SLASHING, DamageTag.FIRE}))
    assert legendary["rarity"] == "artifact"
    # Elemental tag, artifact glow, and the Primeverse "+N" density heft.
    assert {"ember", "glow", "dense"} <= set(legendary["fx"])
    # Ordinary physical tags are the unmarked default and draw no aura.
    assert "physical" not in legendary["fx"] and "slashing" not in legendary["fx"]


def test_public_item_carries_the_presentation_block():
    item = load_items()["longsword"]
    presented = json.loads(json.dumps(public_item(item)))["presentation"]
    assert {"rarity", "silhouette", "material", "fx", "item_type", "handedness", "coverage", "animation_profile"} <= set(presented)
    assert presented["item_type"] == "weapon"
    assert presented["handedness"] == "one-handed"
    assert presented["animation_profile"] == "sword-1h"


def test_two_handed_weapon_and_full_helm_publish_distinct_animation_contracts():
    greatsword = Item(name="greatsword", slot="hand", base_damage=10,
                       silhouette="sword", handedness="two-handed")
    helm = Item(name="full helm", slot="head", silhouette="helm", coverage="full")
    great = item_presentation(greatsword)
    covered = item_presentation(helm)
    assert (great["item_type"], great["handedness"], great["animation_profile"]) == ("weapon", "two-handed", "sword-2h")
    assert (covered["item_type"], covered["coverage"], covered["animation_profile"]) == ("headgear", "full", "armored-guard")
