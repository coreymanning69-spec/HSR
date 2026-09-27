/* Current top-navigation and Options regression check. Host turns are mocked;
   the test serves the web UI locally and changes no user run or save. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const webRoot = path.resolve(__dirname, '..', 'web');

let browser;
let server;
(async () => {
  let base = process.env.HSR_UI_URL;
  if (!base) {
    server = http.createServer((request, response) => {
      const pathname = new URL(request.url, 'http://127.0.0.1').pathname;
      const file = pathname === '/' ? 'index.html' : pathname.replace(/^\//, '');
      const target = path.resolve(webRoot, file);
      if (!target.startsWith(webRoot) || !fs.existsSync(target) || !fs.statSync(target).isFile()) { response.writeHead(404); response.end(); return; }
      const type = target.endsWith('.js') ? 'text/javascript' : target.endsWith('.css') ? 'text/css' : target.endsWith('.svg') ? 'image/svg+xml' : 'text/html';
      response.writeHead(200, {'content-type': type}); response.end(fs.readFileSync(target));
    });
    server.listen(0, '127.0.0.1');
    await new Promise(resolve => server.once('listening', resolve));
    base = `http://127.0.0.1:${server.address().port}`;
  }
  browser = await chromium.launch({headless: true, channel: process.env.HSR_BROWSER_CHANNEL || 'chrome'});
  const page = await browser.newPage({viewport: {width: 1566, height: 900}});
  page.setDefaultTimeout(10000);
  const pageErrors = [];
  page.on('pageerror', e => pageErrors.push(e.message));

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

  // The client polls /api/health; without a 200 it raises the disconnect modal,
  // which steals focus and scroll from the Options panel under test.
  await page.route('**/api/health', route => route.fulfill({json: {ok: true, result: {state: 'booted'}}}));
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
  await page.waitForFunction(() => !globalThis.HollowStarUI.getStatus().busy);
  await clickSel('[data-action="continue:SANDBOX"]');
  await page.locator('[data-action^="load:"]').waitFor();
  await clickSel('[data-action^="load:"]');
  await page.waitForFunction(() => globalThis.HollowStarUI?.getStatus().phase === 'ready');
  await page.locator('.global-screen-nav').waitFor({state: 'visible'});

  await page.evaluate(() => globalThis.HollowStarUI.navigate('options'));
  await page.locator('#options-visibility').waitFor();
  await clickSel('#options-visibility summary');
  assert(await page.locator('#options-visibility').evaluate(node => node.open), 'Options section should open independently');
  const navigationPref = 'input[data-pref="showNavigation"]';
  assert(await isChecked(navigationPref), 'showNavigation should start checked');
  const card = page.locator('#screen-options .mode-menu-card');
  await card.evaluate(node => { node.scrollTop = Math.min(120, node.scrollHeight - node.clientHeight); });
  const scrollBefore = await card.evaluate(node => node.scrollTop);
  await page.locator(navigationPref).evaluate(node => node.focus({preventScroll: true}));
  await clickSel(navigationPref);
  assert.equal(await page.locator('.top-nav-tabs').evaluate(node => getComputedStyle(node).display), 'none');
  assert(await page.locator('.top-nav-menu-btn').isVisible(), 'Menu recovery control disappeared');
  assert(await page.locator('#options-visibility').evaluate(node => node.open), 'preference update should preserve the expanded section');
  assert.equal(await page.evaluate(() => document.activeElement?.dataset.pref), 'showNavigation', 'preference update should retain control focus');
  assert.equal(await card.evaluate(node => node.scrollTop), scrollBefore, 'preference update should preserve Options scroll position');
  await clickSel('#options-style summary');
  assert(await page.locator('#options-style').evaluate(node => node.open), 'a second Options section should open without closing the first');
  await clickSel(navigationPref);
  assert.notEqual(await page.locator('.top-nav-tabs').evaluate(node => getComputedStyle(node).display), 'none');
  assert(await page.locator('#options-visibility').evaluate(node => node.open), 'second preference update should preserve disclosure state');
  assert(await page.locator('#options-style').evaluate(node => node.open), 'preference update should preserve multiple open sections independently');
  await clickSel('#options-visibility summary');
  assert(!(await page.locator('#options-visibility').evaluate(node => node.open)), 'expanded Options section should collapse on summary activation');
  assert(await page.locator('#options-style').evaluate(node => node.open), 'collapsing one section should leave the other open');
  await clickSel('#options-visibility summary');
  assert(await page.locator('#options-visibility').evaluate(node => node.open), 'collapsed Options section should reopen on summary activation');
  const options = await page.locator('#screen-options .mode-menu-card').evaluate(node => {
    node.querySelectorAll('details').forEach(section => { section.open = true; });
    node.scrollTop = node.scrollHeight;
    return {client: node.clientHeight, scroll: node.scrollHeight,
      footerVisible: node.querySelector('.mode-menu-footer').getBoundingClientRect().bottom <= node.getBoundingClientRect().bottom + 2};
  });
  assert(options.client >= 200 && options.scroll > options.client && options.footerVisible,
    'Options internal scroller must show a usable card and reach its footer');

  // No horizontal overflow at a wide desktop width or at phone width.
  const overflow = () => page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
  assert(!(await overflow()), 'horizontal overflow at desktop width');
  await page.setViewportSize({width: 390, height: 844});
  assert(!(await overflow()), 'horizontal overflow at phone width');

  assert.equal(pageErrors.length, 0, 'uncaught page error(s): ' + pageErrors.join(' | '));

  console.log('ui-options-panels-check: PASS');
})().catch(e => { console.error('ui-options-panels-check: FAIL', e); process.exitCode = 1; })
  .finally(() => { browser?.close(); server?.close(); });
