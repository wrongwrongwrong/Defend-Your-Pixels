let audioContext = null;
let muted = false;
let bgmTimer = null;

function ensureContext() {
  if (audioContext || !(window.AudioContext || window.webkitAudioContext)) return audioContext;
  const Ctor = window.AudioContext || window.webkitAudioContext;
  audioContext = new Ctor();
  return audioContext;
}

function resumeContext() {
  const ctx = ensureContext();
  if (ctx?.state === "suspended") ctx.resume();
  return ctx;
}

function playTone(type, frequency, duration, volume, frequencyEnd = frequency, delay = 0) {
  const ctx = resumeContext();
  if (!ctx || muted) return;

  const startAt = ctx.currentTime + delay;
  const oscillator = ctx.createOscillator();
  const gainNode = ctx.createGain();

  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, startAt);
  oscillator.frequency.linearRampToValueAtTime(frequencyEnd, startAt + duration);

  gainNode.gain.setValueAtTime(0.0001, startAt);
  gainNode.gain.linearRampToValueAtTime(volume, startAt + 0.02);
  gainNode.gain.exponentialRampToValueAtTime(0.0001, startAt + duration);

  oscillator.connect(gainNode);
  gainNode.connect(ctx.destination);
  oscillator.start(startAt);
  oscillator.stop(startAt + duration + 0.04);
}

function playSequence(steps) {
  for (const step of steps) {
    playTone(step.type, step.frequency, step.duration, step.volume, step.frequencyEnd, step.delay);
  }
}

function stopBgm() {
  if (bgmTimer !== null) {
    window.clearTimeout(bgmTimer);
    bgmTimer = null;
  }
}

function scheduleOutbackLoop() {
  if (muted) return;
  playSequence([
    { type: "triangle", frequency: 146.8, frequencyEnd: 138.6, duration: 1.1, volume: 0.018, delay: 0.00 },
    { type: "sine", frequency: 220.0, frequencyEnd: 196.0, duration: 0.6, volume: 0.010, delay: 0.35 },
    { type: "triangle", frequency: 174.6, frequencyEnd: 164.8, duration: 0.9, volume: 0.014, delay: 1.45 },
  ]);
  bgmTimer = window.setTimeout(scheduleOutbackLoop, 3200);
}

const SFX_BY_KEY = {
  sfx_page: [
    { type: "triangle", frequency: 330, frequencyEnd: 392, duration: 0.16, volume: 0.022, delay: 0.00 },
  ],
  sfx_select: [
    { type: "square", frequency: 294, frequencyEnd: 440, duration: 0.12, volume: 0.020, delay: 0.00 },
  ],
  sfx_first_hit: [
    { type: "square", frequency: 180, frequencyEnd: 160, duration: 0.14, volume: 0.024, delay: 0.00 },
    { type: "triangle", frequency: 220, frequencyEnd: 200, duration: 0.14, volume: 0.016, delay: 0.05 },
  ],
  sfx_p1_attack: [
    { type: "sawtooth", frequency: 210, frequencyEnd: 150, duration: 0.16, volume: 0.024, delay: 0.00 },
  ],
  sfx_destroy: [
    { type: "sawtooth", frequency: 220, frequencyEnd: 70, duration: 0.30, volume: 0.028, delay: 0.00 },
  ],
  sfx_block: [
    { type: "square", frequency: 140, frequencyEnd: 110, duration: 0.10, volume: 0.018, delay: 0.00 },
    { type: "square", frequency: 100, frequencyEnd: 90, duration: 0.08, volume: 0.014, delay: 0.07 },
  ],
  sfx_explosion: [
    { type: "sawtooth", frequency: 90, frequencyEnd: 35, duration: 0.48, volume: 0.032, delay: 0.00 },
  ],
  sfx_victory: [
    { type: "triangle", frequency: 392, frequencyEnd: 392, duration: 0.18, volume: 0.022, delay: 0.00 },
    { type: "triangle", frequency: 494, frequencyEnd: 494, duration: 0.18, volume: 0.022, delay: 0.16 },
    { type: "triangle", frequency: 587, frequencyEnd: 587, duration: 0.28, volume: 0.024, delay: 0.32 },
  ],
  sfx_tier_up: [
    { type: "triangle", frequency: 262, frequencyEnd: 262, duration: 0.12, volume: 0.018, delay: 0.00 },
    { type: "triangle", frequency: 330, frequencyEnd: 330, duration: 0.12, volume: 0.018, delay: 0.10 },
    { type: "triangle", frequency: 392, frequencyEnd: 392, duration: 0.18, volume: 0.020, delay: 0.20 },
  ],
};

export function playSfx(_scene, key) {
  const sequence = SFX_BY_KEY[key];
  if (!sequence) return;
  playSequence(sequence);
}

export function playBgm(_scene, key) {
  if (key !== "bgm_outback" || muted) return;
  if (bgmTimer !== null) return;
  scheduleOutbackLoop();
}

export function toggleMute() {
  muted = !muted;
  if (muted) stopBgm();
  return muted;
}

export function isMuted() {
  return muted;
}
