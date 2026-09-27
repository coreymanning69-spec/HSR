const responseShape = (payload, transport, requestId, runId) => ({
  ok: Boolean(payload?.ok),
  result: payload?.result ?? null,
  readout: payload?.result?.readout ?? payload?.readout ?? null,
  public_view: payload?.view ?? payload?.result?.turn?.public_view ?? payload?.result?.readout?.public_view ?? payload?.public_view ?? null,
  public_receipt: payload?.receipt ?? payload?.result?.turn?.public_receipt ?? payload?.result?.readout?.public_receipt ?? payload?.public_receipt ?? null,
  error: payload?.ok ? null : payload?.error ?? {code: 'REQUEST_FAILED', message: 'Host request failed'},
  request_id: payload?.id ?? requestId,
  transport,
  run_id: payload?.view?.run_id ?? payload?.result?.run?.run_id ?? payload?.result?.turn?.run_id ?? payload?.result?.readout?.run_id ?? runId ?? null,
});

export function createHSRClient({base = '', mode = 'engine'} = {}) {
  let transport = mode === 'hostless' ? 'hostless' : 'engine-host';
  const call = async (command, fields = {}, options = {}) => {
    const id = globalThis.crypto?.randomUUID?.() ?? `hsr-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const body = {id, command, compact: true, public_only: true, ...fields};
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeout ?? 35000);
    try {
      const reply = await fetch(`${base}/api/host`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      const payload = await reply.json();
      const normalized = responseShape(payload, transport, id, fields.run_id);
      if (!reply.ok && normalized.ok) normalized.ok = false;
      return normalized;
    } catch (error) {
      return responseShape({ok: false, id, error: {
        code: error.name === 'AbortError' ? 'REQUEST_TIMEOUT' : 'NETWORK_ERROR',
        message: error.message || 'Host is unavailable',
      }}, transport, id, fields.run_id);
    } finally {
      clearTimeout(timer);
    }
  };
  const get = async path => {
    try {
      const reply = await fetch(`${base}${path}`, {cache: 'no-store'});
      return responseShape(await reply.json(), transport);
    } catch (error) {
      return responseShape({ok: false, error: {code: 'NETWORK_ERROR', message: error.message}}, transport);
    }
  };
  const client = {
    request: call,
    characterOptions: () => call('character_options'),
    characterRoll: (creation_seed, roll_set = 0) => call('character_roll', {creation_seed, roll_set}),
    health: () => get('/api/health'),
    capabilities: () => get('/api/capabilities'),
    affixCatalog: () => get('/api/affixes'),
    contentCatalog: () => call('content_catalog'),
    manifest: () => get('/api/ui'),
    sessionVocabulary: () => get('/api/session/vocabulary'),
    boot: modeName => call('boot', {mode: modeName || 'DESIGN'}),
    listRuns: () => call('list_runs'),
    createRun: payload => call('create_run', payload),
    designStart: runId => call('design_start', {run_id: runId}),
    designAction: (runId, action) => call('design_action', {run_id: runId, action}),
    previewCharacter: payload => call('preview_character', {build: payload}),
    buildCharacter: (profileId, payload, expectedBuildHash) => call('build_character', {
      profile_id: profileId, build: payload, expected_build_hash: expectedBuildHash,
    }),
    loadRun: runId => call('load_run', {run_id: runId}),
    saveRun: runId => call('save_run', {run_id: runId}),
    readout: runId => call('readout', {run_id: runId}),
    designTurn: (runId, intent, action = null) => call('design_turn', {
      run_id: runId, intent, ...(action ? {action} : {}),
    }),
    validate: () => call('validate'),
    setMode: next => { transport = next === 'hostless' ? 'hostless' : 'engine-host'; },
    get transport() { return transport; },
  };
  return Object.freeze(client);
}
