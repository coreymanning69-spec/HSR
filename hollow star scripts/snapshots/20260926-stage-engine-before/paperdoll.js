// Paper doll: one model, one render path for every character figure.
//
// dollModel() turns a public actor into plain data -- identity, pose, gear
// slots, layers, cosmetics -- and dollMarkup() draws that model. Champions
// with a layered rig (Doran) are painted part by part on the shared skeleton;
// champions with authored pose art use it as the doll's base layer. Nothing
// here decides outcomes: the host resolves combat, this only draws it.
import {championPoseArt, championRig, getChampionPosePath, resolveChampionPose} from './sprite-renderer.js';

// Re-export FX, Rig, and Traversal systems for unified access across paperdoll & figure consumers
export {SkeletalRig, Bone} from './skeletal-rig.js';
export {TraversalController} from './traversal-controller.js';
export {FXEngine, createFXOverlay, getPalette, DAMAGE_PALETTES} from './fx-engine.js';
export {DORAN_PAPERDOLL_LAYERS, DORAN_POSES, DORAN_LOADOUTS} from './doran-rig.js';

const E = value => globalThis.HSRUI.escape(value);

export function visualRole(item = {}, fallback = 'adventurer') {
  const text = `${item.name || ''} ${item.role || ''}`.toLowerCase();
  if (/mage|magic|cleric|caster|witch|wellkeeper/.test(text)) return 'caster';
  if (/guard|steward|fighter|warrior|sentinel/.test(text)) return 'guard';
  if (/town|resident|merchant|keeper/.test(text)) return 'townsfolk';
  return fallback;
}
// Equipment visuals come from the host's `presentation` block on each public
// item -- rarity, silhouette, material, fx -- which the host derives from the
// item's own mechanics. Nothing here reads an item NAME: a name regex draws
// "Hood of the Plate Captain" as plate armour, and a staff as a sword.
function inferredPresentation(row = {}) {
  if (row.presentation && typeof row.presentation === 'object') return row.presentation;
  const slot = String(row.slot || 'hand').toLowerCase();
  let silhouette = String(row.silhouette || '').toLowerCase();
  if (!silhouette) {
    if (slot === 'armor') silhouette = 'armor';
    else if (slot === 'head') silhouette = 'helm';
    else if (slot === 'cloak') silhouette = 'cloak';
    else if (slot === 'boots') silhouette = 'boots';
    else if (['ring', 'neck'].includes(slot)) silhouette = 'trinket';
    else if (slot === 'carried') silhouette = 'staff';
    else if (row.shield_bonus || (row.base_ac && !row.base_damage)) silhouette = 'shield';
    else if (Number(row.range_normal) > 20) silhouette = 'bow';
    else if (/^(INT|WIS|CHA)$/i.test(row.attack_ability || '')) silhouette = 'staff';
    else if (String(row.damage_type || '').toUpperCase() === 'PIERCING' && Number(row.reach || 5) <= 5) silhouette = 'dagger';
    else silhouette = 'sword';
  }
  let material = String(row.material || '').toLowerCase();
  if (!material && silhouette === 'armor') {
    if (Number(row.dex_cap) === 0) material = 'plate';
    else if (row.dex_cap != null) material = 'chain';
    else if (Number(row.base_ac) >= 15) material = 'robe';
    else if (Number(row.base_ac) >= 12) material = 'leather';
    else material = 'robe';
  }
  const handedness = row.handedness || (silhouette === 'shield' ? 'off-hand' : ['bow', 'staff'].includes(silhouette) ? 'two-handed' : ['sword', 'dagger', 'axe', 'wand'].includes(silhouette) ? 'one-handed' : 'none');
  const itemType = row.item_type || (silhouette === 'shield' ? 'shield' : ['sword', 'dagger', 'axe', 'bow', 'staff', 'wand'].includes(silhouette) ? 'weapon' : silhouette === 'armor' ? 'armor' : silhouette === 'helm' ? 'headgear' : silhouette === 'cloak' ? 'cloak' : silhouette === 'trinket' ? 'accessory' : 'utility');
  const animationProfile = row.animation_profile || (silhouette === 'shield' ? 'shield' : silhouette === 'bow' ? 'bow' : ['staff', 'wand'].includes(silhouette) ? silhouette : silhouette === 'dagger' ? 'dagger' : silhouette === 'axe' ? (handedness === 'two-handed' ? 'axe-2h' : 'axe') : silhouette === 'sword' ? (handedness === 'two-handed' ? 'sword-2h' : 'sword-1h') : 'neutral');
  return {rarity: row.rarity || 'mundane', silhouette, material: material || 'steel', fx: Array.isArray(row.fx) ? row.fx : [], item_type: itemType, handedness, coverage: row.coverage || (silhouette === 'helm' ? 'partial' : 'none'), animation_profile: animationProfile};
}
export function equipmentPresentations(item = {}) {
  return (Array.isArray(item.equipment) ? item.equipment : [])
    .map(row => row && inferredPresentation(row))
    .filter(row => row && typeof row === 'object');
}
// Shapes the paperdoll can actually draw; anything else falls back to a blade.
export const WEAPON_SILHOUETTES = Object.freeze({none: 'none', mace: 'mace', polearm: 'polearm', sword: 'sword', dagger: 'dagger', axe: 'axe', staff: 'staff', wand: 'wand', bow: 'bow', shield: 'shield'});
export function visualWeapon(item = {}) {
  const shapes = equipmentPresentations(item).map(row => WEAPON_SILHOUETTES[row.silhouette]).filter(Boolean);
  // A drawn weapon beats a shield: the shield has its own off-hand layer.
  return shapes.find(shape => shape !== 'shield') || (shapes[0] === 'shield' ? 'none' : shapes[0]) || 'none';
}
export const ARMOR_MATERIALS = Object.freeze({plate: 'plate', chain: 'chain', leather: 'leather', robe: 'robe', cloth: 'robe'});
export const WORN_SILHOUETTES = Object.freeze({helm: 'headgear', cloak: 'cloak', shield: 'offhand-shield', trinket: 'trinket'});
export function visualItemTokens(item = {}) {
  const tokens = [];
  for (const row of equipmentPresentations(item)) {
    if (row.silhouette === 'armor' && ARMOR_MATERIALS[row.material] && !tokens.some(t => ARMOR_MATERIALS[t])) {
      tokens.push(ARMOR_MATERIALS[row.material]);
    }
    const worn = row.silhouette === 'helm' && row.coverage === 'full' ? 'full-helm' : WORN_SILHOUETTES[row.silhouette];
    if (worn && !tokens.includes(worn)) tokens.push(worn);
  }
  return tokens;
}
// Rarity ladder, matching hollowstar/phases.py Tier. "unknown" is what the host
// substitutes for an unidentified Imprint and must rank lowest -- an
// unidentified item that sparkled would reveal what it is.
export const RARITY_RANK = Object.freeze({unknown: 0, mundane: 1, magical: 2, artifact: 3, blessed: 4});
export function visualRarity(item = {}) {
  let best = 'mundane';
  for (const row of equipmentPresentations(item)) {
    if ((RARITY_RANK[row.rarity] || 0) > (RARITY_RANK[best] || 0)) best = row.rarity;
  }
  return best;
}
export function visualEffectTokens(item = {}) {
  const allowed = new Set(['ember', 'frost', 'tide', 'gale', 'stone', 'arcane', 'hallow', 'radiant', 'wither', 'mind', 'resonant', 'acid', 'force', 'bleed', 'phase', 'silver', 'dense']);
  const fx = new Set();
  for (const row of equipmentPresentations(item)) {
    if (row.rarity === 'unknown') continue;
    for (const token of Array.isArray(row.fx) ? row.fx : []) {
      const safe = String(token).toLowerCase();
      if (allowed.has(safe)) fx.add(safe);
    }
  }
  return [...fx].sort();
}
// Cosmetic choices from character creation arrive as {field:{id,name,hex}}.
// They are emitted as CSS custom properties rather than as more class names so
// the stylesheet stays a fixed set of rules whatever the palette grows to.
// Each tinted layer is a gradient between a base colour and a companion
// shade. Setting only the base leaves the companion at its default, which
// shows up as auburn hair keeping a lilac highlight -- so the companions are
// derived here from the chosen colour.
export const APPEARANCE_VARS = Object.freeze({
  skin_tone: ['--skin', ['--skin-shadow', -0.22]],
  hair_color: ['--hair', ['--hair-light', 0.22]],
  eye_color: ['--eye'],
  outfit: ['--outfit', ['--outfit-light', 0.18], ['--outfit-dark', -0.3]],
  // Listed after outfit so the dye's declarations win in the style attribute;
  // 'As outfit' carries no hex and is skipped, leaving the outfit colour.
  cloth_color: ['--outfit', ['--outfit-light', 0.18], ['--outfit-dark', -0.3]],
});
export const HEX = /^#[0-9a-f]{6}$/i;
export function shadeHex(hex, amount) {
  const channel = index => {
    const value = parseInt(hex.slice(1 + index * 2, 3 + index * 2), 16);
    const shifted = amount >= 0 ? value + (255 - value) * amount : value * (1 + amount);
    return Math.max(0, Math.min(255, Math.round(shifted))).toString(16).padStart(2, '0');
  };
  return `#${channel(0)}${channel(1)}${channel(2)}`;
}
export function appearanceStyle(item = {}) {
  const appearance = item.appearance && typeof item.appearance === 'object' ? item.appearance : {};
  const parts = [];
  for (const [field, [prop, ...companions]] of Object.entries(APPEARANCE_VARS)) {
    const hex = appearance[field] && appearance[field].hex;
    // Only a literal six-digit colour is allowed through; the value lands in a
    // style attribute, so anything else is dropped rather than escaped.
    if (typeof hex !== 'string' || !HEX.test(hex)) continue;
    parts.push(`${prop}:${hex}`);
    for (const [companion, amount] of companions) parts.push(`${companion}:${shadeHex(hex, amount)}`);
  }
  const scale = appearance.body_type && Number(appearance.body_type.scale);
  if (Number.isFinite(scale) && scale > 0) parts.push(`--build:${Math.min(1.25, Math.max(0.8, scale))}`);
  return parts.join(';');
}
export function appearanceClasses(item = {}) {
  const appearance = item.appearance && typeof item.appearance === 'object' ? item.appearance : {};
  const slug = value => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '-');
  return ['hair_style', 'body_type', 'outfit', 'face_shape', 'facial_marks', 'ear_shape', 'cloak_style', 'headgear_style', 'weapon_style', 'offhand_style', 'trinket_style']
    .map(field => appearance[field] && appearance[field].id ? `${field.replace('_', '-')}-${slug(appearance[field].id)}` : '')
    .filter(Boolean).join(' ');
}
export function isChampion(item = {}) {
  const identity = String(item.identity || '').toLowerCase();
  return item.is_champion === true || item.kind === 'champion' || ['doran', 'sera', 'wren'].includes(identity);
}
export const SPRITE_LAYER_CATALOG = Object.freeze({
  shadow: {className: 'char-shadow', slot: 'ground'}, wings: {className: 'char-wings', slot: 'ground'},
  'effect:aura': {className: 'char-aura', slot: 'effect'},
  cape: {className: 'char-cape', slot: 'clothing'}, legs: {className: 'char-legs', slot: 'clothing'},
  boots: {className: 'char-boots', slot: 'clothing'}, 'arm:back': {className: 'char-arm char-arm-back', slot: 'clothing'},
  'hand:back': {className: 'char-hand char-hand-back', slot: 'body'}, coat: {className: 'char-coat', slot: 'clothing'},
  seam: {className: 'char-seam', slot: 'clothing'}, neck: {className: 'char-neck', slot: 'body'},
  ears: {className: 'char-ears', slot: 'body'}, head: {className: 'char-head', slot: 'body'},
  hair: {className: 'char-hair', slot: 'body'}, fringe: {className: 'char-fringe', slot: 'body'},
  brows: {className: 'char-brows', slot: 'body'}, eyes: {className: 'char-eyes', slot: 'body'},
  nose: {className: 'char-nose', slot: 'body'}, mouth: {className: 'char-mouth', slot: 'body'},
  collar: {className: 'char-collar', slot: 'equipment'}, shoulders: {className: 'char-shoulders', slot: 'equipment'},
  'arm:front': {className: 'char-arm char-arm-front', slot: 'clothing'},
  'hand:front': {className: 'char-hand char-hand-front', slot: 'body'}, cuffs: {className: 'char-cuffs', slot: 'clothing'},
  belt: {className: 'char-belt', slot: 'equipment'}, buckle: {className: 'char-buckle', slot: 'equipment'},
  emblem: {className: 'char-emblem', slot: 'equipment'},
  'weapon:mace': {className: 'char-weapon mace', slot: 'weapon'},
  'weapon:polearm': {className: 'char-weapon polearm', slot: 'weapon'},
  'weapon:sword': {className: 'char-weapon sword', slot: 'weapon'},
  'weapon:dagger': {className: 'char-weapon dagger', slot: 'weapon'},
  'weapon:axe': {className: 'char-weapon axe', slot: 'weapon'},
  'weapon:staff': {className: 'char-weapon staff', slot: 'weapon'},
  'weapon:wand': {className: 'char-weapon wand', slot: 'weapon'},
  'weapon:bow': {className: 'char-weapon bow', slot: 'weapon'},
  'weapon:shield': {className: 'char-weapon shield', slot: 'weapon'},
  'item:headgear': {className: 'char-headgear', slot: 'equipment', src: 'assets/sprites/layers/headgear.svg'},
  'item:full-helm': {className: 'char-headgear char-full-helm', slot: 'equipment', src: 'assets/sprites/layers/headgear.svg'},
  'item:cloak': {className: 'char-cloak', slot: 'equipment', src: 'assets/sprites/layers/cloak.svg'},
  'item:offhand-shield': {className: 'char-offhand-shield', slot: 'equipment', src: 'assets/sprites/layers/shield.svg'},
  'item:trinket': {className: 'char-trinket', slot: 'equipment', src: 'assets/sprites/layers/trinket.svg'},
});
export const BASE_SPRITE_LAYERS = ['shadow', 'wings', 'cape', 'legs', 'boots', 'arm:back', 'hand:back', 'coat', 'seam', 'neck', 'ears', 'head', 'hair', 'fringe', 'brows', 'eyes', 'nose', 'mouth', 'collar', 'shoulders', 'arm:front', 'hand:front', 'cuffs', 'belt', 'buckle', 'emblem'];

