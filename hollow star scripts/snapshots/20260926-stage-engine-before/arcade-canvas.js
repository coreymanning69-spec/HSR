import {dollModel} from './paperdoll.js';
import {drawPuppet, drawChampion, puppetStyle, poseFor} from './puppet-renderer.js';
import {championPoseArt, actorRig, getChampionPosePath, resolveChampionPose} from './sprite-renderer.js';
import {FXEngine, getPalette, reconcileAuras} from './fx-engine.js';
import {SkeletalRig} from './skeletal-rig.js';
import {TraversalController} from './traversal-controller.js';

// The host's arcade_view still reports x/y/z per DM-established schema
// (hollow-star-arcade-public-1): x is the horizontal lane the whole scene
// runs along, z is jump height (server-integrated gravity), and y — the
// only axis this file no longer treats as dominant — becomes a shallow
// front/back lane offset for depth, not the screen's vertical axis. That
// keeps the server's collision math (x/y only) untouched while the canvas
// reads as an actual side view instead of a top-down arena.
const DEFAULT_BOUNDS = {x: [0, 120], y: [0, 120]};
const PX_PER_UNIT = 6;
const GROUND_MARGIN = 36;
const LANE_SPAN_PX = 26;
const PARALLAX_LAYERS = [
  {speed: 0.12, color: '#232f49', heightFrac: 0.5},
  {speed: 0.32, color: '#182238', heightFrac: 0.28},
];
const imageCache = new Map();

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function spriteImage(path) {
  if (!path) return null;
  let image = imageCache.get(path);
  if (image) return image;
  image = new Image();
  image.dataset.fallbackTried = 'false';
  image.src = path;
  image.onerror = () => {
    // The existing sprite lookup is SVG-first while the authored character
    // sheet is PNG-backed. Retry the same lookup as a presentation fallback;
    // the server still owns which sprite_id is public.
    if (image.dataset.fallbackTried === 'false' && path.endsWith('.svg')) {
      image.dataset.fallbackTried = 'true';
      image.src = path.replace(/\.svg$/, '.png');
    } else {
      image.dataset.failed = 'true';
    }
  };
  imageCache.set(path, image);
  return image;
}

function interpolate(previous, current, amount) {
  if (!Array.isArray(previous) || !Array.isArray(current)) return current || previous || [0, 0, 0];
  return previous.map((value, index) => Number(value || 0) + (Number(current[index] || 0) - Number(value || 0)) * amount);
}

