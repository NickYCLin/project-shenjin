import test from "node:test";
import assert from "node:assert/strict";
import { BoxGeometry, Mesh, MeshBasicMaterial, Vector3 } from "three";
import { CameraCollision } from "../src/camera.js";
function wall(x = 0, width = 6) {
  const mesh = new Mesh(new BoxGeometry(width, 6, 1), new MeshBasicMaterial());
  mesh.position.set(x, 2, 5);
  mesh.updateMatrixWorld(true);
  return mesh;
}
const pivot = new Vector3(0, 2, 0),
  desired = new Vector3(0, 2, 10);
test("an unobstructed camera preserves its requested position", () => {
  assert.deepEqual(new CameraCollision().resolve(pivot, desired, []), desired);
});
test("a pillar between player and camera pulls the camera in front of it", () => {
  const result = new CameraCollision().resolve(pivot, desired, [wall()]);
  assert.ok(result.z < 4.5 && result.z > 4);
  assert.equal(result.y, 2);
});
test("an edge probe protects the near plane when center ray misses", () => {
  const result = new CameraCollision().resolve(pivot, desired, [
    wall(0.38, 0.2),
  ]);
  assert.ok(result.z < 4.5);
});
test("collision correction stays stable and frees camera after obstruction is removed", () => {
  const collision = new CameraCollision(),
    obstacle = wall();
  const first = collision.resolve(pivot, desired, [obstacle]);
  for (let i = 0; i < 30; i++)
    assert.ok(
      collision.resolve(pivot, desired, [obstacle]).distanceTo(first) < 1e-8,
    );
  assert.deepEqual(collision.resolve(pivot, desired, []), desired);
});