function appearanceLayerIds(item = {}) {
  const appearance = item.appearance && typeof item.appearance === 'object' ? item.appearance : {};
  return Object.values(appearance).flatMap(row => Array.isArray(row?.visual?.layer_ids) ? row.visual.layer_ids : [])
    .filter(id => SPRITE_LAYER_CATALOG[id]);
}
export function visibleGearTheme(item = {}) {
  // Worn armour decides the coat treatment; "travel" is the unarmoured look,
  // which lets the creator's outfit choice show through.
  const worn = equipmentPresentations(item).find(row => row.silhouette === 'armor' && ARMOR_MATERIALS[row.material]);
  return worn ? ARMOR_MATERIALS[worn.material] : 'travel';
}
export function spriteLayerMarkup(layerId) {
  const layer = SPRITE_LAYER_CATALOG[layerId];
  if (!layer) return '';
  // Future transparent assets are registered here; public state supplies IDs,
  // never arbitrary URLs.
  if (layer.src) return `<img class="sprite-layer ${E(layer.className || '')}" data-sprite-layer="${E(layer.slot)}" data-layer-id="${E(layerId)}" src="${E(layer.src)}" alt="" aria-hidden="true">`;
  return `<i class="sprite-layer ${E(layer.className)}" data-sprite-layer="${E(layer.slot)}" data-layer-id="${E(layerId)}" aria-hidden="true"></i>`;
}
export function visualIdentity(item = {}) {
  return String(item.identity || item.sprite_id || item.id || 'adventurer').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'adventurer';
}
export function presentationAppearance(item = {}) {
  return item.sprite_id || `${item.race_id || 'human'}-${item.gender || 'other'}`;
}
export function visualExpression(item = {}, pose = 'idle') {
  const status = JSON.stringify(item.status || item.conditions || []).toLowerCase();
  if (Number(item.hp ?? 1) <= 0) return 'fallen';
  if (/bleed|burn|fear|poison|stun|wound/.test(status)) return 'strained';
  if (inBattle(pose)) return 'focused';
  return visualIdentity(item) === 'wren' ? 'serene' : 'alert';
}
// Slots an authored base image already paints. Ground (shadow) and effect
// (aura) layers still draw around art; everything else is covered by it.
export const ART_COVERED_SLOTS = Object.freeze(['body', 'clothing', 'equipment', 'weapon']);
// Battle-line poses (side-view combat) render as combat for expression and
// champion art, and reach the rig by name.
const BATTLE_POSES = ['battleIdle', 'ready', 'advance', 'retreat', 'defend', 'victory', 'kneel', 'ko'];
const POSES = ['idle', 'combat', 'travel', 'staffLow', 'staffPoint', ...BATTLE_POSES];
const inBattle = pose => pose === 'combat' || BATTLE_POSES.includes(pose);

