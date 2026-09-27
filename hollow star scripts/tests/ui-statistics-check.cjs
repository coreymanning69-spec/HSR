/* Real-host Continue and Statistics smoke check against isolated --hostless data. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.HSR_UI_URL || 'http://127.0.0.1:8765';
const out = path.resolve(__dirname, '../.local/statistics-evidence');

(async () => {
  fs.mkdirSync(out, {recursive: true});
  const browser = await chromium.launch({headless: true, channel: process.env.HSR_BROWSER_CHANNEL || 'chrome'});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 900}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const request = async (command, extra = {}) => {
      const reply = await (await page.request.post(base + '/api/host', {data: {id: crypto.randomUUID(), command, ...extra}})).json();
      assert(reply.ok, JSON.stringify(reply)); return reply.result;
    };
    await request('boot', {mode: 'SANDBOX'});
    const runId = `stats-ui-${Date.now().toString(36)}`;
    await request('create_run', {mode: 'SANDBOX', run_id: runId, party: ['Doran'],
      opposition: ['Townsperson'], scenario: 'floor_one_life', seed: runId});
    await request('design_start', {run_id: runId});
    await request('save_run', {run_id: runId});
    await page.goto(base + '/');
    await page.getByRole('button', {name: 'Simulation Mode', exact: true}).click();
    await page.locator('[data-action="continue:SANDBOX"]').click();
    await page.locator('.run-row').filter({hasText: runId}).waitFor();
    await page.screenshot({path: path.join(out, 'continue-desktop.png'), fullPage: true});
    await page.locator('.run-row').filter({hasText: runId}).locator('[data-action^="load:"]').click();
    await page.waitForFunction(() => window.HollowStarUI?.getStatus().phase === 'ready');
    await page.reload();
    await page.getByRole('button', {name: 'Simulation Mode', exact: true}).click();
    await page.locator('[data-action="menu:statistics"]').click();
    await page.locator('[data-action="load-statistics-all"]').click();
    await page.locator('.statistics-save-list').getByText(runId).waitFor();
    await page.locator(`[data-action="statistics-save:${runId}"]`).click();
    await page.getByText('Selected save', {exact: true}).waitFor();
    assert(await page.locator('.mode-menu-card').evaluate(node => {
      if (node.scrollHeight <= node.clientHeight) return false;
      node.scrollTop = node.scrollHeight;
      const footer = node.querySelector('.mode-menu-footer').getBoundingClientRect();
      return footer.bottom <= node.getBoundingClientRect().bottom + 1;
    }), 'statistics detail and footer must be reachable in the internal scroller');
    await page.screenshot({path: path.join(out, 'statistics-desktop.png'), fullPage: true});
    await page.setViewportSize({width: 390, height: 844});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'phone horizontal overflow');
    await page.screenshot({path: path.join(out, 'statistics-phone.png'), fullPage: true});
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({passed: true, run_id: runId, errors}));
  } finally { await browser.close(); }
})().catch(error => {console.error(error); process.exitCode = 1;});
