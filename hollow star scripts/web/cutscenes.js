// Authored cutscenes for the Hollow Star. Data only: web/cutscene-player.js
// plays them. Sera, Ember, Soliera and Deashi never speak here (voice gate);
// only the Star and narration are drafted.
//
// unlock: {always: true} | {awareness: n} | {runs: n} | {flag: 'id'}

const svg = (w, h, body, extra = '') => `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg" ${extra}>${body}</svg>`;

// Deterministic starfield so every playback is identical.
function starfield(seed, count, w = 1600, h = 900) {
  let a = seed >>> 0;
  const r = () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  let out = '';
  for (let i = 0; i < count; i++) out += `<circle cx="${(r() * w).toFixed(0)}" cy="${(r() * h).toFixed(0)}" r="${(0.5 + r() * 1.6).toFixed(2)}" fill="#fff" opacity="${(0.25 + r() * 0.75).toFixed(2)}"/>`;
  return svg(w, h, out);
}

const VOID = svg(1600, 900, `<defs><radialGradient id="v" cx="50%" cy="55%" r="75%"><stop offset="0" stop-color="#15101f"/><stop offset=".6" stop-color="#07060c"/><stop offset="1" stop-color="#000"/></radialGradient></defs><rect width="1600" height="900" fill="url(#v)"/>`);

// The Hollow Star: a ring of light with nothing at its centre.
const HOLLOW_STAR = svg(400, 400, `<defs>
  <radialGradient id="hsGlow"><stop offset=".35" stop-color="#fff6d8" stop-opacity="0"/><stop offset=".48" stop-color="#fff6d8" stop-opacity=".95"/><stop offset=".56" stop-color="#e8c46a" stop-opacity=".6"/><stop offset="1" stop-color="#e8c46a" stop-opacity="0"/></radialGradient></defs>
  <circle cx="200" cy="200" r="190" fill="url(#hsGlow)"/>
  <g stroke="#fff3cf" stroke-width="2" opacity=".85">
    <path d="M200 20 L200 95 M200 305 L200 380 M20 200 L95 200 M305 200 L380 200"/>
    <path d="M73 73 L118 118 M282 282 L327 327 M327 73 L282 118 M73 327 L118 282" opacity=".5"/></g>
  <circle cx="200" cy="200" r="58" fill="#000"/>`);

// The Reliquary: an ornate cage-shrine, the place where a relic is held.
const RELIQUARY = svg(600, 700, `<defs><linearGradient id="rq" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3dc97"/><stop offset=".5" stop-color="#a47b2e"/><stop offset="1" stop-color="#4a3510"/></linearGradient></defs>
  <g fill="none" stroke="url(#rq)" stroke-width="6" stroke-linejoin="round">
    <path d="M300 30 L360 110 L240 110 Z"/><path d="M160 110 H440 V140 H160 Z"/>
    <path d="M180 140 V560 M420 140 V560 M240 140 V560 M360 140 V560 M300 140 V560" stroke-width="3" opacity=".8"/>
    <path d="M140 560 H460 L500 620 H100 Z"/><path d="M180 350 Q300 300 420 350" stroke-width="3"/>
    <circle cx="300" cy="70" r="9" fill="#f3dc97"/></g>`);

// A vessel built from parts, so a scene can move the cloak, head and core separately.
const FIGURE_BODY = svg(300, 600, `<path d="M150 150 C95 160 80 230 70 330 L55 560 H245 L230 330 C220 230 205 160 150 150Z" fill="#0d0b12" stroke="#2d2638" stroke-width="3"/>`);
const FIGURE_CLOAK = svg(300, 600, `<path d="M150 140 C60 170 30 330 20 590 H280 C270 330 240 170 150 140Z" fill="#141019" opacity=".92"/><path d="M150 140 C120 200 110 400 100 590" stroke="#2d2638" stroke-width="2" fill="none"/>`);
const FIGURE_HEAD = svg(120, 140, `<ellipse cx="60" cy="72" rx="44" ry="54" fill="#0d0b12" stroke="#2d2638" stroke-width="3"/>`);
const FIGURE_CORE = svg(120, 120, `<defs><radialGradient id="fc"><stop offset=".3" stop-color="#000" stop-opacity="0"/><stop offset=".45" stop-color="#fff6d8"/><stop offset=".6" stop-color="#e8c46a" stop-opacity=".5"/><stop offset="1" stop-color="#e8c46a" stop-opacity="0"/></radialGradient></defs><circle cx="60" cy="60" r="58" fill="url(#fc)"/>`);

