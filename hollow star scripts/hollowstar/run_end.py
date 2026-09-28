"""The one guaranteed "this run is over" pipeline.

Every consequence of a run ending happens here, in order, exactly once per run:
  1. settle account progression (Platinum, rank, loop tier) for each party member
  2. fold the run into the Hollow Star's memory
  3. emit ``run_ended`` on the story event bus
  4. report which cutscenes became newly available, for the client to queue

Idempotent: calling it again for the same run returns the same shape without
re-awarding anything (each step is individually idempotent).
"""
from __future__ import annotations

from pathlib import Path

from hollowstar.star_memory import StarMemory, awareness
from hollowstar.story_state import StoryState

TERMINAL = {"cleared", "defeated", "ejected", "escaped"}


def finalize(progress_root: Path, run_id: str, run) -> dict:
    from hollowstar.progression import Progression
    d = run.context.get("dungeon") or {}
    status = d.get("status")
    if status not in TERMINAL:
        raise ValueError("run has not ended")
    progress = Progression(progress_root)
    star = StarMemory(progress_root)
    story = StoryState(progress_root)
    before = star.view()
    already = run_id in before["settled_run_ids"]

    settled, errors, receipt = {}, [], None
    for selector in run.context.get("party_selectors", []):
        identity = selector if ":" in selector else "divine:" + selector
        try:
            account = progress.settle(identity, run_id, run)
            settled[identity] = {"platinum": account["platinum"], "loop_tier": account["loop_tier"], "rank": account["rank"]}
            receipt = receipt or account["runs"].get(run_id)
        except (ValueError, OSError) as exc:  # one bad account never blocks the rest
            errors.append({"identity": identity, "error": str(exc)})

    lead = next(iter(settled), None) or (run.context.get("account_identity") or "unknown")
    receipt = receipt or {"outcome": "completed" if status == "cleared" else "dead", "status": status,
                          "rooms": d.get("rooms_cleared", 0)}
    after = star.record_run(run_id, lead, receipt, {"name": lead.split(":", 1)[-1]})
    ladder = {}
    from hollowstar.unlock_ladder import UnlockLadder, champion_of
    unlocks = UnlockLadder(progress_root)
    for selector in run.context.get("party_selectors", []):
        champ = None if str(selector).startswith("custom:") else champion_of(selector)
        if champ:
            ladder[champ] = unlocks.credit(champ, run_id, d.get("rooms_cleared", 0))
    if d.get("star_reveal"):
        after = star.set_flag("star_revealed")
    if not already:
        if d.get("star_reveal"):
            story.emit("star_revealed", {"run_id": run_id, "survivors": d["star_reveal"].get("survivors", [])})
        story.emit("run_ended", {"run_id": run_id, "status": status, "outcome": receipt.get("outcome"),
                                 "floor": d.get("floor"), "rooms": d.get("rooms_cleared", 0)})
    return {"run_id": run_id, "already_finalized": already, "settled": settled, "errors": errors,
            "star": after, "awareness_before": awareness(before), "awareness_after": after["awareness"],
            "ladder": ladder, "star_revealed": bool(d.get("star_reveal")),
            "meta_shop_newly_unlocked": after["meta_shop_unlocked"] and not before["meta_shop_unlocked"],
            "story": story.load()}
