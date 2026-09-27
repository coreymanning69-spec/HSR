// Actor Lab: a large, controllable view of the game's rigs for tuning art,
// poses and frame time. It builds actors through the same dollModel() the
// game uses, so what it shows is what combat draws. No run is touched; the
// only host call is the read-only character_options catalog.

import {SkeletalRig} from './skeletal-rig.js';
import {dollModel} from './paperdoll.js';
import {actorRig} from './sprite-renderer.js';
import {FXEngine} from './fx-engine.js';
import {actorStats, hash32} from './actor-core.js';
import {actorLook, lookNotice} from './actor-look.js';
import {heroBurst} from './hero-rig.js';
import {castingProfile} from './magic-articulation.js';
import {VIEW} from './rig-body.js';

const $ = id => document.getElementById(id);
const canvas = $('stage'), ctx = canvas.getContext('2d');
const fx = new FXEngine({maxParticles: 400});
const POSES = ['idle', 'combat', 'battleIdle', 'ready', 'staffLow', 'staffPoint', 'travel', 'run', 'jump', 'climb', 'kneel', 'victory', 'down', 'point', 'wave', 'cheer', 'crossed', 'salute', 'look', 'study', 'defend'];
$('pose').innerHTML = POSES.map(p => `<option>${p}</option>`).join('');
$('pose').value = 'combat';

let catalog = null;
const look = {race: 'human', gender: 'female', appearance: {}};
const fallbackCatalog = {races: ['human', 'elf', 'half-elf', 'orc', 'goblin'].map(id => ({id, name: id})), appearance: {fields: {}}};

async function loadCatalog() {
  try {
    const reply = await fetch('/api/host', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id: 'lab', command: 'character_options'})});
    const payload = await reply.json();
    catalog = payload?.result || fallbackCatalog;
  } catch { catalog = fallbackCatalog; }
  $('race').innerHTML = catalog.races.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
  buildAppearance();
}

// One select per appearance field, plus a free colour picker on colour fields.
function buildAppearance() {
  const fields = catalog.appearance?.fields || {};
  const host = $('appearance'); host.innerHTML = '';
  for (const [field, spec] of Object.entries(fields)) {
    const options = (spec.options || []).filter(o => !o.races || o.races.includes(look.race));
    const row = document.createElement('label');
    row.innerHTML = `${spec.label || field}<select data-field="${field}">${options.map(o => `<option value="${o.id}">${o.name}</option>`).join('')}</select>`;
    const colour = options.some(o => o.hex);
    const picker = document.createElement(colour ? 'input' : 'span');
    if (colour) { picker.type = 'color'; picker.dataset.colour = field; picker.value = options[0].hex; }
    row.append(picker); host.append(row);
    const select = row.querySelector('select');
    const current = look.appearance[field];
    if (current && options.some(o => o.id === current.id)) select.value = current.id;
    else look.appearance[field] = {...options[0]};
    if (colour) picker.value = look.appearance[field].hex || options[0].hex;
    select.addEventListener('change', () => { const o = options.find(x => x.id === select.value); look.appearance[field] = {...o}; if (colour && o.hex) picker.value = o.hex; rebuild(); });
    if (colour) picker.addEventListener('input', () => { look.appearance[field] = {id: 'custom', name: 'Custom', hex: picker.value}; rebuild(); });
  }
  rebuild();
}

function equipment() {
  const rows = [];
  const weapon = $('weapon').value, fxToken = $('fx').value, rarity = $('rarity').value;
  if (weapon !== 'none') rows.push({presentation: {silhouette: weapon, material: $('material').value, rarity, fx: [fxToken, rarity === 'artifact' || rarity === 'blessed' ? 'glow' : ''].filter(Boolean),
    handedness: ['bow', 'staff', 'polearm'].includes(weapon) ? 'two-handed' : $('handedness').value}});
  if ($('second').value) rows.push({presentation: {silhouette: $('second').value, material: 'steel', rarity: 'mundane', fx: [], handedness: 'one-handed'}});
  if ($('armor').value) rows.push({presentation: {silhouette: 'armor', material: $('armor').value, rarity: 'mundane', fx: []}});
  if ($('helm').value) rows.push({presentation: {silhouette: 'helm', material: 'steel', coverage: $('helm').value, rarity: 'mundane', fx: []}});
  if ($('shield').value) rows.push({presentation: {silhouette: 'shield', material: 'steel', rarity: 'mundane', fx: [], handedness: 'off-hand'}});
  return rows;
}

