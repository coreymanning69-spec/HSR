// Actor Look: one description of how an actor appears, built from public data.
//
// Everything a rig needs to draw a figure comes from here -- body proportions,
// named colour slots, face and hair features, what is worn and what is held --
// and all of it is derived from fields the host already publishes: race and
// gender, the creator's appearance choices, and each equipped item's
// `presentation` block (silhouette, material, fx, rarity, handedness,
// coverage). Items therefore change the figure the moment they are equipped,
// and a designer that edits appearance edits exactly what combat will draw.
//
// Presentation only. Nothing here reads an item's NAME or decides mechanics.

import {hash32, isHex, lightHex, mixHex, shadeHex} from './actor-core.js';

// Rig units per foot at the shared 5'8" baseline (97 units, matching the
// champion rigs so a custom lead stands at the right height beside Doran).
export const UNITS_PER_FOOT = 97 / (68 / 12);

// Race frames. height in feet; width scales the torso and limbs; head scales
// the skull (goblins read by their big heads and ears); leg is the share of the
// body below the head given to the legs.
export const RACE_FRAME = Object.freeze({
  human: {height: 5 + 8 / 12, width: 1, head: 1, leg: 1, ear: 1.4},
  elf: {height: 5 + 10 / 12, width: .9, head: .95, leg: 1.04, ear: 4.6},
  'half-elf': {height: 5 + 8.5 / 12, width: .95, head: .98, leg: 1.02, ear: 3},
  orc: {height: 6 + 3 / 12, width: 1.2, head: 1.04, leg: .98, ear: 2.2, tusks: true, brow: 1.4},
  goblin: {height: 3 + 9 / 12, width: .92, head: 1.34, leg: .9, ear: 6.4, nose: 1.6},
});
const GENDER_FRAME = Object.freeze({
  female: {height: .97, shoulders: .9, hips: 1.08, jaw: .9},
  male: {height: 1.02, shoulders: 1.07, hips: .96, jaw: 1.08},
  other: {height: 1, shoulders: 1, hips: 1, jaw: 1},
});
const BUILD = Object.freeze({slight: .86, lean: .93, average: 1, sturdy: 1.12, broad: 1.24});

// Materials: base, shade, highlight, deep. Clean Cel uses base + shade; metal
// adds one posterized highlight band.
export const MATERIALS = Object.freeze({
  steel: {base: '#c9d1d9', shade: '#8e99a6', hi: '#eef2f5', deep: '#5f6975'},
  silver: {base: '#e3e8ee', shade: '#a9b3bf', hi: '#ffffff', deep: '#7b8594'},
  gold: {base: '#e0bd62', shade: '#a8842f', hi: '#f7e4a0', deep: '#6f5620'},
  bronze: {base: '#c08a4b', shade: '#86592a', hi: '#e5b27a', deep: '#5a3a1b'},
  iron: {base: '#8f979f', shade: '#5f666e', hi: '#b9c0c7', deep: '#3e444a'},
  wood: {base: '#8a5f3c', shade: '#5e3e25', hi: '#b0825a', deep: '#3d2716'},
  obsidian: {base: '#25212f', shade: '#110f18', hi: '#7f71c9', deep: '#07060b'},
  bone: {base: '#e8dfc8', shade: '#b9ad90', hi: '#fbf6e8', deep: '#8c8168'},
  crystal: {base: '#a8e6f0', shade: '#5fb3c4', hi: '#f0ffff', deep: '#2f7686'},
  leather: {base: '#7a5641', shade: '#553a2b', hi: '#9c7458', deep: '#36251b'},
  unknown: {base: '#8d8a99', shade: '#5f5c6b', hi: '#b9b6c4', deep: '#3f3d49'},
});
export const ELEMENT_COLOUR = Object.freeze({
  ember: '#ff7a2f', frost: '#8fdcff', tide: '#4aa6ff', gale: '#e3f1ff', stone: '#a08a66', arcane: '#a77bff',
  hallow: '#ffe07a', radiant: '#ffd166', wither: '#7d4bb8', mind: '#f15bb5', resonant: '#6fd0db', acid: '#5fd16b',
  force: '#c05bd9', bleed: '#c0242f', phase: '#9fe7ff', silver: '#eef3f8',
});

