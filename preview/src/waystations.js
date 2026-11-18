import * as THREE from "three";

// Landmarks sit outside the walkable court so its perimeter stays readable.
const paving = new THREE.TextureLoader().load(
  new URL("./images/paving.webp", import.meta.url).href,
);
paving.colorSpace = THREE.SRGBColorSpace;
paving.wrapS = paving.wrapT = THREE.RepeatWrapping;
paving.repeat.set(12, 12);
export function buildWaystation(index) {
  const group = new THREE.Group();
  const materials = new Map();
  function place(geometry, color, x, y, z) {
    if (!materials.has(color))
      materials.set(
        color,
        new THREE.MeshStandardMaterial({
          color,
          roughness: 0.83,
          flatShading: true,
        }),
      );
    const mesh = new THREE.Mesh(geometry, materials.get(color));
    mesh.position.set(x, y, z);
    mesh.castShadow = mesh.receiveShadow = true;
    group.add(mesh);
    return mesh;
  }
  const sandstone = index ? "#bd845d" : "#c99b70",
    dark = "#724b3e",
    brass = "#ce9a45";
  const drum = (x, y, z, top, bottom, height, color, sides = 8) =>
    place(
      new THREE.CylinderGeometry(top, bottom, height, sides),
      color,
      x,
      y,
      z,
    );
  const box = (x, y, z, w, h, d, color) =>
    place(new THREE.BoxGeometry(w, h, d), color, x, y, z);
  const court = drum(0, -0.37, 0, 19, 20, 0.7, sandstone, 64);
  court.material = court.material.clone();
  court.material.map = paving;
  drum(0, -0.85, 0, 19.8, 21, 0.35, dark, 64);
  box(0, -1.4, 0, 400, 0.5, 400, index ? "#a27455" : "#528681");
  for (let i = 0; i < 24; i++) {
    const a = (i * Math.PI) / 12;
    const x = Math.cos(a) * 17.8,
      z = Math.sin(a) * 17.8;
    const slab = box(x, 0.015, z, 0.19, 0.05, 1.5, brass);
    slab.rotation.y = -a;
  }
  for (let i = 0; i < 12; i++) {
    const a = (i * Math.PI) / 6,
      x = Math.sin(a) * 22,
      z = Math.cos(a) * 22;
    if (!index && i % 3 === 0) continue;
    const height = index ? 6 + (i % 3) * 2 : 3;
    drum(x, height / 2 - 0.4, z, 2, 2.45, height, sandstone);
    if (index) {
      for (let j = 0; j < 5; j++)
        drum(
          x,
          height - 0.2 + j * 0.62,
          z,
          2.45 - j * 0.36,
          2.7 - j * 0.39,
          0.65,
          j % 2 ? dark : sandstone,
        );
      drum(x, height + 3.3, z, 0.03, 0.48, 1.4, brass);
    } else {
      const roof = drum(
        x,
        3.3,
        z,
        0.48,
        3.65,
        1.75,
        i % 2 ? "#a54a36" : "#396e70",
        4,
      );
      roof.rotation.y = a;
      const door = box(x * 0.904, 1, z * 0.904, 1.2, 2.4, 0.3, dark);
      door.rotation.y = a;
    }
  }
  // The road continues through a stepped ceremonial gate. Its open span
  // frames the guardian when the player first enters the court.
  const stone = index ? "#915b45" : "#d8b086";
  for (const x of [-4, 4]) {
    box(x, 2.3, -19, 2.5, 4.8, 2.8, stone);
    for (const y of [0.35, 1, 3.8, 4.65]) box(x, y, -19, 2.85, 0.26, 3, dark);
    for (const dx of [-0.88, 0.88])
      drum(x + dx, 2.4, -17.65, 0.23, 0.35, 3.9, brass);
  }
  for (let level = 0; level < 5; level++) {
    const y = 5 + level * 0.87,
      w = 11 - level * 1.55;
    box(0, y, -19, w, 1, 3.25 - level * 0.35, stone);
    box(0, y + 0.49, -19, w + 0.65, 0.22, 3.7 - level * 0.35, dark);
    for (let n = 0; n < 5 - level; n++) {
      const x = (n - (4 - level) / 2) * 1.76;
      box(x, y, -17.33 - level * 0.17, 0.58, 0.69, 0.12, dark);
      drum(x, y + 0.33, -17.25 - level * 0.17, 0.06, 0.55, 0.55, brass, 4);
    }
  }
  for (const x of [-1.7, 0, 1.7]) drum(x, 9.68, -19, 0.05, 0.38, 0.95, brass);
  for (const side of [-1, 1]) {
    for (let n = 0; n < 5; n++) {
      const z = 10 - n * 5.3,
        x = side * (15.9 + Math.cos(n) * 0.6);
      drum(x, 2.7, z, 0.08, 0.12, 5.4, dark);
      box(x + side * 0.75, 5.12, z, 1.8, 0.09, 0.1, brass);
      box(
        x + side * 0.8,
        4.25,
        z,
        1.05,
        1.68,
        0.06,
        n % 2 ? "#a8412b" : "#176760",
      );
      box(x + side * 0.8, 3.59, z, 1.08, 0.12, 0.08, brass);
    }
  }
  if (!index) {
    for (const side of [-1, 1]) {
      const x = side * 8,
        z = -24;
      const hull = drum(x, -0.35, z, 1.3, 0.7, 1.3, dark);
      hull.scale.z = 3.7;
      drum(x, 2.6, z, 0.08, 0.12, 6, dark);
      const sail = place(new THREE.CircleGeometry(2, 3), "#c77746", x, 3, z);
      sail.scale.set(0.8, 1.15, 1);
      sail.material.side = THREE.DoubleSide;
    }
  }
  for (let i = 0; i < 22; i++) {
    const a = i * 2.4,
      r = 65 + (i % 4) * 9,
      h = 14 + ((i * 7) % 24);
    drum(
      Math.cos(a) * r,
      h / 2 - 4,
      Math.sin(a) * r,
      0.6,
      17,
      h,
      index ? "#977e73" : "#809c93",
      7,
    );
  }
  return group;
}
