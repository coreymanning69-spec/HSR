/**
 * Sprite renderer for the HSR web interface.
 * Handles character and item sprite display with fallback to text.
 */

// Re-export FX, Rig, and Traversal systems for unified access across all presentation modules
export {SkeletalRig, Bone} from './skeletal-rig.js';
export {TraversalController} from './traversal-controller.js';
export {FXEngine, createFXOverlay, getPalette, DAMAGE_PALETTES} from './fx-engine.js';
import {DORAN_RIG} from './doran-rig.js';
import {WREN_RIG} from './wren-rig.js';
import {HERO_RIG} from './hero-rig.js';
export {DORAN_RIG, DORAN_PAPERDOLL_LAYERS, DORAN_POSES, drawDoran} from './doran-rig.js';
export {WREN_RIG, WREN_PAPERDOLL_LAYERS, WREN_POSES, drawWren} from './wren-rig.js';
export {HERO_RIG, drawHero, heroBurst, heroPortrait} from './hero-rig.js';

const SPRITE_BASE = '/assets/sprites';

/**
 * Get the sprite path for a character.
 * @param {string} spriteId - Character sprite identifier
 * @returns {string} - Path to the SVG file
 */
export function getCharacterSpritePath(spriteId) {
  if (!spriteId) return null;
  // Character art ships as PNG, one per race and female/male variant (the SVG
  // lookup only ever 404'd, then retried). Anything else -- "human-other",
  // monsters -- has no art: null lets the canvas draw its placeholder
  // instead of requesting a file that is not there.
  if (!/^(human|elf|half-elf|orc|goblin)-(female|male)$/.test(String(spriteId))) return null;
  return `${SPRITE_BASE}/characters/${spriteId}.png`;
}

// Champions built as layered paperdolls on the shared SkeletalRig (Doran
// since 2026-09-23, Wren since 2026-09-25). The rig
// owns every pose, so there is no per-pose art to swap: the figure animates
// through the same beats, IK and blending as any other puppet.
const CHAMPION_RIGS = Object.freeze({doran: DORAN_RIG, wren: WREN_RIG});

/**
 * Look up a champion's layered paperdoll rig, if it has one.
 * @param {string} identity
 * @returns {object|null}
 */
export function championRig(identity) {
  return CHAMPION_RIGS[String(identity || '').toLowerCase()] || null;
}

/**
 * The rig that draws a paperdoll model: the champion's own, or the hero rig
 * that every custom lead, resident and foe is built on. Frame-art models
 * (none today) return null and keep their image path.
 * @param {object} model dollModel() output
 * @returns {object|null}
 */
export function actorRig(model = {}) {
  if (model.base?.type !== 'rig') return null;
  return championRig(model.identity) || HERO_RIG;
}

// Champions with authored per-pose combat art (one transparent canvas per
// pose, anchored bottom-centre) bypass the flat sprite_id lookup above. No
// champion uses this path now: Doran moved to a rig on 2026-09-23 and his old
// frames (assets/sprites/characters/doran/doran-*.png) are unused. The catalog
// shape is kept for any future frame-art champion:
//   {dir, poses: {key: file}, idlePose, readyPose, width, height,
//    sockets: {poseKey: {socket: [x, y]}}, scale, footPadding}
const CHAMPION_POSE_ART = Object.freeze({});

/**
 * Look up a champion's dedicated pose-art catalog, if it has one.
 * @param {string} identity
 * @returns {object|null}
 */
export function championPoseArt(identity) {
  return CHAMPION_POSE_ART[String(identity || '').toLowerCase()] || null;
}

/**
 * Resolve the actual PNG path for one champion pose, falling back to the
 * champion's idle pose if the requested key isn't authored.
 * @param {string} identity
 * @param {string} poseKey
 * @returns {string|null}
 */
export function getChampionPosePath(identity, poseKey) {
  const art = championPoseArt(identity);
  if (!art) return null;
  const file = art.poses[poseKey] || art.poses[art.idlePose];
  return file ? `${art.dir}/${file}` : null;
}

const MANEUVER_POSE = Object.freeze({
  'Trip Attack': 'sweep',
  'Menacing Attack': 'overhead-strike',
  'Rally': 'low-ready',
  'Commanding Presence': 'guard',
});

/**
 * Derive which authored pose frame a champion should show right now from
 * whatever public, live signals are already available: the maneuver the
 * player last picked, the host's presentation.animation tags (turn-based
 * combat), or an arcade entity's live movement/attack/block state. This is
 * presentation only -- it never decides hit/miss/damage, it only picks which
 * already-resolved outcome to draw.
 * @param {string} identity
 * @param {object} signals
 * @returns {string|null} pose key, or null if this identity has no pose art
 */
export function resolveChampionPose(identity, {
  alive = true, inCombat = false, maneuver = null, animation = null, arcadeEntity = null,
} = {}) {
  const art = championPoseArt(identity);
  if (!art) return null;
  if (!alive) return art.idlePose;
  if (maneuver && MANEUVER_POSE[maneuver] && art.poses[MANEUVER_POSE[maneuver]]) return MANEUVER_POSE[maneuver];
  if (animation) {
    const attack = String(animation.attack || '').toLowerCase();
    if (attack) return /sweep|cleave|spin|whirl/.test(attack) ? 'sweep' : 'overhead-strike';
    if (animation.defense) return 'guard';
    if (animation.dodge) return 'low-ready';
  }
  if (arcadeEntity) {
    if (arcadeEntity.attack_ticks > 0) return arcadeEntity.combo_tier % 2 ? 'overhead-strike' : 'sweep';
    if (arcadeEntity.blocking) return 'guard';
    const mode = String(arcadeEntity.movement_mode || '').toUpperCase();
    if (mode === 'CLIMB') return 'low-ready';
    return art.readyPose;
  }
  return inCombat ? art.readyPose : art.idlePose;
}

