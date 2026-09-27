// Voice feed: on-screen speech cards, divine Presence narration, and
// sound-effect bursts for the commentary the engine attaches to events.
//
// Presentation only. The host decides who speaks and what they say
// (hollowstar/commentary.py, doran_voice.py, divine_voice.py); this module
// only paces and draws it. It lives on document.body, outside #app, so the
// full re-render app.js does on every state change never interrupts a card.

import {doranPortrait} from './doran-rig.js';
import {wrenPortrait} from './wren-rig.js';

export const DEFAULT_VOICE_SETTINGS = Object.freeze({
  cards: true,          // speech cards on screen
  presence: true,       // divine-channel narration band
  sfx: true,            // sound-effect bursts over the stage
  doran: true, sera: true, ember: true,
  ambient: true,        // Doran's exploration asides
  pace: 1,              // reading-time multiplier: 2 = cards linger twice as long
  maxCards: 3,          // visible at once; older cards retire early
  position: 'left',     // left | right | center
  log: true,            // also copy every line into the Messages log
});

// Who can speak and how they are drawn. Doran's medallion is a bust drawn by
// his paperdoll rig (sigil if a canvas is unavailable); the girls get designed
// sigils. Presence is never a person: it has no medallion or name.
export const SPEAKERS = Object.freeze({
  Doran: {role: 'Field Steward', sigil: 'D', get portrait() { return doranPortrait(); }},
  Wren: {role: 'Field Steward', sigil: 'W', get portrait() { return wrenPortrait(); }},
  Sera: {role: 'The Executioner', sigil: 'S'},
  Ember: {role: 'The Inquiry', sigil: 'E'},
});

const TAGS = {divine: 'Answering Wren', reply: 'Replying', ambient: 'Aside'};
const CASCADE_MS = 420;       // stagger between lines that arrive together
const PRESENCE_MS = 5200;

const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[ch]));

