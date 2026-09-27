"""Doran's voice: situational reactions, exploration chatter, and replies.

Presentation-only. Nothing here rolls, changes state the engine reads, or
reveals sealed room data. Voice is grounded in DM041_C (profile) and DM041_E
(pair doctrine): professional soldier cadence — serious, clipped, terse; pushes
forward under pressure; reads the seam; counts exits by reflex; respects Wren's
competence; over-formal around the senior women; real appetite for food, bars
and company once a scene releases him. His kit is undamageable and never needs
maintenance, so he never talks about sharpening, oiling or repairing it.

Line markers (prefix, then "|"):
  W  needs Wren alive in the party          T  needs Wren + pair trust >= 1
  S  solo-pride register, only before trust  (no prefix) always eligible
"""
from __future__ import annotations

import hashlib
import re

# ---------------------------------------------------------------------------
# Reaction pools. Keys are situations resolved by _situation(), most specific
# first. {target} is the other combatant's public name.
# ---------------------------------------------------------------------------
REACT = {
    # -- Doran attacking --------------------------------------------------
    "doran_kill": [
        "Down.", "One.", "{target} is finished. Next.", "Clean.", "That's handled.",
        "S|Room's getting smaller.", "S|Told you. One man is enough for this.",
        "W|{target}'s down. Wren, status.", "T|Down. Good opening, Wren.",
    ],
    "doran_kill_big": [
        "Big ones fall the same way. Just longer.",
        "{target} is down. Mark it.",
        "That's the heavy one. Breathe.",
        "S|Korin said size is a question, not an answer.",
        "W|{target}'s down. Wren — you all right?",
        "T|We did that. Both of us. Note it.",
    ],
    "doran_crit": [
        "Seam.", "Found it.", "Right through the gap.", "That's where it lives.",
        "Bone, armor, doesn't matter. Found the line.",
        "It told me where. I listened.",
    ],
    "doran_read": [
        "I've got your read, {target}.", "Seen it. Won't miss it twice.",
        "Every guard has a seam. Yours is low and left.",
    ],
    "doran_dagger_armor": [
        "Armor's a suggestion.", "Plate doesn't matter.", "{target} thinks steel helps. It doesn't.",
        "Through, not around.",
    ],
    "doran_cleaver_hit": [
        "Cleaver.", "Heavy answer.", "Felt that one in the floor.",
        "Ember made it heavy enough. She was right.",
    ],
    "doran_maim": [
        "It won't use that side again.", "Limb's done. Keep pressing.",
    ],
    "doran_hit": [
        "Pressing.", "Again.", "Stay on it.", "Forward.", "Keep it busy.",
        "W|Wren, it's opening on the left.", "T|Your mark, Wren. I'll hold it.",
    ],
    "doran_miss": [
        "Missed. Adjusting.", "It moved. Won't twice.", "Close.",
        "Reset.", "Bad angle. Changing it.",
        "S|Fine. Again.", "T|Wren — cover the gap, I overreached.",
    ],
    "doran_parry": [
        "Mine.", "Turned it.", "Not today.", "Caught that.",
    ],
    "room_pays": [
        "The room pays for that.", "Wall's in the way. Wall loses.", "Structure's damaged. Move.",
    ],
    # -- Doran defending --------------------------------------------------
    "enemy_miss_doran": [
        "Missed.", "Too slow.", "Wrong man.", "Try again.",
        "Plate takes the glance.",
    ],
    "doran_hit_taken": [
        "Taken.", "Felt that.", "Still standing.", "Noted.", "Hm.",
        "It's strong. I've sparred stronger.",
    ],
    "doran_bloodied": [
        "I'm cut. Not badly.", "Half. I'm fine.", "Took some. Still working.",
        "W|Wren, I'm at half. No change to plan.", "T|Wren. I'll need you soon. Not yet.",
    ],
    "doran_hurt_bad": [
        "I'm hurt.", "That one went through.", "Getting heavy.",
        "S|I can finish this.", "W|Wren. Now would be good.",
        "T|Wren — I need you. Say where.",
    ],
    "indomitable": [
        "No.", "Not like that.", "Shook it.",
    ],
    # -- Wren in the fight -----------------------------------------------
    "wren_hit": [
        "W|Wren!", "W|On you, Wren. Coming.", "W|{target}. Here. Look at me.",
        "W|Hit's on Wren. Moving to cover.",
    ],
    "wren_hurt_bad": [
        "W|Wren's hurt. Pulling it off her.", "W|Behind me, Wren. Now.",
        "W|Wren, down. Shield's yours.", "T|I've got the front. Heal, Wren. Go.",
    ],
    "wren_kill": [
        "W|Nice work, Wren.", "W|Clean spell.", "W|Good call.",
        "T|That's the handoff. Again, next time.", "S|W|Hm. Faster than me.",
    ],
    "wren_crit": [
        "W|That's a hit.", "W|Good. Very good.",
    ],
    "wren_heals_doran": [
        "W|Thank you, Wren.", "W|Better. Thanks.", "W|Owe you.",
        "T|Knew you had it.", "S|W|Didn't need it. ...Thank you.",
    ],
    # -- Combat framing ---------------------------------------------------
    "combat_start": [
        "Contact.", "Here we go.", "Weapons.", "Hostiles. Close fast.",
        "S|I'll take the front. Just stay clear.", "W|Wren, your read first.",
        "T|Wren — call it. I'll move on your word.",
    ],
    "combat_start_big": [
        "That's a big one.", "Size isn't the problem. Reach is.",
        "Cleaver's out. Keep distance until I'm in.",
        "W|Wren, that thing's reach is ten feet at least. Plan for it.",
        "T|Split it. I take its attention, you take the rest of it.",
    ],
    # -- Exploration events -----------------------------------------------
    "entry": [
        "Doors, corners, ceiling.", "Two exits. Good.", "One exit. I don't like it.",
        "Quiet. Too quiet, or just quiet. Watching.",
        "Hold at the threshold.", "Clear left. Checking right.",
        "Someone arranged this room.", "Floor's been walked recently.",
        "W|Wren, anything in the Weave?", "T|Your eyes on the magic, mine on the doors.",
    ],
    "reentry": [
        "Back again. Nothing's moved.", "Same room. Different mood.", "We've been here.",
    ],
    "search": [
        "Looking.", "Give me a second.", "Something's off about the stonework.",
        "Checking the seams.", "Nothing yet.",
    ],
    "hazard_hit": [
        "Trap. Everyone breathing?", "Should've read that. My fault.",
        "Floor lied.", "That's on me.",
        "W|Wren, you hit?", "T|Next time I'll wait for your read.",
    ],
    "hazard_avoided": [
        "Saw it.", "Trap. Stepping around.", "Not that easy.",
    ],
    "blocked": [
        "Doesn't work on it. Changing approach.", "Resistant. Noted.",
        "It's built for that. So we don't do that.",
    ],
    "reward": [
        "Count it once. Move.", "Paid.", "Good haul. Stay sharp.",
        "Pack it tight. We're not done.",
    ],
    "purchase": [
        "Fair price.", "Done. Let's go.", "Good. Useful.",
    ],
    "consume": [
        "...That's good.", "Better than it looks.", "Food. Finally.",
        "Could eat three more of these.", "Don't tell anyone I liked that.",
    ],
    "upgrade": [
        "Better.", "Useful change.", "Good work.", "Noted. I'll test it next room.",
    ],
    "identify": [
        "So that's what it is.", "Hm. Useful, or not.", "Good to know before using it.",
    ],
    "check_in": [
        "Checking in. All accounted for.", "Report's short: we're alive, we're moving.",
        "Yes, ma'am. Understood.",
    ],
    "rest": [
        "Short rest. Watch first — mine.", "Sit. I've got the door.",
        "Rest. I'll wake you if anything moves.",
        "W|Sleep, Wren. I'll take first watch.",
    ],
    "night_patrol": [
        "Something moving. Up.", "Patrol. Quiet now.", "Night work.",
    ],
    "descend": [
        "Down we go.", "Deeper. Air's changing.", "Stairs. I'll go first.",
        "Helm's got the dark. Stay behind me.",
    ],
    "social": [
        "Ma'am.", "Sir.", "Understood.", "We're Sanctum. We're here to help.",
        "Thank you for your time.",
    ],
    "terminal": [
        "Done. Everyone breathing? Good. That's the report.",
        "Run's over. Mark the map.", "That's the day.",
        "W|Good work, Wren. Really.", "T|Couldn't have done that one alone. ...Don't repeat that.",
    ],
    "terminal_hard": [
        "Not our day.", "We learn from it.", "I'll carry that one. Next time's different.",
        "W|You're alive, Wren. That's what matters.",
    ],
}

