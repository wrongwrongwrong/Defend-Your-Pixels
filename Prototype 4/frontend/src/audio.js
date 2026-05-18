/**
 * Audio manager for Prototype 4 (Phaser Sound system + Web Audio synth fallback).
 *
 * - Lists every audio asset the game expects (`AUDIO_MANIFEST`).
 * - Loads them all in BootScene via `preloadAll(scene)`.
 * - Missing files don't crash the game — just log a warning.
 * - BGM is a single global track; SFX are short one-shots.
 * - `sfx_marker_turn` is synthesized (523 Hz sine) — no file needed.
 * - Keys without a file yet (sfx_block, sfx_first_hit, sfx_defeat) are
 *   silently skipped until the files are added.
 */

// ─── Asset manifest ───────────────────────────────────────────────────────────
// Keys that share a file just point to the same path — Phaser loads it once
// per key but the memory overhead is minimal for short SFX.
export const AUDIO_MANIFEST = {
  // ── BGM ─────────────────────────────────────────────────────────────────
  bgm_outback:      ["assets/audio/bgm.mp3"],

  // ── Per-player attacks ────────────────────────────────────────────────
  sfx_p1_attack:    ["assets/audio/mick_attack.wav"],
  sfx_p2_attack:    ["assets/audio/emu_attack.wav"],

  // ── Per-player triggers (HQ select + defence activation share same file)
  sfx_p1_hq_select: ["assets/audio/mick_trigger.mp3"],
  sfx_p2_hq_select: ["assets/audio/emu_trigger.mp3"],
  sfx_p1_defense:   ["assets/audio/mick_trigger.mp3"],
  sfx_p2_defense:   ["assets/audio/emu_trigger.mp3"],

  // ── Destruction ────────────────────────────────────────────────────────
  sfx_explosion:    ["assets/audio/HQ_destroyed.mp3"],
  sfx_destroy:      ["assets/audio/HQ_destroyed.mp3"],  // cell destroyed (reuse)

  // ── Progression ────────────────────────────────────────────────────────
  sfx_tier_up:      ["assets/audio/level_up.mp3"],

  // ── Game end ────────────────────────────────────────────────────────────
  sfx_victory:      ["assets/audio/win.mp3"],

  // ── UI / misc ──────────────────────────────────────────────────────────
  sfx_select:       ["assets/audio/place_HQ.mp3"],  // token placed / picker / end turn
  sfx_page:         ["assets/audio/intro.wav"],      // intro slide advance

  // ── Not yet assigned (files TBD — will silently skip until added) ───────
  // sfx_block:     ["assets/audio/sfx_block.mp3"],
  // sfx_first_hit: ["assets/audio/sfx_first_hit.mp3"],
  // sfx_defeat:    ["assets/audio/sfx_defeat.mp3"],

  // ── sfx_marker_turn is synthesized — no file entry needed ─────────────
  // (handled by playSynth / SYNTH_SOUNDS below)
};

// ─── Internal state ───────────────────────────────────────────────────────────
const _state = {
  available: new Set(),  // keys that loaded successfully
  bgmKey:    null,
  bgmObj:    null,
  muted:     false,
  bgmVol:    0.40,
  sfxVol:    0.70,
};

// ─── Loading ──────────────────────────────────────────────────────────────────

/** Call from BootScene.preload(). Queues every manifest entry. */
export function preloadAll(scene) {
  for (const [key, paths] of Object.entries(AUDIO_MANIFEST)) {
    scene.load.audio(key, paths);
  }
  // Phaser's loader emits 'loaderror' for any single missing/malformed file —
  // we skip those silently so the rest of the game still runs.
  scene.load.on("loaderror", (file) => {
    console.warn(`[audio] missing — ${file.key} (${file.url}) — game will run without this sound.`);
  });
  // "filecomplete" fires for every loaded file with (key, type, data).
  // "filecomplete-audio" does NOT exist in Phaser 3 — only the generic
  // "filecomplete" event is emitted for all files by type.
  scene.load.on("filecomplete", (key, type) => {
    if (type === "audio") _state.available.add(key);
  });
}

