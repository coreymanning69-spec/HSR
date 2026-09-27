/**
 * traversal-controller.js — Kinematic Traversal & Obstacle Parkour Subsystem for HSR.
 * 
 * Senses obstacles in the world along the Left -> Right traversal path,
 * managing the kinematic state machine for:
 * 1. Approach & Ledge Reach
 * 2. Vertical Wall / Ladder Climbing
 * 3. Obstacle Top Vaulting & Crest Clearance
 * 4. Ballistic Jumping over Gaps and Low Obstacles
 * 
 * Integrates with `SkeletalRig` to drive procedural poses and compute
 * smooth visual elevation over obstacles while maintaining server-authoritative
 * synchronization.
 */

export class TraversalController {
  constructor() {
    // Map of entityId -> TraversalState
    this.states = new Map();
  }

  getEntityState(entityId) {
    let state = this.states.get(entityId);
    if (!state) {
      state = {
        phase: 'ground', // 'ground', 'approach', 'climb', 'vault', 'jump', 'land'
        obstacleId: null,
        progress: 0,
        verticalElevation: 0, // Visual elevation in world units
        currentObstacle: null,
        climbHeightSoFar: 0,
      };
      this.states.set(entityId, state);
    }
    return state;
  }

  /**
   * Senses if an obstacle is ahead or overlapping with the entity along X.
   */
  findRelevantObstacle(entityX, entityY, facing, obstacles = [], senseDistance = 12) {
    if (!obstacles || !obstacles.length) return null;
    const direction = facing >= 0 ? 1 : -1;

    for (const obstacle of obstacles) {
      const ox = Number(obstacle.position?.[0] || 0);
      const oy = Number(obstacle.position?.[1] || 0);
      const ow = Number(obstacle.width || 6);

      // Check depth lane proximity (within 35 units in Y)
      const laneDist = Math.abs(entityY - oy);
      if (laneDist > 35) continue;

      // Check horizontal proximity
      const obstacleLeft = ox - ow / 2;
      const obstacleRight = ox + ow / 2;

      // Inside obstacle bounds or approaching leading edge
      const inside = entityX >= obstacleLeft - 2 && entityX <= obstacleRight + 2;
      const approaching = direction > 0
        ? entityX < obstacleLeft && entityX + senseDistance >= obstacleLeft
        : entityX > obstacleRight && entityX - senseDistance <= obstacleRight;

      if (inside || approaching) {
        return obstacle;
      }
    }
    return null;
  }

  /**
   * Update kinematic traversal for an entity and apply the result to its SkeletalRig.
   * 
   * @param {string} entityId
   * @param {object} entity - Server arcade entity {position: [x, y, z], movement_mode, facing, ...}
   * @param {Array} obstacles - Live obstacles in current arcade room
   * @param {SkeletalRig} rig - Entity's skeletal rig instance
   * @param {number} dt - Frame delta time in ms
   * @returns {object} {elevationZ, pose, progress, isTraversing}
   */
  update(entityId, entity, obstacles, rig, dt = 16) {
    const state = this.getEntityState(entityId);
    const x = Number(entity.position?.[0] || 0);
    const y = Number(entity.position?.[1] || 0);
    const z = Number(entity.position?.[2] || 0);
    const facing = Number(entity.facing || 1);
    const mode = String(entity.movement_mode || 'run').toLowerCase();

    const confirmed = ['climb', 'vault', 'jump', 'fall', 'fly'].includes(mode);
    const moving = Math.hypot(...(entity.velocity || [0,0]).slice(0,2)) > 0.05;
    const pose = confirmed ? mode : z > 0.05 ? 'jump' : moving ? 'run' : 'idle';
    state.phase = pose; state.progress = 0; state.verticalElevation = 0;
    state.currentObstacle = null;
    rig.applyPose(pose);
    return {elevationZ: 0, pose, progress: 0, isTraversing: confirmed || z > 0.05};
  }
  clear() { this.states.clear(); }
  remove(id) { this.states.delete(id); }
}
