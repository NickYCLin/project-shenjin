/**
 * Deterministic combat model, independent of the renderer.
 * World axes match Three.js: yaw 0 faces +Z, yaw PI faces -Z.
 * Actions return whether they were accepted. step() and restart() return state.
 * Events remain queued until drainEvents() is called; step never drops input events.
 */
export const RULES = Object.freeze({
  arenaRadius: 16.5,
  bossRadius: 1.7,
  playerRadius: 0.5,
  // Reach is measured from the player to the boss's surface.
  attackRange: 2,
  attackWindup: 0.2,
  attackCooldown: 0.55,
  recoverDamageMultiplier: 1.25,
  dodgeCost: 30,
  dodgeDuration: 0.32,
  dodgeInvulnerability: 0.36,
  slamRadius: 3.4,
  windupDuration: 1.1,
  phaseTwoWindupDuration: 0.78,
  slamDuration: 0.3,
  recoveryDuration: 1.05,
  phaseTwoRecoveryDuration: 0.72,
  aspectDuration: 6,
  maxStep: 0.05,
});

const TAU = Math.PI * 2;
const EPSILON = 1e-9;
const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
const finite = (n) => (Number.isFinite(n) ? n : 0);
const distance = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);
const active = (state) =>
  state.status === "ready" || state.status === "playing";

export function createGame() {
  return {
    time: 0,
    status: "ready",
    oath: "ember",
    kills: 0,
    events: [],
    player: {
      x: 0,
      z: 8,
      yaw: Math.PI,
      hp: 100,
      maxHp: 100,
      stamina: 100,
      aspect: 100,
      attackTimer: 0,
      attackElapsed: 0,
      attackId: 0,
      attackResolved: true,
      attackCancelled: false,
      pendingAttack: null,
      dodgeTimer: 0,
      invulnerableTimer: 0,
      aspectTimer: 0,
      oathCooldown: 0,
      dodgeX: 0,
      dodgeZ: -1,
    },
    boss: {
      x: 0,
      z: -5,
      yaw: 0,
      hp: 720,
      maxHp: 720,
      phase: 1,
      state: "idle",
      timer: 0.65,
      targetX: 0,
      targetZ: 8,
      attackId: 0,
      attackPhase: 1,
      windupDuration: RULES.windupDuration,
      recoveryDuration: RULES.recoveryDuration,
      slamRadius: RULES.slamRadius,
    },
  };
}

export function restart(state) {
  // Keep the top-level object stable for renderers that retain it.
  for (const key of Object.keys(state)) delete state[key];
  Object.assign(state, createGame());
  return state;
}

export function start(state) {
  if (state.status === "ready") state.status = "playing";
  return state.status === "playing";
}

export function drainEvents(state) {
  return state.events.splice(0);
}

function emit(state, type, x, z, extra = {}) {
  state.events.push({ type, x, z, time: state.time, ...extra });
}

function updatePhase(state) {
  if (state.boss.hp <= state.boss.maxHp * 0.5) state.boss.phase = 2;
}

export function attack(state) {
  const p = state.player;
  if (!active(state) || p.hp <= 0 || p.attackTimer > 0 || p.dodgeTimer > 0)
    return false;
  start(state);
  p.attackTimer = RULES.attackCooldown;
  p.attackElapsed = 0;
  p.attackId += 1;
  p.attackResolved = false;
  p.attackCancelled = false;
  // An oath switch or aspect activation during the thrust affects the next
  // attack. Position, facing and the boss's recovery are evaluated on impact.
  const isAspect = p.aspectTimer > 0;
  p.pendingAttack = {
    attackId: p.attackId,
    oath: state.oath,
    aspect: isAspect,
    damage:
      ((state.oath === "ember" ? 22 : 16) + 5 * ((state.level ?? 1) - 1)) *
      (isAspect ? 1.75 : 1),
  };
  emit(state, "swing", p.x, p.z, {
    attackId: p.attackId,
    oath: state.oath,
    aspect: isAspect,
  });
  return true;
}

function cancelAttack(state, reason) {
  const p = state.player;
  if (p.attackTimer > 0) p.attackCancelled = true;
  if (!p.pendingAttack) return;
  emit(state, "miss", p.x, p.z, {
    attackId: p.pendingAttack.attackId,
    reason,
  });
  p.pendingAttack = null;
  p.attackResolved = true;
}

