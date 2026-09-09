import { AnimationMixer, LoopOnce, LoopRepeat } from "three";

export const CHARACTER_CLIPS = {
  hero: ["Idle", "Walk", "Thrust", "Dodge", "Hit", "Death"],
  sentinel: ["Idle", "Walk", "Windup", "Slam", "Recover", "Hit", "Death"],
};

/** Skeletal poses use the combat clock for attacks, so contact cannot drift. */
export class CharacterAnimation {
  constructor(root, clips, kind) {
    this.root = root;
    this.mixer = new AnimationMixer(root);
    this.actions = new Map(
      clips.map((clip) => [clip.name, this.mixer.clipAction(clip)]),
    );
    for (const name of CHARACTER_CLIPS[kind]) {
      if (!this.actions.has(name))
        throw new Error(`${kind} is missing required animation ${name}`);
    }
    this.reset();
  }

  reset() {
    this.mixer.stopAllAction();
    this.current = null;
    this.currentKey = null;
    this.flinch = 0;
    this.lastMode = "Idle";
  }

  hit() {
    this.flinch = 0.22;
  }

  update(mode, delta, { progress = null, id = "", speed = 1 } = {}) {
    const key = `${mode}:${id}`;
    const action = this.actions.get(mode);
    if (!action) throw new Error(`Unknown animation ${mode}`);
    if (key !== this.currentKey) {
      const previous = this.current;
      action.reset();
      action.setLoop(
        mode === "Idle" || mode === "Walk" ? LoopRepeat : LoopOnce,
        Infinity,
      );
      action.clampWhenFinished = true;
      action.setEffectiveWeight(1);
      action.play();
      // No long blend on a timed strike: the .20s contact frame must be visible.
      if (previous && previous !== action) {
        previous.fadeOut(0.06);
        action.fadeIn(0.06);
      }
      this.current = action;
      this.currentKey = key;
    }
    action.paused = progress !== null;
    if (progress !== null)
      action.time =
        Math.min(0.999999, Math.max(0, progress)) * action.getClip().duration;
    else if (mode !== "Death") action.setEffectiveTimeScale(speed);
    this.mixer.update(delta);
    this.flinch = Math.max(0, this.flinch - delta);
    this.lastMode = mode;
  }
}
