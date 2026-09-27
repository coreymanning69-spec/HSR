import {createHSRClient} from './hsr-client.js?v=compact-envelope-1';

const E = globalThis.HSRUI.escape;
const screens = ['room', 'battle', 'equipment', 'roster', 'residents', 'journal', 'map', 'library', 'options'];
const ABILITIES = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA'];
const ABILITY_NAMES = {STR: 'Strength', DEX: 'Dexterity', CON: 'Constitution', INT: 'Intelligence', WIS: 'Wisdom', CHA: 'Charisma'};
const preferenceKey = 'hsr-display-preferences';
const defaultPreferences = {iconActions: false, menuDensity: 'comfortable', layout: 'sanctum', textScale: '1', motion: 'full', effects: 'full'};
function readPreferences() {
  try { return {...defaultPreferences, ...JSON.parse(localStorage.getItem(preferenceKey) || '{}')}; }
  catch { return {...defaultPreferences}; }
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
  document.documentElement.style.setProperty('--text-scale', state.preferences.textScale);
}
const state = {
  phase: 'title', transport: 'engine-host', client: createHSRClient(), view: null, receipt: null,
  runId: null, runs: [], options: null, draft: {name: '', identity: '', race: 'human', gender: 'feminine',
  character_class: 'warrior', background: 'veteran', creation_seed: '', level: 1, roll_set: 0,
  ability_assignment: 'auto', floating_bonuses: 'auto', advancements: 'auto', advancement_mode: 'auto',
  skills: 'auto', skill_mode: 'auto', spells: 'auto', spell_mode: 'auto', spell_budget: 0}, preview: null,
  roll: null,
  affixes: null, catalog: null, vocabulary: null, preferences: readPreferences(),
  selected: screens.includes(location.hash.slice(1)) ? location.hash.slice(1) : 'room',
  busy: false, connected: false, note: '', error: '', refreshed: null, initialized: false,
};
try {
  const saved = JSON.parse(sessionStorage.getItem('hsr-ui-state') || '{}');
  if (!location.hash && screens.includes(saved.selected)) state.selected = saved.selected;
  if (saved.draft && typeof saved.draft === 'object') state.draft = {...state.draft, ...saved.draft};
} catch {}
function persistUiState() {
  try { sessionStorage.setItem('hsr-ui-state', JSON.stringify({selected: state.selected, draft: state.draft})); } catch {}
}

const party = () => state.view?.party || [];
const actor = () => party().find(item => item.id === state.selected) || party()[0] || {};
const value = (object, ...keys) => keys.map(key => object?.[key]).find(item => item !== undefined && item !== null);
const card = (title, body, extra = '') => `<section class="card ${extra}"><p class="label">${E(title)}</p>${body}</section>`;
const button = (label, action, extra = '') => `<button type="button" class="action ${extra}" data-action="${E(action)}">${E(label)}</button>`;

