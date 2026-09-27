"""Editable local custom-character profiles and read-only roster views."""

from __future__ import annotations

import copy
import json
from hollowstar.storage import atomic_json
import math
import re
from pathlib import Path

from hollowstar.actors import Actor, Band, DND_ABILITIES, Provenance
from hollowstar.items import Item, public_item
from hollowstar.phases import Tier
from hollowstar.snapshot import import_party, assert_safe_write_path

PROFILE_SCHEMA_V1 = "hollow-star-custom-profile-1"
PROFILE_SCHEMA_V2 = "hollow-star-custom-profile-2"
PROFILE_SCHEMA = "hollow-star-custom-profile-3"
_ID = re.compile(r"^[A-Za-z0-9_-]+$")
_SLOTS = {"hand", "armor", "ring", "neck", "cloak", "boots", "head"}


class ProfileError(ValueError):
    pass


def presentation_sprite_id(race_id: str, gender: str) -> str:
    """Return stable presentation identity; it has no mechanical meaning."""
    return f"{race_id}-{gender}"


# Cosmetic appearance is presentation only.  Nothing resolved here reaches
# ability scores, AC, initiative, saves, or the RNG -- a build that differs
# only in appearance must roll identically.  The catalog lives in
# content/character_creation.json so art options can be added without code.
APPEARANCE_FIELDS = (
    "skin_tone", "face_shape", "facial_marks", "ear_shape", "hair_style", "hair_color",
    "eye_color", "body_type", "outfit", "cloak_style", "headgear_style",
    "weapon_style", "offhand_style", "trinket_style",
)


def _appearance_choices(field_row: dict, race_id: str) -> list[dict]:
    """Options this race may use.  An option with no `races` list suits all."""
    return [option for option in field_row.get("options", [])
            if not option.get("races") or race_id in option["races"]]


def normalize_appearance(data: object, catalog: dict, race_id: str) -> dict:
    """Validate a cosmetic selection against the registry catalog.

    Missing fields fall back to the first option the race can use, so profiles
    saved before appearance existed still build.  An unknown field or option id
    is an error rather than a silent default: a typo that quietly renders the
    wrong character is worse than a rejected build.
    """
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ProfileError("appearance must be an object")
    fields = (catalog or {}).get("fields", {})
    unknown = set(data) - set(fields)
    if unknown:
        raise ProfileError(f"unsupported appearance fields: {sorted(unknown)}")

    resolved: dict[str, dict] = {}
    for field in APPEARANCE_FIELDS:
        field_row = fields.get(field)
        if not isinstance(field_row, dict):
            raise ProfileError(f"character creation registry is missing appearance field {field!r}")
        choices = _appearance_choices(field_row, race_id)
        if not choices:
            raise ProfileError(f"no {field} option is available for race {race_id!r}")
        wanted = data.get(field)
        # Accept either a bare option id or an already-resolved entry, so a
        # saved sheet can be normalized again without being re-flattened first.
        if isinstance(wanted, dict):
            wanted = wanted.get("id")
        if wanted is None:
            option = choices[0]
        else:
            if not isinstance(wanted, str) or not wanted.strip():
                raise ProfileError(f"appearance {field} must be a non-empty string")
            key = wanted.strip().lower().replace("_", "-").replace(" ", "-")
            option = next((row for row in choices if row["id"] == key), None)
            if option is None:
                available = ", ".join(row["id"] for row in choices)
                raise ProfileError(
                    f"unsupported {field} {wanted!r} for race {race_id!r}; available: {available}")
        entry = {"id": option["id"], "name": option.get("name", option["id"])}
        for extra in ("hex", "scale", "visual"):
            if extra in option:
                entry[extra] = option[extra]
        resolved[field] = entry
    return resolved


