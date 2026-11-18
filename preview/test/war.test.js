import test from "node:test";
import assert from "node:assert/strict";
import {
  newBattle,
  joinBattle,
  leaveBattle,
  command,
  tick,
  field,
} from "../src/war-rules.js";
import { attachWar } from "../server/war.js";
import { createServer } from "node:http";
import { once } from "node:events";
import WebSocket from "ws";

test("opponents unlock the altar, contest pauses scoring, victory resets", () => {
  const b = newBattle();
  joinBattle(b, "a", "bloom");
  tick(b, 0.1);
  assert.equal(b.phase, "waiting");
  joinBattle(b, "b", "ward");
  tick(b, 0.1);
  assert.equal(b.phase, "playing");
  command(b, "a", { type: "move", ...field.altar });
  for (let i = 0; i < 40; i++) tick(b, 0.1);
  assert.ok(b.score.bloom > 0);
  command(b, "b", { type: "move", ...field.altar });
  for (let i = 0; i < 25; i++) tick(b, 0.1);
  const score = b.score.bloom;
  tick(b, 0.1);
  assert.equal(b.score.bloom, score);
  assert.ok(b.contested);
  for (let i = 0; i < 3; i++) {
    command(b, "a", { type: "attack" });
    for (let j = 0; j < 9; j++) tick(b, 0.1);
  }
  assert.equal(b.players[1].hp, 0);
  for (let i = 0; i < 400 && b.phase !== "result"; i++) tick(b, 0.1);
  assert.equal(b.winner, "bloom");
  assert.equal(b.players[1].hp, 100);
  for (let i = 0; i < 85; i++) tick(b, 0.1);
  assert.equal(b.score.bloom, 0);
  assert.equal(b.phase, "playing");
  leaveBattle(b, "b");
  assert.equal(b.phase, "waiting");
});
test(
  "independent WebSockets see one shared room and isolated rooms",
  { timeout: 5000 },
  async (t) => {
    const server = createServer();
    attachWar(server);
    server.listen(0, "127.0.0.1");
    await once(server, "listening");
    const peers = [];
    t.after(async () => {
      peers.forEach((ws) => ws.terminate());
      await new Promise((r) => server.close(r));
    });
    async function client(room, faith) {
      const ws = new WebSocket(
        "ws://127.0.0.1:" + server.address().port + "/war-socket",
      );
      peers.push(ws);
      await once(ws, "open");
      const joined = once(ws, "message");
      ws.send(JSON.stringify({ type: "join", room, faith }));
      assert.equal(JSON.parse((await joined)[0]).type, "joined");
      return ws;
    }
    const a = await client("SUN", "bloom"),
      b = await client("SUN", "ward"),
      c = await client("MOON", "pyre");
    const states = await Promise.all(
      [a, b, c].map(
        async (ws) => JSON.parse((await once(ws, "message"))[0]).battle,
      ),
    );
    assert.deepEqual(states[0], states[1]);
    assert.equal(states[0].phase, "playing");
    assert.equal(states[2].phase, "waiting");
    const oldX = states[0].players[0].x;
    a.send(JSON.stringify({ type: "move", ...field.altar }));
    assert.ok(
      JSON.parse((await once(b, "message"))[0]).battle.players[0].x > oldX,
    );
  },
);