// The presentation facts a rig draws gear from, one row per equipped item.
// An unidentified Imprint keeps its host-redacted "unknown" row, so it can
// never render as what it really is.
const GEAR_KEYS = ['silhouette', 'material', 'fx', 'rarity', 'handedness', 'coverage'];
const compactGear = row => Object.fromEntries(GEAR_KEYS.filter(key => row[key] != null)
  .map(key => [key, key === 'fx' ? (Array.isArray(row.fx) && row.rarity !== 'unknown' ? row.fx.map(String) : []) : String(row[key]).toLowerCase()]));
const HELD = new Set(['sword', 'dagger', 'axe', 'mace', 'polearm', 'staff', 'wand', 'bow']);
// Equipped items first; then any authored costume (content/looks.json) for a
// figure with no sheet. Costume only fills gaps: it never replaces a real
// weapon's silhouette or a worn slot.
export function visualGear(item = {}) {
  const gear = equipmentPresentations(item).map(compactGear);
  const costume = (Array.isArray(item.costume) ? item.costume : []).filter(row => row && typeof row.silhouette === 'string').map(compactGear);
  const armed = gear.some(row => HELD.has(row.silhouette));
  for (const row of costume) {
    if (HELD.has(row.silhouette) ? armed : gear.some(g => g.silhouette === row.silhouette)) continue;
    gear.push(row);
  }
  return gear;
}

