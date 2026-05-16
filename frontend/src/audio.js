/**
 * Audio manager for the live frontend (Phaser Sound system).
 *
 * - Lists every audio asset the game expects (`AUDIO_MANIFEST`).
 * - Loads them all in BootScene via `preloadAll(scene)`.
 * - Missing files don't crash the game — just log a warning.
 * - BGM is a single global track; SFX are short one-shots.
 *
 * Why a singleton object?  Phaser's SoundManager already lives at game level,
 * but we want a thin wrapper so scenes don't poke `this.sound` directly with
 * key strings everywhere.
 */

// ─── Asset manifest ───────────────────────────────────────────────────────────
// Every key the game can play. Add formats your file has (mp3 + ogg is ideal
// for cross-browser support; mp3 alone works in all modern desktop browsers).
export const AUDIO_MANIFEST = {
  // ── BGM ─────────────────────────────────────────────────────────────────
  bgm_outback: ["assets/audio/bgm_outback.mp3"],   // main loop during play

  // ── A. Marker rotation ──────────────────────────────────────────────────
  sfx_marker_turn: ["assets/audio/sfx_marker_turn.mp3"], // any marker rotates

  // ── B. Per-player actions ──────────────────────────────────────────────
  // HQ selection (B.1) — when each side locks in their HQ marker
  sfx_p1_hq_select: ["assets/audio/sfx_p1_hq_select.mp3"],
  sfx_p2_hq_select: ["assets/audio/sfx_p2_hq_select.mp3"],
  // Attack fires (B.2) — Old Mick rifle vs emu shriek
  sfx_p1_attack:    ["assets/audio/sfx_p1_attack.mp3"],
  sfx_p2_attack:    ["assets/audio/sfx_p2_attack.mp3"],
  // Defense activation (B.3) — DEF token placed / shielding
  sfx_p1_defense:   ["assets/audio/sfx_p1_defense.mp3"],
  sfx_p2_defense:   ["assets/audio/sfx_p2_defense.mp3"],

  // ── C. Damage stages ───────────────────────────────────────────────────
  sfx_first_hit: ["assets/audio/sfx_first_hit.mp3"],  // 1st hit on a DEF-zone cell (still alive)
  sfx_destroy:   ["assets/audio/sfx_destroy.mp3"],    // final destruction (cell_destroyed)

  // ── D. Tier upgrade (D) ────────────────────────────────────────────────
  sfx_tier_up: ["assets/audio/sfx_tier_up.mp3"],      // any tier increase

  // ── E. Game end ────────────────────────────────────────────────────────
  sfx_victory: ["assets/audio/sfx_victory.mp3"],      // your side wins
  sfx_defeat:  ["assets/audio/sfx_defeat.mp3"],       // your side loses

  // ── Other / shared ─────────────────────────────────────────────────────
  sfx_block:     ["assets/audio/sfx_block.mp3"],      // hard-terrain block / soft destroyed
  sfx_explosion: ["assets/audio/sfx_explosion.mp3"],  // HQ destroyed (big stinger)
  sfx_page:      ["assets/audio/sfx_page.mp3"],       // intro slide advance
  sfx_select:    ["assets/audio/sfx_select.mp3"],     // side selection card click
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
  scene.load.on("filecomplete-audio", (key) => {
    _state.available.add(key);
  });
}

// ─── Playback helpers ─────────────────────────────────────────────────────────

/** Short one-shot sound. Returns the Phaser Sound instance, or null. */
export function playSfx(scene, key, opts = {}) {
  if (_state.muted) return null;
  if (!_state.available.has(key)) return null;
  return scene.sound.play(key, { volume: _state.sfxVol, ...opts });
}

/** Start (or replace) the looping BGM track. Idempotent — calling with the
 *  same key while it's already playing is a no-op. */
export function playBgm(scene, key, opts = {}) {
  if (!_state.available.has(key)) return null;
  if (_state.bgmKey === key && _state.bgmObj?.isPlaying) return _state.bgmObj;

  // Fade out the old one if any
  if (_state.bgmObj) {
    const old = _state.bgmObj;
    scene.tweens.add({
      targets: old, volume: 0, duration: 600,
      onComplete: () => old.stop(),
    });
  }

  const sound = scene.sound.add(key, {
    loop: true,
    volume: _state.muted ? 0 : 0,
    ...opts,
  });
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

export function isMuted() { return _state.muted; }

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
