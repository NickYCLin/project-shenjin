import { faiths } from "./pilgrimage.js";

export const factions = Object.keys(faiths);
export const field = {
  width: 960,
  height: 600,
  altar: { x: 480, y: 300 },
  radius: 72,
  goal: 30,
};
export const camps = {
  bloom: { x: 150, y: 415 },
  ward: { x: 480, y: 85 },
  pyre: { x: 810, y: 415 },
};
export const palette = { bloom: "#81d4b2", ward: "#eec773", pyre: "#ef8e77" };
const scores = () => ({ bloom: 0, ward: 0, pyre: 0 });
const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

export function newBattle() {
  return {
    phase: "waiting",
    players: [],
    score: scores(),
    holder: null,
    contested: false,
    winner: null,
    rest: 0,
  };
}
function spawn(p) {
  Object.assign(p, camps[p.faith], {
    hp: 100,
    respawn: 0,
    cooldown: 0,
    target: null,
    guard: 1.5,
    strike: 0,
  });
}
export function joinBattle(battle, id, faith) {
  if (
    !factions.includes(faith) ||
    battle.players.length >= 12 ||
    battle.players.some((p) => p.id === id)
  )
    return false;
  const p = { id, faith };
  spawn(p);
  battle.players.push(p);
  return true;
}
function reset(battle) {
  Object.assign(battle, {
    score: scores(),
    phase: "waiting",
    holder: null,
    contested: false,
    winner: null,
    rest: 0,
  });
  battle.players.forEach(spawn);
}
export function leaveBattle(battle, id) {
  battle.players = battle.players.filter((p) => p.id !== id);
  if (
    battle.phase === "playing" &&
    new Set(battle.players.map((p) => p.faith)).size < 2
  )
    reset(battle);
}
export function command(battle, id, input) {
  const p = battle.players.find((p) => p.id === id);
  if (!p || battle.phase !== "playing" || p.respawn > 0 || !input) return;
  if (
    input.type === "move" &&
    Number.isFinite(input.x) &&
    Number.isFinite(input.y)
  ) {
    p.target = {
      x: Math.max(15, Math.min(field.width - 15, input.x)),
      y: Math.max(15, Math.min(field.height - 15, input.y)),
    };
  }
  if (input.type === "attack" && p.cooldown <= 0) {
    const enemy = battle.players
      .filter(
        (e) =>
          e.faith !== p.faith &&
          e.hp > 0 &&
          e.guard <= 0 &&
          distance(e, p) <= 92,
      )
      .sort((a, b) => distance(p, a) - distance(p, b))[0];
    p.cooldown = 0.8;
    p.strike = 0.28;
    if (enemy) {
      enemy.hp = Math.max(0, enemy.hp - 34);
      if (!enemy.hp) {
        enemy.respawn = 4;
        enemy.target = null;
      }
    }
  }
}
export function tick(battle, dt) {
  if (battle.phase === "result") {
    battle.rest -= dt;
    if (battle.rest <= 0) reset(battle);
    return;
  }
  if (battle.phase === "waiting") {
    if (new Set(battle.players.map((p) => p.faith)).size < 2) return;
    battle.phase = "playing";
  }
  for (const p of battle.players) {
    if (p.respawn > 0) {
      p.respawn = Math.max(0, p.respawn - dt);
      if (!p.respawn) spawn(p);
      continue;
    }
    for (const key of ["guard", "cooldown", "strike"])
      p[key] = Math.max(0, p[key] - dt);
    if (!p.target) continue;
    const d = distance(p, p.target),
      travel = 145 * dt;
    if (d <= travel) {
      p.x = p.target.x;
      p.y = p.target.y;
      p.target = null;
    } else {
      p.x += ((p.target.x - p.x) * travel) / d;
      p.y += ((p.target.y - p.y) * travel) / d;
    }
  }
  const onAltar = new Set(
    battle.players
      .filter((p) => p.hp > 0 && distance(p, field.altar) <= field.radius)
      .map((p) => p.faith),
  );
  battle.contested = onAltar.size > 1;
  battle.holder = onAltar.size === 1 ? [...onAltar][0] : null;
  if (battle.holder) {
    const f = battle.holder;
    battle.score[f] = Math.min(field.goal, battle.score[f] + dt);
    if (battle.score[f] >= field.goal) {
      battle.phase = "result";
      battle.winner = f;
      battle.rest = 8;
    }
  }
}
