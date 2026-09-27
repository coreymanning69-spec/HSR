// Actor Toolbox: a playable bench for the main display's actors.
//
// The same stage the room scene runs (stage-view.js), with no run behind it:
// spawn any rig, walk it, turn it, change its size and how it carries its
// weapon, swing at dummies, props and other actors, watch the damage land, open
// doors, change the set and the hour, and see every hit box. What it shows is
// what the room scene does, because it is the same code. Nothing here touches
// a run or the host; a run's outcomes stay the host's.
import {createStage} from './stage-view.js';
import {THEME_IDS, THEMES} from './stage-set.js';
import {SWING_STYLES, SWING_ORDER, PROP_TYPES, SIZE_CLASSES, FIXTURES, bodyOf} from './stage-world.js';
import {hash32} from './actor-core.js';

const TODS = ['morning', 'day', 'evening', 'night'];
const row = (silhouette, extra = {}) => ({presentation: {silhouette, material: 'steel', rarity: 'mundane', fx: [], handedness: 'one-handed', ...extra}});
const RACES = ['human', 'elf', 'half-elf', 'orc', 'goblin'];
const WEAPONS = ['none', 'cleaver', 'daggers', 'sword', 'dagger', 'axe', 'mace', 'polearm', 'staff', 'wand', 'bow'];
const ARMORS = ['', 'leather', 'chain', 'plate', 'robe'];
// Presets: what Spawn can put on the floor. `weapon` is the drawn implement.
const PRESETS = {
  doran: {label: 'Doran (Champion, 7\'0" Cleaver)', make: () => ({item: {identity: 'doran', name: 'Doran', is_champion: true, hp: 90, max_hp: 90}, weapon: 'cleaver', team: 'party'})},
  wren: {label: 'Wren (Champion)', make: () => ({item: {identity: 'wren', name: 'Wren', is_champion: true, hp: 50, max_hp: 50}, weapon: 'staff', team: 'party'})},
  hero: {label: 'Hero (random look)', make: seed => hero(seed, {weapon: 'sword', armor: 'chain'})},
  townsperson: {label: 'Townsperson', make: seed => ({...hero(seed, {weapon: 'none', armor: ''}), ambient: true, name: 'Townsperson'})},
  guard: {label: 'Town guard', make: seed => ({...hero(seed, {weapon: 'polearm', armor: 'chain'}), name: 'Town guard', team: 'foe'})},
  goblin: {label: 'Goblin (small)', make: seed => ({...hero(seed, {race: 'goblin', weapon: 'dagger', armor: 'leather'}), size: 'small', name: 'Goblin', team: 'foe'})},
  ogre: {label: 'Ogre (large)', make: seed => ({...hero(seed, {race: 'orc', weapon: 'mace', armor: 'leather'}), size: 'large', name: 'Ogre', team: 'foe'})},
  giant: {label: 'Hill Giant (huge)', make: seed => ({...hero(seed, {race: 'orc', weapon: 'polearm', armor: 'leather'}), size: 'huge', name: 'Hill Giant', team: 'foe'})},
  castellan: {label: 'Brass Castellan (large)', make: seed => ({...hero(seed, {race: 'human', weapon: 'mace', armor: 'plate'}), size: 'large', name: 'Brass Castellan', team: 'foe'})},
};
function pick(list, seed, salt) { return list[hash32(`${seed}:${salt}`) % list.length]; }
function hero(seed, {race, weapon = 'sword', armor = ''} = {}) {
  const r = race || pick(['human', 'human', 'elf', 'half-elf', 'orc'], seed, 'race');
  const equipment = [];
  if (weapon !== 'none') equipment.push(row(weapon, {handedness: ['bow', 'staff', 'polearm'].includes(weapon) ? 'two-handed' : 'one-handed'}));
  if (armor) equipment.push(row('armor', {material: armor}));
  const item = {name: 'Adventurer', race_id: r, gender: pick(['female', 'male', 'other'], seed, 'g'), equipment, hp: 40, max_hp: 40};
  return {item, weapon, team: 'npc'};
}

