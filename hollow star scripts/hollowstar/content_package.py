"""Compiler-facing, data-only scene package contract and public projections.

This is a target for future compilers, not a semantic interpretation of canon.
Packages have no executable code, arbitrary URLs, mechanical effects, or save
paths. Gameplay bindings must be added through the authoritative rules engine.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re

from hollowstar.source_catalog import SourceCatalog, SourceError, relative_path


SCHEMA = "hollow-star-content-package-1"
VIEW_SCHEMA = "hollow-star-content-preview-1"
MAX_PACKAGE_BYTES = 665_600  # 512,000 + 30% (2026-09-23)
PRESENTATION_ASSETS = {
    "townsperson": "/assets/townsperson.png",
    "longsword": "/assets/longsword.png",
    "chain-shirt": "/assets/chain-shirt.png",
    "unidentified-rune": "/assets/unidentified-rune.png",
}
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
HASH = re.compile(r"^[0-9a-f]{64}$")


class PackageError(ValueError):
    """A compiler package does not satisfy the versioned content contract."""


def _object(value, required, optional, label):
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        raise PackageError(f"{label}: required fields {sorted(required)}, optional fields {sorted(optional)}")


def _text(value, label, maximum=12_000, empty=False):
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value.strip()):
        raise PackageError(f"{label}: expected {'optional' if empty else 'non-empty'} text, at most {maximum} characters")
    if any((ord(c) < 32 and c not in "\n\t\r") or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise PackageError(f"{label}: control characters and invalid Unicode are not supported")
    return value


def _id(value, label):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise PackageError(f"{label}: expected lowercase identifier (letters, digits, underscores, hyphens; max 64)")
    return value


def _list(value, label, maximum=256):
    if not isinstance(value, list) or len(value) > maximum:
        raise PackageError(f"{label}: expected list with at most {maximum} entries")
    return value


def _refs(value, known, label):
    _list(value, label)
    if any(not isinstance(ref, str) or ref not in known for ref in value) or len(set(value)) != len(value):
        raise PackageError(f"{label}: references must exist and must not repeat")


def encode(package):
    try:
        return json.dumps(package, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError, RecursionError) as exc:
        raise PackageError("package must be finite JSON data") from exc


def fingerprint(package):
    return hashlib.sha256(encode(package).encode("utf-8")).hexdigest()


def validate_package(raw, catalog: SourceCatalog | None = None):
    encoded = encode(raw)
    if len(encoded.encode("utf-8")) > MAX_PACKAGE_BYTES:
        raise PackageError("package exceeds 512 KB")
    _object(raw, {"schema_version", "id", "version", "title", "universe", "entry_scene", "sources", "scenes", "entities"}, {"timeline", "notes"}, "package")
    if raw["schema_version"] != SCHEMA:
        raise PackageError(f"unsupported schema_version; expected {SCHEMA}")
    _id(raw["id"], "package.id")
    for field in ("version", "title", "universe"):
        _text(raw[field], field, 200)
    for field in ("timeline", "notes"):
        if field in raw:
            _text(raw[field], field, empty=True)
    source_ids, entity_ids, scene_ids = set(), set(), set()
    warnings = []
    for source in _list(raw["sources"], "sources", 128):
        _object(source, {"id", "path", "sha256", "start_line", "end_line"}, set(), "source")
        source_id = _id(source["id"], "source.id")
        if source_id in source_ids:
            raise PackageError(f"duplicate source id: {source_id}")
        source_ids.add(source_id)
        try:
            relative_path(source["path"])
        except SourceError as exc:
            raise PackageError(str(exc)) from exc
        if not isinstance(source["sha256"], str) or not HASH.fullmatch(source["sha256"]):
            raise PackageError("source.sha256 must be a lowercase SHA-256 digest")
        if (type(source["start_line"]) is not int or type(source["end_line"]) is not int
                or not 1 <= source["start_line"] <= source["end_line"]
                or source["end_line"] - source["start_line"] >= 400):
            raise PackageError("source line ranges must cover 1 to 400 lines, starting at line 1 or later")
        if catalog is not None:
            try:
                receipt = catalog.read(source["path"], start_line=source["start_line"],
                                       line_count=source["end_line"] - source["start_line"] + 1,
                                       include_archives=True, expected_sha256=source["sha256"])
                if receipt["end_line"] != source["end_line"]:
                    raise SourceError("source range extends beyond the source")
                if receipt["classification"] == "archive":
                    warnings.append(f"{source_id}: archived reference, not a live authority")
            except (OSError, SourceError) as exc:
                raise PackageError(f"source {source_id}: {exc}") from exc
    if not source_ids:
        warnings.append("Unsourced draft: suitable for preview, not a claim of canon fidelity.")
    for entity in _list(raw["entities"], "entities", 512):
        _object(entity, {"id", "kind", "name", "description", "source_ids"}, {"visibility", "interactions", "asset_id"}, "entity")
        key = _id(entity["id"], "entity.id")
        if key in entity_ids:
            raise PackageError(f"duplicate entity id: {key}")
        entity_ids.add(key)
        if entity["kind"] not in ("character", "item", "prop"):
            raise PackageError("entity.kind must be character, item, or prop")
        _text(entity["name"], "entity.name", 200)
        _text(entity["description"], "entity.description")
        _refs(entity["source_ids"], source_ids, "entity.source_ids")
        if "asset_id" in entity and (not isinstance(entity["asset_id"], str) or entity["asset_id"] not in PRESENTATION_ASSETS):
            raise PackageError("entity.asset_id must name registered local presentation art")
        if entity.get("visibility", "visible") not in ("visible", "hidden"):
            raise PackageError("entity.visibility must be visible or hidden")
        seen = set()
        for action in _list(entity.get("interactions", []), "entity.interactions", 32):
            _object(action, {"id", "label", "text"}, set(), "interaction")
            action_id = _id(action["id"], "interaction.id")
            if action_id in seen:
                raise PackageError("duplicate interaction id")
            seen.add(action_id)
            _text(action["label"], "interaction.label", 200)
            _text(action["text"], "interaction.text")
    scenes = _list(raw["scenes"], "scenes")
    if not scenes:
        raise PackageError("package requires at least one scene")
    for scene in scenes:
        _object(scene, {"id", "title", "description", "entities", "exits", "source_ids"}, {"kind", "theme"}, "scene")
        key = _id(scene["id"], "scene.id")
        if key in scene_ids:
            raise PackageError(f"duplicate scene id: {key}")
        scene_ids.add(key)
        _text(scene["title"], "scene.title", 200)
        _text(scene["description"], "scene.description")
        if scene.get("kind", "scene") not in ("scene", "screen"):
            raise PackageError("scene.kind must be scene or screen")
        if scene.get("theme", "astral") not in ("astral", "ember", "forest", "stone"):
            raise PackageError("unsupported scene theme")
        _refs(scene["entities"], entity_ids, "scene.entities")
        _refs(scene["source_ids"], source_ids, "scene.source_ids")
        seen = set()
        for link in _list(scene["exits"], "scene.exits", 32):
            _object(link, {"id", "label", "target"}, set(), "exit")
            key = _id(link["id"], "exit.id")
            if key in seen:
                raise PackageError("duplicate exit id")
            seen.add(key)
            _text(link["label"], "exit.label", 200)
            _id(link["target"], "exit.target")
    if not isinstance(raw["entry_scene"], str) or raw["entry_scene"] not in scene_ids:
        raise PackageError("entry_scene must reference an existing scene")
    for scene in scenes:
        if any(link["target"] not in scene_ids for link in scene["exits"]):
            raise PackageError(f"scene {scene['id']} has a dangling exit")
    by_id = {scene["id"]: scene for scene in scenes}
    reached, pending = set(), [raw["entry_scene"]]
    while pending:
        key = pending.pop()
        if key not in reached:
            reached.add(key)
            pending.extend(link["target"] for link in by_id[key]["exits"])
    if reached != scene_ids:
        raise PackageError("unreachable scenes: " + ", ".join(sorted(scene_ids - reached)))
    return {"package": copy.deepcopy(raw), "package_hash": fingerprint(raw), "warnings": warnings,
            "counts": {"scenes": len(scenes), "entities": len(entity_ids), "sources": len(source_ids)},
            "source_verification": "verified" if catalog is not None else "not_checked",
            "capabilities": ["navigate", "inspect", "interact"], "mechanics": "unbound"}


def source_starter(source, title=None, universe="unspecified"):
    """Wrap an explicitly selected excerpt verbatim; do not infer people or rules."""
    if not source["text"].strip() or len(source["text"]) > 12_000:
        raise PackageError("select a non-empty source excerpt of at most 12,000 characters")
    return {"schema_version": SCHEMA, "id": "source-" + source["sha256"][:12], "version": "0.1.0",
            "title": title or source["path"].rsplit("/", 1)[-1], "universe": universe,
            "notes": "Verbatim source excerpt. Scene structure and mechanics have not been inferred.",
            "entry_scene": "excerpt", "sources": [{"id": "source", **{key: source[key] for key in
                ("path", "sha256", "start_line", "end_line")}}], "entities": [],
            "scenes": [{"id": "excerpt", "kind": "screen", "title": title or "Source excerpt",
                        "description": source["text"], "entities": [], "exits": [], "source_ids": ["source"]}]}


def initial_state(package):
    return {"scene_id": package["entry_scene"], "visited": [package["entry_scene"]], "inspected": [], "last_event": None}


def transition(package, state, action):
    _object(action, {"type", "target"}, {"interaction_id"}, "action")
    scene = next(s for s in package["scenes"] if s["id"] == state["scene_id"])
    result = copy.deepcopy(state)
    if action["type"] == "navigate":
        link = next((link for link in scene["exits"] if link["id"] == action["target"]), None)
        if link is None or "interaction_id" in action:
            raise PackageError("exit is not available in the current scene")
        result["scene_id"] = link["target"]
        if link["target"] not in result["visited"]:
            result["visited"].append(link["target"])
        result["last_event"] = {"type": "navigate", "text": link["label"]}
    elif action["type"] in ("inspect", "interact"):
        entity = next((e for e in package["entities"] if e["id"] == action["target"]
                       and e["id"] in scene["entities"] and e.get("visibility", "visible") == "visible"), None)
        if entity is None:
            raise PackageError("entity is not visible in the current scene")
        text = entity["description"]
        if action["type"] == "interact":
            choice = next((i for i in entity.get("interactions", []) if i["id"] == action.get("interaction_id")), None)
            if choice is None:
                raise PackageError("interaction is not available on this entity")
            text = choice["text"]
        elif "interaction_id" in action:
            raise PackageError("inspect does not accept an interaction_id")
        if entity["id"] not in result["inspected"]:
            result["inspected"].append(entity["id"])
        result["last_event"] = {"type": action["type"], "entity_id": entity["id"], "name": entity["name"], "text": text}
    else:
        raise PackageError("preview supports navigate, inspect, and interact; mechanical actions require an engine binding")
    return result


def public_view(package, state, preview_id, revision):
    scene = next(s for s in package["scenes"] if s["id"] == state["scene_id"])
    entities = [{"id": e["id"], "kind": e["kind"], "name": e["name"],
                 "inspected": e["id"] in state["inspected"],
                 **({"art": {"asset_id": e["asset_id"], "src": PRESENTATION_ASSETS[e["asset_id"]]}} if e.get("asset_id") else {}),
                 "interactions": [{"id": i["id"], "label": i["label"]} for i in e.get("interactions", [])]}
                for e in package["entities"] if e["id"] in scene["entities"] and e.get("visibility", "visible") == "visible"]
    return {"schema_version": VIEW_SCHEMA, "preview_id": preview_id, "revision": revision,
            "package": {key: package[key] for key in ("id", "version", "title", "universe")},
            "package_hash": fingerprint(package), "preview_only": True, "mechanics": "unbound",
            "scene": {key: scene[key] for key in ("id", "title", "description")},
            "theme": scene.get("theme", "astral"), "kind": scene.get("kind", "scene"),
            "entities": entities, "exits": [{"id": link["id"], "label": link["label"]} for link in scene["exits"]],
            "visited_count": len(state["visited"]), "last_event": copy.deepcopy(state["last_event"])}
