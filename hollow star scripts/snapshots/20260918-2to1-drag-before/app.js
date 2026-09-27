import {createHSRClient} from './hsr-client.js?v=compact-envelope-1';
import {createArcadeCanvas} from './arcade-canvas.js';
import {bindArcadeInput} from './arcade-input.js';
import {createArcadeLoop} from './arcade-loop.js';
import {championPoseArt, getChampionPosePath, resolveChampionPose} from './sprite-renderer.js';

const E = globalThis.HSRUI.escape;
const screens = ['journey', 'room', 'battle', 'equipment', 'roster', 'residents', 'journal', 'map', 'library', 'options'];
const ABILITIES = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA'];
const ABILITY_NAMES = {STR: 'Strength', DEX: 'Dexterity', CON: 'Constitution', INT: 'Intelligence', WIS: 'Wisdom', CHA: 'Charisma'};
const FLAVOR = {
  activity: [
    'Aligning the star charts without touching the canon.',
    'Asking the host politely; escalating to telemetry if ignored.',
    'Cataloguing reality, one suspiciously tidy response at a time.',
    'Checking the wires. The wires insist they are fine.',
    'Counting doors twice. The Reliquary dislikes optimistic arithmetic.',
    'Polishing the public view until the hidden machinery stops showing.',
  ],
  screens: {
    journey: 'The route is public. The consequences are not yet decided.',
    room: 'Every room is honest about its walls and selective about its motives.',
    battle: 'Tactical clarity first; dramatic lighting is merely traditional.',
    equipment: 'A good loadout is an argument made out of metal, cloth, and bad intentions.',
    roster: 'The party is a set of capabilities, not a queue of hero poses.',
    residents: 'Ask carefully. People who live in impossible places practice answering.',
    journal: 'Only witnessed facts enter the record. Rumour may wait outside.',
    map: 'A map is a promise that distance has agreed to be measurable.',
    library: 'The catalogue remembers what the room would prefer you forget.',
    options: 'Tune the interface; leave the underlying reality gloriously alone.',
  },
  actions: {
    inspect: 'Read the object’s public tells before deciding what it deserves.',
    investigate: 'Spend attention now; certainty is rarely discounted later.',
    enter: 'Cross the threshold and let the room update its opinion of you.',
    descend: 'Go lower. The architecture has been saving its best arguments.',
    rest: 'Recover what can be recovered; assume the room is taking notes.',
    exit: 'Leave while leaving is still a choice.',
    attack: 'Resolve violence through the host; the interface only carries the intent.',
    move: 'Change position without pretending movement is consequence-free.',
    cast: 'Commit a spell to the public resolution queue.',
    conversation: 'Open a social channel. Courtesy is optional; information is not.',
    identify: 'Expose the Rune’s name and let its liabilities become legible.',
    escape: 'Attempt the most expensive kind of movement: getting away.',
  },
};
const preferenceKey = 'hsr-display-preferences';
const workspaceKey = 'hsr-workspace-layout-v1';
const defaultPreferences = {scenario: '', scenarioSeed: '', iconActions: false, menuDensity: 'comfortable', layout: 'sanctum', sceneScale: 'standard', dockPosition: 'bottom', showParty: true, showNavigation: true, accent: 'gold', textScale: '1', motion: 'full', effects: 'full', showClock: true, showTickIndicator: true};
function readPreferences() {
  try { return {...defaultPreferences, ...JSON.parse(localStorage.getItem(preferenceKey) || '{}')}; }
  catch { return {...defaultPreferences}; }
}
function readWorkspaceLayout() {
  try { return JSON.parse(localStorage.getItem(workspaceKey) || '{}'); }
  catch { return {}; }
}
function saveWorkspaceLayout() {
  try { localStorage.setItem(workspaceKey, JSON.stringify(state.workspaceLayout)); } catch {}
}
function encounterActive(view = state.view) {
  return Boolean((view?.combat && !view.combat.complete) || (view?.arcade && !view.arcade.complete));
}
function encounterStepActor(view = state.view) {
  const combat = view?.combat;
  if (!combat || combat.complete) return '';
  return combat.pending?.[0]?.reactor || combat.current || '';
}
function selectGameplayScreen(screen) {
  if (!screens.includes(screen) || state.selected === screen) return;
  state.selected = screen;
  persistUiState();
  history.replaceState(null, '', `#${screen}`);
}
function syncEncounterScreen(previousView, nextView) {
  const wasActive = encounterActive(previousView);
  const isActive = encounterActive(nextView);
  if (!wasActive && isActive) selectGameplayScreen('battle');
  else if (wasActive && !isActive) selectGameplayScreen('room');
}
function actionTargets(action) {
  const room = state.view?.room || {};
  const objects = Object.values(room.objects || {}).filter(row => row && row.visible !== false).map(row => ({
    value: row.object_id || row.id, label: objectLabel(row), kind: 'object',
  })).filter(row => row.value);
  const opponents = (state.view?.opposition || []).filter(
    row => row && row.alive !== false && row.hp !== 0,
  ).map(row => ({
    value: row.id || row.npc_id || row.name, label: row.name || row.id, kind: 'target',
  })).filter(row => row.value);
  const exits = Object.entries(room.exits || {}).map(([direction, destination]) => ({
    value: destination?.id || destination, label: `${direction}: ${readable(destination)}`, kind: 'destination',
  })).filter(row => row.value);
  if (['inspect', 'inspect_object', 'search_object', 'open_object'].includes(action)) return objects;
  if (['attack', 'maneuver'].includes(action)) return opponents;
  if (action === 'move' && state.view?.combat && !state.view.combat.complete) {
    const current = state.view.combat.current;
    const selected = [...party(), ...(state.view.opposition || [])].find(row => row.id === current) || {};
    const origin = Array.isArray(selected.position) ? selected.position : [10, 10, 0];
    const cells = [];
    for (const dx of [-10, -5, 5, 10]) for (const dy of [-10, -5, 0, 5, 10]) {
      if (!dx && !dy) continue;
      const x = Math.max(0, Math.min(120, origin[0] + dx));
      const y = Math.max(0, Math.min(120, origin[1] + dy));
      cells.push({value: `${x},${y},${origin[2]}`, label: `${x} ft / ${y} ft`, kind: 'destination'});
    }
    return cells;
  }
  if (['move_room', 'enter'].includes(action)) return exits;
  return [];
}
function targetPicker() {
  const picker = state.actionPicker;
  if (!picker) return '';
  const choices = actionTargets(picker.action);
  return `<section class="hsr-target-picker" aria-live="polite"><strong>${E(picker.label)} — choose a target</strong><div class="target-choices">${choices.map(choice => button(choice.label, `target-choice:${picker.action}:${choice.kind}:${choice.value}`, 'secondary')).join('')}</div>${choices.length ? '' : '<p class="notice">No visible target is available for this action.</p>'}${button('Cancel', 'cancel-target-picker', 'secondary')}</section>`;
}
function savePreferences() {
  try { localStorage.setItem(preferenceKey, JSON.stringify(state.preferences)); } catch (error) { state.note = `Preferences could not be saved: ${error.message}`; }
  applyPreferences();
}
function applyPreferences() {
  document.body.classList.toggle('icon-actions', state.preferences.iconActions);
  document.body.classList.toggle('compact-menu', state.preferences.menuDensity === 'compact');
  document.body.classList.toggle('reduced-motion', state.preferences.motion === 'reduced');
  document.body.classList.toggle('soft-effects', state.preferences.effects === 'soft');
  document.body.dataset.layout = state.preferences.layout;
  document.body.dataset.density = state.preferences.menuDensity;
  document.body.dataset.sceneScale = state.preferences.sceneScale;
  document.body.dataset.dock = state.preferences.dockPosition;
  document.body.dataset.party = state.preferences.showParty ? 'shown' : 'hidden';
  document.body.dataset.navigation = state.preferences.showNavigation ? 'shown' : 'hidden';
  document.body.dataset.accent = state.preferences.accent;
  document.documentElement.style.setProperty('--text-scale', state.preferences.textScale);
}
function readAccountIdentity() {
  try {
    let id = localStorage.getItem('hsr-account-identity');
    if (!id) { id = `local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`; localStorage.setItem('hsr-account-identity', id); }
    return id;
  } catch { return 'local-player'; }
}
// character_options has no live champions field yet; this is a fallback, not the source of truth.
// If the host ever adds state.options.champions, championRoster() below prefers it automatically.
const DEFAULT_CHAMPIONS = [
  {id: 'Doran', title: 'Tier-3 Sanctum field Steward', blurb: 'Mirror-white divine plate, a giant cleaver, and obsidian daggers. Melee-forward, hard to put down.'},
  {id: 'Wren', title: 'Tier-3 Sanctum field Steward', blurb: 'Domain and concentration lanes: mass cures, saves turned to successes, and short-range teleportation for the party.'},
];
function championRoster() {
  return Array.isArray(state.options?.champions) && state.options.champions.length ? state.options.champions : DEFAULT_CHAMPIONS;
}
const MANEUVERS = [
  {maneuver: 'Rally', label: 'Rally', needsTarget: true},
  {maneuver: 'Commanding Presence', label: 'Commanding Presence', needsTarget: false},
  {maneuver: 'Trip Attack', label: 'Trip Attack', needsTarget: true},
  {maneuver: 'Menacing Attack', label: 'Menacing Attack', needsTarget: true},
];
const DOMAIN_FEATURES = [
  {feature: 'Indomitable Spirit', label: 'Indomitable Spirit'},
  {feature: 'simulacrum', label: 'Call Simulacrum'},
];
const UPGRADE_TRACKS = {
  precision: {cap: 5, base_cost: 2, effect: '+1 permanent accuracy per tier'},
  force: {cap: 5, base_cost: 2, effect: '+1 permanent weapon damage per tier'},
  ward: {cap: 5, base_cost: 2, effect: '+1 permanent AC per tier'},
  reserve: {cap: 5, base_cost: 2, effect: '+1 starting healing potion per tier'},
  mastery_capacity: {cap: 5, base_cost: 3, effect: '+1 Gem upgrade capacity per tier'},
};
const CONVERSATION_MODES = [
  {mode: 'ask', label: 'Ask'}, {mode: 'lie', label: 'Lie'},
  {mode: 'threaten', label: 'Threaten'}, {mode: 'insult', label: 'Insult'},
  {mode: 'trade', label: 'Trade'},
];
const state = {
  phase: 'title', route: ['title'], transport: 'local-gateway', client: createHSRClient(), view: null, receipt: null,
  runId: null, runs: [], runsFilter: null, debugReadout: null, options: null, draft: {name: '', race: 'human', gender: 'female',
  character_class: 'warrior', background: 'veteran', creation_seed: '', level: 1, roll_set: 0,
  ability_assignment: 'auto', floating_bonuses: 'auto', advancements: 'auto', advancement_mode: 'auto',
  skills: 'auto', skill_mode: 'auto', spells: 'auto', spell_mode: 'auto', spell_budget: 0}, preview: null,
  roll: null, live: null, liveError: '', stepAnim: '', rollAnim: false,
  affixes: null, catalog: null, scenarios: null, vocabulary: null, preferences: readPreferences(),
  selected: screens.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'room',
  selectedActor: null,
  busy: false, connected: false, note: '', error: '', refreshed: null, initialized: false, activity: {label: 'Idle', started: 0, requests: 0, line: 'Awaiting a request; the reliquary is pretending to be patient.'}, requestKeys: new Set(),
  pendingMode: 'DESIGN', accountIdentity: readAccountIdentity(), progression: null, terminal: null,
  pendingConversation: null, consoleDraft: '', actionPicker: null, presentation: null,
  arcadeUi: null, staleSandbox: null, lastManeuver: null, trayState: 'compact', arrangeMode: false,
  workspaceLayout: readWorkspaceLayout(),
  messageHistory: [], messageHistoryOpen: false,
  clockTick: 0, showClock: true, showTickIndicator: true,
};
// Initialize display preferences from stored prefs
state.showClock = state.preferences.showClock !== false;
state.showTickIndicator = state.preferences.showTickIndicator !== false;
try {
  const saved = JSON.parse(sessionStorage.getItem('hsr-ui-state') || '{}');
  if (!location.hash && screens.includes(saved.selected)) state.selected = saved.selected;
  if (saved.draft && typeof saved.draft === 'object') state.draft = {...state.draft, ...saved.draft};
  if (saved.roll && typeof saved.roll === 'object' && Array.isArray(saved.roll.scores)) state.roll = saved.roll;
} catch {}
function persistUiState() {
  try { sessionStorage.setItem('hsr-ui-state', JSON.stringify({selected: state.selected, draft: state.draft, roll: state.roll})); } catch {}
}
const gameplayLabels = {journey: 'Journey', room: 'Sanctum', battle: 'Encounters', equipment: 'Relics', roster: 'Party', residents: 'Residents', journal: 'Chronicle', map: 'Atlas', library: 'Library', options: 'Options'};
const mobileScreens = ['room', 'battle', 'roster', 'equipment', 'residents'];
function routeTitle() {
  if (state.phase === 'ready') return gameplayLabels[state.selected] || 'Reliquary';
  const labels = {transport:'Connection', 'menu-story':'Story Mode', 'menu-simulation':'Simulation Mode', 'party-select':'Choose Party', 'champion-select':'Champions', create:'Character Workshop', preview:'Character Preview', runs:'Continue', statistics:'Statistics', 'edit-scenario':'Edit Scenario', cheats:'Cheats', options:'Options'};
  return labels[state.phase] || 'Hollow Star';
}
function topNavigation() {
  if (state.phase === 'title') return '';
  return `<nav class="mobile-topbar" aria-label="Page navigation"><button type="button" class="topbar-button" data-action="back" aria-label="Go back">‹ <span>Back</span></button><strong>${E(routeTitle())}</strong><button type="button" class="topbar-button" data-action="title" aria-label="Main menu"><span>Menu</span> ☰</button></nav>`;
}
function statusClock() {
  if (!state.showClock) return '';
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  const tickIcon = state.showTickIndicator ? `<span class="tick-pulse" data-tick="${state.clockTick % 2}">●</span>` : '';
  const runInfo = state.runId ? `<span class="run-info">${E(state.runId.slice(0, 8))}</span>` : '';
  return `<div class="status-clock"><div class="time-display">${tickIcon}<strong>${hours}:${minutes}:${seconds}</strong></div>${runInfo}</div>`;
}
function mobileNavigation() {
  if (state.phase !== 'ready') return '';
  const navButtons = mobileScreens.map(tab => `<button type="button" class="mobile-nav-item ${state.selected === tab ? 'active' : ''}" data-action="tab:${E(tab)}" aria-current="${state.selected === tab ? 'page' : 'false'}" title="${E(gameplayLabels[tab])}"><span aria-hidden="true">${({room:'⌂',battle:'⚔',roster:'♙',equipment:'◇',residents:'☵'})[tab]}</span><small>${E(gameplayLabels[tab])}</small></button>`).join('');
  const moreButton = `<button type="button" class="mobile-nav-item ${!mobileScreens.includes(state.selected) ? 'active' : ''}" data-action="tab:options" title="More options"><span aria-hidden="true">•••</span><small>More</small></button>`;
  return `<nav class="mobile-game-nav" aria-label="Game screens">${navButtons}${moreButton}</nav>`;
}
function partyHud() {
  if (state.phase !== 'ready' || !party().length) return '';
  return `<button type="button" class="mobile-party-hud" data-action="tab:roster" aria-label="Open party">${party().map(member => { const hp = Number(value(member, 'hp', 'current_hp') || 0); const max = Math.max(1, Number(value(member, 'max_hp') || 1)); return `<span><b>${E(member.name || member.id)}</b><i><em style="width:${Math.max(0, Math.min(100, hp / max * 100))}%"></em></i><small>${E(hp)}/${E(max)}</small></span>`; }).join('')}</button>`;
}
function trayHandle() {
  if (state.phase !== 'ready' || (!actionBar() && !consoleBar())) return '';
  const label = state.trayState === 'collapsed' ? 'Open controls' : state.trayState === 'expanded' ? 'Compact controls' : 'Expand controls';
  return `<div class="tray-handle"><button type="button" data-action="cycle-tray" aria-label="${label}"><i></i><span>${E(label)}</span></button></div>`;
}

const party = () => state.view?.party || [];
const actor = () => party().find(item => item.id === state.selectedActor) || party()[0] || {};
const value = (object, ...keys) => keys.map(key => object?.[key]).find(item => item !== undefined && item !== null);
const card = (title, body, extra = '') => `<section class="card ${extra}"><p class="label">${E(title)}</p>${body}</section>`;
const button = (label, action, extra = '') => `<button type="button" class="action ${extra}" data-action="${E(action)}" title="${E(label)}">${E(label)}</button>`;
function navigationState() { return {hsr:true, phase:state.phase, route:[...state.route], selected:state.selected}; }
function go(phase) {
  if (state.route[state.route.length - 1] !== phase) state.route.push(phase);
  state.phase = phase;
  if (state.initialized) history.pushState(navigationState(), '', location.href);
}
function back() {
  state.route.pop(); state.phase = state.route[state.route.length - 1] || 'title';
  if (!state.route.length) state.route = ['title'];
  history.replaceState(navigationState(), '', location.href);
}
function menuList(rows) { return `<div class="actions menu-list">${rows.map(([label, action, extra]) => button(label, action, extra || '')).join('')}</div>`; }
function breadcrumb(...crumbs) { return `<nav class="breadcrumb" aria-label="Navigation">${crumbs.map((c, i) => i === crumbs.length - 1 ? `<span aria-current="page">${E(c)}</span>` : `<span>${E(c)}</span>`).join(' <span class="breadcrumb-sep">/</span> ')}</nav>`; }