const pick = (appearance, field, fallback) => {
  const row = appearance?.[field];
  return row && typeof row === 'object' && row.id ? row.id : fallback;
};
const hexOf = (appearance, field, fallback) => {
  const row = appearance?.[field];
  return row && typeof row === 'object' && isHex(row.hex) ? row.hex.toLowerCase() : fallback;
};

// Actors with no appearance choices (town residents, rehearsal foes, roster
// NPCs) still differ from one another: their colours are seeded from their id,
// so a squad of three watchmen reads as three people in one uniform.
const SEED_SKIN = ['#ecd2bd', '#e3bb9c', '#d6b394', '#c2996f', '#9a6b47', '#6f4630'];
const SEED_HAIR = ['#0f1418', '#3b2a1d', '#5a3a24', '#8b7355', '#7d3b2e', '#c9a961', '#959aa6', '#2a211c'];
const SEED_EYE = ['#4a8fb0', '#5b7a52', '#6b5334', '#777096', '#3a6f8a', '#b08a3e'];
const SEED_HAIR_STYLE = ['short', 'cropped', 'tousled', 'long', 'braided', 'topknot', 'short', 'cropped'];
const RACE_SKIN = {orc: ['#8d9a76', '#77887e', '#6f8064'], goblin: ['#94a36d', '#a8b46a', '#7d8355']};

// Equipment rows as the paperdoll model carries them (presentation blocks).
function gearOf(model) {
  return (Array.isArray(model.gear) ? model.gear : []).filter(row => row && typeof row === 'object');
}
const ARMOR_KINDS = new Set(['plate', 'chain', 'leather', 'robe']);
const WEAPONS = new Set(['sword', 'dagger', 'axe', 'mace', 'polearm', 'staff', 'wand', 'bow']);

// Which pose family a held weapon uses. registerWeaponKind() adds new
// silhouettes (paint them with hero-parts registerWeapon()).
const PROFILE_OF = {bow: 'bow', staff: 'staff', wand: 'wand', dagger: 'dagger', polearm: 'polearm'};
export function registerWeaponKind(kind, profile) { WEAPONS.add(kind); PROFILE_OF[kind] = profile; }
export function weaponProfile(kind, hands) {
  if (kind === 'none' || !kind) return 'unarmed';
  if (PROFILE_OF[kind]) return PROFILE_OF[kind];
  return hands === 2 ? 'heavy' : 'blade';
}

