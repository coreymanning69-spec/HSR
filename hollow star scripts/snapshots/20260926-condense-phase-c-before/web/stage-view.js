// Stage view: the main display.
//
// One persistent scene element per screen. It layers a baked painted set, an
// animated back layer (doors, fire, water, contact shadows), the figures and
// props standing on a depth plane, an FX layer (motes, sparks, wounds, floats)
// and a lighting pass multiplied over everything, so the paper dolls and the
// place they stand in are lit by the same lamps.
//
// The stage runs a Stage World (stage-world.js) for movement, reach and
// damage, and feeds the figures' own rigs through data attributes
// (data-facing, data-gait, data-carry, data-swing) that puppet-dom reads.
// Host state is never decided here: a real run's outcomes come from the host,
// and this view only walks, turns, opens, swings and draws.
import {clamp, lerp, TAU, hash32, rgba, mixHex} from './actor-core.js';
import {createWorld, makeProp, makeEntity, bodyOf, PROP_TYPES, SWING_STYLES, SWING_ORDER, swingTiming, rng, MATERIALS} from './stage-world.js';
import {THEMES, themeFor, layoutExits, bakeSet, drawLive, todOf, TOD, PPF, tint, clearSpot} from './stage-set.js';
import {drawProp, kit, PROP_KINDS} from './stage-art.js';
import {characterFigure, dollModel, visualWeapon} from './paperdoll.js?v=puppet-1';
import {syncPuppets, figureSocket, figureImpulse} from './puppet-dom.js';
import {StageFx, paintWound} from './stage-fx.js';

const HOSTILE = new Set(['camp', 'alley', 'docks', 'warehouse', 'foundry', 'lair', 'drowned', 'crypt', 'dungeon', 'cave', 'forest']);
const GUARD = /guard|sentinel|watch|steward|castellan|warden/i, STILL = /merchant|keeper|bartend|barkeep|clerk|attendant|vendor|shop|ferryman|priest|acolyte/i;
const ANIMATED_PROPS = new Set(['lamppost', 'altar', 'brazier', 'campfire', 'wheel', 'banner', 'cocoon', 'hearth']);
const WORLD_DEPTH = 10;                                             // ft from the front edge to the back wall
const REF_W = 44;                                                   // decor is authored against a 44 ft floor
const perf = () => performance.now();

export function artForObject(id, o = {}) {
  const text = `${id} ${o.name || ''} ${o.display_name || ''} ${o.kind || ''}`.toLowerCase();
  if (/wardrobe|cabinet|locker|toolbox/.test(text)) return 'cabinet';
  if (o.container || /chest|cache|strongbox|box\b/.test(text)) return 'chest';
  for (const [re, kind] of [[/crate/, 'crate'], [/barrel|keg/, 'barrel'], [/\bbin\b|bucket/, 'bin'], [/sack|grain|bag/, 'sack'], [/bell/, 'bell'], [/ledger|board|desk|counter|\bbar\b/, 'desk'],
    [/rope/, 'rope'], [/wheel/, 'wheel'], [/boat|skiff/, 'boat'], [/fire|camp/, 'campfire'], [/altar|bowl|shrine/, 'altar'], [/purse|coin|pouch/, 'pouch'], [/rack|peg|weapon/, 'rack'],
    [/lamp|lantern/, 'lamppost'], [/table|stall/, 'table'], [/bed|bunk/, 'bed'], [/statue/, 'statue'], [/dummy/, 'dummy']]) if (re.test(text)) return kind;
  return o.fixed ? 'crate' : 'parcel';
}

