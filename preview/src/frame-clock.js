/** A bounded fixed-step clock; rendering rate does not change combat speed. */
export class FrameClock {
  constructor(step = 1 / 60, maxFrame = 0.25) {
    this.step = step;
    this.maxFrame = maxFrame;
    this.remainder = 0;
    this.frozen = 0;
  }

  reset() {
    this.remainder = 0;
    this.frozen = 0;
  }

  freeze(seconds) {
    if (Number.isFinite(seconds)) this.frozen = Math.max(this.frozen, seconds);
  }

  advance(delta, tick) {
    if (!Number.isFinite(delta) || delta <= 0) return 0;
    this.remainder += Math.min(delta, this.maxFrame);
    let simulated = 0;
    const maxSteps = Math.ceil(this.maxFrame / this.step) + 1;
    for (let i = 0; i < maxSteps; i++) {
      // A strike can freeze halfway through a slow render frame. Consume the
      // remaining wall time here, including sub-tick fractions, before stepping.
      const frozen = Math.min(this.remainder, this.frozen);
      this.remainder -= frozen;
      this.frozen -= frozen;
      if (this.remainder + 1e-10 < this.step) break;
      this.remainder = Math.max(0, this.remainder - this.step);
      simulated += this.step;
      if (tick(this.step) === false) {
        // A terminal state must not be followed by catch-up ticks.
        this.reset();
        break;
      }
    }
    return simulated;
  }
}
