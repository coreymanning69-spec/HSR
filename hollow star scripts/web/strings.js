// UI and story text lives here, never inline in code, so every line can be
// proofread (and fixed for dictation errors) in one place and a translation is
// one more table. t('key', {n: 3}) fills {n}. A missing key shows the key
// itself so gaps are visible rather than blank.
//
// Scene and dialogue lines stay in their own data files (cutscenes.js,
// dialogues.js); this table is for interface text.

const TABLES = {
  en: {
    'archive.title': 'Memory Archive',
    'archive.subtitle': 'What the Hollow Star keeps between vessels.',
    'archive.sealed': 'Sealed',
    'archive.sealed_blurb': 'The Star has not lived this yet.',
    'archive.new': 'New',
    'archive.remembered': 'Remembered',
    'star.unawakened': 'Unawakened',
    'star.offline': "Connect to the engine to read the Star's memory.",
    'star.vessels': '{n} vessels carried',
    'star.completions': '{n} descents completed',
    'star.falls': '{n} falls remembered',
    'shop.title': 'Meta Shop',
    'shop.subtitle': 'What the Star absorbs, every vessel inherits.',
    'shop.sealed_body': "The Hollow Star has nothing to trade until a vessel's run has ended.",
    'shop.absorb': 'Absorb · {cost} Platinum',
    'shop.mastered': 'Mastered',
    'shop.unlocked_toast': 'The Meta Shop has opened. The Star has something to trade.',
    'codex.title': 'Codex',
    'codex.subtitle': 'Everything the Reliquary has let you learn.',
    'codex.empty': 'Nothing recorded yet. The Reliquary reveals itself one room at a time.',
    'codex.kind.floor': 'Floors', 'codex.kind.monster': 'Bestiary', 'codex.kind.resident': 'Residents',
    'codex.kind.item': 'Items', 'codex.kind.lore': 'Lore', 'codex.kind.location': 'Places',
    'dialogue.unwritten': 'Unwritten line: {speaker} ({id})',
    'run.star_awareness': 'The Hollow Star stirs. Awareness {tier}: {name}.',
    'floor.card': 'Floor {n}',
  },
};

let locale = 'en';
export function setLocale(next) { if (TABLES[next]) locale = next; }
export function t(key, vars = {}) {
  const raw = TABLES[locale]?.[key] ?? TABLES.en[key] ?? key;
  return String(raw).replace(/\{(\w+)\}/g, (_, name) => (vars[name] ?? `{${name}}`));
}
export function missingKeys(keys) { return keys.filter(key => !(key in TABLES.en)); }