def _stored_appearance(value: object, race_id: str) -> dict:
    """Appearance for a saved sheet, filling defaults for pre-appearance saves.

    The catalog lives with the character builder, which imports this module, so
    the import is deferred to keep the dependency one-way.  If the registry is
    unreachable we keep whatever the sheet already carried rather than failing a
    save over cosmetics.
    """
    try:
        from hollowstar.character_builder import _registry
        catalog = _registry().get("appearance", {})
    except Exception:
        return copy.deepcopy(value) if isinstance(value, dict) else {}
    return normalize_appearance(value, catalog, race_id)


def _integer(value: object, label: str, low: int, high: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ProfileError(f"{label} must be an integer from {low} through {high}")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProfileError(f"{label} must be a non-empty string")
    return value.strip()


def _item(data: object) -> Item:
    if not isinstance(data, dict):
        raise ProfileError("each equipment entry must be an object")
    allowed = {"name", "slot", "base_damage", "attack_bonus", "base_ac", "dex_cap", "ac_bonus", "shield_bonus", "attack_ability", "density", "temporary", "flavor", "damage_dice", "damage_modifier", "alternate_modes", "reach", "range_normal", "range_long", "critical_dice", "utility_uses", "sprite_id", "silhouette", "material", "item_type", "handedness", "coverage", "animation_profile"}
    if set(data) - allowed:
        raise ProfileError(f"unsupported equipment fields: {sorted(set(data) - allowed)}")
    slot = str(data.get("slot", "hand")).lower()
    if slot not in _SLOTS:
        raise ProfileError(f"unsupported equipment slot: {slot}")
    density = data.get("density", 1.0)
    if not isinstance(density, (int, float)) or isinstance(density, bool) or not math.isfinite(density) or density <= 0:
        raise ProfileError("equipment density must be a positive number")
    modes = data.get("alternate_modes", {})
    if not isinstance(modes, dict) or any(not isinstance(name, str) or not name.strip() or not isinstance(spec, dict) for name, spec in modes.items()):
        raise ProfileError("alternate_modes must map non-empty names to objects")
    dice = data.get("damage_dice", "")
    if not isinstance(dice, str) or (dice and not re.fullmatch(r"([1-9]|[1-9][0-9]|100)d(4|6|8|10|12|20)", dice)):
        raise ProfileError("damage_dice must be blank or 1..100 dice with 4, 6, 8, 10, 12, or 20 sides")
    critical_dice = data.get("critical_dice", "")
    if not isinstance(critical_dice, str) or (critical_dice and not re.fullmatch(r"([1-9]|[1-9][0-9]|100)d(4|6|8|10|12|20)", critical_dice)):
        raise ProfileError("critical_dice must be blank or 1..100 dice with 4, 6, 8, 10, 12, or 20 sides")
    utility_uses = data.get("utility_uses", [])
    if not isinstance(utility_uses, list) or any(not isinstance(row, str) or not row.strip() for row in utility_uses):
        raise ProfileError("utility_uses must be a list of non-empty strings")
    if not isinstance(data.get("temporary", False), bool):
        raise ProfileError("temporary must be a boolean")
    return Item(
        name=_text(data.get("name"), "equipment name"),
        slot=slot,
        base_damage=_integer(data.get("base_damage", 0), "base_damage", 0, 1000),
        attack_bonus=_integer(data.get("attack_bonus", 0), "attack_bonus", -100, 100),
        damage_dice=dice,
        damage_modifier=_integer(data.get("damage_modifier", 0), "damage_modifier", -100, 100),
        base_ac=_integer(data.get("base_ac", 0), "base_ac", 0, 100),
        dex_cap=data.get("dex_cap"),
        ac_bonus=_integer(data.get("ac_bonus", 0), "ac_bonus", -20, 20),
        shield_bonus=_integer(data.get("shield_bonus", 0), "shield_bonus", 0, 20),
        attack_ability=str(data.get("attack_ability", "")),
        alternate_modes={str(name): dict(spec) for name, spec in modes.items()},
        reach=_integer(data.get("reach", 5), "reach", 0, 1000),
        range_normal=_integer(data.get("range_normal", 5), "range_normal", 0, 10000),
        range_long=_integer(data.get("range_long", 5), "range_long", 0, 10000),
        critical_dice=critical_dice,
        tier=Tier.MUNDANE,
        density=float(density),
        temporary=bool(data.get("temporary", False)),
        flavor=str(data.get("flavor", "")),
        utility_uses=list(utility_uses),
        sprite_id=_text(data.get("sprite_id", ""), "equipment sprite_id") if data.get("sprite_id") else "",
        silhouette=str(data.get("silhouette", "")),
        material=str(data.get("material", "")),
        item_type=str(data.get("item_type", "")),
        handedness=str(data.get("handedness", "")),
        coverage=str(data.get("coverage", "")),
        animation_profile=str(data.get("animation_profile", "")),
    )


def _item_data(item: Item) -> dict:
    return {
        "name": item.name, "slot": item.slot, "base_damage": item.base_damage,
        "attack_bonus": item.attack_bonus, "base_ac": item.base_ac,
        "dex_cap": item.dex_cap, "ac_bonus": item.ac_bonus, "shield_bonus": item.shield_bonus,
        "attack_ability": item.attack_ability, "alternate_modes": item.alternate_modes,
        "reach": item.reach, "range_normal": item.range_normal, "range_long": item.range_long,
        "critical_dice": item.critical_dice, "utility_uses": list(item.utility_uses),
        "damage_dice": item.damage_dice, "damage_modifier": item.damage_modifier,
        "density": item.density, "temporary": item.temporary, "flavor": item.flavor,
        "sprite_id": item.sprite_id, "silhouette": item.silhouette, "material": item.material,
        "item_type": item.item_type, "handedness": item.handedness, "coverage": item.coverage,
        "animation_profile": item.animation_profile,
    }


def actor_sheet(actor: Actor, *, selector: str, kind: str, profile: dict | None = None) -> dict:
    armor = [{"item": item.display_name, "base_ac": item.base_ac} for item in actor.equipment if item.base_ac]
    attacks = [
        {"item": item.display_name, "base_damage": item.base_damage,
         "attack_bonus": item.attack_bonus, "density": item.density}
        for item in actor.equipment if item.slot == "hand"
    ]
    out = {
        "selector": selector, "kind": kind, "editable": kind == "custom",
        "name": actor.name, "band": actor.band.name, "controller": actor.controller,
        "sprite_id": actor.sprite_id,
        "stats": {
            "abilities": {a: {"score": actor.ability_score(a), "modifier": actor.ability_modifier(a)} for a in DND_ABILITIES},
            "hp": actor.hp, "max_hp": actor.max_hp, "armor_class": actor.armor_class,
            "initiative_bonus": actor.initiative_bonus, "speed": actor.speed,
            "proficiency_bonus": actor.proficiency_bonus, "skills": dict(sorted(actor.skill_bonuses.items())),
        },
        "resources": dict(actor.resources), "statuses": dict(actor.statuses),
        "features": list(actor.features),
        "equipment": [public_item(item) for item in actor.equipment],
        "stacking": {
            "armor_class": {"profile_total": actor.armor_class, "equipment_components": armor,
                            "formula": actor.armor_profile(),
                            "rule": "profile_total is authoritative; generic formula is explanatory only and is not added again"},
            "attacks": attacks,
            "active_effects": [effect.name for effect in actor.active_effects()],
        },
        "provenance": {
            "owner_file": actor.provenance.owner_file,
            "snapshot_version": actor.provenance.snapshot_version,
            "verified": actor.provenance.verified,
            "fidelity": actor.provenance.fidelity,
            "deferred": list(actor.provenance.deferred),
            "read_only": kind == "divine_mythos",
        },
    }
    if profile:
        out["build_rules"] = profile.get("build_rules", {})
        keys = ("race", "race_id", "gender", "sprite_id", "appearance", "character_class", "class_id", "specialization", "level", "hsr_rank")
        out["identity"] = {k: profile[k] for k in keys if k in profile}
        out["appearance"] = copy.deepcopy(profile.get("appearance", {}))
        out["known_spells"] = list(profile.get("known_spells", []))
        out["interaction_tags"] = list(profile.get("interaction_tags", []))
        out["origin_item"] = copy.deepcopy(profile.get("origin_item"))
        out["background"] = copy.deepcopy(profile.get("background", {}))
        out["heirloom_item"] = copy.deepcopy(profile.get("heirloom_item"))
        out["creation_receipt"] = copy.deepcopy(profile.get("creation_receipt", {}))
    return out


class ProfileService:
    def __init__(self, root: Path | str, snapshot_path: Path | str | None = None):
        self.root = Path(root)
        self.snapshot_path = Path(snapshot_path) if snapshot_path else None

    def _path(self, profile_id: str) -> Path:
        if not isinstance(profile_id, str) or not _ID.fullmatch(profile_id):
            raise ProfileError("profile_id must be non-empty and contain only letters, digits, _ or -")
        path = assert_safe_write_path(self.root / f"{profile_id}.json")
        if path.parent != self.root.resolve():
            raise ProfileError("profile path escapes the profile root")
        return path

    def _normalize(self, profile_id: str, data: object) -> dict:
        if not isinstance(data, dict):
            raise ProfileError("profile must be an object")
        allowed = {"name", "race", "race_id", "gender", "sprite_id", "character_class", "class_id", "specialization", "ability_scores", "max_hp", "armor_class", "initiative_bonus", "speed", "proficiency_bonus", "skill_bonuses", "equipment", "level", "hsr_rank", "resources", "build_rules", "features", "interaction_tags", "known_spells", "origin_item", "background", "heirloom_item", "creation_receipt", "appearance"}
        if set(data) - allowed:
            raise ProfileError(f"unsupported profile fields: {sorted(set(data) - allowed)}")
        abilities = data.get("ability_scores", {})
        if not isinstance(abilities, dict) or set(abilities) != set(DND_ABILITIES):
            raise ProfileError(f"ability_scores must contain exactly {list(DND_ABILITIES)}")
        skills = data.get("skill_bonuses", {})
        if not isinstance(skills, dict) or not all(isinstance(k, str) and k for k in skills):
            raise ProfileError("skill_bonuses must be an object with named keys")
        equipment = data.get("equipment", [])
        if not isinstance(equipment, list):
            raise ProfileError("equipment must be a list")
        resources = data.get("resources", {})
        if not isinstance(resources, dict) or not all(isinstance(k, str) and k.strip() for k in resources):
            raise ProfileError("resources must have non-empty named keys")
        if "build_rules" in data and not isinstance(data["build_rules"], dict):
            raise ProfileError("build_rules must be an object")
        background = data.get("background", {"id": "legacy", "name": "Legacy", "ability": None,
                                              "starting_gold": 10, "gear": []})
        if not isinstance(background, dict):
            raise ProfileError("background must be an object")
        for field in ("features", "interaction_tags", "known_spells"):
            value = data.get(field, [])
            if not isinstance(value, list) or any(not isinstance(row, str) or not row.strip() for row in value):
                raise ProfileError(f"{field} must be a list of non-empty strings")
        for field in ("origin_item", "heirloom_item", "creation_receipt"):
            if not isinstance(data.get(field, {}), dict):
                raise ProfileError(f"{field} must be an object")
        rules = copy.deepcopy(data.get("build_rules", {}))
        rules.setdefault("starting_gold", _integer(background.get("starting_gold", 10), "background starting_gold", 0, 10000))
        rules.setdefault("starting_gold_source", "custom_background" if background.get("id") != "legacy" else "legacy_default")
        race_id = str(data.get("race_id", str(data.get("race", "")).lower().replace(" ", "-")));
        raw_gender = str(data.get("gender", "other")).strip().lower()
        gender = {"feminine": "female", "masculine": "male"}.get(raw_gender, raw_gender)
        if gender not in {"male", "female", "other"}:
            raise ProfileError("gender must be male, female, or other")
        sprite_id = data.get("sprite_id") or presentation_sprite_id(race_id, gender)
        if not isinstance(sprite_id, str) or not re.fullmatch(r"[a-z0-9-]+", sprite_id):
            raise ProfileError("sprite_id must be a lowercase presentation identifier")
        return {
            "build_rules": rules,
            "level": _integer(data.get("level", 2), "level", 1, 20),
            "hsr_rank": _integer(data.get("hsr_rank", 1), "hsr_rank", 1, 10),
            "resources": {k: _integer(v, f"resource {k}", 0, 10000) for k, v in resources.items()},
            "schema_version": PROFILE_SCHEMA, "profile_id": profile_id,
            "name": _text(data.get("name"), "name"), "race": _text(data.get("race"), "race"),
            "race_id": race_id, "gender": gender, "sprite_id": sprite_id,
            "appearance": _stored_appearance(data.get("appearance"), race_id),
            "character_class": _text(data.get("character_class"), "character_class"),
            "class_id": str(data.get("class_id", str(data.get("character_class", "")).lower().replace(" ", "-"))),
            "specialization": _text(data.get("specialization"), "specialization"),
            "ability_scores": {a: _integer(abilities[a], a, 1, 30) for a in DND_ABILITIES},
            "max_hp": _integer(data.get("max_hp"), "max_hp", 1, 10000),
            "armor_class": _integer(data.get("armor_class"), "armor_class", 0, 100),
            "initiative_bonus": _integer(data.get("initiative_bonus", 0), "initiative_bonus", -100, 100),
            "speed": _integer(data.get("speed", 30), "speed", 0, 1000),
            "proficiency_bonus": _integer(data.get("proficiency_bonus", 2), "proficiency_bonus", 0, 20),
            "skill_bonuses": {k: _integer(v, f"skill {k}", -100, 100) for k, v in skills.items()},
            "equipment": [_item_data(_item(row)) for row in equipment],
            "features": list(data.get("features", [])),
            "interaction_tags": list(data.get("interaction_tags", [])),
            "known_spells": list(data.get("known_spells", [])),
            "origin_item": copy.deepcopy(data.get("origin_item", {})),
            "background": copy.deepcopy(background),
            "heirloom_item": copy.deepcopy(data.get("heirloom_item", {})),
            "creation_receipt": copy.deepcopy(data.get("creation_receipt", {})),
        }

    # Creation seeds are handed out as zero-padded build numbers (00001, 00002...).
    # The counter lives beside, not inside, the profile root so profile listings
    # never see it.  Peeking is free; only a confirmed build advances it.
    SEED_WIDTH = 5

    def _seed_counter_path(self) -> Path:
        return self.root.parent / "creation_seed_counter.json"

    def _seed_counter(self) -> int:
        try:
            value = json.loads(self._seed_counter_path().read_text(encoding="utf-8")).get("next", 1)
            return value if isinstance(value, int) and not isinstance(value, bool) and value >= 1 else 1
        except (OSError, UnicodeError, ValueError, AttributeError):
            return 1

    def peek_creation_seed(self) -> dict:
        number = self._seed_counter()
        while (self.root / f"web-{number:0{self.SEED_WIDTH}d}.json").exists():
            number += 1
        return {"creation_seed": f"{number:0{self.SEED_WIDTH}d}", "number": number}

    def allocate_creation_seed(self) -> dict:
        """Reserve a fresh numbered seed when a new creation session starts."""
        seed = self.peek_creation_seed()
        number = seed["number"]
        path = assert_safe_write_path(self._seed_counter_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(path, {"schema": "hollow-star-creation-seed-counter-1",
                           "next": number + 1, "last_allocated": seed["creation_seed"]})
        return {"creation_seed": seed["creation_seed"], "number": number,
                "next": number + 1}

    def commit_creation_seed(self, seed: object) -> dict | None:
        """Advance the counter past a confirmed numeric seed; hand-typed seeds are left alone."""
        if not isinstance(seed, str) or len(seed) != self.SEED_WIDTH or not seed.isdigit():
            return None
        number = int(seed)
        if number < self._seed_counter():
            return None
        path = assert_safe_write_path(self._seed_counter_path())
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(path, {"schema": "hollow-star-creation-seed-counter-1", "next": number + 1,
                           "last_committed": seed})
        return {"committed": seed, "next": number + 1}

    def save(self, profile_id: str, data: object, *, replace: bool) -> dict:
        path = self._path(profile_id)
        if path.exists() != replace:
            raise ProfileError(f"profile {'does not exist' if replace else 'already exists'}: {profile_id}")
        normalized = self._normalize(profile_id, data)
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(path, normalized)
        return self.inspect(profile_id)

    def save_confirmed_build(self, profile_id: str, data: object) -> tuple[dict, bool]:
        """Save a build once while allowing an identical interrupted retry."""
        path = self._path(profile_id)
        normalized = self._normalize(profile_id, data)
        if path.exists():
            existing = self._load(profile_id)
            if existing != normalized:
                raise ProfileError(f"profile already exists: {profile_id}")
            return self.inspect(profile_id), False
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_json(path, normalized)
        return self.inspect(profile_id), True

    def _load(self, profile_id: str) -> dict:
        path = self._path(profile_id)
        if not path.exists():
            raise ProfileError(f"profile does not exist: {profile_id}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProfileError(f"invalid profile: {profile_id}") from exc
        if not isinstance(raw, dict) or raw.get("schema_version") not in {PROFILE_SCHEMA_V1, PROFILE_SCHEMA_V2, PROFILE_SCHEMA} or raw.get("profile_id") != profile_id:
            raise ProfileError(f"profile contract mismatch: {profile_id}")
        body = {k: v for k, v in raw.items() if k not in {"schema_version", "profile_id"}}
        return self._normalize(profile_id, body)

    def actor(self, profile_id: str) -> Actor:
        data = self._load(profile_id)
        return Actor(
            name=data["name"], band=Band.MORTAL, controller="player",
            sprite_id=data.get("sprite_id") or presentation_sprite_id(data["race_id"], data.get("gender", "other")),
            max_hp=data["max_hp"], hp=data["max_hp"], armor_class=data["armor_class"],
            initiative_bonus=data["initiative_bonus"], speed=data["speed"],
            ability_scores=dict(data["ability_scores"]), proficiency_bonus=data["proficiency_bonus"],
            resources=dict(data["resources"]),
            skill_bonuses=dict(data["skill_bonuses"]), equipment=[_item(row) for row in data["equipment"]],
            features=list(data.get("features", [])),
            provenance=Provenance(owner_file=f".local/reliquary_profiles/{profile_id}.json",
                                  snapshot_version=PROFILE_SCHEMA, verified=False, fidelity="custom",
                                  note="Player-authored local profile; not Divine Mythos canon."),
        )

    def inspect(self, profile_id: str) -> dict:
        data = self._load(profile_id)
        return actor_sheet(self.actor(profile_id), selector=f"custom:{profile_id}", kind="custom", profile=data)

    def list(self) -> list[dict]:
        if not self.root.exists():
            return []
        return [self.inspect(path.stem) for path in sorted(self.root.glob("*.json"))]

    def roster(self) -> list[dict]:
        custom = self.list()
        imported, _ = import_party(self.snapshot_path)
        divine = [actor_sheet(actor, selector=f"divine:{name}", kind="divine_mythos") for name, actor in sorted(imported.items())]
        from hollowstar.loader import load_roster
        stock = load_roster()
        playable = [actor_sheet(actor, selector=f"hsr:{name}", kind="hsr_npc")
                    for name, actor in sorted(stock.items())
                    if actor.controller == "player" and name not in {"Doran", "Wren"}]
        return custom + divine + playable