export function createVoiceFeed({settings = () => DEFAULT_VOICE_SETTINGS, reducedMotion = () => false, locate = () => null} = {}) {
  let layer = null, stack = null, band = null;
  let cascadeUntil = 0;
  const conf = () => ({...DEFAULT_VOICE_SETTINGS, ...(settings() || {})});

  function mount() {
    if (layer?.isConnected) return;
    layer = document.createElement('div');
    layer.className = 'hsr-voice-layer';
    layer.innerHTML = '<div class="voice-presence" role="status" aria-live="polite"></div><div class="voice-stack" role="log" aria-live="polite" aria-label="Party voices"></div>';
    document.body.append(layer);
    band = layer.querySelector('.voice-presence');
    stack = layer.querySelector('.voice-stack');
  }

  // Lines arriving in one burst cascade so they read as a conversation.
  function slot() {
    const now = performance.now();
    const at = Math.max(now, cascadeUntil);
    cascadeUntil = at + CASCADE_MS;
    return at - now;
  }

  function readMs(text, pace) {
    return Math.min(11000, 2600 + String(text).length * 52) * Math.max(0.4, Number(pace) || 1);
  }

  function retire(card) {
    if (!card || card.dataset.leaving) return;
    card.dataset.leaving = '1';
    clearTimeout(card._timer);
    card.classList.add('is-leaving');
    setTimeout(() => card.remove(), reducedMotion() ? 0 : 260);
  }

  function arm(card, ms) {
    const bar = card.querySelector('.voice-timer');
    let left = ms, started = performance.now();
    const run = () => {
      started = performance.now();
      card._timer = setTimeout(() => retire(card), left);
      if (bar && !reducedMotion()) { bar.style.transition = 'none'; bar.style.transform = `scaleX(${left / ms})`; bar.getBoundingClientRect(); bar.style.transition = `transform ${left}ms linear`; bar.style.transform = 'scaleX(0)'; }
    };
    card.addEventListener('mouseenter', () => { clearTimeout(card._timer); left = Math.max(600, left - (performance.now() - started)); if (bar) { const now = getComputedStyle(bar).transform; bar.style.transition = 'none'; bar.style.transform = now; } });
    card.addEventListener('mouseleave', run);
    card.addEventListener('click', () => retire(card));
    run();
  }

  function card(line) {
    const who = SPEAKERS[line.speaker] || {role: '', sigil: String(line.speaker || '?').slice(0, 1)};
    const key = String(line.speaker || 'voice').toLowerCase();
    const medallion = who.portrait
      ? `<span class="voice-portrait" style="background-image:url('${esc(who.portrait)}')"></span>`
      : `<span class="voice-sigil">${esc(who.sigil)}</span>`;
    const tag = line.first_time ? 'First answer' : TAGS[line.register] || '';
    const node = document.createElement('article');
    node.className = `voice-card speaker-${esc(key)} register-${esc(line.register || 'commentary')}${line.priority === 'high' ? ' is-high' : ''}`;
    node.setAttribute('aria-label', `${line.speaker}: ${line.text}`);
    node.innerHTML = `<div class="voice-medallion" aria-hidden="true">${medallion}</div><div class="voice-body"><header><strong>${esc(line.speaker)}</strong>${who.role ? `<small>${esc(who.role)}</small>` : ''}${tag ? `<em>${esc(tag)}</em>` : ''}</header><p>${esc(line.text)}</p></div><i class="voice-timer" aria-hidden="true"></i>`;
    return node;
  }

  function allowed(line, c) {
    const who = String(line.speaker || '').toLowerCase();
    if (line.register === 'presence') return c.presence;
    if (!c.cards) return false;
    if (line.register === 'ambient' && !c.ambient) return false;
    return c[who] !== false;
  }

  function speak(line) {
    const c = conf();
    if (!line?.text || !allowed(line, c)) return false;
    mount();
    stack.dataset.position = c.position;
    if (line.register === 'presence') { setTimeout(() => presence(line.text), slot()); return true; }
    setTimeout(() => {
      const node = card(line);
      stack.append(node);
      const live = [...stack.querySelectorAll('.voice-card:not(.is-leaving)')];
      live.slice(0, Math.max(0, live.length - Math.max(1, Number(c.maxCards) || 3))).forEach(retire);
      // Reflow, then enter: works even where rAF is paused (background tabs).
      node.getBoundingClientRect(); node.classList.add('is-in');
      arm(node, readMs(line.text, c.pace));
    }, slot());
    return true;
  }

  function presence(text) {
    mount();
    band.innerHTML = `<p><span aria-hidden="true">✧</span> ${esc(text)} <span aria-hidden="true">✧</span></p>`;
    band.classList.remove('is-in'); band.getBoundingClientRect(); band.classList.add('is-in');
    clearTimeout(band._timer);
    band._timer = setTimeout(() => band.classList.remove('is-in'), PRESENCE_MS * Math.max(0.5, Number(conf().pace) || 1));
  }

  // A comic-style burst anchored on the struck figure when the stage has one.
  function sfx(cue) {
    const c = conf();
    if (!c.sfx || !cue?.text) return false;
    mount();
    const anchor = locate(cue.target) || document.querySelector('#app .combat-stage') || null;
    const box = anchor?.getBoundingClientRect();
    const x = box ? box.left + box.width / 2 : innerWidth / 2;
    const y = box ? box.top + Math.min(box.height * 0.35, 120) : innerHeight * 0.32;
    const node = document.createElement('div');
    const loud = /[A-Z]{3,}|!/.test(cue.text);
    node.className = `voice-sfx trigger-${esc(cue.trigger || 'combat')}${loud ? ' is-loud' : ''}`;
    node.textContent = cue.text;
    node.style.left = `${Math.round(x + (Math.random() * 60 - 30))}px`;
    node.style.top = `${Math.round(y)}px`;
    node.style.setProperty('--tilt', `${Math.round(Math.random() * 14 - 7)}deg`);
    node.setAttribute('aria-hidden', 'true');
    layer.append(node);
    setTimeout(() => node.remove(), reducedMotion() ? 900 : 1500);
    return true;
  }

  function clear() {
    stack?.querySelectorAll('.voice-card').forEach(retire);
    band?.classList.remove('is-in');
    layer?.querySelectorAll('.voice-sfx').forEach(node => node.remove());
    cascadeUntil = 0;
  }

  // Options-page preview using the real renderer.
  function demo() {
    clear();
    sfx({text: 'KRAK!', trigger: 'combat'});
    [
      {speaker: 'Doran', text: 'Through, not around.', register: 'reaction'},
      {speaker: 'Sera', text: 'Hit it again, Shiny. It didn\'t learn yet.', register: 'commentary'},
      {speaker: 'Ember', text: 'Three questions? Only three? I have more than three for YOU.', register: 'divine', first_time: true, priority: 'high'},
      {speaker: 'Presence', text: 'For a moment the line is very quiet and very wide, and every answer lands in order.', register: 'presence'},
    ].forEach(speak);
  }

  return {speak, sfx, presence, clear, demo};
}