# Quiet-moment chatter while travelling or exploring. Drawn at random and
# spaced out so it reads like a man thinking aloud, not a quip dispenser.
AMBIENT = {
    "explore": [
        "Three exits back there. Counting habit.",
        "Air's stale. Nobody's opened a window down here in a century.",
        "Helm makes the dark easy. Still don't like it.",
        "Korin used to say a quiet hallway is a question.",
        "Boots are silent on this stone. Good.",
        "Floor dips here. Water, once.",
        "I'd pay a lot for a hot meal right now.",
        "After this, a bar. Loud one. With chairs that don't break.",
        "Plate's catching the light. If anything's watching, it's watching me. Fine.",
        "Tight corridor. Cleaver won't swing clean here. Daggers, then.",
        "Someone lived here. Scuffs on the doorframe at hand height.",
        "Letha would have something to say about the dust.",
        "Have four of Korin's carvings. First one's a bad bear. Don't know why I'm thinking about that.",
        "Stay in formation. Habit, not doubt.",
        "Listen. ...No. Nothing.",
        "W|Wren, still with me?",
        "W|You're quiet, Wren. Thinking or worried?",
        "W|Wren — what's your read on this place?",
        "W|Glasses showing anything, Wren?",
        "T|Good pace, Wren. Keep it.",
        "T|You were right, earlier. I should've waited for your call.",
        "S|W|I can scout ahead. Faster alone. ...Or not. Stay close.",
    ],
    "explore_hurt": [
        "I'm fine. Keep moving.",
        "Ribs remember that last one.",
        "Ring's working. Slowly.",
        "Don't slow down on my account.",
        "W|I'm fine, Wren. Stop looking at me like that.",
    ],
}

