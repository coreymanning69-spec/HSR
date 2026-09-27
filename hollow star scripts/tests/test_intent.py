import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hollowstar.intent import IntentClarification, IntentError, parse_intent
from hollowstar.session_intent import vocabulary

VISIBLE_COMBAT = {"combat": {"actors": {"p0": {"name": "Doran"}, "p1": {"name": "Wren"}, "e0": {"name": "Ash Hound 1"}, "e1": {"name": "Ash Hound 2"}}}, "room": {"world_state": {"objects": [{"id": "cabinet", "name": "cabinet"}], "subrooms": [{"id": "bar_back", "name": "bar back"}]}}}
VISIBLE_RELIQUARY = {
    "room": {
        "resident": "Wellkeeper",
        "world_state": {
            "objects": {"1:1:dishes": {"object_id": "1:1:dishes", "kind": "stack", "tags": ["dish", "dishes"]}},
            "npcs": {},
            "subrooms": [{"id": "bar_back", "kind": "staff_area"}],
        },
    },
    "party": [{"name": "Doran"}, {"name": "Wren"}],
    "inventory": {"item-1": {"id": "item-1", "name": "unidentified Ruby Rune", "kind": "imprint"}},
}


def test_common_intents_translate_without_resolution():
    assert parse_intent("attack p0 e1") == {"type": "attack", "actor": "p0", "target": "e1"}
    assert parse_intent("move p0 15 20 0")["destination"] == [15, 20, 0]
    assert parse_intent("cast p1 Bless e0") == {"type": "cast", "actor": "p1", "spell": "Bless", "targets": ["e0"]}
    assert parse_intent("I want to attack p0 e1") == {"type": "attack", "actor": "p0", "target": "e1"}


def test_unknown_intent_fails_closed():
    try:
        parse_intent("invent a result")
    except IntentError:
        pass
    else:
        raise AssertionError("unknown intent must not become an action")


def test_connective_room_investigation_translates_without_guessing_an_actor():
    assert parse_intent("I study the room before committing.") == {"type": "investigate"}


def test_attack_intent_preserves_mode_and_bonus():
    assert parse_intent("attack p0 e0 thrown bonus") == {
        "type":"attack", "actor":"p0", "target":"e0", "mode":"thrown", "bonus":True}


def test_escape_intent_strips_natural_language_route_connector():
    assert parse_intent("escape through lower route") == {"type":"escape","route":"lower route"}


def test_argument_punctuation_is_not_forwarded_as_game_state():
    assert parse_intent("attack p0 e1,") == {"type":"attack", "actor":"p0", "target":"e1"}


def test_move_coordinate_punctuation_is_normalized_before_parsing():
    assert parse_intent("move p0 15 20 0.") == {"type":"move", "actor":"p0", "destination":[15,20,0]}


def test_command_punctuation_is_ignored_during_discovery():
    assert parse_intent("Attack: p0 e1") == {"type":"attack", "actor":"p0", "target":"e1"}


def test_content_names_accept_accented_input_without_changing_canonical_ids():
    context = {"content": [{"id": "relic", "name": "Café Relic", "aliases": [], "owner": "Doran"}]}
    assert parse_intent("use the cafe relic", context) == {
        "type": "content", "actor": "p0", "content_id": "relic"}


def test_intent_length_is_bounded_before_expensive_matching():
    try:
        parse_intent("x" * 2001)
    except IntentError as exc:
        assert "2000 characters" in str(exc)
    else:
        raise AssertionError("oversized intent must fail closed")


def test_move_accepts_natural_coordinate_separators():
    assert parse_intent("move p0 to 15, 20, 0") == {"type":"move", "actor":"p0","destination":[15,20,0]}


def test_visible_plain_language_resolves_without_raw_ids():
    assert parse_intent("Doran attacks Ash Hound 2", VISIBLE_COMBAT) == {"type": "attack", "actor": "p0", "target": "e1"}
    assert parse_intent("Wren opens the cabinet", VISIBLE_COMBAT) == {"type": "open_object", "actor": "p1", "object_id": "cabinet"}


def test_visible_ambiguity_returns_narrator_safe_clarification():
    context = {"combat": {"actors": {"e0": {"name": "hound"}, "e1": {"name": "hound"}}}}
    try:
        parse_intent("attack Doran hound", context)
    except IntentClarification as exc:
        assert "which actor or target" in exc.message
    else:
        raise AssertionError("ambiguous visible entity must not be guessed")


