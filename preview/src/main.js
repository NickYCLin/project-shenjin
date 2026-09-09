import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import {
  RULES,
  createGame,
  step,
  start,
  restart,
  attack,
  dodge,
  activateAspect,
  switchOath,
  drainEvents,
} from "./combat.js";
import "./style.css";

const $ = (id) => document.getElementById(id);
const state = createGame();
const canvas = $("world");
const keys = new Set();
let paused = false,
  loaded = false,
  soundOn = false,
  audioContext,
  drag = false;
let cameraYaw = 0,
  cameraPitch = 0.42,
  lastStamp = performance.now(),
  messageTimer = 0;
let hero,
  guardian,
  weapon,
  environment,
  visualTime = 0,
  lastStatus = "ready";
const effects = [];

// Rendering is deliberately separate from the engine-free combat rules.
let renderer;
try {
  renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    powerPreference: "high-performance",
  });
} catch (error) {
  $("load-status").textContent =
    "無法建立 3D 畫面，請使用支援 WebGL 2 的桌面瀏覽器並開啟硬體加速。";
  throw error;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.65));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.25;
const scene = new THREE.Scene();
scene.background = new THREE.Color("#8fb5bc");
scene.fog = new THREE.Fog("#8fb5bc", 42, 125);
const camera = new THREE.PerspectiveCamera(
  52,
  innerWidth / innerHeight,
  0.1,
  220,
);
camera.position.set(17, 10, 22);
camera.lookAt(0, 3, -8);
scene.add(new THREE.HemisphereLight("#d9edf0", "#8a7857", 2.3));
const sun = new THREE.DirectionalLight("#ffe1ac", 4.1);
sun.position.set(-24, 38, 10);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, {
  left: -25,
  right: 25,
  top: 25,
  bottom: -25,
  near: 0.5,
  far: 120,
});
sun.shadow.normalBias = 0.035;
sun.shadow.bias = -0.00012;
scene.add(sun);
const rim = new THREE.DirectionalLight("#92d4d4", 1.25);
rim.position.set(10, 14, -35);
scene.add(rim);
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(
  new UnrealBloomPass(
    new THREE.Vector2(innerWidth, innerHeight),
    0.26,
    0.5,
    1.1,
  ),
);
composer.addPass(new OutputPass());

function goldMaterial() {
  return new THREE.MeshStandardMaterial({
    color: "#e4bf6c",
    emissive: "#edb84c",
    emissiveIntensity: 2.4,
    roughness: 0.32,
    metalness: 0.55,
    transparent: true,
    opacity: 0.68,
  });
}
const aspectGroup = new THREE.Group();
const aspectMaterial = goldMaterial();
// Four spectral arms are visual prototype geometry, not a finished character rig.
for (const side of [-1, 1])
  for (const high of [0, 1]) {
    const points = [
      new THREE.Vector3(side * 0.22, 1.35, -0.16),
      new THREE.Vector3(side * 0.8, 1.6 + high * 0.4, -0.35),
      new THREE.Vector3(side * 1.25, 1.35 + high * 0.8, -0.18),
      new THREE.Vector3(side * 1.5, 1.8 + high * 0.8, 0),
    ];
    const arm = new THREE.Mesh(
      new THREE.TubeGeometry(
        new THREE.CatmullRomCurve3(points),
        16,
        0.045,
        6,
        false,
      ),
      aspectMaterial,
    );
    aspectGroup.add(arm);
    const palm = new THREE.Mesh(
      new THREE.OctahedronGeometry(0.14),
      aspectMaterial,
    );
    palm.position.copy(points[3]);
    palm.scale.set(0.6, 1.4, 0.7);
    aspectGroup.add(palm);
    for (let f = 0; f < 3; f++) {
      const finger = new THREE.Mesh(
        new THREE.CylinderGeometry(0.018, 0.024, 0.23, 5),
        aspectMaterial,
      );
      finger.position
        .copy(points[3])
        .add(new THREE.Vector3((f - 1) * 0.075, 0.19, 0));
      finger.rotation.z = (f - 1) * -0.2;
      aspectGroup.add(finger);
    }
  }
