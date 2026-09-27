// Presentation only: screen changes and playback of host-authored public speech.
let paintedKey = null, pendingPaint = null, phase = 'idle', overlay = null, generation = 0;
function fadeOverlay() {
  if (!overlay) { overlay = document.createElement('div'); overlay.id = 'hsr-screen-fade'; overlay.setAttribute('aria-hidden', 'true'); document.body.append(overlay); }
  return overlay;
}
export const screenFade = {
  get active() { return phase !== 'idle'; },
  request(key, reduced, paint) {
    pendingPaint = {key, paint};
    if (reduced) {
      generation++; clearTimeout(this.timer); phase = 'idle'; paintedKey = key;
      overlay?.classList.remove('covered', 'revealing');
      overlay?.style.removeProperty('opacity'); overlay?.style.removeProperty('transition');
      paint(); return;
    }
    if (phase === 'out') return;
    if (paintedKey === null || reduced || key === paintedKey) {
      paintedKey = key; paint(); return;
    }
    if (phase === 'in') {
      // The latest destination wins; cover again before replacing the screen.
      clearTimeout(this.timer);
    }
    const token = ++generation;
    phase = 'out';
    const cover = fadeOverlay(); cover.classList.remove('revealing');
    void cover.offsetWidth; // Establish transparent initial state before the first fade.
    cover.classList.add('covered');
    this.timer = setTimeout(() => {
      if (token !== generation) return;
      cover.style.transition = 'none'; cover.style.opacity = '1';
      const next = pendingPaint; paintedKey = next.key;
      next.paint();
      // Two frames ensure the replacement is laid out under a fully black cover.
      requestAnimationFrame(() => requestAnimationFrame(() => {
        if (token !== generation) return;
        // Navigation or a readout arriving during the black layout frames also wins.
        if (pendingPaint !== next) { paintedKey = pendingPaint.key; pendingPaint.paint(); }
        phase = 'in'; cover.classList.add('revealing');
        cover.style.removeProperty('transition'); void cover.offsetWidth;
        cover.classList.remove('covered'); cover.style.removeProperty('opacity');
        this.timer = setTimeout(() => { phase = 'idle'; cover.classList.remove('revealing'); }, 140);
      }));
    }, 100);
  },
};

let ambient = null, ambientTimer = null;
const readSeen = run => {
  try { return new Set(JSON.parse(localStorage.getItem(`hsr-ambient-seen:${run}`) || '[]')); }
  catch { return new Set(); }
};
function remember(a, id) {
  a.seen.add(id);
  try { localStorage.setItem(`hsr-ambient-seen:${a.runId}`, JSON.stringify([...a.seen].slice(-256))); } catch {}
}
export function syncAmbient({runId, scene, stage, paused, onLine}) {
  const location = scene.location || stage.roomId();
  if (!ambient || ambient.runId !== runId || ambient.location !== location) {
    if (ambient) {
      // Do not replay discarded lines when returning to a location.
      for (const item of ambient.queue) remember(ambient, item.id);
      if (ambient.current) remember(ambient, ambient.current.id);
      ambient.stage.clearSpeech();
    }
    ambient = {runId, location, stage, paused, onLine, queue: [], seen: readSeen(runId), current: null, remaining: 0, lastExchange: -Infinity};
  }
  Object.assign(ambient, {stage, paused, onLine});
  for (const event of scene.ambient_events || []) {
    if (event.location !== location || ambient.seen.has(event.id) || ambient.queue.some(row => row.id === event.id) || ambient.current?.id === event.id) continue;
    ambient.queue.push({id: event.id, lines: event.lines.slice(0, 2).map((line, i) => ({...line, deliveryId: `${event.id}:${i}`})).filter(line => !ambient.seen.has(line.deliveryId)), index: 0});
  }
  if (!ambientTimer) ambientTimer = setInterval(playAmbient, 100);
}
function playAmbient() {
  const a = ambient;
  if (!a) return;
  const blocked = !a.stage.el.isConnected || document.hidden || screenFade.active || a.paused();
  if (blocked) { a.stage.clearSpeech(); return; }
  if (a.remaining > 0) {
    a.stage.say(a.current.lines[a.current.index - 1]);
    a.remaining -= 100; return;
  }
  if (a.current && a.current.index >= a.current.lines.length) {
    remember(a, a.current.id); a.stage.clearSpeech(); a.current = null;
  }
  if (!a.current) {
    if (!a.queue.length || performance.now() - a.lastExchange < 30000) return;
    a.current = a.queue.shift(); a.lastExchange = performance.now();
  }
  const line = a.current.lines[a.current.index++];
  if (!line || !a.stage.st.things.has(line.speaker_id)) { a.current = null; a.stage.clearSpeech(); return; }
  a.remaining = Math.max(2800, Math.min(7000, line.text.length * 55));
  remember(a, line.deliveryId); a.stage.say(line); a.onLine(line);
}
