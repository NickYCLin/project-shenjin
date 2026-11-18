import { faiths } from "./pilgrimage.js";
import { field, camps, palette, factions } from "./war-rules.js";

const $ = (id) => document.getElementById(id);
const canvas = $("map"),
  ctx = canvas.getContext("2d");
const paving = new Image();
paving.src = new URL("./images/paving.webp", import.meta.url).href;
const requested = new URL(location.href).searchParams.get("room");
if (requested && /^[a-z0-9]{1,12}$/i.test(requested))
  $("room").value = requested.toUpperCase();
let socket,
  me,
  battle,
  activeRoom,
  connected = false;
const send = (data) => {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(data));
};
function ring(x, y, r, color, width = 2) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.stroke();
}
function disk(x, y, r, color) {
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.fill();
}
function label(text, x, y, color, size = 16) {
  ctx.fillStyle = color;
  ctx.font = "bold " + size + "px serif";
  ctx.textAlign = "center";
  ctx.fillText(text, x, y);
}
function draw() {
  ctx.fillStyle = "#303a36";
  ctx.fillRect(0, 0, 960, 600);
  if (paving.complete && paving.naturalWidth) {
    ctx.globalAlpha = 0.28;
    for (let y = 0; y < 600; y += 192)
      for (let x = 0; x < 960; x += 192) ctx.drawImage(paving, x, y, 192, 192);
    ctx.globalAlpha = 1;
  }
  const center = field.altar,
    accent = palette[battle.holder] ?? "#d2b688";
  for (const f of factions) {
    const camp = camps[f];
    ctx.beginPath();
    ctx.moveTo(camp.x, camp.y);
    ctx.lineTo(center.x, center.y);
    ctx.lineWidth = 26;
    ctx.strokeStyle = "#bcab8b29";
    ctx.stroke();
    for (const r of [39, 45]) ring(camp.x, camp.y, r, palette[f]);
    label(faiths[f].name, camp.x, camp.y + 65, palette[f], 20);
  }
  disk(center.x, center.y, field.radius, "#252a26");
  for (const r of [40, 62, field.radius, 82])
    ring(center.x, center.y, r, accent);
  for (let i = 0; i < 12; i++) {
    ctx.save();
    ctx.translate(center.x, center.y);
    ctx.rotate((i * Math.PI) / 6);
    ctx.strokeStyle = accent;
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.quadraticCurveTo(-27, -40, 0, -62);
    ctx.quadraticCurveTo(27, -40, 0, 0);
    ctx.stroke();
    ctx.restore();
  }
  for (const p of battle.players) {
    if (p.hp === 0) continue;
    const self = p.id === me;
    if (self && p.target) ring(p.target.x, p.target.y, 8, "#fff5d7");
    if (self) ring(p.x, p.y + 2, 21, "#fff5d7", 3);
    if (p.guard > 0) ring(p.x, p.y, 25, "#b7d4e2");
    if (p.strike > 0) ring(p.x, p.y, 92, "#f9e3ad88");
    disk(p.x, p.y + 3, 14, "#1d2522");
    disk(p.x, p.y, 12, palette[p.faith]);
    ctx.fillStyle = "#383730";
    ctx.fillRect(p.x - 2, p.y - 4, 4, 9);
    ctx.strokeStyle = "#fff0c4";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(p.x + 9, p.y + 8);
    ctx.lineTo(p.x + 19, p.y - 18);
    ctx.stroke();
    ctx.fillStyle = "#1e2522";
    ctx.fillRect(p.x - 18, p.y - 24, 36, 4);
    ctx.fillStyle = palette[p.faith];
    ctx.fillRect(p.x - 18, p.y - 24, (36 * p.hp) / 100, 4);
    if (self) label("你", p.x, p.y - 31, "#fff7dc");
  }
}
const scoreNodes = factions.map((f) => {
  const el = document.createElement("strong");
  el.style.color = palette[f];
  $("scores").append(el);
  return el;
});
function refresh() {
  const player = battle.players.find((p) => p.id === me);
  $("roster").textContent = battle.players.length + " / 12 人";
  factions.forEach((f, i) => {
    scoreNodes[i].textContent =
      faiths[f].name + "　" + Math.floor(battle.score[f]) + " 分";
  });
  let status = "等待其他信仰加入。把邀請連結交給隊友或對手。";
  if (battle.phase === "result")
    status =
      faiths[battle.winner].name +
      "獲勝！ " +
      Math.ceil(battle.rest) +
      " 秒後重開。";
  if (battle.phase === "playing")
    status =
      player?.respawn > 0
        ? "返回營地中，" + Math.ceil(player.respawn) + " 秒後復歸。"
        : battle.contested
          ? "祭壇爭奪中，雙方暫停得分。"
          : battle.holder
            ? faiths[battle.holder].name + "正掌控祭壇。"
            : "日輪祭壇開放，進入金環奪點。";
  if ($("status").textContent !== status) $("status").textContent = status;
  $("attack").disabled =
    battle.phase !== "playing" ||
    !player ||
    player.hp === 0 ||
    player.cooldown > 0;
  draw();
}
$("lobby").onsubmit = (event) => {
  event.preventDefault();
  if (socket) return;
  const endpoint = new URL("/war-socket", location.href);
  endpoint.protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(endpoint);
  socket = ws;
  connected = false;
  activeRoom = $("room").value.trim().toUpperCase();
  $("join").disabled = true;
  $("status").textContent = "正在連線…";
  ws.onopen = () =>
    send({ type: "join", room: activeRoom, faith: $("faith").value });
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "joined") {
      connected = true;
      me = msg.id;
      $("code").textContent =
        "戰場 " + activeRoom + "　" + faiths[$("faith").value].name;
      $("lobby").hidden = true;
      $("lobby").style.display = "none";
      $("arena").hidden = false;
      canvas.focus({ preventScroll: true });
    } else if (msg.type === "state") {
      battle = msg.battle;
      refresh();
    }
  };
  ws.onclose = (event) => {
    socket = null;
    battle = null;
    $("arena").hidden = true;
    $("lobby").hidden = false;
    $("lobby").style.display = "";
    $("join").disabled = false;
    $("status").textContent =
      event.code === 1000
        ? "已離開戰場。"
        : connected
          ? "連線中斷，可重新加入。"
          : event.reason === "join rejected"
            ? "戰場已滿，請換一組代號。"
            : "無法加入，請確認主神戰伺服器已啟動後重試。";
  };
};
$("leave").onclick = () => socket?.close(1000);
$("invite").onclick = async () => {
  const url = new URL(location.href);
  url.searchParams.set("room", activeRoom);
  try {
    await navigator.clipboard.writeText(url.href);
    $("invite").textContent = "已複製連結";
  } catch {
    window.prompt("複製此戰場的邀請連結", url.href);
  }
};
$("attack").onclick = () => {
  send({ type: "attack" });
  canvas.focus({ preventScroll: true });
};
canvas.onpointerdown = (event) => {
  canvas.focus({ preventScroll: true });
  const rect = canvas.getBoundingClientRect();
  send({
    type: "move",
    x: ((event.clientX - rect.left) / rect.width) * field.width,
    y: ((event.clientY - rect.top) / rect.height) * field.height,
  });
};
canvas.onkeydown = (event) => {
  const player = battle?.players.find((p) => p.id === me);
  if (!player) return;
  const dirs = {
    ArrowUp: [0, -1],
    ArrowDown: [0, 1],
    ArrowLeft: [-1, 0],
    ArrowRight: [1, 0],
  };
  if (event.code === "Space") {
    event.preventDefault();
    if (!event.repeat) send({ type: "attack" });
  }
  const dir = dirs[event.code];
  if (dir) {
    event.preventDefault();
    if (!event.repeat)
      send({
        type: "move",
        x: player.x + dir[0] * 80,
        y: player.y + dir[1] * 80,
      });
  }
};
window.addEventListener("pagehide", () => socket?.close(1000));
