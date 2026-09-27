import {castingProfile} from './magic-articulation.js';
import {figureSocket, figureImpulse, figureBurst} from './puppet-dom.js';
// Combat director: plays host-resolved combat receipts as ordered beats on the
// persistent battle stage.
//
// The host has already decided every outcome. Each new receipt in
// view.recent_receipts (the player's action and any enemy replies) becomes a
// short sequence -- wind-up, strike, impact on the target, a floating number,
// recover -- played one after another so quick inputs queue rather than cancel.
// Nothing here reads hidden state or changes a result; it only draws one.
import {getChampionPosePath, resolveChampionPose} from './sprite-renderer.js';
import {createFXOverlay, reconcileAuras} from './fx-engine.js';

const BASE_MS = {windup: 140, strike: 200, impact: 300, recover: 180, cast: 460, channel: 300, release: 120, bolt: 420,
  guard: 380, move: 380, float: 1000};
// A figure marked data-beat-tempo="heavy" (Doran's 208 lb Cleaver) winds up
// longer and gives its strike room for snap, hitstop and follow-through.
// A two-handed blade on the hero rig takes a shorter version of that pause.
const TEMPO = {heavy: {windup: 2.2, strike: 1.4}, 'two-handed': {windup: 1.5, strike: 1.15}};

// Every knob the Options screen exposes. The director reads these live on
// each beat, so a change applies to the next beat without a reload.
export const DEFAULT_COMBAT_SETTINGS = Object.freeze({
  enabled: true,        // false: no beats at all, the stage just updates
  speed: 1,             // playback multiplier: 2 = twice as fast
  catchUp: 0.55,        // time factor while more than two beats wait
  maxQueue: 8,          // older beats beyond this are dropped, not played late
  gapMs: 180,           // pause after each beat
  lunge: 56,            // max px a striker travels toward the target (0 = none)
  flinch: true,         // target flashes and shakes on a hit
  shakeOnCrit: true,    // whole stage jolts on a critical hit
  poses: true,          // champions swap to authored strike/guard art
  floats: 'damage',     // 'off' | 'damage' | 'detailed' (roll math)
  showMisses: true,
  floatMs: 1000,
  floatScale: 1,
  typeTint: true,       // tint numbers by damage type (fire, cold, ...)
  fillMissing: true,    // infer hits the 5-receipt window dropped, from HP change
  inspector: false,     // beat log panel under the stage
  // Stage overlays and targeting (read by the app, not the player)
  hpBars: 'all',        // 'all' | 'enemies' | 'party' | 'off'
  hpNumbers: true,      // "28/45" on the bar
  turnMarker: true,     // chevron over whoever's turn it is
  targetRing: true,     // ring under the focused target
  statusChips: true,    // condition badges over the bar
  clickMode: 'focus',   // enemy click: 'focus' | 'attack' (single click) | 'double' (double-click attacks)
  attackUsesFocus: true,// Attack skips the picker when a target is focused
  hotkeys: true,        // Tab/[ ] cycle targets, A attack, E end turn, Esc clear
});
const MAX_HISTORY = 40;

const hpById = view => {
  const rows = [...(view?.party || []), ...(view?.opposition || [])];
  if (!rows.length) return null;
  return new Map(rows.filter(row => row?.id && Number.isFinite(Number(row.hp))).map(row => [row.id, Number(row.hp)]));
};

const signature = receipt => {
  try { return JSON.stringify(receipt); } catch { return ''; }
};