def test_room_verbs_preserve_named_actor_and_destination():
    assert parse_intent("Wren opens the cabinet") == {"type":"open_object", "actor":"p1", "object_id":"cabinet"}
    assert parse_intent("Wren lights crown_of_stars") == {"type":"light_source", "actor":"p1", "source":"crown_of_stars"}
    assert parse_intent("Wren walks into the room behind the bar_back") == {"type":"enter_subroom", "actor":"p1", "location":"bar_back"}


def test_content_parser_reads_natural_clause_and_composed_modifier():
    action = parse_intent("I walk in and use Split Ray Eraser")
    assert action["type"] == "content"
    assert action["actor"] == "p1"  # Portal Shear is Wren-owned.
    assert action["content_id"] == "wren.portal_shear"
    assert action["parameters"] == {"metamagic": ["split_ray"]}


def test_content_parser_prefers_longest_visible_name_inside_clause():
    assert parse_intent("please use the Staff of the Magi to absorb the spell")["content_id"] == "wren.staff_magi"


def test_reliquary_parser_uses_visible_entities_and_defaults_actor():
    assert parse_intent("search the dishes", VISIBLE_RELIQUARY) == {
        "type": "search_object", "actor": "p0", "object_id": "1:1:dishes"}
    assert parse_intent("Wren lights the crown", VISIBLE_RELIQUARY) == {
        "type": "light_source", "actor": "p1", "source": "crown"}
    assert parse_intent("negotiate with the Wellkeeper", VISIBLE_RELIQUARY) == {
        "type": "negotiate", "actor": "p0", "target": "Wellkeeper"}


def test_reliquary_approaches_and_lodging_translate_without_new_entities():
    assert parse_intent("avoid them", VISIBLE_RELIQUARY) == {"type": "avoid", "actor": "p0"}
    assert parse_intent("disarm the hazard", VISIBLE_RELIQUARY) == {"type": "disarm", "actor": "p0"}
    assert parse_intent("fight the Wellkeeper", VISIBLE_RELIQUARY) == {"type": "fight", "actor": "p0"}
    for phrase in ("buy a room", "purchase the room", "rent the room"):
        assert parse_intent(phrase, VISIBLE_RELIQUARY) == {"type": "buy", "actor": "p0", "product": "room"}


def test_identification_is_exact_and_unknown_items_fail_closed():
    assert parse_intent("identify the unidentified Ruby Rune", VISIBLE_RELIQUARY) == {
        "type": "identify", "actor": "p0", "item": "item-1"}
    try:
        parse_intent("identify the blue Rune", VISIBLE_RELIQUARY)
    except IntentError:
        pass
    else:
        raise AssertionError("unknown visible inventory must not be guessed")


def test_resident_is_evidence_not_a_combat_target():
    try:
        parse_intent("attack the Wellkeeper", VISIBLE_RELIQUARY)
    except IntentError as exc:
        assert "use fight" in str(exc)
    else:
        raise AssertionError("a resident string must not become an NPC entity")


def test_sandbox_grammar_is_schema_gated():
    sandbox = {"schema": "hollow-star-dd-sandbox-1", "room": {"objects": {}}}
    assert parse_intent("take the rags", sandbox)["type"] == "take"
    try:
        parse_intent("take the rags", VISIBLE_RELIQUARY)
    except IntentError:
        pass
    else:
        raise AssertionError("sandbox-only grammar must not leak into Reliquary DESIGN")


def test_published_inspection_and_social_phrases_translate():
    phrases = [phrase for group in vocabulary().values() if isinstance(group, list)
               for phrase in group if "<resident>" not in phrase]
    for phrase in ("look around", "show my equipment", "show room"):
        assert phrase in phrases
        assert isinstance(parse_intent(phrase, VISIBLE_RELIQUARY), dict)
    assert parse_intent("talk to Wellkeeper", VISIBLE_RELIQUARY)["type"] == "talk"


if __name__ == "__main__":
    test_common_intents_translate_without_resolution()
    test_unknown_intent_fails_closed()
    test_attack_intent_preserves_mode_and_bonus()
    test_escape_intent_strips_natural_language_route_connector()
    print("4 intent tests passed")
