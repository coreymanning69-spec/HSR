import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.session_intent import parse_session_intent


def test_session_start_phrases_select_mode():
    assert parse_session_intent("Start the game") == {"type": "start", "mode": "DESIGN"}
    assert parse_session_intent("Start the game, let's do a sandbox") == {"type": "start", "mode": "SANDBOX"}
    assert parse_session_intent("I am new here") == {"type": "start", "mode": "DESIGN"}
    assert parse_session_intent("This is my first time") == {"type": "start", "mode": "DESIGN"}


def test_session_show_and_auto_commands_are_ui_neutral():
    assert parse_session_intent("Show my equipment") == {"type": "show", "target": "equipment"}
    assert parse_session_intent("turn off auto") == {"type": "set_auto", "enabled": False}


def test_gameplay_text_is_left_for_the_gameplay_parser():
    assert parse_session_intent("attack the hound") is None


def test_natural_language_run_and_character_phrases_are_session_intents():
    assert parse_session_intent("Let's start a run") == {"type": "start", "mode": "DESIGN"}
    assert parse_session_intent("begin a run") == {"type": "start", "mode": "DESIGN"}
    assert parse_session_intent("make a character") == {"type": "start", "mode": "DESIGN", "lead": "custom"}
    assert parse_session_intent("load my saved run") == {"type": "load"}


def test_session_phrases_do_not_steal_gameplay_sentences():
    assert parse_session_intent("look around and attack the hound") is None


def test_qol_navigation_recovery_and_selection_phrases_are_deterministic():
    assert parse_session_intent("Show me the options") == {"type": "options"}
    assert parse_session_intent("I'm stuck") == {"type": "recover_previous_room"}
    assert parse_session_intent("Wrong option") == {"type": "back"}
    assert parse_session_intent("I pick Wren") == {"type": "select", "choice": "wren"}
