/**
 * fx-engine.js — Unified Canvas FX Engine for Hollow Star Reliquary (HSR).
 * 
 * Provides high-performance 60 FPS procedural visuals for:
 * 1. Projectiles (missile trails, glowing orbs, tracer ribbons, arrows)
 * 2. Impact shockwaves & elemental bursts (fire, cold, radiant, necrotic, etc.)
 * 3. Multi-socket persistent auras:
 *    - 'ground': Rotating geometric rune circles beneath feet
 *    - 'body': Shimmering spherical / hexagonal energy shields
 *    - 'head': Overhead halos, crowns, or status wisps
 * 
 * Usable both as an embedded renderer inside `arcade-canvas.js` and as a transparent
 * overlay canvas over the turn-based `.combat-stage`.
 */

export const DAMAGE_PALETTES = Object.freeze({
  fire: {
    primary: '#ff5e13',
    secondary: '#ffa238',
    glow: 'rgba(255, 94, 19, 0.45)',
    particles: ['#ff4500', '#ff8c00', '#ffd700', '#fff3a8'],
  },
  cold: {
    primary: '#70d6ff',
    secondary: '#bbf0ff',
    glow: 'rgba(112, 214, 255, 0.4)',
    particles: ['#a0e9ff', '#d0f4ff', '#ffffff', '#70d6ff'],
  },
  lightning: {
    primary: '#00f5d4',
    secondary: '#80ffdb',
    glow: 'rgba(0, 245, 212, 0.5)',
    particles: ['#00f5d4', '#e0fbfc', '#ffffff', '#7b2cbf'],
  },
  radiant: {
    primary: '#ffd166',
    secondary: '#fff3b0',
    glow: 'rgba(255, 209, 102, 0.45)',
    particles: ['#ffd166', '#fff3b0', '#ffffff', '#e9d8a6'],
  },
  necrotic: {
    primary: '#9d4edd',
    secondary: '#c77dff',
    glow: 'rgba(157, 78, 221, 0.4)',
    particles: ['#7b2cbf', '#9d4edd', '#3c096c', '#10002b'],
  },
  force: {
    primary: '#b5179e',
    secondary: '#f72585',
    glow: 'rgba(181, 23, 158, 0.45)',
    particles: ['#b5179e', '#7209b7', '#4895ef', '#4cc9f0'],
  },
  acid: {
    primary: '#52b788',
    secondary: '#74c69d',
    glow: 'rgba(82, 183, 136, 0.45)',
    particles: ['#40916c', '#52b788', '#95d5b2', '#d8f3dc'],
  },
  poison: {
    primary: '#38b000',
    secondary: '#70e000',
    glow: 'rgba(56, 176, 0, 0.4)',
    particles: ['#007200', '#38b000', '#9ef01a', '#ccff33'],
  },
  psychic: {
    primary: '#f15bb5',
    secondary: '#fee440',
    glow: 'rgba(241, 91, 181, 0.4)',
    particles: ['#f15bb5', '#9b5de5', '#00bbf9', '#fee440'],
  },
  thunder: {
    primary: '#48cae4',
    secondary: '#0096c7',
    glow: 'rgba(72, 202, 228, 0.45)',
    particles: ['#90e0ef', '#00b4d8', '#0077b6', '#caf0f8'],
  },
  heal: {
    primary: '#55d6be',
    secondary: '#a7bed3',
    glow: 'rgba(85, 214, 190, 0.45)',
    particles: ['#55d6be', '#acf39d', '#ffffff', '#e0fbfb'],
  },
  physical: {
    primary: '#d8c18b',
    secondary: '#f4ede2',
    glow: 'rgba(216, 193, 139, 0.35)',
    particles: ['#c9a86a', '#e8d5b5', '#ffffff', '#8b7355'],
  },
  default: {
    primary: '#c9a86a',
    secondary: '#f2d78c',
    glow: 'rgba(201, 168, 106, 0.35)',
    particles: ['#c9a86a', '#e8d5b5', '#ffffff', '#d4af37'],
  },
});

