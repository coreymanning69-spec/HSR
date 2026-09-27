#!/usr/bin/env python3
"""Hollow Star resident-population and reaction simulator.

Standalone. Imports nothing from `hollowstar` and mutates no engine state.
Its only job is to answer one question before any engine work is done:
given eight authored residents plus generated filler, how much does a room
actually vary between runs -- and does it still feel like the same place?

Deterministic: every roll derives from `RunRNG(seed).fork(label)`, mirroring
the engine's own forking discipline so results are reproducible per seed.

Usage:
    python3 sim_residents.py --runs 200 --floor 1 --room-kind social
    python3 sim_residents.py --detail 8            # print 8 readable rooms
    python3 sim_residents.py --species-compare     # human vs goblin vs wolf
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
# tools/ sits beside hollowstar/, so the content dir is one level up.
DEFAULT_CONTENT = next(
    (p for p in (HERE.parent / "hollowstar" / "content" / "residents.json",
                 HERE / "residents.json") if p.exists()),
    HERE.parent / "hollowstar" / "content" / "residents.json",
)


# --------------------------------------------------------------------------
# deterministic rng, forked per concern (mirrors hollowstar.rng.RunRNG)
# --------------------------------------------------------------------------
class ForkRNG:
    def __init__(self, seed):
        self._r = random.Random(seed)
        self._seed = seed

    def fork(self, label):
        return ForkRNG(f"{self._seed}:{label}")

    def random(self):
        return self._r.random()

    def randint(self, a, b):
        return self._r.randint(a, b)

    def choice(self, seq):
        return self._r.choice(list(seq))

    def d6(self):
        return self._r.randint(1, 6)

    def two_d6(self):
        return self._r.randint(1, 6) + self._r.randint(1, 6)

    def weighted(self, rows, key="weight"):
        total = sum(max(0.0, float(r.get(key, 1))) for r in rows)
        if total <= 0:
            return None
        roll = self._r.random() * total
        upto = 0.0
        for row in rows:
            upto += max(0.0, float(row.get(key, 1)))
            if roll <= upto:
                return row
        return rows[-1]


# --------------------------------------------------------------------------
# population
# --------------------------------------------------------------------------
def band_for(cfg, total):
    for band in cfg["reaction_bands"]:
        if total <= band["max"]:
            return band["id"]
    return cfg["reaction_bands"][-1]["id"]


def anchors_for(cfg, floor, room_kind, tod, rng):
    out = []
    for res in cfg["residents"]:
        anc = res.get("anchor")
        if not anc:
            continue
        if floor not in anc["floors"] or room_kind not in anc["room_kinds"]:
            continue
        r = rng.fork(f"anchor:{res['id']}")
        if r.random() <= anc["certainty"] * res["presence"].get(tod, 0.5):
            out.append(res)
    return out


def familiars_for(cfg, floor, room_kind, tod, rng, want):
    pool = []
    for res in cfg["residents"]:
        if res.get("tier") != "familiar":
            continue
        if room_kind not in res.get("room_kinds", []):
            continue
        aff = float(res.get("floor_affinity", {}).get(str(floor), 0.0))
        pres = float(res["presence"].get(tod, 0.5))
        w = aff * pres
        if w > 0:
            pool.append({"res": res, "weight": w})
    picked = []
    r = rng.fork("familiars")
    for _ in range(want):
        if not pool:
            break
        row = r.weighted(pool)
        if row is None:
            break
        picked.append(row["res"])
        pool = [p for p in pool if p["res"]["id"] != row["res"]["id"]]
    return picked


def filler_for(cfg, count, rng):
    r = rng.fork("filler")
    out = []
    for i in range(count):
        row = r.weighted(cfg["filler_pool"])
        out.append({
            "id": f"{row['id']}#{i}",
            "name": row["id"].replace("_", " "),
            "class": row["class"],
            "species": "human",
            "filler": True,
            "condition": r.choice(row["condition"]),
        })
    return out


def populate(cfg, floor, room_kind, tod, seed, familiar_want=2, filler_range=(2, 6)):
    rng = ForkRNG(f"{seed}:room:{floor}:{room_kind}:{tod}")
    named = anchors_for(cfg, floor, room_kind, tod, rng)
    have = {n["id"] for n in named}
    for res in familiars_for(cfg, floor, room_kind, tod, rng, familiar_want):
        if res["id"] not in have:
            named.append(res)
            have.add(res["id"])
    n_filler = rng.fork("fillercount").randint(*filler_range)
    return named, filler_for(cfg, n_filler, rng)


# --------------------------------------------------------------------------
# reaction
# --------------------------------------------------------------------------
def crowd_modifier(res, present_ids, present_classes):
    mod = 0
    notes = []
    for rel in res.get("relationships", []):
        if rel["target"] not in present_ids:
            continue
        kind = rel["kind"]
        w = int(rel.get("weight", 1))
        if kind in ("fears", "avoids"):
            mod -= min(2, w)
            notes.append(f"tense: {rel['target']} is here")
        elif kind == "protects":
            mod -= 1
            notes.append(f"watchful over {rel['target']}")
        elif kind in ("owed-by",):
            mod += 1
            notes.append(f"attention on {rel['target']}")
        elif kind in ("owes",):
            mod -= 1
            notes.append(f"evasive near {rel['target']}")
    # standing tension: someone of a class this resident despises is in the room
    for cls, val in res.get("stances", {}).items():
        if val <= -3 and cls in present_classes:
            mod -= 1
            notes.append(f"room holds {cls}")
            break
    return mod, notes


def react(cfg, res, player, present_ids, present_classes, tod, seed):
    rng = ForkRNG(f"{seed}:react:{res['id']}")
    sp = cfg["species"][player["species"]]
    reads_as = sp["reads_as"]

    roll = rng.two_d6()
    base = int(res.get("disposition_base", 0))
    stance = int(res.get("stances", {}).get(reads_as, 0))
    bias = int(sp.get("reaction_bias", {}).get(res.get("class", "townsfolk"), 0))
    time_mod = int(cfg["time_of_day"][tod]["modifier"])
    crowd, notes = crowd_modifier(res, present_ids, present_classes)

    total = roll + base + stance + bias + time_mod + crowd
    return {
        "resident": res["id"],
        "name": res["name"],
        "roll": roll,
        "base": base,
        "stance": stance,
        "species_bias": bias,
        "time": time_mod,
        "crowd": crowd,
        "total": total,
        "band": band_for(cfg, total),
        "notes": notes,
    }


# --------------------------------------------------------------------------
# outcomes
# --------------------------------------------------------------------------
BAND_RANK = {"hostile": 0, "wary": 1, "neutral": 2, "warm": 3, "helpful": 4}


def outcomes(cfg, named, filler, reactions, player):
    out = set()
    by_id = {r["resident"]: r for r in reactions}
    classes = {o["class"] for o in filler} | {n["class"] for n in named}
    sp = cfg["species"][player["species"]]
    denied = set(sp.get("denies", []))

    if not named:
        out.add("no_named_faces")

    for n in named:
        r = by_id[n["id"]]
        rank = BAND_RANK[r["band"]]
        off = n.get("offers", {})
        if off.get("quest") and rank >= 3:
            out.add("quest_offered")
        if off.get("shop") and rank >= 1 and "buy" not in denied:
            out.add("trade_open")
        if off.get("identify") and rank >= 2 and "identify" not in denied:
            out.add("identify_available")
        if rank == 4:
            out.add("informant")
        if rank == 0:
            out.add("hostile_face")

    hostiles = [n for n in named if BAND_RANK[by_id[n["id"]]["band"]] == 0]
    if len(hostiles) >= 2 and "guard" not in classes:
        out.add("ambush_forming")
    if any(n["class"] == "bandit" for n in hostiles):
        out.add("collector_present")

    ranks = [BAND_RANK[by_id[n["id"]]["band"]] for n in named]
    if ranks and sum(1 for x in ranks if x <= 1) > len(ranks) / 2:
        out.add("shunned")
    if ranks and min(ranks) <= 1 and max(ranks) >= 3:
        out.add("room_divided")

    present_ids = {n["id"] for n in named}
    for n in named:
        for rel in n.get("relationships", []):
            if rel["kind"] == "protects" and rel["target"] in present_ids:
                out.add("intervention_moment")
            if rel["kind"] in ("fears", "avoids") and rel["target"] in present_ids:
                out.add("tense_room")

    if any(o["class"] == "child" for o in filler) or any(n["class"] == "child" for n in named):
        out.add("children_present")
    if "beast" == sp["reads_as"]:
        out.add("read_as_animal")
    return out


def run_room(cfg, floor, room_kind, tod, seed, player):
    named, filler = populate(cfg, floor, room_kind, tod, seed)
    present_ids = {n["id"] for n in named}
    present_classes = {n["class"] for n in named} | {f["class"] for f in filler}
    reactions = [react(cfg, n, player, present_ids, present_classes, tod, seed) for n in named]
    return {
        "seed": seed, "floor": floor, "room_kind": room_kind, "tod": tod,
        "player": player, "named": named, "filler": filler,
        "reactions": reactions, "outcomes": outcomes(cfg, named, filler, reactions, player),
    }


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------
def entropy(counter):
    n = sum(counter.values())
    if n <= 1:
        return 0.0
    return -sum((c / n) * math.log2(c / n) for c in counter.values() if c)


def sweep(cfg, runs, floor, room_kind, player, tods):
    rows = []
    for i in range(runs):
        tod = tods[i % len(tods)]
        rows.append(run_room(cfg, floor, room_kind, tod, f"run-{i:04d}", player))

    named_sets = Counter(tuple(sorted(n["id"] for n in r["named"])) for r in rows)
    outcome_sets = Counter(tuple(sorted(r["outcomes"])) for r in rows)
    full_sig = Counter(
        (tuple(sorted(n["id"] for n in r["named"])), tuple(sorted(r["outcomes"]))) for r in rows
    )
    appearance = Counter()
    bands = Counter()
    for r in rows:
        for n in r["named"]:
            appearance[n["id"]] += 1
        for rx in r["reactions"]:
            bands[rx["band"]] += 1
    crowd = Counter(len(r["named"]) + len(r["filler"]) for r in rows)
    return {
        "runs": runs, "rows": rows,
        "named_sets": named_sets, "outcome_sets": outcome_sets, "full_sig": full_sig,
        "appearance": appearance, "bands": bands, "crowd": crowd,
        "entropy_named": entropy(named_sets),
        "entropy_outcome": entropy(outcome_sets),
        "entropy_full": entropy(full_sig),
    }


def pct(a, b):
    return f"{100.0 * a / b:5.1f}%" if b else "  n/a"


def report(cfg, s, label):
    n = s["runs"]
    print(f"\n=== {label} — {n} runs ===")
    print(f"  distinct named-cast sets   : {len(s['named_sets']):3d}  (entropy {s['entropy_named']:.2f} bits)")
    print(f"  distinct outcome sets      : {len(s['outcome_sets']):3d}  (entropy {s['entropy_outcome']:.2f} bits)")
    print(f"  distinct full signatures   : {len(s['full_sig']):3d}  (entropy {s['entropy_full']:.2f} bits)")
    top, topn = s["full_sig"].most_common(1)[0]
    print(f"  most common room repeats   : {pct(topn, n)} of runs")
    print("  resident appearance rate:")
    order = {r["id"]: (r.get("tier"), r["name"]) for r in cfg["residents"]}
    for rid, c in sorted(s["appearance"].items(), key=lambda kv: -kv[1]):
        tier, name = order[rid]
        print(f"    {name:16} {tier:8} {pct(c, n)}")
    print("  reaction bands:", ", ".join(f"{k} {pct(v, sum(s['bands'].values()))}" for k, v in
                                         sorted(s["bands"].items(), key=lambda kv: BAND_RANK[kv[0]])))
    print("  outcome frequency:")
    oc = Counter()
    for r in s["rows"]:
        oc.update(r["outcomes"])
    for k, v in oc.most_common():
        print(f"    {k:22} {pct(v, n)}")


def detail(cfg, rows, count):
    for r in rows[:count]:
        print("\n" + "-" * 66)
        print(f"seed {r['seed']}  floor {r['floor']}  {r['room_kind']}  {r['tod']}"
              f"  as {r['player']['species']}")
        if not r["named"]:
            print("  (no named faces — crowd only)")
        for rx in r["reactions"]:
            parts = f"2d6={rx['roll']} base{rx['base']:+d} stance{rx['stance']:+d} sp{rx['species_bias']:+d} time{rx['time']:+d} crowd{rx['crowd']:+d}"
            print(f"  {rx['name']:16} {rx['total']:>3} {rx['band']:<8} [{parts}]")
            for note in rx["notes"]:
                print(f"{'':19}· {note}")
        crowd = Counter(f["name"] for f in r["filler"])
        print(f"  crowd: {', '.join(f'{v}x {k}' for k, v in crowd.items())}")
        print(f"  outcomes: {', '.join(sorted(r['outcomes'])) or '(none)'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--content", default=str(DEFAULT_CONTENT))
    ap.add_argument("--runs", type=int, default=200)
    ap.add_argument("--floor", type=int, default=1)
    ap.add_argument("--room-kind", default="social")
    ap.add_argument("--species", default="human")
    ap.add_argument("--detail", type=int, default=0)
    ap.add_argument("--species-compare", action="store_true")
    args = ap.parse_args()

    cfg = json.loads(Path(args.content).read_text(encoding="utf-8"))
    tods = ["morning", "day", "evening", "night"]

    if args.species_compare:
        for sp in ("human", "goblin", "wolf"):
            s = sweep(cfg, args.runs, args.floor, args.room_kind, {"species": sp}, tods)
            report(cfg, s, f"floor {args.floor} {args.room_kind} as {sp}")
        return

    s = sweep(cfg, args.runs, args.floor, args.room_kind, {"species": args.species}, tods)
    report(cfg, s, f"floor {args.floor} {args.room_kind} as {args.species}")
    if args.detail:
        detail(cfg, s["rows"], args.detail)


if __name__ == "__main__":
    main()
