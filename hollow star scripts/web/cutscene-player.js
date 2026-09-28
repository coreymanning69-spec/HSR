// Layered cutscene player: Flash-timeline style compositing for HSR.
//
// A scene is a list of shots. Layers persist across shots by id (like symbols
// on a Flash timeline): a shot may add a layer, tween an existing one to new
// properties, or remove it. Layers can be groups of child layers, so a figure
// can be built from separate parts (body, head, cloak, glow) and animated as
// one sprite, the way AdventureQuest composes its characters.
//
// Stage space is a fixed 1600x900 canvas scaled to fit the screen, so authored
// coordinates never depend on the window size.
//
// Layer spec:
//   {id, kind: 'svg'|'image'|'text'|'fill'|'group', z, x, y, w, h, scale, rot,
//    opacity, blur, blend, anchor: [ax, ay], content|src|children,
//    loop: 'pulse'|'drift'|'twinkle'|'flicker'|'breathe'|'spin', loopMs,
//    in: {…props to start from}, dur, ease, delay, remove: true}
// Shot spec:
//   {layers: [...], camera: {x, y, zoom, rot, shake, dur}, text: {speaker, line, style},
//    hold: ms (auto-advance; omit to wait for input), flash: 'white'|'gold'|'black'}

const STAGE_W = 1600;
const STAGE_H = 900;
const NUMERIC = ['x', 'y', 'scale', 'rot', 'opacity', 'blur'];
const DEFAULTS = {x: 0, y: 0, scale: 1, rot: 0, opacity: 1, blur: 0};
const LOOPS = {
  pulse: [{opacity: 1, transform: 'scale(1)'}, {opacity: 0.72, transform: 'scale(1.06)'}, {opacity: 1, transform: 'scale(1)'}],
  breathe: [{transform: 'translateY(0) scale(1)'}, {transform: 'translateY(-6px) scale(1.012)'}, {transform: 'translateY(0) scale(1)'}],
  drift: [{transform: 'translate(0,0)'}, {transform: 'translate(18px,-10px)'}, {transform: 'translate(0,0)'}],
  twinkle: [{opacity: 1}, {opacity: 0.25}, {opacity: 1}],
  flicker: [{opacity: 1}, {opacity: 0.8}, {opacity: 0.95}, {opacity: 0.6}, {opacity: 1}],
  spin: [{transform: 'rotate(0deg)'}, {transform: 'rotate(360deg)'}],
};
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const reducedMotion = () => globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

function transformOf(p, anchor) {
  const [ax, ay] = anchor || [0.5, 0.5];
  return `translate(${p.x}px, ${p.y}px) translate(${-ax * 100}%, ${-ay * 100}%) rotate(${p.rot}deg) scale(${p.scale})`;
}
function styleOf(p, anchor) {
  return {transform: transformOf(p, anchor), opacity: String(p.opacity), filter: p.blur ? `blur(${p.blur}px)` : 'none'};
}

function buildNode(spec) {
  const node = document.createElement('div');
  node.className = `cs-layer cs-${spec.kind || 'svg'}`;
  node.dataset.layer = spec.id;
  if (spec.w) node.style.width = `${spec.w}px`;
  if (spec.h) node.style.height = `${spec.h}px`;
  if (spec.blend) node.style.mixBlendMode = spec.blend;
  const inner = document.createElement('div');
  inner.className = 'cs-inner';
  node.appendChild(inner);
  if (spec.kind === 'image') inner.innerHTML = `<img src="${esc(spec.src)}" alt="" draggable="false">`;
  else if (spec.kind === 'text') inner.innerHTML = `<span class="cs-title-text ${esc(spec.style || '')}">${esc(spec.content)}</span>`;
  else if (spec.kind === 'fill') inner.style.background = spec.content || '#000';
  else if (spec.kind !== 'group') inner.innerHTML = spec.content || '';  // authored SVG, trusted scene data
  return node;
}

export class CutscenePlayer {
  constructor({host = document.body, onEnd = null} = {}) {
    this.host = host;
    this.onEnd = onEnd;
    this.layers = new Map();  // id -> {node, props, anchor, loopAnim}
    this.index = -1;
    this.typing = null;
    this.ended = false;
  }

