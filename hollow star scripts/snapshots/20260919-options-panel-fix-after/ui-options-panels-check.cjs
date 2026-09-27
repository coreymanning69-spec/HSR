/* Regression check for the Options screen's Connections/Information/Clock
   panels (web/app.js connectionsBar/informationPanel/clockPanel) and the
   "Show Information"/"Show Clock" quick-link buttons.
   Run with Node and Playwright available; local web server required.
   Uses a mocked /api/host route, never a real run or user save.

   Interactions go through page.evaluate(el => el.click()) on a resolved DOM
   node rather than Playwright's locator().click(): the interface has
   persistent decorative animation (the intro card float, the tick-pulse
   indicator, drag transitions) that Playwright's actionability/stability
   checks never settle against, and locator().click({force:true}) proved
   unreliable here for reasons not traced further. A raw native click on the
   currently-resolved node is what a real user's click does and is what
   every prior manual check in this session's history actually used. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const base = process.env.HSR_UI_URL || 'http://127.0.0.1:8765';

let browser;
(async () => {
  browser = await chromium.launch({headless: true, channel: process.env.HSR_BROWSER_CHANNEL || 'chrome'});
  const page = await browser.newPage({viewport: {width: 1566, height: 900}});
  page.setDefaultTimeout(10000);
  const pageErrors = [];
  page.on('pageerror', e => pageErrors.push(e.message));

  const present = id => page.waitForFunction(idArg => !!document.getElementById(idArg), id);
  const absent = id => page.waitForFunction(idArg => !document.getElementById(idArg), id);
  const clickSel = sel => page.evaluate(s => { const el = document.querySelector(s); if (!el) throw new Error('not found: ' + s); el.click(); }, sel);
  const clickButtonByText = text => page.evaluate(t => {
    const el = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === t);
    if (!el) throw new Error('button not found: ' + t);
    el.click();
  }, text);
  const isChecked = sel => page.evaluate(s => !!document.querySelector(s)?.checked, sel);

  const view = {
    schema: 'hollow-star-public-view-1', run_id: 'options-panels-fixture', mode: 'DESIGN', status: 'active',
    party: [{id: 'p0', name: 'Test adventurer', hp: 32, max_hp: 40, armor_class: 16}],
    room: {id: '1:1', name: 'Public test room', visible_tells: ['Visible lamp']},
    opposition: [], inventory: [], progression: {gold: 24},
    available_actions: [{id: 'inspect', label: 'Inspect'}], recent_receipts: [],
  };
  const run = {run_id: view.run_id, mode: 'SANDBOX', context: {host_mode: 'SANDBOX'}, status: 'active'};

  await page.route('**/api/host', route => {
    const req = route.request().postDataJSON();
    let payload;
    if (req.command === 'health') payload = {ok: true};
    else if (req.command === 'list_runs') payload = {ok: true, result: {runs: [run]}};
    else if (req.command === 'inspect_run') payload = {ok: true, result: {run}};
    else payload = {ok: true, v: 'hollow-star-transfer-capsule-1', view, receipt: {message: 'ok'}, run: view.run_id, result: {run_id: view.run_id}};
    return route.fulfill({json: payload});
  });

  await page.goto(base + '/');
  await page.waitForFunction(() => [...document.querySelectorAll('button')].some(b => b.textContent.trim() === 'Simulation Mode'));
  await clickButtonByText('Simulation Mode');
  await page.waitForTimeout(400);
  await clickButtonByText('Resume');
  await page.waitForTimeout(400);
  await clickButtonByText('Resume');
  await page.waitForFunction(() => globalThis.HollowStarUI?.getStatus().phase === 'ready');

  // All three panels render by default.
  await present('connections-panel');
  await present('information-panel');
  await present('clock-panel');

  await page.evaluate(() => globalThis.HollowStarUI.navigate('options'));
  await page.locator('#options-visibility').waitFor();
  await page.evaluate(() => document.getElementById('options-visibility').setAttribute('open', ''));
  await page.waitForTimeout(200);

  // Each visibility checkbox actually hides/shows its panel (the historical
  // bug: these saved to localStorage with zero visible effect).
  for (const [pref, id] of [['showConnections', 'connections-panel'], ['showInformation', 'information-panel'], ['showClock', 'clock-panel']]) {
    const sel = `input[data-pref="${pref}"]`;
    assert(await isChecked(sel), `${pref} should start checked`);
    await clickSel(sel);
    assert(!(await isChecked(sel)), `${pref} did not uncheck on click`);
    await absent(id);
    await clickSel(sel);
    assert(await isChecked(sel), `${pref} did not re-check on click`);
    await present(id);
  }

  // The preference round-trips through localStorage.
  await clickSel('input[data-pref="showConnections"]');
  const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('hsr-display-preferences')).showConnections);
  assert.equal(stored, false, 'showConnections did not persist to localStorage');
  await clickSel('input[data-pref="showConnections"]');
  await present('connections-panel');

  // The size selects resize the panel (regression check for the historical
  // no-op, and for the clock/information overlap bug the CSS reconciliation
  // introduced when a size other than "standard" is chosen).
  const selectValue = (sel, value) => page.evaluate(([s, v]) => {
    const el = document.querySelector(s);
    el.value = v;
    el.dispatchEvent(new Event('change', {bubbles: true}));
  }, [sel, value]);
  const boundingBox = id => page.evaluate(idArg => {
    const r = document.getElementById(idArg).getBoundingClientRect();
    return {x: r.x, width: r.width};
  }, id);

  const infoBefore = await boundingBox('information-panel');
  await selectValue('select[data-pref="informationSize"]', 'large');
  await page.waitForTimeout(150);
  const infoAfter = await boundingBox('information-panel');
  assert(infoAfter.width > infoBefore.width, 'informationSize=large did not widen the panel');
  const clockBox = await boundingBox('clock-panel');
  assert(clockBox.x + clockBox.width <= infoAfter.x + 1, 'clock panel overlaps information panel at informationSize=large');
  await selectValue('select[data-pref="informationSize"]', 'standard');

  // The quick-link buttons: historically these threw
  // "'#focus-panel:information-panel' is not a valid selector" (a
  // .slice('focus-panel:') call missing .length) and crashed the app.
  await clickSel('input[data-pref="showInformation"]');
  await absent('information-panel');
  await clickButtonByText('Show Information');
  await present('information-panel');
  await clickSel('input[data-pref="showClock"]');
  await absent('clock-panel');
  await clickButtonByText('Show Clock');
  await present('clock-panel');

  // The connections panel expands and a manual ping updates the status text.
  await clickSel('#connections-panel .conn-summary');
  await page.waitForFunction(() => !!document.querySelector('#connections-panel .conn-details'));
  await clickButtonByText('Ping now');
  await page.waitForFunction(() => document.querySelector('#connections-panel [data-link="status"]')?.textContent === 'Connected');

  // No horizontal overflow at a wide desktop width or at phone width.
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
  assert(!(await overflow()), 'horizontal overflow at desktop width');
  await page.setViewportSize({width: 390, height: 844});
  assert(!(await overflow()), 'horizontal overflow at phone width');

  assert.equal(pageErrors.length, 0, 'uncaught page error(s): ' + pageErrors.join(' | '));

  console.log('ui-options-panels-check: PASS');
})().catch(e => { console.error('ui-options-panels-check: FAIL', e); process.exitCode = 1; })
  .finally(() => browser?.close());
