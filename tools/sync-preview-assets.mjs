import { mkdir, copyFile, access } from "node:fs/promises";
const root = new URL("../", import.meta.url);
const names = ["temple", "hero", "sentinel", "spear"];
for (const name of names) {
  try {
    await access(new URL(`art/exports/${name}.glb`, root));
  } catch {
    throw new Error(
      `Missing ${name}.glb. Rebuild Blender assets; see tools/blender/README.md.`,
    );
  }
}
await mkdir(new URL("preview/public/models/", root), { recursive: true });
for (const name of names) {
  await copyFile(
    new URL(`art/exports/${name}.glb`, root),
    new URL(`preview/public/models/${name}.glb`, root),
  );
}
console.log("Synced four original Blender GLB assets.");