export function getPalette(damageType) {
  if (!damageType) return DAMAGE_PALETTES.default;
  const key = String(damageType).toLowerCase().replace(/[^a-z]/g, '');
  return DAMAGE_PALETTES[key] || DAMAGE_PALETTES.default;
}

/**
 * Procedural Particle System
 */
class Particle {
  constructor() {
    this.active = false;
    this.x = 0;
    this.y = 0;
    this.vx = 0;
    this.vy = 0;
    this.color = '#fff';
    this.size = 2;
    this.alpha = 1;
    this.decay = 0.02;
    this.gravity = 0;
    this.shape = 'circle'; // circle, spark, shard
    this.rotation = 0;
    this.vrot = 0;
  }

  spawn(x, y, vx, vy, color, size, decay, gravity = 0, shape = 'circle') {
    this.active = true;
    this.x = x;
    this.y = y;
    this.vx = vx;
    this.vy = vy;
    this.color = color;
    this.size = size;
    this.alpha = 1;
    this.decay = decay;
    this.gravity = gravity;
    this.shape = shape;
    this.rotation = Math.random() * Math.PI * 2;
    this.vrot = (Math.random() - 0.5) * 0.2;
  }

  update() {
    if (!this.active) return false;
    this.x += this.vx;
    this.y += this.vy;
    this.vy += this.gravity;
    this.alpha -= this.decay;
    this.rotation += this.vrot;
    if (this.alpha <= 0) {
      this.active = false;
      return false;
    }
    return true;
  }

  draw(ctx) {
    if (!this.active || this.alpha <= 0) return;
    ctx.save();
    ctx.globalAlpha = Math.max(0, Math.min(1, this.alpha));
    ctx.fillStyle = this.color;
    ctx.translate(this.x, this.y);
    ctx.rotate(this.rotation);

    if (this.shape === 'circle') {
      ctx.beginPath();
      ctx.arc(0, 0, this.size, 0, Math.PI * 2);
      ctx.fill();
    } else if (this.shape === 'spark') {
      ctx.beginPath();
      ctx.moveTo(-this.size * 1.5, 0);
      ctx.lineTo(0, -this.size * 0.5);
      ctx.lineTo(this.size * 1.5, 0);
      ctx.lineTo(0, this.size * 0.5);
      ctx.closePath();
      ctx.fill();
    } else if (this.shape === 'shard') {
      ctx.beginPath();
      ctx.moveTo(-this.size, -this.size * 1.5);
      ctx.lineTo(this.size * 0.8, -this.size * 0.5);
      ctx.lineTo(this.size * 0.4, this.size * 1.5);
      ctx.lineTo(-this.size * 0.8, this.size * 0.8);
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }
}

/**
 * Animated Shockwave / Ring Effect
 */
class Shockwave {
  constructor(x, y, maxRadius, color, duration = 400, lineWidth = 3) {
    this.x = x;
    this.y = y;
    this.maxRadius = maxRadius;
    this.color = color;
    this.duration = duration;
    this.lineWidth = lineWidth;
    this.elapsed = 0;
    this.done = false;
  }

  update(dt) {
    this.elapsed += dt;
    if (this.elapsed >= this.duration) {
      this.done = true;
    }
  }