function resolveAttack(state) {
  const p = state.player;
  const b = state.boss;
  if (!p.pendingAttack || p.attackElapsed + EPSILON < RULES.attackWindup)
    return;
  if (state.status !== "playing" || p.hp <= 0) {
    cancelAttack(state, "defeat");
    return;
  }
  const pending = p.pendingAttack;
  p.pendingAttack = null;
  p.attackResolved = true;
  const dx = b.x - p.x;
  const dz = b.z - p.z;
  const d = Math.hypot(dx, dz);
  const facing =
    d === 0 ? 1 : (dx * Math.sin(p.yaw) + dz * Math.cos(p.yaw)) / d;
  // The 120-degree forward cone and short reach must still overlap at impact.
  if (
    d > RULES.attackRange + RULES.bossRadius + EPSILON ||
    facing < 0.5 - EPSILON ||
    b.hp <= 0
  ) {
    emit(state, "miss", p.x, p.z, {
      attackId: pending.attackId,
      reason: "outside-reach",
    });
    return;
  }
  const counter = b.state === "recover";
  const damage = Math.round(
    pending.damage * (counter ? RULES.recoverDamageMultiplier : 1),
  );
  b.hp = Math.max(0, b.hp - damage);
  if (!pending.aspect && p.aspectTimer <= 0)
    p.aspect = Math.min(100, p.aspect + 8);
  if (pending.oath === "tide") p.hp = Math.min(p.maxHp, p.hp + 4);
  emit(state, "hit", b.x, b.z, {
    damage,
    aspect: pending.aspect,
    oath: pending.oath,
    attackId: pending.attackId,
    counter,
  });
  updatePhase(state);
  if (b.hp === 0) {
    b.state = "dead";
    b.timer = 0;
    state.status = "won";
    state.kills += 1;
    emit(state, "win", b.x, b.z);
  }
}

export function dodge(state, dx = 0, dz = 0) {
  const p = state.player;
  if (!active(state) || p.dodgeTimer > 0 || p.stamina < RULES.dodgeCost)
    return false;
  start(state);
  dx = finite(dx);
  dz = finite(dz);
  const length = Math.hypot(dx, dz);
  p.dodgeX = length > 0 ? dx / length : Math.sin(p.yaw);
  p.dodgeZ = length > 0 ? dz / length : Math.cos(p.yaw);
  p.stamina -= RULES.dodgeCost;
  p.dodgeTimer = RULES.dodgeDuration;
  p.invulnerableTimer = Math.max(
    p.invulnerableTimer,
    RULES.dodgeInvulnerability,
  );
  // Keep the original cooldown, so cancelling does not enable attack spam.
  cancelAttack(state, "dodge");
  emit(state, "dodge", p.x, p.z);
  return true;
}

export function activateAspect(state) {
  const p = state.player;
  if (!active(state) || p.aspectTimer > 0 || p.aspect < 100) return false;
  start(state);
  p.aspectTimer = RULES.aspectDuration;
  emit(state, "aspect", p.x, p.z);
  return true;
}

export function switchOath(state) {
  if (!active(state) || state.player.oathCooldown > 0) return false;
  state.oath = state.oath === "ember" ? "tide" : "ember";
  state.player.oathCooldown = 1.5;
  return true;
}

function constrainToArena(actor, radius) {
  const d = Math.hypot(actor.x, actor.z);
  if (d > radius) {
    actor.x *= radius / d;
    actor.z *= radius / d;
  }
}

function separateActors(state) {
  const p = state.player;
  const b = state.boss;
  const minDistance = RULES.playerRadius + RULES.bossRadius;
  let dx = p.x - b.x;
  let dz = p.z - b.z;
  const d = Math.hypot(dx, dz);
  if (d < minDistance) {
    if (d < 0.0001) {
      dx = 0;
      dz = 1;
    } else {
      dx /= d;
      dz /= d;
    }
    p.x = b.x + dx * minDistance;
    p.z = b.z + dz * minDistance;
  }
  constrainToArena(p, RULES.arenaRadius);
}

function slam(state) {
  const p = state.player;
  const b = state.boss;
  // Damage is resolved once when the 0.30 s Slam clip reaches contact.
  emit(state, "slam", b.targetX, b.targetZ, {
    radius: b.slamRadius,
    phase: b.attackPhase,
  });
  if (
    Math.hypot(p.x - b.targetX, p.z - b.targetZ) >
      b.slamRadius + RULES.playerRadius ||
    p.invulnerableTimer > 0
  )
    return;
  const damage = Math.round((b.attackPhase === 2 ? 32 : 24) * (b.harm ?? 1));
  p.hp = Math.max(0, p.hp - damage);
  p.invulnerableTimer = 0.75;
  emit(state, "hurt", p.x, p.z, { damage });
  if (p.hp === 0) {
    state.status = "lost";
    cancelAttack(state, "defeat");
    emit(state, "lose", p.x, p.z);
  }
}