aspectGroup.visible = false;
const halo = new THREE.Mesh(
  new THREE.TorusGeometry(0.95, 0.017, 6, 64),
  aspectMaterial,
);
halo.position.set(0, 1.62, -0.34);
aspectGroup.add(halo);
scene.add(aspectGroup);
const playerGlow = new THREE.PointLight("#ffd077", 0, 6);
scene.add(playerGlow);
const targetRing = new THREE.Mesh(
  new THREE.RingGeometry(
    RULES.slamRadius + RULES.playerRadius - 0.12,
    RULES.slamRadius + RULES.playerRadius,
    80,
  ),
  new THREE.MeshBasicMaterial({
    color: "#ff573d",
    transparent: true,
    opacity: 0.85,
    side: THREE.DoubleSide,
    depthWrite: false,
  }),
);
targetRing.rotation.x = -Math.PI / 2;
targetRing.position.y = 0.045;
targetRing.visible = false;
scene.add(targetRing);
const targetFill = new THREE.Mesh(
  new THREE.CircleGeometry(RULES.slamRadius + RULES.playerRadius, 80),
  new THREE.MeshBasicMaterial({
    color: "#ea503c",
    transparent: true,
    opacity: 0.1,
    side: THREE.DoubleSide,
    depthWrite: false,
  }),
);
targetFill.rotation.x = -Math.PI / 2;
targetFill.position.y = 0.035;
targetFill.visible = false;
scene.add(targetFill);
const boundary = new THREE.Mesh(
  new THREE.RingGeometry(16.42, 16.5, 128),
  new THREE.MeshBasicMaterial({
    color: "#dfc486",
    transparent: true,
    opacity: 0.5,
    side: THREE.DoubleSide,
  }),
);
boundary.rotation.x = -Math.PI / 2;
boundary.position.y = 0.06;
scene.add(boundary);
// Seeded floating ash; no downloaded texture or runtime network service.
let seed = 27;
function random() {
  seed = (1664525 * seed + 1013904223) >>> 0;
  return seed / 4294967296;
}
const dustGeometry = new THREE.BufferGeometry();
const dustPositions = new Float32Array(240 * 3);
for (let i = 0; i < 240; i++) {
  dustPositions[i * 3] = (random() - 0.5) * 60;
  dustPositions[i * 3 + 1] = random() * 17;
  dustPositions[i * 3 + 2] = (random() - 0.5) * 60;
}
dustGeometry.setAttribute(
  "position",
  new THREE.BufferAttribute(dustPositions, 3),
);
const dust = new THREE.Points(
  dustGeometry,
  new THREE.PointsMaterial({
    color: "#ffe1a0",
    size: 0.055,
    transparent: true,
    opacity: 0.5,
    depthWrite: false,
  }),
);
scene.add(dust);

function prepareModel(model) {
  model.traverse((obj) => {
    if (obj.isMesh) {
      obj.castShadow = true;
      obj.receiveShadow = true;
    }
  });
  return model;
}
async function load() {
  const loader = new GLTFLoader();
  const names = ["temple", "hero", "sentinel", "spear"];
  let count = 0;
  const models = await Promise.all(
    names.map(async (name) => {
      const gltf = await loader.loadAsync(
        `${import.meta.env.BASE_URL}models/${name}.glb`,
      );
      $("load-status").textContent = `神殿甦醒中 · ${++count} / 4`;
      return prepareModel(gltf.scene);
    }),
  );
  [environment, hero, guardian, weapon] = models;
  scene.add(environment, hero, guardian);
  hero.add(weapon);
  weapon.position.set(0.5, 0.55, 0.18);
  weapon.rotation.x = 0.35;
  hero.position.set(state.player.x, 0, state.player.z);
  hero.rotation.y = state.player.yaw;
  guardian.position.set(state.boss.x, 0, state.boss.z);
  loaded = true;
  $("start").disabled = false;
  $("start").textContent = "踏入失落神殿　→";
  $("load-status").textContent = "場景已就緒 · 建議使用鍵盤與滑鼠";
}
load().catch((error) => {
  console.error("Asset load failed", error);
  $("load-status").textContent = "模型載入失敗，請確認資產已同步後重新整理。";
  $("start").textContent = "無法載入神殿";
});

