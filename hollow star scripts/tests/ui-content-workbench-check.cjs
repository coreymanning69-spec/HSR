/* Real-host authoring acceptance. Run against an isolated --data-root. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const base = process.env.HSR_UI_URL || 'http://127.0.0.1:8765';
const out = path.resolve(__dirname, '../.local/content-workbench-evidence');

(async () => {
  fs.mkdirSync(out, {recursive: true});
  const browser = await chromium.launch({headless: true, channel: process.env.HSR_BROWSER_CHANNEL || 'chrome'});
  const errors = [];
  let evidence = {};
  try {
    const context = await browser.newContext({viewport: {width: 1500, height: 950}});
    const page = await context.newPage();
    page.on('pageerror', error => errors.push(error.message));
    const idle = () => page.waitForFunction(() => !document.querySelector('main').hasAttribute('aria-busy'));
    const overflow = async label => assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${label}: horizontal overflow`);
    const api = async (command, params = {}) => {
      const response = await context.request.post(base + '/api/host', {data: {id: crypto.randomUUID(), command, compact: false, ...params}});
      const reply = await response.json();
      assert(reply.ok, JSON.stringify(reply));
      return reply.result;
    };
    await page.goto(base + '/');
    await page.getByRole('link', {name: 'Open Content Workbench', exact: true}).waitFor();
    await page.setViewportSize({width: 390, height: 844});
    await overflow('phone title');
    await page.getByRole('link', {name: 'Open Content Workbench', exact: true}).click();
    await page.setViewportSize({width: 1500, height: 950});
    await page.locator('.source').first().waitFor(); await idle();
    await page.getByRole('button', {name: 'Load example', exact: true}).click(); await idle();
    const imported = JSON.parse(await page.locator('#editor').inputValue());
    await page.locator('#file').setInputFiles({name: 'compiler-output.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(imported))});
    await page.getByText('Package imported into the editor.', {exact: true}).waitFor(); await idle();
    const downloadEvent = page.waitForEvent('download');
    await page.getByRole('button', {name: 'Download', exact: true}).click();
    assert.equal((await downloadEvent).suggestedFilename(), 'hollow-star-content-package.json'); await idle();
    const schema = await (await context.request.get(base + '/content-package.schema.json')).json();
    assert.equal(schema.properties.schema_version.const, imported.schema_version);
    await page.getByRole('button', {name: 'Validate package', exact: true}).click();
    await page.getByText('Package validation passed.', {exact: true}).waitFor(); await idle();
    await page.getByRole('button', {name: 'Open preview', exact: false}).click();
    await page.getByRole('heading', {name: 'The Unwritten Crossing', exact: true}).waitFor(); await idle();
    const previewId = await page.evaluate(() => localStorage.getItem('hsr-content-preview'));
    assert(previewId);
    await page.waitForFunction(() => [...document.querySelectorAll('.entity-art')].every(img => img.complete && img.naturalWidth));
    await page.screenshot({path: path.join(out, 'workbench-desktop.png'), fullPage: true});
    await page.getByRole('button', {name: 'Inspect Unlit Lantern', exact: true}).click();
    await page.locator('.event').getByText(/brass lantern/).waitFor(); await idle();
    await page.getByRole('button', {name: 'Study the map', exact: true}).click();
    await page.locator('.event').getByText(/Two places are linked/).waitFor(); await idle();
    await overflow('desktop');
    await page.screenshot({path: path.join(out, 'workbench-inspection.png'), fullPage: true});
    assert(await page.locator('.event').evaluate(el => { const a = el.getBoundingClientRect(), b = document.getElementById('stage').getBoundingClientRect(); return a.top >= b.top && a.bottom <= b.bottom; }), 'inspection receipt must be in view');
    await page.getByRole('button', {name: 'Enter the archive', exact: false}).click();
    await page.getByRole('heading', {name: 'The Quiet Archive', exact: true}).waitFor(); await idle();
    await page.reload();
    await page.getByRole('heading', {name: 'The Quiet Archive', exact: true}).waitFor(); await idle();
    const view = (await api('packet_preview_read', {preview_id: previewId})).public_view;
    assert.equal(view.revision, 3);
    assert.equal(view.scene.id, 'archive');
    evidence = {preview_id: previewId, reached: view.scene.id, persisted_revision: view.revision};

    // Another tab commits before this one. The stale UI must refresh, not replay its intent.
    await api('packet_preview_action', {preview_id: previewId, expected_revision: 3,
      operation_id: crypto.randomUUID(), action: {type: 'navigate', target: 'crossing'}});
    await page.getByRole('button', {name: 'Inspect Blank Folio', exact: true}).click();
    await page.getByText(/Another view changed this preview/).waitFor(); await idle();
    await page.getByRole('heading', {name: 'The Unwritten Crossing', exact: true}).waitFor();
    assert.equal((await api('packet_preview_read', {preview_id: previewId})).public_view.revision, 4);
    evidence.stale_action_rejected = true;

    // A new browser context has no cached state or localStorage, but can resume by identity.
    const fresh = await browser.newContext({viewport: {width: 390, height: 844}});
    const mobile = await fresh.newPage();
    mobile.on('pageerror', error => errors.push(error.message));
    await mobile.goto(base + '/content-workbench.html');
    await mobile.locator('.source').first().waitFor();
    await mobile.waitForFunction(() => !document.querySelector('main').hasAttribute('aria-busy'));
    await mobile.selectOption('#sessions', previewId);
    await mobile.getByRole('button', {name: 'Resume', exact: true}).click();
    await mobile.getByRole('heading', {name: 'The Unwritten Crossing', exact: true}).waitFor();
    await mobile.waitForFunction(() => !document.querySelector('main').hasAttribute('aria-busy'));
    assert(await mobile.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'phone overflow');
    await mobile.getByRole('button', {name: 'Inspect The Cartographer', exact: true}).click();
    await mobile.locator('.event').getByText(/placeholder character/).waitFor();
    await mobile.screenshot({path: path.join(out, 'workbench-phone.png'), fullPage: true});
    evidence.fresh_browser_resume = true;

    // Exercise real source search, range read, provenance, and source-to-screen conversion.
    await page.fill('#query', 'content-compiler-foundation');
    await page.getByRole('button', {name: 'Find', exact: true}).click(); await idle();
    await page.locator('.source').filter({hasText: 'content-compiler-foundation.md'}).first().click();
    await page.getByRole('dialog').waitFor(); await idle();
    await page.fill('#line-start', '7'); await page.fill('#line-count', '10');
    await page.getByRole('button', {name: 'Read range', exact: true}).click(); await idle();
    const excerpt = await page.locator('#source-text').innerText();
    await page.getByRole('button', {name: 'Use excerpt as a screen', exact: true}).click(); await idle();
    const draft = JSON.parse(await page.locator('#editor').inputValue());
    assert.equal(draft.sources.length, 1);
    assert.equal(draft.scenes[0].description, excerpt);
    assert.match(draft.sources[0].sha256, /^[0-9a-f]{64}$/);
    await page.getByRole('button', {name: 'Open preview', exact: false}).click();
    await page.getByRole('heading', {name: 'Source excerpt', exact: true}).waitFor(); await idle();
    assert.equal(await page.locator('.scene-description').innerText(), excerpt);
    evidence.source_hash = draft.sources[0].sha256;
    evidence.source_path = draft.sources[0].path;

    await page.locator('.source').filter({hasText: 'content-compiler-foundation.md'}).first().click();
    await page.fill('#line-start', '1'); await page.fill('#line-count', '35');
    await page.getByRole('button', {name: 'Read range', exact: true}).click(); await idle();
    await page.getByRole('button', {name: 'Interpret as draft', exact: true}).click(); await idle();
    const interpreted = JSON.parse(await page.locator('#editor').inputValue());
    assert(interpreted.scenes.length >= 2);
    assert.match(await page.locator('#interpret-review').innerText(), /Source evidence/);
    assert.match(await page.locator('#interpret-review').innerText(), /Review flags/);
    await page.getByRole('button', {name: 'Open preview', exact: false}).click(); await idle();
    assert(await page.locator('#stage h3').isVisible());
    evidence.interpreted_scenes = interpreted.scenes.length;
    await page.setViewportSize({width: 390, height: 844});
    await overflow('phone interpreted draft');
    await page.screenshot({path: path.join(out, 'workbench-interpreted-phone.png'), fullPage: true});
    await page.setViewportSize({width: 1500, height: 950});

    // Source/package HTML is rendered as inert text, including event receipts.
    const evil = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../web/content-package-example.json'), 'utf8'));
    evil.scenes[0].description = '<img src=x onerror="window.hsrInjected=true">';
    await page.fill('#editor', JSON.stringify(evil));
    await page.getByRole('button', {name: 'Open preview', exact: false}).click();
    await page.getByRole('heading', {name: 'The Unwritten Crossing', exact: true}).waitFor(); await idle();
    assert.equal(await page.locator('.scene-description img').count(), 0);
    assert.equal(await page.evaluate(() => Boolean(window.hsrInjected)), false);
    evidence.inert_text = true;
    assert.deepEqual(errors, []);
    fs.writeFileSync(path.join(out, 'acceptance.json'), JSON.stringify({...evidence, errors, passed: true}, null, 2) + '\n');
    console.log(JSON.stringify({...evidence, errors, passed: true}));
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
