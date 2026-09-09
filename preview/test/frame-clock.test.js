import test from "node:test";
import assert from "node:assert/strict";
import { FrameClock } from "../src/frame-clock.js";

test("15, 30, 60 and 144 FPS produce the same number of simulation ticks", () => {
  for (const fps of [15, 30, 60, 144]) {
    const clock = new FrameClock();
    let ticks = 0;
    for (let i = 0; i < fps * 5; i++)
      clock.advance(1 / fps, () => {
        ticks++;
      });
    assert.equal(ticks, 300, `${fps} FPS`);
  }
});

test("a background stall is bounded and reset discards paused fractional time", () => {
  const clock = new FrameClock();
  let ticks = 0;
  clock.advance(60, () => {
    ticks++;
  });
  assert.equal(ticks, 15);
  clock.advance(0.008, () => {
    ticks++;
  });
  clock.reset();
  clock.advance(0.009, () => {
    ticks++;
  });
  assert.equal(ticks, 15);
});

test("a terminal state prevents later catch-up ticks in the same render frame", () => {
  const clock = new FrameClock();
  let ticks = 0;
  clock.advance(0.2, () => {
    ticks++;
    return false;
  });
  assert.equal(ticks, 1);
  assert.equal(clock.remainder, 0);
  assert.equal(
    clock.advance(Number.NaN, () => {
      throw Error("unreachable");
    }),
    0,
  );
});

test("repeated hit stops consume equal wall time at 15 to 144 FPS", () => {
  const results = [];
  for (const fps of [15, 30, 60, 144]) {
    const clock = new FrameClock();
    let ticks = 0;
    for (let frame = 0; frame < fps * 10; frame++)
      clock.advance(1 / fps, () => {
        ticks++;
        if (ticks % 30 === 0) clock.freeze(0.045);
      });
    results.push(ticks);
  }
  assert.deepEqual(results, [551, 551, 551, 551]);
});
