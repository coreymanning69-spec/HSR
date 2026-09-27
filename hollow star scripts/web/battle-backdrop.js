// Battle backdrop and wounds: the main display's look, on the combat stage.
//
// The combat stage keeps its own layout, targeting and beat playback. This
// module only gives it the painted set of the room the fight is in, lit by the
// same lamps as the figures, and lets blows leave cuts on what they hit for the
// length of the fight. Presentation only: it reads what the director already
// resolved and decides nothing.
import {bakeSet, THEMES, todOf, TOD, tint} from './stage-set.js';
import {figureSocket} from './puppet-dom.js';
import {paintWound} from './stage-fx.js';
import {clamp, rgba, mixHex} from './actor-core.js';
import {clock} from './clock.js';

// ---- the painted set and its light ------------------------------------------------------
export function mountBattleBackdrop(stage, {themeId, tod = 'evening', seed = 'battle'} = {}) {
  if (!stage || !THEMES[themeId]) return;
  const W = stage.clientWidth, H = stage.clientHeight;
  if (!W || !H) return;
  const key = `${themeId}|${todOf(tod)}|${seed}|${W}x${H}`;
  if (stage.dataset.backdrop === key) return;
  stage.dataset.backdrop = key;
  const dpr = Math.min(2, devicePixelRatio || 1), theme = THEMES[themeId];
  let set = stage.querySelector(':scope > canvas.battle-set'), light = stage.querySelector(':scope > canvas.battle-light');
  if (!set) { set = document.createElement('canvas'); set.className = 'battle-set'; set.setAttribute('aria-hidden', 'true'); stage.prepend(set); }
  if (!light) { light = document.createElement('canvas'); light.className = 'battle-light'; light.setAttribute('aria-hidden', 'true'); stage.append(light); }
  const art = bakeSet(themeId, W, H, {seed, tod, bays: [], dpr});
  set.width = art.width; set.height = art.height; set.style.width = '100%'; set.style.height = '100%';
  set.getContext('2d').drawImage(art, 0, 0);
  light.width = Math.max(8, W >> 2); light.height = Math.max(8, H >> 2);
  stage.classList.add('has-set');
  const lights = theme.lights({tod: TOD[todOf(tod)], cam: theme.cam}), ambient = mixHex(tint(themeId, todOf(tod)), '#ffffff', theme.indoor ? .12 : .26);
  const draw = t => {
    const c = light.getContext('2d'), w = light.width, h = light.height;
    c.globalCompositeOperation = 'source-over'; c.fillStyle = ambient; c.fillRect(0, 0, w, h); c.globalCompositeOperation = 'lighter';
    lights.forEach((L, i) => {
      if (L.kind === 'shaft') return;
      const f = L.flick ? 1 - L.flick * .5 * (1 + Math.sin(t * (L.hz || 5) + i * 1.7) * Math.sin(t * (L.hz || 5) * 1.37 + i)) : 1, x = L.x * w, y = L.y * h, r = L.r * h;
      const g = c.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, rgba(L.c, L.a * f)); g.addColorStop(.5, rgba(L.c, L.a * f * .35)); g.addColorStop(1, rgba(L.c, 0));
      c.fillStyle = g; c.fillRect(x - r, y - r, r * 2, r * 2);
    });
  };
  draw(0);
  stage._backdropTimer?.(); stage._backdropTimer = null;
  const flickers = lights.some(l => l.flick);
  if (flickers && !matchMedia?.('(prefers-reduced-motion: reduce)').matches) stage._backdropTimer = clock.every(100, () => { if (!light.isConnected) { stage._backdropTimer?.(); stage._backdropTimer = null; return; } draw(performance.now() / 1000); });
}

// ---- wounds ----------------------------------------------------------------------------------
const materialOf = (node, name = '') => /golem|castellan|construct|automaton|armou?r|sentinel/i.test(name) ? 'metal' : /skeleton|zombie|wraith|drowned|ghoul|bone/i.test(name) ? 'undead' : 'flesh';
export function createWoundLayer({getStage, enabled = () => true, reducedMotion = () => false} = {}) {
  const store = new Map();                     // actor id -> {wounds, material}
  let canvas = null, off = null, run = '';
  function layer(stage) {
    if (canvas?.isConnected && canvas.parentElement === stage) return canvas;
    canvas = stage.querySelector(':scope > canvas.battle-wounds');
    if (!canvas) { canvas = document.createElement('canvas'); canvas.className = 'battle-wounds'; canvas.setAttribute('aria-hidden', 'true'); stage.append(canvas); }
    return canvas;
  }
  function add({node, actorNode, outcome, damage, damageType}) {
    const stage = getStage(); if (!stage || !node || !enabled() || reducedMotion()) return;
    if (!(Number(damage) > 0) || !['hit', 'crit'].includes(outcome)) return;
    if (stage.dataset.stageRun !== run) { store.clear(); run = stage.dataset.stageRun || ''; }
    const id = node.dataset.stageActor; if (!id) return;
    const row = store.get(id) || {wounds: [], material: materialOf(node, node.getAttribute('aria-label') || '')};
    const r = Math.random, kind = /pierc/.test(damageType || '') ? 'gash' : 'slash', dir = actorNode && actorNode.offsetLeft > node.offsetLeft ? -1 : 1;
    row.wounds.push({u: .3 + r() * .4, v: .22 + r() * .45, ang: (/bludg/.test(damageType || '') ? .3 : 1.1) * dir * (r() < .5 ? 1 : -1), len: clamp(.1 + Number(damage) / 60, .1, .32), kind, age: 0, seed: r()});
    if (row.wounds.length > 8) row.wounds.shift();
    store.set(id, row); start();
  }
  function start() { if (!off) off = clock.subscribe(frame, {priority: 30}); }
  function halt() { off?.(); off = null; }
  function frame(dt) {
    const stage = getStage();
    if (!stage || !store.size) { if (canvas) canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height); halt(); return; }
    const c = layer(stage), dpr = Math.min(2, devicePixelRatio || 1), W = stage.clientWidth, H = stage.clientHeight;
    if (c.width !== Math.round(W * dpr) || c.height !== Math.round(H * dpr)) { c.width = Math.round(W * dpr); c.height = Math.round(H * dpr); c.style.width = '100%'; c.style.height = '100%'; }
    const ctx = c.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    for (const [id, row] of store) {
      const node = stage.querySelector(`:scope > [data-stage-actor="${CSS.escape(id)}"]`); if (!node) continue;
      const head = figureSocket(node, 'head', stage), ground = figureSocket(node, 'ground', stage), chest = figureSocket(node, 'chest', stage);
      if (!head || !ground) continue;
      const down = node.classList.contains('is-down'), h = Math.max(50, ground.y - head.y), rot = down ? Math.atan2(head.x - ground.x, ground.y - head.y) : 0;
      for (const wd of row.wounds) {
        wd.age += dt;
        const y = down ? head.y + (ground.y - head.y) * wd.v : head.y + (ground.y - head.y) * wd.v, x = (down ? head.x + (ground.x - head.x) * wd.v : (chest?.x ?? head.x)) + (down ? 0 : (wd.u - .5) * h * .32);
        paintWound(ctx, wd, {x, y, len: wd.len * h * .5, S: h / 170, material: row.material, bodyRot: rot});
      }
    }
  }
  return {add, resume: start, clear() { store.clear(); }, has: () => store.size > 0};
}
