"""Focused tests for the authoritative Run service.

Run with: python3 tests/test_run_service.py
"""

from __future__ import annotations

import shutil
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.run_service import (RunService, RunServiceError,  # noqa: E402
                                    runtime_for, validate_launch)


def _service() -> tuple[RunService, Path]:
    # hollowstar.run_state.save_run refuses any target whose path does not
    # contain a ".local/reliquary_runs" segment (defense against run saves
    # drifting outside their designated root) -- so an isolated tempdir for
    # tests must still end in exactly that suffix.
    tmp = Path(tempfile.mkdtemp(prefix="hsr-run-service-"))
    return RunService(tmp / ".local" / "reliquary_runs"), tmp


def test_create_persists_and_summarizes() -> None:
    service, tmp = _service()
    try:
        summary = service.create("t1", ["Doran", "Wren"], ["Townsperson"], seed="seed-1")
        assert summary.run_id == "t1"
        assert summary.mode == "SIMULATION"
        assert summary.round_number == 0
        assert not summary.finished
        assert {a["name"] for a in summary.party} == {"Doran", "Wren"}
        assert {a["name"] for a in summary.opposition} == {"Townsperson"}
        assert (service.run_root / "t1.json").exists()
    finally:
        shutil.rmtree(tmp)


def test_create_rejects_duplicate_run_id() -> None:
    service, tmp = _service()
    try:
        service.create("dupe", ["Doran"], ["Townsperson"], seed="s")
        try:
            service.create("dupe", ["Wren"], ["Townsperson"], seed="s")
        except RunServiceError:
            pass
        else:
            raise AssertionError("duplicate run_id must be refused")
    finally:
        shutil.rmtree(tmp)


def test_create_rejects_unknown_actor_names() -> None:
    service, tmp = _service()
    try:
        try:
            service.create("bad-party", ["Nobody"], ["Townsperson"], seed="s")
        except RunServiceError:
            pass
        else:
            raise AssertionError("unknown party actor must be refused")
        try:
            service.create("bad-opp", ["Doran"], ["Nobody"], seed="s")
        except RunServiceError:
            pass
        else:
            raise AssertionError("unknown opposition actor must be refused")
    finally:
        shutil.rmtree(tmp)


def test_create_rejects_empty_rosters_and_bad_run_ids() -> None:
    service, tmp = _service()
    try:
        for bad_id in ("", "has space", "../escape", "a/b"):
            try:
                service.create(bad_id, ["Doran"], ["Townsperson"], seed="s")
            except RunServiceError:
                pass
            else:
                raise AssertionError(f"run_id {bad_id!r} must be refused")
        try:
            service.create("no-party", [], ["Townsperson"], seed="s")
        except RunServiceError:
            pass
        else:
            raise AssertionError("empty party must be refused")
    finally:
        shutil.rmtree(tmp)


def test_list_and_inspect_read_disk_without_prior_load() -> None:
    service, tmp = _service()
    try:
        service.create("t2", ["Doran"], ["Townsperson"], seed="s")
        assert service.list() == ["t2"]
        # A brand-new RunService instance has nothing in memory; inspect must
        # still work by reading the save file directly off disk.
        fresh = RunService(service.run_root)
        summary = fresh.inspect("t2")
        assert summary.run_id == "t2"
        try:
            fresh.inspect("missing")
        except RunServiceError:
            pass
        else:
            raise AssertionError("inspecting a nonexistent run must fail")
    finally:
        shutil.rmtree(tmp)


def test_load_rejects_a_save_with_a_foreign_run_identity() -> None:
    service, tmp = _service()
    try:
        service.create("owned", ["Doran"], ["Townsperson"], seed="s")
        path=service.run_root / "owned.json"
        data=json.loads(path.read_text(encoding="utf-8"));data["run_id"]="foreign"
        path.write_text(json.dumps(data), encoding="utf-8")
        fresh=RunService(service.run_root)
        try:
            fresh.load("owned")
        except RunServiceError as exc:
            assert "identity" in str(exc)
        else:
            raise AssertionError("foreign run identity must be refused")
    finally:
        shutil.rmtree(tmp)