function stepBoss(state, dt) {
  const b = state.boss;
  const p = state.player;
  updatePhase(state);
  b.yaw = Math.atan2(p.x - b.x, p.z - b.z);
  b.timer = Math.max(0, b.timer - dt);
  if (b.timer < EPSILON) b.timer = 0;
  if (b.state === "idle" && b.timer <= 0) b.state = "chase";
  if (b.state === "chase") {
    const d = distance(p, b);
    if (d <= 4.7) {
      b.state = "windup";
      b.attackPhase = b.phase;
      b.windupDuration =
        b.attackPhase === 2
          ? RULES.phaseTwoWindupDuration
          : RULES.windupDuration;
      b.recoveryDuration =
        b.attackPhase === 2
          ? RULES.phaseTwoRecoveryDuration
          : RULES.recoveryDuration;
      b.timer = b.windupDuration;
      b.targetX = p.x;
      b.targetZ = p.z;
      b.attackId += 1;
    } else {
      const move = Math.min((b.phase === 2 ? 3.8 : 2.9) * dt, d - 2.2);
      b.x += Math.sin(b.yaw) * move;
      b.z += Math.cos(b.yaw) * move;
      constrainToArena(b, 14);
    }
  } else if (b.state === "windup" && b.timer <= 0) {
    b.state = "slam";
    b.timer = RULES.slamDuration;
  } else if (b.state === "slam" && b.timer <= 0) {
    slam(state);
    // A lethal strike keeps the final contact pose. Terminal states are not
    // stepped again, so this impact cannot repeat after defeat.
    if (state.status === "playing" && b.doubleStrike && b.attackId % 2 === 1) {
      b.state = "windup";
      b.windupDuration = b.timer = 0.72;
      b.targetX = p.x;
      b.targetZ = p.z;
      b.attackId++;
    } else if (state.status === "playing") {
      b.state = "recover";
      b.timer = b.recoveryDuration;
    }
  } else if (b.state === "recover" && b.timer <= 0) {
    b.state = "chase";
  }
}

export function step(state, input = {}, dt = 0) {
  if (!active(state)) return state;
  dt = clamp(finite(dt), 0, RULES.maxStep);
  if (dt === 0) return state;
  let x = clamp(finite(input?.x), -1, 1);
  let z = clamp(finite(input?.z), -1, 1);
  const length = Math.hypot(x, z);
  if (length > 1) {
    x /= length;
    z /= length;
  }
  if (length > 0 || input?.start) start(state);
  if (state.status !== "playing") return state;

  const p = state.player;
  state.time += dt;
  if (p.attackTimer > 0) {
    p.attackElapsed = Math.min(RULES.attackCooldown, p.attackElapsed + dt);
  }
  p.attackTimer = Math.max(0, p.attackTimer - dt);
  if (p.attackTimer < EPSILON) p.attackTimer = 0;
  p.oathCooldown = Math.max(0, p.oathCooldown - dt);

  if (p.aspectTimer > 0) {
    p.aspectTimer = Math.max(0, p.aspectTimer - dt);
    p.aspect = (100 * p.aspectTimer) / RULES.aspectDuration;
  }
  if (p.dodgeTimer > 0) {
    const dodgeDt = Math.min(dt, p.dodgeTimer);
    p.x += p.dodgeX * 12 * dodgeDt;
    p.z += p.dodgeZ * 12 * dodgeDt;
    p.dodgeTimer = Math.max(0, p.dodgeTimer - dt);
  } else {
    const speed = p.aspectTimer > 0 ? 6.5 : 5.5;
    p.x += x * speed * dt;
    p.z += z * speed * dt;
    if (length > 0) p.yaw = (Math.atan2(x, z) + TAU) % TAU;
    p.stamina = Math.min(100, p.stamina + 22 * dt);
  }
  constrainToArena(p, RULES.arenaRadius);
  separateActors(state);
  stepBoss(state, dt);
  separateActors(state);
  resolveAttack(state);
  // Resolve attacks using the protection available at the start of this frame.
  p.invulnerableTimer = Math.max(0, p.invulnerableTimer - dt);
  return state;
}
