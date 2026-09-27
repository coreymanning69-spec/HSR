"""Run deterministic DESIGN rehearsals and emit a Phase 5 measurement report.

The report is disposable evidence: it writes only to the requested output path
and never changes canon, the handshake, Sandbox, or Forge state.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hollowstar.run_service import RunService
from hollowstar import dungeon, policies, tactical as t


def _action_for(run, strategy: str) -> dict:
    """Return a policy decision from visible state only."""
    if strategy == "baseline":
        return policies.exploration_action(run)
    if run.context.get("combat", {}).get("complete") is False:
        return policies.combat_action(run)
    row = dungeon.room(run)
    if row.get("resolved"):
        return {"type": "enter"}
    if row.get("kind") == "rest":
        return {"type": "rest", "safe": False}
    if row.get("kind") == "shop":
        product = "potion" if row.get("stock", {}).get("potion") is not None else "component"
        if row.get("purchases", []).count(product) < 3 and run.context["dungeon"].get("currency", 0) >= row["stock"][product]:
            return {"type": "buy", "product": product}
    # The adversarial lane spends no hidden information: it declines to
    # investigate first and accepts the engine's resulting escalation.
    if row.get("kind") in {"secret", "social", "hazard"}:
        return {"type": "avoid", "actor": "p0"}
    return {"type": "fight"}


def measure(seed: str, *, strategy: str = "baseline", run_mode: str = "DESIGN") -> dict:
    with tempfile.TemporaryDirectory(prefix="hsr-rehearsal-") as temp:
        service = RunService(Path(temp) / ".local" / "reliquary_runs", durable_saves=False)
        service.create("r", ["Doran", "Wren"], ["Townsperson"], seed, run_mode=run_mode)
        service.design_start("r")
        events, actions, steps = [], [], 0
        hp_loss = collections.Counter()
        room_actions = collections.Counter()
        while steps < 4000:
            run = service._active["r"]
            if run.context["dungeon"]["status"] != "active":
                break
            before_hp = {actor.name: actor.hp for actor in run.party}
            action = _action_for(run, strategy)
            if action.get("type") == "move":
                cost = t.move_cost(run, action["actor"], action["destination"])
                if cost is None or cost > t.economy(run, action["actor"])["movement"]:
                    raise RuntimeError("rehearsal policy proposed an unaffordable move")
            event = service.design_action("r", action, include_state=False)["event"]
            event = dict(event) if isinstance(event, dict) else {"type": None}
            event["floor"] = run.context["dungeon"].get("floor")
            event["requested_action"] = action.get("type")
            events.append(event)
            actions.append(action)
            loss = 0
            for actor in run.party:
                delta = max(0, before_hp[actor.name] - actor.hp)
                hp_loss[actor.name] += delta
                loss += delta
            event["hp_loss"] = loss
            room_actions[(str(event["floor"]), action.get("type"))] += 1
            steps += 1
        run = service._active["r"]
        dungeon = run.context["dungeon"]
        by_type = collections.Counter(str(event.get("type")) for event in events)
        floors = {}
        for event in events:
            floor = event.get("floor")
            if floor is None:
                continue
            row = floors.setdefault(str(floor), {"events": 0, "attrition": 0, "rests": 0, "rewards": 0,
                                                  "hp_loss": 0, "actions": {}})
            row["events"] += 1
            row["hp_loss"] += event.get("hp_loss", 0)
            if event.get("type") in {"damage", "attack", "hazard", "defense", "avoidance_failed"}:
                row["attrition"] += 1
            requested = event.get("requested_action")
            row["actions"][requested] = row["actions"].get(requested, 0) + 1
            if requested == "rest":
                row["rests"] += 1
            if event.get("type") in {"room_resolved", "purchase"} or event.get("result", {}).get("type") == "room_resolved":
                row["rewards"] += 1
        dungeon_state = run.context["dungeon"]
        progression = {"rank_xp": dungeon_state.get("rank_xp", 0),
                       "hsr_rank": dungeon_state.get("hsr_rank", 0)}
        return {
            "seed": seed,
            "strategy": strategy,
            "run_mode": run_mode,
            "steps": steps,
            "status": dungeon_state["status"],
            "rooms_cleared": dungeon_state.get("rooms_cleared", 0),
            "currency": dungeon_state.get("currency", 0),
            "components": dungeon_state.get("components", 0),
            "final_floor": dungeon_state.get("final_floor"),
            "party_alive": [actor.name for actor in run.party if actor.alive],
            "party_hp": {actor.name: actor.hp for actor in run.party},
            "hp_loss": dict(sorted(hp_loss.items())),
            "progression": progression,
            "pressure": {key: dungeon_state.get(key) for key in ("minutes", "fatigue", "light", "noise", "alert")},
            "room_actions": {f"{floor}:{kind}": count for (floor, kind), count in sorted(room_actions.items())},
            "event_counts": dict(sorted(by_type.items())),
            "floors": floors,
            "failures": (["step limit reached while run remained active"]
                         if steps >= 4000 and dungeon_state["status"] == "active" else []),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="append", dest="seeds")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    seeds = args.seeds or ["phase5-1", "phase5-2", "phase5-3"]
    report = {"schema": "hollow-star-phase5-report-1", "mode": "DESIGN", "runs": [measure(seed) for seed in seeds]}
    payload = json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