  play(scene) {
    this.scene = scene;
    this.root = document.createElement('div');
    this.root.className = 'cutscene-root';
    this.root.setAttribute('role', 'dialog');
    this.root.setAttribute('aria-label', scene.title || 'Cutscene');
    this.root.innerHTML = `
      <div class="cs-viewport"><div class="cs-camera"><div class="cs-stage"></div></div>
        <div class="cs-flash"></div><div class="cs-vignette"></div><div class="cs-grain"></div>
        <div class="cs-letterbox cs-top"></div><div class="cs-letterbox cs-bottom"></div>
        <div class="cs-textbox" hidden><p class="cs-speaker"></p><p class="cs-line"></p><span class="cs-caret" aria-hidden="true">▾</span></div>
      </div>
      <div class="cs-chrome"><span class="cs-scene-title">${esc(scene.title || '')}</span>
        <span class="cs-pips">${scene.shots.map(() => '<i></i>').join('')}</span>
        <button type="button" class="cs-skip">Skip ›</button></div>`;
    this.host.appendChild(this.root);
    this.viewport = this.root.querySelector('.cs-viewport');
    this.camera = this.root.querySelector('.cs-camera');
    this.stage = this.root.querySelector('.cs-stage');
    this.fit = () => {
      const s = Math.min(this.viewport.clientWidth / STAGE_W, this.viewport.clientHeight / STAGE_H);
      this.stage.style.transform = `scale(${s})`;
      this.stage.style.left = `${(this.viewport.clientWidth - STAGE_W * s) / 2}px`;
      this.stage.style.top = `${(this.viewport.clientHeight - STAGE_H * s) / 2}px`;
    };
    this.fit();
    addEventListener('resize', this.fit);
    this.onKey = event => {
      if (event.key === 'Escape') { event.preventDefault(); this.end(); }
      else if ([' ', 'Enter', 'ArrowRight'].includes(event.key)) { event.preventDefault(); this.advance(); }
    };
    addEventListener('keydown', this.onKey, true);
    this.root.querySelector('.cs-skip').onclick = event => { event.stopPropagation(); this.end(); };
    this.viewport.onclick = () => this.advance();
    requestAnimationFrame(() => this.root.classList.add('is-open'));
    this.done = new Promise(resolve => { this.resolve = resolve; });
    this.next();
    return this.done;
  }

  advance() {
    if (this.ended) return;
    if (this.typing) { this.typing.finish(); return; }  // first press completes the line
    this.next();
  }

  next() {
    clearTimeout(this.holdTimer);
    this.index += 1;
    if (this.index >= this.scene.shots.length) { this.end(); return; }
    const shot = this.scene.shots[this.index];
    this.root.querySelectorAll('.cs-pips i').forEach((pip, i) => pip.classList.toggle('on', i <= this.index));
    if (shot.flash) this.flash(shot.flash);
    if (shot.camera) this.moveCamera(shot.camera);
    for (const spec of shot.layers || []) this.applyLayer(spec, this.stage);
    this.showText(shot.text);
    if (shot.hold) this.holdTimer = setTimeout(() => { if (!this.typing) this.next(); else this.pendingAuto = true; }, shot.hold);
  }

