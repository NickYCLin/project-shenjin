import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { Sky } from "three/addons/objects/Sky.js";
import { GTAOPass } from "three/addons/postprocessing/GTAOPass.js";
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
import { FrameClock } from "./frame-clock.js";
import { CameraCollision } from "./camera.js";
import { CharacterAnimation } from "./character-animation.js";
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
  cameraPitch = -0.06,
  lastStamp = performance.now(),
  messageTimer = 0;
let hero,
  guardian,
  weapon,
  environment,
  visualTime = 0,
  lastStatus = "ready";
const effects = [];
const damageLabels = [];
const frameClock = new FrameClock();
const cameraCollision = new CameraCollision();
let heroAnimation, sentinelAnimation;
let shake = 0,
  hurtFlash = 0;
let motionOn = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const collisionObjects = [];

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
renderer.toneMappingExposure = 0.95;
const scene = new THREE.Scene();
scene.fog = new THREE.Fog("#b6c5c7", 45, 175);
const camera = new THREE.PerspectiveCamera(
  52,
  innerWidth / innerHeight,
  0.1,
  1500,
);
camera.position.set(-6, 4, 16);
camera.lookAt(1, 4, -8);
const sky = new Sky();
sky.scale.setScalar(1000);
const skyUniforms = sky.material.uniforms;
skyUniforms.turbidity.value = 5;
skyUniforms.rayleigh.value = 1.5;
skyUniforms.sunPosition.value.set(-0.65, 0.38, 0.42);
skyUniforms.cloudScale.value = 0.002;
skyUniforms.cloudCoverage.value = 0.44;
skyUniforms.cloudDensity.value = 0.3;
scene.add(sky);
const pmrem = new THREE.PMREMGenerator(renderer);
skyUniforms.showSunDisc.value = false;
const skyScene = new THREE.Scene();
skyScene.add(sky.clone());
const skyEnvironment = pmrem.fromScene(skyScene, 0.06);
scene.environment = skyEnvironment.texture;
scene.environmentIntensity = 0.28;
skyUniforms.showSunDisc.value = true;
pmrem.dispose();
scene.add(new THREE.HemisphereLight("#d9e7ed", "#605a48", 0.65));
const sun = new THREE.DirectionalLight("#ffdbab", 3.5);
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
const rim = new THREE.DirectionalLight("#92c4d4", 0.65);
rim.position.set(10, 14, -35);
scene.add(rim);
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const ambientOcclusion = new GTAOPass(scene, camera, innerWidth, innerHeight);
ambientOcclusion.updateGtaoMaterial({
  radius: 0.65,
  distanceExponent: 1.5,
  thickness: 1,
});
ambientOcclusion.blendIntensity = 0.65;
composer.addPass(ambientOcclusion);
composer.addPass(
  new UnrealBloomPass(
    new THREE.Vector2(innerWidth, innerHeight),
    0.18,
    0.5,
    1.1,
  ),
);
composer.addPass(new OutputPass());