export function createStage(options = {}) {
  const opts = {mode: 'world', reducedMotion: () => false, ...options};
  const toolbox = opts.mode === 'toolbox';
  const root = document.createElement('section');
  root.className = 'illustrated-scene world-stage'; root.dataset.worldStage = ''; root.dataset.sceneTheme = 'reliquary'; root.tabIndex = -1;
  root.innerHTML = `<div class="ws-cam"><canvas class="ws-bake"></canvas><canvas class="ws-live"></canvas><div class="ws-things"></div><canvas class="ws-fx"></canvas><canvas class="ws-light"></canvas><canvas class="ws-glow"></canvas></div>
    <div class="ws-hotspots"></div><div class="ws-tip" hidden></div><div class="scene-frame-label"><strong></strong><small></small></div>`;
  const $ = sel => root.querySelector(sel);
  let bakeEl = $('.ws-bake');
  const liveEl = $('.ws-live'), things = $('.ws-things'), fxEl = $('.ws-fx'), lightEl = $('.ws-light'), glowEl = $('.ws-glow'), hot = $('.ws-hotspots'), camEl = $('.ws-cam');
  const liveCtx = liveEl.getContext('2d'), fxCtx = fxEl.getContext('2d'), lightCtx = lightEl.getContext('2d'), glowCtx = glowEl.getContext('2d');

  const fx = new StageFx();
  const st = {W: 0, H: 0, L: 0, R: 0, UW: 0, dpr: 1, ppf0: 30, worldW: REF_W, theme: null, themeId: '', tod: 'evening', roomId: '', seed: 'room', bays: [], doors: new Map(), things: new Map(),
    world: createWorld({width: REF_W, depth: WORLD_DEPTH, seed: 'stage'}), leadId: null, hover: null, t: 0, last: 0, raf: 0, running: false, bakeKey: '', debug: false, shake: 0,
    tickMs: 0, combat: false, keys: new Set(), hostile: null, lights: [], lightsKey: '', walkPromise: null, enter: null, quiet: 0, hp: new Map(), listeners: new Map(), ready: false};
  const world = st.world;
  const emitOut = (type, detail) => { for (const fn of st.listeners.get(type) || []) fn(detail); };

  // ---- projection ----------------------------------------------------------
  const cam = () => st.theme?.cam || {front: .91, back: .6, farScale: .66};
  const depthScale = d => lerp(1, cam().farScale, clamp(d, -.2, 1.2));
  function project(x, d) {
    const c = cam(), s = depthScale(d);
    return {sx: st.L + st.UW / 2 + (x - st.worldW / 2) * (st.UW / st.worldW) * s, sy: lerp(c.front, c.back, d) * st.H, s};
  }
  function unproject(px, py) {
    const c = cam(), d = clamp((py / st.H - c.front) / (c.back - c.front), 0, 1), s = depthScale(d);
    return {x: st.worldW / 2 + (px - st.L - st.UW / 2) / ((st.UW / st.worldW) * s), d};
  }
  const ppfAt = d => st.ppf0 * depthScale(d);
  const rangeAt = d => { const s = depthScale(d), half = .485 * st.worldW / s; return [st.worldW / 2 - half, st.worldW / 2 + half]; };
  world.setBounds({rangeAt});

  // ---- layout ----------------------------------------------------------------
  function resize() {
    const W = root.clientWidth, H = root.clientHeight, ins = opts.insets?.() || {}, L = Math.max(0, Math.round(ins.left || 0)), R = Math.max(0, Math.round(ins.right || 0));
    if (!W || !H || (W === st.W && H === st.H && L === st.L && R === st.R)) return;
    const oldW = st.worldW;
    // The display's cards float over its edges: everything that must be seen or
    // clicked is laid out in the clear middle [L, L + UW]; the painting bleeds under the cards.
    st.W = W; st.H = H; st.L = L; st.R = R; st.UW = Math.max(300, W - L - R); st.dpr = Math.min(2, devicePixelRatio || 1); st.ppf0 = PPF * H;
    st.worldW = Math.round(st.UW / st.ppf0 * 10) / 10; world.setSize(st.worldW, WORLD_DEPTH);
    for (const b of st.bays) b.xFt = st.worldW / 2 + (b.x - .5) * st.worldW / depthScale(1);
    if (oldW && oldW !== st.worldW) for (const e of world.list()) e.x *= st.worldW / oldW;
    for (const c of [liveEl, fxEl]) { c.width = Math.round(W * st.dpr); c.height = Math.round(H * st.dpr); c.style.width = W + 'px'; c.style.height = H + 'px'; }
    for (const c of [lightEl, glowEl]) { c.width = Math.max(8, W >> 2); c.height = Math.max(8, H >> 2); c.style.width = W + 'px'; c.style.height = H + 'px'; }
    st.bakeKey = ''; rebake(); for (const rec of st.things.values()) sizeThing(rec); layoutHotspots(); relocateDecor();
  }
  let rebakeTimer = 0;
  function rebake() {
    if (!st.theme || !st.W) return;
    const key = `${st.themeId}|${st.tod}|${st.seed}|${st.W}x${st.H}|${st.L}|${st.R}|${st.bays.map(b => `${b.key}${b.kind}${b.x.toFixed(2)}`).join(',')}`;
    if (key === st.bakeKey) return; st.bakeKey = key;
    const art = bakeSet(st.themeId, st.UW, st.H, {seed: st.seed, tod: st.tod, bays: st.bays, dpr: st.dpr});
    const canvas = document.createElement('canvas'); canvas.width = Math.round(st.W * st.dpr); canvas.height = art.height;
    const c = canvas.getContext('2d'), sx = Math.round(st.L * st.dpr), uw = art.width;
    c.drawImage(art, sx, 0);
    const wl = Math.min(sx, uw), wr = Math.min(canvas.width - sx - uw, uw);           // mirrored bleed under the cards
    if (wl > 0) { c.save(); c.translate(sx, 0); c.scale(-1, 1); c.drawImage(art, 0, 0, wl, art.height, 0, 0, wl, art.height); c.restore(); }
    if (wr > 0) { c.save(); c.translate(sx + uw, 0); c.scale(-1, 1); c.drawImage(art, uw - wr, 0, wr, art.height, -wr, 0, wr, art.height); c.restore(); }
    canvas.className = 'ws-bake'; canvas.style.width = st.W + 'px'; canvas.style.height = st.H + 'px';
    camEl.replaceChild(canvas, bakeEl); bakeEl = canvas;
  }
  const resizeObs = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(() => { clearTimeout(rebakeTimer); rebakeTimer = setTimeout(resize, 60); }) : null;

  // ---- rooms -------------------------------------------------------------------
  // Everything the stage draws for the place itself: theme, doors, decor.
  function setRoom({themeId, tod = 'evening', roomId = '', exits = [], name = '', sub = '', from = null, seed = null, wellHotspot = false} = {}) {
    const changed = roomId !== st.roomId || themeId !== st.themeId;
    st.roomId = roomId;
    st.theme = THEMES[themeId] || THEMES.market; st.themeId = st.theme.id; st.tod = todOf(tod); st.seed = seed || roomId || themeId; st.hostile = HOSTILE.has(st.themeId);
    st.bays = layoutExits(st.theme, exits);
    // Back-wall doors are placed in screen space; the world floor is wide enough at the back to stand in front of each.
    for (const b of st.bays) { const s = depthScale(1); b.xFt = st.worldW / 2 + (b.x - .5) * st.worldW / s; if (!st.doors.has(b.key) || changed) st.doors.set(b.key, {open: 0, target: 0, hover: 0, until: 0}); }
    for (const k of [...st.doors.keys()]) if (!st.bays.some(b => b.key === k)) st.doors.delete(k);
    $('.scene-frame-label strong').textContent = name || st.theme.name; $('.scene-frame-label small').textContent = sub || 'Public room projection';
    root.dataset.sceneTheme = 'reliquary'; root.dataset.setTheme = st.themeId; root.dataset.tod = st.tod;
    st.wellHotspot = wellHotspot;
    if (st.W) { rebake(); }
    if (changed) {
      if (!toolbox) for (const [id, rec] of [...st.things]) if (!(rec.kind === 'actor' && rec.role === 'party')) { rec.node.remove(); world.remove(id); st.things.delete(id); }
      rebuildDecor(); fx.clear(); st.enter = {from, at: st.t}; st.hp.clear(); settle(false); st.busyDoor = false;
      if (!toolbox) {
        const entry = from ? st.bays.find(b => b.id === from) : null;
        actorsOf('party').forEach((rec, i) => {
          const e = rec.ent; e.goal = null; e.route = []; e.vx = e.vd = 0; e.swing = null;
          if (entry) { e.x = entry.xFt + (i ? -i * .6 : 0); e.d = 1.05 + i * .01; e.face = 1; world.faceDir(e, 1, true); const dr = st.doors.get(entry.key); dr.open = .6; dr.target = 1; dr.until = st.t + 1500; world.setBounds({d1: 1.12}); setTimeout(() => world.setBounds({d1: .96}), 900 + i * 250); world.walkTo(e.id, entry.xFt + 1.8 + i * -1.6, .8 - i * .06, {arrive: .5}); }
          else { e.x = st.worldW * (.28 - i * .04); e.d = .82 - i * .07; }
        });
      }
      root.classList.remove('ws-arrive'); void root.offsetWidth; if (!opts.reducedMotion()) root.classList.add('ws-arrive');
    }
    world.setSize(st.worldW, WORLD_DEPTH);
    fx.setAmbient(st.theme.particles, st.W || 1, st.H || 1, (st.H || 500) / 500);
    layoutHotspots();
    return changed;
  }
  function rebuildDecor() {
    for (const [id, rec] of st.things) if (rec.decor) { rec.node.remove(); world.remove(id); st.things.delete(id); }
    st.theme.decor.forEach((d, i) => addProp(d.prop, {id: `decor-${d.prop}-${i}`, x: d.x / REF_W * st.worldW, d: d.d, scale: d.scale || 1, blocking: d.blocking, decor: true, cuttable: toolbox ? undefined : d.prop === 'dummy' || d.prop === 'post'}));
  }
  function relocateDecor() { st.theme?.decor.forEach((d, i) => { const e = world.get(`decor-${d.prop}-${i}`); if (e) { e.x = d.x / REF_W * st.worldW; } }); }

  // ---- things: props and actors ----------------------------------------------
  function addProp(kind, {id, x, d, scale = 1, blocking, decor = false, obj = null, cuttable, hp, art = kind} = {}) {
    if (st.things.has(id)) return st.things.get(id);
    const ent = world.add(makeProp(kind in PROP_TYPES ? kind : 'crate', {id, x, d, scale, blocking, cuttable, hp}));
    const canvas = document.createElement('canvas'); canvas.className = 'ws-prop'; canvas.dataset.prop = kind;
    if (obj) { canvas.dataset.object = id; canvas.setAttribute('aria-hidden', 'true'); }
    things.append(canvas);
    const rec = {id, kind: 'prop', art, ent, node: canvas, decor, obj, scale, sig: '', open: obj?.open ? 1 : 0, openTo: obj?.open ? 1 : 0, ox: 0, oy: 0};
    st.things.set(id, rec); sizeThing(rec); return rec;
  }
  function sizeThing(rec) {
    const ent = rec.ent, b = ent.body;
    if (rec.kind === 'prop') {
      const pad = 14, w = Math.ceil(b.width * st.ppf0) + pad * 2, h = Math.ceil(b.height * st.ppf0) + pad * 2;
      if (rec.w !== w || rec.h !== h) { rec.w = w; rec.h = h; rec.node.width = Math.round(w * st.dpr); rec.node.height = Math.round(h * st.dpr); rec.node.style.width = w + 'px'; rec.node.style.height = h + 'px'; rec.sig = ''; }
      rec.ox = w / 2; rec.oy = h - pad; rec.node.style.transformOrigin = `${rec.ox}px ${rec.oy}px`;
    } else {
      const w = 5.85 * st.ppf0 * b.vis, h = 7.19 * st.ppf0 * b.vis;
      rec.node.style.width = w.toFixed(1) + 'px'; rec.node.style.height = h.toFixed(1) + 'px'; rec.ox = w / 2; rec.oy = h * .94; rec.node.style.transformOrigin = `${rec.ox}px ${rec.oy}px`;
    }
  }
  function paintProp(rec) {
    const ent = rec.ent, dmg = ent.max > 0 ? clamp(1 - ent.hp / ent.max, 0, 1) : 0;
    const sig = `${rec.open.toFixed(2)}|${dmg.toFixed(2)}|${ent.broken}`;
    if (sig === rec.sig && !ANIMATED_PROPS.has(rec.art)) return; rec.sig = sig;
    const c = rec.node.getContext('2d'), K = kit(rec.w, rec.h, Math.random, cam()); K.S = st.H / 500;
    c.setTransform(st.dpr, 0, 0, st.dpr, 0, 0); c.clearRect(0, 0, rec.w, rec.h);
    if (ent.broken) return;
    c.translate(rec.ox, rec.oy);
    drawProp(c, K, rec.art, ent.body.width * st.ppf0, ent.body.height * st.ppf0, {open: rec.open, dmg: dmg * 1.1, t: st.t / 1000});
  }

  // Figures. The item is the public actor (host) or a local spec (Toolbox).
  function itemOf(spec) { return {...spec.item, id: spec.id, name: spec.name || spec.item?.name}; }
  function addActor(spec) {
    const id = String(spec.id); if (st.things.has(id)) return st.things.get(id);
    const item = itemOf(spec), weapon = spec.weapon || visualWeapon(item) || 'none';
    const isDoran = String(item.identity || '').toLowerCase() === 'doran';
    const ent = world.add(makeEntity({id, kind: 'actor', team: spec.team || 'npc', item, weapon: isDoran && weapon === 'none' ? 'cleaver' : weapon, x: spec.x, d: spec.d, face: spec.face || 1, name: item.name,
      hp: spec.hp ?? item.hp ?? 30, max: spec.max ?? item.max_hp ?? spec.hp ?? item.hp ?? 30, ambient: spec.ambient || null, cuttable: spec.cuttable ?? toolbox, armor: spec.armor || 0, material: spec.material || 'flesh'}));
    if (spec.scale) { ent.body = bodyOf({...item, scale: spec.scale}, ent.weapon); }
    const tmp = document.createElement('div');
    tmp.innerHTML = characterFigure(item, `ws-actor role-${spec.role || 'npc'}`, 'idle', {attrs: {'data-stage-actor': id, 'data-actor': spec.role === 'party' ? id : undefined, 'data-resident': spec.role === 'npc' ? id : undefined,
      role: 'button', tabindex: '0', 'aria-label': item.name || id}});
    const node = tmp.firstElementChild; node.dataset.shadow = 'off'; node.dataset.facing = String(ent.face);
    Object.assign(node.style, {position: 'absolute', left: '0', top: '0', bottom: 'auto', right: 'auto'});
    things.append(node);
    const rec = {id, kind: 'actor', role: spec.role || 'npc', ent, node, item, doran: isDoran, sig: '', swingMode: 'beat', carry: null, ox: 0, oy: 0, last: {}, spawnAt: st.t};
    st.things.set(id, rec); sizeThing(rec); refreshModel(rec, true); syncPuppets(root, {reducedMotion: opts.reducedMotion});
    return rec;
  }
  function refreshModel(rec, force = false) {
    const ent = rec.ent, item = {...rec.item, hp: ent.hp, max_hp: ent.max};
    const pose = rec.wantCombat ? 'combat' : 'idle';
    const model = dollModel(item, {pose});
    if (rec.doran && ['cleaver','daggers'].includes(ent.weapon)) model.loadout = model.base.loadout = ent.weapon;
    model.carry = rec.doran ? rec.carry || undefined : undefined;
    const json = JSON.stringify(model);
    if (json !== rec.sig || force) {
      st.needSync = true; rec.sig = json; rec.node.dataset.puppetModel = json; rec.swingMode = rec.doran && model.loadout === 'cleaver' ? 'rig' : 'beat';
      rec.node.classList.toggle('is-down', !ent.alive); rec.node.setAttribute('aria-label', `${item.name || rec.id}${ent.alive ? '' : ' (down)'}`);
      return true;
    }
    return false;
  }
  function removeThing(id) { const rec = st.things.get(id); if (!rec) return; rec.node.remove(); world.remove(id); st.things.delete(id); if (st.leadId === id) st.leadId = null; }
  const lead = () => st.things.get(st.leadId)?.ent || null;
  const actorsOf = role => [...st.things.values()].filter(r => r.kind === 'actor' && (!role || r.role === role));

  // ---- syncing from a public host view ---------------------------------------
  // Party members and residents become figures; room objects become props.
  // Existing figures keep their place, so a re-render never teleports anyone.
  function syncView(view = {}, {selected = null, encounter = false} = {}) {
    st.combat = encounter; st.lastView = view;
    const party = view.party || [], npcs = Object.values(view.room?.npcs || {});
    const wantIds = new Set();
    party.forEach((m, i) => {
      const id = String(m.id); wantIds.add(id);
      let rec = st.things.get(id);
      if (!rec) {
        rec = addActor({id, item: m, role: 'party', team: 'party', x: st.worldW * (.28 - i * .04), d: .82 - i * .07, face: 1, hp: m.hp, max: m.max_hp});
      } else { rec.item = m; rec.ent.hp = Number.isFinite(Number(m.hp)) ? Number(m.hp) : rec.ent.hp; rec.ent.max = Number(m.max_hp) || rec.ent.max; rec.ent.alive = rec.ent.hp > 0; }
    });
    npcs.forEach((n, i) => {
      const id = String(n.id || n.npc_id || `npc-${i}`); wantIds.add(id);
      let rec = st.things.get(id);
      if (!rec) {
        const r = rng(`${st.roomId}:${id}`), text = `${n.role || ''} ${n.name || ''}`;
        const home = {x: st.worldW * (.55 + (i % 4) * .1 + r() * .06), d: .28 + r() * .5}, type = GUARD.test(text) ? 'guard' : STILL.test(text) ? 'still' : 'wander';
        rec = addActor({id, item: {...n, id}, role: 'npc', team: 'npc', x: home.x, d: home.d, face: r() < .5 ? -1 : 1, hp: n.hp, max: n.max_hp, cuttable: false,
          ambient: {type, home, leash: type === 'wander' ? 3.4 : 0, face: type === 'guard' ? (home.x < st.worldW / 2 ? 1 : -1) : 0}});
      } else { rec.item = {...n, id}; rec.ent.hp = Number.isFinite(Number(n.hp)) ? Number(n.hp) : rec.ent.hp; rec.ent.alive = rec.ent.hp > 0; }
    });
    // Two residents standing near each other talk.
    const npcRecs = actorsOf('npc');
    for (const a of npcRecs) for (const b of npcRecs) if (a !== b && a.ent.ambient?.type === 'wander' && b.ent.ambient?.type === 'wander' && world.dist(a.ent, b.ent) < 7) { a.ent.ambient.type = 'talk'; a.ent.ambient.partner = b.id; }
    for (const [id, rec] of [...st.things]) if (rec.kind === 'actor' && !wantIds.has(id) && !toolbox) removeThing(id);
    st.leadId = selected && st.things.has(String(selected)) ? String(selected) : (st.things.has(st.leadId) ? st.leadId : party[0] ? String(party[0].id) : null);
    for (const r of actorsOf('party')) r.node.classList.toggle('is-selected', r.id === st.leadId);
    syncObjects(view.room?.objects || {});
    for (const rec of st.things.values()) if (rec.kind === 'actor') refreshModel(rec);
    syncPuppets(root, {reducedMotion: opts.reducedMotion});
    layoutHotspots();
  }
  function syncObjects(objects) {
    const entries = Object.entries(objects).filter(([, o]) => o && o.visible !== false && !o.taken && !o.carried_by).map(([key, o]) => [String(o.object_id || o.id || key), o]);
    const seen = new Set();
    entries.forEach(([id, o], i) => {
      const key = `obj:${id}`; seen.add(key);
      const art = artForObject(id, o), r = rng(`${st.roomId}:${id}`);
      let rec = st.things.get(key);
      if (!rec) {
        const n = entries.length, x = st.worldW * (n === 1 ? .5 : .16 + i * (.68 / (n - 1))) + (r() - .5) * 2.4, d = .22 + r() * .5;
        rec = addProp(art in PROP_TYPES ? art : 'crate', {id: key, x, d, blocking: false, obj: {id, ...o}, art, cuttable: false});
        rec.objectId = id; rec.node.dataset.object = id;
      } else rec.obj = {id, ...o};
      rec.openTo = o.open ? 1 : 0; rec.label = o.name || o.display_name || (o.discovered ? id : 'an unexamined object');
    });
    for (const [id, rec] of [...st.things]) if (id.startsWith('obj:') && !seen.has(id)) removeThing(id);
  }

  // ---- hotspots: real buttons over doors and objects, for keyboard and readers -
  function layoutHotspots() {
    if (!st.W || !st.theme) return;
    const buttons = [];
    for (const b of st.bays) {
      const s = ppfAt(1), w = b.w * s, h = b.h * s, y = cam().back * st.H;
      buttons.push(`<button type="button" class="scene-hotspot hotspot-exit ws-hot" style="left:${(st.L + b.x * st.UW - w / 2).toFixed(1)}px;top:${(y - h).toFixed(1)}px;width:${w.toFixed(1)}px;height:${h.toFixed(1)}px" data-hotspot="exit" data-exit="${HSRUI.escape(b.key)}" data-destination="${HSRUI.escape(b.id)}" data-walk-x="${((st.L + b.x * st.UW) / st.W * 100).toFixed(1)}" data-tooltip="Walk to ${HSRUI.escape(b.name)}" aria-label="Walk to ${HSRUI.escape(b.name)}"><small>${HSRUI.escape(b.name)}</small></button>`);
    }
    for (const rec of st.things.values()) if (rec.obj) {
      const P = project(rec.ent.x, rec.ent.d), w = rec.ent.body.width * ppfAt(rec.ent.d), h = rec.ent.body.height * ppfAt(rec.ent.d);
      buttons.push(`<button type="button" class="scene-hotspot hotspot-object ws-hot" style="left:${(P.sx - w / 2).toFixed(1)}px;top:${(P.sy - h).toFixed(1)}px;width:${w.toFixed(1)}px;height:${h.toFixed(1)}px" data-hotspot="object" data-object="${HSRUI.escape(rec.objectId)}" data-walk-x="${(P.sx / st.W * 100).toFixed(1)}" aria-label="${HSRUI.escape(rec.label || rec.objectId)}"><small>${HSRUI.escape(rec.label || rec.objectId)}</small></button>`);
    }
    if (st.wellHotspot) {
      const B = wellBox();
      buttons.push(`<button type="button" class="scene-hotspot hotspot-object ws-hot" style="left:${(B.x - B.w / 2).toFixed(1)}px;top:${(B.y - B.h).toFixed(1)}px;width:${B.w.toFixed(1)}px;height:${(B.h + 4).toFixed(1)}px" data-hotspot="well" data-object="well" data-walk-x="${(B.x / st.W * 100).toFixed(1)}" data-tooltip="The town well: examine or descend" aria-label="The town well"><small>The well</small></button>`);
    }
    const html = buttons.join('');
    if (hot.dataset.sig !== html) { hot.innerHTML = html; hot.dataset.sig = html; }
  }

  // The well in the Well room is painted at the widest clear stretch of the back wall.
  function wellBox() { const S = st.H / 500, back = cam().back * st.H; return {x: st.L + clearSpot(st.bays) * st.UW, y: back + (st.H - back) * .16, w: 150 * S, h: 150 * S}; }

  // ---- movement commands -----------------------------------------------------
  const settle = ok => { const p = st.walkPromise; st.walkPromise = null; p?.(ok); };
  function walkLead(x, d, {run = false} = {}) {
    const e = lead(); if (!e) return Promise.resolve(false);
    settle(false); stopKeys();
    return new Promise(resolve => { st.walkPromise = resolve; if (!world.walkTo(e.id, x, d, {arrive: .4, run, then: () => settle(true)})) settle(false); });
  }
  function stopKeys() { st.keyGoal = false; }
  function doorSpot(bay) { return {x: bay.xFt, d: .955}; }
  function toggleDoor(key, on = null) { const dr = st.doors.get(key); if (!dr) return; dr.target = on == null ? (dr.target > .5 ? 0 : 1) : on ? 1 : 0; dr.until = 0; }
  // Door click: walk up, open it, step through. In the Toolbox a door only toggles.
  async function enterDoor(bay) {
    const e = lead(); if (!e || st.busyDoor) return;
    st.busyDoor = true;
    try {
      const spot = doorSpot(bay);
      if (Math.hypot(e.x - spot.x, (e.d - spot.d) * WORLD_DEPTH) > .8 && !await walkLead(spot.x, spot.d)) return;
      toggleDoor(bay.key, true);
      if (toolbox) { await sleep(500); return; }
      await sleep(opts.reducedMotion() ? 0 : 430);
      world.setBounds({d1: 1.12});
      const done = await new Promise(resolve => { st.walkPromise = resolve; world.walkTo(e.id, bay.xFt, 1.08, {arrive: .2, then: () => settle(true)}); });
      world.setBounds({d1: .96});
      if (done) { st.doors.get(bay.key).until = st.t + 900; opts.onExit?.(bay); }
    } finally { st.busyDoor = false; world.setBounds({d1: .96}); }
  }
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  async function talkTo(id) {
    const e = lead(), rec = st.things.get(id); if (!e || !rec) return;
    if (!toolbox) { const ok = await new Promise(resolve => { settle(false); st.walkPromise = resolve; if (!world.approach(e.id, id, {then: () => settle(true)})) settle(false); }); if (!ok) return; }
    world.faceEntity(e, rec.ent); world.faceEntity(rec.ent, e);
    opts.onTalk?.(id, rec);
  }
  async function useObject(rec) {
    const e = lead(); if (!e) return;
    const x = rec.ent.x + (e.x < rec.ent.x ? -1 : 1) * (rec.ent.body.width / 2 + e.body.foot.rx + .9);
    if (!await walkLead(x, clamp(rec.ent.d + .04, .08, .95))) return;
    world.faceEntity(e, rec.ent); opts.onObject?.(rec.objectId, rec);
  }

  // ---- swings ------------------------------------------------------------------
  // Click a training dummy: walk to a comfortable striking distance, face it, swing.
  async function strike(rec) {
    const L = lead(); if (!L || !L.alive || rec.ent.broken) return;
    const t = rec.ent, side = L.x < t.x ? -1 : 1, want = t.body.width / 2 + L.body.reach * .66;
    if (Math.abs(L.x - t.x) > want + .6 || Math.abs(L.d - t.d) * WORLD_DEPTH > 1.2) { if (!await walkLead(t.x + side * want, t.d)) return; }
    world.faceEntity(L, t); swing(st.leadId);
  }
  function swing(id, style = null) {
    const rec = st.things.get(id ?? st.leadId); if (!rec || rec.kind !== 'actor' || !rec.ent.alive) return false;
    const e = rec.ent, weapon = e.weapon;
    if (weapon === 'none' && !rec.doran) return false;
    const next = style || SWING_ORDER[(rec.swingIx = ((rec.swingIx ?? -1) + 1) % SWING_ORDER.length)];
    // A face-to-face swing: turn toward the nearest thing in reach first.
    if (!e.swing) {
      const near = [...world.list()].filter(t => t !== e && !t.broken && t.cuttable !== false && (t.kind === 'prop' || t.alive) && Math.abs(t.d - e.d) * WORLD_DEPTH < 3).sort((a, b) => Math.abs(a.x - e.x) - Math.abs(b.x - e.x))[0];
      if (near && Math.abs(near.x - e.x) < e.body.reach + 3) world.faceEntity(e, near);
    }
    rec.readyUntil = st.t + 3600;
    const drawFirst = rec.doran && (rec.carry === 'stowed' || !rec.carry) && !e.swing;
    // The next frame sees `readyUntil` and draws the blade; the swing starts once it is out.
    if (drawFirst) { setTimeout(() => world.beginSwing(e.id, next), opts.reducedMotion() ? 0 : 520); return true; }
    return Boolean(world.beginSwing(e.id, next));
  }

  // ---- events from the world -------------------------------------------------
  function handleEvent(ev) {
    const P = id => { const rec = st.things.get(id); if (!rec) return null; const p = project(rec.ent.x, rec.ent.d), h = rec.ent.body.height * ppfAt(rec.ent.d); return {rec, x: p.sx, y: p.sy, top: p.sy - h, h}; };
    const S = st.H / 500;
    if (ev.type === 'swing') { const rec = st.things.get(ev.id); if (rec) { rec.swingStyle = ev.style; rec.swingAt = perf(); rec.swingBeatAt = rec.swingAt; rec.readyUntil = st.t + ev.ms + 3200; } }
    else if (ev.type === 'swing_end') { const rec = st.things.get(ev.id); if (rec) { rec.swingStyle = ''; } }
    else if (ev.type === 'contact') { if (!opts.reducedMotion()) st.shake = Math.max(st.shake, 2.5); }
    else if (ev.type === 'hit') {
      const t = P(ev.target), a = ev.attacker ? P(ev.attacker) : null; if (!t) return;
      const cx = t.x + (a ? Math.sign(t.x - a.x || 1) * -2 * S : 0), cy = t.y - t.h * ev.y / Math.max(.5, t.rec.ent.body.height);
      fx.hit(cx, cy, ev.material, {dir: ev.dir, power: clamp(ev.damage / 10, .6, 2.2), crit: ev.crit, S, floorY: t.y + 4 * S});
      fx.float(t.x, t.top - 6 * S, `-${ev.damage}`, {crit: ev.crit, S: clamp(S * ppfAt(t.rec.ent.d) / st.ppf0 + .2, .8, 1.3), color: ev.crit ? '#ffd166' : '#fff2c0'});
      if (t.rec.kind === 'actor') { figureImpulse(t.rec.node, ev.dir * (ev.crit ? 980 : 560)); t.rec.node.classList.add('is-hit'); setTimeout(() => t.rec.node.classList.remove('is-hit'), 150); }
      else { t.rec.shakeUntil = st.t + 200; }
      st.hp.set(ev.target, st.t + 2600);
      if (ev.crit && !opts.reducedMotion()) st.shake = 7; else if (!opts.reducedMotion()) st.shake = Math.max(st.shake, 4);
      if (t.rec.kind === 'actor') refreshModel(t.rec);
      emitOut('hit', ev);
    } else if (ev.type === 'break') {
      const t = P(ev.id); if (!t) return; const S2 = S * ppfAt(t.rec.ent.d) / st.ppf0;
      fx.debris(t.x, t.y, t.rec.ent.body.width * ppfAt(t.rec.ent.d), t.rec.ent.body.height * ppfAt(t.rec.ent.d), t.rec.ent.material, ev.dir, S2 + .25);
      t.rec.ent.blocking = false; t.rec.brokeAt = st.t; emitOut('break', ev);
    } else if (ev.type === 'death') { const rec = st.things.get(ev.id); if (rec?.kind === 'actor') { refreshModel(rec); syncPuppets(root, {reducedMotion: opts.reducedMotion}); } emitOut('death', ev); }
  }

  // ---- input -------------------------------------------------------------------
  const localPt = e => { const r = root.getBoundingClientRect(); return {x: (e.clientX - r.left) * (st.W / (r.width || st.W)), y: (e.clientY - r.top) * (st.H / (r.height || st.H))}; };
  function pick(px, py) {
    // Front-most thing under the pointer first: its body box on the floor plane.
    const rows = [...st.things.values()].filter(r => !r.ent.broken && r.ent.d >= 0).map(r => {
      const p = project(r.ent.x, r.ent.d), sc = ppfAt(r.ent.d), w = Math.max(r.ent.body.width * sc, 26), h = r.ent.body.height * sc;
      return {rec: r, p, w, h};
    }).sort((a, b) => b.p.sy - a.p.sy);
    for (const {rec, p, w, h} of rows) {
      if (rec.decor && !toolbox && !rec.ent.cuttable) continue;               // set dressing is not clickable; training dummies are
      if (rec.kind === 'prop' && !rec.obj && !rec.ent.cuttable && !toolbox) continue;
      if (px >= p.sx - w / 2 - 6 && px <= p.sx + w / 2 + 6 && py >= p.sy - h - 8 && py <= p.sy + 10) return {kind: rec.kind, rec};
    }
    for (const b of st.bays) {
      const s = ppfAt(1), w = b.w * s, h = b.h * s, y = cam().back * st.H;
      const bx = st.L + b.x * st.UW; if (px >= bx - w / 2 - 8 && px <= bx + w / 2 + 8 && py >= y - h - 8 && py <= y + 26) return {kind: 'door', bay: b};
    }
    if (st.wellHotspot) { const B = wellBox(); if (px > B.x - B.w / 2 && px < B.x + B.w / 2 && py > B.y - B.h && py < B.y + 4) return {kind: 'well'}; }
    if (py >= cam().back * st.H - 4) return {kind: 'ground', ...unproject(px, py)};
    return {kind: 'none'};
  }
  // What a click here would do, in words, beside the pointer. Nothing is lit until it is hovered.
  function verbFor(hit) {
    if (!hit) return '';
    if (hit.kind === 'door') return `${st.doors.get(hit.bay.key)?.open > .5 ? 'Go through to' : 'Open the way to'} ${hit.bay.name}`;
    if (hit.kind === 'well') return 'The town well';
    if (hit.kind === 'actor') { const n = hit.rec.ent.name || hit.rec.id; return toolbox ? `Select ${n}` : hit.rec.role === 'party' ? (hit.rec.id === st.leadId ? n : `Take the lead: ${n}`) : `Talk to ${n}`; }
    if (hit.kind === 'prop') return hit.rec.obj ? `Inspect ${hit.rec.label || hit.rec.objectId}` : toolbox ? `Select ${hit.rec.ent.name}` : hit.rec.ent.cuttable ? `Strike the ${hit.rec.ent.name.toLowerCase()}` : '';
    return '';
  }
  function setHover(hit, at = null) {
    const key = hit ? `${hit.kind}:${hit.rec?.id || hit.bay?.key || ''}` : '';
    if (at) { const tip = $('.ws-tip'), text = verbFor(hit); tip.hidden = !text; if (text) { tip.textContent = text; tip.style.left = `${clamp(at.x + 14, 4, st.W - 190)}px`; tip.style.top = `${clamp(at.y - 30, 4, st.H - 30)}px`; } }
    else $('.ws-tip').hidden = true;
    if (st.hoverKey === key) return; st.hoverKey = key; st.hover = hit;
    for (const r of st.things.values()) r.node.classList.toggle('is-hover', Boolean(hit?.rec === r));
    root.style.cursor = hit && ['door', 'actor', 'prop', 'well'].includes(hit.kind) ? 'pointer' : hit?.kind === 'ground' ? 'crosshair' : '';
  }
  root.addEventListener('pointermove', e => { if (opts.locked?.()) return; const p = localPt(e); setHover(pick(p.x, p.y), p); });
  root.addEventListener('pointerleave', () => setHover(null));
  root.addEventListener('click', e => {
    if (opts.locked?.() || e.button !== 0) return;
    const btn = e.target.closest?.('button[data-hotspot]');
    if (btn && e.detail === 0) { e.preventDefault(); activate(btn.dataset); return; }
    if (e.target.closest?.('button,a,input,.scene-frame-label')) return;
    const p = localPt(e), hit = pick(p.x, p.y), run = e.shiftKey || e.detail > 1;
    const L = lead();
    if (hit.kind === 'actor') {
      if (hit.rec.role === 'party') { if (hit.rec.id !== st.leadId) { st.leadId = hit.rec.id; actorsOf('party').forEach(r => r.node.classList.toggle('is-selected', r.id === st.leadId)); opts.onSelect?.(hit.rec.id); } else opts.onSelect?.(hit.rec.id); }
      else if (toolbox) { opts.onPick?.(hit.rec); }
      else talkTo(hit.rec.id);
    } else if (hit.kind === 'prop') { if (toolbox) opts.onPick?.(hit.rec); else if (hit.rec.obj) useObject(hit.rec); else if (hit.rec.ent.cuttable) strike(hit.rec); }
    else if (hit.kind === 'door') enterDoor(hit.bay);
    else if (hit.kind === 'well') { const B = wellBox(), at = unproject(B.x, B.y + 46 * st.H / 500); walkLead(at.x, at.d).then(ok => ok && activate({hotspot: 'well', object: 'well'})); }
    else if (hit.kind === 'ground' && L) walkLead(hit.x, hit.d, {run});
  });
  root.addEventListener('contextmenu', e => {
    const p = localPt(e), hit = pick(p.x, p.y); let target = null;
    if (hit.kind === 'actor') target = hit.rec.node; else if (hit.kind === 'prop' && hit.rec.obj) target = root.querySelector(`.ws-hot[data-object="${CSS.escape(hit.rec.objectId)}"]`);
    else if (hit.kind === 'door') target = root.querySelector(`.ws-hot[data-exit="${CSS.escape(hit.bay.key)}"]`); else if (hit.kind === 'well') target = root.querySelector('.ws-hot[data-hotspot="well"]');
    if (target && target !== e.target) { e.preventDefault(); e.stopPropagation(); target.dispatchEvent(new MouseEvent('contextmenu', {bubbles: true, cancelable: true, clientX: e.clientX, clientY: e.clientY})); }
  }, true);
  // Activate a hotspot by its dataset (keyboard or the app's context menu).
  function activate(d) {
    if (d.hotspot === 'exit') { const b = st.bays.find(x => x.key === d.exit); if (b) enterDoor(b); }
    else if (d.hotspot === 'object') { const rec = [...st.things.values()].find(r => r.objectId === d.object); if (rec) useObject(rec); }
    else if (d.hotspot === 'resident') talkTo(d.resident);
    else if (d.hotspot === 'well') { const b = root.querySelector('.ws-hot[data-hotspot="well"]'); if (b) opts.onWell?.(b); }
  }
  const KEYS = {ArrowLeft: [-1, 0], a: [-1, 0], A: [-1, 0], ArrowRight: [1, 0], d: [1, 0], D: [1, 0], ArrowUp: [0, 1], w: [0, 1], W: [0, 1], ArrowDown: [0, -1], s: [0, -1], S: [0, -1]};
  function onKey(e, down) {
    if (!root.isConnected || opts.locked?.() || st.combat || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.target?.closest?.('input,textarea,select,[contenteditable]')) return;
    if (opts.keysOnlyFocused && !root.contains(document.activeElement) && document.activeElement !== document.body) return;
    if (KEYS[e.key]) { e.preventDefault(); down ? st.keys.add(e.key) : st.keys.delete(e.key); if (down) settle(false); }
    else if (down && !e.repeat && (e.key === 'f' || e.key === 'F' || e.key === ' ') && (toolbox || document.activeElement === document.body || root.contains(document.activeElement))) {
      if (e.key === ' ' && e.target?.closest?.('button,a')) return;
      if (swing(st.leadId)) e.preventDefault();
    }
  }
  const kd = e => onKey(e, true), ku = e => onKey(e, false);
  document.addEventListener('keydown', kd); document.addEventListener('keyup', ku);
  window.addEventListener('blur', () => st.keys.clear());

  // ---- frame ---------------------------------------------------------------------
  function lightsNow() {
    const key = `${st.themeId}|${st.tod}`; if (key !== st.lightsKey) { st.lightsKey = key; st.lights = st.theme.lights({tod: TOD[st.tod], cam: cam()}); }
    return st.lights;
  }
  function carryFor(rec) {
    if (!rec.doran) return null;
    if (rec.carryOverride) return rec.carryOverride === 'auto' ? autoCarry(rec) : rec.carryOverride;
    return autoCarry(rec);
  }
  function autoCarry(rec) {
    if (st.combat || rec.ent.swing || (rec.readyUntil || 0) > st.t) return 'ready';
    if (world.list().some(f => f.kind === 'actor' && f.team === 'foe' && f.alive && world.dist(f, rec.ent) < 16)) return 'ready';
    return st.hostile ? 'shoulder' : 'stowed';
  }
  function frame(now) {
    st.raf = 0; if (!st.running) return;
    if (!root.isConnected) { st.raf = requestAnimationFrame(frame); return; }
    if (document.hidden) { st.last = now; st.raf = requestAnimationFrame(frame); return; }
    const dt = clamp(now - (st.last || now), 0, 64); st.last = now; st.t += dt;
    if (!st.W) resize();
    if (st.W) { const t0 = performance.now(); tick(dt, now); st.tickMs += (performance.now() - t0 - st.tickMs) * .1; }
    st.raf = requestAnimationFrame(frame);
  }
  function tick(dt, now) {
    const reduced = opts.reducedMotion(), L = lead();
    // Held movement keys steer the lead continuously.
    if (st.keys.size && L && L.alive && !L.swing) {
      let dx = 0, dd = 0; for (const k of st.keys) { dx += KEYS[k][0]; dd += KEYS[k][1]; }
      if (dx || dd) { const run = st.shift; world.walkTo(L.id, L.x + dx * 2.6, clamp(L.d + dd * .1, .04, .96), {arrive: .2, run}); }
    }
    followers(L);
    for (const rec of st.things.values()) if (rec.kind === 'actor') {
      if ((rec.readyUntil || 0) > 0 && st.t > rec.readyUntil && !rec.ent.swing) rec.readyUntil = 0;
      const want = carryFor(rec); if (want !== rec.carry) { rec.carry = want; rec.node.dataset.carry = want || ''; if (rec.doran) refreshModel(rec, true); }
      const combat = want === 'ready' && !rec.doran; if (combat !== rec.wantCombat) { rec.wantCombat = combat; refreshModel(rec); }
    }
    for (const ev of world.step(dt, {lead: st.leadId})) handleEvent(ev);
    // Doors ease toward their target and close on their own after a while.
    for (const [key, d] of st.doors) {
      if (d.until && st.t > d.until) { d.target = 0; d.until = 0; }
      d.open += (d.target - d.open) * (reduced ? 1 : 1 - Math.exp(-dt / 110));
      const hov = st.hover?.kind === 'door' && st.hover.bay.key === key ? 1 : 0; d.hover += (hov - d.hover) * (1 - Math.exp(-dt / 90));
    }
    for (const rec of st.things.values()) {
      if (rec.kind === 'prop') {
        rec.open += (rec.openTo - rec.open) * (reduced ? 1 : 1 - Math.exp(-dt / 120));
        const e = rec.ent, P = project(e.x, e.d);
        const shake = rec.shakeUntil > st.t ? Math.sin(st.t * .09) * 3 * (st.H / 500) : 0;
        const fade = e.broken ? clamp(1 - (st.t - (rec.brokeAt || st.t)) / 240, 0, 1) : 1;
        rec.node.style.transform = `translate3d(${(P.sx - rec.ox + shake).toFixed(1)}px,${(P.sy - rec.oy).toFixed(1)}px,0) scale(${P.s.toFixed(3)})`;
        rec.node.style.zIndex = String(100 + Math.round(P.sy - (rec.decor ? 1 : 0)));
        rec.node.style.opacity = fade < 1 ? fade.toFixed(2) : '';
        rec.node.style.display = e.broken && fade <= 0 ? 'none' : '';
        rec.node.classList.toggle('is-open', rec.open > .5);
        if (!(e.broken && fade <= 0)) paintProp(rec);
      } else placeActor(rec, now);
    }
    if (st.needSync) { st.needSync = false; syncPuppets(root, {reducedMotion: opts.reducedMotion}); }
    drawBack(); drawFx(dt); drawLight();
    if (st.shake > .05) { st.shake *= Math.exp(-dt / 90); camEl.style.transform = `translate(${((Math.random() - .5) * st.shake).toFixed(1)}px,${((Math.random() - .5) * st.shake * .7).toFixed(1)}px)`; } else if (st.shake) { st.shake = 0; camEl.style.transform = ''; }
  }
  function followers(L) {
    if (!L || toolbox && !opts.follow) return;
    const rows = actorsOf('party').filter(r => r.id !== L.id && r.ent.alive);
    rows.forEach((rec, i) => {
      const e = rec.ent, tx = L.x - L.face * (2 + i * 1.7), td = clamp(L.d + (i % 2 ? .07 : -.07) * (1 + i * .3), .05, .95), dist = Math.hypot(e.x - tx, (e.d - td) * WORLD_DEPTH);
      if (e.swing || e.stagger > 0) return;
      const chase = dist > 1.6 || (L.moving && dist > .9);
      if (chase) world.walkTo(e.id, tx, td, {arrive: .5, run: dist > 6});
      else if (!e.goal && !L.moving && Math.abs(L.x - e.x) > .5 && !e.turn) world.faceEntity(e, L);
    });
  }
  function placeActor(rec, now) {
    const e = rec.ent, P = project(e.x, e.d), flip = opts.reducedMotion() ? 1 : world.flipOf(e), s = P.s;
    const entering = e.d > 1 ? clamp(1 - (e.d - 1) / .12, 0, 1) : 1;
    rec.node.style.transform = `translate3d(${(P.sx - rec.ox).toFixed(1)}px,${(P.sy - rec.oy - e.z * ppfAt(e.d)).toFixed(1)}px,0) scale(${(Math.max(.14, flip) * s * (e.d > 1 ? .9 : 1)).toFixed(3)},${(s * (e.d > 1 ? .9 : 1)).toFixed(3)})`;
    rec.node.style.zIndex = String(100 + Math.round(P.sy));
    rec.node.style.opacity = entering < 1 ? entering.toFixed(2) : '';
    const L = rec.last, d = rec.node.dataset;
    if (L.face !== e.face) { d.facing = String(e.face); L.face = e.face; }
    const p = world.turnProgress ? world.turnProgress(e) : 0;
    if (e.turn) { d.turnProgress = p.toFixed(2); } else if (d.turnProgress) { delete d.turnProgress; }
    const moving = e.moving && !e.swing && e.stagger <= 0, gait = moving ? e.gait.toFixed(2) : '0';
    if (L.gait !== gait) { d.gait = gait; L.gait = gait; }
    let beat = '';
    if (!e.alive) beat = ''; else if (e.stagger > 0) beat = e.hp / Math.max(1, e.max) < .3 ? 'crit' : 'hit'; else if (e.swing && rec.swingMode === 'beat') {
      beat = swingBeat(e, swingTiming(e.swing.style, e.weapon));
    } else if (moving) beat = 'move';
    if (L.beat !== beat) { if (beat) d.beat = beat; else delete d.beat; L.beat = beat; }
    const sw = e.swing && rec.swingMode === 'rig' ? e.swing.style : '';
    if (L.swing !== sw) { if (sw) { d.swing = sw; d.swingAt = String(Math.round(rec.swingAt || perf())); } else { delete d.swing; delete d.swingAt; } L.swing = sw; }
    else if (sw && d.swingAt !== String(Math.round(rec.swingAt))) d.swingAt = String(Math.round(rec.swingAt));
    // Footfall dust while running.
    if (moving && e.gait > 1.05 && (rec.dustAt || 0) < st.t) { rec.dustAt = st.t + 150; fx.puff(P.sx - e.face * 6, P.sy - 1, 1, '#b7ab99', st.H / 500 * s, e.face); }
    if (!e.alive || (e.hp <= 0 && rec.kind === 'actor')) rec.node.classList.add('is-down');
    rim(rec, P);
  }
  // A thin edge of the nearest strong lamp's colour on the side of a figure that faces it, so a figure
  // by the fire is lit by the fire. Quantised so the style only changes when the light really does.
  function rim(rec, P) {
    const t = st.t / 1000; let best = null, bestK = 0;
    lightsNow().forEach((L, i) => {
      if (L.kind === 'shaft' || L.a < .35 || L.r > .6) return;
      const lx = st.L + L.x * st.UW, ly = L.y * st.H, r = L.r * st.H * 1.05, d = Math.hypot(P.sx - lx, P.sy - rec.ent.body.height * ppfAt(rec.ent.d) * .5 - ly);
      if (d > r) return;
      const flick = L.flick ? 1 - L.flick * .5 * (1 + Math.sin(t * (L.hz || 5) + i * 1.7)) : 1, k = (1 - d / r) * L.a * flick;
      if (k > bestK) { bestK = k; best = {L, lx}; }
    });
    const q = best && bestK > .16 ? `${best.lx < P.sx ? -1 : 1}|${best.L.c}|${Math.round(bestK * 5)}` : '';
    if (rec.rimKey === q) return; rec.rimKey = q;
    rec.node.style.filter = q ? `drop-shadow(${best.lx < P.sx ? -1.6 : 1.6}px 0 0 ${rgba(best.L.c, Math.min(.75, bestK * 1.1))})` : '';
  }
  // Non-champion figures play windup / strike beats off the world's swing clock.
  function swingBeat(e, T) {
    const at = e.swing.at, into = world.time - at;
    const lead = e.weapon === 'daggers' ? 42 : 90, tail = e.weapon === 'daggers' ? 65 : 110;
    if (into < T.contactMs - lead) return 'windup'; if (into < T.contactMs + tail) return 'strike'; return '';
  }

  // ---- back layer, fx layer, light layer ------------------------------------
  function drawBack() {
    const c = liveCtx; c.setTransform(st.dpr, 0, 0, st.dpr, 0, 0); c.clearRect(0, 0, st.W, st.H);
    c.save(); c.translate(st.L, 0); drawLive(c, st.theme, st.UW, st.H, {t: st.t / 1000, bays: st.bays, doors: st.doors, tod: st.tod}); c.restore();
    // Contact shadows: one soft ellipse under each thing, scaled by its footprint and depth.
    for (const rec of st.things.values()) {
      const e = rec.ent; if (e.broken || (rec.decor && rec.art === 'banner')) continue;
      const P = project(e.x, e.d), sc = ppfAt(e.d), rx = Math.max(e.body.foot.rx, e.body.width * .32) * sc * 1.05, ry = rx * .2, a = rec.kind === 'actor' ? (e.alive ? .34 : .22) : .26;
      const g = c.createRadialGradient(P.sx, P.sy, 0, P.sx, P.sy, rx); g.addColorStop(0, `rgba(6,8,14,${a})`); g.addColorStop(1, 'rgba(6,8,14,0)');
      c.save(); c.translate(0, P.sy); c.scale(1, ry / rx); c.translate(0, -P.sy); c.fillStyle = g; c.beginPath(); c.arc(P.sx, P.sy, rx, 0, TAU); c.fill(); c.restore();
    }
  }
  function actorBox(rec) { const e = rec.ent, P = project(e.x, e.d), sc = ppfAt(e.d); return {P, sc, w: e.body.width * sc, h: e.body.height * sc}; }
  function drawWounds(c, rec) {
    const e = rec.ent; if (!e.wounds.length) return;
    const {P, sc, w, h} = actorBox(rec), S = st.H / 500 * sc / st.ppf0, mat = MATERIALS[e.material] || MATERIALS.flesh;
    let head = null, ground = null, chest = null, bodyRot = 0;
    if (rec.kind === 'actor') {
      head = figureSocket(rec.node, 'head', root); ground = figureSocket(rec.node, 'ground', root); chest = figureSocket(rec.node, 'chest', root);
      if (head && ground && !e.alive) bodyRot = Math.atan2(head.x - ground.x, ground.y - head.y);          // a fallen figure lies along its own axis
    }
    for (const wd of e.wounds) {
      const down = head && ground && !e.alive, topY = down ? head.y : head ? Math.min(head.y - h * .08, P.sy - h) : P.sy - h, botY = ground ? ground.y : P.sy;
      const y = lerp(topY, botY, wd.v), x = (down ? lerp(head.x, ground.x, wd.v) : chest ? chest.x : P.sx) + (down ? 0 : (wd.u - .5) * w * .8), len = wd.len * h * .5;
      paintWound(c, wd, {x, y, len, S, material: e.material, bodyRot});
    }
  }
  function drawFx(dt) {
    const c = fxCtx, S = st.H / 500; c.setTransform(st.dpr, 0, 0, st.dpr, 0, 0); c.clearRect(0, 0, st.W, st.H);
    if (!opts.reducedMotion()) { fx.stepAmbient(dt, st.W, st.H, S); fx.drawAmbient(c, S); }
    fx.step(dt);
    for (const rec of st.things.values()) if (!rec.ent.broken && rec.ent.wounds.length && !rec.decor) drawWounds(c, rec);
    // Health bars over whatever was hurt lately (or is hovered in the Toolbox).
    for (const [id, until] of st.hp) {
      const rec = st.things.get(id); if (!rec || rec.ent.broken || st.t > until) { if (!rec || st.t > until) st.hp.delete(id); continue; }
      const {P, w, h} = actorBox(rec), bw = clamp(w * 1.1, 34, 90), by = P.sy - h - 12 * S, k = clamp(rec.ent.hp / Math.max(1, rec.ent.max), 0, 1);
      c.fillStyle = 'rgba(8,10,18,.85)'; c.fillRect(P.sx - bw / 2 - 1.5, by - 1.5, bw + 3, 8 * S + 3);
      c.fillStyle = k > .5 ? '#5fbf6e' : k > .25 ? '#e0b64a' : '#d2473a'; c.fillRect(P.sx - bw / 2, by, bw * k, 8 * S);
      c.strokeStyle = 'rgba(232,225,207,.5)'; c.lineWidth = 1; c.strokeRect(P.sx - bw / 2 - .5, by - .5, bw + 1, 8 * S + 1);
    }
    fx.draw(c, S);
    if (st.debug) drawDebug(c, S);
  }
  function drawDebug(c, S) {
    c.save(); c.font = `${10 * S}px ui-monospace, monospace`; c.textAlign = 'left';
    for (const rec of st.things.values()) {
      const e = rec.ent, {P, sc, w, h} = actorBox(rec); if (rec.decor && !e.cuttable && rec.art === 'banner') continue;
      c.strokeStyle = rec.kind === 'actor' ? 'rgba(90,220,150,.9)' : 'rgba(240,200,90,.8)'; c.lineWidth = 1.2; c.strokeRect(P.sx - w / 2, P.sy - h, w, h);              // hurt box
      c.strokeStyle = 'rgba(90,170,255,.9)'; c.beginPath(); c.ellipse(P.sx, P.sy, e.body.foot.rx * sc, e.body.foot.rd * sc * .5 + 2, 0, 0, TAU); c.stroke();               // footprint
      if (rec.kind === 'actor' && e.body.reach) {                                                                                                                         // swing reach
        const S2 = e.swing ? SWING_STYLES[e.swing.style] : SWING_STYLES.chop, half = S2.arc / 2 * Math.PI / 180, r = (e.body.reach + 0) * sc, cy = P.sy - h * .62;
        c.strokeStyle = e.swing ? 'rgba(255,90,90,.95)' : 'rgba(255,140,90,.4)'; c.beginPath();
        if (S2.arc >= 180) c.arc(P.sx, cy, r, 0, TAU); else { c.moveTo(P.sx, cy); c.arc(P.sx, cy, r, e.face > 0 ? -half : Math.PI - half, e.face > 0 ? half : Math.PI + half); c.closePath(); } c.stroke();
      }
      c.fillStyle = 'rgba(232,225,207,.85)'; c.fillText(`${rec.id.replace(/^obj:|^decor-/, '')} ${e.body.height.toFixed(1)}ft${rec.kind === 'actor' ? ` r${e.body.reach.toFixed(1)}` : ''} ${Math.max(0, e.hp | 0)}/${e.max | 0}`, P.sx - w / 2, P.sy - h - 3);
    }
    c.restore();
  }
  function drawLight() {
    const c = lightCtx, w = lightEl.width, h = lightEl.height, k = w / st.W, t = st.t / 1000;
    const amb = tint(st.themeId, st.tod), lights = lightsNow();
    c.globalCompositeOperation = 'source-over'; c.fillStyle = mixHex(amb, '#ffffff', st.theme.indoor ? .12 : .26); c.fillRect(0, 0, w, h);
    c.globalCompositeOperation = 'lighter';
    lights.forEach((L, i) => {
      const flick = L.flick ? 1 - L.flick * .5 * (1 + Math.sin(t * (L.hz || 5) + i * 1.7) * Math.sin(t * (L.hz || 5) * 1.37 + i)) : 1, x = (st.L + L.x * st.UW) * k, y = L.y * st.H * k, r = L.r * st.H * k;
      if (L.kind === 'shaft') {
        const g = c.createLinearGradient(x, y, x + r * .3, y + r); g.addColorStop(0, rgba(L.c, L.a * .5)); g.addColorStop(1, rgba(L.c, 0));
        c.fillStyle = g; c.beginPath(); c.moveTo(x - r * .06, y); c.lineTo(x + r * .08, y); c.lineTo(x + r * .5, y + r * .95); c.lineTo(x + r * .16, y + r * .95); c.closePath(); c.fill(); return;
      }
      const g = c.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, rgba(L.c, L.a * flick)); g.addColorStop(.5, rgba(L.c, L.a * flick * .35)); g.addColorStop(1, rgba(L.c, 0));
      c.fillStyle = g; c.fillRect(x - r, y - r, r * 2, r * 2);
    });
    for (const f of fx.flashes) { const a = (1 - f.age / f.life) * f.a, x = f.x * k, y = f.y * k, r = f.r * k, g = c.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, rgba(f.c, a)); g.addColorStop(1, rgba(f.c, 0)); c.fillStyle = g; c.fillRect(x - r, y - r, r * 2, r * 2); }
    // Bloom over the brightest sources.
    const gc = glowCtx; gc.clearRect(0, 0, w, h);
    lights.forEach((L, i) => {
      if (L.kind === 'shaft' || L.a < .3 || L.r > .6) return;
      const flick = L.flick ? 1 - L.flick * .5 * (1 + Math.sin(t * (L.hz || 5) + i * 1.7)) : 1, x = (st.L + L.x * st.UW) * k, y = L.y * st.H * k, r = L.r * st.H * k * .45, g = gc.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, rgba(L.c, .28 * L.a * flick)); g.addColorStop(1, rgba(L.c, 0)); gc.fillStyle = g; gc.fillRect(x - r, y - r, r * 2, r * 2);
    });
  }

  // ---- lifecycle ------------------------------------------------------------------
  function start() { if (st.running) return; st.running = true; st.last = 0; resizeObs?.observe(root); requestAnimationFrame(() => { resize(); }); st.raf = requestAnimationFrame(frame); }
  function stop() { st.running = false; cancelAnimationFrame(st.raf); }
  function destroy() { stop(); resizeObs?.disconnect(); document.removeEventListener('keydown', kd); document.removeEventListener('keyup', ku); root.remove(); }
  addEventListener('keydown', e => { if (e.key === 'Shift') st.shift = true; }); addEventListener('keyup', e => { if (e.key === 'Shift') st.shift = false; });

  const api = {
    el: root, world, st, start, stop, destroy, resize, relayout() { resize(); layoutHotspots(); }, roomId: () => st.roomId, setRoom, syncView, walkLead, enterDoor, talkTo, useObject, activate, swing, toggleDoor, project, unproject, pick, fx,
    setDebug(on) { st.debug = Boolean(on); }, get debug() { return st.debug; },
    setCombat(on) { st.combat = Boolean(on); },
    on(type, fn) { (st.listeners.get(type) || st.listeners.set(type, new Set()).get(type)).add(fn); return () => st.listeners.get(type).delete(fn); },
    lead: () => st.things.get(st.leadId) || null, setLead(id) { if (st.things.has(id)) { st.leadId = id; actorsOf().forEach(r => r.node.classList.toggle('is-selected', r.id === id)); } },
    things: () => [...st.things.values()], thing: id => st.things.get(id) || null,
    // Toolbox controls.
    spawnActor(spec) { const rec = addActor(spec); if (spec.select) api.setLead(rec.id); refreshModel(rec, true); syncPuppets(root, {reducedMotion: opts.reducedMotion}); return rec; },
    spawnProp(kind, spec = {}) { return addProp(kind, {id: spec.id || `${kind}-${Math.random().toString(36).slice(2, 6)}`, x: spec.x ?? st.worldW * .5, d: spec.d ?? .4, scale: spec.scale || 1, cuttable: spec.cuttable ?? true, blocking: spec.blocking, hp: spec.hp, art: kind}); },
    remove: removeThing,
    clearThings({keepLead = false} = {}) { for (const id of [...st.things.keys()]) if (!(keepLead && id === st.leadId)) removeThing(id); fx.clear(); },
    setCarry(id, mode) { const rec = st.things.get(id); if (rec) { rec.carryOverride = mode; } },
    setScale(id, k) { const rec = st.things.get(id); if (!rec) return; rec.ent.body = bodyOf({...rec.item, scale: k}, rec.ent.weapon); sizeThing(rec); },
    heal(id) { world.heal(id); const rec = st.things.get(id); if (rec) { rec.node.style.display = ''; rec.node.style.opacity = ''; rec.node.classList.remove('is-down'); rec.ent.blocking = rec.kind === 'prop'; if (rec.kind === 'actor') refreshModel(rec, true); rec.sig = ''; syncPuppets(root, {reducedMotion: opts.reducedMotion}); } },
    hurt(id, style = 'chop') { const rec = st.things.get(id); if (rec) { world.hit(st.leadId, id, style); } },
    refresh(id) { const rec = st.things.get(id); if (rec) { refreshModel(rec, true); syncPuppets(root, {reducedMotion: opts.reducedMotion}); } },
    view: () => st.lastView, stats: () => ({tickMs: +st.tickMs.toFixed(2), things: st.things.size, particles: fx.p.length}),
    bakeInfo: () => ({key: st.bakeKey, W: st.W, H: st.H, worldW: st.worldW, ppf0: st.ppf0}),
    snapshot() {
      return {theme: st.themeId, tod: st.tod, size: [st.W, st.H], worldW: st.worldW, lead: st.leadId, doors: [...st.doors].map(([k, v]) => ({key: k, open: +v.open.toFixed(2)})),
        things: [...st.things.values()].map(r => { const e = r.ent, P = project(e.x, e.d); return {id: r.id, kind: r.kind, x: +e.x.toFixed(2), d: +e.d.toFixed(2), sx: Math.round(P.sx), sy: Math.round(P.sy), face: e.face, moving: e.moving, hp: e.hp, max: e.max, height: +e.body.height.toFixed(2), reach: +e.body.reach.toFixed(2), carry: r.carry || '', swing: e.swing?.style || '', wounds: e.wounds.length}; })};
    },
  };
  return api;
}