function tone(frequency, duration = 0.1, kind = "sine", volume = 0.055) {
  if (!soundOn) return;
  try {
    audioContext ??= new (window.AudioContext || window.webkitAudioContext)();
    if (audioContext.state === "suspended") void audioContext.resume();
    const osc = audioContext.createOscillator(),
      gain = audioContext.createGain();
    osc.type = kind;
    osc.frequency.setValueAtTime(frequency, audioContext.currentTime);
    osc.frequency.exponentialRampToValueAtTime(
      Math.max(30, frequency * 0.48),
      audioContext.currentTime + duration,
    );
    gain.gain.setValueAtTime(volume, audioContext.currentTime);
    gain.gain.exponentialRampToValueAtTime(
      0.001,
      audioContext.currentTime + duration,
    );
    osc.connect(gain);
    gain.connect(audioContext.destination);
    osc.start();
    osc.stop(audioContext.currentTime + duration);
  } catch {
    soundOn = false;
    $("sound").textContent = "音效不可用";
    $("sound").setAttribute("aria-pressed", "false");
  }
}
function message(text) {
  $("combat-message").textContent = text;
  messageTimer = 1.5;
  $("combat-message").style.opacity = "1";
}
function begin() {
  if (!loaded) return;
  start(state);
  paused = false;
  document.body.classList.add("playing");
  $("intro").hidden = true;
  $("hud").hidden = false;
  $("pause").hidden = false;
  $("result").hidden = true;
  $("pause-panel").hidden = true;
  $("pause").textContent = "暫停";
  cameraYaw = 0;
  cameraPitch = 0.42;
  keys.clear();
  canvas.focus({ preventScroll: true });
  message("第一誓 · 神殿試煉");
}
function again() {
  restart(state);
  effects.forEach((e) => {
    scene.remove(e.mesh);
    e.mesh.geometry.dispose();
    e.mesh.material.dispose();
  });
  effects.length = 0;
  begin();
}
function setPause(value) {
  if (!["playing"].includes(state.status)) return;
  paused = value;
  keys.clear();
  drag = false;
  $("pause-panel").hidden = !paused;
  $("pause").textContent = paused ? "繼續" : "暫停";
  if (paused) $("resume").focus();
  else canvas.focus({ preventScroll: true });
}
function moveInput() {
  const sx =
    Number(keys.has("KeyD") || keys.has("ArrowRight")) -
    Number(keys.has("KeyA") || keys.has("ArrowLeft"));
  const sz =
    Number(keys.has("KeyS") || keys.has("ArrowDown")) -
    Number(keys.has("KeyW") || keys.has("ArrowUp"));
  return {
    x: sx * Math.cos(cameraYaw) + sz * Math.sin(cameraYaw),
    z: -sx * Math.sin(cameraYaw) + sz * Math.cos(cameraYaw),
  };
}
function action(type) {
  if (paused || state.status !== "playing") return;
  if (type === "attack") {
    const dx = state.boss.x - state.player.x,
      dz = state.boss.z - state.player.z;
    // Soft facing assist makes the initial spear timing study approachable.
    if (Math.hypot(dx, dz) < 7) state.player.yaw = Math.atan2(dx, dz);
    attack(state);
  } else if (type === "dodge") {
    const direction = moveInput();
    dodge(state, direction.x, direction.z);
  } else if (type === "aspect") activateAspect(state);
  else if (switchOath(state))
    message(state.oath === "ember" ? "燼誓 · 破陣" : "潮誓 · 生息");
  canvas.focus({ preventScroll: true });
}
$("start").addEventListener("click", begin);
$("restart").addEventListener("click", again);
$("restart-pause").addEventListener("click", again);
$("pause").addEventListener("click", () => setPause(!paused));
$("resume").addEventListener("click", () => setPause(false));
for (const name of ["attack", "dodge", "aspect", "oath"])
  $(name).addEventListener("click", () => action(name));
