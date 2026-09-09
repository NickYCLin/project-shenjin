import test from "node:test";
import assert from "node:assert/strict";
import {
  RULES,
  createGame,
  start,
  step,
  restart,
  attack,
  dodge,
  activateAspect,
  switchOath,
  drainEvents,
} from "../src/combat.js";

function advance(state, seconds, input = {}) {
  for (let left = seconds; left > 1e-9; left -= RULES.maxStep) {
    step(state, input, Math.min(left, RULES.maxStep));
  }
}

function inMelee() {
  const state = createGame();
  state.player.x = 0;
  state.player.z = 3;
  state.boss.x = 0;
  state.boss.z = 0;
  state.boss.state = "idle";
  state.boss.timer = 100;
  start(state);
  return state;
}

function imminentSlam(state, remaining = 0.01) {
  state.boss.state = "windup";
  state.boss.timer = remaining;
  state.boss.targetX = state.player.x;
  state.boss.targetZ = state.player.z;
}

test("ready state remains still until movement or an explicit start", () => {
  const state = createGame();
  step(state, {}, 0.05);
  assert.equal(state.status, "ready");
  assert.equal(state.time, 0);
  step(state, { z: -1 }, 0.05);
  assert.equal(state.status, "playing");
  assert.ok(state.player.z < 8);
});

test("attacks only hit within reach and forward cone and cannot bypass cooldown", () => {
  const state = inMelee();
  assert.equal(attack(state), true);
  assert.equal(state.boss.hp, 698);
  assert.equal(attack(state), false);
  assert.equal(state.boss.hp, 698);
  advance(state, 0.56);
  state.player.yaw = 0;
  assert.equal(attack(state), true);
  assert.equal(state.boss.hp, 698, "a backwards swing must miss");
  advance(state, 0.56);
  state.player.yaw = Math.PI;
  state.player.z = 8;
  attack(state);
  assert.equal(state.boss.hp, 698, "an out-of-range swing must miss");
  advance(state, 0.56);
  state.player.z = 3;
  attack(state);
  assert.equal(state.boss.hp, 676);
});

test("a slam hits once, then recovers without damaging every frame", () => {
  const state = inMelee();
  imminentSlam(state);
  step(state, {}, 0.05);
  assert.equal(state.player.hp, 76);
  assert.equal(state.boss.state, "slam");
  advance(state, 0.8);
  assert.equal(state.player.hp, 76);
  assert.equal(
    drainEvents(state).filter((event) => event.type === "hurt").length,
    1,
  );
});

test("dodge consumes stamina, grants brief invulnerability, and cannot repeat during dodge", () => {
  const state = inMelee();
  imminentSlam(state);
  assert.equal(dodge(state, 1, 0), true);
  assert.equal(state.player.stamina, 70);
  assert.equal(dodge(state, 1, 0), false);
  step(state, {}, 0.05);
  assert.equal(state.player.hp, 100);
  assert.ok(state.player.x > 0);
  advance(state, 0.4);
  assert.equal(state.player.invulnerableTimer, 0);
  imminentSlam(state);
  step(state, {}, 0.05);
  assert.equal(state.player.hp, 76, "protection must expire");
  state.player.stamina = 29;
  assert.equal(dodge(state), false);
});

test("windup locks its telegraph position and moving clear avoids damage", () => {
  const state = inMelee();
  state.boss.state = "chase";
  step(state, {}, 0.05);
  assert.equal(state.boss.state, "windup");
  const target = [state.boss.targetX, state.boss.targetZ];
  advance(state, 1.15, { x: 1 });
  assert.deepEqual([state.boss.targetX, state.boss.targetZ], target);
  assert.equal(state.player.hp, 100);
  assert.ok(drainEvents(state).some((event) => event.type === "slam"));
});

test("aspect has a finite duration, boosts hits, and needs hit-earned charge again", () => {
  const state = inMelee();
  assert.equal(activateAspect(state), true);
  assert.equal(activateAspect(state), false);
  attack(state);
  assert.equal(state.boss.hp, 681);
  advance(state, 6.1);
  assert.equal(state.player.aspectTimer, 0);
  assert.equal(state.player.aspect, 0);
  assert.equal(activateAspect(state), false);
  attack(state);
  assert.equal(state.player.aspect, 8);
  assert.equal(state.boss.hp, 659);
});

test("oath switching cannot reset attacks or grant repeat healing", () => {
  const state = inMelee();
  state.player.hp = 60;
  assert.equal(switchOath(state), true);
  assert.equal(state.oath, "tide");
  attack(state);
  assert.equal(state.player.hp, 64);
  assert.equal(state.boss.hp, 704);
  assert.equal(switchOath(state), false);
  assert.equal(attack(state), false);
  assert.equal(state.player.hp, 64);
  advance(state, 1.51);
  assert.equal(switchOath(state), true);
  assert.equal(state.oath, "ember");
});

