# Audio assets

Drop your sound files in **this folder**. The Phaser loader will pick them up
automatically next time you refresh the browser.

Missing files do NOT crash the game — you'll just see a console warning like:

```
[audio] missing — sfx_rifle (assets/audio/sfx_rifle.mp3) — game will run without this sound.
```

So you can add files one at a time and hear each one as it gets dropped in.

## Required filenames

The code in `frontend/src/audio.js` looks for these specific names. **Match the
filename exactly (case sensitive)**, or rename in `audio.js` to whatever you want.

| File                       | Plays when                                | Notes                                 |
|----------------------------|-------------------------------------------|---------------------------------------|
| `bgm_outback.mp3`          | First Intro click → loops forever         | 1–2 min loop, ~0.5–2 MB ideal         |
| `sfx_rifle.mp3`            | ATK damages a cell (`cell_damaged`)       | Short bolt-action gunshot             |
| `sfx_hit.mp3`              | Cell destroyed (`cell_destroyed`)         | Wood/dust impact, slightly meatier    |
| `sfx_block.mp3`            | Hard terrain block / soft destroyed       | Bullet ricochet "PING" works great    |
| `sfx_explosion.mp3`        | HQ destroyed / Tier-4 NUKE                | Big satisfying explosion              |
| `sfx_page.mp3`             | Story slide advance                       | Paper rustle / typewriter ding        |
| `sfx_select.mp3`           | Side selection card click                 | Soft confirm tone                     |
| `sfx_turn.mp3`             | Turn marker flips                         | Bell ding / military whistle          |
| `sfx_victory.mp3`          | Game won by attrition                     | Short fanfare                         |
| `sfx_defeat.mp3`           | Game lost                                 | Sad horn / wind                       |

You don't need to add all of them — the game tolerates missing files. Start
with `bgm_outback.mp3` + `sfx_rifle.mp3` + `sfx_hit.mp3` + `sfx_explosion.mp3`,
add the rest later.

## Format

- **MP3** (`.mp3`) is the safest cross-browser choice for desktop testing.
- If you also have `.ogg`, edit `audio.js` to add the path and Phaser will
  auto-pick whichever the browser supports:
  ```js
  bgm_outback: ["assets/audio/bgm_outback.mp3", "assets/audio/bgm_outback.ogg"],
  ```

## Where to find files

See the project notes — recommended sources:
- **freesound.org** (huge SFX library, CC licenses)
- **incompetech.com** (Kevin MacLeod, BGM, CC-BY)
- **opengameart.org**
- **mixkit.co/free-sound-effects**
- **AI-generated**: suno.ai / udio.com for original BGM

## Volume & mute

- Top-right of the game canvas has a 🔊 button that mutes/unmutes everything.
- Default volumes (`audio.js`): BGM 40%, SFX 70%. Edit the `_state` defaults
  if you want different levels.

## When does BGM start?

Browsers block autoplay until the user interacts. The game starts BGM the
**first time you click or press a key in the Intro scene** — that gesture
unlocks autoplay for the whole session.
