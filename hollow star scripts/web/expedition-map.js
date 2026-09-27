// Expedition route map (Encounters and Atlas). Markup only: the host owns the
// seeded graph, reachability and every node's resolution.

const GLYPHS = {fight: '⚔', elite: '☠', rest: '☾', loot: '◆', shop: '¤', hazard: '⚠', social: '☵', boss: '♛'};
const W = 96; const H = 62; const PAD = 30;

export function nodeGlyph(type) { return GLYPHS[type] || '•'; }

export function routeMap(graph, {selected = '', compact = false, E} = {}) {
  const columns = graph?.columns || [];
  if (!columns.length) return '';
  const tallest = Math.max(...columns.map(column => column.length));
  const width = PAD * 2 + (columns.length - 1) * W;
  const height = PAD * 2 + Math.max(0, tallest - 1) * H;
  const place = new Map();
  columns.forEach((column, c) => column.forEach((node, i) => {
    const offset = (tallest - column.length) * H / 2;
    place.set(node.id, {x: PAD + c * W, y: PAD + offset + i * H});
  }));
  const links = columns.flat().flatMap(node => (node.links || []).filter(id => place.has(id)).map(id => {
    const a = place.get(node.id); const b = place.get(id);
    const walked = node.reach === 'visited' || node.reach === 'current';
    return `<line class="xp-link${walked ? ' is-walked' : ''}" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"/>`;
  })).join('');
  const nodes = columns.flat().map(node => {
    const p = place.get(node.id);
    const pick = node.reach === 'available';
    const cls = `xp-node xp-${E(node.type)} is-${E(node.reach || 'locked')}${node.id === selected ? ' is-selected' : ''}`;
    const attrs = pick && !compact ? ` role="button" tabindex="0" data-xp-node="${E(node.id)}"` : '';
    const label = `${node.label || node.type}${node.ladder ? `, ${node.ladder.waves.length} wave ladder` : ''}, ${node.reach || 'locked'}`;
    return `<g class="${cls}" transform="translate(${p.x} ${p.y})"${attrs} aria-label="${E(label)}"><title>${E(label)}</title><circle r="${node.type === 'boss' ? 19 : 15}"/><text dy="5" text-anchor="middle">${E(nodeGlyph(node.type))}</text></g>`;
  }).join('');
  return `<svg class="xp-map${compact ? ' is-compact' : ''}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" role="group" aria-label="Floor ${E(graph.floor)} route">${links}${nodes}</svg>`;
}