def test_save_requires_the_run_to_be_loaded_first() -> None:
    service, tmp = _service()
    try:
        service.create("t3", ["Doran"], ["Townsperson"], seed="s")
        fresh = RunService(service.run_root)
        try:
            fresh.save("t3")
        except RunServiceError:
            pass
        else:
            raise AssertionError("saving an unloaded run must fail")
        fresh.load("t3")
        fresh.save("t3")  # now fine
    finally:
        shutil.rmtree(tmp)


def test_design_transitions_have_fallback_evidence() -> None:
    service, tmp = _service()
    try:
        service.create("evidence", ["Doran"], ["Townsperson"], seed="s")
        started=service.design_start("evidence")
        assert started["event"]["evidence"]["generated_lazily"] is True
        checked=service.design_action("evidence", {"type":"check_in"})
        assert checked["event"]["evidence"]["action"] == "check_in"
        fresh=RunService(service.run_root)
        assert fresh.observe("evidence")["events"][-1]["evidence"]["action"] == "check_in"
    finally:
        shutil.rmtree(tmp)


def test_load_restores_exact_state_across_service_instances() -> None:
    service, tmp = _service()
    try:
        service.create("t4", ["Doran", "Wren"], ["Townsperson"], seed="cross-instance")
        reloaded = RunService(service.run_root)
        summary = reloaded.load("t4")
        assert summary.seed == "cross-instance"
        assert {a["name"] for a in summary.party} == {"Doran", "Wren"}
    finally:
        shutil.rmtree(tmp)


def test_previous_room_recovery_preserves_state_and_records_a_receipt() -> None:
    service, tmp = _service()
    try:
        service.create("recovery", ["Doran"], ["Townsperson"], seed="recovery")
        service.design_start("recovery")
        run = service._active["recovery"]
        run.context["dungeon"]["rooms"]["1:1"]["resolved"] = True
        service.design_action("recovery", {"type": "exit"})
        run = service._active["recovery"]
        run.context.pop("combat", None)
        result = service.design_action("recovery", {"type": "recover_previous_room"})
        assert result["event"]["type"] == "previous_room_recovered"
        assert result["event"]["evidence"]["state_preserved"] is True
        assert (result["state"]["floor"], result["state"]["room"]["number"]) == (1, 1)
    finally:
        shutil.rmtree(tmp)


def main() -> None:
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"  ok  {test.__name__}")
    print(f"\n{len(tests)} run-service tests passed")


def test_forge_is_restricted_to_the_stewards() -> None:
    service, tmp = _service()
    try:
        # Doran and Wren are the Forge roster.
        assert service.create("forge-pair", ["Doran", "Wren"], ["Townsperson"], "s",
                              run_mode="FORGE", lead_selector="Doran")
        # Anyone else belongs in Sandbox, and the refusal says so.
        try:
            service.create("forge-outsider", ["Doran", "hsr:Cassian Ward"], ["Townsperson"], "s",
                           run_mode="FORGE", lead_selector="Doran")
        except RunServiceError as exc:
            assert "Cassian Ward" in str(exc) and "SANDBOX" in str(exc)
        else:
            raise AssertionError("Forge accepted a non-Steward party")
        # The same party is welcome in Sandbox.
        assert service.create("sandbox-outsider", ["hsr:Cassian Ward"], ["Townsperson"], "s",
                              run_mode="SANDBOX", lead_selector="hsr:Cassian Ward")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_forge_custom_launch_is_limited_to_authored_city() -> None:
    accepted = validate_launch(mode="FORGE", party=["custom:lead"], scenario="reliquary_city")
    assert accepted["launch_role"] == "CUSTOM"
    try:
        validate_launch(mode="FORGE", party=["custom:lead"], scenario="reliquary")
    except RunServiceError as exc:
        assert "reliquary_city" in str(exc)
    else:
        raise AssertionError("Story custom characters entered the champion route")


def test_runtime_routes_by_party() -> None:
    assert runtime_for(["Doran"]) == "FORGE"
    assert runtime_for(["Wren"]) == "FORGE"
    assert runtime_for(["divine:Doran", "Wren"]) == "FORGE"
    assert runtime_for(["hsr:Cassian Ward"]) == "SANDBOX"
    assert runtime_for(["Doran", "hsr:Kiyuru"]) == "SANDBOX"
    assert runtime_for(["custom:someone"]) == "SANDBOX"
    assert runtime_for([]) == "SANDBOX"


if __name__ == "__main__":
    main()