  draw(ctx) {
    if (this.done) return;
    const progress = Math.min(1, this.elapsed / this.duration);
    const radius = this.maxRadius * Math.sin((progress * Math.PI) / 2);
    const alpha = Math.max(0, 1 - progress);

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = this.color;
    ctx.lineWidth = this.lineWidth * (1 - progress * 0.5);
    ctx.beginPath();
    ctx.arc(this.x, this.y, radius, 0, Math.PI * 2);
    ctx.stroke();

    // Subtle inner glow ring
    ctx.globalAlpha = alpha * 0.4;
    ctx.lineWidth = this.lineWidth * 2;
    ctx.beginPath();
    ctx.arc(this.x, this.y, Math.max(1, radius * 0.85), 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }
}

/**
 * Trajectory-based Projectile (used in tactical stage and for arcade tracers)
 */
class ProjectileFlight {
  constructor({
    id,
    fromX,
    fromY,
    toX,
    toY,
    speed = 0.8, // normalized units per ms or speed factor
    durationMs = null,
    damageType = 'default',
    archetype = 'orb', // 'arrow', 'orb', 'bolt', 'beam'
    onHit = null,
  }) {
    this.id = id || Math.random().toString(36).substring(2, 9);
    this.fromX = fromX;
    this.fromY = fromY;
    this.toX = toX;
    this.toY = toY;
    this.currentX = fromX;
    this.currentY = fromY;
    this.damageType = damageType;
    this.palette = getPalette(damageType);
    this.archetype = archetype;
    this.onHit = onHit;
    this.done = false;

    const dx = toX - fromX;
    const dy = toY - fromY;
    this.dist = Math.hypot(dx, dy);
    this.angle = Math.atan2(dy, dx);

    // If duration not specified, compute from distance and speed
    const defaultDuration = Math.max(220, Math.min(750, this.dist * 1.5));
    this.duration = durationMs || defaultDuration;
    this.elapsed = 0;
    this.history = []; // trail positions: [{x, y, alpha}]
  }

  update(dt, emitParticle) {
    if (this.done) return;
    this.elapsed += dt;
    const progress = Math.min(1, this.elapsed / this.duration);

    // Parabolic arc for arrows, straight or slight corkscrew for magical bolts
    const linearX = this.fromX + (this.toX - this.fromX) * progress;
    let linearY = this.fromY + (this.toY - this.fromY) * progress;

    if (this.archetype === 'arrow') {
      const arcHeight = Math.min(50, this.dist * 0.18);
      linearY -= Math.sin(progress * Math.PI) * arcHeight;
    } else if (this.archetype === 'bolt') {
      const wobble = Math.sin(progress * Math.PI * 8) * 3;
      linearY += Math.cos(this.angle) * wobble;
    }

    this.currentX = linearX;
    this.currentY = linearY;

    // Trail history
    this.history.unshift({x: this.currentX, y: this.currentY, time: performance.now()});
    if (this.history.length > 12) this.history.pop();

    // Spawn trail particles
    if (emitParticle && Math.random() < 0.65) {
      const pColor = this.palette.particles[Math.floor(Math.random() * this.palette.particles.length)];
      const spreadX = (Math.random() - 0.5) * 4;
      const spreadY = (Math.random() - 0.5) * 4;
      emitParticle(
        this.currentX,
        this.currentY,
        -Math.cos(this.angle) * (1 + Math.random() * 2) + spreadX,
        -Math.sin(this.angle) * (1 + Math.random() * 2) + spreadY,
        pColor,
        Math.random() * 3 + 1.5,
        0.05 + Math.random() * 0.03,
        this.archetype === 'arrow' ? 0.05 : 0,
        this.archetype === 'arrow' ? 'spark' : 'circle'
      );
    }

    if (progress >= 1) {
      this.done = true;
      if (typeof this.onHit === 'function') {
        this.onHit(this.toX, this.toY, this.damageType);
      }
    }
  }

