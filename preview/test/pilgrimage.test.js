import { test } from "node:test";
import assert from "node:assert/strict";
import {
  createGame,
  start,
  activateAspect,
  dodge,
  attack,
  step,
} from "../src/combat.js";
import {
  prepareEncounter,
  readJourney,
  invokeGift,
  route,
} from "../src/pilgrimage.js";
test("saved route bounds and faith are validated before loading an encounter", () => {
  const fresh = readJourney(null);
  for (const raw of [
    "{",
    JSON.stringify({ ...fresh, cleared: 4 }),
    JSON.stringify({ ...fresh, faith: "toString" }),
  ])
    assert.deepEqual(readJourney(raw), fresh);
  const journey = { ...fresh, cleared: 2, faith: "ward" };
  assert.deepEqual(readJourney(JSON.stringify(journey)), journey);
  const state = createGame();
  prepareEncounter(state, journey, 2);
  assert.equal(state.boss.hp, route[2].hp);
  assert.equal(state.player.hp, 130);
  assert.equal(invokeGift(state), false);
  start(state);
  assert.equal(invokeGift(state), true);
  assert.equal(state.player.invulnerableTimer, 2.5);
  assert.equal(invokeGift(state), false);
});
test("healing and recharging affect the corresponding resource", () => {
  for (const faith of ["bloom", "pyre"]) {
    const state = createGame();
    prepareEncounter(state, { faith, cleared: 0 }, 0);
    start(state);
    state.player.hp = 50;
    state.player.aspect = 0;
    assert.ok(invokeGift(state));
    assert.equal(state.player.hp, faith === "bloom" ? 82 : 50);
    assert.equal(state.player.aspect, faith === "pyre" ? 100 : 0);
  }
});

test("a pilgrim can finish each unlocked encounter in order", () => {
  const journey = readJourney(null);
  for (const [i, stage] of route.entries()) {
    const state = createGame();
    prepareEncounter(state, journey, i);
    start(state);
    activateAspect(state);
    for (let frame = 0; frame < 7200 && state.status === "playing"; frame++) {
      const dx = state.boss.x - state.player.x,
        dz = state.boss.z - state.player.z;
      const distance = Math.hypot(dx, dz);
      if (state.boss.state === "slam" && state.boss.timer < 0.18)
        dodge(state, -dz, dx);
      if (distance < 3.6) attack(state);
      if (state.player.hp < 70) invokeGift(state);
      step(
        state,
        distance > 2.8 ? { x: dx / distance, z: dz / distance } : {},
        1 / 60,
      );
    }
    assert.equal(state.status, "won", stage.place);
    journey.cleared++;
  }
  assert.deepEqual(readJourney(JSON.stringify(journey)), journey);
});
