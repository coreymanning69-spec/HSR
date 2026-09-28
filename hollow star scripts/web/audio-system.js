// Audio system: plays sound the game points at by id. The sound files
// themselves are made outside this repo and listed in
// web/assets/audio-manifest.json; nothing here ships audio.
//
// Manifest entry: "id": {"src": "audio/music/floor1.ogg", "category": "music",
//                         "volume": 0.8, "loop": true}
// Categories: music, ambience, sfx, voice, ui. Each has its own volume, all
// under master. An id missing from the manifest (or a file that fails to load)
// is logged once and otherwise ignored, so content can reference sounds
// before they exist.
//
//   audio.playMusic('floor-1')              crossfades from whatever is playing
//   audio.playAmbience('well-wind')         second looping bed, independent of music
//   audio.play('door-open')                 one-shot (sfx/voice/ui by manifest category)
//   audio.stinger('star-reveal')            one-shot that ducks music briefly
//   audio.stopMusic() / audio.setVolumes({...}) / audio.status()

export const AUDIO_CATEGORIES = ['music', 'ambience', 'sfx', 'voice', 'ui'];
export const DEFAULT_AUDIO_SETTINGS = Object.freeze({muted: false, master: 0.8, music: 0.7, ambience: 0.6, sfx: 0.8, voice: 1, ui: 0.6});

export function createAudioSystem({manifestUrl = 'assets/audio-manifest.json', settings = () => DEFAULT_AUDIO_SETTINGS} = {}) {
  let manifest = null;
  const missing = new Set();
  const beds = {music: null, ambience: null};  // {id, el}
  let duck = 1;
  const ready = fetch(manifestUrl).then(r => (r.ok ? r.json() : {})).catch(() => ({}))
    .then(data => { manifest = data && typeof data.sounds === 'object' ? data.sounds : {}; return manifest; });

  const gain = (category, entry) => {
    const s = {...DEFAULT_AUDIO_SETTINGS, ...(settings() || {})};
    if (s.muted) return 0;
    return Math.max(0, Math.min(1, s.master * (s[category] ?? 1) * (entry?.volume ?? 1) * (category === 'music' ? duck : 1)));
  };
  const lookup = id => {
    const entry = manifest?.[id];
    if (!entry?.src) {
      if (!missing.has(id)) { missing.add(id); console.debug?.(`[audio] no manifest entry for "${id}"`); }
      return null;
    }
    return entry;
  };
  const element = (entry) => {
    const el = new Audio(entry.src);
    el.preload = 'auto';
    el.addEventListener('error', () => { if (!missing.has(entry.src)) { missing.add(entry.src); console.debug?.(`[audio] could not load ${entry.src}`); } }, {once: true});
    return el;
  };
  const fade = (el, to, ms) => new Promise(resolve => {
    if (!el) return resolve();
    const from = el.volume; const start = performance.now();
    const step = now => {
      const t = Math.min(1, (now - start) / Math.max(1, ms));
      el.volume = from + (to - from) * t;
      if (t < 1) requestAnimationFrame(step); else resolve();
    };
    requestAnimationFrame(step);
  });

  async function playBed(slot, id, {fadeMs = 1200} = {}) {
    await ready;
    if (beds[slot]?.id === id) return;
    const old = beds[slot];
    beds[slot] = null;
    if (old) fade(old.el, 0, fadeMs).then(() => old.el.pause());
    const entry = id ? lookup(id) : null;
    if (!entry) return;
    const category = slot;  // beds always use their slot's volume
    const el = element(entry);
    el.loop = entry.loop !== false;
    el.volume = 0;
    beds[slot] = {id, el, entry, category};
    try { await el.play(); } catch { /* autoplay blocked until first input; resumes on next call */ }
    fade(el, gain(category, entry), fadeMs);
  }

  async function play(id, {category} = {}) {
    await ready;
    const entry = lookup(id);
    if (!entry) return null;
    const el = element(entry);
    el.volume = gain(category || entry.category || 'sfx', entry);
    try { await el.play(); } catch {}
    return el;
  }

  async function stinger(id) {
    duck = 0.35; refresh();
    const el = await play(id, {category: 'sfx'});
    const restore = () => { duck = 1; refresh(); };
    if (el) el.addEventListener('ended', restore, {once: true}); else restore();
  }

  function refresh() {
    for (const bed of Object.values(beds)) if (bed) bed.el.volume = gain(bed.category, bed.entry);
  }

  return {
    ready,
    playMusic: (id, opts) => playBed('music', id, opts),
    stopMusic: (opts) => playBed('music', null, opts),
    playAmbience: (id, opts) => playBed('ambience', id, opts),
    stopAmbience: (opts) => playBed('ambience', null, opts),
    play, stinger, setVolumes: refresh,
    status: () => ({music: beds.music?.id || null, ambience: beds.ambience?.id || null, known: Object.keys(manifest || {}).length, missing: [...missing]}),
  };
}
