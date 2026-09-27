const responseShape = (payload, transport, requestId, runId) => ({
  ok: Boolean(payload?.ok),
  result: payload?.result ?? null,
  readout: payload?.result?.readout ?? payload?.readout ?? null,
  event: payload?.event ?? payload?.result?.event ?? payload?.result?.turn?.outcome ?? payload?.result?.turn?.event ?? null,
  public_view: payload?.view ?? payload?.result?.turn?.public_view ?? payload?.result?.readout?.public_view ?? payload?.result?.idle?.public_view ?? payload?.result?.public_view ?? payload?.public_view ?? null,
  public_receipt: payload?.receipt ?? payload?.result?.turn?.public_receipt ?? payload?.result?.readout?.public_receipt ?? payload?.result?.idle?.public_receipt ?? payload?.result?.public_receipt ?? payload?.public_receipt ?? null,
  error: payload?.ok ? null : payload?.error ?? {code: 'REQUEST_FAILED', message: 'Host request failed'},
  request_id: payload?.id ?? requestId,
  transport,
  run_id: payload?.view?.run_id ?? payload?.result?.run?.run_id ?? payload?.result?.turn?.run_id ?? payload?.result?.readout?.run_id ?? payload?.result?.idle?.run_id ?? runId ?? null,
});

export function createHSRClient({base = '', onTrace = null} = {}) {
  const trace = entry => { try { onTrace?.(entry); } catch {} };
  let transport = 'local-gateway';
  const inFlight = new Map();
  const call = async (command, fields = {}, options = {}) => {
    const dedupeKey = options.dedupeKey || `${command}:${JSON.stringify(fields)}`;
    if (inFlight.has(dedupeKey)) return inFlight.get(dedupeKey);
    const id = globalThis.crypto?.randomUUID?.() ?? `hsr-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const body = {id, command, compact: true, public_only: true, ...fields};
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), options.timeout ?? 35000);
    const started = performance.now();
    const request = (async () => { try {
      const reply = await fetch(`${base}/api/host`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      const payload = await reply.json();
      const normalized = responseShape(payload, transport, id, fields.run_id);
      if (!reply.ok && normalized.ok) normalized.ok = false;
      trace({kind: 'host', command, id, run_id: fields.run_id ?? null, http: reply.status, ok: normalized.ok, ms: Math.round(performance.now() - started), error: normalized.error, fields, reply: payload});
      return normalized;
    } catch (error) {
      trace({kind: 'host', command, id, run_id: fields.run_id ?? null, http: null, ok: false, ms: Math.round(performance.now() - started), error: {code: error.name === 'AbortError' ? 'REQUEST_TIMEOUT' : 'NETWORK_ERROR', message: error.message}, fields});
      return responseShape({ok: false, id, error: {
        code: error.name === 'AbortError' ? 'REQUEST_TIMEOUT' : 'NETWORK_ERROR',
        message: error.message || 'Host is unavailable',
      }}, transport, id, fields.run_id);
    } finally {
      clearTimeout(timer);
      inFlight.delete(dedupeKey);
    } })();
    inFlight.set(dedupeKey, request);
    return request;
  };
  const get = async path => {
    try {
      const reply = await fetch(`${base}${path}`, {cache: 'no-store'});
      const payload = await reply.json();
      if (!reply.ok || !payload?.ok) trace({kind: 'get', command: path, http: reply.status, ok: false, error: payload?.error});
      return responseShape(payload, transport);
    } catch (error) {
      trace({kind: 'get', command: path, http: null, ok: false, error: {code: 'NETWORK_ERROR', message: error.message}});
      return responseShape({ok: false, error: {code: 'NETWORK_ERROR', message: error.message}}, transport);
    }
  };
  const client = {
    request: call,
    characterOptions: () => call('character_options'),
    characterRoll: (creation_seed, roll_set = 0) => call('character_roll', {creation_seed, roll_set}),
    health: () => get('/api/health'),
    // Heartbeat: round-trip latency plus the host's wall clock (X-Host-Time, ms).
    ping: async () => {
      const sent = Date.now(); const t0 = performance.now();
      try {
        const reply = await fetch(`${base}/api/health`, {cache: 'no-store'});
        const rtt = performance.now() - t0;
        const payload = await reply.json().catch(() => null);
        const stamp = Number(reply.headers.get('X-Host-Time')) || Date.parse(reply.headers.get('Date') || '') || null;
        return {ok: reply.ok && Boolean(payload?.ok), rtt, hostTime: stamp, offset: stamp ? stamp - (sent + rtt / 2) : 0};
      } catch (error) {
        return {ok: false, rtt: null, hostTime: null, offset: 0, error: error.message};
      }
    },
    capabilities: () => get('/api/capabilities'),
    affixCatalog: () => get('/api/affixes'),
    contentCatalog: () => call('content_catalog'),
    scenarioCatalog: (mode = null) => call('scenario_catalog', mode ? {mode} : {}),
    manifest: () => get('/api/ui'),
    sessionVocabulary: () => get('/api/session/vocabulary'),
    boot: modeName => {
      const mode = modeName || 'DESIGN';
      return call('boot', {mode, ...(mode === 'FORGE' ? {intent: true} : {})});
    },
    listRuns: () => call('list_runs'),
    statistics: (mode, runId = null) => call('statistics', {mode, ...(runId ? {run_id: runId} : {})}),
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
    examine: (runId, fields = {}) => call('examine', {run_id: runId, ...fields}),
    companionTalk: (runId, speaker, text) => call('companion_talk', {run_id: runId, speaker, text}, {dedupeKey: `companion:${Date.now()}`}),
    startRun: payload => call('start-run', payload),
    sandboxRelease: runId => call('sandbox_release', {run_id: runId}),
    roomAction: (runId, type, fields = {}) => call('design_action', {run_id: runId, action: {type, ...fields}}),
    hostAction: (command, runId, fields = {}) => call(command, {run_id: runId, ...fields}),
    autoStep: (runId, inCombat) => call(inCombat ? 'design_auto_combat' : 'design_auto', {run_id: runId}),
    // Plays consecutive NPC turns and NPC-held reactions (at most 12 steps),
    // stopping for a player decision; reply.result.receipts lists each step.
    drainNpc: (runId, maxSteps = 12) => call('design_drain_npc', {run_id: runId, max_steps: maxSteps}, {dedupeKey: `drain:${runId}:${Date.now()}`}),
    idleTick: (runId, maxSteps = 1) => call('idle_tick', {run_id: runId, max_steps: maxSteps}),
    autoTravel: (runId, destination = 'well', maxSteps = 4, enterDescent = false) => call('auto_travel', {
      run_id: runId, destination, max_steps: maxSteps, enter_descent: enterDescent,
    }),
    configureMacros: (runId, macros) => call('design_action', {run_id: runId,
      action: {type: 'configure_macros', macros}}),
    terminalReceipt: runId => call('terminal_receipt', {run_id: runId}),
    progression: identity => call('progression', {identity}),
    purchaseUpgrade: (identity, upgrade) => call('upgrade', {identity, upgrade}),
    metaShop: identity => call('meta_shop', {identity}),
    // Attunement Matrix: destroy an item and slot its powers; `replace` names
    // an attuned power to overwrite when the lane is full.
    decant: (runId, item, actor = 'p0', replace = null) => call('design_action', {run_id: runId,
      action: {type: 'decant', item, actor, ...(replace ? {replace} : {})}}),
    releaseAttunement: (runId, actor, lane, name) => call('design_action', {run_id: runId,
      action: {type: 'release_attunement', actor, lane, name}}),
    settleRun: (identity, runId) => call('settle_run', {identity, run_id: runId}),
    validate: () => call('validate'),
    setMode: () => { transport = 'local-gateway'; },
    get transport() { return transport; },
  };
  return Object.freeze(client);
}
