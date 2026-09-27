"""Focused tests for the first interactive single-player screen slice."""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.actors import Actor, Band  # noqa: E402
from hollowstar.effects import Effect  # noqa: E402
from hollowstar.items import Item  # noqa: E402
from hollowstar.phases import Direction, Phase, Tier  # noqa: E402
from hollowstar.screen import ScreenCommandError, SinglePlayerScreen  # noqa: E402


def screen() -> SinglePlayerScreen:
    actor = Actor(
        name="Test Sera",
        band=Band.HEROIC,
        max_hp=40,
        hp=40,
        armor_class=15,
        ability_scores={"STR": 10, "DEX": 14, "CON": 12, "INT": 10, "WIS": 8, "CHA": 18},
        proficiency_bonus=3,
    )
    return SinglePlayerScreen(actor, io.StringIO(), io.StringIO())


def test_sheet_shows_live_dnd_stats() -> None:
    output = screen().execute("status")
    assert "HP 40/40" in output
    assert "AC 15" in output
    assert "STR: 10  modifier +0" in output
    assert "WIS:  8  modifier -1" in output
    assert "CHA: 18  modifier +4" in output


def test_commands_update_shared_actor_state() -> None:
    ui = screen()
    assert "DEX is now 16 (+3)." == ui.execute("boost dex 2")
    assert ui.actor.ability_score("DEX") == 16
    assert ui.execute("damage 9") == "Damage applied. HP is now 31/40."
    assert ui.execute("heal 4") == "Healing applied. HP is now 35/40."
    assert ui.execute("set ac 19") == "AC is now 19."
    assert ui.actor.armor_class == 19


def test_invalid_updates_fail_without_mutation() -> None:
    ui = screen()
    try:
        ui.execute("set STR 31")
    except ScreenCommandError:
        pass
    else:
        raise AssertionError("out-of-range ability score must fail")
    assert ui.actor.ability_score("STR") == 10
    try:
        ui.execute("damage -1")
    except ScreenCommandError:
        pass
    else:
        raise AssertionError("negative damage must fail")


def test_items_view_groups_by_slot_and_shows_effects() -> None:
    actor = Actor(name="Geared Sera", max_hp=20, hp=20, armor_class=12)
    actor.equipment = [
        Item(
            name="longsword",
            slot="hand",
            tier=Tier.MUNDANE,
            inherent=[
                Effect(
                    name="iced material",
                    phase=Phase.PERSISTENCE,
                    direction=Direction.GRANT,
                    tell="Frost beads along the edge.",
                )
            ],
        ),
        Item(name="chain shirt", slot="armor", base_ac=13),
    ]
    ui = SinglePlayerScreen(actor, io.StringIO(), io.StringIO())
    output = ui.execute("items")
    assert "ITEMS & RUNES" in output
    assert "ARMOR" in output
    assert "HAND" in output
    assert output.index("ARMOR") < output.index("HAND")  # SLOT_ORDER
    assert "iced material" in output
    assert "<PERSISTENCE/GRANT>" in output
    assert "tell: Frost beads along the edge." in output
    assert "(no effects)" in output  # chain shirt has none
    assert ui.execute("runes") == output
    assert ui.execute("equipment") == output


def test_items_view_handles_empty_loadout() -> None:
    ui = screen()
    assert "(no equipment)" in ui.execute("items")


def test_menu_loop_uses_same_state_as_commands() -> None:
    # [2] boost prompts for ability then amount; [3] damage prompts for amount.
    incoming = io.StringIO("2\nSTR\n2\n3\n5\n1\n0\n")
    output = io.StringIO()
    actor = Actor(name="Menu Sera", max_hp=20, hp=20, armor_class=12)
    SinglePlayerScreen(actor, incoming, output).run()
    assert actor.ability_score("STR") == 12
    assert actor.hp == 15
    assert "STR: 12" in output.getvalue()


def main() -> None:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\n{len(tests)} screen tests passed")


if __name__ == "__main__":
    main()
