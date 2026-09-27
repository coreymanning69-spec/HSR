// status-fx.js — which persistent visual each public status/condition earns.
//
// One registry replaces the if-chain that used to live in fx-engine's
// reconcileAuras.  A rule matches when the row has any of its `tags` (a
// condition, a truthy status_tags key) or its `when(row)` predicate passes.
// Per socket the highest `priority` wins, so overlapping statuses resolve
// deterministically instead of by write order.  Add a status by adding a rule:
//
//   registerStatusFx({tags: ['frozen'], socket: 'body', aura: 'frost', priority: 3});
//
// Radius defaults follow the socket (head 22, otherwise 28).

export const STATUS_FX = [];

export function registerStatusFx(rule) {
  STATUS_FX.push({priority: 0, ...rule});
  return rule;
}

registerStatusFx({tags: ['shield'], when: row => row.blocking, socket: 'body', aura: 'force', priority: 1});
registerStatusFx({tags: ['poisoned'], socket: 'body', aura: 'poison', priority: 2});
registerStatusFx({tags: ['burning'], socket: 'body', aura: 'fire', priority: 3});
registerStatusFx({when: row => row.invulnerable, socket: 'head', aura: 'radiant'});
registerStatusFx({tags: ['bless', 'blessed'], socket: 'ground', aura: 'radiant'});

export const SOCKETS = ['body', 'head', 'ground'];

export function statusTags(row = {}) {
  const tags = new Set(Array.isArray(row.conditions) ? row.conditions : []);
  for (const [key, value] of Object.entries(row.status_tags || {})) if (value) tags.add(key);
  return tags;
}

// -> {socket: {aura, radius}} for the row's current statuses.
export function wantedAuras(row = {}) {
  const tags = statusTags(row), wanted = {};
  for (const rule of STATUS_FX) {
    if (!(rule.tags?.some(tag => tags.has(tag)) || rule.when?.(row))) continue;
    const held = wanted[rule.socket];
    if (held && held.priority > rule.priority) continue;
    wanted[rule.socket] = {aura: rule.aura, radius: rule.radius ?? (rule.socket === 'head' ? 22 : 28), priority: rule.priority};
  }
  return wanted;
}