function addMessage(text, type = 'note') {
  const timestamp = new Date().toLocaleTimeString();
  state.messageHistory.push({text, type, timestamp});
  if (state.messageHistory.length > 100) state.messageHistory.shift();
}
function fail(message) {
  state.error = message;
  state.note = 'Last displayed public state retained. Refresh before retrying an uncertain action.';
  addMessage(message, 'error');
}
const ACTIVITY_LINES = FLAVOR.activity;
function messagePanel() {
  const historyHtml = state.messageHistory.length ? state.messageHistory.map(msg => `<div class="message-row ${E(msg.type)}"><span class="message-timestamp">${E(msg.timestamp)}</span><span class="message-text">${E(msg.text)}</span></div>`).join('') : '<p class="message-empty">No messages yet.</p>';
  return `<div class="hsr-message-panel" data-panel="messages"><div class="panel-header"><strong>Messages & Errors</strong><button type="button" data-action="clear-messages" class="secondary" aria-label="Clear history">Clear</button><button type="button" data-action="close-messages" aria-label="Close panel">×</button></div><div class="message-history">${historyHtml}</div></div>`;
}
function consoleBar() {
  if (state.runId && state.phase === 'ready') {
    const hint = state.pendingConversation ? `Replying to ${state.pendingConversation.npc} · ${state.pendingConversation.mode}` : 'Command or chat line to the host';
    return `<form id="console-form" class="hsr-console is-input" data-panel="console"><div class="panel-header"><strong>${E(hint)}</strong><button type="button" data-action="toggle-messages" aria-label="Open messages">📋</button></div><div class="actions"><input id="console-input" name="console" required autocomplete="off" placeholder="Inspect the room…" value="${E(state.consoleDraft || '')}"><button class="action">Send</button>${state.pendingConversation ? button('Cancel', 'cancel-conversation', 'secondary') : ''}</div></form>`;
  }
  return '';
}
function result(reply) {
  if (!reply.ok) throw Error(reply.error?.message || reply.error?.code || 'Host request failed');
  if (reply.public_view) {
    const previousView = state.view;
    state.view = reply.public_view;
    state.receipt = reply.public_receipt;
    state.presentation = reply.public_receipt?.presentation || reply.public_receipt?.evidence?.presentation || reply.result?.presentation || reply.result?.outcome?.presentation || null;
    state.runId = reply.run_id || state.runId;
    state.refreshed = new Date();
    syncEncounterScreen(previousView, state.view);
  }
  return reply;
}
// The loading popup lives outside #app, so render() never rebuilds it. Requests
// that finish inside the grace delay never reveal it; the tick touches only its text.
const LOADING_GRACE_MS = 180;
const LOADING_TICK_MS = 120;
function loadingPopup() {
  const root = document.querySelector('#hsr-loading');
  const slot = name => root?.querySelector(`[data-loading-${name}]`);
  const nodes = {label: slot('label'), line: slot('line'), requests: slot('requests'), elapsed: slot('elapsed')};
  const set = (node, text) => { if (node && node.textContent !== text) node.textContent = text; };
  return {
    tick() {
      const a = state.activity;
      set(nodes.elapsed, `${((performance.now() - a.started) / 1000).toFixed(1)}s elapsed`);
      set(nodes.requests, `${a.requests} active request${a.requests === 1 ? '' : 's'}`);
    },
    arm() { this.tick(); root?.classList.add('is-busy'); },
    reveal() { set(nodes.label, state.activity.label); set(nodes.line, state.activity.line); this.tick(); root?.classList.add('is-shown'); },
    dismiss() { root?.classList.remove('is-shown', 'is-busy'); },
  };
}
async function work(fn, label = 'Working', line = '') {
  if (state.busy) return;
  state.busy = true; state.error = ''; state.activity = {label, started: performance.now(), requests: 1, line: line || ACTIVITY_LINES[Math.floor(Date.now()/1800) % ACTIVITY_LINES.length]};
  const app = document.querySelector('#app'); const popup = loadingPopup();
  let reveal = 0; let ticker = 0;
  try {
    app?.setAttribute('aria-busy', 'true'); popup.arm();
    reveal = setTimeout(() => popup.reveal(), LOADING_GRACE_MS);
    ticker = setInterval(() => popup.tick(), LOADING_TICK_MS);
    render();
    await fn();
  } catch (error) { fail(error.message); }
  finally {
    clearInterval(ticker); clearTimeout(reveal); popup.dismiss(); app?.removeAttribute('aria-busy');
    state.busy = false; state.activity = {...state.activity, requests: 0, label: 'Ready'}; render();
  }
}
async function boot() {
  const reply = result(await state.client.boot('DESIGN'));
  state.note = reply.ok ? 'Local gateway ready.' : '';
  const options = await state.client.characterOptions();
  if (options?.ok) state.options = options.result;
}
async function connect(mode = state.transport, nextPhase = 'title') {
  // The current screen (title, transport picker, or the gameplay shell) stays
  // behind the loading popup. Stale state is dropped inside work() so a busy
  // client is never swapped out mid-request; a failure stays on that screen.
  await work(async () => {
    state.view = null; state.receipt = null; state.connected = false;
    state.transport = mode;
    state.client = createHSRClient({mode});
    const [health, bootReply] = await Promise.all([state.client.health(), state.client.boot('DESIGN')]);
    if (!health.ok) throw Error(health.error?.message || 'Host unavailable');
    result(bootReply);
    const [optionsReply, affixReply, catalogReply, vocabularyReply] = await Promise.all([
      state.client.characterOptions(), state.client.affixCatalog(), state.client.contentCatalog(), state.client.sessionVocabulary()
    ]);
    if (optionsReply?.ok) state.options = optionsReply.result;
    if (affixReply?.ok) state.affixes = affixReply.result?.affixes;
    if (catalogReply?.ok) state.catalog = catalogReply.result?.content || null;
    if (vocabularyReply?.ok) state.vocabulary = vocabularyReply.result;
    state.connected = true;
    go(nextPhase); state.note = 'Local gateway ready.';
  }, 'Opening the Reliquary', 'Refreshing engine state…');
}
function title() {
  return `<div class="intro-screen">
    <div class="intro-background">
      <svg viewBox="0 0 1600 900" class="intro-art" preserveAspectRatio="xMidYMid slice">
        <defs>
          <linearGradient id="skyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style="stop-color:#1a1f35;stop-opacity:1" />
            <stop offset="50%" style="stop-color:#2d3a52;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#0d111b;stop-opacity:1" />
          </linearGradient>
          <radialGradient id="moonGrad" cx="50%" cy="40%">
            <stop offset="0%" style="stop-color:#f5e6d3;stop-opacity:1" />
            <stop offset="80%" style="stop-color:#e8d4b8;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#c9a86a;stop-opacity:0.8" />
          </radialGradient>
        </defs>
        <rect width="1600" height="900" fill="url(#skyGrad)"/>
        <g class="intro-sun">
          <circle cx="1100" cy="200" r="180" fill="url(#moonGrad)" opacity="0.95"/>
          <circle cx="1100" cy="200" r="180" fill="none" stroke="rgba(201,168,106,0.3)" stroke-width="2" opacity="0.6"/>
        </g>
        <g class="intro-clouds" fill="#cbd0d733">
          <path d="M80 230 C160 175 245 205 282 250 C350 218 438 250 452 300 L55 300 C42 272 53 246 80 230Z"/>
          <path d="M1190 330 C1260 285 1330 302 1372 344 C1430 320 1514 350 1538 395 L1160 395 C1150 370 1160 345 1190 330Z"/>
        </g>
        <g class="intro-mountains">
          <polygon points="0,600 200,300 500,600" fill="#1a2333" opacity="0.8"/>
          <polygon points="250,650 600,250 900,650" fill="#253548" opacity="0.7"/>
          <polygon points="700,700 1100,350 1500,700" fill="#1f2d42" opacity="0.75"/>
          <polygon points="1200,750 1400,400 1600,750" fill="#2a3a52" opacity="0.8"/>
        </g>
      </svg>
    </div>
    <div class="intro-content">
      <section class="intro-card">
        <h1 class="intro-title">Hollow Star Reliquary</h1>
        <p class="intro-subtitle">Enter a world of divine mystery and tactical combat</p>
        <div class="intro-actions">
          ${button('Story Mode', 'menu:menu-story', 'intro-action-primary')}
          ${button('Simulation Mode', 'menu:menu-simulation', 'intro-action-primary')}
          ${button('Options', 'menu:options', 'intro-action-secondary')}
        </div>
        <p class="intro-mode-help">Story Mode carries the Reliquary's authored module; Simulation Mode is the open sandbox for stats, cheats, and rehearsal.</p>
        <p class="intro-connection">
          <span class="label">Connection</span>
          Local gateway · <span class="connection-status ${state.connected ? 'connected' : 'disconnected'}">${state.connected ? '● Ready' : '○ Checking'}</span>
        </p>
      </section>
    </div>
  </div>`;
}
function transportChoice() {
  return `${breadcrumb('Main Menu', 'Gateway')}${atmosphere('gateway', 'Choose a gateway', 'Select where the authoritative game host runs. Your current gateway is local; hosted gateways can be added later without changing the client.')}${card('Gateway', `<h2>Where should this run live?</h2><div class="gateway-choice-grid">
    <article class="gateway-choice selected"><p class="eyebrow">Available now</p><h3>Local gateway</h3><p>Runs through the host on this device. Core story, simulation, combat, progression, and local saves remain playable offline.</p><div class="actions">${button('Use local gateway', 'start-engine', 'primary')}</div></article>
    <article class="gateway-choice unavailable"><p class="eyebrow">Coming later</p><h3>Hosted gateway</h3><p>Attach to a remote server for synced services and shared features. This option is not available yet.</p><span class="gateway-status">Not configured</span></article>
  </div>${button('Back', 'back', 'secondary')}`)}`;
}
const MODE_LABELS = {FORGE: 'Story Mode', SANDBOX: 'Simulation Mode'};
const MODE_SCENARIOS = {FORGE: 'reliquary', SANDBOX: 'floor_one_life', DESIGN: 'floor_one_life'};
// Story Mode is bound to its authored module; only Simulation honours the
// Edit Scenario choice, and only after the host has confirmed that scenario
// exists for the mode, so a stale preference can never launch a rejected run.
function scenarioFor(mode) {
  const fallback = MODE_SCENARIOS[mode] || 'floor_one_life';
  if (mode === 'FORGE') return fallback;
  const chosen = state.preferences.scenario;
  if (!chosen) return fallback;
  const known = (state.scenarios || []).some(row => row.scenario === chosen && (row.modes || []).includes(mode));
  return known ? chosen : fallback;
}
function scenarioTitle(id) {
  return (state.scenarios || []).find(row => row.scenario === id)?.title || id;
}
function runSeed(base) {
  const override = String(state.preferences.scenarioSeed || '').trim();
  return override || base;
}
function modeBadge(mode) {
  if (!mode) return '';
  const cls = mode === 'FORGE' ? 'mode-forge' : mode === 'SANDBOX' ? 'mode-sandbox' : 'mode-other';
  return `<span class="mode-badge ${cls}">${E(MODE_LABELS[mode] || mode)}</span>`;
}
function storyMenu() {
  return `<div class="mode-menu">${breadcrumb('Main Menu', 'Story Mode')}${atmosphere('gateway', 'Story Mode', "The Reliquary's authored module: five floors, canon-candidate progress.")}${card('Story Mode', `${menuList([
    ['New Game', 'mode:FORGE', 'primary'],
    ['Continue', 'continue:FORGE'],
    ['Statistics', 'menu:statistics'],
  ])}<div class="mode-menu-footer">${button('Back', 'back', 'secondary')}</div>`, 'mode-menu-card')}</div>`;
}
function simulationMenu() {
  return `<div class="mode-menu">${breadcrumb('Main Menu', 'Simulation Mode')}${atmosphere('gateway', 'Simulation Mode', 'The open sandbox for stats, cheats, and rehearsal — nothing here writes to canon.')}${card('Simulation Mode', `${menuList([
    ['Create Character', 'mode:SANDBOX', 'primary'],
    ['Resume', 'continue:SANDBOX'],
    ['Statistics', 'menu:statistics'],
    [`Edit Scenario${state.preferences.scenario ? ` — ${scenarioTitle(state.preferences.scenario)}` : ''}`, 'menu:edit-scenario', 'secondary'],
    ['Cheats', 'menu:cheats'],
  ])}<div class="mode-menu-footer">${button('Back', 'back', 'secondary')}</div>`, 'mode-menu-card')}</div>`;
}
function partySelect() {
  return `${breadcrumb('Main Menu', MODE_LABELS[state.pendingMode] || 'New lead')}${atmosphere('gateway', MODE_LABELS[state.pendingMode] || 'New lead', 'Build a fresh lead from the character workshop, or step into the Reliquary as an existing Sanctum champion.')}${card('Choose a lead', `<div class="actions">${button('Build a custom character', 'create')}${button('Play as a Champion', 'champion-select')}</div>${button('Back', 'back', 'secondary')}`)}`;
}
function champion() {
  const cards = championRoster().map(row => `<article class="champion-card"><h3>${E(row.id)}</h3><p class="notice">${E(row.title)}</p><p>${E(row.blurb)}</p>${button(`Begin as ${row.id}`, `champion:${row.id}`)}</article>`).join('');
  return `${breadcrumb('Main Menu', MODE_LABELS[state.pendingMode] || 'New lead', 'Champion Band')}${atmosphere('gateway', 'Champion Band', 'These field Stewards carry their own canon kit into the Reliquary instead of a freshly built adventurer.')}${card('Playable champions', `<div class="champion-grid">${cards}</div>${button('Back', 'back', 'secondary')}`)}`;
}
function field(label, key, type = 'text', required = true) {
  const choiceKey = {race: 'races', character_class: 'classes', background: 'backgrounds'}[key];
  const input = type === 'select'
    ? `<select name="${E(key)}" data-create-field="${E(key)}">${(state.options?.[choiceKey] || []).map(row => `<option value="${E(row.id)}" ${state.draft[key] === row.id ? 'selected' : ''}>${E(row.name)}</option>`).join('')}</select>`
    : `<input name="${E(key)}" data-create-field="${E(key)}" type="${type}" value="${E(state.draft[key] || '')}" ${required ? 'required' : ''}>`;
  const tips = {name: 'The visible name on the sheet; the technical profile id is generated privately from the seed.', creation_seed: 'Deterministic seed: same seed and choices produce the same rolls and receipt.', race: 'Ancestry changes traits and starter presentation, not your identity.', character_class: 'Class selects starter gear and class rules.', background: 'Background supplies a small ability bonus, skills, gold, and origin flavor.'};
  return `<label title="${E(tips[key] || label)}">${E(label)}${input}<small class="field-help">${E(tips[key] || '')}</small></label>`;
}
function optionBy(kind, id) {
  return (state.options?.[kind] || []).find(row => row.id === id) || {};
}
function modifier(score) {
  const value = Number(score);
  if (!Number.isFinite(value)) return '—';
  const mod = Math.floor((value - 10) / 2);
  return `${mod >= 0 ? '+' : ''}${mod}`;
}
function automaticAssignment(scores) {
  if (!scores.length) return {};
  const cls = optionBy('classes', state.draft.character_class);
  const order = [...(cls.primary || []), ...ABILITIES.filter(ability => !(cls.primary || []).includes(ability))];
  return Object.fromEntries(order.map((ability, index) => [ability, [...scores].sort((a, b) => b - a)[index]]));
}
function abilityTable(scores, assignment) {
  const values = assignment && typeof assignment === 'object' ? assignment : {};
  return `<div class="ability-table"><div class="ability-head"><span>Ability</span><span>Score</span><span>Mod</span></div>${ABILITIES.map(ability => {
    const current = values[ability] ?? '';
    const options = scores.map(score => `<option value="${E(score)}" ${String(current) === String(score) ? 'selected' : ''}>${E(score)}</option>`).join('');
    return `<label class="ability-row"><span><strong>${E(ability)}</strong><small>${E(ABILITY_NAMES[ability])}</small></span><select data-assign="${E(ability)}" aria-label="${E(ABILITY_NAMES[ability])} score"><option value="">Auto</option>${options}</select><strong>${E(current === '' ? '—' : modifier(current))}</strong></label>`;
  }).join('')}</div>`;
}
function bonusLine(bonuses = {}) {
  return ABILITIES.filter(ability => bonuses[ability]).map(ability => `${ABILITY_NAMES[ability]} ${bonuses[ability] > 0 ? '+' : ''}${bonuses[ability]}`).join(' · ') || 'No ability score bonuses';
}
function getSkillDescription(skillName) {
  const skills = state.options?.skills || {};
  const row = skills[skillName];
  return typeof row === 'object' ? row.description : '';
}
function traitsLine(row) {
  return (row.traits || []).map(trait => trait.replaceAll('_', ' ')).join(' · ') || 'No listed traits';
}
function detailCard(titleText, body) {
  return `<section class="creator-detail"><p class="label">${E(titleText)}</p>${body}</section>`;
}
function starterGearPreview(cls) { const gear = cls.equipment || []; return `<div class="starter-gear" aria-label="Class starter gear presentation">${gear.slice(0, 3).map(item => { const text = String(item.name || '').toLowerCase(); const asset = /sword|blade/.test(text) ? 'longsword.png' : /shirt|armor|mail/.test(text) ? 'chain-shirt.png' : /helm|helmet|hood|cowl/.test(text) ? 'sprites/layers/headgear-v1.png' : /cloak|mantle|cape/.test(text) ? 'sprites/layers/cloak-v1.png' : /shield|buckler/.test(text) ? 'sprites/layers/shield-v1.png' : /ring|amulet|signet|charm/.test(text) ? 'sprites/layers/trinket-v1.png' : /rune/.test(text) ? 'unidentified-rune.png' : 'townsperson.png'; return `<span title="${E(item.name || 'Starter item')}"><img src="assets/${asset}" alt="${E(item.name || 'Starter item')}" onerror="this.hidden=true"><small>${E(item.name || 'Starter item')}</small></span>`; }).join('') || '<small>No starter gear listed.</small>'}</div>`; }
function raceSpriteAsset(raceId, variant) {
  const safeRace = (state.options?.races || []).some(row => row.id === raceId) ? raceId : 'human';
  return `assets/sprites/characters/${safeRace}-${variant === 'male' ? 'male' : 'female'}.png`;
}
function portraitVariant(gender) {
  // The supplied sheet has two visual bodies. Non-binary profile metadata stays
  // intact and uses the first visual body until a dedicated neutral asset exists.
  return gender === 'male' ? 'male' : 'female';
}
function raceSprite(raceId, variant, alt = '') {
  return `<img class="sprite-layer sprite-layer-base" data-sprite-layer="base" src="${E(raceSpriteAsset(raceId, variant))}" alt="${E(alt)}" loading="eager" decoding="async">`;
}
function creatorLayerArt(cls = {}) {
  const text = JSON.stringify(cls.equipment || []).toLowerCase();
  const ids = [];
  if (/helm|helmet|hood|cowl/.test(text)) ids.push(['headgear', 'Headgear art']);
  if (/cloak|mantle|cape/.test(text)) ids.push(['cloak', 'Cloak art']);
  if (/shield|buckler/.test(text)) ids.push(['shield', 'Shield art']);
  if (/ring|amulet|signet|charm/.test(text)) ids.push(['trinket', 'Trinket art']);
  return ids.map(([id, label]) => `<img class="sprite-layer creator-item-layer layer-${id}" data-sprite-layer="equipment" src="assets/sprites/layers/${id}.svg" alt="${E(label)}" aria-hidden="true">`).join('');
}
function raceChoices() {
  const races = state.options?.races || [];
  const variant = portraitVariant(state.draft.gender);
  return `<fieldset class="race-picker"><legend>Choose ancestry</legend><p class="field-help">Select an ancestry. Portraits follow the gender choice above and update immediately; this is presentation-only.</p><div class="race-option-grid">${races.map(race => {
    const selected = state.draft.race === race.id;
    return `<button type="button" class="race-option${selected ? ' selected' : ''}" data-race-choice="${E(race.id)}" aria-pressed="${selected}" aria-label="Choose ${E(race.name)} ancestry"><span class="race-option-art" aria-hidden="true">${raceSprite(race.id, variant)}</span><span class="race-option-copy"><strong>${E(race.name)}</strong><small>${E(traitsLine(race))}</small></span><span class="race-option-check" aria-hidden="true">${selected ? 'Selected' : 'Choose'}</span></button>`;
  }).join('')}</div></fieldset>`;
}
function selectedRacePreview(race, gender, cls = {}) {
  const variant = portraitVariant(gender);
  return `<div class="race-preview-art sprite-stack" data-sprite-pose="idle">${raceSprite(race.id || 'human', variant, `${race.name || 'Human'} ${variant} presentation sprite`)}${creatorLayerArt(cls)}<span class="sprite-overlay-slot" data-sprite-slot="equipment" aria-hidden="true"></span><span class="sprite-overlay-slot" data-sprite-slot="weapon" aria-hidden="true"></span><span class="sprite-overlay-slot" data-sprite-slot="effect" aria-hidden="true"></span></div>`;
}
function choiceSummary() {
  const race = optionBy('races', state.draft.race);
  const cls = optionBy('classes', state.draft.character_class);
  const background = optionBy('backgrounds', state.draft.background);
  const floating = race.floating_bonus;
  const classSpells = cls.spells || [];
  const budget = classSpells.length ? Number(state.draft.spell_budget || Number(state.draft.level || 1) * 5) : 0;
  if (classSpells.length && !state.draft.spell_budget) state.draft.spell_budget = budget;
  return `<div class="creator-choice-grid">
    ${detailCard('Ancestry', `<h3>${E(race.name || 'Choose a race')}</h3><p>${E(traitsLine(race))}</p><p class="bonus-line">${E(bonusLine(race.bonuses))}</p><p class="notice">${E(race.size || '—')} · ${E(race.speed || '—')} ft · ${E((race.skill_bonuses && Object.entries(race.skill_bonuses).map(([skill, value]) => `${skill} +${value}`).join(' · ')) || 'No skill bonus')}</p>${floating ? `<p class="notice">Floating bonus: choose ${E(floating.count)} abilities at ${E(floating.amount > 0 ? '+' : '')}${E(floating.amount)} each; Charisma excluded.</p>` : ''}`)}
    ${detailCard('Class', `<h3>${E(cls.name || 'Choose a class')}</h3><p>${E(cls.hit_die ? `d${cls.hit_die} hit die · primary ${cls.primary.join(' / ')} · saves ${cls.saves.join(' / ')}` : 'Choose a class')}</p><p class="bonus-line">${E((cls.features || []).join(' · ') || 'No listed features')}</p><p class="notice">Trained skills: ${E((cls.skills || []).join(' · ') || 'none')} · choose ${E(cls.skill_count || 0)}${classSpells.length ? ` · ${E(classSpells.length)} spells available` : ''}</p>`)}
    ${detailCard('Background', `<h3>${E(background.name || 'Choose a background')}</h3><p class="bonus-line">${E(background.ability ? `${ABILITY_NAMES[background.ability]} +1` : 'No ability bonus')}</p><p class="notice">Starting gold: ${E(background.gold ? `${background.gold.dice}d${background.gold.sides}+${background.gold.bonus}` : '—')} · ${(background.gear || []).map(item => E(item.name)).join(' · ') || 'No gear'}</p>`)}
  </div>`;
}
function floatingControls(race) {
  const rule = race.floating_bonus;
  if (!rule) return '';
  const manual = Array.isArray(state.draft.floating_bonuses);
  const selected = manual ? state.draft.floating_bonuses : (state.live?.receipt?.floating_bonuses || []);
  return detailCard('Ancestry bonuses', `<p>Choose ${E(rule.count)} abilities for the floating ${E(rule.amount > 0 ? '+' : '')}${E(rule.amount)} bonus.${manual ? '' : ' <span class="cc-badge">Auto: your class priorities</span>'}</p><div class="check-grid">${ABILITIES.filter(ability => !rule.exclude.includes(ability)).map(ability => `<label class="check-chip"><input type="checkbox" data-floating="${E(ability)}" ${selected.includes(ability) ? 'checked' : ''}><span>${E(ability)}<small>${E(ABILITY_NAMES[ability])}</small></span></label>`).join('')}</div>`);
}
function advancementControls(level, cls) {
  const points = 2 * ((state.options?.advancement_levels || []).filter(threshold => level >= threshold).length);
  if (!points) return ''; 
  const values = state.draft.advancements && typeof state.draft.advancements === 'object' ? state.draft.advancements : {};
  const manual = state.draft.advancement_mode === 'manual';
  return detailCard('Advancement', `<p>Level ${E(level)} grants <strong>${E(points)} ability points</strong>. Class priority: ${E((cls.primary || []).join(' / '))}.</p><div class="actions compact-actions">${button(manual ? 'Use automatic allocation' : 'Allocate manually', manual ? 'advancements-auto' : 'advancements-manual', 'secondary')}</div>${manual ? `<div class="ability-table advancement-table"><div class="ability-head"><span>Ability</span><span>Points</span><span>Result</span></div>${ABILITIES.map(ability => `<label class="ability-row"><span><strong>${E(ability)}</strong><small>${E(ABILITY_NAMES[ability])}</small></span><input type="number" min="0" max="${E(points)}" value="${E(values[ability] || 0)}" data-advancement="${E(ability)}"><strong>+${E(values[ability] || 0)}</strong></label>`).join('')}</div>` : '<p class="notice">The host will allocate these points deterministically toward the selected class priorities.</p>'}`);
}
function skillControls(race, cls) {
  const count = (cls.skill_count || 0) + (race.extra_skills || 0);
  const manual = state.draft.skill_mode === 'manual';
  const selected = Array.isArray(state.draft.skills) ? state.draft.skills : [];
  const skills = state.options?.skills || {};
  const getSkillAbility = (skill) => {
    const row = skills[skill];
    return typeof row === 'object' ? row.ability : row;
  };
  const getSkillDescription = (skill) => {
    const row = skills[skill];
    return typeof row === 'object' ? row.description : '';
  };
  if (!manual) return detailCard('Skills', `<p>Choose <strong>${E(count)}</strong> trained skills. The host will select a valid class-priority set automatically.</p><div class="actions compact-actions">${button('Choose skills manually', 'skills-manual', 'secondary')}</div><p class="notice">Class skills: ${E((cls.skills || []).join(' · '))}${race.extra_skills ? ' · ancestry grants one additional skill' : ''}</p>`);
  return detailCard('Skills', `<p>Choose exactly <strong>${E(count)}</strong> trained skills; at least ${E(cls.skill_count || 0)} must come from the class list.</p><div class="check-grid skill-grid">${Object.entries(skills).map(([skill, data]) => {
    const ability = getSkillAbility(skill);
    const description = getSkillDescription(skill);
    const tooltip = description ? ` title="${E(description)}"` : '';
    return `<label class="check-chip ${cls.skills?.includes(skill) ? 'class-skill' : ''}"${tooltip}><input type="checkbox" data-skill="${E(skill)}" ${selected.includes(skill) ? 'checked' : ''}><span>${E(skill)}<small>${E(ability)}${cls.skills?.includes(skill) ? ' · class' : ''}</small></span></label>`;
  }).join('')}</div><div class="actions compact-actions">${button('Use automatic skills', 'skills-auto', 'secondary')}</div>`);
}
function spellControls(cls, level) {
  const spells = cls.spells || [];
  if (!spells.length) return '';
  const manual = state.draft.spell_mode === 'manual';
  const budget = Number(state.draft.spell_budget || level * 5);
  const selected = Array.isArray(state.draft.spells) ? state.draft.spells : [];
  return detailCard('Spells', `<div class="spell-heading"><p>Spell budget: <strong>${E(budget)} points</strong> · rank cap is enforced by the host at preview.</p><input type="number" min="0" max="${E(level * 5)}" value="${E(budget)}" data-create-field="spell_budget" aria-label="Spell budget"></div>${manual ? `<div class="check-grid spell-grid">${spells.map(spell => `<label class="check-chip"><input type="checkbox" data-spell="${E(spell)}" ${selected.includes(spell) ? 'checked' : ''}><span>${E(spell.replace('@5e', ''))}<small>${E(spell.includes('@HSR') ? 'HSR signature' : '5e spell')}</small></span></label>`).join('')}</div><div class="actions compact-actions">${button('Use automatic spell selection', 'spells-auto', 'secondary')}</div>` : `<p class="notice">${E(spells.length)} class spells are available. The host will choose a deterministic legal set inside the budget.</p><div class="actions compact-actions">${button('Choose spells manually', 'spells-manual', 'secondary')}</div>`}`);
}
function buildPayload() {
  const d = state.draft;
  const level = Number(d.level || 1);
  const cls = optionBy('classes', d.character_class);
  const spellBudget = (cls.spells || []).length ? Number(d.spell_budget || level * 5) : 0;
  const build = {name: d.name, creation_seed: d.creation_seed || d.name, race: d.race, gender: d.gender, character_class: d.character_class,
    background: d.background, level, roll_set: Number(d.roll_set || 0),
    ability_assignment: d.ability_assignment && typeof d.ability_assignment === 'object' ? d.ability_assignment : 'auto',
    floating_bonuses: Array.isArray(d.floating_bonuses) ? d.floating_bonuses : 'auto',
    advancements: d.advancement_mode === 'manual' ? (d.advancements || {}) : 'auto',
    skills: d.skill_mode === 'manual' ? (d.skills || []) : 'auto',
    spell_budget: spellBudget,
    spells: d.spell_mode === 'manual' ? (d.spells || []) : 'auto'};
  if (d.appearance && Object.keys(d.appearance).length) build.appearance = {...d.appearance};
  return build;
}
// ---------------------------------------------------------------------------
// Character creation: a paged, flow-chart style walk from identity to a final
// sheet.  Every page shows what the choice does; the host stays the only
// authority on numbers (live preview), and nothing saves until Confirm.
// ---------------------------------------------------------------------------
const CREATE_STEPS = [
  {id: 'identity', label: 'Identity', title: 'Who descends?', lede: 'Name your lead. Eight short steps follow, and each one shows exactly what it changes. Nothing is saved until you confirm the final sheet.'},
  {id: 'ancestry', label: 'Ancestry', title: 'Choose an ancestry', lede: 'Ancestry sets your starting ability bonuses and a few innate traits.'},
  {id: 'class', label: 'Class', title: 'Choose a class', lede: 'Class is your role in a fight. It sets hit points, armor, gear, saves and the abilities that matter most.'},
  {id: 'background', label: 'Background', title: 'Choose a background', lede: 'Where you came from: +1 to one ability, starting gold and a few personal effects.'},
  {id: 'abilities', label: 'Abilities', title: 'Roll your abilities', lede: 'Roll 4d6 six times and drop the lowest die each time. You get one reroll. The recommended placement puts your best rolls into your class priorities.'},
  {id: 'training', label: 'Training', title: 'Skills and spells', lede: 'Pick the skills you are trained in and, if your class casts, your starting spells. Automatic choices are always legal.'},
  {id: 'look', label: 'Look', title: 'Appearance', lede: 'Cosmetic only. Nothing here changes a number.'},
  {id: 'summary', label: 'Summary', title: 'Final sheet', lede: 'Review the finished lead. Confirming saves the profile and starts the run.'},
];
const RATING_AXES = [['offense', 'Offense'], ['defense', 'Defense'], ['magic', 'Magic'], ['complexity', 'Complexity']];
const LOOK_FIELDS = ['skin_tone', 'hair_style', 'hair_color', 'eye_color', 'body_type', 'outfit'];
const STEP_INDEX = Object.fromEntries(CREATE_STEPS.map((row, index) => [row.id, index]));
const live = {seq: 0, timer: 0};

