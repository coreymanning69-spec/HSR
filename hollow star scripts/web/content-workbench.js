const $ = id => document.getElementById(id);
const state = {offset: 0, search: null, source: null, sourcePath: null, view: null, pendingStart: null, pendingAction: null, busy: false};
const node = (tag, text, className) => { const value = document.createElement(tag); if (text != null) value.textContent = text; if (className) value.className = className; return value; };
const status = (text, error = false) => { $('status').textContent = text; $('status').classList.toggle('error', error); };
const operation = () => crypto.randomUUID();

async function api(command, params = {}) {
  const response = await fetch('/api/host', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id: operation(), command, compact: false, ...params})});
  const reply = await response.json();
  if (!reply.ok) { const error = new Error(reply.error?.message || reply.error?.code || `Request failed (${response.status})`); error.code = reply.error?.code; throw error; }
  return reply.result;
}

async function task(fn) {
  if (state.busy) return;
  state.busy = true;
  document.body.classList.add('busy');
  document.querySelector('main').setAttribute('aria-busy', 'true');
  try { await fn(); }
  catch (error) { status(error.message || String(error), true); }
  finally { state.busy = false; document.body.classList.remove('busy'); document.querySelector('main').removeAttribute('aria-busy'); }
}

function button(text, fn, className = '') {
  const value = node('button', text, className); value.type = 'button';
  value.addEventListener('click', () => task(fn)); return value;
}

function packageValue() {
  const text = $('editor').value;
  if (!text.trim()) throw new Error('Load a source or a package first.');
  try { return JSON.parse(text); }
  catch (error) { throw new Error(`Package JSON: ${error.message}`); }
}

function setPackage(value) {
  $('editor').value = JSON.stringify(value, null, 2);
  state.pendingStart = null;
  $('interpret-review').textContent = '';
  $('validation').textContent = 'Draft loaded. Validate it, then open a preview.';
  $('validation').classList.remove('invalid');
}

function reportValidation(report) {
  const counts = report.counts;
  $('validation').textContent = `${counts.scenes} scenes · ${counts.entities} entities · ${counts.sources} source references\n` +
    (counts.sources ? 'Source hashes verified. ' : '') + 'Navigation and inspection ready. Mechanics unbound.' +
    (report.warnings.length ? '\n' + report.warnings.join('\n') : '');
  $('validation').classList.remove('invalid');
}

async function search() {
  status('Searching local sources…');
  const result = await api('source_search', {query: $('query').value, include_archives: $('archives').checked, offset: state.offset, limit: 30});
  state.search = result;
  $('source-list').replaceChildren();
  for (const row of result.sources) {
    const item = button('', () => openSource(row), 'source');
    item.append(node('strong', row.name), node('small', `${row.classification} · ${row.format.toUpperCase()} · ${(row.bytes / 1024).toFixed(1)} KB`), node('small', row.path));
    if (row.snippet) item.append(node('span', row.snippet, 'snippet'));
    if (!row.text_readable) item.append(node('small', 'Asset reference · text adapter unavailable'));
    $('source-list').append(item);
  }
  if (!result.sources.length) $('source-list').append(node('p', 'No matching sources. Try a filename or a shorter phrase.', 'muted'));
  $('source-count').textContent = `${result.total} matches · ${result.scanned} files checked`;
  $('source-prev').disabled = !state.offset;
  $('source-next').disabled = !result.has_more;
  const limits = result.skipped || result.truncated ? ` ${result.skipped} sources skipped; ${result.truncated ? 'inventory limit reached' : 'format or search limits apply'}.` : '';
  status(`Local library ready.${limits}`);
}

async function openSource(row) {
  if (!row.text_readable) { status('This is an asset reference. Search for its text extract to make a source screen.'); return; }
  state.source = null;
  state.sourcePath = row.path;
  $('line-start').value = row.line || 1;
  $('line-count').value = 100;
  await readRange();
  if (!$('source-dialog').open) $('source-dialog').showModal();
}

async function readRange() {
  const result = await api('source_read', {path: state.sourcePath, start_line: Number($('line-start').value),
    line_count: Number($('line-count').value), include_archives: $('archives').checked,
    ...(state.source ? {expected_sha256: state.source.sha256} : {})});
  state.source = result.source;
  $('source-title').textContent = state.source.path.split('/').pop();
  $('source-path').textContent = state.source.path;
  $('source-text').textContent = state.source.text;
  $('source-text').scrollTop = 0;
  $('source-receipt').textContent = `Lines ${state.source.start_line}–${state.source.end_line} of ${state.source.total_lines} · ${state.source.classification} · SHA-256 ${state.source.sha256.slice(0, 16)}…`;
  $('headings').replaceChildren(new Option('Choose a heading…', ''));
  for (const heading of state.source.headings) $('headings').append(new Option(`${heading.line} · ${heading.title}`, String(heading.line)));
  status('Source loaded read-only.');
}