export function actorLook(model = {}) {
  const appearance = model.appearanceData && typeof model.appearanceData === 'object' ? model.appearanceData : {};
  const seedText = `${model.id || ''}|${model.name || ''}|${model.identity || ''}`;
  const seed = hash32(seedText);
  const seeded = (list, salt) => list[(seed >>> salt) % list.length];
  const race = RACE_FRAME[model.race] ? model.race : 'human';
  const frame = RACE_FRAME[race];
  const gender = GENDER_FRAME[model.gender] ? model.gender : 'other';
  const g = GENDER_FRAME[gender];
  const buildId = pick(appearance, 'body_type', 'average');
  const build = BUILD[buildId] || 1;
  const custom = Object.keys(appearance).length > 0;

  // ---- colour slots
  const skin = hexOf(appearance, 'skin_tone', race in RACE_SKIN ? seeded(RACE_SKIN[race], 3) : seeded(SEED_SKIN, 5));
  const hair = hexOf(appearance, 'hair_color', seeded(SEED_HAIR, 7));
  const eye = hexOf(appearance, 'eye_color', seeded(SEED_EYE, 11));
  const outfitId = pick(appearance, 'outfit', custom ? 'travel' : seeded(['travel', 'tunic', 'coat', 'vest'], 13));
  // The dye (cloth_color) recolours whatever outfit is worn; 'as outfit' has no hex.
  const cloth = hexOf(appearance, 'cloth_color', hexOf(appearance, 'outfit', {travel: '#6d594e', tunic: '#6b7383', coat: '#3f4a63', robe: '#76628f', vest: '#7a6a4f', uniform: '#4a5a5f'}[outfitId] || '#5d6478'));
  const accent = hexOf(appearance, 'accent_color', '#d9b56e');

  // ---- what is worn and held, from the item presentation blocks
  const gear = gearOf(model);
  const armor = gear.find(row => row.silhouette === 'armor' && ARMOR_KINDS.has(row.material === 'cloth' ? 'robe' : row.material));
  const helm = gear.find(row => row.silhouette === 'helm');
  const cloakItem = gear.find(row => row.silhouette === 'cloak');
  const boots = gear.find(row => row.silhouette === 'boots');
  const trinketItem = gear.find(row => row.silhouette === 'trinket');
  const shield = gear.find(row => row.silhouette === 'shield');
  const weapons = gear.filter(row => WEAPONS.has(row.silhouette));
  // A drawn weapon beats a carried one; a focus (staff/wand) stays in hand.
  const main = weapons[0] || null;
  const second = weapons.find((row, i) => i > 0 && row.handedness !== 'two-handed' && !['bow', 'staff', 'polearm'].includes(row.silhouette)) || null;
  const mainKind = main ? main.silhouette : (WEAPONS.has(model.weapon) ? model.weapon : 'none');
  const hands = main?.handedness === 'two-handed' || ['bow', 'staff', 'polearm'].includes(mainKind) ? 2 : 1;
  const finish = pick(appearance, 'weapon_style', 'plain');

  let torso = armor ? (armor.material === 'cloth' ? 'robe' : armor.material) : (outfitId === 'robe' ? 'robe' : outfitId);
  if (model.gearTheme && ARMOR_KINDS.has(model.gearTheme) && !armor) torso = model.gearTheme;
  const armored = torso === 'plate' || torso === 'chain';
  // Headgear: an equipped helm decides; otherwise the creator's choice.
  let headgear = pick(appearance, 'headgear_style', 'none');
  if (helm) headgear = helm.coverage === 'full' ? 'full-helm' : 'half-helm';
  else if ((model.itemTokens || []).includes('full-helm')) headgear = 'full-helm';
  let cloak = pick(appearance, 'cloak_style', 'none');
  if (cloakItem && cloak === 'none') cloak = 'travel-cape';
  if (cloak === 'hooded-cloak' && headgear === 'none') headgear = 'hood';
  let offhand = pick(appearance, 'offhand_style', 'none');
  if (shield) offhand = offhand === 'buckler' ? 'buckler' : 'kite-shield';
  // A two-handed weapon needs both hands: the off-hand choice is carried, not held.
  const offStowed = hands === 2 && offhand !== 'none';
  let trinket = pick(appearance, 'trinket_style', 'none');
  if (trinketItem && trinket === 'none') trinket = 'pendant';

  const fx = Array.isArray(model.effects) ? model.effects.filter(token => ELEMENT_COLOUR[token]) : [];
  const weaponFx = Array.isArray(main?.fx) ? main.fx.filter(token => ELEMENT_COLOUR[token]) : [];
  const rarity = model.rarity || 'mundane';

  const materialOf = (row, fallback) => {
    const m = String(row?.material || '').toLowerCase();
    return MATERIALS[m] ? m : fallback;
  };
  const mainMaterial = materialOf(main, ['staff', 'wand', 'bow'].includes(mainKind) ? 'wood' : 'steel');
  const armorMetal = materialOf({material: armor?.fx?.includes('silver') ? 'silver' : ''}, 'steel');

  const child = model.age === 'child';
  const heightFt = frame.height * g.height * (buildId === 'slight' ? .98 : buildId === 'broad' ? 1.01 : 1) * (child ? .66 : 1);
  const look = {
    race, gender, custom,
    body: {
      heightUnits: heightFt * UNITS_PER_FOOT, width: frame.width * build * (child ? .86 : 1), head: frame.head * (child ? 1.2 : 1), leg: frame.leg * (child ? .94 : 1),
      shoulders: g.shoulders * (buildId === 'broad' ? 1.06 : 1), hips: g.hips, jaw: g.jaw, build: buildId,
    },
    palette: {
      skin, skinShade: shadeHex(skin, .24), skinDeep: shadeHex(skin, .42), blush: mixHex(skin, '#c65a4f', .22),
      hair, hairShade: shadeHex(hair, .34), hairHi: lightHex(hair, .22),
      eye, cloth, clothShade: shadeHex(cloth, .32), clothHi: lightHex(cloth, .14), clothDeep: shadeHex(cloth, .5),
      accent, accentShade: shadeHex(accent, .3), accentHi: lightHex(accent, .3),
      trouser: shadeHex(cloth, .48), trouserShade: shadeHex(cloth, .62),
      leather: MATERIALS.leather.base, leatherShade: MATERIALS.leather.shade, leatherHi: MATERIALS.leather.hi, leatherDeep: MATERIALS.leather.deep,
      metal: MATERIALS[armorMetal].base, metalShade: MATERIALS[armorMetal].shade, metalHi: MATERIALS[armorMetal].hi, metalDeep: MATERIALS[armorMetal].deep,
      mail: '#9aa4ae', mailShade: '#6c7680',
      ink: '#10131b', white: '#f7f4ec', lip: mixHex(skin, '#a8453f', .4),
    },
    face: pick(appearance, 'face_shape', seeded(['balanced', 'angular', 'round', 'narrow', 'soft'], 17)),
    marks: pick(appearance, 'facial_marks', 'none'),
    ears: pick(appearance, 'ear_shape', /elf/.test(race) ? 'pointed' : race === 'goblin' ? 'swept' : 'standard'),
    hairStyle: pick(appearance, 'hair_style', seeded(SEED_HAIR_STYLE, 19)),
    tusks: Boolean(frame.tusks), nose: frame.nose || 1, brow: frame.brow || 1, earSize: frame.ear,
    torso, armored, outfit: outfitId,
    cloak, headgear, offhand, offStowed, trinket,
    boots: torso === 'plate' ? 'sabatons' : boots ? 'boots' : torso === 'robe' ? 'shoes' : 'boots',
    main: {kind: mainKind, hands, profile: weaponProfile(mainKind, hands), material: mainMaterial, finish,
      fx: weaponFx, rarity: main?.rarity || rarity, glow: (main?.fx || []).includes('glow'), dense: (main?.fx || []).includes('dense')},
    second: second ? {kind: second.silhouette, material: materialOf(second, 'steel'), fx: (second.fx || []).filter(t => ELEMENT_COLOUR[t])} : null,
    shieldMaterial: materialOf(shield, 'steel'),
    fx, rarity, child,
    // An element glow around the whole figure (a drowned foe's tide, a spirit's phase).
    aura: ELEMENT_COLOUR[model.aura] ? model.aura : '',
    expression: model.expression || 'alert',
    seed,
  };
  look.key = lookKey(look);
  return look;
}

