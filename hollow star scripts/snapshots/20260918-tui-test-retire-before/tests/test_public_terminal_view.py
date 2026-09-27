from hollowstar.session_screen import SessionScreen


def test_terminal_room_readout_uses_public_affordances_and_receipts():
    output = SessionScreen.render_dungeon({
        "room": {"title": "Hall", "terrain": "stone", "law": "quiet", "tells": []},
        "status": "active",
        "combat": {"complete": True, "round": 1, "current": "p0", "actors": {}, "positions": {},
                   "order": [], "economy": {}, "pending": []},
        "events": [{"event": "room_observation"}],
        "available_actions": [{"id": "inspect", "label": "Inspect"}],
    })
    assert "Actions: Inspect" in output
    assert "Recent: room_observation" in output
