import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { validateBytes } from "gltf-validator";
const limits = {
  temple: 180000,
  hero: 15000,
  sentinel: 30000,
  spear: 8000,
  "temple-v2": 600000,
  "hero-rigged": 110000,
  "sentinel-rigged": 160000,
};
let failed = false;
for (const [name, limit] of Object.entries(limits)) {
  const data = await readFile(
    new URL(`../art/exports/${name}.glb`, import.meta.url),
  );
  const report = await validateBytes(new Uint8Array(data), {
    uri: `${name}.glb`,
    maxIssues: 30,
  });
  const jsonLength = data.readUInt32LE(12);
  const gltf = JSON.parse(data.subarray(20, 20 + jsonLength).toString());
  let triangles = 0;
  for (const mesh of gltf.meshes ?? [])
    for (const primitive of mesh.primitives) {
      if ((primitive.mode ?? 4) !== 4)
        throw new Error(`${name}: expected triangle mesh`);
      const accessor =
        gltf.accessors[primitive.indices ?? primitive.attributes.POSITION];
      triangles += accessor.count / 3;
    }
  if (data.length > 40 * 1024 * 1024 || triangles > limit || triangles === 0) {
    throw new Error(
      `${name}: exceeds checked-in asset size/triangle budget or is empty`,
    );
  }
  if ((gltf.images ?? []).some((image) => image.bufferView === undefined)) {
    throw new Error(
      `${name}: texture images must be embedded for offline playback`,
    );
  }
  console.log(
    `${name}: ${triangles.toLocaleString()} triangles; ${report.issues.numErrors} errors, ${report.issues.numWarnings} warnings`,
  );
  if (report.issues.numErrors || report.issues.numWarnings) {
    console.log(JSON.stringify(report.issues.messages, null, 2));
    failed = true;
  }
}
const sourceManifest = JSON.parse(
  await readFile(
    new URL("../art/textures/sources.json", import.meta.url),
    "utf8",
  ),
);
for (const asset of sourceManifest.assets)
  for (const item of Object.values(asset.maps)) {
    const data = await readFile(new URL(`../${item.path}`, import.meta.url));
    if (
      data.length !== item.size ||
      createHash("sha256").update(data).digest("hex") !== item.sha256
    ) {
      throw new Error(`Texture source checksum mismatch: ${item.path}`);
    }
  }
const colliders = JSON.parse(
  await readFile(
    new URL("../art/exports/temple-v2-colliders.json", import.meta.url),
    "utf8",
  ),
);
if (!colliders.boxes.length || colliders.boxes.length > 150)
  throw new Error("Invalid camera collider count");
for (const box of colliders.boxes) {
  if (
    [box.min, box.max].some(
      (vector) =>
        vector.length !== 3 || vector.some((value) => !Number.isFinite(value)),
    ) ||
    box.min.some((value, axis) => value >= box.max[axis])
  ) {
    throw new Error("Invalid camera collider bounds");
  }
}
console.log(
  `Texture source checksums verified; ${colliders.boxes.length} camera proxies checked.`,
);
if (failed) process.exitCode = 1;