export function dollModel(item = {}, {pose = 'idle', maneuver = null, animation = null} = {}) {
  const champion = isChampion(item);
  const identity = visualIdentity(item);
  const rig = champion ? championRig(identity) : null;
  const resolvedPose = POSES.includes(pose) || rig?.poses.includes(pose) ? pose : 'idle';
  const weapon = visualWeapon(item);
  const itemTokens = visualItemTokens(item);
  const effects = visualEffectTokens(item);
  const requested = Array.isArray(item.sprite_layer_ids) ? item.sprite_layer_ids.filter(id => SPRITE_LAYER_CATALOG[id]) : [];
  const gear = visualGear(item);
  // A rigged champion reports its own part catalog; everyone else the CSS stack.
  const catalog = rig ? rig.layers : SPRITE_LAYER_CATALOG;
  const layers = rig ? Object.keys(rig.layers)
    : [...new Set([...BASE_SPRITE_LAYERS, ...(effects.length ? ['effect:aura'] : []), `weapon:${weapon}`, ...itemTokens.map(token => `item:${token}`), ...appearanceLayerIds(item), ...requested])]
      .filter(id => SPRITE_LAYER_CATALOG[id]);
  const slots = {};
  for (const id of layers) (slots[catalog[id].slot] ||= []).push(id);
  // Everyone draws on a vector rig: a champion on its own, everyone else --
  // custom leads, residents, foes -- on the hero rig, built from this model.
  let base = item.base_type === 'canvas' ? {type: 'canvas'} : {type: 'rig', rig: 'hero', loadout: weapon, maneuver: maneuver || null};
  if (rig) {
    base = {type: 'rig', rig: identity, loadout: rig.loadout(item, weapon), maneuver: maneuver || null, heightUnits: rig.heightUnits};
  } else if (champion && championPoseArt(identity)) {
    const poseKey = resolveChampionPose(identity, {alive: Number(item.hp ?? 1) > 0, inCombat: inBattle(resolvedPose), maneuver, animation});
    const src = getChampionPosePath(identity, poseKey);
    const catalog = championPoseArt(identity);
    const scale = Number(catalog.scale) || 1;
    const drop = (Number(catalog.footPadding) || 0) * scale * 100;
    if (src) base = {type: 'art', poseKey, src, scale, drop};
  }
  return {
    id: item.id || '', name: item.name || '', identity, champion, role: visualRole(item),
    appearance: presentationAppearance(item), appearanceData: item.appearance || {}, pose: resolvedPose, expression: visualExpression(item, resolvedPose),
    rarity: visualRarity(item), gearTheme: visibleGearTheme(item), weapon: weapon !== 'none' ? weapon : (gear.find(row => HELD.has(row.silhouette))?.silhouette || 'none'),
    itemTokens, effects, gear, age: item.age === 'child' || item.child === true ? 'child' : 'adult', aura: typeof item.aura === 'string' ? item.aura : '',
    race: item.race_id || String(item.sprite_id || '').replace(/-(female|male|other)$/, '') || 'human', gender: item.gender || 'other', alive: Number(item.hp ?? 1) > 0,
    layers, slots, base, style: appearanceStyle(item), cosmeticClasses: appearanceClasses(item),
    ...(rig ? {loadout: base.loadout, maneuver: base.maneuver, ...(rig.presentation ? {kit: rig.presentation(item)} : {})} : {}),
  };
}

