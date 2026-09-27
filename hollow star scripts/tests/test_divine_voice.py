"""Sera/Ember pools and Ember's answers to Wren's divine spells."""
from types import SimpleNamespace as N

from hollowstar import divine_voice, doran_voice
from hollowstar.commentary import attach


def make_run():
    party = [N(name="Doran", hp=370, max_hp=370, alive=True), N(name="Wren", hp=220, max_hp=220, alive=True)]
    run = N(context={"party_selectors": ["divine:Doran", "divine:Wren"], "dungeon": {}, "seed": "d"}, party=party)
    return run


def voices(event):
    return [(line["speaker"], line.get("register")) for line in event.get("commentary", [])]


def test_wren_commune_is_answered_by_ember_with_first_time_line():
    run = make_run()
    event = attach(run, "cast", {"type": "cast", "actor": "p1", "spell": "Commune@5e"})
    ember = [line for line in event["commentary"] if line["speaker"] == "Ember"]
    assert ember and ember[0]["register"] == "divine" and ember[0]["first_time"]
    assert ember[0]["text"] in divine_voice.DIVINE["Commune"]["ember_first"]
    presence = [line for line in event["commentary"] if line["speaker"] == "Presence"]
    assert presence and presence[0]["register"] == "presence"
    second = attach(run, "cast", {"type": "cast", "actor": "p1", "spell": "Commune@5e"})
    later = [line for line in second["commentary"] if line["speaker"] == "Ember"][0]
    assert not later["first_time"] and later["text"] in divine_voice.DIVINE["Commune"]["ember"]


def test_non_divine_spell_and_non_wren_caster_get_no_divine_answer():
    run = make_run()
    assert ("Ember", "divine") not in voices(attach(run, "cast", {"type": "cast", "actor": "p1", "spell": "Fireball@5e"}))
    assert ("Ember", "divine") not in voices(attach(run, "cast", {"type": "cast", "actor": "p0", "spell": "Commune@5e"}))


def test_unearthly_recovery_feature_is_answered():
    run = make_run()
    event = attach(run, "unearthly_recovery", {"type": "healing", "target": "p1", "actor": "p1",
                                                "feature": "unearthly_recovery", "healing": 110})
    assert any(line["register"] == "presence" for line in event["commentary"])


def test_soliera_is_never_a_speaker_and_presence_is_never_quoted_speech():
    speakers = {"Sera", "Ember", "Presence"}
    for entry in (*divine_voice.DIVINE.values(), *divine_voice.FEATURES.values()):
        for line in entry.get("presence", []):
            assert '"' not in line and "“" not in line
            assert "Soliera" not in line  # presence shows effect, never names intent
    run = make_run()
    for spell in divine_voice.DIVINE:
        event = attach(run, "cast", {"type": "cast", "actor": "p1", "spell": f"{spell}@5e"})
        assert {line["speaker"] for line in event.get("commentary", [])} <= speakers | {"Doran"}


def test_general_pools_rotate_instead_of_repeating():
    state = {}
    seen = {line["text"] for turn in range(40) for line in divine_voice.general("combat", turn, state, "s")}
    assert len(seen) >= 8