function goldMaterial() {
  return new THREE.MeshStandardMaterial({
    color: "#c79542",
    emissive: "#d89224",
    emissiveIntensity: 0.7,
    roughness: 0.32,
    metalness: 0.55,
    transparent: true,
    opacity: 0.3,
    depthWrite: false,
  });
}
const aspectGroup = new THREE.Group();
const aspectMaterial = goldMaterial();
const aspectEtching = new THREE.LineBasicMaterial({
  color: "#ffe2a0",
  transparent: true,
  opacity: 0.55,
  depthWrite: false,
});
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
        0.075,
        12,
        false,
      ),
      aspectMaterial,
    );
    aspectGroup.add(arm);
    arm.add(
      new THREE.LineSegments(
        new THREE.WireframeGeometry(arm.geometry),
        aspectEtching,
      ),
    );
    const palm = new THREE.Mesh(
      new THREE.SphereGeometry(0.14, 12, 8),
      aspectMaterial,
    );
    palm.position.copy(points[3]);
    palm.scale.set(0.85, 1.25, 0.5);
    aspectGroup.add(palm);
    for (let f = 0; f < 5; f++) {
      const thumb = f === 4;
      const fingerX = thumb ? side * 0.13 : (f - 1.5) * 0.06;
      const fingerLength = thumb ? 0.16 : 0.22 - Math.abs(f - 1.5) * 0.025;
      const finger = new THREE.Mesh(
        new THREE.TubeGeometry(
          new THREE.CatmullRomCurve3([
            new THREE.Vector3(fingerX, thumb ? 0 : 0.1, 0),
            new THREE.Vector3(fingerX * 1.5, fingerLength, 0.02),
            new THREE.Vector3(fingerX * 1.4, fingerLength + 0.05, 0.07),
          ]),
          8,
          0.022,
          6,
          false,
        ),
        aspectMaterial,
      );
      finger.position.copy(points[3]);
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
      for (const material of Array.isArray(obj.material)
        ? obj.material
        : [obj.material]) {
        for (const texture of [
          material.map,
          material.normalMap,
          material.roughnessMap,
        ]) {
          if (texture)
            texture.anisotropy = Math.min(
              8,
              renderer.capabilities.getMaxAnisotropy(),
            );
        }
      }
    }
  });
  return model;
}
async function load() {
  const loader = new GLTFLoader();
  const names = ["temple-v2", "hero-rigged", "sentinel-rigged", "spear"];
  let count = 0;
  const models = await Promise.all(
    names.map(async (name) => {
      const gltf = await loader.loadAsync(
        `${import.meta.env.BASE_URL}models/${name}.glb`,
      );
      $("load-status").textContent = `神殿甦醒中 · ${++count} / 4`;
      prepareModel(gltf.scene);
      return gltf;
    }),
  );
  [environment, hero, guardian, weapon] = models.map((model) => model.scene);
  heroAnimation = new CharacterAnimation(hero, models[1].animations, "hero");
  sentinelAnimation = new CharacterAnimation(
    guardian,
    models[2].animations,
    "sentinel",
  );
  const socket = hero.getObjectByName("WeaponSocket");
  if (!socket?.isBone)
    throw new Error("Animated hero is missing its weapon socket");
  socket.add(weapon);
  weapon.position.set(0, -0.65, 0);
  weapon.rotation.set(0, 0, 0);
  scene.add(environment, hero, guardian);
  const colliderResponse = await fetch(
    `${import.meta.env.BASE_URL}models/temple-v2-colliders.json`,
  );
  if (!colliderResponse.ok)
    throw new Error("Temple camera colliders are missing");
  const colliders = await colliderResponse.json();
  const colliderMaterial = new THREE.MeshBasicMaterial({
    side: THREE.DoubleSide,
  });
  for (const box of colliders.boxes) {
    const min = new THREE.Vector3(...box.min),
      max = new THREE.Vector3(...box.max);
    const size = max.clone().sub(min);
    const proxy = new THREE.Mesh(
      new THREE.BoxGeometry(size.x, size.y, size.z),
      colliderMaterial,
    );
    proxy.position.copy(min).add(max).multiplyScalar(0.5);
    proxy.updateMatrixWorld(true);
    // Deliberately outside the rendered scene; simple volumes keep camera probes cheap.
    collisionObjects.push(proxy);
  }
  environment.updateMatrixWorld(true);
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
  frameClock.reset();
  shake = hurtFlash = 0;
  document.body.classList.add("playing");
  $("intro").hidden = true;
  $("hud").hidden = false;
  $("pause").hidden = false;
  $("result").hidden = true;
  $("pause-panel").hidden = true;
  $("pause").textContent = "暫停";
  cameraYaw = 0;
  cameraPitch = -0.06;
  keys.clear();
  canvas.focus({ preventScroll: true });
  message("第一誓 · 神殿試煉");
}
function again() {
  restart(state);
  heroAnimation.reset();
  sentinelAnimation.reset();
  damageLabels.forEach((label) => label.element.remove());
  damageLabels.length = 0;
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
  frameClock.reset();
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
    if (
      state.player.attackTimer <= 0 &&
      state.player.dodgeTimer <= 0 &&
      Math.hypot(dx, dz) < 5
    )
      state.player.yaw = Math.atan2(dx, dz);
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
$("motion").setAttribute("aria-pressed", String(motionOn));
$("motion").textContent = `震動：${motionOn ? "開" : "關"}`;
$("motion").addEventListener("click", () => {
  motionOn = !motionOn;
  $("motion").setAttribute("aria-pressed", String(motionOn));
  $("motion").textContent = `震動：${motionOn ? "開" : "關"}`;
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
      -0.08,
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
function sparks(x, y, z, color) {
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(24 * 3);
  const velocities = [];
  for (let i = 0; i < 24; i++) {
    velocities.push(
      new THREE.Vector3(
        (random() - 0.5) * 5,
        random() * 3,
        (random() - 0.5) * 5,
      ),
    );
  }
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const mesh = new THREE.Points(
    geometry,
    new THREE.PointsMaterial({
      color,
      size: 0.07,
      transparent: true,
      depthWrite: false,
    }),
  );
  mesh.position.set(x, y, z);
  scene.add(mesh);
  effects.push({ mesh, age: 0, velocities });
}
function damageNumber(value, x, y, z, counter = false) {
  const element = document.createElement("span");
  element.className = `damage-number${counter ? " counter" : ""}`;
  element.textContent = counter ? `${value} · 破綻` : String(value);
  element.setAttribute("aria-hidden", "true");
  $("app").append(element);
  damageLabels.push({ element, position: new THREE.Vector3(x, y, z), age: 0 });
}
function processEvents() {
  for (const event of drainEvents(state)) {
    if (event.type === "swing") tone(300, 0.11, "triangle", 0.025);
    if (event.type === "hit") {
      const towards = new THREE.Vector2(
        state.player.x - state.boss.x,
        state.player.z - state.boss.z,
      ).normalize();
      const x = state.boss.x + towards.x * RULES.bossRadius;
      const z = state.boss.z + towards.y * RULES.bossRadius;
      sparks(x, 1.4, z, event.counter ? "#b0ffeb" : "#ffe1a4");
      damageNumber(event.damage, x, 2.2, z, event.counter);
      sentinelAnimation.hit();
      frameClock.freeze(event.counter ? 0.07 : 0.045);
      shake = motionOn ? 0.07 : 0;
      tone(event.counter ? 190 : 130, 0.14, "triangle");
    }
    if (event.type === "hurt") {
      heroAnimation.hit();
      hurtFlash = 0.3;
      shake = motionOn ? 0.16 : 0;
      frameClock.freeze(0.055);
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
      burst(event.x, event.z, "#f7894d", 4.3);
      sparks(event.x, 0.3, event.z, "#ffb067");
      shake = motionOn ? 0.09 : 0;
      tone(44, 0.4, "triangle", 0.09);
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
      recover: "破綻出現 · 反擊傷害 +25%",
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
const smoothedCamera = new THREE.Vector3(),
  projection = new THREE.Vector3();
function animateCharacters(delta, moving) {
  const p = state.player,
    b = state.boss;
  hero.position.set(p.x, 0, p.z);
  hero.rotation.y = p.yaw;
  guardian.position.set(b.x, 0, b.z);
  guardian.rotation.y = b.yaw;
  if (p.hp <= 0) heroAnimation.update("Death", delta);
  else if (state.status === "won") heroAnimation.update("Idle", delta);
  else if (p.dodgeTimer > 0)
    heroAnimation.update("Dodge", delta, {
      progress: 1 - p.dodgeTimer / RULES.dodgeDuration,
    });
  else if (p.attackTimer > 0 && !p.attackCancelled)
    heroAnimation.update("Thrust", delta, {
      progress: p.attackElapsed / RULES.attackCooldown,
      id: p.attackId,
    });
  else if (heroAnimation.flinch > 0) heroAnimation.update("Hit", delta);
  else
    heroAnimation.update(moving ? "Walk" : "Idle", delta, {
      speed: p.aspectTimer > 0 ? 1.18 : 1,
    });

  if (b.state === "dead") sentinelAnimation.update("Death", delta);
  else if (b.state === "windup")
    sentinelAnimation.update("Windup", delta, {
      progress: 1 - b.timer / b.windupDuration,
      id: b.attackId,
    });
  else if (b.state === "slam")
    sentinelAnimation.update("Slam", delta, {
      progress: 1 - b.timer / RULES.slamDuration,
      id: b.attackId,
    });
  else if (b.state === "recover")
    sentinelAnimation.update("Recover", delta, {
      progress: 1 - b.timer / b.recoveryDuration,
      id: b.attackId,
    });
  else if (sentinelAnimation.flinch > 0) sentinelAnimation.update("Hit", delta);
  else
    sentinelAnimation.update(b.state === "chase" ? "Walk" : "Idle", delta, {
      speed: b.phase === 2 ? 1.3 : 1,
    });
}
function frame(stamp) {
  requestAnimationFrame(frame);
  const realDelta = Math.min(Math.max((stamp - lastStamp) / 1000, 0), 0.25);
  lastStamp = stamp;
  let animationDelta = paused ? 0 : realDelta;
  if (!paused) {
    visualTime += realDelta;
    messageTimer -= realDelta;
    hurtFlash = Math.max(0, hurtFlash - realDelta);
    shake = Math.max(0, shake - realDelta * 0.8);
  }
  if (loaded) {
    processEvents();
    if (!paused && state.status === "playing") {
      animationDelta = frameClock.advance(realDelta, (dt) => {
        step(state, moveInput(), dt);
        processEvents();
        return state.status === "playing";
      });
    } else frameClock.reset();
    updateHUD();
    const move = moveInput();
    const moving = Math.hypot(move.x, move.z) > 0 && state.status === "playing";
    animateCharacters(animationDelta, moving);
    aspectGroup.position.copy(hero.position);
    aspectGroup.rotation.y = hero.rotation.y;
    aspectGroup.visible = state.player.aspectTimer > 0 && state.player.hp > 0;
    halo.rotation.z = visualTime * 0.3;
    playerGlow.position.copy(hero.position).add(new THREE.Vector3(0, 1.7, 0));
    playerGlow.intensity = aspectGroup.visible ? 3.5 : 0;
    targetRing.visible = targetFill.visible =
      ["windup", "slam"].includes(state.boss.state) &&
      state.status === "playing";
    targetRing.position.set(state.boss.targetX, 0.065, state.boss.targetZ);
    targetFill.position.set(state.boss.targetX, 0.055, state.boss.targetZ);
    targetRing.material.opacity = 0.7 + Math.sin(visualTime * 18) * 0.2;
    targetFill.material.opacity = state.boss.state === "slam" ? 0.45 : 0.13;
    if (state.status === "ready") {
      targetCamera.set(-6 + Math.sin(visualTime * 0.075), 4, 16);
      lookAt.set(1, 4, -8);
      camera.position.lerp(targetCamera, 1 - Math.exp(-realDelta * 3));
    } else {
      const distance = 5;
      lookAt.set(
        state.player.x + Math.cos(cameraYaw) * 0.65,
        2,
        state.player.z - Math.sin(cameraYaw) * 0.65,
      );
      targetCamera.set(
        lookAt.x + Math.sin(cameraYaw) * distance,
        1.7 + Math.sin(cameraPitch) * distance,
        lookAt.z + Math.cos(cameraYaw) * distance,
      );
      smoothedCamera
        .copy(camera.position)
        .lerp(targetCamera, 1 - Math.exp(-realDelta * 5));
      cameraCollision.resolve(
        lookAt,
        smoothedCamera,
        collisionObjects,
        camera.position,
      );
    }
    camera.lookAt(lookAt);
    if (!paused && motionOn && shake > 0) {
      camera.rotation.z += Math.sin(visualTime * 95) * shake * 0.07;
      camera.rotation.x += Math.cos(visualTime * 85) * shake * 0.035;
    }
  }
  if (!paused) {
    for (let i = effects.length - 1; i >= 0; i--) {
      const effect = effects[i];
      effect.age += realDelta;
      if (effect.velocities) {
        const positions = effect.mesh.geometry.attributes.position;
        effect.velocities.forEach((velocity, index) => {
          positions.setXYZ(
            index,
            velocity.x * effect.age,
            velocity.y * effect.age - effect.age * effect.age * 2,
            velocity.z * effect.age,
          );
        });
        positions.needsUpdate = true;
      } else effect.mesh.scale.setScalar(1 + effect.age * effect.radius * 3);
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
  camera.updateMatrixWorld();
  for (let i = damageLabels.length - 1; i >= 0; i--) {
    const label = damageLabels[i];
    if (!paused) label.age += realDelta;
    projection.copy(label.position);
    projection.y += label.age;
    projection.project(camera);
    label.element.style.transform = `translate(-50%, -50%) translate(${(projection.x * 0.5 + 0.5) * innerWidth}px,${(-projection.y * 0.5 + 0.5) * innerHeight}px)`;
    label.element.style.opacity =
      projection.z > 1 ? "0" : String(Math.max(0, 1 - label.age / 0.8));
    if (label.age > 0.8) {
      label.element.remove();
      damageLabels.splice(i, 1);
    }
  }
  $("hurt-flash").style.opacity = String(hurtFlash * 1.3);
  if (messageTimer <= 0) $("combat-message").style.opacity = "0";
  composer.render();
}
requestAnimationFrame(frame);