/**
 * Get the sprite path for an item.
 * @param {string} spriteId - Item sprite identifier
 * @returns {string} - Path to the SVG file
 */
export function getItemSpritePath(spriteId) {
  if (!spriteId) return null;
  return `${SPRITE_BASE}/items/${spriteId}.svg`;
}

/**
 * Create a character sprite element.
 * @param {Object} actor - Actor data
 * @param {Object} options - Display options
 * @returns {HTMLElement}
 */
export function createCharacterSprite(actor, options = {}) {
  const {
    size = 'medium',        // small, medium, large
    showName = true,
    className = ''
  } = options;

  const container = document.createElement('div');
  container.className = `character-sprite sprite-${size} ${className}`;
  container.setAttribute('data-actor-id', actor.name || 'unknown');

  const spritePath = getCharacterSpritePath(actor.sprite_id);

  if (spritePath) {
    const img = document.createElement('img');
    img.src = spritePath;
    img.alt = actor.name;
    img.className = 'sprite-image';
    img.onerror = () => {
      // Fallback to text if sprite fails to load
      container.textContent = actor.name ? actor.name[0].toUpperCase() : '?';
      container.classList.add('sprite-fallback');
    };
    container.appendChild(img);
  } else {
    // Fallback: show initials or name
    container.textContent = actor.name ? actor.name[0].toUpperCase() : '?';
    container.classList.add('sprite-fallback');
  }

  if (showName && actor.name) {
    const nameLabel = document.createElement('div');
    nameLabel.className = 'sprite-label';
    nameLabel.textContent = actor.name;
    container.appendChild(nameLabel);
  }

  return container;
}

/**
 * Create an item sprite element.
 * @param {Object} item - Item data
 * @param {Object} options - Display options
 * @returns {HTMLElement}
 */
export function createItemSprite(item, options = {}) {
  const {
    size = 'small',         // small, medium, large
    showName = false,
    className = ''
  } = options;

  const container = document.createElement('div');
  container.className = `item-sprite sprite-${size} ${className}`;
  container.setAttribute('data-item-id', item.name || 'unknown');
  container.setAttribute('data-slot', item.slot || 'hand');

  const spritePath = getItemSpritePath(item.sprite_id);

  if (spritePath) {
    const img = document.createElement('img');
    img.src = spritePath;
    img.alt = item.name;
    img.className = 'sprite-image';
    img.onerror = () => {
      // Fallback to icon abbreviation
      container.textContent = item.name ? item.name[0].toUpperCase() : '?';
      container.classList.add('sprite-fallback');
    };
    container.appendChild(img);
  } else {
    // Fallback: show abbreviated item name
    container.textContent = item.name ? item.name[0].toUpperCase() : '?';
    container.classList.add('sprite-fallback');
  }

  if (showName && item.name) {
    const nameLabel = document.createElement('div');
    nameLabel.className = 'sprite-label';
    nameLabel.textContent = item.name;
    container.appendChild(nameLabel);
  }

  // Add slot indicator if not hand
  if (item.slot && item.slot !== 'hand') {
    const slotBadge = document.createElement('div');
    slotBadge.className = 'sprite-slot-badge';
    slotBadge.textContent = item.slot[0].toUpperCase();
    slotBadge.title = item.slot;
    container.appendChild(slotBadge);
  }

  return container;
}

/**
 * Render a character roster grid with sprites.
 * @param {Array} actors - Array of actor objects
 * @param {HTMLElement} container - Target container
 * @param {Object} options - Display options
 */
export function renderCharacterRoster(actors, container, options = {}) {
  container.innerHTML = '';
  container.className = 'character-roster';

  actors.forEach((actor) => {
    const card = document.createElement('div');
    card.className = 'character-card';

    const sprite = createCharacterSprite(actor, { size: 'medium', showName: true });
    card.appendChild(sprite);

    const statsDiv = document.createElement('div');
    statsDiv.className = 'character-stats';
    statsDiv.innerHTML = `
      <div class="stat-line"><span>HP:</span> <span>${actor.hp}/${actor.max_hp}</span></div>
      <div class="stat-line"><span>AC:</span> <span>${actor.armor_class}</span></div>
    `;
    card.appendChild(statsDiv);

    container.appendChild(card);
  });
}

/**
 * Render an inventory grid with item sprites.
 * @param {Array} items - Array of item objects
 * @param {HTMLElement} container - Target container
 * @param {Object} options - Display options
 */
export function renderInventory(items, container, options = {}) {
  container.innerHTML = '';
  container.className = 'inventory-grid';

  items.forEach((item) => {
    const slot = document.createElement('div');
    slot.className = `inventory-slot slot-${item.slot || 'hand'}`;

    const sprite = createItemSprite(item, { size: 'small', showName: true });
    slot.appendChild(sprite);

    container.appendChild(slot);
  });
}
