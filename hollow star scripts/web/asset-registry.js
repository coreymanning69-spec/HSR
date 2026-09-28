// Asset registry: art made outside this repo (backgrounds, sprite parts,
// portraits, cutscene panels) is listed in web/assets/manifest.json and looked
// up by id. Code and scene data only ever name ids, so dropping in a new file
// and a manifest line replaces the placeholder with no code change.
//
// Manifest shape:
//   {"images": {"bg.floor-1.town": {"src": "assets/bg/floor1-town.png", "w": 1600, "h": 900}},
//    "sprites": {"vessel": {"parts": {"cloak": "sprite.vessel.cloak", "body": "...", "head": "..."}}}}
// Every "parts" value is itself an image id, so a sprite is a stack of layers.

let manifest = {images: {}, sprites: {}};
const missing = new Set();

export const assetsReady = fetch('assets/manifest.json')
  .then(r => (r.ok ? r.json() : {})).catch(() => ({}))
  .then(data => {
    manifest = {images: data?.images || {}, sprites: data?.sprites || {}};
    return manifest;
  });

export function image(id) {
  const entry = manifest.images[id];
  if (!entry?.src) {
    if (id && !missing.has(id)) { missing.add(id); console.debug?.(`[assets] no image "${id}" yet; using placeholder`); }
    return null;
  }
  return entry;
}

export function sprite(id) {
  return manifest.sprites[id] || null;
}

export function assetStatus() {
  return {images: Object.keys(manifest.images).length, sprites: Object.keys(manifest.sprites).length, missing: [...missing]};
}
