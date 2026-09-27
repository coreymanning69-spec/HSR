// Shared prelude for Node probes that run web/ modules headlessly.
//
// The package is CommonJS, so web/*.js cannot be imported in place. Every
// module is copied into a throwaway directory marked {"type":"module"}, where
// their ordinary relative imports ('./actor-core.js', './skeletal-rig.js')
// resolve exactly as they do in the browser. Probes then call
// `await webModule('wren-rig.js')`. Prepend this text to the probe source and
// run it with `node --input-type=module -e` from the hollow star scripts root.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const webDir = fs.mkdtempSync(path.join(os.tmpdir(), 'hsr-web-'));
fs.writeFileSync(path.join(webDir, 'package.json'), '{"type":"module"}');
for (const name of fs.readdirSync('web')) if (name.endsWith('.js')) fs.copyFileSync(path.join('web', name), path.join(webDir, name));
process.on('exit', () => { try { fs.rmSync(webDir, {recursive: true, force: true}); } catch {} });
const webModule = name => import(pathToFileURL(path.join(webDir, name)).href);
// A recording 2D context: every call is a no-op, fills are logged by colour.
const noop = () => {}, grad = {addColorStop: noop};
let painted = [];
const ctx = new Proxy({}, {get: (t, k) => k in t ? t[k] : /^create(Linear|Radial)Gradient$/.test(k) ? () => grad
  : k === 'fill' ? () => painted.push(t.fillStyle) : noop, set: (t, k, v) => (t[k] = v, true)});