  applyLayer(spec, parent) {
    const fast = reducedMotion();
    const existing = this.layers.get(spec.id);
    if (spec.remove) {
      if (!existing) return;
      const anim = existing.node.animate([{opacity: existing.props.opacity}, {opacity: 0}], {duration: fast ? 0 : spec.dur ?? 500, fill: 'forwards', easing: 'ease-in'});
      anim.onfinish = () => existing.node.remove();
      this.layers.delete(spec.id);
      return;
    }
    const target = {};
    for (const key of NUMERIC) if (spec[key] !== undefined) target[key] = spec[key];
    let entry = existing;
    if (!entry) {
      const node = buildNode(spec);
      node.style.zIndex = String(spec.z ?? 0);
      parent.appendChild(node);
      entry = {node, props: {...DEFAULTS, ...target}, anchor: spec.anchor};
      this.layers.set(spec.id, entry);
      for (const child of spec.children || []) this.applyLayer(child, node.querySelector('.cs-inner'));
      const from = {...entry.props, ...(spec.in || {})};
      Object.assign(node.style, styleOf(entry.props, entry.anchor));
      if (spec.in && !fast) {
        node.animate([styleOf(from, entry.anchor), styleOf(entry.props, entry.anchor)],
          {duration: spec.dur ?? 900, delay: spec.delay ?? 0, easing: spec.ease || 'cubic-bezier(.2,.7,.2,1)', fill: 'backwards'});
      }
    } else {
      if (spec.z !== undefined) entry.node.style.zIndex = String(spec.z);
      const before = {...entry.props};
      entry.props = {...entry.props, ...target};
      Object.assign(entry.node.style, styleOf(entry.props, entry.anchor));
      if (!fast) entry.node.animate([styleOf(before, entry.anchor), styleOf(entry.props, entry.anchor)],
        {duration: spec.dur ?? 900, delay: spec.delay ?? 0, easing: spec.ease || 'cubic-bezier(.4,0,.2,1)', fill: 'backwards'});
      if (spec.content !== undefined && spec.kind !== 'group') entry.node.querySelector('.cs-inner').innerHTML = spec.content;
    }
    if (spec.loop !== undefined) {
      entry.loopAnim?.cancel();
      entry.loopAnim = null;
      if (spec.loop && LOOPS[spec.loop] && !fast) {
        entry.loopAnim = entry.node.querySelector('.cs-inner').animate(LOOPS[spec.loop],
          {duration: spec.loopMs ?? 4000, iterations: Infinity, easing: spec.loop === 'spin' ? 'linear' : 'ease-in-out'});
      }
    }
  }

  moveCamera({x = 0, y = 0, zoom = 1, rot = 0, shake = 0, dur = 1400}) {
    const fast = reducedMotion();
    const to = `translate(${-x}px, ${-y}px) scale(${zoom}) rotate(${rot}deg)`;
    const from = this.camera.style.transform || 'none';
    this.camera.style.transform = to;
    if (!fast) this.camera.animate([{transform: from}, {transform: to}], {duration: dur, easing: 'cubic-bezier(.45,0,.2,1)'});
    if (shake && !fast) {
      this.viewport.animate(Array.from({length: 9}, (_, i) => ({transform: i === 8 ? 'none' : `translate(${(Math.random() - 0.5) * shake}px, ${(Math.random() - 0.5) * shake}px)`})),
        {duration: 420, easing: 'linear'});
    }
  }

  flash(color) {
    if (reducedMotion()) return;
    const node = this.root.querySelector('.cs-flash');
    node.style.background = color === 'gold' ? 'var(--cs-gold, #e8c46a)' : color === 'black' ? '#000' : '#fff';
    node.animate([{opacity: 0.95}, {opacity: 0}], {duration: 900, easing: 'ease-out'});
  }

  showText(text) {
    const box = this.root.querySelector('.cs-textbox');
    this.typing?.finish();
    if (!text) { box.hidden = true; return; }
    box.hidden = false;
    box.className = `cs-textbox ${text.style ? `cs-${text.style}` : ''}`;
    box.querySelector('.cs-speaker').textContent = text.speaker || '';
    box.querySelector('.cs-speaker').hidden = !text.speaker;
    const lineNode = box.querySelector('.cs-line');
    const line = String(text.line || '');
    box.classList.remove('is-done');
    if (reducedMotion()) { lineNode.textContent = line; box.classList.add('is-done'); return; }
    let shown = 0;
    lineNode.textContent = '';
    const finish = () => {
      clearInterval(timer);
      lineNode.textContent = line;
      box.classList.add('is-done');
      this.typing = null;
      if (this.pendingAuto) { this.pendingAuto = false; this.holdTimer = setTimeout(() => this.next(), 900); }
    };
    const timer = setInterval(() => {
      shown += 1;
      lineNode.textContent = line.slice(0, shown);
      if (shown >= line.length) finish();
    }, text.speed ?? 34);
    this.typing = {finish};
  }

  end() {
    if (this.ended) return;
    this.ended = true;
    clearTimeout(this.holdTimer);
    this.typing?.finish();
    removeEventListener('keydown', this.onKey, true);
    removeEventListener('resize', this.fit);
    this.root.classList.remove('is-open');
    this.root.classList.add('is-closing');
    setTimeout(() => this.root.remove(), reducedMotion() ? 0 : 700);
    this.onEnd?.(this.scene);
    this.resolve?.(this.scene);
  }
}

export function playCutscene(scene, options = {}) {
  return new CutscenePlayer(options).play(scene);
}