// Normalise one public receipt into the few facts a beat needs.
export function beatFromReceipt(receipt) {
  if (!receipt || typeof receipt !== 'object') return null;
  const p = receipt.presentation || receipt.evidence?.presentation || {};
  const result = receipt.result && typeof receipt.result === 'object' ? receipt.result : {};
  const actor = p.actor_id || receipt.actor || receipt.source || result.source || null;
  const target = p.target_id || (typeof receipt.target === 'string' ? receipt.target : null) || result.target || null;
  const kind = String(p.action || receipt.type || '').toLowerCase();
  if (!actor || !kind) return null;
  const roll = receipt.roll && typeof receipt.roll === 'object' ? receipt.roll : null;
  const threshold = Number(receipt.evidence?.critical_threshold) || 20;
  const critical = receipt.critical === true || (roll?.success && Number(roll.natural) >= threshold);
  const damage = [result.damage, receipt.damage, receipt.evidence?.damage_applied].map(Number).find(Number.isFinite);
  const healing = [receipt.healing, result.healing].map(Number).find(Number.isFinite);
  let outcome = null;
  if (kind === 'attack' || roll) outcome = roll?.success === false ? 'miss' : critical ? 'crit' : 'hit';
  else if (Number.isFinite(damage) && damage > 0) outcome = 'hit';
  const tags = p.animation || {};
  const style = receipt.style || (tags.attack ? 'attack' : tags.cast ? 'cast' : tags.defense ? 'guard' : tags.dodge ? 'dodge'
    : tags.move ? 'move' : kind === 'attack' ? 'attack' : ['cast', 'staff_cast', 'domain'].includes(kind) ? 'cast' : (kind === 'damage' || kind === 'impact' || kind === 'healing') ? 'impact' : null);
  const destination = Array.isArray(p.destination) && String(p.destination) !== String(p.origin) ? p.destination : null;
  // Only something visible gets a beat: bookkeeping such as end_turn has no
  // animation tag, roll, heal or movement, and plays nothing.
  const beatStyle = style || (destination ? 'move' : (outcome || Number.isFinite(healing)) ? 'cast' : null);
  if (!beatStyle) return null;
  const math = roll ? {natural: Number(roll.natural), bonus: Number(roll.bonus), total: Number(roll.total),
    dc: Number(roll.dc ?? receipt.evidence?.target_ac), rolls: Array.isArray(roll.rolls) ? roll.rolls.map(Number) : [],
    advantage: Boolean(receipt.evidence?.advantage), disadvantage: Boolean(receipt.evidence?.disadvantage)} : null;
  const damageRolls = Array.isArray(receipt.evidence?.damage_rolls) ? receipt.evidence.damage_rolls.map(Number) : null;
  const damageType = typeof (result.damage_type || receipt.damage_type) === 'string' ? (result.damage_type || receipt.damage_type).toLowerCase().replace(/[^a-z]/g, '') : null;
  return {actor, target, kind, style: beatStyle, casting: castingProfile({...receipt,damageType}), effectApplied: receipt.applied===true || result.applied===true, outcome, damage, healing, destination, animation: tags,
    roll: math, damageRolls, damageType, expression: receipt.evidence?.damage_expression || null};
}

