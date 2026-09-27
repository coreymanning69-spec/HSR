"""Doran's voice: situational reactions, ambient chatter, and replies."""
from types import SimpleNamespace as N

from hollowstar import doran_voice
from hollowstar.commentary import attach


def creature(name, hp=100, max_hp=100, alive=True):
    return N(name=name, hp=hp, max_hp=max_hp, alive=alive)


def make_run(wren=True, doran_hp=370, foe=None):
    party = [creature("Doran", doran_hp, 370)] + ([creature("Wren", 220, 220)] if wren else [])
    run = N(context={"party_selectors": ["divine:Doran"], "dungeon": {}, "seed": "t"}, party=party)
    roster = {f"p{i}": actor for i, actor in enumerate(party)}
    roster["e0"] = foe or creature("Brass Castellan", 480, 480)
    doran_voice._roster = lambda _run, roster=roster: roster
    return run, roster


def doran_line(event):
    return next((line for line in event.get("commentary", []) if line["speaker"] == "Doran"), None)


def teardown_function():
    import importlib
    importlib.reload(doran_voice)


def test_big_kill_always_speaks_with_target_name():
    run, roster = make_run()
    roster["e0"].alive = False
    event = attach(run, "attack", {"type": "attack", "source": "p0", "target": "e0",
                                   "roll": {"success": True}, "evidence": {}})
    line = doran_line(event)
    assert line and line["trigger"] == "doran_kill_big"
    assert "{target}" not in line["text"]


def test_badly_hurt_reacts_and_wren_lines_need_wren():
    run, roster = make_run(wren=False, doran_hp=40)
    for turn in range(12):
        event = attach(run, "attack", {"type": "attack", "source": "e0", "target": "p0", "roll": {"success": True}})
        line = doran_line(event)
        assert line and line["trigger"] == "doran_hurt_bad"
        assert "Wren" not in line["text"]


def test_wren_assists_build_pair_trust():
    run, _ = make_run()
    for _ in range(4):
        attach(run, "cast", {"type": "healing", "source": "p1", "target": "p0"})
    assert run.context["dungeon"]["commentary"]["doran"]["pair"] == 4


def test_ambient_is_spaced_and_never_in_combat():
    run, _ = make_run()
    spoken = [turn for turn in range(60) if doran_line(attach(run, "move", {"type": "move"}))]
    assert spoken, "Doran never spoke while exploring"
    assert all(b - a >= doran_voice.AMBIENT_GAP for a, b in zip(spoken, spoken[1:]))
    run.context["combat"] = {"active": True}
    assert not any(doran_line(attach(run, "move", {"type": "move"})) for _ in range(30))


def test_pool_is_exhausted_before_any_line_repeats():
    run, _ = make_run(wren=False)
    size = len(doran_voice.REACT["descend"])
    texts = [doran_line(attach(run, "descend", {"type": "descend"}))["text"] for _ in range(size)]
    assert len(set(texts)) == size


def test_replies_read_the_public_view():
    view = {"party": [{"name": "Doran", "hp": 60, "max_hp": 370}, {"name": "Wren", "hp": 220, "max_hp": 220}],
            "opposition": [{"name": "Stone Giant", "hp": 300, "max_hp": 300}], "room": {"name": "Forge Hall"}}
    assert doran_voice.reply(view, "Doran, how are you holding up?")["topic"] == "status"
    threat = doran_voice.reply(view, "what do you think of that thing?")
    assert threat["topic"] == "threat" and "Stone Giant" in threat["text"]
    assert doran_voice.reply(view, "tell me about Wren")["topic"] == "wren"
    assert doran_voice.reply(view, "asdf qwerty")["topic"] == "fallback"
    assert "{" not in doran_voice.reply(view, "where are we")["text"]


def test_no_maintenance_talk_for_undamageable_kit():
    everything = [line for pool in (*doran_voice.REACT.values(), *doran_voice.AMBIENT.values()) for line in pool]
    everything += [line for _, _, pool in doran_voice.REPLY_TOPICS for line in pool]
    banned = ("sharpen", "whetstone", "oil", "polish", "repair", "clean your blade")
    assert not [line for line in everything if any(word in line.lower() for word in banned)]