function createStep() { return Math.max(0, Math.min(CREATE_STEPS.length - 1, Number(state.draft.create_step || 0))); }
function seededIndex(key, n) {
  let h = 2166136261;
  for (const ch of String(key)) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); }
  return n ? (h >>> 0) % n : 0;
}
function signed(n) { const v = Number(n) || 0; return `${v >= 0 ? '+' : ''}${v}`; }
function pips(value, max = 5) {
  return `<span class="cc-pips" aria-label="${E(value)} of ${E(max)}">${Array.from({length: max}, (_, i) => `<i class="${i < value ? 'on' : ''}"></i>`).join('')}</span>`;
}
function ratingBars(ratings = {}) {
  return `<div class="cc-ratings">${RATING_AXES.map(([key, label]) => `<div><span>${E(label)}</span>${pips(Number(ratings[key] || 0))}</div>`).join('')}</div>`;
}
function chips(items, extra = '') { return items.filter(Boolean).map(text => `<span class="cc-chip ${extra}">${E(text)}</span>`).join(''); }
function shortBonuses(bonuses = {}) {
  const rows = ABILITIES.filter(a => bonuses[a]);
  if (rows.length === ABILITIES.length && rows.every(a => bonuses[a] === bonuses.STR)) return `${signed(bonuses.STR)} to every ability`;
  return rows.map(a => `${a} ${signed(bonuses[a])}`).join(' · ');
}
function pairsWithClasses(race) {
  return (state.options?.classes || []).filter(cls => (cls.primary || []).some(a => (race.bonuses?.[a] || 0) >= 2)).map(cls => cls.name);
}
function pairsWithRaces(cls) {
  return (state.options?.races || []).filter(race => (cls.primary || []).some(a => (race.bonuses?.[a] || 0) >= 2)).map(race => race.name);
}
function stepValid(index) {
  const d = state.draft; const id = CREATE_STEPS[index].id;
  if (id === 'identity' && !String(d.name || '').trim()) return 'Give your lead a name to continue.';
  if (id === 'abilities' && !state.roll) return 'Roll your ability scores to continue.';
  if (id === 'training' && d.skill_mode === 'manual') {
    const cls = optionBy('classes', d.character_class);
    const need = (cls.skill_count || 0) + (optionBy('races', d.race).extra_skills || 0);
    if ((d.skills || []).length !== need) return `Choose exactly ${need} skills, or switch back to automatic.`;
    if ((d.skills || []).filter(s => (cls.skills || []).includes(s)).length < (cls.skill_count || 0)) return `At least ${cls.skill_count} skills must come from the ${cls.name} list.`;
  }
  if (id === 'ancestry' && optionBy('races', d.race).floating_bonus && Array.isArray(d.floating_bonuses)
      && d.floating_bonuses.length !== optionBy('races', d.race).floating_bonus.count) return 'Pick both floating bonuses, or leave them automatic.';
  return '';
}
function draftAppearanceItem() {
  const d = state.draft; const fields = state.options?.appearance?.fields || {};
  const appearance = {};
  for (const [field, id] of Object.entries(d.appearance || {})) {
    const row = (fields[field]?.options || []).find(option => option.id === id);
    if (row) appearance[field] = row;
  }
  const liveProfile = state.live?.profile;
  const cls = optionBy('classes', d.character_class);
  return {...(liveProfile || {}), name: d.name || 'Your lead', race_id: d.race, gender: d.gender, class_id: d.character_class,
    character_class: cls.name, sprite_id: `${d.race}-${d.gender}`, appearance, equipment: liveProfile?.equipment || cls.equipment || []};
}
function leadFigure(extra = '') {
  return `<div class="cc-doll ${extra}">${layeredCharacterFigure(draftAppearanceItem(), 'cc-doll-figure', 'idle')}</div>`;
}
function leadPanel() {
  const d = state.draft; const p = state.live?.profile; const notes = state.live?.notes;
  const race = optionBy('races', d.race); const cls = optionBy('classes', d.character_class); const bg = optionBy('backgrounds', d.background);
  // Seeded rolls mean the preview already knows the scores; keep them hidden until the player rolls.
  const revealed = !!state.roll; const scores = revealed ? p?.ability_scores || {} : {};
  const stat = (label, value) => `<div class="cc-mini-stat"><span>${E(label)}</span><strong>${E(value ?? '—')}</strong></div>`;
  return `<aside class="cc-lead" aria-label="Your lead so far">
    <div class="cc-lead-top">${leadFigure()}<div><p class="eyebrow">Your lead</p><h3>${E(d.name || 'Unnamed')}</h3><p class="cc-lead-line">${E([race.name, cls.name].filter(Boolean).join(' '))}<br><small>${E(bg.name || '')} · level ${E(d.level || 1)}</small></p>${notes ? `<span class="cc-archetype">${E(notes.archetype)}</span>` : ''}</div></div>
    <div class="cc-mini-grid">${stat('HP', revealed ? p?.max_hp : '?')}${stat('AC', revealed ? p?.armor_class : '?')}${stat('Init', revealed && p ? signed(p.initiative_bonus) : '?')}${stat('Speed', p ? `${p.speed} ft` : null)}</div>
    <div class="cc-mini-scores">${ABILITIES.map(a => `<div><span>${E(a)}</span><strong>${E(scores[a] ?? '?')}</strong><small>${E(scores[a] ? modifier(scores[a]) : '')}</small></div>`).join('')}</div>
    <p class="cc-lead-note">${state.liveError ? `<span class="error">${E(state.liveError)}</span>` : state.roll ? 'Live numbers from the host.' : 'Scores, HP and AC appear once you roll on the Abilities step.'}</p>
  </aside>`;
}
function stepRail(current) {
  const d = state.draft; const reached = Number(d.max_step || 0);
  const value = {identity: d.name, ancestry: optionBy('races', d.race).name, class: optionBy('classes', d.character_class).name,
    background: optionBy('backgrounds', d.background).name, abilities: state.roll ? `${state.roll.scores.join(' ')}` : '',
    training: d.skill_mode === 'manual' ? 'Manual' : 'Auto', look: Object.keys(d.appearance || {}).length ? 'Custom' : 'Default',
    summary: state.live?.notes?.archetype || ''};
  return `<ol class="cc-rail" aria-label="Character creation steps">${CREATE_STEPS.map((step, index) => {
    const status = index === current ? 'current' : index < reached || index < current ? 'done' : index <= reached ? 'open' : 'locked';
    return `<li class="cc-node is-${status}"><button type="button" data-action="step-goto:${index}" ${status === 'locked' ? 'disabled data-locked="true"' : ''} aria-current="${index === current ? 'step' : 'false'}"><span class="cc-node-dot">${index < current || status === 'done' ? '✓' : index + 1}</span><span class="cc-node-text"><strong>${E(step.label)}</strong><small>${E(index <= Math.max(reached, current) ? value[step.id] || '' : '')}</small></span></button></li>`;
  }).join('')}</ol>`;
}
function choiceCard({kind, id, selected, art = '', title, sub = '', body = '', label}) {
  return `<button type="button" class="cc-card${selected ? ' selected' : ''}" data-choice="${E(kind)}:${E(id)}" ${kind === 'race' ? `data-race-choice="${E(id)}"` : ''} aria-pressed="${selected}" aria-label="${E(label || `Choose ${title}`)}">${art}<span class="cc-card-copy"><strong>${E(title)}</strong>${sub ? `<small>${E(sub)}</small>` : ''}${body}</span><span class="cc-card-check" aria-hidden="true">${selected ? '✓' : ''}</span></button>`;
}
function detailPanel(title, blurb, sections) {
  return `<section class="cc-detail" aria-live="polite"><p class="label">What this does</p><h3>${E(title)}</h3>${blurb ? `<p class="cc-blurb">${E(blurb)}</p>` : ''}${sections.filter(Boolean).map(([head, html]) => `<div class="cc-detail-row"><span>${E(head)}</span><div>${html}</div></div>`).join('')}</section>`;
}
function identityPage() {
  const d = state.draft; const storyMode = state.pendingMode === 'FORGE';
  const gender = ['female', 'male', 'other'].map(g => `<button type="button" class="cc-seg${d.gender === g ? ' selected' : ''}" data-choice="gender:${g}" aria-pressed="${d.gender === g}">${E(g[0].toUpperCase() + g.slice(1))}</button>`).join('');
  return `<div class="cc-identity">
    <label class="cc-name">Lead name<input name="name" data-create-field="name" type="text" value="${E(d.name || '')}" placeholder="e.g. Ardent Vale" autocomplete="off" maxlength="40" required></label>
    <div class="cc-field"><span class="cc-field-label">Presentation</span><div class="cc-segmented" role="group" aria-label="Gender">${gender}</div><small class="field-help">Changes the portraits only. "Other" uses the first visual body for now.</small></div>
    <div class="cc-build-number"><span>Build</span><strong>#${E(d.creation_seed || '—')}</strong><small>Your seed. The same seed and the same choices always produce the same character.</small></div>
    <details class="cc-advanced"><summary>Advanced</summary><div class="cc-advanced-grid"><label>Creation seed<input name="creation_seed" data-create-field="creation_seed" type="text" value="${E(d.creation_seed || '')}" autocomplete="off"><small class="field-help">Type any seed to recreate a build. Numbered seeds come from the build counter.</small></label>${storyMode ? '<label>Level<input type="text" value="1 · fixed for Story Mode" disabled></label>' : `<label>Starting level<input name="level" data-create-field="level" type="number" min="1" max="20" value="${E(d.level || 1)}"><small class="field-help">Higher levels add HP, advancement points and spell budget.</small></label>`}</div></details>
  </div>
  <div class="cc-fork">
    <button type="button" class="cc-fork-card" data-action="step-next"><span class="cc-fork-icon" aria-hidden="true">⟶</span><strong>Build step by step</strong><small>Choose ancestry, class, background and scores yourself. About two minutes.</small></button>
    <button type="button" class="cc-fork-card alt" data-action="randomize-build"><span class="cc-fork-icon" aria-hidden="true">⚄</span><strong>Randomize whole build</strong><small>The seed picks everything and jumps to the final sheet. You can still edit any step.</small></button>
  </div>`;
}
function ancestryPage() {
  const d = state.draft; const variant = portraitVariant(d.gender);
  const races = state.options?.races || []; const blurbs = state.options?.race_playstyle || {};
  const race = optionBy('races', d.race);
  const cards = races.map(row => choiceCard({kind: 'race', id: row.id, selected: d.race === row.id, label: `Choose ${row.name} ancestry`,
    art: `<span class="cc-card-art race-option-art">${raceSprite(row.id, variant)}</span>`, title: row.name, sub: shortBonuses(row.bonuses) + (row.floating_bonus ? ` · +${row.floating_bonus.amount} ×${row.floating_bonus.count} your pick` : '')})).join('');
  const floating = race.floating_bonus ? floatingControls(race) : '';
  const skillBonus = Object.entries(race.skill_bonuses || {}).map(([s, v]) => `${s} ${signed(v)}`);
  return `<div class="cc-split"><div class="cc-cards race-option-grid">${cards}</div>${detailPanel(race.name || '', blurbs[race.id], [
    ['Abilities', chips([...ABILITIES.filter(a => race.bonuses?.[a]).map(a => `${ABILITY_NAMES[a]} ${signed(race.bonuses[a])}`), race.floating_bonus ? `+${race.floating_bonus.amount} to ${race.floating_bonus.count} of your choice` : ''], 'gold')],
    ['Traits', chips((race.traits || []).map(t => t.replaceAll('_', ' ')), 'cap')],
    ['Body', `${E(String(race.size || '—').replace(/^./, c => c.toUpperCase()))} · ${E(race.speed || '—')} ft speed`],
    skillBonus.length || race.extra_skills ? ['Skills', chips([...skillBonus, race.extra_skills ? `+${race.extra_skills} extra trained skill` : ''])] : null,
    ['Pairs well with', chips(pairsWithClasses(race).length ? pairsWithClasses(race) : ['Any class'], 'soft')],
  ])}</div>${floating}`;
}
function classPage() {
  const d = state.draft; const ratings = state.options?.class_ratings || {};
  const cls = optionBy('classes', d.character_class); const r = ratings[cls.id] || {};
  const cards = (state.options?.classes || []).map(row => choiceCard({kind: 'class', id: row.id, selected: d.character_class === row.id, title: row.name,
    sub: ratings[row.id]?.role || '', body: ratingBars(ratings[row.id])})).join('');
  return `<div class="cc-split"><div class="cc-cards cc-class-cards">${cards}</div>${detailPanel(cls.name || '', r.blurb, [
    ['Role', `<strong>${E(r.role || '—')}</strong>`],
    ['Hit points', `d${E(cls.hit_die)} hit die · level 1 HP = ${E(cls.hit_die)} + CON`],
    ['Priorities', chips((cls.primary || []).map(a => ABILITY_NAMES[a]), 'gold')],
    ['Saves', chips((cls.saves || []).map(a => ABILITY_NAMES[a]))],
    ['Features', chips(cls.features || [])],
    ['Starter kit', starterGearPreview(cls)],
    ['Skills', `Choose ${E(cls.skill_count)} from ${E((cls.skills || []).join(', '))}`],
    (cls.spells || []).length ? ['Magic', `${E(cls.spells.length)} spells · budget ${E(5 * Number(d.level || 1))} points at level ${E(d.level || 1)}`] : null,
    ['Pairs well with', chips(pairsWithRaces(cls).length ? pairsWithRaces(cls) : ['Human', 'Half-Elf'], 'soft')],
  ])}</div>`;
}
function backgroundPage() {
  const d = state.draft; const bg = optionBy('backgrounds', d.background);
  const cls = optionBy('classes', d.character_class);
  const cards = (state.options?.backgrounds || []).map(row => choiceCard({kind: 'background', id: row.id, selected: d.background === row.id, title: row.name,
    sub: `${ABILITY_NAMES[row.ability]} +1 · ${row.gold.dice}d${row.gold.sides}+${row.gold.bonus} gold`,
    body: (cls.primary || []).includes(row.ability) ? `<em class="cc-fit">Fits ${E(cls.name)}</em>` : ''})).join('');
  const fits = (cls.primary || []).includes(bg.ability);
  return `<div class="cc-split"><div class="cc-cards cc-bg-cards">${cards}</div>${detailPanel(bg.name || '', '', [
    ['Ability', chips([`${ABILITY_NAMES[bg.ability] || ''} +1`], 'gold')],
    ['For your class', fits ? `Boosts a ${E(cls.name)} priority. Efficient.` : `Boosts an ability outside ${E(cls.name)} priorities. Flavorful rather than optimal.`],
    ['Starting gold', `${E(bg.gold?.dice)}d${E(bg.gold?.sides)} + ${E(bg.gold?.bonus)} (average ${E(Math.round((bg.gold?.dice || 0) * ((bg.gold?.sides || 0) + 1) / 2 + (bg.gold?.bonus || 0)))})`],
    ['Personal effects', `<ul class="cc-gear">${(bg.gear || []).map(item => `<li><strong>${E(item.name)}</strong><small>${E(item.flavor || '')}</small></li>`).join('')}</ul>`],
  ])}</div>`;
}
function abilitiesPage() {
  const d = state.draft; const cls = optionBy('classes', d.character_class);
  if (!state.roll) return `<div class="cc-roll-empty"><div class="cc-dice-art" aria-hidden="true"><i>⚃</i><i>⚄</i><i>⚅</i><i>⚂</i></div><h3>Roll 4d6, drop the lowest, six times.</h3><p>Each score runs from 3 to 18, and 10–11 is average. After the roll, your ${E(cls.name)} priorities (${E((cls.primary || []).map(a => ABILITY_NAMES[a]).join(' and '))}) get your best rolls unless you move them.</p>${button('Roll ability scores', 'roll-abilities', 'cc-big')}</div>`;
  const receipt = state.live?.receipt || {}; const rolled = state.roll.scores || [];
  const auto = d.ability_assignment === 'auto';
  const assignment = auto ? automaticAssignment(rolled) : d.ability_assignment;
  const anim = state.rollAnim ? ' is-rolling' : '';
  const strip = `<div class="cc-dice-strip${anim}">${state.roll.rolls.map((row, i) => { let dropped = false; return `<div class="cc-die-set" style="--i:${i}"><div class="cc-dice">${row.dice.map(v => { const drop = !dropped && v === row.dropped; if (drop) dropped = true; return `<span class="${drop ? 'dropped' : ''}">${E(v)}</span>`; }).join('')}</div><strong>${E(row.total)}</strong></div>`; }).join('')}</div>`;
  const rows = ABILITIES.map(a => {
    const base = receipt.assigned_scores?.[a] ?? assignment[a]; const race = receipt.race_bonuses?.[a] || 0;
    const bgb = receipt.background?.ability_bonus?.[a] || 0; const adv = receipt.advancements?.[a] || 0;
    const fin = receipt.final_scores?.[a] ?? base; const primary = (cls.primary || []).includes(a);
    const options = rolled.map(score => `<option value="${E(score)}" ${String(assignment[a]) === String(score) ? 'selected' : ''}>${E(score)}</option>`).join('');
    return `<div class="cc-ab-row${primary ? ' primary' : ''}"><span class="cc-ab-name"><strong>${E(a)}</strong><small>${E(ABILITY_NAMES[a])}${primary ? ' · priority' : ''}</small></span><select data-assign="${E(a)}" aria-label="${E(ABILITY_NAMES[a])} score"><option value="">Auto</option>${options}</select><span class="cc-ab-bonus">${race ? signed(race) : '·'}</span><span class="cc-ab-bonus">${bgb ? signed(bgb) : '·'}</span>${Number(d.level || 1) >= 4 ? `<span class="cc-ab-bonus">${adv ? signed(adv) : '·'}</span>` : ''}<strong class="cc-ab-final">${E(fin ?? '—')}</strong><strong class="cc-ab-mod">${E(fin ? modifier(fin) : '—')}</strong></div>`;
  }).join('');
  const advCol = Number(d.level || 1) >= 4;
  return `<div class="cc-roll-head"><div><h3>Your rolls · total ${E(rolled.reduce((a, b) => a + b, 0))}</h3><p class="notice">Build #${E(state.roll.creation_seed)} · roll ${E((state.roll.roll_set || 0) + 1)} of 2</p></div><div class="actions compact-actions">${auto ? '<span class="cc-badge">Recommended for ' + E(cls.name) + '</span>' : button('Use recommended placement', 'assign-auto', 'secondary')}${state.roll.roll_set === 0 ? button('Use my one reroll', 'roll-abilities', 'secondary') : '<span class="cc-badge muted">Reroll used</span>'}</div></div>
    ${strip}
    <div class="cc-ab-table${advCol ? ' with-adv' : ''}"><div class="cc-ab-head"><span>Ability</span><span>Rolled</span><span>Race</span><span>Bkgd</span>${advCol ? '<span>Adv</span>' : ''}<span>Final</span><span>Mod</span></div>${rows}</div>
    <p class="notice">Pick a rolled score for any ability to place it by hand; the score it replaces moves back to Auto. The modifier is (score − 10) ÷ 2, rounded down, and it is what actually gets added to your rolls.</p>
    ${advancementControls(Number(d.level || 1), cls)}`;
}
function trainingPage() {
  const d = state.draft; const race = optionBy('races', d.race); const cls = optionBy('classes', d.character_class);
  const p = state.live?.profile; const skills = state.options?.skills || {};
  const count = (cls.skill_count || 0) + (race.extra_skills || 0);
  const manual = d.skill_mode === 'manual';
  const trained = manual ? (d.skills || []) : (state.live?.receipt?.trained_skills || []);
  const prof = p?.proficiency_bonus ?? 2; const scores = p?.ability_scores || {};
  const fromClass = trained.filter(s => (cls.skills || []).includes(s)).length;
  const grid = Object.entries(skills).map(([skill, row]) => {
    const ability = typeof row === 'object' ? row.ability : row; const desc = typeof row === 'object' ? row.description : '';
    const on = trained.includes(skill); const classSkill = (cls.skills || []).includes(skill);
    const bonus = on && p?.skill_bonuses?.[skill] !== undefined ? p.skill_bonuses[skill] : Math.floor(((scores[ability] || 10) - 10) / 2) + (on ? prof : 0);
    return `<button type="button" class="cc-skill${on ? ' selected' : ''}${classSkill ? ' class-skill' : ''}" data-skill-pick="${E(skill)}" aria-pressed="${on}"><span class="cc-skill-top"><strong>${E(skill)}</strong><em>${E(state.roll ? signed(bonus) : ability)}</em></span><small>${E(ability)}${classSkill ? ` · ${E(cls.name)} skill` : ''}</small>${desc ? `<span class="cc-skill-desc">${E(desc)}</span>` : ''}</button>`;
  }).join('');
  const spells = p && d.spell_mode !== 'manual' && (p.known_spells || []).length ? `<div class="cc-auto-picks"><span>Automatic spells</span>${chips(p.known_spells.map(s => s.replace(/@.*$/, '')))}</div>` : '';
  return `<div class="cc-roll-head"><div><h3>Trained skills · ${E(trained.length)} of ${E(count)}</h3><p class="notice">Pick ${E(count)}${race.extra_skills ? ` (${E(race.name)} adds one)` : ''}, at least ${E(cls.skill_count)} from the ${E(cls.name)} list (gold edge). Trained skills add your proficiency bonus, ${E(signed(prof))}.${fromClass < (cls.skill_count || 0) && manual ? ` <strong class="cc-warn-inline">Need ${E(cls.skill_count - fromClass)} more class skill${cls.skill_count - fromClass === 1 ? '' : 's'}.</strong>` : ''}</p></div>${manual ? button('Use automatic picks', 'skills-auto', 'secondary') : '<span class="cc-badge">Automatic picks · tap any skill to customize</span>'}</div>
    <div class="cc-skill-grid">${grid}</div>${spellControls(cls, Number(d.level || 1))}${spells}`;
}
function lookPage() {
  const d = state.draft; const fields = state.options?.appearance?.fields || {};
  const current = state.live?.profile?.appearance || {};
  const groups = LOOK_FIELDS.filter(f => fields[f]).map(field => {
    const spec = fields[field];
    const rows = (spec.options || []).filter(row => !row.races || row.races.includes(d.race));
    const chosen = d.appearance?.[field] || current[field]?.id || rows[0]?.id;
    return `<fieldset class="cc-look-group"><legend>${E(spec.label)}</legend><div class="cc-look-options">${rows.map(row => `<button type="button" class="cc-look${row.hex ? ' swatch' : ''}${chosen === row.id ? ' selected' : ''}" data-look="${E(field)}:${E(row.id)}" aria-pressed="${chosen === row.id}" title="${E(row.name)}">${row.hex && /^#[0-9a-f]{6}$/i.test(row.hex) ? `<i style="background:${row.hex}"></i>` : ''}<span>${E(row.name)}</span></button>`).join('')}</div></fieldset>`;
  }).join('');
  return `<div class="cc-look-layout"><div class="cc-look-stage">${leadFigure('large')}</div><div class="cc-look-groups">${groups}</div></div>`;
}
function sentenceCase(text) { return String(text || '').replace(/^./, c => c.toUpperCase()); }
function hpFormula(p) {
  const hd = optionBy('classes', p.class_id).hit_die || 0; const con = Math.floor(((p.ability_scores?.CON || 10) - 10) / 2);
  const first = `${hd} (d${hd} max) ${con >= 0 ? '+' : '−'} ${Math.abs(con)} CON`;
  if (p.level <= 1) return first;
  const per = Math.max(1, ({10: 6, 8: 5, 6: 4})[hd] + con);
  return `${first}, then +${per} for each of ${p.level - 1} more levels`;
}
function acFormula(p) {
  const gear = p.equipment || []; const armor = gear.find(item => item.base_ac); const shield = gear.filter(item => item.shield_bonus);
  const dexMod = Math.floor(((p.ability_scores?.DEX || 10) - 10) / 2);
  const dex = armor && armor.dex_cap !== undefined && armor.dex_cap !== null ? Math.min(dexMod, armor.dex_cap) : dexMod;
  const parts = [armor ? `${armor.name} ${armor.base_ac}` : 'unarmored 10'];
  if (dex) parts.push(`DEX ${signed(dex)}${armor && armor.dex_cap !== undefined && armor.dex_cap !== null && dexMod > armor.dex_cap ? ' (capped)' : ''}`);
  shield.forEach(item => parts.push(`${item.name} +${item.shield_bonus}`));
  return parts.join(' · ');
}
function summaryPage() {
  const c = state.live; const p = c?.profile; const notes = c?.notes;
  if (!p || typeof c.build_hash !== 'string') return `<div class="cc-roll-empty"><h3>Assembling your sheet…</h3><p>${E(state.liveError || 'The host is validating the build.')}</p>${button('Try again', 'step-goto:7', 'secondary')}</div>`;
  const r = c.receipt || {}; const rules = p.build_rules || {}; const scores = p.ability_scores || {};
  const bg = p.background || {};
  const tile = (label, value, sub = '', i = 0) => `<div class="cc-tile" style="--i:${i}"><span>${E(label)}</span><strong>${E(value)}</strong>${sub ? `<small>${E(sub)}</small>` : ''}</div>`;
  const breakdown = a => [`rolled ${r.assigned_scores?.[a]}`, r.race_bonuses?.[a] ? `race ${signed(r.race_bonuses[a])}` : '', r.background?.ability_bonus?.[a] ? `bkgd +1` : '', r.advancements?.[a] ? `adv ${signed(r.advancements[a])}` : ''].filter(Boolean).join(' · ');
  const weapon = (p.equipment || []).filter(item => item.attack_bonus !== undefined);
  const list = (items, cls) => `<ul class="cc-notes-list ${cls}">${items.map(t => `<li>${E(t)}</li>`).join('')}</ul>`;
  return `<div class="cc-summary">
    <header class="cc-sum-head"><div class="cc-sum-figure">${leadFigure('large')}</div><div><p class="eyebrow">Final sheet · not saved</p><h2>${E(p.name || state.draft.name)}</h2><p class="cc-sum-line"><strong>${E(p.race)} ${E(p.character_class)}</strong> · level ${E(p.level)} · ${E(bg.name)} · Build #${E(r.creation_seed)}</p>${notes ? `<p class="cc-sum-arch"><span class="cc-archetype big">${E(notes.archetype)}</span>${E(sentenceCase(notes.summary.split(': ').slice(1).join(': ')))}</p>${ratingBars(notes.ratings)}` : ''}</div></header>
    ${notes ? `<section class="cc-notes"><p class="label">Build notes</p><div class="cc-notes-grid"><div><h4>Good at</h4>${list(notes.strengths, 'good')}</div><div><h4>Watch out</h4>${list(notes.watchouts, 'warn')}</div><div><h4>Synergy</h4>${list(notes.synergies, 'syn')}</div></div>${notes.tip ? `<p class="cc-tip"><strong>How to play it:</strong> ${E(notes.tip)}</p>` : ''}</section>` : ''}
    <section class="cc-sheet"><p class="label">Abilities</p><div class="cc-score-row">${ABILITIES.map((a, i) => `<div class="cc-score" style="--i:${i}" title="${E(breakdown(a))}"><span>${E(a)}</span><strong>${E(scores[a])}</strong><em>${E(modifier(scores[a]))}</em><small>${E(breakdown(a))}</small></div>`).join('')}</div></section>
    <section class="cc-sheet"><p class="label">Combat</p><div class="cc-tiles">${tile('Hit points', p.max_hp, hpFormula(p), 0)}${tile('Armor class', p.armor_class, acFormula(p), 1)}${tile('Initiative', signed(p.initiative_bonus), 'DEX modifier', 2)}${tile('Speed', `${p.speed} ft`, '', 3)}${tile('Proficiency', signed(p.proficiency_bonus), `levels ${Math.floor((p.level - 1) / 4) * 4 + 1}–${Math.floor((p.level - 1) / 4) * 4 + 4}`, 4)}${tile('Passive Perception', notes?.derived?.passive_perception ?? '—', '10 + Perception', 5)}${rules.attacks > 1 ? tile('Attacks', rules.attacks, 'per Attack action', 6) : ''}${rules.spell_save_dc ? tile('Spell save DC', rules.spell_save_dc, `8 + prof + ${p.class_id === 'magician' ? 'INT' : 'WIS'}`, 7) : ''}${rules.spell_save_dc ? tile('Spell attack', signed(rules.spell_attack_bonus), 'prof + casting mod', 8) : ''}${rules.sneak_attack_dice ? tile('Sneak Attack', `${rules.sneak_attack_dice}d6`, '', 9) : ''}</div>
      ${weapon.length ? `<div class="cc-attacks">${weapon.map(w => `<div><strong>${E(w.name)}</strong><span>${E(signed(w.attack_bonus))} to hit</span><span>${E(w.damage_dice)} ${E(signed(w.damage_modifier))}</span></div>`).join('')}</div>` : ''}</section>
    <div class="cc-sheet-grid">
      <section class="cc-sheet"><p class="label">Saving throws</p><div class="cc-kv">${ABILITIES.map(a => `<div class="${(optionBy('classes', p.class_id).saves || []).includes(a) ? 'prof' : ''}"><span>${E(ABILITY_NAMES[a])}</span><strong>${E(signed(rules.saves?.[a]))}</strong></div>`).join('')}</div></section>
      <section class="cc-sheet"><p class="label">Trained skills</p><div class="cc-kv">${Object.entries(p.skill_bonuses || {}).map(([s, b]) => `<div title="${E(getSkillDescription(s) || '')}"><span>${E(s)}</span><strong>${E(signed(b))}</strong></div>`).join('')}</div></section>
      <section class="cc-sheet"><p class="label">Features</p>${chips(p.features || [])}<p class="notice">Recognized as ${E((p.interaction_tags || []).map(tag => tag.replaceAll('_', ' ')).join(' · '))}</p>${p.known_spells?.length ? `<p class="label">Spells · ${E(r.spell_points_spent)}/${E(r.spell_budget)} points</p>${chips(p.known_spells.map(s => s.replace(/@.*$/, '')))}` : ''}</section>
      <section class="cc-sheet"><p class="label">Starting kit</p><ul class="cc-gear">${(p.equipment || []).map(item => `<li><strong>${E(item.display_name || item.name)}</strong>${item.flavor ? `<small>${E(item.flavor)}</small>` : ''}</li>`).join('')}</ul><p class="notice">Gold ${E(bg.starting_gold)} · origin ${E(p.origin_item?.name || '—')}${p.heirloom_item?.name ? ` · heirloom ${E(p.heirloom_item.name)}` : ''}</p></section>
    </div>
    <details class="receipt-details"><summary>Show deterministic creation receipt · hash ${E(c.build_hash.slice(0, 12))}</summary><pre>${E(JSON.stringify(r, null, 2))}</pre></details>
    <div class="cc-confirm">${button('Confirm and create run', 'confirm-build', 'cc-big')}<small>Saves Build #${E(r.creation_seed)} and starts the descent.</small></div>
  </div>`;
}
function creator() {
  const step = createStep(); const info = CREATE_STEPS[step];
  const pages = {identity: identityPage, ancestry: ancestryPage, class: classPage, background: backgroundPage, abilities: abilitiesPage, training: trainingPage, look: lookPage, summary: summaryPage};
  const blocked = stepValid(step);
  const noLead = ['identity', 'look', 'summary'].includes(info.id);
  const dir = state.stepAnim || ''; state.stepAnim = ''; const rolling = state.rollAnim; state.rollAnim = false;
  const surprise = step > 0 && step < CREATE_STEPS.length - 1 ? button('Surprise me', 'surprise-step', 'secondary cc-surprise') : '';
  const next = step < CREATE_STEPS.length - 1
    ? `<button type="button" class="action cc-next" data-action="step-next" ${blocked ? 'aria-disabled="true"' : ''}>${step === CREATE_STEPS.length - 2 ? 'Review final sheet' : `Next: ${E(CREATE_STEPS[step + 1].label)}`} ›</button>` : '';
  void rolling;
  return `<section class="card cc-shell" data-create-step="${E(info.id)}">
    <header class="cc-header"><div><p class="eyebrow">New lead · Build #${E(state.draft.creation_seed || '—')} · step ${step + 1} of ${CREATE_STEPS.length}</p><h2>${E(info.title)}</h2><p class="cc-lede">${E(info.lede)}</p></div></header>
    ${stepRail(step)}
    <div class="cc-body${noLead ? ' no-lead' : ''}"><div class="cc-main cc-enter-${E(dir)}" id="character-form">${pages[info.id]()}</div>${noLead ? '' : leadPanel()}</div>
    <footer class="cc-nav">${step > 0 ? button('‹ Back', 'step-back', 'secondary') : button('‹ Menu', 'back', 'secondary')}<span class="cc-nav-mid">${blocked ? `<small class="cc-blocked">${E(blocked)}</small>` : ''}${surprise}</span>${next}${step === CREATE_STEPS.length - 1 ? button('Start over', 'restart', 'secondary') : ''}</footer>
  </section>`;
}
function scheduleLivePreview(delay = 140) {
  clearTimeout(live.timer);
  live.timer = setTimeout(refreshLivePreview, delay);
}
async function refreshLivePreview() {
  if (state.phase !== 'create' || !state.options || !state.draft.creation_seed) return;
  const seq = ++live.seq; const build = {...buildPayload(), name: state.draft.name || 'Unnamed lead'};
  try {
    const reply = await state.client.previewCharacter(build);
    if (seq !== live.seq) return;
    if (!reply.ok) { state.liveError = reply.error?.message || 'Preview unavailable'; }
    else { state.live = reply.result?.character || null; state.liveError = ''; }
  } catch (error) { if (seq === live.seq) state.liveError = error.message; }
  if (state.phase === 'create' && !state.busy) render();
}
async function ensureCreationSeed() {
  if (state.draft.creation_seed && !state.draft.seed_auto) return;
  const reply = await state.client.request('peek_creation_seed', {});
  const nextSeed = reply.ok ? reply.result?.seed?.creation_seed : String(Date.now() % 100000).padStart(5, '0');
  if (state.draft.creation_seed && state.draft.creation_seed !== nextSeed) {
    state.roll = null; state.preview = null; state.live = null; state.liveError = '';
    state.draft.roll_set = 0; state.draft.ability_assignment = 'auto';
  }
  state.draft.creation_seed = nextSeed;
  state.draft.seed_auto = true; persistUiState();
}
function setCreateStep(index, dir) {
  const target = Math.max(0, Math.min(CREATE_STEPS.length - 1, index));
  state.stepAnim = dir || (target > createStep() ? 'fwd' : 'back');
  state.draft.create_step = target;
  state.draft.max_step = Math.max(Number(state.draft.max_step || 0), target);
  persistUiState();
  window.scrollTo?.({top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
}
async function enterSummary() {
  setCreateStep(STEP_INDEX.summary, 'fwd'); state.live = state.live && state.live.notes ? state.live : null; render();
  await work(async () => {
    const build = buildPayload();
    const reply = result(await state.client.previewCharacter(build));
    state.preview = reply.result; state.live = reply.result?.character || null;
  }, 'Assembling the final sheet');
}
async function rollAbilities() {
  const seed = state.draft.creation_seed;
  if (!seed) throw Error('The build seed is missing; reopen character creation.');
  if (state.roll?.roll_set === 1) throw Error('The single ability-score reroll has already been used.');
  const nextSet = state.roll ? 1 : 0;
  const reply = result(await state.client.characterRoll(seed, nextSet));
  state.roll = reply.result?.ability_roll || null; state.draft.roll_set = nextSet; state.draft.ability_assignment = 'auto';
  state.rollAnim = true;
  state.note = nextSet ? 'Rerolled. The first set stays in the creation receipt.' : '';
  persistUiState();
}
async function surpriseStep() {
  const d = state.draft; const id = CREATE_STEPS[createStep()].id;
  const n = d.surprise_n = Number(d.surprise_n || 0) + 1;
  const pick = (rows, current) => { const pool = rows.filter(row => row.id !== current); return pool.length ? pool[seededIndex(`${d.creation_seed}:${id}:${n}`, pool.length)].id : current; };
  if (id === 'ancestry') { d.race = pick(state.options.races, d.race); d.floating_bonuses = 'auto'; d.appearance = {}; }
  else if (id === 'class') { d.character_class = pick(state.options.classes, d.character_class); d.spell_budget = 0; d.spells = 'auto'; d.spell_mode = 'auto'; d.skills = 'auto'; d.skill_mode = 'auto'; }
  else if (id === 'background') d.background = pick(state.options.backgrounds, d.background);
  else if (id === 'abilities') {
    if (!state.roll) await rollAbilities();
    else { const scores = [...state.roll.scores]; const order = [...ABILITIES]; for (let i = order.length - 1; i > 0; i--) { const j = seededIndex(`${d.creation_seed}:shuffle:${n}:${i}`, i + 1); [order[i], order[j]] = [order[j], order[i]]; } d.ability_assignment = Object.fromEntries(order.map((a, i) => [a, scores[i]])); }
  } else if (id === 'training') {
    const cls = optionBy('classes', d.character_class); const race = optionBy('races', d.race);
    const pool = [...(cls.skills || [])]; const chosen = [];
    while (chosen.length < cls.skill_count && pool.length) chosen.push(pool.splice(seededIndex(`${d.creation_seed}:skill:${n}:${chosen.length}`, pool.length), 1)[0]);
    const rest = Object.keys(state.options.skills || {}).filter(s => !chosen.includes(s));
    for (let i = 0; i < (race.extra_skills || 0); i++) chosen.push(rest.splice(seededIndex(`${d.creation_seed}:extra:${n}:${i}`, rest.length), 1)[0]);
    d.skill_mode = 'manual'; d.skills = chosen; d.spell_mode = 'auto'; d.spells = 'auto';
  } else if (id === 'look') {
    const fields = state.options?.appearance?.fields || {}; d.appearance = {};
    for (const field of LOOK_FIELDS) { const rows = (fields[field]?.options || []).filter(row => !row.races || row.races.includes(d.race)); if (rows.length) d.appearance[field] = rows[seededIndex(`${d.creation_seed}:look:${field}:${n}`, rows.length)].id; }
  }
  persistUiState();
}
async function randomizeWholeBuild() {
  await ensureCreationSeed();
  const d = state.draft;
  const reply = result(await state.client.request('randomize_build', {creation_seed: d.creation_seed, name: d.name || '', level: Number(d.level || 1)}));
  const b = reply.result.build;
  Object.assign(d, {race: b.race, character_class: b.character_class, background: b.background, gender: b.gender, appearance: b.appearance,
    roll_set: 0, ability_assignment: 'auto', floating_bonuses: 'auto', advancements: 'auto', advancement_mode: 'auto', skills: 'auto', skill_mode: 'auto',
    spells: 'auto', spell_mode: 'auto', spell_budget: 0});
  if (!String(d.name || '').trim()) d.name = `Wanderer ${d.creation_seed}`;
  const roll = result(await state.client.characterRoll(d.creation_seed, 0));
  state.roll = roll.result?.ability_roll || null;
  d.max_step = CREATE_STEPS.length - 1; persistUiState();
  const previewReply = result(await state.client.previewCharacter(buildPayload()));
  state.preview = previewReply.result; state.live = previewReply.result?.character || null;
  setCreateStep(STEP_INDEX.summary, 'fwd');
}
function bindCreator() {
  if (state.phase !== 'create') return;
  document.querySelectorAll('[data-choice]').forEach(node => node.onclick = () => {
    const [kind, id] = node.dataset.choice.split(':'); const d = state.draft;
    if (kind === 'race') { if (d.race !== id) { d.floating_bonuses = 'auto'; d.appearance = {}; } d.race = id; }
    else if (kind === 'class') { if (d.character_class !== id) { d.spell_budget = 0; d.spells = 'auto'; d.spell_mode = 'auto'; d.skills = 'auto'; d.skill_mode = 'auto'; d.ability_assignment = 'auto'; } d.character_class = id; }
    else if (kind === 'background') d.background = id;
    else if (kind === 'gender') d.gender = id;
    persistUiState(); render(); scheduleLivePreview();
  });
  document.querySelectorAll('[data-skill-pick]').forEach(node => node.onclick = () => {
    const d = state.draft; const skill = node.dataset.skillPick;
    const count = (optionBy('classes', d.character_class).skill_count || 0) + (optionBy('races', d.race).extra_skills || 0);
    let list = d.skill_mode === 'manual' ? [...(d.skills || [])] : [...(state.live?.receipt?.trained_skills || [])];
    if (list.includes(skill)) list = list.filter(s => s !== skill);
    else {
      list.push(skill);
      if (list.length > count) {
        // Drop the oldest pick whose removal still leaves enough class skills.
        const cls = optionBy('classes', d.character_class); const isClass = s => (cls.skills || []).includes(s);
        const drop = list.slice(0, -1).findIndex(s => list.filter(x => x !== s && isClass(x)).length >= (cls.skill_count || 0));
        list.splice(drop >= 0 ? drop : 0, 1);
      }
    }
    d.skill_mode = 'manual'; d.skills = list; persistUiState(); render(); scheduleLivePreview();
  });
  document.querySelectorAll('[data-look]').forEach(node => node.onclick = () => {
    const [field, id] = node.dataset.look.split(':');
    state.draft.appearance = {...(state.draft.appearance || {}), [field]: id}; persistUiState(); render(); scheduleLivePreview();
  });
  const name = document.querySelector('.cc-name input');
  if (name) {
    name.oninput = () => { state.draft.name = name.value; persistUiState(); const next = document.querySelector('.cc-next'); const ok = !!name.value.trim(); next?.setAttribute('aria-disabled', ok ? 'false' : 'true'); document.querySelector('.cc-blocked')?.toggleAttribute('hidden', ok); };
    name.onchange = () => { state.draft.name = name.value.trim(); persistUiState(); scheduleLivePreview(); };
    name.onkeydown = event => { if (event.key === 'Enter') { event.preventDefault(); event.stopPropagation(); state.draft.name = name.value.trim(); persistUiState(); creatorAction('step-next'); } };
  }
  // Arrow keys walk a card grid the way a controller would.
  document.querySelectorAll('.cc-cards').forEach(grid => grid.onkeydown = event => {
    if (!['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp'].includes(event.key)) return;
    const cards = [...grid.querySelectorAll('.cc-card')]; const at = cards.indexOf(document.activeElement);
    if (at < 0) return; event.preventDefault();
    const step = ['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1;
    const target = cards[(at + step + cards.length) % cards.length]; target.focus(); target.click();
  });
}
async function creatorAction(action) {
  if (action === 'step-next') {
    const step = createStep(); const blocked = stepValid(step);
    if (blocked) { state.error = blocked; render(); document.querySelector('.cc-name input')?.focus(); return true; }
    state.error = '';
    if (step + 1 === STEP_INDEX.summary) await enterSummary();
    else { setCreateStep(step + 1, 'fwd'); render(); scheduleLivePreview(0); }
    return true;
  }
  if (action === 'step-back') { setCreateStep(createStep() - 1, 'back'); state.error = ''; render(); return true; }
  if (action.startsWith('step-goto:')) {
    const index = Number(action.slice(10));
    if (!Number.isInteger(index) || index > Math.max(Number(state.draft.max_step || 0), createStep())) return true;
    if (index === STEP_INDEX.summary) await enterSummary(); else { setCreateStep(index); render(); scheduleLivePreview(0); }
    return true;
  }
  if (action === 'surprise-step') { await work(surpriseStep, 'Consulting the dice'); scheduleLivePreview(0); return true; }
  if (action === 'randomize-build') { await work(randomizeWholeBuild, 'Rolling a whole lead'); return true; }
  if (action === 'roll-abilities') { await work(rollAbilities, 'Rolling 4d6 six times'); scheduleLivePreview(0); return true; }
  if (action === 'assign-auto') { state.draft.ability_assignment = 'auto'; persistUiState(); render(); scheduleLivePreview(0); return true; }
  return false;
}
// The old standalone preview screen now lives as the final creator step.
function resetCreationDraft() {
  state.draft = {...state.draft, name: '', creation_seed: '', seed_auto: false, level: 1, roll_set: 0, ability_assignment: 'auto', floating_bonuses: 'auto', advancements: 'auto', advancement_mode: 'auto', skills: 'auto', skill_mode: 'auto', spells: 'auto', spell_mode: 'auto', spell_budget: 0, appearance: {}, create_step: 0, max_step: 0, surprise_n: 0};
  state.roll = null; state.preview = null; state.live = null; state.liveError = ''; persistUiState();
}
function preview() { state.phase = 'create'; state.draft.create_step = CREATE_STEPS.length - 1; return creator(); }
function runs() {
  const isSandbox = state.runsFilter === 'SANDBOX';
  const verb = isSandbox ? 'Resume' : 'Continue';
  const heading = isSandbox ? 'Resume the Simulation' : 'Continue the Story';
  const emptyCopy = isSandbox
    ? 'No saved Simulation runs are available. Start one from Simulation Mode.'
    : 'No saved Story runs are available. Start one from Story Mode.';
  return `${breadcrumb('Main Menu', isSandbox ? 'Simulation Mode' : 'Story Mode', heading)}${atmosphere('runs', heading, 'Choose any host-reported run and resume it through the same public engine contract.')}${card(heading, `${state.runs.length ? `<div class="run-list">${state.runs.map(run => {
    const id = typeof run === 'string' ? run : run.run_id;
    return `<article class="run-row"><div><strong>${E(id)}</strong><small>${E(run.summary || run.status || 'Saved run')}</small></div>${button(verb, `load:${id}`)}</article>`;
  }).join('')}</div>` : `<p>${E(emptyCopy)}</p>`}
  <div class="actions">${button('Refresh list', 'refresh-runs')}${button('Back', 'back', 'secondary')}</div>`)}`;
}

function visualRole(item = {}, fallback = 'adventurer') {
  const text = `${item.name || ''} ${item.role || ''}`.toLowerCase();
  if (/mage|magic|cleric|caster|witch|wellkeeper/.test(text)) return 'caster';
  if (/guard|steward|fighter|warrior|sentinel/.test(text)) return 'guard';
  if (/town|resident|merchant|keeper/.test(text)) return 'townsfolk';
  return fallback;
}
// Equipment visuals come from the host's `presentation` block on each public
// item -- rarity, silhouette, material, fx -- which the host derives from the
// item's own mechanics. Nothing here reads an item NAME: a name regex draws
// "Hood of the Plate Captain" as plate armour, and a staff as a sword.
function equipmentPresentations(item = {}) {
  return (Array.isArray(item.equipment) ? item.equipment : [])
    .map(row => row && row.presentation)
    .filter(row => row && typeof row === 'object');
}
// Shapes the paperdoll can actually draw; anything else falls back to a blade.
const WEAPON_SILHOUETTES = Object.freeze({sword: 'sword', dagger: 'sword', axe: 'sword', staff: 'staff', bow: 'bow', shield: 'shield'});
function visualWeapon(item = {}) {
  const shapes = equipmentPresentations(item).map(row => WEAPON_SILHOUETTES[row.silhouette]).filter(Boolean);
  // A drawn weapon beats a shield: the shield has its own off-hand layer.
  return shapes.find(shape => shape !== 'shield') || shapes[0] || 'sword';
}
const ARMOR_MATERIALS = Object.freeze({plate: 'plate', chain: 'chain', leather: 'leather', robe: 'robe', cloth: 'robe'});
const WORN_SILHOUETTES = Object.freeze({helm: 'headgear', cloak: 'cloak', shield: 'offhand-shield', trinket: 'trinket'});
function visualItemTokens(item = {}) {
  const tokens = [];
  for (const row of equipmentPresentations(item)) {
    if (row.silhouette === 'armor' && ARMOR_MATERIALS[row.material] && !tokens.some(t => ARMOR_MATERIALS[t])) {
      tokens.push(ARMOR_MATERIALS[row.material]);
    }
    const worn = WORN_SILHOUETTES[row.silhouette];
    if (worn && !tokens.includes(worn)) tokens.push(worn);
  }
  return tokens;
}
// Rarity ladder, matching hollowstar/phases.py Tier. "unknown" is what the host
// substitutes for an unidentified Imprint and must rank lowest -- an
// unidentified item that sparkled would reveal what it is.
const RARITY_RANK = Object.freeze({unknown: 0, mundane: 1, magical: 2, artifact: 3, blessed: 4});
function visualRarity(item = {}) {
  let best = 'mundane';
  for (const row of equipmentPresentations(item)) {
    if ((RARITY_RANK[row.rarity] || 0) > (RARITY_RANK[best] || 0)) best = row.rarity;
  }
  return best;
}
function visualEffectTokens(item = {}) {
  const allowed = new Set(['ember', 'frost', 'tide', 'gale', 'stone', 'arcane', 'hallow', 'radiant', 'wither', 'mind', 'resonant', 'acid', 'force', 'bleed', 'phase', 'silver', 'dense']);
  const fx = new Set();
  for (const row of equipmentPresentations(item)) {
    if (row.rarity === 'unknown') continue;
    for (const token of Array.isArray(row.fx) ? row.fx : []) {
      const safe = String(token).toLowerCase();
      if (allowed.has(safe)) fx.add(safe);
    }
  }
  return [...fx].sort();
}
// Cosmetic choices from character creation arrive as {field:{id,name,hex}}.
// They are emitted as CSS custom properties rather than as more class names so
// the stylesheet stays a fixed set of rules whatever the palette grows to.
// Each tinted layer is a gradient between a base colour and a companion
// shade. Setting only the base leaves the companion at its default, which
// shows up as auburn hair keeping a lilac highlight -- so the companions are
// derived here from the chosen colour.
const APPEARANCE_VARS = Object.freeze({
  skin_tone: ['--skin', ['--skin-shadow', -0.22]],
  hair_color: ['--hair', ['--hair-light', 0.22]],
  eye_color: ['--eye'],
  outfit: ['--outfit', ['--outfit-light', 0.18], ['--outfit-dark', -0.3]],
});
const HEX = /^#[0-9a-f]{6}$/i;
function shadeHex(hex, amount) {
  const channel = index => {
    const value = parseInt(hex.slice(1 + index * 2, 3 + index * 2), 16);
    const shifted = amount >= 0 ? value + (255 - value) * amount : value * (1 + amount);
    return Math.max(0, Math.min(255, Math.round(shifted))).toString(16).padStart(2, '0');
  };
  return `#${channel(0)}${channel(1)}${channel(2)}`;
}
function appearanceStyle(item = {}) {
  const appearance = item.appearance && typeof item.appearance === 'object' ? item.appearance : {};
  const parts = [];
  for (const [field, [prop, ...companions]] of Object.entries(APPEARANCE_VARS)) {
    const hex = appearance[field] && appearance[field].hex;
    // Only a literal six-digit colour is allowed through; the value lands in a
    // style attribute, so anything else is dropped rather than escaped.
    if (typeof hex !== 'string' || !HEX.test(hex)) continue;
    parts.push(`${prop}:${hex}`);
    for (const [companion, amount] of companions) parts.push(`${companion}:${shadeHex(hex, amount)}`);
  }
  const scale = appearance.body_type && Number(appearance.body_type.scale);
  if (Number.isFinite(scale) && scale > 0) parts.push(`--build:${Math.min(1.25, Math.max(0.8, scale))}`);
  return parts.join(';');
}
function appearanceClasses(item = {}) {
  const appearance = item.appearance && typeof item.appearance === 'object' ? item.appearance : {};
  const slug = value => String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '-');
  return ['hair_style', 'body_type', 'outfit']
    .map(field => appearance[field] && appearance[field].id ? `${field.replace('_', '-')}-${slug(appearance[field].id)}` : '')
    .filter(Boolean).join(' ');
}
function isChampion(item = {}) {
  const identity = String(item.identity || '').toLowerCase();
  return item.is_champion === true || item.kind === 'champion' || ['doran', 'sera', 'wren'].includes(identity);
}
const SPRITE_LAYER_CATALOG = Object.freeze({
  shadow: {className: 'char-shadow', slot: 'ground'}, wings: {className: 'char-wings', slot: 'ground'},
  'effect:aura': {className: 'char-aura', slot: 'effect'},
  cape: {className: 'char-cape', slot: 'clothing'}, legs: {className: 'char-legs', slot: 'clothing'},
  boots: {className: 'char-boots', slot: 'clothing'}, 'arm:back': {className: 'char-arm char-arm-back', slot: 'clothing'},
  'hand:back': {className: 'char-hand char-hand-back', slot: 'body'}, coat: {className: 'char-coat', slot: 'clothing'},
  seam: {className: 'char-seam', slot: 'clothing'}, neck: {className: 'char-neck', slot: 'body'},
  ears: {className: 'char-ears', slot: 'body'}, head: {className: 'char-head', slot: 'body'},
  hair: {className: 'char-hair', slot: 'body'}, fringe: {className: 'char-fringe', slot: 'body'},
  brows: {className: 'char-brows', slot: 'body'}, eyes: {className: 'char-eyes', slot: 'body'},
  nose: {className: 'char-nose', slot: 'body'}, mouth: {className: 'char-mouth', slot: 'body'},
  collar: {className: 'char-collar', slot: 'equipment'}, shoulders: {className: 'char-shoulders', slot: 'equipment'},
  'arm:front': {className: 'char-arm char-arm-front', slot: 'clothing'},
  'hand:front': {className: 'char-hand char-hand-front', slot: 'body'}, cuffs: {className: 'char-cuffs', slot: 'clothing'},
  belt: {className: 'char-belt', slot: 'equipment'}, buckle: {className: 'char-buckle', slot: 'equipment'},
  emblem: {className: 'char-emblem', slot: 'equipment'},
  'weapon:sword': {className: 'char-weapon sword', slot: 'weapon'},
  'weapon:staff': {className: 'char-weapon staff', slot: 'weapon'},
  'weapon:bow': {className: 'char-weapon bow', slot: 'weapon'},
  'weapon:shield': {className: 'char-weapon shield', slot: 'weapon'},
  'item:headgear': {className: 'char-headgear', slot: 'equipment', src: 'assets/sprites/layers/headgear.svg'},
  'item:cloak': {className: 'char-cloak', slot: 'equipment', src: 'assets/sprites/layers/cloak.svg'},
  'item:offhand-shield': {className: 'char-offhand-shield', slot: 'equipment', src: 'assets/sprites/layers/shield.svg'},
  'item:trinket': {className: 'char-trinket', slot: 'equipment', src: 'assets/sprites/layers/trinket.svg'},
});
const BASE_SPRITE_LAYERS = ['shadow', 'wings', 'cape', 'legs', 'boots', 'arm:back', 'hand:back', 'coat', 'seam', 'neck', 'ears', 'head', 'hair', 'fringe', 'brows', 'eyes', 'nose', 'mouth', 'collar', 'shoulders', 'arm:front', 'hand:front', 'cuffs', 'belt', 'buckle', 'emblem'];
function visibleGearTheme(item = {}) {
  // Worn armour decides the coat treatment; "travel" is the unarmoured look,
  // which lets the creator's outfit choice show through.
  const worn = equipmentPresentations(item).find(row => row.silhouette === 'armor' && ARMOR_MATERIALS[row.material]);
  return worn ? ARMOR_MATERIALS[worn.material] : 'travel';
}
function spriteLayerMarkup(layerId) {
  const layer = SPRITE_LAYER_CATALOG[layerId];
  if (!layer) return '';
  // Future transparent assets are registered here; public state supplies IDs,
  // never arbitrary URLs.
  if (layer.src) return `<img class="sprite-layer ${E(layer.className || '')}" data-sprite-layer="${E(layer.slot)}" data-layer-id="${E(layerId)}" src="${E(layer.src)}" alt="" aria-hidden="true">`;
  return `<i class="sprite-layer ${E(layer.className)}" data-sprite-layer="${E(layer.slot)}" data-layer-id="${E(layerId)}" aria-hidden="true"></i>`;
}
function visualIdentity(item = {}) {
  return String(item.identity || item.sprite_id || item.id || 'adventurer').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'adventurer';
}
function presentationAppearance(item = {}) {
  return item.sprite_id || `${item.race_id || 'human'}-${item.gender || 'other'}`;
}
function visualExpression(item = {}, pose = 'idle') {
  const status = JSON.stringify(item.status || item.conditions || []).toLowerCase();
  if (Number(item.hp ?? 1) <= 0) return 'fallen';
  if (/bleed|burn|fear|poison|stun|wound/.test(status)) return 'strained';
  if (pose === 'combat') return 'focused';
  return visualIdentity(item) === 'wren' ? 'serene' : 'alert';
}
function layeredCharacterFigure(item = {}, extra = '', pose = 'idle', champion = false) {
  const role = visualRole(item); const weapon = visualWeapon(item);
  const appearance = presentationAppearance(item);
  const identity = visualIdentity(item);
  const resolvedPose = ['combat', 'travel'].includes(pose) ? pose : 'idle';
  const requested = Array.isArray(item.sprite_layer_ids) ? item.sprite_layer_ids.filter(id => SPRITE_LAYER_CATALOG[id]) : [];
  const itemTokens = visualItemTokens(item);
  const itemLayers = itemTokens.map(token => `item:${token}`);
  const effects = visualEffectTokens(item);
  const layerIds = [...new Set([...BASE_SPRITE_LAYERS, ...(effects.length ? ['effect:aura'] : []), `weapon:${weapon}`, ...itemLayers, ...requested])].filter(id => SPRITE_LAYER_CATALOG[id]);
  // Cosmetics ride as custom properties, gear state as classes: a value the
  // stylesheet interpolates vs. a selector it has to match.
  const styleVars = appearanceStyle(item);
  const rarity = visualRarity(item);
  return `<div class="scene-character paperdoll-character ${champion ? 'champion-character' : 'custom-character'} ${E(role)} ${E(extra)} identity-${E(identity)} appearance-${E(appearance)} ${E(appearanceClasses(item))} gear-${E(visibleGearTheme(item))} rarity-${E(rarity)} ${effects.map(token => `fx-${E(token)}`).join(' ')} ${itemTokens.map(token => `item-${E(token)}`).join(' ')} pose-${E(resolvedPose)} expression-${E(visualExpression(item, resolvedPose))}"${styleVars ? ` style="${E(styleVars)}"` : ''} data-sprite-id="${E(appearance)}" data-character-identity="${E(identity)}" data-sprite-pose="${E(resolvedPose)}" data-sprite-rarity="${E(rarity)}" data-sprite-layers="${E(layerIds.join(' '))}" aria-label="${E(item.name || role)} ${champion ? 'champion' : 'custom character'}">
    ${layerIds.map(spriteLayerMarkup).join('')}
    <span class="actor-nameplate">${E(item.name || role)}</span></div>`;
}
function characterFigure(item = {}, extra = '', pose = 'idle') {
  if (isChampion(item)) return championFigure(item, extra, pose);
  return layeredCharacterFigure(item, extra, pose, false);
}
function championFigure(item = {}, extra = '', pose = 'idle') {
  const identity = visualIdentity(item);
  const art = championPoseArt(identity);
  const base = layeredCharacterFigure(item, extra, pose, true);
  if (!art) return base;
  const recentManeuver = state.lastManeuver;
  const maneuver = recentManeuver?.actor === item.id && Date.now() - recentManeuver.at < 2200 ? recentManeuver.maneuver : null;
  const isPresentationTarget = state.presentation?.actor_id === item.id;
  const poseKey = resolveChampionPose(identity, {
    alive: Number(item.hp ?? 1) > 0,
    inCombat: pose === 'combat',
    maneuver,
    animation: isPresentationTarget ? state.presentation.animation : null,
  });
  const path = getChampionPosePath(identity, poseKey);
  // The authored pose PNG replaces the generic CSS paperdoll for champions
  // that have dedicated art; layeredCharacterFigure's markup stays in the DOM
  // as a fallback (revealed by CSS only if the image 404s), so a broken path
  // degrades to the same figure every other identity already gets.
  return base.replace(
    'class="scene-character',
    `data-champion-pose="${E(poseKey)}" class="scene-character champion-pose-art`,
  ).replace(
    '<span class="actor-nameplate">',
    `<img class="champion-pose-image" src="${E(path)}" alt="" aria-hidden="true" onerror="this.closest('.champion-pose-art')?.classList.add('champion-pose-fallback')"><span class="actor-nameplate">`,
  );
}
function scenePosition(item = {}, index = 0) {
  const p = Array.isArray(item.position) ? item.position : [index ? 40 : 10, index * 10, 0];
  const x = Math.max(5, Math.min(90, Number(p[0] || 0) / 120 * 100));
  const z = Math.max(0, Number(p[2] || 0));
  return `left:${x}%;bottom:${Math.min(62, 21 + z * .45)}px;`;
}
function battleCharacterFigure(item = {}, index = 0) {
  const presentation = state.presentation || {};
  const animation = presentation.actor_id === item.id ? (presentation.animation?.attack || presentation.animation?.move || presentation.animation?.defense || presentation.animation?.dodge || presentation.animation?.cast || presentation.animation?.flight || '') : '';
  const extra = `${index >= party().length ? 'opponent' : ''} battle-actor`;
  const html = characterFigure(item, extra, 'combat');
  return html.replace('class="scene-character', `style="${scenePosition(item, index)}" data-animation="${E(animation)}" class="scene-character`);
}
function flightActor(item = {}, index = 0, arena = {}) {
  const row = (arena.actors || []).concat(arena.opposition || []).find(value => value.id === item.id) || {};
  const x = Math.max(4, Math.min(92, Number(row.x ?? 10) / 120 * 100));
  const y = Math.max(8, Math.min(78, 78 - Number(row.y ?? 10) / 120 * 62));
  const z = Math.max(0, Number(row.z || 0));
  const opponent = (arena.opposition || []).some(value => value.id === item.id);
  const sprite = item.identity === 'wren' ? '<span class="wren-flight-sprite" aria-hidden="true"></span>' : '';
  return `<div class="flight-actor ${opponent ? 'flight-opponent' : 'flight-player'}" style="left:${x}%;top:${y}%;transform:translateZ(${z}px)" data-actor="${E(item.id)}" aria-label="${E(item.name || item.id)} at flight position"><div class="flight-glow"></div>${sprite}<span>${E(item.name || item.id)}</span><small>${E(item.hp ?? '?')} / ${E(item.max_hp ?? '?')}</small></div>`;
}
function arcadeStage() {
  const arena = state.view?.arcade || {};
  const wave = arena.complete ? 'Gate open' : `Wave ${Math.min((arena.wave_index || 0) + 1, arena.waves || 1)} / ${arena.waves || 1}`;
  return `<section class="arcade-stage" data-arcade-root aria-label="Live host-resolved arcade encounter">
    <div class="arcade-stage-header"><div><p class="eyebrow">Arcade encounter</p><h2>Market crossing</h2></div><span class="arcade-frame" data-arcade-status>${E(wave)} · Frame ${E(arena.frame ?? 0)}</span></div>
    <div class="arcade-canvas-mount" data-arcade-canvas></div>
    <p class="notice">Positions, obstacles, and hit confirmation arrive from the host. The canvas only interpolates the latest public frames.</p>
  </section>`;
}
function arcadeControls() {
  const selected = actor();
  const identity = selected.identity;
  const modes = identity === 'doran' ? ['run', 'jump', 'climb'] : identity === 'wren' ? ['run', 'jump', 'fly'] : ['run', 'jump'];
  const flight = identity === 'wren' ? `<div class="arcade-flight-controls"><span class="label">Wren flight</span><button type="button" class="action secondary" data-arcade-flight="on">Take flight</button><button type="button" class="action secondary" data-arcade-flight="off">Land</button></div>` : '';
  return `<div class="arcade-controls" data-arcade-controls aria-label="Arcade controls"><div class="arcade-pad"><button type="button" class="action arcade-control" data-arcade-dx="0" data-arcade-dy="5" aria-label="Move up">▲</button><button type="button" class="action arcade-control" data-arcade-dx="-5" data-arcade-dy="0" aria-label="Move left">◀</button><button type="button" class="action arcade-control arcade-attack" data-arcade-attack="true">Attack</button><button type="button" class="action arcade-control" data-arcade-dx="5" data-arcade-dy="0" aria-label="Move right">▶</button><button type="button" class="action arcade-control" data-arcade-dx="0" data-arcade-dy="-5" aria-label="Move down">▼</button></div><div class="arcade-combat-controls" aria-label="Combat options"><button type="button" class="action arcade-control arcade-block" data-arcade-block="true" aria-label="Hold to block">Block</button><button type="button" class="action arcade-control" data-arcade-dodge="true" aria-label="Dodge">Dodge</button><button type="button" class="action arcade-control" data-arcade-ranged="true" aria-label="Ranged attack">Ranged</button></div><div class="arcade-modes"><span class="label">Movement mode</span>${modes.map(mode => `<button type="button" class="action secondary" data-arcade-mode="${E(mode)}">${E(mode)}</button>`).join('')}</div>${flight}<p class="notice">Keyboard: WASD or arrow keys to move · Space / Enter to attack (chains into a combo) · hold Shift to block · X to dodge · F for a ranged attack.</p></div>`;
}
function battleStage() {
  const fighters = [...party(), ...(state.view?.opposition || [])];
  if (state.view?.arcade && !state.view.arcade.complete) return arcadeStage();
  const arena = state.view?.flight_arena;
  if (arena) return `<section class="illustrated-scene scene-battle flight-stage" aria-label="Live flight combat arena">
    <div class="scene-moon"></div><div class="flight-cloud cloud-one"></div><div class="flight-cloud cloud-two"></div>
    <div class="flight-arena-label"><strong>Wren's flight</strong><small>Host-resolved aerial encounter</small></div>
    ${fighters.map((item, index) => flightActor(item, index, arena)).join('')}
    <div class="flight-reticle" aria-hidden="true"></div>
  </section>`;
  return `<section class="illustrated-scene scene-battle battle-stage" aria-label="Live combat encounter">
    <div class="scene-moon"></div><div class="scene-mountains back"></div><div class="scene-mountains front"></div><div class="scene-road"></div>
    ${fighters.map((item, index) => battleCharacterFigure(item, index)).join('') || '<p class="notice battle-empty">No public combatants reported.</p>'}
    <div class="scene-frame-label"><strong>${E(state.view?.room?.name || 'The Reliquary')}</strong><small>Live host-resolved encounter</small></div>
  </section>`;
}
function sceneWorld(kind = 'room') {
  const r = state.view?.room || {}; const lead = actor(); const foe = state.view?.opposition?.[0];
  const pose = state.view?.scene?.animation === 'travel' ? 'travel' : (kind === 'battle' ? 'combat' : 'idle');
  return `<section class="illustrated-scene scene-${E(kind)}" aria-label="Illustrated ${E(kind)} view">
    <div class="scene-moon"></div><div class="scene-mountains back"></div><div class="scene-mountains front"></div>
    <div class="scene-town"></div><div class="scene-road"></div><div class="scene-well"></div>
    ${characterFigure(lead, '', pose)}${kind === 'battle' && foe ? characterFigure(foe, 'opponent', 'combat') : ''}
    <div class="scene-frame-label"><strong>${E(r.name || r.id || 'The Reliquary')}</strong><small>${kind === 'battle' ? 'Public encounter projection' : 'Public room projection'}</small></div>
  </section>`;
}
function atmosphere(kind, titleText, subtitle) {
  return `<section class="atmosphere atmosphere-${E(kind)}" title="${E(FLAVOR.screens[kind] || subtitle)}"><div class="atmosphere-orbit"></div><span class="atmosphere-glyph" aria-hidden="true">${kind === 'journal' ? '▤' : kind === 'map' ? '◎' : kind === 'library' ? '⌘' : '✧'}</span><div><p class="eyebrow">Hollow Star interface</p><h2>${E(titleText)}</h2><p>${E(subtitle)}</p><small class="atmosphere-aside">${E(FLAVOR.screens[kind] || '')}</small></div></section>`;
}
function readable(value) {
  if (value === null || value === undefined || value === '') return '';
  if (typeof value !== 'object') return String(value);
  if (Array.isArray(value)) return value.map(readable).filter(Boolean).join(' · ');
  const primary = value.name || value.kind || value.room || value.text || value.label || value.id;
  const extras = [
    value.difficult ? 'difficult' : '',
    value.cover ? `cover ${value.cover}` : '',
    value.distance_ft ? `${value.distance_ft} ft` : '',
    value.door ? `via ${readable(value.door)}` : '',
  ].filter(Boolean).join(', ');
  if (!primary) return extras;
  return extras ? `${readable(primary)} (${extras})` : readable(primary);
}
function objectLabel(obj = {}) { return obj.name || obj.display_name || (obj.discovered ? obj.object_id || obj.id : 'an unexamined object') || 'an unexamined object'; }
function objectActions(obj = {}) {
  const kind = String(obj.kind || '').toLowerCase();
  const openable = kind === 'cabinet' || kind === 'container';
  const buttons = [button('Inspect', `object-inspect:${obj.object_id || obj.id}`, 'secondary')];
  if (!obj.discovered) buttons.push(button('Search', `object-search:${obj.object_id || obj.id}`, 'secondary'));
  if (openable) buttons.push(button('Open', `object-open:${obj.object_id || obj.id}`, 'secondary'));
  return buttons.join('');
}
function roomObjects() {
  const objects = Object.values(state.view?.room?.objects || {}).filter(obj => obj && obj.visible !== false);
  if (!objects.length) return '';
  return `<div class="room-objects"><p class="label">Things worth a closer look</p>${objects.map(obj => `<div class="object-row"><span>${E(objectLabel(obj))}${obj.discovered ? '' : '<small> · undiscovered</small>'}</span><span class="actions compact-actions">${objectActions(obj)}</span></div>`).join('')}</div>`;
}
function room() {
  const r = state.view?.room || {};
  const exits = Object.entries(r.exits || {}).map(([direction, destination]) => `${direction}: ${readable(destination)}`).join(' · ');
  const tells = (r.visible_tells || r.tells || []).map(readable).filter(Boolean).join(' · ');
  const description = readable(r.description || r.atmosphere || state.view?.narration || state.receipt?.message || state.receipt?.narration);
  return `${sceneWorld('room')}${card('Sanctum room', `<div class="room-hero"><div><p class="eyebrow">${E(readable(r.apparent_function || r.condition) || 'Observed space')}</p><h2>${E(readable(r.name || r.id) || 'Unreported room')}</h2><p>${E(description || 'No public description reported.')}</p></div><span class="room-sigil" aria-hidden="true">⌂</span></div>
    <div class="room-facts"><div><small>Law</small><strong>${E(readable(r.law) || 'Not reported')}</strong></div><div><small>Terrain</small><strong>${E(readable(r.terrain) || 'Not reported')}</strong></div><div><small>Exits</small><strong>${E(exits || 'None reported')}</strong></div></div>
    <p class="notice">${E(tells || 'No visible tells reported.')}</p>${roomObjects()}`)}`;
}
function journey() {
  const scene = state.view?.scene || {};
  const progress = Math.round(Number(scene.progress || 0) * 100);
  const pause = state.receipt?.pause;
  const entities = (scene.visible_entities || []).slice(0, 5).map(row => `<span class="journey-entity"><strong>${E(row.name || row.id)}</strong><small>${E(row.role || 'resident')}</small></span>`).join('');
  return `${sceneWorld('journey')}${card('Journey', `<div class="room-hero"><div><p class="eyebrow">${E(scene.floor_id || 'Reliquary')}</p><h2>${E(scene.phase || 'exploration')} · ${E(state.view?.room?.name || state.view?.room?.title || 'Unknown route')}</h2><p>Move from left to right through the public route. Social decisions remain yours; idle travel pauses when a meaningful choice appears.</p></div><span class="room-sigil">→</span></div>
    <div class="journey-progress" aria-label="Floor progress"><span style="width:${progress}%"></span></div><div class="journey-meta"><span>${E(progress)}% route progress</span><span>Background: ${E(scene.background_id || 'unreported')}</span><span>Direction: ${E(scene.direction || 'right')}</span></div>
    ${entities ? `<div class="journey-entities"><p class="label">Visible decision points</p>${entities}</div>` : '<p class="notice">No public residents are currently visible.</p>'}
    <div class="actions">${button(scene.travel?.active ? 'Traveling…' : 'Auto-travel to descent', 'auto-travel', 'primary')}${button('Advance safely', 'idle-tick', 'secondary')}${button('Open social view', 'tab:residents', 'secondary')}${button('Read current room', 'tab:room', 'secondary')}</div>
    <p class="notice">${E(scene.travel?.active ? `Host travel loop: ${scene.travel.destination || 'route'} · ${scene.travel.steps || 0} step(s).` : (pause?.message || 'Auto-travel follows the authored public route and stops at the descent decision.'))}</p>`)}`;
}
function autoToggle() {
  const auto = state.view?.auto;
  const stepActor = encounterStepActor();
  if (!auto?.supported || !stepActor || stepActor.startsWith('p')) return '';
  return `<button type="button" class="action secondary" data-auto-step="${E(auto.step_command)}">${auto.active ? 'Resolving NPC turn…' : 'Advance NPC turn'}</button>`;
}
function signatureActions() {
  const identity = actor().identity;
  const target = (state.view?.opposition || []).find(o => Number(o.hp ?? 1) > 0)?.id || '';
  if (identity === 'wren') {
    return `<div class="signature-actions"><p class="label">Wren's domain</p>${DOMAIN_FEATURES.map(row => `<button type="button" class="action signature" data-domain-feature="${E(row.feature)}" title="${E(row.label)}">${E(row.label)}</button>`).join('')}</div>`;
  }
  if (identity === 'doran') {
    return `<div class="signature-actions"><p class="label">Doran's maneuvers</p>${MANEUVERS.map(row => `<button type="button" class="action signature" data-maneuver="${E(row.maneuver)}" data-target="${E(row.needsTarget ? target : '')}" title="${E(row.label)}">${E(row.label)}</button>`).join('')}</div>`;
  }
  return '';
}
function turnPanel() {
  const c = state.view?.combat;
  if (!c || c.complete) return '';
  const current = c.current;
  const row = [...party(), ...(state.view?.opposition || [])].find(item => item.id === current) || {};
  const economy = c.economy?.[current] || {};
  const scores = row.ability_scores || {};
  const modifiers = row.ability_modifiers || {};
  const pending = (c.pending || []).filter(window => window.reactor === actor().id || window.reactor === current);
  const reactions = pending.length ? `<div class="reaction-panel" aria-live="polite"><p class="label">Reaction window</p>${pending.map(window => `<div class="reaction-window"><strong>${E(window.kind || 'Reaction')}</strong><small>${E(window.target || 'A visible combatant')} · legal: ${E((window.options || []).join(' / ') || 'decline')}</small><div class="actions compact-actions">${(window.options || []).filter(option => option !== 'opportunity').map(option => button(option, `reaction:${option}`, 'secondary')).join('')}${button('Decline', 'reaction:decline_reaction', 'secondary')}</div></div>`).join('')}</div>` : '';
  const playerTurn = String(current || '').startsWith('p');
  const turnActions = playerTurn
    ? '<div class="actions turn-actions"><button type="button" class="action" data-engine-action="attack">⚔ Attack</button><button type="button" class="action" data-engine-action="cast">✧ Cast</button><button type="button" class="action" data-engine-action="move">⇢ Move</button><button type="button" class="action" data-engine-action="end_turn">⏳ End turn</button></div>'
    : '<p class="notice" aria-live="polite">NPC turn. Advance it through the host-resolved Encounter control.</p>';
  const developerNote = `<details class="developer-note"><summary>Developer note · next Combat pass</summary><p>Macro authoring, contextual spell selection, and richer terrain/range presentation still need dedicated controls. The host remains authoritative for legality, dice, resources, and saves.</p></details>`;
  return `<div class="turn-panel" aria-label="Turn-based combat controls"><div class="turn-panel-head"><strong>${E(row.name || current || 'Current turn')}</strong><span>Initiative ${E(c.order?.indexOf(current) + 1 || '—')}</span></div><div class="turn-economy"><span>Action <b>${E(economy.action ?? 0)}</b></span><span>Bonus <b>${E(economy.bonus ?? 0)}</b></span><span>Reaction <b>${E(economy.reaction ?? 0)}</b></span><span>Move <b>${E(economy.movement ?? 0)} ft</b></span></div><div class="turn-stats">${Object.keys(scores).map(key => `<span title="${E(key)} score"><b>${E(key)}</b> ${E(scores[key])} <small>${Number(modifiers[key] || 0) >= 0 ? '+' : ''}${E(modifiers[key] || 0)}</small></span>`).join('')}</div>${turnActions}${reactions}<p class="notice">Rules, targets, movement, dice, resources, and saves remain host-resolved.</p>${developerNote}</div>`;
}
function battle() {
  const v = state.view || {};
  const active = encounterActive(v);
  const arena = v.flight_arena;
  const arcadeActive = Boolean(v.arcade && !v.arcade.complete);
  const flightControls = arena && !arcadeActive ? `<div class="flight-controls" aria-label="Flight controls"><p class="label">Flight controls</p>
    <button type="button" class="action flight-control" data-flight-type="wings" title="Manifest Wren's wings and take flight">Take Flight</button>
    <button type="button" class="action flight-control" data-flight-type="land" title="Dismiss Wren's wings and land">Land</button>
    ${[['flight_move','←','-5','0','Move left'],['ascend','↑','0','5','Ascend'],['descend','↓','0','-5','Descend'],['flight_move','→','5','0','Move right']].map(([type,label,dx,dy,accessibleLabel]) => `<button type="button" class="action flight-control" data-flight-type="${type}" data-flight-dx="${dx}" data-flight-dy="${dy}" aria-label="${E(accessibleLabel)}" title="${E(accessibleLabel)}"><span aria-hidden="true">${label}</span></button>`).join('')}</div>` : '';
  return `${active ? battleStage() : sceneWorld('battle')}${card('Encounter', `<div class="battle-banner"><div><p class="eyebrow">${arcadeActive ? 'Arcade readout' : 'Tactical readout'}</p><h2>${active ? (arcadeActive ? 'Market crossing' : arena ? 'Aerial encounter' : 'Active encounter') : 'Quiet floor'}</h2><p>Round ${E(v.round || v.combat?.round || '—')} · Turn ${E(v.turn || '—')}</p></div><span class="battle-sigil" aria-hidden="true">⚔</span></div>
    <div class="roster-grid">${[...party(), ...(v.opposition || [])].map(actorCard).join('') || '<p>No public combat roster.</p>'}</div>${active ? `<div class="actions">${arcadeActive ? '' : autoToggle()}</div>${arcadeActive ? arcadeControls() : `${turnPanel()}${flightControls}${signatureActions()}`}` : '<p class="notice">The engine will surface combat controls when an encounter begins.</p>'}`)}`;
}
function actorCard(item) {
  const statuses = Array.isArray(item.status) ? item.status.join(' · ') : (item.status || 'No visible statuses');
  const appearance = presentationAppearance(item);
  return `<button class="actor-card ${actor().id === item.id ? 'selected' : ''}" data-actor="${E(item.id)}" data-examine-actor="${E(item.id)}" title="Click to select ${E(item.name)}. Double-click to examine."><span class="mini-character ${E(visualRole(item))} identity-${E(visualIdentity(item))} appearance-${E(appearance)} expression-${E(visualExpression(item, 'idle'))}"><i></i><b>${E((item.name || '?')[0])}</b></span><span><strong>${E(item.name)}</strong><small>${E(value(item, 'hp') ?? '?')} / ${E(value(item, 'max_hp', 'ac') ?? '?')} HP · AC ${E(value(item, 'armor_class', 'ac') ?? '?')}</small><small>${E(statuses)}</small></span></button>`;
}
function imprintPanel() {
  const imprints = state.view?.imprints || {};
  const rows = Object.entries(imprints);
  if (!rows.length) return '';
  return `<div class="imprint-grid"><p class="label">Reliquary Imprints</p>${rows.map(([slot, row]) => `<div class="imprint-slot"><small>${E(slot.replaceAll('_', ' '))}</small><strong>${E(row?.name || row?.display_name || 'Empty')}</strong>${row?.tooltip ? `<small class="notice">${E(row.tooltip)}</small>` : ''}</div>`).join('')}<p class="notice">Imprints are temporary overlays; they dissolve or become inert outside the Reliquary.</p></div>`;
}
function equipment() {
  const items = [...(actor().equipment || []), ...(state.view?.inventory || [])];
  return `${atmosphere('equipment', `${actor().name || 'Party'} equipment`, 'A clear armory view of every host-reported item, affix, and visible property.')}${card('Reliquary gear', `<div class="equipment-heading"><div><p class="eyebrow">Loadout and carried finds</p><h2>${E(actor().name || 'Party')} equipment</h2></div><span class="gear-sigil" aria-hidden="true">✦</span></div><div class="compact-items">${items.map((item, index) => globalThis.HSRUI.card(item, 'item', index, 'assets/')).join('') || '<p>No public items listed.</p>'}</div>
    <p class="notice">Properties, affixes, effects, and identification state are reported by the host only.</p>${imprintPanel()}`)}`;
}
function residents() {
  const residents = Object.values(state.view?.room?.npcs || {});
  const transcript = [...(state.view?.conversation || []), ...(state.view?.recent_receipts || []), state.receipt].filter(Boolean).slice(-8).map(row => row.reply || row.message || row.narration || row.summary || row.text || row.outcome).filter(Boolean);
  const chat = transcript.length ? transcript.map((line, index) => `<div class="chat-line ${index === transcript.length - 1 ? 'latest' : ''}"><span class="chat-mark">${index % 2 ? '◇' : '◈'}</span><p>${E(line)}</p></div>`).join('') : '<p class="notice">No public conversation has been recorded yet. Choose a resident or begin with an observation.</p>';
  const chatChoices = [button('We look around', 'intent:we look around', 'secondary'), button('Ask what is happening', 'intent:ask what is happening', 'secondary'), button('Keep listening', 'intent:keep listening', 'secondary')].join('');
  return `${atmosphere('residents', 'Visible residents', 'Pretty social portraits show who is speaking; ordinary scene figures keep the lived-in town readable.')}${card('Residents / social', `<div class="npc-gallery">${residents.map(npc => { const id = npc.id || npc.npc_id || npc.role; const role = String(npc.role || '').toLowerCase(); const portrait = /wellkeeper/.test(role) ? 'wellkeeper' : /merchant|market/.test(role) ? 'merchant' : /smith/.test(role) ? 'smith' : /bar|tavern/.test(role) ? 'server' : /watch|guard/.test(role) ? 'watch' : 'herbalist'; return `<article class="npc-card visual-npc"><div class="npc-portrait portrait-${portrait}" role="img" aria-label="${E(npc.name || npc.role || 'town resident')} portrait"></div><div><h3>${E(npc.name || npc.role)}</h3><p>${E(npc.role || npc.disposition || 'Disposition not reported.')}</p><div class="actions compact-actions">${button('Talk', `talk:${id}`)}${CONVERSATION_MODES.map(m => `<button type="button" class="action secondary" data-conversation="${E(id)}" data-conversation-mode="${E(m.mode)}">${E(m.label)}</button>`).join('')}</div></div></article>`; }).join('') || '<p>No residents are visible in this public readout.</p>'}</div>`)}` + card('Town conversation', `<div class="chat-window" aria-live="polite">${chat}</div><div class="chat-choices">${chatChoices}</div>`);
}
function affixCatalog() {
  const catalog = state.affixes || {};
  const rows = [...(catalog.active || []), ...(catalog.staged || [])];
  return card('Affix catalog', `<h2>Endless Engagement pool</h2>
    <p>${E(catalog.counts?.active || 0)} active · ${E(catalog.counts?.staged || 0)} staged. Staged rows are inspectable but not gameplay-active.</p>
    <div class="compact-items">${rows.map(row => `<details><summary><strong>${E(row.name)}</strong> <small>${E(row.affix_type)} · ${row.options?.staged ? 'staged' : 'active'}</small></summary>
      <p>${E(row.tooltip)}</p><p class="notice">${E((row.tags || []).join(' · ') || 'No tags')}</p>
      ${(row.phase_effects || []).map(effect => `<div class="stat"><span>${E(effect.phase)} / ${E(effect.direction)}</span><strong>${E(effect.name)}</strong><small>${E(effect.condition)}${effect.status ? ` · ${E(effect.status)} ${E(effect.status_duration)} turns` : ''}</small></div>`).join('')}
    </details>`).join('')}</div>`);
}
function library() {
  const catalog = state.catalog || {};
  const items = catalog.items || [];
  const rooms = catalog.rooms || [];
  const affixes = [...(state.affixes?.active || []), ...(state.affixes?.staged || [])];
  return `${atmosphere('library', 'Reliquary library', 'Weapons, armor, rooms, and runes remain readable while their rules come directly from HSRHost.')}${card('Reliquary library', `<h2>Engine content</h2>
    <p>Direct read-only access to the content loaded by the Python engine. Rules stay authoritative in the host.</p>
    <div class="library-grid"><section><h3>Items and armor (${items.length})</h3>${items.map(item => `<details><summary><strong>${E(item.display_name || item.name)}</strong><small>${E(item.slot || 'equipment')} · ${E(item.tier || 'unreported')}</small></summary><p>${E(item.flavor || item.description || 'No description reported.')}</p><p class="notice">${E((item.tags || []).join(' · ') || 'No tags')}</p>${item.base_damage ? `<p>Damage: ${E(item.base_damage)} · Attack: ${E(item.attack_bonus ?? 0)}</p>` : ''}${item.base_ac ? `<p>Base AC: ${E(item.base_ac)}</p>` : ''}</details>`).join('') || '<p>No item catalog reported.</p>'}</section>
    <section><h3>Rooms and spaces (${rooms.length})</h3>${rooms.map(room => `<details><summary><strong>${E(room.name || room.id)}</strong><small>${E(room.type || room.apparent_function || 'room')}</small></summary><p>${E(room.terrain || room.description || 'No terrain reported.')}</p><p class="notice">${E([room.resident, room.law, room.exit].filter(Boolean).join(' · '))}</p></details>`).join('') || '<p>No room catalog reported.</p>'}</section>
    <section><h3>Affixes and runes (${affixes.length})</h3>${affixes.map(row => `<details><summary><strong>${E(row.name)}</strong><small>${E(row.affix_type || 'rune')}</small></summary><p>${E(row.tooltip || 'No description reported.')}</p><p class="notice">${E((row.tags || []).join(' · ') || 'No tags')}</p></details>`).join('') || '<p>No affix catalog reported.</p>'}</section></div>`)}`;
}
function options() {
  const p = state.preferences;
  const vocabulary = state.vocabulary || {};
  const textOptions = Object.entries(vocabulary).filter(([key, value]) => Array.isArray(value)).map(([key, values]) => `<details><summary><strong>${E(key)}</strong></summary><p>${E(values.join(' · '))}</p></details>`).join('');
  return `${state.phase === 'options' ? breadcrumb('Main Menu', 'Options') : ''}${atmosphere('options', 'Display options', 'Tune the illustrated interface without changing a roll, room, item, or saved run.')}${card('Options', `<h2>HSR Interface</h2><p>Preferences are local to this browser and survive game-mode changes, navigation, and reloads.</p>
    <div class="option-list">
      <label class="option-row"><span><strong>Icon actions</strong><small>Use compact symbols for bottom action controls while keeping accessible labels.</small></span><input type="checkbox" data-pref="iconActions" ${p.iconActions ? 'checked' : ''}></label>
      <fieldset class="layout-presets"><legend>Workspace preset</legend><p class="notice">Each preset changes the actual desktop composition. You can still tune every part below.</p><div class="preset-grid">
        <button type="button" class="preset-card ${p.layout === 'sanctum' ? 'selected' : ''}" data-action="layout-preset:sanctum"><i class="preset-map sanctum" aria-hidden="true"><b></b><b></b><b></b></i><strong>Sanctum</strong><small>Party, scene, and navigation together.</small></button>
        <button type="button" class="preset-card ${p.layout === 'focus' ? 'selected' : ''}" data-action="layout-preset:focus"><i class="preset-map focus" aria-hidden="true"><b></b><b></b><b></b></i><strong>Focus</strong><small>A wide, distraction-free scene.</small></button>
        <button type="button" class="preset-card ${p.layout === 'idle' ? 'selected' : ''}" data-action="layout-preset:idle"><i class="preset-map idle" aria-hidden="true"><b></b><b></b><b></b></i><strong>Idle</strong><small>Quiet, text-first, low-animation view.</small></button>
      </div></fieldset>
      <label class="option-row"><span><strong>Menu density</strong><small>Adjust the room, battle, and equipment navigation rail.</small></span><select data-pref="menuDensity" aria-label="Menu density"><option value="compact" ${p.menuDensity === 'compact' ? 'selected' : ''}>Compact</option><option value="comfortable" ${p.menuDensity === 'comfortable' ? 'selected' : ''}>Comfortable</option><option value="spacious" ${p.menuDensity === 'spacious' ? 'selected' : ''}>Spacious</option></select></label>
      <label class="option-row"><span><strong>Scene size</strong><small>Choose how much desktop space the illustrated room or battle occupies.</small></span><select data-pref="sceneScale"><option value="compact" ${p.sceneScale === 'compact' ? 'selected' : ''}>Compact</option><option value="standard" ${p.sceneScale === 'standard' ? 'selected' : ''}>Standard</option><option value="cinematic" ${p.sceneScale === 'cinematic' ? 'selected' : ''}>Cinematic</option></select></label>
      <label class="option-row"><span><strong>Action dock</strong><small>Keep commands below the scene or float them on either desktop edge.</small></span><select data-pref="dockPosition"><option value="bottom" ${p.dockPosition === 'bottom' ? 'selected' : ''}>Below scene</option><option value="left" ${p.dockPosition === 'left' ? 'selected' : ''}>Float left</option><option value="right" ${p.dockPosition === 'right' ? 'selected' : ''}>Float right</option></select></label>
      <div class="option-row"><span><strong>Visible desktop panels</strong><small>Hide either rail without losing its information; restore it here at any time.</small></span><span class="option-checks"><label><input type="checkbox" data-pref="showParty" ${p.showParty ? 'checked' : ''}> Party</label><label><input type="checkbox" data-pref="showNavigation" ${p.showNavigation ? 'checked' : ''}> Navigation</label></span></div>
      <fieldset class="accent-picker"><legend>Accent color</legend><p class="notice">Shift the interface character while preserving contrast.</p><div class="accent-options"><label class="accent-swatch"><input type="radio" name="accent" value="gold" data-pref="accent" ${p.accent === 'gold' ? 'checked' : ''}><span class="swatch" style="background:linear-gradient(135deg, #c9a86a, #b5985c)"></span><strong>Gold</strong><small>Reliquary</small></label><label class="accent-swatch"><input type="radio" name="accent" value="moon" data-pref="accent" ${p.accent === 'moon' ? 'checked' : ''}><span class="swatch" style="background:linear-gradient(135deg, #c8d8ec, #9eb5cf)"></span><strong>Moon</strong><small>Silver</small></label><label class="accent-swatch"><input type="radio" name="accent" value="ember" data-pref="accent" ${p.accent === 'ember' ? 'checked' : ''}><span class="swatch" style="background:linear-gradient(135deg, #e3a19a, #bf7b75)"></span><strong>Ember</strong><small>Rose</small></label></div></fieldset>
      <label class="option-row"><span><strong>Text size — ${Math.round(Number(p.textScale) * 100)}%</strong><small>Scale the mostly-text interface without changing the engine.</small></span><input type="range" min=".9" max="1.25" step=".05" value="${E(p.textScale)}" data-pref="textScale" aria-label="Text size"></label>
      <fieldset class="display-elements"><legend>Status display</legend><p class="notice">Show additional UI elements in the top corner.</p><span class="option-checks"><label><input type="checkbox" data-pref="showClock" ${p.showClock ? 'checked' : ''}> Show clock</label><label><input type="checkbox" data-pref="showTickIndicator" ${p.showTickIndicator ? 'checked' : ''}> Show tick pulse</label></span></fieldset>
      <label class="option-row"><span><strong>Reduced motion</strong><small>Disable transition effects for idle or low-power use.</small></span><input type="checkbox" data-pref="motion" ${p.motion === 'reduced' ? 'checked' : ''}></label>
      <label class="option-row"><span><strong>Soft effects</strong><small>Reduce glow and shadow intensity.</small></span><input type="checkbox" data-pref="effects" ${p.effects === 'soft' ? 'checked' : ''}></label>
    </div>
    <div class="actions">${button('Reset display preferences', 'reset-preferences', 'secondary')}${button('Refresh engine state', 'refresh-readout', 'secondary')}${state.phase === 'options' ? button('Back', 'back', 'secondary') : ''}</div>
    <details class="interface-reference"><summary><strong>Conversation and text commands</strong></summary><p>Use these host-routed phrases anywhere the intent box appears. Talk buttons on visible residents prefill a conversation request; the NPC response and consequences come back only through the public host receipt.</p>${textOptions || '<p>Text vocabulary is unavailable until the local gateway refreshes.</p>'}</details>`)}`;
}
function bounded(titleText, message) { return card(titleText, `<h2>${E(titleText)}</h2><p>${E(message)}</p>`); }
function upgradeRow([key, spec]) {
  const level = state.progression?.upgrades?.[key] ?? 0;
  const capped = level >= spec.cap;
  const cost = spec.base_cost * (level + 1);
  return `<div class="upgrade-row"><div><strong>${E(key.replaceAll('_', ' '))}</strong><small>${E(spec.effect)} · tier ${E(level)}/${E(spec.cap)}</small></div>${capped ? '<span class="notice">Capped</span>' : `<button type="button" class="action secondary" data-upgrade="${E(key)}">Buy · ${E(cost)}</button>`}</div>`;
}
function progressionPanel() {
  const p = state.progression;
  if (!p) return `<div class="actions">${button('Load account progression', 'load-progression', 'secondary')}</div>`;
  const t = p.tracking || {};
  return `<div class="progression-panel"><div class="stats"><div><strong>${E(p.rank ?? 1)}</strong><small>Rank</small></div><div><strong>${E(p.platinum ?? 0)}</strong><small>Platinum</small></div><div><strong>${E(p.loop_tier ?? 1)}</strong><small>Loop tier</small></div></div>
    <p class="label">Permanent upgrades</p>${Object.entries(UPGRADE_TRACKS).map(upgradeRow).join('')}
    <p class="label">Account stats</p><div class="stat"><span>Gold earned / spent / lost</span><strong>${E(t.gold_earned ?? 0)} / ${E(t.gold_spent ?? 0)} / ${E(t.gold_lost ?? 0)}</strong></div><div class="stat"><span>Rooms entered / cleared</span><strong>${E(t.rooms_entered ?? 0)} / ${E(t.rooms_cleared ?? 0)}</strong></div><div class="stat"><span>Combat encounters / rounds</span><strong>${E(t.combat_encounters ?? 0)} / ${E(t.combat_rounds ?? 0)}</strong></div><div class="stat"><span>Gameplay minutes</span><strong>${E(t.gameplay_minutes ?? 0)}</strong></div>
    <div class="actions">${button('Refresh progression', 'load-progression', 'secondary')}</div></div>`;
}
function terminalReceiptPanel() {
  const t = state.terminal;
  if (!t) return `<div class="actions">${button('Fetch run report', 'load-terminal-receipt', 'secondary')}</div>`;
  const conducts = t.conducts || {};
  const lost = t.tracking?.lost_unbanked_items || t.lost_unbanked_items || [];
  return `<div class="run-report"><p class="label">Conducts</p>${Object.keys(conducts).length ? `<div class="stats">${Object.entries(conducts).map(([name, achieved]) => `<div class="conduct-badge ${achieved ? 'earned' : ''}"><strong>${achieved ? '✓' : '—'}</strong><small>${E(name.replaceAll('_', ' '))}</small></div>`).join('')}</div>` : '<p class="notice">No conduct evaluation reported yet.</p>'}
    ${lost.length ? `<p class="notice">Lost to the descent, unbanked: ${E(lost.map(row => row.name || row.id || row).join(' · '))}</p>` : ''}
    <div class="actions">${button('Refresh run report', 'load-terminal-receipt', 'secondary')}</div></div>`;
}
function journal() {
  const events = state.view?.recent_receipts || [];
  return `${atmosphere('journal', 'Journey journal', 'Only host-reported discoveries and public receipts enter this record.')}${card('Recent events', events.length ? events.map(e => `<div class="log-item">${E(e.message || e.outcome || e.type || JSON.stringify(e))}</div>`).join('') : '<p class="notice">No resolved events yet.</p>')}<div class="actions">${button('View Statistics', 'menu:statistics', 'secondary')}</div>`;
}
function statisticsScreen() {
  return `${breadcrumb('Main Menu', 'Statistics')}${atmosphere('journal', 'Statistics', 'Account progression and, when a run is loaded, its Conducts report.')}${card('Reliquary progression', progressionPanel())}${card('Run report', state.runId ? terminalReceiptPanel() : '<p class="notice">Load or continue a run to see its Conducts report.</p>')}<div class="actions">${button('Back', 'back', 'secondary')}</div>`;
}
function scenarioEditor() {
  const rows = state.scenarios;
  const chosen = state.preferences.scenario || MODE_SCENARIOS.SANDBOX;
  const seed = state.preferences.scenarioSeed || '';
  const body = rows === null
    ? `<p class="notice">Loading the host's scenario catalog…</p>`
    : !rows.length
      ? `<p class="notice">The host reported no Simulation scenarios.</p><div class="actions">${button('Retry', 'load-scenarios', 'secondary')}</div>`
      : `<div class="gateway-choice-grid">${rows.map(row => `<article class="gateway-choice${row.scenario === chosen ? ' selected' : ''}"><p class="eyebrow">${row.scenario === chosen ? 'Selected' : 'Available'}</p><h3>${E(row.title)}</h3><p>${E(row.blurb)}</p><div class="actions">${row.scenario === chosen ? '<span class="gateway-status">In use for new Simulation runs</span>' : button(`Use ${row.title}`, `scenario:${row.scenario}`, 'primary')}</div></article>`).join('')}</div>
      <label class="option-row"><span><strong>Seed override</strong><small>Blank uses the lead's own creation seed. A fixed seed makes a Simulation run repeatable.</small></span><input type="text" data-scenario-seed value="${E(seed)}" placeholder="(lead's creation seed)" aria-label="Simulation seed override"></label>
      <div class="actions">${button('Reset to defaults', 'reset-scenario', 'secondary')}</div>`;
  return `${breadcrumb('Main Menu', 'Simulation Mode', 'Edit Scenario')}${atmosphere('gateway', 'Edit Scenario', 'Pick which authored surface a new Simulation run opens on. Scenario content stays a read-only engine input; only the choice is yours.')}${card('Scenario', `${body}<p class="notice">This applies to the next Simulation run you start. A run already in progress keeps the scenario it was created with.</p><div class="actions">${button('Back', 'back', 'secondary')}</div>`)}`;
}
function cheatsPanel() {
  const debug = state.debugReadout;
  return `${breadcrumb('Main Menu', 'Simulation Mode', 'Cheats')}${atmosphere('gateway', 'Cheats', 'Private sandbox debug state — rehearsal only, never canon.')}${card('Cheats', `<p class="notice">Reveals state normally hidden from the public view: exact HP pools, hidden checks, undiscovered content, and engine internals for the current Simulation run.</p>${state.runId ? `<div class="actions">${button('Reveal debug state', 'load-debug-state', 'secondary')}</div>${debug ? `<pre>${E(JSON.stringify(debug, null, 2))}</pre>` : ''}` : '<p class="notice">Start or resume a Simulation run first, then return here.</p>'}<div class="actions">${button('Back', 'back', 'secondary')}</div>`)}`;
}
function gameplay() {
  const content = {journey, room, battle, equipment, roster: () => `${atmosphere('roster', 'The party', 'Selectable adventurers with readable silhouettes, health, armor, status, and equipment roles.')}${card('Roster', `<div class="roster-showcase">${characterFigure(actor(), 'featured')}${party().map(actorCard).join('') || 'No public party reported.'}</div>`)}`,
    residents, journal,
    map: () => `${atmosphere('map', 'The descent', 'Known places glow at the edge of a larger unknown Reliquary.')}${bounded('Floors / map', state.runId ? 'Unknown areas remain unknown until the host reports them.' : 'Start or resume a run to begin charting the descent.')}`,
    library, options};
  return content[state.selected]?.() || room();
}
function shell() {
  const tabs = screens.map(tab => `<button type="button" role="tab" class="tab ${state.selected === tab ? 'active' : 'secondary'}" data-action="tab:${E(tab)}" aria-selected="${state.selected === tab}" aria-controls="screen-${E(tab)}">${E(gameplayLabels[tab])}</button>`).join('');
  return `<header class="masthead"><div><p class="kicker">Hollow Star Reliquary</p><h1>${E(state.view?.room?.name || 'Reliquary')}</h1>
    <p class="metadata">${modeBadge(state.view?.mode)}${state.view?.mode ? ' · ' : ''}${E(state.transport)} · ${E(state.runId || 'No run')} · ${state.refreshed ? `refreshed ${state.refreshed.toLocaleTimeString()}` : 'not refreshed'}</p></div>
    <div class="actions">${button(state.arrangeMode ? 'Lock layout' : 'Arrange', 'toggle-arrange', 'secondary')}${state.arrangeMode ? button('Reset layout', 'reset-layout', 'secondary') : ''}${button('Refresh', 'refresh-readout')}${button('Save / Exit', 'save')}</div></header>
    ${partyHud()}
    <main class="master-grid ${state.arrangeMode ? 'arrange-mode' : ''}"><aside class="left-rail workspace-panel" data-workspace-panel="party" style="${panelStyle('party')}"><div class="panel-drag-handle" data-panel-handle="party"><span>Party</span><small>Drag · resize</small></div>${party().map(actorCard).join('') || '<p>No public party.</p>'}</aside>
    <section id="screen-${E(state.selected)}" class="center-stage" role="tabpanel" aria-label="${E(gameplayLabels[state.selected] || state.selected)}">${gameplay()}${state.receipt ? card('Latest public receipt', `<details><summary>Show receipt details</summary><pre>${E(JSON.stringify(state.receipt, null, 2))}</pre></details>`) : ''}</section>
     <aside class="right-rail workspace-panel" data-workspace-panel="navigation" style="${panelStyle('navigation')}"><div class="panel-drag-handle" data-panel-handle="navigation"><span>Workspace</span><small>Drag · resize</small></div>${card('Connection', `<div class="stat"><span>State</span><strong>${state.busy ? 'pending' : state.error ? 'error' : 'connected'}</strong></div><div class="stat"><span>Run</span><strong>${E(state.runId || '—')}</strong></div><div class="stat"><span>Tick / time</span><strong>${E(state.view?.event_clock?.tick ?? '—')} / ${E(state.view?.world_time ?? state.view?.event_clock?.seconds ?? '—')}</strong></div><p>${E(state.note || '')}</p>`)}${card('Screens', `<nav class="tabs" role="tablist" aria-label="Screens">${tabs}</nav>`)}</aside></main>`;
}

function panelStyle(id) {
  const row = state.workspaceLayout[id] || {};
  const x = Number.isFinite(row.x) ? row.x : 0;
  const y = Number.isFinite(row.y) ? row.y : 0;
  const width = Number.isFinite(row.width) && row.width > 0 ? `${row.width}px` : '';
  const height = Number.isFinite(row.height) && row.height > 0 ? `${row.height}px` : '';
  return `--panel-x:${x}px;--panel-y:${y}px;${width ? `width:${width};` : ''}${height ? `height:${height};` : ''}`;
}

function bindWorkspacePanels() {
  if (!state.arrangeMode || matchMedia('(max-width: 720px)').matches) return;
  document.querySelectorAll('[data-workspace-panel]').forEach(panel => {
    const id = panel.dataset.workspacePanel;
    const handle = panel.querySelector(`[data-panel-handle="${id}"]`);
    if (!handle) return;
    handle.onpointerdown = event => {
      if (event.button !== undefined && event.button !== 0) return;
      event.preventDefault();
      handle.setPointerCapture(event.pointerId);
      const start = {x:event.clientX, y:event.clientY};
      const saved = state.workspaceLayout[id] || {};
      const origin = {x:Number(saved.x) || 0, y:Number(saved.y) || 0};
      handle.onpointermove = move => {
        if (!handle.hasPointerCapture(move.pointerId)) return;
        const maxX = Math.max(0, innerWidth - 120);
        const maxY = Math.max(0, innerHeight - 100);
        const x = Math.max(-maxX, Math.min(maxX, origin.x + move.clientX - start.x));
        const y = Math.max(-maxY, Math.min(maxY, origin.y + move.clientY - start.y));
        panel.style.setProperty('--panel-x', `${x}px`);
        panel.style.setProperty('--panel-y', `${y}px`);
        state.workspaceLayout[id] = {...saved, x, y};
      };
      handle.onpointerup = move => {
        if (handle.hasPointerCapture(move.pointerId)) handle.releasePointerCapture(move.pointerId);
        handle.onpointermove = null; handle.onpointerup = null; saveWorkspaceLayout();
      };
    };
    if ('ResizeObserver' in window) {
      let first = true;
      const observer = new ResizeObserver(entries => {
        if (first) { first = false; return; }
        const box = entries[0]?.contentRect;
        // A panel reports 0x0 the moment its node is detached (e.g. Lock layout
        // re-rendering the shell) -- that is never a real resize and must not
        // be persisted, or the next render reapplies a zero size permanently.
        if (!box || box.width < 10 || box.height < 10) return;
        state.workspaceLayout[id] = {...(state.workspaceLayout[id] || {}), width:Math.round(box.width), height:Math.round(box.height)};
        saveWorkspaceLayout();
      });
      observer.observe(panel);
    }
  });
}
function updateArcadeStatus() {
  const arena = state.view?.arcade;
  const node = document.querySelector('[data-arcade-status]');
  if (!node || !arena) return;
  const wave = arena.complete ? 'Gate open' : `Wave ${Math.min((arena.wave_index || 0) + 1, arena.waves || 1)} / ${arena.waves || 1}`;
  const self = arena.entities?.[actor().id];
  const combo = self?.combo_tier ? ` · Combo x${self.combo_tier + 1}` : '';
  const guard = self?.blocking ? ' · Blocking' : self?.invulnerable ? ' · Dodging' : '';
  node.textContent = `${wave} · Frame ${arena.frame ?? 0}${combo}${guard}`;
}
async function sendArcadeControl(action) {
  const ui = state.arcadeUi;
  if (!ui || ui.controlBusy || !state.runId) return;
  ui.controlBusy = true;
  try {
    result(await state.client.designAction(state.runId, action));
    const readout = result(await state.client.readout(state.runId));
    ui.canvas.setActors([...party(), ...(state.view?.opposition || [])]);
    ui.canvas.setState(state.view?.arcade);
    updateArcadeStatus();
    state.note = `${action.type.replaceAll('_', ' ')} resolved by the host.`;
  } catch (error) {
    ui.loop.stop();
    fail(error.message);
    render();
  } finally {
    if (state.arcadeUi === ui) ui.controlBusy = false;
  }
}
async function sendArcadeFlight(on, actorKey) {
  const ui = state.arcadeUi;
  if (!ui || ui.controlBusy || !state.runId) return;
  ui.controlBusy = true;
  try {
    // Flight has a real tactical prerequisite: the host must manifest Wren's
    // wings before the arcade movement mode can change.
    if (on) result(await state.client.designAction(state.runId, {
      type: 'wings',
      actor: actorKey,
    }));
    result(await state.client.designAction(state.runId, {
      type: 'arcade_toggle_flight',
      actor: actorKey,
      on,
    }));
    result(await state.client.readout(state.runId));
    ui.canvas.setActors([...party(), ...(state.view?.opposition || [])]);
    ui.canvas.setState(state.view?.arcade);
    updateArcadeStatus();
  } catch (error) {
    ui.loop.stop();
    fail(error.message);
    render();
  } finally {
    if (state.arcadeUi === ui) ui.controlBusy = false;
  }
}
function mountArcade() {
  const root = document.querySelector('[data-arcade-root]');
  const active = Boolean(state.view?.arcade && !state.view.arcade.complete);
  if (!root || !active) {
    if (state.arcadeUi) {
      state.arcadeUi.loop.stop(); state.arcadeUi.input.destroy(); state.arcadeUi.canvas.destroy(); state.arcadeUi = null;
    }
    return;
  }
  if (state.arcadeUi && (state.arcadeUi.root !== root || state.arcadeUi.runId !== state.runId)) {
    state.arcadeUi.loop.stop(); state.arcadeUi.input.destroy(); state.arcadeUi.canvas.destroy(); state.arcadeUi = null;
  }
  if (!state.arcadeUi) {
    const mount = root.querySelector('[data-arcade-canvas]');
    const inputRoot = document.querySelector('[data-arcade-controls]') || root;
    const ui = {root, runId: state.runId, pending: [], blocking: false, controlBusy: false, canvas: createArcadeCanvas(mount)};
    ui.input = bindArcadeInput(inputRoot, {
      actor: () => actor().id || 'p0',
      onInput: input => ui.pending.push(input),
      onAttack: input => ui.pending.push(input),
      onDodge: input => ui.pending.push(input),
      onRanged: input => ui.pending.push(input),
      onBlock: held => { ui.blocking = held; },
      onMode: (mode, key) => sendArcadeControl({type: 'arcade_set_movement_mode', actor: key, mode}),
      onFlight: (on, key) => sendArcadeFlight(on, key),
    });
    ui.loop = createArcadeLoop({
      client: state.client,
      runId: state.runId,
      getInputs: () => {
        if (ui.controlBusy) return null;
        const queued = ui.pending.splice(0);
        // Block is a held state, not a queued discrete action: re-assert it
        // every poll while the key/button is down so the host sees it as
        // continuously blocked rather than a single instantaneous flash.
        if (ui.blocking) queued.push({actor: actor().id || 'p0', block: true});
        return queued;
      },
      onFrame: (view, reply) => {
        if (!view) return;
        state.view = view;
        state.receipt = reply.public_receipt;
        state.refreshed = new Date();
        ui.canvas.setActors([...party(), ...(view.opposition || [])]);
        ui.canvas.setState(view.arcade);
        updateArcadeStatus();
      },
      onComplete: () => {
        if (state.arcadeUi !== ui) return;
        ui.loop.stop(); ui.input.destroy(); ui.canvas.destroy(); state.arcadeUi = null;
        selectGameplayScreen('room'); state.note = 'Arcade gate cleared; the room reward is now public.'; render();
      },
      onError: error => {
        ui.loop.stop(); state.note = `Arcade frame paused: ${error.message}`; updateArcadeStatus();
      },
    });
    state.arcadeUi = ui;
    ui.canvas.setActors([...party(), ...(state.view?.opposition || [])]);
    ui.canvas.setState(state.view.arcade);
    ui.loop.start();
  } else {
    state.arcadeUi.canvas.setActors([...party(), ...(state.view?.opposition || [])]);
    state.arcadeUi.canvas.setState(state.view.arcade);
    updateArcadeStatus();
  }
}
function actionBar() {
  const stepActor = encounterStepActor();
  const actions = (state.view?.available_actions || []).filter(row => {
    const id = row.id || row.action;
    if (['attack', 'maneuver'].includes(id)) return actionTargets(id).length > 0;
    if (encounterActive() && ['move', 'cast', 'end_turn'].includes(id)) return stepActor.startsWith('p');
    return true;
  });
  if (!state.runId || !actions.length) return '';
  const icons = {inspect: '⌕', investigate: '◌', enter: '↳', descend: '⇣', enter_gauntlet: '⇣', rest: '☾', exit: '←', attack: '⚔', move: '⇢', cast: '✧', end_turn: '⏳', conversation: '☵', identify: '◇', escape: '↗'};
  return `<nav class="engine-action-bar" data-panel="actions" aria-label="Engine actions"><span class="action-bar-label">Engine actions</span>${actions.map(row => {
    const id = row.id || row.action;
    return `<button class="action engine-action" data-engine-action="${E(id)}" title="${E(FLAVOR.actions[id] || row.label || id)}"><span class="action-glyph" aria-hidden="true">${E(icons[id] || '·')}</span><span class="action-text">${E(row.label || id)}</span></button>`;
  }).join('')}</nav>`;
}
const FOCUS_ATTRS = ['data-choice', 'data-look', 'data-skill-pick', 'data-action', 'data-create-field', 'data-assign', 'data-skill', 'data-spell', 'data-floating', 'data-advancement'];
function focusSignature(node) {
  if (!node || node === document.body) return '';
  const attr = FOCUS_ATTRS.find(name => node.hasAttribute?.(name));
  return attr ? `[${attr}="${CSS.escape(node.getAttribute(attr))}"]` : '';
}
function restoreFocus(key) { if (key) document.querySelector(key)?.focus({preventScroll: true}); }
function render() {
  const focusKey = focusSignature(document.activeElement);
  applyPreferences();
  let body = state.phase === 'title' ? title() : state.phase === 'transport' ? transportChoice() :
    state.phase === 'menu-story' ? storyMenu() : state.phase === 'menu-simulation' ? simulationMenu() :
    state.phase === 'party-select' ? partySelect() : state.phase === 'champion-select' ? champion() : state.phase === 'create' ? creator() :
    state.phase === 'preview' ? preview() : state.phase === 'runs' ? runs() :
    state.phase === 'statistics' ? statisticsScreen() : state.phase === 'edit-scenario' ? scenarioEditor() :
    state.phase === 'cheats' ? cheatsPanel() : state.phase === 'options' ? options() : shell();
  const staleSandboxNotice = state.staleSandbox
    ? `<div class="notice error stale-sandbox-notice"><p>${E(state.error)}</p><div class="actions">${button(`End ${state.staleSandbox.run_id} and start fresh`, 'resolve-stale-sandbox', 'primary')}</div></div>`
    : state.error ? `<p class="notice error" role="alert">${E(state.error)}</p>` : '';
  const dockContent = `${actionBar()}${targetPicker()}${consoleBar()}`;
  const messagePanelHtml = state.messageHistoryOpen ? messagePanel() : '';
  document.querySelector('#app').innerHTML = `${statusClock()}${topNavigation()}${body}${staleSandboxNotice}<p class="notice" role="status">${E(state.note)}</p>${messagePanelHtml}${dockContent ? `<div class="hsr-dock tray-${E(state.trayState)}">${trayHandle()}<div class="tray-content">${dockContent}</div></div>` : ''}${mobileNavigation()}`;
  document.querySelectorAll('button,input,select').forEach(node => { node.disabled = state.busy || node.dataset.locked === 'true'; });
  bind(); bindCreator(); restoreFocus(focusKey);
  // Update clock tick
  state.clockTick++;
  if (state.clockTick % 2 === 0) {
    const clockEl = document.querySelector('.status-clock');
    if (clockEl) {
      const now = new Date();
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const seconds = String(now.getSeconds()).padStart(2, '0');
      const timeDisplay = clockEl.querySelector('.time-display');
      if (timeDisplay) timeDisplay.innerHTML = `<span class="tick-pulse" data-tick="${state.clockTick % 2}">●</span><strong>${hours}:${minutes}:${seconds}</strong>`;
    }
  }
}
async function loadReadout(runId) { result(await state.client.readout(runId)); go('ready'); state.note = 'Public state refreshed.'; }
async function loadFilteredRuns(filterMode) {
  const reply = await state.client.listRuns(); if (!reply.ok) throw Error(reply.error?.message);
  const ids = reply.result?.runs || [];
  const inspected = await Promise.all(ids.map(async run => {
    const id = typeof run === 'string' ? run : run.run_id;
    const detail = await state.client.request('inspect_run', {run_id: id});
    return detail.ok ? detail.result?.run || run : run;
  }));
  return filterMode ? inspected.filter(run => String(run.context?.host_mode || run.mode || '').toUpperCase() === filterMode) : inspected;
}
const STALE_SANDBOX_PATTERN = /one active D&D sandbox run is already (?:saved|loaded): ([\w-]+)/;
// A sandbox run abandoned by a prior session (browser closed, host restarted)
// never leaves 'active' status on its own, so it holds the one-active-slot
// lock forever. withSandboxRecovery lets the UI offer to end it and retry
// instead of just failing every future sandbox start with no way out.
async function withSandboxRecovery(attempt) {
  try {
    await attempt();
    state.staleSandbox = null;
  } catch (error) {
    const staleRunId = STALE_SANDBOX_PATTERN.exec(error.message || '')?.[1];
    if (!staleRunId) throw error;
    state.staleSandbox = {run_id: staleRunId, retry: attempt};
    state.error = `A previous D&D sandbox run ("${staleRunId}") is still marked active and is holding the only sandbox slot.`;
  }
}
async function resolveStaleSandbox() {
  const stale = state.staleSandbox;
  if (!stale) return;
  await work(async () => {
    result(await state.client.sandboxRelease(stale.run_id));
    state.staleSandbox = null;
    await stale.retry();
  }, `Ending ${stale.run_id}`);
}
async function loadScenarios() {
  await work(async () => {
    const reply = await state.client.scenarioCatalog('SANDBOX');
    if (!reply.ok) throw Error(reply.error?.message || 'The host could not list scenarios.');
    state.scenarios = reply.result?.scenarios || [];
  }, 'Loading scenarios');
}
async function beginChampionRun(name) {
  const attempt = async () => {
    const mode = state.pendingMode || 'SANDBOX';
    result(await state.client.boot(mode));
    const runId = `${name.toLowerCase()}-${Date.now().toString(36)}`;
    result(await state.client.startRun({
      run_id: runId, mode, seed: runSeed(`${name}-${Date.now()}`), scenario: scenarioFor(mode),
      party: [name], lead_selector: name, opposition: ['Townsperson'],
      ...(mode === 'FORGE' ? {module_id: 'reliquary-template'} : {}),
    }));
    state.runId = runId;
    result(await state.client.designStart(runId));
    await loadReadout(runId);
  };
  await work(() => withSandboxRecovery(attempt), `Beginning as ${name}`);
}
function bind() {
  document.querySelectorAll('[data-actor]').forEach(node => node.onclick = () => { state.selectedActor = node.dataset.actor; render(); });
  document.querySelectorAll('[data-examine-actor]').forEach(node => node.ondblclick = event => {
    event.preventDefault(); event.stopPropagation();
    work(async () => {
      const reply = result(await state.client.examine(state.runId, {entity_type: 'actor', entity_id: node.dataset.examineActor}));
      const dialog = document.querySelector('#item-dialog');
      if (!dialog || !reply.result?.examine) return;
      const skillDescs = {};
      const skills = state.options?.skills || {};
      Object.entries(skills).forEach(([skill, data]) => {
        skillDescs[skill] = typeof data === 'object' ? data.description : '';
      });
      dialog.innerHTML = globalThis.HSRUI.examineDetail(reply.result.examine, skillDescs);
      dialog.showModal();
    }, 'Examining', 'Reading public rules and source contributions from the host.');
  });
  document.querySelectorAll('[data-flight-type]').forEach(node => node.onclick = () => work(async () => {
    const type = node.dataset.flightType;
    const action = {type, actor: state.view?.flight_arena?.controller || actor().id || 'p0'};
    if (type === 'flight_move') { action.dx = Number(node.dataset.flightDx); action.dy = Number(node.dataset.flightDy); }
    result(await state.client.designAction(state.runId, action));
    await loadReadout(state.runId);
    state.note = 'Flight intent resolved by the host.';
  }));
  document.querySelectorAll('[data-item]').forEach(node => node.onclick = () => {
    const carried = actor().equipment || [];
    const item = [...carried, ...(state.view?.inventory || [])][Number(node.dataset.item)];
    const equippable = item && Number(node.dataset.item) >= carried.length && item.kind === 'imprint' && item.identified === true;
    const dialog = document.querySelector('#item-dialog');
    dialog.innerHTML = `${globalThis.HSRUI.detail(item, 'assets/')}${equippable ? `<div class="actions"><button type="button" class="action" data-equip-item="${E(item.id)}">Equip</button></div>` : ''}`;
    dialog.querySelector('[data-equip-item]')?.addEventListener('click', () => {
      dialog.close();
      work(async () => {
        result(await state.client.roomAction(state.runId, 'equip', {item: item.id, actor: actor().id || 'p0'}));
        await loadReadout(state.runId);
        state.note = 'Rune equipped.';
      });
    });
    dialog.showModal();
  });
  document.querySelectorAll('[data-action]').forEach(node => node.onclick = async () => {
    const action = node.dataset.action;
    if (action === 'auto-travel') {
      await work(async () => {
        const reply = await state.client.autoTravel(state.runId, 'well', 4, false);
        const payload = result(reply).result.travel;
        state.view = payload.public_view;
        state.receipt = payload.public_receipt;
        state.selected = 'journey';
        state.note = payload.event?.reached ? 'Travel reached the descent route. Choose Descend to enter the Reliquary.' : 'Host travel advanced the public route.';
        render();
      });
      return;
    }
    if (action.startsWith('layout-preset:')) {
      state.preferences.layout = action.slice('layout-preset:'.length);
      savePreferences(); render(); return;
    }
    if (action === 'cycle-tray') {
      state.trayState = state.trayState === 'collapsed' ? 'compact' : state.trayState === 'compact' ? 'expanded' : 'collapsed';
      render();
      return;
    }
    if (action === 'toggle-messages') { state.messageHistoryOpen = !state.messageHistoryOpen; render(); return; }
    if (action === 'close-messages') { state.messageHistoryOpen = false; render(); return; }
    if (action === 'clear-messages') { state.messageHistory = []; render(); return; }
    if (action === 'toggle-arrange') { state.arrangeMode = !state.arrangeMode; render(); return; }
    if (action === 'reset-layout') { state.workspaceLayout = {}; saveWorkspaceLayout(); render(); return; }
    if (action === 'resolve-stale-sandbox') { await resolveStaleSandbox(); return; }
    if (action === 'title') { state.route = ['title']; state.phase = 'title'; render(); }
    else if (action === 'back') { back(); render(); }
    else if (action.startsWith('menu:')) {
      const phase = action.slice(5);
      go(phase); render();
      // Both screens name the chosen scenario, so the catalog is fetched on the
      // way into Simulation Mode rather than only inside the picker.
      if ((phase === 'edit-scenario' || phase === 'menu-simulation') && state.scenarios === null) { await loadScenarios(); render(); }
    }
    else if (action === 'create') { if (state.pendingMode === 'FORGE') state.draft.level = 1; go('create'); render(); await ensureCreationSeed(); render(); scheduleLivePreview(0); }
    else if (action === 'restart') { resetCreationDraft(); go('create'); render(); await ensureCreationSeed(); render(); scheduleLivePreview(0); }
    else if (state.phase === 'create' && await creatorAction(action)) { /* handled by the paged creator */ }
    else if (action === 'engine' || action === 'start-engine') await connect('engine-host', action === 'engine' ? 'title' : 'party-select');
    else if (action.startsWith('mode:')) { state.pendingMode = action.slice(5); go(state.view ? 'party-select' : 'transport'); render(); }
    else if (action === 'champion-select') { go('champion-select'); render(); }
    else if (action.startsWith('champion:')) await beginChampionRun(action.slice(9));
    else if (action === 'cancel-conversation') { state.pendingConversation = null; state.consoleDraft = ''; render(); }
    else if (action === 'load-progression') await work(async () => { const reply = await state.client.progression(state.accountIdentity); if (!reply.ok) throw Error(reply.error?.message); state.progression = reply.result?.progression || null; });
    else if (action.startsWith('object-inspect:') || action.startsWith('object-search:') || action.startsWith('object-open:')) await work(async () => {
      const [kind, objectId] = [action.split(':')[0].slice(7), action.slice(action.indexOf(':') + 1)];
      const object = state.view?.room?.objects?.[objectId] || {};
      const lifeObject = !object.object_id && !object.kind;
      const type = lifeObject ? (kind === 'open' ? 'open' : 'inspect') : (kind === 'inspect' ? 'inspect_object' : kind === 'search' ? 'search_object' : 'open_object');
      result(await state.client.roomAction(state.runId, type, {object_id: objectId, actor: actor().id || 'p0'}));
      await loadReadout(state.runId);
    });
    else if (action === 'load-terminal-receipt') await work(async () => { const reply = await state.client.terminalReceipt(state.runId); if (!reply.ok) throw Error(reply.error?.message); state.terminal = reply.result?.terminal_receipt || null; });
    else if (action === 'load-debug-state') await work(async () => {
      const reply = await state.client.request('sandbox_debug', {run_id: state.runId});
      if (!reply.ok) throw Error(reply.error?.message || 'Debug state unavailable');
      state.debugReadout = reply.result?.debug_readout || null;
    });
    else if (action === 'randomize-race' || action === 'randomize-class') { const rows = state.options?.[action === 'randomize-race' ? 'races' : 'classes'] || []; if (rows.length) { const index = Math.abs([...String(state.draft.creation_seed || state.draft.name || 'hsr')].reduce((n,c)=>n+c.charCodeAt(0),0)) % rows.length; state.draft[action === 'randomize-race' ? 'race' : 'character_class'] = rows[index].id; persistUiState(); render(); } }
    else if (action === 'randomize-stats') await work(async () => { const seed = state.draft.creation_seed || state.draft.name; if (!seed) throw Error('Enter a lead name or creation seed before randomizing stats.'); state.draft.creation_seed = seed; const reply = result(await state.client.characterRoll(seed, 0)); state.roll = reply.result?.ability_roll || null; state.draft.roll_set = 0; state.draft.ability_assignment = 'auto'; persistUiState(); }, 'Randomizing deterministic stats');
    else if (action === 'roll-abilities') await work(async () => {
      const seed = state.draft.creation_seed || state.draft.name;
      if (!seed) throw Error('Enter a lead name or creation seed before rolling ability scores.');
      const nextSet = state.roll ? 1 : 0;
      if (state.roll?.roll_set === 1) throw Error('The single ability-score reroll has already been used.');
      state.draft.creation_seed = seed;
      state.draft.roll_set = nextSet;
      const reply = result(await state.client.characterRoll(seed, nextSet));
      state.roll = reply.result?.ability_roll || null;
      state.draft.ability_assignment = 'auto';
      state.note = nextSet ? 'Rerolled the ability scores. The first set remains in the host receipt.' : 'Ability scores rolled. Assign them or keep automatic placement.';
      persistUiState();
    });
    else if (action === 'advancements-manual') { state.draft.advancement_mode = 'manual'; state.draft.advancements = {}; render(); }
    else if (action === 'advancements-auto') { state.draft.advancement_mode = 'auto'; state.draft.advancements = 'auto'; render(); }
    else if (action === 'skills-manual') { state.draft.skill_mode = 'manual'; state.draft.skills = []; render(); }
    else if (action === 'skills-auto') { state.draft.skill_mode = 'auto'; state.draft.skills = 'auto'; render(); }
    else if (action === 'spells-manual') { state.draft.spell_mode = 'manual'; state.draft.spells = []; render(); }
    else if (action === 'spells-auto') { state.draft.spell_mode = 'auto'; state.draft.spells = 'auto'; render(); }
    else if (action.startsWith('continue:')) await work(async () => {
      const filterMode = action.slice(9);
      result(await state.client.boot('DESIGN'));
      state.runs = await loadFilteredRuns(filterMode);
      state.runsFilter = filterMode;
      go('runs');
    });
    else if (action === 'refresh-runs') await work(async () => { state.runs = await loadFilteredRuns(state.runsFilter); });
    else if (action.startsWith('load:')) await work(async () => {
      const id = action.slice(5);
      const inspected = await state.client.request('inspect_run', {run_id: id});
      if (!inspected.ok) throw Error(inspected.error?.message || 'Saved run could not be inspected');
      const mode = String(inspected.result?.run?.context?.host_mode || inspected.result?.run?.mode || 'DESIGN').toUpperCase();
      if (['DESIGN', 'SANDBOX', 'FORGE', 'REVIEW'].includes(mode)) result(await state.client.boot(mode));
      result(await state.client.loadRun(id)); await loadReadout(id);
    });
    else if (action === 'reset-preferences') { state.preferences = {...defaultPreferences}; savePreferences(); render(); }
    else if (action === 'load-scenarios') { await loadScenarios(); render(); }
    else if (action.startsWith('scenario:')) {
      const id = action.slice(9);
      if (!(state.scenarios || []).some(row => row.scenario === id)) { fail('That scenario is not offered by this host.'); render(); return; }
      state.preferences.scenario = id; savePreferences();
      state.note = `New Simulation runs will open on ${scenarioTitle(id)}.`;
      render();
    }
    else if (action === 'reset-scenario') {
      state.preferences.scenario = defaultPreferences.scenario;
      state.preferences.scenarioSeed = defaultPreferences.scenarioSeed;
      savePreferences();
      state.note = 'Scenario choice reset to the Simulation default.';
      render();
    }
    else if (action === 'refresh-readout') await work(async () => loadReadout(state.runId));
    else if (action === 'save') await work(async () => {
      result(await state.client.saveRun(state.runId));
      state.note = 'Run saved. No automatic retry will be made if the response is uncertain.';
      state.route = ['title']; state.phase = 'title';
    });
    else if (action.startsWith('tab:')) { selectGameplayScreen(action.slice(4)); render(); }
    else if (action.startsWith('talk:') || action.startsWith('intent:')) {
      state.pendingConversation = null;
      state.consoleDraft = action.startsWith('talk:') ? `talk to ${action.slice(5)}` : action.slice(7);
      render();
      document.querySelector('#console-input')?.focus();
    }
  });
  const seedInput = document.querySelector('[data-scenario-seed]');
  if (seedInput) seedInput.onchange = () => {
    state.preferences.scenarioSeed = seedInput.value.trim();
    savePreferences();
    state.note = state.preferences.scenarioSeed
      ? `Simulation runs will use the seed ${state.preferences.scenarioSeed}.`
      : "Simulation runs will use the lead's own creation seed.";
    render();
  };
  document.querySelectorAll('[data-pref]').forEach(node => node.onchange = () => {
    const key = node.dataset.pref;
    if (key === 'iconActions') state.preferences.iconActions = node.checked;
    else if (key === 'motion') state.preferences.motion = node.checked ? 'reduced' : 'full';
    else if (key === 'effects') state.preferences.effects = node.checked ? 'soft' : 'full';
    else if (key === 'layout') state.preferences.layout = node.value;
    else if (key === 'menuDensity') state.preferences.menuDensity = node.value;
    else if (key === 'sceneScale') state.preferences.sceneScale = node.value;
    else if (key === 'dockPosition') state.preferences.dockPosition = node.value;
    else if (key === 'showParty' || key === 'showNavigation') state.preferences[key] = node.checked;
    else if (key === 'accent') state.preferences.accent = node.value;
    else if (key === 'textScale') state.preferences.textScale = node.value;
    else if (key === 'showClock') state.showClock = node.checked;
    else if (key === 'showTickIndicator') state.showTickIndicator = node.checked;
    savePreferences(); render();
  });
  document.querySelectorAll('[data-engine-action]').forEach(node => node.onclick = async () => {
    const action = node.dataset.engineAction;
    if (action === 'idle_tick') {
      await work(async () => {
        result(await state.client.idleTick(state.runId, 1));
        state.selected = 'journey';
        state.note = state.receipt?.pause ? `Idle paused: ${state.receipt.pause.message}` : 'Idle advanced one safe step.';
        render();
      });
      return;
    }
    if (['inspect', 'inspect_object', 'search_object', 'open_object', 'attack', 'move', 'move_room', 'enter'].includes(action)) {
      state.actionPicker = {action, label: node.querySelector('.action-text')?.textContent || action};
      render();
      return;
    }
    await work(async () => {
      const label = node.querySelector('.action-text')?.textContent || action;
      const reply = await state.client.designTurn(state.runId, label, {type: action, actor: actor().id || 'p0'});
      result(reply);
      state.note = `${node.querySelector('.action-text')?.textContent || action} submitted to the engine.`;
      addMessage(state.note);
    });
  });
  document.querySelectorAll('[data-action^="target-choice:"]').forEach(node => node.onclick = async () => {
    const parts = node.dataset.action.split(':');
    const action = parts[1]; const kind = parts[2]; const rawValue = parts.slice(3).join(':');
    state.actionPicker = null;
    await work(async () => {
      const fields = {type: action, actor: actor().id || 'p0'};
      if (['inspect', 'inspect_object', 'search_object', 'open_object'].includes(action)) fields.object_id = rawValue;
      else if (action === 'move' && kind === 'destination' && rawValue.includes(',')) fields.destination = rawValue.split(',').map(Number);
      else if (['move_room', 'enter'].includes(action)) fields.destination = rawValue;
      else fields.target = rawValue;
      result(await state.client.designTurn(state.runId, node.textContent.trim(), fields));
      await loadReadout(state.runId);
    });
  });
  document.querySelector('[data-action="cancel-target-picker"]')?.addEventListener('click', () => { state.actionPicker = null; render(); });
  document.querySelectorAll('[data-auto-step]').forEach(node => node.onclick = () => work(async () => {
    result(await state.client.request(node.dataset.autoStep, {run_id: state.runId}));
    await loadReadout(state.runId);
  }));
  document.querySelector('[data-action="idle-tick"]')?.addEventListener('click', () => work(async () => {
    result(await state.client.idleTick(state.runId, 1));
    state.selected = 'journey';
    state.note = state.receipt?.pause ? `Idle paused: ${state.receipt.pause.message}` : 'Idle advanced one safe step.';
    render();
  }));
  document.querySelectorAll('[data-domain-feature]').forEach(node => node.onclick = () => work(async () => {
    const reply = await state.client.roomAction(state.runId, 'domain', {feature: node.dataset.domainFeature, actor: actor().id || 'p0'});
    result(reply); await loadReadout(state.runId);
    state.note = `${node.dataset.domainFeature} submitted to the engine.`;
    addMessage(state.note);
  }));
  document.querySelectorAll('[data-maneuver]').forEach(node => node.onclick = () => work(async () => {
    const fields = {maneuver: node.dataset.maneuver, actor: actor().id || 'p0'};
    if (node.dataset.target) fields.target = node.dataset.target;
    state.lastManeuver = {actor: fields.actor, maneuver: node.dataset.maneuver, at: Date.now()};
    const reply = await state.client.roomAction(state.runId, 'maneuver', fields);
    result(reply); await loadReadout(state.runId);
    state.note = `${node.dataset.maneuver} submitted to the engine.`;
    addMessage(state.note);
  }));
  document.querySelectorAll('[data-action^="reaction:"]').forEach(node => node.onclick = () => work(async () => {
    const defense = node.dataset.action.slice('reaction:'.length);
    const fields = {type: defense === 'decline_reaction' ? 'decline_reaction' : 'reaction', actor: actor().id || 'p0'};
    if (defense !== 'decline_reaction') fields.defense = defense;
    result(await state.client.designAction(state.runId, fields));
    await loadReadout(state.runId);
    state.note = defense === 'decline_reaction' ? 'Reaction declined through the host.' : `${defense} reaction submitted to the host.`;
    addMessage(state.note);
  }));
  document.querySelectorAll('[data-conversation]').forEach(node => node.onclick = () => {
    state.pendingConversation = {npc: node.dataset.conversation, mode: node.dataset.conversationMode};
    state.consoleDraft = '';
    render();
    document.querySelector('#console-input')?.focus();
  });
  document.querySelectorAll('[data-upgrade]').forEach(node => node.onclick = () => work(async () => {
    const reply = await state.client.purchaseUpgrade(state.accountIdentity, node.dataset.upgrade);
    if (!reply.ok) throw Error(reply.error?.message || 'Purchase failed');
    state.progression = reply.result?.progression || state.progression;
  }));
  document.querySelectorAll('[data-create-field]').forEach(node => node.onchange = () => {
    const key = node.dataset.createField;
    state.draft[key] = ['level', 'spell_budget'].includes(key) ? Number(node.value) : node.value;
    if (key === 'creation_seed' && node.value) state.draft.creation_seed = node.value;
    if (key === 'character_class' && state.draft.spell_budget && !(optionBy('classes', node.value).spells || []).length) state.draft.spell_budget = 0;
    persistUiState(); render();
  });
  document.querySelectorAll('[data-race-choice]').forEach(node => node.onclick = () => {
    state.draft.race = node.dataset.raceChoice;
    state.draft.floating_bonuses = 'auto';
    persistUiState(); render();
  });
  document.querySelectorAll('[data-assign]').forEach(node => node.onchange = () => {
    const next = state.draft.ability_assignment && typeof state.draft.ability_assignment === 'object'
      ? {...state.draft.ability_assignment} : automaticAssignment(state.roll?.scores || []);
    const chosen = Number(node.value);
    // A rolled score is a physical slot. Selecting it here removes it from
    // whichever ability currently owns that slot, preventing a tempting but
    // invalid all-18/duplicated assignment before preview reaches the host.
    if (node.value) {
      document.querySelectorAll('[data-assign]').forEach(select => {
        if (select !== node && select.value && Number(select.value) === chosen) {
          select.value = '';
          delete next[select.dataset.assign];
        }
      });
      next[node.dataset.assign] = chosen;
    } else delete next[node.dataset.assign];
    state.draft.ability_assignment = Object.keys(next).length === ABILITIES.length ? next : 'auto';
    persistUiState(); render();
  });
  document.querySelectorAll('[data-floating]').forEach(node => node.onchange = () => {
    let next = [...document.querySelectorAll('[data-floating]:checked')].map(input => input.dataset.floating);
    const limit = optionBy('races', state.draft.race).floating_bonus?.count || next.length;
    // Picking past the limit swaps out the oldest pick instead of creating an invalid build.
    if (node.checked && next.length > limit) {
      const others = next.filter(a => a !== node.dataset.floating);
      next = [...(limit > 1 ? others.slice(-(limit - 1)) : []), node.dataset.floating];
    }
    state.draft.floating_bonuses = next.length ? next : 'auto'; persistUiState(); render(); scheduleLivePreview();
  });
  document.querySelectorAll('[data-advancement]').forEach(node => node.onchange = () => {
    state.draft.advancements = {...(state.draft.advancements && typeof state.draft.advancements === 'object' ? state.draft.advancements : {}), [node.dataset.advancement]: Number(node.value || 0)};
    persistUiState(); render();
  });
  document.querySelectorAll('[data-skill]').forEach(node => node.onchange = () => {
    state.draft.skills = [...document.querySelectorAll('[data-skill]:checked')].map(input => input.dataset.skill); persistUiState(); render();
  });
  document.querySelectorAll('[data-spell]').forEach(node => node.onchange = () => {
    state.draft.spells = [...document.querySelectorAll('[data-spell]:checked')].map(input => input.dataset.spell); persistUiState(); render();
  });
  document.querySelector('#character-form')?.addEventListener('submit', async event => {
    event.preventDefault(); const data = Object.fromEntries(new FormData(event.target));
    state.draft = {...state.draft, ...data, level: Number(data.level || state.draft.level || 1), spell_budget: Number(data.spell_budget || state.draft.spell_budget || 0)};
    if (!state.draft.creation_seed) state.draft.creation_seed = state.draft.name; persistUiState();
    await work(async () => {
      const build = buildPayload();
      const reply = await state.client.previewCharacter(build);
      state.preview = result(reply).result; state.phase = 'preview';
    });
  });
  document.querySelector('[data-action="confirm-build"]')?.addEventListener('click', async () => {
    const attempt = async () => {
      const profileSeed = state.draft.creation_seed || state.draft.name;
      const profileId = `web-${profileSeed.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-|-$/g, '') || Date.now()}`;
      const build = buildPayload();
      result(await state.client.buildCharacter(profileId, build, (state.live || state.preview?.character)?.build_hash));
      const runId = `${profileId}-${Date.now().toString(36)}`;
      const mode = state.pendingMode || 'DESIGN';
      result(await state.client.boot(mode));
      result(await state.client.startRun({
        run_id: runId, mode, seed: runSeed(state.draft.creation_seed), scenario: scenarioFor(mode),
        party: [`custom:${profileId}`], lead_selector: `custom:${profileId}`, opposition: ['Townsperson'],
        ...(mode === 'FORGE' ? {module_id: 'reliquary-template'} : {}),
      }));
      state.runId = runId;
      result(await state.client.designStart(runId));
      await loadReadout(runId);
      resetCreationDraft();
    };
    await work(() => withSandboxRecovery(attempt));
  });
  document.querySelector('#console-form')?.addEventListener('submit', async event => {
    event.preventDefault();
    const text = new FormData(event.target).get('console')?.trim();
    if (!text) return;
    const conversation = state.pendingConversation;
    state.consoleDraft = ''; state.pendingConversation = null;
    await work(async () => {
      if (conversation) result(await state.client.designTurn(state.runId, text, {type: 'talk', target: conversation.npc, mode: conversation.mode, text, actor: actor().id || 'p0'}));
      else if (/^(look around|show room)$/i.test(text)) state.selected = 'room';
      else if (/^show my equipment$/i.test(text)) state.selected = 'equipment';
      else {
        const social = text.match(/^(talk to|thank)\s+(.+)$/i);
        if (social) {
          const residents = Object.values(state.view?.room?.npcs || {});
          const named = residents.find(row => String(row.name || row.id).toLowerCase() === social[2].toLowerCase())
            || (state.view?.room?.resident && String(state.view.room.resident).toLowerCase() === social[2].toLowerCase()
              ? {id: state.view.room.resident} : null);
          if (!named) throw Error('That resident is not visible in the current room.');
          result(await state.client.designTurn(state.runId, text, {type: 'talk', target: named.id || named.npc_id || named.name, mode: 'speak', text, actor: actor().id || 'p0'}));
        } else result(await state.client.designTurn(state.runId, text));
      }
      await loadReadout(state.runId);
    });
  });
  // Dragging support for message panel and console
  document.querySelectorAll('[data-panel]').forEach(panel => {
    let offsetX = 0, offsetY = 0, mouseX = 0, mouseY = 0;
    const header = panel.querySelector('.panel-header');
    if (!header) return;
    header.style.cursor = 'grab';
    header.onmousedown = e => {
      header.style.cursor = 'grabbing';
      mouseX = e.clientX;
      mouseY = e.clientY;
      offsetX = panel.offsetLeft - mouseX;
      offsetY = panel.offsetTop - mouseY;
      const moveHandler = e => {
        panel.style.left = (e.clientX + offsetX) + 'px';
        panel.style.top = (e.clientY + offsetY) + 'px';
      };
      const upHandler = () => {
        document.removeEventListener('mousemove', moveHandler);
        document.removeEventListener('mouseup', upHandler);
        header.style.cursor = 'grab';
      };
      document.addEventListener('mousemove', moveHandler);
      document.addEventListener('mouseup', upHandler);
    };
  });
  bindWorkspacePanels();
  mountArcade();
}
window.addEventListener('hashchange', () => {
  const next = location.hash.slice(1);
  if (screens.includes(next) && state.phase === 'ready') { state.selected = next; render(); }
});
window.addEventListener('popstate', event => {
  if (!event.state?.hsr) return;
  state.phase = event.state.phase || 'title';
  state.route = Array.isArray(event.state.route) && event.state.route.length ? [...event.state.route] : ['title'];
  if (screens.includes(event.state.selected)) state.selected = event.state.selected;
  render();
});
document.querySelector('#item-dialog')?.addEventListener('click', event => { if (event.target === event.currentTarget) event.currentTarget.close(); });
function ensureAppInitialized() {
  if (state.initialized) return;
  state.initialized = true;
  const app = document.querySelector('#app');
  if (!app) {
    console.error('HSR: app element not found');
    return;
  }
  try {
    applyPreferences();
    history.replaceState(navigationState(), '', location.href);
    render();
    console.log('HSR app initialized');
  } catch (error) {
    console.error('HSR app initialization error:', error);
    if (window.HSRStartupError) window.HSRStartupError(error, 'ensureAppInitialized');
    else app.innerHTML = `<div style="padding:30px; color:#a9a397;"><p>HSR initialization failed:</p><pre>${E(error.message)}</pre></div>`;
  }
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', ensureAppInitialized);
} else {
  ensureAppInitialized();
}
// Clock ticker - updates time display every second
setInterval(() => {
  if (!state.showClock) return;
  const clockEl = document.querySelector('.status-clock');
  if (!clockEl) return;
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');
  const timeDisplay = clockEl.querySelector('.time-display');
  if (timeDisplay) {
    state.clockTick++;
    const tickIcon = state.showTickIndicator ? `<span class="tick-pulse" data-tick="${state.clockTick % 2}">●</span>` : '';
    timeDisplay.innerHTML = `${tickIcon}<strong>${hours}:${minutes}:${seconds}</strong>`;
  }
}, 500);
globalThis.HollowStarUI = Object.freeze({schema: 'hsr-ui-client-2', getPublicView: () => structuredClone(state.view), getStatus: () => ({phase: state.phase, run_id: state.runId, transport: state.transport, busy: state.busy})});