export function createToolbox({reducedMotion = () => false, onClose = null, standalone = false} = {}) {
  const el = document.createElement('div'); el.className = 'toolbox'; el.dataset.toolbox = '';
  const props = Object.keys(PROP_TYPES).filter(k => !FIXTURES.has(k) || ['statue', 'pillar'].includes(k)).slice(0, 12);
  el.innerHTML = `<div class="toolbox-main">
      <div class="toolbox-head"><h2>Actor Toolbox</h2><p>Simulation Mode · the room scene's own stage, with nothing behind it.</p>${onClose ? '<button type="button" class="action secondary toolbox-close" data-tb="close">Back</button>' : ''}</div>
      <div data-tb-stage style="min-height:0"></div>
      <div class="toolbox-foot"><span><kbd>click</kbd> ground walks · <kbd>shift</kbd>/<kbd>double-click</kbd> runs</span><span><kbd>W A S D</kbd> move the selected actor</span><span><kbd>F</kbd>/<kbd>Space</kbd> swing</span><span><kbd>click</kbd> an actor or prop selects it</span></div>
    </div>
    <aside class="toolbox-panel" aria-label="Actor Toolbox controls">
      <section class="tb-sec"><h3>Set</h3><div class="tb-row"><label>Place<select data-tb="theme">${THEME_IDS.map(id => `<option value="${id}">${THEMES[id].name}</option>`).join('')}</select></label>
        <label>Hour<select data-tb="tod">${TODS.map(t => `<option>${t}</option>`).join('')}</select></label></div>
        <div class="tb-row" data-tb="doors"></div></section>
      <section class="tb-sec"><h3>Actor</h3><div class="tb-row"><label>Spawn<select data-tb="preset">${Object.entries(PRESETS).map(([k, v]) => `<option value="${k}">${v.label}</option>`).join('')}</select></label><button type="button" class="tb-btn" data-tb="spawn">Spawn</button></div>
        <div class="tb-row"><label>Selected<select data-tb="selected"></select></label></div>
        <div class="tb-row"><label>Carry<select data-tb="carry"><option value="auto">Auto (place decides)</option><option value="stowed">Stowed on back</option><option value="shoulder">On the shoulder</option><option value="ready">Held out front</option></select></label>
          <label>Weapon<select data-tb="weapon">${WEAPONS.map(w => `<option>${w}</option>`).join('')}</select></label></div>
        <div class="tb-row"><label>Armor<select data-tb="armor">${ARMORS.map(a => `<option value="${a}">${a || 'none'}</option>`).join('')}</select></label><label>Race<select data-tb="race">${RACES.map(r => `<option>${r}</option>`).join('')}</select></label></div>
        <div class="tb-row"><label>Size <span data-tb="scale-read">1.00×</span><input type="range" data-tb="scale" min="0.5" max="3.2" step="0.05" value="1"></label></div>
        <div class="tb-row"><button type="button" class="tb-btn" data-tb="rebuild">Apply look</button><button type="button" class="tb-btn" data-tb="heal">Heal</button><button type="button" class="tb-btn" data-tb="down">Strike down</button><button type="button" class="tb-btn" data-tb="remove">Remove</button></div></section>
      <section class="tb-sec"><h3>Swing</h3><div class="tb-row">${SWING_ORDER.map(s => `<button type="button" class="tb-btn wide" data-swing="${s}" title="${SWING_STYLES[s].label}">${SWING_STYLES[s].label}</button>`).join('')}<button type="button" class="tb-btn wide" data-tb="combo">Combo ×4</button></div>
        <div class="tb-row"><button type="button" class="tb-btn wide" data-tb="approach">Walk up &amp; swing</button><button type="button" class="tb-btn wide" data-tb="face">Turn around</button></div></section>
      <section class="tb-sec"><h3>Targets</h3><div class="tb-row">${props.map(k => `<button type="button" class="tb-btn" data-prop="${k}">${PROP_TYPES[k].name}</button>`).join('')}</div>
        <div class="tb-row"><button type="button" class="tb-btn wide" data-tb="reset">Heal everything</button><button type="button" class="tb-btn wide" data-tb="clear">Clear floor</button></div></section>
      <section class="tb-sec"><h3>Display</h3><div class="tb-row"><button type="button" class="tb-btn" data-tb="boxes" aria-pressed="false">Show hit boxes</button><a class="tb-btn" href="actor-lab.html" target="_blank" rel="noopener">Pose sheet (Actor Lab)</a></div></section>
      <section class="tb-sec"><h3>Readout</h3><pre class="tb-read" data-tb="read" aria-live="off"></pre><pre class="tb-log" data-tb="log" aria-live="off"></pre></section>
    </aside>`;
  const $ = k => el.querySelector(`[data-tb="${k}"]`);
  const stage = createStage({mode: 'toolbox', reducedMotion, follow: false, onPick: rec => select(rec.id), onSelect: id => select(id)});
  el.querySelector('[data-tb-stage]').append(stage.el);
  let selected = null, counter = 0, timer = 0;
  const themeSel = $('theme'), todSel = $('tod'), logEl = $('log'), readEl = $('read');
  const seedOf = () => `tb${++counter}-${Math.random().toString(36).slice(2, 6)}`;
  const log = text => { logEl.textContent = (text + '\n' + logEl.textContent).split('\n').slice(0, 9).join('\n'); };
  const EXITS = [['a', {id: 'tavern'}], ['b', {id: 'guardhouse'}], ['c', {id: 'alley'}]];
  function applyRoom() {
    stage.setRoom({themeId: themeSel.value, tod: todSel.value, roomId: `toolbox:${themeSel.value}`, exits: EXITS, name: `Actor Toolbox · ${THEMES[themeSel.value].name}`, sub: 'Simulation Mode'});
    $('doors').innerHTML = EXITS.map(([k]) => `<button type="button" class="tb-btn" data-door="${k}">Door ${k.toUpperCase()}: open / close</button>`).join('');
  }
  function refreshSelect() {
    const sel = $('selected'), actors = stage.things().filter(r => r.kind === 'actor');
    sel.innerHTML = actors.map(r => `<option value="${r.id}">${r.ent.name || r.id}${r.ent.alive ? '' : ' (down)'}</option>`).join('');
    if (selected && stage.thing(selected)) sel.value = selected;
  }
  function select(id) {
    const rec = stage.thing(id); if (!rec) return; selected = id;
    if (rec.kind === 'actor') { stage.setLead(id); $('carry').value = rec.carryOverride || 'auto'; $('scale').value = String(rec.ent.body.vis); $('scale-read').textContent = `${Number(rec.ent.body.vis).toFixed(2)}×`; const item = rec.item; $('weapon').value = rec.ent.weapon; $('race').value = item.race_id || 'human'; }
    refreshSelect();
  }
  function spawn(key, spec = {}) {
    const preset = PRESETS[key] || PRESETS.hero, seed = spec.seed || seedOf(), made = preset.make(seed), w = stage.st.worldW;
    const id = spec.id || `${key}-${seed}`;
    const x = spec.x ?? w * (.2 + (stage.things().filter(r => r.kind === 'actor').length % 5) * .13), d = spec.d ?? .4;
    const rec = stage.spawnActor({id, item: made.item, weapon: made.weapon, team: made.team || 'npc', x, d, face: 1, role: 'toolbox', name: made.name || made.item.name, scale: made.size ? SIZE_CLASSES[made.size] : undefined, cuttable: true,
      hp: made.item.hp, max: made.item.max_hp, ambient: made.ambient ? {type: 'wander', home: {x, d}, leash: 3.4} : null, select: spec.select});
    refreshSelect(); return rec;
  }
  const selRec = () => (selected && stage.thing(selected)) || stage.lead();
  const swingSel = async style => { const r = selRec(); if (r) stage.swing(r.id, style); };
  const nearestTarget = r => stage.things().filter(t => t !== r && !t.ent.broken && t.ent.cuttable !== false && (t.kind === 'prop' || t.ent.alive)).sort((a, b) => Math.abs(a.ent.x - r.ent.x) - Math.abs(b.ent.x - r.ent.x))[0];

  themeSel.value = 'arena'; todSel.value = 'day'; applyRoom();
  themeSel.onchange = todSel.onchange = () => { applyRoom(); };
  stage.on('hit', ev => log(`${ev.attacker || '·'} → ${ev.target}: ${ev.damage}${ev.crit ? ' CRIT' : ''} ${ev.material} (${Math.max(0, ev.hp)}/${ev.max})${ev.killed ? ' ✝' : ''}`));
  stage.on('break', ev => log(`${ev.id} breaks`));
  stage.on('death', ev => { log(`${ev.id} falls`); refreshSelect(); });
  el.addEventListener('click', async e => {
    const b = e.target.closest('button,a'); if (!b) return; const d = b.dataset, rec = selRec();
    if (d.swing) swingSel(d.swing);
    else if (d.prop) stage.spawnProp(d.prop, {x: stage.st.worldW * (.42 + Math.random() * .4), d: .25 + Math.random() * .5});
    else if (d.door) stage.toggleDoor(d.door);
    else if (d.tb === 'close') onClose?.();
    else if (d.tb === 'spawn') select(spawn($('preset').value).id);
    else if (d.tb === 'combo') { if (rec) for (let i = 0; i < 4; i++) { stage.swing(rec.id, SWING_ORDER[i]); await new Promise(r => setTimeout(r, i ? 90 : 20)); } }
    else if (d.tb === 'approach' && rec) { const t = nearestTarget(rec); if (t) { const w = stage.world, side = rec.ent.x < t.ent.x ? -1 : 1; w.walkTo(rec.id, t.ent.x + side * (t.ent.body.width / 2 + rec.ent.body.reach * .62), t.ent.d, {arrive: .3, then: () => { w.faceEntity(rec.ent, t.ent); setTimeout(() => stage.swing(rec.id), 220); }}); } }
    else if (d.tb === 'face' && rec) stage.world.faceDir(rec.ent, -rec.ent.face);
    else if (d.tb === 'heal' && rec) { stage.heal(rec.id); refreshSelect(); }
    else if (d.tb === 'down' && rec) { stage.hurt(rec.id); const r = stage.thing(rec.id); r.ent.hp = 0; r.ent.alive = false; stage.refresh(rec.id); refreshSelect(); }
    else if (d.tb === 'remove' && rec) { stage.remove(rec.id); selected = null; refreshSelect(); }
    else if (d.tb === 'reset') { stage.things().forEach(r => stage.heal(r.id)); refreshSelect(); }
    else if (d.tb === 'clear') { stage.clearThings({keepLead: true}); selected = stage.lead()?.id || null; refreshSelect(); }
    else if (d.tb === 'boxes') { const on = b.getAttribute('aria-pressed') !== 'true'; b.setAttribute('aria-pressed', String(on)); stage.setDebug(on); }
    else if (d.tb === 'rebuild' && rec?.kind === 'actor') {
      const it = {...rec.item}, weapon = $('weapon').value, armor = $('armor').value, race = $('race').value;
      if (it.identity === 'doran' && ['cleaver','daggers'].includes(weapon)) { it.loadout = weapon; rec.ent.weapon = weapon; }
      if (!it.identity) { it.race_id = race; it.equipment = [...(weapon !== 'none' ? [row(weapon, {handedness: ['bow', 'staff', 'polearm'].includes(weapon) ? 'two-handed' : 'one-handed'})] : []), ...(armor ? [row('armor', {material: armor})] : [])]; rec.ent.weapon = weapon; }
      rec.item = it; stage.refresh(rec.id);
    }
  });
  $('selected').onchange = e => select(e.target.value);
  $('carry').onchange = e => { const r = selRec(); if (r) stage.setCarry(r.id, e.target.value); };
  $('scale').oninput = e => { const r = selRec(); if (!r) return; const k = Number(e.target.value); $('scale-read').textContent = `${k.toFixed(2)}×`; stage.setScale(r.id, k); };

  const readout = () => {
    const r = selRec(); if (!r) { readEl.textContent = 'nothing selected'; return; }
    const e = r.ent, b = e.body, snap = stage.snapshot(), t = snap.things.find(x => x.id === r.id);
    readEl.textContent = [`${e.name || r.id}  (${b.sizeClass}${b.mult !== 1 ? ` ×${b.mult.toFixed(2)}` : ''})`, `height ${b.height.toFixed(2)} ft   shoulders ${b.width.toFixed(2)} ft`, `footprint ${b.foot.rx.toFixed(2)}×${(b.foot.rd * 2).toFixed(2)} ft   reach ${b.reach.toFixed(1)} ft`,
      `hp ${Math.max(0, e.hp | 0)}/${e.max | 0}   wounds ${e.wounds.length}   ${e.alive ? '' : 'DOWN '}`, `x ${e.x.toFixed(1)}  depth ${e.d.toFixed(2)}  facing ${e.face > 0 ? '→' : '←'}  ${e.moving ? `gait ${e.gait.toFixed(2)}/s` : 'standing'}`,
      `carry ${t?.carry || '–'}   ${e.swing ? `swinging: ${e.swing.style}` : ''}`].join('\n');
  };
  const api = {el, stage, spawn, select, applyRoom,
    start() { stage.start(); timer = setInterval(readout, 300); if (!stage.things().some(t => t.kind === 'actor')) { select(spawn('doran', {id: 'doran', x: stage.st.worldW * .3, d: .42, select: true}).id); spawn('townsperson', {x: stage.st.worldW * .78, d: .3}); } readout(); },
    stop() { stage.stop(); clearInterval(timer); }, destroy() { api.stop(); stage.destroy(); el.remove(); }};
  return api;
}
