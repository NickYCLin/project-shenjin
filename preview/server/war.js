import { WebSocketServer, WebSocket } from "ws";
import { randomUUID } from "node:crypto";
import {
  newBattle,
  joinBattle,
  leaveBattle,
  command,
  tick,
} from "../src/war-rules.js";

export function attachWar(server) {
  const rooms = new Map();
  const wss = new WebSocketServer({
    noServer: true,
    maxPayload: 512,
    perMessageDeflate: false,
  });
  function upgrade(req, socket, head) {
    const path = req.url?.split("?")[0];
    if (path !== "/war-socket") return;
    try {
      if (
        req.headers.origin &&
        new URL(req.headers.origin).host !== req.headers.host
      ) {
        socket.destroy();
        return;
      }
    } catch {
      socket.destroy();
      return;
    }
    wss.handleUpgrade(req, socket, head, (ws) => wss.emit("connection", ws));
  }
  server.on("upgrade", upgrade);
  wss.on("connection", (ws) => {
    const id = randomUUID();
    let room,
      code,
      quota = 40,
      windowStart = Date.now();
    const joinTimer = setTimeout(() => ws.close(1008, "join timeout"), 10000);
    ws.alive = true;
    ws.on("pong", () => {
      ws.alive = true;
    });
    ws.on("error", () => ws.terminate());
    ws.on("message", (data, binary) => {
      if (Date.now() - windowStart >= 1000) {
        windowStart = Date.now();
        quota = 40;
      }
      if (--quota < 0 || binary) {
        ws.close(1008);
        return;
      }
      let msg;
      try {
        msg = JSON.parse(data);
      } catch {
        ws.close(1007);
        return;
      }
      if (!room) {
        if (
          msg?.type !== "join" ||
          typeof msg.room !== "string" ||
          !/^[A-Z0-9]{1,12}$/.test(msg.room)
        ) {
          ws.close(1008, "invalid room");
          return;
        }
        code = msg.room;
        if (!rooms.has(code) && rooms.size >= 100) {
          ws.close(1013, "rooms full");
          return;
        }
        const candidate = rooms.get(code) ?? {
          battle: newBattle(),
          clients: new Set(),
        };
        if (!joinBattle(candidate.battle, id, msg.faith)) {
          ws.close(1008, "join rejected");
          return;
        }
        room = candidate;
        rooms.set(code, room);
        room.clients.add(ws);
        clearTimeout(joinTimer);
        ws.send(JSON.stringify({ type: "joined", id, room: code }));
      } else command(room.battle, id, msg);
    });
    ws.on("close", () => {
      clearTimeout(joinTimer);
      if (!room) return;
      leaveBattle(room.battle, id);
      room.clients.delete(ws);
      if (!room.clients.size) rooms.delete(code);
    });
  });
  const update = setInterval(() => {
    for (const { battle, clients } of rooms.values()) {
      tick(battle, 0.1);
      const snapshot = JSON.stringify({ type: "state", battle });
      for (const ws of clients)
        if (ws.readyState === WebSocket.OPEN && ws.bufferedAmount < 65536)
          ws.send(snapshot);
    }
  }, 100);
  const heartbeat = setInterval(() => {
    for (const ws of wss.clients) {
      if (!ws.alive) ws.terminate();
      else {
        ws.alive = false;
        ws.ping();
      }
    }
  }, 15000);
  function close() {
    clearInterval(update);
    clearInterval(heartbeat);
    server.off("upgrade", upgrade);
    for (const ws of wss.clients) ws.terminate();
    wss.close();
  }
  server.once("close", close);
}