  draw(ctx) {
    if (this.done) return;
    ctx.save();

    if(this.archetype==='beam') {
      ctx.strokeStyle=this.palette.primary;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(this.fromX,this.fromY);
      for(let i=1;i<=12;i++){const k=i/12,j=i===12?0:Math.sin(i*17+Math.floor(this.elapsed/45))*9;
        ctx.lineTo(this.fromX+(this.toX-this.fromX)*k-Math.sin(this.angle)*j,this.fromY+(this.toY-this.fromY)*k+Math.cos(this.angle)*j);}
      ctx.stroke();ctx.restore();return;
    }
    // 1. Draw glowing tracer ribbon
    if (this.history.length > 1) {
      ctx.beginPath();
      ctx.moveTo(this.history[0].x, this.history[0].y);
      for (let i = 1; i < this.history.length; i++) {
        ctx.lineTo(this.history[i].x, this.history[i].y);
      }
      ctx.strokeStyle = this.palette.glow;
      ctx.lineWidth = this.archetype === 'arrow' ? 2 : 6;
      ctx.lineCap = 'round';
      ctx.stroke();

      ctx.strokeStyle = this.palette.primary;
      ctx.lineWidth = this.archetype === 'arrow' ? 1.2 : 2.5;
      ctx.stroke();
    }

    // 2. Draw head/projectile body
    ctx.translate(this.currentX, this.currentY);
    ctx.rotate(this.angle);

    if (this.archetype === 'arrow') {
      // Draw stylized arrow
      ctx.fillStyle = this.palette.secondary;
      ctx.strokeStyle = '#2b2319';
      ctx.lineWidth = 1;

      // Shaft
      ctx.beginPath();
      ctx.moveTo(-16, 0);
      ctx.lineTo(4, 0);
      ctx.stroke();

      // Arrowhead
      ctx.beginPath();
      ctx.moveTo(8, 0);
      ctx.lineTo(0, -4);
      ctx.lineTo(2, 0);
      ctx.lineTo(0, 4);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Fletching
      ctx.fillStyle = '#f0e6d2';
      ctx.beginPath();
      ctx.moveTo(-16, 0);
      ctx.lineTo(-20, -3);
      ctx.lineTo(-14, 0);
      ctx.lineTo(-20, 3);
      ctx.closePath();
      ctx.fill();
    } else {
      // Magical orb / bolt
      const rad = this.archetype === 'bolt' ? 5 : 6;

      // Outer glow halo
      const grad = ctx.createRadialGradient(0, 0, 1, 0, 0, rad * 2.2);
      grad.addColorStop(0, this.palette.secondary);
      grad.addColorStop(0.4, this.palette.primary);
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(0, 0, rad * 2.2, 0, Math.PI * 2);
      ctx.fill();

      // Bright white core
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(0, 0, rad * 0.55, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }
}

/**
 * Persistent Aura Effect instance (attached to entity position or socket)
 */
class ActiveAura {
  constructor({
    id,
    entityId,
    socket = 'ground', // 'ground', 'body', 'head'
    auraType = 'radiant', // maps to palette
    radius = 28,
    durationMs = null, // null for permanent until removed
    label = '',
  }) {
    this.id = id || `${entityId}_${socket}_${Date.now()}`;
    this.entityId = entityId;
    this.socket = socket;
    this.auraType = auraType;
    this.palette = getPalette(auraType);
    this.radius = radius;
    this.duration = durationMs;
    this.elapsed = 0;
    this.rotation = Math.random() * Math.PI * 2;
    this.done = false;
    this.label = label;
  }

  update(dt, x, y, emitParticle) {
    if (this.done) return;
    this.elapsed += dt;
    if (this.duration && this.elapsed >= this.duration) {
      this.done = true;
      return;
    }

    this.rotation += 0.015; // Slow ambient rotation

    // Ambient aura particles
    if (emitParticle && Math.random() < 0.22) {
      const pColor = this.palette.particles[Math.floor(Math.random() * this.palette.particles.length)];
      if (this.socket === 'ground') {
        const angle = Math.random() * Math.PI * 2;
        const dist = this.radius * (0.6 + Math.random() * 0.4);
        emitParticle(
          x + Math.cos(angle) * dist,
          y + Math.sin(angle) * dist * 0.35, // foreshortened ground ellipse
          (Math.random() - 0.5) * 0.4,
          -(0.4 + Math.random() * 0.8), // float gently upward
          pColor,
          Math.random() * 2 + 1,
          0.02 + Math.random() * 0.015,
          -0.01,
          'circle'
        );
      } else if (this.socket !== 'head') {
        const angle = Math.random() * Math.PI * 2;
        emitParticle(
          x + Math.cos(angle) * (this.radius * 0.9),
          y + Math.sin(angle) * (this.radius * 0.9),
          (Math.random() - 0.5) * 0.5,
          (Math.random() - 0.5) * 0.5,
          pColor,
          Math.random() * 2.5 + 1,
          0.03,
          0,
          'spark'
        );
      } else if (this.socket === 'head') {
        emitParticle(
          x + (Math.random() - 0.5) * 16,
          y - 6 + (Math.random() - 0.5) * 6,
          (Math.random() - 0.5) * 0.3,
          -(0.5 + Math.random() * 0.6),
          pColor,
          Math.random() * 2 + 1.2,
          0.025,
          -0.02,
          'shard'
        );
      }
    }
  }

  draw(ctx, x, y) {
    if (this.done) return;
    const pulse = 1 + Math.sin(this.elapsed * 0.0035) * 0.07;
    const effectiveRadius = this.radius * pulse;

    ctx.save();
    ctx.translate(x, y);

    if (this.socket === 'ground') {
      // 1. Ground Runic Circle (Foreshortened 2.6:1 ellipse)
      const ry = effectiveRadius * 0.38;
      const rx = effectiveRadius;

      // Soft ground glow fill
      const grad = ctx.createRadialGradient(0, 0, 1, 0, 0, rx);
      grad.addColorStop(0, this.palette.glow);
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
      ctx.fill();

      // Outer ring
      ctx.strokeStyle = this.palette.primary;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
      ctx.stroke();

      // Inner rune ring
      ctx.strokeStyle = this.palette.secondary;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.ellipse(0, 0, rx * 0.72, ry * 0.72, 0, 0, Math.PI * 2);
      ctx.stroke();

      // Rotating radial tick runes
      ctx.save();
      const numTicks = 8;
      for (let i = 0; i < numTicks; i++) {
        const tickAngle = this.rotation + (i * (Math.PI * 2)) / numTicks;
        const tx1 = Math.cos(tickAngle) * rx * 0.72;
        const ty1 = Math.sin(tickAngle) * ry * 0.72;
        const tx2 = Math.cos(tickAngle) * rx;
        const ty2 = Math.sin(tickAngle) * ry;
        ctx.beginPath();
        ctx.moveTo(tx1, ty1);
        ctx.lineTo(tx2, ty2);
        ctx.stroke();
      }
      ctx.restore();
    } else if (this.socket !== 'head') {
      // 2. Body Shield Sphere / Hexagonal Barrier
      const r = effectiveRadius;

      // Shimmering barrier shell
      const grad = ctx.createRadialGradient(0, 0, r * 0.4, 0, 0, r);
      grad.addColorStop(0, 'rgba(255,255,255,0.04)');
      grad.addColorStop(0.7, this.palette.glow);
      grad.addColorStop(1, this.palette.primary);

      ctx.fillStyle = grad;
      ctx.globalAlpha = 0.55 + Math.sin(this.elapsed * 0.005) * 0.2;
      ctx.beginPath();
      ctx.arc(0, 0, r, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = this.palette.secondary;
      ctx.lineWidth = 1.8;
      ctx.stroke();

      // Hexagonal subtle lattice lines
      ctx.globalAlpha = 0.35;
      ctx.strokeStyle = this.palette.primary;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let i = 0; i < 6; i++) {
        const a = (i * Math.PI) / 3 + this.rotation * 0.5;
        const hx = Math.cos(a) * r * 0.92;
        const hy = Math.sin(a) * r * 0.92;
        if (i === 0) ctx.moveTo(hx, hy);
        else ctx.lineTo(hx, hy);
      }
      ctx.closePath();
      ctx.stroke();
    } else if (this.socket === 'head') {
      // 3. Overhead Halo / Holy Crown / Status Wisp
      const haloR = effectiveRadius * 0.45;
      const haloY = -effectiveRadius * 0.8;

      ctx.translate(0, haloY);
      ctx.strokeStyle = this.palette.primary;
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      ctx.ellipse(0, 0, haloR, haloR * 0.35, 0, 0, Math.PI * 2);
      ctx.stroke();

      // Halo bright center
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.ellipse(0, 0, haloR * 0.8, haloR * 0.28, 0, 0, Math.PI * 2);
      ctx.stroke();

      // Crown spikes or radiant rays
      ctx.strokeStyle = this.palette.secondary;
      for (let i = -2; i <= 2; i++) {
        const rx = i * (haloR * 0.35);
        ctx.beginPath();
        ctx.moveTo(rx, 0);
        ctx.lineTo(rx * 1.3, -8 - Math.abs(i) * 2);
        ctx.stroke();
      }
    }

    ctx.restore();
  }
}

/**
 * FXEngine — Orchestrates particle pooling, active shockwaves, projectiles, and auras.
 */
export class FXEngine {
  constructor({maxParticles = 300} = {}) {
    this.particles = Array.from({length: maxParticles}, () => new Particle());
    this.shockwaves = [];
    this.spellReactions = [];
    this.projectiles = [];
    this.auras = new Map(); // key: aura id -> ActiveAura
    this.lastTime = performance.now();
  }

  emitParticle(x, y, vx, vy, color, size, decay, gravity = 0, shape = 'circle') {
    const p = this.particles.find(item => !item.active);
    if (p) {
      p.spawn(x, y, vx, vy, color, size, decay, gravity, shape);
    }
  }

  /**
   * Spawn an elemental shockwave / impact burst
   */
  spawnImpact(x, y, damageType = 'default', {radius = 32, count = 20} = {}) {
    const palette = getPalette(damageType);

    // Shockwave expansion ring
    this.shockwaves.push(new Shockwave(x, y, radius, palette.primary, 360, 2.5));

    // Particle burst
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 1.5 + Math.random() * 4.5;
      const color = palette.particles[Math.floor(Math.random() * palette.particles.length)];
      const size = Math.random() * 3 + 1.5;
      const shape = damageType === 'cold' ? 'shard' : damageType === 'lightning' ? 'spark' : 'circle';
      const gravity = damageType === 'fire' || damageType === 'heal' ? -0.05 : 0.08;

      this.emitParticle(
        x,
        y,
        Math.cos(angle) * speed,
        Math.sin(angle) * speed,
        color,
        size,
        0.025 + Math.random() * 0.02,
        gravity,
        shape
      );
    }
  }

  /**
   * Spawn a flying projectile from (fromX, fromY) to (toX, toY)
   */
  spawnProjectile({
    id,
    fromX,
    fromY,
    toX,
    toY,
    speed,
    durationMs,
    damageType = 'default',
    archetype = 'orb',
    impactOnHit = true,
    onHit,
  }) {
    const flight = new ProjectileFlight({
      id,
      fromX,
      fromY,
      toX,
      toY,
      speed,
      durationMs,
      damageType,
      archetype,
      onHit: (hitX, hitY, dtype) => {
        if(impactOnHit)this.spawnImpact(hitX, hitY, dtype);
        if (typeof onHit === 'function') onHit(hitX, hitY, dtype);
      },
    });
    this.projectiles.push(flight);
    return flight;
  }

  /**
   * Register or refresh a persistent aura on an entity
   */
  setAura(entityId, {socket = 'ground', auraType = 'radiant', radius = 28, durationMs = null, label = ''} = {}) {
    const key = `${entityId}_${socket}`;
    const aura = new ActiveAura({
      id: key,
      entityId,
      socket,
      auraType,
      radius,
      durationMs,
      label,
    });
    this.auras.set(key, aura);
    return aura;
  }

  /**
   * Remove a persistent aura
   */
  removeAura(entityId, socket = null) {
    if (socket) {
      this.auras.delete(`${entityId}_${socket}`);
    } else {
      for (const [key, aura] of this.auras.entries()) {
        if (aura.entityId === entityId) {
          this.auras.delete(key);
        }
      }
    }
  }

  /**
   * Clear all active effects
   */
  spawnSpellReaction(entityId,element) {
    this.spellReactions.push({entityId,element,elapsed:0,duration:850});
    if(this.spellReactions.length>32)this.spellReactions.shift();
  }
  clear() {
    this.spellReactions.length=0;
    this.particles.forEach(p => { p.active = false; });
    this.shockwaves.length = 0;
    this.projectiles.length = 0;
    this.auras.clear();
  }

  /**
   * Advance simulation by dt milliseconds
   */
  update(dt, getEntityCoords = () => null) {
    const emit = (x, y, vx, vy, color, size, decay, grav, shp) =>
      this.emitParticle(x, y, vx, vy, color, size, decay, grav, shp);

    for(const effect of this.spellReactions)effect.elapsed+=dt;
    this.spellReactions=this.spellReactions.filter(e=>e.elapsed<e.duration);
    // 1. Update particles
    for (let i = 0; i < this.particles.length; i++) {
      if (this.particles[i].active) {
        this.particles[i].update();
      }
    }

    // 2. Update shockwaves
    for (let i = this.shockwaves.length - 1; i >= 0; i--) {
      this.shockwaves[i].update(dt);
      if (this.shockwaves[i].done) {
        this.shockwaves.splice(i, 1);
      }
    }

    // 3. Update projectiles
    for (let i = this.projectiles.length - 1; i >= 0; i--) {
      this.projectiles[i].update(dt, emit);
      if (this.projectiles[i].done) {
        this.projectiles.splice(i, 1);
      }
    }

    // 4. Update auras
    for (const [key, aura] of this.auras.entries()) {
      const coords = getEntityCoords(aura.entityId, aura.socket);
      if (coords) {
        aura.update(dt, coords.x, coords.y, emit);
      }
      if (aura.done) {
        this.auras.delete(key);
      }
    }
  }

  /**
   * Render all effects onto a 2D Canvas context
   */
  draw(ctx, getEntityCoords = () => null) {
    // 1. Draw auras (Ground auras first so characters stand on top)
    for (const aura of this.auras.values()) {
      if (aura.socket === 'ground') {
        const coords = getEntityCoords(aura.entityId, aura.socket);
        if (coords) aura.draw(ctx, coords.x, coords.y);
      }
    }

    for(const effect of this.spellReactions) {
      const at=getEntityCoords(effect.entityId,'chest');if(!at)continue;
      const p=effect.elapsed/effect.duration,r=26+8*p;
      ctx.save();ctx.translate(at.x,at.y);ctx.globalAlpha=Math.sin(Math.PI*p);
      ctx.strokeStyle=getPalette(effect.element).primary;ctx.fillStyle=ctx.strokeStyle;ctx.lineWidth=2;
      if(effect.element==='cold') {
        for(let i=0;i<8;i++){const a=i*Math.PI/4;ctx.save();ctx.rotate(a);ctx.beginPath();
          ctx.moveTo(0,-r-12);ctx.lineTo(5,-r+6);ctx.lineTo(0,-r);ctx.lineTo(-5,-r+6);ctx.closePath();ctx.stroke();ctx.restore();}
      } else if(effect.element==='lightning') {
        for(let i=0;i<3;i++){ctx.beginPath();for(let j=0;j<9;j++){const x=(i-1)*17+Math.sin(j*13+i+Math.floor(p*12))*9,y=-38+j*9;j?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();}
      } else if(effect.element==='fire') {
        for(let i=0;i<7;i++){const x=(i-3)*8,y=18-Math.sin(i*3+p*5)*5;ctx.beginPath();ctx.moveTo(x-5,y);
          ctx.quadraticCurveTo(x-10,y-20,x+Math.sin(p*7+i)*6,y-40);ctx.quadraticCurveTo(x+10,y-15,x+5,y);ctx.fill();}
      } else if(effect.element==='heal') {
        for(let i=0;i<5;i++){const x=Math.sin(i*2.4)*24,y=25-65*p+i*5;ctx.beginPath();ctx.moveTo(x-4,y);ctx.lineTo(x+4,y);ctx.moveTo(x,y-4);ctx.lineTo(x,y+4);ctx.stroke();}
      } else {
        for(let i=0;i<3;i++){ctx.beginPath();ctx.ellipse(0,(i-1)*15,r,7+p*5,p*.4,0,Math.PI*2);ctx.stroke();}
      }
      ctx.restore();
    }
    // 2. Draw shockwaves
    for (let i = 0; i < this.shockwaves.length; i++) {
      this.shockwaves[i].draw(ctx);
    }

    // 3. Draw particles
    for (let i = 0; i < this.particles.length; i++) {
      if (this.particles[i].active) {
        this.particles[i].draw(ctx);
      }
    }

    // 4. Draw projectiles
    for (let i = 0; i < this.projectiles.length; i++) {
      this.projectiles[i].draw(ctx);
    }

    // 5. Draw body & head auras (on top of characters/particles)
    for (const aura of this.auras.values()) {
      if (aura.socket !== 'ground') {
        const coords = getEntityCoords(aura.entityId, aura.socket);
        if (coords) aura.draw(ctx, coords.x, coords.y);
      }
    }
  }
}

/**
 * Helper to mount a transparent FX overlay canvas atop an existing DOM element (e.g. .combat-stage)
 */
export function createFXOverlay(containerElement, {reducedMotion = () => false} = {}) {
  const canvas = document.createElement('canvas');
  canvas.className = 'hsr-fx-overlay';
  canvas.style.position = 'absolute';
  canvas.style.inset = '0';
  canvas.style.pointerEvents = 'none';
  canvas.style.zIndex = '30';
  containerElement.appendChild(canvas);

  const ctx = canvas.getContext('2d');
  const engine = new FXEngine();
  let frameId = 0;
  let lastTime = performance.now();
  let getCoordsCallback = () => null;

  function resize() {
    const rect = containerElement.getBoundingClientRect();
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    const w = Math.floor(rect.width);
    const h = Math.floor(rect.height);
    if (w > 0 && h > 0 && (canvas.width !== w * dpr || canvas.height !== h * dpr)) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
  }

  function loop(now) {
    if (typeof document !== 'undefined' && document.hidden) {
      frameId = requestAnimationFrame(loop);
      return;
    }
    const dt = Math.min(64, now - lastTime);
    lastTime = now;

    if (!canvas.isConnected) { engine.clear(); return; }
    resize();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    engine.update(dt, getCoordsCallback);
    if (!reducedMotion()) engine.draw(ctx, getCoordsCallback);

    frameId = requestAnimationFrame(loop);
  }

  frameId = requestAnimationFrame(loop);

  return {
    engine,
    canvas,
    setCoordsProvider(provider) {
      getCoordsCallback = provider;
    },
    destroy() {
      cancelAnimationFrame(frameId);
      engine.clear();
      canvas.remove();
    },
  };
}

// Reconcile persistent public conditions, retaining finite-duration impact effects.
export function reconcileAuras(engine,id,row={}) {
  const tags=new Set(Array.isArray(row.conditions)?row.conditions:[]);
  for(const [key,value]of Object.entries(row.status_tags||{}))if(value)tags.add(key);
  const wanted={};
  if(row.blocking||tags.has('shield'))wanted.body='force';
  if(tags.has('poisoned'))wanted.body='poison';
  if(tags.has('burning'))wanted.body='fire';
  if(row.invulnerable)wanted.head='radiant';
  if(tags.has('bless')||tags.has('blessed'))wanted.ground='radiant';
  for(const socket of ['body','head','ground']) {
    const old=engine.auras.get(`${id}_${socket}`),type=wanted[socket];
    if(type){if(!old||old.auraType!==type)engine.setAura(id,{socket,auraType:type,radius:socket==='head'?22:28});}
    else if(old&&old.duration===null)engine.removeAura(id,socket);
  }
}
