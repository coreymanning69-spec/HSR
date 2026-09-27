"""Deterministic, source-linked Markdown drafts for the local Content Workbench.

This parser recognizes editorial structure, never canon authority or mechanics.
Unrecognized prose remains visible in the draft for human review.
"""
from __future__ import annotations

import re

from hollowstar.content_package import SCHEMA, PackageError


HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
ENTITY = re.compile(r"^(?:[-*]\s*)?(Character|Item|Prop):\s*(.+?)\s*$", re.I)
INTERACTION = re.compile(r"^(?:[-*]\s*)?Interaction:\s*(.+?)\s*$", re.I)
SLUG = re.compile(r"[^a-z0-9]+")


def _slug(value: str, fallback: str) -> str:
    result = SLUG.sub("-", value.casefold()).strip("-")[:55].rstrip("-")
    return result or fallback


def _unique(value: str, used: set[str]) -> str:
    base = value[:55].rstrip("-") or "entry"
    result, number = base, 2
    while result in used:
        result = f"{base}-{number}"
        number += 1
    used.add(result)
    return result


def interpret_markdown(source: dict) -> dict:
    """Return a package and review flags from one SourceCatalog.read receipt."""
    if not source["path"].lower().endswith(".md"):
        raise PackageError("interpretation requires a Markdown source")
    lines = source["text"].splitlines()
    if not lines or not any(line.strip() for line in lines):
        raise PackageError("select a non-empty Markdown range")
    flags: list[dict] = []
    metadata: dict[str, str] = {}
    body_start = 0
    if source["start_line"] == 1 and lines[0].strip() == "---":
        closing = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if closing is None:
            flags.append({"line": 1, "message": "Frontmatter has no closing delimiter; kept as prose."})
        else:
            for line in lines[1:closing]:
                match = re.match(r"^([a-z_]+):\s*(.*?)\s*$", line)
                if match and match.group(1) in {"title", "verse", "timeline"}:
                    metadata[match.group(1)] = match.group(2).strip('"\'')
            body_start = closing + 1
    sections: list[dict] = []
    current = {"title": metadata.get("title") or source["path"].rsplit("/", 1)[-1],
               "start": body_start, "lines": []}
    fenced = False
    for i in range(body_start, len(lines)):
        line = lines[i]
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        match = None if fenced else HEADING.match(line)
        if match:
            if current["lines"] or sections:
                sections.append(current)
            current = {"title": match.group(2), "start": i, "lines": []}
        else:
            current["lines"].append((i, line))
    sections.append(current)
    if len(sections) > 128:
        raise PackageError("interpretation has more than 128 sections; select a smaller range")
    sources, scenes, entities = [], [], []
    scene_ids: set[str] = set()
    entity_ids: set[str] = set()
    for index, section in enumerate(sections):
        title = section["title"][:200]
        scene_id = _unique(_slug(title, f"section-{index + 1}"), scene_ids)
        source_id = f"source-{index + 1}"
        first = source["start_line"] + section["start"]
        last = source["start_line"] + (section["lines"][-1][0] if section["lines"] else section["start"])
        first = min(first, source["end_line"])
        last = max(first, min(last, source["end_line"]))
        sources.append({"id": source_id, "path": source["path"], "sha256": source["sha256"],
                        "start_line": first, "end_line": last})
        prose: list[str] = []
        visible: list[str] = []
        for offset, line in section["lines"]:
            entity_match = ENTITY.match(line)
            interaction_match = INTERACTION.match(line)
            if entity_match:
                kind = entity_match.group(1).lower()
                parts = re.split(r"\s+[—–|]\s+", entity_match.group(2), maxsplit=1)
                name = parts[0].strip()
                if not name:
                    prose.append(line)
                    flags.append({"line": source["start_line"] + offset, "message": "Entity label has no name; kept as prose."})
                    continue
                entity_id = _unique(_slug(name, "entity"), entity_ids)
                entities.append({"id": entity_id, "kind": kind, "name": name[:200],
                                 "description": (parts[1].strip() if len(parts) > 1 else name)[:12000],
                                 "source_ids": [source_id], "interactions": []})
                visible.append(entity_id)
                if len(parts) == 1:
                    flags.append({"line": source["start_line"] + offset, "message": "Entity has no explicit description; review its card."})
            elif interaction_match:
                parts = [part.strip() for part in interaction_match.group(1).split("|", 2)]
                target = next((entity for entity in reversed(entities) if entity["id"] in visible
                               and entity["name"].casefold() == parts[0].casefold()), None)
                if len(parts) != 3 or not target or not all(parts):
                    prose.append(line)
                    flags.append({"line": source["start_line"] + offset,
                                  "message": "Interaction needs a visible target, label, and result separated by |; kept as prose."})
                    continue
                action_ids = {action["id"] for action in target["interactions"]}
                target["interactions"].append({"id": _unique(_slug(parts[1], "interaction"), action_ids),
                                                "label": parts[1][:200], "text": parts[2][:12000]})
            else:
                prose.append(line)
        description = "\n".join(prose).strip() or title
        if len(description) > 12000:
            raise PackageError(f"section {title!r} exceeds the scene description limit; select a smaller range")
        if description == title:
            flags.append({"line": first, "message": "Section has no prose; review its draft screen."})
        scenes.append({"id": scene_id, "kind": "screen", "title": title,
                       "description": description, "entities": visible, "exits": [], "source_ids": [source_id]})
    for index, scene in enumerate(scenes[:-1]):
        following = scenes[index + 1]
        scene["exits"].append({"id": "next", "label": f"Next section: {following['title']}", "target": following["id"]})
    if not entities:
        flags.append({"line": source["start_line"], "message": "No explicit entity labels found; prose remains as scene text."})
    package = {"schema_version": SCHEMA, "id": "draft-" + source["sha256"][:12], "version": "0.1.0",
               "title": (metadata.get("title") or sections[0]["title"])[:200],
               "universe": (metadata.get("verse") or "unspecified")[:200],
               "entry_scene": scenes[0]["id"], "sources": sources, "scenes": scenes, "entities": entities,
               "notes": "Local Markdown interpretation draft. Section order is editorial navigation; review all claims. Mechanics unbound."}
    if metadata.get("timeline"):
        package["timeline"] = metadata["timeline"][:12000]
    return {"package": package, "review_flags": flags}
