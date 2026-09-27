"""Server-authoritative side-scrolling encounters.

The browser may request movement and an attack intent, but it never submits
damage, hit points, wave completion, or reward state. ``tick`` is the only
frame transition; collision math stays in :mod:`hollowstar.spatial` and
damage stays in :mod:`hollowstar.tactical`.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

from hollowstar import spatial
from hollowstar import tactical as t
from hollowstar.authored_mechanics import is_wren
from hollowstar.spatial import MovementMode


class ArcadeError(ValueError):
    pass


@dataclass
class Obstacle:
    obstacle_id: str
    kind: str
    position: tuple[int, int, int]
    required_mode: set = field(default_factory=set)
    width: int = 5
    height: int = 40


@dataclass
class WaveSpec:
    wave_id: int
    enemy_keys: list


WORLD_MIN = 0
WORLD_MAX = 120
MAX_DELTA = 120

# Vertical jump-arc physics. Entirely additive to the x/y model above: `z`
# (position[2]) was always 0 before this, so gravity only ever moves an
# entity through space no earlier tick/test depended on.
GRAVITY = 3
JUMP_IMPULSE = 16

# Dodge/roll: a short dash plus a brief invulnerability window, gated by a
# cooldown so it can't be spammed every tick.
DODGE_DISTANCE = 20
DODGE_IFRAMES = 6
DODGE_COOLDOWN = 15

# Combo: consecutive attacks inside this many frames of each other escalate
# through the tiers below before the chain resets.
COMBO_WINDOW_FRAMES = 10
COMBO_MAX_TIER = 3
COMBO_TIER_DAMAGE_BONUS = 3

# Block halves damage from an attacker in front of the blocking actor's
# facing; it does nothing against a flank or rear hit.
BLOCK_REDUCTION_FRONT = 0.5

# Ranged/projectile attacks: a fixed speed and lifetime, independent of the
# per-tick melee hitbox window since a projectile must persist across ticks.
RANGED_SPEED = 10
RANGED_LIFETIME_FRAMES = 40
PROJECTILE_SHAPE = (0, -2, 6, 6)

# A minimal automatic melee AI so arcade combat is actually bidirectional:
# without this, nothing ever attacks a party member and block/dodge would
# have nothing to defend against. No movement AI, no ranged enemies — just
# an in-range swing on a cooldown.
ENEMY_ATTACK_RANGE = 40
ENEMY_ATTACK_COOLDOWN = 20

# Enemy size definitions: hitbox multipliers and speed.  Applied when an
# enemy entity is first built so the hurtbox and speed are baked in.
ENEMY_SIZES = {
    "small":  {"w_mult": 0.5,  "h_mult": 0.75, "speed": 3, "hp_mult": 0.75, "dmg_mult": 0.8},
    "medium": {"w_mult": 1.0,  "h_mult": 1.0,  "speed": 4, "hp_mult": 1.0,  "dmg_mult": 1.0},
    "large":  {"w_mult": 2.0,  "h_mult": 1.5,  "speed": 3, "hp_mult": 2.0,  "dmg_mult": 1.5},
    "boss":   {"w_mult": 2.5,  "h_mult": 2.0,  "speed": 2, "hp_mult": 4.0,  "dmg_mult": 2.0},
}

# Recognised enemy behaviour tags.  Any spec tactic not in this set falls
# back to "chase" at movement time.
ENEMY_TACTICS = {"patrol", "chase", "ranged", "ambush", "boss"}


def _entities(run):
    return run.context["arcade"]["entities"]


def _entity(run, key):
    entities = _entities(run)
    if key not in entities:
        raise ArcadeError(f"unknown arcade entity: {key}")
    return entities[key]


def _strict_int(value, label):
    if type(value) is not int:
        raise ArcadeError(f"{label} must be an integer")
    return value


def _spatial_entity(record):
    return spatial.SpatialEntity(
        entity_id=record["entity_id"],
        actor_ref=record["actor_ref"],
        position=tuple(record["position"]),
        facing=record.get("facing", 1),
        movement_mode=MovementMode(record.get("movement_mode", MovementMode.RUN.value)),
        hurtbox=tuple(record.get("hurtbox", (0, 0, 5, 10))),
        velocity=tuple(record.get("velocity", (0, 0))),
        velocity_z=int(record.get("velocity_z", 0)),
        grounded=bool(record.get("grounded", True)),
        status_tags=copy.deepcopy(record.get("status_tags", {})),
        team=record.get("team", ""),
    )


def _write_spatial(record, entity):
    record.update({
        "position": list(entity.position),
        "facing": entity.facing,
        "movement_mode": entity.movement_mode.value,
        "hurtbox": list(entity.hurtbox),
        "velocity": list(entity.velocity),
        "velocity_z": entity.velocity_z,
        "grounded": entity.grounded,
        "status_tags": copy.deepcopy(entity.status_tags),
        "team": entity.team,
    })


def _active_enemy_keys(arcade):
    index = arcade.get("wave_index", 0)
    waves = arcade.get("waves", [])
    if arcade.get("complete") or index >= len(waves):
        return set()
    return set(waves[index].get("enemy_keys", []))


def _active_keys(run):
    active_enemies = _active_enemy_keys(run.context["arcade"])
    return {key for key in _entities(run) if key.startswith("p")} | active_enemies


def can_bypass(identity, wings_manifested, mode):
    return mode in spatial.movement_capabilities(identity) and (
        mode != MovementMode.FLY or wings_manifested
    )


def _waves_from_row(row, enemy_keys):
    raw = row.get("waves")
    if raw is None:
        return [WaveSpec(wave_id=0, enemy_keys=list(enemy_keys))]
    if not isinstance(raw, list) or not raw:
        raise ArcadeError("arcade waves must be a non-empty list")

    known = set(enemy_keys)
    assigned = set()
    waves = []
    for index, spec in enumerate(raw):
        if not isinstance(spec, dict):
            raise ArcadeError("each arcade wave must be an object")
        selected = spec.get("enemy_keys")
        if selected is None and "enemy_indices" in spec:
            indices = spec.get("enemy_indices")
            if not isinstance(indices, list) or any(type(value) is not int for value in indices):
                raise ArcadeError("wave enemy_indices must be integer indexes")
            selected = [enemy_keys[value] for value in indices if 0 <= value < len(enemy_keys)]
            if len(selected) != len(indices):
                raise ArcadeError("wave enemy_indices contains an unknown enemy")
        if selected is None:
            count = spec.get("enemy_count", spec.get("count"))
            if count is None:
                selected = list(enemy_keys) if index == 0 else []
            else:
                _strict_int(count, "wave enemy_count")
                if count < 1 or count > len(enemy_keys):
                    raise ArcadeError("wave enemy_count is outside the available enemy range")
                selected = [key for key in enemy_keys if key not in assigned][:count]
        if not isinstance(selected, list) or not selected:
            raise ArcadeError("each arcade wave must contain at least one enemy")
        if any(key not in known for key in selected):
            raise ArcadeError("wave references an unknown enemy")
        if assigned.intersection(selected):
            raise ArcadeError("an arcade enemy may belong to only one wave")
        assigned.update(selected)
        waves.append(WaveSpec(wave_id=index, enemy_keys=list(selected)))
    if assigned != known:
        raise ArcadeError("arcade waves must account for every spawned enemy")
    return waves


def enter_from_room(run, row):
    """Build the public arcade projection from the active room and combat."""
    from hollowstar import room_state

    geometry = room_state.combat_geometry(row)
    combat_state = run.context.get("combat")
    if not combat_state or combat_state.get("complete"):
        raise ArcadeError("arcade mode requires active combat")
    entities = {}
    for index, key in enumerate(t.actors(run)):
        entities[key] = {
            "entity_id": key,
            "actor_ref": key,
            "team": "party" if key.startswith("p") else "opposition",
            "position": [10 if key.startswith("p") else 90, 10 + 10 * index, 0],
            "facing": 1 if key.startswith("p") else -1,
            "movement_mode": MovementMode.RUN.value,
            "hurtbox": [0, 0, 5, 10],
            "velocity": [0, 0],
            "velocity_z": 0,
            "grounded": True,
            "status_tags": {},
        }

    obstacles = []
    for structure in geometry["structures"]:
        required = structure.get("required_mode", [])
        if not required:
            continue
        if not isinstance(required, list):
            raise ArcadeError("structure required_mode must be a list")
        try:
            required_modes = sorted({MovementMode(mode).value for mode in required})
        except ValueError as exc:
            raise ArcadeError("structure required_mode contains an unknown movement mode") from exc
        width = structure.get("width", 5)
        height = structure.get("height", 40)
        _strict_int(width, "structure width")
        _strict_int(height, "structure height")
        if width < 1 or height < 1:
            raise ArcadeError("structure dimensions must be positive")
        obstacles.append({
            "id": structure["object_id"],
            "kind": structure.get("kind", "obstacle"),
            "position": list(structure["position"]),
            "required_mode": required_modes,
            "width": width,
            "height": height,
        })

    enemy_keys = [key for key in t.actors(run) if key.startswith("e")]
    waves = _waves_from_row(row, enemy_keys)
    run.context["arcade"] = {
        "schema": 1,
        "entities": entities,
        "obstacles": obstacles,
        "waves": [{"wave_id": wave.wave_id, "enemy_keys": list(wave.enemy_keys)} for wave in waves],
        "wave_index": 0,
        "scroll_position": 0,
        "frame": 0,
        "gate_open": False,
        "complete": False,
        "projectiles": [],
    }
    return {
        "type": "arcade_started",
        "entities": list(entities),
        "waves": len(waves),
        "evidence": {
            "room_id": f"{row['floor']}:{row['number']}",
            "obstacle_count": len(obstacles),
            "encounter_mode": "arcade",
        },
    }


def _wave_cleared(run):
    arcade = run.context["arcade"]
    index = arcade.get("wave_index", 0)
    waves = arcade.get("waves", [])
    if index >= len(waves):
        return True
    return all(not t.actor(run, key).alive for key in waves[index]["enemy_keys"])


def toggle_flight(run, key, on):
    if type(on) is not bool:
        raise ArcadeError("flight toggle must be boolean")
    actor, rules = t.actor(run, key), t.rules(run, key)
    if not is_wren(rules.get("identity")):
        raise ArcadeError("only Wren may toggle flight")
    entity = _spatial_entity(_entity(run, key))
    if on:
        if not rules.get("fly_speed"):
            raise ArcadeError("wings are not manifested; use the 'fly' action first")
        entity.movement_mode = MovementMode.FLY
        entity.grounded = False
    else:
        entity.movement_mode = MovementMode.RUN
        entity.grounded = True
    _write_spatial(_entity(run, key), entity)
    return {"type": "flight_toggled", "actor": key, "movement_mode": entity.movement_mode.value}


def set_movement_mode(run, key, mode_name):
    actor, rules = t.actor(run, key), t.rules(run, key)
    if not actor.alive:
        raise ArcadeError("an unconscious actor cannot change movement mode")
    try:
        mode = MovementMode(mode_name)
    except ValueError as exc:
        raise ArcadeError(f"unknown movement mode: {mode_name}") from exc
    wings = bool(rules.get("fly_speed"))
    if not can_bypass(rules.get("identity"), wings, mode):
        raise ArcadeError(f"{rules.get('identity')} cannot use movement mode {mode_name}")
    entity = _spatial_entity(_entity(run, key))
    entity.movement_mode = mode
    entity.grounded = mode not in {MovementMode.FLY, MovementMode.JUMP}
    _write_spatial(_entity(run, key), entity)
    return {"type": "movement_mode", "actor": key, "movement_mode": mode.value}


def _blocked_by_obstacles(run, entity, destination):
    arcade = run.context["arcade"]
    ex, ey, _ = entity.position
    dx, dy, _ = destination
    entity_y, entity_width, entity_height = entity.hurtbox[1], entity.hurtbox[2], entity.hurtbox[3]
    current_x = (ex + entity.hurtbox[0], ex + entity.hurtbox[0] + entity_width)
    target_x = (dx + entity.hurtbox[0], dx + entity.hurtbox[0] + entity_width)
    current_y = (ey + entity_y, ey + entity_y + entity_height)
    target_y = (dy + entity_y, dy + entity_y + entity_height)
    sweep_x = (min(current_x[0], target_x[0]), max(current_x[1], target_x[1]))
    sweep_y = (min(current_y[0], target_y[0]), max(current_y[1], target_y[1]))
    for obstacle in arcade["obstacles"]:
        ox, oy, _ = obstacle["position"]
        obstacle_x = (ox, ox + obstacle["width"])
        obstacle_y = (oy, oy + obstacle["height"])
        overlaps = sweep_x[0] < obstacle_x[1] and sweep_x[1] > obstacle_x[0]
        overlaps &= sweep_y[0] < obstacle_y[1] and sweep_y[1] > obstacle_y[0]
        if overlaps and entity.movement_mode.value not in obstacle["required_mode"]:
            return obstacle
    return None


def _physics(state) -> dict:
    """Return effective physics constants, allowing per-room overrides.

    Callers pass ``run.context["arcade"]`` (or any dict) and receive a dict
    with the four tuneable constants.  Any key present in
    ``state["physics_overrides"]`` replaces the corresponding module default.
    """
    overrides = state.get("physics_overrides", {})
    return {
        "gravity": overrides.get("gravity", GRAVITY),
        "jump_impulse": overrides.get("jump_impulse", JUMP_IMPULSE),
        "dodge_iframes": overrides.get("dodge_iframes", DODGE_IFRAMES),
        "dodge_cooldown": overrides.get("dodge_cooldown", DODGE_COOLDOWN),
    }


def _integrate_vertical(entity, phys=None):
    """One tick of jump-arc gravity against ``entity.position[2]``.

    Pure: mutates the passed SpatialEntity in place and returns whether
    anything changed, so the caller can skip writing back an untouched
    grounded entity. FLY and CLIMB hold altitude/position on their own and
    are exempt from automatic gravity.
    """
    if phys is None:
        phys = {"gravity": GRAVITY, "jump_impulse": JUMP_IMPULSE}
    if entity.movement_mode == MovementMode.JUMP and entity.position[2] == 0 and entity.velocity_z == 0:
        entity.velocity_z = phys["jump_impulse"]
    if entity.position[2] == 0 and entity.velocity_z == 0:
        return False
    if entity.movement_mode in (MovementMode.FLY, MovementMode.CLIMB):
        return False
    velocity_z = entity.velocity_z - phys["gravity"]
    height = entity.position[2] + velocity_z
    if height <= 0:
        height, velocity_z = 0, 0
        entity.grounded = True
        entity.movement_mode = MovementMode.RUN
    else:
        entity.grounded = False
        entity.movement_mode = MovementMode.FALL if velocity_z <= 0 else MovementMode.JUMP
    entity.velocity_z = velocity_z
    entity.position = (entity.position[0], entity.position[1], height)
    return True


def _block_reduction(owner_key, target_key, entity_objects):
    """Fraction of damage a blocking target absorbs from this attacker.

    A block only helps against an attacker in front of the target's facing;
    a flank or rear hit still lands in full.
    """
    owner = entity_objects[owner_key]
    target = entity_objects[target_key]
    if not target.status_tags.get("blocking"):
        return 0.0
    attacker_in_front = (owner.position[0] - target.position[0]) * (target.facing or 1) >= 0
    return BLOCK_REDUCTION_FRONT if attacker_in_front else 0.0


def _apply_dodge(run, key, frame, dx=None, dy=None):
    record = _entity(run, key)
    entity = _spatial_entity(record)
    tags = entity.status_tags
    ready_frame = tags.get("dodge_ready_frame", 0)
    if frame < ready_frame:
        return {"type": "arcade_dodge_on_cooldown", "actor": key, "ready_frame": ready_frame}
    if dx is not None:
        dx = _strict_int(dx, "dodge dx")
    if dy is not None:
        dy = _strict_int(dy, "dodge dy")
    if not dx and not dy:
        dx, dy = entity.facing * DODGE_DISTANCE, 0
    else:
        dx, dy = dx or 0, dy or 0
        magnitude = max(abs(dx), abs(dy), 1)
        dx = round(dx / magnitude * DODGE_DISTANCE)
        dy = round(dy / magnitude * DODGE_DISTANCE)
    destination = (
        min(max(WORLD_MIN, entity.position[0] + dx), WORLD_MAX),
        min(max(WORLD_MIN, entity.position[1] + dy), WORLD_MAX),
        entity.position[2],
    )
    blocked = _blocked_by_obstacles(run, entity, destination)
    if not blocked:
        entity.position = destination
    tags["invulnerable_until_frame"] = frame + DODGE_IFRAMES
    tags["dodge_ready_frame"] = frame + DODGE_COOLDOWN
    _write_spatial(record, entity)
    return {
        "type": "arcade_dodge_blocked" if blocked else "arcade_dodge",
        "actor": key,
        "position": list(entity.position),
        "invulnerable_until_frame": tags["invulnerable_until_frame"],
    }


def _ranged_spec(run, key):
    """(damage_expression, damage_type, bypass_resistance) for a ranged shot.

    Every actor gets *some* ranged option: an equipped weapon tagged ranged
    or thrown drives the numbers when present, otherwise a modest default so
    the option is never simply unavailable.
    """
    actor, rules = t.actor(run, key), t.rules(run, key)
    identity = rules.get("identity")
    if identity == "wren":
        return "2d10", "RADIANT", False
    profile = actor.weapon_profile() or {}
    if profile.get("damage_dice") and (profile.get("ranged") or profile.get("thrown") or profile.get("range")):
        modifier = profile.get("damage_modifier", 0)
        expression = profile["damage_dice"] + (f"{modifier:+d}" if modifier else "")
        return expression, rules.get("damage_type", "PIERCING"), False
    return "1d6", "FORCE", False


def _spawn_projectile(run, key, frame):
    entity = _spatial_entity(_entity(run, key))
    expression, damage_type, bypass = _ranged_spec(run, key)
    arcade = run.context["arcade"]
    projectiles = arcade.setdefault("projectiles", [])
    sequence = arcade.get("_projectile_seq", 0) + 1
    arcade["_projectile_seq"] = sequence
    projectile = {
        "projectile_id": f"pr-{sequence}",
        "owner": key,
        "team": entity.team or key[:1],
        "position": list(entity.position),
        "velocity": [RANGED_SPEED if entity.facing >= 0 else -RANGED_SPEED, 0],
        "shape": list(PROJECTILE_SHAPE),
        "damage_type": damage_type,
        "damage_expression": expression,
        "bypass_resistance": bypass,
        "expires_frame": frame + RANGED_LIFETIME_FRAMES,
    }
    projectiles.append(projectile)
    return {"type": "arcade_ranged_spawn", "actor": key, "projectile_id": projectile["projectile_id"]}


def _aabb_overlap(position_a, box_a, position_b, box_b):
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b
    apx, apy = position_a[0], position_a[1]
    bpx, bpy = position_b[0], position_b[1]
    return (apx + ax < bpx + bx + bw and apx + ax + aw > bpx + bx
            and apy + ay < bpy + by + bh and apy + ay + ah > bpy + by)


def _advance_projectiles(run, frame, entity_objects, active_enemies):
    """Move every live projectile one tick, resolve hits, drop the rest.

    A projectile is a moving hitbox that persists across ticks (unlike a
    melee swing's single-frame Hitbox), so it keeps its own small state list
    in ``run.context["arcade"]["projectiles"]`` instead of riding through
    ``spatial.Hitbox``/``resolve_hitbox_overlap``.
    """
    arcade = run.context["arcade"]
    events = []
    remaining = []
    for projectile in arcade.get("projectiles", []):
        x, y, z = projectile["position"]
        vx, vy = projectile["velocity"]
        x, y = x + vx, y + vy
        projectile["position"] = [x, y, z]
        in_bounds = WORLD_MIN <= x <= WORLD_MAX and WORLD_MIN <= y <= WORLD_MAX
        expired = frame >= projectile["expires_frame"] or not in_bounds
        hit_target = None
        if not expired:
            shape = tuple(projectile["shape"])
            for target_key, target_entity in entity_objects.items():
                if target_key == projectile["owner"]:
                    continue
                target_team = target_entity.team or target_key[:1]
                if target_team == projectile["team"]:
                    continue
                if target_key.startswith("e") and target_key not in active_enemies:
                    continue
                if not t.actor(run, target_key).alive:
                    continue
                if target_entity.status_tags.get("invulnerable_until_frame", 0) >= frame:
                    continue
                if _aabb_overlap((x, y, z), shape, target_entity.position, target_entity.hurtbox):
                    hit_target = target_key
                    break
        if hit_target:
            reduction = _block_reduction(projectile["owner"], hit_target, entity_objects)
            hitbox = spatial.Hitbox(
                owner_id=projectile["owner"], shape=shape, active_from=frame, active_to=frame,
                damage_type=projectile["damage_type"], damage_expression=projectile["damage_expression"],
                bypass_resistance=projectile["bypass_resistance"],
            )
            events.append(spawn_hit(run, projectile["owner"], hit_target, hitbox, reduction=reduction))
            events.append({"type": "arcade_projectile_hit", "projectile_id": projectile["projectile_id"], "target": hit_target})
            continue
        if expired:
            events.append({"type": "arcade_projectile_expired", "projectile_id": projectile["projectile_id"]})
            continue
        remaining.append(projectile)
    arcade["projectiles"] = remaining
    return events


def _enemy_actions(run, frame, entity_objects, active_enemies):
    """Each active, cooled-down enemy within range swings at the nearest
    active party member. Returns hitboxes to fold into this tick's overlap
    resolution alongside any player-submitted ones."""
    arcade = run.context["arcade"]
    party = {
        key: obj for key, obj in entity_objects.items()
        if key.startswith("p") and t.actor(run, key).alive
    }
    hitboxes = []
    for key in active_enemies:
        if key not in entity_objects or not t.actor(run, key).alive:
            continue
        entity = entity_objects[key]
        record = arcade["entities"][key]
        tags = record.setdefault("status_tags", {})
        if frame < tags.get("attack_ready_frame", 0):
            continue
        in_range = [
            pkey for pkey, pobj in party.items()
            if abs(pobj.position[0] - entity.position[0]) <= ENEMY_ATTACK_RANGE
        ]
        if not in_range:
            continue
        target_key = min(in_range, key=lambda pkey: abs(party[pkey].position[0] - entity.position[0]))
        tags["attack_ready_frame"] = frame + ENEMY_ATTACK_COOLDOWN
        entity.facing = 1 if party[target_key].position[0] >= entity.position[0] else -1
        record["facing"] = entity.facing
        profile = t.actor(run, key).weapon_profile() or {}
        expression = profile.get("damage_dice") or "1d6"
        modifier = profile.get("damage_modifier", 0)
        if modifier:
            expression = f"{expression}{modifier:+d}"
        shape = (0, -4, 35, 18) if entity.facing >= 0 else (-30, -4, 35, 18)
        hitboxes.append(spatial.Hitbox(
            owner_id=key, shape=shape, active_from=frame, active_to=frame,
            damage_type=t.rules(run, key).get("damage_type", "SLASHING"),
            damage_expression=expression, bypass_resistance=False,
        ))
    return hitboxes


def move_entity(run, key, dx, dy):
    dx = _strict_int(dx, "dx")
    dy = _strict_int(dy, "dy")
    if abs(dx) > MAX_DELTA or abs(dy) > MAX_DELTA:
        raise ArcadeError("movement delta is too large")
    record = _entity(run, key)
    entity = _spatial_entity(record)
    destination = (entity.position[0] + dx, entity.position[1] + dy, entity.position[2])
    if not all(WORLD_MIN <= value <= WORLD_MAX for value in destination):
        raise ArcadeError("movement leaves the arcade bounds")
    blocked = _blocked_by_obstacles(run, entity, destination)
    if blocked:
        return {
            "type": "movement_blocked",
            "actor": key,
            "obstacle": blocked["id"],
            "required_mode": list(blocked["required_mode"]),
        }
    if dx:
        entity.facing = 1 if dx > 0 else -1
    entity.position = destination
    _write_spatial(record, entity)
    return {"type": "arcade_move", "actor": key, "position": list(destination)}


def spawn_hit(run, source, target, hitbox, reduction=0.0):
    """Route one overlap through the existing deterministic damage pipeline.

    ``reduction`` (0-1) comes from a successful front block; it lowers the
    rolled amount before tactical.damage ever sees it, rather than teaching
    tactical.py about arcade-only mitigation.
    """
    amount, rolls = t.dice(run, hitbox.damage_expression)
    if reduction:
        amount = max(0, round(amount * (1 - reduction)))
    event = t.damage(
        run, source, target, amount, hitbox.damage_type,
        bypass_resistance=hitbox.bypass_resistance,
    )
    event["rolls"] = rolls
    if reduction:
        event["blocked"] = True
        event["block_reduction"] = reduction
    return event


def _attack_hitbox(run, key, frame):
    if not key.startswith("p"):
        raise ArcadeError("only player-controlled entities may declare arcade attacks")
    actor, rules = t.actor(run, key), t.rules(run, key)
    identity = rules.get("identity")
    if identity == "doran":
        expression, damage_type, bypass = "1d8+10", "PIERCING", True
    elif identity == "wren":
        expression, damage_type, bypass = "4d12", "RADIANT", False
    else:
        profile = actor.weapon_profile()
        if not profile or not profile.get("damage_dice"):
            raise ArcadeError("arcade attack requires an equipped weapon with damage dice")
        modifier = profile.get("damage_modifier", 0)
        expression = profile["damage_dice"] + (f"{modifier:+d}" if modifier else "")
        damage_type = rules.get("damage_type", "SLASHING")
        bypass = False

    record = _entity(run, key)
    entity = _spatial_entity(record)
    tags = entity.status_tags
    last_frame = tags.get("combo_last_frame")
    tier = tags.get("combo_tier", 0) + 1 if last_frame is not None and frame - last_frame <= COMBO_WINDOW_FRAMES else 0
    tier = min(tier, COMBO_MAX_TIER)
    tags["combo_tier"] = tier
    tags["combo_last_frame"] = frame
    _write_spatial(record, entity)

    shape = (0, -4, 35, 18) if entity.facing >= 0 else (-30, -4, 35, 18)
    if tier:
        expression = _add_flat_bonus(expression, tier * COMBO_TIER_DAMAGE_BONUS)
    if tier >= COMBO_MAX_TIER:
        # Finishing hit: a wider arc alongside the escalated damage.
        shape = (shape[0] - (10 if entity.facing >= 0 else 0), shape[1], shape[2] + 10, shape[3])
    return spatial.Hitbox(
        owner_id=key, shape=shape, active_from=frame, active_to=frame,
        damage_type=damage_type, damage_expression=expression,
        bypass_resistance=bypass,
    )


def _add_flat_bonus(expression, bonus):
    """Fold a flat bonus into a single ``NdM+K`` modifier.

    tactical.dice() only accepts one trailing modifier, so a combo bonus
    can't just be string-concatenated onto an expression that already has
    one (e.g. Doran's "1d8+10") without producing an expression it rejects.
    """
    if not bonus:
        return expression
    match = re.fullmatch(r"(\d{1,3}d(?:4|6|8|10|12|20))([+-]\d+)?", expression)
    if not match:
        return expression
    base, existing = match[1], int(match[2] or 0)
    total = existing + bonus
    return f"{base}{total:+d}" if total else base


def _coerce_hitbox(run, action, frame):
    key = action["actor"]
    if action.get("attack"):
        return _attack_hitbox(run, key, frame)
    raw = action.get("hitbox")
    if isinstance(raw, spatial.Hitbox):
        if raw.owner_id != key:
            raise ArcadeError("hitbox owner must match the input actor")
        return raw
    if isinstance(raw, dict):
        if raw.get("owner_id", key) != key:
            raise ArcadeError("hitbox owner must match the input actor")
        shape = raw.get("shape")
        if not isinstance(shape, list) or len(shape) != 4 or any(type(value) is not int for value in shape):
            raise ArcadeError("client hitbox shape must be four integers")
        # Transport callers may describe only the shape. Damage remains
        # derived from the actor's authoritative weapon profile.
        hitbox = _attack_hitbox(run, key, frame)
        hitbox.shape = tuple(shape)
        return hitbox
    raise ArcadeError("arcade attacks require attack intent or a server Hitbox")


def tick(run, inputs=None):
    """Advance one fixed server tick and return its public frame."""
    arcade = run.context.get("arcade")
    if not arcade or arcade.get("complete"):
        raise ArcadeError("no active arcade encounter")
    if inputs is not None and not isinstance(inputs, list):
        raise ArcadeError("arcade inputs must be a list")
    arcade.setdefault("projectiles", [])
    arcade["frame"] += 1
    frame = arcade["frame"]
    events = []
    hitboxes = []
    active = _active_keys(run)

    # Gravity/jump-arc physics integrates every tick regardless of input, so
    # a mid-air actor keeps falling even on a tick with no client action.
    for record in arcade["entities"].values():
        entity = _spatial_entity(record)
        if _integrate_vertical(entity):
            _write_spatial(record, entity)

    # Blocking is a held state: it only stays active on a tick where the
    # actor re-submits it, so it clears the instant the button/key is let go.
    for record in arcade["entities"].values():
        record.setdefault("status_tags", {})["blocking"] = False

    for action in inputs or []:
        if not isinstance(action, dict) or not isinstance(action.get("actor"), str):
            raise ArcadeError("each arcade input requires an actor")
        key = action["actor"]
        if key not in active:
            raise ArcadeError("input actor is not active in the current arcade frame")
        if not key.startswith("p"):
            raise ArcadeError("arcade client inputs may only control party actors")
        if "dx" in action or "dy" in action:
            events.append(move_entity(run, key, action.get("dx", 0), action.get("dy", 0)))
        if action.get("block"):
            arcade["entities"][key]["status_tags"]["blocking"] = True
        if action.get("dodge"):
            events.append(_apply_dodge(run, key, frame, action.get("dx"), action.get("dy")))
        if action.get("attack") or "hitbox" in action:
            hitboxes.append(_coerce_hitbox(run, action, frame))
        if action.get("ranged"):
            events.append(_spawn_projectile(run, key, frame))

    entity_objects = {key: _spatial_entity(record) for key, record in arcade["entities"].items()}
    active_enemies = _active_enemy_keys(arcade)
    hitboxes.extend(_enemy_actions(run, frame, entity_objects, active_enemies))
    hits = spatial.resolve_hitbox_overlap(entity_objects, hitboxes, frame)
    for hit in hits:
        owner_key, target_key = hit["hitbox_owner"], hit["target_id"]
        if target_key.startswith("e") and target_key not in active_enemies:
            continue
        if not t.actor(run, target_key).alive:
            continue
        target_entity = entity_objects[target_key]
        if target_entity.status_tags.get("invulnerable_until_frame", 0) >= frame:
            events.append({"type": "arcade_hit_avoided", "actor": target_key, "source": owner_key})
            continue
        reduction = _block_reduction(owner_key, target_key, entity_objects)
        events.append(spawn_hit(run, owner_key, target_key, hit["hitbox"], reduction=reduction))

    events.extend(_advance_projectiles(run, frame, entity_objects, active_enemies))

    if _wave_cleared(run):
        cleared_index = arcade["wave_index"]
        arcade["wave_index"] += 1
        if arcade["wave_index"] >= len(arcade["waves"]):
            arcade["complete"] = True
            arcade["gate_open"] = True
            events.append({
                "type": "arcade_room_cleared",
                "evidence": {"waves_cleared": len(arcade["waves"])},
            })
        else:
            events.append({"type": "arcade_wave_cleared", "wave_index": cleared_index})
    return {
        "type": "arcade_tick",
        "frame": frame,
        "events": events,
        "gate_open": arcade["gate_open"],
        "complete": arcade["complete"],
        "arcade_view": view(run),
    }


def view(run):
    arcade = run.context["arcade"]
    active_enemies = _active_enemy_keys(arcade)
    return {
        "schema": "hollow-star-arcade-public-1",
        "frame": arcade["frame"],
        "wave_index": arcade["wave_index"],
        "waves": len(arcade["waves"]),
        "gate_open": arcade["gate_open"],
        "complete": arcade["complete"],
        "bounds": {"x": [WORLD_MIN, WORLD_MAX], "y": [WORLD_MIN, WORLD_MAX], "z": [WORLD_MIN, WORLD_MAX]},
        "entities": {
            key: {
                "position": list(record["position"]),
                "movement_mode": record.get("movement_mode", MovementMode.RUN.value),
                "facing": record.get("facing", 1),
                "velocity": list(record.get("velocity", [0, 0])),
                "attack_ticks": max(0, 6 - (arcade["frame"] - record.get("status_tags", {}).get("combo_last_frame", -1000))),
                "grounded": bool(record.get("grounded", True)),
                "team": record.get("team", ""),
                "active": key.startswith("p") or key in active_enemies,
                "blocking": bool(record.get("status_tags", {}).get("blocking", False)),
                "combo_tier": record.get("status_tags", {}).get("combo_tier", 0),
                "invulnerable": record.get("status_tags", {}).get("invulnerable_until_frame", 0) >= arcade["frame"],
            }
            for key, record in arcade["entities"].items()
        },
        "obstacles": [copy.deepcopy(obstacle) for obstacle in arcade["obstacles"]],
        "projectiles": [copy.deepcopy(projectile) for projectile in arcade.get("projectiles", [])],
    }
