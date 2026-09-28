// Dialogue runner: branching conversations with conditions and effects, drawn
// in the same frame style as cutscenes (cutscene.css).
//
// A dialogue: {id, start, nodes: {nodeId: Node}}
// Node: {speaker, line, portrait?, style?: 'star'|'narration',
//        if?: Condition, else?: nodeId,          skip to `else` when `if` fails
//        set?: {flag: value},                    story flags set on entering
//        emit?: 'event-name',                    story event emitted on entering
//        choices?: [{text, next, if?: Condition, set?: {...}}],
//        next?: nodeId}                          no choices/next = conversation ends
// Condition (all keys must hold): {flag: 'x'} {flag: 'x', is: value} {not_flag: 'x'}
//   {awareness: n} (Star tier >= n) {party: 'divine:Wren'} {runs: n}
//
// Voice gate: a node with `voice_gate: true` or a line of '[COREY]' is an
// unwritten slot for a character the AI may not voice. It plays as a clearly
// marked placeholder instead of invented dialogue.

import {t} from './strings.js';

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

export function conditionHolds(cond, ctx) {
  if (!cond) return true;
  const flags = ctx.flags || {};
  if (cond.flag !== undefined && ('is' in cond ? flags[cond.flag] !== cond.is : !flags[cond.flag])) return false;
  if (cond.not_flag !== undefined && flags[cond.not_flag]) return false;
  if (cond.awareness !== undefined && (ctx.star?.awareness?.tier ?? 0) < cond.awareness) return false;
  if (cond.runs !== undefined && (ctx.star?.runs ?? 0) < cond.runs) return false;
  if (cond.party !== undefined && !(ctx.party || []).includes(cond.party)) return false;
  return true;
}

export function isUnwritten(node) {
  return Boolean(node?.voice_gate) || String(node?.line || '').trim() === '[COREY]';
}

// Pure stepping, separate from the DOM so it can be tested and reused by other UIs.
export function resolveNode(dialogue, id, ctx, guard = 0) {
  const node = dialogue.nodes[id];
  if (!node || guard > 50) return null;
  if (!conditionHolds(node.if, ctx)) return node.else ? resolveNode(dialogue, node.else, ctx, guard + 1) : null;
  return {id, ...node, choices: (node.choices || []).filter(choice => conditionHolds(choice.if, ctx))};
}

export function runDialogue(dialogue, {context = {}, onEffect = null, textSpeed = 34, host = document.body} = {}) {
  const ctx = {...context, flags: {...(context.flags || {})}};
  const root = document.createElement('div');
  root.className = 'dialogue-root';
  root.innerHTML = `<div class="cs-textbox dlg-box"><p class="cs-speaker"></p><p class="cs-line"></p><div class="dlg-choices"></div><span class="cs-caret" aria-hidden="true">▾</span></div>`;
  host.appendChild(root);
  requestAnimationFrame(() => root.classList.add('is-open'));
  const box = root.querySelector('.dlg-box');
  const speakerNode = root.querySelector('.cs-speaker');
  const lineNode = root.querySelector('.cs-line');
  const choicesNode = root.querySelector('.dlg-choices');
  let current = null; let typing = null; let resolve;
  const done = new Promise(r => { resolve = r; });

  const apply = node => {
    for (const [flag, value] of Object.entries(node.set || {})) { ctx.flags[flag] = value; onEffect?.({type: 'flag', flag, value}); }
    if (node.emit) onEffect?.({type: 'emit', event: node.emit});
  };
  const finishTyping = () => { typing?.(); typing = null; };
  const show = id => {
    finishTyping();
    current = id ? resolveNode(dialogue, id, ctx) : null;
    if (!current) return close();
    apply(current);
    const unwritten = isUnwritten(current);
    box.className = `cs-textbox dlg-box${current.style ? ` cs-${current.style}` : ''}${unwritten ? ' dlg-unwritten' : ''}`;
    speakerNode.textContent = current.speaker || '';
    speakerNode.hidden = !current.speaker;
    const line = unwritten ? t('dialogue.unwritten', {speaker: current.speaker || '?', id: current.id}) : String(current.line || '');
    choicesNode.innerHTML = '';
    box.classList.remove('is-done');
    let shown = 0;
    const reveal = () => {
      lineNode.textContent = line;
      box.classList.add('is-done');
      choicesNode.innerHTML = current.choices.map((choice, i) => `<button type="button" class="dlg-choice" data-choice="${i}">${esc(choice.text)}</button>`).join('');
      choicesNode.querySelector('button')?.focus({preventScroll: true});
    };
    if (!textSpeed || document.body.classList.contains('reduced-motion')) { reveal(); return; }
    lineNode.textContent = '';
    const timer = setInterval(() => { shown += 1; lineNode.textContent = line.slice(0, shown); if (shown >= line.length) { clearInterval(timer); typing = null; reveal(); } }, textSpeed);
    typing = () => { clearInterval(timer); reveal(); };
  };
  const advance = () => {
    if (typing) { finishTyping(); return; }
    if (current?.choices?.length) return;  // a choice must be picked
    show(current?.next);
  };
  const choose = index => {
    const choice = current?.choices?.[index];
    if (!choice) return;
    for (const [flag, value] of Object.entries(choice.set || {})) { ctx.flags[flag] = value; onEffect?.({type: 'flag', flag, value}); }
    show(choice.next);
  };
  const onKey = event => {
    if (event.key === 'Escape') { event.preventDefault(); close(); }
    else if ((event.key === ' ' || event.key === 'Enter') && !event.target.closest?.('.dlg-choice')) { event.preventDefault(); advance(); }
    else if (/^[1-9]$/.test(event.key)) choose(Number(event.key) - 1);
  };
  function close() {
    removeEventListener('keydown', onKey, true);
    root.classList.remove('is-open');
    setTimeout(() => root.remove(), 400);
    resolve({flags: ctx.flags, ended_at: current?.id || null});
  }
  root.addEventListener('click', event => {
    const choice = event.target.closest('.dlg-choice');
    if (choice) choose(Number(choice.dataset.choice)); else advance();
  });
  addEventListener('keydown', onKey, true);
  show(dialogue.start);
  return done;
}