test("boss phase two begins below half health and shortens the next windup", () => {
  const state = inMelee();
  state.boss.hp = 370;
  attack(state);
  assert.equal(state.boss.phase, 2);
  state.boss.state = "chase";
  step(state, {}, 0.05);
  assert.equal(state.boss.state, "windup");
  assert.equal(state.boss.timer, 0.78);
  imminentSlam(state);
  step(state, {}, 0.05);
  assert.equal(state.player.hp, 68);
});

test("victory is terminal, increments kills once, and preserves action events until drained", () => {
  const state = inMelee();
  state.boss.hp = 10;
  attack(state);
  assert.equal(state.status, "won");
  assert.equal(state.boss.state, "dead");
  assert.equal(state.boss.hp, 0);
  assert.equal(state.kills, 1);
  step(state, { x: 1 }, 0.05);
  assert.equal(attack(state), false);
  assert.equal(dodge(state), false);
  assert.equal(activateAspect(state), false);
  assert.equal(state.kills, 1);
  assert.deepEqual(
    drainEvents(state).map((event) => event.type),
    ["hit", "win"],
  );
  assert.deepEqual(drainEvents(state), []);
});

test("defeat is terminal and restart clears all combat and input timers", () => {
  const state = inMelee();
  state.player.hp = 10;
  imminentSlam(state);
  step(state, {}, 0.05);
  assert.equal(state.status, "lost");
  assert.equal(state.player.hp, 0);
  assert.deepEqual(
    drainEvents(state).map((event) => event.type),
    ["slam", "hurt", "lose"],
  );
  const time = state.time;
  advance(state, 1, { x: 1 });
  assert.equal(state.time, time);
  assert.equal(attack(state), false);
  assert.equal(switchOath(state), false);
  const reference = state;
  assert.equal(restart(state), reference);
  assert.deepEqual(state, createGame());
});

test("dt is capped and invalid dt cannot corrupt state; diagonal movement is normalized", () => {
  const state = createGame();
  start(state);
  step(state, { x: 1, z: 1 }, 100);
  assert.equal(state.time, RULES.maxStep);
  assert.ok(
    Math.abs(Math.hypot(state.player.x, state.player.z - 8) - 0.275) < 1e-9,
  );
  const before = structuredClone(state);
  for (const dt of [NaN, Infinity, -1, 0]) step(state, { x: 1 }, dt);
  assert.deepEqual(state, before);
});

test("the arena contains the player and movement cannot cross the boss core", () => {
  const state = inMelee();
  advance(state, 0.5, { z: -1 });
  assert.ok(state.player.z >= RULES.bossRadius + RULES.playerRadius - 1e-9);
  state.player.x = 16.4;
  state.player.z = 0;
  advance(state, 1, { x: 1 });
  assert.ok(
    Math.hypot(state.player.x, state.player.z) <= RULES.arenaRadius + 1e-9,
  );
});

test("input-triggered events survive the next simulation step", () => {
  const state = inMelee();
  dodge(state, 1, 0);
  activateAspect(state);
  step(state, {}, 0.05);
  assert.deepEqual(
    drainEvents(state).map((event) => event.type),
    ["dodge", "aspect"],
  );
});

test("the complete encounter can be won through movement, attacks, and timed dodges", () => {
  const state = createGame();
  start(state);
  activateAspect(state);
  for (let frame = 0; frame < 1800 && state.status === "playing"; frame += 1) {
    const dx = state.boss.x - state.player.x;
    const dz = state.boss.z - state.player.z;
    const d = Math.hypot(dx, dz);
    if (state.boss.state === "windup" && state.boss.timer < 0.18)
      dodge(state, -dz, dx);
    if (d < 5.1) attack(state);
    step(state, d > 3.5 ? { x: dx / d, z: dz / d } : {}, 0.05);
  }
  assert.equal(state.status, "won");
  assert.equal(state.kills, 1);
  assert.equal(state.boss.phase, 2);
  assert.ok(state.player.hp > 0);
});

test("the boss naturally chases and defeats a stationary player", () => {
  const state = createGame();
  start(state);
  for (let frame = 0; frame < 1000 && state.status === "playing"; frame += 1)
    step(state, {}, 0.05);
  assert.equal(state.status, "lost");
  assert.equal(state.player.hp, 0);
  assert.ok(state.boss.attackId >= 5);
});