// extra: classes appended to the figure. style: prepended to the appearance
// variables (one attribute). attrs: extra data-* attributes, values escaped.
// overlay: markup drawn above the doll (HP bar, turn marker, target ring).
export function dollMarkup(model, {extra = '', style = '', attrs = {}, overlay = ''} = {}) {
  const art = model.base.type === 'art', rig = model.base.type === 'rig', hero = rig && model.base.rig === 'hero';
  const classes = ['scene-character', 'paperdoll-character', model.champion ? 'champion-character' : 'custom-character',
    model.role, extra, `identity-${model.identity}`, `appearance-${model.appearance}`, model.cosmeticClasses,
    `gear-${model.gearTheme}`, `rarity-${model.rarity}`, ...model.effects.map(token => `fx-${token}`),
    ...model.itemTokens.map(token => `item-${token}`), `pose-${model.pose}`, `expression-${model.expression}`,
    'doll-puppet', art ? 'doll-art champion-pose-art' : hero ? `doll-rig hero-rig loadout-${model.base.loadout}` : rig ? `doll-rig champion-rig loadout-${model.base.loadout}` : 'doll-canvas'].filter(Boolean).join(' ');
  const artScale = art ? `--doll-art-scale:${model.base.scale};--doll-art-drop:-${model.base.drop.toFixed(1)}%` : '';
  const styleAttr = [style, model.style, artScale].filter(Boolean).join(';');
  const extraAttrs = Object.entries(attrs).filter(([, value]) => value !== undefined && value !== null)
    .map(([key, value]) => ` ${key.replace(/[^a-z0-9-]/gi, '')}="${E(value)}"`).join('');
  const label = model.name || model.role;
  // A 208 lb cleaver swings on a heavier beat (combat director tempo).
  // A two-handed blade on the hero rig winds up a little longer; Doran's
  // 208 lb Cleaver keeps its own, heavier tempo.
  const twoHanded = hero && model.gear.some(row => row.handedness === 'two-handed' && ['sword', 'axe', 'mace'].includes(row.silhouette));
  const tempo = model.base.loadout === 'cleaver' ? 'heavy' : twoHanded ? 'two-handed' : '';
  const rigAttrs = rig ? ` data-loadout="${E(model.base.loadout)}"${tempo ? ` data-beat-tempo="${tempo}"` : ''}` : '';
  const baseArt = art
    ? `<img class="doll-base-art champion-pose-image" data-sprite-layer="base" src="${E(model.base.src)}" alt="" aria-hidden="true" onerror="this.closest('.doll-art')?.classList.add('champion-pose-fallback')">`
    : '';
  return `<div class="${E(classes)}"${styleAttr ? ` style="${E(styleAttr)}"` : ''}${extraAttrs}${art ? ` data-champion-pose="${E(model.base.poseKey)}"` : ''} data-puppet-model="${E(JSON.stringify(model))}" data-doll-base="${E(model.base.type)}"${rigAttrs} data-sprite-id="${E(model.appearance)}" data-character-identity="${E(model.identity)}" data-sprite-pose="${E(model.pose)}" data-sprite-rarity="${E(model.rarity)}" data-sprite-layers="${E(model.layers.join(' '))}" aria-label="${E(label)} ${model.champion ? 'champion' : 'custom character'}">
    <canvas class="puppet-canvas" aria-hidden="true"></canvas>${baseArt}${overlay}
    <span class="actor-nameplate">${E(label)}</span></div>`;
}

export function characterFigure(item = {}, extra = '', pose = 'idle', options = {}) {
  return dollMarkup(dollModel(item, {pose, ...options}), {extra, ...options});
}