function fail(message) {
  state.error = message;
  state.note = 'Last displayed public state retained. Refresh before retrying an uncertain action.';
}
function result(reply) {
  if (!reply.ok) throw Error(reply.error?.message || reply.error?.code || 'Host request failed');
  if (reply.public_view) {
    state.view = reply.public_view;
    state.receipt = reply.public_receipt;
    state.runId = reply.run_id || state.runId;
    state.refreshed = new Date();
  }
  return reply;
}
async function work(fn) {
  if (state.busy) return;
  state.busy = true; state.error = '';
  render();
  try { await fn(); } catch (error) { fail(error.message); }
  finally { state.busy = false; render(); }
}
async function boot() {
  const reply = result(await state.client.boot('DESIGN'));
  state.note = reply.ok ? 'Host connected.' : '';
  const options = await state.client.characterOptions();
  if (options?.ok) state.options = options.result;
}
async function connect(mode = state.transport, nextPhase = 'title') {
  state.phase = 'loading'; state.view = null; state.receipt = null; state.connected = false; state.error = ''; render();
  state.transport = mode;
  state.client = createHSRClient({mode});
  await work(async () => {
    const health = await state.client.health();
    if (!health.ok) throw Error(health.error?.message || 'Host unavailable');
    const bootReply = await state.client.boot('DESIGN');
    result(bootReply);
    const optionsReply = await state.client.characterOptions();
    if (optionsReply?.ok) state.options = optionsReply.result;
    const affixReply = await state.client.affixCatalog();
    if (affixReply?.ok) state.affixes = affixReply.result?.affixes;
    const catalogReply = await state.client.contentCatalog();
    if (catalogReply?.ok) state.catalog = catalogReply.result?.content || null;
    const vocabularyReply = await state.client.sessionVocabulary();
    if (vocabularyReply?.ok) state.vocabulary = vocabularyReply.result;
    state.connected = true;
    state.phase = nextPhase; state.note = `${mode === 'hostless' ? 'Hostless local' : 'Engine Host'} connected.`;
  });
  if (state.phase === 'loading') { state.phase = 'title'; render(); }
}
async function hostCall(command, payload = {}) {
  const reply = await state.client.request(command, payload);
  if (reply) return reply;
  const id = crypto.randomUUID();
  const response = await fetch('/api/host', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id, command, compact: true, public_only: true, ...payload})});
  return response.json();
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
        <!-- Mountains -->
        <polygon points="0,600 200,300 500,600" fill="#1a2333" opacity="0.8"/>
        <polygon points="250,650 600,250 900,650" fill="#253548" opacity="0.7"/>
        <polygon points="700,700 1100,350 1500,700" fill="#1f2d42" opacity="0.75"/>
        <polygon points="1200,750 1400,400 1600,750" fill="#2a3a52" opacity="0.8"/>
        <!-- Moon -->
        <circle cx="1100" cy="200" r="180" fill="url(#moonGrad)" opacity="0.95"/>
        <circle cx="1100" cy="200" r="180" fill="none" stroke="rgba(201,168,106,0.3)" stroke-width="2" opacity="0.6"/>
      </svg>
    </div>
    <div class="intro-content">
      <section class="intro-card">
        <h1 class="intro-title">Hollow Star Reliquary</h1>
        <p class="intro-subtitle">Enter a world of divine mystery and tactical combat</p>
        <div class="intro-actions">
          ${button('New Game', 'new-game', 'intro-action-primary')}
          ${button('Continue Game', 'continue', 'intro-action-primary')}
        </div>
        <div class="intro-secondary">
          ${button('Reconnect', 'reconnect', 'intro-action-secondary')}
        </div>
        <p class="intro-connection">
          <span class="label">Connection</span>
          ${E(state.transport)} · <span class="connection-status ${state.connected ? 'connected' : 'disconnected'}">${state.connected ? '● Connected' : '○ Not connected'}</span>
        </p>
      </section>
    </div>
  </div>`;
}
function transportChoice() {
  return `${atmosphere('gateway', 'Choose a gateway', 'Both paths use the same illustrated client; Engine Host also serves MCP and CLI adapters.')}${card('New game mode', `<h2>Choose where this run lives</h2><p>The selected transport remains visible throughout play.</p>
    <div class="actions">${button('Hostless local game', 'start-hostless')}${button('Engine Host game', 'start-engine')}</div>${button('Back', 'title', 'secondary')}`)}`;
}
function field(label, key, type = 'text', required = true) {
  const choiceKey = {race: 'races', character_class: 'classes', background: 'backgrounds'}[key];
  const input = type === 'select'
    ? `<select name="${E(key)}" data-create-field="${E(key)}">${(state.options?.[choiceKey] || []).map(row => `<option value="${E(row.id)}" ${state.draft[key] === row.id ? 'selected' : ''}>${E(row.name)}</option>`).join('')}</select>`
    : `<input name="${E(key)}" data-create-field="${E(key)}" type="${type}" value="${E(state.draft[key] || '')}" ${required ? 'required' : ''}>`;
  return `<label>${E(label)}${input}</label>`;
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
function traitsLine(row) {
  return (row.traits || []).map(trait => trait.replaceAll('_', ' ')).join(' · ') || 'No listed traits';
}
function detailCard(titleText, body) {
  return `<section class="creator-detail"><p class="label">${E(titleText)}</p>${body}</section>`;
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
  const selected = Array.isArray(state.draft.floating_bonuses) ? state.draft.floating_bonuses : [];
  return detailCard('Ancestry bonuses', `<p>Choose ${E(rule.count)} abilities for the floating ${E(rule.amount > 0 ? '+' : '')}${E(rule.amount)} bonus.</p><div class="check-grid">${ABILITIES.filter(ability => !rule.exclude.includes(ability)).map(ability => `<label class="check-chip"><input type="checkbox" data-floating="${E(ability)}" ${selected.includes(ability) ? 'checked' : ''}><span>${E(ability)}<small>${E(ABILITY_NAMES[ability])}</small></span></label>`).join('')}</div>`);
}
function advancementControls(level, cls) {
  const points = 2 * ((state.options?.advancement_levels || []).filter(threshold => level >= threshold).length);
  if (!points) return `<div class="creator-detail"><p class="label">Advancement</p><p>No ability advancement points at level ${E(level)}. Points unlock at levels ${E((state.options?.advancement_levels || []).join(', '))}.</p></div>`;
  const values = state.draft.advancements && typeof state.draft.advancements === 'object' ? state.draft.advancements : {};
  const manual = state.draft.advancement_mode === 'manual';
  return detailCard('Advancement', `<p>Level ${E(level)} grants <strong>${E(points)} ability points</strong>. Class priority: ${E((cls.primary || []).join(' / '))}.</p><div class="actions compact-actions">${button(manual ? 'Use automatic allocation' : 'Allocate manually', manual ? 'advancements-auto' : 'advancements-manual', 'secondary')}</div>${manual ? `<div class="ability-table advancement-table"><div class="ability-head"><span>Ability</span><span>Points</span><span>Result</span></div>${ABILITIES.map(ability => `<label class="ability-row"><span><strong>${E(ability)}</strong><small>${E(ABILITY_NAMES[ability])}</small></span><input type="number" min="0" max="${E(points)}" value="${E(values[ability] || 0)}" data-advancement="${E(ability)}"><strong>+${E(values[ability] || 0)}</strong></label>`).join('')}</div>` : '<p class="notice">The host will allocate these points deterministically toward the selected class priorities.</p>'}`);
}
function skillControls(race, cls) {
  const count = (cls.skill_count || 0) + (race.extra_skills || 0);
  const manual = state.draft.skill_mode === 'manual';
  const selected = Array.isArray(state.draft.skills) ? state.draft.skills : [];
  const skills = state.options?.skills || {};
  if (!manual) return detailCard('Skills', `<p>Choose <strong>${E(count)}</strong> trained skills. The host will select a valid class-priority set automatically.</p><div class="actions compact-actions">${button('Choose skills manually', 'skills-manual', 'secondary')}</div><p class="notice">Class skills: ${E((cls.skills || []).join(' · '))}${race.extra_skills ? ' · ancestry grants one additional skill' : ''}</p>`);
  return detailCard('Skills', `<p>Choose exactly <strong>${E(count)}</strong> trained skills; at least ${E(cls.skill_count || 0)} must come from the class list.</p><div class="check-grid skill-grid">${Object.entries(skills).map(([skill, ability]) => `<label class="check-chip ${cls.skills?.includes(skill) ? 'class-skill' : ''}"><input type="checkbox" data-skill="${E(skill)}" ${selected.includes(skill) ? 'checked' : ''}><span>${E(skill)}<small>${E(ability)}${cls.skills?.includes(skill) ? ' · class' : ''}</small></span></label>`).join('')}</div><div class="actions compact-actions">${button('Use automatic skills', 'skills-auto', 'secondary')}</div>`);
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
  const build = {name: d.name, creation_seed: d.creation_seed || d.name, race: d.race, gender: d.gender, character_class: d.character_class,
    background: d.background, level: Number(d.level || 1), roll_set: Number(d.roll_set || 0),
    ability_assignment: d.ability_assignment && typeof d.ability_assignment === 'object' ? d.ability_assignment : 'auto',
    floating_bonuses: Array.isArray(d.floating_bonuses) ? d.floating_bonuses : 'auto',
    advancements: d.advancement_mode === 'manual' ? (d.advancements || {}) : 'auto',
    skills: d.skill_mode === 'manual' ? (d.skills || []) : 'auto',
    spell_budget: Number(d.spell_budget || 0),
    spells: d.spell_mode === 'manual' ? (d.spells || []) : 'auto'};
  return build;
}
function creator() {
  const d = state.draft;
  const race = optionBy('races', d.race); const cls = optionBy('classes', d.character_class);
  const scores = state.roll?.scores || [];
  const assignment = d.ability_assignment === 'auto' ? automaticAssignment(scores) : d.ability_assignment;
  return card('Character creation', `<div class="creator-header"><div><p class="eyebrow">A new lead for the descent</p><h2>Build the character</h2><p>Every choice below is sent to the host for deterministic validation. Nothing is saved until you confirm the final preview.</p></div><div class="creator-badge">${E(d.level || 1)}<small>LEVEL</small></div></div>
    <form id="character-form" class="creator-form">
      <div class="creator-identity">${field('Lead name', 'name')}${field('Lead identity', 'identity', 'text', false)}${field('Creation seed', 'creation_seed', 'text', false)}</div>
      <div class="creator-selects">${field('Race', 'race', 'select')}<label>Gender<select name="gender" data-create-field="gender"><option value="feminine" ${d.gender === 'feminine' ? 'selected' : ''}>Feminine</option><option value="masculine" ${d.gender === 'masculine' ? 'selected' : ''}>Masculine</option></select></label>${field('Class', 'character_class', 'select')}${field('Background', 'background', 'select')}<label>Level<input name="level" data-create-field="level" type="number" min="1" max="20" value="${E(d.level || 1)}" required></label></div>
      <section class="creator-sprite-preview"><div class="creation-sprite race-${E(d.race || 'human')} gender-${E(d.gender || 'feminine')}" role="img" aria-label="${E((race.name || 'Human') + ' ' + (d.gender || 'feminine'))} character preview"></div><div><p class="label">Live appearance preview</p><p class="notice">Updates as race and gender change. Presentation only; the host remains authoritative for the build.</p></div></section>
      ${choiceSummary()}
      ${floatingControls(race)}
      <section class="creator-detail"><p class="label">Ability scores</p><div class="roll-toolbar"><div><h3>${scores.length ? `Rolled ${E(state.roll.method)}` : 'Roll your ability scores'}</h3><p class="notice">${scores.length ? `Seed ${E(state.roll.creation_seed)} · roll set ${E((state.roll.roll_set || 0) + 1)} of 2` : 'The host uses 4d6 and drops the lowest die for each ability.'}</p></div>${button(scores.length ? (state.roll.roll_set === 0 ? 'Use one reroll' : 'Reroll used') : 'Roll ability scores', 'roll-abilities', 'secondary')}</div>${scores.length ? `<div class="roll-strip">${state.roll.rolls.map((row, index) => `<span class="roll-chip"><strong>${E(row.total)}</strong><small>${E(row.dice.join(' · '))} · drop ${E(row.dropped)}</small></span>`).join('')}</div>${abilityTable(scores, assignment)}<p class="notice">Leave assignments on Auto for deterministic class-priority placement, or choose a rolled score for each ability. Duplicate scores are valid.</p>` : '<p class="notice">You may preview without rolling here; the host will still produce the exact deterministic receipt from your seed.</p>'}</section>
      ${advancementControls(Number(d.level || 1), cls)}
      ${skillControls(race, cls)}
      ${spellControls(cls, Number(d.level || 1))}
      <div class="actions creator-actions"><button type="submit" class="action">Preview complete character</button>${button('Back', 'title', 'secondary')}${button('Restart', 'restart', 'secondary')}</div>
    </form>`);
}
function preview() {
  const c = state.preview?.character || {};
  if (!c.profile || typeof c.build_hash !== 'string') return card('Preview error', '<p>The host returned an invalid character preview. Nothing was saved.</p>');
  const p = c.profile || {};
  const receipt = c.receipt || {}; const scores = p.ability_scores || {};
  const saves = p.build_rules?.saves || {}; const skills = p.skill_bonuses || {};
  const equipment = (p.equipment || []).map(item => item.display_name || item.name || item.id).filter(Boolean);
  const background = p.background || {};
  return card('Preview only', `<div class="preview-header"><div><p class="eyebrow">Final sheet · not saved</p><h2>${E(p.name || state.draft.name)}</h2><p><strong>${E(p.race || 'Unreported')} ${E(p.character_class || 'Unreported')}</strong> · level ${E(p.level)} · ${E(background.name || 'Unreported')}</p></div><div class="preview-hash">${E(c.build_hash.slice(0, 12))}<small>BUILD HASH</small></div></div>
    <p class="notice"><strong>Preview only.</strong> Confirming creates the profile and a new DESIGN run through the host. Back returns to the editable draft.</p>
    <div class="preview-grid"><section class="sheet-panel"><p class="label">Ability scores</p><div class="score-grid">${ABILITIES.map(ability => `<div><strong>${E(scores[ability])}</strong><span>${E(ability)}</span><small>${E(modifier(scores[ability]))}</small></div>`).join('')}</div><div class="stat"><span>HP / AC / Speed</span><strong>${E(p.max_hp)} / ${E(p.armor_class)} / ${E(p.speed)} ft</strong></div><div class="stat"><span>Proficiency</span><strong>+${E(p.proficiency_bonus)}</strong></div></section>
      <section class="sheet-panel"><p class="label">Bonuses and abilities</p><div class="stat"><span>Race bonuses</span><strong>${E(bonusLine(receipt.race_bonuses))}</strong></div><div class="stat"><span>Floating bonuses</span><strong>${E((receipt.floating_bonuses || []).join(' · ') || 'None')}</strong></div><div class="stat"><span>Saves</span><strong>${E(ABILITIES.filter(a => saves[a]).map(a => `${a} ${modifier(saves[a])}`).join(' · '))}</strong></div><p class="notice">${E((p.features || []).join(' · '))}</p><p class="notice">Interaction: ${E((p.interaction_tags || []).join(' · ') || 'None')}</p></section>
      <section class="sheet-panel"><p class="label">Skills and magic</p><p><strong>Trained skills</strong><br>${E(Object.entries(skills).map(([skill, bonus]) => `${skill} ${bonus >= 0 ? '+' : ''}${bonus}`).join(' · ') || 'None')}</p>${p.known_spells?.length ? `<p><strong>Known spells</strong><br>${E(p.known_spells.map(spell => spell.replace('@5e', '')).join(' · '))}</p><p class="notice">Spell energy ${E(p.build_rules?.casting_energy_max || 0)} · rank cap ${E(p.build_rules?.spell_rank_cap || 0)} · spent ${E(receipt.spell_points_spent || 0)} / ${E(receipt.spell_budget || 0)}</p>` : '<p class="notice">No spellcasting package.</p>'}</section>
      <section class="sheet-panel"><p class="label">Starting kit</p><p>${E(equipment.join(' · ') || 'No public equipment reported.')}</p><p class="notice">Gold ${E(background.starting_gold)} · origin ${E(p.origin_item?.name || receipt.origin_roll?.item_id || '—')} · heirloom ${E(p.heirloom_item?.name || (receipt.heirloom_roll?.triggered ? receipt.heirloom_roll.item_id : 'none'))}</p></section></div>
    <details class="receipt-details"><summary>Show deterministic creation receipt</summary><pre>${E(JSON.stringify(receipt, null, 2))}</pre></details>
    <div class="actions creator-actions">${button('Confirm and create run', 'confirm-build')}${button('Edit character', 'create', 'secondary')}${button('Restart', 'restart', 'secondary')}</div>`);
}
function runs() {
  return `${atmosphere('runs', 'Return to the Reliquary', 'Choose any host-reported run and resume it through the same public engine contract.')}${card('Continue game', `<h2>Saved runs</h2>${state.runs.length ? `<div class="run-list">${state.runs.map(run => {
    const id = typeof run === 'string' ? run : run.run_id;
    return `<article class="run-row"><div><strong>${E(id)}</strong><small>${E(run.summary || run.status || 'Saved run')}</small></div>${button('Load', `load:${id}`)}</article>`;
  }).join('')}</div>` : '<p>No saved runs are available. Start a new game to create one.</p>'}
  <div class="actions">${button('Refresh list', 'refresh-runs')}${button('Start New Game', 'new-game')}${button('Back', 'title', 'secondary')}</div>`)}`;
}

function visualRole(item = {}, fallback = 'adventurer') {
  const text = `${item.name || ''} ${item.role || ''}`.toLowerCase();
  if (/mage|magic|cleric|caster|witch|wellkeeper/.test(text)) return 'caster';
  if (/guard|steward|fighter|warrior|sentinel/.test(text)) return 'guard';
  if (/town|resident|merchant|keeper/.test(text)) return 'townsfolk';
  return fallback;
}
function visualWeapon(item = {}) {
  const text = JSON.stringify(item.equipment || []).toLowerCase();
  if (/staff|wand|rod/.test(text)) return 'staff';
  if (/bow|crossbow/.test(text)) return 'bow';
  if (/shield/.test(text)) return 'shield';
  return 'sword';
}
function characterFigure(item = {}, extra = '') {
  const role = visualRole(item); const weapon = visualWeapon(item);
  const appearance = item.sprite_id || `${item.race_id || 'human'}-${item.gender || 'feminine'}`;
  return `<div class="scene-character ${E(role)} ${E(extra)} appearance-${E(appearance)}" data-sprite-id="${E(appearance)}" aria-label="${E(item.name || role)} illustrated figure">
    <i class="char-shadow"></i><i class="char-boots"></i><i class="char-coat"></i><i class="char-seam"></i>
    <i class="char-cuffs"></i><i class="char-head"></i><i class="char-hair"></i><i class="char-fringe"></i>
    <i class="char-eyes"></i><i class="char-nose"></i><i class="char-collar"></i><i class="char-belt"></i>
    <i class="char-buckle"></i><i class="char-weapon ${E(weapon)}"></i>
    <span>${E(item.name || role)}</span></div>`;
}
function sceneWorld(kind = 'room') {
  const r = state.view?.room || {}; const lead = actor(); const foe = state.view?.opposition?.[0];
  return `<section class="illustrated-scene scene-${E(kind)}" aria-label="Illustrated ${E(kind)} view">
    <div class="scene-moon"></div><div class="scene-mountains back"></div><div class="scene-mountains front"></div>
    <div class="scene-town"></div><div class="scene-road"></div><div class="scene-well"></div>
    ${characterFigure(lead)}${kind === 'battle' && foe ? characterFigure(foe, 'opponent') : ''}
    <div class="scene-frame-label"><strong>${E(r.name || r.id || 'The Reliquary')}</strong><small>${kind === 'battle' ? 'Public encounter projection' : 'Public room projection'}</small></div>
  </section>`;
}
function atmosphere(kind, titleText, subtitle) {
  return `<section class="atmosphere atmosphere-${E(kind)}"><div class="atmosphere-orbit"></div><span class="atmosphere-glyph" aria-hidden="true">${kind === 'journal' ? '▤' : kind === 'map' ? '◎' : kind === 'library' ? '⌘' : '✧'}</span><div><p class="eyebrow">Hollow Star interface</p><h2>${E(titleText)}</h2><p>${E(subtitle)}</p></div></section>`;
}
function room() {
  const r = state.view?.room || {};
  const exits = Object.entries(r.exits || {}).map(([direction, destination]) => `${direction}: ${destination}`).join(' · ');
  const tells = (r.visible_tells || r.tells || []).map(tell => typeof tell === 'string' ? tell : tell.text || tell.description || tell.name || tell.tell).filter(Boolean).join(' · ');
  return `${sceneWorld('room')}${card('Sanctum room', `<div class="room-hero"><div><p class="eyebrow">${E(r.apparent_function || r.condition || 'Observed space')}</p><h2>${E(r.name || r.id || 'Unreported room')}</h2><p>${E(r.description || r.posture || r.terrain || 'No public description reported.')}</p></div><span class="room-sigil" aria-hidden="true">⌂</span></div>
    <div class="room-facts"><div><small>Law</small><strong>${E(r.law || 'Not reported')}</strong></div><div><small>Terrain</small><strong>${E(r.terrain || 'Not reported')}</strong></div><div><small>Exits</small><strong>${E(exits || 'None reported')}</strong></div></div>
    <p class="notice">${E(tells || 'No visible tells reported.')}</p>${intent()}`)}`;
}
function battle() {
  const v = state.view || {};
  const active = Boolean(v.combat || v.turn || (v.opposition || []).length);
  return `${sceneWorld('battle')}${card('Encounter', `<div class="battle-banner"><div><p class="eyebrow">Tactical readout</p><h2>${active ? 'Active encounter' : 'Quiet floor'}</h2><p>Round ${E(v.round || v.combat?.round || '—')} · Turn ${E(v.turn || '—')}</p></div><span class="battle-sigil" aria-hidden="true">⚔</span></div>
    <div class="roster-grid">${[...party(), ...(v.opposition || [])].map(actorCard).join('') || '<p>No public combat roster.</p>'}</div>${active ? intent() : '<p class="notice">The engine will surface combat controls when an encounter begins.</p>'}`)}`;
}
function actorCard(item) {
  const statuses = Array.isArray(item.status) ? item.status.join(' · ') : (item.status || 'No visible statuses');
  return `<button class="actor-card ${actor().id === item.id ? 'selected' : ''}" data-actor="${E(item.id)}"><span class="mini-character ${E(visualRole(item))}"><i></i><b>${E((item.name || '?')[0])}</b></span><span><strong>${E(item.name)}</strong><small>${E(value(item, 'hp') ?? '?')} / ${E(value(item, 'max_hp') ?? '?')} HP · AC ${E(value(item, 'armor_class', 'ac') ?? '?')}</small><small>${E(statuses)}</small></span></button>`;
}
function equipment() {
  const items = [...(actor().equipment || []), ...(state.view?.inventory || [])];
  return `${atmosphere('equipment', `${actor().name || 'Party'} equipment`, 'A clear armory view of every host-reported item, affix, and visible property.')}${card('Reliquary gear', `<div class="equipment-heading"><div><p class="eyebrow">Loadout and carried finds</p><h2>${E(actor().name || 'Party')} equipment</h2></div><span class="gear-sigil" aria-hidden="true">✦</span></div><div class="compact-items">${items.map((item, index) => globalThis.HSRUI.card(item, 'item', index, 'assets/')).join('') || '<p>No public items listed.</p>'}</div>
    <p class="notice">Properties, affixes, effects, and identification state are reported by the host only.</p>`)}`;
}
function residents() {
  const residents = Object.values(state.view?.room?.npcs || {});
  const transcript = [...(state.view?.recent_receipts || []), state.receipt].filter(Boolean).slice(-8).map(row => row.message || row.narration || row.summary || row.text || row.outcome).filter(Boolean);
  const chat = transcript.length ? transcript.map((line, index) => `<div class="chat-line ${index === transcript.length - 1 ? 'latest' : ''}"><span class="chat-mark">${index % 2 ? '◇' : '◈'}</span><p>${E(line)}</p></div>`).join('') : '<p class="notice">No public conversation has been recorded yet. Choose a resident or begin with an observation.</p>';
  const chatChoices = [button('We look around', 'intent:we look around', 'secondary'), button('Ask what is happening', 'intent:ask what is happening', 'secondary'), button('Keep listening', 'intent:keep listening', 'secondary')].join('');
  return `${atmosphere('residents', 'Visible residents', 'Pretty social portraits show who is speaking; ordinary scene figures keep the lived-in town readable.')}${card('Residents / social', `<div class="npc-gallery">${residents.map(npc => { const id = npc.id || npc.npc_id || npc.role; const role = String(npc.role || '').toLowerCase(); const portrait = /wellkeeper/.test(role) ? 'wellkeeper' : /merchant|market/.test(role) ? 'merchant' : /smith/.test(role) ? 'smith' : /bar|tavern/.test(role) ? 'server' : /watch|guard/.test(role) ? 'watch' : 'herbalist'; return `<article class="npc-card visual-npc"><div class="npc-portrait portrait-${portrait}" role="img" aria-label="${E(npc.name || npc.role || 'town resident')} portrait"></div><div><h3>${E(npc.name || npc.role)}</h3><p>${E(npc.role || npc.disposition || 'Disposition not reported.')}</p>${button('Talk', `talk:${id}`)}</div></article>`; }).join('') || '<p>No residents are visible in this public readout.</p>'}</div>`)}` + card('Town conversation', `<div class="chat-window" aria-live="polite">${chat}</div><div class="chat-choices">${chatChoices}</div>${intent()}`);
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
  return `${atmosphere('options', 'Display options', 'Tune the illustrated interface without changing a roll, room, item, or saved run.')}${card('Options', `<h2>HSR Interface</h2><p>Preferences are local to this browser and survive game-mode changes, navigation, and reloads.</p>
    <div class="option-list">
      <label class="option-row"><span><strong>Icon actions</strong><small>Use compact symbols for bottom action controls while keeping accessible labels.</small></span><input type="checkbox" data-pref="iconActions" ${p.iconActions ? 'checked' : ''}></label>
      <label class="option-row"><span><strong>Interface variation</strong><small>Choose a Sanctum layout, focused reading layout, or quiet text-first idle layout.</small></span><select data-pref="layout"><option value="sanctum" ${p.layout === 'sanctum' ? 'selected' : ''}>Sanctum</option><option value="focus" ${p.layout === 'focus' ? 'selected' : ''}>Focus</option><option value="idle" ${p.layout === 'idle' ? 'selected' : ''}>Idle / text-first</option></select></label>
      <label class="option-row"><span><strong>Menu density</strong><small>Adjust the room, battle, and equipment navigation rail.</small></span><input type="range" min="0" max="2" step="1" value="${p.menuDensity === 'compact' ? 0 : p.menuDensity === 'spacious' ? 2 : 1}" data-pref="menuDensity" aria-label="Menu density"></label>
      <label class="option-row"><span><strong>Text size</strong><small>Scale the mostly-text interface without changing the engine.</small></span><input type="range" min=".9" max="1.25" step=".05" value="${E(p.textScale)}" data-pref="textScale" aria-label="Text size"></label>
      <label class="option-row"><span><strong>Reduced motion</strong><small>Disable transition effects for idle or low-power use.</small></span><input type="checkbox" data-pref="motion" ${p.motion === 'reduced' ? 'checked' : ''}></label>
      <label class="option-row"><span><strong>Soft effects</strong><small>Reduce glow and shadow intensity.</small></span><input type="checkbox" data-pref="effects" ${p.effects === 'soft' ? 'checked' : ''}></label>
    </div>
    <div class="actions">${button('Reset display preferences', 'reset-preferences', 'secondary')}${button('Refresh engine state', 'refresh-readout', 'secondary')}</div>
    <details class="interface-reference"><summary><strong>Conversation and text commands</strong></summary><p>Use these host-routed phrases anywhere the intent box appears. Talk buttons on visible residents prefill a conversation request; the NPC response and consequences come back only through the public host receipt.</p>${textOptions || '<p>Text vocabulary unavailable; reconnect to refresh it.</p>'}</details>`)}`;
}
function bounded(titleText, message) { return card(titleText, `<h2>${E(titleText)}</h2><p>${E(message)}</p>`); }
function intent() {
  return `<form id="intent-form"><label for="intent">Intent to send to the host</label><div class="actions"><input id="intent" name="intent" required autocomplete="off" placeholder="Inspect the room…"><button class="action">Submit intent</button></div></form>`;
}
function gameplay() {
  const content = {room, battle, equipment, roster: () => `${atmosphere('roster', 'The party', 'Selectable adventurers with readable silhouettes, health, armor, status, and equipment roles.')}${card('Roster', `<div class="roster-showcase">${characterFigure(actor(), 'featured')}${party().map(actorCard).join('') || 'No public party reported.'}</div>`)}`,
    residents, journal: () => `${atmosphere('journal', 'Journey journal', 'Only host-reported discoveries and public receipts enter this record.')}${bounded('Journal', 'Only host-reported discoveries and receipts appear here.')}`,
    map: () => `${atmosphere('map', 'The descent', 'Known places glow at the edge of a larger unknown Reliquary.')}${bounded('Floors / map', 'Unknown areas remain unknown until the host reports them.')}`,
    library, options};
  return content[state.selected]?.() || room();
}
function shell() {
  const labels = {room: 'Sanctum', battle: 'Encounters', equipment: 'Relics', roster: 'Party', residents: 'Residents', journal: 'Chronicle', map: 'Atlas', library: 'Library', options: 'Options'};
  const tabs = screens.map(tab => button(labels[tab], `tab:${tab}`, state.selected === tab ? 'active' : 'secondary')).join('');
  return `<header class="masthead"><div><p class="kicker">Hollow Star Reliquary</p><h1>${E(state.view?.room?.name || 'Reliquary')}</h1>
    <p class="metadata">${E(state.transport)} · ${E(state.runId || 'No run')} · ${state.refreshed ? `refreshed ${state.refreshed.toLocaleTimeString()}` : 'not refreshed'}</p></div>
    <div class="actions">${button('Refresh', 'refresh-readout')}${button('Save / Exit', 'save')}${button('Reconnect', 'reconnect', 'secondary')}</div></header>
    <main class="master-grid"><aside class="left-rail"><p class="label">Party</p>${party().map(actorCard).join('') || '<p>No public party.</p>'}</aside>
    <section class="center-stage">${gameplay()}${state.receipt ? card('Latest public receipt', `<pre>${E(JSON.stringify(state.receipt, null, 2))}</pre>`) : ''}</section>
    <aside class="right-rail">${card('Connection', `<div class="stat"><span>State</span><strong>${state.busy ? 'pending' : state.error ? 'error' : 'connected'}</strong></div><div class="stat"><span>Run</span><strong>${E(state.runId || '—')}</strong></div><p>${E(state.note || '')}</p>`)}${card('Screens', `<nav class="tabs">${tabs}</nav>`)}</aside></main>`;
}
function actionBar() {
  const actions = state.view?.available_actions || [];
  if (!state.runId || !actions.length) return '';
  const icons = {inspect: '⌕', investigate: '◌', enter: '↳', rest: '☾', exit: '←', attack: '⚔', move: '⇢', cast: '✧', end_turn: '⏳', conversation: '☵', identify: '◇', escape: '↗'};
  return `<nav class="engine-action-bar" aria-label="Engine actions"><span class="action-bar-label">Engine actions</span>${actions.map(row => {
    const id = row.id || row.action;
    return `<button class="action engine-action" data-engine-action="${E(id)}" title="${E(row.label || id)}"><span class="action-glyph" aria-hidden="true">${E(icons[id] || '·')}</span><span class="action-text">${E(row.label || id)}</span></button>`;
  }).join('')}</nav>`;
}
function render() {
  applyPreferences();
  let body = state.phase === 'loading' ? card('Opening the Reliquary', '<h2>Refreshing engine state…</h2><p class="notice">Clearing stale interfaces before connecting.</p>') : state.phase === 'title' ? title() : state.phase === 'transport' ? transportChoice() : state.phase === 'create' ? creator() :
    state.phase === 'preview' ? preview() : state.phase === 'runs' ? runs() : shell();
  document.querySelector('#app').innerHTML = `${body}${actionBar()}${state.error ? `<p class="notice error" role="alert">${E(state.error)}</p>` : ''}<p class="notice" role="status">${E(state.note)}</p>`;
  document.querySelectorAll('button,input,select').forEach(node => { node.disabled = state.busy; });
  bind();
}
async function loadReadout(runId) { result(await state.client.readout(runId)); state.phase = 'ready'; state.note = 'Public state refreshed.'; }
function bind() {
  document.querySelectorAll('[data-actor]').forEach(node => node.onclick = () => { state.selected = node.dataset.actor; render(); });
  document.querySelectorAll('[data-item]').forEach(node => node.onclick = () => {
    const item = [...(actor().equipment || []), ...(state.view?.inventory || [])][Number(node.dataset.item)];
    const dialog = document.querySelector('#item-dialog'); dialog.innerHTML = globalThis.HSRUI.detail(item, 'assets/'); dialog.showModal();
  });
  document.querySelectorAll('[data-action]').forEach(node => node.onclick = async () => {
    const action = node.dataset.action;
    if (action === 'new-game') { state.phase = state.view ? 'create' : 'transport'; render(); }
    else if (action === 'title') { state.phase = 'title'; render(); }
    else if (action === 'create') { state.phase = 'create'; render(); }
    else if (action === 'restart') { state.draft = {...state.draft, name: '', identity: '', creation_seed: '', level: 1, roll_set: 0, ability_assignment: 'auto', floating_bonuses: 'auto', advancements: 'auto', advancement_mode: 'auto', skills: 'auto', skill_mode: 'auto', spells: 'auto', spell_mode: 'auto', spell_budget: 0}; state.roll = null; persistUiState(); state.preview = null; state.phase = 'create'; render(); }
    else if (action === 'hostless' || action === 'engine') await connect(action === 'hostless' ? 'hostless' : 'engine-host');
    else if (action === 'start-hostless' || action === 'start-engine') await connect(action === 'start-hostless' ? 'hostless' : 'engine-host', 'create');
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
    else if (action === 'continue') await work(async () => { result(await state.client.boot('DESIGN')); const reply = await state.client.listRuns(); if (!reply.ok) throw Error(reply.error?.message); state.runs = reply.result?.runs || []; state.phase = 'runs'; });
    else if (action === 'refresh-runs') await work(async () => { const reply = await state.client.listRuns(); if (!reply.ok) throw Error(reply.error?.message); state.runs = reply.result?.runs || []; });
    else if (action.startsWith('load:')) await work(async () => { const id = action.slice(5); result(await state.client.loadRun(id)); await loadReadout(id); });
    else if (action === 'reconnect') await connect();
    else if (action === 'reset-preferences') { state.preferences = {...defaultPreferences}; savePreferences(); render(); }
    else if (action === 'refresh-readout') await work(async () => loadReadout(state.runId));
    else if (action === 'save') await work(async () => { result(await state.client.saveRun(state.runId)); state.note = 'Run saved. No automatic retry will be made if the response is uncertain.'; });
    else if (action.startsWith('tab:')) { state.selected = action.slice(4); persistUiState(); history.replaceState(null, '', `#${state.selected}`); render(); }
    else if (action.startsWith('talk:') || action.startsWith('intent:')) { const input = document.querySelector('#intent'); if (input) { input.value = action.startsWith('talk:') ? `talk to ${action.slice(5)}` : action.slice(7); input.focus(); } }
  });
  document.querySelectorAll('[data-pref]').forEach(node => node.onchange = () => {
    const key = node.dataset.pref;
    if (key === 'iconActions') state.preferences.iconActions = node.checked;
    else if (key === 'motion') state.preferences.motion = node.checked ? 'reduced' : 'full';
    else if (key === 'effects') state.preferences.effects = node.checked ? 'soft' : 'full';
    else if (key === 'layout') state.preferences.layout = node.value;
    else if (key === 'menuDensity') state.preferences.menuDensity = ['compact', 'comfortable', 'spacious'][Number(node.value)] || 'comfortable';
    else if (key === 'textScale') state.preferences.textScale = node.value;
    savePreferences(); render();
  });
  document.querySelectorAll('[data-engine-action]').forEach(node => node.onclick = async () => {
    const action = node.dataset.engineAction;
    await work(async () => {
      const label = node.querySelector('.action-text')?.textContent || action;
      const reply = await state.client.designTurn(state.runId, label, {type: action, actor: actor().id || 'p0'});
      result(reply);
      state.note = `${node.querySelector('.action-text')?.textContent || action} submitted to the engine.`;
    });
  });
  document.querySelectorAll('[data-create-field]').forEach(node => node.onchange = () => {
    const key = node.dataset.createField;
    state.draft[key] = ['level', 'spell_budget'].includes(key) ? Number(node.value) : node.value;
    if (key === 'creation_seed' && node.value) state.draft.creation_seed = node.value;
    if (key === 'character_class' && state.draft.spell_budget && !(optionBy('classes', node.value).spells || []).length) state.draft.spell_budget = 0;
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
    const next = [...document.querySelectorAll('[data-floating]:checked')].map(input => input.dataset.floating);
    state.draft.floating_bonuses = next.length ? next : 'auto'; persistUiState(); render();
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
  document.querySelector('[data-action="confirm-build"]')?.addEventListener('click', async () => await work(async () => {
    const profileSeed = state.draft.identity || state.draft.creation_seed;
    const profileId = `web-${profileSeed.toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-|-$/g, '') || Date.now()}`;
    const build = buildPayload();
    result(await state.client.buildCharacter(profileId, build, state.preview.character.build_hash));
    const runId = `${profileId}-${Date.now().toString(36)}`;
    result(await state.client.createRun({run_id: runId, seed: state.draft.creation_seed, party: [`custom:${profileId}`], lead_selector: `custom:${profileId}`, opposition: ['Townsperson']}));
    state.runId = runId;
    const started = await state.client.designStart(runId);
    result(started);
    await loadReadout(runId);
  }));
  document.querySelector('#intent-form')?.addEventListener('submit', async event => { event.preventDefault(); const intentText = new FormData(event.target).get('intent')?.trim(); if (intentText) await work(async () => result(await state.client.designTurn(state.runId, intentText))); });
}
window.addEventListener('hashchange', () => {
  const next = location.hash.slice(1);
  if (screens.includes(next) && state.phase === 'ready') { state.selected = next; render(); }
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
    render();
    console.log('HSR app initialized');
  } catch (error) {
    console.error('HSR app initialization error:', error);
    app.innerHTML = `<div style="padding:30px; color:#a9a397;"><p>HSR initialization failed:</p><pre>${E(error.message)}</pre></div>`;
  }
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', ensureAppInitialized);
} else {
  ensureAppInitialized();
}
globalThis.HollowStarUI = Object.freeze({schema: 'hsr-ui-client-2', getPublicView: () => structuredClone(state.view), getStatus: () => ({phase: state.phase, run_id: state.runId, transport: state.transport, busy: state.busy})});
