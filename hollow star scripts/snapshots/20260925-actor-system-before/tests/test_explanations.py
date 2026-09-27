"""Focused tests for public examine data and text explanations."""

import copy
import json
import tempfile
from pathlib import Path

from hollowstar.actors import Actor
from hollowstar.effects import Effect
from hollowstar.explanations import examine_view, item_explanation, resolution_explanation
from hollowstar.items import Item
from hollowstar.intent import parse_intent
from hollowstar.phases import Direction, Phase
from hollowstar.resolution import select_stackable
from hollowstar.view_model import build_public_view


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent


def test_explicit_stack_group_selects_one_deterministically_and_reports_suppression():
    weaker = Effect("ring one", Phase.MAGNITUDE, Direction.MODIFY,
                    stack_group="item.attack_accuracy", priority=10, flat_bonus=1)
    stronger = Effect("ring two", Phase.MAGNITUDE, Direction.MODIFY,
                      stack_group="item.attack_accuracy", priority=20, flat_bonus=2)
    selected, suppressed = select_stackable([weaker, stronger])
    assert [effect.name for effect in selected] == ["ring two"]
    assert suppressed == [{"effect": "ring one", "stack_group": "item.attack_accuracy",
                           "reason": "suppressed by ring two"}]


def test_public_view_contains_explainable_actor_and_item_effects():
    item = Item("Blessed Blade", damage_dice="1d8", attack_bonus=1, inherent=[
        Effect("Blessed accuracy", Phase.MAGNITUDE, Direction.MODIFY,
               stat="attack_roll", flat_bonus=1, source_id="item:blessed_blade",
               stack_group="item.attack_accuracy", public_summary="+1 attack")
    ])
    actor = Actor("Lead", controller="player", equipment=[item], skill_bonuses={"Stealth": 5})
    state = {"party": [{**actor.__dict__, "id": "p0", "equipment": [{
        "id": "blessed-blade", "name": "Blessed Blade", "display_name": "Blessed Blade",
        "damage_dice": "1d8", "attack_bonus": 1, "inherent": [{
            "name": "Blessed accuracy", "phase": "MAGNITUDE", "direction": "MODIFY",
            "stat": "attack_roll", "flat_bonus": 1, "stack_group": "item.attack_accuracy",
            "public_summary": "+1 attack"
        }]
    }]}]}
    view = build_public_view(state)
    public_actor = view["party"][0]
    assert public_actor["effects"][0]["summary"] == "+1 attack"
    assert public_actor["skill_bonuses"] == {"Stealth": 5}
    assert item_explanation(public_actor["equipment"][0])["effects"][0]["source"]["name"] == "Blessed Blade"
    assert json.loads(json.dumps(view))


def test_examine_view_is_visible_only_and_explains_results():
    view = build_public_view({
        "party": [{"id": "p0", "name": "Lead", "controller": "player", "hp": 8,
                   "max_hp": 10, "ac": 14, "skill_bonuses": {"Stealth": 5}}],
        "inventory": [{"id": "potion", "name": "Healing Potion", "kind": "potion",
                        "utility_uses": ["drink to restore health"]}],
    })
    examined = examine_view(view, entity_type="item", query="healing potion")
    assert examined["name"] == "Healing Potion"
    assert examined["utility"] == ["drink to restore health"]
    assert examine_view(view, entity_type="actor", entity_id="p0")["skills"] == {"Stealth": 5}
    result = resolution_explanation({"evidence": {"attack": {"rolls": [12], "bonus": 4,
        "target_ac": 14, "hit": True}}})
    assert result["breakdown"][0] == {"label": "Roll", "value": [12]}


def test_examine_and_explain_text_intents_are_bounded():
    context = {"party": [{"id": "p0", "name": "Lead"}],
               "inventory": [{"id": "potion", "name": "Healing Potion"}]}
    assert parse_intent("examine the healing potion", context) == {
        "type": "examine", "entity_type": "item", "entity_id": "potion"}
    assert parse_intent("why did that happen") == {"type": "explain", "subject": "last_result"}


def test_host_examine_command_and_text_turn_are_read_only():
    from hollowstar.host import HSRHost

    with tempfile.TemporaryDirectory() as temp:
        data_root = Path(temp) / ".local" / "reliquary_runs"
        host = HSRHost.from_options(WORKSPACE, data_root=data_root)
        assert host.handle({"id": "boot", "command": "boot", "mode": "DESIGN"})["ok"]
        assert host.handle({"id": "create", "command": "create_run", "run_id": "examine-test",
                            "party": ["Doran"], "opposition": ["Townsperson"],
                            "seed": "examine-seed"})["ok"]
        assert host.handle({"id": "start", "command": "design_start", "run_id": "examine-test"})["ok"]
        direct = host.handle({"id": "inspect", "command": "examine", "run_id": "examine-test",
                              "entity_type": "actor", "entity_id": "p0"})
        assert direct["ok"] is True
        assert direct["result"]["examine"]["name"] == "Doran"
        assert direct["result"]["public_receipt"]["read_only"] is True
        turn = host.handle({"id": "turn", "command": "design_turn", "run_id": "examine-test",
                            "intent": "examine Doran"})
        assert turn["ok"] is True
        assert turn["result"]["turn"]["examine"]["name"] == "Doran"
        assert turn["result"]["turn"]["public_receipt"]["read_only"] is True
