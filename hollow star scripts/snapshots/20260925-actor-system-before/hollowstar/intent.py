"""Deterministic chat-intent translation; never resolves game mechanics."""
from __future__ import annotations

import re
import unicodedata


class IntentError(ValueError):
    pass


class IntentClarification(IntentError):
    """The visible context does not identify one legal entity."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _token(word: str) -> str:
    """Normalize prose punctuation without changing any game meaning."""
    return word.strip(" ,.!?:;\"'()[]{}")


def _rows(value: object) -> list[dict]:
    """Normalize public list/dict collections without looking behind the view."""
    if isinstance(value, dict):
        values = value.values()
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        return []
    return [row for row in values if isinstance(row, dict)]


def _arguments(words: list[str], *, connectors: set[str] | None = None) -> list[str]:
    ignored = {"the", "a", "an"} | (connectors or set())
    return [_token(word) for word in words if _token(word) and _token(word).lower() not in ignored]


def _actor_id(raw: str | None, context: dict | None) -> str:
    return _resolve_actor(raw, context) if raw else "p0"


def _same_name(left: str, right: str) -> bool:
    return _content_key(left).removeprefix("the ") == _content_key(right).removeprefix("the ")


def _visible_entities(context: dict | None) -> dict[str, list[tuple[str, str]]]:
    """Build only from state already exposed to the conversation layer."""
    found = {"actor": [], "target": [], "object": [], "location": [], "item": []}
    if not isinstance(context, dict):
        return found
    combat = context.get("combat") or {}
    for entity_id, row in (combat.get("actors") or {}).items():
        if isinstance(row, dict) and isinstance(row.get("name"), str):
            kind = "actor" if str(entity_id).startswith("p") else "target"
            found[kind].append((row["name"], entity_id))
            found["actor" if kind == "target" else "target"].append((row["name"], entity_id))
    room = context.get("room") or {}
    world = room.get("world_state") or {}
    for row in _rows(world.get("objects") or []):
        identifier = row.get("id") or row.get("object_id")
        if isinstance(identifier, str):
            label = row.get("name") or identifier
            found["object"].append((str(label), identifier))
            found["object"].append((identifier, identifier))
            if row.get("kind"):
                found["object"].append((str(row["kind"]), identifier))
            for tag in row.get("tags") or []:
                found["object"].append((str(tag), identifier))
    for row in _rows(world.get("npcs") or []):
        identifier = row.get("id") or row.get("npc_id")
        if isinstance(identifier, str):
            label = row.get("name") or row.get("role") or identifier
            found["target"].append((str(label), identifier))
            found["target"].append((identifier, identifier))
    for row in _rows(world.get("subrooms") or []):
        identifier = row.get("id")
        if isinstance(identifier, str):
            label = row.get("name") or identifier
            found["location"].append((str(label), identifier))
            found["location"].append((identifier, identifier))
    for row in _rows(context.get("inventory") or []):
        identifier = row.get("id")
        if isinstance(identifier, str):
            label = row.get("name") or identifier
            found["item"].append((str(label), identifier))
            found["item"].append((identifier, identifier))
    return found


def _content_rows(context: dict | None) -> list[dict]:
    """Read only the content catalog already made visible to the caller."""
    if isinstance(context, dict):
        rows = context.get("content")
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    if context is None:
        # Direct parser use has no room state to leak. The host always supplies
        # a visible catalog; this fallback merely keeps the standalone parser
        # useful for canonical Doran/Wren examples.
        try:
            from hollowstar.content_registry import load_registry, visible_catalog
            return visible_catalog(load_registry(), {"doran", "wren"})
        except (OSError, ValueError):
            return []
    return []


def _sandbox_target(raw: str, context: dict) -> str:
    """Resolve one target from the public sandbox room, never hidden state."""
    query = _content_key(raw)
    query = re.sub(r"^(?:the|a|an)\s+", "", query)
    rows = []
    for group in (context.get("npcs") or {}, (context.get("room") or {}).get("objects") or {}):
        values = group.values() if isinstance(group, dict) else []
        for row in values:
            if not isinstance(row, dict):
                continue
            labels = [row.get("id", ""), row.get("name", ""), row.get("role", "")]
            if any(_content_key(str(label)).removeprefix("the ") == query for label in labels if label):
                rows.append(row.get("id"))
    if len(set(rows)) == 1:
        return str(rows[0])
    return raw.strip(" ,.!?:;")


def _sandbox_parse(text: str, context: dict | None) -> dict | None:
    """Translate the small, compositional language of the D&D fixture."""
    if not isinstance(context, dict) or context.get("schema") != "hollow-star-dd-sandbox-1":
        return None
    lowered = text.strip().lower()
    actor = "p0"
    actor_match = re.match(r"^(doran|wren)\s+", lowered)
    if actor_match:
        actor = {"doran": "p0", "wren": "p1"}[actor_match.group(1)]
        lowered = lowered[actor_match.end():].strip()
    if lowered in {"end turn", "wait", "wait a turn"}:
        return {"type": "end_turn", "actor": actor}
    if lowered in {"clear dungeon", "clear", "finish", "complete"}:
        return {"type": "clear", "actor": actor}
    if lowered in {"escape", "flee", "run away"}:
        return {"type": "escape", "actor": actor}
    if lowered in {"surrender", "give up"}:
        return {"type": "surrender", "actor": actor}
    move = re.match(r"^(?:go|move|walk|run)\s+(?:to\s+)?(north|south|east|west)$", lowered)
    if move:
        return {"type": "move_room", "actor": actor, "direction": move.group(1)}
    cast = re.match(r"^cast\s+(.+?)(?:\s+(?:at|on)\s+(.+))?$", lowered)
    if cast:
        spell, target = cast.groups()
        action = {"type": "cast", "actor": actor, "spell": spell}
        if target:
            action["target"] = _sandbox_target(target, context)
        return action
    save = re.match(r"^(?:make|roll)\s+(str|dex|con|int|wis|cha)(?:\s+save)?(?:\s+(?:against|dc)\s+(\d+))?$", lowered)
    if save:
        ability, dc = save.groups()
        return {"type": "saving_throw", "actor": actor, "ability": ability.upper(), "dc": int(dc or 10)}
    social = re.match(r"^(say|speak|ask|threaten|insult|lie)(?:\s+to)?\s+(.+)$", lowered)
    if social:
        mode, remainder = social.groups()
        target = remainder
        speech = ""
        if mode in {"say", "speak", "ask"}:
            target_match = re.match(r"(.+?)\s+(?:saying|that|about)\s+(.+)$", remainder)
            if target_match:
                target, speech = target_match.groups()
            else:
                target_match = re.match(r"(.+?)\s+to\s+(.+)$", remainder)
                if target_match:
                    speech, target = target_match.groups()
        return {"type": "conversation", "actor": actor, "target": _sandbox_target(target, context),
                "mode": {"say": "speak", "speak": "speak"}.get(mode, mode), "text": speech or remainder}
    attack = re.match(r"^attack\s+(?:the\s+)?(.+)$", lowered)
    if attack:
        return {"type": "attack", "actor": actor, "target": _sandbox_target(attack.group(1), context)}
    ignite = re.match(r"^(?:ignite|light|set)\s+(?:the\s+)?(.+?)(?:\s+on fire)?$", lowered)
    if ignite:
        return {"type": "ignite", "actor": actor, "object": _sandbox_target(ignite.group(1), context)}
    damage = re.match(r"^(?:break|destroy|smash)\s+(?:the\s+)?(.+)$", lowered)
    if damage:
        return {"type": "damage_object", "actor": actor, "object": _sandbox_target(damage.group(1), context)}
    open_object = re.match(r"^open\s+(?:the\s+)?(.+)$", lowered)
    if open_object:
        return {"type": "open_object", "actor": actor, "object": _sandbox_target(open_object.group(1), context)}
    inspect = re.match(r"^(?:inspect|examine|look at)\s+(?:the\s+)?(.+)$", lowered)
    if inspect:
        return {"type": "inspect", "actor": actor, "object": _sandbox_target(inspect.group(1), context)}
    take = re.match(r"^(?:take|pick up|grab)\s+(?:the\s+)?(.+)$", lowered)
    if take:
        return {"type": "take", "actor": actor, "object": _sandbox_target(take.group(1), context)}
    drop = re.match(r"^drop\s+(?:the\s+)?(.+)$", lowered)
    if drop:
        return {"type": "drop", "actor": actor, "object": drop.group(1)}
    return None


def _life_parse(text: str, context: dict | None) -> dict | None:
    """Bounded natural-language adapter for the persistent Floor One slice."""
    if not isinstance(context, dict) or context.get("schema") != "hollow-star-floor-one-public-1":
        return None
    lowered = text.strip().lower()
    if lowered in {"wait", "wait a little", "let time pass"}:
        return {"type": "world_tick", "elapsed_seconds": 30}
    if lowered in {"descend", "go down", "climb down", "enter reliquary", "enter the reliquary", "go into the well"}:
        return {"type": "descend"}
    if re.fullmatch(r"(?:look(?:\s+around)?|search|survey|explore|investigate|observe)"
                    r"(?:\s+(?:the\s+)?(?:room|area|square|place|surroundings|here|around))?[.!]?", lowered):
        return {"type": "survey"}
    move = re.match(r"^(?:go|move|walk|travel)\s+(?:to\s+)?(.+)$", lowered)
    if move:
        return {"type": "move", "destination": _content_key(move.group(1)).replace(" ", "_")}
    attack = re.match(r"^(?:attack|kill|strike)\s+(?:the\s+)?(.+)$", lowered)
    if attack:
        return {"type": "attack", "target": attack.group(1).strip(" .!")}
    social = re.match(r"^(say|speak|ask|threaten|insult|lie|trade)(?:\s+to)?\s+(.+)$", lowered)
    if social:
        mode, target = social.groups()
        return {"type": "talk", "target": target.strip(" .!"),
                "mode": {"say": "speak", "speak": "speak"}.get(mode, mode),
                "text": lowered}
    object_action = re.match(r"^(open|inspect|examine|take|pick up)\s+(?:the\s+)?(.+)$", lowered)
    if object_action:
        verb, target = object_action.groups()
        return {"type": {"examine": "inspect", "pick up": "take"}.get(verb, verb),
                "object": _content_key(target).replace(" ", "-")}
    return None


def _content_key(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"[^a-zA-Z0-9]+", " ", value).lower().strip()


def _resolve_content(raw: str, rows: list[dict]) -> dict | None:
    query = _content_key(raw)
    if query.startswith("the "):
        query = query[4:]
    matches=[]
    for row in rows:
        labels=[row.get("id", ""),row.get("name", ""),*(row.get("aliases") or [])]
        if any(_content_key(str(label)) == query or _content_key(str(label)).removeprefix("the ") == query for label in labels):
            matches.append(row)
    unique={row.get("id"):row for row in matches}
    if len(unique)==1:
        return next(iter(unique.values()))
    if len(unique)>1:
        labels=sorted(row.get("name",row.get("id","content")) for row in unique.values())
        raise IntentClarification("I need clarification: which item or ability do you mean — " + ", ".join(labels) + "?")
    return None


def _resolve_actor(raw: str, context: dict | None) -> str:
    aliases={"wren":"p1","doran":"p0"}
    if raw.lower() in aliases:
        return aliases[raw.lower()]
    entities=_visible_entities(context).get("actor",[])
    return _resolve_visible(raw,entities,"actor") if entities else raw


def _content_match(words: list[str], start: int, rows: list[dict]) -> tuple[dict | None, int, int]:
    """Find the longest visible content name inside a prose clause.

    The old parser only tried the whole suffix after ``use``.  That made
    harmless connective language and compositional names such as
    ``split ray eraser`` impossible to read.  Matching every contiguous span
    keeps the grammar deterministic while allowing the sentence around the
    name to remain natural language.
    """
    candidates = []
    for begin in range(start, len(words)):
        for end in range(len(words), begin, -1):
            phrase = " ".join(_token(word) for word in words[begin:end] if _token(word))
            stripped = re.sub(r"^(?:the|a|an)\s+", "", phrase, flags=re.I)
            row = _resolve_content(stripped, rows)
            if row is not None:
                candidates.append((row, begin, end))
    if not candidates:
        return None, start, start
    # Prefer the longest canonical span, then the earliest occurrence.  This
    # makes "staff of the magi" win over the shorter alias "staff".
    candidates.sort(key=lambda item: (-(item[2] - item[1]), item[1]))
    return candidates[0]


def _parse_content_sentence(words: list[str], context: dict | None) -> dict | None:
    """Translate visible canonical names and aliases into a content action.

    A sentence can contain navigation or social connective tissue before the
    actual use clause.  This function intentionally extracts one actionable
    content mention; the desktop runtime remains responsible for resolving
    the resulting action and any unsupported rule.
    """
    rows=_content_rows(context)
    if not rows:
        return None
    verbs={"draw","draws","use","uses","open","opens","invoke","invokes",
           "activate","activates","equip","equips","wield","wields","cast","casts"}
    verb_index=next((index for index,word in enumerate(words) if _token(word).lower() in verbs),None)
    if verb_index is None:
        return None
    # Only a plainly named party member before the verb is an explicit actor.
    # Pronouns and connective clauses ("I walk in and") leave ownership to the
    # visible catalog, which is the safe default for an ability/item use.
    prefix = " ".join(_token(word) for word in words[:verb_index])
    actor = None
    if prefix and not re.search(r"\b(?:i|me|we|us|you|someone|they)\b", prefix, re.I):
        for name in ("doran", "wren"):
            if re.search(rf"\b{re.escape(name)}\b", prefix, re.I):
                actor = _resolve_actor(name, context)
                break
    content_start = verb_index + 1
    content_words = [_token(word) for word in words[content_start:] if _token(word)]
    if not content_words:
        return None
    # ``to absorb the spell`` and similar tails describe the use, not the
    # item/ability name.  Keep them available for parameters while bounding
    # primary-name matching at the first natural-language connector.
    connector_index = next(
        (index for index, word in enumerate(content_words)
         if word.lower() in {"to", "for", "on", "at", "against", "into"}),
        len(content_words),
    )
    name_words = content_words[:connector_index]
    entry, match_start, match_end = _content_match(name_words, 0, rows)
    if entry is None:
        # A failed content match is intentionally handed back to the older
        # room grammar, preserving commands such as "Wren opens the cabinet".
        return None
    if actor is None:
        actor={"doran":"p0","wren":"p1"}.get(str(entry.get("owner","")).lower())
    if actor is None:
        raise IntentError("the visible content has no party owner")
    action={"type":"content","actor":actor,"content_id":entry["id"]}
    before = " ".join(name_words[:match_start]).lower()
    after = " ".join(content_words[match_end:]).lower()
    surrounding = f"{before} {after}".strip()
    metamagic = {
        "split ray": "split_ray",
        "twin": "twin",
        "distant": "distant",
        "empower": "empower",
        "maximize": "maximize",
    }
    modifiers = [value for phrase, value in metamagic.items() if phrase in surrounding]
    if modifiers:
        action["parameters"] = {"metamagic": modifiers}
    if entry.get("id")=="wren.staff_magi" and "absorb" in surrounding and "spell" in surrounding:
        action.setdefault("parameters", {})["mode"]="absorb"
    # Preserve a simple target phrase for future resolver-specific lowering;
    # the content resolver still owns legality and entity resolution.
    target_match = re.search(r"\b(?:on|at|against)\s+(.+)$", after)
    if target_match:
        action["target_text"] = target_match.group(1).strip()
    return action


def _resolve_visible(raw: str, candidates: list[tuple[str, str]], role: str) -> str:
    key = raw.lower().replace("_", " ")
    matches = {identifier for label, identifier in candidates
               if label.lower().replace("_", " ") == key}
    if len(matches) == 1:
        return next(iter(matches))
    if len(matches) > 1:
        labels = sorted({label for label, identifier in candidates if identifier in matches})
        raise IntentClarification(
            f"I need clarification: which {role} do you mean — " + ", ".join(labels) + "?"
        )
    return raw


def _contextualize(words: list[str], context: dict | None) -> list[str]:
    """Replace visible multi-word names before the grammar parser runs."""
    entities = _visible_entities(context)
    candidates = [(label, ident) for group in entities.values() for label, ident in group]
    for label, identifier in sorted(candidates, key=lambda item: len(item[0]), reverse=True):
        label_words = label.split()
        for index in range(len(words) - len(label_words) + 1):
            if [ _token(w).lower() for w in words[index:index + len(label_words)] ] == [w.lower() for w in label_words]:
                resolved = _resolve_visible(label, candidates, "actor or target")
                words[index:index + len(label_words)] = [resolved]
                break
    return words


def _combat_target(raw: str, context: dict | None) -> str:
    """Resolve a visible combat entity the same way attack targets resolve."""
    candidates = _visible_entities(context).get("target", [])
    if context is not None and candidates:
        target = _resolve_visible(raw, candidates, "target")
        if target not in {identifier for _, identifier in candidates}:
            raise IntentError(f"{raw} is not a visible combat entity")
        return target
    return raw


HELP_CONNECTORS = {"against", "attack", "attacking", "vs", "versus", "with", "on", "at"}


def _parse_help(words: list[str], actor: str, context: dict | None) -> dict:
    """``help <ally> against <foe>`` or ``help against <foe>`` (the engine picks the ally)."""
    tail = [_token(word) for word in words if _token(word)]
    if not tail:
        raise IntentError("help needs a foe: say 'help <ally> against <foe>' (type /help for console commands)")
    split = next((index for index, word in enumerate(tail) if word.lower() in HELP_CONNECTORS), None)
    ally_words = _arguments(tail[:split] if split is not None else [])
    foe_words = _arguments(tail[split + 1:] if split is not None else tail)
    if not foe_words:
        raise IntentError("help needs a foe within 5 feet: say 'help <ally> against <foe>'")
    action = {"type": "help", "actor": actor}
    if ally_words:
        action["ally"] = _resolve_actor(" ".join(ally_words), context)
    foe = _combat_target(" ".join(foe_words), context)
    if str(foe).startswith("p") and foe[1:].isdigit() and "ally" not in action:
        raise IntentError("help needs a foe: say 'help <ally> against <foe>'")
    action["target"] = foe
    return action


def _parse_decant(words: list[str], actor: str, context: dict | None) -> dict:
    """``decant <item> [for|into <party member>] [replacing <attuned power>]``."""
    tail = [_token(word) for word in words if _token(word)]
    lowered = [word.lower() for word in tail]
    replace = None
    for marker in ("replacing", "replace", "over"):
        if marker in lowered:
            index = lowered.index(marker)
            replace = " ".join(_arguments(tail[index + 1:])) or None
            tail, lowered = tail[:index], lowered[:index]
            break
    for marker in ("for", "into", "onto", "to"):
        if marker in lowered:
            index = lowered.index(marker)
            owner = " ".join(_arguments(tail[index + 1:]))
            if owner:
                actor = _resolve_actor(owner, context)
            tail = tail[:index]
            break
    item_words = _arguments(tail)
    if not item_words:
        raise IntentError("decant requires a visible inventory item")
    raw_item = " ".join(item_words)
    candidates = _visible_entities(context).get("item", [])
    item = _resolve_visible(raw_item, candidates, "inventory item") if candidates else raw_item
    if candidates and item not in {identifier for _, identifier in candidates}:
        raise IntentError("decant target is not a visible inventory item")
    action = {"type": "decant", "actor": actor, "item": item}
    if replace:
        action["replace"] = replace
    return action


def parse_intent(text: str, context: dict | None = None) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise IntentError("intent must be non-empty")
    if len(text) > 2000:
        raise IntentError("intent must be at most 2000 characters")
    normalized_text = text.strip().lower()
    if normalized_text in {"party status", "party health", "show party status", "show party health"}:
        return {"type": "query", "data": "party_status"}
    if normalized_text in {"look around", "show room"}:
        return {"type": "observe_room"}
    if normalized_text == "show my equipment":
        return {"type": "query", "data": "equipment"}
    if normalized_text in {"explain that", "explain this", "explain the result",
                           "why did that happen", "why did that happen?",
                           "why did it happen"}:
        return {"type": "explain", "subject": "last_result"}
    examine_match = re.fullmatch(r"(?:examine|inspect closely|look closely at)\s+(?:the\s+)?(.+)", normalized_text)
    if examine_match:
        query = examine_match.group(1).strip()
        visible = _visible_entities(context)
        matches = []
        for kind in ("item", "actor", "target", "object"):
            candidates = visible.get(kind, [])
            try:
                identifier = _resolve_visible(query, candidates, kind) if candidates else query
            except IntentClarification:
                raise
            if identifier in {value for _, value in candidates}:
                matches.append((kind, identifier))
        identifiers = {identifier for _, identifier in matches}
        if len(identifiers) > 1:
            raise IntentClarification(f"I need clarification: which visible {query} do you mean?")
        if len(identifiers) == 1:
            identifier = next(iter(identifiers))
            kind = next(kind for kind in ("item", "actor", "target", "object")
                        if (kind, identifier) in matches)
            return {"type": "examine", "entity_type": kind, "entity_id": identifier}
        return {"type": "examine", "query": query}
    resident_match = re.fullmatch(r"(?:talk to|thank)\s+(.+)", normalized_text)
    if resident_match:
        target_text = resident_match.group(1).strip()
        resident = (context or {}).get("room", {}).get("resident") if isinstance((context or {}).get("room"), dict) else None
        if isinstance(resident, str) and _same_name(target_text, resident):
            target_text = resident
        return {"type": "talk", "target": target_text, "mode": "speak", "text": ""}
    life_action = _life_parse(text, context)
    if life_action is not None:
        return life_action
    sandbox_action = _sandbox_parse(text, context)
    if sandbox_action is not None:
        return sandbox_action
    words = _contextualize(text.strip().split(), context)
    content_action = _parse_content_sentence(words, context)
    if content_action is not None:
        return content_action
    # Keep connective conversation useful when it still names one visible,
    # unambiguous room-level intent.  These clauses are deliberately bounded
    # to the room/environment vocabulary; an object or actor phrase continues
    # through the stricter grammar below so the host can reject or clarify it
    # instead of guessing.
    room_investigation = re.compile(
        r"\b(?:study|survey|inspect|examine|observe|search|look(?:\s+around|\s+over)?)\b"
        r"[^.!?\n]*\b(?:room|area|scene|surroundings|market|settlement|place)\b"
    )
    if room_investigation.search(normalized_text):
        return {"type": "investigate"}
    normalized=[]
    index=0
    while index < len(words):
        first=_token(words[index]).lower()
        if first == 'test' and index + 1 < len(words) and _token(words[index+1]).lower() == 'perception':
            normalized.append('test-perception'); index += 2; continue
        if first == 'reveal' and index + 2 < len(words) and [_token(words[index+j]).lower() for j in (1,2)] == ['room','record']:
            normalized.append('reveal-room-record'); index += 3; continue
        if first in {'break', 'breaks'} and index + 1 < len(words) and _token(words[index+1]).lower() == 'free':
            normalized.append('escape_grapple'); index += 2; continue
        normalized.append(words[index]); index += 1
    words = normalized
    aliases = {"attacks": "attack", "opens": "open_object", "open": "open_object", "searches": "search_object", "search": "search_object", "examines": "inspect_object", "examine": "inspect_object", "lights": "light_source", "light": "light_source", "walks": "enter_subroom", "walk": "enter_subroom", "enters": "enter_subroom", "enter": "enter_subroom", "negotiates": "negotiate", "avoids": "avoid", "disarms": "disarm", "fights": "fight", "buys": "buy", "purchase": "buy", "purchases": "buy", "rent": "buy", "rents": "buy", "identifies": "identify", "flies": "fly", "flying": "fly", "lands": "land", "landing": "land", "reforge": "reforge_affix", "affix": "reforge_affix",
               # Contextual D&D actions and the Attunement Matrix.
               "dodges": "dodge", "dashes": "dash", "disengages": "disengage",
               "shoves": "shove", "push": "shove", "pushes": "shove",
               "trips": "trip", "knock": "trip", "knocks": "trip",
               "grapples": "grapple", "grab": "grapple", "grabs": "grapple",
               "assist": "help", "assists": "help", "aid": "help", "aids": "help", "helps": "help",
               "decants": "decant", "devour": "decant", "devours": "decant",
               "disenchant": "decant", "disenchants": "decant"}
    words = [aliases.get(_token(word).lower(), _token(word)) for word in words]
    supported = {"attack", "move", "investigate", "negotiate", "avoid", "disarm", "fight", "buy", "test-perception", "reveal-room-record", "cast", "equip", "identify", "combine", "reforge_affix", "rest", "inspect", "exit", "retreat", "escape", "reset", "decline", "end_concentration", "staff_utility", "force_regurgitation", "observe_room", "inspect_room", "inspect_object", "search_object", "open_object", "light_source", "enter_subroom", "fly", "land",
                 "dodge", "dash", "disengage", "shove", "trip", "grapple", "escape_grapple", "help", "decant"}
    command_index = next((i for i, word in enumerate(words) if _token(word).lower() in supported), None)
    if command_index is None:
        raise IntentError("could not translate intent; use a supported combat, room, or dungeon action")
    preceding_candidate = _token(words[command_index - 1]) if command_index else None
    preceding_actor = (preceding_candidate if preceding_candidate and preceding_candidate.lower()
                       not in {"i", "want", "to", "please", "the", "a", "an"} else None)
    words = words[command_index:]
    command = _token(words[0]).lower()
    if command in {"investigate", "test-perception", "reveal-room-record", "rest", "inspect", "exit", "retreat", "reset", "end_concentration", "observe_room", "inspect_room"}:
        return {"type": command}
    actor = _actor_id(preceding_actor, context)
    if command in {"avoid", "disarm", "fight"}:
        return {"type": command, "actor": actor}
    if command in {"dodge", "dash", "disengage", "escape_grapple"}:
        return {"type": command, "actor": actor}
    if command in {"shove", "trip", "grapple"}:
        arguments = _arguments(words[1:], connectors={"to", "into", "onto", "over"})
        if not arguments:
            raise IntentError(f"{command} requires a visible target")
        action = {"type": command, "actor": actor, "target": _combat_target(arguments[0], context)}
        if command == "shove" and {"prone", "down"} & {word.lower() for word in arguments[1:]}:
            action["mode"] = "prone"
        return action
    if command == "help":
        return _parse_help(words[1:], actor, context)
    if command == "decant":
        return _parse_decant(words[1:], actor, context)
    if command in {"fly", "land"}:
        if isinstance(context, dict) and isinstance(context.get("arcade"), dict):
            return {"type": "arcade_toggle_flight", "actor": actor, "on": command == "fly"}
        return {"type": command, "actor": actor}
    if command == "negotiate":
        action = {"type": command, "actor": actor}
        target_words = _arguments(words[1:], connectors={"with", "to"})
        if target_words:
            target = " ".join(target_words)
            resident = (context or {}).get("room", {}).get("resident") if isinstance((context or {}).get("room"), dict) else None
            if not isinstance(resident, str) or not _same_name(target, resident):
                raise IntentError("negotiation target is not the visible room resident")
            action["target"] = resident
        return action
    if command == "buy":
        product_words = _arguments(words[1:], connectors={"for"})
        if not product_words:
            raise IntentError("buy requires a visible product")
        return {"type": "buy", "actor": actor, "product": "_".join(product_words).lower()}
    if command == "identify":
        item_words = _arguments(words[1:])
        if not item_words:
            raise IntentError("identify requires a visible inventory item")
        raw_item = " ".join(item_words)
        candidates = _visible_entities(context).get("item", [])
        if candidates:
            item = _resolve_visible(raw_item, candidates, "inventory item")
            if item not in {identifier for _, identifier in candidates}:
                raise IntentError("identify target is not a visible inventory item")
        elif context is not None:
            raise IntentError("identify requires a visible inventory item")
        else:
            item = raw_item
        return {"type": "identify", "actor": actor, "item": item}
    if command == "reforge_affix":
        if "with" not in [word.lower() for word in words[1:]]:
            raise IntentError("reforge requires an inventory item and an active affix: reforge <item> with <affix>")
        split = next(index for index, word in enumerate(words[1:], 1) if word.lower() == "with")
        raw_item = " ".join(_arguments(words[1:split]))
        affix = " ".join(_arguments(words[split + 1:]))
        if not raw_item or not affix:
            raise IntentError("reforge requires an inventory item and an active affix")
        candidates = _visible_entities(context).get("item", [])
        item = _resolve_visible(raw_item, candidates, "inventory item") if candidates else raw_item
        return {"type": "reforge_affix", "actor": actor, "item": item, "affix": affix}
    if command in {"inspect_object", "search_object", "open_object"} and len(words) >= 2:
        object_words = _arguments(words[1:])
        if not object_words:
            raise IntentError(f"{command} requires a visible object")
        raw_object = " ".join(object_words)
        candidates = _visible_entities(context).get("object", [])
        object_id = _resolve_visible(raw_object, candidates, "object") if candidates else raw_object
        return {"type": command, "actor": actor, "object_id": object_id}
    if command == "light_source" and len(words) >= 2:
        source_words = _arguments(words[1:])
        if not source_words:
            raise IntentError("light_source requires a source")
        return {"type": command, "actor": actor, "source": "_".join(source_words).lower()}
    if command == "enter_subroom" and len(words) >= 2:
        location_words = _arguments(words[1:], connectors={"room", "into", "behind"})
        if not location_words:
            raise IntentError("enter_subroom requires a destination")
        return {"type": command, "actor": actor, "location": "_".join(location_words).lower()}
    if command == "escape" and len(words) >= 2 and "grapple" in {_token(word).lower() for word in words[1:]}:
        return {"type": "escape_grapple", "actor": actor}
    if command == "escape" and len(words) >= 2:
        route_words=[_token(word) for word in words[1:] if _token(word).lower() not in {"via","through","from"}]
        return {"type":"escape", "route":" ".join(route_words)}
    if command == "staff_utility" and len(words) >= 3:
        action={"type":"staff_utility","actor":_token(words[1]),"mode":_token(words[2])}
        if len(words) > 3: action["target"]=_token(words[3])
        return action
    if command == "force_regurgitation" and len(words) >= 3:
        return {"type":"force_regurgitation","actor":_token(words[1]),"target":_token(words[2])}
    if command == "decline" and len(words) >= 2:
        return {"type": "decline_reaction", "actor": _token(words[1])}
    if command == "attack" and len(words) >= 2:
        arguments = _arguments(words[1:])
        explicit_actor = preceding_actor
        if not explicit_actor and len(arguments) >= 2 and (re.fullmatch(r"p\d+", arguments[0].lower()) or arguments[0].lower() in {"doran", "wren"}):
            explicit_actor = arguments.pop(0)
        actor = _actor_id(explicit_actor, context)
        if not arguments:
            raise IntentError("attack requires a visible target")
        target = arguments[0]
        room = (context or {}).get("room") if isinstance(context, dict) else None
        combat = (context or {}).get("combat") if isinstance(context, dict) else None
        resident = room.get("resident") if isinstance(room, dict) else None
        if not combat and isinstance(resident, str) and _same_name(target, resident):
            raise IntentError(f"{resident} is a room resident, not a combat entity; use fight to enter the room conflict")
        target_candidates = _visible_entities(context).get("target", [])
        if context is not None and target_candidates:
            target = _resolve_visible(target, target_candidates, "target")
            if target not in {identifier for _, identifier in target_candidates}:
                raise IntentError("attack target is not a visible combat entity")
        action = {"type": "attack", "actor": actor, "target": target}
        extras = [word.lower().rstrip(",.!?") for word in arguments[1:]]
        if "bonus" in extras: action["bonus"] = True
        modes = [word for word in extras if word != "bonus"]
        if len(modes) > 1: raise IntentError("attack accepts at most one weapon mode")
        if modes: action["mode"] = modes[0]
        return action
    if command == "move" and len(words) >= 4:
        coordinate_words=[_token(word) for word in words[2:] if _token(word).lower() not in {"to","at"}]
        coordinate_text=" ".join(coordinate_words).replace(",", " ")
        try:
            destination = [int(value) for value in coordinate_text.split()]
        except ValueError as exc:
            raise IntentError("move coordinates must be integers") from exc
        if len(destination) != 3:
            raise IntentError("move requires exactly three coordinates")
        return {"type": "move", "actor": _token(words[1]), "destination": destination}
    if command == "cast" and len(words) >= 3:
        return {"type": "cast", "actor": _token(words[1]), "spell": _token(words[2]), "targets": [_token(word) for word in words[3:]]}
    if command == "equip" and len(words) >= 3:
        return {"type": "equip", "actor": _token(words[1]), "item": _token(words[2])}
    raise IntentError("could not translate intent; provide the actor and required arguments")
