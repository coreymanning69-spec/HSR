export const ARCADE_POLL_MS = 120;

export function createArcadeLoop({client, runId, getInputs, onFrame, onComplete, onError}) {
  let timer = null;
  let stopped = true;
  let busy = false;

  const schedule = () => {
    if (!stopped) timer = setTimeout(poll, ARCADE_POLL_MS);
  };

  async function poll() {
    if (stopped || busy) return;
    const inputs = getInputs?.();
    if (inputs === null) {
      schedule();
      return;
    }
    busy = true;
    try {
      // The server owns the frame; this fixed cadence only limits transport
      // pressure and gives the canvas a predictable interpolation window.
      const reply = await client.designAction(runId, {type: 'arcade_tick', inputs: inputs || []});
      if (!reply.ok) throw Error(reply.error?.message || reply.error?.code || 'Arcade frame rejected');
      const event = reply.result?.event || reply.result?.outcome || {};
      const readout = await client.readout(runId);
      if (!readout.ok) throw Error(readout.error?.message || readout.error?.code || 'Arcade readout unavailable');
      onFrame?.(readout.public_view, readout);
      if (event.arcade?.complete || event.complete || readout.public_view?.arcade?.complete) onComplete?.();
    } catch (error) {
      onError?.(error);
    } finally {
      busy = false;
      schedule();
    }
  }

  return {
    start() {
      if (!stopped) return;
      stopped = false;
      poll();
    },
    stop() {
      stopped = true;
      if (timer) clearTimeout(timer);
      timer = null;
    },
    isBusy() { return busy; },
  };
}