$("sound").addEventListener("click", () => {
  soundOn = !soundOn;
  $("sound").textContent = `音效：${soundOn ? "開" : "關"}`;
  $("sound").setAttribute("aria-pressed", String(soundOn));
  if (soundOn) tone(220, 0.25);
  if (state.status === "playing" && !paused)
    canvas.focus({ preventScroll: true });
});
window.addEventListener("keydown", (event) => {
  if (
    ["Space", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(
      event.code,
    ) &&
    state.status === "playing"
  )
    event.preventDefault();
  if (event.code === "Escape") {
    setPause(!paused);
    return;
  }
  if (
    paused ||
    state.status !== "playing" ||
    event.target instanceof HTMLButtonElement
  )
    return;
  keys.add(event.code);
  if (event.repeat) return;
  if (event.code === "KeyJ") action("attack");
  if (event.code === "Space") action("dodge");
  if (event.code === "KeyQ") action("aspect");
  if (event.code === "KeyE") action("oath");
});
window.addEventListener("keyup", (event) => keys.delete(event.code));
window.addEventListener("blur", () => {
  keys.clear();
  drag = false;
  setPause(true);
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) setPause(true);
});
canvas.addEventListener("contextmenu", (event) => event.preventDefault());
canvas.addEventListener("pointerdown", (event) => {
  canvas.focus({ preventScroll: true });
  if (event.button === 0) action("attack");
  if (event.button === 2) {
    drag = true;
    canvas.setPointerCapture(event.pointerId);
  }
});
canvas.addEventListener("pointerup", () => {
  drag = false;
});
canvas.addEventListener("pointercancel", () => {
  drag = false;
});
canvas.addEventListener("pointermove", (event) => {
  if (drag && !paused && state.status === "playing") {
    cameraYaw -= event.movementX * 0.005;
    cameraPitch = THREE.MathUtils.clamp(
      cameraPitch + event.movementY * 0.003,
      0.18,
      0.9,
    );
  }
});
window.addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  composer.setSize(innerWidth, innerHeight);
});

