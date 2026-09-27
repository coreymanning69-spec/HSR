"""Correctness tests for isolated Hollow Star run saves.

Run with: python3 tests/test_run_state.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.actors import Actor, Band
from hollowstar.combat import Encounter
from hollowstar.snapshot import import_party
from hollowstar.rng import RunRNG
from hollowstar.run_state import RunStateError, resume_run, save_run
from hollowstar.snapshot import CorpusWriteRefused


ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def isolated_save_path(run_id: str):
    """Keep standalone save tests out of either workspace .local tree."""
    with tempfile.TemporaryDirectory(prefix="hsr-run-state-") as temp:
        yield Path(temp) / ".local" / "reliquary_runs" / f"{run_id}.json"


def encounter() -> Encounter:
    roster, _ = import_party()
    enemy = Actor(
        name="Round-trip target",
        band=Band.HEROIC,
        max_hp=1000,
        hp=1000,
        armor_class=12,
        initiative_bonus=0,
    )
    return Encounter(
        party=[roster["Doran"], roster["Wren"]],
        opposition=[enemy],
        rng=RunRNG("round-trip-seed"),
    )


def test_save_resume_preserves_state_and_rng() -> None:
    original = encounter()
    original.run_round()
    original.party[0].hp = 123
    original.party[0].resources["action_surge"] = 1
    original.party[0].statuses["TEST_STATUS"] = 3
    original.party[0].equipment[0].temporary = True

    with isolated_save_path("test-round-trip") as path:
        save_run(original, "round-trip", path)
        resumed = resume_run(path)

    assert resumed.mode == "SIMULATION"
    assert resumed.round_number == original.round_number
    assert resumed.party[0].hp == 123
    assert resumed.party[0].resources["action_surge"] == 1
    assert resumed.party[0].statuses == {"TEST_STATUS": 3}
    assert resumed.party[0].equipment[0].temporary is True
    assert resumed.party[0].provenance.snapshot_version == original.party[0].provenance.snapshot_version
    assert resumed.transcript == original.transcript

    original.run_round()
    resumed.run_round()
    assert resumed.round_number == original.round_number
    assert resumed.rng.calls == original.rng.calls
    assert resumed.transcript == original.transcript
    assert [a.hp for a in resumed.party + resumed.opposition] == [
        a.hp for a in original.party + original.opposition
    ]


def test_rng_continuation_is_exact() -> None:
    current = encounter()
    current.rng.d20()
    with isolated_save_path("test-rng") as path:
        save_run(current, "rng", path)
        resumed = resume_run(path)
        assert resumed.rng.d20() == current.rng.d20()
        assert resumed.rng.calls == current.rng.calls


def test_invalid_schema_and_engine_fail_closed() -> None:
    with isolated_save_path("test-bad") as path:
        save_run(encounter(), "bad", path)
        data = json.loads(path.read_text(encoding="utf-8"))

        data["schema_version"] = "hollow-star-run-99"
        path.write_text(json.dumps(data), encoding="utf-8")
        try:
            resume_run(path)
        except RunStateError:
            pass
        else:
            raise AssertionError("schema mismatch must fail closed")

        data["schema_version"] = "hollow-star-run-1"
        data["engine_version"] = "99.0.0"
        path.write_text(json.dumps(data), encoding="utf-8")
        try:
            resume_run(path)
        except RunStateError:
            pass
        else:
            raise AssertionError("engine mismatch must fail closed")


def test_live_mode_and_corpus_writes_are_refused() -> None:
    live = encounter()
    live.mode = "LIVE"
    with isolated_save_path("test-live") as path:
        try:
            save_run(live, "live", path)
        except RunStateError:
            pass
        else:
            raise AssertionError("LIVE run saves must be refused")

    corpus_path = ROOT.parent / "divine mythos set" / "DM046_0.json"
    try:
        save_run(encounter(), "corpus", corpus_path)
    except CorpusWriteRefused:
        pass
    else:
        raise AssertionError("corpus writes must be refused")


def test_malformed_encoded_state_fails_closed() -> None:
    with isolated_save_path("test-malformed") as path:
        save_run(encounter(), "malformed", path)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["encounter"]["party"] = {"__dataclass__": "NotWhitelisted", "fields": {}}
        path.write_text(json.dumps(data), encoding="utf-8")
        try:
            resume_run(path)
        except RunStateError:
            pass
        else:
            raise AssertionError("unknown encoded dataclasses must fail closed")


def main() -> None:
    test_save_resume_preserves_state_and_rng()
    test_rng_continuation_is_exact()
    test_invalid_schema_and_engine_fail_closed()
    test_live_mode_and_corpus_writes_are_refused()
    test_malformed_encoded_state_fails_closed()
    print("5 run-state tests passed")


if __name__ == "__main__":
    main()