async function useSource() {
  if (!state.source) return;
  const result = await api('packet_starter', {path: state.source.path, start_line: state.source.start_line,
    line_count: state.source.end_line - state.source.start_line + 1, expected_sha256: state.source.sha256,
    include_archives: $('archives').checked});
  setPackage(result.package);
  reportValidation(result);
  $('source-dialog').close();
  status('The selected excerpt is now a screen in the package editor.');
}

async function interpretSource() {
  if (!state.source) return;
  const result = await api('packet_interpret', {path: state.source.path, start_line: state.source.start_line,
    line_count: state.source.end_line - state.source.start_line + 1, expected_sha256: state.source.sha256,
    include_archives: $('archives').checked});
  setPackage(result.package);
  reportValidation(result);
  const evidence = result.package.sources.map(row => `${row.path}:${row.start_line}–${row.end_line} · ${row.sha256.slice(0, 16)}…`);
  const flags = result.review_flags.map(row => `Line ${row.line}: ${row.message}`);
  $('interpret-review').textContent = `Source evidence (${evidence.length})\n${evidence.join('\n')}\nReview flags (${flags.length})${flags.length ? '\n' + flags.join('\n') : ''}`;
  $('source-dialog').close();
  status('Local interpretation draft loaded. Review the source evidence and flags before preview.');
}

async function sessions() {
  const result = await api('packet_preview_list');
  $('sessions').replaceChildren(new Option('Choose a preview…', ''));
  for (const row of result.previews) $('sessions').append(new Option(`${row.title} · r${row.revision} · ${row.preview_id.slice(-6)}`, row.preview_id));
  if (state.view) $('sessions').value = state.view.preview_id;
}

function render(view, showReceipt = false) {
  const focusChange = state.view?.preview_id === view.preview_id && state.view.revision !== view.revision;
  state.view = view;
  state.pendingAction = null;
  localStorage.setItem('hsr-content-preview', view.preview_id);
  const stage = $('stage'); stage.replaceChildren(); stage.dataset.theme = view.theme;
  stage.append(node('p', `${view.package.universe} / ${view.kind}`, 'eyebrow'), node('h3', view.scene.title), node('p', view.scene.description, 'scene-description'));
  const grid = node('div', null, 'entity-grid');
  for (const entity of view.entities) {
    const card = node('article', null, `entity-card entity-${entity.kind}`);
    const symbol = node('div', {character: '♙', item: '◇', prop: '⌑'}[entity.kind], 'entity-symbol'); symbol.setAttribute('aria-hidden', 'true');
    if (entity.art) { const art = node('img'); art.src = entity.art.src; art.alt = entity.name + ' — presentation art'; art.className = 'entity-art'; symbol.replaceChildren(art); symbol.classList.add('has-art'); symbol.removeAttribute('aria-hidden'); }
    card.append(symbol, node('h4', entity.name), node('p', entity.kind + (entity.inspected ? ' · inspected' : '')),
      button(`Inspect ${entity.name}`, () => act({type: 'inspect', target: entity.id})));
    for (const choice of entity.interactions) card.append(button(choice.label, () => act({type: 'interact', target: entity.id, interaction_id: choice.id})));
    grid.append(card);
  }
  stage.append(grid);
  if (view.exits.length) {
    const exits = node('nav', null, 'scene-exits'); exits.setAttribute('aria-label', 'Scene exits');
    for (const exit of view.exits) exits.append(button(`${exit.label} →`, () => act({type: 'navigate', target: exit.id})));
    stage.append(exits);
  }
  if (view.last_event) {
    const receipt = node('section', null, 'event'); receipt.setAttribute('aria-live', 'polite');
    receipt.append(node('strong', view.last_event.name || 'Scene transition'), node('p', view.last_event.text));
    stage.append(receipt);
    if (showReceipt && focusChange) { receipt.tabIndex = -1; receipt.focus({preventScroll: true}); }
    if (showReceipt) requestAnimationFrame(() => { stage.scrollTop = Math.max(0, receipt.offsetTop - stage.clientTop - 16); });
  }
  if (!showReceipt) { stage.scrollTop = 0; if (focusChange) { const heading = stage.querySelector('h3'); heading.tabIndex = -1; heading.focus({preventScroll: true}); } }
  const selected = Array.from($('sessions').options).find(option => option.value === view.preview_id);
  if (selected) selected.textContent = `${view.package.title} · r${view.revision} · ${view.preview_id.slice(-6)}`;
  $('preview-meta').textContent = `Revision ${view.revision} · ${view.visited_count} scenes visited · ${view.package_hash.slice(0, 10)}`;
  $('restore-package').disabled = false;
}

