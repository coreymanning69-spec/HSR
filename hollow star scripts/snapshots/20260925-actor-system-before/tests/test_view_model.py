from hollowstar.view_model import build_public_view


def test_public_view_normalizes_party_and_opposition_without_debug_fields():
    view = build_public_view({
        "run_id": "demo",
        "status": "active",
        "room": {"id": "hall", "name": "Hall", "tells": ["cold air"]},
        "combat": {"round": 2, "current": "p0"},
        "actors": {
            "p0": {"name": "Wren", "controller": "player", "hp": 10, "max_hp": 12, "ac": 17},
            "e0": {"name": "Hound", "controller": "npc", "hp": 5, "max_hp": 8, "ac": 13},
        },
        "private_debug": {"hidden_roll": 20},
    }, mode="DESIGN")
    assert view["schema"] == "hollow-star-public-view-1"
    assert [row["name"] for row in view["party"]] == ["Wren"]
    assert [row["name"] for row in view["opposition"]] == ["Hound"]
    assert view["progression"]["hsr_rank"] is None
    assert "private_debug" not in view


def test_public_view_preserves_exploration_party_lists():
    view = build_public_view({"room": {}, "party": [{"name": "Doran", "hp": 10, "max_hp": 10, "ac": 25}]})
    assert view["party"][0]["id"] == "p0"
    assert view["party"][0]["name"] == "Doran"


def test_public_view_projects_sanitized_combat_state_for_tactical_ui():
    view = build_public_view({
        "combat": {
            "round": 2, "current": "p0", "order": ["p0", "goblin"],
            "economy": {"p0": {"action": 1, "bonus": 1, "reaction": 1, "movement": 30,
                                "hidden_resource": 99}},
            "positions": {"p0": [5, 0, 0], "e0": [20, 0, 0]},
            "pending": [{"kind": "opportunity", "reactor": "p0", "target": "goblin",
                         "options": ["opportunity"], "private_roll": 18}],
            "rules": {"p0": {"secret": "omit"}},
        },
        "party": [{"id": "p0", "name": "Doran", "controller": "player", "hp": 20, "max_hp": 20}],
    })
    assert view["combat"]["schema"] == "hollow-star-public-combat-1"
    assert view["combat"]["current"] == "p0"
    assert view["combat"]["economy"]["p0"] == {"action": 1, "bonus": 1, "reaction": 1, "movement": 30}
    assert view["combat"]["pending"][0] == {"kind": "opportunity", "reactor": "p0", "target": "goblin", "options": ["opportunity"]}
    assert view["combat"]["target_context"] == [{"id": "e0", "distance_ft": 15}]
    assert view["combat"]["disabled_reasons"]["attack"] == "Resolve or decline the open reaction first."
    assert "rules" not in view["combat"]


def test_public_view_projects_checkpoint_and_next_actions_without_private_state():
    actions = [{"id": "checkpoint", "label": "Bank threshold checkpoint"}]
    view = build_public_view({
        "room": {"id": "1:1", "name": "First Threshold", "resolved": True},
        "checkpoint": {"available": True, "current": None, "history": []},
        "available_actions": actions,
    })
    assert view["checkpoint"]["available"] is True
    assert view["next_actions"] == actions


def test_public_room_carries_only_already_visible_environment_evidence():
    view = build_public_view({
        "room": {
            "room_id": "1:1", "title": "Town", "apparent_function": "settlement",
            "resident": "Wellkeeper", "posture": "watchful", "law": "Sleep raises an alarm.",
            "world_state": {
                "objects": {"1:1:dishes": {"object_id": "1:1:dishes", "kind": "stack"}},
                "npcs": {"1:1:staff": {"npc_id": "1:1:staff", "role": "bar staff"}},
                "subrooms": [{"id": "bar_back", "kind": "staff_area"}],
            },
            "function": "secret function", "motive": "hidden motive", "secret": "hidden",
        }
    })
    room = view["room"]
    assert room["apparent_function"] == "settlement"
    assert room["resident"] == "Wellkeeper"
    assert room["law"] == "Sleep raises an alarm."
    assert "1:1:dishes" in room["objects"]
    assert "1:1:staff" in room["npcs"]
    assert room["subrooms"][0]["id"] == "bar_back"
    assert not ({"function", "motive", "secret"} & set(room))


def test_public_view_serializes_live_item_equipment():
    import json
    from hollowstar.items import Item
    view = build_public_view({
        "run_id": "demo", "status": "active", "room": {"id": "hall", "name": "Hall"},
        "actors": {"p0": {"name": "Wren", "controller": "player", "hp": 10, "max_hp": 12, "ac": 17,
                          "equipment": [Item(name="Longsword", damage_dice="1d8")]}},
    }, mode="DESIGN")
    json.dumps(view)
    assert view["party"][0]["equipment"][0]["name"] == "Longsword"


def test_public_view_rejoins_custom_presentation_after_tactical_projection():
    view = build_public_view({
        "combat": {"actors": {"p0": {"name": "Aster", "controller": "player", "hp": 8, "max_hp": 8, "ac": 15}}},
        "party": [{"id": "p0", "name": "Aster", "controller": "player", "sprite_id": "elf-female",
                   "race_id": "elf", "gender": "female",
                   "appearance": {"hair_style": {"id": "braided", "name": "Braided"}}}],
    })
    lead = view["party"][0]
    assert lead["sprite_id"] == "elf-female"
    assert lead["appearance"]["hair_style"]["id"] == "braided"