// Actors on the stage.
let actors = [];
function makeActor(item, {x = .5, facing = 1, pose = null, scale = 1} = {}) {
  const model = dollModel(item, {pose: 'combat'});
  return {item, model, rig: new SkeletalRig(), def: actorRig(model), x, facing, pose, scale, beat: '', beatUntil: 0, alive: true, casting: null,
    kick: 0, walk: null, sockets: null};
}
function mainItem() {
  const id = $('rig').value;
  if (id === 'wren') return {id: 'p1', name: 'Wren', identity: 'wren', alive: true, loadout: $('wrenLoadout').value};
  if (id === 'doran') return {id: 'p0', name: 'Doran', identity: 'doran', alive: true, loadout: $('doranLoadout').value};
  return {id: id === 'npc' ? 'lab-foe' : 'lab-hero', name: id === 'npc' ? 'Lab Foe' : 'Lab Hero',
    race_id: look.race, gender: look.gender, appearance: structuredClone(look.appearance), equipment: equipment(), hp: 10};
}
function randomItem(seed) {
  const pick = (list, salt) => list[(hash32(seed + salt)) % list.length];
  const fields = catalog?.appearance?.fields || {};
  const race = pick(['human', 'human', 'elf', 'half-elf', 'orc', 'goblin'], 'r');
  const appearance = {};
  for (const [field, spec] of Object.entries(fields)) {
    const options = (spec.options || []).filter(o => !o.races || o.races.includes(race));
    if (options.length) appearance[field] = {...pick(options, field)};
  }
  const weapon = pick(['sword', 'axe', 'mace', 'dagger', 'polearm', 'staff', 'wand', 'bow', 'sword'], 'w');
  const eq = [{presentation: {silhouette: weapon, material: pick(['steel', 'steel', 'iron', 'silver', 'bronze', 'obsidian'], 'm'), rarity: pick(['mundane', 'mundane', 'magical', 'artifact'], 'q'),
    fx: [pick(['', '', 'ember', 'frost', 'radiant', 'wither', 'arcane', 'gale'], 'f')].filter(Boolean), handedness: pick(['one-handed', 'one-handed', 'two-handed'], 'h')}}];
  const armor = pick(['', 'plate', 'chain', 'leather', 'robe', ''], 'a');
  if (armor) eq.push({presentation: {silhouette: 'armor', material: armor}});
  if (pick([0, 0, 1], 'hm')) eq.push({presentation: {silhouette: 'helm', coverage: pick(['partial', 'full'], 'hc')}});
  if (['sword', 'axe', 'mace'].includes(weapon) && pick([0, 1], 's')) eq.push({presentation: {silhouette: 'shield', material: 'steel'}});
  return {id: `crowd-${seed}`, name: `Crowd ${seed}`, race_id: race, gender: pick(['female', 'male', 'other'], 'g'), appearance, equipment: eq, hp: 10};
}

let mode = 'single';
function rebuild() {
  sheet = null;
  const keep = actors[0];
  if (mode === 'crowd') {
    actors = Array.from({length: 10}, (_, i) => makeActor(i === 0 ? mainItem() : randomItem(String(i * 7919)), {x: .07 + i * .095, facing: i % 2 ? -1 : 1, scale: .42}));
  } else if (mode === 'compare') {
    const items = [{id: 'p0', name: 'Doran', identity: 'doran'}, {id: 'p1', name: 'Wren', identity: 'wren'}, mainItem(), randomItem('orc-7'), randomItem('gob-3')];
    items[3].race_id = 'orc'; items[4].race_id = 'goblin';
    actors = items.map((item, i) => makeActor(item, {x: .12 + i * .19, facing: 1, scale: .62}));
  } else {
    actors = [makeActor(mainItem(), {x: .38, facing: Number($('facing').value)}), makeActor(randomItem('dummy'), {x: .78, facing: -1, scale: .9})];
  }
  if (keep && actors[0]) {
    actors[0].rig = keep.def === actors[0].def ? keep.rig : actors[0].rig;
    if (keep.turn) actors[0].turn = keep.turn;
  }
  const main = actors[0];
  if (main?.def?.identity === 'hero') $('notice-tags').innerHTML = lookNotice(actorLook(main.model)).map(t => `<span>${t}</span>`).join('');
  else $('notice-tags').innerHTML = '';
}

