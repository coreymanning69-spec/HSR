export function bindArcadeInput(root, {actor, onInput, onAttack, onMode, onFlight, onBlock, onDodge, onRanged}) {
  const listeners = [];
  const listen = (target, event, handler, options) => {
    target.addEventListener(event, handler, options);
    listeners.push(() => target.removeEventListener(event, handler, options));
  };
  const submitMove = (dx, dy) => onInput?.({actor: actor(), dx, dy});
  // Delegated from the document, not bound per button: the control panel is
  // rebuilt on every render, and per-button listeners died with it.
  const inside = event => {
    const hit = event.target?.closest?.('[data-arcade-dx],[data-arcade-attack],[data-arcade-mode],[data-arcade-flight],[data-arcade-dodge],[data-arcade-ranged],[data-arcade-block]');
    return hit && (root.contains(hit) || hit.closest('[data-arcade-controls]')) ? hit : null;
  };
  listen(document, 'click', event => {
    const button = inside(event); if (!button || button.disabled) return;
    const d = button.dataset;
    if ('arcadeDx' in d) submitMove(Number(d.arcadeDx || 0), Number(d.arcadeDy || 0));
    else if ('arcadeAttack' in d) onAttack?.({actor: actor(), attack: true});
    else if ('arcadeMode' in d) onMode?.(d.arcadeMode, actor());
    else if ('arcadeFlight' in d) onFlight?.(d.arcadeFlight === 'on', actor());
    else if ('arcadeDodge' in d) onDodge?.({actor: actor(), dodge: true});
    else if ('arcadeRanged' in d) onRanged?.({actor: actor(), ranged: true});
  });
  // Block is a held state, not a one-shot click: it must keep re-asserting
  // itself every tick while the button/key stays down, and clear the moment
  // it's released (the server treats an un-resubmitted block as dropped).
  let blockHeld = false;
  listen(document, 'pointerdown', event => { const button = inside(event); if (button && 'arcadeBlock' in button.dataset) { blockHeld = true; onBlock?.(true); } });
  const release = () => { if (blockHeld) { blockHeld = false; onBlock?.(false); } };
  listen(document, 'pointerup', release);
  listen(document, 'pointercancel', release);

  const keys = {
    w: [0, 5], ArrowUp: [0, 5],
    s: [0, -5], ArrowDown: [0, -5],
    a: [-5, 0], ArrowLeft: [-5, 0],
    d: [5, 0], ArrowRight: [5, 0],
  };
  let shiftHeld = false;
  listen(window, 'keydown', event => {
    if (event.target && /input|textarea|select/i.test(event.target.tagName)) return;
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault();
      onAttack?.({actor: actor(), attack: true});
      return;
    }
    if (event.key === 'Shift') {
      if (!shiftHeld) {
        shiftHeld = true;
        onBlock?.(true);
      }
      return;
    }
    if ((event.key === 'x' || event.key === 'X') && !event.repeat) {
      event.preventDefault();
      onDodge?.({actor: actor(), dodge: true});
      return;
    }
    if ((event.key === 'f' || event.key === 'F') && !event.repeat) {
      event.preventDefault();
      onRanged?.({actor: actor(), ranged: true});
      return;
    }
    const move = keys[event.key] || keys[event.key.toLowerCase()];
    if (!move) return;
    event.preventDefault();
    submitMove(move[0], move[1]);
  });
  listen(window, 'keyup', event => {
    if (event.key === 'Shift') {
      shiftHeld = false;
      onBlock?.(false);
    }
  });
  return {destroy() {listeners.splice(0).forEach(remove => remove());}};
}
