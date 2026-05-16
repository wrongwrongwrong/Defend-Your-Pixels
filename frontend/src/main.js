import { BootScene }  from "./scenes/BootScene.js";
import { IntroScene } from "./scenes/IntroScene.js";
import { GameScene }  from "./scenes/GameScene.js";
import { CANVAS_W, CANVAS_H } from "./constants.js";

// Classic script tag loads Phaser onto globalThis; ES modules do not treat bare
// `Phaser` as a live binding in all environments.
const Phaser = globalThis.Phaser;
if (!Phaser) {
  throw new Error("Phaser missing — check CDN (phaser.min.js) or network block.");
}

const config = {
  type: Phaser.AUTO,
  width:  CANVAS_W,
  height: CANVAS_H,
  backgroundColor: "#0f0c08",
  parent: "game-container",
  dom: { createContainer: true },
  scene: [BootScene, IntroScene, GameScene],
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
};

new Phaser.Game(config);