// Proportions only: two looks with the same key share one skeleton shape.
function lookKey(look) {
  const b = look.body;
  return `hero:${look.race}:${look.gender}:${b.build}:${b.heightUnits.toFixed(1)}:${b.head.toFixed(2)}`;
}

// What a watcher would notice at a glance, in the same vocabulary the host's
// salience module uses. The host is the authority for what the world reacts
// to; the client uses this only for the designer's "how you read" preview.
export function lookNotice(look) {
  const tags = [];
  if (look.headgear === 'full-helm') tags.push('enclosed helm');
  else if (look.headgear === 'hood') tags.push('hooded');
  else if (look.headgear === 'circlet') tags.push('circlet');
  if (look.torso === 'plate') tags.push('plate armour');
  else if (look.torso === 'chain') tags.push('mail');
  else if (look.torso === 'robe') tags.push('robed');
  if (look.main.fx.length) tags.push(`${look.main.fx[0]} weapon`);
  if (['artifact', 'blessed'].includes(look.rarity)) tags.push('relic-bright');
  if (look.marks !== 'none') tags.push(look.marks.replace('-', ' '));
  if (look.hairStyle !== 'shaved' && !['full-helm', 'hood'].includes(look.headgear)) {
    const l = look.palette.hair;
    if (/^#[89ab]/.test(l) && parseInt(l.slice(3, 5), 16) < 0x60) tags.push('red hair');
  }
  if (look.offhand === 'lantern') tags.push('lantern-bearer');
  if (look.cloak !== 'none') tags.push('cloaked');
  return tags.slice(0, 6);
}