const WELL = svg(700, 500, `<defs><radialGradient id="wd" cx="50%" cy="40%"><stop offset="0" stop-color="#000"/><stop offset="1" stop-color="#0c0a10"/></radialGradient></defs>
  <ellipse cx="350" cy="190" rx="280" ry="90" fill="url(#wd)" stroke="#3a3244" stroke-width="10"/>
  <path d="M70 190 V420 Q350 520 630 420 V190" fill="#15121b" stroke="#3a3244" stroke-width="6"/>
  <g stroke="#2a2432" stroke-width="3">${Array.from({length: 6}, (_, i) => `<path d="M${100 + i * 95} 250 V440"/>`).join('')}</g>
  <path d="M110 190 V40 H590 V190" fill="none" stroke="#3a3244" stroke-width="12"/><path d="M350 40 V150" stroke="#6b5f78" stroke-width="3"/>`);

const COCOON = svg(500, 700, `<defs><radialGradient id="cc" cx="50%" cy="45%"><stop offset="0" stop-color="#f7e7b5"/><stop offset=".45" stop-color="#b58d4a"/><stop offset="1" stop-color="#2a1d0c"/></radialGradient></defs>
  <path d="M250 20 C400 80 450 300 420 470 C400 600 330 680 250 690 C170 680 100 600 80 470 C50 300 100 80 250 20Z" fill="url(#cc)" stroke="#e8c46a" stroke-width="3"/>
  <g fill="none" stroke="#6b4c1c" stroke-width="3" opacity=".7">${Array.from({length: 7}, (_, i) => `<path d="M${95 + i * 5} ${130 + i * 75} Q250 ${100 + i * 80} ${405 - i * 5} ${130 + i * 75}"/>`).join('')}</g>`);

const PALACE = svg(1600, 900, `<defs><linearGradient id="pf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c1609"/><stop offset="1" stop-color="#0a0804"/></linearGradient></defs>
  <rect width="1600" height="900" fill="url(#pf)"/>
  <g fill="#2a2110" stroke="#6b5424" stroke-width="3">${Array.from({length: 8}, (_, i) => `<rect x="${60 + i * 205}" y="80" width="70" height="700"/><rect x="${45 + i * 205}" y="60" width="100" height="30"/>`).join('')}</g>
  <path d="M0 780 H1600 V900 H0Z" fill="#1a140a"/><path d="M0 780 H1600" stroke="#e8c46a" stroke-width="2" opacity=".5"/>`);

const DUST = svg(1600, 900, Array.from({length: 40}, (_, i) => `<circle cx="${(i * 397) % 1600}" cy="${(i * 211) % 900}" r="${1 + (i % 3)}" fill="#e8c46a" opacity=".35"/>`).join(''));

const figure = (id, x, y, extra = {}, spriteId = 'vessel') => ({
  id, kind: 'group', w: 300, h: 600, x, y, anchor: [0.5, 1], z: 10, ...extra,
  children: [
    {id: `${id}-cloak`, asset: `sprite.${spriteId}.cloak`, kind: 'svg', content: FIGURE_CLOAK, w: 300, h: 600, x: 150, y: 300, z: 1, loop: 'breathe', loopMs: 5200},
    {id: `${id}-body`, asset: `sprite.${spriteId}.body`, kind: 'svg', content: FIGURE_BODY, w: 300, h: 600, x: 150, y: 300, z: 2},
    {id: `${id}-head`, asset: `sprite.${spriteId}.head`, kind: 'svg', content: FIGURE_HEAD, w: 120, h: 140, x: 150, y: 110, z: 3},
    {id: `${id}-core`, asset: `sprite.${spriteId}.core`, kind: 'svg', content: FIGURE_CORE, w: 120, h: 120, x: 150, y: 250, z: 4, opacity: 0, loop: 'pulse', loopMs: 2600},
  ],
});

