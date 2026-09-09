import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import {
  CharacterAnimation,
  CHARACTER_CLIPS,
} from "../src/character-animation.js";

for (const kind of ["hero", "sentinel"]) {
  test(`${kind}: shipped GLB contains skin and playable joint animation`, async () => {
    const data = await readFile(
      new URL(`../../art/exports/${kind}-rigged.glb`, import.meta.url),
    );
    const loader = new GLTFLoader();
    // Node has no image decoder. Keep the shipped geometry/skin/animation binary intact;
    // omit material bindings only in this headless pose test. The validator checks images.
    loader.register((parser) => ({
      name: "HeadlessSkeletonTest",
      beforeRoot() {
        for (const mesh of parser.json.meshes ?? [])
          for (const primitive of mesh.primitives) delete primitive.material;
      },
    }));
    const gltf = await loader.parseAsync(
      data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength),
      "",
    );
    let skinned = 0;
    gltf.scene.traverse((object) => {
      if (object.isSkinnedMesh) skinned++;
    });
    assert.ok(skinned > 0, "must be a real skinned model");
    assert.deepEqual(
      gltf.animations.map((a) => a.name).sort(),
      [...CHARACTER_CLIPS[kind]].sort(),
    );
    const animation = new CharacterAnimation(gltf.scene, gltf.animations, kind);
    animation.update("Walk", 0.16);
    gltf.scene.updateMatrixWorld(true);
    const before = new Map();
    gltf.scene.traverse((object) => {
      if (object.isBone)
        before.set(object.name, [...object.matrixWorld.elements]);
    });
    animation.update("Walk", 0.25);
    gltf.scene.updateMatrixWorld(true);
    let movedBones = 0;
    gltf.scene.traverse((object) => {
      if (
        object.isBone &&
        object.matrixWorld.elements.some(
          (value, index) =>
            Math.abs(value - before.get(object.name)[index]) > 1e-4,
        )
      )
        movedBones++;
    });
    assert.ok(movedBones >= 4, "walk must move articulated joints");
    const mode = kind === "hero" ? "Thrust" : "Windup";
    animation.update(mode, 1 / 60, { progress: 0.4, id: 1 });
    const contactTime = animation.current.time;
    animation.update(mode, 0, { progress: 0.4, id: 1 });
    assert.equal(
      animation.current.time,
      contactTime,
      "a paused combat clock must freeze the pose",
    );
    animation.update(mode, 1 / 60, { progress: 0.8, id: 1 });
    assert.ok(animation.current.time > contactTime);
    animation.update("Death", 2);
    animation.reset();
    animation.update("Idle", 1 / 60);
    assert.equal(animation.lastMode, "Idle");
    if (kind === "hero")
      assert.ok(gltf.scene.getObjectByName("WeaponSocket")?.isBone);
  });
}