async function start() {
  const value = packageValue(), signature = JSON.stringify(value);
  if (state.pendingStart?.signature !== signature) state.pendingStart = {signature, operation_id: operation()};
  status('Validating references and opening a preview…');
  const result = await api('packet_preview_start', {package: value, operation_id: state.pendingStart.operation_id});
  render(result.public_view); reportValidation(result.validation); state.pendingStart = null;
  await sessions(); status('Preview opened. Every action is validated and saved by Python.');
}

async function act(action) {
  const view = state.view;
  const signature = JSON.stringify([view.preview_id, view.revision, action]);
  if (state.pendingAction?.signature !== signature) state.pendingAction = {signature, operation_id: operation()};
  try {
    const result = await api('packet_preview_action', {preview_id: view.preview_id, action,
      expected_revision: view.revision, operation_id: state.pendingAction.operation_id});
    render(result.public_view, action.type !== 'navigate'); status('Preview saved.');
  } catch (error) {
    if (error.code === 'PREVIEW_CONFLICT') {
      const refreshed = await api('packet_preview_read', {preview_id: view.preview_id});
      render(refreshed.public_view);
      status('Another view changed this preview. Refreshed to the current scene; choose your action again.', true);
    } else throw error;
  }
}

async function resume(previewId) {
  if (!previewId) throw new Error('Choose a saved preview first.');
  render((await api('packet_preview_read', {preview_id: previewId})).public_view);
  status('Saved preview restored.');
}

$('search-form').addEventListener('submit', event => {event.preventDefault(); state.offset = 0; task(search);});
$('source-prev').addEventListener('click', () => task(async () => {state.offset = Math.max(0, state.offset - 30); await search();}));
$('source-next').addEventListener('click', () => task(async () => {state.offset += 30; await search();}));
$('archives').addEventListener('change', () => task(async () => {state.offset = 0; await search();}));
$('close-source').addEventListener('click', () => $('source-dialog').close());
$('read-range').addEventListener('click', () => task(readRange));
$('headings').addEventListener('change', () => {if ($('headings').value) {$('line-start').value = $('headings').value; task(readRange);}});
$('use-source').addEventListener('click', () => task(useSource));
$('interpret-source').addEventListener('click', () => task(interpretSource));
$('editor').addEventListener('input', () => {$('validation').textContent = 'Draft changed. Validate before opening a new preview.'; $('validation').classList.remove('invalid');});
$('example').addEventListener('click', () => task(async () => {const response = await fetch('/content-package-example.json'); if (!response.ok) throw new Error('Example is unavailable.'); setPackage(await response.json()); status('Non-canon example loaded.');}));
$('import').addEventListener('click', () => {if (!state.busy) $('file').click();});
$('file').addEventListener('change', () => task(async () => {const file = $('file').files[0]; if (!file) return; if (file.size > 512000) throw new Error('Package exceeds 512 KB.'); setPackage(JSON.parse(await file.text())); $('file').value = ''; status('Package imported into the editor.');}));
$('download').addEventListener('click', () => task(async () => {const value = packageValue(); const blob = new Blob([JSON.stringify(value, null, 2) + '\n'], {type: 'application/json'}); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'hollow-star-content-package.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); status('Package downloaded.');}));
$('validate').addEventListener('click', () => task(async () => {try {reportValidation(await api('packet_validate', {package: packageValue()})); status('Package validation passed.');} catch(error) {$('validation').textContent = error.message; $('validation').classList.add('invalid'); throw error;}}));
$('start').addEventListener('click', () => task(start));
$('resume').addEventListener('click', () => task(() => resume($('sessions').value)));
$('refresh').addEventListener('click', () => task(async () => {if (state.view) await resume(state.view.preview_id); await sessions();}));
$('restore-package').addEventListener('click', () => task(async () => {setPackage((await api('packet_preview_export', {preview_id: state.view.preview_id})).package); status('The immutable preview package has been copied into the editor.');}));

await task(async () => {
  await sessions(); await search();
  const saved = localStorage.getItem('hsr-content-preview');
  if (saved) {try {await resume(saved);} catch {localStorage.removeItem('hsr-content-preview'); status('Previous preview is unavailable. Choose a saved preview or open a new package.');}}
});

$('clear-preview').addEventListener('click', () => {
  if (state.busy) return;
  state.view = null;
  state.pendingStart = null;
  state.pendingAction = null;
  $('sessions').value = '';
  $('stage').replaceChildren(node('p', 'No active preview. Open a package to begin again.', 'empty'));
  $('preview-meta').textContent = 'No active preview';
  $('restore-package').disabled = true;
  status('Preview cleared. Saved previews remain available to resume.');
});