// ---------------------------------------------------------------------------
// Beats, played the way the combat director plays them.
const wait = ms => new Promise(r => setTimeout(r, ms));
function socketOf(actor, name) { const s = actor.sockets?.[name] || actor.sockets?.chest; return s ? {x: s.x, y: s.y} : {x: 0, y: 0}; }
function setBeat(actor, beat, ms = 0) { actor.beat = beat; actor.beatUntil = ms ? performance.now() + ms : 0; }
async function play(kind) {
  const actor = actors[0], target = actors[1] || actors[0];
  if (!actor) return;
  const element = $('element').value;
  if (kind === 'clear') { setBeat(actor, ''); actor.casting = null; return; }
  if (kind === 'channel' || kind === 'release') {
    actor.casting = selectedCasting();
    setBeat(actor, kind === 'channel' ? 'cast_channel' : 'cast_release');
    return;
  }
  if (kind === 'attack') {
    const heavy = actor.def.identity === 'doran';
    setBeat(actor, 'windup'); await wait(heavy ? 310 : 150);
    setBeat(actor, 'strike'); await wait(heavy ? 150 : 70);
    impact(target, 'hit', 'slashing'); await wait(260);
    setBeat(actor, ''); return;
  }
  if (kind === 'cast') {
    actor.casting = selectedCasting();
    setBeat(actor, 'cast_channel');
    const focus = () => socketOf(actor, 'focus');
    fx.setAura('lab-focus', {socket: 'focus', auraType: element, radius: 14, durationMs: 700});
    await wait(420);
    setBeat(actor, 'cast_release'); await wait(90);
    const from = focus(), to = socketOf(target, 'chest');
    if (target !== actor) { fx.spawnProjectile({fromX: from.x, fromY: from.y, toX: to.x, toY: to.y, damageType: element, archetype: actor.casting.delivery, impactOnHit: false, durationMs: 380}); await wait(380); }
    impact(target, 'hit', element); await wait(300);
    setBeat(actor, ''); actor.casting = null; return;
  }
  if (kind === 'knock') { knock(actor, 1100); setBeat(actor, 'crit', 320); return; }
  if (kind === 'death') { actor.pose = 'death'; await wait(720); actor.pose = 'down'; actor.alive = false; return; }
  if (kind === 'walk') { actor.walk = {from: actor.x, to: actor.x > .5 ? .15 : .7, at: performance.now(), ms: 1600}; actor.facing = actor.walk.to > actor.x ? 1 : -1; return; }
  setBeat(actor, kind, kind === 'guard' ? 520 : 340);
}
function selectedCasting() {
  return castingProfile({type: $('source').value === 'implement' ? 'staff_cast' : 'cast',
    presentation: {casting: {stance: $('stance').value, hands: Number($('hands').value), source: $('source').value, element: $('element').value}},
    damage_type: $('element').value});
}
function knock(actor, power) { actor.kick = -actor.facing * power; actor.rig.motion?.impulse(actor.kick * .9); }
function impact(target, outcome, damageType) {
  const p = socketOf(target, 'chest');
  fx.spawnImpact(p.x, p.y, damageType === 'slashing' ? 'default' : damageType, {radius: 34, count: 22});
  heroBurst(target.rig, damageType, p.x, p.y);
  setBeat(target, outcome, 320); knock(target, outcome === 'crit' ? 900 : 520);
}

