import {syncPuppets} from './puppet-dom.js';
import {createHSRClient} from './hsr-client.js?v=drain-1';
import {createArcadeCanvas} from './arcade-canvas.js';
import {bindArcadeInput} from './arcade-input.js';
import {createArcadeLoop} from './arcade-loop.js';
import {createCombatDirector, DEFAULT_COMBAT_SETTINGS, damageMath, healMath} from './combat-director.js?v=director-12';
import {combatStyle, styleAllows, isTypingTarget, stepDestination, groundDestination, flightDestination, withinMovement, avoidOccupied, threatenedBy, hotbarSlots, spaceIntent, radialItems, radialLayout, gridDistance} from './combat-input.js?v=input-1';
import {createVoiceFeed, DEFAULT_VOICE_SETTINGS} from './voice-feed.js?v=2';
import {ffLayout, effectRack, visibleEffects, effectLabel, turnOrderStrip, commandWindow, partyStatusPanel} from './battle-scene.js?v=effects-2';
import {routeMap, nodeGlyph} from './expedition-map.js?v=xp-2';
import {createStage} from './stage-view.js';
import {screenFade, syncAmbient} from './qol.js';
import {themeFor} from './stage-set.js';
import {bodyOf} from './stage-world.js';
import {createToolbox} from './actor-toolbox.js';
import {mountBattleBackdrop, createWoundLayer} from './battle-backdrop.js';
import {playCutscene} from './cutscene-player.js?v=cs-2';
import {createAudioSystem, DEFAULT_AUDIO_SETTINGS, AUDIO_CATEGORIES} from './audio-system.js';
import {assetStatus} from './asset-registry.js';
import {t} from './strings.js';
import {runDialogue} from './dialogue-runner.js';
import {DIALOGUES} from './dialogues.js';
import {titleCard, storyToast} from './transitions.js';
import {CUTSCENES, cutsceneUnlocked} from './cutscenes.js?v=cs-2';
import {characterFigure as drawDoll, visualRole, visualIdentity, presentationAppearance, visualExpression} from './paperdoll.js?v=puppet-1';

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
    end_turn: 'Finish the turn. Unspent actions are lost.',
    decant: 'Destroy an identified Imprint, relic, or legendary and absorb its powers into your Attunement.',
  },
};
const preferenceKey = 'hsr-display-preferences';
const workspaceKey = 'hsr-workspace-layout-v1';
const defaultPreferences = {scenario: '', scenarioSeed: '', iconActions: false, menuDensity: 'comfortable', layout: 'sanctum', sceneScale: 'standard', dockPosition: 'bottom', debugMode: false, showParty: true, showNavigation: true, showWorkspace: true, showActionDock: true, showStatusMessages: true, menuSize: 'standard', accent: 'gold', textScale: '1', stageMode: 'on', stageAspect: '2:1', stageResolution: 'standard', motion: 'full', effects: 'full', showTickIndicator: true, colorblind: 'off'};
// Connection box and heartbeat. Nested groups are merged key by key so a
// setting added later still gets its default for people with older saves.
const DEFAULT_LINK_SETTINGS = Object.freeze({
  heartbeatMs: 5000,    // 0 = off; manual "Ping now" still works
  warnMs: 150,          // latency at or above this shows amber
  badMs: 400,           // ...and this shows red
  clock24h: true,
  seconds: true,
  showLatency: true,    // latency beside the clock in the collapsed box
  showDrift: true,
  sparkline: true,      // latency history graph in the expanded box
  historySize: 40,
});
const DEFAULT_STORY_SETTINGS = Object.freeze({textSpeed: 'normal', skipSeenCutscenes: false, floorCards: true});
const TEXT_SPEEDS = {slow: 55, normal: 34, fast: 16, instant: 0};
const NESTED_PREFERENCES = {combat: DEFAULT_COMBAT_SETTINGS, link: DEFAULT_LINK_SETTINGS, voice: DEFAULT_VOICE_SETTINGS, audio: DEFAULT_AUDIO_SETTINGS, story: DEFAULT_STORY_SETTINGS};
function readPreferences() {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(preferenceKey) || '{}') || {}; } catch {}
  const merged = {...defaultPreferences, ...saved};
  for (const [group, defaults] of Object.entries(NESTED_PREFERENCES)) merged[group] = {...defaults, ...(saved[group] || {})};
  return merged;
}
function defaultPreferenceSet() {
  const fresh = {...defaultPreferences};
  for (const [group, defaults] of Object.entries(NESTED_PREFERENCES)) fresh[group] = {...defaults};
  return fresh;
}
function readWorkspaceLayout() {
  try {
    const layout = JSON.parse(localStorage.getItem(workspaceKey) || '{}');
    // The old right rail was one draggable panel. Keep its saved position for
    // the new Workspace box, while giving Screens an independent clean anchor.
    if (layout.navigation && !layout.workspace) layout.workspace = {...layout.navigation};
    delete layout.navigation;
    // Connections/Information/Clock are retired as standalone draggable panels
    // -- their data now lives inside the Workspace card. The Main Window
    // (.center-stage) is no longer draggable either. Drop the orphaned offsets
    // rather than let them sit unused forever.
    delete layout.connections; delete layout.information; delete layout.clock; delete layout.stage;
    return layout;
  } catch { return {}; }
}
function saveWorkspaceLayout() {
  try { localStorage.setItem(workspaceKey, JSON.stringify(state.workspaceLayout)); } catch {}
}
function encounterActive(view = state.view) {
  // Floor One keeps a public combat-shaped envelope for schema stability, but
  // its idle town state has no current actor or initiative order. Only a
  // combat envelope with a live turn is an encounter for navigation and
  // action-bar gating.
  const combat = view?.combat;
  const liveCombat = combat && !combat.complete && (combat.current || (combat.order || []).length);
  return Boolean(liveCombat || (view?.arcade && !view.arcade.complete));
}
// The Floor One town is the only place the host runs idle travel and free-text
// social intents; once the run has descended, those are dungeon rooms and the
// controls that need a social world are withheld instead of sent and refused.
function floorOneWorld(view = state.view) {
  return view?.scene?.floor_id === 'floor-1-town';
}
function arcadeActive(view = state.view) {
  return Boolean(view?.arcade && !view.arcade.complete);
}
function tacticalActive(view = state.view) {
  const combat = view?.combat;
  return Boolean(combat && !combat.complete && (combat.current || (combat.order || []).length) && !arcadeActive(view));
}
function encounterStepActor(view = state.view) {
  const combat = view?.combat;
  if (!combat || combat.complete) return '';
  return combat.pending?.[0]?.reactor || combat.current || '';
}
function selectGameplayScreen(screen) {
  if (!screens.includes(screen) || state.selected === screen) return false;
  if (screen === 'options' && state.selected !== 'options') state.optionsReturnScreen = state.selected;
  clearScreenTransientState();
  state.selected = screen;
  persistUiState();
  history.replaceState(navigationState(), '', `${location.pathname}${location.search}#${screen}`);
  return true;
}
function refreshScreen(screen = state.selected) {
  if (!screens.includes(screen)) return false;
  // A refresh is also the safe boundary between screens: close native dialogs,
  // discard floating combat text/context menus, and rebuild one clean surface.
  if (!selectGameplayScreen(screen)) clearScreenTransientState();
  render();
  return true;
}
function syncEncounterScreen(previousView, nextView) {
  // Arcade and turn-based fights both live in Encounters; when one ends the
  // player stays there to pick the next expedition node.
  if (arcadeActive(nextView) && !arcadeActive(previousView)) selectGameplayScreen('battle');
  else if (tacticalActive(nextView) && !tacticalActive(previousView)) selectGameplayScreen('battle');
  else if (encounterActive(previousView) && !encounterActive(nextView)) selectGameplayScreen(nextView?.expedition?.active ? 'battle' : 'room');
}
function actionTargets(action) {
  const room = state.view?.room || {};
  const objects = Object.values(room.objects || {}).filter(row => row && row.visible !== false).map(row => ({
    value: row.object_id || row.id, label: objectLabel(row), kind: 'object',
  })).filter(row => row.value);
  const targetContext = new Map((state.view?.combat?.target_context || []).map(row => [row.id, row]));
  const opponents = (state.view?.opposition || []).filter(
    row => row && row.alive !== false && row.hp !== 0,
  ).map(row => ({
    value: row.id || row.npc_id || row.name,
    label: `${row.name || row.id}${targetContext.has(row.id) ? ` · ${targetContext.get(row.id).distance_ft} ft` : ''}`,
    kind: 'target',
  })).filter(row => row.value);
  const exits = Object.entries(room.exits || {}).map(([direction, destination]) => ({
    value: destination?.id || destination, label: `${direction}: ${readable(destination)}`, kind: 'destination',
  })).filter(row => row.value);
  const residents = Object.values(room.npcs || {}).filter(row => row && row.id && row.alive !== false && !row.child).map(row => ({
    value: row.id, label: row.name || row.id, kind: 'target',
  }));
  if (['inspect', 'inspect_object', 'search_object', 'open_object', 'take'].includes(action)) return objects;
  if (['talk', 'attack'].includes(action) && !encounterActive() && state.view?.schema === 'hollow-star-public-view-1') return residents;
  if (action === 'grand_cleave') return ['east','west','north','south'].map(value => ({value, label:value[0].toUpperCase()+value.slice(1)+' · 180° arc, allies included',kind:'facing'}));
  if (action.startsWith('maneuver_')) {
    const row=(state.view?.combat?.contextual_actions || []).find(r=>r.id===action);
    return opponents.filter(p=>row?.targets?.includes(p.value));
  }
  if (['attack','maneuver','read_seam','quick_toss','dagger_attack','cleaver_attack'].includes(action)) {
    const row=(state.view?.combat?.contextual_actions || []).find(r=>r.id===action);
    return Array.isArray(row?.targets) ? opponents.filter(p=>row.targets.includes(p.value)) : opponents;
  }
  if (['shove', 'trip', 'grapple', 'help'].includes(action)) {
    // The host lists the legal target ids per action (within 5 ft, size
    // limits); fall back to every visible opponent if it did not.
    const row = (state.view?.combat?.contextual_actions || []).find(item => item.id === action);
    const legal = Array.isArray(row?.targets) ? new Set(row.targets) : null;
    return legal ? opponents.filter(choice => legal.has(choice.value)) : opponents;
  }
  if (action === 'decant') {
    return (state.view?.inventory || []).filter(item => item?.id && item.identified !== false
      && (item.kind === 'imprint' || ['rare', 'legendary'].includes(item.rarity))).map(item => ({
      value: item.id, label: `${item.display_name || item.name || item.id}${item.rarity ? ` · ${item.rarity}` : ''}`, kind: 'item',
    }));
  }
  if (action === 'move' && encounterActive()) {
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
  if (action === 'move' || ['move_room', 'enter'].includes(action)) return exits;
  return [];
}
function targetPicker() {
  const picker = state.actionPicker;
  if (!picker) return '';
  const choices = actionTargets(picker.action);
  return `<section class="hsr-target-picker" aria-live="polite"><strong>${E(picker.label)} — choose a target</strong><div class="target-choices">${choices.map(choice => button(choice.label, `target-choice:${picker.action}:${choice.kind}:${choice.value}`, 'secondary')).join('')}</div>${choices.length ? '' : '<p class="notice">No visible target is available for this action.</p>'}${button('Cancel', 'cancel-target-picker', 'secondary')}</section>`;
}
function spellPicker() {
  const picker = state.spellPicker;
  if (!picker) return '';
  const spell = picker.spells.find(row => row.id === picker.id) || picker.spells[0];
  if (!spell) return '<p>No spells are available.</p>';
  const grid = spell.radius || spell.operation === 'teleport';
  const origin = party().find(row => row.id === picker.actor)?.position || [0, 0, 0];
  const noTargets = grid || ['time_stop', 'gate', 'niv_descent'].includes(spell.operation);
  const choices = spell.operation === 'heal' || spell.operation === 'utility' ? party() : (state.view?.opposition || []);
  const meta = [
    ['silent','Silent Spell','Removes the verbal component.','No cost'],['still','Still Spell','Removes the somatic component.','No cost'],
    ['enlarge','Distant Spell','Doubles range when range is applicable.','1 focus'],['extend','Extended Spell','Doubles duration when duration is applicable.','1 focus'],
    ['careful','Careful Spell','Protects chosen allies from the spell’s saving throw.','1 focus'],['empower','Empowered Spell','Raises variable numeric effects.','2 focus'],
    ['maximize','Maximized Spell','Pushes eligible dice to their maximum.','3 focus'],['widen','Widened Spell','Doubles an eligible area.','3 focus'],
    ['twin','Twinned Spell','Repeats a legal single-target spell on another target.','4 focus'],['quicken','Quickened Spell','Converts the cast to a bonus action under the host action tax.','4 focus']
  ];
  const hasArea = Boolean(spell.radius), hasDuration = Boolean(spell.duration), hasSave = Boolean(spell.save), hasTarget = !['time_stop','gate','niv_descent'].includes(spell.operation);
  const legalMeta = meta.filter(([id]) => !['enlarge','extend','careful','widen','twin','quicken'].includes(id) || ((id==='enlarge' && spell.range) || (id==='extend' && hasDuration) || (id==='careful' && hasSave && hasArea) || (id==='widen' && hasArea) || (id==='twin' && hasTarget) || id==='quicken'));
  return `<section class="hsr-target-picker spell-workspace" aria-label="Spell selection"><form id="spell-form">
    <div class="spell-workspace-head"><div><p class="eyebrow">Ritual casting interface</p><h2>${E(spell.display_name)}</h2><p class="spell-summary">${E(spell.summary || 'A host-validated magical working.')}</p></div><span class="spell-rank">Rank ${E(spell.level)} · ${E(spell.school || 'Arcane')}</span></div>
    <label class="spell-select-label">Select working<select id="spell-choice">${picker.spells.map(row => `<option value="${E(row.id)}" ${row.id === spell.id ? 'selected' : ''}>${E(row.display_name)} · Rank ${E(row.level)}</option>`).join('')}</select></label>
    <div class="spell-rule-grid"><div><span class="spell-rule-label">Casting time</span><strong>${E(spell.casting_time || (spell.full_turn ? 'Full turn' : spell.bonus ? 'Bonus action' : 'Action'))}</strong></div><div><span class="spell-rule-label">Range</span><strong>${E(spell.range)} ft${spell.radius ? ` · ${E(spell.radius)} ft radius` : ''}</strong></div><div><span class="spell-rule-label">Resolution</span><strong>${E(spell.method || 'Host validated')}</strong></div><div><span class="spell-rule-label">Components</span><strong>${E(spell.components || 'V, S')}</strong></div></div>
    <p class="spell-description">${E(spell.description || '')}</p>
    ${spell.warning ? `<p class="spell-warning">${E(spell.warning)}</p>` : ''}${spell.resolution === 'record_only' ? '<p class="notice">This working is legal to prepare, but its deeper world interaction still requires adjudication. The host will not invent an outcome.</p>' : ''}
    ${noTargets ? '' : `<label>Target<select name="target">${spell.operation === 'utility' ? '<option value="">No target</option>' : ''}${choices.filter(row => row.hp > 0).map(row => `<option value="${E(row.id)}">${E(row.name)}</option>`).join('')}</select></label>`}
    ${grid ? `<fieldset><legend>${spell.radius ? 'Area center (can include allies)' : 'Destination'} in feet</legend>${['x','y','z'].map((axis,i) => `<label>${axis.toUpperCase()}<input name="${axis}" type="number" min="0" max="120" step="5" value="${origin[i]}" required></label>`).join('')}</fieldset>` : ''}
    ${spell.operation === 'gate' ? '<label>Destination plane<input name="plane" required></label><label>Named creature (optional)<input name="named_creature"></label>' : ''}
    ${spell.operation === 'imprisonment' ? '<label>Mode<select name="mode"><option>burial</option><option>chaining</option><option>hedged prison</option><option>minimus containment</option><option>slumber</option><option>thralldom</option></select></label>' : ''}
    ${spell.operation === 'niv_descent' ? '<label><input name="dive" type="checkbox" required> Commit an intentional dive</label>' : ''}
    <fieldset class="metamagic-panel"><legend>Metamagic modifications</legend><p class="notice">Each modification increases focus strain or action tax. The host performs the final legality check.</p><div class="metamagic-grid">${legalMeta.map(([id,label,desc,cost]) => `<label class="metamagic-option"><input type="checkbox" name="metamagic" value="${id}"><span><strong>${label}</strong><small>${desc}</small><em>${cost}</em></span></label>`).join('')}</div></fieldset>
    <div class="spell-commit"><div><span class="spell-rule-label">Commitment</span><strong>${spell.concentration ? 'Requires concentration' : 'No concentration listed'}${spell.duration ? ` · ${E(spell.duration)} rounds` : ''}</strong></div><div class="actions"><button class="action" type="submit">Preview and cast</button>${button('Cancel', 'cancel-spell-picker', 'secondary')}</div></div>
  </form></section>`;
}
function resourceSheet(row) {
  if (!row?.id) return '';
  const pools = Object.entries(row.resources || {}).filter(([key]) => !key.startsWith('slot_'));
  const slots = Object.entries(row.resources || {}).filter(([key]) => key.startsWith('slot_'));
  const values = entries => entries.map(([key,n]) => `<span><b>${E(key.replaceAll('_',' '))}</b> ${E(n)}</span>`).join('');
  return `<details class="turn-panel" open><summary>${E(row.name)} · resources and skills</summary>
    <div class="turn-stats">${row.spell_save_dc == null ? '' : `<span>Spell save DC <b>${E(row.spell_save_dc)}</b></span><span>Spell attack <b>+${E(row.spell_attack_bonus)}</b></span>`}${values(pools)}</div>
    ${slots.length ? `<details><summary>Spell slots by level</summary><div class="turn-stats">${values(slots)}</div></details>` : ''}
    <div class="turn-stats">${values(Object.entries(row.skill_bonuses || {}).map(([key,n]) => [key, Number(n) >= 0 ? `+${n}` : n]))}</div>
  </details>`;
}
function savePreferences() {
  try { localStorage.setItem(preferenceKey, JSON.stringify(state.preferences)); } catch (error) { state.note = `Preferences could not be saved: ${error.message}`; }
  applyPreferences();
}
// --- Fixed-ratio stage --------------------------------------------------
// The creator is authored at ONE logical size and scaled to the window, so
// "everything fits on one screen" is proved once rather than per breakpoint.
// Below STAGE_MIN_WIDTH the zoom stops being readable and the stage bows out.
const STAGE_MIN_WIDTH = 900;
const STAGE_ASPECTS = {'2.28:1': 2.28, '2:1': 2, '16:9': 16 / 9, '21:9': 21 / 9, fill: 0};
// The scarce axis is HEIGHT, so that is what the resolution setting names.
// A bigger number means more logical pixels down, so more content fits and the
// whole stage is scaled down further -- it is a zoom control, not a fit gamble.
const STAGE_HEIGHTS = {auto: 0, compact: 820, standard: 900, roomy: 1000, max: 1120};
// The layout is authored against this; below it the fixed rows stop fitting.
const STAGE_MIN_HEIGHT = 820;
// How much of the window the stage leaves as the surrounding style margin.
const STAGE_MARGIN = 32;

function stageGeometry() {
  const p = state.preferences;
  const availW = Math.max(320, innerWidth - STAGE_MARGIN * 2);
  const availH = Math.max(240, innerHeight - STAGE_MARGIN * 2);
  // 'fill' means: take the window's own shape, so nothing is letterboxed.
  const ratio = p.stageAspect === 'fill' ? availW / availH : (STAGE_ASPECTS[p.stageAspect] || 2);
  // Height is the constant the pages are tuned against and is never allowed
  // below STAGE_MIN_HEIGHT -- that is what stops "does it fit?" from depending
  // on the window again. The aspect only ever widens the stage.
  const height = Math.max(STAGE_MIN_HEIGHT, STAGE_HEIGHTS[p.stageResolution] || 900);
  const width = Math.round(height * ratio);
  const scale = Math.min(availW / width, availH / height);
  return {width, height, scale, ratio};
}
function stageEnabled() {
  return state.preferences.stageMode !== 'off' && innerWidth > STAGE_MIN_WIDTH;
}
function applyStageGeometry() {
  const root = document.documentElement;
  if (!document.querySelector('.hsr-stage') || !stageEnabled()) {
    root.style.removeProperty('--stage-scale');
    document.body.dataset.stage = 'off';
    return;
  }
  document.body.dataset.stage = 'on';
  const g = stageGeometry();
  root.style.setProperty('--stage-w', g.width);
  root.style.setProperty('--stage-h', g.height);
  root.style.setProperty('--stage-scale', g.scale.toFixed(4));
}
// A scaled stage has to be re-measured on every resize; nothing else does.
let stageResizeTimer = 0;
addEventListener('resize', () => {
  clearTimeout(stageResizeTimer);
  stageResizeTimer = setTimeout(applyStageGeometry, 60);
});

// --- In-stage overlays --------------------------------------------------
// Dense sub-choices (pick N skills, a wardrobe group, the receipt) live over
// the stage instead of lengthening it. They render inside .hsr-stage so they
// scale with it; a native <dialog> would sit in the top layer at 1:1.
function openOverlay(kind, arg = '') {
  state.overlay = {kind, arg};
  render();
}
function closeOverlay() {
  if (!state.overlay) return false;
  state.overlay = null;
  render();
  return true;
}
function overlayShell({title, lede, body, foot = '', wide = false}) {
  return `<div class="cc-overlay" data-overlay-root role="dialog" aria-modal="true" aria-label="${E(title)}">
    <div class="cc-overlay-card${wide ? ' wide' : ''}">
      <header class="cc-overlay-head"><div><p class="eyebrow">Choose</p><h3>${E(title)}</h3>${lede ? `<p>${E(lede)}</p>` : ''}</div>
        <button type="button" class="cc-overlay-close" data-action="overlay-close" aria-label="Close">×</button></header>
      <div class="cc-overlay-body">${body}</div>
      <footer class="cc-overlay-foot">${foot}<button type="button" class="action primary" data-action="overlay-close">Done</button></footer>
    </div></div>`;
}
function opener({action, label, value, hint, ariaLabel}) {
  return `<button type="button" class="cc-opener" data-action="${E(action)}" aria-label="${E(ariaLabel || label)}">
    <strong>${E(label)}</strong><span class="cc-opener-value">${E(value)}</span>${hint ? `<small>${E(hint)}</small>` : ''}</button>`;
}

function applyPreferences() {
  document.body.classList.toggle('icon-actions', state.preferences.iconActions);
  document.body.classList.toggle('compact-menu', state.preferences.menuDensity === 'compact');
  document.body.classList.toggle('reduced-motion', state.preferences.motion === 'reduced');
  document.body.classList.toggle('soft-effects', state.preferences.effects === 'soft');
  document.body.dataset.colorblind = state.preferences.colorblind === 'on' ? 'on' : 'off';
  audio?.setVolumes();
  document.body.dataset.layout = state.preferences.layout;
  document.body.dataset.density = state.preferences.menuDensity;
  document.body.dataset.sceneScale = state.preferences.sceneScale;
  document.body.dataset.dock = state.preferences.dockPosition;
  // Party is only ever a public-facing surface once there is an actual party
  // (companions today, hosted/multi-PC runs later) -- solo play never shows an
  // empty-looking rail for one adventurer. Debug/Simulation/Nerdy Mode exposes
  // the old manual "showParty" checkbox as a full override for testing.
  document.body.dataset.party = state.preferences.debugMode ? (state.preferences.showParty ? 'shown' : 'hidden') : (party().length > 1 ? 'shown' : 'hidden');
  document.body.dataset.navigation = state.preferences.showNavigation ? 'shown' : 'hidden';
  document.body.dataset.workspace = state.preferences.showWorkspace === false ? 'hidden' : 'shown';
  document.body.dataset.accent = state.preferences.accent;
  document.documentElement.style.setProperty('--text-scale', state.preferences.textScale);
  document.body.dataset.stage = stageEnabled() ? 'on' : 'off';
  document.body.dataset.stageAspect = state.preferences.stageAspect;
}
function readAccountIdentity() {
  try {
    let id = localStorage.getItem('hsr-account-identity');
    if (!id) id = `hsr:local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    else if (!/^(?:custom|divine|hsr):[A-Za-z0-9 _-]+$/.test(id)) id = `hsr:${id.replace(/[^A-Za-z0-9 _-]/g, '-').slice(0, 60) || 'local-player'}`;
    localStorage.setItem('hsr-account-identity', id);
    return id;
  } catch { return 'hsr:local-player'; }
}
function championRoster() {
  return Array.isArray(state.options?.champions) ? state.options.champions : [];
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
  // Attunement Matrix capacity (host: progression.UPGRADES / meta_shop).
  prefix_capacity: {cap: 5, base_cost: 3, effect: '+1 decanted Prefix attunement slot per tier'},
  suffix_capacity: {cap: 5, base_cost: 3, effect: '+1 decanted Suffix attunement slot per tier'},
  legendary_capacity: {cap: 5, base_cost: 4, effect: '+1 decanted Legendary attunement slot per tier'},
};
const CONVERSATION_MODES = [
  {mode: 'ask', label: 'Ask'}, {mode: 'lie', label: 'Lie'},
  {mode: 'threaten', label: 'Threaten'}, {mode: 'insult', label: 'Insult'},
  {mode: 'trade', label: 'Trade'},
];
const state = {
  phase: 'title', route: ['title'], transport: 'local-gateway', client: createHSRClient({onTrace: (...a) => hostTrace(...a)}), view: null, receipt: null,
  runId: null, runs: [], runsFilter: null, debugReadout: null, options: null, draft: {name: '', race: 'human', gender: 'female',
  character_class: 'warrior', background: 'veteran', creation_seed: '', level: 1, roll_set: 0,
  ability_assignment: 'auto', floating_bonuses: 'auto', advancements: 'auto', advancement_mode: 'auto',
  skills: 'auto', skill_mode: 'auto', spells: 'auto', spell_mode: 'auto', spell_budget: 0}, preview: null,
  roll: null, live: null, liveError: '', stepAnim: '', rollAnim: false, overlay: null,
  affixes: null, catalog: null, scenarios: null, vocabulary: null, preferences: readPreferences(),
  selected: screens.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'room',
  selectedActor: null,
  busy: false, connected: false, note: '', error: '', refreshed: null, initialized: false, activity: {label: 'Idle', started: 0, requests: 0, line: 'Awaiting a request; the reliquary is pretending to be patient.'}, requestKeys: new Set(),
  pendingMode: 'DESIGN', pendingLead: null, accountIdentity: readAccountIdentity(), progression: null, star: null, metaShop: null, story: null, finalizedRuns: new Set(), terminal: null,
  statisticsMode: null, statistics: null, statisticsView: 'menu', statisticsDetail: null,
  pendingConversation: null, consoleDraft: '', actionPicker: null, presentation: null,
  arcadeUi: null, staleSandbox: null, lastManeuver: null, trayState: 'compact', arrangeMode: false, playHeaderOpen: false,
  workspaceLayout: readWorkspaceLayout(), dragSequence: 0,
  messageHistory: [], messageHistoryOpen: false, messagePanelTab: 'messages', debugFilter: 'issues', consoleHistory: [], consoleCursor: -1,
  optionsReturnScreen: 'room', contextMenu: null, tapHint: null, systemMenuOpen: false,
  clockTick: 0, focusTarget: null, lastRunSeed: '',
  bookbagOpen: false, bookbagTab: 'all', bookbagSelectedItem: null,
  link: {status: 'checking', rtt: null, offset: 0, lastBeat: 0, lastRequestMs: null, open: false, compact: false, history: []},
  dismissedDisconnect: false,
};
state.dragSequence = Math.max(0, ...Object.values(state.workspaceLayout).map(row => Number(row?.z) || 0));
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
const SCREEN_ICONS = {journey: '✦', room: '⌂', battle: '⚔', equipment: '◇', roster: '♙', residents: '☵', journal: '▤', map: '◎', library: '⌘', options: '⚙'};
function routeTitle() {
  if (state.phase === 'ready') return gameplayLabels[state.selected] || 'Reliquary';
  const labels = {transport:'Gateway', 'menu-story':'Story Mode', 'menu-simulation':'Simulation Mode', 'party-select':'Choose Lead', 'champion-select':'Champions', create:'Character Workshop', preview:'Character Preview', 'entry-select':'Starting Entry', runs:'Continue', statistics:'Statistics', 'edit-scenario':'Edit Scenario', cheats:'Cheats', toolbox:'Actor Toolbox', options:'Options'};
  return labels[state.phase] || 'Hollow Star';
}
function topNavigation() {
  if (state.phase === 'title') return '';
  if (state.phase === 'ready') {
    const tabs = screens.map(tab => `<button type="button" role="tab" class="global-nav-tab ${state.selected === tab ? 'active' : ''}" data-action="tab:${E(tab)}" aria-selected="${state.selected === tab}" aria-controls="screen-${E(tab)}" title="${E(gameplayLabels[tab])}"><span class="nav-tab-icon" aria-hidden="true">${SCREEN_ICONS[tab] || '•'}</span><small class="nav-tab-label">${E(gameplayLabels[tab])}</small></button>`).join('');
    return `<nav class="mobile-topbar global-screen-nav" role="tablist" aria-label="Screen navigation">
      <div class="top-nav-brand"><button type="button" class="top-nav-brand-btn" data-action="toggle-system-menu" title="Open Game Menu (Esc)"><span class="top-nav-sigil" aria-hidden="true">✦</span><strong class="top-nav-title">Reliquary</strong></button><small class="top-nav-screen">${E(gameplayLabels[state.selected] || state.selected)}</small></div>
      <div class="top-nav-tabs">${tabs}</div>
      <div class="top-nav-status">${bookbagHudButton()}${workspaceStatusLine()}<button type="button" class="action secondary top-nav-menu-btn" data-action="toggle-system-menu" title="Game System Menu (Esc)">Menu ⚙</button></div>
    </nav>`;
  }
  return `<nav class="mobile-topbar" aria-label="Page navigation">
    <div class="top-nav-left"><button type="button" class="topbar-button action secondary" data-action="back" aria-label="Go back">‹ <span>Back</span></button></div>
    <div class="top-nav-center"><strong>${E(routeTitle())}</strong></div>
    <div class="top-nav-right"><button type="button" class="topbar-button action secondary" data-action="title" aria-label="Main menu"><span>Title</span> ⌂</button></div>
  </nav>`;
}
const pad2 = n => String(n).padStart(2, '0');
function clockText(date) {
  const link = state.preferences.link;
  let hours = date.getHours(); let suffix = '';
  if (!link.clock24h) { suffix = hours >= 12 ? ' PM' : ' AM'; hours = hours % 12 || 12; }
  return `${link.clock24h ? pad2(hours) : hours}:${pad2(date.getMinutes())}${link.seconds ? `:${pad2(date.getSeconds())}` : ''}${suffix}`;
}
function latencyTone(rtt) {
  const link = state.preferences.link;
  if (rtt == null) return 'none';
  return rtt >= link.badMs ? 'bad' : rtt >= link.warnMs ? 'warn' : 'good';
}
// Latency history as an inline SVG polyline; threshold lines drawn dashed.
function latencySparkline() {
  const samples = state.link.history || [];
  if (samples.length < 2) return '<p class="conn-spark-empty">Collecting samples…</p>';
  const w = 220; const h = 44; const link = state.preferences.link;
  const top = Math.max(link.badMs * 1.1, ...samples.map(v => v ?? 0));
  const x = i => (i / (samples.length - 1)) * w;
  const y = v => h - (Math.min(v, top) / top) * h;
  const points = samples.map((v, i) => (v == null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`)).filter(Boolean).join(' ');
  const valid = samples.filter(v => v != null);
  const sorted = [...valid].sort((a, b) => a - b);
  const pct = q => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))];
  const mean = valid.reduce((a, b) => a + b, 0) / (valid.length || 1);
  const jitter = valid.length > 1 ? valid.slice(1).reduce((sum, v, i) => sum + Math.abs(v - valid[i]), 0) / (valid.length - 1) : 0;
  const lost = samples.length - valid.length;
  return `<svg class="conn-spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" role="img" aria-label="Latency history, ${samples.length} samples">
      <line x1="0" x2="${w}" y1="${y(link.warnMs).toFixed(1)}" y2="${y(link.warnMs).toFixed(1)}" class="spark-warn"/>
      <line x1="0" x2="${w}" y1="${y(link.badMs).toFixed(1)}" y2="${y(link.badMs).toFixed(1)}" class="spark-bad"/>
      <polyline points="${points}" class="spark-line"/></svg>
    <p class="conn-spark-stats">n=${valid.length} · min ${Math.round(sorted[0] ?? 0)} · p50 ${Math.round(pct(.5) ?? 0)} · p95 ${Math.round(pct(.95) ?? 0)} · mean ${Math.round(mean)} · jitter ${Math.round(jitter)} ms${lost ? ` · ${lost} lost` : ''}</p>`;
}
const LINK_LABELS = {online: 'Connected', offline: 'Disconnected', checking: 'Checking…'};
function linkReadout() {
  const link = state.link; const now = Date.now();
  const ms = v => v == null ? '—' : `${Math.round(v)} ms`;
  const age = link.lastBeat ? `${Math.max(0, Math.round((now - link.lastBeat) / 1000))}s ago` : '—';
  return {
    status: LINK_LABELS[link.status] || link.status,
    menuStatus: link.status === 'online' ? '' : ` · ${LINK_LABELS[link.status] || link.status}`,
    host: link.status === 'offline' && !link.lastBeat ? '—' : clockText(new Date(now + link.offset)),
    local: clockText(new Date(now)),
    latency: ms(link.rtt), request: ms(link.lastRequestMs), beat: age,
    drift: link.lastBeat ? `${link.offset >= 0 ? '+' : ''}${Math.round(link.offset)} ms` : '—',
  };
}
// Connections + Information + Clock used to be three independent floating
// panels. They're one condensed line inside the Workspace card now: dot,
// status, latency, and the local clock, always visible. Debug/Simulation/
// Nerdy Mode turns the line into a disclosure revealing everything the old
// Information panel showed (host time, request, last beat, drift, sparkline).
// Satisfies the same DOM contract refreshLinkReadout() reads from: a
// conn-online|offline|checking class on the root, data-link nodes, a
// .tick-pulse[data-tick], and (expanded only) [data-link-spark].
function workspaceStatusLine() {
  const r = linkReadout();
  const debug = state.preferences.debugMode;
  const open = debug && Boolean(state.link.open);
  const summary = `<span class="conn-dot" aria-hidden="true"></span><span class="conn-state" data-link="status">${E(r.status)}</span><span class="conn-latency tone-${E(latencyTone(state.link.rtt))}" data-link="latency">${E(r.latency)}</span><span class="tick-pulse" data-tick="${state.clockTick % 2}" aria-hidden="true">●</span><span class="workspace-clock" data-link="local">${E(r.local)}</span>`;
  const head = debug
    ? `<button type="button" class="conn-summary" data-action="conn-toggle" aria-expanded="${open}">${summary}<span class="conn-caret" aria-hidden="true">${open ? '▲' : '▼'}</span></button>`
    : `<div class="conn-summary conn-summary-static">${summary}</div>`;
  const details = open ? `<div class="conn-details"><dl><dt>Host time</dt><dd data-link="host">${E(r.host)}</dd><dt>Request</dt><dd data-link="request">${E(r.request)}</dd><dt>Last beat</dt><dd data-link="beat">${E(r.beat)}</dd><dt>Drift</dt><dd data-link="drift">${E(r.drift)}</dd></dl><div class="conn-spark-wrap" data-link-spark>${latencySparkline()}</div><div class="conn-actions">${button('Ping now', 'conn-ping', 'secondary')}</div></div>` : '';
  return `<div class="workspace-status-line conn-${E(state.link.status)}" data-workspace-status>${head}${details}</div>`;
}
function refreshLinkReadout() {
  const boxes = document.querySelectorAll('[data-workspace-status]');
  const r = linkReadout();
  document.querySelectorAll('[data-workspace-status] [data-link], .intro-connection [data-link]').forEach(node => { const v = r[node.dataset.link]; if (v !== undefined && node.textContent !== v) node.textContent = v; });
  document.querySelectorAll('.intro-connection .intro-link').forEach(node => { node.classList.remove('link-online', 'link-offline', 'link-checking'); node.classList.add(`link-${state.link.status}`); });
  boxes.forEach(box => { box.className = box.className.replace(/conn-(online|offline|checking)/, `conn-${state.link.status}`); });
  document.querySelectorAll('.tick-pulse').forEach(pulse => pulse.dataset.tick = String(state.clockTick % 2));
  document.querySelectorAll('.conn-latency').forEach(latency => latency.className = `conn-latency tone-${latencyTone(state.link.rtt)}`);
}
let heartbeatInFlight = false;
async function heartbeat() {
  // Skip while a host request is running so pings never queue behind game work.
  if (heartbeatInFlight || state.busy || document.hidden) return;
  // No client, or a ping that throws, means the engine is unreachable: say so
  // rather than leaving the light on "checking" forever.
  if (!state.client?.ping) { state.link.status = 'offline'; state.link.rtt = null; refreshLinkReadout(); return; }
  heartbeatInFlight = true;
  try {
    const beat = await state.client.ping();
    const before = state.link.status;
    state.link.status = beat.ok ? 'online' : 'offline';
    if (before !== state.link.status) {
      debugLog(beat.ok ? 'info' : 'error', 'LINK', `Host link ${before} → ${state.link.status}`, beat.ok ? null : beat.error || null);
      if (beat.ok) state.dismissedDisconnect = false;
      render();
    }
    if (beat.ok) { state.link.rtt = beat.rtt; state.link.offset = beat.offset; state.link.lastBeat = Date.now(); }
    else state.link.rtt = null;
    state.link.history.push(beat.ok ? beat.rtt : null);
    const keep = Math.max(5, Number(state.preferences.link.historySize) || 40);
    if (state.link.history.length > keep) state.link.history.splice(0, state.link.history.length - keep);
    const spark = document.querySelector('[data-link-spark]'); if (spark) spark.innerHTML = latencySparkline();
  } catch {
    const before = state.link.status;
    state.link.status = 'offline'; state.link.rtt = null; state.link.history.push(null);
    if (before !== 'offline') render();
  } finally { heartbeatInFlight = false; refreshLinkReadout(); }
}
function disconnectOverlay() {
  if (state.link.status !== 'offline' || state.dismissedDisconnect) return '';
  return `<div class="disconnect-warning-modal" role="alertdialog" aria-modal="true" aria-labelledby="disconnect-title">
    <div class="disconnect-modal-card">
      <div class="disconnect-icon" aria-hidden="true">⚠</div>
      <div class="disconnect-content">
        <p class="eyebrow" style="color:var(--crimson,#e25555);">Connection Severed</p>
        <h2 id="disconnect-title">Host Gateway Disconnected</h2>
        <p class="disconnect-body-text">The connection to the local Hollow Star engine / server was lost or the hosting window was closed.</p>
        <div class="disconnect-alert-box">
          <strong>Warning:</strong> Nothing is currently being saved to the Reliquary. Any new commands or actions cannot be processed by the engine until the host is reconnected.
        </div>
        <div class="disconnect-actions">
          ${button('Retry Connection', 'conn-retry', 'primary')}
          ${button('Dismiss Warning', 'dismiss-disconnect', 'secondary')}
        </div>
      </div>
    </div>
  </div>`;
}
function mobileNavigation() {
  if (state.phase !== 'ready') return '';
  // Turn-based combat has its own command set and no "back a screen" concept
  // mid-turn, so the generic Back/collapsible-Actions chrome is dropped in
  // favor of the tactical controls, shown inline and already open.
  if (tacticalActive(state.view)) {
    return `<nav class="mobile-game-nav global-action-footer combat-action-footer" aria-label="Combat actions">${actionBar()}</nav>`;
  }
  return `<nav class="mobile-game-nav global-action-footer" aria-label="Screen actions"><button type="button" class="mobile-nav-item" data-action="back" aria-label="Go back"><span aria-hidden="true">‹</span><span>Back</span></button>${actionBar()}</nav>`;
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
const button = (label, action, extra = '') => `<button type="button" class="action ${extra}" data-action="${E(action)}">${E(label)}</button>`;
function navigationState() { return {hsr:true, phase:state.phase, route:[...state.route], selected:state.selected}; }
function clearScreenTransientState() {
  state.titleActive = null;
  state.actionPicker = null;
  state.combatRadial = null;
  state.threatWarning = null;
  state.focusTarget = null;
  state.pendingConversation = null;
  state.consoleDraft = '';
  state.messageHistoryOpen = false;
  state.presentation = null;
  state.note = '';
  state.error = '';
  state.contextMenu = null;
  document.querySelectorAll('#app .combat-float, #app .hsr-context-menu').forEach(node => node.remove());
  document.querySelectorAll('dialog').forEach(dialog => {
    if (dialog.open) dialog.close();
    if (dialog.id === 'item-dialog' || dialog.id === 'examine-dialog') dialog.replaceChildren();
  });
}
function go(phase) {
  if (state.phase === phase) return;
  if (state.phase !== phase) clearScreenTransientState();
  if (state.route[state.route.length - 1] !== phase) state.route.push(phase);
  state.phase = phase;
  if (state.initialized) history.pushState(navigationState(), '', location.href);
}
function back() {
  clearScreenTransientState();
  state.route.pop(); state.phase = state.route[state.route.length - 1] || 'title';
  if (!state.route.length) state.route = ['title'];
  history.replaceState(navigationState(), '', location.href);
}
const BREADCRUMB_PHASES = {'Main Menu': 'title', 'Story Mode': 'menu-story', 'Simulation Mode': 'menu-simulation', 'Gateway': 'transport', 'Choose Lead': 'party-select', 'Starting Entry': 'entry-select'};
function breadcrumb(...crumbs) {
  return `<nav class="breadcrumb" aria-label="Navigation">${crumbs.map((crumb, i) => {
    const label = typeof crumb === 'string' ? crumb : crumb.label;
    const phase = typeof crumb === 'string' ? BREADCRUMB_PHASES[crumb] : crumb.phase;
    if (i === crumbs.length - 1) return `<span aria-current="page">${E(label)}</span>`;
    return phase
      ? `<button type="button" class="breadcrumb-link" data-action="breadcrumb:${E(phase)}">${E(label)}</button>`
      : `<span>${E(label)}</span>`;
  }).join(' <span class="breadcrumb-sep">/</span> ')}</nav>`;
}

function addMessage(text, type = 'note') {
  const timestamp = new Date().toLocaleTimeString();
  state.messageHistory.push({text, type, timestamp});
  if (state.messageHistory.length > 100) state.messageHistory.shift();
}
function fail(message) {
  state.error = message;
  state.note = 'Last displayed public state retained. Refresh before retrying an uncertain action.';
  addMessage(message, 'error');
  debugLog('error', 'UI', message, {phase: state.phase, screen: state.selected, run_id: state.runId});
}
// Debug capture. Everything worth pasting into an AI when something breaks —
// host failures, slow calls, uncaught errors, console errors/warnings, asset
// load failures, link drops — lands here. `/copy` or the panel's "Copy" button
// produces one plain-text block with environment context first.
const DEBUG_LOG = [];
const DEBUG_LIMIT = 400;
const SLOW_HOST_MS = 2500;
const clip = (value, max = 1500) => { let text; try { text = typeof value === 'string' ? value : JSON.stringify(value); } catch { text = String(value); } return text && text.length > max ? `${text.slice(0, max)}… (+${text.length - max} chars)` : text; };
function debugLog(level, source, text, detail = null) {
  DEBUG_LOG.push({time: new Date().toISOString(), level, source, text: String(text ?? ''), detail: detail == null ? null : clip(detail)});
  if (DEBUG_LOG.length > DEBUG_LIMIT) DEBUG_LOG.splice(0, DEBUG_LOG.length - DEBUG_LIMIT);
  try { if (state?.messageHistoryOpen && state.messagePanelTab === 'debug') queueMicrotask(() => { const box = document.querySelector('[data-debug-list]'); if (box) box.innerHTML = debugRows(); }); } catch {}
}
function hostTrace(entry) {
  const label = `${entry.command}${entry.run_id ? ` [${entry.run_id}]` : ''}`;
  if (!entry.ok) debugLog('error', entry.kind === 'get' ? 'GET' : 'HOST', `${label} failed: ${entry.error?.code || 'ERROR'} — ${entry.error?.message || 'no message'}${entry.http ? ` (HTTP ${entry.http})` : ''}${entry.ms != null ? ` in ${entry.ms} ms` : ''}`, {request_id: entry.id, fields: entry.fields, error: entry.error, reply: entry.reply});
  else if (entry.ms > SLOW_HOST_MS) debugLog('warn', 'HOST', `${label} slow: ${entry.ms} ms`, {request_id: entry.id});
  else debugLog('trace', 'HOST', `${label} ok · ${entry.ms} ms`);
  const warnings = entry.reply?.warnings || entry.reply?.result?.warnings;
  if (Array.isArray(warnings) && warnings.length) debugLog('warn', 'HOST', `${label} returned ${warnings.length} warning(s)`, warnings);
}
(() => {
  addEventListener('error', event => {
    const target = event.target;
    if (target && target !== window && (target.src || target.href)) { debugLog('warn', 'ASSET', `Failed to load <${target.tagName?.toLowerCase()}> ${target.src || target.href}`); return; }
    debugLog('error', 'JS', `${event.message || 'Uncaught error'} @ ${event.filename || '?'}:${event.lineno || 0}:${event.colno || 0}`, event.error?.stack || null);
  }, true);
  addEventListener('unhandledrejection', event => { const reason = event.reason; debugLog('error', 'PROMISE', `Unhandled rejection: ${reason?.message || reason}`, reason?.stack || null); });
  addEventListener('securitypolicyviolation', event => debugLog('warn', 'CSP', `${event.violatedDirective} blocked ${event.blockedURI}`));
  addEventListener('offline', () => debugLog('warn', 'NET', 'Browser went offline'));
  addEventListener('online', () => debugLog('info', 'NET', 'Browser back online'));
  for (const level of ['error', 'warn']) {
    const original = console[level].bind(console);
    console[level] = (...args) => { original(...args); debugLog(level, 'CONSOLE', args.map(arg => arg instanceof Error ? arg.message : typeof arg === 'string' ? arg : clip(arg, 400)).join(' '), args.find(arg => arg instanceof Error)?.stack || null); };
  }
})();
function debugRows() {
  const filter = state.debugFilter || 'issues';
  const rows = DEBUG_LOG.filter(row => filter === 'all' || row.level !== 'trace');
  return rows.length ? rows.slice(-150).reverse().map(row => `<div class="message-row debug-${E(row.level)}"><span class="message-timestamp">${E(row.time.slice(11, 19))}</span><span class="message-text"><b>${E(row.level.toUpperCase())} · ${E(row.source)}</b> ${E(row.text)}${row.detail ? `<code class="debug-detail">${E(row.detail)}</code>` : ''}</span></div>`).join('') : '<p class="message-empty">No debug lines captured.</p>';
}
function debugReport({all = false} = {}) {
  const p = state.preferences || {};
  const view = state.view || {};
  const head = [
    '=== HSR DEBUG REPORT ===',
    `generated: ${new Date().toISOString()}`,
    `url: ${location.href}`,
    `userAgent: ${navigator.userAgent}`,
    `viewport: ${innerWidth}x${innerHeight} @${devicePixelRatio}x · online=${navigator.onLine}`,
    `phase: ${state.phase} · route: ${state.route.join(' > ')} · screen: ${state.selected}`,
    `run_id: ${state.runId || '—'} · transport: ${state.transport} · busy: ${state.busy}`,
    `link: ${state.link.status} · rtt ${state.link.rtt == null ? '—' : Math.round(state.link.rtt)} ms · last request ${state.link.lastRequestMs == null ? '—' : Math.round(state.link.lastRequestMs)} ms`,
    `party: ${party().map(m => `${m.name || m.id}(${value(m, 'hp', 'current_hp') ?? '?'}/${value(m, 'max_hp') ?? '?'})`).join(', ') || '—'}`,
    `room: ${view.room?.name || view.room?.id || '—'} · opposition: ${(view.opposition || []).length}`,
    `last error: ${state.error || '—'}`,
    `last command: ${state.consoleHistory[state.consoleHistory.length - 1] || '—'}`,
    `prefs: debugMode=${p.debugMode} stage=${p.stageMode} motion=${p.motion} layout=${p.layout}`,
    `last receipt: ${clip(state.receipt, 800) || '—'}`,
    '',
    `--- log (${all ? 'all incl. every host call' : 'issues + info'}, oldest first) ---`,
  ];
  const lines = DEBUG_LOG.filter(row => all || row.level !== 'trace').map(row => `[${row.time}] ${row.level.toUpperCase()} ${row.source}: ${row.text}${row.detail ? `\n    ${row.detail}` : ''}`);
  const messages = state.messageHistory.slice(-30).map(msg => `[${msg.timestamp}] ${msg.type}: ${msg.text}`);
  return [...head, ...(lines.length ? lines : ['(empty)']), '', '--- recent messages ---', ...(messages.length ? messages : ['(none)']), '=== END ==='].join('\n');
}
async function copyDebugReport(all = false) {
  const text = debugReport({all});
  try { await navigator.clipboard.writeText(text); addMessage(`Debug report copied (${text.length} chars). Paste it into your AI.`, 'note'); }
  catch {
    // Clipboard API blocked (no focus / insecure origin): textarea fallback.
    const area = Object.assign(document.createElement('textarea'), {value: text}); area.style.cssText = 'position:fixed;opacity:0'; document.body.append(area); area.select();
    const ok = document.execCommand?.('copy'); area.remove();
    addMessage(ok ? `Debug report copied (${text.length} chars).` : 'Clipboard blocked — use /report to download it instead.', ok ? 'note' : 'error');
  }
}
function downloadDebugReport() {
  const url = URL.createObjectURL(new Blob([debugReport({all: true})], {type: 'text/plain'}));
  const link = Object.assign(document.createElement('a'), {href: url, download: `hsr-debug-${Date.now()}.txt`}); link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
// Commentary + sound-effect cues the host attaches to an event (Sera, Ember,
// Doran, divine Presence). result() calls this for EVERY engine reply, so
// buttons, typed intents and auto-combat all reach the voice feed. Only the
// reply's own event is read, never the history list; a signature guard stops
// a readout that echoes the last event from replaying it.
const voiceFeed = createVoiceFeed({
  settings: () => state.preferences.voice,
  reducedMotion: () => state.preferences.motion !== 'full' || globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
  locate: id => id ? document.querySelector(`#app [data-stage-actor="${CSS.escape(String(id))}"]`) : null,
});
let lastVoiceSignature = '';
function logVoice(line) {
  if (state.preferences.voice?.log === false) return;
  if (line.register === 'presence') addMessage(`✧ ${line.text}`, 'voice voice-presence');
  else addMessage(`${line.speaker}: “${line.text}”`, `voice voice-${String(line.speaker || '').toLowerCase()}${line.register === 'ambient' ? ' voice-ambient' : ''}${line.register === 'divine' ? ' voice-divine' : ''}${line.register === 'reply' ? ' voice-reply' : ''}`);
}
function surfaceCommentary(reply) {
  const events = [reply?.event, reply?.result?.event, reply?.result?.turn?.event, reply?.result?.turn?.outcome, reply?.result?.outcome, reply?.result?.outcome?.event, reply?.result?.turn?.outcome?.event].filter(item => item && typeof item === 'object');
  const seen = new Set();
  const lines = []; let cue = null;
  for (const event of events) {
    if (event.sfx?.text && !cue) cue = event.sfx;
    for (const line of Array.isArray(event.commentary) ? event.commentary : []) {
      const key = `${line.speaker}:${line.text}`; if (seen.has(key)) continue; seen.add(key); lines.push(line);
    }
  }
  if (!lines.length && !cue) return;
  const signature = JSON.stringify([lines, cue]);
  if (signature === lastVoiceSignature) return;
  lastVoiceSignature = signature;
  if (cue) { voiceFeed.sfx(cue); if (state.preferences.voice?.log !== false && state.preferences.voice?.sfx !== false) addMessage(`*${cue.text}*`, 'sfx'); }
  for (const line of lines) { voiceFeed.speak(line); logVoice(line); }
  debugLog('trace', 'VOICE', `${lines.map(l => l.speaker).join(', ') || 'sfx only'}${cue ? ` · ${cue.text}` : ''}`);
}
// "Doran, …", "@doran …", "talk to Doran …" address a party companion rather
// than the room. Returns true when the line was handled.
const COMPANION_LINE = /^(?:@|talk to\s+|ask\s+|hey\s+)?(doran|wren)\b[\s,:!?-]*(.*)$/i;
async function companionTalk(speaker, text) {
  const reply = await state.client.companionTalk(state.runId, speaker.toLowerCase(), text);
  if (!reply.ok) throw Error(reply.error?.message || 'No answer.');
  const line = reply.result?.reply;
  if (line) { voiceFeed.speak(line); logVoice(line); }
}
async function sendIntent(text) {
  const companion = text.match(COMPANION_LINE);
  const addressed = companion && (/^(@|talk to|ask|hey)/i.test(text) || /^[a-z]+\s*[,:]/i.test(text));
  if (addressed && !party().some(m => String(m.name || '').toLowerCase() === companion[1].toLowerCase())) throw Error(`${companion[1][0].toUpperCase()}${companion[1].slice(1).toLowerCase()} isn't in this party.`);
  if (companion && party().some(m => String(m.name || '').toLowerCase() === companion[1].toLowerCase()) && (/^(@|talk to|ask|hey)/i.test(text) || /^[a-z]+\s*[,:]/i.test(text) || !companion[2])) {
    addMessage(`You: “${companion[2] || '…'}”`, 'input');
    return companionTalk(companion[1], companion[2] || 'hey');
  }
  const social = text.match(/^(talk to|thank)\s+(\S+)(?:\s+(.*))?$/i);
  if (social) {
    const residents = Object.values(state.view?.room?.npcs || {});
    const wanted = social[2].toLowerCase();
    const named = residents.find(row => String(row.name || row.id).toLowerCase() === wanted || String(row.name || '').toLowerCase().split(/\s+/)[0] === wanted)
      || (state.view?.room?.resident && String(state.view.room.resident).toLowerCase() === wanted ? {id: state.view.room.resident} : null);
    if (!named) throw Error(`"${social[2]}" is not visible in the current room.`);
    result(await state.client.designTurn(state.runId, text, {type: 'talk', target: named.id || named.npc_id || named.name, mode: 'speak', text, actor: actor().id || 'p0'}));
  } else result(await state.client.designTurn(state.runId, text));
  await loadReadout(state.runId);
}
// Console command table; `/help` prints it. Lines without a leading "/" still
// go to the host as a natural-language turn. `host: true` runs inside work().
const CONSOLE_COMMANDS = {
  help: {usage: '/help [command|actions]', text: 'List console commands; "/help actions" prints what each engine action does.', run: args => {
    if (args[0] === 'actions') return printActionGuide();
    const one = CONSOLE_COMMANDS[args[0]?.replace(/^\//, '')];
    if (one) return addMessage(`${one.usage} — ${one.text}`, 'note');
    Object.values(CONSOLE_COMMANDS).forEach(cmd => addMessage(`${cmd.usage} — ${cmd.text}`, 'note'));
    addMessage('Anything else goes to the host as an intent. ↑/↓ recall lines; Tab completes /commands.', 'note');
  }},
  clear: {usage: '/clear [debug|all]', text: 'Clear messages (or the debug log, or both).', run: args => { if (args[0] !== 'debug') state.messageHistory = []; if (args[0] === 'debug' || args[0] === 'all') DEBUG_LOG.length = 0; }},
  msgs: {usage: '/msgs', text: 'Open the Messages tab.', run: () => { state.messagePanelTab = 'messages'; }},
  debug: {usage: '/debug [on|off|all]', text: 'Open the Debug tab; on/off toggles Debug Mode; all shows every host call.', run: args => {
    if (args[0] === 'on' || args[0] === 'off') { state.preferences.debugMode = args[0] === 'on'; savePreferences(); applyPreferences(); addMessage(`Debug Mode ${args[0]}.`, 'note'); return; }
    state.debugFilter = args[0] === 'all' ? 'all' : 'issues'; state.messagePanelTab = 'debug';
  }},
  copy: {usage: '/copy [all]', text: 'Copy a debug report (environment + log) for pasting into an AI.', run: args => copyDebugReport(args[0] === 'all')},
  report: {usage: '/report', text: 'Download the full debug report as a .txt file.', run: () => downloadDebugReport()},
  log: {usage: '/log <text>', text: 'Drop your own marker into the debug log ("clicked X, it froze").', run: (args, raw) => { debugLog('info', 'USER', raw || '(mark)'); addMessage('Marked in debug log.', 'note'); }},
  ping: {usage: '/ping', text: 'Ping the host now and print latency.', run: async () => { const beat = await state.client.ping(); addMessage(beat.ok ? `Host online · ${Math.round(beat.rtt)} ms · drift ${Math.round(beat.offset)} ms` : `Host unreachable: ${beat.error || 'no response'}`, beat.ok ? 'note' : 'error'); if (!beat.ok) debugLog('error', 'PING', 'Manual ping failed', beat); }},
  status: {usage: '/status', text: 'Print phase, run, link and party status.', run: () => debugReport().split('\n').slice(5, 14).forEach(line => addMessage(line, 'note'))},
  refresh: {usage: '/refresh', text: 'Reload public state from the host.', host: true, run: () => loadReadout(state.runId)},
  go: {usage: `/go <${screens.join('|')}>`, text: 'Switch screen.', run: args => { if (!screens.includes(args[0])) throw Error(`Unknown screen. Try: ${screens.join(', ')}`); selectGameplayScreen(args[0]); }},
  look: {usage: '/look', text: 'Show the room screen.', run: () => selectGameplayScreen('room')},
  gear: {usage: '/gear', text: 'Show equipment.', run: () => selectGameplayScreen('equipment')},
  options: {usage: '/options', text: 'Open Options.', run: () => selectGameplayScreen('options')},
  party: {usage: '/party', text: 'Print party HP, AC and conditions.', run: () => { if (!party().length) return addMessage('No party loaded.', 'note'); party().forEach(m => addMessage(`${m.name || m.id}: ${value(m, 'hp', 'current_hp') ?? '?'}/${value(m, 'max_hp') ?? '?'} HP · AC ${value(m, 'armor_class', 'ac') ?? '?'}${(m.conditions || []).length ? ` · ${m.conditions.map(c => c.name || c).join(', ')}` : ''}`, 'note')); }},
  foes: {usage: '/foes', text: 'Print visible opposition.', run: () => { const foes = state.view?.opposition || []; if (!foes.length) return addMessage('No visible opposition.', 'note'); foes.forEach(f => addMessage(`${f.name || f.id} (${f.id})${value(f, 'hp', 'current_hp') != null ? ` · ${value(f, 'hp', 'current_hp')}/${value(f, 'max_hp') ?? '?'} HP` : ''}${f.defeated ? ' · defeated' : ''}`, 'note')); }},
  talk: {usage: '/talk <name> [text]', text: 'Speak to a visible resident.', host: true, run: (args, raw) => { const [name, ...rest] = raw.split(/\s+/); if (!name) throw Error('Usage: /talk <name> [text]'); return sendIntent(rest.length ? `talk to ${name} ${rest.join(' ')}` : `talk to ${name}`); }},
  say: {usage: '/say <text>', text: 'Send a line to the host verbatim (even if it starts with "/").', host: true, run: (args, raw) => sendIntent(raw)},
  do: {usage: '/do <type> [key=value …]', text: 'Send a structured action, e.g. /do attack target=m1.', host: true, run: async args => {
    const [type, ...pairs] = args; if (!type) throw Error('Usage: /do <type> [key=value …]');
    // key=value pairs; a value runs until the next key= so "spell=Spirit Guardians@5e" stays whole.
    const action = {type, actor: actor().id || 'p0'};
    for (const [, k, v] of pairs.join(' ').matchAll(/(\w+)=(.*?)(?=\s+\w+=|$)/g)) action[k] = v.trim() || true;
    result(await state.client.designTurn(state.runId, `${type} ${pairs.join(' ')}`.trim(), action)); await loadReadout(state.runId);
  }},
  raw: {usage: '/raw <command> [json]', text: 'Send a raw host command; the reply goes to the Debug tab.', host: true, run: async (args, raw) => {
    const [command, ...rest] = raw.split(/\s+/); if (!command) throw Error('Usage: /raw <command> [json]');
    const fields = rest.length ? JSON.parse(rest.join(' ')) : {}; if (state.runId && !('run_id' in fields)) fields.run_id = state.runId;
    const reply = await state.client.request(command, fields, {dedupeKey: `raw:${Date.now()}`});
    addMessage(`${command} → ${reply.ok ? 'ok (see Debug tab)' : `${reply.error?.code}: ${reply.error?.message}`}`, reply.ok ? 'note' : 'error');
    debugLog('info', 'RAW', `${command} reply`, reply.result ?? reply.error);
  }},
  again: {usage: '/again', text: 'Repeat the last non-slash line.', host: true, run: () => { const last = [...state.consoleHistory].reverse().find(line => !line.startsWith('/')); if (!last) throw Error('Nothing to repeat.'); return sendIntent(last); }},
  history: {usage: '/history', text: 'Print the last 15 console lines.', run: () => state.consoleHistory.slice(-15).forEach((line, i) => addMessage(`${i + 1}. ${line}`, 'note'))},
  sfx: {usage: '/sfx [on|off]', text: 'Show or hide sound-effect bursts (KRAK!, clink-clink…).', run: args => { const v = state.preferences.voice; v.sfx = args[0] ? args[0] !== 'off' : !v.sfx; savePreferences(); addMessage(`Sound effects ${v.sfx ? 'on' : 'off'}.`, 'note'); }},
  voices: {usage: '/voices [on|off|demo]', text: 'Show or hide voice cards; "demo" previews them.', run: args => { const v = state.preferences.voice; if (args[0] === 'demo') return voiceFeed.demo(); v.cards = args[0] ? args[0] !== 'off' : !v.cards; savePreferences(); addMessage(`Voice cards ${v.cards ? 'on' : 'off'}.`, 'note'); }},
  doran: {usage: '/doran <text>', text: 'Say something to Doran (also: "Doran, …" or "@doran …").', host: true, run: (args, raw) => { addMessage(`You: “${raw || '…'}”`, 'input'); return companionTalk('doran', raw || 'hey'); }},
  cancel: {usage: '/cancel', text: 'Cancel a pending conversation reply.', run: () => { state.pendingConversation = null; addMessage('Conversation cancelled.', 'note'); }},
  time: {usage: '/time', text: 'Print local and host clock.', run: () => { const r = linkReadout(); addMessage(`Local ${r.local} · Host ${r.host} · drift ${r.drift}`, 'note'); }},
};
const ACTIVITY_LINES = FLAVOR.activity;
// The Messages/Debug log, as parts: the console embeds them when expanded,
// and the standalone popup uses them when no run (so no console) exists.
function messageLog() {
  const tab = state.messagePanelTab === 'debug' ? 'debug' : 'messages';
  const issues = DEBUG_LOG.filter(row => row.level === 'error' || row.level === 'warn').length;
  const historyHtml = state.messageHistory.length ? state.messageHistory.map(msg => `<div class="message-row ${E(msg.type)}"><span class="message-timestamp">${E(msg.timestamp)}</span><span class="message-text">${E(msg.text)}</span></div>`).join('') : '<p class="message-empty">No messages yet. Type /help in the command bar.</p>';
  const tabs = `<span class="message-tabs" role="group" aria-label="Log view"><button type="button" data-action="messages-tab:messages" aria-pressed="${tab === 'messages'}">Messages</button><button type="button" data-action="messages-tab:debug" aria-pressed="${tab === 'debug'}">Debug${issues ? ` (${issues})` : ''}</button></span>`;
  const tools = tab === 'debug'
    ? `<button type="button" data-action="debug-copy" aria-label="Copy debug report for AI">Copy</button><button type="button" data-action="debug-download" aria-label="Download debug report">Save</button><button type="button" data-action="debug-filter">${state.debugFilter === 'all' ? 'Issues' : 'All'}</button><button type="button" data-action="debug-clear" aria-label="Clear debug log">Clear</button>`
    : `<button type="button" data-action="clear-messages" class="secondary" aria-label="Clear history">Clear</button>`;
  const history = `<div class="message-history" ${tab === 'debug' ? 'data-debug-list' : ''}>${tab === 'debug' ? debugRows() : historyHtml}</div>`;
  return {tabs, tools, history};
}
function messagePanel() {
  const log = messageLog();
  return `<div class="hsr-message-panel" data-panel="messages"><div class="panel-header"><strong>${log.tabs}</strong>${log.tools}<button type="button" data-action="close-messages" aria-label="Close panel">×</button></div>${log.history}</div>`;
}
// The console floats over the play surface. Collapsed it is one slim row;
// expanded it grows a header (caption, log tabs, log tools) and the log itself
// above the input. It moves by its grip or header like any workspace panel,
// resizes from its edges, and both persist in workspaceLayout.console.
const CONSOLE_EDGES = ['n', 'e', 'w', 'ne', 'nw'];
function consoleSizeStyle() {
  const row = state.workspaceLayout.console || {};
  const width = Number(row.width), height = Number(row.height);
  return `${width > 0 ? `--console-w:${width}px;` : ''}${height > 0 ? `--console-h:${height}px;` : ''}`;
}
function consoleBar() {
  if (!state.runId || state.phase !== 'ready') return '';
  const open = Boolean(state.messageHistoryOpen);
  if (state.consoleCompact) return `<button type="button" class="console-compact" data-action="toggle-console-compact" aria-label="Expand host command line">Host ›</button>`;
  const talk = state.pendingConversation;
  const caption = talk ? `Replying to ${talk.npc} · ${talk.mode}` : 'Command or chat line to the host';
  const log = open ? messageLog() : null;
  const toggle = `<button type="button" class="console-toggle" data-action="toggle-messages" aria-expanded="${open}" aria-controls="console-log" aria-label="${open ? 'Collapse the message log' : 'Expand the message log'}"><span>${open ? 'Hide log' : 'Log'}</span><i aria-hidden="true">${open ? '▾' : '▴'}</i></button>`;
  const head = open ? `<div class="console-head"><strong class="console-caption">${E(caption)}</strong>${log.tabs}<span class="console-head-tools">${log.tools}</span></div><div class="console-log" id="console-log" role="log" aria-live="polite">${log.history}</div>` : '';
  const chip = talk && !open ? `<span class="console-chip" title="${E(caption)}">${E(talk.npc)}</span>` : '';
  return `<form id="console-form" class="hsr-console hsr-command-bar is-input ${open ? 'is-expanded' : 'is-collapsed'}" data-panel="console" style="${consoleSizeStyle()}">
    ${CONSOLE_EDGES.map(edge => `<span class="console-resize console-resize-${edge}" data-console-resize="${edge}" aria-hidden="true"></span>`).join('')}
    ${head}<button type="button" class="console-minimize" data-action="toggle-console-compact" aria-label="Collapse host command line">‹</button><div class="actions console-row">${chip}<input id="console-input" name="console" required autocomplete="off" aria-label="${E(caption)}" placeholder="${talk ? `Reply to ${E(talk.npc)}…` : 'Inspect the room…'}" value="${E(state.consoleDraft || '')}"><button class="action primary">Send</button>${talk ? button('Cancel', 'cancel-conversation', 'secondary') : ''}${toggle}</div>
  </form>`;
}
// Edge resizing for the floating console. The console is anchored by its
// bottom-left corner, so east/north edges simply grow it; the west edge grows
// it leftwards by moving the drag offset by the same amount. Height only
// applies while the log is open -- collapsed, the console is one row tall.
function bindConsole() {
  const panel = document.querySelector('#app > .hsr-command-bar');
  if (!panel || matchMedia('(max-width: 720px)').matches) return;
  const limits = {width: 380, height: 220, gutter: 8};
  const box = panel.getBoundingClientRect();
  // A window resize can strand a moved console off screen; bring it home.
  if (box.right < 80 || box.left > innerWidth - 80 || box.top > innerHeight - 40 || box.bottom < 40) {
    const {x, y, ...rest} = state.workspaceLayout.console || {};
    state.workspaceLayout.console = rest;
    applyDragOffset(panel, 'console');
  }
  panel.querySelectorAll('[data-console-resize]').forEach(edge => {
    edge.onpointerdown = event => {
      if (event.button !== 0) return;
      event.preventDefault(); event.stopPropagation();
      const dir = edge.dataset.consoleResize;
      const start = {x: event.clientX, y: event.clientY, box: panel.getBoundingClientRect()};
      const saved = {...(state.workspaceLayout.console || {})};
      const expanded = panel.classList.contains('is-expanded');
      const clamp = (value, low, high) => Math.round(Math.max(low, Math.min(high, value)));
      try { edge.setPointerCapture(event.pointerId); } catch {}
      panel.classList.add('is-resizing');
      edge.onpointermove = move => {
        const dx = move.clientX - start.x, dy = move.clientY - start.y;
        const next = {...saved};
        if (dir.includes('e')) next.width = clamp(start.box.width + dx, limits.width, innerWidth - start.box.left - limits.gutter);
        if (dir.includes('w')) {
          next.width = clamp(start.box.width - dx, limits.width, start.box.right - limits.gutter);
          next.x = Math.round((Number(saved.x) || 0) + (start.box.width - next.width));
        }
        if (dir.includes('n') && expanded) next.height = clamp(start.box.height - dy, limits.height, start.box.bottom - 64);
        state.workspaceLayout.console = next;
        if (next.width) panel.style.setProperty('--console-w', `${next.width}px`);
        if (next.height) panel.style.setProperty('--console-h', `${next.height}px`);
        applyDragOffset(panel, 'console');
      };
      edge.onpointerup = edge.onpointercancel = up => {
        if (edge.hasPointerCapture(up.pointerId)) edge.releasePointerCapture(up.pointerId);
        edge.onpointermove = edge.onpointerup = edge.onpointercancel = null;
        panel.classList.remove('is-resizing');
        saveWorkspaceLayout();
      };
    };
  });
}
// Plays each new host receipt on the battle stage in order. When the queue
// drains, one render brings any figure it skipped back in step with the host.
const battleWounds = createWoundLayer({getStage: () => document.querySelector('#app .combat-stage:not(.demo-stage)'), enabled: () => state.preferences.combat.wounds !== false, reducedMotion: () => state.preferences.motion !== 'full'});
const combatDirector = createCombatDirector({
  onImpact: info => battleWounds.add(info),
  getStage: () => document.querySelector('#app .combat-stage'),
  reducedMotion: () => state.preferences.motion !== 'full' || globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
  onIdle: () => { state.combatPlacement = null; if (!state.busy) render(); },
  settings: () => state.preferences.combat,
  onBeat: history => refreshCombatInspector(history),
  placeFigure: (node, position) => {
    // Flight actors use the arena's own x/y projection; the render after the
    // queue drains moves them, and their left/top transition animates it.
    if (node.classList.contains('flight-actor') || node.closest('.ff-stage')) return;
    const id = node.dataset.stageActor;
    const fighters = [...party(), ...(state.view?.opposition || [])];
    const moving = state.combatPlacement = {...(state.combatPlacement || {}), [id]: position};
    const style = stageLayout(fighters, moving).get(id);
    if (!style) return;
    const [left, bottom] = style.split(';');
    node.style.left = left.split(':')[1]; node.style.bottom = bottom.split(':')[1];
  },
});
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
    announceDescent(previousView?.descent, state.view?.descent);
    recordSightings(state.view);
    // A Turn 0 cascade resolves before initiative; say so once, in the log.
    const turnZero = state.view?.combat?.turn_zero;
    if (Array.isArray(turnZero) && turnZero.length && !(previousView?.combat?.turn_zero || []).length) {
      for (const row of turnZero) addMessage(`Turn 0 · ${row.tell || String(row.type || 'effect').replaceAll('_', ' ')}${row.defeated?.length ? ` (${row.defeated.length} fell before initiative)` : ''}`, 'note');
    }
    // Enemy turns and NPC reactions the host played inside this one step.
    const steps = reply.result?.receipts || reply.result?.turn?.receipts || [];
    const npcSteps = steps.some(row => { const who = row?.presentation?.actor_id || row?.actor || row?.source; return who && !playerControlled(who, state.view); });
    combatDirector.ingest(previousView, state.view, steps, {banner: npcSteps && playerControlled(previousView?.combat?.current, previousView) ? 'Opposition phase' : ''});
    announceTurnChange(previousView, state.view, {opposed: npcSteps});
    surfaceCommentary(reply);
    if (state.focusTarget && !livingOpponents().some(row => row.id === state.focusTarget)) state.focusTarget = null;
  }
  return reply;
}
// Most host calls answer in tens of milliseconds. Rebuilding the screen just to
// show "busy" and again to clear it is what made quick actions flicker, so the
// screen is only locked in place while a request runs: controls stop taking
// input without repainting. The activity toast appears only when a request is
// slow enough to notice (ACTIVITY_REVEAL_MS); one render lands the result.
const ACTIVITY_REVEAL_MS = 320;
function lockControls(locked) {
  const app = document.querySelector('#app');
  if (!app) return;
  app.toggleAttribute('aria-busy', locked);
  app.querySelectorAll('button,input,select,textarea').forEach(node => { node.disabled = locked || node.dataset.locked === 'true'; });
}
async function work(fn, label = 'Working', line = '') {
  if (state.busy) return;
  state.busy = true; state.error = ''; state.activity = {label, started: performance.now(), requests: 1, visible: false, line: line || ACTIVITY_LINES[Math.floor(Date.now()/1800) % ACTIVITY_LINES.length]};
  lockControls(true);
  // No on-screen toast: a slow request is noted in the Debug log instead, so menus never flash.
  const reveal = setTimeout(() => { if (state.busy) debugLog('trace', 'ACTIVITY', `${state.activity.label} — ${state.activity.line}`); }, ACTIVITY_REVEAL_MS);
  try {
    await fn();
  } catch (error) { fail(error.message); }
  finally {
    clearTimeout(reveal);
    state.link.lastRequestMs = performance.now() - state.activity.started;
    state.busy = false; state.activity = {...state.activity, requests: 0, visible: false, label: 'Ready'};
    lockControls(false); render();
    scheduleNpcDrain();
  }
}
// ---- Autonomous opposition ---------------------------------------------------
// When the host hands the turn (or a reaction window) to an AI-controlled
// combatant, the client asks it to play those steps itself (design_drain_npc)
// instead of waiting on an "Advance NPC turn" click. The host stops at the
// first player decision; each step's receipt queues on the combat director.
function playerControlled(id, view = state.view) {
  if (!id) return false;
  // The public view reports "player", "npc" or (when unrecorded) "unknown";
  // only an explicit "npc" hands a party member to the policy.
  const member = (view?.party || []).find(row => row.id === id);
  if (member) return member.controller === 'player' || (member.controller !== 'npc' && String(id).startsWith('p'));
  return false;
}
function npcDecisionPending(view = state.view) {
  if (!tacticalActive(view)) return false;
  const step = encounterStepActor(view);
  return Boolean(step) && !playerControlled(step, view);
}
function combatSignature(view = state.view) {
  const c = view?.combat || {};
  return JSON.stringify([view?.run_id, c.current, c.round, (c.order || []).indexOf(c.current), (c.pending || []).length,
    (view?.opposition || []).map(row => row.hp), (view?.party || []).map(row => row.hp)]);
}
let npcDrainRunning = false;
function scheduleNpcDrain() {
  if (npcDrainRunning || state.busy || state.preferences.combat.autoNpc === false || !npcDecisionPending()) return;
  // A drain that changed nothing is not retried until the combat moves on.
  if (state.npcDrainStalled && state.npcDrainStalled === combatSignature()) return;
  setTimeout(() => { drainNpcTurns(); }, 0);
}
async function drainNpcTurns() {
  if (npcDrainRunning || state.busy || !state.client?.drainNpc || !state.runId || !npcDecisionPending()) return;
  npcDrainRunning = true;
  state.npcPhase = true;
  const before = combatSignature();
  try {
    await work(async () => {
      render();
      for (let call = 0; call < 8 && npcDecisionPending(); call++) {
        const reply = result(await state.client.drainNpc(state.runId));
        const drain = reply.result?.drain || {};
        if (!drain.steps || drain.stopped !== 'step_limit') break;
      }
    }, 'Enemy turn', 'The opposition moves…');
  } finally {
    npcDrainRunning = false;
    state.npcPhase = false;
    state.npcDrainStalled = combatSignature() === before ? before : null;
    if (npcDecisionPending() && !state.npcDrainStalled) scheduleNpcDrain(); else render();
  }
}
function announceTurnChange(previous, next, {opposed = false} = {}) {
  const before = previous?.combat, after = next?.combat;
  if (!after || after.complete || !after.current || !tacticalActive(next) || before?.current === after.current) return;
  if (!before || before.complete || previous?.run_id !== next?.run_id) return;
  const fighters = [...(next.party || []), ...(next.opposition || [])];
  const name = fighters.find(row => row.id === after.current)?.name || after.current;
  if (playerControlled(after.current, next)) {
    combatDirector.queueBanner(`${name}'s turn`, 'turn');
    // The dock follows whoever the host says acts now.
    if ((next.party || []).some(row => row.id === after.current)) state.selectedActor = after.current;
  } else if (!opposed && playerControlled(before.current, previous)) combatDirector.queueBanner('Opposition phase', 'enemy');
}
async function boot() {
  const reply = result(await state.client.boot('DESIGN'));
  state.note = '';
  const options = await state.client.characterOptions();
  if (options?.ok) state.options = options.result;
}
async function connect(mode = state.transport, nextPhase = 'title') {
  // The current screen (title, transport picker, or the gameplay shell) stays
  // in place under the activity toast (shown only if the connect is slow). Stale state is dropped inside work() so a busy
  // client is never swapped out mid-request; a failure stays on that screen.
  await work(async () => {
    state.view = null; state.receipt = null; state.connected = false;
    state.transport = mode;
    state.client = createHSRClient({mode, onTrace: hostTrace});
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
    state.connected = true; heartbeat();
    go(nextPhase); state.note = '';
  }, 'Opening the Reliquary', 'Refreshing engine state…');
}
// ---- Title screen -----------------------------------------------------------
// The slogan rotates in place, the highlighted choice is always the one Enter
// fires, and the background layers drift with the pointer (or on their own once
// the pointer rests) so the menu is pleasant to leave open.
const TITLE_SLOGANS = [
  'Expect to die. Often.',
  'Platinum outlasts the descent. Your next run remembers.',
  'A saving throw can change a story. A careless step can end one.',
  'Rest while you can. Spells and courage both run low.',
  'A relic is only as kind as the hands that carry it.',
  'Read the room before you roll the dice.',
  'Explore the unknown. Build your legend.',
  'Every descent writes a new name in the dark.',
  'The Reliquary remembers those who return.',
  'Light a lantern. Go deeper.',
  'Steel, spell, and a steady nerve.',
  'Some doors open only once.',
  'Fortune favours the curious.',
  'The stars are hollow. The halls are not.',
  'Your legend begins below.',
  'Choose your road. Live with the echo.',
  'What sleeps beneath the city stirs.',
  'Every relic has a keeper.',
  'The stone breathes when the torches burn low.',
  'Not all that was entombed here was dead.',
  'Listen closely: the deeper walls remember your footsteps.',
  'The stars above are quiet; the hollow ones hunger.',
  'Gold tarnishes in the deep, but blood stays bright.',
  'You are not the first to seek what was hidden, nor the first to be kept.',
  'Old covenants lie shattered in the dust of the lower vaults.',
  'A flickering flame is the only shield between you and what watches.',
  'The silence between these pillars is heavy with unspoken grief.',
  'Every path downwards is paved with abandoned vows.',
  'Do not answer the whispers from behind the sealed doors.',
  'The reliquary was not built to protect the relics from the world.',
  'Shadows stretch longest where no light has fallen for centuries.',
  'Even the stone here bleeds memory when struck.',
  'Step softly; the sleepers below sleep lightly.',
  'What you carry into the dark is nothing compared to what you leave behind.',
  'The dark does not hate you; it merely consumes all that burns.',
  'Count your companions at each threshold. Make sure none were replaced.',
  'The abyss has a heartbeat, if you dare stand still enough to hear it.',
  'Beneath the hollow stars, even the gods avert their gaze.',
];
const TITLE_CHOICES = [
  ['Story Mode', 'menu:menu-story', 'intro-action-primary'],
  ['Simulation Mode', 'menu:menu-simulation', 'intro-action-primary'],
  ['Memory Archive', 'menu:archive', 'intro-action-secondary'],
  ['Options', 'menu:options', 'intro-action-secondary'],
];
// Fixed-seed scatter so the sky is identical on every render.
function titleRandom(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const TITLE_STARS = (() => {
  const r = titleRandom(7); const out = [];
  while (out.length < 72) {
    const x = r() * 1600; const y = r() * 440;
    if (Math.hypot(x - 1100, y - 200) < 215) continue; // keep the moon's face clear
    out.push(`<circle cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${(0.6 + r() * 1.4).toFixed(2)}" style="animation-delay:-${(r() * 6).toFixed(2)}s;animation-duration:${(3 + r() * 5).toFixed(2)}s"/>`);
  }
  return out.join('');
})();
const TITLE_MOTES = (() => {
  const r = titleRandom(19);
  return Array.from({length: 10}, () => `<circle cx="${(80 + r() * 1440).toFixed(0)}" cy="${(720 + r() * 150).toFixed(0)}" r="${(1.4 + r() * 1.6).toFixed(2)}" style="animation-delay:-${(r() * 16).toFixed(2)}s;animation-duration:${(12 + r() * 8).toFixed(2)}s"/>`).join('');
})();
function title() {
  if (state.titleSlogan == null) state.titleSlogan = Math.floor(Math.random() * TITLE_SLOGANS.length);
  const active = state.titleActive; // null until the player hovers, focuses or presses a key
  const link = state.link.status;
  return `<div class="intro-screen">
    <div class="intro-content">
      <section class="intro-card">
        <h1 class="intro-title">
          <span class="intro-title-the">The</span>
          <span class="intro-title-main">Hollow<br>Star</span>
          <span class="intro-title-sub">Reliquary</span>
        </h1>
        <div class="intro-title-rule" aria-hidden="true"></div>
        <p class="intro-subtitle" aria-live="polite" data-title-slogan><span class="title-slogan-layer is-visible">${E(TITLE_SLOGANS[state.titleSlogan % TITLE_SLOGANS.length])}</span><span class="title-slogan-layer" aria-hidden="true"></span></p>
        <div class="intro-actions">
          ${TITLE_CHOICES.map(([label, action, cls], i) => `<button type="button" class="action ${cls}${i === active ? ' is-active' : ''}" data-action="${E(action)}">${E(label)}</button>${i === 1 ? '<div class="intro-title-rule intro-action-rule" aria-hidden="true"></div>' : ''}`).join('\n          ')}
        </div>
        <p class="intro-mode-help">Story Mode carries the Reliquary's authored modules and your account progression. Completed runs bank Platinum for permanent upgrades, and victories raise the Loop tier so future descents grow richer and more demanding. Simulation Mode remains the open sandbox for stats, cheats, and rehearsal.</p>
        <p class="intro-workbench"><a href="/content-workbench.html" class="label" aria-label="Open Content Workbench">Content Workbench ↗</a></p>
        <p class="intro-connection">
          <button type="button" class="action intro-link link-${E(link)}" data-action="menu:transport" aria-label="Open connection settings" title="Open connection settings"><span class="intro-link-dot" aria-hidden="true"></span><span>Local</span></button>
        </p>
      </section>
    </div>
  </div>`;
}
// ---- Shared backdrop ----------------------------------------------------------
// The title-screen world is one persistent layer behind every screen. It is
// built once and never touched by render(), so its drift, twinkle and parallax
// run unbroken across menus, creation and play: screens change over it, not
// with it. Each phase picks how present it is; the level is a body attribute.
const BACKDROP_DIM_PHASES = new Set(['create', 'preview', 'options', 'ready', 'toolbox']);
function backdropLevel() { return BACKDROP_DIM_PHASES.has(state.phase) ? 'dim' : 'full'; }
function backdropArt() {
  return `<svg viewBox="0 0 1600 900" class="intro-art" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id="skyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" style="stop-color:var(--intro-sky-top);stop-opacity:1" />
        <stop offset="50%" style="stop-color:var(--intro-sky-mid);stop-opacity:1" />
        <stop offset="100%" style="stop-color:var(--intro-sky-bottom);stop-opacity:1" />
      </linearGradient>
      <radialGradient id="moonGrad" cx="50%" cy="40%">
        <stop offset="0%" style="stop-color:var(--intro-moon-core);stop-opacity:1" />
        <stop offset="80%" style="stop-color:var(--intro-moon-mid);stop-opacity:1" />
        <stop offset="100%" style="stop-color:var(--gold);stop-opacity:0.8" />
      </radialGradient>
      <radialGradient id="haloGrad">
        <stop offset="55%" style="stop-color:var(--intro-moon-core);stop-opacity:0.18" />
        <stop offset="100%" style="stop-color:var(--intro-moon-core);stop-opacity:0" />
      </radialGradient>
      <radialGradient id="spireGlow">
        <stop offset="0%" style="stop-color:var(--gold);stop-opacity:0.9" />
        <stop offset="100%" style="stop-color:var(--gold);stop-opacity:0" />
      </radialGradient>
      <linearGradient id="mistGrad" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" style="stop-color:var(--intro-mist);stop-opacity:0" />
        <stop offset="50%" style="stop-color:var(--intro-mist);stop-opacity:1" />
        <stop offset="100%" style="stop-color:var(--intro-mist);stop-opacity:0" />
      </linearGradient>
      <linearGradient id="shootGrad" gradientUnits="userSpaceOnUse" x1="-150" y1="0" x2="0" y2="0">
        <stop offset="0%" style="stop-color:var(--intro-moon-core);stop-opacity:0" />
        <stop offset="100%" style="stop-color:var(--intro-moon-core);stop-opacity:1" />
      </linearGradient>
    </defs>
    <rect x="-200" y="-200" width="2000" height="1300" fill="url(#skyGrad)"/>
    <g class="intro-layer" data-depth="0.02">
      <g class="intro-stars" fill="var(--intro-moon-core)">${TITLE_STARS}</g>
      <line class="intro-shooting-star" x1="-150" y1="0" x2="0" y2="0" stroke="url(#shootGrad)" stroke-width="2" stroke-linecap="round"/>
    </g>
    <g class="intro-layer" data-depth="0.05">
      <circle cx="1100" cy="200" r="300" fill="url(#haloGrad)"/>
      <g class="intro-sun">
        <circle cx="1100" cy="200" r="180" fill="url(#moonGrad)" opacity="0.95"/>
        <circle cx="1100" cy="200" r="180" fill="none" stroke="rgba(201,168,106,0.3)" stroke-width="2" opacity="0.6"/>
      </g>
    </g>
    <g class="intro-layer" data-depth="0.08">
      <path fill="var(--intro-mountain-back)" opacity="0.55" d="M-200 560 L60 500 L170 520 L300 470 L420 505 L560 450 L700 492 L860 440 L980 480 L1120 430 L1260 470 L1380 432 L1500 468 L1800 440 L1800 1000 L-200 1000Z"/>
      <g class="intro-spire" fill="var(--intro-mountain-back)">
        <polygon points="1392,440 1398,300 1402,284 1406,300 1412,440"/>
        <polygon points="1382,442 1388,384 1394,442"/>
        <polygon points="1410,442 1416,398 1422,442"/>
      </g>
      <circle class="intro-spire-light" cx="1402" cy="282" r="16" fill="url(#spireGlow)"/>
      <circle class="intro-spire-light" cx="1402" cy="282" r="2.2" fill="var(--intro-moon-core)"/>
    </g>
    <g class="intro-layer" data-depth="0.12">
      <g class="intro-clouds" fill="var(--intro-cloud)">
        <path d="M80 230 C160 175 245 205 282 250 C350 218 438 250 452 300 L55 300 C42 272 53 246 80 230Z"/>
        <path d="M1190 330 C1260 285 1330 302 1372 344 C1430 320 1514 350 1538 395 L1160 395 C1150 370 1160 345 1190 330Z"/>
        <path d="M620 150 C680 125 760 135 790 160 C840 150 900 165 910 185 L600 185 C592 170 600 158 620 150Z" opacity="0.6"/>
      </g>
    </g>
    <g class="intro-layer" data-depth="0.18">
      <g class="intro-mountains">
        <polygon points="0,600 200,300 500,600" fill="var(--intro-mountain-back)" opacity="0.8"/>
        <polygon points="250,650 600,250 900,650" fill="var(--intro-mountain-mid)" opacity="0.7"/>
        <polygon points="700,700 1100,350 1500,700" fill="var(--intro-mountain-front)" opacity="0.75"/>
        <polygon points="1200,750 1400,400 1600,750" fill="var(--intro-mountain-edge)" opacity="0.8"/>
      </g>
    </g>
    <g class="intro-layer" data-depth="0.26">
      <g class="intro-mist"><rect x="-300" y="600" width="2200" height="140" fill="url(#mistGrad)"/></g>
      <path fill="var(--intro-sky-bottom)" d="M-200 800 C120 760 260 790 420 770 C600 748 760 790 940 772 C1120 754 1300 792 1460 770 C1560 758 1640 770 1800 780 L1800 1100 L-200 1100Z"/>
    </g>
    <g class="intro-layer" data-depth="0.34">
      <g class="intro-motes" fill="var(--intro-firefly)">${TITLE_MOTES}</g>
    </g>
  </svg>`;
}
function ensureBackdrop() {
  let node = document.getElementById('hsr-backdrop');
  if (!node) {
    node = document.createElement('div');
    node.id = 'hsr-backdrop';
    node.setAttribute('aria-hidden', 'true');
    node.innerHTML = `${backdropArt()}<div class="intro-vignette"></div>`;
    document.querySelector('#app')?.before(node);
  }
  document.body.dataset.backdrop = backdropLevel();
  ensureBackdropMotion();
}
function motionReduced() {
  return state.preferences.motion === 'reduced' || Boolean(globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
}
// Parallax: each backdrop .intro-layer shifts by its data-depth. On full-
// strength screens the pointer steers it; after four idle seconds, and always
// on dimmed screens, a slow drift takes over so the world never sits frozen.
// Motion is a critically damped spring on elapsed time: it eases in from rest
// when the pointer first arrives instead of lurching, at any refresh rate. The
// loop reads the layers each frame and idles while the tab is hidden.
const backdropMotion = {x: 0, y: 0, vx: 0, vy: 0, tx: 0, ty: 0, lastMove: -1e9, lastFrame: 0, running: false, layers: null};
const BACKDROP_SPRING = {pointer: 2, idle: 1}; // stiffness, rad/s: lower is lazier
addEventListener('pointermove', event => {
  if (document.body.dataset.backdrop !== 'full' || document.hidden) return;
  backdropMotion.tx = (event.clientX / innerWidth) * 2 - 1;
  backdropMotion.ty = (event.clientY / innerHeight) * 2 - 1;
  backdropMotion.lastMove = performance.now();
  ensureBackdropMotion();
}, {passive: true});
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) ensureBackdropMotion();
});
function ensureBackdropMotion() {
  if (backdropMotion.running || document.hidden) return;
  backdropMotion.running = true;
  backdropMotion.lastFrame = performance.now();
  requestAnimationFrame(backdropMotionFrame);
}
function backdropMotionFrame(now) {
  if (document.hidden) {
    backdropMotion.running = false;
    return;
  }
  const dt = backdropMotion.lastFrame ? Math.min(.05, (now - backdropMotion.lastFrame) / 1000) : 0;
  backdropMotion.lastFrame = now;
  if (!backdropMotion.layers?.length) {
    const found = document.querySelectorAll('#hsr-backdrop .intro-layer');
    if (found.length) backdropMotion.layers = [...found];
  }
  const layers = backdropMotion.layers;
  if (!layers || !layers.length) {
    backdropMotion.running = false;
    return;
  }
  if (motionReduced()) {
    if (!backdropMotion.reducedApplied) {
      layers.forEach(layer => layer.removeAttribute('transform'));
      backdropMotion.reducedApplied = true;
    }
    backdropMotion.running = false;
    return;
  }
  backdropMotion.reducedApplied = false;
  const idle = document.body.dataset.backdrop !== 'full' || now - backdropMotion.lastMove > 4000;
  const goalX = idle ? Math.sin(now / 9000) * .7 : backdropMotion.tx;
  const goalY = idle ? Math.sin(now / 13000) * .45 : backdropMotion.ty;
  const w = idle ? BACKDROP_SPRING.idle : BACKDROP_SPRING.pointer;
  backdropMotion.vx += ((goalX - backdropMotion.x) * w * w - 2 * w * backdropMotion.vx) * dt;
  backdropMotion.vy += ((goalY - backdropMotion.y) * w * w - 2 * w * backdropMotion.vy) * dt;
  backdropMotion.x += backdropMotion.vx * dt;
  backdropMotion.y += backdropMotion.vy * dt;
  layers.forEach(layer => {
    const depth = Number(layer.dataset.depth) || 0;
    layer.setAttribute('transform', `translate(${(-backdropMotion.x * depth * 140).toFixed(2)} ${(-backdropMotion.y * depth * 80).toFixed(2)})`);
  });
  requestAnimationFrame(backdropMotionFrame);
}
// Slogans crossfade in place every fourteen seconds; no re-render.
setInterval(() => {
  if (state.phase !== 'title' || document.hidden) return;
  const node = document.querySelector('#app [data-title-slogan]');
  if (!node) return;
  state.titleSlogan = ((state.titleSlogan ?? 0) + 1) % TITLE_SLOGANS.length;
  const layers = [...node.querySelectorAll('.title-slogan-layer')];
  const outgoing = layers.find(layer => layer.classList.contains('is-visible'));
  const incoming = layers.find(layer => layer !== outgoing);
  if (!outgoing || !incoming) return;
  incoming.textContent = TITLE_SLOGANS[state.titleSlogan];
  incoming.removeAttribute('aria-hidden');
  outgoing.setAttribute('aria-hidden', 'true');
  node.classList.toggle('instant-slogan', motionReduced());
  incoming.classList.add('is-visible');
  outgoing.classList.remove('is-visible');
}, 14000);
// Menu highlight follows pointer/focus and keyboard navigation. Pointer exit
// clears a pointer-only highlight; Enter or Space activates the current item.
function titleButtons() { return [...document.querySelectorAll('#app .intro-actions .action')]; }
function setTitleActive(index, moveFocus = false, source = 'keyboard') {
  const buttons = titleButtons();
  if (!buttons.length) return;
  state.titleActive = (index + buttons.length) % buttons.length;
  state.titleActiveSource = source;
  buttons.forEach((node, i) => node.classList.toggle('is-active', i === state.titleActive));
  if (moveFocus) buttons[state.titleActive].focus({preventScroll: true});
}
const titleTrack = event => {
  const target = event.target.closest?.('#app .intro-actions .action');
  if (target) setTitleActive(titleButtons().indexOf(target), false, event.type === 'focusin' ? 'focus' : 'pointer');
};
document.addEventListener('pointerover', titleTrack);
document.addEventListener('pointerout', event => {
  const target = event.target.closest?.('#app .intro-actions .action');
  if (!target || target.contains(event.relatedTarget)) return;
  if (state.titleActiveSource === 'pointer' && titleButtons()[state.titleActive] === target) {
    state.titleActive = null;
    state.titleActiveSource = null;
    target.classList.remove('is-active');
  }
});
document.addEventListener('focusin', titleTrack);
document.addEventListener('keydown', event => {
  if (state.phase !== 'title' || state.overlay || state.busy || event.ctrlKey || event.metaKey || event.altKey) return;
  const focus = document.activeElement;
  if (focus && focus !== document.body && !focus.closest?.('.intro-card')) return;
  const inMenu = Boolean(focus?.closest?.('.intro-actions'));
  const key = event.key;
  const current = state.titleActive;
  if (key === 'ArrowDown' || key === 's' || key === 'S') { event.preventDefault(); setTitleActive(current == null ? 0 : current + 1, inMenu); }
  else if (key === 'ArrowUp' || key === 'w' || key === 'W') { event.preventDefault(); setTitleActive(current == null ? -1 : current - 1, inMenu); }
  else if (key === 'Enter' || key === ' ') {
    const buttons = titleButtons();
    const focused = buttons.indexOf(focus);
    const chosen = focused >= 0 ? buttons[focused] : current == null ? null : buttons[current];
    if (chosen && !chosen.disabled) { event.preventDefault(); chosen.click(); }
  }
});
function transportChoice() {
  return `<div class="mode-menu">${breadcrumb('Main Menu', 'Connection')}${atmosphere('gateway', 'Choose a connection', 'Select where the authoritative game host runs. Your current connection is local; a server connection can be added later without changing the client.')}${card('Connection', `<div class="gateway-choice-grid">
    <article class="gateway-choice"><p class="eyebrow">Available now</p><h3>Local</h3><p>Runs through the host on this device. Core story, simulation, combat, progression, and local saves remain playable offline.</p><div class="actions">${button('Use Local', 'start-engine', 'primary')}</div></article>
    <article class="gateway-choice unavailable"><p class="eyebrow">Coming later</p><h3>Server</h3><p>Attach to a remote server for synced services and shared features. This option is not available yet.</p><span class="gateway-status">Not configured</span></article>
  </div><div class="mode-menu-footer"><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
}
const MODE_LABELS = {FORGE: 'Story Mode', SANDBOX: 'Simulation Mode'};
const MODE_SCENARIOS = {FORGE: 'reliquary', SANDBOX: 'floor_one_life', DESIGN: 'floor_one_life'};
// Story Mode is bound to its authored module; only Simulation honours the
// Edit Scenario choice, and only after the host has confirmed that scenario
// exists for the mode, so a stale preference can never launch a rejected run.
function scenarioFor(mode) {
  const fallback = MODE_SCENARIOS[mode] || 'floor_one_life';
  if (mode === 'FORGE') return 'reliquary_city';
  const chosen = state.preferences.scenario;
  if (!chosen) return fallback;
  const known = (state.scenarios || []).some(row => row.scenario === chosen && (row.modes || []).includes(mode));
  return known ? chosen : fallback;
}
function scenarioTitle(id) {
  return (state.scenarios || []).find(row => row.scenario === id)?.title || id;
}
// A fresh, unguessable seed for anything the player asks to be random. The
// host stays deterministic *per seed*, so any seed shown can be typed back in
// to replay the same result.
function randomSeed(length = 8) {
  const bytes = new Uint8Array(length);
  (globalThis.crypto?.getRandomValues ? crypto.getRandomValues(bytes) : bytes.forEach((_, i) => { bytes[i] = Math.random() * 256; }));
  const alphabet = 'abcdefghjkmnpqrstuvwxyz23456789';
  return [...bytes].map(byte => alphabet[byte % alphabet.length]).join('');
}
// World seed for a new run: the Seed override when set (repeatable), else a
// fresh random seed, so starting the same character twice is two different
// descents instead of the same one replayed.
function runSeed() {
  const override = String(state.preferences.scenarioSeed || '').trim();
  return override || randomSeed();
}
// Readable, race-flavoured names from a seed. Same seed, same name; the
// player can overwrite it at any time and it then stays theirs.
const NAME_PARTS = {
  human: [['Al', 'Bran', 'Cor', 'Ed', 'Ma', 'Ro', 'Sa', 'Tam', 'Wil', 'Ys'], ['ric', 'wen', 'in', 'ra', 'ley', 'mond', 'eth', 'ara', 'ton', 'elle']],
  elf: [['Ae', 'Cael', 'Ela', 'Fae', 'Ith', 'Lue', 'Nae', 'Syl', 'Tha', 'Vae'], ['lith', 'rien', 'drel', 'nor', 'wyn', 'ssa', 'thil', 'ren', 'iel', 'lan']],
  'half-elf': [['Ari', 'Cal', 'Dar', 'Eli', 'Ker', 'Lia', 'Mer', 'Ria', 'Tal', 'Ves'], ['an', 'wen', 'ric', 'iel', 'ros', 'ith', 'ael', 'ora', 'en', 'yn']],
  orc: [['Bru', 'Dur', 'Gar', 'Gro', 'Kra', 'Mog', 'Rok', 'Shag', 'Thu', 'Urz'], ['gash', 'nak', 'rok', 'mash', 'gul', 'dak', 'thar', 'ok', 'ra', 'zug']],
  goblin: [['Bik', 'Fiz', 'Gib', 'Nix', 'Pok', 'Rat', 'Skee', 'Tik', 'Vex', 'Zub'], ['bit', 'gle', 'nik', 'snip', 'wick', 'zle', 'rot', 'kin', 'ble', 'sy']],
};
const EPITHETS = ['of the Lantern Road', 'the Unhurried', 'Ashborn', 'of Kettle Ford', 'the Patient', 'Starwatch', 'the Second', 'of the Low Bells', 'Thornward', 'the Quiet'];
function seededName(seed, race = 'human') {
  let h = 2166136261;
  for (const ch of `${seed}:${race}`) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619) >>> 0; }
  const pick = rows => { h = Math.imul(h ^ (h >>> 15), 2246822507) >>> 0; return rows[h % rows.length]; };
  const [first, second] = NAME_PARTS[race] || NAME_PARTS.human;
  const name = pick(first) + pick(second);
  return h % 3 === 0 ? `${name} ${pick(EPITHETS)}` : name;
}
function modeBadge(mode) {
  if (!mode) return '';
  const cls = mode === 'FORGE' ? 'mode-forge' : mode === 'SANDBOX' ? 'mode-sandbox' : 'mode-other';
  return `<span class="mode-badge ${cls}">${E(MODE_LABELS[mode] || mode)}</span>`;
}
// ---- The Hollow Star: memory, archive, Meta Shop ----------------------------
// Sound is produced outside this repo; the system plays whatever the audio
// manifest lists and silently skips ids it doesn't have yet.
var audio = createAudioSystem({settings: () => state.preferences.audio});
function textSpeedMs() { return TEXT_SPEEDS[state.preferences.story?.textSpeed] ?? 34; }
function metaShopUnlocked() { return Boolean(state.star?.meta_shop_unlocked); }
async function loadStar() {
  try {
    const reply = await state.client.request('star_memory', {}, {dedupeKey: 'star_memory'});
    if (reply.ok) state.star = reply.result?.star || state.star;
  } catch { /* the archive still opens with only always-unlocked scenes */ }
  return state.star;
}
async function playScene(id, {auto = false} = {}) {
  const scene = CUTSCENES.find(row => row.id === id);
  if (!scene) return;
  if (auto && state.preferences.story?.skipSeenCutscenes && (state.star?.seen_cutscenes || []).includes(id)) return;
  await playCutscene(scene, {textSpeed: textSpeedMs(), audio});
  try {
    const reply = await state.client.request('star_mark_seen', {cutscene: id});
    if (reply.ok) state.star = reply.result?.star || state.star;
  } catch {}
}
function starGlyph() {
  return `<svg class="star-glyph" viewBox="0 0 100 100" aria-hidden="true"><defs><radialGradient id="sg"><stop offset=".38" stop-color="#fff6d8" stop-opacity="0"/><stop offset=".5" stop-color="#fff6d8"/><stop offset=".62" stop-color="#e8c46a" stop-opacity=".5"/><stop offset="1" stop-color="#e8c46a" stop-opacity="0"/></radialGradient></defs><circle cx="50" cy="50" r="48" fill="url(#sg)"/><circle cx="50" cy="50" r="15" fill="#07060b"/></svg>`;
}
function starStatus() {
  const s = state.star;
  if (!s) return `<div class="star-status">${starGlyph()}<div><p class="star-tier">${E(t('star.unawakened'))}</p><p class="star-facts"><span>${E(t('star.offline'))}</span></p></div></div>`;
  return `<div class="star-status">${starGlyph()}<div><p class="label">Hollow Star · Awareness ${E(s.awareness?.tier ?? 0)}</p><p class="star-tier">${E(s.awareness?.name || 'Ember')}</p>
    <p class="star-facts"><span>${E(t('star.vessels', {n: s.runs}))}</span><span>${E(t('star.completions', {n: s.completions}))}</span><span>${E(t('star.falls', {n: s.deaths}))}</span></p></div></div>`;
}
function archiveScreen() {
  const seen = new Set(state.star?.seen_cutscenes || []);
  const cards = CUTSCENES.map(scene => {
    const open = cutsceneUnlocked(scene, state.star);
    return `<button type="button" class="archive-card${open ? '' : ' is-sealed'}" ${open ? `data-action="cutscene:${E(scene.id)}"` : 'aria-disabled="true"'}>
      <span class="archive-thumb" aria-hidden="true">${open ? scene.thumb : ''}</span>
      <em>${open ? t(seen.has(scene.id) ? 'archive.remembered' : 'archive.new') : t('archive.sealed')}</em>
      <strong>${E(open ? scene.title : '· · ·')}</strong><small>${E(open ? scene.blurb : t('archive.sealed_blurb'))}</small></button>`;
  }).join('');
  return `<div class="mode-menu">${breadcrumb('Main Menu', t('archive.title'))}${atmosphere('gateway', t('archive.title'), t('archive.subtitle'))}${card(t('archive.title'), `${starStatus()}<div class="archive-grid">${cards}</div>
    <div class="mode-menu-footer"><div class="footer-left">${button('Speak with the Star', 'dialogue:star-between-runs', 'secondary')}${button(t('codex.title'), 'menu:codex', 'secondary')}</div><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
}
async function loadStory() {
  try {
    const reply = await state.client.request('story_state', {}, {dedupeKey: 'story_state'});
    if (reply.ok) state.story = reply.result?.story || state.story;
  } catch {}
  return state.story;
}
// Fire-and-forget: story events never block play, and never fail it.
function emitStory(event, payload = {}) {
  state.client.request('story_emit', {event, payload}, {dedupeKey: `story:${event}:${JSON.stringify(payload)}:${Date.now()}`})
    .then(reply => { if (reply.ok) state.story = reply.result?.story || state.story; }).catch(() => {});
}
async function talkTo(id) {
  const dialogue = DIALOGUES[id];
  if (!dialogue) return;
  await loadStar(); await loadStory();
  const party = (state.view?.party || []).map(row => row.selector || row.identity).filter(Boolean);
  await runDialogue(dialogue, {context: {star: state.star, flags: state.story?.flags || {}, party}, textSpeed: textSpeedMs(),
    onEffect: effect => {
      if (effect.type === 'flag') state.client.request('story_flag', {flag: effect.flag, value: effect.value}).catch(() => {});
      if (effect.type === 'emit') emitStory(effect.event);
    }});
  await loadStory();
}
function slug(value) { return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 90) || 'unknown'; }
// Codex: the first time a creature or resident is seen, record it. Once per name per session.
function recordSightings(view) {
  state.codexSeen = state.codexSeen || new Set();
  for (const row of view?.opposition || []) {
    const name = row.name || row.id; if (!name) continue;
    const kind = String(row.role || row.kind || '').includes('resident') ? 'resident' : 'monster';
    const id = slug(name);
    if (state.codexSeen.has(`${kind}:${id}`)) continue;
    state.codexSeen.add(`${kind}:${id}`);
    state.client.request('codex_discover', {kind, entry: id, title: name}).catch(() => {});
  }
}
// The run-end pipeline: once per run, the host settles progression, feeds the
// Star and emits run_ended. The client only reports what changed.
async function finalizeRun(runId) {
  if (!runId || state.finalizedRuns.has(runId)) return;
  state.finalizedRuns.add(runId);
  try {
    const reply = await state.client.request('run_end', {run_id: runId});
    if (!reply.ok) { addMessage(`Run could not be finalized: ${reply.error?.message || 'host error'}`, 'note'); state.finalizedRuns.delete(runId); return; }
    const out = reply.result?.run_end || {};
    state.star = out.star || state.star; state.story = out.story || state.story;
    if (out.meta_shop_newly_unlocked) storyToast(t('shop.unlocked_toast'));
    if ((out.awareness_after?.tier ?? 0) > (out.awareness_before?.tier ?? 0)) storyToast(t('run.star_awareness', {tier: out.awareness_after.tier, name: out.awareness_after.name}));
    for (const row of out.errors || []) addMessage(`Settlement skipped for ${row.identity}: ${row.error}`, 'note');
    for (const [champ, view] of Object.entries(out.ladder || {})) {
      const name = champ[0].toUpperCase() + champ.slice(1);
      if (view.levels_gained > 0) storyToast(t('ladder.level_toast', {name, n: view.level}));
      if (view.picks_left) storyToast(t(view.picks_left === 1 ? 'ladder.picks_toast_one' : 'ladder.picks_toast', {name, n: view.picks_left}));
    }
    if (out.star_revealed) { await playScene('last-standing'); render(); }
  } catch { state.finalizedRuns.delete(runId); }
}
function codexScreen() {
  const codex = state.story?.codex || {};
  const kinds = ['floor', 'monster', 'resident', 'location', 'item', 'lore'].filter(kind => Object.keys(codex[kind] || {}).length);
  const shelves = kinds.map(kind => `<section class="codex-shelf"><h3>${E(t(`codex.kind.${kind}`))}</h3><div class="codex-entries">${Object.entries(codex[kind]).map(([id, row]) => `<div class="codex-entry"><strong>${E(row.title || id)}</strong><small>${E(String(row.discovered_at || '').slice(0, 10))}</small></div>`).join('')}</div></section>`).join('');
  return `<div class="mode-menu">${breadcrumb('Main Menu', t('codex.title'))}${atmosphere('journal', t('codex.title'), t('codex.subtitle'))}${card(t('codex.title'), `<div class="codex-shelves">${shelves || `<p class="notice">${E(t('codex.empty'))}</p>`}</div>
    <div class="mode-menu-footer"><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
}
function storyDebugPanel() {
  const s = state.star;
  const flags = Object.entries(state.story?.flags || {});
  const a = audio.status(); const art = assetStatus();
  return `<section class="card"><p class="label">Story debug · Hollow Star</p>
    <p class="notice">Account-wide story state. Changes here are real saves on this machine.</p>
    <p>Awareness ${E(s?.awareness?.tier ?? '—')} (${E(s?.awareness?.name ?? 'unloaded')}) · runs ${E(s?.runs ?? 0)} · completions ${E(s?.completions ?? 0)} · deaths ${E(s?.deaths ?? 0)}</p>
    <div class="actions">${button('Load story state', 'story-debug:load', 'secondary')}${button('+1 run', 'story-debug:runs', 'secondary')}${button('+1 completion', 'story-debug:completions', 'secondary')}${button('Reveal Star (tier 4)', 'story-debug:reveal', 'secondary')}${button('Forget seen cutscenes', 'story-debug:forget', 'secondary')}${button('Reset Star memory', 'story-debug:reset', 'secondary')}</div>
    <p class="label">Replay any cutscene (ignores locks)</p><div class="actions">${CUTSCENES.map(row => button(row.title, `cutscene:${row.id}`, 'secondary')).join('')}</div>
    <p class="label">Dialogues</p><div class="actions">${Object.keys(DIALOGUES).map(id => button(id, `dialogue:${id}`, 'secondary')).join('')}</div>
    <p class="label">Story flags</p><form class="actions" data-story-flag-form><input name="flag" placeholder="flag_name" aria-label="Flag name"><button type="submit" class="action secondary">Set flag</button></form>
    <p>${flags.length ? flags.map(([k, v]) => `<code>${E(k)}=${E(v)}</code>`).join(' ') : '<span class="notice">No flags set.</span>'}</p>
    <p class="label">Champion ladder (set level)</p><div class="actions">${['doran', 'wren'].flatMap(c => [1, 25, 50, 100].map(n => button(`${c[0].toUpperCase() + c.slice(1)} ${n}`, `ladder-debug:${c}:${n}`, 'secondary'))).join('')}</div>
    <p>${Object.values(state.ladders || {}).map(v => `${E(v.champion)} L${E(v.level)} · ${E(v.picks_left)} picks`).join(' · ') || '<span class="notice">Ladder not loaded.</span>'}</p>
    <p class="label">Content systems</p><p>Audio: ${E(a.known)} sounds in manifest · music ${E(a.music || 'none')}${a.missing.length ? ` · missing: ${E(a.missing.slice(0, 6).join(', '))}` : ''}<br>Art: ${E(art.images)} images, ${E(art.sprites)} sprites${art.missing.length ? ` · placeholders for: ${E(art.missing.slice(0, 6).join(', '))}` : ''}</p>
  </section>`;
}
function storyOptions() {
  const st = state.preferences.story; const au = state.preferences.audio;
  const sel = (key, value, opts) => `<select data-pref-group="story" data-pref-key="${key}">${opts.map(([v, l]) => `<option value="${v}" ${value === v ? 'selected' : ''}>${l}</option>`).join('')}</select>`;
  return `<label class="option-row"><span><strong>Text speed</strong><small>How fast cutscene and dialogue lines type out.</small></span>${sel('textSpeed', st.textSpeed, [['slow', 'Slow'], ['normal', 'Normal'], ['fast', 'Fast'], ['instant', 'Instant']])}</label>
    <label class="option-row"><span><strong>Skip cutscenes already seen</strong><small>Automatic scenes you have watched stay in the Memory Archive instead of replaying.</small></span><input type="checkbox" data-pref-group="story" data-pref-key="skipSeenCutscenes" ${st.skipSeenCutscenes ? 'checked' : ''}></label>
    <label class="option-row"><span><strong>Floor title cards</strong><small>Show a title card when a new floor begins.</small></span><input type="checkbox" data-pref-group="story" data-pref-key="floorCards" ${st.floorCards ? 'checked' : ''}></label>
    <label class="option-row"><span><strong>Colour-blind support</strong><small>Add patterns and symbols wherever colour carries meaning.</small></span><input type="checkbox" data-pref="colorblind" ${state.preferences.colorblind === 'on' ? 'checked' : ''}></label>
    <label class="option-row"><span><strong>Mute all audio</strong></span><input type="checkbox" data-pref-group="audio" data-pref-key="muted" ${au.muted ? 'checked' : ''}></label>
    ${['master', ...AUDIO_CATEGORIES].map(cat => `<label class="option-row"><span><strong>${E(cat[0].toUpperCase() + cat.slice(1))} volume — ${Math.round(au[cat] * 100)}%</strong></span><input type="range" min="0" max="1" step=".05" value="${E(au[cat])}" data-pref-group="audio" data-pref-key="${cat}"></label>`).join('')}`;
}
async function loadLadders() {
  try { const reply = await state.client.request('unlock_ladder', {}, {dedupeKey: 'unlock_ladder'}); if (reply.ok) state.ladders = reply.result?.ladders || null; } catch {}
}
function ladderPicksLabel(n) {
  return n === 1 ? t('ladder.picks_one') : n ? t('ladder.picks', {n}) : t('ladder.picks_none');
}

function ladderTile(v, e) {
  const state = e.unlocked ? 'is-unlocked' : e.available ? 'is-available' : 'is-locked';
  const foot = e.unlocked ? `<em>${E(t('ladder.unlocked'))}</em>`
    : !e.available ? `<small class="ladder-when">${E(t('ladder.opens_at', {n: e.min_level}))}</small>`
    : v.picks_left ? `<button type="button" class="action secondary" data-action="unlock:${E(v.champion)}:${E(e.key)}">${E(t('ladder.unlock'))}</button>`
    : `<small class="ladder-when">${E(t('ladder.needs_pick'))}${v.next_pick_level ? ` · ${E(t('ladder.next_pick', {n: v.next_pick_level}))}` : ''}</small>`;
  const from = e.available || e.unlocked ? `<small>${E(t('ladder.min_level', {n: e.min_level}))}</small>` : '';
  return `<div class="ladder-entry ${state}"><strong>${E(e.label)}</strong>${from}${foot}</div>`;
}

function ladderScreen() {
  const back = `<div class="mode-menu-footer"><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`;
  const ladders = state.ladders;
  const body = !ladders ? `<p class="notice">${E(t('star.offline'))}</p>` : Object.values(ladders).map(v => {
    const name = v.champion[0].toUpperCase() + v.champion.slice(1);
    const done = v.level >= v.max_level;
    const per = v.xp_per_level || 1;
    const into = v.xp_into_level || 0;
    const unlocked = v.entries.filter(e => e.unlocked).length;
    const xp = done ? t('ladder.xp_max') : t('ladder.xp', {x: into, per, next: v.level + 1});
    const nextPick = !done && v.next_pick_level ? ` · ${t('ladder.next_pick', {n: v.next_pick_level})}` : '';
    return `<section class="ladder-champion"><header class="ladder-head"><h3>${E(name)}</h3><span class="ladder-level">${E(t('ladder.level', {n: v.level, max: v.max_level}))}</span>
      <span class="ladder-picks${v.picks_left ? ' has-picks' : ''}">${E(ladderPicksLabel(v.picks_left))}</span>${v.slot_cap ? `<span class="ladder-picks">${E(t('ladder.slots', {n: v.slot_cap}))}</span>` : ''}
      <span class="ladder-count">${E(t('ladder.count', {unlocked, total: v.entries.length}))}</span></header>
      <div class="journey-progress" role="progressbar" aria-label="${E(name)} champion level" aria-valuemin="1" aria-valuemax="${E(v.max_level)}" aria-valuenow="${E(v.level)}"><span style="width:${Math.round(v.level / v.max_level * 100)}%"></span></div>
      <p class="ladder-xp"><span class="ladder-xp-bar" aria-hidden="true"><span style="width:${done ? 100 : Math.round(into / per * 100)}%"></span></span>${E(xp + nextPick)}</p>
      <div class="ladder-grid">${v.entries.map(e => ladderTile(v, e)).join('')}</div></section>`;
  }).join('');
  const hint = ladders ? `<p class="ladder-hint">${E(t('ladder.earn_hint'))}</p>` : '';
  return `<div class="mode-menu">${breadcrumb('Main Menu', 'Story Mode', t('ladder.title'))}${atmosphere('gateway', t('ladder.title'), t('ladder.subtitle'))}${card(t('ladder.title'), `<div class="ladder">${body}</div>${hint}${back}`, 'mode-menu-card')}</div>`;
}
function metaShopScreen() {
  const back = `<div class="mode-menu-footer"><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`;
  if (!metaShopUnlocked()) {
    return `<div class="mode-menu">${breadcrumb('Main Menu', 'Story Mode', 'Meta Shop')}${card('Meta Shop', `<div class="meta-lock">${starGlyph()}<strong>Sealed</strong><p>The Hollow Star has nothing to trade until a vessel's run has ended.</p></div>${back}`, 'mode-menu-card')}</div>`;
  }
  const p = state.progression;
  const rows = state.metaShop || Object.entries(UPGRADE_TRACKS).map(([key, spec]) => {
    const tier = p?.upgrades?.[key] ?? 0;
    return {key, effect: spec.effect, tier, cap: spec.cap, capped: tier >= spec.cap, next_cost: tier >= spec.cap ? null : spec.base_cost * (tier + 1)};
  });
  const platinum = p?.platinum ?? 0;
  const tracks = rows.map(row => `<div class="meta-track${row.capped ? ' is-capped' : ''}"><h3>${E(row.key.replaceAll('_', ' '))}</h3><p>${E(row.effect)}</p>
    <div class="meta-pips" aria-label="Tier ${E(row.tier)} of ${E(row.cap)}">${Array.from({length: row.cap}, (_, i) => `<i class="${i < row.tier ? 'on' : ''}"></i>`).join('')}</div>
    ${row.capped ? `<span class="notice">${E(t('shop.mastered'))}</span>` : `<button type="button" class="action secondary" data-upgrade="${E(row.key)}"${platinum < row.next_cost ? ' disabled' : ''}>${E(t('shop.absorb', {cost: row.next_cost}))}</button>`}</div>`).join('');
  return `<div class="mode-menu">${breadcrumb('Main Menu', 'Story Mode', 'Meta Shop')}${atmosphere('gateway', 'Meta Shop', 'What the Star absorbs, every vessel inherits.')}${card('Meta Shop', `<div class="meta-shop">
    <div class="meta-shop-purse">${starGlyph()}<div><p class="label">Platinum · ${E(state.accountIdentity)}</p><span class="plat">${E(platinum)}</span></div></div>
    <div class="meta-shop-grid">${tracks}</div></div>${back}`, 'mode-menu-card')}</div>`;
}
async function loadMetaShop() {
  const reply = await state.client.request('meta_shop', {identity: state.accountIdentity});
  if (reply.ok) { state.progression = reply.result?.progression || state.progression; state.metaShop = reply.result?.meta_shop || null; }
}
function storyMenu() {
  return `<div class="mode-menu">${breadcrumb('Main Menu', 'Story Mode')}${atmosphere('gateway', 'Story Mode', 'Choose a Champion or create an adventurer for the Reliquary’s authored story.')}${card('Story Mode', `<div class="menu-list-stack">
    <div class="menu-grid-row-3">
      <button type="button" class="action menu-item-card" data-action="mode:FORGE" data-tooltip="Begin a new authored descent into the Reliquary with certified Champions or a custom build."><strong>New Game</strong><small>Begin a new authored descent into the Reliquary</small></button>
      <button type="button" class="action menu-item-card" data-action="continue:FORGE" data-tooltip="Resume an existing saved Story Mode expedition."><strong>Continue</strong><small>Resume a saved Story Mode expedition</small></button>
      <button type="button" class="action menu-item-card" data-action="menu:statistics" data-tooltip="Review past journeys, records, and progression."><strong>Statistics</strong><small>Review past journeys, records, and progression</small></button>
    </div>
    <div class="menu-grid-row-2">
      ${metaShopUnlocked()
        ? `<button type="button" class="action menu-item-card" data-action="menu:meta-shop" data-tooltip="Spend Platinum on permanent upgrades the Hollow Star carries into every vessel."><strong>Meta Shop</strong><small>Permanent upgrades carried between runs</small></button>`
        : `<button type="button" class="action menu-item-card is-locked" aria-disabled="true" data-tooltip="The Hollow Star has nothing to trade yet. Finish your first run."><strong>Meta Shop · Sealed</strong><small>Unlocks after your first run ends</small></button>`}
      <button type="button" class="action menu-item-card" data-action="menu:archive" data-tooltip="Replay the Hollow Star's memories."><strong>Memory Archive</strong><small>Cutscenes the Star has lived through</small></button>
    </div>
    <div class="menu-grid-row-2">
      <button type="button" class="action menu-item-card" data-action="menu:ladder" data-tooltip="Doran and Wren earn their own power back, level 1 to 100."><strong>Champion Ladder</strong><small>Unlock Doran and Wren's abilities as they level</small></button>
      <button type="button" class="action menu-item-card" data-action="menu:codex" data-tooltip="Floors, creatures and residents you have discovered."><strong>Codex</strong><small>What the Reliquary has let you learn</small></button>
    </div>
  </div><div class="mode-menu-footer"><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
}
function simulationMenu() {
  const intro = `<div class="simulation-overview-banner"><p>Select an authored scenario, test encounters, and experiment freely with party builds and rules tuning. Simulation Mode lets you playtest custom adventurers or certified Champions, configure seed overrides, rehearse boss encounters like the Brass Castellan, and inspect full live engine telemetry without altering canon story records.</p></div>`;
  const descent = `<div class="menu-group-label">Descent Operations</div><div class="menu-grid-row-2">
    <button type="button" class="action menu-item-card" data-action="mode:SANDBOX" data-tooltip="Launch a fresh sandbox descent. Select a certified Champion or create a custom build to enter the Reliquary."><strong>New Run</strong><small>Launch a sandbox descent with custom profile or champions</small></button>
    <button type="button" class="action menu-item-card" data-action="continue:SANDBOX" data-tooltip="Resume an active or saved Simulation run without affecting Story Mode progression."><strong>Continue</strong><small>Resume an active or saved simulation run</small></button>
  </div>`;
  const tools = optionsSection('sim-rehearsal-tools', 'Rehearsal & Diagnostic Tools', 'Boss rehearsal, scenario overrides, telemetry and engine internals', `<div class="menu-grid-row-4">
    <button type="button" class="action secondary menu-item-card" data-action="champion-rehearsal" data-tooltip="Instantly launch the tactical encounter against the Brass Castellan boss with Doran and Wren."><strong>Brass Castellan Rehearsal</strong><small>Doran + Wren boss encounter rehearsal</small></button>
    <button type="button" class="action secondary menu-item-card" data-action="menu:edit-scenario" data-tooltip="Select active test scenario and seed overrides for custom playtesting."><strong>Edit Scenario${state.preferences.scenario ? ` — ${scenarioTitle(state.preferences.scenario)}` : ''}</strong><small>Select active test scenario and seed overrides</small></button>
    <button type="button" class="action secondary menu-item-card" data-action="menu:statistics" data-tooltip="Review simulation telemetry, encounter clear times, victory rates, and lifetime performance."><strong>Statistics</strong><small>Examine simulation run histories and metrics</small></button>
    <button type="button" class="action secondary menu-item-card" data-action="menu:cheats" data-tooltip="Inspect engine internals, hidden checks, enemy AI intent, and underlying rolls."><strong>Cheats</strong><small>Inspect engine internals and debug state</small></button>
  </div>`);
  const workbench = optionsSection('sim-actor-toolbox', 'Diagnostic Stage Tools', 'Actor Toolbox and Actor Lab — pose, move and inspect any figure', `<div class="menu-grid-row-2">
    <button type="button" class="action menu-item-card" data-action="menu:toolbox" data-tooltip="Spawn and steer any figure on the main display's own stage: walking, turning, sizes and hit boxes, weapon carry, swings, damage, doors and sets."><strong>Actor Toolbox</strong><small>Move, turn, resize and swing any figure; cut dummies; open doors; change the set</small></button>
    <a class="action secondary menu-item-card" href="actor-lab.html" target="_blank" rel="noopener" data-tooltip="The pose sheet, line-up and frame-time readout for every rig."><strong>Actor Lab</strong><small>Pose sheet, line-up and frame time</small></a>
  </div>`);
  return `<div class="mode-menu">${breadcrumb('Main Menu', 'Simulation Mode')}${atmosphere('gateway', 'Simulation Mode', 'A private sandbox for rehearsal.')}${card('Simulation Mode', `<div class="menu-list-stack simulation-menu-stack">
    ${intro}
    ${descent}
    ${workbench}
    ${tools}
  </div><div class="mode-menu-footer"><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
}
function partySelect() {
  const forge = state.pendingMode === 'FORGE';
  const copy = forge
    ? 'Story Mode can begin with Doran or Wren, or with a new adventurer entering the authored town. Custom adventurers keep their own profile equipment and do not inherit the Champions’ kits or conversation trees.'
    : 'Simulation Mode accepts custom profiles and certified Champions.';
  // The step list is read from the workshop itself so the count cannot drift.
  const steps = CREATE_STEPS.map(step => step.label.toLowerCase());
  const workshop = `${steps.slice(0, -1).join(', ')}, and ${steps.at(-1)}`;
  // Neither card is pre-lit; both glow only on hover or focus. The whole card
  // is the click target, and its inner button carries no data-action of its
  // own, so a click on the button bubbles up and fires the choice exactly once.
  const cards = `<div class="party-select-grid">
    <article class="cc-fork-card alt" data-action="create">
      <span class="cc-fork-icon" aria-hidden="true">✦</span>
      <strong>Build a Custom Adventurer</strong>
      <small>Shape your lead through the ${CREATE_STEPS.length}-step workshop: ${E(workshop)}.</small>
      <div class="actions"><button type="button" class="action">Build a custom character</button></div>
    </article>
    <article class="cc-fork-card alt" data-action="champion-select">
      <span class="cc-fork-icon" aria-hidden="true">⚔</span>
      <strong>Play as a Champion</strong>
      <small>Embark with Doran or Wren. Carry certified field kits, maneuvers, domain powers, and story branches.</small>
      <div class="actions"><button type="button" class="action">Play as a Champion</button></div>
    </article>
  </div>`;
  return `<div class="mode-menu">${breadcrumb('Main Menu', MODE_LABELS[state.pendingMode] || 'New lead', 'Choose Lead')}${atmosphere('gateway', MODE_LABELS[state.pendingMode] || 'New lead', copy)}${card('Choose a lead', `${cards}<div class="mode-menu-footer"><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
}
function champion() {
  const cards = championRoster().map(row => {
    const art = characterFigure({identity: row.id.toLowerCase(), name: row.id}, 'featured', 'idle');
    return `<article class="champion-card"><div class="champion-art">${art}</div><div class="champion-copy"><h3>${E(row.id)}</h3><p class="notice">${E(row.title)}</p><p>${E(row.blurb)}</p><p>${row.id.toLowerCase() === "doran" ? "A soldier and tactician with the strength to take the dangerous lane himself. Doran reads a room and applies relentless pressure. His challenge is learning when a solo clearer needs a partner." : "A leader who feels like a party in one: spellcraft, support, and the breadth to answer more than one kind of danger. Wren brings an established identity and relationships into every descent."}</p><p class="notice">Champions are the intended dungeon clearers: formidable standalone leads with authored histories, personal story branches, and character-specific conversations. Custom adventurers follow their own path and do not inherit these identities, kits, or interactions.</p><div class="actions">${button(`Begin as ${row.id}`, `champion:${row.id}`)}</div></div></article>`;
  }).join('');
  return `<div class="mode-menu">${breadcrumb('Main Menu', MODE_LABELS[state.pendingMode] || 'New lead', 'Champions')}${atmosphere('gateway', 'Champions', 'These field Stewards carry their own canon kit into the Reliquary instead of a freshly built adventurer.')}${card('Playable champions', `<div class="champion-grid">${cards}</div><div class="mode-menu-footer"><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
}
function entrySelect() {
  const lead = state.pendingLead || {};
  let heroArt = '';
  let heroName = '';
  let heroSubtitle = '';
  let heroDetails = '';

  if (lead.kind === 'champion') {
    const champ = (championRoster() || []).find(r => r.id === lead.name) || {id: lead.name, title: 'Champion', blurb: ''};
    heroArt = characterFigure({identity: champ.id.toLowerCase(), name: champ.id}, 'featured', 'idle');
    heroName = champ.id;
    heroSubtitle = champ.title || 'Playable Champion';
    heroDetails = champ.blurb || 'Ready to descend with certified field kit and maneuvers.';
  } else if (lead.kind === 'custom') {
    const preview = lead.preview || state.draft;
    const race = preview.race || state.draft.race || 'human';
    heroArt = characterFigure(preview, 'featured', 'idle');
    heroName = preview.name || state.draft.name || 'Custom Adventurer';
    const clsName = optionBy('classes', preview.character_class || state.draft.character_class)?.name || 'Adventurer';
    const raceName = optionBy('races', race)?.name || 'Human';
    heroSubtitle = `Level ${preview.level || 1} ${raceName} ${clsName}`;
    heroDetails = preview.summary || 'Equipped and prepared for the descent into the Reliquary.';
  }

  const cards = `
    <div class="entry-select-hero">
      <div class="entry-hero-art">${heroArt}</div>
      <div class="entry-hero-copy">
        <p class="eyebrow">Chosen Lead</p>
        <h2>${E(heroName)}</h2>
        <p class="notice">${E(heroSubtitle)}</p>
        <p>${E(heroDetails)}</p>
      </div>
    </div>
    <div class="entry-path-grid">
      <article class="cc-fork-card alt entry-path-card" data-action="start-story:well">
        <span class="cc-fork-icon" aria-hidden="true">⚔</span>
        <p class="eyebrow">Descent Gate · Combat Ready</p>
        <strong>The Sunken Well</strong>
        <small>Step directly to the barred gate into the ancient Reliquary. Weapons drawn, spells ready, one click to the first combat threshold.</small>
        <div class="actions"><button type="button" class="action primary">Begin Descent</button></div>
      </article>
      <article class="cc-fork-card alt entry-path-card" data-action="start-story:market">
        <span class="cc-fork-icon" aria-hidden="true">☵</span>
        <p class="eyebrow">City Arrival · Social & Preparation</p>
        <strong>Central Market Square</strong>
        <small>Arrive among the townspeople, merchants, and guildmasters above the depths. Gather intelligence and supplies before taking the plunge.</small>
        <div class="actions"><button type="button" class="action">Explore Town</button></div>
      </article>
    </div>
  `;

  return `<div class="mode-menu">${breadcrumb('Main Menu', 'Story Mode', 'Choose Starting Path')}${atmosphere('gateway', 'Starting Entry', 'Choose how you enter the Reliquary: straight to the descent gate for immediate action, or into the town for preparation.')}${card('Choose your starting path', `${cards}<div class="mode-menu-footer"><div class="footer-right">${button('Back', 'back-to-lead', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
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
function floatingOpener(race) {
  const rule = race.floating_bonus;
  if (!rule) return '';
  const manual = Array.isArray(state.draft.floating_bonuses);
  const selected = manual ? state.draft.floating_bonuses : (state.live?.receipt?.floating_bonuses || []);
  return opener({action: 'overlay-open:floating', label: 'Ancestry bonuses',
    value: `${selected.length} of ${rule.count} chosen`,
    hint: `Choose ${rule.count} abilities for the floating ${rule.amount > 0 ? '+' : ''}${rule.amount} bonus.`});
}
function floatingOverlayBody(race) {
  const rule = race.floating_bonus;
  const manual = Array.isArray(state.draft.floating_bonuses);
  const selected = manual ? state.draft.floating_bonuses : (state.live?.receipt?.floating_bonuses || []);
  return `${manual ? '' : '<p><span class="cc-badge">Auto: your class priorities</span></p>'}<div class="check-grid">${ABILITIES.filter(ability => !rule.exclude.includes(ability)).map(ability => `<label class="check-chip"><input type="checkbox" data-floating="${E(ability)}" ${selected.includes(ability) ? 'checked' : ''}><span>${E(ability)}<small>${E(ABILITY_NAMES[ability])}</small></span></label>`).join('')}</div>`;
}
function advancementControls(level, cls) {
  const points = 2 * ((state.options?.advancement_levels || []).filter(threshold => level >= threshold).length);
  if (!points) return ''; 
  const values = state.draft.advancements && typeof state.draft.advancements === 'object' ? state.draft.advancements : {};
  const manual = state.draft.advancement_mode === 'manual';
  return detailCard('Advancement', `<p>Level ${E(level)} grants <strong>${E(points)} ability points</strong>. Class priority: ${E((cls.primary || []).join(' / '))}.</p><div class="actions compact-actions">${button(manual ? 'Use automatic allocation' : 'Allocate manually', manual ? 'advancements-auto' : 'advancements-manual', 'secondary')}</div>${manual ? `<div class="ability-table advancement-table"><div class="ability-head"><span>Ability</span><span>Points</span><span>Result</span></div>${ABILITIES.map(ability => `<label class="ability-row"><span><strong>${E(ability)}</strong><small>${E(ABILITY_NAMES[ability])}</small></span><input type="number" min="0" max="${E(points)}" value="${E(values[ability] || 0)}" data-advancement="${E(ability)}"><strong>+${E(values[ability] || 0)}</strong></label>`).join('')}</div>` : '<p class="notice">The host will allocate these points deterministically toward the selected class priorities.</p>'}`);
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
  {id: 'identity', label: 'Identity', title: 'Who descends?', lede: 'Name your lead. This is the first of eight short steps, and each one shows exactly what it changes. Nothing is saved until you confirm the final sheet.'},
  {id: 'ancestry', label: 'Ancestry', title: 'Choose an ancestry', lede: 'Ancestry sets your starting ability bonuses and a few innate traits.'},
  {id: 'class', label: 'Class', title: 'Choose a class', lede: 'Class is your role in a fight. It sets hit points, armor, gear, saves and the abilities that matter most.'},
  {id: 'background', label: 'Background', title: 'Choose a background', lede: 'Where you came from: +1 to one ability, starting gold and a few personal effects.'},
  {id: 'abilities', label: 'Abilities', title: 'Roll your abilities', lede: 'Roll 4d6 six times and drop the lowest die each time. You get one reroll. The recommended placement puts your best rolls into your class priorities.'},
  {id: 'training', label: 'Training', title: 'Skills and spells', lede: 'Pick the skills you are trained in and, if your class casts, your starting spells. Automatic choices are always legal.'},
  {id: 'look', label: 'Look', title: 'Appearance', lede: 'Cosmetic only. Nothing here changes a number.'},
  {id: 'summary', label: 'Summary', title: 'Final sheet', lede: 'Review the finished lead. Confirming saves the profile and starts the run.'},
];
const RATING_AXES = [['offense', 'Offense'], ['defense', 'Defense'], ['magic', 'Magic'], ['complexity', 'Complexity']];
const LOOK_FIELDS = ['skin_tone', 'face_shape', 'facial_marks', 'ear_shape', 'hair_style', 'hair_color', 'eye_color', 'body_type', 'outfit', 'cloth_color', 'accent_color', 'cloak_style', 'headgear_style', 'weapon_style', 'offhand_style', 'trinket_style'];
const LOOK_GROUPS = [
  {label: 'Face', fields: ['skin_tone', 'face_shape', 'facial_marks', 'ear_shape', 'eye_color']},
  {label: 'Hair and build', fields: ['hair_style', 'hair_color', 'body_type']},
  {label: 'Wardrobe', fields: ['outfit', 'cloth_color', 'accent_color', 'cloak_style', 'headgear_style']},
  {label: 'Loadout styling', fields: ['weapon_style', 'offhand_style', 'trinket_style']},
];
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
  for (const [field, spec] of Object.entries(fields)) {
    const choices=(spec.options||[]).filter(row=>!row.races?.length||row.races.includes(d.race));
    const picked=d.appearance?.[field];
    // A colour from the picker is stored as '#rrggbb' and drawn as a custom entry.
    if(spec.custom&&typeof picked==='string'&&/^#[0-9a-f]{6}$/i.test(picked)){appearance[field]={id:'custom',name:'Custom',hex:picked.toLowerCase()};continue;}
    const row=choices.find(option=>option.id===picked)||choices[0];
    if(row)appearance[field]=Object.fromEntries(['id','name','hex','scale','visual'].filter(k=>row[k]!==undefined).map(k=>[k,row[k]]));
  }
  const liveProfile = state.live?.profile;
  const cls = optionBy('classes', d.character_class);
  return {...(liveProfile || {}), name: d.name || 'Your lead', race_id: d.race, gender: d.gender, class_id: d.character_class,
    character_class: cls.name, sprite_id: `${d.race}-${d.gender}`, appearance, equipment: liveProfile?.class_id === d.character_class ? liveProfile.equipment : cls.equipment || []};
}
// Poses the creator can preview; every one is a real combat or travel pose.
const PREVIEW_POSES = [['idle', 'Idle'], ['run', 'Move'], ['attack', 'Attack'], ['combat', 'Guard'], ['cast', 'Cast'], ['hit', 'Hit'], ['victory', 'Victory']];
function leadFigure(extra = '') {
  return `<div class="cc-puppet-preview" data-puppet-preview data-preview-pose="${E(state.puppetPreviewPose || 'idle')}" data-preview-facing="${state.puppetPreviewFacing || 1}"><div class="cc-doll ${extra}">${drawDoll(draftAppearanceItem(), 'cc-doll-figure', 'idle')}</div><div class="puppet-preview-controls" role="group" aria-label="Sprite preview"><button type="button" data-puppet-facing aria-label="Turn character">↔ Turn</button>${(extra === 'large' ? PREVIEW_POSES : PREVIEW_POSES.slice(0, 3)).map(([p, label]) => `<button type="button" data-puppet-pose="${p}" aria-pressed="${(state.puppetPreviewPose || 'idle') === p}">${label}</button>`).join('')}</div></div>`;
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
    // Final assigned scores in STR→CHA order (what the sheet and host use), not the raw dice in roll order.
    background: optionBy('backgrounds', d.background).name, abilities: state.roll ? (state.live?.profile?.ability_scores ? ABILITIES.map(a => state.live.profile.ability_scores[a] ?? '?').join(' ') : state.roll.scores.join(' ')) : '',
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
  const description = blurb ? `<details class="cc-more"><summary>See more about ${E(title)}</summary><p class="cc-blurb">${E(blurb)}</p></details>` : '';
  return `<section class="cc-detail" aria-live="polite"><p class="label">What this does</p><h3>${E(title)}</h3>${description}${sections.filter(Boolean).map(([head, html]) => `<div class="cc-detail-row"><span>${E(head)}</span><div>${html}</div></div>`).join('')}</section>`;
}
function identityPage() {
  const d = state.draft; const storyMode = state.pendingMode === 'FORGE';
  const gender = ['female', 'male', 'other'].map(g => `<button type="button" class="cc-seg${d.gender === g ? ' selected' : ''}" data-choice="gender:${g}" aria-pressed="${d.gender === g}">${E(g[0].toUpperCase() + g.slice(1))}</button>`).join('');
  return `<div class="cc-identity">
    <label class="cc-name">Lead name<input name="name" data-create-field="name" type="text" value="${E(d.name || '')}" placeholder="e.g. Ardent Vale" autocomplete="off" maxlength="40" required></label>
    <div class="cc-field"><span class="cc-field-label">Presentation</span><div class="cc-segmented" role="group" aria-label="Gender">${gender}</div><small class="field-help">Sets the sprite’s body presentation. Every choice works in preview and play.</small></div>
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
  const floating = race.floating_bonus ? floatingOpener(race) : '';
  const skillBonus = Object.entries(race.skill_bonuses || {}).map(([s, v]) => `${s} ${signed(v)}`);
  return `<div class="cc-split"><div class="cc-cards race-option-grid">${cards}</div>${detailPanel(race.name || '', blurbs[race.id], [
    ['Abilities', chips([...ABILITIES.filter(a => race.bonuses?.[a]).map(a => `${ABILITY_NAMES[a]} ${signed(race.bonuses[a])}`), race.floating_bonus ? `+${race.floating_bonus.amount} to ${race.floating_bonus.count} of your choice` : ''], 'gold') + (floating ? `<div class="floating-bonus-callout">${floating}</div>` : '')],
    ['Traits', chips((race.traits || []).map(t => t.replaceAll('_', ' ')), 'cap')],
    ['Body', `${E(String(race.size || '—').replace(/^./, c => c.toUpperCase()))} · ${E(race.speed || '—')} ft speed`],
    skillBonus.length || race.extra_skills ? ['Skills', chips([...skillBonus, race.extra_skills ? `+${race.extra_skills} extra trained skill` : ''])] : null,
    ['Pairs well with', chips(pairsWithClasses(race).length ? pairsWithClasses(race) : ['Any class'], 'soft')],
  ])}</div>`;
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
    ['Starting gold', `<span class="cc-gold-badge"><i aria-hidden="true">🪙</i><strong>${E(bg.gold?.dice)}d${E(bg.gold?.sides)} + ${E(bg.gold?.bonus)}</strong> <small>(average ${E(Math.round((bg.gold?.dice || 0) * ((bg.gold?.sides || 0) + 1) / 2 + (bg.gold?.bonus || 0)))})</small></span>`],
    ['Personal effects', `<ul class="cc-gear">${(bg.gear || []).map(item => `<li><strong>${E(item.name)}</strong><small>${E(item.flavor || '')}</small></li>`).join('')}</ul>`],
  ])}</div>`;
}
function abilitiesPage() {
  const d = state.draft; const cls = optionBy('classes', d.character_class);
  if (!state.roll) return `<div class="cc-roll-empty"><div class="cc-dice-art" aria-hidden="true"><i>⚃</i><i>⚄</i><i>⚅</i><i>⚂</i></div><h3>Roll 4d6, drop the lowest, six times.</h3><p>Each score runs from 3 to 18, and 10–11 is average. After the roll, your ${E(cls.name)} priorities (${E((cls.primary || []).map(a => ABILITY_NAMES[a]).join(' and '))}) get your best rolls unless you move them.</p>${button('Roll ability scores', 'roll-abilities', 'primary cc-big')}</div>`;
  const receipt = state.live?.receipt || {}; const rolled = state.roll.scores || [];
  const auto = d.ability_assignment === 'auto';
  const assignment = auto ? automaticAssignment(rolled) : d.ability_assignment;
  const anim = state.rollAnim ? ' is-rolling' : '';
  const strip = `<div class="cc-dice-strip${anim}">${state.roll.rolls.map((row, i) => { let dropped = false; return `<div class="cc-die-set" style="--i:${i}"><div class="cc-dice">${row.dice.map(v => { const drop = !dropped && v === row.dropped; if (drop) dropped = true; return `<span class="${drop ? 'dropped' : ''}">${E(v)}</span>`; }).join('')}</div><strong>${E(row.total)}</strong></div>`; }).join('')}</div>`;
  const rows = ABILITIES.map(a => {
    const base = receipt.assigned_scores?.[a] ?? assignment[a]; const race = receipt.race_bonuses?.[a] || 0;
    const bgb = receipt.background?.ability_bonus?.[a] || 0; const adv = receipt.advancements?.[a] || 0;
    const fin = receipt.final_scores?.[a] ?? base; const primary = (cls.primary || []).includes(a);
    const options = rolled.map(score => {
      const isCurrent = String(assignment[a]) === String(score);
      const otherOwner = !isCurrent && Object.entries(assignment).find(([ab, sc]) => ab !== a && String(sc) === String(score));
      const ownerLabel = otherOwner ? ` (${otherOwner[0]})` : '';
      return `<option value="${E(score)}" ${isCurrent ? 'selected' : ''}>${E(score)}${ownerLabel}</option>`;
    }).join('');
    return `<div class="cc-ab-row${primary ? ' primary' : ''}"><span class="cc-ab-name"><strong>${E(a)}</strong><small>${E(ABILITY_NAMES[a])}${primary ? ' · priority' : ''}</small></span><select data-assign="${E(a)}" aria-label="${E(ABILITY_NAMES[a])} score"><option value="">Auto</option>${options}</select><span class="cc-ab-bonus">${race ? signed(race) : '·'}</span><span class="cc-ab-bonus">${bgb ? signed(bgb) : '·'}</span>${Number(d.level || 1) >= 4 ? `<span class="cc-ab-bonus">${adv ? signed(adv) : '·'}</span>` : ''}<strong class="cc-ab-final">${E(fin ?? '—')}</strong><strong class="cc-ab-mod">${E(fin ? modifier(fin) : '—')}</strong></div>`;
  }).join('');
  const advCol = Number(d.level || 1) >= 4;
  return `<div class="cc-roll-head"><div><h3>Your rolls · total ${E(rolled.reduce((a, b) => a + b, 0))}</h3><p class="notice">Build #${E(state.roll.creation_seed)} · roll ${E((state.roll.roll_set || 0) + 1)} of 2</p></div><div class="actions compact-actions">${auto ? '<span class="cc-badge">Recommended for ' + E(cls.name) + '</span>' : button('Use recommended placement', 'assign-auto', 'secondary')}${state.roll.roll_set === 0 ? button('Use my one reroll', 'roll-abilities', 'secondary') : '<span class="cc-badge muted">Reroll used</span>'}</div></div>
    ${strip}
    <div class="cc-ab-table${advCol ? ' with-adv' : ''}"><div class="cc-ab-head"><span>Ability</span><span>Rolled</span><span>Race</span><span>Bkgd</span>${advCol ? '<span>Adv</span>' : ''}<span>Final</span><span>Mod</span></div>${rows}</div>
    <p class="notice">Pick a rolled score for any ability to place it by hand; the score it replaces moves back to Auto. The modifier is (score − 10) ÷ 2, rounded down, and it is what actually gets added to your rolls.</p>
    ${advancementControls(Number(d.level || 1), cls)}`;
}
function skillRow(skill, row, trained, cls, p, prof, scores) {
  const ability = typeof row === 'object' ? row.ability : row;
  const desc = typeof row === 'object' ? row.description : '';
  const on = trained.includes(skill); const classSkill = (cls.skills || []).includes(skill);
  const bonus = on && p?.skill_bonuses?.[skill] !== undefined ? p.skill_bonuses[skill]
    : Math.floor(((scores[ability] || 10) - 10) / 2) + (on ? prof : 0);
  const open = state.skillOpen === skill;
  return `<button type="button" class="cc-skill${on ? ' selected' : ''}${classSkill ? ' class-skill' : ''}${open ? ' is-expanded' : ''}" data-skill-pick="${E(skill)}" aria-pressed="${on}" aria-expanded="${open}"><span class="cc-skill-top"><strong>${E(skill)}</strong><em>${E(state.roll ? signed(bonus) : ability)}</em></span><small>${E(ability)}${classSkill ? ` · ${E(cls.name)} skill` : ''}</small>${desc ? `<span class="cc-skill-desc">${E(desc)}</span>` : ''}</button>`;
}
function trainingPage() {
  const d = state.draft; const race = optionBy('races', d.race); const cls = optionBy('classes', d.character_class);
  const p = state.live?.profile;
  const count = (cls.skill_count || 0) + (race.extra_skills || 0);
  const manual = d.skill_mode === 'manual';
  const trained = manual ? (d.skills || []) : (state.live?.receipt?.trained_skills || []);
  const prof = p?.proficiency_bonus ?? 2;
  const fromClass = trained.filter(sk => (cls.skills || []).includes(sk)).length;
  const short = fromClass < (cls.skill_count || 0) && manual;
  const spells = cls.spells || [];
  const known = (p?.known_spells || []).map(sp => sp.replace(/@.*$/, ''));
  // The wall of skills moved into an overlay: this step now states the outcome
  // and opens the picker, so it cannot outgrow the stage.
  return `<div class="cc-train">
    <div class="cc-train-row">
      ${opener({action: 'overlay-open:skills', label: 'Trained skills',
        value: `${trained.length} of ${count} chosen`,
        hint: `Pick ${count}${race.extra_skills ? ` (${race.name} adds one)` : ''}, at least ${cls.skill_count} from the ${cls.name} list.`})}
      ${spells.length ? opener({action: 'overlay-open:spells', label: 'Spells',
        value: d.spell_mode === 'manual' ? `${(Array.isArray(d.spells) ? d.spells : []).length} chosen by hand` : `${known.length} chosen automatically`,
        hint: `Budget ${state.draft.spell_budget || Number(d.level || 1) * 5} points · the host enforces the rank cap.`})
        : '<div class="cc-train-none"><strong>No spellcasting</strong><small>' + E(cls.name) + ' has no spell list. Nothing to choose here.</small></div>'}
    </div>
    <div class="cc-train-picked">
      <p class="label">Trained now</p>
      ${trained.length ? chips(trained.map(sk => `${sk} ${state.roll && p?.skill_bonuses?.[sk] !== undefined ? signed(p.skill_bonuses[sk]) : ''}`.trim()), 'gold') : '<span class="cc-chip soft">None yet</span>'}
      ${known.length ? `<p class="label">Spells</p>${chips(known)}` : ''}
      <p class="notice">${manual ? 'Choosing by hand.' : 'Automatic picks are always legal.'} Trained skills add your proficiency bonus, ${E(signed(prof))}.${short ? ` <strong class="cc-warn-inline">Need ${E(cls.skill_count - fromClass)} more class skill${cls.skill_count - fromClass === 1 ? '' : 's'}.</strong>` : ''}</p>
      ${manual ? `<div class="actions compact-actions">${button('Use automatic picks', 'skills-auto', 'secondary')}</div>` : ''}
    </div>
  </div>`;
}
function lookFieldChoice(field) {
  const d = state.draft; const fields = state.options?.appearance?.fields || {};
  const spec = fields[field]; if (!spec) return '';
  const current = state.live?.profile?.appearance || {};
  const rows = (spec.options || []).filter(row => !row.races || row.races.includes(d.race));
  const chosen = d.appearance?.[field] || current[field]?.id || rows[0]?.id;
  // Colour fields also take any colour: the picker stores '#rrggbb' and the host validates it.
  const custom = spec.custom ? (() => {
    const hex = typeof chosen === 'string' && /^#[0-9a-f]{6}$/i.test(chosen) ? chosen.toLowerCase() : (current[field]?.id === 'custom' && current[field].hex) || rows.find(row => row.id === chosen)?.hex || '#888888';
    const on = typeof chosen === 'string' && chosen.startsWith('#');
    return `<label class="cc-look swatch cc-look-custom${on ? ' selected' : ''}" title="Pick any colour"><input type="color" data-look-colour="${E(field)}" value="${E(hex)}" aria-label="${E(spec.label)}: custom colour"><span>Custom</span></label>`;
  })() : '';
  return `<fieldset class="cc-look-group"><legend>${E(spec.label)}</legend>${spec.note ? `<p class="cc-look-note">${E(spec.note)}</p>` : ''}<div class="cc-look-options">${rows.map(row => `<button type="button" class="cc-look${row.hex ? ' swatch' : ''}${chosen === row.id ? ' selected' : ''}" data-look="${E(field)}:${E(row.id)}" aria-pressed="${chosen === row.id}" title="${E(row.name)}">${row.hex && /^#[0-9a-f]{6}$/i.test(row.hex) ? `<i style="background:${row.hex}"></i>` : ''}<span>${E(row.name)}</span></button>`).join('')}${custom}</div></fieldset>`;
}
function lookGroupSummary(group) {
  const d = state.draft; const fields = state.options?.appearance?.fields || {};
  const current = state.live?.profile?.appearance || {};
  const names = group.fields.filter(f => fields[f]).map(f => {
    const rows = (fields[f].options || []).filter(row => !row.races || row.races.includes(d.race));
    const id = d.appearance?.[f] || current[f]?.id || rows[0]?.id;
    return typeof id === 'string' && id.startsWith('#') ? 'Custom' : rows.find(row => row.id === id)?.name;
  }).filter(Boolean);
  return names.join(' · ') || 'Default';
}
function lookPage() {
  const fields = state.options?.appearance?.fields || {};
  const touched = Object.keys(state.draft.appearance || {}).length;
  // Fourteen option walls do not fit a fixed stage, and they never needed to:
  // the paperdoll is the point of this step. Each group opens over it.
  return `<div class="cc-look-layout">
    <div class="cc-look-stage">${leadFigure('large')}<p class="cc-look-caption">The same paperdoll is used in the final sheet, roster and combat.</p>${(state.live?.notice || []).length ? `<p class="cc-look-notice"><span class="label">People will notice</span>${chips(state.live.notice)}</p>` : ''}</div>
    <div class="cc-look-groups">
      <p class="notice">Presentation only — nothing here changes a number. ${touched ? `${E(touched)} field${touched === 1 ? '' : 's'} customised.` : 'All fields are at their defaults.'}</p>
      <div class="cc-look-openers">${LOOK_GROUPS.map((group, i) => group.fields.some(f => fields[f])
        ? opener({action: `overlay-open:look:${i}`, label: group.label, value: lookGroupSummary(group),
                  hint: `${group.fields.filter(f => fields[f]).length} options`})
        : '').join('')}</div>
      <div class="actions compact-actions">${button('Surprise me', 'surprise-step', 'secondary')}</div>
    </div>
  </div>`;
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
  // This is the one screen that must never scroll: Confirm lives on it. Build
  // notes and the receipt move to overlays -- they are detail, not the numbers
  // the Confirm decision rests on, which all stay visible.
  return `<div class="cc-summary">
    <header class="cc-sum-head"><div class="cc-sum-figure">${leadFigure('large')}</div><div class="cc-sum-id">
      <p class="eyebrow">Final sheet · not saved</p><h2>${E(p.name || state.draft.name)}</h2>
      <p class="cc-sum-line"><strong>${E(p.race)} ${E(p.character_class)}</strong> · level ${E(p.level)} · ${E(bg.name)} · Build #${E(r.creation_seed)}</p>
      ${notes ? `<p class="cc-sum-arch"><span class="cc-archetype big">${E(notes.archetype)}</span>${E(sentenceCase(notes.summary.split(': ').slice(1).join(': ')))}</p>${ratingBars(notes.ratings)}` : ''}
    </div>
      <div class="cc-sum-more">${notes ? opener({action: 'overlay-open:notes', label: 'Build notes', value: `${notes.strengths.length} strengths · ${notes.watchouts.length} to watch`, hint: 'Good at, watch out, synergy and how to play it'}) : ''}${opener({action: 'overlay-open:receipt', label: 'Creation receipt', value: `hash ${c.build_hash.slice(0, 12)}`, hint: 'The deterministic record behind every number here', ariaLabel: 'Show deterministic creation receipt'})}</div>
    </header>
    <section class="cc-sheet cc-sheet-abilities"><p class="label">Abilities</p><div class="cc-score-row">${ABILITIES.map((a, i) => `<div class="cc-score" style="--i:${i}" title="${E(breakdown(a))}"><span>${E(a)}</span><strong>${E(scores[a])}</strong><em>${E(modifier(scores[a]))}</em><small>${E(breakdown(a))}</small></div>`).join('')}</div></section>
    <div class="cc-sum-cols">
      <section class="cc-sheet"><p class="label">Combat</p><div class="cc-tiles">${tile('Hit points', p.max_hp, hpFormula(p), 0)}${tile('Armor class', p.armor_class, acFormula(p), 1)}${tile('Initiative', signed(p.initiative_bonus), 'DEX modifier', 2)}${tile('Speed', `${p.speed} ft`, '', 3)}${tile('Proficiency', signed(p.proficiency_bonus), `levels ${Math.floor((p.level - 1) / 4) * 4 + 1}–${Math.floor((p.level - 1) / 4) * 4 + 4}`, 4)}${tile('Passive Perception', notes?.derived?.passive_perception ?? '—', '10 + Perception', 5)}${rules.attacks > 1 ? tile('Attacks', rules.attacks, 'per Attack action', 6) : ''}${rules.spell_save_dc ? tile('Spell save DC', rules.spell_save_dc, `8 + prof + ${p.class_id === 'magician' ? 'INT' : 'WIS'}`, 7) : ''}${rules.spell_save_dc ? tile('Spell attack', signed(rules.spell_attack_bonus), 'prof + casting mod', 8) : ''}${rules.sneak_attack_dice ? tile('Sneak Attack', `${rules.sneak_attack_dice}d6`, '', 9) : ''}</div>
        ${weapon.length ? `<div class="cc-attacks">${weapon.map(w => `<div><strong>${E(w.name)}</strong><span>${E(signed(w.attack_bonus))} to hit</span><span>${E(w.damage_dice)} ${E(signed(w.damage_modifier))}</span></div>`).join('')}</div>` : ''}</section>
      <section class="cc-sheet"><p class="label">Saving throws</p><div class="cc-kv">${ABILITIES.map(a => `<div class="${(optionBy('classes', p.class_id).saves || []).includes(a) ? 'prof' : ''}"><span>${E(ABILITY_NAMES[a])}</span><strong>${E(signed(rules.saves?.[a]))}</strong></div>`).join('')}</div>
        <p class="label">Trained skills</p><div class="cc-kv">${Object.entries(p.skill_bonuses || {}).map(([sk, b]) => `<div title="${E(getSkillDescription(sk) || '')}"><span>${E(sk)}</span><strong>${E(signed(b))}</strong></div>`).join('')}</div></section>
      <section class="cc-sheet"><p class="label">Features</p>${chips(p.features || [])}${p.known_spells?.length ? `<p class="label">Spells · ${E(r.spell_points_spent)}/${E(r.spell_budget)} pts</p>${chips(p.known_spells.map(sp => sp.replace(/@.*$/, '')))}` : ''}
        <p class="label">Starting kit</p><ul class="cc-gear">${(p.equipment || []).map(item => `<li><strong>${E(item.display_name || item.name)}</strong></li>`).join('')}</ul>
        <p class="notice">Gold ${E(bg.starting_gold)} · origin ${E(p.origin_item?.name || '—')}${p.heirloom_item?.name ? ` · heirloom ${E(p.heirloom_item.name)}` : ''}</p></section>
    </div>
    <div class="cc-confirm">${button('Confirm and create run', 'confirm-build', 'primary cc-big')}<small>Saves Build #${E(r.creation_seed)} and starts the descent.</small></div>
  </div>`;
}
function creatorOverlay() {
  const o = state.overlay; if (!o) return '';
  const d = state.draft; const cls = optionBy('classes', d.character_class); const race = optionBy('races', d.race);
  const p = state.live?.profile; const prof = p?.proficiency_bonus ?? 2; const scores = p?.ability_scores || {};
  if (o.kind === 'skills') {
    const skills = state.options?.skills || {};
    const count = (cls.skill_count || 0) + (race.extra_skills || 0);
    const manual = d.skill_mode === 'manual';
    const trained = manual ? (d.skills || []) : (state.live?.receipt?.trained_skills || []);
    const fromClass = trained.filter(sk => (cls.skills || []).includes(sk)).length;
    const short = Math.max(0, (cls.skill_count || 0) - fromClass);
    return overlayShell({
      title: `Trained skills · ${trained.length} of ${count}`,
      lede: `Pick ${count}${race.extra_skills ? ` — ${race.name} grants one extra` : ''}. At least ${cls.skill_count} must come from the ${cls.name} list, shown with a gold edge. Click a skill again to read what it covers.`,
      body: `<div class="cc-skill-grid">${Object.entries(skills).map(([skill, row]) => skillRow(skill, row, trained, cls, p, prof, scores)).join('')}</div>`,
      foot: `<span class="cc-overlay-count"><strong>${trained.length}</strong> of ${count} chosen${short && manual ? ` · ${short} more must be a ${E(cls.name)} skill` : ''}</span>${manual ? button('Use automatic picks', 'skills-auto', 'secondary') : ''}`,
    });
  }
  if (o.kind === 'floating') {
    const rule = race.floating_bonus; if (!rule) return '';
    const manual = Array.isArray(d.floating_bonuses);
    const selected = manual ? d.floating_bonuses : (state.live?.receipt?.floating_bonuses || []);
    return overlayShell({
      title: `Ancestry bonuses · ${selected.length} of ${rule.count}`,
      lede: `Choose ${rule.count} abilities for the floating ${rule.amount > 0 ? '+' : ''}${rule.amount} bonus. Charisma is excluded.`,
      body: floatingOverlayBody(race),
      foot: `<span class="cc-overlay-count"><strong>${selected.length}</strong> of ${rule.count} chosen</span>`,
    });
  }
  if (o.kind === 'spells') {
    const spells = cls.spells || [];
    const manual = d.spell_mode === 'manual';
    const budget = Number(d.spell_budget || Number(d.level || 1) * 5);
    const selected = Array.isArray(d.spells) ? d.spells : [];
    return overlayShell({
      title: `Spells · ${cls.name}`,
      lede: `Budget ${budget} points. The host enforces the rank cap and refuses an illegal set, so an automatic pick is always safe.`,
      body: manual
        ? `<div class="check-grid spell-grid">${spells.map(spell => `<label class="check-chip"><input type="checkbox" data-spell="${E(spell)}" ${selected.includes(spell) ? 'checked' : ''}><span>${E(spell.replace('@5e', ''))}<small>${E(spell.includes('@HSR') ? 'HSR signature' : '5e spell')}</small></span></label>`).join('')}</div>`
        : `<p class="notice">${E(spells.length)} class spells are available. The host picks a deterministic legal set inside the budget.</p>${(p?.known_spells || []).length ? `<p class="label">Chosen for you</p>${chips(p.known_spells.map(sp => sp.replace(/@.*$/, '')))}` : ''}`,
      foot: `<span class="cc-overlay-count">Budget <strong>${budget}</strong> points</span><label class="cc-overlay-budget">Budget<input type="number" min="0" max="${E(Number(d.level || 1) * 5)}" value="${E(budget)}" data-create-field="spell_budget" aria-label="Spell budget"></label>${button(manual ? 'Use automatic selection' : 'Choose manually', manual ? 'spells-auto' : 'spells-manual', 'secondary')}`,
    });
  }
  if (o.kind === 'look') {
    const group = LOOK_GROUPS[Number(o.arg) || 0]; if (!group) return '';
    const fields = state.options?.appearance?.fields || {};
    return overlayShell({
      title: group.label,
      lede: 'Cosmetic only — nothing in here changes a number. The paperdoll behind this updates as you pick.',
      body: group.fields.filter(f => fields[f]).map(lookFieldChoice).join(''),
      foot: `${button('Surprise me', 'surprise-step', 'secondary')}`,
    });
  }
  if (o.kind === 'notes') {
    const notes = state.live?.notes; if (!notes) return '';
    const list = (items, cls2) => `<ul class="cc-notes-list ${cls2}">${items.map(t => `<li>${E(t)}</li>`).join('')}</ul>`;
    return overlayShell({
      title: `Build notes · ${notes.archetype}`,
      lede: sentenceCase(notes.summary.split(': ').slice(1).join(': ')),
      body: `<div class="cc-notes-grid"><div><h4>Good at</h4>${list(notes.strengths, 'good')}</div><div><h4>Watch out</h4>${list(notes.watchouts, 'warn')}</div><div><h4>Synergy</h4>${list(notes.synergies, 'syn')}</div></div>${notes.tip ? `<p class="cc-tip"><strong>How to play it:</strong> ${E(notes.tip)}</p>` : ''}`,
    });
  }
  if (o.kind === 'receipt') {
    const c = state.live; if (!c) return '';
    return overlayShell({
      title: 'Deterministic creation receipt',
      lede: `Hash ${String(c.build_hash || '').slice(0, 12)}. The same seed and the same choices always reproduce this exactly.`,
      body: `<pre class="cc-receipt-pre">${E(JSON.stringify(c.receipt || {}, null, 2))}</pre>`,
    });
  }
  return '';
}
function creator() {
  const step = createStep(); const info = CREATE_STEPS[step];
  const pages = {identity: identityPage, ancestry: ancestryPage, class: classPage, background: backgroundPage, abilities: abilitiesPage, training: trainingPage, look: lookPage, summary: summaryPage};
  const blocked = stepValid(step);
  const noLead = ['look', 'summary'].includes(info.id);
  const dir = state.stepAnim || ''; state.stepAnim = ''; const rolling = state.rollAnim; state.rollAnim = false;
  const surprise = step > 0 && step < CREATE_STEPS.length - 1 ? button('Surprise me', 'surprise-step', 'secondary cc-surprise') : '';
  const next = step < CREATE_STEPS.length - 1
    ? `<button type="button" class="action primary cc-next" data-action="step-next" ${blocked ? 'aria-disabled="true"' : ''}>${step === CREATE_STEPS.length - 2 ? 'Review final sheet' : `Next: ${E(CREATE_STEPS[step + 1].label)}`} ›</button>` : '';
  void rolling;
  const confirmBtn = step === CREATE_STEPS.length - 1 ? button('Confirm and create run', 'confirm-build', 'action primary cc-confirm-nav') : '';
  const shell = `<section class="card cc-shell" data-create-step="${E(info.id)}">
    <header class="cc-header"><div><p class="eyebrow">New lead · Build #${E(state.draft.creation_seed || '—')} · step ${step + 1} of ${CREATE_STEPS.length}</p><h2>${E(info.title)}</h2><p class="cc-lede">${E(info.lede)}</p></div><nav class="cc-top-nav" aria-label="Character creation navigation">${step > 0 ? button('Back one step', 'step-back', 'secondary') : button('Return to lead selection', 'back', 'secondary')}<button type="button" class="action secondary" data-action="title">Main menu</button></nav></header>
    ${stepRail(step)}
    <div class="cc-body${noLead ? ' no-lead' : ''}"><div class="cc-main cc-enter-${E(dir)}" id="character-form">${pages[info.id]()}</div>${noLead ? '' : leadPanel()}</div>
    <footer class="cc-nav">${step > 0 ? button('‹ Back', 'step-back', 'secondary') : button('‹ Menu', 'back', 'secondary')}<span class="cc-nav-mid">${blocked ? `<small class="cc-blocked">${E(blocked)}</small>` : ''}${surprise}</span>${next}${confirmBtn}${step === CREATE_STEPS.length - 1 ? button('Start over', 'restart', 'secondary') : ''}</footer>
  </section>`;
  // The stage is the whole creator's viewport: one fixed-ratio box, scaled to
  // the window, with overlays layered inside it rather than over the document.
  return `<div class="hsr-stage-frame"><div class="hsr-stage">${shell}${creatorOverlay()}</div></div>`;
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
  const reply = await state.client.request('allocate_creation_seed', {});
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
  const d = state.draft;
  // A new random seed every press; the seed stays visible and editable, so a
  // build you like can be reproduced by typing the same seed back in.
  d.creation_seed = randomSeed(); d.seed_auto = false;
  state.roll = null; state.preview = null; state.live = null; state.liveError = '';
  const reply = result(await state.client.request('randomize_build', {creation_seed: d.creation_seed, name: d.name || '', level: Number(d.level || 1)}));
  const b = reply.result.build;
  Object.assign(d, {race: b.race, character_class: b.character_class, background: b.background, gender: b.gender, appearance: b.appearance,
    roll_set: 0, ability_assignment: 'auto', floating_bonuses: 'auto', advancements: 'auto', advancement_mode: 'auto', skills: 'auto', skill_mode: 'auto',
    spells: 'auto', spell_mode: 'auto', spell_budget: 0});
  if (!String(d.name || '').trim() || d.name_auto) { d.name = seededName(d.creation_seed, d.race); d.name_auto = true; }
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
  let lookColourTimer = 0;
  document.querySelectorAll('[data-look-colour]').forEach(node => {
    const apply = final => {
      state.draft.appearance = {...(state.draft.appearance || {}), [node.dataset.lookColour]: node.value.toLowerCase()};
      clearTimeout(lookColourTimer);
      lookColourTimer = setTimeout(() => { persistUiState(); render(); if (final) scheduleLivePreview(); }, final ? 0 : 90);
    };
    node.oninput = () => apply(false); node.onchange = () => apply(true);
  });
  document.querySelectorAll('[data-look]').forEach(node => node.onclick = () => {
    const [field, id] = node.dataset.look.split(':');
    state.draft.appearance = {...(state.draft.appearance || {}), [field]: id}; persistUiState(); render(); scheduleLivePreview();
  });
  const name = document.querySelector('.cc-name input');
  if (name) {
    name.oninput = () => { state.draft.name = name.value; state.draft.name_auto = false; persistUiState(); const next = document.querySelector('.cc-next'); const ok = !!name.value.trim(); next?.setAttribute('aria-disabled', ok ? 'false' : 'true'); document.querySelector('.cc-blocked')?.toggleAttribute('hidden', ok); };
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
  if (action === 'overlay-close') { closeOverlay(); return true; }
  if (action.startsWith('overlay-open:')) {
    const [, kind, arg = ''] = action.split(':');
    openOverlay(kind, arg);
    return true;
  }
  // Any navigation closes an open overlay first, so a step change never leaves
  // a panel floating over the wrong screen.
  if (state.overlay && (action.startsWith('step-') || action === 'restart' || action === 'back')) state.overlay = null;
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
  const startAction = isSandbox ? 'mode:SANDBOX' : 'mode:FORGE';
  const emptyView = `<div class="empty-state"><span class="empty-icon" aria-hidden="true">✦</span><p>${E(emptyCopy)}</p><div class="actions">${button(isSandbox ? 'Start Simulation Run' : 'Start New Story', startAction, 'primary')}</div></div>`;
  const runList = state.runs.length ? `<div class="run-list">${state.runs.map(run => {
    const id = typeof run === 'string' ? run : run.run_id;
    return `<article class="run-row"><div class="run-row-info"><strong>${E(runTitle(run, id))}</strong><small>${E(runSubtitle(run, id))}</small></div><div class="run-row-actions">${button(verb, `load:${id}`, 'primary')}${button('New seed', `play-again:fresh:${id}`, 'secondary')}${button('Replay seed', `play-again:same:${id}`, 'secondary')}</div></article>`;
  }).join('')}</div>` : emptyView;
  return `<div class="mode-menu">${breadcrumb('Main Menu', isSandbox ? 'Simulation Mode' : 'Story Mode', heading)}${atmosphere('runs', heading, 'Choose any host-reported run and resume it through the same public engine contract.')}${card(heading, `${runList}<div class="mode-menu-footer"><div class="footer-left">${button('Refresh list', 'refresh-runs', 'secondary')}</div><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
}

// The resting doll reflects only the chosen maneuver's stance. Strikes,
// hits and misses are transient beats the combat director plays over it, so
// a figure never freezes mid-swing after the host's reply.
function characterFigure(item = {}, extra = '', pose = 'idle', options = {}) {
  // Only a figure with an actor id can wear a stance; id-less art (the
  // Champions picker) must not match a null maneuver as undefined === undefined.
  const recent = state.lastManeuver;
  const maneuver = item.id && recent?.actor === item.id && Date.now() - recent.at < 2200 ? recent.maneuver : null;
  return drawDoll(item, extra, pose, {maneuver, ...options});
}
function scenePosition(item = {}, index = 0) {
  const p = Array.isArray(item.position) ? item.position : [index ? 40 : 10, index * 10, 0];
  const x = Math.max(5, Math.min(90, Number(p[0] || 0) / 120 * 100));
  const z = Math.max(0, Number(p[2] || 0));
  return `left:${x}%;bottom:${Math.min(62, 21 + z * .45)}px;`;
}
// Host positions are true arena feet; at melee range two figures would stand
// on one another. The stage keeps their order and height but spreads them to
// a readable minimum gap, compressing evenly if the row would overflow.
const STAGE_MIN_GAP = 16; const STAGE_MIN_X = 6; const STAGE_MAX_X = 90;
function stageLayout(fighters = [], overrides = {}) {
  const rows = fighters.map((item, index) => {
    const position = overrides[item.id] || item.position;
    const p = Array.isArray(position) ? position : [index ? 40 : 10, index * 10, 0];
    return {id: item.id || `slot-${index}`, x: Math.max(0, Math.min(120, Number(p[0] || 0))) / 120 * 100, z: Math.max(0, Number(p[2] || 0)), side: index >= party().length ? 1 : 0};
  }).sort((a, b) => a.x - b.x || a.side - b.side);
  rows.forEach((row, i) => { row.x = Math.max(row.x, i ? rows[i - 1].x + STAGE_MIN_GAP : STAGE_MIN_X); });
  const last = rows[rows.length - 1];
  if (last && last.x > STAGE_MAX_X) {
    const span = STAGE_MAX_X - STAGE_MIN_X; const used = last.x - rows[0].x || 1;
    const start = rows.length > 1 ? STAGE_MIN_X : Math.min(rows[0].x, STAGE_MAX_X);
    const origin = rows[0].x;
    rows.forEach(row => { row.x = start + (row.x - origin) * Math.min(1, span / used); });
  }
  return new Map(rows.map(row => [row.id, `left:${row.x.toFixed(2)}%;bottom:${Math.min(62, 21 + row.z * .45)}px;`]));
}
// Everything a stage draws over a combatant, shared by the ground and flight
// stages so both read the same way: HP bar, badges, turn marker, target ring,
// state classes, and an accessible label/role for click and keyboard targeting.
function stageOverlay(item = {}, index = 0) {
  const c = state.preferences.combat;
  const id = item.id || `slot-${index}`;
  const enemy = index >= party().length;
  const hp = Number(item.hp); const max = Number(item.max_hp);
  const down = Number.isFinite(hp) && hp <= 0;
  const combat = state.view?.combat;
  const active = Boolean(combat && !combat.complete && combat.current === id);
  const focused = enemy && state.focusTarget === id && !down;
  const picking = Boolean(state.actionPicker) && actionTargets(state.actionPicker.action).some(choice => choice.value === id);
  const selected = !enemy && actor().id === id;
  // A queued step would leave this foe's reach: warn before the host rolls it.
  const threatened = enemy && !down && (state.threatWarning?.foes || []).includes(id);
  const showBar = c.hpBars === 'all' || (c.hpBars === 'enemies' && enemy) || (c.hpBars === 'party' && !enemy);
  const ratio = Number.isFinite(hp) && max > 0 ? Math.max(0, Math.min(1, hp / max)) : null;
  const tone = ratio == null ? 'none' : ratio <= .25 ? 'crit' : ratio <= .5 ? 'low' : 'ok';
  const effects = visibleEffects(item);
  const overlay = [
    c.turnMarker && active ? '<span class="doll-turn" aria-hidden="true"></span>' : '',
    c.targetRing && (focused || picking) ? `<span class="doll-ring${picking ? ' is-picking' : ''}" aria-hidden="true"></span>` : '',
    threatened ? '<span class="doll-threat" aria-hidden="true"></span>' : '',
    showBar && ratio != null ? `<span class="doll-hp" data-tone="${tone}" aria-hidden="true"><i style="width:${(ratio * 100).toFixed(1)}%"></i>${c.hpNumbers ? `<em>${Math.max(0, hp)}/${max}</em>` : ''}</span>` : '',
    c.statusChips ? effectRack({member: item, E}) : '',
  ].join('');
  const flags = [enemy && 'opponent', active && 'is-active-turn', focused && 'is-targeted', threatened && 'is-threatening', picking && 'is-pickable', selected && 'is-selected', down && 'is-down'].filter(Boolean).join(' ');
  const label = `${item.name || id}${ratio != null ? `, ${Math.max(0, hp)} of ${max} HP` : ''}${active ? ', acting now' : ''}${focused ? ', targeted' : ''}${down ? ', down' : ''}${effects.length ? `, ${effects.length} effects: ${effects.map(effectLabel).join('; ')}` : ''}`;
  return {id, overlay, flags, attrs: {'data-stage-actor': id, role: 'button', tabindex: '0', 'aria-label': label, 'aria-pressed': focused || selected ? 'true' : 'false'}};
}
// Battle-line pose from public state only: fallen, badly hurt, acting, waiting.
function battlePose(item = {}) {
  const combat = state.view?.combat;
  if (!combat?.formation) return 'combat';
  const hp = Number(item.hp); const max = Number(item.max_hp);
  if (Number.isFinite(hp) && hp <= 0) return 'ko';
  if (Number.isFinite(hp) && max > 0 && hp / max <= .25) return 'kneel';
  return combat.current === item.id ? 'ready' : 'battleIdle';
}
// A giant's box is bigger than a person's (size class from the host's rules), so its
// paper doll and its hit area both are; feet stay where the layout puts them.
function figureSizeStyle(item = {}) {
  const vis = bodyOf(item).vis;
  return Math.abs(vis - 1) < .02 ? '' : `width:${(184 * vis).toFixed(0)}px;height:${(316 * vis).toFixed(0)}px;margin-left:${(-(vis - 1) * 92).toFixed(0)}px;`;
}
function battleCharacterFigure(item = {}, index = 0, layout = null) {
  const o = stageOverlay(item, index);
  return characterFigure(item, `battle-actor ${o.flags}`, battlePose(item), {
    style: figureSizeStyle(item) + (layout?.get(o.id) || scenePosition(item, index)), overlay: o.overlay,
    // In a fight Doran holds the Cleaver out in front of him with one hand, at ease.
    attrs: visualIdentity(item) === 'doran' ? {...o.attrs, 'data-carry': 'ready'} : o.attrs,
  });
}
// Minimal DOM morph: keeps elements whose tag matches and only patches what
// changed, so CSS transitions (the HP bar width) run instead of snapping and
// already-decoded images are not re-requested.
// Keyed reconciliation: children carrying data-key (or id) are matched by key,
// so inserting at the top of a list moves nodes instead of rewriting every
// sibling below it (focus, canvases and scroll survive). Unkeyed children keep
// the original positional morph.
const nodeKey = node => node.nodeType === Node.ELEMENT_NODE ? (node.getAttribute('data-key') || node.id || null) : null;
function morphChildren(target, source) {
  const to = [...source.childNodes];
  const keyed = new Map();
  target.childNodes.forEach(node => { const key = nodeKey(node); if (key && !keyed.has(key)) keyed.set(key, node); });
  const used = new Set();
  to.forEach((next, i) => {
    const key = nodeKey(next);
    let cur = key ? keyed.get(key) : target.childNodes[i];
    if (cur && (used.has(cur) || (!key && nodeKey(cur) && to.some(n => nodeKey(n) === nodeKey(cur))))) cur = null;
    const slot = target.childNodes[i] || null;
    if (!cur || cur.nodeType !== next.nodeType || cur.nodeName !== next.nodeName) {
      const fresh = next.cloneNode(true);
      if (cur && !key && cur === slot) cur.replaceWith(fresh); else target.insertBefore(fresh, slot);
      used.add(fresh); return;
    }
    if (cur !== slot) target.insertBefore(cur, slot);
    used.add(cur);
    if (cur.nodeType === Node.TEXT_NODE) { if (cur.data !== next.data) cur.data = next.data; return; }
    if (cur.nodeType !== Node.ELEMENT_NODE) return;
    syncAttributes(cur, next);
    if (cur.innerHTML !== next.innerHTML) morphChildren(cur, next);
  });
  [...target.childNodes].slice(to.length).forEach(node => node.remove());
}
function syncAttributes(target, source) {
  [...target.attributes].forEach(({name}) => { if (!source.hasAttribute(name)) target.removeAttribute(name); });
  [...source.attributes].forEach(({name, value}) => { if (target.getAttribute(name) !== value) target.setAttribute(name, value); });
}
function keepArcadeRoot(previous) {
  const next = document.querySelector('#app [data-arcade-root]');
  if (!previous || !next) return;
  // The header's wave/frame text is kept current by updateArcadeStatus().
  next.replaceWith(previous);
}
function reconcileBattleStage(previous) {
  const next = document.querySelector('#app .combat-stage');
  if (!previous || !next || previous.dataset.stageRun !== next.dataset.stageRun) return;
  const kept = new Map([...previous.querySelectorAll(':scope > [data-stage-actor]')].map(node => [node.dataset.stageActor, node]));
  const anchor = previous.querySelector(':scope > .scene-frame-label');
  next.querySelectorAll(':scope > [data-stage-actor]').forEach(fresh => {
    const old = kept.get(fresh.dataset.stageActor);
    if (!old) { previous.insertBefore(fresh, anchor); return; }
    kept.delete(fresh.dataset.stageActor);
    // A figure mid-beat belongs to the combat director until the queue drains.
    if (old.dataset.beat) return;
    syncAttributes(old, fresh);
    if (old.innerHTML !== fresh.innerHTML) morphChildren(old, fresh);
  });
  kept.forEach(node => node.remove());
  const label = next.querySelector(':scope > .scene-frame-label');
  if (anchor && label && anchor.innerHTML !== label.innerHTML) anchor.innerHTML = label.innerHTML;
  previous.querySelector(':scope > .battle-empty')?.remove();
  const empty = next.querySelector(':scope > .battle-empty'); if (empty) previous.insertBefore(empty, anchor);
  syncAttributes(previous, next);
  next.replaceWith(previous);
}
function flightActor(item = {}, index = 0, arena = {}, layout = null) {
  const row = (arena.actors || []).concat(arena.opposition || []).find(value => value.id === item.id) || {};
  const x = Math.max(4, Math.min(92, Number(row.x ?? 10) / 120 * 100));
  const y = Math.max(8, Math.min(78, 78 - Number(row.y ?? 10) / 120 * 62));
  const z = Math.max(0, Number(row.z || 0));
  const o = stageOverlay(item, index);
  // Every combatant is drawn by its paperdoll rig. Wren floats in guard and
  // manifests her wings only once she is actually airborne (DM041_D).
  // (The wren-flight-wings-v1.png sprite sheet was retired 2026-09-25.)
  const airborne = z > 0 || Number(item.fly_speed) > 0;
  const doll = characterFigure(item.identity === 'wren' ? {...item, wings: airborne} : item, 'flight-doll', 'combat');
  const attrs = Object.entries(o.attrs).map(([key, value]) => ` ${key}="${E(value)}"`).join('');
  return `<div class="flight-actor ${o.flags.includes('opponent') ? 'flight-opponent' : 'flight-player'} ${o.flags}" style="${layout?.get(o.id) || `left:${x}%;top:${y}%;`}transform:translateZ(${z}px)"${attrs}><div class="flight-glow"></div>${doll}${o.overlay}<span>${E(item.name || item.id)}</span></div>`;
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
  const arena = state.view?.flight_arena;
  const formation = state.view?.combat?.formation;
  const packed = fighters.length > 4;
  const maxSide = Math.max(party().length, (state.view?.opposition || []).length);
  const density = packed ? ' is-crowded' : '';
  const packedLayout = packed ? ffLayout(fighters, formation || {}, party().length) : null;
  if (arena) return `<section class="illustrated-scene scene-battle flight-stage combat-stage${density}" data-combatants="${fighters.length}" data-max-side="${maxSide}" data-stage-run="${E(state.runId || '')}:flight" data-scene-theme="reliquary" aria-label="Live flight combat arena">
    <div class="scene-moon"></div><div class="flight-cloud cloud-one"></div><div class="flight-cloud cloud-two"></div>
    <div class="flight-arena-label"><strong>Wren's flight</strong><small>Host-resolved aerial encounter</small></div>
    ${fighters.map((item, index) => flightActor(item, index, arena, packedLayout)).join('')}
    <div class="flight-reticle" aria-hidden="true"></div>
  </section>`;
  const layout = packedLayout || (formation ? ffLayout(fighters, formation, party().length) : stageLayout(fighters));
  const c = state.view?.combat || {};
  const names = Object.fromEntries(fighters.map(item => [item.id, item.name || item.id]));
  const down = new Set(fighters.filter(item => Number(item.hp) <= 0 || item.alive === false).map(item => item.id));
  return `<section class="illustrated-scene scene-battle battle-stage combat-stage${formation || packed ? ' ff-stage' : ''}${density}" data-combatants="${fighters.length}" data-max-side="${maxSide}" data-stage-run="${E(state.runId || '')}:ground" data-scene-theme="reliquary" aria-label="Live combat encounter">
    <div class="scene-moon"></div><div class="scene-mountains back"></div><div class="scene-mountains front"></div><div class="scene-road"></div>
    ${formation ? turnOrderStrip({order: c.order || [], current: c.current, names, down, E}) : ''}
    ${fighters.map((item, index) => battleCharacterFigure(item, index, layout)).join('') || '<p class="notice battle-empty">No public combatants reported.</p>'}
    <div class="scene-frame-label" data-action="toggle-location" role="button" tabindex="0"><strong>${E(state.view?.room?.name || 'The Reliquary')}</strong><small>Live host-resolved encounter</small></div>
  </section>${state.preferences.combat.inspector ? combatInspector() : ''}`;
}
// ---- Main display ------------------------------------------------------------
// The room scene is one persistent stage (stage-view.js): a painted set for the
// place, figures that turn and walk a depth plane, doors that open, props that
// take a blow, all lit by the same lamps. The host still decides every
// outcome. The stage draws the walk, carries a click to the same host calls the
// menus use, and animates the result. render() swaps a placeholder for the
// live stage each time, so nothing restarts when the screen redraws.
function sceneWorld(kind = 'room') {
  return `<div class="world-stage-slot" data-world-slot data-scene-kind="${E(kind)}"></div>${SCENE_END}`;
}
function placeName(id) { return readable(id).replace(/[-_]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
function findRoomObject(id) {
  const objects = state.view?.room?.objects || {};
  return objects[id] || Object.values(objects).find(row => String(row?.object_id || row?.id) === String(id)) || null;
}
let worldStage = null;
// The host's clock is seconds since the run began (28800 = 08:00). The set is
// painted for that hour; a scene with no clock keeps its named backdrop.
function worldTimeOfDay(view = state.view) {
  if (view?.scene?.time) return view.scene.time.minute_of_day;
  const named = String(view?.scene?.background_id || '');
  return /night/.test(named) ? 'night' : /dusk|evening/.test(named) ? 'evening' : /dawn|morning/.test(named) ? 'morning' : 'day';
}
function worldLocked() {
  return Boolean(screenFade.active || state.busy || encounterActive() || state.overlay || state.contextMenu || state.systemMenuOpen || document.querySelector('.game-system-modal, dialog[open]'));
}
// The party rail and the info dock float over the display's edges; the stage
// lays doors and props out in the clear middle and lets the painting bleed under them.
function hudInsets() {
  const scene = worldStage?.el; if (!scene?.isConnected) return {};
  const box = scene.getBoundingClientRect(), k = box.width ? scene.clientWidth / box.width : 1, out = {left: 0, right: 0};
  const rail = document.querySelector('#app .play-surface > .master-grid > .left-rail'), dock = document.querySelector('#app .hud-dock');
  const overlaps = r => r.top < box.bottom && r.bottom > box.top;      // stacked flow (phones) puts them beside the scene, not over it
  if (rail) { const r = rail.getBoundingClientRect(); if (r.width && overlaps(r) && r.right > box.left) out.left = Math.max(0, (Math.min(r.right, box.right) - box.left) * k + 6); }
  if (dock && !dock.closest('.hud-collapsed')) { const r = dock.getBoundingClientRect(); if (r.width && overlaps(r) && r.left < box.right) out.right = Math.max(0, (box.right - Math.max(r.left, box.left)) * k + 6); }
  else if (dock) out.right = 60;
  return out;
}
function ensureWorldStage() {
  if (worldStage) return worldStage;
  worldStage = createStage({
    mode: 'world', reducedMotion: motionReduced, swapMouseButtons: () => state.preferences.swapMouseButtons, locked: worldLocked, insets: hudInsets,
    onExit: bay => takeExit(bay.key, bay.id),
    onObject: id => objectAction('inspect', id),
    onTalk: id => { state.focusTarget = id; state.pendingConversation = null; state.consoleDraft = `talk to ${id}`; render(); document.querySelector('#console-input')?.focus(); },
    onSelect: id => { if (state.selectedActor !== id) { state.selectedActor = id; render(); } },
    onWell: node => openContextAt(node),
  });
  globalThis.__hsrStage = worldStage;                      // a handle for the probes and the console
  return worldStage;
}
// Swap the placeholder for the live stage and point it at the current view.
function keepWorldStage() {
  const slot = document.querySelector('#app [data-world-slot]');
  if (!slot) { worldStage?.stop(); return; }
  const stage = ensureWorldStage(), room = state.view?.room || {}, scene = state.view?.scene || {};
  const themeId = themeFor(room, scene), roomId = String(room.id || room.room_id || scene.location || themeId), prev = stage.roomId();
  slot.replaceWith(stage.el);
  stage.setRoom({themeId, tod: worldTimeOfDay(), roomId, exits: Object.entries(room.exits || {}), name: room.name || room.title || placeName(roomId),
    sub: scene.time ? `Day ${scene.time.day} · ${String(Math.floor(scene.time.minute_of_day / 60)).padStart(2, '0')}:${String(Math.floor(scene.time.minute_of_day % 60)).padStart(2, '0')}` : 'Public room projection', from: prev && prev !== roomId ? prev : null, wellHotspot: roomId === 'well'});
  stage.syncView(state.view || {}, {selected: state.selectedActor, encounter: encounterActive()});
  stage.start(); stage.relayout();
  syncAmbient({runId: state.runId, scene, stage, paused: () => worldLocked() || Boolean(state.activeDialogueNpc || state.pendingConversation || state.view?.conversation?.active),
    onLine: line => {
      addMessage(`${line.speaker}: “${line.text}”`, 'voice voice-ambient');
      document.querySelectorAll('.message-history').forEach(box => {
        const row = document.createElement('div'); row.className = 'message-row voice voice-ambient';
        const text = document.createElement('span'); text.className = 'message-text'; text.textContent = `${line.speaker}: “${line.text}”`;
        row.append(text); box.append(row);
        while (box.querySelectorAll('.message-row').length > 100) box.querySelector('.message-row').remove();
        box.scrollTop = box.scrollHeight;
      });
    }});
}
// Encounters get the painted set of the room they are in, under the combat stage's own layout.
function keepBattleBackdrop() {
  const stage = document.querySelector('#app .combat-stage:not(.demo-stage):not(.flight-stage)');
  if (!stage) return;
  const room = state.view?.room || {}, scene = state.view?.scene || {}, themeId = themeFor(room, scene);
  mountBattleBackdrop(stage, {themeId, tod: worldTimeOfDay(), seed: String(room.id || room.room_id || themeId)});
  if (battleWounds.has()) battleWounds.resume();
}
// The Actor Toolbox (Simulation Mode) is persistent the same way.
let toolbox = null;
function keepToolbox() {
  const slot = document.querySelector('#app [data-toolbox-slot]');
  if (!slot) { toolbox?.stop(); return; }
  toolbox ||= createToolbox({reducedMotion: motionReduced, onClose: () => { back(); render(); }});
  slot.replaceWith(toolbox.el); toolbox.start();
}
function toolboxScreen() { return '<div class="toolbox-slot" data-toolbox-slot></div>'; }
async function objectAction(kind, objectId) {
  const object = findRoomObject(objectId) || {};
  const lifeObject = !object.object_id && !object.kind;
  const type = kind === 'take' ? 'take' : lifeObject ? (kind === 'open' ? 'open' : 'inspect') : (kind === 'inspect' ? 'inspect_object' : kind === 'search' ? 'search_object' : 'open_object');
  await work(async () => {
    result(await state.client.roomAction(state.runId, type, {object_id: objectId, actor: actor().id || 'p0'}));
    await loadReadout(state.runId);
  });
}
async function takeExit(direction, destination) {
  await work(async () => {
    result(await state.client.designTurn(state.runId, `Walk to ${placeName(destination)}`, {type: 'move', actor: actingActorId(), destination, direction}));
    await loadReadout(state.runId);
  });
}
function openContextAt(node) {
  const rect = node.getBoundingClientRect();
  node.dispatchEvent(new MouseEvent('contextmenu', {bubbles: true, cancelable: true, clientX: rect.left + rect.width / 2, clientY: rect.top}));
}
// Adapters for the context menu and figure activation, which still speak in
// hotspot nodes: the stage does the walking and the acting.
function hotspotX(node) { return Number(node.dataset.walkX) || 50; }
function walkLeadTo(xPct) {
  const s = worldStage; if (!s || state.busy || encounterActive()) return Promise.resolve();
  const at = s.unproject(xPct / 100 * s.st.W, s.st.H * .82); return s.walkLead(at.x, at.d);
}
async function activateHotspot(node) {
  if (state.busy || encounterActive() || !worldStage) return;
  worldStage.activate({...node.dataset});
}
// Marks the end of a full-bleed scene so shell() can dock everything after it
// as a HUD over the scene instead of stacking it below.
const SCENE_END = '<!--hsr-scene-end-->';
function hudStage(html) {
  const at = html.indexOf(SCENE_END);
  if (at < 0) return html;
  const scene = html.slice(0, at);
  const rest = html.slice(at + SCENE_END.length);
  const room = state.view?.room || {}, area = state.view?.scene || {};
  const dungeon = area.floor_id && area.floor_id !== 'floor-1-town';
  const location = state.locationOpen ? `<aside class="location-details" aria-label="Location details"><button type="button" data-action="toggle-location" aria-label="Close location details">‹ Close</button><h3>${E(room.name || room.title || 'The Reliquary')}</h3><p>${E(room.description || room.atmosphere || state.view?.narration || (dungeon ? 'The city lies above. Every threshold leads further into the Reliquary.' : 'The town above the well is a place to prepare, trade, and meet the people who live beside the descent.'))}</p>${dungeon ? `<p>Floor: ${E(area.floor_id)} · ${E(area.phase || 'Exploration')}</p><p>${E(room.terrain || '')}</p>` : '<p>Explore local shops, speak with residents, and look for sights and services along the streets.</p>'}<h4>Ways onward</h4>${Object.entries(room.exits || {}).map(([direction, destination]) => `<p>${E(direction)} → ${E(typeof destination === 'string' ? placeName(destination) : destination.name || destination.destination || direction)}</p>`).join('') || '<p>No public exits reported.</p>'}<div class="actions">${button('Open Atlas', 'tab:map', 'secondary')}${!dungeon ? button('Meet residents', 'tab:residents', 'secondary') : ''}</div></aside>` : '';
  const collapsed = Boolean(state.preferences.hudCollapsed);
  return `<div class="stage-hud${collapsed ? ' hud-collapsed' : ''}">${scene}${location}<button type="button" class="hud-toggle" data-action="toggle-hud" aria-expanded="${collapsed ? 'false' : 'true'}" aria-controls="hud-dock" data-tooltip="${collapsed ? 'Show the info panel' : 'Hide the info panel'}"><span aria-hidden="true">${collapsed ? '‹' : '›'}</span><small>${collapsed ? 'Info' : 'Hide'}</small></button><aside id="hud-dock" class="hud-dock" aria-label="Scene information" data-scroll-key="hud-dock">${rest}</aside></div>`;
}
const ATMOSPHERE_GLYPHS = {journal: '▤', map: '◎', library: '⌘'};
function atmosphere(kind, titleText, subtitle) {
  return `<section class="atmosphere atmosphere-${E(kind)}"><div class="atmosphere-orbit"></div><span class="atmosphere-glyph" aria-hidden="true">${ATMOSPHERE_GLYPHS[kind] || '✧'}</span><div><p class="eyebrow">Hollow Star interface</p><h2>${E(titleText)}</h2><p>${E(subtitle)}</p><small class="atmosphere-aside">${E(FLAVOR.screens[kind] || '')}</small></div></section>`;
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
  return `<div class="room-objects"><p class="label">Things worth a closer look</p>${objects.map(obj => `<div class="object-row" role="button" tabindex="0" data-object="${E(obj.object_id || obj.id)}"><span>${E(objectLabel(obj))}${obj.discovered ? '' : '<small> · undiscovered</small>'}</span><span class="actions compact-actions">${objectActions(obj)}</span></div>`).join('')}</div>`;
}
async function openExamineDialog({entity_type = '', entity_id = '', query = ''} = {}) {
  let dialog = document.querySelector('#examine-dialog');
  if (!dialog) {
    dialog = document.createElement('dialog');
    dialog.id = 'examine-dialog';
    document.body.appendChild(dialog);
  }
  const targetLabel = query || entity_id || entity_type || 'entity';
  dialog.innerHTML = `
    <article class="examine-dialog-card">
      <header class="examine-dialog-header">
        <p class="eyebrow">Reliquary Analysis</p>
        <h2>Examining ${E(targetLabel)}</h2>
      </header>
      <div class="examine-dialog-body">
        <p class="muted">Querying host for observable metrics...</p>
      </div>
      <footer class="examine-dialog-footer">
        <button type="button" class="action secondary" data-close-examine>Close</button>
      </footer>
    </article>
  `;
  dialog.showModal();
  dialog.querySelectorAll('[data-close-examine]').forEach(n => n.onclick = () => dialog.close());
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });

  if (!state.runId) {
    dialog.querySelector('.examine-dialog-body').innerHTML = `<p class="muted">No active run to query for this entity.</p>`;
    return;
  }
  try {
    const payload = {};
    if (entity_type) payload.entity_type = entity_type;
    if (entity_id) payload.entity_id = entity_id;
    if (query) payload.query = query;
    const reply = await state.client.examine(state.runId, payload);
    if (!reply?.ok || !reply?.result?.examine) {
      const err = reply?.error?.message || 'Could not examine entity.';
      dialog.querySelector('.examine-dialog-body').innerHTML = `<p class="notice error">${E(err)}</p>`;
      return;
    }
    const info = reply.result.examine;
    let detailsHtml = '';
    if (info.entity_type === 'object') {
      const details = Object.entries(info.details || {}).map(([k, v]) => `<div><small>${E(k)}</small><strong>${E(readable(v))}</strong></div>`).join('');
      detailsHtml = details ? `<div class="examine-facts-grid">${details}</div>` : '';
    } else if (info.entity_type === 'actor' || info.entity_type === 'target') {
      const stats = Object.entries(info.ability_scores || {}).map(([k, v]) => {
        const mod = info.ability_modifiers?.[k];
        const modStr = mod !== undefined ? ` (${mod >= 0 ? '+' : ''}${mod})` : '';
        return `<div><small>${E(k)}</small><strong>${E(v)}${modStr}</strong></div>`;
      }).join('');
      const skills = Object.entries(info.skills || {}).map(([k, v]) => `<span class="tag-pill">${E(k)} +${E(v)}</span>`).join(' ') || '<em class="muted">None</em>';
      const conds = (info.conditions || []).map(c => `<span class="tag-pill status-pill">${E(readable(c))}</span>`).join(' ') || '<em class="muted">None</em>';
      detailsHtml = `
        ${stats ? `<div class="examine-facts-grid">${stats}</div>` : ''}
        <div class="examine-section"><small>Skills</small><p>${skills}</p></div>
        <div class="examine-section"><small>Conditions</small><p>${conds}</p></div>
      `;
    }
    dialog.innerHTML = `
      <article class="examine-dialog-card">
        <header class="examine-dialog-header">
          <p class="eyebrow">${E(info.entity_type?.toUpperCase() || 'EXAMINATION')}</p>
          <h2>${E(info.name || targetLabel)}</h2>
          <p class="examine-short">${E(info.short || '')}</p>
        </header>
        <div class="examine-dialog-body">
          ${detailsHtml}
        </div>
        <footer class="examine-dialog-footer">
          <button type="button" class="action" data-close-examine>Dismiss</button>
        </footer>
      </article>
    `;
    dialog.querySelectorAll('[data-close-examine]').forEach(n => n.onclick = () => dialog.close());
    dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
  } catch (err) {
    dialog.querySelector('.examine-dialog-body').innerHTML = `<p class="notice error">${E(err.message)}</p>`;
  }
}
function room() {
  const r = state.view?.room || {};
  const exits = Object.entries(r.exits || {}).map(([direction, destination]) => `${direction}: ${readable(destination)}`).join(' · ');
  const tells = (r.visible_tells || r.tells || []).map(readable).filter(Boolean).join(' · ');
  const description = readable(r.description || r.atmosphere || state.view?.narration || state.receipt?.message || state.receipt?.narration);
  return `${sceneWorld('room')}${runEndCard()}${card('Sanctum room', `${descentBanner()}<div class="room-hero"><div><p class="eyebrow">${E(readable(r.apparent_function || r.condition) || 'Observed space')}</p><h2>${E(readable(r.name || r.id) || 'Unreported room')}</h2><p>${E(description || 'No public description reported.')}</p></div><span class="room-sigil" aria-hidden="true">⌂</span></div>
    <div class="room-facts"><div><small>Law</small><strong>${E(readable(r.law) || 'Not reported')}</strong></div><div><small>Terrain</small><strong>${E(readable(r.terrain) || 'Not reported')}</strong></div><div><small>Exits</small><strong>${E(exits || 'None reported')}</strong></div></div>
    <p class="notice">${E(tells || 'No visible tells reported.')}</p>${roomObjects()}${lifecyclePanel()}
    <div class="actions sanctum-links">${button('Plan gambits', 'tab:roster', 'secondary')}${button('Expedition route', 'tab:battle', 'secondary')}</div>`)}`;
}
// Floor arrivals and the run's end are host facts; the client only says them once.
function announceDescent(before, after) {
  // A run's first readout has no "before": that is arriving on its opening floor.
  if (after && !before && after.status === 'active' && state.runId && state.floorAnnounced !== state.runId) {
    state.floorAnnounced = state.runId;
    emitStory('floor_entered', {floor: after.floor, floor_name: after.floor_name || null});
    if (state.preferences.story?.floorCards !== false && after.floor === 1 && (after.room ?? 1) <= 1) titleCard(t('floor.card', {n: after.floor}), after.floor_name || '');
  }
  if (!after || !before) return;
  if (after.floor > before.floor) {
    emitStory('floor_entered', {floor: after.floor, floor_name: after.floor_name || null});
    if (state.preferences.story?.floorCards !== false) titleCard(t('floor.card', {n: after.floor}), after.floor_name || '');
    const line = `Floor ${after.floor} of ${after.floors_total}${after.floor_name ? ` · ${after.floor_name}` : ''}`;
    addMessage(`Descended — ${line}.`, 'note');
    state.note = `Descended to ${line}.`;
  }
  if (before.status === 'active' && after.status !== 'active') {
    finalizeRun(state.runId);
    addMessage(after.status === 'cleared' ? 'The Reliquary is cleared.' : `The run has ended: ${after.status}.`, 'note');
  }
}
function descentBanner() {
  const d = state.view?.descent;
  if (!d) return '';
  const pct = d.rooms_on_floor ? Math.round((Math.min(d.room, d.rooms_on_floor) / d.rooms_on_floor) * 100) : 0;
  const scaled = d.opposition_scale < 1 ? `<small class="descent-scale" title="Opposition is scaled to this party (dungeon.json party_scaling).">Opposition ×${E(d.opposition_scale)}</small>` : '';
  return `<div class="descent-banner" aria-label="Descent progress"><div><p class="eyebrow">Floor ${E(d.floor)} of ${E(d.floors_total)}</p><strong>${E(d.floor_name || 'Unnamed floor')}</strong></div><div class="descent-rooms"><small>Room ${E(Math.min(d.room, d.rooms_on_floor))} of ${E(d.rooms_on_floor)}</small><div class="journey-progress"><span style="width:${pct}%"></span></div></div>${scaled}</div>`;
}
function runEndCard() {
  const d = state.view?.descent;
  if (!d || d.status === 'active') return '';
  const cleared = d.status === 'cleared';
  const title = cleared ? 'The Reliquary is cleared' : d.status === 'defeated' ? 'The party has fallen' : `Run ${readable(d.status)}`;
  const body = cleared ? `All ${E(d.floors_total)} floors walked; ${E(d.rooms_cleared)} rooms cleared.` : `Reached floor ${E(d.floor)} of ${E(d.floors_total)} (${E(d.floor_name || 'unnamed')}), room ${E(d.room)}; ${E(d.rooms_cleared)} rooms cleared.`;
  return card(title, `<p>${body}</p><div class="actions">${button('Run report', 'tab:journal', 'primary')}${button('Main menu', 'title', 'secondary')}</div>`);
}
function lifecyclePanel() {
  const d = state.view?.descent;
  if (d && d.floor && d.room) {
    const resolved = Boolean(state.view?.room?.resolved);
    const canExit = (state.view?.available_actions || []).some(row => (row.id || row.action || row.type) === 'exit');
    const lastRoom = d.room >= d.rooms_on_floor;
    const finalFloor = d.floor >= d.floors_total;
    const reward = state.receipt?.reward;
    const next = lastRoom ? (finalFloor ? '' : `Descend to floor ${d.floor + 1}`) : 'Continue to the next room';
    const banked = state.view?.checkpoint?.current?.checkpoint_id;
    return `<section class="lifecycle-panel" aria-label="Run progress"><p class="label">Run progress</p>${reward ? '<p class="notice success">Victory reward received. Gold, Gems, and progression are already recorded by the host.</p>' : ''}<div class="room-facts"><div><small>This room</small><strong>${resolved ? 'Cleared' : 'Unresolved'}</strong></div><div><small>Checkpoint</small><strong>${banked ? 'Banked' : 'None banked'}</strong></div></div>${resolved && lastRoom ? `<p class="notice">${finalFloor ? 'The last room of the last floor is settled.' : `Floor ${E(d.floor)} is cleared. The way down is open.`}</p>` : ''}${resolved && canExit && next ? `<div class="actions descent-actions"><button type="button" class="action primary" data-engine-action="exit">${lastRoom ? '⇣' : '→'} ${E(next)}</button></div>` : ''}</section>`;
  }
  const checkpoint = state.view?.checkpoint || {};
  const current = checkpoint.current;
  const available = checkpoint.available;
  const resolved = Boolean(state.view?.room?.resolved);
  const reward = state.receipt?.reward;
  return `<section class="lifecycle-panel" aria-label="Run progress"><p class="label">Run progress</p>${reward ? '<p class="notice success">Victory reward received. Gold, Gems, and progression are already recorded by the host.</p>' : ''}<div class="room-facts"><div><small>Threshold</small><strong>${resolved ? 'Cleared' : 'Unresolved'}</strong></div><div><small>Checkpoint</small><strong>${current?.checkpoint_id ? 'Banked' : available ? 'Available after victory' : 'Not available here'}</strong></div></div>${resolved ? '<p class="notice">The sealed arch is open. The deeper five-floor Reliquary remains ahead.</p>' : ''}</section>`;
}
function journey() {
  if (encounterActive()) {
    return `${sceneWorld('journey')}${card('Journey', `<p class="notice">A fight is underway. Travel resumes once it is settled.</p><div class="actions">${button('Open Encounters', 'tab:battle', 'primary')}</div>`)}`;
  }
  const scene = state.view?.scene || {};
  const progress = Math.round(Number(scene.progress || 0) * 100);
  const pause = state.receipt?.pause;
  // A resident who lives at the descent location is visible on every visit,
  // so `available_actions` (set purely from the room id) is the reliable
  // signal here -- the idle-pause "social choice" notice never clears while
  // that resident stands there, and must not gate the one real way down.
  const canDescend = (state.view?.available_actions || []).some(row => (row.id || row.action || row.type) === 'descend');
  const entities = (scene.visible_entities || []).slice(0, 5).map(row => `<span class="journey-entity" role="button" tabindex="0" data-resident="${E(row.id || '')}"><strong>${E(row.name || row.id)}</strong><small>${E(row.role || 'resident')}</small></span>`).join('');
  return `${sceneWorld('journey')}${card('Journey', `<div class="room-hero"><div><p class="eyebrow">${E(scene.floor_id || 'Reliquary')}</p><h2>${E(scene.phase || 'exploration')} · ${E(state.view?.room?.name || state.view?.room?.title || 'Unknown route')}</h2><p>Move from left to right through the public route. Social decisions remain yours; idle travel pauses when a meaningful choice appears.</p></div><span class="room-sigil">→</span></div>
    <div class="journey-progress" aria-label="Floor progress"><span style="width:${progress}%"></span></div><div class="journey-meta"><span>${E(progress)}% route progress</span><span>Background: ${E(scene.background_id || 'unreported')}</span><span>Direction: ${E(scene.direction || 'right')}</span></div>
    ${entities ? `<div class="journey-entities"><p class="label">Visible decision points</p>${entities}</div>` : '<p class="notice">No public residents are currently visible.</p>'}
    <div class="actions">${floorOneWorld() ? `${button(scene.travel?.active ? 'Traveling…' : 'Auto-travel to descent', 'auto-travel', 'primary')}${button('Advance safely', 'idle-tick', 'secondary')}` : ''}${button('Open social view', 'tab:residents', 'secondary')}${button('Read current room', 'tab:room', 'secondary')}</div>
    ${canDescend ? `<div class="actions descent-actions">${button('Descend into the Reliquary', 'descend-now', 'primary')}</div>` : ''}
    <p class="notice">${E(scene.travel?.active ? `Host travel loop: ${scene.travel.destination || 'route'} · ${scene.travel.steps || 0} step(s).` : (pause?.message || (floorOneWorld() ? 'Auto-travel follows the authored public route and stops at the descent decision.' : 'The town is behind you. Use Room and Encounters to move through the Reliquary.')))}</p>`)}`;
}
function autoToggle() {
  const auto = state.view?.auto;
  const stepActor = encounterStepActor();
  if (!auto?.supported || !stepActor) return '';
  const isPlayer = playerControlled(stepActor);
  const label = isPlayer ? '⚡ Auto turn (Gambit)' : (state.npcPhase ? 'Enemy turn in progress…' : 'Play enemy turns');
  // NPC steps drain through design_drain_npc; this button is the manual
  // fallback when automatic enemy turns are switched off in Options.
  const command = isPlayer || !tacticalActive() ? auto.step_command : 'design_drain_npc';
  return `<button type="button" class="action secondary" data-auto-step="${E(command)}" title="${isPlayer ? 'Execute automated turn via character Gambits' : 'Play every NPC turn until a hero must decide'}">${label}</button>`;
}
function signatureActions() {
  const identity = actor().identity;
  const target = (state.view?.opposition || []).find(o => Number(o.hp ?? 1) > 0)?.id || '';
  if (identity === 'wren') {
    return `${resourceSheet(actor())}<div class="signature-actions"><p class="label">Wren's domain</p>${DOMAIN_FEATURES.map(row => `<button type="button" class="action signature" data-domain-feature="${E(row.feature)}" title="${E(row.label)}">${E(row.label)}</button>`).join('')}${button('Unearthly Recovery', 'wren-recovery', 'secondary')}</div>`;
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
  const pending = (c.pending || []).filter(window => party().some(p => p.id === window.reactor) || window.reactor === current);
  const reactions = pending.length ? `<div class="reaction-panel" aria-live="polite"><p class="label">Reaction window</p>${pending.map(window => {
    const reactorName = party().find(p => p.id === window.reactor)?.name || window.reactor;
    return `<div class="reaction-window" data-reactor="${E(window.reactor)}"><strong>${E(window.kind || 'Reaction')} <small>(${E(reactorName)})</small></strong><small>${E(window.target || 'A visible combatant')} · legal: ${E((window.options || []).join(' / ') || 'decline')}</small><div class="actions compact-actions">${(window.options || []).map(option => `<button type="button" class="action secondary" data-action="reaction:${E(option)}" data-reactor="${E(window.reactor)}" data-tooltip="${E(option)}">${E(option)}</button>`).join('')}<button type="button" class="action secondary" data-action="reaction:decline_reaction" data-reactor="${E(window.reactor)}" data-tooltip="Decline">Decline</button></div></div>`;
  }).join('')}</div>` : '';
  const playerTurn = String(current || '').startsWith('p');
  const turnActions = playerTurn
    ? '<div class="actions turn-actions"><button type="button" class="action" data-engine-action="attack">⚔ Attack</button><button type="button" class="action" data-engine-action="cast">✧ Cast</button><button type="button" class="action" data-engine-action="move">⇢ Move</button><button type="button" class="action" data-engine-action="end_turn">⏳ End turn</button></div>'
    : `<p class="notice npc-phase" aria-live="polite">${state.npcPhase || state.preferences.combat.autoNpc !== false ? 'Enemy turn in progress… the host plays it and hands control back at your next decision.' : 'Enemy turn. Automatic enemy turns are off; use "Play enemy turns".'}</p>`;
  const targets = (c.target_context || []).map(target => {
    const visible = (state.view?.opposition || []).find(item => item.id === target.id);
    return `<span><b>${E(visible?.name || target.id)}</b> ${E(target.distance_ft)} ft</span>`;
  }).join('');
  const disabled = Object.values(c.disabled_reasons || {})[0];
  return `<div class="turn-panel" aria-label="Turn-based combat controls"><div class="turn-panel-head"><strong>${E(row.name || current || 'Current turn')}</strong><span>Initiative ${E(c.order?.indexOf(current) + 1 || '—')}</span></div><div class="turn-economy"><span>Action <b>${E(economy.action ?? 0)}</b></span><span>Bonus <b>${E(economy.bonus ?? 0)}</b></span><span>Reaction <b>${E(economy.reaction ?? 0)}</b></span><span>Move <b>${E(economy.movement ?? 0)} ft</b></span></div><div class="turn-stats">${Object.keys(scores).map(key => `<span title="${E(key)} score"><b>${E(key)}</b> ${E(scores[key])} <small>${Number(modifiers[key] || 0) >= 0 ? '+' : ''}${E(modifiers[key] || 0)}</small></span>`).join('')}</div>${targets ? `<div class="turn-stats" aria-label="Visible target distances">${targets}</div>` : ''}${turnActions}${reactions}${disabled ? `<p class="notice">${E(disabled)}</p>` : '<p class="notice">Choose a visible target; the host validates range, terrain, dice, resources, and saves.</p>'}</div>`;
}
function flightControls() {
  if (!state.view?.flight_arena) return '';
  return `<div class="flight-controls" aria-label="Flight controls"><p class="label">Flight controls</p>
    <button type="button" class="action flight-control" data-flight-type="wings" title="Manifest Wren's wings and take flight">Take Flight</button>
    <button type="button" class="action flight-control" data-flight-type="land" title="Dismiss Wren's wings and land">Land</button>
    ${[['flight_move','←','-5','0','Move left'],['ascend','↑','0','5','Ascend'],['descend','↓','0','-5','Descend'],['flight_move','→','5','0','Move right']].map(([type,label,dx,dy,accessibleLabel]) => `<button type="button" class="action flight-control" data-flight-type="${type}" data-flight-dx="${dx}" data-flight-dy="${dy}" aria-label="${E(accessibleLabel)}" title="${E(accessibleLabel)}"><span aria-hidden="true">${label}</span></button>`).join('')}</div>`;
}
function usableItems() {
  return (state.view?.inventory || []).filter(item => item && item.kind === 'potion');
}
// Turn-based fight in the side-view battle layout. Commands post the same
// engine actions as the classic turn panel; the classic panel stays one click
// away under "Tactical detail" for reactions, distances and ability scores.
function ffBattle() {
  const c = state.view?.combat || {};
  const current = c.current;
  const row = [...party(), ...(state.view?.opposition || [])].find(item => item.id === current) || {};
  const isPlayer = String(current || '').startsWith('p');
  const pending = (c.pending || []).length;
  const command = commandWindow({
    name: row.name || current || '', playerTurn: isPlayer && !pending, economy: c.economy?.[current] || {},
    menu: state.ffMenu || '', skills: signatureActions(), items: usableItems(), autoButton: autoToggle(),
    disabled: Object.values(c.disabled_reasons || {})[0] || '', E,
  });
  return `${battleStage()}<div class="ff-hud">${command}${partyStatusPanel({party: party(), opposition: state.view?.opposition || [], current, E})}</div>
    ${flightControls()}
    <details class="ff-detail"${pending ? ' open' : ''}><summary>Tactical detail${pending ? ' · reaction open' : ''}</summary>${turnPanel()}</details>`;
}
function arcadeEncounter() {
  const v = state.view || {};
  return `${arcadeStage()}${card('Encounters · Arcade', `<div class="battle-banner"><div><p class="eyebrow">Live arcade</p><h2>${E(v.room?.name || 'Wave ladder')}</h2><p>Move, dodge, block and attack in real time. The host resolves every frame and hit; clear each wave to open the gate.</p></div><span class="battle-sigil" aria-hidden="true">✦</span></div><div class="roster-grid">${[...party(), ...(v.opposition || [])].map(actorCard).join('') || '<p>No public combat roster.</p>'}</div>${arcadeControls()}`)}`;
}
const XP_MODES = [
  {mode: 'arcade', label: 'Arcade', help: 'Real-time wave ladder. You move, dodge and strike.'},
  {mode: 'tactical', label: 'Fight', help: 'Turn-based side-view battle. You pick every command.'},
  {mode: 'auto', label: 'Auto', help: 'Gambits play the node for you and report back.'},
];
function expeditionNodeCard(xp) {
  const maps = xp.maps || {};
  const node = Object.values(maps).flatMap(graph => (graph.columns || []).flat()).find(row => row.id === state.xpSelected);
  if (!node || node.reach !== 'available') {
    return `<p class="notice">${xp.choices?.length ? 'Pick a lit node on the route to see how to take it.' : 'No node is reachable right now.'}</p>`;
  }
  const combatNode = ['fight', 'elite', 'boss'].includes(node.type);
  const ladder = node.ladder ? `<p class="xp-ladder">${node.ladder.waves.map((wave, index) => `<span>Wave ${index + 1} · ${E(wave.enemy_count)} foe${wave.enemy_count > 1 ? 's' : ''}</span>`).join('')}</p>` : '';
  const modes = XP_MODES.filter(row => combatNode || row.mode !== 'arcade').map(row => `<button type="button" class="action ${row.mode === 'tactical' ? 'primary' : 'secondary'}" data-xp-go="${E(row.mode)}" title="${E(row.help)}">${E(combatNode || row.mode !== 'tactical' ? row.label : 'Enter')}</button>`).join('');
  return `<div class="xp-node-card"><span class="xp-node-glyph" aria-hidden="true">${E(nodeGlyph(node.type))}</span><div><p class="eyebrow">Floor ${E(node.floor)} · step ${E(node.column)}</p><h3>${E(node.label)}</h3>${ladder}<div class="actions">${modes}</div></div></div>`;
}
function expeditionHub() {
  const v = state.view || {};
  const xp = v.expedition;
  if (!state.runId || !xp) {
    return `${atmosphere('battle', 'Encounters', 'Expeditions open once a run has descended into the Reliquary.')}${card('Expedition', `<p class="notice">${state.runId ? 'Descend from Journey to reach the Reliquary route. Floor One Life is a single-floor town loop with no descent; Reliquary City (Simulation) and Story Mode lead down into it.' : 'Start or resume a run first.'}</p><div class="actions">${button('Open Journey', 'tab:journey', 'secondary')}${state.runId ? button('Edit Scenario', 'menu:edit-scenario', 'secondary') : ''}</div>`)}`;
  }
  if (!xp.active) {
    return `${atmosphere('battle', 'Encounters', 'Chart a route through this floor: fights, wave ladders, caches, rests and a boss at the end.')}${card('Expedition', `<p>Each step offers a choice of nodes. Take a fight as a real-time arcade ladder, a turn-based battle, or let your gambits play it while you are away.</p><div class="actions">${button('Chart the route', 'xp-start', 'primary')}</div>`)}`;
  }
  const graph = (xp.maps || {})[String(xp.next_floor)] || (xp.maps || {})[String(xp.floor)];
  const last = xp.last_auto;
  const summary = last ? `<div class="xp-summary"><p class="label">Last AFK run</p><p>${E(last.nodes.length)} node(s) · stopped: ${E(String(last.stopped).replaceAll('_', ' '))} · +${E(last.gold_gained)} gold · party at ${E(Math.round(last.party_health * 100))}%</p>${last.nodes.length ? `<p class="xp-trail">${last.nodes.map(row => `<span>${E(nodeGlyph(row.type))} ${E(row.type)}</span>`).join('')}</p>` : ''}</div>` : '';
  const unresolved = !xp.room_resolved;
  const afk = `<form class="xp-afk" data-xp-afk><p class="label">AFK expedition</p><label>Nodes <select name="max_nodes">${[1, 2, 3, 4, 5, 6].map(n => `<option value="${n}"${n === (state.xpAfk?.max_nodes ?? 3) ? ' selected' : ''}>${n}</option>`).join('')}</select></label><label>Stop below <select name="retreat_below">${[20, 30, 40, 50].map(n => `<option value="${n}"${n === (state.xpAfk?.retreat ?? 30) ? ' selected' : ''}>${n}% health</option>`).join('')}</select></label><button type="submit" class="action primary">Go AFK</button><small>Gambits from the Party screen drive every fight.</small></form>`;
  return `${card(`Expedition · Floor ${xp.next_floor || xp.floor}`, `<div class="xp-head"><div><p class="eyebrow">Party health ${E(Math.round((xp.party_health || 0) * 100))}%</p><h2>Choose the next node</h2></div><div class="xp-legend">${['fight', 'elite', 'loot', 'rest', 'hazard', 'shop', 'boss'].map(type => `<span>${E(nodeGlyph(type))} ${E(type)}</span>`).join('')}</div></div>
    <div class="xp-map-wrap">${graph ? routeMap(graph, {selected: state.xpSelected, E}) : '<p class="notice">Route not charted.</p>'}</div>
    ${unresolved ? `<p class="notice">This room is still open. Settle it before moving on.</p><div class="actions">${button('Auto-resolve room', 'xp-resolve', 'secondary')}${button('Open Sanctum', 'tab:room', 'secondary')}</div>` : expeditionNodeCard(xp)}
    ${afk}${summary}`, 'xp-card')}`;
}
function battle() {
  const v = state.view || {};
  const active = tacticalActive(v);
  if (arcadeActive(v)) return arcadeEncounter();
  if (active) return ffBattle();
  return expeditionHub();
}
// Hosts send statuses as a list, a {NAME: rounds} map or a string.
function statusText(status) {
  if (Array.isArray(status)) return status.filter(Boolean).join(' · ');
  if (status && typeof status === 'object') return Object.entries(status).map(([name, rounds]) => (Number(rounds) > 1 ? `${name} (${rounds})` : name)).join(' · ');
  return status ? String(status) : '';
}
function actorCard(item) {
  const statuses = statusText(item.status) || 'No visible statuses';
  const appearance = presentationAppearance(item);
  const ident = String(item.identity || item.id || '').toLowerCase();
  const isChampion = ident === 'doran' || ident === 'wren' || Boolean(item.is_champion || item.champion);
  const championTitle = ident === 'doran' ? 'The Iron Bulwark' : ident === 'wren' ? 'Sovereign of the Void' : isChampion ? 'Champion' : '';
  const championTag = championTitle ? `<span class="champion-title-tag">✦ ${E(championTitle)}</span>` : '';
  return `<button class="actor-card ${isChampion ? 'sovereign-champion' : ''} ${actor().id === item.id ? 'selected' : ''}" data-actor="${E(item.id)}" data-examine-actor="${E(item.id)}" title="Click to select ${E(item.name)}. Double-click to examine."><span class="mini-character ${E(visualRole(item))} identity-${E(visualIdentity(item))} appearance-${E(appearance)} expression-${E(visualExpression(item, 'idle'))}"><i></i><b>${E((item.name || '?')[0])}</b></span><span><strong>${E(item.name)}</strong>${championTag}<small>${E(value(item, 'hp') ?? '?')} / ${E(value(item, 'max_hp', 'ac') ?? '?')} HP · AC ${E(value(item, 'armor_class', 'ac') ?? '?')}</small><small>${E(statuses)}</small></span></button>`;
}
function imprintPanel() {
  const imprints = state.view?.imprints || {};
  const rows = Object.entries(imprints);
  if (!rows.length) return '';
  return `<div class="imprint-grid"><p class="label">Reliquary Imprints</p>${rows.map(([slot, row]) => `<div class="imprint-slot"><small>${E(slot.replaceAll('_', ' '))}</small><strong>${E(row?.name || row?.display_name || 'Empty')}</strong>${row?.tooltip ? `<small class="notice">${E(row.tooltip)}</small>` : ''}</div>`).join('')}<p class="notice">Imprints are temporary overlays; they dissolve or become inert outside the Reliquary.</p></div>`;
}
// The Attunement Matrix: powers decanted from destroyed loot, by lane.
// Capacity comes from the Meta Shop tiers frozen into this run.
function attunementPanel() {
  const matrix = state.view?.attunement;
  if (!matrix?.capacity) return '';
  const id = actor().id || 'p0';
  const lanes = matrix.actors?.[id]?.lanes || {};
  const laneHtml = ['prefix', 'suffix', 'legendary'].map(lane => {
    const rows = lanes[lane] || [];
    const cap = Math.max(rows.length, Number(matrix.capacity[lane] ?? 1));
    const slots = Array.from({length: cap}, (_, index) => rows[index]);
    return `<div class="attunement-lane"><p class="label">${E(lane)} · ${E(rows.length)}/${E(matrix.capacity[lane] ?? 1)}</p>${slots.map(entry => entry
      ? `<div class="attunement-slot is-filled" title="${E(entry.description || `From ${entry.source || 'a decanted item'}`)}"><strong>${E(entry.name)}</strong><small>from ${E(entry.source || 'a decanted item')}${entry.lattice?.length ? ` · ${E(entry.lattice.join(', ').replaceAll('_', ' '))}` : ''}</small>${encounterActive() ? '' : `<button type="button" class="action secondary attunement-release" data-action="release-attunement:${E(id)}:${E(lane)}:${E(entry.name)}" title="Empty this slot. The power is lost.">Release</button>`}</div>`
      : '<div class="attunement-slot is-empty"><small>Empty slot</small></div>').join('')}</div>`;
  }).join('');
  const candidates = encounterActive() ? [] : actionTargets('decant');
  const decant = candidates.length
    ? `<div class="attunement-decant"><p class="label">Decant a carried item</p><div class="actions compact-actions">${candidates.map(choice => `<button type="button" class="action secondary" data-action="decant-item:${E(choice.value)}" title="Destroys the item and attunes its Prefix, Suffix, or legendary power to ${E(actor().name || id)}">${E(choice.label)}</button>`).join('')}</div></div>`
    : '';
  return `<div class="attunement-panel"><p class="label">Attunement Matrix · ${E(actor().name || id)}</p><div class="attunement-lanes">${laneHtml}</div>${decant}<p class="notice">Decanting destroys the item. Attuned powers last for this run; buy more slots in the Meta Shop.</p></div>`;
}
function getItemCategory(item) {
  if (!item) return 'gear';
  const cat = String(item.category || item.kind || '').toLowerCase();
  const name = String(item.name || item.display_name || '').toLowerCase();
  const slot = String(item.slot || '').toLowerCase();
  if (cat === 'weapon' || item.damage_dice || item.base_damage || /sword|dagger|mace|bow|staff|spear|axe|hammer|rapier|club|halberd|crossbow/.test(name)) {
    return 'weapon';
  }
  if (cat === 'armor' || slot === 'armor' || slot === 'shield' || item.base_ac || item.shield_bonus || ((/armor|shield|mail|cuirass|helm|greaves|plate/.test(name)) && !name.includes('pewter plate'))) {
    return 'armor';
  }
  if (cat === 'tableware' || cat === 'prop' || /plate|fork|spoon|knife|tankard|goblet|torch|mug|pitcher|bowl|pot/.test(name)) {
    return 'tableware';
  }
  if (cat === 'consumable' || /potion|ration|elixir|flask|herb|poultice|salve|scroll/.test(name)) {
    return 'consumable';
  }
  return 'gear';
}

function statDiffDrawer(selectedItem, currentActor = actor()) {
  if (!selectedItem) return '';
  const carried = currentActor.equipment || [];
  const slot = selectedItem.slot || getItemCategory(selectedItem);
  const equipped = carried.find(i => i.slot === slot || (slot === 'armor' && ['armor', 'torso'].includes(i.slot)) || (slot === 'weapon' && i.slot === 'hand')) || null;
  const isEquipped = carried.some(i => (i.id && i.id === selectedItem.id) || (i.name && i.name === selectedItem.name));
  const isPotion = selectedItem.kind === 'potion' || getItemCategory(selectedItem) === 'consumable';
  const isImprint = selectedItem.kind === 'imprint';

  const selAc = (Number(selectedItem.base_ac) || 0) + (Number(selectedItem.ac_bonus) || 0) + (Number(selectedItem.shield_bonus) || 0);
  const eqAc = equipped ? (Number(equipped.base_ac) || 0) + (Number(equipped.ac_bonus) || 0) + (Number(equipped.shield_bonus) || 0) : 0;
  const acDiff = selAc - eqAc;

  const selDmg = selectedItem.damage_dice || (selectedItem.base_damage ? `${selectedItem.base_damage} flat` : '');
  const eqDmg = equipped ? (equipped.damage_dice || (equipped.base_damage ? `${equipped.base_damage} flat` : '')) : '';

  const selW = Number(selectedItem.weight) || (selectedItem.density ? Number(selectedItem.density) : 1.0);
  const eqW = equipped ? (Number(equipped.weight) || (equipped.density ? Number(equipped.density) : 1.0)) : 0;
  const wDiff = selW - eqW;

  const selAffixes = [selectedItem.prefix?.name || selectedItem.prefix, selectedItem.suffix?.name || selectedItem.suffix].filter(Boolean);

  const diffBadge = (diff, invert = false) => {
    if (diff === 0) return '<span class="diff-equal">±0</span>';
    const isGood = invert ? diff < 0 : diff > 0;
    return `<span class="${isGood ? 'diff-up' : 'diff-down'}">${diff > 0 ? '+' : ''}${diff.toFixed(1)}</span>`;
  };

  return `
    <div class="stat-diff-drawer" aria-label="Item comparison and actions">
      <div class="stat-diff-head">
        <div>
          <span class="eyebrow" style="color:var(--gold-hi);">Selected: ${E(selectedItem.display_name || selectedItem.name)}</span>
          <h3 style="margin:2px 0 0;">${isEquipped ? 'Currently Equipped' : equipped ? `Replaces ${E(equipped.display_name || equipped.name)}` : `Equips to ${E(slot)} Slot`}</h3>
        </div>
        <button type="button" class="action secondary" data-action="clear-item-selection" style="min-height:30px;padding:3px 8px;font-size:11px;">✕ Clear</button>
      </div>
      <div class="stat-diff-grid">
        ${(selAc || eqAc) ? `
          <div class="stat-diff-cell">
            <dt>Armor Class (AC)</dt>
            <dd>${selAc} ${equipped ? `<small class="muted">vs ${eqAc}</small> ${diffBadge(acDiff)}` : ''}</dd>
          </div>
        ` : ''}
        ${(selDmg || eqDmg) ? `
          <div class="stat-diff-cell">
            <dt>Weapon Damage</dt>
            <dd>${E(selDmg || 'None')} ${equipped ? `<small class="muted">vs ${E(eqDmg || '—')}</small>` : ''}</dd>
          </div>
        ` : ''}
        <div class="stat-diff-cell">
          <dt>Item Weight</dt>
          <dd>${selW.toFixed(1)} lbs ${equipped ? `${diffBadge(wDiff, true)}` : ''}</dd>
        </div>
        <div class="stat-diff-cell">
          <dt>Active Affixes</dt>
          <dd style="font-size:12px;">${selAffixes.length ? E(selAffixes.join(', ')) : '<span class="muted">Inherent only</span>'}</dd>
        </div>
      </div>
      <div class="actions compact-actions" style="margin-top:8px;">
        ${isEquipped
          ? `<button type="button" class="action secondary" data-action="unequip-item:${E(selectedItem.slot || selectedItem.name)}">Unequip</button>`
          : isPotion
            ? `<button type="button" class="action primary" data-action="use-potion:${E(selectedItem.id || selectedItem.name)}">🧪 Drink / Use</button>`
            : `<button type="button" class="action primary" data-action="equip-item-id:${E(selectedItem.id || selectedItem.name)}">⚔️ Equip on ${E(currentActor.name || 'Lead')}</button>`
        }
        ${!isEquipped && isImprint ? `<button type="button" class="action secondary" data-action="decant-item:${E(selectedItem.id || selectedItem.name)}">⚗️ Decant Rune</button>` : ''}
        <button type="button" class="action secondary" data-action="inspect-item-modal:${E(selectedItem.id || selectedItem.name)}">⌕ Full Inspection</button>
      </div>
    </div>
  `;
}

function equipment() {
  const current = actor();
  const allItems = [...(current.equipment || []), ...(state.view?.inventory || [])];
  const str = current.ability_scores?.STR ?? current.stats?.STR ?? 10;
  const maxCapacity = Math.max(15, str * 15);
  const totalWeight = allItems.reduce((sum, item) => sum + (Number(item.weight) || (item.density ? Number(item.density) : 1.0)), 0);
  const pct = Math.min(100, Math.round((totalWeight / maxCapacity) * 100));
  const isEncumbered = totalWeight > maxCapacity;
  const activeFilter = state.equipmentFilter || 'all';

  const filterChips = [
    ['all', 'All'],
    ['weapon', 'Weapons'],
    ['armor', 'Armor'],
    ['tableware', 'Tableware & Props'],
    ['gear', 'Adventuring Gear'],
    ['consumable', 'Consumables'],
  ];

  const chipsHtml = `<div class="equipment-filter-chips" role="tablist" aria-label="Item category filters">${filterChips.map(([k, label]) => `<button type="button" class="action filter-chip ${activeFilter === k ? 'active' : 'secondary'}" data-item-filter="${k}" role="tab" aria-selected="${activeFilter === k}">${E(label)}</button>`).join('')}</div>`;

  const encumbranceHtml = `<div class="encumbrance-meter" title="Carrying Capacity: STR ${str} × 15 lbs = ${maxCapacity} lbs">
    <div class="encumbrance-header">
      <small>Carrying Capacity (STR ${str} × 15): <strong>${totalWeight.toFixed(1)} / ${maxCapacity} lbs</strong></small>
      ${isEncumbered ? '<span class="mode-badge mode-other">Encumbered</span>' : `<small class="muted">${pct}% load</small>`}
    </div>
    <div class="encumbrance-track" role="progressbar" aria-valuenow="${totalWeight.toFixed(1)}" aria-valuemin="0" aria-valuemax="${maxCapacity}">
      <div class="encumbrance-bar ${isEncumbered ? 'encumbered' : ''}" style="width: ${pct}%"></div>
    </div>
  </div>`;

  const filtered = allItems.map((item, originalIndex) => ({item, originalIndex}))
    .filter(({item}) => activeFilter === 'all' || getItemCategory(item) === activeFilter);

  const selectedItem = state.equipmentSelectedItem;
  const cardsHtml = filtered.length
    ? filtered.map(({item, originalIndex}) => {
        const cardHtml = globalThis.HSRUI.card(item, 'item', originalIndex, 'assets/');
        if (selectedItem && (selectedItem.id === item.id || selectedItem.name === item.name)) {
          return cardHtml.replace('class="item-card"', 'class="item-card selected-item-card" style="border-color:var(--gold-hi);box-shadow:0 0 12px rgba(var(--gold-hi-rgb),.6);"');
        }
        return cardHtml;
      }).join('')
    : '<p class="notice">No items in this category.</p>';

  const comparisonDrawerHtml = selectedItem ? statDiffDrawer(selectedItem, current) : '';

  return `${atmosphere('equipment', `${current.name || 'Party'} equipment`, 'A clear armory view of every host-reported item, affix, and visible property.')}${card('Reliquary gear', `<div class="equipment-layout-doll"><div class="equipment-doll-stage">${characterFigure(current, 'equipment-doll', 'idle')}<div class="scene-frame-label"><strong>${E(current.name || 'Hero')}</strong><small>${E(current.identity || current.role || 'Adventurer')}</small></div></div><div><div class="equipment-heading"><div><p class="eyebrow">Loadout and carried finds</p><h2>${E(current.name || 'Party')} equipment</h2></div><span class="gear-sigil" aria-hidden="true">✦</span></div>${encumbranceHtml}${chipsHtml}${comparisonDrawerHtml}<div class="compact-items">${cardsHtml}</div></div></div><p class="notice">Properties, affixes, effects, and identification state are reported by the host only.</p>${imprintPanel()}${attunementPanel()}`)}`;
}

function bookbagHudButton() {
  const current = actor();
  const allItems = [...(current.equipment || []), ...(state.view?.inventory || [])];
  const str = current.ability_scores?.STR ?? current.stats?.STR ?? 10;
  const maxCap = Math.max(15, str * 15);
  const totalW = allItems.reduce((sum, item) => sum + (Number(item.weight) || (item.density ? Number(item.density) : 1.0)), 0);
  const isEnc = totalW > maxCap;
  return `<button type="button" class="bookbag-hud-btn ${isEnc ? 'encumbered' : ''}" data-action="toggle-bookbag" title="Toggle Rune & Equipment Bookbag (Hotkeys: I / B)">
    <span class="icon">🎒</span>
    <span><strong>${totalW.toFixed(1)}</strong> / ${maxCap} lbs</span>
  </button>`;
}

function getItemSlotIcon(slot) {
  const icons = {
    head: '🪖', helmet: '🪖', necklace: '📿', neck: '📿', cloak: '🧥', torso: '🛡️', armor: '🛡️',
    hand: '⚔️', weapon: '⚔️', shield: '🛡️', legs: '🦵', boots: '🥾', ring: '💍', ring_1: '💍', ring_2: '💍'
  };
  return icons[String(slot || '').toLowerCase()] || '🎒';
}

function bookbagModal() {
  if (!state.bookbagOpen) return '';
  const current = actor();
  const inventory = state.view?.inventory || [];
  const equippedList = current.equipment || [];
  const str = current.ability_scores?.STR ?? current.stats?.STR ?? 10;
  const maxCap = Math.max(15, str * 15);
  const allItems = [...equippedList, ...inventory];
  const totalW = allItems.reduce((sum, item) => sum + (Number(item.weight) || (item.density ? Number(item.density) : 1.0)), 0);
  const pct = Math.min(100, Math.round((totalW / maxCap) * 100));
  const isEnc = totalW > maxCap;

  const activeTab = state.bookbagTab || 'all';
  const filterTabs = [
    ['all', 'All Items'],
    ['weapon', 'Weapons'],
    ['armor', 'Armor'],
    ['consumable', 'Potions/Belt'],
    ['gear', 'Gear'],
    ['imprint', 'Imprints/Runes']
  ];

  const filterTabHtml = filterTabs.map(([key, label]) => 
    `<button type="button" class="bookbag-filter-chip ${activeTab === key ? 'active' : ''}" data-action="bookbag-tab:${key}">${label}</button>`
  ).join('');

  const filteredItems = inventory.filter(item => {
    if (activeTab === 'all') return true;
    const cat = getItemCategory(item);
    if (activeTab === 'imprint') return item.kind === 'imprint';
    return cat === activeTab || item.slot === activeTab || item.gear_type === activeTab;
  });

  const slots = [
    {key: 'head', label: 'Head', item: equippedList.find(i => ['head', 'helmet'].includes(i.slot))},
    {key: 'neck', label: 'Neck', item: equippedList.find(i => ['neck', 'necklace'].includes(i.slot))},
    {key: 'hand', label: 'Weapon', item: equippedList.find(i => i.slot === 'hand')},
    {key: 'torso', label: 'Torso', item: equippedList.find(i => ['torso', 'armor'].includes(i.slot))},
    {key: 'shield', label: 'Shield', item: equippedList.find(i => i.slot === 'shield')},
    {key: 'legs', label: 'Legs', item: equippedList.find(i => i.slot === 'legs')},
    {key: 'boots', label: 'Boots', item: equippedList.find(i => i.slot === 'boots')},
    {key: 'ring', label: 'Ring', item: equippedList.find(i => i.slot?.startsWith('ring'))}
  ];

  const slotGridHtml = slots.map(s => {
    const has = Boolean(s.item);
    const icon = has ? getItemSlotIcon(s.item.slot) : getItemSlotIcon(s.key);
    const isTarget = state.bookbagSelectedItem && (state.bookbagSelectedItem.slot === s.key || (s.key === 'hand' && (state.bookbagSelectedItem.kind === 'weapon' || state.bookbagSelectedItem.item_type === 'weapon')) || (s.key === 'torso' && (state.bookbagSelectedItem.kind === 'armor' || state.bookbagSelectedItem.item_type === 'armor')));
    return `<div class="equipment-slot-box slot-${s.key} ${has ? 'has-item' : ''} ${isTarget ? 'highlight-target' : ''}" data-action="${has ? `inspect-equipped:${s.key}` : `slot-click:${s.key}`}" title="${has ? `${E(s.item.display_name || s.item.name)} (${s.label})` : `Empty ${s.label} slot`}">
      <span class="slot-icon">${icon}</span>
      <span class="slot-label">${has ? E((s.item.display_name || s.item.name).slice(0, 10)) : s.label}</span>
    </div>`;
  }).join('');

  const backpackGridHtml = filteredItems.length ? filteredItems.map((item) => {
    const icon = getItemSlotIcon(item.slot || item.gear_type || item.kind);
    const selected = state.bookbagSelectedItem?.id === item.id;
    return `<div class="osrs-item-tile ${selected ? 'selected' : ''}" data-action="bookbag-select:${E(item.id)}" title="${E(item.display_name || item.name)}">
      <span class="item-weight-badge">${(Number(item.weight) || 1.0).toFixed(1)} lbs</span>
      <span class="item-icon-art">${icon}</span>
      <span class="item-tile-name">${E(item.display_name || item.name)}</span>
    </div>`;
  }).join('') : '<p class="notice" style="grid-column: 1 / -1; text-align: center;">Backpack is empty in this category.</p>';

  const selectedItem = state.bookbagSelectedItem;
  let inspectorHtml = '<p class="notice">Click an item or equipped slot to view stats and options.</p>';
  if (selectedItem) {
    const isEquipped = equippedList.some(i => i.id === selectedItem.id || i.name === selectedItem.name);
    const isPotion = selectedItem.kind === 'potion' || getItemCategory(selectedItem) === 'consumable';
    inspectorHtml = `
      <div class="bookbag-item-inspector">
        <div>
          <h3>${E(selectedItem.display_name || selectedItem.name)}</h3>
          <small class="muted">${E(selectedItem.slot || selectedItem.category || 'Gear')} · Tier: ${E(selectedItem.tier || 'mundane')} · Weight: ${E((Number(selectedItem.weight) || 1.0).toFixed(1))} lbs</small>
        </div>
        ${selectedItem.base_damage ? `<p><strong>Damage:</strong> ${E(selectedItem.damage_dice || selectedItem.base_damage)} (${E(selectedItem.attack_ability || 'STR')})</p>` : ''}
        ${selectedItem.base_ac ? `<p><strong>Base AC:</strong> ${E(selectedItem.base_ac)} ${selectedItem.ac_bonus ? `(+${selectedItem.ac_bonus})` : ''}</p>` : ''}
        ${selectedItem.flavor ? `<p class="notice"><em>${E(selectedItem.flavor)}</em></p>` : ''}
        <div class="actions compact-actions">
          ${isEquipped 
            ? `<button type="button" class="action" data-action="unequip-item:${E(selectedItem.slot || selectedItem.name)}">Unequip</button>`
            : isPotion 
              ? `<button type="button" class="action primary" data-action="use-potion:${E(selectedItem.id)}">Drink Potion</button>`
              : `<button type="button" class="action primary" data-action="equip-item-id:${E(selectedItem.id)}">Equip</button>`
          }
        </div>
      </div>
    `;
  }

  const potions = inventory.filter(i => i.kind === 'potion' || getItemCategory(i) === 'consumable');
  const quickBeltHtml = potions.length ? potions.slice(0, 3).map(p => 
    `<button type="button" class="action secondary" data-action="use-potion:${E(p.id)}">🧪 Use ${E(p.display_name || p.name)}</button>`
  ).join('') : '<span class="muted">No potions in quick belt.</span>';

  return `
    <div class="bookbag-overlay" data-action="close-bookbag-backdrop">
      <div class="bookbag-modal" onclick="event.stopPropagation()">
        <div class="bookbag-header">
          <div class="bookbag-header-title">
            <span>🎒</span>
            <span>Rune & Equipment Bookbag</span>
          </div>
          <button type="button" class="bookbag-close-btn" data-action="close-bookbag" aria-label="Close bookbag">✕</button>
        </div>
        <div class="bookbag-capacity-bar">
          <div class="bookbag-capacity-info">
            <span>Carrying Capacity (STR ${str} × 15 = <strong>${maxCap} lbs</strong>)</span>
            <span><strong>${totalW.toFixed(1)} / ${maxCap} lbs</strong> ${isEnc ? '<span class="mode-badge mode-other">Encumbered</span>' : `<small class="muted">(${pct}% load)</small>`}</span>
          </div>
          <div class="bookbag-capacity-track">
            <div class="bookbag-capacity-fill ${isEnc ? 'encumbered' : ''}" style="width: ${pct}%"></div>
          </div>
        </div>
        <div class="bookbag-body">
          <div class="bookbag-doll-panel">
            <div class="osrs-equipment-grid">
              ${slotGridHtml}
            </div>
            <div class="equipment-doll-stage" style="transform: scale(0.85); transform-origin: top center;">
              ${characterFigure(current, 'bookbag-doll', 'idle')}
            </div>
          </div>
          <div class="bookbag-backpack-panel">
            <div class="bookbag-filter-chips">
              ${filterTabHtml}
            </div>
            <div class="osrs-backpack-grid">
              ${backpackGridHtml}
            </div>
            ${inspectorHtml}
          </div>
        </div>
        <div class="bookbag-quick-belt">
          <div><small><strong>Quick-Use Consumable Belt:</strong></small></div>
          <div class="actions compact-actions">${quickBeltHtml}</div>
        </div>
      </div>
    </div>
  `;
}

function bindBookbagControls() {
  document.querySelectorAll('[data-action="toggle-bookbag"]').forEach(node => {
    node.onclick = () => { state.bookbagOpen = !state.bookbagOpen; render(); };
  });
  document.querySelectorAll('[data-action="close-bookbag"], [data-action="close-bookbag-backdrop"]').forEach(node => {
    node.onclick = () => { state.bookbagOpen = false; render(); };
  });
  document.querySelectorAll('[data-action^="bookbag-tab:"]').forEach(node => {
    node.onclick = () => {
      state.bookbagTab = node.dataset.action.slice('bookbag-tab:'.length);
      render();
    };
  });
  document.querySelectorAll('[data-action^="bookbag-select:"]').forEach(node => {
    node.onclick = () => {
      const id = node.dataset.action.slice('bookbag-select:'.length);
      const inventory = state.view?.inventory || [];
      state.bookbagSelectedItem = inventory.find(i => String(i.id) === id) || null;
      render();
    };
  });
  document.querySelectorAll('[data-action^="inspect-equipped:"]').forEach(node => {
    node.onclick = () => {
      const slot = node.dataset.action.slice('inspect-equipped:'.length);
      const equippedList = actor().equipment || [];
      const eq = equippedList.find(i => i.slot === slot || (slot === 'ring' && i.slot?.startsWith('ring')));
      if (eq) state.bookbagSelectedItem = eq;
      render();
    };
  });
  document.querySelectorAll('[data-action^="equip-item-id:"]').forEach(node => {
    node.onclick = () => work(async () => {
      const itemId = node.dataset.action.slice('equip-item-id:'.length);
      const reply = await state.client.designAction(state.runId, {type: 'equip', item: itemId, actor: actingActorId()});
      result(reply);
      await loadReadout(state.runId);
      state.note = 'Item equipped.';
      addMessage(state.note);
      render();
    });
  });
  document.querySelectorAll('[data-action^="unequip-item:"]').forEach(node => {
    node.onclick = () => work(async () => {
      const target = node.dataset.action.slice('unequip-item:'.length);
      const reply = await state.client.designAction(state.runId, {type: 'unequip', slot: target, item: target, actor: actingActorId()});
      result(reply);
      await loadReadout(state.runId);
      state.note = 'Item unequipped.';
      addMessage(state.note);
      render();
    });
  });
  document.querySelectorAll('[data-action^="use-potion:"]').forEach(node => {
    node.onclick = () => work(async () => {
      const itemId = node.dataset.action.slice('use-potion:'.length);
      const reply = await state.client.designAction(state.runId, {type: 'consume', item: itemId, actor: actingActorId()});
      result(reply);
      await loadReadout(state.runId);
      state.note = 'Consumable used.';
      addMessage(state.note);
      render();
    });
  });
}
function cinematicDialogueStage(npc) {
  if (!npc) return '';
  const id = npc.id || npc.npc_id || npc.role;
  const role = String(npc.role || '').toLowerCase();
  const portrait = /wellkeeper/.test(role) ? 'wellkeeper' : /merchant|market/.test(role) ? 'merchant' : /smith/.test(role) ? 'smith' : /bar|tavern/.test(role) ? 'server' : /watch|guard/.test(role) ? 'watch' : 'herbalist';
  const disposition = String(npc.state?.disposition || npc.disposition || 'neutral').toLowerCase();
  const toneMap = {helpful: 'helpful', warm: 'warm', friendly: 'helpful', neutral: 'neutral', wary: 'wary', hostile: 'hostile'};
  const tone = toneMap[disposition] || 'neutral';
  const dispositionPct = {helpful: 100, warm: 80, neutral: 50, wary: 25, hostile: 5}[tone] || 50;
  const tell = npc.state?.reaction || npc.reaction || (Array.isArray(npc.tells) && npc.tells[0]) || 'Watching your hands and stance.';

  const transcript = [...(state.view?.conversation || []), ...(state.view?.recent_receipts || []), state.receipt]
    .filter(Boolean)
    .slice(-8)
    .map(row => ({
      speaker: row.speaker || (row.outcome ? 'Host' : npc.name || npc.role),
      text: row.reply || row.message || row.narration || row.summary || row.text || row.outcome,
      isPlayer: Boolean(row.intent || row.mode === 'ask' || row.mode === 'speak')
    }))
    .filter(row => Boolean(row.text));

  const dialogue = Array.isArray(npc.dialogue) && npc.dialogue.length ? npc.dialogue : [
    {id: 'ask-town', label: 'Ask what is happening in town', mode: 'ask', text: 'What is happening in town?'},
    {id: 'ask-route', label: 'Ask about the route to the well', mode: 'ask', text: 'Where is the route to the well?'},
    {id: 'ask-self', label: 'Ask who they are', mode: 'ask', text: 'Who are you, and what do you do here?'},
    {id: 'de-escalate', label: 'Lower the temperature', mode: 'speak', text: 'We are looking for information, not a fight.'}
  ];

  const getIntentIcon = (opt) => {
    const m = String(opt.mode || opt.id || '').toLowerCase();
    const t = String(opt.text || opt.label || '').toLowerCase();
    if (m === 'trade' || /trade|buy|sell|price/.test(t)) return {icon: '💰', cls: 'intent-trade', label: 'Trade'};
    if (m === 'threaten' || m === 'insult' || /threat|fight|kill/.test(t)) return {icon: '⚔️', cls: 'intent-threaten', label: 'Threaten'};
    if (m === 'lie' || /lie|deceive/.test(t)) return {icon: '🎭', cls: 'intent-lie', label: 'Deceive'};
    if (m === 'speak' || /lower|calm|peace|not a fight/.test(t)) return {icon: '🛡️', cls: 'intent-deescalate', label: 'De-escalate'};
    if (/work|quest|task|bounty/.test(t)) return {icon: '✦', cls: 'intent-quest', label: 'Quest'};
    return {icon: '?', cls: 'intent-inquire', label: 'Inquire'};
  };

  const visitedSet = state.visitedDialogues || new Set();

  const branchesHtml = dialogue.map(option => {
    const intent = getIntentIcon(option);
    const key = `${id}:${option.id || option.text}`;
    const visited = visitedSet.has(key);
    return `<button type="button" class="dialogue-choice-btn ${visited ? 'visited' : ''}" data-dialogue-target="${E(id)}" data-dialogue-mode="${E(option.mode || 'speak')}" data-dialogue-text="${E(option.text)}" data-dialogue-key="${E(key)}" title="${E(option.text)}">
      <span class="dialogue-intent-badge ${intent.cls}" aria-hidden="true">${intent.icon}</span>
      <span>${E(option.label || option.text)}</span>
      ${visited ? '<small class="muted" style="margin-left:auto;">✓</small>' : '<small class="notice" style="margin-left:auto;color:var(--gold-hi);">●</small>'}
    </button>`;
  }).join('');

  return `<section class="cinematic-dialogue-stage" aria-label="Social dialogue with ${E(npc.name || npc.role)}">
    <div class="dialogue-speaker-col">
      <div class="dialogue-speaker-portrait portrait-${portrait}" role="img" aria-label="${E(npc.name || npc.role)} portrait"></div>
      <div>
        <h3 style="margin:4px 0;">${E(npc.name || npc.role)}</h3>
        <small class="muted">${E(npc.role || 'Town Resident')}</small>
      </div>
      <div class="disposition-meter-wrap">
        <div class="disposition-header">
          <span>Disposition:</span>
          <span class="disposition-badge tone-${tone}">${E(disposition)}</span>
        </div>
        <div class="disposition-track">
          <div class="disposition-fill tone-${tone}" style="width: ${dispositionPct}%"></div>
        </div>
        <small class="notice" style="font-size:10px;text-align:left;margin-top:2px;"><strong>Reaction:</strong> ${E(tell)}</small>
      </div>
      <button type="button" class="action secondary" data-action="close-cinematic-dialogue" style="width:100%;margin-top:auto;">Leave exchange</button>
    </div>
    <div class="dialogue-content-col">
      <div class="dialogue-transcript-box" aria-live="polite">
        ${transcript.length ? transcript.map((line, idx) => `
          <div class="dialogue-speech-bubble ${line.isPlayer ? 'is-player' : ''} ${idx === transcript.length - 1 ? 'latest' : ''}">
            <strong style="color:${line.isPlayer ? '#60a5fa' : 'var(--gold-hi)'};font-size:12px;">${E(line.speaker)}:</strong>
            <p style="margin:0;font-size:13px;color:var(--paper);">${E(line.text)}</p>
          </div>
        `).join('') : '<p class="notice">The resident meets your gaze, awaiting your opening words.</p>'}
      </div>
      <div class="dialogue-branches-grid">
        <p class="label">Dialogue Options</p>
        ${branchesHtml}
      </div>
    </div>
  </section>`;
}

function residentCard(npc) {
  const id = npc.id || npc.npc_id || npc.role;
  const role = String(npc.role || '').toLowerCase();
  const portrait = /wellkeeper/.test(role) ? 'wellkeeper' : /merchant|market/.test(role) ? 'merchant' : /smith/.test(role) ? 'smith' : /bar|tavern/.test(role) ? 'server' : /watch|guard/.test(role) ? 'watch' : 'herbalist';
  const dialogue = Array.isArray(npc.dialogue) ? npc.dialogue : [];
  const tree = dialogue.map(option => `<button type="button" class="action secondary dialogue-option" data-dialogue-target="${E(id)}" data-dialogue-mode="${E(option.mode)}" data-dialogue-text="${E(option.text)}" title="${E(option.text)}">${E(option.label || option.text)}</button>`).join('');
  const traits = (npc.traits || []).map(trait => `<span>${E(String(trait).replaceAll('_', ' '))}</span>`).join('');
  const offers = Object.keys(npc.offers || {}).filter(key => npc.offers[key]).map(key => String(key).replaceAll('_', ' ')).join(' · ');
  return `<article class="npc-card visual-npc" data-resident="${E(id)}"><div class="resident-doll-frame">${characterFigure(npc, 'resident-doll', 'idle')}<div class="npc-portrait portrait-${portrait}" role="img" aria-label="${E(npc.name || npc.role || 'town resident')} portrait"></div></div><div><h3>${E(npc.name || npc.role)}</h3><p>${E(npc.role || npc.disposition || 'Disposition not reported.')}</p><p class="npc-state"><strong>State:</strong> ${E(npc.state?.disposition || npc.disposition || 'unknown')} · ${E(npc.state?.reaction || npc.reaction || 'no reaction reported')}</p>${traits ? `<div class="npc-traits" aria-label="Visible traits">${traits}</div>` : ''}${offers ? `<p class="notice">Offers: ${E(offers)}</p>` : ''}<div class="dialogue-tree"><p class="label">Dialogue tree</p><div class="actions compact-actions">${tree || '<span class="notice">No public dialogue options.</span>'}</div></div><div class="actions compact-actions"><button type="button" class="action primary" data-action="talk-cinematic:${E(id)}">🗣️ Talk to ${E(npc.name || npc.role)}</button>${CONVERSATION_MODES.map(m => `<button type="button" class="action secondary" data-conversation="${E(id)}" data-conversation-mode="${E(m.mode)}">${E(m.label)}</button>`).join('')}</div></div></article>`;
}

function residents() {
  const allNpcs = Object.values(state.view?.room?.npcs || {});
  const activeNpcId = state.activeDialogueNpc;
  const activeNpc = allNpcs.find(n => (n.id || n.npc_id || n.role) === activeNpcId) || (activeNpcId ? allNpcs[0] : null);

  const cinematicHtml = activeNpc ? cinematicDialogueStage(activeNpc) : '';
  const galleryHtml = allNpcs.map(residentCard).join('') || '<p>No residents are visible in this public readout.</p>';

  const transcript = [...(state.view?.conversation || []), ...(state.view?.recent_receipts || []), state.receipt].filter(Boolean).slice(-8).map(row => row.reply || row.message || row.narration || row.summary || row.text || row.outcome).filter(Boolean);
  const chat = transcript.length ? transcript.map((line, index) => `<div class="chat-line ${index === transcript.length - 1 ? 'latest' : ''}"><span class="chat-mark">${index % 2 ? '◇' : '◈'}</span><p>${E(line)}</p></div>`).join('') : '<p class="notice">No public conversation has been recorded yet. Choose a resident or begin with an observation.</p>';
  // These phrases are parsed only by the Floor One social grammar; a dungeon
  // room has no town conversation to continue, so offer none rather than send
  // a phrase the host cannot translate.
  const chatChoices = !floorOneWorld() ? '' : [button('We look around', 'intent:we look around', 'secondary'), button('Ask what is happening', 'intent:ask what is happening', 'secondary'), button('Keep listening', 'intent:keep listening', 'secondary')].join('');

  return `${atmosphere('residents', 'Visible residents', 'Pretty social portraits show who is speaking; ordinary scene figures keep the lived-in town readable.')}${cinematicHtml}${card('Town residents / roster', `<div class="npc-gallery">${galleryHtml}</div>`)}` + (activeNpc ? '' : card('Town conversation', `<div class="chat-window" aria-live="polite">${chat}</div>${chatChoices ? `<div class="chat-choices">${chatChoices}</div>` : ''}`));
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
function optionsSection(id, title, summary, body, open = false) {
  return `<details class="options-section" id="${E(id)}" ${open ? 'open' : ''}><summary><span><strong>${E(title)}</strong><small>${E(summary)}</small></span><span class="options-section-chevron" aria-hidden="true">⌄</span></summary><div class="options-section-body">${body}</div></details>`;
}
function optionsIndex() {
  const rows = [
    ['options-interface', 'Interface layout'], ['options-visibility', 'Visible blocks'],
    ['options-style', 'Style and accessibility'], ['options-story', 'Story and audio'], ['options-combat', 'Combat presentation'], ['options-voices', 'Voices'],
    ['options-link', 'Connection and clock'], ['options-text', 'Commands and vocabulary'],
  ];
  return `<nav class="options-index" aria-label="Options index"><strong>Jump to</strong>${rows.map(([id, label]) => `<a href="#${id}">${E(label)}</a>`).join('')}</nav>`;
}
// Swatch previews for Options > Interface theme. A swatch shows a theme that is
// not active, so it cannot read that theme's tokens; these mirror the channels
// in tokens.css (THEME). Adding a theme = one block there + one row here.
const INTERFACE_THEMES = [
  {id: 'gold', name: 'Gold', note: 'Reliquary', accent: '#c9a86a', lift: '#262d44', surface: '#11131c'},
  {id: 'moon', name: 'Moon', note: 'Silver', accent: '#c8d8ec', lift: '#243a58', surface: '#0d1523'},
  {id: 'ember', name: 'Ember', note: 'Rose', accent: '#e3a19a', lift: '#482738', surface: '#1b0f17'},
];
function options() {
  const p = state.preferences;
  const vocabulary = state.vocabulary || {};
  const textOptions = Object.entries(vocabulary).filter(([key, value]) => Array.isArray(value)).map(([key, values]) => `<details><summary><strong>${E(key)}</strong></summary><p>${E(values.join(' · '))}</p></details>`).join('');
  const interfaceBody = `<label class="option-row"><span><strong>Icon actions</strong><small>Use compact symbols for bottom action controls while keeping accessible labels.</small></span><input type="checkbox" data-pref="iconActions" ${p.iconActions ? 'checked' : ''}></label>
       <fieldset class="layout-presets"><legend>Workspace preset</legend><p class="notice">Each preset changes the actual desktop composition. You can still tune every part below.</p><div class="preset-grid">
         <button type="button" class="preset-card ${p.layout === 'sanctum' ? 'selected' : ''}" data-action="layout-preset:sanctum"><i class="preset-map sanctum" aria-hidden="true"><b></b><b></b><b></b></i><strong>Sanctum</strong><small>Party, scene, and navigation together.</small></button>
         <button type="button" class="preset-card ${p.layout === 'focus' ? 'selected' : ''}" data-action="layout-preset:focus"><i class="preset-map focus" aria-hidden="true"><b></b><b></b><b></b></i><strong>Focus</strong><small>A wide, distraction-free scene.</small></button>
         <button type="button" class="preset-card ${p.layout === 'idle' ? 'selected' : ''}" data-action="layout-preset:idle"><i class="preset-map idle" aria-hidden="true"><b></b><b></b><b></b></i><strong>Idle</strong><small>Quiet, text-first, low-animation view.</small></button>
       </div></fieldset>
       <label class="option-row"><span><strong>Menu density</strong><small>Adjust the room, battle, and equipment navigation rail.</small></span><select data-pref="menuDensity" aria-label="Menu density"><option value="compact" ${p.menuDensity === 'compact' ? 'selected' : ''}>Compact</option><option value="comfortable" ${p.menuDensity === 'comfortable' ? 'selected' : ''}>Comfortable</option><option value="spacious" ${p.menuDensity === 'spacious' ? 'selected' : ''}>Spacious</option></select></label>
       <label class="option-row"><span><strong>Scene size</strong><small>Choose how much desktop space the illustrated room or battle occupies.</small></span><select data-pref="sceneScale"><option value="compact" ${p.sceneScale === 'compact' ? 'selected' : ''}>Compact</option><option value="standard" ${p.sceneScale === 'standard' ? 'selected' : ''}>Standard</option><option value="cinematic" ${p.sceneScale === 'cinematic' ? 'selected' : ''}>Cinematic</option></select></label>
      <label class="option-row"><span><strong>Fixed stage</strong><small>Fit character creation to one screen at a set shape instead of letting it scroll.</small></span><select data-pref="stageMode"><option value="on" ${p.stageMode !== 'off' ? 'selected' : ''}>On</option><option value="off" ${p.stageMode === 'off' ? 'selected' : ''}>Off (scrolling page)</option></select></label>
      <label class="option-row"><span><strong>Stage shape</strong><small>The aspect the stage is drawn at. "Fill" matches your display exactly and never letterboxes.</small></span><select data-pref="stageAspect"><option value="2.28:1" ${p.stageAspect === '2.28:1' ? 'selected' : ''}>2.28:1 (cinematic)</option><option value="2:1" ${p.stageAspect === '2:1' ? 'selected' : ''}>2:1</option><option value="16:9" ${p.stageAspect === '16:9' ? 'selected' : ''}>16:9</option><option value="21:9" ${p.stageAspect === '21:9' ? 'selected' : ''}>21:9 (ultrawide)</option><option value="fill" ${p.stageAspect === 'fill' ? 'selected' : ''}>Fill the display</option></select></label>
      <label class="option-row"><span><strong>Stage detail</strong><small>How many logical pixels tall the stage is drawn before it is scaled to your display. Higher fits more on screen at smaller text; it never changes whether things fit.</small></span><select data-pref="stageResolution"><option value="compact" ${p.stageResolution === 'compact' ? 'selected' : ''}>Compact · 820 (largest text)</option><option value="standard" ${p.stageResolution === 'standard' ? 'selected' : ''}>Standard · 900</option><option value="roomy" ${p.stageResolution === 'roomy' ? 'selected' : ''}>Roomy · 1000</option><option value="max" ${p.stageResolution === 'max' ? 'selected' : ''}>Maximum · 1120 (most on screen)</option></select></label>
       <label class="option-row"><span><strong>Engine help</strong><small>Keep the compact Help menu near the overall command bar or float it on either desktop edge.</small></span><select data-pref="dockPosition"><option value="bottom" ${p.dockPosition === 'bottom' ? 'selected' : ''}>Near command bar</option><option value="left" ${p.dockPosition === 'left' ? 'selected' : ''}>Float left</option><option value="right" ${p.dockPosition === 'right' ? 'selected' : ''}>Float right</option></select></label>`;
  const visibilityBody = `<div class="option-row"><span><strong>Visible interface blocks</strong><small>Use the header Menu button to show session details. These settings leave the main display and Menu button available.</small></span><span class="option-checks"><label><input type="checkbox" data-pref="showNavigation" ${p.showNavigation ? 'checked' : ''}> Navigation</label><label><input type="checkbox" data-pref="showWorkspace" ${p.showWorkspace !== false ? 'checked' : ''}> Workspace</label></span></div>
       <div class="option-row"><span><strong>Menu sizing</strong><small>Adjust the independent Menu block.</small></span><select data-pref="menuSize"><option value="compact" ${p.menuSize === 'compact' ? 'selected' : ''}>Compact</option><option value="standard" ${p.menuSize === 'standard' ? 'selected' : ''}>Standard</option><option value="large" ${p.menuSize === 'large' ? 'selected' : ''}>Large</option></select></div>
       <div class="option-row"><span><strong>Debug / Simulation / Nerdy Mode</strong><small>Reveal full interface stats everywhere — connection detail, latency history, and a manual Party override for testing multi-actor layouts.</small></span><input type="checkbox" data-pref="debugMode" ${p.debugMode ? 'checked' : ''}></div>
       ${p.debugMode ? `<div class="option-row"><span><strong>Party (debug override)</strong><small>Force the Party rail shown or hidden regardless of actual party size.</small></span><input type="checkbox" data-pref="showParty" ${p.showParty ? 'checked' : ''}></div>` : ''}`;
  const styleBody = `<fieldset class="accent-picker"><legend>Interface theme</legend><p class="notice">Recolours the whole interface — panels, text, borders, the title world and the play header — while preserving contrast.</p><div class="accent-options">${INTERFACE_THEMES.map(theme => `<label class="accent-swatch"><input type="radio" name="accent" value="${theme.id}" data-pref="accent" ${p.accent === theme.id ? 'checked' : ''}><span class="swatch" style="background:radial-gradient(circle at 76% 50%,${theme.accent} 0 9px,transparent 10px),linear-gradient(135deg,${theme.lift},${theme.surface} 70%)"></span><strong>${theme.name}</strong><small>${theme.note}</small></label>`).join('')}</div></fieldset>
       <label class="option-row"><span><strong>Text size — ${Math.round(Number(p.textScale) * 100)}%</strong><small>Scale the mostly-text interface without changing the engine.</small></span><input type="range" min=".9" max="1.25" step=".05" value="${E(p.textScale)}" data-pref="textScale" aria-label="Text size"></label>
       <fieldset class="display-elements"><legend>Status display</legend><p class="notice">Show additional presentation controls without changing host state.</p><span class="option-checks"><label><input type="checkbox" data-pref="showTickIndicator" ${p.showTickIndicator ? 'checked' : ''}> Show tick pulse</label><label><input type="checkbox" data-pref="showActionDock" ${p.showActionDock !== false ? 'checked' : ''}> Action dock</label><label><input type="checkbox" data-pref="showStatusMessages" ${p.showStatusMessages !== false ? 'checked' : ''}> Status messages</label></span></fieldset>
       <label class="option-row"><span><strong>Reduced motion</strong><small>Disable transition effects for idle or low-power use.</small></span><input type="checkbox" data-pref="motion" ${p.motion === 'reduced' ? 'checked' : ''}></label>
       <label class="option-row"><span><strong>Soft effects</strong><small>Reduce glow and shadow intensity.</small></span><input type="checkbox" data-pref="effects" ${p.effects === 'soft' ? 'checked' : ''}></label>`;
  const pointerBody = `<label class="option-row"><span><strong>Swap Mouse Buttons</strong><small>Use right-click for main actions and left-click for the context menu.</small></span><input type="checkbox" data-pref="swapMouseButtons" ${p.swapMouseButtons ? 'checked' : ''}></label>
       <label class="option-row"><span><strong>Double Click Speed — ${p.doubleClickSpeed || 500}ms</strong><small>Adjust how fast you need to click for double-click actions.</small></span><input type="range" min="100" max="1000" step="50" value="${E(p.doubleClickSpeed || 500)}" data-pref="doubleClickSpeed" aria-label="Double click speed"></label>`;
  const textBody = `<p>Use these host-routed phrases anywhere the intent box appears. Talk buttons on visible residents prefill a conversation request; the NPC response and consequences come back only through the public host receipt.</p>${textOptions || '<p class="notice">Text vocabulary is unavailable until the local gateway refreshes.</p>'}`;
  return `<div class="mode-menu">${state.phase === 'options' ? breadcrumb('Main Menu', 'Options') : breadcrumb('Game', 'Options')}${atmosphere('options', 'Display options', 'Tune the illustrated interface without changing a roll, room, item, or saved run.')}${card('Options', `<h2>HSR Interface</h2><p>Preferences are local to this browser and survive game-mode changes, navigation, and reloads.</p>${optionsIndex()}${optionsSection('options-interface', 'Interface layout', 'Workspace composition, density, and action placement.', interfaceBody, true)}${optionsSection('options-visibility', 'Visible blocks', 'Toggle the Menu and Navigation surfaces, and Debug/Simulation/Nerdy Mode.', visibilityBody)}${optionsSection('options-style', 'Style and accessibility', 'Accent, text scale, motion, effects, and status details.', styleBody)}${optionsSection('options-pointer', 'Pointer and Mouse', 'Double click timing, swap mouse buttons, and hover behavior.', pointerBody)}${optionsSection('options-story', 'Story, audio and accessibility', 'Text speed, cutscenes, colour-blind support, and volume by category.', storyOptions())}${optionsSection('options-combat', 'Combat presentation', 'Playback timing, targets, and tactical display.', combatOptions())}${optionsSection('options-voices', 'Voices and sound cues', 'Speech cards, divine presence, sound effects, and who speaks.', voiceOptions())}${optionsSection('options-link', 'Connection and clock', 'Heartbeat, clock format, drift, and latency history.', linkOptions())}${optionsSection('options-text', 'Commands and vocabulary', 'Host-routed intent phrases available in the current gateway.', textBody)}<div class="mode-menu-footer"><div class="footer-left">${button('Reset display preferences', 'reset-preferences', 'secondary')}${button('Refresh engine state', 'refresh-readout', 'secondary')}</div><div class="footer-right">${button('Back', 'back-options', 'secondary')}${state.phase === 'ready' ? button('Return to Game', 'return-game', 'primary') : ''}</div></div>`, 'mode-menu-card')}</div>`;
}
// Context menus describe public game targets only. Unrelated interface controls
// keep their normal browser context menu.
const CONTEXT_ICONS = {item: '◇', actor: '♙', 'stage-actor': '♙', conversation: '☵', resident: '☵', object: '⌕', scene: '⌂', action: '▸', fullscreen: '⛶', system_menu: '⚙'};
function placeContextMenu(menuState) {
  const menu = document.querySelector('.hsr-context-menu');
  if (!menu || state.contextMenu !== menuState) return;
  const rect = menu.getBoundingClientRect();
  const width = Math.max(menu.offsetWidth || 0, rect.width || 0, 260);
  const height = Math.max(menu.offsetHeight || 0, rect.height || 0, 200);
  menu.style.left = `${Math.max(8, Math.min(Number(menuState.x) || 8, window.innerWidth - width - 8))}px`;
  menu.style.top = `${Math.max(8, Math.min(Number(menuState.y) || 8, window.innerHeight - height - 8))}px`;
}
document.addEventListener('pointerdown', event => { if (event.button === 0 && state.contextMenu && !event.target.closest('.hsr-context-menu')) dismissContextMenu(); });
function dismissContextMenu() { state.contextMenu = null; document.querySelector('.hsr-context-menu')?.remove(); }
function contextMenu() {
  const menu = state.contextMenu;
  if (!menu) return '';
  const targetLabel = menu.label || 'Workspace';
  const icon = CONTEXT_ICONS[menu.primaryTarget?.kind] || CONTEXT_ICONS[menu.contextKind] || '✧';
  const width = Math.min(280, window.innerWidth - 16);
  const left = Math.max(8, Math.min(Number(menu.x) || 8, window.innerWidth - width - 8));
  const top = Math.max(8, Math.min(Number(menu.y) || 8, window.innerHeight - 260));
  const actions = menu.contextActions?.length
    ? `<div class="context-menu-actions">${menu.contextActions.map((row, index) => `<button type="button" class="action ${index === 0 ? 'primary-action' : 'secondary'}" data-action="context-primary:${index}"><span>${E(row.label)}</span></button>`).join('')}</div>`
    : menu.primaryAction ? `<div class="context-menu-actions"><button type="button" class="action primary-action" data-action="context-primary"><span>${E(menu.primaryLabel || `Open ${targetLabel}`)}</span></button></div>` : '';
  return `<aside class="hsr-context-menu" role="dialog" aria-label="${E(targetLabel)} actions" style="left:${left}px;top:${top}px;--context-width:${width}px">
    <p class="context-menu-title"><span class="context-menu-icon" aria-hidden="true">${icon}</span><strong>${E(targetLabel)}</strong></p>
    ${menu.description ? `<p class="context-menu-description">${E(menu.description)}</p>` : '<p class="notice">No additional description is available.</p>'}
    <p class="context-menu-description" data-context-detail${menu.detail ? '' : ' hidden'}>${E(menu.detail || '')}</p>
    ${actions}
    
  </aside>`;
}
// The right-click action wheel on an enemy (mouse / hybrid combat styles).
// Items come from combat-input.radialItems over the host's contextual rows.
function openCombatRadial(id, x, y) {
  const who = currentCombatant();
  state.focusTarget = id;
  dismissContextMenu();
  state.combatRadial = {x, y, target: id,
    items: radialItems(id, state.view?.combat?.contextual_actions || [], {identity: who.identity, playerTurn: myTacticalTurn()})};
  render();
  document.querySelector('.combat-radial button:not([disabled])')?.focus({preventScroll: true});
}
function combatRadialMenu() {
  const menu = state.combatRadial;
  if (!menu || !tacticalActive()) return '';
  const name = livingOpponents().find(row => row.id === menu.target)?.name || menu.target;
  const spots = radialLayout(menu.items.length, 78);
  const x = Math.max(96, Math.min(Number(menu.x) || 0, innerWidth - 96));
  const y = Math.max(96, Math.min(Number(menu.y) || 0, innerHeight - 96));
  const items = menu.items.map((item, index) => `<button type="button" class="combat-radial-item${item.available ? '' : ' is-unavailable'}" data-radial-item="${index}" style="--rx:${spots[index].x}px;--ry:${spots[index].y}px"${item.available ? '' : ' disabled'} data-tooltip="${E(item.available ? item.label : `${item.label}: ${item.reason}`)}" aria-label="${E(item.label)}"><span aria-hidden="true">${E(item.icon)}</span><small>${E(item.label)}</small></button>`).join('');
  return `<aside class="combat-radial" role="menu" aria-label="${E(name)} combat actions" style="left:${x}px;top:${y}px"><strong class="combat-radial-hub">${E(name)}</strong>${items}</aside>`;
}
function runRadialItem(index) {
  const menu = state.combatRadial;
  const item = menu?.items?.[index];
  state.combatRadial = null;
  if (!item || !item.available) { render(); return; }
  const target = menu.target;
  const name = livingOpponents().find(row => row.id === target)?.name || target;
  if (item.action === 'inspect') { render(); openExamineDialog({entity_type: 'target', entity_id: target}); return; }
  if (item.action === 'cast') { state.focusTarget = target; render(); clickEngineButton('cast'); return; }
  submitTarget(item.action, 'target', target, `${item.label} → ${name}`);
}
function toggleFullscreen() {
  try {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen?.().catch(() => {});
    } else {
      document.exitFullscreen?.().catch(() => {});
    }
  } catch {}
}
function systemMenuModal() {
  if (!state.systemMenuOpen) return '';
  const isFullscreen = Boolean(document.fullscreenElement);
  return `<div class="game-system-modal-backdrop" role="dialog" aria-modal="true" aria-label="System Menu" data-action="close-system-menu">
    <div class="game-system-modal-card" onclick="event.stopPropagation()">
      <div class="game-system-modal-header">
        <span class="system-modal-crest">✦</span>
        <h2>Hollow Star Reliquary</h2>
        <p class="system-modal-sub">System &amp; Session Controls</p>
      </div>
      <div class="game-system-modal-actions">
        <button type="button" class="action primary system-btn" data-action="close-system-menu"><span class="btn-icon">▶</span> Resume Expedition</button>
        <button type="button" class="action secondary system-btn" data-action="toggle-fullscreen"><span class="btn-icon">⛶</span> ${isFullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen (F11)'}</button>
        ${state.runId ? `<button type="button" class="action secondary system-btn" data-action="save"><span class="btn-icon">⌑</span> Save Checkpoint</button>` : ''}
        <button type="button" class="action secondary system-btn" data-action="menu:options"><span class="btn-icon">⚙</span> Interface &amp; Audio Options</button>
        <div class="system-btn-divider"></div>
        <button type="button" class="action secondary system-btn" data-action="title"><span class="btn-icon">⌂</span> Return to Main Menu</button>
      </div>
      <button type="button" class="system-close-corner" data-action="close-system-menu" aria-label="Close menu">✕</button>
    </div>
  </div>`;
}
// ---- Options: combat presentation and connection -------------------------
const PREF_FORMAT = {
  'combat.speed': v => `${Number(v).toFixed(2)}×`, 'combat.catchUp': v => `${Math.round(Number(v) * 100)}% time`,
  'combat.maxQueue': v => `${v} beats`, 'combat.gapMs': v => `${v} ms`, 'combat.lunge': v => (Number(v) ? `${v} px` : 'off'),
  'combat.floatMs': v => `${(Number(v) / 1000).toFixed(1)} s`, 'combat.floatScale': v => `${Math.round(Number(v) * 100)}%`,
  'link.warnMs': v => `${v} ms`, 'link.badMs': v => `${v} ms`, 'link.historySize': v => `${v} samples`,
  'voice.pace': v => `${Number(v).toFixed(2)}×`, 'voice.maxCards': v => `${v} cards`,
};
function formatPref(path, value) { return (PREF_FORMAT[path] || String)(value); }
function prefControl(path, label, help, spec) {
  const [group, key] = path.split('.');
  const value = state.preferences[group][key];
  let control;
  if (spec.type === 'bool') control = `<input type="checkbox" data-pref-path="${path}" data-kind="bool" ${value ? 'checked' : ''}>`;
  else if (spec.type === 'select') control = `<select data-pref-path="${path}" data-kind="${spec.number ? 'number' : 'text'}">${spec.options.map(([v, text]) => `<option value="${E(v)}" ${String(v) === String(value) ? 'selected' : ''}>${E(text)}</option>`).join('')}</select>`;
  else control = `<span class="pref-range"><input type="range" data-pref-path="${path}" data-kind="number" min="${spec.min}" max="${spec.max}" step="${spec.step}" value="${E(value)}" aria-label="${E(label)}"><output data-pref-out="${path}">${E(formatPref(path, value))}</output></span>`;
  const changed = String(value) !== String(NESTED_PREFERENCES[group][key]);
  return `<label class="option-row pref-row${changed ? ' is-changed' : ''}"><span><strong>${E(label)}${changed ? ' <em class="pref-changed" title="Changed from default">•</em>' : ''}</strong><small>${E(help)}</small><code class="pref-key">${E(path)} = ${E(JSON.stringify(value))}</code></span>${control}</label>`;
}
function combatOptions() {
  const c = state.preferences.combat;
  const rows = [
    ['Playback', [
      ['combat.enabled', 'Animate combat', 'Play each host result as beats. Off: the stage simply updates to the new state.', {type: 'bool'}],
      ['combat.speed', 'Playback speed', 'Multiplies every beat duration. 2× halves them.', {type: 'range', min: .25, max: 3, step: .25}],
      ['combat.catchUp', 'Catch-up pacing', 'Beat time while more than two beats are waiting. Lower catches up faster after a busy enemy turn.', {type: 'range', min: .2, max: 1, step: .05}],
      ['combat.gapMs', 'Gap between beats', 'Rest after each beat, before speed scaling.', {type: 'range', min: 0, max: 600, step: 20}],
    ]],
    ['Motion', [
      ['combat.lunge', 'Lunge distance', 'How far a striker steps toward its target. 0 keeps figures planted.', {type: 'range', min: 0, max: 96, step: 4}],
      ['combat.flinch', 'Hit flinch', 'Target flashes and shakes when struck.', {type: 'bool'}],
      ['combat.wounds', 'Wounds', 'A blow that does damage leaves a cut on the figure it hit, which stays for the rest of the fight.', {type: 'bool'}],
      ['combat.shakeOnCrit', 'Crit stage shake', 'The whole stage jolts on a critical hit.', {type: 'bool'}],
      ['combat.poses', 'Champion pose swaps', 'Champions with authored art switch to strike and guard frames.', {type: 'bool'}],
    ]],
    ['Numbers', [
      ['combat.floats', 'Floating numbers', 'Detailed adds the host roll math: d20, bonus, total vs AC/DC, and damage dice.', {type: 'select', options: [['off', 'Off'], ['damage', 'Damage only'], ['detailed', 'Detailed (roll math)']]}],
      ['combat.showMisses', 'Show misses', 'A "Miss" label when an attack fails.', {type: 'bool'}],
      ['combat.typeTint', 'Tint by damage type', 'Fire, cold, lightning, necrotic and so on get their own colour.', {type: 'bool'}],
      ['combat.floatMs', 'Number lifetime', 'How long a floating number stays up.', {type: 'range', min: 500, max: 3000, step: 100}],
      ['combat.floatScale', 'Number size', 'Scale of floating numbers.', {type: 'range', min: .6, max: 2, step: .1}],
    ]],
    ['Controls', [
      ['combat.style', 'Combat controls', 'Hybrid: every style at once. Turn-based: the command dock and pickers only. WASD: W/A/S/D steps 5 ft, Space attacks the focused or nearest foe in reach (or ends the turn once your attack is spent), 1-4 fire the hotbar, Tab/Q cycle targets. Mouse: left-click the ground to move, left-click a foe to focus it (double-click attacks), right-click a foe for the action wheel, right-click the ground to clear. The host still validates every move and roll.', {type: 'select', options: [['hybrid', 'Hybrid (all)'], ['turn_based', 'Turn-based dock'], ['direct_wasd', 'WASD + Space'], ['mouse_click', 'Left / right mouse']]}],
      ['combat.autoNpc', 'Automatic enemy turns', 'Enemies and their reactions play by themselves until a hero must decide. Off: an explicit "Play enemy turns" button.', {type: 'bool'}],
      ['combat.threatWarn', 'Opportunity-attack warning', 'A step that would leave a foe\'s reach rings that foe in red first; repeat the step to commit it.', {type: 'bool'}],
    ]],
    ['Stage overlays & targeting', [
      ['combat.hpBars', 'HP bars', 'Bars drawn on the figures themselves, on the ground, flight and arcade stages alike.', {type: 'select', options: [['all', 'Everyone'], ['enemies', 'Enemies only'], ['party', 'Party only'], ['off', 'Off']]}],
      ['combat.hpNumbers', 'HP numbers', 'Current/max printed on the bar.', {type: 'bool'}],
      ['combat.statusChips', 'Condition badges', 'Up to four status abbreviations over the bar; hover for the full name.', {type: 'bool'}],
      ['combat.turnMarker', 'Active-turn marker', 'A chevron over whoever the host says is acting.', {type: 'bool'}],
      ['combat.targetRing', 'Target ring', 'Ring under the focused enemy, dashed rings under every legal pick while choosing.', {type: 'bool'}],
      ['combat.clickMode', 'Clicking an enemy', 'Focus: click marks the target, double-click attacks it. Attack: one click attacks. Double: only a double-click attacks.', {type: 'select', options: [['focus', 'Focus (double-click attacks)'], ['attack', 'Attack on click'], ['double', 'Attack on double-click only']]}],
      ['combat.attackUsesFocus', 'Attack uses focused target', 'The Attack button fires at the focused enemy instead of opening the picker.', {type: 'bool'}],
      ['combat.hotkeys', 'Hotkeys', 'On the battle screen: [ ] or Tab cycle targets, E ends the turn, Esc clears; WASD styles add movement, Space and 1-4; the turn-based and mouse styles keep A to attack. Ignored while typing.', {type: 'bool'}],
    ]],
    ['Diagnostics', [
      ['combat.fillMissing', 'Infer dropped hits', 'The host sends its last five receipts. When HP falls by more than those explain, play the difference as an inferred hit.', {type: 'bool'}],
      ['combat.inspector', 'Beat inspector', 'A log under the battle stage: every beat with timing, roll math and flags.', {type: 'bool'}],
    ]],
  ];
  const groups = rows.map(([title, items]) => `<div class="pref-group"><h4>${E(title)}</h4>${items.map(([path, label, help, spec]) => prefControl(path, label, help, spec)).join('')}</div>`).join('');
  return `<fieldset class="pref-section" id="combat-options"><legend>Combat presentation</legend>
    <p class="notice">How host-resolved combat is drawn. None of this changes a roll, a hit, or damage; it only changes what you see and when.</p>
    <div class="combat-demo">${combatDemoStage()}<div class="actions">${button('Play demo', 'combat-demo', 'primary')}${button('Reset combat defaults', 'reset-pref-group:combat', 'secondary')}</div>
    <p class="notice">The demo runs sample beats (hit, miss, crit, heal) through the same player with your current settings.</p></div>
    ${groups}${c.inspector ? `<p class="notice">Inspector is on. It appears under the battle stage and below the demo.</p>${combatInspector()}` : ''}</fieldset>`;
}
function voiceOptions() {
  const rows = [
    ['On screen', [
      ['voice.cards', 'Voice cards', 'Doran, Sera and Ember speak in cards over the scene. Off: lines only go to the Messages log.', {type: 'bool'}],
      ['voice.presence', 'Divine presence', 'Narration band when a divine channel answers one of Wren\'s spells.', {type: 'bool'}],
      ['voice.sfx', 'Sound effects', 'Comic-style bursts (KRAK!, TINK!) over the struck figure.', {type: 'bool'}],
      ['voice.position', 'Card position', 'Where the speech cards stack.', {type: 'select', options: [['left', 'Bottom left'], ['right', 'Bottom right'], ['center', 'Bottom centre']]}],
      ['voice.maxCards', 'Cards at once', 'Older cards retire early beyond this.', {type: 'range', min: 1, max: 6, step: 1}],
      ['voice.pace', 'Reading time', 'How long each card stays up. 2× doubles it. Hover a card to hold it; click to dismiss.', {type: 'range', min: .5, max: 2.5, step: .25}],
    ]],
    ['Who speaks', [
      ['voice.doran', 'Doran', 'Field reactions and replies when you address him ("Doran, …").', {type: 'bool'}],
      ['voice.ambient', 'Doran\'s asides', 'His thinking-aloud lines while you travel and explore.', {type: 'bool'}],
      ['voice.sera', 'Sera', 'Her commentary and teasing.', {type: 'bool'}],
      ['voice.ember', 'Ember', 'Her questions, and her answers to Wren\'s divine spells.', {type: 'bool'}],
      ['voice.log', 'Copy to Messages', 'Also record every line in the Messages log.', {type: 'bool'}],
    ]],
  ];
  const groups = rows.map(([title, items]) => `<div class="pref-group"><h4>${E(title)}</h4>${items.map(([path, label, help, spec]) => prefControl(path, label, help, spec)).join('')}</div>`).join('');
  return `<fieldset class="pref-section" id="voice-options"><legend>Voices and sound cues</legend>
    <p class="notice">Who speaks and what they say comes from the host. These settings only change how it is shown.</p>
    <div class="actions">${button('Preview voices', 'voice-demo', 'primary')}${button('Reset voice defaults', 'reset-pref-group:voice', 'secondary')}</div>
    ${groups}</fieldset>`;
}
function linkOptions() {
  const rows = [
    ['link.heartbeatMs', 'Heartbeat', 'How often the connection box pings the host. Off: only "Ping now" measures.', {type: 'select', number: true, options: [[0, 'Off'], [2000, 'Every 2 s'], [5000, 'Every 5 s'], [10000, 'Every 10 s'], [30000, 'Every 30 s']]}],
    ['link.warnMs', 'Latency warning', 'At or above this round-trip time the latency turns amber.', {type: 'range', min: 25, max: 500, step: 25}],
    ['link.badMs', 'Latency alarm', 'At or above this it turns red.', {type: 'range', min: 100, max: 2000, step: 50}],
    ['link.clock24h', '24-hour clock', 'Off shows AM/PM.', {type: 'bool'}],
    ['link.seconds', 'Show seconds', 'Seconds on the host clock.', {type: 'bool'}],
    ['link.showLatency', 'Latency in the collapsed box', 'Keep the ms figure beside the clock.', {type: 'bool'}],
    ['link.showDrift', 'Clock drift', 'Host clock minus local clock, estimated at the midpoint of each ping.', {type: 'bool'}],
    ['link.sparkline', 'Latency graph', 'History graph with min, p50, p95, mean, jitter and lost pings in the expanded box.', {type: 'bool'}],
    ['link.historySize', 'Graph window', 'How many pings the graph and statistics cover.', {type: 'range', min: 10, max: 120, step: 5}],
  ];
  return `<fieldset class="pref-section" id="link-options"><legend>Connection & clock</legend>
    <p class="notice">The box in the top corner. Clock drift assumes a symmetric round trip, so it is accurate to about half the latency.</p>
    ${rows.map(([path, label, help, spec]) => prefControl(path, label, help, spec)).join('')}
    <div class="actions">${button('Reset connection defaults', 'reset-pref-group:link', 'secondary')}</div></fieldset>`;
}
// Two sample dolls on a small stage of their own. The director finds the
// first .combat-stage in #app, which on the Options screen is this one.
const DEMO_FIGHTERS = [
  {id: 'demo-a', name: 'Doran', identity: 'doran', hp: 10, position: [30, 10, 0]},
  {id: 'demo-b', name: 'Hollow Guard', role: 'guard', hp: 10, position: [70, 10, 0],
    equipment: [{presentation: {silhouette: 'sword'}}, {presentation: {silhouette: 'armor', material: 'chain'}}]},
];
function combatDemoStage() {
  return `<section class="illustrated-scene scene-battle battle-stage combat-stage demo-stage" data-stage-run="demo" aria-label="Combat animation demo">
    <div class="scene-moon"></div><div class="scene-mountains back"></div><div class="scene-road"></div>
    ${drawDoll(DEMO_FIGHTERS[0], 'battle-actor', 'combat', {style: 'left:22%;bottom:21px;', attrs: {'data-stage-actor': 'demo-a'}})}
    ${drawDoll(DEMO_FIGHTERS[1], 'opponent battle-actor', 'combat', {style: 'left:58%;bottom:21px;', attrs: {'data-stage-actor': 'demo-b'}})}
  </section>`;
}
function playCombatDemo() {
  // Every number is spelled out the way the host reports it: damage_parts
  // for the dice (a crit doubles the dice, not the modifier), heal evidence
  // for the heal, so the demo's roll math adds up exactly.
  const attack = (actor, target, outcome, damage, natural, extra = {}) => {
    const type = extra.type || 'slashing';
    const expression = extra.expression || '2d6+4';
    const parts = outcome === 'miss' ? null
      : [{label: 'weapon', expression, rolls: extra.rolls, critical: outcome === 'crit', total: damage}];
    return {actor, target, kind: 'attack', style: 'attack', outcome, damage,
      animation: {attack: 'melee_light'}, roll: {natural, bonus: 12, total: natural + 12, dc: 17, rolls: [natural], advantage: false, disadvantage: false},
      damageRolls: parts ? extra.rolls : null, expression, damageType: type,
      damageDetail: parts ? damageMath({parts, damageType: type}) : ''};
  };
  combatDirector.play([
    attack('demo-a', 'demo-b', 'hit', 11, 14, {rolls: [3, 4]}),
    attack('demo-b', 'demo-a', 'miss', null, 3),
    attack('demo-a', 'demo-b', 'crit', 23, 20, {rolls: [6, 5, 4, 4], type: 'radiant'}),
    attack('demo-b', 'demo-a', 'hit', 6, 16, {rolls: [2], expression: '1d8+4', type: 'fire'}),
    {actor: 'demo-a', target: 'demo-a', kind: 'heal', style: 'cast', outcome: null, healing: 6, animation: {cast: 'cast'},
      healDetail: healMath({expression: '1d4+5', rolls: [1], rolled: 6, adjustments: []})},
  ]);
}
function combatInspector(history = combatDirector.history) {
  const rows = history.slice().reverse().map(row => `<tr class="${row.inferred ? 'is-inferred' : ''}${row.missingFigure ? ' is-missing' : ''}">
    <td>${(row.at / 1000).toFixed(2)}s</td><td>${row.ms}ms</td><td>${E(row.actor || '—')}</td><td>${E(row.target || '—')}</td><td>${E(row.style)}</td>
    <td>${E(row.outcome || '—')}</td><td>${Number.isFinite(row.damage) ? `-${row.damage}` : Number.isFinite(row.healing) ? `+${row.healing}` : ''}</td>
    <td class="insp-detail">${E(row.detail || '')}${row.inferred ? ' <em>inferred from HP</em>' : ''}${row.missingFigure ? ' <em>no figure on stage</em>' : ''}</td></tr>`).join('');
  return `<section class="combat-inspector" data-combat-inspector aria-label="Beat inspector"><header><strong>Beat inspector</strong><small>${history.length} beats · newest first</small>
    <span>${button('Clear', 'combat-inspector-clear', 'secondary')}${button('Close', 'combat-inspector-close', 'secondary')}</span></header>
    <div class="insp-scroll"><table><thead><tr><th>t</th><th>dur</th><th>actor</th><th>target</th><th>beat</th><th>result</th><th>Δhp</th><th>roll math</th></tr></thead>
    <tbody>${rows || '<tr><td colspan="8">No beats yet. Take a combat action or play the demo.</td></tr>'}</tbody></table></div></section>`;
}
// Updated in place so a playing beat is never interrupted by a full render.
function refreshCombatInspector(history) {
  document.querySelectorAll('[data-combat-inspector]').forEach(node => {
    const holder = document.createElement('div'); holder.innerHTML = combatInspector(history);
    node.replaceWith(holder.firstElementChild);
  });
  document.querySelectorAll('[data-combat-inspector] [data-action]').forEach(node => node.onclick = () => {
    if (node.dataset.action === 'combat-inspector-clear') combatDirector.clearHistory();
    else { state.preferences.combat.inspector = false; savePreferences(); render(); }
  });
}
// ---- Stage targeting -------------------------------------------------------
// In an encounter the host only accepts the combatant whose turn (or
// reaction window) it is; outside one, the selected party member acts.
function actingActorId() {
  const step = encounterStepActor();
  return encounterActive() && step.startsWith('p') ? step : (actor().id || 'p0');
}
// Mirrors the host's attack payment check (tactical._attack_economy_problem):
// a spent turn is answered here, not by a rejected request.
function attackSpent(bonus = false) {
  const combat = state.view?.combat;
  if (!combat || combat.complete || !combat.current) return false;
  const e = combat.economy?.[combat.current];
  if (!e) return false;
  return bonus ? !e.bonus : !e.attacks && !e.action;
}
async function submitTarget(action, kind, rawValue, label) {
  state.actionPicker = null;
  const acting = party().find(row => row.id === actingActorId()) || actor();
  if (action === 'attack' && attackSpent(String(acting.identity || '').toLowerCase() === 'wren')) {
    state.note = 'Action already used this turn. End the turn to continue.';
    addMessage(state.note);
    render();
    return;
  }
  await work(async () => {
    const fields = {type: action, actor: actingActorId()};
    if (['inspect', 'inspect_object', 'search_object', 'open_object'].includes(action)) fields.object_id = rawValue;
    else if (action === 'decant') fields.item = rawValue;
    else if (action === 'move' && kind === 'destination') fields.destination = rawValue.includes(',') ? rawValue.split(',').map(Number) : rawValue;
    else if (['move_room', 'enter'].includes(action)) fields.destination = rawValue;
    else if (action === 'grand_cleave') fields.facing = rawValue;
    else fields.target = rawValue;
    if (action.startsWith('maneuver_')) Object.assign(fields,{type:'maneuver',maneuver:(state.view?.combat?.contextual_actions || []).find(row=>row.id===action)?.maneuver,mode:acting.loadout==='cleaver'?'cleaver':'dagger'});
    if (action === 'quick_toss') Object.assign(fields,{type:'maneuver',maneuver:'Quick Toss',mode:'dagger'});
    if (['dagger_attack','cleaver_attack'].includes(action)) Object.assign(fields,{type:'attack',mode:action==='cleaver_attack'?'cleaver':'dagger'});
    // Wren's only attack, Crown of Stars, is a bonus-action attack; the host
    // requires the flag (its own auto policy sends the same shape).
    if (action === 'attack' && String(actor().identity || '').toLowerCase() === 'wren') fields.bonus = true;
    result(await state.client.designTurn(state.runId, label, fields));
    await loadReadout(state.runId);
  });
}
const livingOpponents = () => (state.view?.opposition || []).filter(row => row?.id && row.alive !== false && Number(row.hp ?? 1) > 0);
const playerTurn = () => {
  const combat = state.view?.combat;
  return Boolean(combat && !combat.complete && String(combat.current || '').startsWith('p'));
};
function focusTarget(id) {
  state.focusTarget = id; render();
  const node = document.querySelector(`.combat-stage [data-stage-actor="${CSS.escape(id)}"]`);
  node?.focus({preventScroll: true});
}
function attackFocused() {
  const target = livingOpponents().find(row => row.id === state.focusTarget);
  if (!target || !playerTurn() || state.busy) return false;
  submitTarget('attack', 'target', target.id, `Attack ${target.name || target.id}`);
  return true;
}
function cycleTarget(step) {
  const rows = livingOpponents(); if (!rows.length) return;
  const i = rows.findIndex(row => row.id === state.focusTarget);
  focusTarget(rows[(i + step + rows.length) % rows.length].id);
}
// One handler for mouse, touch and keyboard (Enter/Space on a focused doll).
function activateFigure(id, {double = false} = {}) {
  const c = state.preferences.combat;
  const picker = state.actionPicker;
  if (picker) {
    const choice = actionTargets(picker.action).find(row => row.value === id);
    if (choice) { submitTarget(picker.action, choice.kind, choice.value, choice.label); return; }
  }
  if (party().some(row => row.id === id)) { state.selectedActor = id; render(); return; }
  const resident = Object.values(state.view?.room?.npcs || {}).find(row => String(row.id || row.npc_id) === id);
  if (resident && !encounterActive()) {
    const node = document.querySelector(`.illustrated-scene:not(.combat-stage) [data-resident="${CSS.escape(id)}"]`);
    if (node && !double) { node.dataset.hotspot = 'resident'; activateHotspot(node); return; }
    state.focusTarget = id;
    if (double) {
      const talkBtn = document.querySelector(`[data-action="talk:${CSS.escape(id)}"]`);
      if (talkBtn) { talkBtn.click(); return; }
    }
    render();
    return;
  }
  if (!livingOpponents().some(row => row.id === id)) {
    state.focusTarget = id;
    render();
    return;
  }
  const wasFocused = state.focusTarget === id;
  if (c.clickMode === 'attack' || (c.clickMode === 'double' && double)) { state.focusTarget = id; if (!attackFocused()) render(); return; }
  if (c.clickMode === 'focus' && wasFocused && double) { attackFocused(); return; }
  focusTarget(id);
}
const groundBoundStages = new WeakSet();
// On the formation (side-view) stage x is not a grid projection, so a click
// on the foes' half closes on the nearest foe and one on the party's half
// falls back, each capped to the movement left.
function formationStep(origin, fraction) {
  if (!Array.isArray(origin)) return null;
  const foes = foeRows().filter(row => Array.isArray(row.position));
  const nearest = foes.slice().sort((a, b) => gridDistance(origin, a.position) - gridDistance(origin, b.position))[0];
  if (!nearest) return null;
  const toward = Math.sign(nearest.position[0] - origin[0]) || 1;
  if (fraction >= 0.5) return [Math.max(0, Math.min(120, nearest.position[0] - 5 * toward)), nearest.position[1], origin[2]];
  return [Math.max(0, Math.min(120, origin[0] - toward * Number(currentEconomy().movement || 0))), origin[1], origin[2]];
}
function bindStageTargeting() {
  const liveStage = document.querySelector('#app .combat-stage:not(.demo-stage)');
  if (liveStage && !groundBoundStages.has(liveStage)) {
    groundBoundStages.add(liveStage);
    liveStage.addEventListener('click', event => {
      if (!styleAllows(style(), 'mouse') || !myTacticalTurn()) return;
      if (event.target.closest('[data-stage-actor], button, a, [role="button"], .ff-order, .combat-radial, .combat-inspector')) return;
      if (state.combatRadial) { state.combatRadial = null; render(); return; }
      const who = currentCombatant();
      const origin = combatPosition(who.id);
      const rect = liveStage.getBoundingClientRect();
      if (!rect.width) return;
      const fraction = (event.clientX - rect.left) / rect.width;
      const destination = liveStage.classList.contains('flight-stage') ? flightDestination(origin, fraction, (event.clientY - rect.top) / rect.height)
        : liveStage.classList.contains('ff-stage') ? formationStep(origin, fraction) : groundDestination(origin, fraction);
      if (destination) stepTo(destination, 'Walk');
    });
  }
  document.querySelectorAll('[data-radial-item]').forEach(node => node.onclick = event => { event.stopPropagation(); runRadialItem(Number(node.dataset.radialItem)); });
  document.querySelectorAll('.illustrated-scene:not(.demo-stage) [data-stage-actor], .combat-stage:not(.demo-stage) [data-stage-actor]').forEach(node => {
    node.onclick = () => activateFigure(node.dataset.stageActor);
    node.ondblclick = event => { event.preventDefault(); activateFigure(node.dataset.stageActor, {double: true}); };
    node.onkeydown = event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activateFigure(node.dataset.stageActor, {double: event.key === 'Enter' && event.shiftKey}); } };
  });
}
// ---- Combat input router ------------------------------------------------------
// Keys and clicks become the same engine actions the command dock sends
// (web/combat-input.js holds the pure mapping). Options > Combat controls
// picks the style: hybrid (everything), turn_based, direct_wasd, mouse_click.
const style = () => combatStyle(state.preferences.combat.style);
function myTacticalTurn() {
  return tacticalActive() && playerTurn() && !state.busy && playerControlled(state.view?.combat?.current)
    && !(state.view?.combat?.pending || []).length;
}
function currentCombatant() {
  const id = state.view?.combat?.current;
  return party().find(row => row.id === id) || {};
}
function currentEconomy() {
  const c = state.view?.combat || {};
  return c.economy?.[c.current] || {};
}
const combatPosition = id => state.view?.combat?.positions?.[id] || [...party(), ...(state.view?.opposition || [])].find(row => row.id === id)?.position || null;
function foeRows() {
  return livingOpponents().map(row => ({...row, position: combatPosition(row.id)}));
}
// A step that leaves a foe's reach is announced first: the threatening foes
// get a red ring, and the same step again within THREAT_CONFIRM_MS commits.
const THREAT_CONFIRM_MS = 2600;
async function stepTo(destination, label = 'Move') {
  if (!destination || !myTacticalTurn()) return false;
  const who = currentCombatant();
  const origin = combatPosition(who.id);
  const others = [...party(), ...livingOpponents()].filter(row => row.id !== who.id && row.alive !== false && Number(row.hp ?? 1) > 0)
    .map(row => combatPosition(row.id)).filter(Boolean);
  const capped = avoidOccupied(origin, withinMovement(origin, destination, currentEconomy().movement), others);
  if (!capped) { state.note = 'No movement left this turn.'; addMessage(state.note); render(); return false; }
  const threats = state.preferences.combat.threatWarn === false ? [] : threatenedBy(origin, capped, foeRows(), {disengaged: (who.statuses || []).includes('DISENGAGED')});
  const warned = state.threatWarning;
  if (threats.length && !(warned && String(warned.destination) === String(capped) && performance.now() - warned.at < THREAT_CONFIRM_MS)) {
    const stamp = performance.now();
    state.threatWarning = {destination: capped, foes: threats, at: stamp};
    const names = threats.map(id => livingOpponents().find(row => row.id === id)?.name || id).join(', ');
    state.note = `Leaving ${names}'s reach provokes an opportunity attack. Repeat the move to commit, or Disengage first.`;
    addMessage(state.note);
    render();
    setTimeout(() => { if (state.threatWarning?.at === stamp) { state.threatWarning = null; render(); } }, THREAT_CONFIRM_MS);
    return false;
  }
  state.threatWarning = null;
  await work(async () => {
    result(await state.client.designTurn(state.runId, `${label} to ${capped.join(',')}`, {type: 'move', actor: who.id, destination: capped}));
    await loadReadout(state.runId);
  });
  return true;
}
async function engineSubmit(type, target = null, label = '') {
  if (!myTacticalTurn()) return false;
  const who = currentCombatant();
  if (target) { submitTarget(type, 'target', target, label || `${type} ${target}`); return true; }
  const fields = {type, actor: who.id};
  await work(async () => {
    result(await state.client.designTurn(state.runId, label || type, fields));
    await loadReadout(state.runId);
  });
  return true;
}
// The one front door for "the player chose action `id`", from any entry
// point (a [data-engine-action] click, a digit hotkey, or a future combat/
// turn-flow controller): decide whether it needs a target picker or can
// submit immediately, and do it. Exploration actions have no tactical turn
// economy, so this submits directly via designTurn rather than through
// engineSubmit (which requires myTacticalTurn() and is combat-only).
async function dispatchAction(id, {label = ''} = {}) {
  state.engineHelpOpen = false;
  if (id === 'cast') {
    await work(async () => {
      const reply = result(await state.client.request('spell_catalog', {run_id: state.runId}));
      const spells = reply.result?.spells || [];
      state.spellPicker = {spells, id: spells.find(row => row.display_name === 'Magic Missile')?.id || spells[0]?.id,
        actor: encounterStepActor() || actor().id};
    });
    return;
  }
  if (id === 'idle_tick') {
    if (!floorOneWorld()) { selectGameplayScreen('room'); render(); return; }
    await work(async () => {
      result(await state.client.idleTick(state.runId, 1));
      selectGameplayScreen('journey');
      state.note = state.receipt?.pause ? `Idle paused: ${state.receipt.pause.message}` : 'Idle advanced one safe step.';
      render();
    });
    return;
  }
  if (id === 'resolve_reaction' || id === 'decline_reaction') {
    const window = (state.view?.combat?.pending || []).find(row => String(row.reactor || '').startsWith('p')) || state.view?.combat?.pending?.[0];
    if (!window) { fail('No reaction window is open.'); return; }
    const defense = (window.options || [])[0];
    const fields = id === 'resolve_reaction' && defense
      ? {type: 'reaction', actor: window.reactor, defense}
      : {type: 'decline_reaction', actor: window.reactor};
    await work(async () => {
      result(await state.client.designAction(state.runId, fields));
      await loadReadout(state.runId);
      state.note = fields.type === 'reaction' ? `${defense} reaction submitted to the host.` : 'Reaction declined through the host.';
      addMessage(state.note);
    });
    return;
  }
  if (id === 'attack' && state.preferences.combat.attackUsesFocus && attackFocused()) return;
  if (['inspect', 'inspect_object', 'search_object', 'open_object', 'take', 'talk', 'attack', 'move', 'move_room', 'enter',
    ...CONTEXTUAL_TARGETED, 'decant'].includes(id) || id.startsWith('maneuver_')) {
    state.actionPicker = {action: id, label: label || id};
    render();
    return;
  }
  await work(async () => {
    const reply = await state.client.designTurn(state.runId, label || id, {type: id, actor: actingActorId()});
    result(reply);
    state.note = `${label || id} submitted to the engine.`;
    addMessage(state.note);
  });
}
function clickEngineButton(id) {
  const node = [...document.querySelectorAll(`[data-engine-action="${CSS.escape(id)}"]`)].find(button => !button.disabled);
  if (node) { node.click(); return true; }
  return false;
}
// Hotbar slot N: the contextual action combat-input.hotbarSlots binds it to.
function fireHotbar(slot) {
  const who = currentCombatant();
  const rows = state.view?.combat?.contextual_actions || [];
  const bound = hotbarSlots(who.identity, rows).find(row => row.slot === slot);
  if (!bound?.id) return false;
  if (!bound.available) { state.note = `${bound.label}: ${bound.reason || 'not available now.'}`; addMessage(state.note); render(); return true; }
  if (bound.id === 'cast' || bound.id === 'move') return clickEngineButton(bound.id);
  if (bound.targets?.length) {
    const focus = bound.targets.includes(state.focusTarget) ? state.focusTarget : null;
    const origin = combatPosition(who.id);
    const target = focus || bound.targets.slice().sort((a, b) => gridDistance(origin, combatPosition(a)) - gridDistance(origin, combatPosition(b)))[0];
    submitTarget(bound.id, 'target', target, `${bound.label} → ${livingOpponents().find(row => row.id === target)?.name || target}`);
    return true;
  }
  engineSubmit(bound.id, null, bound.label);
  return true;
}
function spaceAction() {
  const who = currentCombatant();
  const wren = String(who.identity || '').toLowerCase() === 'wren';
  const intent = spaceIntent({economy: currentEconomy(), focus: state.focusTarget, foes: foeRows(),
    position: combatPosition(who.id), reach: wren ? 60 : String(who.identity || '').toLowerCase() === 'doran' ? 70 : 5, wren});
  if (intent.kind === 'attack') {
    const name = livingOpponents().find(row => row.id === intent.target)?.name || intent.target;
    state.focusTarget = intent.target;
    submitTarget('attack', 'target', intent.target, `Attack ${name}`);
    return true;
  }
  return clickEngineButton('end_turn') || (engineSubmit('end_turn', null, 'End turn'), true);
}
// Hotkeys only while the battle stage is on screen and no text field has focus.
document.addEventListener('keydown', event => {
  if (!state.preferences.combat.hotkeys || state.phase !== 'ready' || !document.querySelector('#app .combat-stage:not(.demo-stage)')) return;
  if (isTypingTarget(event.target) || isTypingTarget(document.activeElement) || event.ctrlKey || event.metaKey || event.altKey) return;
  if (document.querySelector('dialog[open]') || state.systemMenuOpen || state.bookbagOpen) return;
  const key = event.key;
  const lower = String(key).toLowerCase();
  const direct = styleAllows(style(), 'keys');
  const handled = () => { event.preventDefault(); event.stopPropagation(); };
  // Tab and Space keep their usual jobs on a focused control (keyboard
  // navigation, pressing a button); they drive combat from the page or stage.
  const focus = document.activeElement;
  const onControl = Boolean(focus && focus !== document.body && !focus.closest?.('.combat-stage')
    && focus.matches?.('button,a,summary,[role="button"],[tabindex]'));
  if (key === ']' || (key === 'Tab' && !onControl && (direct || focus?.closest?.('.combat-stage')))) { handled(); cycleTarget(event.shiftKey ? -1 : 1); return; }
  if (key === '[') { handled(); cycleTarget(-1); return; }
  if (direct && lower === 'q') { handled(); cycleTarget(event.shiftKey ? -1 : 1); return; }
  if (key === 'Escape' && (state.focusTarget || state.actionPicker || state.combatRadial || state.threatWarning)) {
    handled(); state.focusTarget = null; state.actionPicker = null; state.combatRadial = null; state.threatWarning = null; render(); return;
  }
  if (direct && tacticalActive()) {
    const who = currentCombatant();
    const destination = ['w', 'a', 's', 'd', 'arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(lower) && !event.shiftKey
      ? stepDestination(combatPosition(who.id), lower) : null;
    if (destination) { handled(); if (myTacticalTurn()) stepTo(destination, 'Step'); return; }
    if ((key === ' ' || event.code === 'Space') && !onControl) { handled(); if (myTacticalTurn()) spaceAction(); return; }
    if (/^[1-4]$/.test(key)) { handled(); if (myTacticalTurn()) fireHotbar(Number(key)); return; }
  }
  if (styleAllows(style(), 'legacy_keys') && lower === 'a') { if (attackFocused()) handled(); return; }
  if (lower === 'e') { const end = [...document.querySelectorAll('[data-engine-action="end_turn"]')].find(node => !node.disabled); if (end) { handled(); end.click(); } }
});
// ---- Replay -----------------------------------------------------------------
// Run titles come from what the run is (lead, scenario, progress), not its id,
// so generated ids never need to be meaningful and can be anything unique.
function runLaunch(run = {}) {
  const ctx = run.context || {};
  return {
    lead: ctx.run_launch?.lead_selector || (ctx.party_selectors || [])[0] || run.party?.[0]?.name || '',
    party: Array.isArray(ctx.party_selectors) && ctx.party_selectors.length ? ctx.party_selectors : (run.party || []).map(row => row?.name).filter(Boolean),
    scenario: ctx.scenario || '', mode: String(ctx.host_mode || run.mode || '').toUpperCase(), seed: run.seed ?? '',
  };
}
function selectorName(selector = '') {
  const text = String(selector);
  if (text.startsWith('custom:')) return text.slice(7).replace(/^web-/, '').replace(/-[a-z0-9]{6,}$/, '').replace(/-/g, ' ') || 'Custom lead';
  return text || 'Unknown lead';
}
function runTitle(run, id) {
  if (typeof run !== 'object' || !run) return id;
  const launch = runLaunch(run);
  const lead = selectorName(launch.lead).replace(/\b\w/g, ch => ch.toUpperCase());
  return `${lead} · ${scenarioTitle(launch.scenario) || MODE_LABELS[launch.mode] || 'Run'}`;
}
function runSubtitle(run, id) {
  if (typeof run !== 'object' || !run) return 'Saved run';
  const launch = runLaunch(run);
  const status = run.lifecycle?.status === 'replaced' ? 'Replaced by a new game'
    : run.lifecycle?.status === 'ended' || run.finished ? `Finished${run.winner ? ` · ${run.winner} won` : ''}`
    : `Round ${run.round_number ?? 0}`;
  const metrics = run.history?.metrics || {};
  const recorded = [metrics.rooms_cleared != null ? `${metrics.rooms_cleared} rooms cleared` : null,
    metrics.floors_reached != null ? `floor ${metrics.floors_reached}` : null,
    metrics.gameplay_minutes != null ? `${metrics.gameplay_minutes} game min` : null].filter(Boolean).join(' · ');
  return `${status} · seed ${launch.seed || '—'} · ${id}${recorded ? ' · ' + recorded : ''}`;
}
// Start a new run from a finished or saved one: same party, scenario and
// mode, with a fresh random seed ("New seed") or the original ("Replay seed").
// A Seed override, when set, still wins over both.
async function playAgain(runId, sameSeed) {
  const attempt = async () => {
    const reply = await state.client.request('inspect_run', {run_id: runId});
    if (!reply.ok) throw Error(reply.error?.message || `Could not read ${runId}.`);
    const launch = runLaunch(reply.result?.run || {});
    if (!launch.party.length) throw Error(`${runId} does not record its party, so it cannot be restarted automatically.`);
    const mode = ['FORGE', 'SANDBOX', 'DESIGN'].includes(launch.mode) ? launch.mode : 'SANDBOX';
    const override = String(state.preferences.scenarioSeed || '').trim();
    const seed = override || (sameSeed && launch.seed !== '' ? String(launch.seed) : randomSeed());
    state.lastRunSeed = seed;
    result(await state.client.boot(mode));
    const newId = `${selectorName(launch.lead).toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 24) || 'run'}-${Date.now().toString(36)}`;
    state.startingRunId = newId; state.afterRunStart = null;
    result(await state.client.startRun({
      run_id: newId, mode, seed, scenario: launch.scenario || scenarioFor(mode),
      party: launch.party, lead_selector: launch.lead || launch.party[0], opposition: ['Townsperson'],
      ...(mode === 'FORGE' ? {module_id: 'reliquary-template'} : {}),
    }));
    state.runId = newId; state.terminal = null; state.focusTarget = null;
    await initializeRunScene(mode, newId);
    await loadReadout(newId);
    announceRunStart(sameSeed ? `Replaying ${runId}.` : `New run from ${runId}.`);
  };
  await work(() => withSandboxRecovery(attempt), sameSeed ? 'Replaying the same seed' : 'Starting again with a new seed');
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
function journal() {
  const events = state.view?.recent_receipts || [];
  const route = (state.view?.expedition?.log || []).slice().reverse();
  const routeLog = route.length ? card('Expedition log', route.map(row => `<div class="log-item">${E(nodeGlyph(row.type))} ${E(row.type)} · room ${E(row.room)} · ${E(row.mode)}</div>`).join('')) : '';
  return `${atmosphere('journal', 'Journey journal', 'Only host-reported discoveries and public receipts enter this record.')}${card('Recent events', events.length ? events.map(e => `<div class="log-item">${E(e.message || e.outcome || e.type || JSON.stringify(e))}</div>`).join('') : '<p class="notice">No resolved events yet.</p>')}${routeLog}<div class="actions">${button('View Statistics', 'menu:statistics', 'secondary')}</div>`;
}
function statisticsModeLabel() { return state.statisticsMode === 'SANDBOX' ? 'Simulation Mode' : 'Story Mode'; }
function metricRows(metrics = {}) {
  const groups = [
    ['Progress', [['Rooms entered', 'rooms_entered'], ['Rooms cleared', 'rooms_cleared'], ['Floors reached', 'floors_reached'], ['Floors completed', 'floors_completed']]],
    ['Combat', [['Encounters', 'combat_encounters'], ['Rounds', 'combat_rounds'], ['Actions', 'actions_resolved']]],
    ['Currency and time', [['Gold earned', 'gold_earned'], ['Gold spent', 'gold_spent'], ['Gold lost', 'gold_lost'], ['Gold retained', 'gold_retained'], ['Platinum earned', 'platinum_earned'], ['Gameplay minutes', 'gameplay_minutes'], ['Active seconds', 'active_session_seconds']]],
  ];
  return groups.map(([title, rows]) => `<div class="statistics-run-summary"><strong>${E(title)}</strong>${rows.map(([label, key]) => `<small>${E(label)}: ${E(metrics[key] ?? 'Unknown')}</small>`).join('')}</div>`).join('');
}
function compactRunSummary(entry) {
  const summary = entry?.summary || entry || {};
  const party = Array.isArray(summary.party) ? summary.party.map(selectorName).join(', ') : 'Unknown party';
  const status = entry?.status === 'replaced' ? 'Replaced by a new game' : entry?.status === 'ended' ? `Ended${entry.reason ? ` · ${entry.reason.replaceAll('_', ' ')}` : ''}` : 'Saved';
  return `<div class="statistics-run-summary"><strong>${E(party)}</strong><small>${E(statisticsModeLabel())} · ${E(summary.scenario || 'Run')} · ${E(status)} · seed ${E(summary.seed || '—')}</small>${entry?.ended_at ? `<small>Ended ${E(entry.ended_at)}</small>` : ''}${entry?.pruned ? '<small>Full save rotated out; summary retained.</small>' : ''}</div>`;
}
function selectedStatisticsDetail() {
  const entry = state.statistics?.selected_run;
  const detail = state.statisticsDetail;
  if (!entry && !detail) return '';
  if (!detail) return card('Run detail', `${compactRunSummary(entry)}${metricRows(entry.metrics)}`);
  const summary = detail.summary || {};
  const view = detail.public_view || {};
  const player = view.player || view.party?.[0] || {};
  return card('Selected save', `<div class="statistics-run-summary"><strong>${E(player.name || summary.party?.[0] || summary.run_id || 'Saved run')}</strong><small>${E(summary.scenario || 'Run')} · seed ${E(summary.seed || '—')} · ${E(summary.round_number ?? 0)} rounds</small><small>Read-only save data; the active run was not changed.</small></div>${player.hp !== undefined ? `<div class="stats"><div><strong>${E(player.hp)}/${E(player.max_hp ?? '—')}</strong><small>Health</small></div><div><strong>${E(player.armor_class ?? player.ac ?? '—')}</strong><small>Armor</small></div><div><strong>${E(view.room?.name || view.room?.title || '—')}</strong><small>Current place</small></div></div>` : ''}${metricRows(entry?.metrics)}`);
}
function statisticsHistoryPanel() {
  const data = state.statistics;
  if (state.statisticsView === 'last') {
    return card('Last Run', data?.last_run ? `${compactRunSummary(data.last_run)}${metricRows(data.last_run.metrics)}` : '<p class="notice">No ended run is recorded for this mode yet.</p>');
  }
  if (state.statisticsView === 'list') {
    const rows = data?.saves || [];
    return card('Select a Save', rows.length ? `<div class="statistics-save-list">${rows.map(entry => button(`${entry.summary?.run_id || entry.run_id} · Read data`, `statistics-save:${entry.run_id}`, 'secondary')).join('')}</div>` : '<p class="notice">No retained saves are available for this mode.</p>');
  }
  if (state.statisticsView === 'all') {
    const rows = data?.all_runs || [];
    return card('All run summaries', rows.length ? `<div class="statistics-save-list">${rows.map(entry => button(`${entry.summary?.party?.map(selectorName).join(', ') || entry.run_id} · ${entry.metrics?.outcome || entry.status || 'Saved'} · ${entry.run_id}`, `statistics-save:${entry.run_id}`, 'secondary')).join('')}</div>` : '<p class="notice">No run summaries are recorded for this mode.</p>');
  }
  return '';
}
function statisticsScreen() {
  const modeLabel = statisticsModeLabel();
  const historyPanel = `${card('Run history', `<div class="actions statistics-options">${button('Last Run', 'load-statistics-last', state.statisticsView === 'last' ? 'primary' : 'secondary')}${button('Select a Save', 'load-statistics-list', state.statisticsView === 'list' ? 'primary' : 'secondary')}${button('All Runs', 'load-statistics-all', state.statisticsView === 'all' ? 'primary' : 'secondary')}</div>`)}${statisticsHistoryPanel()}${selectedStatisticsDetail()}`;
  const accounts = state.statistics?.lifetime_accounts || [];
  const lifetimePanel = accounts.length ? card('Lifetime settled totals', accounts.map(lifetime => `<div class="statistics-run-summary"><strong>${E(lifetime.identity)}</strong><small>Rank ${E(lifetime.rank)} · Platinum ${E(lifetime.platinum)} · Loop tier ${E(lifetime.loop_tier)} · ${E(lifetime.settled_runs)} settled runs</small></div>${metricRows(lifetime.tracking)}`).join('')) : '';
  return `<div class="mode-menu">${breadcrumb('Main Menu', modeLabel, 'Statistics')}${atmosphere('journal', 'Statistics', `${modeLabel} save history and account progression.`)}${card('Statistics', `${historyPanel}${lifetimePanel}${card('Reliquary progression', progressionPanel())}<div class="mode-menu-footer"><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
}
function scenarioEditor() {
  const rows = state.scenarios;
  const chosen = state.preferences.scenario || MODE_SCENARIOS.SANDBOX;
  const seed = state.preferences.scenarioSeed || '';
  const body = rows === null
    ? `<p class="notice">Loading the host's scenario catalog…</p>`
    : !rows.length
      ? `<p class="notice">The host reported no Simulation scenarios.</p><div class="actions">${button('Retry', 'load-scenarios', 'secondary')}</div>`
      : `<div class="scenario-grid">${rows.map(row => `<article class="scenario-card${row.scenario === chosen ? ' selected' : ''}"><div class="scenario-card-header"><p class="eyebrow">${row.scenario === chosen ? 'Selected' : 'Available'}</p>${row.scenario === chosen ? '<span class="status-pill active">In Use</span>' : ''}</div><h3>${E(row.title)}</h3><p>${E(row.blurb)}</p><div class="actions">${row.scenario === chosen ? '<span class="scenario-status">Current Simulation scenario</span>' : button(`Use ${row.title}`, `scenario:${row.scenario}`, 'primary')}</div></article>`).join('')}</div>
      <div class="scenario-seed-section"><label class="option-row"><span><strong>Seed override</strong><small>Blank gives every new run a fresh random world. Type a seed (any text, or one shown when a run starts) to replay that exact world.</small></span><span class="seed-field"><input type="text" data-scenario-seed value="${E(seed)}" placeholder="(random each run)" aria-label="Simulation seed override">${button('Randomize', 'seed-override-random', 'secondary')}${button('Clear', 'seed-override-clear', 'secondary')}</span></label></div>`;
  return `<div class="mode-menu">${breadcrumb('Main Menu', 'Simulation Mode', 'Edit Scenario')}${atmosphere('gateway', 'Edit Scenario', 'Pick which authored surface a new Simulation run opens on. Scenario content stays a read-only engine input; only the choice is yours.')}${card('Scenario', `${body}<p class="notice">This applies to the next Simulation run you start. A run already in progress keeps the scenario it was created with.</p><div class="mode-menu-footer"><div class="footer-left">${button('Reset to defaults', 'reset-scenario', 'secondary')}</div><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
}
function cheatsPanel() {
  const debug = state.debugReadout;
  return `<div class="mode-menu">${breadcrumb('Main Menu', 'Simulation Mode', 'Cheats')}${atmosphere('gateway', 'Cheats', 'Private sandbox debug state — rehearsal only, never canon.')}${storyDebugPanel()}${card('Cheats', `<p class="notice">Reveals state normally hidden from the public view: exact HP pools, hidden checks, undiscovered content, and engine internals for the current Simulation run.</p>${state.runId ? `<div class="actions cheats-actions">${button('Reveal debug state', 'load-debug-state', 'primary')}</div>${debug ? `<div class="code-viewer"><pre>${E(JSON.stringify(debug, null, 2))}</pre></div>` : ''}` : '<p class="notice">Start or resume a Simulation run first, then return here.</p>'}<div class="mode-menu-footer"><div class="footer-right">${button('Back', 'back', 'secondary')}</div></div>`, 'mode-menu-card')}</div>`;
}
const GAMBIT_WHEN = [
  ['always', 'Always'], ['self_hp_below', 'Own HP below %'], ['ally_hp_below', 'Ally HP below %'],
  ['enemy_hp_below', 'Target HP below %'], ['enemy_count_gte', 'Enemies at least'], ['enemy_adjacent', 'Enemy adjacent'],
  // Forecast conditions are judged on the action this line would take.
  ['hit_chance_gte', 'Hit chance at least %'], ['kill_chance_gte', 'Kill chance at least %'],
  ['expected_damage_gte', 'Expected damage at least'], ['spell_ready', 'Spell ready (id)'],
  ['self_concentrating', 'Concentrating'],
];
// Conditions that take no value, and the one that takes a spell id.
const GAMBIT_FLAGS = ['always', 'enemy_adjacent', 'self_concentrating'];
const GAMBIT_TEXT = ['spell_ready'];
const GAMBIT_THEN = [['attack', 'Attack'], ['plan_damage', 'Best damage (planner)'], ['plan_kill', 'Finish a foe (planner)'],
  ['plan_heal', 'Best heal (planner)'], ['dodge', 'Defend'], ['second_wind', 'Second Wind'], ['unearthly_recovery', 'Unearthly Recovery'], ['end_turn', 'Hold']];
const GAMBIT_TARGETS = [['nearest_enemy', 'Nearest enemy'], ['lowest_hp_enemy', 'Weakest enemy'], ['highest_hp_enemy', 'Strongest enemy'], ['adjacent_enemy', 'Adjacent enemy'],
  ['killable_enemy', 'Killable enemy'], ['likeliest_hit_enemy', 'Easiest to hit'], ['most_damage_enemy', 'Takes most damage'], ['self', 'Self']];
function gambitRowsFor(id) {
  if (state.gambitDraft?.[id]) return state.gambitDraft[id];
  return (state.view?.auto?.macros?.[id] || []).map(entry => {
    const [key, value] = Object.entries(entry.when || {}).find(([k]) => k !== 'target') || ['always', ''];
    const then = entry.then?.type === 'plan' ? `plan_${entry.then.goal}` : entry.then?.type || 'attack';
    return {when: key, value: value === true ? '' : value, then, target: entry.then?.target || 'nearest_enemy'};
  });
}
// Draft rows -> the engine's data-only Macro vocabulary (hollowstar/policies.py).
function gambitMacros(rows) {
  return rows.map((row, index) => {
    const when = {};
    if (GAMBIT_FLAGS.includes(row.when)) { if (row.when !== 'always') when[row.when] = true; }
    else if (GAMBIT_TEXT.includes(row.when)) when[row.when] = String(row.value || '').trim();
    else when[row.when] = Number(row.value || 0);
    const planned = String(row.then).startsWith('plan_');
    const then = planned ? {type: 'plan', goal: row.then.slice(5)} : {type: row.then};
    if (!planned && !['second_wind', 'unearthly_recovery', 'end_turn', 'dodge'].includes(row.then)) then.target = row.target;
    return {id: `ui-${index + 1}`, priority: (index + 1) * 10, when, then};
  });
}
function gambitEditor() {
  const members = party();
  if (!state.runId || !members.length) return '';
  const id = state.gambitActor && members.some(m => m.id === state.gambitActor) ? state.gambitActor : members[0].id;
  const rows = gambitRowsFor(id);
  const opt = (list, chosen) => list.map(([value, label]) => `<option value="${E(value)}"${String(value) === String(chosen) ? ' selected' : ''}>${E(label)}</option>`).join('');
  const body = rows.map((row, index) => `<div class="gambit-row" data-gambit-row="${index}"><span class="gambit-priority">${index + 1}</span><select data-gambit-field="when" aria-label="Condition">${opt(GAMBIT_WHEN, row.when)}</select>${GAMBIT_TEXT.includes(row.when) ? `<input data-gambit-field="value" type="text" value="${E(row.value ?? '')}" placeholder="Fireball@5e" aria-label="Spell id">` : `<input data-gambit-field="value" type="number" min="0" max="${row.when === 'expected_damage_gte' ? 1000 : 100}" value="${E(row.value ?? '')}" aria-label="Condition value"${GAMBIT_FLAGS.includes(row.when) ? ' hidden' : ''}>`}<select data-gambit-field="then" aria-label="Action">${opt(GAMBIT_THEN, row.then)}</select><select data-gambit-field="target" aria-label="Target">${opt(GAMBIT_TARGETS, row.target)}</select><button type="button" class="action secondary" data-gambit-remove="${index}" aria-label="Remove gambit ${index + 1}">✕</button></div>`).join('');
  return card('Gambits', `<div class="gambit-tabs">${members.map(m => `<button type="button" class="action ${m.id === id ? 'primary' : 'secondary'}" data-gambit-actor="${E(m.id)}">${E(m.name || m.id)}</button>`).join('')}</div>
    <p class="notice">Checked top to bottom on every automatic turn: Auto in battle, Auto nodes and AFK expeditions. The first legal line acts; if none match, the default tactics play.</p>
    <div class="gambit-list" data-gambit-list="${E(id)}">${body || '<p class="notice">No gambits yet. Default tactics apply.</p>'}</div>
    <div class="actions">${button('Add gambit', 'gambit-add', 'secondary')}${button('Save gambits', 'gambit-save', 'primary')}</div>`, 'gambit-card');
}
function formationPanel() {
  const formation = state.view?.combat?.formation;
  const members = party();
  const rowOf = member => formation?.[member.id]?.row || (member.identity === 'wren' ? 'back' : 'front');
  const column = row => members.filter(m => rowOf(m) === row).map(m => `<li>${E(m.name || m.id)}</li>`).join('') || '<li class="notice">Empty</li>';
  return card('Formation', `<div class="formation-grid"><div><p class="label">Back row</p><ul>${column('back')}</ul></div><div><p class="label">Front row</p><ul>${column('front')}</ul></div></div><p class="notice">The engine sets rows from reach: casters and long-reach fighters stand in the back row.</p>`);
}
function partyScreen() {
  const lead = actor();
  return `${atmosphere('roster', 'The party', 'Who fights, where they stand, and how they act when you are not steering.')}${card('Roster', `<div class="roster-showcase">${characterFigure(lead, 'featured', 'combat')}<div>${party().map(actorCard).join('') || 'No public party reported.'}</div></div>`)}${formationPanel()}${gambitEditor()}${championAbilities()}`;
}
function atlas() {
  const xp = state.view?.expedition;
  if (!xp?.active) {
    return `${atmosphere('map', 'The descent', 'Known places glow at the edge of a larger unknown Reliquary.')}${bounded('Atlas', state.runId ? 'Chart a route in Encounters to begin mapping the descent.' : 'Start or resume a run to begin charting the descent.')}`;
  }
  const floors = Object.keys(xp.maps || {}).sort((a, b) => Number(a) - Number(b));
  const visited = (xp.log || []).length;
  return `${atmosphere('map', 'The descent', `${visited} node(s) walked across ${floors.length} charted floor(s).`)}${floors.map(key => card(`Floor ${key}`, `<div class="xp-map-wrap is-atlas">${routeMap(xp.maps[key], {compact: true, E})}</div>`)).join('')}<div class="actions">${button('Open Encounters', 'tab:battle', 'primary')}</div>`;
}
function gameplay() {
  const content = {journey, room, battle, equipment, roster: partyScreen, residents, journal, map: atlas, library, options};
  const screen = content[state.selected];
  return screen ? screen() : bounded('Unknown screen', `No screen is registered for "${state.selected}".`);
}
function shellAtmosphereKind() {
  // Map the current gameplay screen to the atmosphere visual kind so the
  // header adapts when switching tabs. Screens that already render their own
  // atmosphere inside gameplay() (equipment, roster, residents, journal, map,
  // library, options) still get the shell-level one for the unified capsule;
  // their inner atmosphere is then a thematic sub-header inside the card.
  const kindMap = {journey: 'gateway', room: 'room', battle: 'battle', equipment: 'equipment', roster: 'roster', residents: 'residents', journal: 'journal', map: 'map', library: 'library', options: 'options'};
  return kindMap[state.selected] || 'gateway';
}
function shellAtmosphereTitle() {
  const roomName = state.view?.room?.name || state.view?.room?.title;
  if (state.selected === 'room' && roomName) return roomName;
  return gameplayLabels[state.selected] || 'Reliquary';
}
function shellAtmosphereSubtitle() {
  const subs = {
    journey: 'Where you’re going: the route ahead, who’s on it, and the way down.',
    room: 'Where you are: this room’s walls, law, and terrain — nothing beyond it.',
    battle: 'Tactical clarity first; dramatic lighting is merely traditional.',
    equipment: 'A clear armory view of every host-reported item, affix, and visible property.',
    roster: 'Selectable adventurers with readable silhouettes, health, armor, status, and equipment roles.',
    residents: 'Pretty social portraits show who is speaking; ordinary scene figures keep the lived-in town readable.',
    journal: 'Only witnessed facts enter the record. Rumour may wait outside.',
    map: 'Known places glow at the edge of a larger unknown Reliquary.',
    library: 'The catalogue remembers what the room would prefer you forget.',
    options: 'Tune the interface; leave the underlying reality gloriously alone.',
  };
  return subs[state.selected] || 'Public game state from the host.';
}
// The gameplay header is one compact strip: where you are on the left, the
// screen's flavour line on the right, and the session tools at the far edge.
// It replaces the old stacked breadcrumb + hero atmosphere + label/metadata
// rows, so the play surface below can take every remaining pixel.
function playHeader(screenLabel) {
  const mode = state.view?.mode;
  const modeLabel = MODE_LABELS[mode] || 'Game';
  const kind = shellAtmosphereKind();
  const trail = breadcrumb({label: 'Main Menu', phase: 'title'}, {label: modeLabel, phase: mode === 'FORGE' ? 'menu-story' : 'menu-simulation'}, screenLabel);
  const facts = [E(state.transport), E(state.runId || 'No run'), state.refreshed ? `refreshed ${E(state.refreshed.toLocaleTimeString())}` : 'not refreshed'];
  const metadata = `<p class="shell-metadata">${modeBadge(mode)}${facts.map(fact => `<span>${fact}</span>`).join('')}</p>`;
  const tools = `${button(state.arrangeMode ? 'Lock layout' : 'Arrange', 'toggle-arrange', 'secondary')}${state.arrangeMode ? button('Reset layout', 'reset-layout', 'secondary') : ''}${button('Refresh', 'refresh-readout', 'secondary')}${button('Save', 'save', 'secondary')}<span class="play-header-divider" aria-hidden="true"></span>${button('Return to Menu', 'return-menu', 'secondary')}`;
  return `<header id="play-header" class="play-header play-header-${E(kind)}" ${state.playHeaderOpen ? '' : 'hidden'}>
    <span class="play-header-glyph" aria-hidden="true">${ATMOSPHERE_GLYPHS[kind] || '✧'}</span>
    <div class="play-header-title">${trail}<h2>${E(shellAtmosphereTitle())}</h2>${metadata}</div>
    <p class="play-header-aside">${E(shellAtmosphereSubtitle())}</p>
    <div class="play-header-tools" role="toolbar" aria-label="Session">${tools}</div>
  </header>`;
}
function shell() {
  const screenLabel = gameplayLabels[state.selected] || state.selected;
  return `<div class="mode-menu gameplay-shell">${playHeader(screenLabel)}<section class="play-surface" aria-label="${E(screenLabel)} display">${partyHud()}
    <main class="master-grid ${state.arrangeMode ? 'arrange-mode' : ''}"><aside class="left-rail workspace-panel" data-workspace-panel="party" style="${panelStyle('party')}"><div class="panel-drag-handle" data-panel-handle="party"><span>Party</span><small>Drag · resize</small></div>${party().map(actorCard).join('') || '<p>No public party.</p>'}</aside>
    <section id="screen-${E(state.selected)}" class="center-stage" role="tabpanel" aria-label="${E(screenLabel)}">${hudStage(`${gameplay()}${state.receipt ? card('Latest public receipt', `<details><summary>Show receipt details</summary><pre>${E(JSON.stringify(state.receipt, null, 2))}</pre></details>`) : ''}`)}</section></main></section></div>`;
}

function panelStyle(id) {
  const row = state.workspaceLayout[id] || {};
  const x = Number(row.x); const y = Number(row.y);
  const width = Number(row.width); const height = Number(row.height);
  const z = Number(row.z);
  return `--drag-x:${Number.isFinite(x) ? x : 0}px;--drag-y:${Number.isFinite(y) ? y : 0}px;${Number.isFinite(width) && width > 0 ? `width:${width}px;` : ''}${Number.isFinite(height) && height > 0 ? `height:${height}px;` : ''}${Number.isFinite(z) && z > 0 ? `z-index:${CHROME_Z_BASE + z};` : ''}`;
}

// Must match --z-chrome in tokens.css -- the JS-computed inline z-index for a
// moved chrome panel (base + how recently it was picked up) and the CSS
// resting tier are the same one scale, just expressed in two languages.
const CHROME_Z_BASE = 600;
// Every menu and interface panel can be dragged by its grip (or an existing
// header). Offsets persist in workspaceLayout; double-click a grip to reset it.
// The Main Window (.center-stage) is deliberately absent from this list: it is
// a fixed backdrop, never draggable, always pinned beneath every panel here
// (see the z-index scale in tokens.css / styles.css). It used to be listed and
// could out-rank chrome panels in the shared drag-order z-race -- that was the
// "dragged panels end up behind the background" bug.
// .mobile-topbar and .mobile-game-nav are deliberately absent from this list:
// they are the app's global fixed nav/action chrome (see topNavigation() /
// mobileNavigation()), pinned at the top/bottom edge of #app.app-shell on
// every breakpoint now, not just mobile -- letting them join the drag pool
// would make the persistent Back/Options frame driftable like a workspace panel.
// The command console is the exception among bottom chrome: it floats over
// the play surface and is always movable (see consoleBar()).
const DRAGGABLES = [
  ['.mobile-party-hud', 'party-hud'], ['.left-rail', 'party'],
  ['.hsr-target-picker', 'targets'], ['.hsr-message-panel', 'messages'],
  ['#app > .hsr-command-bar', 'console'],
  ['.cc-main', 'creator-main'],
  ['.cc-body > aside', 'creator-lead'], ['#app > .notice[role="status"]', 'status-note'],
];
function applyDragOffset(panel, id) {
  const row = state.workspaceLayout[id] || {};
  const x = Number(row.x) || 0, y = Number(row.y) || 0;
  const z = Number(row.z);
  panel.style.setProperty('--drag-x', `${x}px`);
  panel.style.setProperty('--drag-y', `${y}px`);
  if (Number.isFinite(z) && z > 0) panel.style.zIndex = String(CHROME_Z_BASE + z);
  else panel.style.removeProperty('z-index');
  panel.classList.toggle('is-moved', Boolean(x || y));
}
const DRAGGABLES_SELECTOR = DRAGGABLES.map(([selector]) => selector).join(',');
function bindDraggables() {
  if (matchMedia('(max-width: 720px)').matches) return;
  // render() replaces #app's whole subtree on every call, so this runs on
  // every state change -- one combined query beats 17 separate tree walks.
  const counts = new Map();
  document.querySelectorAll(DRAGGABLES_SELECTOR).forEach(panel => {
      const entry = DRAGGABLES.find(([selector]) => panel.matches(selector));
      if (!entry) return;
      const key = entry[1];
      if (!panel.textContent.trim()) return;
      // Normal play keeps the frame quiet. Arrange exposes the move/resize
      // affordances for workspace panels; transient targets/messages remain
      // movable only while they are actually open.
      if (!state.arrangeMode && !['targets', 'messages', 'console'].includes(key)) return;
      const index = counts.get(key) || 0;
      counts.set(key, index + 1);
      const id = index ? `${key}-${index}` : key;
      panel.classList.add('hsr-draggable');
      panel.dataset.dragId = id;
      if (getComputedStyle(panel).position === 'static') panel.classList.add('drag-anchor');
      applyDragOffset(panel, id);
      let grip = panel.querySelector(':scope > [data-drag-grip]');
      if (!grip) {
        grip = document.createElement('span');
        grip.className = 'drag-grip';
        grip.dataset.dragGrip = '';
        grip.setAttribute('role', 'button');
        grip.tabIndex = 0;
        grip.setAttribute('aria-label', 'Drag panel (double-click to reset)');
        grip.title = 'Drag to move · double-click to reset';
        grip.textContent = '⠿';
        grip.onkeydown = event => {
          if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); grip.ondblclick?.(event); }
        };
        grip.onclick = event => { event.preventDefault(); event.stopPropagation(); };
        panel.prepend(grip);
      }
      const handles = [grip, ...panel.querySelectorAll(':scope > .panel-header, :scope > .panel-drag-handle, :scope > .action-bar-label, :scope > .console-head, :scope > .console-row')];
      handles.forEach(handle => {
        handle.ondblclick = event => {
          if (event?.target?.closest?.('button,input,select,textarea,a')) return;
          delete state.workspaceLayout[id]; saveWorkspaceLayout(); applyDragOffset(panel, id);
          if (id === 'console') { panel.style.removeProperty('--console-w'); panel.style.removeProperty('--console-h'); }
        };
        handle.onpointerdown = event => {
          if (event.button !== 0 || event.target.closest('button,input,select,textarea,a')) return;
          event.preventDefault();
          const saved = state.workspaceLayout[id] || {};
          const origin = {x: Number(saved.x) || 0, y: Number(saved.y) || 0};
          const start = {x: event.clientX, y: event.clientY};
          const box = panel.getBoundingClientRect();
          const keep = 60;
          const z = ++state.dragSequence;
          state.workspaceLayout[id] = {...saved, z};
          panel.style.zIndex = String(CHROME_Z_BASE + z);
          try { handle.setPointerCapture(event.pointerId); } catch {}
          panel.classList.add('is-dragging');
          handle.onpointermove = move => {
            let dx = move.clientX - start.x, dy = move.clientY - start.y;
            dx = Math.max(keep - box.right, Math.min(innerWidth - keep - box.left, dx));
            dy = Math.max(-box.top, Math.min(innerHeight - keep - box.top, dy));
            state.workspaceLayout[id] = {...saved, x: Math.round(origin.x + dx), y: Math.round(origin.y + dy)};
            applyDragOffset(panel, id);
          };
          handle.onpointerup = handle.onpointercancel = up => {
            if (handle.hasPointerCapture(up.pointerId)) handle.releasePointerCapture(up.pointerId);
            handle.onpointermove = handle.onpointerup = handle.onpointercancel = null;
            panel.classList.remove('is-dragging');
            saveWorkspaceLayout();
          };
        };
      });
  });
}
function bindWorkspacePanels() {
  if (!state.arrangeMode || matchMedia('(max-width: 720px)').matches) return;
  document.querySelectorAll('[data-workspace-panel]').forEach(panel => {
    const id = panel.dataset.workspacePanel || panel.id.replace('-panel', '');
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
        selectGameplayScreen(state.view?.expedition?.active ? 'battle' : 'room'); state.note = 'Arcade gate cleared; the room reward is now public.'; render();
      },
      onError: error => {
        ui.loop.stop(); state.note = `Arcade frame paused: ${error.message}`; updateArcadeStatus();
      },
    });
    state.arcadeUi = ui;
    ui.canvas.setOptions({hpBars: state.preferences.combat.hpBars, hpNumbers: state.preferences.combat.hpNumbers, reducedMotion: motionReduced(), sceneKey: `${state.runId}:${state.view?.room?.id}`});
    ui.canvas.setActors([...party(), ...(state.view?.opposition || [])]);
    ui.canvas.setState(state.view.arcade);
    ui.loop.start();
  } else {
    state.arcadeUi.canvas.setOptions({hpBars: state.preferences.combat.hpBars, hpNumbers: state.preferences.combat.hpNumbers, reducedMotion: motionReduced(), sceneKey: `${state.runId}:${state.view?.room?.id}`});
    state.arcadeUi.canvas.setActors([...party(), ...(state.view?.opposition || [])]);
    state.arcadeUi.canvas.setState(state.view.arcade);
    updateArcadeStatus();
  }
}
// The Tactical Menu's command tree — shared by the combat-forced inline
// layout and the exploration-time "Tactical Menu" mode chip.
function renderTacticalContent(actions) {
  const attackAction = actions.find(a => (a.id || a.action || a.type) === 'attack');
  const moveAction = actions.find(a => (a.id || a.action || a.type) === 'move');
  const castAction = actions.find(a => (a.id || a.action || a.type) === 'cast');
  const endAction = actions.find(a => (a.id || a.action || a.type) === 'end_turn');

  const maneuvers = actions.filter(a => a.category === 'tactical' || a.category === 'maneuver');

  return `<div class="tactical-command-tree">
    <button type="button" class="tactical-command-btn" data-engine-action="attack" data-hotkey="1" ${attackAction ? '' : 'disabled'}><span style="font-size:18px;">⚔️</span><span>Attack [1]</span></button>
    <button type="button" class="tactical-command-btn" data-engine-action="move" data-hotkey="2" ${moveAction ? '' : 'disabled'}><span style="font-size:18px;">⇢</span><span>Move [2]</span></button>
    <button type="button" class="tactical-command-btn" data-engine-action="cast" data-hotkey="3" ${castAction ? '' : 'disabled'}><span style="font-size:18px;">✧</span><span>Magic [3]</span></button>
    <button type="button" class="tactical-command-btn" data-action="toggle-bookbag"><span style="font-size:18px;">🎒</span><span>Items [I]</span></button>
    ${maneuvers.length ? `<button type="button" class="tactical-command-btn" data-engine-action="${E(maneuvers[0].id || maneuvers[0].type)}" data-hotkey="4"><span style="font-size:18px;">⚡</span><span>Maneuver [4]</span></button>` : ''}
    <button type="button" class="tactical-command-btn" data-engine-action="end_turn" ${endAction ? '' : 'disabled'} style="border-color:var(--gold);"><span style="font-size:18px;">⏳</span><span>End Turn [Space]</span></button>
  </div>`;
}
function actionBar() {
  if (state.phase !== 'ready') return '';
  // A life action never degrades into an empty affordance set; the host's type, label, and category are preserved.
  const stepActor = encounterStepActor();
  const arcadeLive = Boolean(state.view?.arcade && !state.view.arcade.complete);
  const actions = (state.view?.available_actions || []).filter(row => {
    const id = row.id || row.action || row.type;
    if (row.available === false) return false;
    if (arcadeLive && ['attack', 'maneuver', 'move', 'cast', 'end_turn', 'resolve_reaction', 'decline_reaction', ...CONTEXTUAL_DIRECT, ...CONTEXTUAL_TARGETED].includes(id)) return false;
    if (['attack', 'maneuver', ...CONTEXTUAL_TARGETED, 'decant'].includes(id) || id.startsWith('maneuver_')) return actionTargets(id).length > 0;
    if (encounterActive() && ['move', 'cast', 'end_turn', ...CONTEXTUAL_DIRECT].includes(id)) return stepActor.startsWith('p');
    return true;
  });
  if (!state.runId) return '';

  // Turn-based combat forces the Tactical layout inline (no popup, no mode
  // switcher) regardless of the player's exploration-mode preference: the
  // other three modes have no wiring for combat's turn economy/targeting.
  if (tacticalActive()) {
    return `<div class="hsr-dock-container combat-inline">${renderTacticalContent(actions)}</div>`;
  }

  const activeMode = state.preferences.actionMode || 'unified';

  const modeChips = [
    ['unified', 'Unified Hotbar'],
    ['tactical', 'Tactical Menu'],
    ['contextual', 'Contextual'],
    ['console', 'Console']
  ].map(([m, label]) => `<button type="button" class="dock-mode-chip ${activeMode === m ? 'active' : ''}" data-action="set-action-mode:${m}">${label}</button>`).join('');

  const modeBar = `<div class="dock-mode-bar"><span>Action Interface</span><div class="dock-mode-chips">${modeChips}</div></div>`;

  let contentHtml = '';

  if (activeMode === 'tactical') {
    contentHtml = renderTacticalContent(actions);
  } else if (activeMode === 'contextual') {
    const topActions = actions.slice(0, 6);
    contentHtml = `<div class="actions" style="padding:10px;justify-content:center;flex-wrap:wrap;">${topActions.map((row, idx) => {
      const id = row.id || row.action || row.type;
      const cost = row.cost && row.cost !== 'free' ? ` · ${String(row.cost).replaceAll('_', ' ')}` : '';
      return `<button class="action engine-action" data-engine-action="${E(id)}" data-hotkey="${idx + 1}" title="${E((row.help || FLAVOR.actions[id] || row.label || id) + cost)}"><span class="action-glyph" aria-hidden="true">${E(ACTION_ICONS[id] || '·')}</span><span class="action-text">${E(row.label || id)}</span><span class="hotkey-badge">${idx + 1}</span></button>`;
    }).join('')}</div>`;
  } else if (activeMode === 'console') {
    contentHtml = `<form class="inline-console-mode" id="inline-action-console" onsubmit="event.preventDefault();"><input type="text" id="inline-console-input" placeholder="Type command (e.g. 'attack e0', 'move 10,10', 'cast shield', 'end turn')..." autocomplete="off"><button type="submit" class="action primary" style="min-height:36px;padding:6px 14px;">Execute [Enter]</button></form>`;
  } else {
    // Default Unified Action Dock
    const groups = [];
    for (const row of actions) {
      const title = ACTION_CATEGORY_TITLES[row.category] || (encounterActive() ? 'Other' : 'Room');
      let group = groups.find(g => g.title === title);
      if (!group) groups.push(group = {title, rows: []});
      group.rows.push(row);
    }
    groups.sort((a, b) => ACTION_CATEGORY_ORDER.indexOf(a.title) - ACTION_CATEGORY_ORDER.indexOf(b.title));

    let actionIndex = 1;
    const buttons = groups.map(group => `${groups.length > 1 ? `<span class="engine-action-group">${E(group.title)}</span>` : ''}${group.rows.map(row => {
      const id = row.id || row.action || row.type;
      const cost = row.cost && row.cost !== 'free' ? ` · ${String(row.cost).replaceAll('_', ' ')}` : '';
      const hotkey = id === 'end_turn' ? 'Space' : actionIndex <= 9 ? String(actionIndex++) : '';
      const hotkeyAttr = /^[1-9]$/.test(hotkey) ? ` data-hotkey="${hotkey}"` : '';
      return `<button class="action engine-action" data-engine-action="${E(id)}"${hotkeyAttr} title="${E((row.help || FLAVOR.actions[id] || row.label || id) + cost)}"><span class="action-glyph" aria-hidden="true">${E(ACTION_ICONS[id] || '·')}</span><span class="action-text">${E(row.label || id)}</span>${hotkey ? `<span class="hotkey-badge">${hotkey}</span>` : ''}</button>`;
    }).join('')}`).join('');

    contentHtml = `<nav class="engine-action-bar" data-panel="actions" aria-label="Engine actions">${buttons}<button type="button" class="action secondary engine-help-print" data-action="help-print" title="Print what each action does, and the console commands, into the log">Print help to log</button></nav>`;
  }

  if (activeMode !== 'unified') {
    const champions=actions.filter(row=>row.category==='champion');
    if(champions.length) contentHtml += `<nav class="actions" aria-label="Champion abilities">${champions.map(row=>`<button type="button" class="action engine-action" data-engine-action="${E(row.id)}" title="${E(row.help || '')}"><span class="action-text">${E(row.label)}</span></button>`).join('')}</nav>`;
  }
  return `<details class="engine-help" id="engine-help" ${state.engineHelpOpen ? 'open' : ''}><summary class="mobile-nav-item" aria-label="Help and engine actions"><span>Actions</span><span aria-hidden="true">›</span></summary><div class="hsr-dock-container">${modeBar}${contentHtml}</div></details>`;
}
// Contextual combat actions the host publishes (tactical.contextual_actions).
const CONTEXTUAL_DIRECT = ['dodge', 'dash', 'disengage', 'escape_grapple', 'stand', 'action_surge', 'second_wind', 'ring_heal'];
const CONTEXTUAL_TARGETED = ['shove', 'trip', 'grapple', 'help', 'grand_cleave', 'read_seam', 'quick_toss', 'dagger_attack', 'cleaver_attack'];
const ACTION_ICONS = {inspect: '⌕', investigate: '◌', enter: '↳', descend: '⇣', enter_gauntlet: '⇣', rest: '☾', exit: '←', attack: '⚔', move: '⇢', cast: '✧', end_turn: '⏳', conversation: '☵', identify: '◇', escape: '↗',
  dodge: '↺', dash: '»', disengage: '⇠', shove: '⇥', trip: '⤓', grapple: '⊗', escape_grapple: '⊘', help: '✚', stand: '⤒', decant: '⚗'};
// The Help popup is a <details>; a full render rebuilds the DOM, so its open
// state lives in state.engineHelpOpen. Escape or a click outside closes it.
function closeEngineHelp() {
  if (!state.engineHelpOpen && !document.querySelector('#engine-help[open]')) return;
  state.engineHelpOpen = false;
  document.querySelector('#engine-help')?.removeAttribute('open');
}
document.addEventListener('keydown', event => { if (event.key === 'Escape' && (state.engineHelpOpen || document.querySelector('#engine-help[open]'))) { event.preventDefault(); event.stopPropagation(); closeEngineHelp(); } });
document.addEventListener('pointerdown', event => { if (!event.target?.closest?.('#engine-help')) closeEngineHelp(); });
// Click feedback on the main display: a ring pings where the scene was
// clicked, so every click on the stage visibly lands before the host replies.
document.addEventListener('pointerdown', event => {
  if (event.button !== 0 || motionReduced()) return;
  const scene = event.target?.closest?.('.stage-hud > .illustrated-scene');
  if (!scene) return;
  const box = scene.getBoundingClientRect();
  const ping = document.createElement('span');
  ping.className = `stage-ping${event.target.closest('[data-stage-actor],[data-object]') ? ' on-target' : ''}`;
  ping.setAttribute('aria-hidden', 'true');
  ping.style.left = `${event.clientX - box.left}px`;
  ping.style.top = `${event.clientY - box.top}px`;
  scene.append(ping);
  ping.addEventListener('animationend', () => ping.remove(), {once: true});
});
const ACTION_CATEGORY_TITLES = {champion: 'Champion', standard: 'Standard', tactical: 'Tactical', movement: 'Movement', turn: 'Turn'};
const ACTION_CATEGORY_ORDER = ['Room', 'Champion', 'Standard', 'Tactical', 'Movement', 'Other', 'Turn'];
// "Print help to log" and `/help actions`: one readable guide, written to the
// Messages log (and mirrored into Debug) so it survives the popup closing.
function printActionGuide() {
  const combat = state.view?.combat;
  const catalog = Array.isArray(combat?.contextual_actions) ? combat.contextual_actions : [];
  const rows = catalog.length ? catalog : (state.view?.available_actions || []);
  addMessage(`— Action guide${catalog.length ? ` · ${party().find(m => m.id === combat.current)?.name || combat.current}'s turn` : ''} —`, 'note');
  for (const row of rows) {
    const id = row.id || row.action || row.type;
    const text = row.help || FLAVOR.actions[id] || '';
    const cost = row.cost && row.cost !== 'free' ? ` [${String(row.cost).replaceAll('_', ' ')}]` : '';
    const blocked = row.available === false && row.reason ? ` (not now: ${row.reason})` : '';
    addMessage(`${row.label || id}${cost}${text ? ` — ${text}` : ''}${blocked}`, 'note');
  }
  if (!rows.length) addMessage('No engine actions are available on this screen.', 'note');
  addMessage('Type a plain sentence to act ("shove the thug", "trip e0", "help Wren against e1", "decant item-3"). /help lists console commands; /help actions reprints this guide.', 'note');
  debugLog('info', 'HELP', 'Action guide printed to the log', rows.map(row => row.id || row.action || row.type));
  state.messageHistoryOpen = true;
  state.messagePanelTab = 'messages';
}
const FOCUS_ATTRS = ['data-choice', 'data-look', 'data-skill-pick', 'data-pref-path', 'data-pref', 'data-action', 'data-create-field', 'data-assign', 'data-skill', 'data-spell', 'data-floating', 'data-advancement'];
function focusSignature(node) {
  if (!node || node === document.body) return '';
  if (node.matches?.('input[type="radio"][data-pref]')) return `[data-pref="${CSS.escape(node.dataset.pref)}"][value="${CSS.escape(node.value)}"]`;
  const attr = FOCUS_ATTRS.find(name => node.hasAttribute?.(name));
  if (!attr) return '';
  const value = CSS.escape(node.getAttribute(attr));
  const overlay = node.closest?.('[data-overlay-root]');
  return `${overlay ? `[data-overlay-root] [${attr}="${value}"]` : `[${attr}="${value}"]`}`;
}
function restoreFocus(key) {
  if (!key) return;
  const node = document.querySelector(key);
  if (!node) return;
  node.focus({preventScroll: true});
}
function captureRenderContinuity() {
  const app = document.querySelector('#app');
  const scrollSelectors = ['.menu-viewport', '.mode-menu-card', '.center-stage', '.hud-dock', '.hsr-stage-frame', '.cc-overlay-body', '.cc-cards', '.cc-lead', '.ability-table', '.cc-ab-table', '.run-list', '.statistics-save-list'];
  const scroll = scrollSelectors.flatMap(selector => [...(app?.querySelectorAll(selector) || [])].map((node, index) => ({selector, index, top: node.scrollTop, left: node.scrollLeft})));
  const disclosures = [...(app?.querySelectorAll('#screen-options details[id]') || [])].map(node => ({id: node.id, open: node.open}));
  const active = document.activeElement;
  const focusedOverlayBody = active?.closest?.('[data-overlay-root]')?.querySelector('.cc-overlay-body');
  return {
    scroll,
    disclosures,
    focus: focusSignature(active),
    selection: active && typeof active.selectionStart === 'number'
      ? {start: active.selectionStart, end: active.selectionEnd, direction: active.selectionDirection}
      : null,
    windowX: window.scrollX,
    windowY: window.scrollY,
    overlayHadFocus: Boolean(active?.closest?.('[data-overlay-root]')),
    overlayScroll: focusedOverlayBody ? ({top: focusedOverlayBody.scrollTop, left: focusedOverlayBody.scrollLeft}) : null,
  };
}
function restoreRenderContinuity(snapshot) {
  if (!snapshot) return;
  const applyScroll = () => {
    for (const {selector, index, top, left} of snapshot.scroll) {
      const node = document.querySelectorAll(selector)[index];
      if (node) { node.scrollTop = top; node.scrollLeft = left; }
    }
    if (snapshot.overlayScroll) {
      const node = document.querySelector('[data-overlay-root] .cc-overlay-body');
      if (node) { node.scrollTop = snapshot.overlayScroll.top; node.scrollLeft = snapshot.overlayScroll.left; }
    }
  };
  for (const {id, open} of snapshot.disclosures) {
    const node = document.getElementById(id);
    if (node?.matches('details')) node.open = open;
  }
  applyScroll();
  restoreFocus(snapshot.focus);
  applyScroll();
  requestAnimationFrame(applyScroll);
  const focused = snapshot.focus ? document.querySelector(snapshot.focus) : null;
  if (focused && snapshot.selection) {
    try { focused.setSelectionRange(snapshot.selection.start, snapshot.selection.end, snapshot.selection.direction); } catch {}
  }
  if (window.scrollX !== snapshot.windowX || window.scrollY !== snapshot.windowY) window.scrollTo(snapshot.windowX, snapshot.windowY);
}
// ---- Screen changes ---------------------------------------------------------
// render() runs on every state change, but only a change of screen should look
// like one. A screen is the phase (plus the gameplay tab in play); when it
// changes, the outgoing screen is kept as an inert ghost that fades out while
// the new one fades and rises in over the still-moving backdrop. Same-screen
// renders swap in place with no animation at all.
let renderedScreen = null;
const SCREEN_EXIT_MS = 200;
let screenExitTimer = 0;
function screenKey() { return state.phase === 'ready' ? `ready:${state.selected}:${state.runId || ''}:${state.view?.room?.id || state.view?.room?.room_id || ''}` : state.phase; }
function ghostScreen(app) {
  return null; // Do not clone frame chrome between screens.
  if (!app?.childElementCount) return null;
  const rect = app.getBoundingClientRect();
  const scrolled = [...app.querySelectorAll('*')].map((node, index) => [index, node.scrollTop, node.scrollLeft]).filter(([, top, left]) => top || left);
  const ghost = app.cloneNode(true);
  ghost.removeAttribute('id'); ghost.removeAttribute('aria-live'); ghost.removeAttribute('aria-busy');
  ghost.classList.add('screen-exit'); ghost.setAttribute('aria-hidden', 'true'); ghost.inert = true;
  ghost.querySelectorAll('[id]').forEach(node => node.removeAttribute('id'));
  Object.assign(ghost.style, {top: `${rect.top}px`, left: `${rect.left}px`, width: `${rect.width}px`, height: `${rect.height}px`});
  return {ghost, scrolled};
}
function releaseGhost(entry, app) {
  if (!entry) return;
  document.querySelectorAll('.screen-exit').forEach(node => node.remove());
  app.after(entry.ghost);
  const nodes = entry.ghost.querySelectorAll('*');
  for (const [index, top, left] of entry.scrolled) { if (nodes[index]) { nodes[index].scrollTop = top; nodes[index].scrollLeft = left; } }
  clearTimeout(screenExitTimer);
  screenExitTimer = setTimeout(() => {
    entry.ghost.remove();
    screenExitTimer = 0;
  }, SCREEN_EXIT_MS + 40);
}
function render() {
  screenFade.request(screenKey(), motionReduced(), renderNow);
}
function renderNow() {
  dismissContextMenu();
  const app = document.querySelector('#app');
  const key = screenKey();
  const firstPaint = renderedScreen === null;
  const phaseChanged = !firstPaint && renderedScreen.split(':')[0] !== state.phase;
  const tabChanged = !firstPaint && !phaseChanged && renderedScreen !== key;
  if (phaseChanged) {
    clearTimeout(screenExitTimer);
    screenExitTimer = 0;
    document.querySelectorAll('.screen-exit').forEach(node => node.remove());
  }
  renderedScreen = key;
  const animate = !motionReduced();
  const ghost = animate && phaseChanged ? ghostScreen(app) : null;
  // Scroll and disclosure state belong to the screen they were read from.
  const continuity = phaseChanged ? {...captureRenderContinuity(), scroll: [], disclosures: []} : captureRenderContinuity();
  const activeTooltipText = document.querySelector('#hsr-tooltip')?.textContent;
  const activeTooltipTarget = document.querySelector('[aria-describedby="hsr-tooltip"]');
  const activeTargetSig = activeTooltipTarget ? focusSignature(activeTooltipTarget) : null;
  document.querySelector('#hsr-tooltip')?.remove();
  document.querySelectorAll('[aria-describedby="hsr-tooltip"]').forEach(node => node.removeAttribute('aria-describedby'));
  applyPreferences();
  ensureBackdrop();
  let body = state.phase === 'title' ? title() : state.phase === 'transport' ? transportChoice() :
    state.phase === 'menu-story' ? storyMenu() : state.phase === 'menu-simulation' ? simulationMenu() :
    state.phase === 'party-select' ? partySelect() : state.phase === 'champion-select' ? champion() :
    state.phase === 'create' ? creator() : state.phase === 'entry-select' ? entrySelect() :
    state.phase === 'preview' ? preview() : state.phase === 'runs' ? runs() :
    state.phase === 'statistics' ? statisticsScreen() : state.phase === 'edit-scenario' ? scenarioEditor() :
    state.phase === 'cheats' ? cheatsPanel() : state.phase === 'archive' ? archiveScreen() : state.phase === 'codex' ? codexScreen() : state.phase === 'ladder' ? ladderScreen() : state.phase === 'meta-shop' ? metaShopScreen() : state.phase === 'toolbox' ? toolboxScreen() : state.phase === 'options' ? options() : shell();
  // The desktop app is a locked-ratio frame, so long pre-game/menu screens
  // need one named in-frame scrolling region.  Gameplay owns its centre-stage
  // scroller and the fixed creator owns its stage; wrapping either here would
  // introduce a second scroll surface and break their geometry contracts.
  if (!['title', 'ready', 'create', 'preview', 'toolbox'].includes(state.phase)) {
    body = `<div class="menu-viewport" data-menu-viewport>${body}</div>`;
  }
  const staleSandboxNotice = state.staleSandbox
    ? `<div class="notice error stale-sandbox-notice"><p>${E(state.error)}</p><div class="actions">${button(`End ${state.staleSandbox.run_id} and start fresh`, 'resolve-stale-sandbox', 'primary')}</div></div>`
    : state.error ? `<p class="notice error" role="alert">${E(state.error)}</p>` : '';
  // In the 'ready' phase the Workspace card already shows state.note at the
  // bottom of Run status -- showing it again here as a second, page-level
  // paragraph was the literal duplicate the redesign set out to remove.
  const activityNotice = state.busy && state.activity.visible
    ? `<p class="notice local-activity" role="status"><strong>${E(state.activity.label)}</strong> — ${E(state.activity.line)}</p>`
    : (state.phase === 'ready' || state.preferences.showStatusMessages === false) ? '' : `<p class="notice" role="status">${E(state.note)}</p>`;
  const dockContent = `${targetPicker()}${spellPicker()}`;
  const commandBarHtml = consoleBar();
  // The console carries the log inline; the standalone popup is only for
  // screens that have no console to expand.
  const messagePanelHtml = state.messageHistoryOpen && !commandBarHtml ? messagePanel() : '';
  // Keep the console log where the reader left it: pinned to the newest line
  // unless they had scrolled back through history.
  const oldLog = document.querySelector('#app .console-log .message-history');
  const logScroll = oldLog ? {top: oldLog.scrollTop, pinned: oldLog.scrollHeight - oldLog.scrollTop - oldLog.clientHeight < 24} : null;
  // Persistent regions survive the rebuild: the combat stage (reconciled by
  // actor) and the arcade root (its canvas, loop and input keep running).
  const liveStage = document.querySelector('#app .combat-stage'); liveStage?.remove();
  const liveArcade = document.querySelector('#app [data-arcade-root]'); liveArcade?.remove();
  if (worldStage?.el.isConnected) worldStage.el.remove();
  if (toolbox?.el.isConnected) toolbox.el.remove();
    const nextHtml = `${topNavigation()}${body}${staleSandboxNotice}${activityNotice}${messagePanelHtml}${commandBarHtml}${dockContent && state.preferences.showActionDock !== false ? `<div class="hsr-dock tray-${E(state.trayState)}">${trayHandle()}<div class="tray-content">${dockContent}</div></div>` : ''}${mobileNavigation()}${combatRadialMenu()}${disconnectOverlay()}${bookbagModal()}${systemMenuModal()}`;
  if (app.innerHTML !== nextHtml) {
    const temp = document.createElement('div');
    temp.innerHTML = nextHtml;
    morphChildren(app, temp);
  }
  document.querySelectorAll('#app [title]').forEach(node => node.removeAttribute('title'));
  document.querySelectorAll('button,input,select').forEach(node => { node.disabled = state.busy || node.dataset.locked === 'true'; });
  reconcileBattleStage(liveStage);
  keepArcadeRoot(liveArcade);
  keepWorldStage();
  document.querySelectorAll('#app [data-item],#app [data-gear]').forEach(node => node.dataset.tooltipRich = 'true');
  keepToolbox();
  keepBattleBackdrop();
  syncPuppets(app, {reducedMotion: motionReduced});
  combatDirector.kick();
  bind(); bindCreator(); bindConsole();
  app.querySelectorAll('[data-puppet-pose]').forEach(button => button.onclick = () => {
    state.puppetPreviewPose=button.dataset.puppetPose;
    app.querySelectorAll('[data-puppet-preview]').forEach(n=>n.dataset.previewPose=state.puppetPreviewPose);
    app.querySelectorAll('[data-puppet-pose]').forEach(n=>n.setAttribute('aria-pressed',String(n.dataset.puppetPose===state.puppetPreviewPose)));
  });
  app.querySelectorAll('[data-puppet-facing]').forEach(button => button.onclick = () => {
    state.puppetPreviewFacing=-(state.puppetPreviewFacing||1);
    app.querySelectorAll('[data-puppet-preview]').forEach(n=>n.dataset.previewFacing=state.puppetPreviewFacing);
  });
  if (activeTargetSig && activeTooltipText) {
    const freshTarget = document.querySelector(activeTargetSig);
    if (freshTarget && freshTarget.matches(':hover')) {
      freshTarget.dispatchEvent(new PointerEvent('pointerover', {bubbles:true, pointerType:'mouse'}));
    }
  }
  const newLog = document.querySelector('#app .console-log .message-history');
  if (newLog) newLog.scrollTop = !logScroll || logScroll.pinned ? newLog.scrollHeight : logScroll.top;
  applyStageGeometry();
  restoreRenderContinuity(continuity);
  // Clicking the dimmed backdrop dismisses; clicking the card does not.
  const overlayRoot = document.querySelector('[data-overlay-root]');
  if (overlayRoot) {
    overlayRoot.onclick = event => { if (event.target === overlayRoot) closeOverlay(); };
    if (!continuity.overlayHadFocus) overlayRoot.querySelector('.cc-overlay-close, .action')?.focus({preventScroll: true});
  }
  app.classList.remove('screen-enter', 'stage-enter');
  releaseGhost(ghost, app);
}
addEventListener('keydown', event => {
  if (event.key === 'Escape' && state.overlay) { event.preventDefault(); event.stopPropagation(); closeOverlay(); }
}, true);
// Gambit editor rows as currently shown, so edits survive add/remove/tab swaps.
function readGambitRows() {
  return [...document.querySelectorAll('[data-gambit-row]')].map(row => {
    const field = name => row.querySelector(`[data-gambit-field="${name}"]`)?.value ?? '';
    return {when: field('when'), value: field('value'), then: field('then'), target: field('target')};
  });
}
function bindExpeditionControls() {
  document.querySelectorAll('[data-xp-node]').forEach(node => {
    const pick = () => { state.xpSelected = node.dataset.xpNode; render(); };
    node.addEventListener('click', pick);
    node.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); pick(); } });
  });
  document.querySelectorAll('[data-xp-go]').forEach(node => node.onclick = () => work(async () => {
    const mode = node.dataset.xpGo;
    const reply = result(await state.client.request('expedition_choose', {run_id: state.runId, node: state.xpSelected, mode}));
    state.xpSelected = null;
    const auto = reply.result?.event?.auto || reply.event?.auto;
    state.note = mode === 'auto' ? `Gambits played the node${auto?.stopped ? ` (${String(auto.stopped).replaceAll('_', ' ')})` : ''}.` : 'Node entered.';
    addMessage(state.note);
    selectGameplayScreen('battle');
  }, 'Entering node'));
  document.querySelectorAll('[data-xp-afk]').forEach(n => n.onsubmit = event => {
    event.preventDefault();
    const data = new FormData(event.target);
    const maxNodes = Number(data.get('max_nodes')); const retreat = Number(data.get('retreat_below'));
    state.xpAfk = {max_nodes: maxNodes, retreat};
    work(async () => {
      result(await state.client.request('expedition_auto', {run_id: state.runId, max_nodes: maxNodes, retreat_below: retreat / 100}));
      const summary = state.view?.expedition?.last_auto;
      state.note = summary ? `AFK run: ${summary.nodes.length} node(s), stopped: ${String(summary.stopped).replaceAll('_', ' ')}.` : 'AFK run finished.';
      addMessage(state.note);
      selectGameplayScreen('battle');
    }, 'AFK expedition');
  });
  document.querySelectorAll('[data-ff-menu]').forEach(node => node.onclick = () => {
    state.ffMenu = state.ffMenu === node.dataset.ffMenu ? '' : node.dataset.ffMenu;
    render();
  });
  document.querySelectorAll('[data-ff-item]').forEach(node => node.onclick = () => work(async () => {
    result(await state.client.roomAction(state.runId, 'consume', {item: node.dataset.ffItem, actor: actingActorId()}));
    await loadReadout(state.runId);
    state.ffMenu = '';
    state.note = 'Item used.';
    addMessage(state.note);
  }));
  document.querySelectorAll('[data-gambit-actor]').forEach(node => node.onclick = () => {
    const id = document.querySelector('[data-gambit-list]')?.dataset.gambitList;
    if (id) state.gambitDraft = {...(state.gambitDraft || {}), [id]: readGambitRows()};
    state.gambitActor = node.dataset.gambitActor;
    render();
  });
  document.querySelectorAll('[data-gambit-remove]').forEach(node => node.onclick = () => {
    const id = document.querySelector('[data-gambit-list]')?.dataset.gambitList;
    const rows = readGambitRows();
    rows.splice(Number(node.dataset.gambitRemove), 1);
    state.gambitDraft = {...(state.gambitDraft || {}), [id]: rows};
    render();
  });
  document.querySelectorAll('[data-gambit-field="when"]').forEach(node => node.onchange = () => {
    const id = document.querySelector('[data-gambit-list]')?.dataset.gambitList;
    state.gambitDraft = {...(state.gambitDraft || {}), [id]: readGambitRows()};
    render();
  });
}
async function loadReadout(runId) { result(await state.client.readout(runId)); go('ready'); state.note = 'Public state refreshed.'; }
function resetRunStateForLoad() {
  state.view = null; state.receipt = null; state.presentation = null; state.terminal = null;
  state.debugReadout = null; state.arcadeUi = null; state.lastManeuver = null;
  state.actionPicker = null; state.spellPicker = null; state.focusTarget = null; state.pendingConversation = null;
  state.consoleDraft = ''; state.contextMenu = null; state.staleSandbox = null;
  state.runId = null; state.lastRunSeed = ''; state.messageHistory = [];
  state.statistics = null; state.statisticsDetail = null; state.statisticsView = 'menu';
  resetCreationDraft(); clearScreenTransientState();
}
async function loadFilteredRuns(filterMode) {
  const reply = await state.client.listRuns(); if (!reply.ok) throw Error(reply.error?.message);
  const historyReply = await state.client.statistics(filterMode);
  if (!historyReply.ok) throw Error(historyReply.error?.message || 'Run summaries are unavailable.');
  const history = new Map((historyReply.result?.saves || []).map(row => [row.run_id, row]));
  const ids = reply.result?.runs || [];
  const inspected = await Promise.all(ids.map(async run => {
    const id = typeof run === 'string' ? run : run.run_id;
    const detail = await state.client.request('inspect_run', {run_id: id});
    return detail.ok ? {...(detail.result?.run || run), history: history.get(id)} : run;
  }));
  return filterMode ? inspected.filter(run => String(run.context?.host_mode || run.mode || '').toUpperCase() === filterMode) : inspected;
}
async function loadStatistics(mode = state.statisticsMode, runId = null, view = 'list') {
  const reply = await state.client.statistics(mode, runId);
  if (!reply.ok) throw Error(reply.error?.message || 'Statistics are unavailable.');
  state.statistics = reply.result || null;
  state.statisticsView = view;
  state.statisticsDetail = reply.result?.selected_save || null;
}
const STALE_SANDBOX_PATTERN = /one active D&D sandbox run is already (?:saved|loaded): ([\w-]+)/;
// A sandbox run abandoned by a prior session (browser closed, host restarted)
// never leaves 'active' status on its own, so it holds the one-active-slot
// lock forever. withSandboxRecovery lets the UI offer to end it and retry
// instead of just failing every future sandbox start with no way out.
// Starting a game never stops at the host's one-active-sandbox rule: the old
// run is released (recorded as abandoned, exactly once, as a manual release
// would) and the start is retried. The note says what was ended.
async function withSandboxRecovery(attempt) {
  state.startingRunId = null;
  try {
    await attempt();
    state.staleSandbox = null;
  } catch (error) {
    const staleRunId = STALE_SANDBOX_PATTERN.exec(error.message || '')?.[1];
    if (!staleRunId) throw error;
    result(await state.client.sandboxRelease(staleRunId));
    // The lock trips at design_start, after the new run was already created.
    // Finish *that* run rather than re-running the attempt, which would mint
    // a second run id and leave the first behind as an orphan save.
    const created = state.startingRunId;
    if (created) {
      result(await state.client.designStart(created));
      state.runId = created;
      state.route = ['title'];
      await loadReadout(created);
      await state.afterRunStart?.();
    } else await attempt();
    state.staleSandbox = null;
    announceRunStart(`Ended the earlier sandbox run ${staleRunId} (recorded as abandoned) to start this one.`);
  }
}
function announceRunStart(prefix = '') {
  // The seed sentence is a durable, look-it-up-later detail (how to replay this
  // run), not a transient status line -- it belongs in the Messages & Errors
  // log only. Putting it in state.note too used to show the exact same
  // sentence in two places on screen at once.
  const seedText = state.lastRunSeed ? `Run seed ${state.lastRunSeed}${state.preferences.scenarioSeed ? ' (fixed by Seed override)' : ' — type it into Seed override to replay this exact run'}.` : '';
  state.note = prefix;
  if (seedText) addMessage([prefix, seedText].filter(Boolean).join(' '));
}
async function initializeRunScene(mode, runId) {
  // SANDBOX start-run creates the D&D sandbox immediately. Calling
  // design_start again is invalid there; FORGE still needs its authored
  // entry fixture initialized through the design command.
  if (mode !== 'SANDBOX') result(await state.client.designStart(runId));
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
async function beginChampionRun(name, startingLocation = 'market') {
  const attempt = async () => {
    const mode = state.pendingMode || 'SANDBOX';
    // Story/Champion mode uses the authored first village as its opening
    // scene. Keep the host mode FORGE so Champion-only launch rules and the
    // Story badge remain intact; the scenario selects the actual world.
    const scenario = mode === 'FORGE' ? 'reliquary_city' : scenarioFor(mode);
    result(await state.client.boot(mode));
    const runId = `${name.toLowerCase()}-${Date.now().toString(36)}`;
    state.startingRunId = runId; state.afterRunStart = null;
    result(await state.client.startRun({
      run_id: runId, mode, seed: state.lastRunSeed = runSeed(), scenario,
      party: [name], lead_selector: name, opposition: ['Townsperson'],
      starting_location: startingLocation,
      ...(mode === 'FORGE' ? {intent: 'Story Mode: open the authored first village for this Champion run.'} : {}),
      ...(mode === 'FORGE' ? {module_id: 'reliquary-template'} : {}),
    }));
    state.runId = runId;
    // A run actually starting discards the party-select/create/entry-select
    // trail behind it -- none of those screens are valid to return to once a
    // lead is locked in and the descent is underway, so Back from gameplay
    // must not be able to walk back into them.
    state.route = ['title'];
    await initializeRunScene(mode, runId);
    await loadReadout(runId);
    if (scenario === 'reliquary_city') {
      selectGameplayScreen(startingLocation === 'well' ? 'journey' : 'residents');
    }
    announceRunStart();
  };
  await work(() => withSandboxRecovery(attempt), `Beginning as ${name}`);
}
async function beginCustomRun(profileId, startingLocation = 'market') {
  const attempt = async () => {
    const mode = state.pendingMode || 'DESIGN';
    if (!['FORGE', 'SANDBOX'].includes(mode)) throw Error('Custom characters are available only in Story or Simulation Mode.');
    const scenario = scenarioFor(mode);
    const runId = `${profileId}-${Date.now().toString(36)}`;
    state.startingRunId = runId; state.afterRunStart = () => resetCreationDraft();
    result(await state.client.startRun({
      run_id: runId, mode, seed: state.lastRunSeed = runSeed(), scenario: scenarioFor(mode),
      party: [`custom:${profileId}`], lead_selector: `custom:${profileId}`, opposition: ['Townsperson'],
      starting_location: startingLocation,
      ...(mode === 'FORGE' ? {module_id: 'reliquary-template'} : {}),
    }));
    state.runId = runId;
    // See beginChampionRun: once the custom lead's descent actually begins,
    // Back must never be able to walk back into the workshop/lead-select
    // screens behind it -- they're finished business, not undo history.
    state.route = ['title'];
    await initializeRunScene(mode, runId);
    await loadReadout(runId);
    if (scenario === 'reliquary_city') {
      selectGameplayScreen(startingLocation === 'well' ? 'journey' : 'residents');
    }
    resetCreationDraft();
    announceRunStart();
  };
  // Confirmation already runs inside work() to build the local profile. Do not
  // discard the run launch by starting a nested busy transaction.
  if (state.busy) await withSandboxRecovery(attempt);
  else await work(() => withSandboxRecovery(attempt), 'Beginning custom descent');
}
async function beginChampionRehearsal() {
  await work(async () => {
    result(await state.client.boot('SANDBOX'));
    const runId = `castellan-${Date.now().toString(36)}`;
    result(await state.client.request('create_run', {
      run_id: runId, mode: 'SANDBOX', seed: state.lastRunSeed = runSeed(),
      scenario: 'champion_rehearsal', module_id: 'wren-boss-rehearsal',
      party: ['Doran', 'Wren'], opposition: ['Townsperson'], lead_selector: 'Doran',
    }));
    state.runId = runId;
    result(await state.client.designStart(runId));
    await loadReadout(runId);
    selectGameplayScreen('room');
    announceRunStart('Custom boss rehearsal ready. This fixture is not balance-certified.');
  }, 'Preparing champion rehearsal');
}
function championAbilities() {
  const options = Array.isArray(actor().ability_options) ? actor().ability_options : [];
  if (!options.length) return resourceSheet(actor());
  return resourceSheet(actor()) + card('Champion abilities', `<p class="notice">Host-reported options for ${E(actor().name || 'the selected champion')}. The host still decides when each option is legal and what it does.</p><div class="ability-option-grid">${options.map(option => `<details class="ability-option"><summary><strong>${E(option.label || option.id)}</strong><small>${E(option.kind || 'ability')} · ${E(option.phase || 'available')}</small></summary><p>${E(option.phase === 'social check' ? 'Available during a host-resolved social check.' : 'Available when the relevant host encounter or exploration state opens.')}</p></details>`).join('')}</div>`);
}
function bind() {
  document.querySelectorAll('#engine-help').forEach(n => n.ontoggle = event => { state.engineHelpOpen = event.currentTarget.open; });
  const app = document.querySelector('#app');
  const tooltipSelector = '[data-tooltip],[data-tooltip-rich]';

  const renderRichTooltip = node => {
    if (!node) return null;
    const itemNode = node.closest('[data-item], [data-gear]');
    if (itemNode) {
      const isGear = itemNode.hasAttribute('data-gear');
      const index = Number(itemNode.dataset.item ?? itemNode.dataset.gear);
      const carried = actor().equipment || [];
      const entity = isGear ? carried[index] : [...carried, ...(state.view?.inventory || [])][index];
      if (entity) {
        const name = globalThis.HSRUI?.name?.(entity) || 'Item';
        const slot = entity.slot || entity.kind || 'Relic';
        const rarity = entity.rarity || 'common';
        const sprite = globalThis.HSRUI?.resolveItemSprite ? globalThis.HSRUI.resolveItemSprite(entity) : 'fallback-prop';
        const numbers = (globalThis.HSRUI?.numbers?.(entity) || []).slice(0, 4);
        const affixes = ['prefix', 'suffix'].map(k => entity[k]?.name || entity[k]).filter(Boolean);
        const flavor = entity.flavor || entity.description;
        return `<div class="rich-tooltip-item">
          <div class="rich-tooltip-head">
            <img class="rich-tooltip-art" src="assets/sprites/items/${E(sprite)}.svg" alt="" onerror="this.style.display='none'">
            <div>
              <span class="rich-tooltip-tag">${E(slot)} · ${E(rarity)}</span>
              <strong class="rich-tooltip-title">${E(name)}</strong>
            </div>
          </div>
          ${affixes.length ? `<div class="affix-chips">${affixes.map(a => `<span>${E(a)}</span>`).join('')}</div>` : ''}
          ${numbers.length ? `<div class="rich-tooltip-stats">${numbers.map(([k, v]) => `<div class="rich-tooltip-stat"><span>${E(k)}</span><b>${E(v)}</b></div>`).join('')}</div>` : ''}
          ${flavor ? `<p class="rich-tooltip-flavor">${E(flavor)}</p>` : ''}
        </div>`;
      }
    }

    const actorNode = node.closest('[data-actor]');
    if (actorNode) {
      const entity = party().find(row => String(row.id) === actorNode.dataset.actor);
      if (entity) {
        const hp = Number(value(entity, 'hp', 'current_hp') || 0);
        const maxHp = Math.max(1, Number(value(entity, 'max_hp') || 1));
        const hpPct = Math.max(0, Math.min(100, Math.round(hp / maxHp * 100)));
        return `<div class="rich-tooltip-actor">
          <div class="rich-tooltip-head">
            <div>
              <span class="rich-tooltip-tag">${E(entity.class_name || entity.role || 'Party Member')} · Level ${E(entity.level || 1)}</span>
              <strong class="rich-tooltip-title">${E(entity.name || 'Hero')}</strong>
            </div>
          </div>
          <div class="rich-tooltip-bar"><i style="width:${hpPct}%"></i><span>HP ${hp}/${maxHp}</span></div>
        </div>`;
      }
    }

    const stageActor = node.closest('[data-stage-actor]:not([data-resident])');
    if (stageActor) {
      const id = stageActor.dataset.stageActor;
      const entity = [...party(), ...(state.view?.opposition || [])].find(row => String(row.id) === id);
      if (entity) {
        const isParty = party().some(row => String(row.id) === id);
        const hp = Number(value(entity, 'hp', 'current_hp') || 0);
        const maxHp = Math.max(1, Number(value(entity, 'max_hp') || 1));
        const hpPct = Math.max(0, Math.min(100, Math.round(hp / maxHp * 100)));
        return `<div class="rich-tooltip-combatant">
          <div class="rich-tooltip-head">
            <div>
              <span class="rich-tooltip-tag ${isParty ? 'tag-ally' : 'tag-foe'}">${isParty ? 'Ally' : 'Hostile Target'}</span>
              <strong class="rich-tooltip-title">${E(entity.name || 'Combatant')}</strong>
            </div>
          </div>
          <div class="rich-tooltip-bar"><i style="width:${hpPct}%"></i><span>HP ${hp}/${maxHp}</span></div>
        </div>`;
      }
    }

    return null;
  };

  const tooltipText = node => {
    const text = node?.dataset.tooltip || '';
    return text.trim() === node?.textContent?.trim() && !node.dataset.tooltipForce ? '' : text;
  };

  const hideTooltip = () => {
    document.querySelector('#hsr-tooltip')?.remove();
    document.querySelectorAll('[aria-describedby="hsr-tooltip"]').forEach(node => node.removeAttribute('aria-describedby'));
  };

  const showTooltip = (node, x, y) => {
    if (node?.closest('.hsr-context-menu')) return;
    const rich = node.matches('[data-tooltip-rich],[data-item],[data-gear]') ? renderRichTooltip(node) : '';
    const text = rich ? '' : tooltipText(node);
    if (!rich && !text) return;
    hideTooltip();
    const tip = document.createElement('div');
    tip.id = 'hsr-tooltip';
    tip.className = `hsr-tooltip${rich ? ' rich-tooltip' : ''}`;
    tip.setAttribute('role', 'tooltip');
    if (rich) {
      tip.innerHTML = rich;
    } else {
      tip.textContent = text;
    }
    document.body.append(tip);
    node.setAttribute('aria-describedby', tip.id);
    const rect = node.getBoundingClientRect();
    const px = Number.isFinite(x) ? x : rect.left + rect.width / 2;
    const py = Number.isFinite(y) ? y : rect.bottom;
    const box = tip.getBoundingClientRect();
    tip.style.left = `${Math.max(8, Math.min(px + 12, innerWidth - box.width - 8))}px`;
    if (rect.bottom + box.height + 14 > innerHeight && rect.top - box.height - 10 > 0) {
      tip.style.top = `${Math.max(8, rect.top - box.height - 10)}px`;
    } else {
      tip.style.top = `${Math.max(8, Math.min(py + 14, innerHeight - box.height - 8))}px`;
    }
  };

  const describeContextTarget = node => {
    if (!node) return null;
    const item = node.closest('[data-item], [data-gear]');
    if (item) {
      const isGear = item.hasAttribute('data-gear');
      const index = Number(item.dataset.item ?? item.dataset.gear);
      const carried = actor().equipment || [];
      const entity = isGear ? carried[index] : [...carried, ...(state.view?.inventory || [])][index];
      const entityId = entity?.id || item.dataset.itemId;
      const itemName = entity?.display_name || entity?.name || item.dataset.itemId || 'Item';
      const isEquipped = isGear || index < carried.length;
      const isImprint = entity?.kind === 'imprint';
      const isIdentified = entity?.identified !== false;
      const equippable = !isEquipped && ((isImprint && isIdentified) || entity?.slot);
      const unequipable = isEquipped && Boolean(state.runId) && Boolean(entity?.slot);
      const droppable = !isEquipped && Boolean(state.runId);

      const contextActions = [
        ...(equippable ? [{label: `Equip on ${actor().name || 'Lead'}`, target: {kind: 'equip', itemId: entityId, name: itemName}}] : []),
        ...(unequipable ? [{label: 'Unequip', target: {kind: 'unequip', itemId: entityId, name: itemName}}] : []),
        ...(entityId ? [{label: 'Inspect item', target: {kind: 'examine', payload: {entity_type: 'item', entity_id: entityId}}}] : []),
        ...(droppable ? [{label: 'Drop Item', target: {kind: 'drop', itemId: entityId, name: itemName}}] : []),
      ];

      return {
        label: itemName,
        description: entity?.flavor || entity?.description || entity?.tooltip || `${entity?.slot || entity?.kind || 'Item'} · ${entity?.rarity || 'common'}`,
        primaryTarget: contextActions[0]?.target || {kind: 'examine', payload: {entity_type: 'item', entity_id: entityId}},
        primaryLabel: contextActions[0]?.label || 'Examine',
        contextActions,
        examine: entityId ? {entity_type: 'item', entity_id: entityId} : null,
      };
    }

    const actorNode = node.closest('[data-actor]');
    if (actorNode) {
      const id = actorNode.dataset.actor;
      const entity = party().find(row => String(row.id) === id);
      const name = entity?.name || actorNode.querySelector('strong')?.textContent?.trim() || 'Character';
      const isSelected = state.selectedActor === id;
      const contextActions = [
        ...(!isSelected ? [{label: 'Select Character', target: {kind: 'select_actor', actorId: id}}] : []),
        {label: 'Examine Character Sheet', target: {kind: 'examine', payload: {entity_type: 'actor', entity_id: id}}},
      ];
      return {
        label: name,
        description: `${entity?.class_name || entity?.role || 'Adventurer'} · Level ${entity?.level || 1}`,
        primaryTarget: contextActions[0]?.target,
        primaryLabel: contextActions[0]?.label,
        contextActions,
        examine: id ? {entity_type: 'actor', entity_id: id} : null,
      };
    }

    const stageActor = node.closest('[data-stage-actor]:not([data-resident])');
    if (stageActor && !stageActor.dataset.resident) {
      const id = stageActor.dataset.stageActor;
      const entity = [...party(), ...(state.view?.opposition || [])].find(row => String(row.id) === id);
      const friendly = party().some(row => String(row.id) === id);
      const name = entity?.name || stageActor.getAttribute('aria-label') || 'Combatant';
      const contextActions = [
        {label: friendly ? 'Select Ally' : 'Focus Target', target: {kind: 'stage-actor', value: id}},
        {label: 'Inspect Combatant', target: {kind: 'examine', payload: {entity_type: friendly ? 'actor' : 'target', entity_id: id}}},
      ];
      return {
        label: name,
        description: friendly ? 'Party member on battlefield' : 'Hostile combatant / target',
        primaryTarget: contextActions[0].target,
        primaryLabel: contextActions[0].label,
        contextActions,
        examine: id ? {entity_type: friendly ? 'actor' : 'target', entity_id: id} : null,
      };
    }

    const conversation = node.closest('[data-conversation]');
    if (conversation) {
      const id = conversation.dataset.conversation;
      const resident = Object.values(state.view?.room?.npcs || {}).find(row => String(row.id || row.npc_id) === id);
      const name = resident?.name || conversation.textContent.trim() || 'Resident';
      const contextActions = [
        {label: `Talk with ${name}`, target: {kind: 'conversation', value: id, mode: conversation.dataset.conversationMode}},
        {label: 'Inspect Resident', target: {kind: 'examine', payload: {entity_type: 'target', entity_id: id}}},
      ];
      return {
        label: name,
        description: [resident?.role, resident?.state?.disposition || resident?.disposition, resident?.state?.reaction || resident?.reaction].filter(Boolean).join(' · '),
        primaryTarget: contextActions[0].target,
        primaryLabel: contextActions[0].label,
        contextActions,
        examine: {entity_type: 'target', entity_id: id},
      };
    }

    const residentNode = node.closest('[data-resident]');
    if (residentNode) {
      const id = residentNode.dataset.resident;
      const resident = Object.values(state.view?.room?.npcs || {}).find(row => String(row.id || row.npc_id) === id);
      const name = resident?.name || residentNode.querySelector('h3')?.textContent?.trim() || 'Resident';
      const contextActions = [
        {label: `Talk with ${name}`, target: {kind: 'action', value: `talk:${id}`}},
        {label: 'Inspect Resident', target: {kind: 'examine', payload: {entity_type: 'target', entity_id: id}}},
      ];
      return {
        label: name,
        description: [resident?.role, resident?.state?.disposition || resident?.disposition].filter(Boolean).join(' · ') || residentNode.innerText.trim().slice(0, 260),
        primaryTarget: contextActions[0].target,
        primaryLabel: contextActions[0].label,
        contextActions,
        examine: id ? {entity_type: 'target', entity_id: id} : null,
      };
    }

    const exitNode = node.closest('[data-exit]');
    if (exitNode) {
      const name = placeName(exitNode.dataset.destination);
      const contextActions = [{label: `Walk to ${name}`, target: {kind: 'hotspot', node: exitNode}}];
      return {label: name, description: 'A way out of this room.', primaryTarget: contextActions[0].target, primaryLabel: contextActions[0].label, contextActions};
    }

    const objectNode = node.closest('[data-object]');
    if (objectNode) {
      const id = objectNode.dataset.object;
      const object = findRoomObject(id) || (id === 'well' ? {id: 'well', name: 'The Town Well', description: 'The stone well leading down into the Reliquary depths.'} : null);
      const kind = String(object?.kind || '').toLowerCase();
      const contextActions = [
        {label: 'Inspect Lore', target: {kind: 'examine', payload: {entity_type: 'object', entity_id: id}}},
        ...(!object?.discovered ? [{label: 'Search', target: {kind: 'action', value: `object-search:${id}`}}] : []),
        ...((['cabinet', 'container'].includes(kind) || object?.container) && !object?.open ? [{label: 'Open', target: {kind: 'action', value: `object-open:${id}`}}] : []),
        ...(object && id !== 'well' && !object.fixed && !object.object_id && !object.kind ? [{label: 'Take', target: {kind: 'action', value: `object-take:${id}`}}] : []),
        ...(id !== 'well' ? [{label: 'Walk over', target: {kind: 'walk', node: objectNode}}] : []),
        ...(id === 'well' ? [{label: 'Descend', target: {kind: 'available-action', value: 'descend'}}] : []),
      ];
      return {
        label: objectLabel(object || {}),
        description: object?.description || object?.material || '',
        primaryTarget: contextActions[0].target,
        primaryLabel: contextActions[0].label,
        contextActions,
        examine: id ? {entity_type: 'object', entity_id: id} : null,
      };
    }

    const xpNode = node.closest('[data-xp-node]');
    if (xpNode) {
      const id = xpNode.dataset.xpNode;
      const contextActions = [
        {label: 'Travel / Engage Node', target: {kind: 'xp-node', value: id}},
      ];
      return {
        label: `Map Route: ${id}`,
        description: xpNode.getAttribute('aria-label') || 'Expedition route waypoint',
        primaryTarget: contextActions[0].target,
        primaryLabel: contextActions[0].label,
        contextActions,
      };
    }

    // Fallback: Scene / Area Context Menu
    if (state.selected === 'options' || state.phase === 'options') return null;
    if (node.closest('#screen-options, #options-interface, .game-system-modal, summary, input, select, textarea')) return null;
    const room = state.view?.room || {};
    const scene = state.view?.scene || {};
    const label = room.name || room.title || scene.phase || (state.selected === 'battle' ? 'Encounter Area' : 'Sanctum');
    const facts = [
      readable(room.description || room.atmosphere || state.view?.narration),
      ...(room.visible_tells || room.tells || []).map(readable),
      room.law ? `Law: ${readable(room.law)}` : '', room.terrain ? `Terrain: ${readable(room.terrain)}` : '',
      ...Object.entries(room.exits || {}).map(([direction, exit]) => `Exit ${direction}: ${readable(exit)}`),
    ].filter(Boolean);
    const contextActions = [
      ...(state.view?.available_actions || []).map(row => {
        const id = row.id || row.action || row.type;
        return id ? {label: row.label || FLAVOR.actions[id] || readable(id), target: {kind: 'available-action', value: id}} : null;
      }).filter(Boolean),
      {label: 'Toggle Fullscreen (F11)', target: {kind: 'fullscreen'}},
      {label: 'System Menu (Esc)', target: {kind: 'system_menu'}},
    ];

    return {
      contextKind: 'scene',
      label: readable(label),
      description: facts.join(' · ') || 'No additional room details are reported.',
      primaryTarget: contextActions[0]?.target || null,
      primaryLabel: contextActions[0]?.label || '',
      contextActions,
    };
  };

  const activate = target => {
    if (!target) return;
    if (target.kind === 'examine') {
      openExamineDialog(target.payload);
      return;
    }
    if (target.kind === 'equip') {
      work(async () => {
        result(await state.client.roomAction(state.runId, 'equip', {item: target.itemId, actor: target.actorId || actor().id || 'p0'}));
        await loadReadout(state.runId);
        state.note = `${target.name || 'Item'} equipped.`;
      });
      return;
    }
    if (target.kind === 'unequip') {
      work(async () => {
        result(await state.client.roomAction(state.runId, 'unequip', {item: target.itemId, actor: target.actorId || actor().id || 'p0'}));
        await loadReadout(state.runId);
        state.note = `${target.name || 'Item'} unequipped.`;
      });
      return;
    }
    if (target.kind === 'drop') {
      work(async () => {
        result(await state.client.roomAction(state.runId, 'drop', {item: target.itemId, actor: target.actorId || actor().id || 'p0'}));
        await loadReadout(state.runId);
        state.note = `${target.name || 'Item'} dropped.`;
      });
      return;
    }
    if (target.kind === 'select_actor') {
      state.selectedActor = target.actorId;
      render();
      return;
    }
    if (target.kind === 'navigate') {
      refreshScreen(target.screen);
      return;
    }
    if (target.kind === 'fullscreen') {
      toggleFullscreen();
      return;
    }
    if (target.kind === 'system_menu') {
      state.systemMenuOpen = true;
      render();
      return;
    }
    if (target.kind === 'action' && target.value.startsWith('talk:') && worldStage?.el.isConnected) { worldStage.talkTo(target.value.slice(5)); return; }
    if (target.kind === 'hotspot') { activateHotspot(target.node); return; }
    // Object verbs go straight to the host; a matching button may not be on screen.
    const objectVerb = target.kind === 'action' && /^object-(inspect|search|open|take):/.exec(target.value);
    if (objectVerb) { objectAction(objectVerb[1], target.value.slice(target.value.indexOf(':') + 1)); return; }
    if (target.kind === 'walk') { walkLeadTo(hotspotX(target.node)); return; }
    if (target.kind === 'xp-node') {
      document.querySelector(`[data-xp-node="${CSS.escape(target.value)}"]`)?.dispatchEvent(new MouseEvent('click', {bubbles: true}));
      return;
    }

    let selector = '';
    if (target.kind === 'item') selector = `[data-item="${CSS.escape(target.value)}"]`;
    if (target.kind === 'actor') selector = `[data-actor="${CSS.escape(target.value)}"]`;
    if (target.kind === 'stage-actor') selector = `[data-stage-actor="${CSS.escape(target.value)}"]`;
    if (target.kind === 'conversation') selector = `[data-conversation="${CSS.escape(target.value)}"]${target.mode ? `[data-conversation-mode="${CSS.escape(target.mode)}"]` : ''}`;
    if (target.kind === 'action') selector = `[data-action="${CSS.escape(target.value)}"]`;
    if (target.kind === 'available-action') {
      const aliases = {descend: '[data-action="descend-now"]', idle_tick: '[data-action="idle-tick"]', auto_travel: '[data-action="auto-travel"]'};
      selector = aliases[target.value] || `[data-engine-action="${CSS.escape(target.value)}"]`;
    }
    document.querySelector(selector)?.click();
  };

  const contextTarget = node => {
    return describeContextTarget(node);
  };

  if (app) app.oncontextmenu = event => {
    if (state.preferences.swapMouseButtons && !event.hsrContextOnly && (event.isTrusted || event.hsrNativeSecondary) && !event.target.closest('.hsr-context-menu')) {
      event.preventDefault();
      const target = contextTarget(event.target);
      if (target?.primaryTarget) requestAnimationFrame(() => activate(target.primaryTarget));
      return;
    }
    // Mouse combat: right-click a foe opens the action wheel; right-click the
    // ground clears the focus and any open radial/context menu.
    if (styleAllows(style(), 'mouse') && tacticalActive() && event.target.closest('#app .combat-stage:not(.demo-stage)')) {
      const figure = event.target.closest('[data-stage-actor]');
      const id = figure?.dataset.stageActor;
      if (id && livingOpponents().some(row => row.id === id)) { event.preventDefault(); openCombatRadial(id, event.clientX, event.clientY); return; }
      if (!figure) { event.preventDefault(); state.focusTarget = null; state.combatRadial = null; state.threatWarning = null; dismissContextMenu(); render(); return; }
    }
    if (state.combatRadial && !event.target.closest('.combat-radial')) { state.combatRadial = null; render(); }
    event.preventDefault();
    if (event.target.closest('.hsr-context-menu')) { dismissContextMenu(); return; }
    const target = contextTarget(event.target) || {label: 'Workspace', contextKind: 'scene'};
    const primary = target.contextKind !== 'scene' ? target.contextActions?.find(row => !['examine', 'fullscreen', 'system_menu'].includes(row.target?.kind)) : null;
    const examine = target.examine ? {label: 'Examine', target: {kind: 'examine', payload: target.examine}} : null;
    state.contextMenu = {x: event.clientX, y: event.clientY, ...target,
      contextActions: [primary, examine, {label: 'Menu', target: {kind: 'system_menu'}}, {label: 'Fullscreen', target: {kind: 'fullscreen'}}].filter(Boolean)};
    document.querySelector('.hsr-context-menu')?.remove();
    app.insertAdjacentHTML('beforeend', contextMenu());
    const menu = document.querySelector('.hsr-context-menu');
    menu.addEventListener('click', e => {
      const button = e.target.closest('[data-action]'); if (!button) return;
      e.preventDefault(); e.stopPropagation();
      const index = Number(button.dataset.action.split(':').at(-1));
      const selected = state.contextMenu?.contextActions?.[index]?.target;
      dismissContextMenu(); activate(selected);
    });
    placeContextMenu(state.contextMenu);
    menu.querySelector('button')?.focus({preventScroll: true});
  };

  if (app && !app.dataset.secondaryInteractions) {
    app.dataset.secondaryInteractions = 'native-clicks';
  }
  if (app && !app.dataset.contextDismiss) {
    app.dataset.contextDismiss = 'true';
    app.addEventListener('click', event => {
      if (state.preferences.swapMouseButtons && event.button === 0 && !event.target.closest('.world-stage') && !event.target.closest('.hsr-context-menu, .system-btn, button, a, [role="button"], input, select, summary')) {
        const target = contextTarget(event.target);
        if (target) {
          event.preventDefault();
          event.stopPropagation();
          app.oncontextmenu(new MouseEvent('contextmenu', {bubbles: true, cancelable: true, clientX: event.clientX, clientY: event.clientY}));
          return;
        }
      }
      if (state.contextMenu && !event.target.closest('.hsr-context-menu')) dismissContextMenu();
      // A click away from the action wheel only closes it.
      if (state.combatRadial && !event.target.closest('.combat-radial')) {
        state.combatRadial = null; event.preventDefault(); event.stopPropagation(); render();
      }
    }, true);
    app.addEventListener('pointerover', event => {
      if (event.pointerType === 'touch') return;
      const node = event.target.closest(tooltipSelector);
      if (node && !node.contains(event.relatedTarget)) showTooltip(node, event.clientX, event.clientY);
    });
    app.addEventListener('pointerout', event => {
      if (event.pointerType !== 'touch' && event.target.closest(tooltipSelector) && !event.target.closest(tooltipSelector).contains(event.relatedTarget)) hideTooltip();
    });
    app.addEventListener('focusin', event => { const node = event.target.closest(tooltipSelector); if (node) showTooltip(node); else hideTooltip(); });
    app.addEventListener('focusout', event => { if (event.target.closest(tooltipSelector)) hideTooltip(); });
    app.addEventListener('pointerdown', event => {
      if (event.pointerType !== 'touch') return;
      const node = event.target.closest('button,a,input,select,summary,[role="button"],[tabindex]');
      const text = tooltipText(node);
      const rich = node?.matches('[data-tooltip-rich]') && renderRichTooltip(node);
      if (!node || (!text && !rich)) { state.tapHint = null; state.touchReveal = null; return; }
      if (state.tapHint !== node) {
        state.tapHint = node; state.touchReveal = node; state.touchActivate = null; showTooltip(node);
      } else {
        state.tapHint = null; state.touchReveal = null; state.touchActivate = node; hideTooltip();
        window.setTimeout(() => { if (state.touchActivate === node) { state.touchActivate = null; node.click(); } }, 120);
      }
    }, true);
    app.addEventListener('click', event => {
      const node = event.target.closest('button,a,input,select,summary,[role="button"],[tabindex]');
      if (state.touchReveal === node) {
        state.touchReveal = null; event.preventDefault(); event.stopImmediatePropagation();
        return;
      }
      if (state.touchActivate === node) { state.touchActivate = null; return; }
    }, true);
  }
  window.onkeydown = event => {
    if (event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10')) { event.preventDefault(); openContextAt(document.activeElement || app); return; }
    if (event.defaultPrevented) return;
    const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);
    if (typing && !['Escape', 'F11'].includes(event.key)) return;
    if (event.key === 'F11') {
      event.preventDefault();
      toggleFullscreen();
      return;
    }
    if (event.key === 'i' || event.key === 'I' || event.key === 'b' || event.key === 'B') {
      state.bookbagOpen = !state.bookbagOpen;
      render();
      return;
    }
    if (event.key === 'c' || event.key === 'C' || event.key === 'p' || event.key === 'P') {
      selectGameplayScreen('roster');
      render();
      return;
    }
    if (event.key === ' ' || event.code === 'Space') {
      event.preventDefault();
      const endBtn = document.querySelector('[data-engine-action="end_turn"]');
      if (endBtn && !endBtn.disabled) { endBtn.click(); return; }
      const firstAction = document.querySelector('.engine-action:not(:disabled)');
      if (firstAction) { firstAction.click(); return; }
    }
    if (event.key >= '1' && event.key <= '9') {
      // Read the hotkey the render assigned (data-hotkey) rather than
      // re-deriving DOM order, so this can't desync from the badge shown.
      const node = document.querySelector(`[data-hotkey="${event.key}"]:not(:disabled)`);
      if (node) {
        event.preventDefault();
        node.click();
        return;
      }
    }
    if (event.key === 'Escape') {
      if (state.activeDialogueNpc) { state.activeDialogueNpc = null; render(); return; }
      if (state.equipmentSelectedItem) { state.equipmentSelectedItem = null; render(); return; }
      if (state.systemMenuOpen) { state.systemMenuOpen = false; render(); return; }
      if (state.bookbagOpen) { state.bookbagOpen = false; render(); return; }
      if (state.contextMenu || document.querySelector('#hsr-tooltip')) { dismissContextMenu(); hideTooltip(); return; }
      const openDialog = document.querySelector('dialog[open]');
      if (openDialog) { openDialog.close(); return; }
      // Escape in a text field only leaves the field; the System menu needs a second press.
      if (typing) { document.activeElement.blur(); return; }
      if (state.phase === 'ready') { state.systemMenuOpen = true; render(); return; }
    }
  };
  window.oncontextmenu = event => {
    if (event.target.closest('.hsr-context-menu')) return;
    event.preventDefault();
  };
  bindBookbagControls();
  document.querySelectorAll('.options-index a').forEach(link => link.onclick = event => {
    event.preventDefault();
    const target = document.querySelector(link.getAttribute('href'));
    if (target?.tagName === 'DETAILS') target.open = true;
    target?.scrollIntoView({behavior: state.preferences.motion === 'reduced' ? 'auto' : 'smooth', block: 'start'});
    history.replaceState(navigationState(), '', `${location.pathname}${location.search}${link.getAttribute('href')}`);
  });
  document.querySelectorAll('[data-skill-pick]').forEach(node => {
    let holdTimer = 0;
    const toggleExpanded = event => {
      event?.preventDefault();
      const expanded = !node.classList.contains('is-expanded');
      node.classList.toggle('is-expanded', expanded);
      node.setAttribute('aria-expanded', String(expanded));
    };
    node.ondblclick = event => { event.preventDefault(); event.stopPropagation(); toggleExpanded(event); };
    node.onpointerdown = event => {
      if (event.pointerType === 'touch') holdTimer = window.setTimeout(() => toggleExpanded(event), 520);
    };
    node.onpointerup = node.onpointercancel = node.onpointerleave = () => { if (holdTimer) { clearTimeout(holdTimer); holdTimer = 0; } };
  });
  document.querySelectorAll('[data-actor]').forEach(node => {
    node.onclick = () => { state.selectedActor = node.dataset.actor; render(); };
    node.ondblclick = event => {
      event.preventDefault();
      openExamineDialog({entity_type: 'actor', entity_id: node.dataset.actor});
    };
  });
  document.querySelectorAll('[data-stage-actor]').forEach(node => {
    node.ondblclick = event => {
      event.preventDefault();
      const id = node.dataset.stageActor;
      const isParty = party().some(row => String(row.id) === id);
      openExamineDialog({entity_type: isParty ? 'actor' : 'target', entity_id: id});
    };
  });
  document.querySelectorAll('[data-object]').forEach(node => {
    node.onclick = event => {
      if (event.target.closest('button,[data-action]')) return;
      event.preventDefault();
      const id = node.dataset.object;
      openExamineDialog({entity_type: 'object', entity_id: id});
    };
  });
  document.querySelectorAll('[data-flight-type]').forEach(node => node.onclick = () => work(async () => {
    const type = node.dataset.flightType;
    const action = {type, actor: state.view?.flight_arena?.controller || actor().id || 'p0'};
    if (type === 'flight_move') { action.dx = Number(node.dataset.flightDx); action.dy = Number(node.dataset.flightDy); }
    result(await state.client.designAction(state.runId, action));
    await loadReadout(state.runId);
    state.note = 'Flight intent resolved by the host.';
  }));
  document.querySelectorAll('[data-item-filter]').forEach(node => node.onclick = () => {
    state.equipmentFilter = node.dataset.itemFilter;
    render();
  });
  function openItemModal(item) {
    if (!item) return;
    const carried = actor().equipment || [];
    const allItems = [...carried, ...(state.view?.inventory || [])];
    const itemIndex = allItems.findIndex(i => (i.id && i.id === item.id) || (i.name && i.name === item.name));
    const isEquipped = itemIndex >= 0 && itemIndex < carried.length;
    const isInventory = itemIndex >= carried.length;
    const isImprint = item.kind === 'imprint';
    const isIdentified = item.identified === true;
    const equippable = isInventory && ((isImprint && isIdentified) || item.slot);
    const unequipable = isEquipped && Boolean(state.runId) && Boolean(item.slot);
    const droppable = isInventory && Boolean(state.runId);
    const reforgeable = equippable && isImprint;
    const activeAffixes = (state.affixes?.active || []).filter(row => row.options?.attachable);
    const dialog = document.querySelector('#item-dialog');
    if (!dialog) return;

    let actionsHtml = '<div class="actions item-dialog-actions">';
    if (equippable) {
      actionsHtml += `<button type="button" class="action primary" data-equip-item="${E(item.id || item.name)}">Equip</button>`;
    }
    if (unequipable) {
      actionsHtml += `<button type="button" class="action secondary" data-unequip-item="${E(item.id || item.name)}">Unequip</button>`;
    }
    if (droppable) {
      actionsHtml += `<button type="button" class="action secondary" data-drop-item="${E(item.id || item.name)}">Drop</button>`;
    }
    actionsHtml += `<button type="button" class="action secondary" data-close-item-dialog>Close</button>`;
    actionsHtml += '</div>';

    dialog.innerHTML = `${globalThis.HSRUI.detail(item, 'assets/')}${actionsHtml}${reforgeable ? `<section class="receipt-details"><p class="label">Reforge active affix · 1 Gem</p><div class="actions">${activeAffixes.map(affix => `<button type="button" class="action secondary" data-reforge-affix="${E(affix.name)}" title="Replace this item’s ${E(affix.affix_type)} with ${E(affix.name)}">${E(affix.name)}</button>`).join('') || '<small>No active affixes loaded.</small>'}</div></section>` : ''}`;

    dialog.querySelector('[data-close-item-dialog]')?.addEventListener('click', () => {
      dialog.close();
    });
    dialog.querySelector('[data-equip-item]')?.addEventListener('click', () => {
      dialog.close();
      work(async () => {
        result(await state.client.roomAction(state.runId, 'equip', {item: item.id || item.name, actor: actor().id || 'p0'}));
        await loadReadout(state.runId);
        state.note = `${item.name || 'Item'} equipped.`;
      });
    });
    dialog.querySelector('[data-unequip-item]')?.addEventListener('click', () => {
      dialog.close();
      work(async () => {
        result(await state.client.roomAction(state.runId, 'unequip', {item: item.id || item.name, actor: actor().id || 'p0'}));
        await loadReadout(state.runId);
        state.note = `${item.name || 'Item'} unequipped.`;
      });
    });
    dialog.querySelector('[data-drop-item]')?.addEventListener('click', () => {
      dialog.close();
      work(async () => {
        result(await state.client.roomAction(state.runId, 'drop', {item: item.id || item.name, actor: actor().id || 'p0'}));
        await loadReadout(state.runId);
        state.note = `${item.name || 'Item'} dropped.`;
      });
    });
    dialog.querySelectorAll('[data-reforge-affix]').forEach(control => control.addEventListener('click', () => {
      const affix = control.dataset.reforgeAffix;
      work(async () => {
        result(await state.client.roomAction(state.runId, 'reforge_affix', {item: item.id, affix, actor: actor().id || 'p0'}));
        await loadReadout(state.runId);
        state.note = `${affix} bound to the Rune.`;
        dialog.close();
      });
    }));
    dialog.showModal();
  }

  document.querySelectorAll('[data-item]').forEach(node => {
    node.ondblclick = event => {
      event.preventDefault();
      const carried = actor().equipment || [];
      const allItems = [...carried, ...(state.view?.inventory || [])];
      const itemIndex = Number(node.dataset.item);
      const item = allItems[itemIndex] || allItems.find(i => String(i.id || i.name) === node.dataset.itemId);
      if (item) openItemModal(item);
    };
    node.onclick = () => {
      const carried = actor().equipment || [];
      const allItems = [...carried, ...(state.view?.inventory || [])];
      const itemIndex = Number(node.dataset.item);
      const item = allItems[itemIndex] || allItems.find(i => String(i.id || i.name) === node.dataset.itemId);
      if (!item) return;
      openItemModal(item);
    };
  });
  document.querySelectorAll('[data-action]').forEach(node => node.onclick = async () => {
    const action = node.dataset.action;
    if (action === 'champion-rehearsal') { await beginChampionRehearsal(); return; }
    if (action.startsWith('set-action-mode:')) {
      state.preferences.actionMode = action.slice('set-action-mode:'.length);
      savePreferences();
      render();
      return;
    }
    if (action.startsWith('talk-cinematic:')) {
      state.activeDialogueNpc = action.slice('talk-cinematic:'.length);
      render();
      return;
    }
    if (action === 'close-cinematic-dialogue') {
      state.activeDialogueNpc = null;
      render();
      return;
    }
    if (action === 'clear-item-selection') {
      state.equipmentSelectedItem = null;
      render();
      return;
    }
    if (action.startsWith('inspect-item-modal:')) {
      const itemId = action.slice('inspect-item-modal:'.length);
      const allItems = [...(actor().equipment || []), ...(state.view?.inventory || [])];
      const item = allItems.find(i => String(i.id || i.name) === itemId) || state.equipmentSelectedItem;
      if (item) openItemModal(item);
      return;
    }
    if (action.startsWith('equip-item-id:')) {
      const itemId = action.slice('equip-item-id:'.length);
      await work(async () => {
        result(await state.client.roomAction(state.runId, 'equip', {item: itemId, actor: actor().id || 'p0'}));
        await loadReadout(state.runId);
        state.note = `Item equipped on ${actor().name || 'Lead'}.`;
        addMessage(state.note);
      });
      return;
    }
    if (action.startsWith('unequip-item:')) {
      const slotOrName = action.slice('unequip-item:'.length);
      await work(async () => {
        result(await state.client.roomAction(state.runId, 'unequip', {item: slotOrName, actor: actor().id || 'p0'}));
        await loadReadout(state.runId);
        state.note = `Item unequipped from ${actor().name || 'Lead'}.`;
        addMessage(state.note);
      });
      return;
    }
    if (action.startsWith('use-potion:')) {
      const itemId = action.slice('use-potion:'.length);
      await work(async () => {
        result(await state.client.designAction(state.runId, {type: 'consume', item: itemId, actor: actor().id || 'p0'}));
        await loadReadout(state.runId);
        state.note = 'Potion used.';
        addMessage(state.note);
      });
      return;
    }
    if (action === 'xp-start' || action === 'xp-resolve') {
      await work(async () => {
        result(await state.client.request(action === 'xp-start' ? 'expedition_start' : 'expedition_resolve', {run_id: state.runId}));
        state.note = action === 'xp-start' ? 'Route charted. Pick the first node.' : 'Gambits settled the room.';
        selectGameplayScreen('battle');
      });
      return;
    }
    if (action === 'gambit-add' || action === 'gambit-save') {
      const id = document.querySelector('[data-gambit-list]')?.dataset.gambitList;
      if (!id) return;
      const rows = readGambitRows();
      if (action === 'gambit-add') {
        state.gambitDraft = {...(state.gambitDraft || {}), [id]: [...rows, {when: 'always', value: '', then: 'attack', target: 'nearest_enemy'}]};
        render();
        return;
      }
      await work(async () => {
        const macros = {...Object.fromEntries(Object.entries(state.view?.auto?.macros || {})), [id]: gambitMacros(rows)};
        result(await state.client.configureMacros(state.runId, macros));
        await loadReadout(state.runId);
        state.gambitDraft = {...(state.gambitDraft || {}), [id]: undefined};
        state.note = `Gambits saved for ${party().find(m => m.id === id)?.name || id}.`;
        addMessage(state.note);
      });
      return;
    }
    if (action === 'auto-travel') {
      if (!floorOneWorld()) { selectGameplayScreen('room'); render(); return; }
      await work(async () => {
        const reply = await state.client.autoTravel(state.runId, 'well', 4, false);
        const payload = result(reply).result.travel;
        state.view = payload.public_view;
        state.receipt = payload.public_receipt;
        selectGameplayScreen('journey');
        state.note = payload.event?.reached ? 'Travel reached the descent route. Choose Descend to enter the Reliquary.' : 'Host travel advanced the public route.';
        render();
      });
      return;
    }
    if (action === 'descend-now') {
      // A resident stationed at the well stays visible on every visit, which
      // permanently masks the host's own idle-pause "descent_decision" code.
      // This calls the host's descend action directly rather than waiting on
      // that notice, matching what `available_actions` already promises.
      await work(async () => {
        result(await state.client.designAction(state.runId, {type: 'descend'}));
        await loadReadout(state.runId);
        state.note = 'Descending into the Reliquary.';
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
    if (action === 'voice-demo') { voiceFeed.demo(); return; }
    if (action === 'help-print') { state.engineHelpOpen = false; printActionGuide(); render(); return; }
    if (action.startsWith('decant-item:')) {
      const item = action.slice('decant-item:'.length);
      await work(async () => {
        result(await state.client.decant(state.runId, item, actor().id || 'p0'));
        await loadReadout(state.runId);
        const event = state.receipt || {};
        state.note = `Decanted into ${actor().name || 'the party'}'s Attunement Matrix.`;
        addMessage(state.note);
        debugLog('info', 'ATTUNE', 'decant', event);
      });
      return;
    }
    if (action.startsWith('release-attunement:')) {
      const [, who, lane, ...rest] = action.split(':');
      await work(async () => {
        result(await state.client.releaseAttunement(state.runId, who, lane, rest.join(':')));
        await loadReadout(state.runId);
        state.note = `${rest.join(':')} released from the ${lane} lane.`;
        addMessage(state.note);
      });
      return;
    }
    if (action === 'toggle-console-compact') { state.consoleCompact = !state.consoleCompact; render(); return; }
    if (action === 'toggle-location') { state.locationOpen = !state.locationOpen; render(); return; }
    if (action === 'toggle-messages') { state.messageHistoryOpen = !state.messageHistoryOpen; render(); return; }
    if (action === 'close-messages') { state.messageHistoryOpen = false; render(); return; }
    if (action === 'clear-messages') { state.messageHistory = []; render(); return; }
    if (action.startsWith('messages-tab:')) { state.messagePanelTab = action.slice('messages-tab:'.length); render(); return; }
    if (action === 'debug-copy') { await copyDebugReport(state.debugFilter === 'all'); render(); return; }
    if (action === 'debug-download') { downloadDebugReport(); return; }
    if (action === 'debug-filter') { state.debugFilter = state.debugFilter === 'all' ? 'issues' : 'all'; render(); return; }
    if (action === 'debug-clear') { DEBUG_LOG.length = 0; render(); return; }
    if (action === 'toggle-arrange') { state.arrangeMode = !state.arrangeMode; state.contextMenu = null; render(); return; }
    if (action === 'toggle-hud') { state.preferences.hudCollapsed = !state.preferences.hudCollapsed; savePreferences(); render(); return; }
    if (action === 'toggle-play-header') { state.playHeaderOpen = !state.playHeaderOpen; render(); return; }
    if (action === 'toggle-system-menu') { state.systemMenuOpen = !state.systemMenuOpen; state.contextMenu = null; render(); return; }
    if (action === 'close-system-menu') { state.systemMenuOpen = false; render(); return; }
    if (action === 'toggle-fullscreen') { toggleFullscreen(); state.systemMenuOpen = false; render(); return; }
    if (action === 'conn-toggle') { state.link.open = !state.link.open; render(); return; }
    if (action === 'close-context-menu') { state.contextMenu = null; render(); return; }
    if (action === 'context-primary' || action.startsWith('context-primary:')) {
      const index = action.includes(':') ? Number(action.split(':').at(-1)) : -1;
      const target = index >= 0 ? state.contextMenu?.contextActions?.[index]?.target : state.contextMenu?.primaryTarget;
      state.contextMenu = null; render();
      requestAnimationFrame(() => activate(target));
      return;
    }
    if (action === 'return-game') { state.contextMenu = null; refreshScreen(state.optionsReturnScreen || 'room'); return; }
    if (action === 'back-options') {
      state.contextMenu = null;
      if (state.phase === 'ready') refreshScreen(state.optionsReturnScreen || 'room'); else { back(); render(); }
      return;
    }
    if (action === 'conn-ping' || action === 'conn-retry') {
      state.dismissedDisconnect = false;
      await heartbeat();
      render();
      return;
    }
    if (action === 'dismiss-disconnect') {
      state.dismissedDisconnect = true;
      render();
      return;
    }
    if (action === 'resolve-stale-sandbox') { await resolveStaleSandbox(); return; }
    if (action === 'title') { state.systemMenuOpen = false; clearScreenTransientState(); state.route = ['title']; state.phase = 'title'; history.replaceState(navigationState(), '', `${location.pathname}${location.search}`); render(); }
    else if (action === 'back') { back(); render(); }
    else if (action.startsWith('breadcrumb:')) {
      const phase = action.slice('breadcrumb:'.length);
      clearScreenTransientState();
      state.route = phase === 'title' ? ['title'] : ['title', phase];
      state.phase = phase;
      if (phase === 'menu-story') state.pendingMode = 'FORGE';
      if (phase === 'menu-simulation') state.pendingMode = 'SANDBOX';
      history.replaceState(navigationState(), '', phase === 'title' ? `${location.pathname}${location.search}` : location.href);
      render();
    }
    else if (action.startsWith('menu:')) {
      const phase = action.slice(5);
      if (phase === 'options' && state.phase === 'ready') { refreshScreen('options'); return; }
      if (phase === 'statistics') {
        state.statisticsMode = state.phase === 'menu-simulation' ? 'SANDBOX'
          : state.phase === 'menu-story' ? 'FORGE'
          : String(state.view?.mode || state.pendingMode || 'FORGE').toUpperCase();
        if (!['FORGE', 'SANDBOX'].includes(state.statisticsMode)) state.statisticsMode = 'FORGE';
        state.statistics = null; state.statisticsDetail = null; state.statisticsView = 'menu';
      }
      go(phase); render();
      if (['archive', 'menu-story', 'meta-shop', 'codex', 'cheats', 'ladder'].includes(phase)) {
        await loadStar();
        if (phase === 'ladder' || phase === 'cheats') await loadLadders();
        if (phase === 'codex' || phase === 'cheats') await loadStory();
        if (phase === 'meta-shop' && metaShopUnlocked()) await loadMetaShop();
        if (state.phase === phase) render();
      }
      // Both screens name the chosen scenario, so the catalog is fetched on the
      // way into Simulation Mode rather than only inside the picker.
      if ((phase === 'edit-scenario' || phase === 'menu-simulation') && state.scenarios === null) { await loadScenarios(); render(); }
    }
    else if (action === 'create') { if (state.pendingMode === 'FORGE') state.draft.level = 1; go('create'); render(); await ensureCreationSeed(); render(); scheduleLivePreview(0); }
    else if (action === 'restart') { resetCreationDraft(); go('create'); render(); await ensureCreationSeed(); render(); scheduleLivePreview(0); }
    else if (state.phase === 'create' && await creatorAction(action)) { /* handled by the paged creator */ }
    else if (action === 'engine' || action === 'start-engine') await connect('engine-host', 'title');
    else if (action.startsWith('cutscene:')) { await playScene(action.slice(9)); render(); }
    else if (action.startsWith('dialogue:')) { await talkTo(action.slice(9)); render(); }
    else if (action.startsWith('unlock:')) {
      const [, champion, ...rest] = action.split(':');
      await work(async () => { const reply = await state.client.request('unlock_pick', {champion, key: rest.join(':')}); if (!reply.ok) throw Error(reply.error?.message || 'Unlock failed'); await loadLadders(); });
    }
    else if (action.startsWith('ladder-debug:')) {
      const [, champion, level] = action.split(':');
      await work(async () => { const reply = await state.client.request('unlock_debug', {champion, level: Number(level)}); if (!reply.ok) throw Error(reply.error?.message); await loadLadders(); });
    }
    else if (action.startsWith('story-debug:')) {
      const op = action.slice(12);
      await work(async () => {
        if (op !== 'load') {
          const s = state.star || await loadStar() || {};
          const payload = op === 'runs' || op === 'completions' ? {op, value: (s[op] || 0) + 1}
            : op === 'reveal' ? {op: 'set_flag', value: 'star_revealed'} : op === 'forget' ? {op: 'forget_cutscenes'} : {op: 'reset'};
          const reply = await state.client.request('star_debug', payload);
          if (!reply.ok) throw Error(reply.error?.message || 'Star debug failed');
          state.star = reply.result?.star;
        }
        await loadStar(); await loadStory();
      });
    }
    else if (action.startsWith('mode:')) {
      state.pendingMode = action.slice(5);
      if (state.connected) { go('party-select'); render(); }
      else await connect('engine-host', 'party-select');
      // The first Story descent opens on the Star's birth; after that it lives in the archive.
      if (state.pendingMode === 'FORGE' && state.connected && !(state.star?.seen_cutscenes || []).includes('opening')) {
        await loadStar();
        if (state.star && !state.star.seen_cutscenes.includes('opening')) { await playScene('opening', {auto: true}); render(); }
      }
    }
    else if (action === 'champion-select') { go('champion-select'); render(); }
    else if (action.startsWith('champion:')) {
      const champ = action.slice(9);
      if (state.pendingMode === 'FORGE') {
        state.pendingLead = {kind: 'champion', name: champ};
        go('entry-select');
        render();
      } else {
        await beginChampionRun(champ);
      }
    }
    else if (action.startsWith('start-story:')) {
      const location = action.slice(12);
      const lead = state.pendingLead;
      if (!lead) { go('party-select'); render(); return; }
      if (lead.kind === 'champion') {
        await beginChampionRun(lead.name, location);
      } else if (lead.kind === 'custom') {
        await beginCustomRun(lead.profileId, location);
      }
    }
    else if (action === 'back-to-lead') {
      if (state.pendingLead?.kind === 'champion') go('champion-select');
      else if (state.pendingLead?.kind === 'custom') {
        state.draft.create_step = CREATE_STEPS.length - 1;
        go('create');
      } else go('party-select');
      render();
    }
    else if (action === 'cancel-conversation') { state.pendingConversation = null; state.consoleDraft = ''; render(); }
    else if (action === 'load-progression') await work(async () => { const reply = await state.client.progression(state.accountIdentity); if (!reply.ok) throw Error(reply.error?.message); state.progression = reply.result?.progression || null; });
    else if (/^object-(inspect|search|open|take):/.test(action)) await objectAction(action.slice(7, action.indexOf(':')), action.slice(action.indexOf(':') + 1));
    else if (action === 'load-terminal-receipt') await work(async () => { const reply = await state.client.terminalReceipt(state.runId); if (!reply.ok) throw Error(reply.error?.message); state.terminal = reply.result?.terminal_receipt || null; });
    else if (action === 'load-debug-state') await work(async () => {
      const reply = await state.client.request('sandbox_debug', {run_id: state.runId});
      if (!reply.ok) throw Error(reply.error?.message || 'Debug state unavailable');
      state.debugReadout = reply.result?.debug_readout || null;
    });
    else if (action === 'randomize-race' || action === 'randomize-class') {
      // A different pick every press (never the current one when there is a choice).
      const key = action === 'randomize-race' ? 'race' : 'character_class';
      const rows = (state.options?.[action === 'randomize-race' ? 'races' : 'classes'] || []).filter(row => row && row.id);
      const pool = rows.length > 1 ? rows.filter(row => row.id !== state.draft[key]) : rows;
      if (pool.length) {
        state.draft[key] = pool[Math.floor(Math.random() * pool.length)].id;
        if (key === 'race' && state.draft.name_auto) state.draft.name = seededName(state.draft.creation_seed || randomSeed(), state.draft.race);
        persistUiState(); render(); scheduleLivePreview(0);
      }
    }
    else if (action === 'randomize-stats') await work(async () => { const seed = randomSeed(); state.draft.creation_seed = seed; state.draft.seed_auto = false; if (state.draft.name_auto) state.draft.name = seededName(seed, state.draft.race); const reply = result(await state.client.characterRoll(seed, 0)); state.roll = reply.result?.ability_roll || null; state.draft.roll_set = 0; state.draft.ability_assignment = 'auto'; persistUiState(); }, 'Rolling fresh stats');
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
      result(await state.client.boot(filterMode));
      state.runs = await loadFilteredRuns(filterMode);
      state.runsFilter = filterMode;
      go('runs');
    });
    else if (action === 'refresh-runs') await work(async () => { state.runs = await loadFilteredRuns(state.runsFilter); });
    else if (action.startsWith('load:')) await work(async () => {
      const id = action.slice(5);
      resetRunStateForLoad();
      const inspected = await state.client.request('inspect_run', {run_id: id});
      if (!inspected.ok) throw Error(inspected.error?.message || 'Saved run could not be inspected');
      const mode = String(inspected.result?.run?.context?.host_mode || inspected.result?.run?.mode || 'DESIGN').toUpperCase();
      if (['DESIGN', 'SANDBOX', 'FORGE', 'REVIEW'].includes(mode)) result(await state.client.boot(mode));
      result(await state.client.loadRun(id)); await loadReadout(id);
    });
    else if (action === 'load-statistics-last') await work(async () => {
      await loadStatistics(state.statisticsMode, null, 'last');
    });
    else if (action === 'load-statistics-list') await work(async () => {
      await loadStatistics(state.statisticsMode, null, 'list');
    });
    else if (action === 'load-statistics-all') await work(async () => {
      await loadStatistics(state.statisticsMode, null, 'all');
    });
    else if (action.startsWith('statistics-save:')) await work(async () => {
      const id = action.slice('statistics-save:'.length);
      await loadStatistics(state.statisticsMode, id, state.statisticsView === 'all' ? 'all' : 'list');
    });
    else if (action === 'reset-preferences') { state.preferences = defaultPreferenceSet(); savePreferences(); scheduleHeartbeat(); render(); }
    else if (action.startsWith('reset-pref-group:')) { const group = action.slice(17); state.preferences[group] = {...NESTED_PREFERENCES[group]}; savePreferences(); scheduleHeartbeat(); render(); }
    else if (action === 'combat-demo') playCombatDemo();
    else if (action === 'seed-override-random' || action === 'seed-override-clear') {
      state.preferences.scenarioSeed = action === 'seed-override-random' ? randomSeed() : '';
      savePreferences();
      state.note = state.preferences.scenarioSeed ? `New runs will use the seed ${state.preferences.scenarioSeed} until you clear it.` : 'Every new run gets a fresh random seed.';
      render();
    }
    else if (action.startsWith('play-again:')) { const [, how, ...rest] = action.split(':'); await playAgain(rest.join(':'), how === 'same'); }
    else if (action === 'combat-inspector-clear') combatDirector.clearHistory();
    else if (action === 'combat-inspector-close') { state.preferences.combat.inspector = false; savePreferences(); render(); }
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
      state.note = 'Run saved. You can keep playing or return to the main menu.';
    });
    else if (action === 'return-menu') { clearScreenTransientState(); state.route = ['title']; state.phase = 'title'; state.note = ''; render(); }
    else if (action.startsWith('tab:')) { refreshScreen(action.slice(4)); }
    else if (action.startsWith('talk:') && DIALOGUES[`npc:${slug(action.slice(5))}`]) {
      await talkTo(`npc:${slug(action.slice(5))}`); render();
    }
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
      : 'Every new run gets a fresh random seed.';
    render();
  };
  document.querySelectorAll('[data-pref-path]').forEach(node => {
    const [group, key] = node.dataset.prefPath.split('.');
    const read = () => node.dataset.kind === 'bool' ? node.checked : node.dataset.kind === 'number' ? Number(node.value) : node.value;
    // Sliders update their readout live but only save/re-render on release.
    node.oninput = () => { const out = document.querySelector(`[data-pref-out="${node.dataset.prefPath}"]`); if (out) out.textContent = formatPref(node.dataset.prefPath, read()); };
    node.onchange = () => {
      state.preferences[group] = {...state.preferences[group], [key]: read()};
      savePreferences();
      if (group === 'link') scheduleHeartbeat();
      render();
    };
  });
  document.querySelectorAll('[data-pref-group]').forEach(node => node.onchange = () => {
    const group = state.preferences[node.dataset.prefGroup]; const key = node.dataset.prefKey;
    group[key] = node.type === 'checkbox' ? node.checked : node.type === 'range' ? Number(node.value) : node.value;
    savePreferences(); applyPreferences(); render();
  });
  document.querySelector('[data-story-flag-form]')?.addEventListener('submit', event => {
    event.preventDefault();
    const flag = new FormData(event.target).get('flag');
    work(async () => { const reply = await state.client.request('story_flag', {flag, value: true}); if (!reply.ok) throw Error(reply.error?.message); state.story = reply.result?.story; });
  });
  document.querySelectorAll('[data-pref]').forEach(node => node.onchange = () => {
    const key = node.dataset.pref;
    if (key === 'iconActions') state.preferences.iconActions = node.checked;
    else if (key === 'swapMouseButtons') state.preferences.swapMouseButtons = node.checked;
    else if (key === 'motion') state.preferences.motion = node.checked ? 'reduced' : 'full';
    else if (key === 'effects') state.preferences.effects = node.checked ? 'soft' : 'full';
    else if (key === 'colorblind') state.preferences.colorblind = node.checked ? 'on' : 'off';
    else if (key === 'layout') state.preferences.layout = node.value;
    else if (key === 'menuDensity') state.preferences.menuDensity = node.value;
    else if (key === 'stageMode') state.preferences.stageMode = node.value;
    else if (key === 'stageAspect') state.preferences.stageAspect = node.value;
    else if (key === 'stageResolution') state.preferences.stageResolution = node.value;
    else if (key === 'sceneScale') state.preferences.sceneScale = node.value;
    else if (key === 'dockPosition') state.preferences.dockPosition = node.value;
    else if (key === 'showParty' || key === 'showNavigation' || key === 'showWorkspace' || key === 'debugMode') state.preferences[key] = node.checked;
    else if (key === 'menuSize') state.preferences[key] = node.value;
    else if (key === 'accent') state.preferences.accent = node.value;
    else if (key === 'textScale') state.preferences.textScale = node.value;
    else if (key === 'showActionDock' || key === 'showStatusMessages' || key === 'showTickIndicator') state.preferences[key] = node.checked;
    savePreferences(); render();
  });
  document.querySelectorAll('[data-engine-action]').forEach(node => node.onclick = () =>
    dispatchAction(node.dataset.engineAction, {label: node.querySelector('.action-text')?.textContent || node.dataset.engineAction}));
  document.querySelectorAll('[data-action^="target-choice:"]').forEach(node => node.onclick = async () => {
    const parts = node.dataset.action.split(':');
    await submitTarget(parts[1], parts[2], parts.slice(3).join(':'), node.textContent.trim());
  });
  bindStageTargeting();
  document.querySelectorAll('[data-action=\"cancel-target-picker\"]').forEach(n => n.onclick = () => { state.actionPicker = null; render(); });
  document.querySelectorAll('[data-action=\"cancel-spell-picker\"]').forEach(n => n.onclick = () => { state.spellPicker = null; render(); });
  document.querySelectorAll('#spell-choice').forEach(n => n.onchange = event => { state.spellPicker.id = event.target.value; render(); });
  document.querySelectorAll('#spell-form').forEach(n => n.onsubmit = event => {
    event.preventDefault();
    const data = new FormData(event.target);
    const picker = state.spellPicker;
    const spec = picker.spells.find(row => row.id === picker.id);
    const action = {type: 'cast', actor: picker.actor, spell: spec.id, targets: data.get('target') ? [data.get('target')] : [], metamagic: data.getAll('metamagic')};
    if (spec.radius || spec.operation === 'teleport') action[spec.radius ? 'center' : 'destination'] = ['x','y','z'].map(axis => Number(data.get(axis)));
    for (const key of ['mode','plane','named_creature']) if (data.get(key)) action[key] = data.get(key);
    if (spec.operation === 'niv_descent') action.dive = data.has('dive');
    work(async () => {
      result(await state.client.designAction(state.runId, action));
      state.spellPicker = null;
      await loadReadout(state.runId);
      state.note = `${spec.display_name} resolved.`;
    });
  });
  bindExpeditionControls();
  document.querySelectorAll('[data-auto-step]').forEach(node => node.onclick = () => work(async () => {
    result(await state.client.request(node.dataset.autoStep, {run_id: state.runId}));
    await loadReadout(state.runId);
  }));
  document.querySelectorAll('[data-action=\"idle-tick\"]').forEach(n => n.onclick = () => floorOneWorld() && work(async () => {
    result(await state.client.idleTick(state.runId, 1));
    selectGameplayScreen('journey');
    state.note = state.receipt?.pause ? `Idle paused: ${state.receipt.pause.message}` : 'Idle advanced one safe step.';
    render();
  }));
  document.querySelectorAll('[data-domain-feature]').forEach(node => node.onclick = () => work(async () => {
    const reply = await state.client.roomAction(state.runId, 'domain', {feature: node.dataset.domainFeature, actor: actor().id || 'p0'});
    result(reply); await loadReadout(state.runId);
    state.note = `${node.dataset.domainFeature} submitted to the engine.`;
    addMessage(state.note);
  }));
  document.querySelectorAll('[data-action=\"wren-recovery\"]').forEach(n => n.onclick = () => work(async () => {
    result(await state.client.designAction(state.runId, {type: 'unearthly_recovery', actor: actor().id}));
    await loadReadout(state.runId);
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
    const actorId = node.dataset.reactor || actor().id || 'p0';
    const fields = {type: defense === 'decline_reaction' ? 'decline_reaction' : 'reaction', actor: actorId};
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
  document.querySelectorAll('[data-dialogue-target]').forEach(node => node.onclick = () => work(async () => {
    const text = node.dataset.dialogueText || node.textContent.trim();
    const target = node.dataset.dialogueTarget;
    if (target) state.activeDialogueNpc = target;
    if (node.dataset.dialogueKey) {
      if (!state.visitedDialogues) state.visitedDialogues = new Set();
      state.visitedDialogues.add(node.dataset.dialogueKey);
    }
    result(await state.client.designTurn(state.runId, text, {
      type: 'talk', target: target || 'resident', mode: node.dataset.dialogueMode || 'ask',
      text, actor: actor().id || 'p0',
    }));
    selectGameplayScreen('residents');
    state.note = `${node.textContent.trim()} submitted to the host.`;
    addMessage(state.note);
  }));
  document.querySelectorAll('[data-upgrade]').forEach(node => node.onclick = () => work(async () => {
    const reply = await state.client.purchaseUpgrade(state.accountIdentity, node.dataset.upgrade);
    if (!reply.ok) throw Error(reply.error?.message || 'Purchase failed');
    state.progression = reply.result?.progression || state.progression;
    if (state.phase === 'meta-shop') await loadMetaShop();
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
  document.querySelectorAll('#character-form').forEach(n => n.onsubmit = async event => {
    event.preventDefault(); const data = Object.fromEntries(new FormData(event.target));
    state.draft = {...state.draft, ...data, level: Number(data.level || state.draft.level || 1), spell_budget: Number(data.spell_budget || state.draft.spell_budget || 0)};
    if (!state.draft.creation_seed) state.draft.creation_seed = state.draft.name; persistUiState();
    await work(async () => {
      const build = buildPayload();
      const reply = await state.client.previewCharacter(build);
      state.preview = result(reply).result; state.phase = 'preview';
    });
  });
  document.querySelectorAll('[data-action="confirm-build"]').forEach(node => node.onclick = async () => {
    const attempt = async () => {
      const profileSeed = state.draft.creation_seed || state.draft.name;
      const profileId = `web-${profileSeed.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-|-$/g, '') || Date.now()}`;
      const build = buildPayload();
      const mode = state.pendingMode || 'DESIGN';
      if (!['FORGE', 'SANDBOX'].includes(mode)) throw Error('Custom characters are available only in Story or Simulation Mode.');
      result(await state.client.boot(mode));
      result(await state.client.buildCharacter(profileId, build, (state.live || state.preview?.character)?.build_hash));
      if (mode === 'FORGE') {
        state.pendingLead = {kind: 'custom', profileId, build, preview: state.live || state.preview?.character || state.draft};
        go('entry-select');
        render();
      } else {
        await beginCustomRun(profileId, 'market');
      }
    };
    await work(() => withSandboxRecovery(attempt));
  });
  const consoleInput = document.querySelector('#console-input');
  consoleInput?.addEventListener('keydown', event => {
    const hist = state.consoleHistory;
    if (event.key === 'ArrowUp' && hist.length) { event.preventDefault(); state.consoleCursor = state.consoleCursor < 0 ? hist.length - 1 : Math.max(0, state.consoleCursor - 1); consoleInput.value = hist[state.consoleCursor]; }
    else if (event.key === 'ArrowDown' && state.consoleCursor >= 0) { event.preventDefault(); state.consoleCursor += 1; if (state.consoleCursor >= hist.length) { state.consoleCursor = -1; consoleInput.value = ''; } else consoleInput.value = hist[state.consoleCursor]; }
    else if (event.key === 'Escape' && state.messageHistoryOpen && !state.overlay) { event.preventDefault(); state.consoleDraft = consoleInput.value; state.messageHistoryOpen = false; render(); document.querySelector('#console-input')?.focus(); }
    else if (event.key === 'Tab' && consoleInput.value.startsWith('/') && !consoleInput.value.includes(' ')) {
      event.preventDefault();
      const stem = consoleInput.value.slice(1).toLowerCase(); const hits = Object.keys(CONSOLE_COMMANDS).filter(name => name.startsWith(stem));
      if (hits.length === 1) consoleInput.value = `/${hits[0]} `;
      else if (hits.length) { state.consoleDraft = consoleInput.value; addMessage(`Matches: ${hits.map(h => `/${h}`).join(' ')}`, 'note'); state.messageHistoryOpen = true; state.messagePanelTab = 'messages'; render(); document.querySelector('#console-input')?.focus(); }
    }
  });
  consoleInput?.addEventListener('input', () => { state.consoleDraft = consoleInput.value; });
  document.querySelectorAll('#console-form').forEach(n => n.onsubmit = async event => {
    event.preventDefault();
    const text = new FormData(event.target).get('console')?.trim();
    if (!text) return;
    const conversation = state.pendingConversation;
    state.consoleDraft = ''; state.pendingConversation = null; state.consoleCursor = -1;
    if (state.consoleHistory[state.consoleHistory.length - 1] !== text) state.consoleHistory.push(text);
    if (state.consoleHistory.length > 50) state.consoleHistory.shift();
    debugLog('trace', 'INPUT', text);
    if (text.startsWith('/') && !conversation) {
      const [head, ...args] = text.slice(1).split(/\s+/);
      const raw = text.slice(1 + head.length).trim();
      const command = CONSOLE_COMMANDS[head.toLowerCase()];
      state.messageHistoryOpen = true;
      if (!command) { addMessage(`Unknown command /${head}. Type /help.`, 'error'); render(); return; }
      addMessage(`> ${text}`, 'input');
      if (command.host) await work(() => command.run(args, raw));
      else { try { await command.run(args, raw); } catch (error) { fail(error.message); } }
      render(); document.querySelector('#console-input')?.focus(); return;
    }
    await work(async () => {
      if (conversation) { result(await state.client.designTurn(state.runId, text, {type: 'talk', target: conversation.npc, mode: conversation.mode, text, actor: actor().id || 'p0'})); await loadReadout(state.runId); }
      else if (/^(look around|show room)$/i.test(text)) selectGameplayScreen('room');
      else if (/^show my equipment$/i.test(text)) selectGameplayScreen('equipment');
      else await sendIntent(text);
    });
  });
  bindDraggables();
  bindWorkspacePanels();
  mountArcade();
}
window.addEventListener('hashchange', () => {
  const next = location.hash.slice(1);
  if (screens.includes(next) && state.phase === 'ready') refreshScreen(next);
});
window.addEventListener('popstate', event => {
  if (!event.state?.hsr) return;
  clearScreenTransientState();
  state.phase = event.state.phase || 'title';
  state.route = Array.isArray(event.state.route) && event.state.route.length ? [...event.state.route] : ['title'];
  if (screens.includes(event.state.selected)) state.selected = event.state.selected;
  render();
});
document.querySelectorAll('#item-dialog').forEach(n => n.onclick = event => { if (event.target === event.currentTarget) event.currentTarget.close(); });
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
  } catch (error) {
    console.error('HSR app initialization error:', error);
    if (window.HSRStartupError) window.HSRStartupError(error, 'ensureAppInitialized');
    else app.innerHTML = `<div style="padding:30px; color:var(--muted);"><p>HSR initialization failed:</p><pre>${E(error.message)}</pre></div>`;
  }
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', ensureAppInitialized);
} else {
  ensureAppInitialized();
}
// Clock ticker: host clock and heartbeat age refresh every second; a heartbeat
// pings the host every five seconds for status, latency and clock offset.
setInterval(() => { state.clockTick++; refreshLinkReadout(); }, 1000);
let heartbeatTimer = 0;
function scheduleHeartbeat() {
  clearInterval(heartbeatTimer);
  const every = Number(state.preferences.link.heartbeatMs) || 0;
  if (every > 0) heartbeatTimer = setInterval(heartbeat, Math.max(1000, every));
}
scheduleHeartbeat();
setTimeout(heartbeat, 300);
globalThis.HollowStarUI = Object.freeze({
  schema: 'hsr-ui-client-3',
  getPublicView: () => structuredClone(state.view),
  getStatus: () => ({phase: state.phase, run_id: state.runId, transport: state.transport, busy: state.busy}),
  navigate: screen => state.phase === 'ready' ? refreshScreen(screen) : false,
  refresh: () => refreshScreen(state.selected),
  refreshReadout: () => state.runId ? work(() => loadReadout(state.runId)) : false,
  // Combat input/drain state for probes: no setters, nothing a click can't reach.
  getCombatStatus: () => ({draining: npcDrainRunning, npcPhase: Boolean(state.npcPhase), style: combatStyle(state.preferences.combat.style),
    radial: state.combatRadial ? structuredClone(state.combatRadial) : null, threat: state.threatWarning ? structuredClone(state.threatWarning) : null,
    focus: state.focusTarget, history: combatDirector.history}),
});