# Replies when the player addresses Doran directly. First matching topic wins.
# Placeholders: {hp} {max} {room} {foe} {foes} {wren_hp} {wren_max}
REPLY_TOPICS = [
    ("greet", r"\b(hi|hello|hey|morning|evening|yo)\b", [
        "Here.", "Ready.", "Listening.", "Go ahead.",
    ]),
    ("status", r"\b(how are you|you ok|you okay|you alright|you all right|holding up|hurt|injur|wound|health|hp)\b", [
        "@hp",
    ]),
    ("threat", r"\b(what do you think|read|assess|threat|danger|enemy|enemies|foe|that thing|can we take)\b", [
        "@threat",
    ]),
    ("plan", r"\b(plan|what now|next|where to|what should|orders|lead)\b", [
        "@plan",
    ]),
    ("where", r"\b(where are we|this place|this room|where is this)\b", [
        "{room}. Two ways in that I've seen. I'm watching both.",
        "{room}. Too many places to stand where I can't see you.",
    ]),
    ("wren", r"\bwren\b", [
        "Wren's good. Better than good. Don't tell her I said so.",
        "She sees things I don't. I'm learning to wait for that.",
        "Year in the same cohort. Still learning how she works in the field.",
        "She over-explains. I under-explain. It works out.",
    ]),
    ("korin", r"\bkorin\b", [
        "Korin taught me everything that matters. Most of it by knocking me down.",
        "He'd say I'm moving too fast. He'd be right.",
        "I have four of his carvings. First one's a bear. A bad bear.",
    ]),
    ("letha", r"\bletha\b", [
        "Ma'am. Six years I've called her ma'am. Won't stop now.",
        "Letha keeps the house running. Nobody argues with Letha.",
    ]),
    ("sera", r"\bsera\b", [
        "Lady Sera is... Lady Sera. She trained me. I'm grateful.",
        "She designed the plate. And the stick figure on my knee. Both deliberate, I think.",
        "I told her she was more beautiful in person. She agreed. Then we went to work.",
    ]),
    ("ember", r"\bember\b", [
        "Lady Ember picked the colors. White and dark. She was right.",
        "She says there's a second stick figure. 'On the other side.' I haven't found it.",
        "She made the Cleaver heavy enough. Her words.",
    ]),
    ("soliera", r"\bsoliera\b", [
        "The daggers are hers. I try to deserve them.",
        "I don't speak for her. I carry what she gave me.",
    ]),
    ("daggers", r"\b(dagger|daggers|knife|knives|blade|obsidian)\b", [
        "They find the weak point. I just follow them there.",
        "Armor, bone. Doesn't matter to these.",
        "They come when I call. Every time.",
    ]),
    ("cleaver", r"\b(cleaver|greatsword|sword)\b", [
        "Two hundred and eight pounds. Could barely lift it at first.",
        "Good for big things. Bad for small rooms. The room pays.",
    ]),
    ("armor", r"\b(armor|armour|plate|helm|shield)\b", [
        "Nothing I wear is mine. I intend to earn it.",
        "It doesn't glow. It just gives the light back. People aim at it. That's the point.",
        "Shield gets in my way. Getting better at that.",
    ]),
    ("food", r"\b(food|eat|hungry|meal|starving|dinner|lunch|breakfast)\b", [
        "Yes. Always yes.", "After this. Something hot. A lot of it.",
        "Food's the one thing I never get tired of.",
    ]),
    ("drink", r"\b(drink|bar|tavern|ale|beer|wine|party|celebrate)\b", [
        "When we're done. Not before.", "Loud room. Good ale. Somewhere to sit. Later.",
        "I'll buy the first round. After.",
    ]),
    ("rest", r"\b(tired|rest|sleep|break|exhausted)\b", [
        "Rest if you need it. I'll watch.", "I'm fine. You rest.",
        "Short one. Then we move.",
    ]),
    ("fear", r"\b(scared|afraid|fear|nervous|worried)\b", [
        "Good. Means you're paying attention.", "Stay behind me. That's what I'm for.",
        "I've been scared. It passes when you move.",
    ]),
    ("praise", r"\b(good job|nice|well done|great|impressive|amazing)\b", [
        "Thank you.", "Just the work.", "...Thanks.",
    ]),
    ("thanks", r"\b(thank|thanks|appreciate)\b", [
        "Of course.", "Anytime.", "That's the job.",
    ]),
    ("sorry", r"\b(sorry|my fault|apolog)\b", [
        "Happens. Fix it next time.", "Already forgotten.", "Don't carry it. Move.",
    ]),
    ("joke", r"\b(joke|funny|laugh|smile)\b", [
        "...No.", "I smile. Occasionally. Off duty.",
        "Korin once told a joke. We still don't know what it meant.",
    ]),
    ("home", r"\b(home|sanctum|miss)\b", [
        "The Sanctum's the reason I'm any use.", "Clean water, real food, hard training. That's home.",
        "We'll be back. With a report worth reading.",
    ]),
    ("who", r"\b(who are you|about you|yourself|tell me about)\b", [
        "Doran. Sanctum field Steward. Battle Master. That's the important part.",
        "Soldier. Korin trained me. That's most of it.",
    ]),
]

