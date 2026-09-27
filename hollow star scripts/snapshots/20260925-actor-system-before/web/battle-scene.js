// Side-view battle presentation (Final Fantasy look, D&D rules).
//
// Pure markup helpers: nothing here resolves an action. Rows and slots come
// from the host's `combat.formation`; commands post the same engine actions the
// classic turn panel does (attack, cast, dodge, move, end_turn, consume), so
// initiative, the action/bonus/reaction economy and every roll stay in
// hollowstar/tactical.py.

// Row anchors in stage percent. Party faces right from the left side; enemies
// are mirrored by the paperdoll `.opponent` rule and face left.
const ANCHORS = {
  party: {front: 30, back: 15},
  enemy: {front: 64, back: 80},
};
const SLOT_STEP_X = 4.5;   // diagonal stagger per slot, FF-style
const SLOT_STEP_Y = 30;    // px lift per slot

export function ffLayout(fighters = [], formation = {}, partyCount = 0) {
  const fallbackSlots = {};
  return new Map(fighters.map((item, index) => {
    const id = item.id || `slot-${index}`;
    const side = index < partyCount ? 'party' : 'enemy';
    let spot = formation[id];
    if (!spot) {
      const slot = fallbackSlots[side] = (fallbackSlots[side] ?? -1) + 1;
      spot = {side, row: 'front', slot};
    }
    const dir = spot.side === 'party' ? -1 : 1;
    const x = ANCHORS[spot.side === 'party' ? 'party' : 'enemy'][spot.row === 'back' ? 'back' : 'front']
      + dir * spot.slot * SLOT_STEP_X;
    const bottom = 18 + spot.slot * SLOT_STEP_Y + (spot.row === 'back' ? 14 : 0);
    const depth = 20 - spot.slot - (spot.row === 'back' ? 5 : 0);
    return [id, `left:${Math.max(3, Math.min(90, x)).toFixed(2)}%;bottom:${bottom}px;z-index:${depth};`];
  }));
}

export function turnOrderStrip({order = [], current = '', names = {}, down = new Set(), E}) {
  if (!order.length) return '';
  const cells = order.map((id, index) => {
    const who = String(id).startsWith('p') ? 'party' : 'enemy';
    const flags = [id === current && 'is-current', down.has(id) && 'is-down'].filter(Boolean).join(' ');
    return `<li class="ff-order-cell ff-${who} ${flags}" data-ff-order="${E(id)}"><small>${index + 1}</small><span>${E(names[id] || id)}</span></li>`;
  }).join('');
  return `<ol class="ff-order" aria-label="Initiative order">${cells}</ol>`;
}

const COMMANDS = [
  {id: 'attack', label: 'Attack', engine: 'attack', cost: 'action'},
  {id: 'skills', label: 'Skills', menu: 'skills'},
  {id: 'magic', label: 'Magic', engine: 'cast', cost: 'action'},
  {id: 'items', label: 'Items', menu: 'items'},
  {id: 'defend', label: 'Defend', engine: 'dodge', cost: 'action'},
  {id: 'move', label: 'Move', engine: 'move'},
  {id: 'end', label: 'End turn', engine: 'end_turn'},
];

export function commandWindow({name = '', playerTurn = false, economy = {}, menu = '', skills = '', items = [],
  autoButton = '', disabled = '', E}) {
  if (!playerTurn) {
    return `<section class="ff-command ff-command-wait" aria-label="Battle commands"><header><strong>${E(name || 'Enemy turn')}</strong></header><p class="ff-hint">Opponent's turn.</p><div class="ff-command-row">${autoButton}</div></section>`;
  }
  const buttons = COMMANDS.map(command => {
    const spent = command.cost && Number(economy[command.cost] ?? 1) <= 0;
    const open = command.menu && command.menu === menu;
    const attrs = command.engine
      ? `data-engine-action="${E(command.engine)}"`
      : `data-ff-menu="${E(command.menu)}" aria-expanded="${open}"`;
    return `<button type="button" class="ff-cmd${open ? ' is-open' : ''}" ${attrs}${spent ? ' disabled title="Already spent this turn"' : ''}>${E(command.label)}</button>`;
  }).join('');
  let submenu = '';
  if (menu === 'skills') submenu = `<div class="ff-submenu" aria-label="Skills">${skills || '<p class="ff-hint">No signature skills for this combatant.</p>'}</div>`;
  if (menu === 'items') {
    submenu = `<div class="ff-submenu" aria-label="Items">${items.length
      ? items.map(item => `<button type="button" class="ff-cmd ff-item" data-ff-item="${E(item.id)}">${E(item.name || item.id)}</button>`).join('')
      : '<p class="ff-hint">No usable items carried.</p>'}</div>`;
  }
  const pips = ['action', 'bonus', 'reaction'].map(key => `<span class="ff-pip${Number(economy[key] ?? 0) > 0 ? ' is-ready' : ''}" title="${E(key)}">${E(key[0].toUpperCase())}</span>`).join('');
  return `<section class="ff-command" aria-label="Battle commands"><header><strong>${E(name)}</strong><span class="ff-pips">${pips}<small>${E(economy.movement ?? 0)} ft</small></span></header><div class="ff-command-list" role="menu">${buttons}</div>${submenu}<div class="ff-command-row">${autoButton}</div>${disabled ? `<p class="ff-hint">${E(disabled)}</p>` : ''}</section>`;
}

export function partyStatusPanel({party = [], current = '', E}) {
  const rows = party.map(member => {
    const hp = Number(member.hp); const max = Number(member.max_hp);
    const ratio = Number.isFinite(hp) && max > 0 ? Math.max(0, Math.min(1, hp / max)) : 0;
    const tone = ratio <= .25 ? 'crit' : ratio <= .5 ? 'low' : 'ok';
    return `<li class="ff-status-row${member.id === current ? ' is-current' : ''}${hp <= 0 ? ' is-down' : ''}" data-actor="${E(member.id)}"><span class="ff-status-name">${E(member.name || member.id)}</span><span class="ff-status-hp"><b>${E(Math.max(0, hp || 0))}</b>/${E(max || '?')}</span><span class="ff-bar" data-tone="${tone}"><i style="width:${(ratio * 100).toFixed(1)}%"></i></span></li>`;
  }).join('');
  return `<section class="ff-status" aria-label="Party status"><ul>${rows}</ul></section>`;
}
