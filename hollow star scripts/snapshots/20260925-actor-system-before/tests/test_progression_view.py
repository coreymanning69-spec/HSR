from hollowstar.view_model import build_public_view


def test_public_view_accepts_persisted_progression_projection():
    view = build_public_view(
        {"room": {}, "status": "active"},
        progression={
            "rank": 3,
            "rank_xp": 8,
            "currency": 5,
            "upgrades": {"supplies": 1, "crafting": 0},
            "runs": {"run-a": {"status": "cleared"}},
        },
    )
    assert view["progression"]["hsr_rank"] == 3
    assert view["progression"]["currency"] == 5
    assert view["progression"]["upgrades"]["supplies"] == 1
    assert view["progression"]["settled_runs"] == ["run-a"]
