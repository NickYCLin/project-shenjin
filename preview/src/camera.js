import { Raycaster, Vector3 } from "three";

/** Five parallel probes protect the camera's center and near-plane edges. */
export class CameraCollision {
  constructor(clearance = 0.32) {
    this.clearance = clearance;
    this.ray = new Raycaster();
    this.direction = new Vector3();
    this.right = new Vector3();
    this.up = new Vector3();
    this.origin = new Vector3();
    this.offset = new Vector3();
  }

  resolve(pivot, desired, colliders, output = new Vector3()) {
    this.direction.subVectors(desired, pivot);
    const distance = this.direction.length();
    if (distance < 1e-5 || !colliders.length) return output.copy(desired);
    this.direction.divideScalar(distance);
    this.right.crossVectors(this.direction, new Vector3(0, 1, 0)).normalize();
    if (this.right.lengthSq() < 1e-6) this.right.set(1, 0, 0);
    this.up.crossVectors(this.right, this.direction).normalize();
    let safeDistance = distance;
    this.ray.near = 0;
    this.ray.far = distance + this.clearance;
    for (const [x, y] of [
      [0, 0],
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1],
    ]) {
      this.offset
        .copy(this.right)
        .multiplyScalar(x * this.clearance)
        .addScaledVector(this.up, y * this.clearance);
      this.origin.copy(pivot).add(this.offset);
      this.ray.set(this.origin, this.direction);
      const hit = this.ray.intersectObjects(colliders, true)[0];
      if (hit)
        safeDistance = Math.min(
          safeDistance,
          Math.max(0.08, hit.distance - this.clearance),
        );
    }
    return output.copy(pivot).addScaledVector(this.direction, safeDistance);
  }
}
