/**
 * Web Audio Sound Engine for Old Mick Against the Mob.
 * No audio files needed - generates sounds procedurally.
 * @module sound
 */

export class SoundEngine {
  constructor() {
    try {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    } catch(e) { this.ctx = null; }
  }

  _osc(type, freq, startT, dur, vol, freqEnd) {
    if (!this.ctx) return;
    if (this.ctx.state === 'suspended') this.ctx.resume();
    const t   = this.ctx.currentTime + startT;
    const osc = this.ctx.createOscillator();
    const g   = this.ctx.createGain();
    osc.connect(g); g.connect(this.ctx.destination);
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t);
    if (freqEnd) osc.frequency.exponentialRampToValueAtTime(freqEnd, t + dur);
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    osc.start(t); osc.stop(t + dur + 0.01);
  }

  /** Short click — token placed / moved */
  place()  { this._osc('sine',    523, 0,    0.12, 0.20); }

  /** Three rising tones — terrain locked */
  lock()   {
    [523, 659, 784].forEach((f, i) =>
      this._osc('sine', f, i * 0.10, 0.14, 0.25));
  }

  /** Downward sawtooth — rifle / emu fires */
  fire()   { this._osc('sawtooth', 300, 0, 0.25, 0.35, 55); }

  /** Thud — attack hits a target */
  hit()    { this._osc('square',   120, 0, 0.40, 0.45, 35); }

  /** Hard block sound — blocked by hard terrain */
  block()  { this._osc('square',   250, 0, 0.18, 0.30, 80); }

  /** Nuke — deep rumble + descending saw */
  nuke()   {
    this._osc('sawtooth', 110, 0, 1.20, 0.60, 20);
    this._osc('sine',      55, 0, 1.50, 0.40, 18);
  }

  /** Turn change — soft chime */
  turn()   {
    this._osc('sine', 660, 0,    0.12, 0.18);
    this._osc('sine', 880, 0.12, 0.10, 0.14);
  }
}

/** Global SFX instance */
export const SFX = new SoundEngine();

/**
 * Unlock audio on first user gesture (Chrome/Safari block AudioContext).
 * Call this once to set up the unlock listeners.
 */
export function initAudioUnlock() {
  const _unlockAudio = () => {
    if (SFX.ctx && SFX.ctx.state === 'suspended') SFX.ctx.resume();
    SFX._osc('sine', 880, 0, 0.02, 0.001);
    window.removeEventListener('click',    _unlockAudio);
    window.removeEventListener('keydown',  _unlockAudio);
    window.removeEventListener('touchend', _unlockAudio);
  };
  window.addEventListener('click',    _unlockAudio);
  window.addEventListener('keydown',  _unlockAudio);
  window.addEventListener('touchend', _unlockAudio);
}
