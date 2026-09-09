import { mkdir, copyFile, access, rm } from "node:fs/promises";
const root = new URL("../", import.meta.url);
const names = ["temple-v2", "hero-rigged", "sentinel-rigged", "spear"];
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
// Drop only known obsolete generated copies after upgrading a v0.1 checkout.
for (const name of ["temple", "hero", "sentinel"]) {
  await rm(new URL(`preview/public/models/${name}.glb`, root), { force: true });
}
for (const name of names) {
  await copyFile(
    new URL(`art/exports/${name}.glb`, root),
    new URL(`preview/public/models/${name}.glb`, root),
  );
}
console.log("Synced temple, two animated characters and spear.");
await copyFile(
  new URL("art/exports/temple-v2-colliders.json", root),
  new URL("preview/public/models/temple-v2-colliders.json", root),
);
