"""Host-foundation tests; runnable without pytest."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
sys.path.insert(0, str(ROOT))

from hollowstar.host import HSRHost  # noqa: E402
from hollowstar.paths import HostPathError, resolve_paths  # noqa: E402
from hollowstar.protocol import run_stdio  # noqa: E402


def test_validation_status_returns_compact_pc_receipt() -> None:
    with tempfile.TemporaryDirectory() as temp:
        data_root = Path(temp) / ".local" / "reliquary_runs"
        job_root = data_root.parent / "validation_jobs"
        job_root.mkdir(parents=True)
        (job_root / "check-test123.json").write_text(json.dumps({
            "schema": 1, "job_id": "check-test123", "status": "completed",
            "started_at": "2026-09-06T00:00:00Z", "finished_at": "2026-09-06T00:01:00Z",
            "duration_seconds": 60.0, "exit_code": 0, "log_path": "secret-log-path",
            "summary": ["RESULT: CLEAN"],
        }), encoding="utf-8")
        host = HSRHost.from_options(WORKSPACE, data_root=data_root)
        assert host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})["ok"]
        result = host.handle({"id": "s", "command": "validation_status", "job_id": "check-test123"})
        assert result["ok"] is True
        receipt = result["result"]["validation"]
        assert receipt["status"] == "completed"
        assert receipt["summary"] == ["RESULT: CLEAN"]
        assert "log_path" not in receipt


def test_paths_are_workspace_based() -> None:
    paths = resolve_paths(WORKSPACE)
    assert paths.workspace_root == WORKSPACE.resolve()
    assert paths.hsr_root == ROOT.resolve()
    assert paths.snapshot_path.exists()
    assert paths.handshake_path == (ROOT / "HSR_HANDSHAKE.json").resolve()
    assert paths.run_root == (WORKSPACE / ".local" / "reliquary_runs").resolve()
    assert paths.profile_root == (WORKSPACE / ".local" / "reliquary_profiles").resolve()


def test_state_path_cannot_escape_or_enter_corpus() -> None:
    paths = resolve_paths(WORKSPACE)
    assert paths.assert_state_path(paths.run_root / "one.json") == paths.run_root / "one.json"
    for bad in (WORKSPACE / "divine mythos set" / "bad.md", WORKSPACE / "outside.json"):
        try:
            paths.assert_state_path(bad)
        except HostPathError:
            pass
        else:
            raise AssertionError(f"unsafe state path was accepted: {bad}")


def test_nonlocal_workspace_fails_closed() -> None:
    paths = resolve_paths(WORKSPACE)
    mounted = replace(paths, workspace_root=Path(r"C:\project-mount\Soliera and Sera v8.5"))
    report = mounted.local_location_report()
    assert report["approved"] is False
    try:
        mounted.assert_local_pc_workspace()
    except HostPathError:
        pass
    else:
        raise AssertionError("nonlocal project mount was accepted")


def test_host_modes_and_validation() -> None:
    host = HSRHost.from_options(WORKSPACE)
    assert host.handle({"id": "h", "command": "health"})["ok"] is True
    boot = host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
    assert boot["ok"] is True
    assert boot["result"]["context"]["story_markdown_loaded"] is False
    snapshot = host.handle({"id": "v", "command": "validate", "target": "snapshot"})
    assert snapshot["ok"] is True
    assert snapshot["result"]["snapshot"]["characters"] == ["Doran", "Wren"]
    sandbox = host.handle({"id": "s", "command": "boot", "mode": "SANDBOX"})
    assert sandbox["ok"] is True
    assert sandbox["result"]["capabilities"]["modes"]["SANDBOX"].startswith("available")
    forge = host.handle({"id": "f", "command": "boot", "mode": "FORGE", "intent": "threshold test"})
    assert forge["ok"] is True


def test_sandbox_and_forge_boots_are_isolated_and_mode_bound() -> None:
    with tempfile.TemporaryDirectory(prefix="hsr-mode-boundary-") as temp:
        data_root = Path(temp) / ".local" / "reliquary_runs"
        sandbox = HSRHost.from_options(WORKSPACE, data_root=data_root)
        assert sandbox.handle({"id": "b", "command": "boot", "mode": "SANDBOX"})["ok"]
        created = sandbox.handle({"id": "c", "command": "create_run", "run_id": "isolated-sandbox",
                                  "party": ["Doran"], "opposition": ["Townsperson"], "seed": 17,
                                  "module_id": "reliquary-template"})
        assert created["ok"] is True
        assert created["result"]["run"]["seed"] == "17"
        assert created["result"]["run"]["context"]["host_mode"] == "SANDBOX"
        assert sandbox.handle({"id": "s", "command": "design_start", "run_id": "isolated-sandbox"})["ok"]

        forge = HSRHost.from_options(WORKSPACE, data_root=Path(temp) / ".local" / "reliquary_runs")
        assert forge.handle({"id": "b", "command": "boot", "mode": "FORGE"})["error"]["code"] == "FORGE_INTENT_REQUIRED"
        assert forge.handle({"id": "b2", "command": "boot", "mode": "FORGE", "intent": "fixture"})["ok"]
        assert forge.handle({"id": "c2", "command": "create_run", "run_id": "isolated-forge",
                             "party": ["Doran"], "opposition": ["Townsperson"], "seed": 18,
                             "module_id": "reliquary-template"})["ok"]
        started = forge.handle({"id": "s2", "command": "design_start", "run_id": "isolated-forge"})
        assert started["ok"] is True
        # Forge is a playable authored threshold, not the generic tavern
        # sandbox. It stays non-canon through its receipt boundary.
        assert started["result"]["event"]["evidence"]["world_started"] is True
        assert started["result"]["event"]["evidence"]["non_canon"] is True
        assert started["result"]["state"]["room"]["title"] == "The First Threshold"
        assert started["result"]["state"]["party"][0]["name"] == "Doran"
        assert started["result"]["state"]["combat"]["actors"]["e0"]["name"]
        assert started["result"]["state"]["combat"]["complete"] is False
        completed = forge.handle({"id": "a", "command": "forge_action", "run_id": "isolated-forge",
                                  "action": {"type": "complete"}})
        assert completed["result"]["event"]["type"] == "forge_completed"
        assert completed["result"]["event"]["receipt"]["corpus_write"] is False


def _run_save_path(run_id: str) -> Path:
    return WORKSPACE / ".local" / "reliquary_runs" / f"{run_id}.json"


def _assert_no_nested_state(value) -> None:
    if isinstance(value, dict):
        forbidden = {"state", "visible_state", "debug", "debug_readout", "audit", "audit_events", "sealed_record"}
        overlap = forbidden & set(value)
        assert not overlap, overlap
        for item in value.values():
            _assert_no_nested_state(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_nested_state(item)


def test_run_commands_require_a_booted_host() -> None:
    host = HSRHost.from_options(WORKSPACE)
    for command in ("create_run", "load_run", "list_runs", "inspect_run", "save_run"):
        result = host.handle({"id": "x", "command": command, "run_id": "whatever"})
        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_BOOTED"


def test_profile_commands_use_the_same_host_and_share_the_mode_boundary() -> None:
    host = HSRHost.from_options(WORKSPACE)
    for command in ("create_profile", "update_profile", "list_profiles", "inspect_profile", "list_roster"):
        result = host.handle({"id": command, "command": command, "profile_id": "x"})
        assert result["ok"] is False
        assert result["error"]["code"] == "NOT_BOOTED"
    host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
    roster = host.handle({"id": "r", "command": "list_roster"})
    assert roster["ok"] is True
    assert {row["selector"] for row in roster["result"]["roster"] if row["kind"] == "divine_mythos"} == {"divine:Doran", "divine:Wren"}
    sandbox = host.handle({"id": "s", "command": "boot", "mode": "SANDBOX"})
    assert sandbox["ok"] is True


def test_create_load_list_inspect_save_round_trip() -> None:
    run_id = "host-test-round-trip"
    path = _run_save_path(run_id)
    if path.exists():
        path.unlink()
    try:
        host = HSRHost.from_options(WORKSPACE)
        host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})

        created = host.handle(
            {
                "id": "1",
                "command": "create_run",
                "run_id": run_id,
                "party": ["Doran", "Wren"],
                "opposition": ["Townsperson"],
                "seed": "host-test-seed",
            }
        )
        assert created["ok"] is True
        assert path.exists()
        assert {a["name"] for a in created["result"]["run"]["party"]} == {"Doran", "Wren"}

        listed = host.handle({"id": "2", "command": "list_runs"})
        assert run_id in listed["result"]["runs"]

        inspected = host.handle({"id": "3", "command": "inspect_run", "run_id": run_id})
        assert inspected["result"]["run"]["seed"] == "host-test-seed"

        # A second, freshly booted host must be able to load the same save --
        # this is the cross-process persistence the audit found missing.
        other = HSRHost.from_options(WORKSPACE)
        other.handle({"id": "b2", "command": "boot", "mode": "REVIEW"})
        loaded = other.handle({"id": "4", "command": "load_run", "run_id": run_id})
        assert loaded["ok"] is True
        assert loaded["result"]["run"]["round_number"] == 0

        saved = other.handle({"id": "5", "command": "save_run", "run_id": run_id})
        assert saved["ok"] is True

        duplicate = host.handle(
            {
                "id": "6",
                "command": "create_run",
                "run_id": run_id,
                "party": ["Doran"],
                "opposition": ["Townsperson"],
                "seed": "s",
            }
        )
        assert duplicate["ok"] is False
        assert duplicate["error"]["code"] == "RUN_INVALID"
    finally:
        if path.exists():
            path.unlink()


def test_retention_keeps_five_per_mode_prunes_validated_saves_and_preserves_history() -> None:
    with tempfile.TemporaryDirectory(prefix="hsr-retention-") as temp:
        root = Path(temp) / ".local"
        host = HSRHost.from_options(WORKSPACE, data_root=root)
        assert host.handle({"id": "boot", "command": "boot", "mode": "SANDBOX"})["ok"]
        for index in range(6):
            result = host.handle({
                "id": f"create-{index}", "command": "create_run", "mode": "SANDBOX",
                "run_id": f"sandbox-{index}", "party": ["Doran"],
                "opposition": ["Townsperson"], "scenario": "floor_one_life",
                "seed": f"retention-{index}",
            })
            assert result["ok"], result

        malformed = root / "reliquary_runs" / "malformed.json"
        malformed.write_text("not a run", encoding="utf-8")
        from hollowstar.progression import Progression, _default
        from hollowstar.storage import atomic_json
        progress = Progression(root / "reliquary_progress")
        account = _default("divine:Doran")
        account["tracking"]["rooms_cleared"] = 7
        account["runs"]["settled-example"] = {"outcome": "completed"}
        atomic_json(progress.path("divine:Doran"), account)
        listed = host.handle({"id": "list", "command": "list_runs"})
        assert listed["ok"]
        assert set(listed["result"]["runs"]) == {f"sandbox-{index}" for index in range(1, 6)}
        assert not (root / "reliquary_runs" / "sandbox-0.json").exists()
        assert malformed.exists()

        stats = host.handle({"id": "stats", "command": "statistics", "mode": "SANDBOX"})
        assert stats["ok"], stats
        assert len(stats["result"]["saves"]) == 5
        assert stats["result"]["last_run"]["summary"]["run_id"] == "sandbox-4"
        assert stats["result"]["last_run"]["pruned"] is False
        history = json.loads((root / "hsr_run_history.json").read_text(encoding="utf-8"))
        assert history["entries"]["sandbox-0"]["pruned"] is True
        assert history["entries"]["sandbox-0"]["summary"]["scenario"] == "floor_one_life"
        assert history["schema_version"] == "hollow-star-run-history-2"
        assert "rooms_cleared" not in history["entries"]["sandbox-0"].get("metrics", {})
        assert len(stats["result"]["all_runs"]) == 6
        assert stats["result"]["lifetime_accounts"][0]["tracking"]["rooms_cleared"] == 7
        assert stats["result"]["lifetime_accounts"][0]["settled_runs"] == 1
        old = host.handle({"id": "old-stats", "command": "statistics", "mode": "SANDBOX", "run_id": "sandbox-0"})
        assert old["ok"], old
        assert old["result"]["selected_run"]["pruned"] is True
        assert "selected_save" not in old["result"]

        before = host._session()
        original_load = host._load_run
        host._load_run = lambda request: (_ for _ in ()).throw(AssertionError("statistics loaded a run"))
        try:
            selected = host.handle({
                "id": "select", "command": "statistics", "mode": "SANDBOX", "run_id": "sandbox-5",
            })
        finally:
            host._load_run = original_load
        assert selected["ok"], selected
        assert selected["result"]["selected_save"]["summary"]["run_id"] == "sandbox-5"
        assert host._session() == before


def test_legacy_history_remains_retrievable_with_unknown_metrics() -> None:
    from hollowstar.run_history import RunHistory
    with tempfile.TemporaryDirectory(prefix="hsr-legacy-history-") as temp:
        root = Path(temp)
        path = root / "hsr_run_history.json"
        path.write_text(json.dumps({"schema_version": "hollow-star-run-history-1", "entries": {
            "old-run": {"run_id": "old-run", "mode": "SANDBOX", "status": "ended",
                        "summary": {"run_id": "old-run", "party": ["divine:Doran"]},
                        "ended_at": "2026-01-01T00:00:00Z", "pruned": True}}}), encoding="utf-8")
        result = RunHistory(root, root / "runs", None).statistics("SANDBOX")
        assert result["all_runs"][0]["run_id"] == "old-run"
        assert "metrics" not in result["all_runs"][0]


def test_run_metrics_copy_only_recorded_public_counters() -> None:
    from hollowstar.run_history import compact_public_metrics
    result = compact_public_metrics({"tracking": {"rooms_cleared": 4, "combat_rounds": 9,
                                                 "gold_earned": 20, "hidden_roll": 99,
                                                 "gold_spent": "unknown"},
                                     "terminal_receipt": {"outcome": "completed", "sealed_record": "secret"}})
    assert result == {"rooms_cleared": 4, "combat_rounds": 9, "gold_earned": 20,
                      "outcome": "completed"}


def test_retention_protects_an_active_save_even_when_it_is_not_newest() -> None:
    with tempfile.TemporaryDirectory(prefix="hsr-retention-active-") as temp:
        root = Path(temp) / ".local"
        host = HSRHost.from_options(WORKSPACE, data_root=root)
        assert host.handle({"id": "boot", "command": "boot", "mode": "SANDBOX"})["ok"]
        service = host._runs()
        summaries = [service.create(
            f"protected-{index}", ["Doran"], ["Townsperson"], f"protected-{index}",
            scenario="floor_one_life", run_mode="SANDBOX",
        ) for index in range(6)]
        host._record_session(summaries[0].as_dict())
        listed = host.handle({"id": "list", "command": "list_runs"})
        assert listed["ok"]
        assert "protected-0" in listed["result"]["runs"]
        assert len(listed["result"]["runs"]) == 5
        assert (root / "reliquary_runs" / "protected-0.json").exists()


def test_statistics_is_mode_scoped() -> None:
    with tempfile.TemporaryDirectory(prefix="hsr-statistics-modes-") as temp:
        root = Path(temp) / ".local"
        host = HSRHost.from_options(WORKSPACE, data_root=root)
        assert host.handle({"id": "sb", "command": "boot", "mode": "SANDBOX"})["ok"]
        assert host.handle({
            "id": "sbr", "command": "create_run", "mode": "SANDBOX", "run_id": "sandbox-only",
            "party": ["Doran"], "opposition": ["Townsperson"], "scenario": "floor_one_life", "seed": "sb",
        })["ok"]
        assert host.handle({"id": "fg", "command": "boot", "mode": "FORGE", "intent": "story"})["ok"]
        assert host.handle({
            "id": "fgr", "command": "create_run", "mode": "FORGE", "run_id": "story-only",
            "party": ["Doran"], "opposition": ["Townsperson"], "scenario": "reliquary", "seed": "fg",
        })["ok"]
        story = host.handle({"id": "story-stats", "command": "statistics", "mode": "FORGE"})
        simulation = host.handle({"id": "sim-stats", "command": "statistics", "mode": "SANDBOX"})
        assert [row["run_id"] for row in story["result"]["saves"]] == ["story-only"]
        assert [row["run_id"] for row in simulation["result"]["saves"]] == ["sandbox-only"]


def test_create_run_validates_input_shape() -> None:
    host = HSRHost.from_options(WORKSPACE)
    host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
    bad_requests = [
        {"run_id": "x", "party": "Doran", "opposition": ["Townsperson"], "seed": "s"},
        {"run_id": "x", "party": ["Doran"], "opposition": [], "seed": "s"},
        {"run_id": "x", "party": ["Doran"], "opposition": ["Townsperson"], "seed": ""},
        {"run_id": "x", "party": ["Nobody"], "opposition": ["Townsperson"], "seed": "s"},
    ]
    for payload in bad_requests:
        result = host.handle({"id": "r", "command": "create_run", **payload})
        assert result["ok"] is False, payload
        assert not _run_save_path("x").exists()


def test_gameplay_commands_stay_blocked_alongside_run_management() -> None:
    host = HSRHost.from_options(WORKSPACE)
    host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
    for command in ("start_run", "resume_run", "apply_action"):
        result = host.handle({"id": command, "command": command})
        assert result["ok"] is False
        assert result["error"]["code"] == "UNSUPPORTED_OPERATION"
    caps = host.handle({"id": "c", "command": "inspect", "target": "capabilities"})
    assert caps["result"]["capabilities"]["run_management"] is True
    assert caps["result"]["capabilities"]["gameplay"] is True


def test_design_turn_persists_intent_and_returns_narrator_safe_state() -> None:
    run_id = "host-test-design-turn"
    path = _run_save_path(run_id)
    if path.exists():
        path.unlink()
    try:
        host = HSRHost.from_options(WORKSPACE)
        host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
        created = host.handle({
            "id": "c", "command": "create_run", "run_id": run_id,
            "party": ["Doran", "Wren"], "opposition": ["Townsperson"], "seed": "turn-seed",
        })
        assert created["ok"] is True
        assert host.handle({"id": "s", "command": "design_start", "run_id": run_id})["ok"] is True
        turn = host.handle({
            "id": "t", "command": "design_turn", "run_id": run_id,
            "intent": "I want to study the room before committing.",
            "action": {"type": "investigate", "actor": "p0"},
            "public_only": False,
        })
        assert turn["ok"] is True
        payload = turn["result"]["turn"]
        assert payload["player_intent"] == "I want to study the room before committing."
        room_view = payload["visible_state"]["room"]
        assert "perceived_facts" in room_view
        assert "secret" not in room_view
        assert "motive" not in room_view
        assert "counterplay" not in room_view
        assert payload["narrator"]["source"] == "host-returned visible state only"
        readout = host.handle({"id": "r", "command": "readout", "run_id": run_id, "public_only": False})
        assert readout["ok"] is True
        loaded = HSRHost.from_options(WORKSPACE)
        loaded.handle({"id": "b2", "command": "boot", "mode": "DESIGN"})
        assert loaded.handle({"id": "l", "command": "load_run", "run_id": run_id})["ok"] is True
        events = loaded._runs()._active[run_id].context["dungeon"]["events"]
        assert events[-1]["player_intent"] == "I want to study the room before committing."
    finally:
        if path.exists():
            path.unlink()


def test_design_turn_room_resolution_is_flat_and_receipted() -> None:
    run_id = "host-test-flat-resolution"
    path = _run_save_path(run_id)
    if path.exists():
        path.unlink()
    try:
        host = HSRHost.from_options(WORKSPACE)
        host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
        assert host.handle({"id": "c", "command": "create_run", "run_id": run_id,
                            "party": ["Doran", "Wren"], "opposition": ["Townsperson"],
                            "seed": "flat-resolution-seed"})["ok"]
        assert host.handle({"id": "s", "command": "design_start", "run_id": run_id})["ok"]
        run = host._runs()._active[run_id]
        run.party[0].skill_bonuses["Persuasion"] = 100

        result = host.handle({"id": "t", "command": "design_turn", "run_id": run_id,
                              "intent": "negotiate with the wellkeeper",
                              "action": {"type": "negotiate", "actor": "p0"}})

        assert result["ok"] is True
        turn = result["result"]["turn"]
        assert turn["outcome"]["type"] == "room_resolved"
        assert turn["outcome"]["method"] == "negotiate"
        assert "result" not in turn["outcome"]
        assert turn["public_receipt"]["type"] == "room_resolved"
        assert turn["public_receipt"]["method"] == "negotiate"
    finally:
        if path.exists():
            path.unlink()


def test_short_object_ids_only_resolve_visible_objects() -> None:
    run_id = "host-test-visible-object-ids"
    path = _run_save_path(run_id)
    if path.exists():
        path.unlink()
    try:
        host = HSRHost.from_options(WORKSPACE)
        host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
        assert host.handle({"id": "c", "command": "create_run", "run_id": run_id,
                            "party": ["Doran", "Wren"], "opposition": ["Townsperson"],
                            "seed": "visible-object-seed"})["ok"]
        assert host.handle({"id": "s", "command": "design_start", "run_id": run_id})["ok"]

        hidden = host.handle({"id": "h", "command": "design_action", "run_id": run_id,
                              "action": {"type": "open_object", "object_id": "cabinet"}})
        assert hidden["ok"] is False
        assert hidden["error"]["code"] == "ACTION_INVALID"

        visible = host.handle({"id": "v", "command": "design_action", "run_id": run_id,
                               "action": {"type": "inspect_object", "object_id": "bar"}})
        assert visible["ok"] is True
        assert visible["result"]["event"]["object"]["object_id"] == "1:1:bar"
    finally:
        if path.exists():
            path.unlink()


def test_readout_projects_recent_public_receipt_and_narration() -> None:
    run_id = "host-test-readout-receipt"
    path = _run_save_path(run_id)
    if path.exists():
        path.unlink()
    try:
        host = HSRHost.from_options(WORKSPACE)
        host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
        assert host.handle({"id": "c", "command": "create_run", "run_id": run_id,
                            "party": ["Doran", "Wren"], "opposition": ["Townsperson"],
                            "seed": "readout-receipt-seed"})["ok"]
        assert host.handle({"id": "s", "command": "design_start", "run_id": run_id})["ok"]
        assert host.handle({"id": "o", "command": "design_action", "run_id": run_id,
                            "action": {"type": "observe_room"}})["ok"]

        readout = host.handle({"id": "r", "command": "readout", "run_id": run_id})

        assert readout["ok"] is True
        payload = readout["result"]["readout"]
        assert payload["public_receipt"]["physical_observation"] is True
        assert payload["public_view"]["narration"]
        assert payload["public_view"]["room"]["resolved"] is False
        assert payload["public_view"]["room"]["reward_claimed"] is False
    finally:
        if path.exists():
            path.unlink()


def test_perceived_and_sealed_room_payloads_are_separate_and_receipted() -> None:
    run_id = "host-test-payload-split"
    path = _run_save_path(run_id)
    if path.exists():
        path.unlink()
    try:
        host = HSRHost.from_options(WORKSPACE)
        host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
        assert host.handle({"id": "c", "command": "create_run", "run_id": run_id,
                            "party": ["Doran", "Wren"], "opposition": ["Townsperson"],
                            "seed": "payload-split-seed"})["ok"]
        assert host.handle({"id": "s", "command": "design_start", "run_id": run_id})["ok"]

        observed = host.handle({"id": "o", "command": "observe", "run_id": run_id})
        room_view = observed["result"]["state"]["room"]
        assert "secret" not in room_view
        assert "function" not in room_view
        assert "motive" not in room_view
        assert "counterplay" not in room_view

        tested = host.handle({"id": "p", "command": "test-perception", "run_id": run_id,
                              "actor": "p0", "tell_id": room_view["tells"][0]["id"]})
        assert tested["ok"] is True
        assert "secret" not in tested["result"]["visible_state"]["room"]

        revealed = host.handle({"id": "r", "command": "reveal-room-record", "run_id": run_id})
        assert revealed["ok"] is True
        assert "sealed_record" in revealed["result"]["outcome"]
        assert "secret" in revealed["result"]["outcome"]["sealed_record"]
        assert revealed["result"]["outcome"]["evidence"]["explicit_fetch"] is True

        readout = host.handle({"id": "q", "command": "readout", "run_id": run_id, "public_only": False})
        readout_json = json.dumps(readout["result"]["readout"]["visible_state"])
        assert '"sealed_record"' not in readout_json
        receipt = host._runs()._active[run_id].context["dungeon"]["receipts"][-1]
        assert receipt["command"] == "reveal-room-record"
        assert receipt["sealed_record"]["secret"]
    finally:
        if path.exists():
            path.unlink()


def test_design_turn_translates_intent_when_action_is_omitted() -> None:
    run_id = "host-test-intent-only"
    path = _run_save_path(run_id)
    if path.exists():
        path.unlink()
    try:
        host = HSRHost.from_options(WORKSPACE)
        host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
        assert host.handle({"id": "c", "command": "create_run", "run_id": run_id,
                            "party": ["Doran", "Wren"], "opposition": ["Townsperson"],
                            "seed": "intent-only-seed"})["ok"]
        assert host.handle({"id": "s", "command": "design_start", "run_id": run_id})["ok"]
        result = host.handle({"id": "t", "command": "design_turn", "run_id": run_id,
                              "intent": "investigate", "public_only": True})
        assert result["ok"] is True
        turn = result["result"]["turn"]
        assert turn["action"] == {"type": "investigate"}
        assert "visible_state" not in turn
        assert turn["public_view"]["room"]["resident"] == "Wellkeeper"
    finally:
        if path.exists():
            path.unlink()


def test_design_turn_inspect_is_read_only_and_visible_only() -> None:
    run_id = "host-test-inspect-intent"
    path = _run_save_path(run_id)
    if path.exists():
        path.unlink()
    try:
        host = HSRHost.from_options(WORKSPACE)
        host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
        host.handle({"id": "c", "command": "create_run", "run_id": run_id,
                     "party": ["Doran", "Wren"], "opposition": ["Townsperson"], "seed": "inspect-seed"})
        host.handle({"id": "s", "command": "design_start", "run_id": run_id})
        result = host.handle({"id": "t", "command": "design_turn", "run_id": run_id, "intent": "inspect"})
        assert result["ok"] is True
        turn = result["result"]["turn"]
        assert "visible_state" not in turn
        assert turn["outcome"]["evidence"]["read_only"] is True
        assert turn["outcome"]["evidence"]["state_embedded"] is False
        _assert_no_nested_state(turn["outcome"])
        _assert_no_nested_state(turn["public_view"]["last_event"])
        _assert_no_nested_state(turn["public_view"]["recent_receipts"])
        # Guards against the turn embedding full state, not a tight wire budget.
        # Raised from 10000 when per-item visual metadata (rarity, silhouette,
        # material, fx, handedness and animation profile joined the public
        # equipment projection, then by 30% (12500 -> 16250) on 2026-09-23
        # after the attunement and contextual-action fields left ~60 bytes.
        assert len(json.dumps(turn, separators=(",", ":"))) < 16250
    finally:
        if path.exists():
            path.unlink()


def test_design_turn_party_status_is_a_read_only_public_query() -> None:
    run_id = "host-test-party-status"
    path = _run_save_path(run_id)
    if path.exists():
        path.unlink()
    try:
        host = HSRHost.from_options(WORKSPACE)
        host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
        host.handle({"id": "c", "command": "create_run", "run_id": run_id,
                     "party": ["Doran"], "opposition": ["Townsperson"], "seed": "status-seed"})
        host.handle({"id": "s", "command": "design_start", "run_id": run_id})
        result = host.handle({"id": "q", "command": "design_turn", "run_id": run_id,
                              "intent": "party status"})
        assert result["ok"] is True
        turn = result["result"]["turn"]
        assert turn["action"] == {"type": "query", "data": "party_status"}
        assert turn["public_receipt"]["read_only"] is True
        assert turn["public_view"]["run_id"] == run_id
    finally:
        if path.exists():
            path.unlink()


def test_design_turn_debug_state_is_explicit_bounded_and_content_free() -> None:
    run_id = "host-test-bounded-narrator-state"
    path = _run_save_path(run_id)
    if path.exists():
        path.unlink()
    try:
        host = HSRHost.from_options(WORKSPACE)
        host.handle({"id": "b", "command": "boot", "mode": "DESIGN"})
        host.handle({"id": "c", "command": "create_run", "run_id": run_id,
                     "party": ["Doran", "Wren"], "opposition": ["Townsperson"],
                     "seed": "bounded-state-seed"})
        host.handle({"id": "s", "command": "design_start", "run_id": run_id})
        default = host.handle({"id": "t-default", "command": "design_turn", "run_id": run_id,
                               "intent": "inspect"})
        assert default["ok"] is True
        assert "visible_state" not in default["result"]["turn"]
        result = host.handle({"id": "t", "command": "design_turn", "run_id": run_id,
                              "intent": "inspect", "public_only": False})
        assert result["ok"] is True
        turn = result["result"]["turn"]
        assert turn["narrator"]["narration_source_block"] == "public_view"
        assert "content" not in turn["visible_state"]
        assert len(turn["visible_state"].get("events", [])) <= 5
        assert turn["public_view"]["schema"] == "hollow-star-public-view-1"
    finally:
        if path.exists():
            path.unlink()


def test_stdio_protocol_is_one_response_per_request() -> None:
    incoming = io.StringIO(
        '{"id":"1","command":"health"}\n'
        'not-json\n'
        '{"id":"2","command":"inspect","target":"capabilities"}\n'
        '{"id":"3","command":"shutdown"}\n'
    )
    outgoing = io.StringIO()
    code = run_stdio(HSRHost.from_options(WORKSPACE), incoming, outgoing)
    assert code == 0
    rows = [json.loads(line) for line in outgoing.getvalue().splitlines()]
    assert len(rows) == 4
    assert rows[0]["ok"] is True
    assert rows[1]["error"]["code"] == "INVALID_REQUEST"
    assert rows[2]["result"]["capabilities"]["natural_language_parsing"] == "deterministic command translation"
    assert rows[3]["result"]["shutdown"] is True


def test_path_independent_launcher_from_workspace_root() -> None:
    launcher = ROOT / "hollowstar_host.py"
    result = subprocess.run(
        [sys.executable, str(launcher), "health"],
        cwd=WORKSPACE,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["engine_version"] == "0.2.2"


def test_inspect_modules_lists_validated_template() -> None:
    host = HSRHost.from_options(WORKSPACE)
    result = host.handle({"id": "modules", "command": "inspect_modules"})
    assert result["ok"] is True
    assert result["result"]["modules"][0]["module_id"] == "reliquary-template"


def test_path_independent_launcher_from_another_working_directory() -> None:
    launcher = ROOT / "hollowstar_host.py"
    other_cwd = Path.home()
    result = subprocess.run(
        [sys.executable, str(launcher), "validate", "--target", "snapshot"],
        cwd=other_cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["result"]["snapshot"]["seed_mode"] == "SIMULATION"


def main() -> None:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    main()


def test_scenario_catalog_lists_only_launchable_scenarios() -> None:
    from hollowstar.run_service import RunService

    with tempfile.TemporaryDirectory() as temp:
        host = HSRHost.from_options(WORKSPACE, data_root=Path(temp) / ".local" / "reliquary_runs")
        # Answerable before boot: the picker is a content description, not a run.
        reply = host.handle({"id": "s", "command": "scenario_catalog"})
        assert reply["ok"] is True, reply
        rows = reply["result"]["scenarios"]
        assert {row["scenario"] for row in rows} == RunService.SCENARIOS
        assert all(row["title"] and row["blurb"] and row["modes"] for row in rows)

        narrowed = host.handle({"id": "s2", "command": "scenario_catalog", "mode": "SANDBOX"})
        offered = {row["scenario"] for row in narrowed["result"]["scenarios"]}
        assert offered and offered <= RunService.SCENARIOS
        assert "reliquary" not in offered  # Story Mode's authored module is not a Simulation surface
        bad = host.handle({"id": "s3", "command": "scenario_catalog", "mode": 7})
        assert bad["ok"] is False and bad["error"]["code"] == "INVALID_REQUEST"


def test_every_offered_scenario_creates_a_run() -> None:
    """Nothing may be offered in the menu that create() would then reject."""
    from hollowstar.run_service import RunService

    with tempfile.TemporaryDirectory() as temp:
        run_root = Path(temp) / ".local" / "reliquary_runs"
        run_root.mkdir(parents=True)
        service = RunService(run_root, module_root=Path(__file__).parents[1] / "hollowstar" / "content" / "modules")
        for row in RunService.scenario_catalog("SANDBOX"):
            summary = service.create(
                f"pick-{row['scenario'].replace('_', '-')}", ["Doran"], ["Townsperson"],
                "scenario-menu-seed", scenario=row["scenario"], run_mode="SANDBOX",
            )
            assert summary.as_dict()["context"]["scenario"] == row["scenario"]


def test_start_run_enforces_launch_roles_before_creating_state() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / ".local"
        host = HSRHost.from_options(WORKSPACE, data_root=root)
        assert host.handle({"id": "boot", "command": "boot", "mode": "FORGE", "intent": "story"})["ok"]
        rejected = host.handle({
            "id": "custom-forge", "command": "start-run", "mode": "FORGE",
            "run_id": "should-not-exist", "party": ["custom:missing"],
            "lead_selector": "custom:missing", "opposition": ["Townsperson"],
            "scenario": "reliquary", "module_id": "reliquary-template", "seed": "role-test",
        })
        assert rejected["ok"] is False
        assert rejected["error"]["code"] == "LAUNCH_INVALID"
        assert "reliquary_city" in rejected["error"]["message"]
        assert not (root / "reliquary_runs" / "should-not-exist.json").exists()


def test_start_run_infers_sandbox_for_custom_profiles_and_forge_for_champions() -> None:
    from hollowstar.run_service import runtime_for

    assert runtime_for(["Doran"]) == "FORGE"
    assert runtime_for(["Wren"]) == "FORGE"
    assert runtime_for(["custom:lead"]) == "SANDBOX"
    assert runtime_for(["hsr:Cassian Ward"]) == "SANDBOX"
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / ".local"
        host = HSRHost.from_options(WORKSPACE, data_root=root)
        assert host.handle({"id": "boot", "command": "boot", "mode": "DESIGN"})["ok"]
        build = {"name": "Sandbox Lead", "creation_seed": "sandbox-role", "background": "scout"}
        preview = host.handle({"id": "preview", "command": "preview_character", "build": build})
        assert preview["ok"]
        saved = host.handle({
            "id": "save", "command": "build_character", "profile_id": "sandbox-lead",
            "build": build, "expected_build_hash": preview["result"]["character"]["build_hash"],
        })
        assert saved["ok"]
        started = host.handle({
            "id": "implicit-sandbox", "command": "start-run", "run_id": "implicit-sandbox",
            "party": ["custom:sandbox-lead"], "lead_selector": "custom:sandbox-lead",
            "opposition": ["Townsperson"], "seed": "implicit-role",
        })
        assert started["ok"], started
        assert started["result"]["run"]["context"]["host_mode"] == "SANDBOX"


def test_start_run_routes_life_scenarios_and_serializes_descent() -> None:
    for scenario in ("floor_one_life", "reliquary_city"):
        with tempfile.TemporaryDirectory() as temp:
            host = HSRHost.from_options(WORKSPACE, data_root=Path(temp) / ".local")
            run_id = f"route-{scenario}"
            started = host.handle({
                "id": "start", "command": "start-run", "mode": "SANDBOX",
                "run_id": run_id, "party": ["Doran"], "lead_selector": "Doran",
                "opposition": ["Townsperson"], "seed": "route-seed",
                "scenario": scenario,
            })
            assert started["ok"], started
            assert started["result"]["start"]["public_view"]["room"]["id"] == "market"
            json.dumps(started)
            travel = host.handle({"id": "travel", "command": "auto_travel",
                                  "run_id": run_id, "destination": "well"})
            assert travel["ok"], travel
            descended = host.handle({"id": "descend", "command": "design_action",
                                     "run_id": run_id, "action": {"type": "descend"}})
            assert descended["ok"], descended
            assert descended["result"]["event"]["type"] == (
                "entered" if scenario == "reliquary_city" else "descent_started")
            assert descended["result"]["public_view"]["room"]
            json.dumps(descended)