// ---------------------------------------------------------------------------
// Skeleton overlay: spine, shoulder line and both arms (near = red, far = blue), so
// shoulder placement, elbow side and hand targets can be judged against the art.
function drawBones(c, rig) {
  const B = n => rig.bones.get(n); if (!B('torso') || B('torso').worldX == null) return;
  const dot = (x, y, r, col) => { c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fillStyle = col; c.fill(); };
  const seg = (x1, y1, x2, y2, col, w) => { c.beginPath(); c.moveTo(x1, y1); c.lineTo(x2, y2); c.strokeStyle = col; c.lineWidth = w; c.stroke(); };
  const k = Math.max(.5, rig.scale / 3.4);
  c.save();
  const chain = ['pelvis', 'spine', 'torso', 'neck', 'head'].map(B);
  c.beginPath(); chain.forEach((b, i) => i ? c.lineTo(b.worldX, b.worldY) : c.moveTo(b.worldX, b.worldY)); c.strokeStyle = 'rgba(255,255,255,.75)'; c.lineWidth = 1.4 * k; c.stroke();
  for (const b of chain) dot(b.worldX, b.worldY, 2.2 * k, '#fff');
  const ls = B('left_shoulder'), rs = B('right_shoulder'); seg(ls.worldX, ls.worldY, rs.worldX, rs.worldY, 'rgba(255,224,122,.9)', 1.2 * k);
  for (const side of ['left', 'right']) {
    const col = side === 'right' ? '#ff5050' : '#4da8ff', sh = B(side + '_shoulder'), ua = B(side + '_upper_arm'), la = B(side + '_lower_arm');
    seg(ua.worldX, ua.worldY, ua.tipX, ua.tipY, col, 1.6 * k); seg(la.worldX, la.worldY, la.tipX, la.tipY, col, 1.6 * k);
    dot(sh.worldX, sh.worldY, 3.4 * k, col); dot(ua.tipX, ua.tipY, 2.8 * k, col); dot(la.tipX, la.tipY, 2.8 * k, col);
  }
  c.restore();
}

// ---------------------------------------------------------------------------
// Pose sheet: the current look settled into every pose and beat, in a grid.
const SHEET = [['idle', ''], ['combat', ''], ['combat', 'windup'], ['combat', 'strike'], ['combat', 'strike+'], ['combat', 'guard'],
  ['combat', 'hit'], ['combat', 'crit'], ['combat', 'dodge'], ['combat', 'cast_channel'], ['combat', 'cast_release'], ['run', ''],
  ['jump', ''], ['kneel', ''], ['victory', ''], ['down', ''], ['point', ''], ['wave', ''], ['cheer', ''], ['crossed', ''], ['study', ''], ['climb', '']];
let sheet = null;
function renderSheet(w, h) {
  const item = mainItem(), model = dollModel(item, {pose: 'combat'}), def = actorRig(model);
  const cols = 6, rows = Math.ceil(SHEET.length / cols), cw = w / cols, chh = h / rows;
  const off = document.createElement('canvas'), dpr = Math.min(2, devicePixelRatio || 1);
  off.width = Math.round(w * dpr); off.height = Math.round(h * dpr);
  const c = off.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0); c.fillStyle = '#121826'; c.fillRect(0, 0, w, h);
  const casting = selectedCasting();
  SHEET.forEach(([pose, beat], i) => {
    const x = (i % cols) * cw, y = Math.floor(i / cols) * chh, floor = y + chh * .9;
    c.fillStyle = i % 2 ? '#1a2133' : '#1d2538'; c.fillRect(x, y, cw, chh);
    c.strokeStyle = 'rgba(217,181,110,.2)'; c.beginPath(); c.moveTo(x, floor + .5); c.lineTo(x + cw, floor + .5); c.stroke();
    const rig = new SkeletalRig(); rig.scale = Math.min(cw / 60, chh / 125);
    const live = pose === 'run' || beat === 'strike+';
    let now = 10000;
    const frames = beat === 'strike' ? 4 : beat === 'strike+' ? 12 : live ? 26 : 3;
    for (let f = 0; f < frames; f++) {
      now += 16;
      const paint = f === frames - 1;
      def.draw(paint ? c : ctx, rig, {...model, alive: pose !== 'down'}, {x: x + cw * .45, y: floor, facing: 1, dt: 16, now, pose, beat: beat.replace('+', ''),
        casting, reducedMotion: !live, idleFidgets: false, paint});
    }
    if (showBones) drawBones(c, rig);
    c.fillStyle = 'rgba(232,225,207,.75)'; c.font = '11px system-ui'; c.fillText(beat ? beat.replace('+', ' (follow)') : pose, x + 6, y + 14);
  });
  return off;
}

