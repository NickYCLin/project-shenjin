import { readFile } from "node:fs/promises";
import { validateBytes } from "gltf-validator";
const limits = { temple: 180000, hero: 15000, sentinel: 30000, spear: 8000 };
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
  if (data.length > 20 * 1024 * 1024 || triangles > limit || triangles === 0) {
    throw new Error(
      `${name}: exceeds checked-in asset size/triangle budget or is empty`,
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
if (failed) process.exitCode = 1;