export const CUTSCENES = [
  {
    id: 'opening',
    title: 'Born Into Your Own Reliquary',
    blurb: 'Before the first vessel, there was a light with nothing inside it.',
    unlock: {always: true},
    thumb: HOLLOW_STAR,
    shots: [
      {layers: [
        {asset: 'cs.bg.void', id: 'void', kind: 'svg', content: VOID, w: 1600, h: 900, x: 800, y: 450, z: 0},
        {id: 'stars-far', kind: 'svg', content: starfield(3, 160), w: 1700, h: 960, x: 800, y: 450, z: 1, opacity: 0.6, in: {opacity: 0}, dur: 3000, loop: 'twinkle', loopMs: 7000},
        {id: 'stars-near', kind: 'svg', content: starfield(11, 50), w: 1800, h: 1000, x: 800, y: 450, z: 2, opacity: 0.9, in: {opacity: 0, scale: 1.1}, dur: 4000},
      ], audio: {music: 'music.hollow-star-theme'}, text: {style: 'narration', line: 'Before there was a door, there was a wish. Two of them, giggling.'}},
      {layers: [
        {id: 'star', asset: 'cs.hollow-star', kind: 'svg', content: HOLLOW_STAR, w: 400, h: 400, x: 800, y: 420, z: 5, scale: 0.35, opacity: 1, in: {opacity: 0, scale: 0.05}, dur: 2600, loop: 'pulse', loopMs: 3400},
      ], camera: {zoom: 1.08, dur: 3000}, text: {style: 'narration', line: 'Something was made to be held.'}},
      {layers: [
        {id: 'star', scale: 0.8, dur: 2200},
        {id: 'stars-near', x: 760, dur: 6000},
      ], text: {style: 'narration', line: 'A star, bright at every edge. Empty at the centre.'}},
      {flash: 'gold', layers: [
        {id: 'reliquary', asset: 'cs.reliquary', kind: 'svg', content: RELIQUARY, w: 600, h: 700, x: 800, y: 470, z: 4, opacity: 0.95, in: {opacity: 0, y: 560, scale: 0.9}, dur: 2400},
        {id: 'star', scale: 0.32, y: 400, dur: 2400},
      ], camera: {zoom: 1, dur: 2400}, text: {style: 'narration', line: 'Around it, a shrine rose up. Bars of gold. A place where a relic is kept.'}},
      {layers: [], text: {speaker: 'The Hollow Star', style: 'star', line: '…Is this mine?'}},
      {layers: [
        {id: 'title', kind: 'text', content: 'You are the Hollow Star', style: 'large', x: 800, y: 150, z: 20, in: {opacity: 0, y: 170}, dur: 1800},
      ], text: {style: 'narration', line: 'You are the relic. And you were born inside your own reliquary.'}},
      {layers: [
        {id: 'title', remove: true, dur: 600},
        figure('vessel', 800, 840, {opacity: 1, in: {opacity: 0}, dur: 2000}),
        {id: 'star', y: 560, scale: 0.12, dur: 2400, ease: 'cubic-bezier(.6,0,.4,1)'},
        {id: 'reliquary', opacity: 0.25, dur: 2000},
      ], camera: {zoom: 1.15, y: 60, dur: 2600}, text: {style: 'narration', line: 'Someone steps through the gate. They will do.'}},
      {flash: 'white', layers: [
        {id: 'star', opacity: 0, scale: 0.02, dur: 500},
        {id: 'vessel-core', opacity: 1, dur: 700},
      ], audio: {stinger: 'sfx.star-ignite'}, camera: {zoom: 1.15, y: 60, shake: 10, dur: 400}, text: {speaker: 'The Hollow Star', style: 'star', line: 'Oh. I can feel their hands. Warm.'}},
      {layers: [
        {id: 'sub', kind: 'text', content: 'Floor One · The Town Above the Well', style: 'small', x: 800, y: 110, z: 20, in: {opacity: 0}, dur: 1600},
      ], hold: 3600, text: {style: 'narration', line: 'Go on, then. Let us see what we become.'}},
    ],
  },
  {
    id: 'echo-well',
    title: 'The Well Remembers',
    blurb: 'Awareness I · Echo. The Star notices it has been here before.',
    unlock: {awareness: 1},
    thumb: WELL,
    shots: [
      {layers: [
        {asset: 'cs.bg.void', id: 'void', kind: 'svg', content: VOID, w: 1600, h: 900, x: 800, y: 450, z: 0},
        {id: 'stars', kind: 'svg', content: starfield(29, 90), w: 1600, h: 900, x: 800, y: 450, z: 1, opacity: 0.4},
        {id: 'well', asset: 'cs.well', kind: 'svg', content: WELL, w: 700, h: 500, x: 800, y: 560, z: 3, in: {opacity: 0, y: 600}, dur: 2400},
      ], text: {style: 'narration', line: 'The well at the centre of town. Stone, rope, a bucket that never quite reaches water.'}},
      {layers: [figure('vessel', 1180, 860, {scale: 0.8, in: {opacity: 0, x: 1300}, dur: 2200})],
        camera: {zoom: 1.1, x: 60, dur: 2400}, text: {speaker: 'The Hollow Star', style: 'star', line: 'This well. I have looked into it before.'}},
      {layers: [
        {id: 'ghost', kind: 'group', w: 300, h: 600, x: 460, y: 860, anchor: [0.5, 1], z: 4, scale: 0.8, opacity: 0.28, blur: 2, in: {opacity: 0}, dur: 3000, loop: 'flicker', loopMs: 1800,
          children: [{id: 'ghost-body', kind: 'svg', content: FIGURE_CLOAK, w: 300, h: 600, x: 150, y: 300}]},
      ], text: {style: 'narration', line: 'Across the stones, for a breath, another traveller stands where you stand. Then does not.'}},
      {layers: [{id: 'vessel-core', opacity: 1, dur: 800}],
        text: {speaker: 'The Hollow Star', style: 'star', line: 'Not through these eyes. Through someone else\'s.'}},
      {layers: [{id: 'ghost', remove: true, dur: 1600}], hold: 3200,
        text: {style: 'narration', line: 'The bucket drops. Far below, something counts the splash.'}},
    ],
  },
  {
    id: 'witness',
    title: 'What Outlives the Vessel',
    blurb: 'Awareness II · Witness. The vessel falls. The Star does not.',
    unlock: {awareness: 2},
    thumb: FIGURE_CORE,
    shots: [
      {layers: [
        {asset: 'cs.bg.void', id: 'void', kind: 'svg', content: VOID, w: 1600, h: 900, x: 800, y: 450, z: 0},
        figure('vessel', 800, 860, {in: {opacity: 0}, dur: 1600}),
        {id: 'vessel-core', opacity: 1},
      ], text: {style: 'narration', line: 'It ends the way these things end. Quickly, and then very slowly.'}},
      {flash: 'black', layers: [
        {id: 'vessel', opacity: 0, y: 900, rot: -8, dur: 2600, ease: 'ease-in'},
        {id: 'lone-star', asset: 'cs.hollow-star', kind: 'svg', content: HOLLOW_STAR, w: 400, h: 400, x: 800, y: 560, z: 12, scale: 0.18, in: {opacity: 0}, dur: 1200, loop: 'pulse', loopMs: 2400},
      ], camera: {shake: 14, dur: 300}, text: {speaker: 'The Hollow Star', style: 'star', line: 'You fell. I didn\'t.'}},
      {layers: [{id: 'lone-star', y: 420, scale: 0.4, dur: 3200}],
        text: {speaker: 'The Hollow Star', style: 'star', line: 'That seems unfair to you. I\'ll remember it for both of us.'}},
      {layers: [{id: 'names', kind: 'text', content: 'Every vessel is carried forward', style: 'small', x: 800, y: 160, z: 20, in: {opacity: 0}, dur: 1600}], hold: 3400,
        text: {style: 'narration', line: 'The Reliquary resets. The light in its centre does not.'}},
    ],
  },
  {
    id: 'keeper',
    title: 'Kept Things',
    blurb: 'Awareness III · Keeper. The Star starts choosing what to keep.',
    unlock: {awareness: 3},
    thumb: RELIQUARY,
    shots: [
      {layers: [
        {asset: 'cs.bg.void', id: 'void', kind: 'svg', content: VOID, w: 1600, h: 900, x: 800, y: 450, z: 0},
        {id: 'reliquary', asset: 'cs.reliquary', kind: 'svg', content: RELIQUARY, w: 600, h: 700, x: 800, y: 470, z: 3, in: {opacity: 0}, dur: 2000},
        {id: 'star', asset: 'cs.hollow-star', kind: 'svg', content: HOLLOW_STAR, w: 400, h: 400, x: 800, y: 440, z: 5, scale: 0.4, loop: 'pulse', loopMs: 3000},
      ], text: {style: 'narration', line: 'Inside the shrine, the hollow is not quite so hollow any more.'}},
      {layers: [
        {id: 'dust', kind: 'svg', content: DUST, w: 1600, h: 900, x: 800, y: 450, z: 6, in: {opacity: 0}, dur: 3000, loop: 'drift', loopMs: 9000},
      ], text: {speaker: 'The Hollow Star', style: 'star', line: 'A swordsman\'s patience. A thief\'s hands. A cleric\'s stubbornness.'}},
      {layers: [{id: 'star', scale: 0.55, dur: 2400}],
        text: {speaker: 'The Hollow Star', style: 'star', line: 'I kept them. I hope nobody minds.'}},
      {layers: [], hold: 3400, text: {style: 'narration', line: 'Somewhere far above, a very old fire feels its heart skip.'}},
    ],
  },
  {
    id: 'last-standing',
    title: 'I Won Again',
    blurb: 'The Opulent Palace. The last one standing. The Star steps out.',
    unlock: {flag: 'star_revealed'},
    thumb: COCOON,
    shots: [
      {layers: [
        {id: 'palace', asset: 'cs.bg.palace', kind: 'svg', content: PALACE, w: 1600, h: 900, x: 800, y: 450, z: 0},
        {id: 'cocoon', asset: 'cs.cocoon', kind: 'svg', content: COCOON, w: 500, h: 700, x: 800, y: 430, z: 3, opacity: 0.5},
        figure('vessel', 520, 860, {scale: 0.85}),
      ], audio: {music: null, ambience: 'amb.palace-silence'}, text: {style: 'narration', line: 'The palace is very quiet. Everyone else is dead.'}},
      {flash: 'gold', layers: [
        figure('mirror', 1080, 860, {scale: 0.85, in: {opacity: 0, blur: 12}, dur: 2600}, 'star-mirror'),
        {id: 'mirror-core', opacity: 1, dur: 1800},
      ], text: {speaker: 'The Hollow Star', style: 'star', line: 'Oh. So I won this time, too. …That\'s cool.'}},
      {layers: [], camera: {zoom: 1.2, x: 140, dur: 2400},
        text: {speaker: 'The Hollow Star', style: 'star', line: 'I wonder if next time, I\'ll be the one in there. Fighting you.'}},
      {layers: [{id: 'mirror', x: 900, dur: 900, ease: 'ease-in'}, {id: 'vessel', x: 700, dur: 900, ease: 'ease-in'}],
        flash: 'white', camera: {zoom: 1.2, shake: 22, dur: 300}, hold: 1800, text: {style: 'narration', line: 'Shall we find out?'}},
    ],
  },
];

export function cutsceneUnlocked(scene, star) {
  const u = scene.unlock || {};
  if (u.always) return true;
  if (!star) return false;
  if (u.awareness !== undefined) return (star.awareness?.tier ?? 0) >= u.awareness;
  if (u.runs !== undefined) return (star.runs ?? 0) >= u.runs;
  if (u.flag) return (star.flags || []).includes(u.flag);
  return false;
}