REPLY_FALLBACK = [
    "Hm.", "Understood.", "Noted.", "If you say so.", "Later. Eyes on the room.",
    "Not sure what you mean. Say it plainly.",
]

# Situations that always speak; the rest roll a chance so routine swings stay quiet.
ALWAYS = {"doran_kill_big", "doran_hurt_bad", "wren_hurt_bad", "wren_heals_doran", "combat_start",
          "combat_start_big", "terminal", "terminal_hard", "hazard_hit", "doran_parry", "indomitable",
          "wren_kill", "doran_crit", "descend", "consume"}
CHANCE = {"doran_hit": 0.3, "doran_miss": 0.35, "enemy_miss_doran": 0.25, "doran_hit_taken": 0.4,
          "social": 0.35, "entry": 0.75, "search": 0.4, "reward": 0.6, "purchase": 0.5}
AMBIENT_CHANCE = 0.4
AMBIENT_GAP = 3          # turns since Doran last spoke before chatter is allowed
RECENT_LIMIT = 16

EXPLORE_ACTIONS = {"move", "look", "search", "inspect", "wait", "idle", "idle_tick", "auto_travel",
                   "explore", "travel", "walk", "listen", "observe"}
EXPLORE_EVENTS = {"move", "movement", "idle_advanced", "auto_travel_advanced", "world_tick", "exited",
                  "perception_already_known", "move_to", "hold_position"}
