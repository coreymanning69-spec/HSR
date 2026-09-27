"""Shared spatial entity/hitbox model for real-time arcade encounters.

Pure data and pure resolution functions only: no rendering, no game loop,
no server I/O. `arcade.py` drives this once per tick; damage application is
handed off to `resolution.py`/`tactical.damage` rather than duplicated here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from hollowstar.authored_mechanics import is_doran, is_wren


class MovementMode(Enum):
    RUN = "run"
    JUMP = "jump"
    CLIMB = "climb"
    FLY = "fly"
    FALL = "fall"


@dataclass
class SpatialEntity:
    entity_id: str
    actor_ref: str
    position: tuple[int, int, int]
    facing: int = 1
    movement_mode: MovementMode = MovementMode.RUN
    hurtbox: tuple[int, int, int, int] = (0, 0, 5, 10)
    velocity: tuple[int, int] = (0, 0)
    # Vertical (jump/fall) speed, separate from the horizontal `velocity`
    # pair above. Arcade's tick() integrates gravity against this each frame;
    # spatial.py stays pure data, it never advances it itself.
    velocity_z: int = 0
    grounded: bool = True
    status_tags: dict = field(default_factory=dict)
    # The collision layer is presentation-independent. Arcade uses it to
    # reject friendly fire before handing a resolved overlap to tactics.
    team: str = ""


@dataclass
class Hitbox:
    owner_id: str
    shape: tuple[int, int, int, int]
    active_from: int
    active_to: int
    damage_type: str
    damage_expression: str
    bypass_resistance: bool = False


def movement_capabilities(identity):
    """Movement modes available to an identity. Wings-manifested is checked
    separately by the caller before FLY is offered to Wren."""
    if is_doran(identity):
        return {MovementMode.RUN, MovementMode.JUMP, MovementMode.CLIMB}
    if is_wren(identity):
        return {MovementMode.RUN, MovementMode.JUMP, MovementMode.FLY}
    return {MovementMode.RUN, MovementMode.JUMP}


def _overlaps(a, box_a, b, box_b):
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b
    apx, apy, _ = a.position
    bpx, bpy, _ = b.position
    return (apx + ax < bpx + bx + bw and apx + ax + aw > bpx + bx
            and apy + ay < bpy + by + bh and apy + ay + ah > bpy + by)


def resolve_hitbox_overlap(entities, hitboxes, frame):
    """Return hit events: [{"hitbox_owner", "target_id", "hitbox": Hitbox}, ...].

    `entities` is a dict of entity_id -> SpatialEntity. Friendly fire and
    self-hits are excluded; frame gating uses each hitbox's active window.
    """
    by_id = {e.entity_id: e for e in entities.values()} if isinstance(entities, dict) else {e.entity_id: e for e in entities}
    events = []
    for hitbox in hitboxes:
        if not (hitbox.active_from <= frame <= hitbox.active_to):
            continue
        owner = by_id.get(hitbox.owner_id)
        if owner is None:
            continue
        for target in by_id.values():
            if target.entity_id == hitbox.owner_id:
                continue
            owner_team = getattr(owner, "team", "") or owner.entity_id[:1]
            target_team = getattr(target, "team", "") or target.entity_id[:1]
            if owner_team == target_team:
                continue
            if _overlaps(owner, hitbox.shape, target, target.hurtbox):
                events.append({"hitbox_owner": hitbox.owner_id, "target_id": target.entity_id, "hitbox": hitbox})
    return events
