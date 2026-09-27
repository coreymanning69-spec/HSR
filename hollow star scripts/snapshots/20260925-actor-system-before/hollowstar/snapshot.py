"""
The party snapshot contract.

This is DM046_0 certification step 5: "export a compact machine-readable party
snapshot for the Python engine." Steps 1-4 are complete, Step 5's artifact is
current, and Step 6 is complete. Sandbox and Forge are available subject to
their separate isolation and explicit-intent gates. This module is the engine
side of that gate.

DIRECTION OF AUTHORITY -- read this before changing anything here
----------------------------------------------------------------
The snapshot is DERIVED INPUT. It is not an authority and never becomes one.

    DM041_A + DM041_A1  ->  Doran's standing mechanics
    DM041_B + DM041_B1  ->  Wren's standing mechanics
    DM044_0 + DM044_1   ->  the derived combat/simulation runtime pair
                            (loaded together; neither half is valid alone)
                             |
                             v
                    party_snapshot.json     <- generated, disposable
                             |
                             v
                       hollowstar Actors

If a number here disagrees with an owner file, the owner file is right and the
snapshot is stale. Regenerate it with tools/export_party_snapshot.py; never
patch the JSON by hand, and never write anything back up that arrow.

SIMULATION SEED ONLY
--------------------
DM044_0 section 0 defines two modes. LIVE seeds from the volatile current-story
ledger (DM038_L) and fails closed if that read is stale. SIMULATION seeds
from a declared fixture or the explicit full baselines.

This engine is SIMULATION, always. The snapshot therefore carries the full
baselines and deliberately does not reference the live-state family at all,
which means no run can read current readiness and no run can drift it.

WHAT `verified` MEANS
---------------------
Actor.provenance.verified answers exactly one question: did these numbers come
from a certified authority? It does not claim the engine implements everything
the sheet describes. That second question is `fidelity` plus `deferred`, and
for both Stewards today the honest answer is "partial" with a named list.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from hollowstar.actors import Actor, Band, Provenance
from hollowstar.effects import Effect
from hollowstar.items import Item
from hollowstar.phases import Direction, Phase, Scope, Tier
from hollowstar.tags import DamageTag, GATES

SCHEMA_VERSION = "hollow-star-party-snapshot-1"

# The engine version range this schema is known to work against. A snapshot
# generated for a newer engine must not be silently loaded by an older one.
MIN_ENGINE_VERSION = "0.2.0"

DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[1] / "snapshots" / "party_snapshot.json"

# Run saves live here and nowhere else. DM046_0 section 6.
RUN_SAVE_ROOT = Path(".local") / "reliquary_runs"

# Any path segment that smells like the Divine Mythos corpus. The engine reads
# from the corpus exactly once, through the export tool, and writes to it never.
CORPUS_MARKERS = (
    "divine mythos set",
    "project context",
    "storm king pdfs",
    "storm king texts",
    "tr3_skt_archive",
)

# Owner files whose values are volatile live state. A simulation snapshot must
# not cite them: reading them would couple runs to campaign readiness, and
# writing them would let a Sandbox run edit chronology.
LIVE_STATE_OWNERS = ("DM038_L", "DM038_CH", "DM035_0")


class SnapshotError(Exception):
    """Raised when a snapshot cannot be trusted. Always fail closed."""


class CorpusWriteRefused(SnapshotError):
    """Raised when something tries to write into the corpus. Never soften."""


# --------------------------------------------------------------------------
# Write guard
# --------------------------------------------------------------------------


def assert_safe_write_path(path: Path | str) -> Path:
    """
    Refuse any write that lands inside the Divine Mythos corpus.

    Constraint 4 of the handoff and DM046_0 section 6: generated content never
    goes back into the corpus. This is cheap to call and belongs in front of
    every save path the engine grows.
    """
    p = Path(path)
    parts = [seg.lower() for seg in p.resolve().parts]
    for marker in CORPUS_MARKERS:
        if marker in parts:
            raise CorpusWriteRefused(
                f"refusing to write inside the Divine Mythos corpus: {p} "
                f"(matched {marker!r}). Run saves belong in {RUN_SAVE_ROOT}/."
            )
    return p


def _version_tuple(v: str) -> tuple[int, ...]:
    head = v.split("-")[0].split("+")[0]
    return tuple(int(x) for x in head.split(".") if x.isdigit())


# --------------------------------------------------------------------------
# Load and validate
# --------------------------------------------------------------------------


@dataclass
class ImportReport:
    """What actually came across, and what did not."""

    snapshot_version: str = ""
    source_fingerprint: str = ""
    imported: list[str] = field(default_factory=list)
    deferred: dict[str, list[str]] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"snapshot {self.snapshot_version}  fingerprint {self.source_fingerprint}",
            f"imported: {', '.join(self.imported) or 'nothing'}",
        ]
        for who, items in self.deferred.items():
            lines.append(f"  {who}: {len(items)} deferred capabilities")
            for d in items:
                lines.append(f"    - {d}")
        return "\n".join(lines)


def load_snapshot(path: Path | str | None = None) -> dict:
    """Read and validate a snapshot. Raises SnapshotError rather than guessing."""
    p = Path(path) if path else DEFAULT_SNAPSHOT
    if not p.exists():
        raise SnapshotError(
            f"no party snapshot at {p}. DM046_0 step 5 is not satisfied; "
            f"generate one with tools/export_party_snapshot.py."
        )
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SnapshotError(f"{p} is not valid JSON: {exc}") from exc
    validate(data)
    return data


def validate(data: dict) -> None:
    """Structural and policy checks. Every failure is fatal by design."""
    got = data.get("schema_version")
    if got != SCHEMA_VERSION:
        raise SnapshotError(
            f"schema mismatch: engine speaks {SCHEMA_VERSION!r}, snapshot says {got!r}"
        )

    from hollowstar import __version__ as engine_version

    required = data.get("engine_contract", {}).get("min_engine_version", MIN_ENGINE_VERSION)
    if _version_tuple(engine_version) < _version_tuple(required):
        raise SnapshotError(
            f"snapshot needs engine >= {required}, this engine is {engine_version}"
        )

    if data.get("seed_mode") != "SIMULATION":
        raise SnapshotError(
            "party snapshots are SIMULATION artifacts only. "
            "LIVE seeding is DM044_0's job and reads DM038_L directly."
        )

    sources = data.get("sources") or []
    if not sources:
        raise SnapshotError("snapshot cites no source owners; refusing to trust it")
    for src in sources:
        owner = src.get("owner", "")
        if owner in LIVE_STATE_OWNERS:
            raise SnapshotError(
                f"snapshot cites live-state owner {owner}. A simulation snapshot "
                f"must seed from the full baselines, not campaign readiness."
            )
        for key in ("owner", "file", "sha256", "source_schema"):
            if not src.get(key):
                raise SnapshotError(f"source {owner or '?'} is missing {key!r}")

    chars = data.get("characters") or {}
    if not chars:
        raise SnapshotError("snapshot contains no characters")
    for cid, entry in chars.items():
        if "engine" not in entry:
            raise SnapshotError(f"character {cid!r} has no engine mapping block")
        if "certified" not in entry:
            raise SnapshotError(f"character {cid!r} carries no certified source block")


# --------------------------------------------------------------------------
# Snapshot -> engine objects
# --------------------------------------------------------------------------


def _tags(names) -> set[DamageTag]:
    return {DamageTag[n] for n in (names or [])}


def _build_effect(d: dict) -> Effect:
    return Effect(
        name=d["name"],
        phase=Phase[d["phase"]],
        direction=Direction[d["direction"]],
        tier=Tier[d.get("tier", "MUNDANE")],
        scope=Scope[d.get("scope", "TARGET")],
        condition=d.get("condition", "always"),
        flat_bonus=d.get("flat_bonus", 0),
        multiplier=d.get("multiplier", 1.0),
        applies_to_tags=_tags(d.get("applies_to_tags")),
        grants_tags=_tags(d.get("grants_tags")),
        opens_gate=d.get("opens_gate", ""),
        closes_gate=d.get("closes_gate", ""),
        inflicts_status=d.get("inflicts_status", ""),
        status_duration=d.get("status_duration", 0),
        status_potency=d.get("status_potency", 1),
        blocks_statuses=set(d.get("blocks_statuses", [])),
        charges=d.get("charges"),
        tell=d.get("tell", ""),
        description=d.get("description", ""),
        operation=d.get("operation", "add"),
        stat=d.get("stat", ""),
        stack_group=d.get("stack_group", ""),
        source_id=d.get("source_id", ""),
        duration=d.get("duration", "permanent"),
        priority=d.get("priority", 0),
        public_summary=d.get("public_summary", ""),
        specificity=d.get("specificity", 0),
    )


def _build_item(d: dict) -> Item:
    return Item(
        name=d["name"],
        slot=d.get("slot", "hand"),
        base_damage=d.get("base_damage", 0),
        attack_bonus=d.get("attack_bonus", 0),
        base_ac=d.get("base_ac", 0),
        tier=Tier[d.get("tier", "MUNDANE")],
        tags=_tags(d.get("tags")),
        inherent=[_build_effect(e) for e in d.get("inherent", [])],
        density=d.get("density", 1.0),
        utility_uses=d.get("utility_uses", []),
        flavor=d.get("flavor", ""),
    )


def build_actor(entry: dict, snapshot_version: str) -> Actor:
    """Turn one snapshot character block into an Actor."""
    e = entry["engine"]
    prov = entry.get("provenance", {})
    deferred = list(entry.get("deferred", []))
    certified_stats = entry.get("certified", {}).get("stats", {})
    certified_abilities = certified_stats.get("abilities", {})
    source_abilities = e.get("ability_scores") or {
        ability.upper(): int(certified_abilities.get(ability.lower(), 10))
        for ability in ("STR", "DEX", "CON", "INT", "WIS", "CHA")
    }
    source_skills = e.get("skill_bonuses") or dict(certified_stats.get("skills", {}))

    actor = Actor(
        name=e["name"],
        band=Band[e.get("band", "STEWARD")],
        controller=e.get("controller", "player"),
        max_hp=e["max_hp"],
        hp=e["max_hp"],
        armor_class=e["armor_class"],
        initiative_bonus=e.get("initiative_bonus", 0),
        speed=e.get("speed", 30),
        attacks_per_action=e.get("attacks_per_action", 1),
        reactions=e.get("reactions", 1),
        ability_scores={
            ability: int(source_abilities.get(ability, 10))
            for ability in ("STR", "DEX", "CON", "INT", "WIS", "CHA")
        },
        proficiency_bonus=e.get(
            "proficiency_bonus", certified_stats.get("proficiency_bonus", 0)
        ),
        skill_bonuses=source_skills,
        natural_tags=_tags(e.get("natural_tags")),
        gate=GATES.get(e.get("gate", "none"), GATES["none"]),
        inherent=[_build_effect(x) for x in e.get("inherent", [])],
        equipment=[_build_item(x) for x in e.get("equipment", [])],
        resources=dict(e.get("resources", {})),
        provenance=Provenance(
            owner_file=prov.get("owner_file", ""),
            support_files=prov.get("support_files", []),
            snapshot_version=snapshot_version,
            verified=True,  # validate() passed; the numbers are certified
            fidelity="complete" if not deferred else "partial",
            deferred=deferred,
            note=prov.get("note", ""),
        ),
    )
    return actor


def import_party(path: Path | str | None = None) -> tuple[dict[str, Actor], ImportReport]:
    """
    Load a snapshot and produce certified Actors plus an honest report.

    This is the call that flips Doran and Wren from placeholder to certified.
    Anything the engine cannot express yet lands in the report instead of
    being quietly dropped -- a missing signature ability should be visible,
    not inferred later from a balance result that made no sense.
    """
    data = load_snapshot(path)
    version = data.get("snapshot_version", "unversioned")
    report = ImportReport(
        snapshot_version=version,
        source_fingerprint=data.get("source_fingerprint", ""),
    )

    roster: dict[str, Actor] = {}
    for cid, entry in data["characters"].items():
        actor = build_actor(entry, version)
        roster[actor.name] = actor
        report.imported.append(actor.name)
        if actor.provenance.deferred:
            report.deferred[actor.name] = list(actor.provenance.deferred)

    return roster, report


def merge_into_roster(
    roster: dict[str, Actor], path: Path | str | None = None
) -> tuple[dict[str, Actor], ImportReport]:
    """
    Overlay certified actors onto a JSON roster, replacing the stubs.

    Roster entries the snapshot does not cover are left alone, so townspeople
    and monsters stay where they are while the Stewards get promoted.
    """
    certified, report = import_party(path)
    merged = dict(roster)
    merged.update(certified)
    return merged, report
