from hollowstar import cli


def test_clarification_menu_round_trip():
    opts = cli.clarification_options("I need clarification: which target do you mean — Goblin Archer, Goblin Shaman?")
    assert opts == ["Goblin Archer", "Goblin Shaman"]
    assert cli.prompt_disambiguation(opts, reader=lambda _: "2") == "Goblin Shaman"
    assert cli.prompt_disambiguation(opts, reader=lambda _: "") is None


def test_status_bar_shows_hp_and_budget():
    bar = cli.status_bar({"party": [{"name": "Doran", "hp": 5, "max_hp": 20}],
                          "economy": {"p0": {"action": 1, "bonus": 0, "movement": 30}}})
    assert "5/20 HP" in bar and "Move: 30ft" in bar