BIG_WORDS = ("giant", "castellan", "golem", "dragon", "titan", "colossus", "behemoth", "wyrm", "troll", "ogre")


def _roll(*parts) -> float:
    digest = hashlib.sha256(":".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _eligible(line: str, wren: bool, trust: int) -> str | None:
    flags, _, text = line.rpartition("|") if "|" in line[:6] else ("", "", line)
    flags = set(flags.split("|")) if flags else set()
    if "W" in flags and not wren:
        return None
    if "T" in flags and not (wren and trust >= 1):
        return None
    if "S" in flags and trust >= 1:
        return None
    return text


def _choose(pool: list[str], memory: dict, key: str, wren: bool, trust: int, salt) -> str | None:
    options = [text for text in (_eligible(line, wren, trust) for line in pool) if text]
    if not options:
        return None
    recent = memory.setdefault("recent", [])
    fresh = [text for text in options if text not in recent] or options
    text = fresh[int(_roll(key, salt) * len(fresh))]
    recent.append(text)
    del recent[:-RECENT_LIMIT]
    return text


# ---------------------------------------------------------------------------
# Run inspection helpers (read-only).
# ---------------------------------------------------------------------------
def _roster(run) -> dict:
    try:
        from hollowstar.tactical import actors
        found = actors(run)
        if found:
            return found
    except Exception:
        pass
    return {f"p{i}": actor for i, actor in enumerate(getattr(run, "party", []) or [])}


def _find(roster: dict, name: str):
    for key, creature in roster.items():
        if str(getattr(creature, "name", "")).lower() == name:
            return key, creature
    return None, None


def _ratio(creature) -> float:
    try:
        return max(0.0, creature.hp / max(1, creature.max_hp))
    except Exception:
        return 1.0


def _big(creature) -> bool:
    name = str(getattr(creature, "name", "")).lower()
    return any(word in name for word in BIG_WORDS) or getattr(creature, "max_hp", 0) >= 200


def _in_combat(run) -> bool:
    combat = run.context.get("combat")
    if not isinstance(combat, dict):
        return False
    return bool(combat.get("active") or combat.get("initiative") or combat.get("order")) and not combat.get("ended")


def _situation(run, action_type: str, event: dict, kind: str | None, doran_id, wren_id, roster):
    """Return (situation, format vars) for the most specific thing that happened."""
    ev = event.get("combat") if isinstance(event.get("combat"), dict) else event
    etype = str(ev.get("type", "")).lower()
    outer = str(event.get("type", "")).lower()
    action = str(action_type or "").lower()
    source, target = ev.get("source"), ev.get("target")
    defender = roster.get(target) if target else None
    names = {"target": getattr(defender, "name", None) or (ev.get("evidence") or {}).get("target") or "it"}

    if etype == "attack":
        hit = bool((ev.get("roll") or {}).get("success"))
        dead = defender is not None and not getattr(defender, "alive", True)
        if source == doran_id:
            pending = ev.get("pending_defense")
            if not hit:
                return "doran_miss", names
            if dead:
                return ("doran_kill_big" if _big(defender) else "doran_kill"), names
            if ev.get("critical"):
                return "doran_crit", names
            if ev.get("maim"):
                return "doran_maim", names
            if ev.get("mode") == "cleaver":
                return "doran_cleaver_hit", names
            evidence = ev.get("evidence") or {}
            if evidence.get("critical_threshold") == 16 and _roll(run.seed if hasattr(run, "seed") else "", target) < 0.4:
                return "doran_read", names
            if (evidence.get("target_ac") or 0) >= 18:
                return "doran_dagger_armor", names
            return "doran_hit", names
        if target == doran_id:
            names["target"] = getattr(roster.get(source), "name", None) or "it"
            if (ev.get("pending_defense") or {}).get("options") == ["parry"]:
                return "doran_parry", names
            if not hit:
                return "enemy_miss_doran", names
            doran = roster.get(doran_id)
            ratio = _ratio(doran)
            return ("doran_hurt_bad" if ratio <= 0.25 else "doran_bloodied" if ratio <= 0.5 else "doran_hit_taken"), names
        if wren_id and target == wren_id and hit:
            names["target"] = getattr(roster.get(source), "name", None) or "it"
            return ("wren_hurt_bad" if _ratio(roster.get(wren_id)) <= 0.35 else "wren_hit"), names
        if wren_id and source == wren_id and hit:
            if dead:
                return "wren_kill", names
            if ev.get("critical"):
                return "wren_crit", names
        return None, names
    if etype == "healing" and target == doran_id and wren_id and source == wren_id:
        return "wren_heals_doran", names
    if etype == "initiative":
        foes = [c for k, c in roster.items() if not str(k).startswith("p") and getattr(c, "alive", True)]
        return ("combat_start_big" if any(_big(c) for c in foes) else "combat_start"), names
    if etype == "indomitable":
        return "indomitable", names
    if etype == "dagger_cut_structure":
        return "room_pays", names
    if etype in {"permission_blocked", "blocked", "immunity", "resistance_blocked"}:
        return "blocked", names
    for label in (etype, outer):
        mapped = {
            "entered": "entry", "room_entered": "entry", "entered_room": "entry", "reentered": "reentry",
            "hazard": "hazard_hit", "avoidance_failed": "hazard_hit", "hazard_avoided_by_heirloom": "hazard_avoided",
            "perception_test": "search", "test_perception": "search", "rune_identified": "identify",
            "purchase": "purchase", "consume": "consume", "check_in": "check_in", "checkpoint_banked": "rest",
            "night_patrol": "night_patrol", "descend": "descend", "room_resolved": "reward",
            "upgrade": "upgrade", "imprints_combined": "upgrade", "affix_reforged": "upgrade",
        }.get(label)
        if mapped:
            return mapped, names
    if outer in {"run_ended", "ended"} or etype in {"run_ended", "ended"}:
        doran = roster.get(doran_id)
        return ("terminal_hard" if doran is not None and not getattr(doran, "alive", True) else "terminal"), names
    if action in {"design_start", "enter"}:
        return "entry", names
    if action in {"talk", "speak", "conversation"}:
        return "social", names
    if "reward" in event:
        return "reward", names
    if kind == "upgrade":
        return "upgrade", names
    return None, names


def react(run, action_type: str, event: dict, kind: str | None, turn: int, state: dict) -> dict | None:
    """Return at most one Doran line for this event, or None."""
    roster = _roster(run)
    doran_id, doran = _find(roster, "doran")
    if doran is None:
        return None
    wren_id, wren = _find(roster, "wren")
    wren_here = wren is not None and getattr(wren, "alive", True)
    memory = state.setdefault("doran", {"pair": 0, "last_spoke": -10, "last": {}})
    situation, names = _situation(run, action_type, event, kind, doran_id, wren_id, roster)
    if situation in {"wren_kill", "wren_heals_doran", "wren_crit"}:
        memory["pair"] = int(memory.get("pair", 0)) + 1
    trust = 0 if memory.get("pair", 0) < 3 else 1 if memory.get("pair", 0) < 8 else 2
    seed = run.context.get("seed") or run.context.get("run_seed") or ""

    if situation:
        last = memory.setdefault("last", {})
        if situation not in ALWAYS:
            if turn - int(last.get(situation, -10)) <= 1:
                return None
            if _roll(seed, turn, situation) > CHANCE.get(situation, 0.55):
                return None
        text = _choose(REACT.get(situation, []), memory, situation, wren_here, trust, f"{seed}:{turn}")
        if not text:
            return None
        last[situation] = turn
        memory["last_spoke"] = turn
        return {"speaker": "Doran", "text": text.format(**names), "trigger": situation,
                "priority": "high" if situation in ALWAYS else "normal", "register": "reaction"}

    # Nothing specific happened: maybe think aloud while exploring.
    ev = event.get("combat") if isinstance(event.get("combat"), dict) else event
    exploring = str(action_type or "").lower() in EXPLORE_ACTIONS or str(ev.get("type", "")).lower() in EXPLORE_EVENTS
    if not exploring or _in_combat(run):
        return None
    if turn - int(memory.get("last_spoke", -10)) < AMBIENT_GAP or _roll(seed, turn, "ambient") > AMBIENT_CHANCE:
        return None
    pool = AMBIENT["explore_hurt"] if _ratio(doran) <= 0.5 and _roll(seed, turn, "hurt") < 0.6 else AMBIENT["explore"]
    text = _choose(pool, memory, "ambient", wren_here, trust, f"{seed}:{turn}")
    if not text:
        return None
    memory["last_spoke"] = turn
    return {"speaker": "Doran", "text": text, "trigger": "ambient", "priority": "low", "register": "ambient"}


# ---------------------------------------------------------------------------
# Replies — answers built from the public view only.
# ---------------------------------------------------------------------------
def _member(view: dict, name: str) -> dict | None:
    for row in view.get("party") or []:
        if str(row.get("name", "")).lower() == name:
            return row
    return None


def _hp(row: dict | None) -> tuple[int, int]:
    if not row:
        return 0, 1
    hp = row.get("hp", row.get("current_hp", 0)) or 0
    return int(hp), int(row.get("max_hp") or 1)


def _foes(view: dict) -> list[dict]:
    return [row for row in view.get("opposition") or [] if not row.get("defeated") and (row.get("hp", 1) or 0) > 0]


def _dynamic(tag: str, view: dict, wren_here: bool, salt) -> str:
    hp, top = _hp(_member(view, "doran"))
    ratio = hp / max(1, top)
    foes = _foes(view)
    if tag == "@hp":
        if ratio >= 0.9:
            options = ["Fine. Barely scratched.", "Full strength. Ready.", f"{hp} of {top}. Nothing to report."]
        elif ratio >= 0.5:
            options = [f"{hp} of {top}. Working.", "Cut up a little. Doesn't matter.", "Fine. Ring's handling it."]
        elif ratio > 0.25:
            options = [f"Honestly? {hp} of {top}. I'll manage.", "Hurt. Still useful."]
            if wren_here:
                options.append("Half gone. If Wren has something spare, I won't argue.")
        else:
            options = [f"{hp} of {top}. Not good.", "I need healing. Soon."]
            if wren_here:
                options.append("Wren. I need you. That's the honest answer.")
        wren = _member(view, "wren")
        if wren_here and wren:
            w_hp, w_top = _hp(wren)
            if w_hp / max(1, w_top) <= 0.4:
                return options[int(_roll(salt, "hp") * len(options))] + " Worry about Wren first."
        return options[int(_roll(salt, "hp") * len(options))]
    if tag == "@threat":
        if not foes:
            return ["Nothing hostile in sight. Doesn't mean nothing's here.", "Clear. For now.",
                    "Quiet. I'm still counting exits."][int(_roll(salt, "t") * 3)]
        lead = max(foes, key=lambda row: row.get("max_hp") or row.get("hp") or 0)
        name = lead.get("name") or lead.get("id") or "it"
        big = any(word in str(name).lower() for word in BIG_WORDS) or (lead.get("max_hp") or 0) >= 200
        if big:
            options = [f"{name}. Big. Reach is the danger, not the strength.",
                       f"{name}'s the problem. I get inside its reach, everything else gets easier.",
                       f"{name}. Cleaver work. Keep clear of its swing."]
            if wren_here:
                options.append(f"{name}. Wren slows it, I finish it. That's the shape.")
        elif len(foes) > 2:
            options = [f"{len(foes)} of them. Narrow the space. Make them come one at a time.",
                       f"{len(foes)}. Too many to chase. Hold a line."]
        else:
            options = [f"{name}. I can take it.", f"{name}. Watch its shoulder. It'll tell you everything.",
                       "Manageable. Don't get careless."]
        return options[int(_roll(salt, "t") * len(options))]
    if tag == "@plan":
        if foes:
            options = ["Kill what's in front of us. Then talk.", "Close the distance. I'll take the front."]
            if wren_here:
                options.append("Your read, Wren's spells, my blades. In that order.")
        elif ratio <= 0.5:
            options = ["Rest if we can. I'm not at my best.", "Short rest. Then forward."]
        else:
            options = ["Forward. Next room.", "Search this room, then move.", "Keep going. We're making good time."]
        return options[int(_roll(salt, "p") * len(options))]
    return tag


def reply(view: dict, text: str, memory: dict | None = None) -> dict:
    """Answer a line addressed to Doran using only the public view."""
    memory = memory if isinstance(memory, dict) else {}
    memory["asked"] = int(memory.get("asked", 0)) + 1
    wren = _member(view, "wren")
    wren_here = bool(wren) and _hp(wren)[0] > 0
    room = view.get("room") or {}
    room_name = room.get("name") or room.get("title") or room.get("id") or "This room"
    lowered = f" {text.lower()} "
    salt = f"{text}:{memory['asked']}"
    topic, pool = "fallback", REPLY_FALLBACK
    for name, pattern, lines in REPLY_TOPICS:
        if re.search(pattern, lowered):
            topic, pool = name, lines
            break
    choice = _choose(pool, memory, topic, wren_here, 1 if wren_here else 0, salt) or pool[0]
    if choice.startswith("@"):
        choice = _dynamic(choice, view, wren_here, salt)
    foes = _foes(view)
    w_hp, w_top = _hp(wren)
    d_hp, d_top = _hp(_member(view, "doran"))
    choice = choice.format(room=room_name, foe=(foes[0].get("name") if foes else "nothing"), foes=len(foes),
                           hp=d_hp, max=d_top, wren_hp=w_hp, wren_max=w_top)
    return {"speaker": "Doran", "text": choice, "topic": topic, "register": "reply"}
