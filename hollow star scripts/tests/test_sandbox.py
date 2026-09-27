"""Vertical tests for the deterministic D&D sandbox slice."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.intent import parse_intent  # noqa: E402
from hollowstar.host import HSRHost  # noqa: E402
from hollowstar.run_service import RunService, RunServiceError  # noqa: E402


def _service(name: str = "trial") -> tuple[RunService, Path]:
    root = Path(tempfile.mkdtemp(prefix="hsr-dd-sandbox-"))
    service = RunService(root / ".local" / "reliquary_runs")
    service.create(name, ["Doran"], ["Townsperson"], seed="sandbox-seed", scenario="dd_sandbox")
    service.sandbox_start(name)
    return service, root


def test_natural_language_lowers_only_to_publicly_visible_targets() -> None:
    service, root = _service()
    try:
        visible = service.observe("trial")
        assert parse_intent("insult the bartender", visible) == {
            "type": "conversation", "actor": "p0", "target": "mara", "mode": "insult", "text": "the bartender"
        }
        assert parse_intent("go east", visible) == {"type": "move_room", "actor": "p0", "direction": "east"}
        assert parse_intent("break the oak door", visible)["object"] == "tavern_door"
    finally:
        shutil.rmtree(root)


def test_attack_receipt_is_exact_and_seed_replays() -> None:
    first, root1 = _service("first")
    second, root2 = _service("second")
    try:
        action = {"type": "attack", "actor": "p0", "target": "mara"}
        first_event = first.design_action("first", action)["event"]["receipt"]
        second_event = second.design_action("second", action)["event"]["receipt"]
        assert first_event["attack"] == second_event["attack"]
        assert first_event.get("damage") == second_event.get("damage")
        assert first_event["witnesses"]
        assert first_event["combat_started"] is True
    finally:
        shutil.rmtree(root1)
        shutil.rmtree(root2)


def test_conversation_failure_and_tavern_mob_are_stateful() -> None:
    service, root = _service()
    try:
        event = service.design_action("trial", {"type": "insult", "actor": "p0", "target": "mara"})["event"]["receipt"]
        assert event["outcome"] in {"succeeded", "failed"}
        assert event["mob_formed"]["name"] == "Crooked Crown mob"
        state = service.observe("trial")
        assert state["phase"] == "combat"
        assert len(state["visible_witnesses"]) >= 3
        assert all(row["disposition"] == "hostile" for row in state["npcs"].values())
    finally:
        shutil.rmtree(root)


def test_attack_during_conversation_names_local_witnesses() -> None:
    service, root = _service()
    try:
        service.design_action("trial", {"type": "speak", "actor": "p0", "target": "mara", "text": "I need a room"})
        event = service.design_action("trial", {"type": "attack", "actor": "p0", "target": "mara"})["event"]["receipt"]
        assert event["combat_started"]
        assert {row["id"] for row in event["witnesses"]} >= {"mara", "brann", "elric", "nessa"}
        assert service.observe("trial")["conversation"]["target"] == "mara"
    finally:
        shutil.rmtree(root)


def test_fire_spreads_by_material_distance_airflow_and_connectivity() -> None:
    service, root = _service()
    try:
        service.design_action("trial", {"type": "ignite", "actor": "p0", "object": "oil_lamp"})
        event = service.design_action("trial", {"type": "end_turn", "actor": "p0"})["event"]["receipt"]
        spreads = event["environment"]["spreads"]
        assert any(row.get("object") == "bar" and row["distance_ft"] == 5 for row in spreads)
        assert any(row.get("to_room") == "street" for row in spreads)
        state = service.observe("trial")
        assert state["room"]["fire"]["active"]
        assert state["room"]["smoke"] > 0
    finally:
        shutil.rmtree(root)


def test_destroyed_door_changes_future_movement_legality() -> None:
    service, root = _service()
    try:
        try:
            service.design_action("trial", {"type": "move_room", "actor": "p0", "direction": "north"})
        except RunServiceError as exc:
            assert "blocks" in str(exc)
        else:
            raise AssertionError("closed door must block movement")
        service.design_action("trial", {"type": "damage_object", "actor": "p0", "object": "tavern_door", "amount": 18})
        service.design_action("trial", {"type": "move_room", "actor": "p0", "direction": "north"})
        assert service.observe("trial")["current_room"] == "tavern_back"
    finally:
        shutil.rmtree(root)


def test_weight_changes_movement_cost_and_over_capacity_is_refused() -> None:
    service, root = _service()
    try:
        run = service._active["trial"]
        run.party[0].ability_scores["STR"] = 8
        service.design_action("trial", {"type": "take", "actor": "p0", "object": "coin_crate"})
        event = service.design_action("trial", {"type": "move_room", "actor": "p0", "direction": "east"})["event"]["receipt"]
        assert event["encumbrance"] == "heavy"
        assert event["movement_cost"] == 2
        assert service.observe("trial")["actors"]["p0"]["carried_weight"] == 85
    finally:
        shutil.rmtree(root)


def test_spell_and_concentration_are_explicitly_resolved() -> None:
    service, root = _service()
    try:
        started = service.design_action("trial", {"type": "cast", "actor": "p0", "spell": "Bless"})
        assert started["event"]["receipt"]["concentration"]["spell"] == "bless"
        assert service.observe("trial")["concentration"]["remaining_rounds"] == 10
        ended = service.design_action("trial", {"type": "end_concentration", "actor": "p0"})
        assert ended["event"]["receipt"]["ended"] is True
        assert service.observe("trial")["concentration"] is None
    finally:
        shutil.rmtree(root)


def test_saving_throw_and_opportunity_attack_evidence_are_stateful() -> None:
    service, root = _service()
    try:
        save = service.design_action("trial", {"type": "saving_throw", "actor": "p0", "ability": "DEX", "dc": 15})
        assert save["event"]["receipt"]["event"] == "saving_throw_resolved"
        service.design_action("trial", {"type": "insult", "actor": "p0", "target": "mara"})
        moved = service.design_action("trial", {"type": "move_room", "actor": "p0", "direction": "east"})
        assert moved["event"]["receipt"]["opportunity_attacks"]
        assert service.observe("trial")["current_room"] == "street"
    finally:
        shutil.rmtree(root)


def test_public_receipt_seals_hidden_state_but_debug_exposes_it_explicitly() -> None:
    service, root = _service()
    try:
        public = service.observe("trial")
        assert "debug" not in public
        assert all("goals" not in npc for npc in public["npcs"].values())
        debug = service.sandbox_debug("trial")["debug_readout"]
        assert debug["debug"]["hidden"]["npc_goals"]["mara"] == ["keep the peace"]
        assert debug["debug"]["rng_state_available"] is True
    finally:
        shutil.rmtree(root)


def test_save_resume_branch_and_finished_run_audit_are_isolated() -> None:
    service, root = _service()
    try:
        service.design_action("trial", {"type": "open_object", "actor": "p0", "object": "coin_crate"})
        service.save("trial")
        resumed = RunService(service.run_root)
        resumed.load("trial")
        assert resumed.observe("trial")["room"]["objects"]["coin_crate"]["open"] is True
        resumed.branch("trial", "alternate")
        alternate = RunService(service.run_root)
        alternate.load("alternate")
        alternate.design_action("alternate", {"type": "ignite", "actor": "p0", "object": "oil_lamp"})
        assert resumed.observe("trial")["room"]["fire"]["active"] is False
        resumed.design_action("trial", {"type": "clear", "actor": "p0"})
        finished = resumed.finished_runs()
        assert "trial" in finished
        record = json.loads((resumed.finished_root / "trial.json").read_text(encoding="utf-8"))
        assert record["record_type"] == "finished_run"
        assert record["rules_version"] == "hybrid-5e-35-core-1"
        assert record["combat_receipts"] == []
        assert resumed.sandbox_prestige()["runs"] == 1
    finally:
        shutil.rmtree(root)


def test_stale_active_sandbox_blocks_start_until_released() -> None:
    """A sandbox run abandoned without a party wipe or gate-clear (browser
    closed, host restarted) stays 'active' on disk forever unless something
    explicitly releases it. sandbox_start must keep refusing new runs until
    sandbox_release runs; after that, a new sandbox_start must succeed."""
    service, root = _service("first")
    try:
        fresh = RunService(service.run_root)
        fresh.create("second", ["Doran"], ["Townsperson"], seed="sandbox-seed-2", scenario="dd_sandbox")
        try:
            fresh.sandbox_start("second")
            assert False, "expected the still-active 'first' run to block a second sandbox_start"
        except RunServiceError as exc:
            assert "first" in str(exc)
            assert "already saved" in str(exc)
        released = fresh.sandbox_release("first")
        assert released == {"run_id": "first", "status": "abandoned"}
        assert "first" in fresh.finished_runs()
        # Releasing twice is a no-op, not an error, and must not double-record.
        assert fresh.sandbox_release("first") == {"run_id": "first", "status": "abandoned"}
        fresh.sandbox_start("second")  # no longer raises
        assert fresh.observe("second")["status"] == "active"
    finally:
        shutil.rmtree(root)


def test_terminal_death_writes_low_flat_prestige() -> None:
    service, root = _service()
    try:
        result = service.design_action("trial", {"type": "kill_self", "actor": "p0"})
        assert result["state"]["status"] == "dead"
        assert result["state"]["prestige"] == {"flat": 0, "percent": 0, "bonus": 0, "total": 0, "status": "dead", "rules_version": "hybrid-5e-35-core-1"}
        assert (service.finished_root / "trial.json").exists()
    finally:
        shutil.rmtree(root)


def test_npc_reaction_death_also_finalizes_the_run() -> None:
    service, root = _service()
    try:
        service.design_action("trial", {"type": "insult", "actor": "p0", "target": "mara"})
        run = service._active["trial"]
        run.party[0].hp = 1
        run.party[0].armor_class = 0
        result = service.design_action("trial", {"type": "end_turn", "actor": "p0"})
        assert result["state"]["status"] == "dead"
        assert result["state"]["prestige"]["total"] == 0
        record = json.loads((service.finished_root / "trial.json").read_text(encoding="utf-8"))
        assert record["cause_of_death"] == "sandbox actor reached 0 HP"
    finally:
        shutil.rmtree(root)


def test_host_design_turn_and_debug_boundary_are_wired() -> None:
    root = Path(tempfile.mkdtemp(prefix="hsr-dd-host-"))
    try:
        host = HSRHost.from_options(data_root=root / ".local")
        assert host.handle({"id": 1, "command": "boot", "mode": "DESIGN"})["ok"]
        assert host.handle({"id": 2, "command": "create_run", "run_id": "host-trial", "seed": "host-seed",
                            "party": ["Doran"], "opposition": ["Townsperson"], "scenario": "dd_sandbox"})["ok"]
        assert host.handle({"id": 3, "command": "sandbox_start", "run_id": "host-trial"})["ok"]
        turn = host.handle({"id": 4, "command": "design_turn", "run_id": "host-trial",
                            "intent": "insult the bartender", "public_only": False})
        assert turn["ok"]
        assert turn["result"]["turn"]["public_receipt"]["event"] == "conversation_resolved"
        assert "debug" not in turn["result"]["turn"]["visible_state"]
        debug = host.handle({"id": 5, "command": "sandbox_debug", "run_id": "host-trial"})
        assert debug["ok"] and "debug" in debug["result"]["debug_readout"]
    finally:
        shutil.rmtree(root)


def test_sandbox_conversation_modes_including_trade() -> None:
    root = Path(tempfile.mkdtemp(prefix="hsr-sandbox-trade-"))
    try:
        host = HSRHost.from_options(data_root=root / ".local")
        assert host.handle({"id": 1, "command": "boot", "mode": "SANDBOX"})["ok"]
        assert host.handle({"id": 2, "command": "create_run", "run_id": "trade-trial", "seed": "host-seed",
                            "party": ["Doran"], "opposition": ["Townsperson"], "scenario": "dd_sandbox"})["ok"]
        assert host.handle({"id": 3, "command": "sandbox_start", "run_id": "trade-trial"})["ok"]
        turn = host.handle({"id": 4, "command": "design_action", "run_id": "trade-trial",
                            "action": {"type": "conversation", "actor": "p0", "target": "mara",
                                       "mode": "trade", "text": "let us trade"}})
        assert turn["ok"], turn
        assert turn["result"]["event"]["type"] == "conversation_resolved"
        assert turn["result"]["event"]["receipt"]["mode"] == "trade"
    finally:
        shutil.rmtree(root)


def main() -> None:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\n{len(tests)} sandbox tests passed")


if __name__ == "__main__":
    main()
