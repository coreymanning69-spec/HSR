from hollowstar.host import HSRHost


def test_host_returns_shared_session_envelope_without_booting():
    host = HSRHost.from_options()
    response = host.handle({
        "id": "session-1",
        "command": "session_intent",
        "intent": "Start the game, let's do a sandbox",
    })
    assert response["ok"] is True
    assert response["result"]["session"] == {"type": "start", "mode": "SANDBOX"}
    assert host.booted is False


def test_host_rejects_untranslatable_session_text():
    host = HSRHost.from_options()
    response = host.handle({"id": "session-2", "command": "session_intent", "intent": "attack the hound"})
    assert response["ok"] is False
    assert response["error"]["code"] == "SESSION_INTENT_UNSUPPORTED"


def test_cli_parser_accepts_progression_readout_arguments():
    from hollowstar.cli import _parser
    args = _parser().parse_args(["readout", "--run-id", "demo", "--identity", "divine:Wren"])
    assert args.command == "readout"
    assert args.run_id == "demo"
    assert args.identity == "divine:Wren"