export function createArcadeCanvas(container) {
  const canvas = document.createElement('canvas');
  canvas.className = 'arcade-canvas';
  canvas.setAttribute('role', 'img');
  canvas.setAttribute('aria-label', 'Host-resolved arcade encounter');
  container.appendChild(canvas);
  const context = canvas.getContext('2d');
  const fx = new FXEngine();
  const entityRigs = new Map();
  const traversal = new TraversalController();
  let lastTime = performance.now();
  let current = null;
  let previous = null;
  let actors = new Map();
  // Same HP-bar choice as the combat stages ('all' | 'enemies' | 'party' | 'off').
  let options = {hpBars: 'all', hpNumbers: true};
  let changedAt = performance.now();
  let frameRequest = 0;
  let width = 0;
  let height = 0;
  let resizeObserver = null;
  let resizeRequest = 0;

  function resize() {
    const rect = container.getBoundingClientRect();
    const nextWidth = Math.max(280, Math.floor(rect.width || 720));
    const nextHeight = Math.max(220, Math.floor(nextWidth * 0.48));
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    if (nextWidth === width && nextHeight === height && canvas.width === nextWidth * dpr) return;
    width = nextWidth;
    height = nextHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.aspectRatio = `${width} / ${height}`;
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function groundLine() {
    return height - GROUND_MARGIN;
  }

  // Horizontal-follow camera, centered on the party's average x so the
  // scene scrolls as the player moves instead of showing the whole 0-120
  // world flattened into one static frame.
  function cameraX() {
    const bounds = current?.bounds?.x || DEFAULT_BOUNDS.x;
    const entities = current?.entities || {};
    const partyX = Object.entries(entities)
      .filter(([id, row]) => (row.team === 'party' || id.startsWith('p')) && row.active !== false)
      .map(([, row]) => Number(row.position?.[0] || 0));
    const focus = partyX.length ? partyX.reduce((sum, value) => sum + value, 0) / partyX.length : (bounds[0] + bounds[1]) / 2;
    const halfSpan = width / 2 / PX_PER_UNIT;
    const low = bounds[0] + halfSpan;
    const high = Math.max(low, bounds[1] - halfSpan);
    return clamp(focus, low, high);
  }

  // World (x, laneY, jumpZ) -> screen point. `groundY` is where a shadow or
  // an obstacle's base sits; `y` additionally rises with jump height so a
  // jumping actor visibly leaves the ground rather than just tagging a mode.
  function worldToScreen(raw, camera) {
    const ground = groundLine();
    const x = width / 2 + (Number(raw?.[0] || 0) - camera) * PX_PER_UNIT;
    const laneRange = current?.bounds?.y || DEFAULT_BOUNDS.y;
    const laneFraction = clamp((Number(raw?.[1] || 0) - laneRange[0]) / Math.max(1, laneRange[1] - laneRange[0]), 0, 1);
    const groundY = ground - (laneFraction - 0.5) * LANE_SPAN_PX;
    const jumpZ = Number(raw?.[2] || 0) * PX_PER_UNIT * 0.6;
    return {x, y: groundY - jumpZ, groundY};
  }

  function drawBackground(camera) {
    const ground = groundLine();
    const sky = context.createLinearGradient(0, 0, 0, ground);
    sky.addColorStop(0, '#1d2d47');
    sky.addColorStop(1, '#101a2c');
    context.fillStyle = sky;
    context.fillRect(0, 0, width, ground);

    // Two flat parallax ridges scrolling at different rates against the
    // camera — placeholder shapes standing in for background art later.
    PARALLAX_LAYERS.forEach(layer => {
      const layerTop = ground - height * layer.heightFrac;
      const offset = ((camera * layer.speed * PX_PER_UNIT) % 96 + 96) % 96;
      context.fillStyle = layer.color;
      context.beginPath();
      context.moveTo(0, ground);
      context.lineTo(0, layerTop + 10);
      for (let x = -offset; x <= width + 96; x += 48) {
        const peak = layerTop + Math.sin((x + offset) * 0.02) * 10;
        context.lineTo(x, peak);
      }
      context.lineTo(width, ground);
      context.closePath();
      context.fill();
    });

    context.fillStyle = '#141d30';
    context.fillRect(0, ground, width, height - ground);
    context.strokeStyle = 'rgba(201,168,106,.4)';
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(0, ground + 0.5);
    context.lineTo(width, ground + 0.5);
    context.stroke();
  }

  function drawObstacle(obstacle, camera) {
    const point = worldToScreen(obstacle.position, camera);
    const obstacleWidth = Math.max(4, Number(obstacle.width || 5) * PX_PER_UNIT * 0.4);
    const obstacleHeight = Math.max(16, Number(obstacle.height || 40) * 0.6);
    context.fillStyle = obstacle.kind === 'gap' ? 'rgba(167,92,86,.56)' : 'rgba(201,168,106,.38)';
    context.fillRect(point.x - obstacleWidth / 2, point.groundY - obstacleHeight, obstacleWidth, obstacleHeight);
    context.strokeStyle = 'rgba(242,215,140,.75)';
    context.strokeRect(point.x - obstacleWidth / 2, point.groundY - obstacleHeight, obstacleWidth, obstacleHeight);
    context.fillStyle = '#d8c18b';
    context.font = '10px Georgia, serif';
    context.fillText(obstacle.kind || 'obstacle', point.x - obstacleWidth / 2 + 4, point.groundY - obstacleHeight - 5);
  }

  function drawProjectile(projectile, camera) {
    const point = worldToScreen(projectile.position, camera);
    const dtype = projectile.damage_type || 'default';
    const palette = getPalette(dtype);
    const vx = Number(projectile.velocity?.[0] || 0) * PX_PER_UNIT;

    // Trail particles emitted into FXEngine
    if (!options.reducedMotion && !globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches && Math.random() < 0.65) {
      const pColor = palette.particles[Math.floor(Math.random() * palette.particles.length)];
      fx.emitParticle(
        point.x,
        point.y - 10,
        -Math.sign(vx || 1) * (1.2 + Math.random() * 2),
        (Math.random() - 0.5) * 1.5,
        pColor,
        Math.random() * 2.5 + 1.2,
        0.04,
        0,
        dtype === 'cold' ? 'shard' : 'circle'
      );
    }

    // Glowing core & tracer halo
    context.save();
    const grad = context.createRadialGradient(point.x, point.y - 10, 1, point.x, point.y - 10, 9);
    grad.addColorStop(0, '#ffffff');
    grad.addColorStop(0.4, palette.primary);
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    context.fillStyle = grad;
    context.beginPath();
    context.arc(point.x, point.y - 10, 9, 0, Math.PI * 2);
    context.fill();

    // Bright white core
    context.fillStyle = '#ffffff';
    context.beginPath();
    context.arc(point.x, point.y - 10, 2.5, 0, Math.PI * 2);
    context.fill();
    context.restore();
  }

  function drawEntity(id, row, amount, camera, dt = 16, prepareOnly = false) {
    const before = previous?.entities?.[id];
    const interpolated = {...row, position: interpolate(before?.position, row.position, amount)};
    const point = worldToScreen(interpolated.position, camera);
    const actor = actors.get(id) || {};
    const model = dollModel(actor, {pose: 'idle'});
    const opponent = row.team === 'opposition' || id.startsWith('e');

    // Get or initialize entity SkeletalRig
    let rig = entityRigs.get(id);
    if (!rig) {
      rig = new SkeletalRig({scale: opponent ? 0.9 : 1.0});
      entityRigs.set(id, rig);
    }

    // Kinematic Traversal update (obstacle climb & jump)
    const trav = traversal.update(id, interpolated, current?.obstacles || [], rig, dt);
    const visualElevation = trav.elevationZ * PX_PER_UNIT * 0.6;
    const actorY = point.y - visualElevation;
    const facing = Number(row.facing || (opponent ? -1 : 1));

    const reduced = options.reducedMotion || globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    // A rig carries its own race height; only the legacy puppet scales by style.
    rig.scale = (opponent ? .95 : 1.05) * (actorRig(model) ? 1 : puppetStyle(model).height);
    rig.time += reduced ? 0 : dt;
    rig.applyPose(poseFor(model, row), {weapon:model.weapon,staffStyle:puppetStyle(model).weaponStyle,bodyWidth:puppetStyle(model).width, progress:(rig.time % 600)/600, reducedMotion:reduced});
    rig.update(0, point.x, actorY, facing);

    reconcileAuras(fx, id, {...actor, ...row});

    // Layered champions (Doran) pose themselves on the same rig: host state in,
    // sockets out for the FX engine. prepareOnly measures without painting.
    // Champions on their own rigs, everyone else on the hero rig.
    const rigged = actorRig(model);
    if (rigged) {
      // An encounter is combat: standing still is his vanguard, not the planted rest.
      const live = trav.pose && trav.pose !== 'idle' ? trav.pose : poseFor(model, row);
      const pose = live === 'idle' ? 'guard' : live;
      if (prepareOnly) {
        rig.artSockets = rigged.draw(context, rig, model, {x: point.x, y: actorY, facing, dt: reduced ? 0 : dt, pose,
          reducedMotion: reduced, paint: false, idleFidgets: false, screenX: point.x, screenY: actorY, screenFacing: facing});
        return;
      }
      context.save();
      context.globalAlpha = row.active === false ? 0.25 : 1;
      const lift = Number(interpolated.position[2] || 0) > 0.1 || trav.isTraversing ? 0.75 : 1;
      context.fillStyle = 'rgba(0,0,0,.45)';
      context.beginPath();
      context.ellipse(point.x, point.groundY + 3, 34 * lift, 7, 0, 0, Math.PI * 2);
      context.fill();
      if (row.invulnerable) context.globalAlpha *= 0.55;
      rig.artSockets = rigged.draw(context, rig, model, {x: point.x, y: actorY, facing, dt: 0, pose,
        reducedMotion: reduced, idleFidgets: false, shadow: false});
      context.restore();
    }

    const poseArt = rigged ? null : championPoseArt(actor.identity);
    const path = poseArt
      ? getChampionPosePath(actor.identity, resolveChampionPose(actor.identity, {
          alive: Number(actor.hp ?? 1) > 0, inCombat: true, arcadeEntity: row,
        }))
      : null;
    const image = spriteImage(path);
    const size = opponent ? 48 : 56;
    const drawHeight = poseArt ? size * 1.7 : size;
    const drawWidth = poseArt ? drawHeight * (poseArt.width / poseArt.height) : size;
    const airborne = Number(interpolated.position[2] || 0) > 0.1 || trav.isTraversing;
    const squash = airborne ? 1 - clamp((Number(interpolated.position[2] || 0) + trav.elevationZ) / 60, 0, 0.18) : 1;

    const authored=poseArt && image?.complete && image.naturalWidth && image.dataset.failed !== 'true';
    if(!rigged)rig.artSockets=null;
    if(authored){
      rig.artSockets=drawChampion(context,rig,image,poseArt,resolveChampionPose(actor.identity,{alive:model.alive,inCombat:true,arcadeEntity:row}),{down:!model.alive,paint:false});
    }
    if(prepareOnly)return;
    if(!rigged){
    context.save();
    context.globalAlpha = row.active === false ? 0.25 : 1;

    // Ground shadow
    context.fillStyle = 'rgba(0,0,0,.45)';
    context.beginPath();
    context.ellipse(point.x, point.groundY + 3, size * .52 * (airborne ? 0.75 : 1), 7, 0, 0, Math.PI * 2);
    context.fill();

    if (row.invulnerable) context.globalAlpha *= 0.55;

    if (poseArt && image && image.complete && image.naturalWidth && image.dataset.failed !== 'true') {
      rig.artSockets=drawChampion(context,rig,image,poseArt,resolveChampionPose(actor.identity,{alive:model.alive,inCombat:true,arcadeEntity:row}),{down:!model.alive});

    } else {
      rig.artSockets=null;
      drawPuppet(context, rig, model, {shadow:false});
    }
    context.restore();
    }

    // HP Bar
    const hp = Number(actor.hp); const max = Number(actor.max_hp);
    const showBar = options.hpBars === 'all' || (options.hpBars === 'enemies' && opponent) || (options.hpBars === 'party' && !opponent);
    if (showBar && Number.isFinite(hp) && max > 0) {
      const ratio = clamp(hp / max, 0, 1);
      const barW = 46; const barX = point.x - barW / 2; const barY = actorY - rig.scale * ((rigged?.heightUnits || 98) + 12);
      context.fillStyle = 'rgba(10,12,18,.85)'; context.fillRect(barX - 1, barY - 1, barW + 2, 7);
      context.fillStyle = opponent ? '#c2473a' : ratio <= .25 ? '#b53b2e' : ratio <= .5 ? '#c0902e' : '#3f9d56';
      context.fillRect(barX, barY, barW * ratio, 5);
      if (options.hpNumbers) {
        context.fillStyle = '#fff'; context.font = '8px monospace'; context.textAlign = 'center';
        context.fillText(`${Math.max(0, hp)}/${max}`, point.x, barY - 3);
      }
    }
    context.fillStyle = '#f1eadc';
    context.textAlign = 'center';
    context.font = '11px Georgia, serif';
    context.fillText(actor.name || id, point.x, point.groundY + 22);
    context.textAlign = 'start';
    const modeTag = trav.pose ? trav.pose.toUpperCase() : (row.movement_mode ? row.movement_mode.toUpperCase() : '');
    const tag = row.combo_tier ? [modeTag, `COMBO x${row.combo_tier + 1}`].filter(Boolean).join(' · ') : modeTag;
    if (tag) {
      context.fillStyle = '#c9a86a';
      context.font = '9px Georgia, serif';
      context.fillText(tag, point.x - size / 2, point.groundY + 36);
    }
  }

  function draw(now) {
    const dt = Math.min(64, now - lastTime);
    lastTime = now;

    const reduced = options.reducedMotion || globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    resize();
    const camera = cameraX();
    context.clearRect(0, 0, width, height);
    drawBackground(camera);

    if (current) {
      (current.obstacles || []).forEach(obstacle => drawObstacle(obstacle, camera));

      const amount = clamp((now - changedAt) / 160, 0, 1);
      Object.entries(current.entities || {}).forEach(([id,row])=>drawEntity(id,row,amount,camera,dt,true));
      if(!reduced)fx.update(dt,(id,socket)=>{const r=entityRigs.get(id);return r?(r.artSockets?.[socket==='body'?'chest':socket]||r.getSocket(socket)):null;});
      // Draw Ground Auras (beneath entity feet)
      for (const aura of fx.auras.values()) {
        if (!reduced && aura.socket === 'ground') {
          const r = entityRigs.get(aura.entityId);
          if (r) {
            const pos = r.getSocket('ground');
            aura.draw(context, pos.x, pos.y);
          }
        }
      }

      (current.projectiles || []).forEach(projectile => drawProjectile(projectile, camera));
      Object.entries(current.entities || {}).forEach(([id, row]) => drawEntity(id, row, amount, camera, 0));

      // Draw FX (shockwaves, particles, body/head auras) on top
      for (let i = 0; !reduced && i < fx.shockwaves.length; i++) fx.shockwaves[i].draw(context);
      for (let i = 0; !reduced && i < fx.particles.length; i++) {
        if (fx.particles[i].active) fx.particles[i].draw(context);
      }
      for (const aura of fx.auras.values()) {
        if (!reduced && aura.socket !== 'ground') {
          const r = entityRigs.get(aura.entityId);
          if (r) {
            const pos = (r.artSockets?.[aura.socket === 'body' ? 'chest' : aura.socket] || r.getSocket(aura.socket));
            aura.draw(context, pos.x, pos.y);
          }
        }
      }
    } else {
      context.fillStyle = '#c9a86a';
      context.font = '14px Georgia, serif';
      context.fillText('Waiting for the host frame…', 24, 34);
    }
    frameRequest = requestAnimationFrame(draw);
  }

  resize();
  if (typeof ResizeObserver === 'function') {
    resizeObserver = new ResizeObserver(() => {
      if (resizeRequest) cancelAnimationFrame(resizeRequest);
      resizeRequest = requestAnimationFrame(() => { resizeRequest = 0; resize(); });
    });
    resizeObserver.observe(container);
  }
  frameRequest = requestAnimationFrame(draw);

  return {
    element: canvas,
    setState(next) {
      if (!next || typeof next !== 'object') return;
      if (current && (Number(next.frame) < Number(current.frame))) { previous=null; current=null; entityRigs.clear(); traversal.clear(); fx.clear(); }
      for(const id of entityRigs.keys())if(!next.entities?.[id]){entityRigs.delete(id);traversal.remove(id);fx.removeAura(id);}
      if (current?.projectiles && next?.projectiles) {
        const nextIds = new Set(next.projectiles.map(p => p.projectile_id));
        for (const p of current.projectiles) {
          if (!nextIds.has(p.projectile_id)) {
            const cam = cameraX();
            const pt = worldToScreen(p.position, cam);
            fx.spawnImpact(pt.x, pt.y - 10, p.damage_type || 'default', {radius: 26, count: 18});
          }
        }
      }
      previous = current;
      current = next;
      changedAt = performance.now();
    },
    setOptions(next) {
      if(next?.sceneKey !== undefined && options.sceneKey !== undefined && next.sceneKey !== options.sceneKey){current=null;previous=null;entityRigs.clear();traversal.clear();fx.clear();}
      options = {...options, ...(next || {})};
    },
    setActors(next) {
      actors = new Map((next || []).filter(Boolean).map(actor => [actor.id, actor]));
    },
    destroy() {
      cancelAnimationFrame(frameRequest);
      if (resizeRequest) cancelAnimationFrame(resizeRequest);
      resizeObserver?.disconnect();
      fx.clear();
      entityRigs.clear();
      traversal.clear();
      canvas.remove();
    },
  };

}