// ─── Synthesized sounds (Web Audio API) ──────────────────────────────────────
// Used for sounds that don't have a file yet, or where a synthesized tone
// is intentionally preferred (e.g. the crisp 523 Hz token-rotate click).

const _synth = {
  ctx: null,
  getCtx() {
    if (!this.ctx) {
      try { this.ctx = new (window.AudioContext || window.webkitAudioContext)(); }
      catch (e) { this.ctx = null; }
    }
    return this.ctx;
  },
  /** Play one oscillator tone. */
  osc(type, freq, startT, dur, vol, freqEnd) {
    const ctx = this.getCtx();
    if (!ctx) return;
    if (ctx.state === "suspended") ctx.resume();
    const t   = ctx.currentTime + startT;
    const osc = ctx.createOscillator();
    const g   = ctx.createGain();
    osc.connect(g);
    g.connect(ctx.destination);
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t);
    if (freqEnd) osc.frequency.exponentialRampToValueAtTime(freqEnd, t + dur);
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    osc.start(t);
    osc.stop(t + dur + 0.01);
  },
};

// Map SFX key → synth generator function.
// sfx_marker_turn: short 523 Hz sine click (same as the "place" sound in
// sound_preview.html — confirms a token rotation without being distracting).
const SYNTH_SOUNDS = {
  sfx_marker_turn: () => _synth.osc("sine", 523, 0, 0.12, 0.20),
};

/** Play a synthesized sound by key (bypasses Phaser's sound manager). */
export function playSynth(key) {
  if (_state.muted) return;
  const fn = SYNTH_SOUNDS[key];
  if (fn) fn();
}

// ─── Playback helpers ─────────────────────────────────────────────────────────

/**
 * Play a short one-shot sound.
 * If the file isn't loaded, falls back to the synth table.
 * Returns the Phaser Sound instance (or null for synth / muted).
 */
export function playSfx(scene, key, opts = {}) {
  if (_state.muted) return null;
  if (_state.available.has(key)) {
    return scene.sound.play(key, { volume: _state.sfxVol, ...opts });
  }
  // Fallback: synthesized sound (e.g. sfx_marker_turn)
  if (SYNTH_SOUNDS[key]) {
    playSynth(key);
    return null;
  }
  return null;
}

/**
 * Start (or replace) the looping BGM track.
 * Idempotent — calling with the same key while it's already playing is a no-op.
 */
export function playBgm(scene, key, opts = {}) {
  if (!_state.available.has(key)) return null;
  if (_state.bgmKey === key && _state.bgmObj?.isPlaying) return _state.bgmObj;

  // Fade out the old track if any
  if (_state.bgmObj) {
    const old = _state.bgmObj;
    scene.tweens.add({
      targets: old, volume: 0, duration: 600,
      onComplete: () => old.stop(),
    });
  }

  const sound = scene.sound.add(key, { loop: true, volume: 0, ...opts });
  sound.play();
  // Fade in
  scene.tweens.add({
    targets: sound,
    volume: _state.muted ? 0 : _state.bgmVol,
    duration: 800,
  });
  _state.bgmKey = key;
  _state.bgmObj = sound;
  return sound;
}

export function stopBgm(scene) {
  if (!_state.bgmObj) return;
  const old = _state.bgmObj;
  scene.tweens.add({
    targets: old, volume: 0, duration: 500,
    onComplete: () => old.stop(),
  });
  _state.bgmKey = null;
  _state.bgmObj = null;
}

// ─── Mute / volume ────────────────────────────────────────────────────────────

export function isMuted()    { return _state.muted; }

export function toggleMute() {
  _state.muted = !_state.muted;
  if (_state.bgmObj) _state.bgmObj.setVolume(_state.muted ? 0 : _state.bgmVol);
  return _state.muted;
}

export function setBgmVolume(v) {
  _state.bgmVol = Math.max(0, Math.min(1, v));
  if (_state.bgmObj && !_state.muted) _state.bgmObj.setVolume(_state.bgmVol);
}

export function setSfxVolume(v) {
  _state.sfxVol = Math.max(0, Math.min(1, v));
}

/** True when at least one audio asset has loaded — useful for guards. */
export function hasAnyAudio() { return _state.available.size > 0; }