// placeFigure(node, position) moves a figure to a host position (the app owns
// the stage coordinate mapping); the stage's CSS transition animates it.
export function createCombatDirector({getStage, reducedMotion = () => false, onIdle = () => {}, placeFigure = null,
  settings = () => DEFAULT_COMBAT_SETTINGS, onBeat = () => {}} = {}) {
  const cfg = () => ({...DEFAULT_COMBAT_SETTINGS, ...(settings() || {})});
  const history = [];
  const started = performance.now();
  const queue = [];
  const seen = new Set();
  let seenRun = null;
  let lastHp = null;
  let playing = false;
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  // Resolve on the figure's own rig:contact (puppet-dom fires it when the blow
  // lands or the spell leaves the hand), or after `ms` if the rig never says.
  const contact = (node, ms) => new Promise(resolve => {
    if (!node || ms <= 0) { resolve(false); return; }
    const done = hit => { clearTimeout(timer); node.removeEventListener('rig:contact', onHit); resolve(hit); };
    const onHit = () => done(true);
    const timer = setTimeout(() => done(false), ms);
    node.addEventListener('rig:contact', onHit);
  });

  const figure = id => {
    const stage = getStage();
    if (!stage || !id) return null;
    return [...stage.querySelectorAll(':scope > [data-stage-actor]')].find(node => node.dataset.stageActor === id) || null;
  };
  const pace = () => (queue.length > 2 ? Number(cfg().catchUp) || 1 : 1) / Math.max(0.1, Number(cfg().speed) || 1);

  let fxOverlay = null;

  function socketCoords(node, socket = 'chest') {
    if (!node) return {x: 0, y: 0};
    const attached=figureSocket(node,socket,getStage());
    if(attached)return attached;
    const isOpponent = node.classList.contains('opponent');
    const w = node.offsetWidth || 60;
    const h = node.offsetHeight || 100;
    const cx = node.offsetLeft + w / 2;
    const cy = node.offsetTop + h / 2;
    switch (socket) {
      case 'main_hand':
      case 'weapon_main':
      case 'weapon_tip':
      case 'focus':
        return {x: node.offsetLeft + (isOpponent ? w * 0.25 : w * 0.75), y: node.offsetTop + h * 0.45};
      case 'off_hand':
      case 'shield':
        return {x: node.offsetLeft + (isOpponent ? w * 0.75 : w * 0.25), y: node.offsetTop + h * 0.48};
      case 'head':
        return {x: cx, y: node.offsetTop + h * 0.12};
      case 'ground':
      case 'root':
        return {x: cx, y: node.offsetTop + h * 0.95};
      case 'chest':
      default:
        return {x: cx, y: cy};
    }
  }

  function getFX() {
    const stage = getStage();
    if (!stage) return null;
    if (!fxOverlay || !fxOverlay.canvas.isConnected) {
      if (fxOverlay) fxOverlay.destroy();
      fxOverlay = createFXOverlay(stage, {reducedMotion});
      fxOverlay.setCoordsProvider((actorId, socket) => {
        const node = figure(actorId);
        return node ? socketCoords(node, socket) : null;
      });
    }
    return fxOverlay.engine;
  }

  function setBeat(node, beat) {
    if (!node) return;
    if (beat) node.dataset.beat = beat; else delete node.dataset.beat;
  }
  function setAttackAnimation(node, animation) {
    if (!node) return;
    if (animation) node.dataset.attackAnimation = animation;
    else delete node.dataset.attackAnimation;
  }
  function swapPose(node, animation) {
    const img = node?.querySelector('img.doll-base-art');
    if (!img) return () => {};
    const identity = node.dataset.characterIdentity;
    const pose = resolveChampionPose(identity, {inCombat: true, animation});
    const src = pose && getChampionPosePath(identity, pose);
    if (!src || img.getAttribute('src') === src) return () => {};
    const previous = img.getAttribute('src');
    const previousPose=node.dataset.championPose; node.dataset.championPose=pose;
    img.setAttribute('src', src);
    return () => { if (img.isConnected) {img.setAttribute('src', previous);node.dataset.championPose=previousPose;} };
  }
  function float(node, text, tone, extra = {}) {
    const stage = getStage();
    const c = cfg();
    if (!stage || !node || c.floats === 'off') return;
    const label = document.createElement('span');
    label.className = `combat-float float-${tone}${c.typeTint && extra.damageType ? ` dtype-${extra.damageType}` : ''}`;
    label.setAttribute('aria-hidden', 'true');
    const main = document.createElement('b'); main.textContent = text; label.append(main);
    if (c.floats === 'detailed' && extra.detail) {
      const sub = document.createElement('small'); sub.textContent = extra.detail; label.append(sub);
    }
    const ms = Math.max(300, Number(c.floatMs) || BASE_MS.float);
    label.style.left = `${node.offsetLeft + node.offsetWidth / 2}px`;
    label.style.top = `${Math.max(0, node.offsetTop + node.offsetHeight * 0.18)}px`;
    label.style.setProperty('--float-scale', String(Number(c.floatScale) || 1));
    label.style.animationDuration = `${ms}ms`;
    stage.append(label);
    setTimeout(() => label.remove(), ms);
  }
  // The host's own numbers, verbatim: "d20 13 +12 = 25 vs 17 · 2d6 [4,5] slashing".
  function rollDetail(beat) {
    const r = beat.roll; const parts = [];
    if (r && Number.isFinite(r.total)) {
      const dice = r.rolls.length > 1 ? `d20 [${r.rolls.join(',')}]${r.advantage ? ' adv' : r.disadvantage ? ' dis' : ''}` : `d20 ${r.natural}`;
      parts.push(`${dice} ${r.bonus >= 0 ? '+' : ''}${r.bonus} = ${r.total}${Number.isFinite(r.dc) ? ` vs ${r.dc}` : ''}`);
    }
    if (beat.damageRolls?.length) parts.push(`${beat.expression || 'dmg'} [${beat.damageRolls.join(',')}]${beat.damageType ? ` ${beat.damageType}` : ''}`);
    return parts.join(' · ');
  }
  function lungeTowards(actorNode, targetNode) {
    if (!actorNode) return;
    let dx = actorNode.classList.contains('opponent') ? -1 : 1;
    if (targetNode) {
      const gap = (targetNode.offsetLeft + targetNode.offsetWidth / 2) - (actorNode.offsetLeft + actorNode.offsetWidth / 2);
      const reach = Math.max(0, Number(cfg().lunge) || 0);
      dx = Math.sign(gap || dx) * Math.min(reach, Math.max(Math.min(18, reach), Math.abs(gap) * 0.3));
    } else dx *= Math.min(24, Math.max(0, Number(cfg().lunge) || 0));
    actorNode.style.setProperty('--beat-dx', `${dx.toFixed(0)}px`);
  }

  async function play(beat) {
    const c = cfg();
    const actorNode = figure(beat.actor);
    const targetNode = beat.target ? figure(beat.target) : null;
    const reduced = reducedMotion();
    const tempo = TEMPO[actorNode?.dataset.beatTempo] || {};
    const t = key => (reduced ? 0 : (key === 'recover' ? Number(c.gapMs) || 0 : BASE_MS[key]) * (tempo[key] || 1) * pace());
    const t0 = performance.now();
    const detail = rollDetail(beat);
    const fx = getFX();
    const impact = () => {
      if (!targetNode && !Number.isFinite(beat.healing)) return;
      const node = targetNode || actorNode;
      if (beat.outcome && (c.flinch || beat.outcome === 'miss')) setBeat(node, beat.outcome);
      if (beat.outcome === 'crit' && c.shakeOnCrit && !reduced) {
        const stage = getStage();
        if (stage) { stage.dataset.shake = '1'; setTimeout(() => { delete stage.dataset.shake; }, 360); }
      }
      const extra = {detail, damageType: beat.damageType};
      if (beat.outcome === 'miss') { if (c.showMisses) float(node, 'Miss', 'miss', extra); }
      else if (Number.isFinite(beat.damage) && beat.damage > 0) float(node, `${beat.outcome === 'crit' ? 'Crit ' : ''}-${beat.damage}`, beat.outcome === 'crit' ? 'crit' : 'hit', extra);
      else if (beat.outcome === 'hit' || beat.outcome === 'crit') float(node, beat.outcome === 'crit' ? 'Crit!' : 'Hit', beat.outcome, extra);
      if (Number.isFinite(beat.healing) && beat.healing > 0) float(node, `+${beat.healing}`, 'heal', extra);

      // The body answers the blow: a shove away from the attacker that cloth,
      // hair and stance take up, and the element thrown off where it landed.
      if (node && !reduced && targetNode && (beat.outcome === 'hit' || beat.outcome === 'crit' || beat.outcome === 'miss')) {
        const away = actorNode && actorNode !== targetNode
          ? Math.sign((targetNode.offsetLeft + targetNode.offsetWidth / 2) - (actorNode.offsetLeft + actorNode.offsetWidth / 2)) || 1
          : (targetNode.classList.contains('opponent') ? 1 : -1);
        const force = beat.outcome === 'crit' ? 980 : beat.outcome === 'hit' ? 540 : 260;
        figureImpulse(targetNode, away * force * (Number(beat.damage) > 0 ? Math.min(1.4, .8 + Number(beat.damage) / 40) : 1));
        if (beat.outcome !== 'miss') figureBurst(targetNode, beat.damageType || (beat.outcome === 'crit' ? 'silver' : ''));
      }
      if (fx && node && !reduced) {
        if(beat.style==='cast'&&beat.outcome!=='miss'&&(beat.damage>0||beat.healing>0||beat.effectApplied))
          fx.spawnSpellReaction(node.dataset.stageActor,beat.casting?.element||beat.damageType||'force');
        const pos = socketCoords(node, 'chest');
        if (Number.isFinite(beat.healing) && beat.healing > 0) {
          fx.spawnImpact(pos.x, pos.y, 'heal', {radius: 36, count: 24});
          fx.setAura(node.dataset.stageActor, {socket: 'ground', auraType: 'heal', durationMs: 1600});
        } else if (beat.outcome === 'hit' || beat.outcome === 'crit') {
          fx.spawnImpact(pos.x, pos.y, beat.damageType || 'default', {
            radius: beat.outcome === 'crit' ? 44 : 32,
            count: beat.outcome === 'crit' ? 28 : 18,
          });
        }
      }
    };
    const record = () => {
      history.push({at: Math.round(t0 - started), ms: Math.round(performance.now() - t0), actor: beat.actor, target: beat.target,
        style: beat.style, outcome: beat.outcome, damage: beat.damage, healing: beat.healing, detail,
        inferred: Boolean(beat.inferred), missingFigure: Boolean(beat.actor) && !actorNode});
      if (history.length > MAX_HISTORY) history.shift();
      onBeat(history);
    };
    if (!actorNode) { impact(); await wait(t('impact')); record(); return; }
    const restorePose = c.poses ? swapPose(actorNode, beat.style === 'attack' ? {attack: beat.animation.attack || 'strike'}
      : beat.style === 'guard' ? {defense: 'guard'} : beat.style === 'dodge' ? {dodge: 'dodge'} : null) : () => {};
    try {
      setAttackAnimation(actorNode, beat.style === 'attack' ? beat.animation?.attack : null);
      const isRanged = beat.animation?.attack === 'ranged' || (targetNode && Math.abs(targetNode.offsetLeft - actorNode.offsetLeft) > 160 && beat.style === 'attack');
      const isSpell = beat.style === 'cast';

      if (isSpell) {
        // Channel: power gathers at the focus (staff head, or between the hands).
        const casting=beat.casting||castingProfile(beat);
        actorNode.dataset.casting=JSON.stringify(casting);
        const damageType = casting.element;
        setBeat(actorNode, 'cast_channel');
        if (fx && !reduced) fx.setAura(actorNode.dataset.stageActor, {socket: 'focus', auraType: damageType, radius: 14, durationMs: t('channel') + t('release')});
        await wait(t('channel'));
        // Release: the bolt leaves the weapon tip on the rig's own contact frame.
        setBeat(actorNode, 'cast_release');
        await contact(actorNode, t('release'));
        const flight = reduced ? 0 : Math.round(BASE_MS.bolt * pace());
        if (fx && targetNode && !reduced && targetNode!==actorNode) {
          const from = socketCoords(actorNode, 'focus');
          const to = socketCoords(targetNode, 'chest');
          fx.spawnProjectile({fromX: from.x, fromY: from.y, toX: to.x, toY: to.y, damageType, archetype: casting.delivery, impactOnHit: false, durationMs: flight || 1});
          await wait(flight);
        }
        impact();
        await wait(t('impact'));
      } else if (isRanged) {
        setBeat(actorNode, 'windup');
        await contact(actorNode, t('windup'));
        if (fx && targetNode) {
          const from = socketCoords(actorNode, 'weapon_tip');
          const to = socketCoords(targetNode, 'chest');
          fx.spawnProjectile({fromX: from.x, fromY: from.y, toX: to.x, toY: to.y,
            damageType: beat.damageType || 'physical', archetype: 'arrow', durationMs: 320});
        }
        await wait(reduced ? 0 : Math.round(320 * pace()));
        impact();
        await wait(t('impact'));
      } else if (beat.style === 'attack') {
        lungeTowards(actorNode, targetNode);
        setBeat(actorNode, 'windup'); await wait(t('windup'));
        // The impact lands on the rig's contact frame, not a fixed timer.
        setBeat(actorNode, 'strike'); await contact(actorNode, t('strike'));
        impact(); await wait(t('impact'));
      } else {
        if (beat.destination && placeFigure) placeFigure(actorNode, beat.destination);
        setBeat(actorNode, beat.style); await wait(t(beat.style in BASE_MS ? beat.style : 'cast'));
        impact(); if (beat.outcome) await wait(t('impact'));
      }
    } finally {
      setBeat(actorNode, null); setBeat(targetNode, null);
      delete actorNode.dataset.casting;
      fx?.removeAura(actorNode.dataset.stageActor,'focus');
      setAttackAnimation(actorNode, null);
      actorNode.style.removeProperty('--beat-dx');
      restorePose();
      await wait(t('recover'));
      record();
    }
  }

  async function run() {
    playing = true;
    try {
      while (queue.length) {
        if (document.hidden || !getStage()) { queue.length = 0; break; }
        await play(queue.shift());
      }
    } finally {
      playing = false;
      onIdle();
    }
  }

  return {
    // Queue receipts not seen before on this run. Seen-ness is remembered per
    // run rather than diffed against the previous view: compact turn replies
    // omit recent_receipts, so the previous view is not a reliable baseline.
    // The first view of a run is history, not something that just happened.
    ingest(_previous, next) {
      const rows = next?.recent_receipts;
      if (!Array.isArray(rows)) return 0;
      const hp = hpById(next);
      if (seenRun !== next.run_id) {
        seenRun = next.run_id; seen.clear(); queue.length=0; fxOverlay?.engine.clear(); lastHp = hp;
        rows.forEach(row => seen.add(signature(row)));
        return 0;
      }
      const beats = [];
      for (const row of rows) {
        const key = signature(row);
        if (seen.has(key)) continue;
        seen.add(key);
        if(['cast','staff_cast'].includes(row.type)&&Array.isArray(row.events)&&row.events.length) {
          for(const ev of row.events) {
            const result=ev.result&&typeof ev.result==='object'?ev.result:{};
            const spellBeat=beatFromReceipt({...row,events:undefined,...result,type:row.type,style:'cast',
              actor:row.actor||row.source,target:result.target||ev.target||row.target,
              presentation:{...row.presentation,target_id:result.target||ev.target||row.target},
              healing:ev.healing??result.healing,damage:result.damage??ev.damage,
              damage_type:result.damage_type||row.ruling?.damage_type,
              // Saving successfully can still mean half damage. Only an attack roll misses.
              roll:ev.attack||null});
            if(spellBeat)beats.push(spellBeat);
          }
          continue;
        }
        const beat = beatFromReceipt(row);
        const hasMultipleEvents = Array.isArray(row?.events) && row.events.length > 1;
        if (beat) {
          if (hasMultipleEvents) {
            beat.damage = null;
            beat.healing = null;
          }
          beats.push(beat);
        }
        if (Array.isArray(row?.events)) {
          for (const ev of row.events) {
            if (!ev || typeof ev !== 'object') continue;
            const res = ev.result && typeof ev.result === 'object' ? ev.result : null;
            const sub = res ? {
              ...res,
              actor: res.source || row.actor || row.source,
              target: res.target || ev.target || row.target,
              roll: ev.attack || ev.save || res.roll,
              style: 'impact',
            } : {
              ...ev,
              type: ev.type || (ev.attack ? 'attack' : ev.save ? 'save' : 'impact'),
              target: ev.target || row.target,
              actor: ev.actor || row.actor || row.source,
              roll: ev.attack || ev.save,
              style: ev.healing ? 'cast' : 'impact',
            };
            const subBeat = beatFromReceipt(sub);
            if (subBeat) {
              if (hasMultipleEvents || !beat || subBeat.target !== beat.target || subBeat.damage !== beat.damage) {
                beats.push(subBeat);
              }
            }
          }
        }
      }
      // The host sends only its last five receipts, so a busy reply can drop
      // its first events. Damage the receipts do not account for still shows,
      // as an impact played before the rest of this reply.
      if (lastHp && hp && cfg().fillMissing) {
        const missed = [];
        for (const [id, now] of hp) {
          const before = lastHp.get(id);
          if (!Number.isFinite(before) || now >= before) continue;
          const shown = beats.filter(beat => beat.target === id && beat.outcome !== 'miss')
            .reduce((sum, beat) => sum + (Number.isFinite(beat.damage) ? beat.damage : 0), 0);
          const unexplained = before - now - shown;
          if (unexplained > 0) missed.push({actor: null, target: id, kind: 'damage', style: 'impact', outcome: 'hit', damage: unexplained, animation: {}, inferred: true});
        }
        beats.unshift(...missed);
      }
      const allRows = [...(next?.party || []), ...(next?.opposition || [])];
      const fx = getFX();
      if(fx){const ids=new Set(allRows.map(r=>r.id));for(const aura of fx.auras.values())if(!ids.has(aura.entityId))fx.removeAura(aura.entityId);
        for(const row of allRows)if(row.id)reconcileAuras(fx,row.id,row);}

      if (hp) lastHp = hp;
      if (seen.size > 200) [...seen].slice(0, seen.size - 100).forEach(key => seen.delete(key));
      if (!cfg().enabled) return 0;
      queue.push(...beats);
      const cap = Math.max(1, Number(cfg().maxQueue) || 8);
      if (queue.length > cap) queue.splice(0, queue.length - cap);
      return beats.length;
    },
    kick() { if (!playing && queue.length) run(); },
    // Queue beats directly: the Options demo feeds sample beats through here.
    play(beats) { queue.push(...beats.filter(Boolean)); this.kick(); },
    get history() { return history.slice(); },
    clearHistory() { history.length = 0; onBeat(history); },
    get playing() { return playing; },
    get pending() { return queue.length; },
    get fx() { return getFX(); },
    destroy() {
      queue.length=0; seen.clear(); lastHp=null; seenRun=null;
      if (fxOverlay) {
        fxOverlay.destroy();
        fxOverlay = null;
      }
    },
  };
}
