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

function advance(state, seconds, input = {}, dt = 1 / 60) {
  for (let left = seconds; left > 1e-9; left -= dt) {
    step(state, input, Math.min(left, dt));
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
  const b = state.boss;
  b.state = "windup";
  b.timer = remaining;
  b.attackPhase = b.phase;
  b.recoveryDuration =
    b.phase === 2 ? RULES.phaseTwoRecoveryDuration : RULES.recoveryDuration;
  b.targetX = state.player.x;
  b.targetZ = state.player.z;
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

test("the thrust hits once at 0.20 seconds and locks attacks until 0.55 seconds", () => {
  const state = inMelee();
  assert.equal(attack(state), true);
  assert.equal(state.boss.hp, 720, "accepting input must not deal damage");
  assert.equal(state.player.attackResolved, false);
  assert.deepEqual(
    drainEvents(state).map((event) => event.type),
    ["swing"],
  );
  advance(state, 0.19);
  assert.equal(state.boss.hp, 720, "the spear is still winding up");
  assert.equal(attack(state), false);
  advance(state, 0.01);
  assert.equal(state.boss.hp, 698);
  assert.equal(state.player.attackResolved, true);
  assert.equal(state.player.pendingAttack, null);
  assert.equal(state.player.attackCancelled, false);
  advance(state, 0.34);
  assert.equal(attack(state), false, "recovery still locks another thrust");
  assert.equal(state.boss.hp, 698, "one swing must not hit repeatedly");
  advance(state, 0.01);
  assert.equal(attack(state), true);
  assert.equal(state.player.attackId, 2);
  assert.deepEqual(
    drainEvents(state).map((event) => event.type),
    ["hit", "swing"],
  );
});

test("the visible spear reaches only 2 metres beyond the boss surface", () => {
  const state = inMelee();
  state.player.z = RULES.bossRadius + RULES.attackRange + 0.05;
  attack(state);
  advance(state, RULES.attackWindup);
  assert.equal(state.boss.hp, 720);
  const miss = drainEvents(state).find((event) => event.type === "miss");
  assert.equal(miss.attackId, 1);
  advance(state, RULES.attackCooldown);
  state.player.z = RULES.bossRadius + RULES.attackRange;
  attack(state);
  advance(state, RULES.attackWindup);
  assert.equal(state.boss.hp, 698, "the surface-reach boundary is inclusive");
});

test("moving out of reach during windup avoids a previously valid hit", () => {
  const state = inMelee();
  attack(state);
  advance(state, 0.2, { z: 1 });
  assert.ok(state.player.z > RULES.bossRadius + RULES.attackRange);
  assert.equal(state.boss.hp, 720);
  advance(state, 0.4, { z: -1 });
  assert.equal(
    state.boss.hp,
    720,
    "returning after a miss cannot resolve again",
  );
  assert.equal(
    drainEvents(state).filter((event) => event.type === "miss").length,
    1,
  );
});

test("moving into reach during windup can connect the thrust", () => {
  const state = inMelee();
  state.player.z = 4.5;
  attack(state);
  advance(state, 0.2, { z: -1 });
  assert.ok(state.player.z < RULES.bossRadius + RULES.attackRange);
  assert.equal(state.boss.hp, 698);
});

test("the forward cone uses impact facing rather than input-time facing", () => {
  const state = inMelee();
  attack(state);
  advance(state, 0.1);
  state.player.yaw = 0;
  advance(state, 0.1);
  assert.equal(state.boss.hp, 720, "turning away must miss");
  advance(state, 0.35);
  attack(state);
  state.player.yaw = Math.PI;
  advance(state, 0.2);
  assert.equal(
    state.boss.hp,
    698,
    "turning toward the boss before impact hits",
  );
});

test("dodging cancels a pending thrust without allowing cooldown bypass", () => {
  const state = inMelee();
  attack(state);
  advance(state, 0.1);
  assert.equal(dodge(state, 1, 0), true);
  assert.equal(state.player.pendingAttack, null);
  assert.equal(state.player.attackResolved, true);
  assert.equal(state.player.attackCancelled, true);
  advance(state, 0.4);
  assert.equal(state.boss.hp, 720);
  assert.equal(attack(state), false);
  const events = drainEvents(state);
  assert.deepEqual(
    events.map((event) => event.type),
    ["swing", "miss", "dodge"],
  );
  assert.equal(events[1].reason, "dodge");
  advance(state, 0.05);
  assert.equal(attack(state), true);
  assert.equal(state.player.attackCancelled, false);
});

test("dodging after impact cancels the recovery animation without undoing damage", () => {
  const state = inMelee();
  attack(state);
  advance(state, 0.2);
  dodge(state, 1, 0);
  advance(state, 0.4);
  assert.equal(state.player.attackCancelled, true);
  assert.equal(state.boss.hp, 698);
  assert.equal(
    drainEvents(state).filter((event) => event.type === "miss").length,
    0,
  );
});

test("a slam hits once at clip contact after 0.30 seconds, then recovers", () => {
  const state = inMelee();
  imminentSlam(state);
  step(state, {}, 0.05);
  assert.equal(state.player.hp, 100, "entering Slam has not reached contact");
  assert.equal(state.boss.state, "slam");
  assert.equal(state.boss.timer, RULES.slamDuration);
  advance(state, RULES.slamDuration - 0.01);
  assert.equal(
    state.player.hp,
    100,
    "damage must wait for the final clip frame",
  );
  assert.deepEqual(drainEvents(state), []);
  advance(state, 0.01);
  assert.equal(state.player.hp, 76);
  assert.equal(state.boss.state, "recover");
  const impactEvents = drainEvents(state);
  assert.deepEqual(
    impactEvents.map((event) => event.type),
    ["slam", "hurt"],
  );
  assert.ok(Math.abs(impactEvents[0].time - 0.35) < 1e-9);
  advance(state, 0.8);
  assert.equal(state.player.hp, 76);
  assert.equal(
    drainEvents(state).filter((event) => event.type === "hurt").length,
    0,
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
  advance(state, RULES.slamDuration);
  assert.equal(state.player.hp, 76, "protection must expire");
  state.player.stamina = 29;
  assert.equal(dodge(state), false);
});

test("dodging during the downswing protects contact after windup has ended", () => {
  const state = inMelee();
  imminentSlam(state);
  step(state, {}, 0.05);
  advance(state, 0.2);
  assert.equal(state.boss.state, "slam");
  assert.equal(state.player.hp, 100);
  dodge(state, 1, 0);
  advance(state, 0.1);
  assert.ok(
    Math.hypot(
      state.player.x - state.boss.targetX,
      state.player.z - state.boss.targetZ,
    ) <
      RULES.slamRadius + RULES.playerRadius,
    "the player is still inside the hazard, so invulnerability must prevent damage",
  );
  assert.equal(state.player.hp, 100);
  assert.equal(state.boss.state, "recover");
  const events = drainEvents(state);
  assert.equal(events.filter((event) => event.type === "slam").length, 1);
  assert.equal(events.filter((event) => event.type === "hurt").length, 0);
});

test("windup locks its telegraph position and moving clear avoids damage", () => {
  const state = inMelee();
  state.boss.state = "chase";
  step(state, {}, 0.05);
  assert.equal(state.boss.state, "windup");
  const target = [state.boss.targetX, state.boss.targetZ];
  advance(state, RULES.windupDuration + RULES.slamDuration + 0.05, { x: 1 });
  assert.deepEqual([state.boss.targetX, state.boss.targetZ], target);
  assert.equal(state.player.hp, 100);
  assert.ok(drainEvents(state).some((event) => event.type === "slam"));
});

test("aspect has a finite duration, boosts hits, and needs hit-earned charge again", () => {
  const state = inMelee();
  assert.equal(activateAspect(state), true);
  assert.equal(activateAspect(state), false);
  attack(state);
  advance(state, 0.2);
  assert.equal(state.boss.hp, 681);
  advance(state, 6);
  assert.equal(state.player.aspectTimer, 0);
  assert.equal(state.player.aspect, 0);
  assert.equal(activateAspect(state), false);
  attack(state);
  advance(state, 0.2);
  assert.equal(state.player.aspect, 8);
  assert.equal(state.boss.hp, 659);
});

test("activating aspect or switching oath mid-thrust affects only future swings", () => {
  const state = inMelee();
  state.player.hp = 60;
  attack(state);
  switchOath(state);
  activateAspect(state);
  advance(state, 0.2);
  assert.equal(
    state.boss.hp,
    698,
    "accepted ember thrust keeps its base damage",
  );
  assert.equal(
    state.player.hp,
    60,
    "changing to tide cannot retroactively heal",
  );
  const hit = drainEvents(state).find((event) => event.type === "hit");
  assert.equal(hit.oath, "ember");
  assert.equal(hit.aspect, false);
  advance(state, 0.35);
  attack(state);
  advance(state, 0.2);
  assert.equal(state.boss.hp, 670, "the next thrust uses tide and aspect");
  assert.equal(state.player.hp, 64);
});

test("an aspect thrust keeps its snapshot when the form expires before impact", () => {
  const state = inMelee();
  activateAspect(state);
  advance(state, 5.9);
  attack(state);
  advance(state, 0.2);
  assert.equal(state.player.aspectTimer, 0);
  assert.equal(state.boss.hp, 681);
  assert.equal(
    state.player.aspect,
    0,
    "an aspect hit cannot refill expired charge",
  );
});

test("oath switching cannot reset attacks or grant repeat healing", () => {
  const state = inMelee();
  state.player.hp = 60;
  assert.equal(switchOath(state), true);
  assert.equal(state.oath, "tide");
  attack(state);
  assert.equal(state.player.hp, 60, "healing occurs at impact");
  advance(state, 0.2);
  assert.equal(state.player.hp, 64);
  assert.equal(state.boss.hp, 704);
  assert.equal(switchOath(state), false);
  assert.equal(attack(state), false);
  advance(state, 1.31);
  assert.equal(switchOath(state), true);
  assert.equal(state.oath, "ember");
});

test("phase two affects the next windup without changing an existing telegraph", () => {
  const state = inMelee();
  state.boss.hp = 370;
  state.boss.state = "chase";
  step(state, {}, 0.05);
  assert.equal(state.boss.timer, RULES.windupDuration);
  assert.equal(state.boss.attackPhase, 1);
  attack(state);
  advance(state, 0.2);
  assert.equal(state.boss.phase, 2);
  assert.equal(state.boss.attackPhase, 1);
  advance(state, 0.9);
  assert.equal(state.player.hp, 100, "phase-one windup ends before contact");
  assert.equal(state.boss.state, "slam");
  advance(state, RULES.slamDuration);
  assert.equal(
    state.player.hp,
    76,
    "the advertised phase-one slam remains 24 damage",
  );
  const slamEvent = drainEvents(state).find((event) => event.type === "slam");
  assert.equal(slamEvent.phase, 1);
  assert.equal(state.boss.state, "recover");
  assert.ok(Math.abs(state.boss.timer - RULES.recoveryDuration) < 1e-9);
  advance(state, RULES.recoveryDuration + 0.02);
  assert.equal(state.boss.state, "windup");
  assert.equal(state.boss.attackPhase, 2);
  assert.equal(state.boss.windupDuration, RULES.phaseTwoWindupDuration);
  assert.equal(state.boss.recoveryDuration, RULES.phaseTwoRecoveryDuration);
  imminentSlam(state);
  step(state, {}, 0.05);
  advance(state, RULES.slamDuration);
  assert.equal(state.player.hp, 44, "the next phase-two slam deals 32 damage");
});

test("a thrust landing during recovery deals 25 percent extra damage", () => {
  const state = inMelee();
  state.boss.state = "slam";
  state.boss.timer = 0.1;
  attack(state);
  advance(state, 0.2);
  assert.equal(state.boss.state, "recover");
  assert.equal(state.boss.hp, 692);
  const hit = drainEvents(state).find((event) => event.type === "hit");
  assert.equal(hit.counter, true);
  assert.equal(hit.damage, Math.round(22 * 1.25));
});

test("starting a thrust in recovery does not earn a bonus after recovery ends", () => {
  const state = inMelee();
  state.boss.state = "recover";
  state.boss.timer = 0.1;
  attack(state);
  advance(state, 0.2);
  assert.equal(state.boss.hp, 698);
  assert.equal(
    drainEvents(state).find((event) => event.type === "hit").counter,
    false,
  );
});

test("victory is terminal, increments kills once, and preserves action events until drained", () => {
  const state = inMelee();
  state.boss.hp = 10;
  attack(state);
  assert.equal(state.status, "playing");
  advance(state, 0.2);
  assert.equal(state.status, "won");
  assert.equal(state.boss.state, "dead");
  assert.equal(state.boss.hp, 0);
  assert.equal(state.kills, 1);
  const before = structuredClone(state);
  step(state, { x: 1 }, 0.05);
  assert.deepEqual(state, before);
  assert.equal(attack(state), false);
  assert.equal(dodge(state), false);
  assert.equal(activateAspect(state), false);
  assert.equal(state.kills, 1);
  assert.deepEqual(
    drainEvents(state).map((event) => event.type),
    ["swing", "hit", "win"],
  );
  assert.deepEqual(drainEvents(state), []);
});

test("defeating the boss before downswing contact prevents the pending slam", () => {
  const state = inMelee();
  state.player.hp = 10;
  state.boss.hp = 10;
  imminentSlam(state, 0.1);
  attack(state);
  advance(state, 0.5);
  assert.equal(state.status, "won");
  assert.equal(state.player.hp, 10);
  assert.equal(state.boss.state, "dead");
  assert.equal(state.kills, 1);
  assert.deepEqual(
    drainEvents(state).map((event) => event.type),
    ["swing", "hit", "win"],
  );
});

test("a lethal slam cancels a pending hit before it can kill the boss", () => {
  const state = inMelee();
  state.player.hp = 10;
  state.boss.hp = 10;
  imminentSlam(state);
  state.boss.state = "slam";
  state.boss.timer = 0.1;
  attack(state);
  advance(state, 0.5);
  assert.equal(state.status, "lost");
  assert.equal(state.boss.hp, 10);
  assert.equal(state.player.pendingAttack, null);
  assert.equal(state.player.attackCancelled, true);
  assert.equal(state.kills, 0);
  const events = drainEvents(state);
  assert.equal(
    events.some((event) => event.type === "hit"),
    false,
  );
  assert.equal(events.find((event) => event.type === "miss").reason, "defeat");
});

test("defeat is terminal and restart clears all combat and input timers", () => {
  const state = inMelee();
  state.player.hp = 10;
  imminentSlam(state);
  step(state, {}, 0.05);
  advance(state, RULES.slamDuration);
  assert.equal(state.boss.state, "slam");
  assert.equal(
    state.boss.timer,
    0,
    "lethal hit preserves the completed contact pose",
  );
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

test("impact and cooldown timing agree at 60 and 120 simulation steps per second", () => {
  function simulate(dt) {
    const state = inMelee();
    state.player.aspect = 0;
    for (let i = 0; i < 6; i += 1) {
      assert.equal(attack(state), true);
      advance(state, 0.55, {}, dt);
    }
    return state;
  }
  const sixty = simulate(1 / 60);
  const oneTwenty = simulate(1 / 120);
  assert.equal(sixty.boss.hp, oneTwenty.boss.hp);
  assert.equal(sixty.player.aspect, oneTwenty.player.aspect);
  assert.equal(sixty.player.attackTimer, oneTwenty.player.attackTimer);
  const events60 = drainEvents(sixty);
  const events120 = drainEvents(oneTwenty);
  assert.equal(events60.length, 12);
  assert.deepEqual(
    events60.map((event) => event.type),
    events120.map((event) => event.type),
  );
  for (let i = 0; i < events60.length; i += 1) {
    assert.ok(Math.abs(events60[i].time - events120[i].time) < 1e-9);
    if (events60[i].type === "hit")
      assert.ok(Math.abs(events60[i].time - events60[i - 1].time - 0.2) < 1e-9);
  }
});

test("the complete encounter can be won through movement, attacks, and timed dodges", () => {
  const state = createGame();
  start(state);
  activateAspect(state);
  for (let frame = 0; frame < 7200 && state.status === "playing"; frame += 1) {
    const dx = state.boss.x - state.player.x;
    const dz = state.boss.z - state.player.z;
    const d = Math.hypot(dx, dz);
    if (state.boss.state === "slam" && state.boss.timer < 0.18)
      dodge(state, -dz, dx);
    if (d < 3.6) attack(state);
    step(state, d > 2.8 ? { x: dx / d, z: dz / d } : {}, 1 / 60);
  }
  assert.equal(state.status, "won");
  assert.equal(state.kills, 1);
  assert.equal(state.boss.phase, 2);
  assert.ok(state.player.hp > 0);
});

test("the boss naturally chases and defeats a stationary player at 60 and 120 Hz", () => {
  function encounter(dt) {
    const state = createGame();
    start(state);
    for (
      let frame = 0;
      frame < 60 / dt && state.status === "playing";
      frame += 1
    )
      step(state, {}, dt);
    assert.equal(state.status, "lost");
    assert.equal(state.player.hp, 0);
    assert.equal(state.boss.attackId, 5);
    return state;
  }
  const sixty = encounter(1 / 60);
  const oneTwenty = encounter(1 / 120);
  assert.ok(Math.abs(sixty.time - oneTwenty.time) < 0.1);
  assert.deepEqual(
    drainEvents(sixty).map((event) => event.type),
    drainEvents(oneTwenty).map((event) => event.type),
  );
});