// ---------------------------------------------------------------------------
// Frame loop.
let last = performance.now(), fps = 60, frameMs = 0, showSockets = false, showBones = false;
function resize() {
  const dpr = Math.min(2, devicePixelRatio || 1), r = canvas.getBoundingClientRect();
  canvas.width = Math.round(r.width * dpr); canvas.height = Math.round(r.height * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
addEventListener('resize', resize);
function backdrop(w, h, floor) {
  const sky = ctx.createLinearGradient(0, 0, 0, floor);
  sky.addColorStop(0, '#1a2338'); sky.addColorStop(1, '#2c3650'); ctx.fillStyle = sky; ctx.fillRect(0, 0, w, floor);
  ctx.fillStyle = '#1b2130'; ctx.fillRect(0, floor, w, h - floor);
  ctx.strokeStyle = 'rgba(217,181,110,.25)'; ctx.beginPath(); ctx.moveTo(0, floor + .5); ctx.lineTo(w, floor + .5); ctx.stroke();
  // Height marks every foot at the current zoom (5 ft and 7 ft highlighted).
  const unit = 97 / (68 / 12) * Number($('zoom').value) * (mode === 'single' ? 1 : actors[0]?.scale || 1);
  ctx.fillStyle = 'rgba(154,163,183,.5)'; ctx.font = '10px ui-monospace, monospace';
  for (let ft = 1; ft <= 8; ft++) { const y = floor - ft * unit; if (y < 0) break; ctx.fillStyle = ft === 5 || ft === 7 ? 'rgba(217,181,110,.55)' : 'rgba(154,163,183,.35)'; ctx.fillRect(0, y, 10, 1); ctx.fillText(`${ft}ft`, 12, y + 3); }
}
function tick(now) {
  const dt = Math.min(64, now - last); last = now; fps += (1000 / Math.max(1, dt) - fps) * .05;
  const w = canvas.clientWidth, h = canvas.clientHeight, floor = h * .86, zoom = Number($('zoom').value);
  const t0 = performance.now(); actorStats.paintMs = 0; actorStats.paints = 0;
  if (mode === 'sheet') {
    if (!sheet || sheet.w !== w || sheet.h !== h) sheet = {w, h, img: renderSheet(w, h)};
    ctx.drawImage(sheet.img, 0, 0, w, h);
    $('hud').textContent = 'pose sheet';
    requestAnimationFrame(tick); return;
  }
  backdrop(w, h, floor);
  const reduced = $('motion').value === 'reduced';
  for (const a of actors) {
    if (a.beatUntil && now > a.beatUntil) { a.beat = ''; a.beatUntil = 0; }
    if (a.walk) {
      const k = Math.min(1, (now - a.walk.at) / a.walk.ms); a.x = a.walk.from + (a.walk.to - a.walk.from) * k;
      if (k >= 1) a.walk = null;
    }
    a.kick *= Math.exp(-dt / 140);
    let turnP = 0;
    if (a.turn) {
      turnP = Math.min(1, (now - a.turn.at) / a.turn.ms);
      if (turnP >= 0.5 && a.facing !== a.turn.to) a.facing = a.turn.to;
      if (turnP >= 1) a.turn = null;
    }
    const x = a.x * w + a.kick * .06, scale = zoom * a.scale;
    a.rig.scale = scale;
    const pose = a.pose || (a === actors[0] && mode === 'single' ? $('pose').value : a.walk ? 'run' : 'combat');
    const model = a.alive ? a.model : {...a.model, alive: false};
    const drawStart = performance.now();
    const flipW = turnP > 0 ? Math.sqrt(Math.cos(Math.PI * turnP) ** 2 + 0.14 * Math.sin(Math.PI * turnP) ** 2) : 1;
    if (turnP > 0) { ctx.save(); ctx.translate(x, 0); ctx.scale(flipW, 1); ctx.translate(-x, 0); }
    a.sockets = a.def.draw(ctx, a.rig, model, {x, y: floor, facing: a.facing, dt: reduced ? 0 : dt, now, pose: a.walk ? 'run' : pose,
      beat: a.beat, casting: a.casting, reducedMotion: reduced, idleFidgets: true, screenX: x, screenY: floor, turnProgress: turnP});
    if (turnP > 0) ctx.restore();
    if (showBones) drawBones(ctx, a.rig);
    actorStats.paintMs += performance.now() - drawStart; actorStats.paints++;
    if (showSockets && a.sockets) for (const [name, p] of Object.entries(a.sockets)) {
      ctx.fillStyle = name === 'focus' ? '#ff5edb' : name === 'weapon_tip' ? '#5effc0' : '#ffe07a';
      ctx.beginPath(); ctx.arc(p.x, p.y, 3, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(255,255,255,.7)'; ctx.font = '9px ui-monospace, monospace'; ctx.fillText(name, p.x + 5, p.y - 4);
    }
  }
  fx.update(dt, (id, socket) => id === 'lab-focus' ? socketOf(actors[0], socket) : null);
  fx.draw(ctx, (id, socket) => id === 'lab-focus' ? socketOf(actors[0], socket) : null);
  frameMs += (performance.now() - t0 - frameMs) * .1;
  $('hud').textContent = `fps ${fps.toFixed(0)}   frame ${frameMs.toFixed(2)} ms\nactors ${actors.length}   paint/actor ${(actorStats.paintMs / Math.max(1, actorStats.paints)).toFixed(2)} ms`;
  requestAnimationFrame(tick);
}

// ---------------------------------------------------------------------------
// Wiring.
for (const id of ['weapon', 'handedness', 'material', 'fx', 'rarity', 'armor', 'helm', 'shield', 'second', 'rig', 'doranLoadout', 'wrenLoadout']) $(id).addEventListener('change', rebuild);
$('facing').addEventListener('change', () => {
  const next = Number($('facing').value);
  if (actors[0] && actors[0].facing !== next) actors[0].turn = {from: actors[0].facing, to: next, at: performance.now(), ms: 180};
  rebuild();
});
$('race').addEventListener('change', () => { look.race = $('race').value; buildAppearance(); });
$('gender').addEventListener('change', () => { look.gender = $('gender').value; rebuild(); });
$('pose').addEventListener('change', () => { if (actors[0]) { actors[0].pose = null; actors[0].alive = true; } });
document.querySelectorAll('[data-beat]').forEach(b => b.addEventListener('click', () => { if (actors[0]) { actors[0].alive = true; if (b.dataset.beat !== 'death') actors[0].pose = null; } play(b.dataset.beat); }));
const toggle = (id, fn) => $(id).addEventListener('click', () => { const on = $(id).getAttribute('aria-pressed') !== 'true'; $(id).setAttribute('aria-pressed', String(on)); fn(on); });
toggle('sockets', on => { showSockets = on; });
toggle('bones', on => { showBones = on; sheet = null; });
$('yaw').addEventListener('input', () => { VIEW.yaw = Number($('yaw').value); $('yawv').textContent = VIEW.yaw.toFixed(2); sheet = null; });
toggle('compare', on => { mode = on ? 'compare' : 'single'; $('crowd').setAttribute('aria-pressed', 'false'); rebuild(); });
toggle('crowd', on => { mode = on ? 'crowd' : 'single'; $('compare').setAttribute('aria-pressed', 'false'); rebuild(); });
toggle('sheetBtn', on => { mode = on ? 'sheet' : 'single'; rebuild(); });
for (const id of ['stance', 'hands', 'source', 'element']) $(id).addEventListener('change', () => {
  sheet = null;
  if (actors[0]?.beat?.startsWith('cast_')) actors[0].casting = selectedCasting();
});
$('random').addEventListener('click', () => {
  const item = randomItem(String(Math.floor(Math.random() * 1e6)));
  look.race = item.race_id; look.gender = item.gender; look.appearance = item.appearance;
  $('race').value = look.race; $('gender').value = look.gender; buildAppearance();
});
// Crowd mode keeps everyone busy so the frame time is honest.
setInterval(() => {
  if (mode !== 'crowd') return;
  const a = actors[1 + Math.floor(Math.random() * (actors.length - 1))]; if (!a) return;
  const beat = ['windup', 'strike', 'hit', 'cast_channel', 'dodge'][Math.floor(Math.random() * 5)];
  setBeat(a, beat, 360);
}, 180);

resize(); loadCatalog(); requestAnimationFrame(tick);
window.lab = {actors: () => actors, play, rebuild, look, stats: actorStats};
