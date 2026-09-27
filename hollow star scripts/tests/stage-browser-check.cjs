/* Browser check for the main display's stage and the Actor Toolbox.
 *
 * Loads actor-toolbox.html headlessly and drives the stage the way a player
 * would: every painted set bakes to real pixels, exits get doors of the right
 * kind, doors open, figures turn and walk and carry Doran's Cleaver the right
 * way for the place, a swing lands damage and leaves wounds, bigger bodies get
 * bigger boxes, and the whole thing stays cheap per frame. No host is involved. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), http = require('node:http');
const root = path.resolve(__dirname, '..'), web = path.join(root, 'web'), out = path.join(root, '.local', 'stage-check');
const types = {'.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml'};

(async () => {
  let browser, server;
  try {
    fs.mkdirSync(out, {recursive: true});
    server = http.createServer((req, res) => {
      let f = decodeURIComponent(new URL(req.url, 'http://local').pathname).replace(/^\/(web\/)?/, '') || 'actor-toolbox.html';
      const target = path.resolve(web, f);
      if (!target.startsWith(web) || !fs.existsSync(target) || !fs.statSync(target).isFile()) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, {'content-type': types[path.extname(target)] || 'application/octet-stream'}); res.end(fs.readFileSync(target));
    });
    server.listen(0, '127.0.0.1'); await new Promise(r => server.once('listening', r));
    try { browser = await chromium.launch({headless: true, channel: 'chrome'}); } catch { browser = await chromium.launch({headless: true}); }
    const page = await browser.newPage({viewport: {width: 1400, height: 800}}), errors = [];
    page.on('pageerror', e => errors.push(e.message)); page.on('console', m => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });
    page.on('response', r => { if (r.status() >= 400 && !/favicon/.test(r.url())) errors.push(`${r.status()} ${r.url()}`); });
    await page.goto(`http://127.0.0.1:${server.address().port}/actor-toolbox.html`);
    await page.waitForFunction('window.toolbox', null, {timeout: 15000});
    await page.waitForTimeout(700);

    // ---- every set bakes real, distinct pixels and maps rooms to themes ------------
    const sets = await page.evaluate(async () => {
      const S = await import('/stage-set.js');
      const rows = [], seen = new Set();
      for (const id of S.THEME_IDS) {
        for (const tod of ['morning', 'night']) {
          const t0 = performance.now(), c = S.bakeSet(id, 640, 400, {seed: 'check', tod, bays: S.layoutExits(S.THEMES[id], [['a', {id: 'tavern'}], ['b', {id: 'market'}]]), dpr: 1});
          const ms = performance.now() - t0, d = c.getContext('2d').getImageData(0, 0, 640, 400).data;
          let lo = 255, hi = 0, sum = 0; for (let i = 0; i < d.length; i += 4 * 97) { const l = (d[i] + d[i + 1] + d[i + 2]) / 3; lo = Math.min(lo, l); hi = Math.max(hi, l); sum += l; }
          seen.add(`${id}:${Math.round(sum / 1000)}`);
          rows.push({id, tod, ms: Math.round(ms), range: Math.round(hi - lo)});
        }
      }
      const ex = (theme, list) => S.layoutExits(S.THEMES[theme], list.map((id, i) => [`r${i}`, {id}])).map(b => [b.id, b.kind]);
      return {rows, count: S.THEME_IDS.length, themes: {market: S.themeFor({id: 'market'}), tavern: S.themeFor({id: 'tavern'}), machine: S.themeFor({name: 'The Machine Works', terrain: 'Conveyor lanes, metal gantries, steam vents'}),
        sea: S.themeFor({terrain: 'Drowned decks, broken piers, dark water'}), palace: S.themeFor({name: 'The Opulent Palace and Cocoon'}), dragons: S.themeFor({name: 'The Three Dragons'}), unknown: S.themeFor({id: 'zz-77'})},
        exits: ex('market', ['tavern', 'guardhouse', 'alley', 'well']), indoor: ex('tavern', ['market']), tod: {night: S.todOf('NIGHT'), junk: S.todOf('x')}};
    });
    assert.ok(sets.count >= 20, `theme count ${sets.count}`);
    for (const r of sets.rows) { assert.ok(r.range > 40, `${r.id}/${r.tod} baked flat (${r.range})`); assert.ok(r.ms < 600, `${r.id} bake ${r.ms}ms`); }
    assert.deepEqual(sets.themes, {market: 'market', tavern: 'tavern', machine: 'foundry', sea: 'drowned', palace: 'palace', dragons: 'lair', unknown: sets.themes.unknown});
    assert.ok(['dungeon', 'crypt', 'cave'].includes(sets.themes.unknown), 'unknown rooms get a descent set');
    assert.deepEqual(sets.exits, [['tavern', 'wood'], ['guardhouse', 'iron'], ['alley', 'arch'], ['well', 'path']]);
    assert.deepEqual(sets.indoor, [['market', 'arch']], 'an indoor path becomes an archway');
    assert.equal(sets.tod.night, 'night'); assert.equal(sets.tod.junk, 'evening');

    // ---- doors open ----------------------------------------------------------------
    await page.evaluate(() => { window.toolbox.stage.toggleDoor('a', true); });
    await page.waitForTimeout(900);
    const door = await page.evaluate(() => window.toolbox.stage.snapshot().doors.find(d => d.key === 'a').open);
    assert.ok(door > .9, `door opened (${door})`);
    await page.evaluate(() => { window.toolbox.stage.toggleDoor('a', false); });

    // ---- walking: turn first, face where it goes, stride rate reaches the rig ----------
    const walk = await page.evaluate(async () => {
      const s = window.toolbox.stage, w = s.world, e = w.get('doran'), rec = s.thing('doran'), sleep = ms => new Promise(r => setTimeout(r, ms));
      s.clearThings({keepLead: true}); e.x = 20; e.d = .5; e.face = 1; w.walkTo('doran', 6, .5); const seen = new Set(); let gait = 0, faces = new Set();
      for (let i = 0; i < 40; i++) { await sleep(50); seen.add(rec.node.dataset.beat || ''); gait = Math.max(gait, Number(rec.node.dataset.gait || 0)); faces.add(rec.node.dataset.facing); }
      return {x: e.x, face: e.face, facing: rec.node.dataset.facing, beats: [...seen], gait, faces: [...faces], carry: rec.node.dataset.carry};
    });
    assert.ok(walk.x < 12, `walked left (${walk.x})`);
    assert.equal(walk.face, -1); assert.equal(walk.facing, '-1');
    assert.ok(walk.beats.includes('move'), 'move beat while walking'); assert.ok(walk.gait > .3, `gait ${walk.gait}`);
    assert.equal(walk.carry, 'stowed', 'sheathed on his back in a friendly place');

    // ---- carry follows the place and the moment; swing lands damage and wounds ---------
    const fight = await page.evaluate(async () => {
      const T = window.toolbox, s = T.stage, w = s.world, sleep = ms => new Promise(r => setTimeout(r, ms));
      s.clearThings({keepLead: true}); const d = w.get('doran'); d.x = 8; d.d = .5; d.face = 1; d.hp = d.max;
      const dummy = s.spawnProp('dummy', {id: 'dm', x: 14, d: .5}), post = s.spawnProp('post', {id: 'ps', x: 40, d: .5}), start = dummy.ent.hp;
      const before = s.thing('doran').carry;
      s.setCarry('doran', 'shoulder'); await sleep(200); const shoulder = s.thing('doran').node.dataset.carry;
      s.setCarry('doran', 'auto'); await sleep(200);
      s.swing('doran', 'chop'); await sleep(700); const drawn = s.thing('doran').node.dataset.carry, swingAttr = s.thing('doran').node.dataset.swing;
      await sleep(1400);
      const hit = {hp: dummy.ent.hp, start, wounds: dummy.ent.wounds.length, postHp: post.ent.hp, postMax: post.ent.max};
      const fog = s.fx.p.length; await sleep(3400);
      return {before, shoulder, drawn, swingAttr, hit, later: s.thing('doran').node.dataset.carry, swingAfter: s.thing('doran').node.dataset.swing || '', fog};
    });
    assert.equal(fight.before, 'stowed'); assert.equal(fight.shoulder, 'shoulder'); assert.equal(fight.drawn, 'ready', 'a swing draws the blade');
    assert.equal(fight.swingAttr, 'chop'); assert.equal(fight.swingAfter, '');
    assert.ok(fight.hit.hp < fight.hit.start, 'the dummy took damage'); assert.ok(fight.hit.wounds >= 1, 'and carries the cut');
    assert.equal(fight.hit.postHp, fight.hit.postMax, 'something out of reach was left alone');
    assert.equal(fight.later, 'stowed', 'the blade goes back on his back after the fight');

    // ---- bodies: giants get bigger boxes and bigger hit boxes ---------------------------
    const sizes = await page.evaluate(async () => {
      const T = window.toolbox, s = T.stage, sleep = ms => new Promise(r => setTimeout(r, ms));
      s.clearThings({keepLead: true}); const w = s.st.worldW, giant = T.spawn('giant', {id: 'gi', x: w * .7, d: .6}), gob = T.spawn('goblin', {id: 'gb', x: w * .5, d: .6}), hero = T.spawn('hero', {id: 'hr', x: w * .3, d: .6});
      await sleep(400); const px = rec => rec.node.getBoundingClientRect().height;
      const snap = Object.fromEntries(s.snapshot().things.map(t => [t.id, t]));
      s.setDebug(true); await sleep(200); s.setDebug(false);
      return {giant: snap.gi.height, gob: snap.gb.height, hero: snap.hr.height, doran: snap.doran.height, boxes: [px(giant), px(gob), px(hero)], reach: [snap.gi.reach, snap.gb.reach]};
    });
    assert.ok(sizes.giant > 12 && sizes.gob < 5.2 && Math.abs(sizes.doran - 7.08) < .05, JSON.stringify(sizes));
    assert.ok(sizes.boxes[0] > sizes.boxes[2] * 2 && sizes.boxes[1] < sizes.boxes[2], 'drawn boxes follow size class');
    assert.ok(sizes.reach[0] > sizes.reach[1] * 2);

    // ---- picking: a door, an actor and the ground resolve where they are drawn ---------
    const picks = await page.evaluate(() => {
      const s = window.toolbox.stage, b = s.st.bays[0], door = s.pick(s.st.L + b.x * s.st.UW, s.st.H * s.st.theme.cam.back - 60), any = s.thing('doran'), p = s.project(any.ent.x, any.ent.d);
      return {door: door.kind, doorKey: door.bay?.key, actor: s.pick(p.sx, p.sy - 60).kind, ground: s.pick(400, s.st.H * .85).kind};
    });
    assert.equal(picks.door, 'door'); assert.equal(picks.ground, 'ground');
    assert.ok(['actor', 'prop'].includes(picks.actor));

    // ---- a party keeps together, and the pointer says what a click would do -------------------
    const party = await page.evaluate(async () => {
      const {createStage} = await import('/stage-view.js'), sleep = ms => new Promise(r => setTimeout(r, ms));
      const s = createStage({mode: 'toolbox', follow: true}); s.el.style.cssText = 'position:fixed;left:0;top:0;width:1000px;height:520px;z-index:9';
      document.body.append(s.el); s.setRoom({themeId: 'market', tod: 'day', roomId: 'follow', exits: [['a', {id: 'tavern'}], ['b', {id: 'alley'}]]}); s.start(); await sleep(300);
      const hero = (id, x) => s.spawnActor({id, item: {name: id.toUpperCase(), race_id: 'human', equipment: []}, weapon: 'none', team: 'party', role: 'party', x, d: .6});
      hero('a', 6); hero('b', 4.5); hero('c', 3); s.setLead('a');
      await s.walkLead(19, .5); await sleep(2600);
      const lead = s.world.get('a'), gaps = ['b', 'c'].map(id => Math.abs(s.world.get(id).x - lead.x));
      const facing = ['a', 'b', 'c'].map(id => s.world.get(id).face);
      const bay = s.st.bays[0], sx = s.st.L + bay.x * s.st.UW, sy = s.st.H * s.st.theme.cam.back - 50, box = s.el.getBoundingClientRect();
      s.el.dispatchEvent(new PointerEvent('pointermove', {clientX: box.left + sx, clientY: box.top + sy, bubbles: true}));
      const tip = s.el.querySelector('.ws-tip'), label = tip.hidden ? '' : tip.textContent;
      s.el.dispatchEvent(new PointerEvent('pointerleave', {bubbles: true}));
      const hidden = tip.hidden; s.destroy();
      return {gaps, facing, label, hidden};
    });
    assert.ok(party.gaps.every(g => g < 7), `followers stayed close (${party.gaps})`);
    assert.deepEqual([...new Set(party.facing)], [1], 'the party faces the way it travelled');
    assert.match(party.label, /Tavern/); assert.ok(party.hidden, 'the label goes when the pointer leaves');

    // ---- cost ------------------------------------------------------------------------------
    await page.waitForTimeout(400);
    const stats = await page.evaluate(() => window.toolbox.stage.stats());
    assert.ok(stats.tickMs < 6, `stage tick ${stats.tickMs}ms`);
    await page.screenshot({path: path.join(out, 'toolbox.png')});
    assert.deepEqual(errors, []);
    console.log(`stage check passed: ${sets.count} sets, tick ${stats.tickMs}ms, bake max ${Math.max(...sets.rows.map(r => r.ms))}ms`);
  } finally { await browser?.close(); server?.close(); }
})().catch(error => { console.error(error); process.exit(1); });