function burst(x, z, color, radius = 1) {
  const mesh = new THREE.Mesh(
    new THREE.RingGeometry(0.7, 0.85, 48),
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 1,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.set(x, 0.12, z);
  scene.add(mesh);
  effects.push({ mesh, age: 0, radius });
}
function processEvents() {
  for (const event of drainEvents(state)) {
    if (event.type === "hit") {
      burst(state.boss.x, state.boss.z, "#ffe1a4", 2);
      tone(150, 0.1, "triangle");
    }
    if (event.type === "hurt") {
      message("誓衛重擊");
      tone(60, 0.22, "sawtooth", 0.035);
    }
    if (event.type === "dodge") {
      burst(state.player.x, state.player.z, "#a1e5d8", 0.8);
      tone(320, 0.08);
    }
    if (event.type === "aspect") {
      message("神相 · 降臨");
      tone(330, 0.8, "sine");
    }
    if (event.type === "slam") {
      burst(
        event.x ?? state.boss.targetX,
        event.z ?? state.boss.targetZ,
        "#f7894d",
        4.3,
      );
      tone(44, 0.4, "triangle", 0.09);
    }
    if (event.type === "oath") {
      message(state.oath === "ember" ? "燼誓 · 破陣" : "潮誓 · 生息");
    }
  }
}
function updateHUD() {
  $("hp-text").textContent = `${Math.ceil(state.player.hp)} / 100`;
  $("hp-bar").style.width = `${state.player.hp}%`;
  $("stamina-bar").style.width = `${state.player.stamina}%`;
  $("aspect-bar").style.width = `${state.player.aspect}%`;
  $("aspect-text").textContent =
    state.player.aspectTimer > 0
      ? "降臨中"
      : `${Math.floor(state.player.aspect)}%`;
  $("boss-bar").style.width = `${(state.boss.hp / state.boss.maxHp) * 100}%`;
  $("boss-phase").textContent =
    state.boss.phase === 2 ? "神殿鎮守 · 第二相" : "神殿鎮守 · 第一相";
  $("boss-action").textContent =
    {
      idle: "靠近守衛，尋找破綻",
      chase: "守衛正在逼近",
      windup: "重擊將至 · 離開紅色圓陣",
      slam: "重擊",
      recover: "破綻出現 · 趁現在反擊",
      dead: "試煉完成",
    }[state.boss.state] ?? "";
  $("oath-name").textContent =
    state.oath === "ember" ? "燼誓 · 破陣" : "潮誓 · 生息";
  $("aspect").classList.toggle("active", state.player.aspectTimer > 0);
  if (lastStatus !== state.status && ["won", "lost"].includes(state.status)) {
    const won = state.status === "won";
    keys.clear();
    $("result-kicker").textContent = won
      ? "OATH FULFILLED"
      : "THE OATH REMAINS";
    $("result-title").textContent = won ? "誓衛已沉眠" : "餘燼，尚未熄滅";
    $("result-copy").textContent = won
      ? `你用了 ${Math.round(state.time)} 秒完成試煉。換一種神誓，再試一次不同的節奏。`
      : "重擊前會出現紅色圓陣。向外閃避，等守衛收招時再進攻。";
    $("result").hidden = false;
    $("pause").hidden = true;
    $("restart").focus();
  }
  lastStatus = state.status;
}
const targetCamera = new THREE.Vector3(),
  lookAt = new THREE.Vector3();
function frame(stamp) {
  requestAnimationFrame(frame);
  const dt = Math.min(Math.max((stamp - lastStamp) / 1000, 0), 0.05);
  lastStamp = stamp;
  if (!paused) {
    visualTime += dt;
    messageTimer -= dt;
  }
  if (loaded) {
    if (!paused && state.status === "playing") step(state, moveInput(), dt);
    processEvents();
    updateHUD();
    const move = moveInput();
    const moving =
      Math.hypot(move.x, move.z) > 0 && !paused && state.status === "playing";
    hero.position.set(
      state.player.x,
      moving ? Math.abs(Math.sin(visualTime * 11)) * 0.04 : 0,
      state.player.z,
    );
    hero.rotation.y = state.player.yaw;
    hero.rotation.z =
      state.player.dodgeTimer > 0 ? 0.3 * Math.sin(visualTime * 25) : 0;
    weapon.rotation.x =
      state.player.attackTimer > 0
        ? 1.3 - Math.sin(state.player.attackTimer * 10) * 0.3
        : 0.35;
    guardian.position.set(
      state.boss.x,
      state.boss.state === "windup" ? Math.sin(visualTime * 5) * 0.03 : 0,
      state.boss.z,
    );
    guardian.rotation.y = Math.atan2(
      state.player.x - state.boss.x,
      state.player.z - state.boss.z,
    );
    guardian.rotation.x =
      state.boss.state === "slam" ? 0.18 : state.status === "won" ? -0.65 : 0;
    aspectGroup.position.copy(hero.position);
    aspectGroup.rotation.y = hero.rotation.y;
    aspectGroup.visible = state.player.aspectTimer > 0;
    halo.rotation.z = visualTime * 0.3;
    playerGlow.position.copy(hero.position).add(new THREE.Vector3(0, 1.7, 0));
    playerGlow.intensity = aspectGroup.visible ? 8 : 0;
    targetRing.visible = targetFill.visible = ["windup", "slam"].includes(
      state.boss.state,
    );
    targetRing.position.set(state.boss.targetX, 0.065, state.boss.targetZ);
    targetFill.position.set(state.boss.targetX, 0.055, state.boss.targetZ);
    targetRing.material.opacity = 0.6 + Math.sin(visualTime * 18) * 0.3;
    targetFill.material.opacity = state.boss.state === "slam" ? 0.45 : 0.13;
    if (state.status === "ready") {
      targetCamera.set(17 + Math.sin(visualTime * 0.075) * 2, 10, 22);
      lookAt.set(0, 3, -8);
    } else {
      const distance = 10.5;
      targetCamera.set(
        state.player.x + Math.sin(cameraYaw) * distance,
        2.4 + Math.sin(cameraPitch) * distance,
        state.player.z + Math.cos(cameraYaw) * distance,
      );
      lookAt.set(state.player.x, 2.5, state.player.z - 1.2);
    }
    camera.position.lerp(targetCamera, 1 - Math.exp(-dt * 3));
    camera.lookAt(lookAt);
  }
  if (!paused) {
    for (let i = effects.length - 1; i >= 0; i--) {
      const effect = effects[i];
      effect.age += dt;
      effect.mesh.scale.setScalar(1 + effect.age * effect.radius * 3);
      effect.mesh.material.opacity = Math.max(0, 1 - effect.age * 2);
      if (effect.age > 0.5) {
        scene.remove(effect.mesh);
        effect.mesh.geometry.dispose();
        effect.mesh.material.dispose();
        effects.splice(i, 1);
      }
    }
    dust.rotation.y = visualTime * 0.006;
  }
  if (messageTimer <= 0) $("combat-message").style.opacity = "0";
  composer.render();
}
requestAnimationFrame(frame);
