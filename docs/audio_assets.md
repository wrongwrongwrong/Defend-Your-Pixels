# Audio Assets

Drop sound files into the active frontend audio assets folder. The Phaser loader
should pick them up automatically on refresh.

Missing files must not crash the game. They should only log warnings.

## Required filenames

The frontend audio manager looks for these specific names. Match the filenames
exactly, or update the manifest in the frontend code.

| File | Plays when | Notes |
|------|------------|-------|
| `bgm_outback.mp3` | First Intro click, loops during play | 1-2 minute loop is ideal |
| `sfx_p1_attack.mp3` | Farmer-side attack fire | Short rifle shot |
| `sfx_p2_attack.mp3` | Mob-side attack fire | Distinct emu-side attack cue |
| `sfx_first_hit.mp3` | First hit on a protected cell | Light chip / impact |
| `sfx_destroy.mp3` | Cell destroyed | Stronger destruction cue |
| `sfx_block.mp3` | Terrain hit or soft-terrain destruction | Ricochet or thud |
| `sfx_explosion.mp3` | HQ destroyed or nuke triggered | Large explosion |
| `sfx_page.mp3` | Intro slide advance | Paper / typewriter cue |
| `sfx_select.mp3` | Side selection click or confirm-style UI action | Soft confirm tone |
| `sfx_marker_turn.mp3` | Marker rotation feedback | Optional until wired |
| `sfx_p1_hq_select.mp3` | P1 HQ lock | Optional until wired |
| `sfx_p2_hq_select.mp3` | P2 HQ lock | Optional until wired |
| `sfx_p1_defense.mp3` | P1 defense placement | Optional until wired |
| `sfx_p2_defense.mp3` | P2 defense placement | Optional until wired |
| `sfx_tier_up.mp3` | Any tier increase | Shared tier-up stinger |
| `sfx_victory.mp3` | Win | Short fanfare |
| `sfx_defeat.mp3` | Loss | Sad horn / wind |

## Format

- MP3 is the safest cross-browser choice for desktop testing.
- If you also have OGG, add both paths in the frontend audio manifest.

Example:

```js
bgm_outback: ["assets/audio/bgm_outback.mp3", "assets/audio/bgm_outback.ogg"]
```

## Sources

Useful places to source or create files:

- `freesound.org`
- `incompetech.com`
- `opengameart.org`
- `mixkit.co/free-sound-effects`
- AI-generated music or SFX tools if the team wants original audio

## Volume and mute

- The top-right of the game canvas includes a mute toggle.
- Default levels are controlled in the frontend audio manager.

## Browser autoplay note

Browsers block autoplay until the user interacts. BGM should start on the first
player interaction in the Intro scene.
