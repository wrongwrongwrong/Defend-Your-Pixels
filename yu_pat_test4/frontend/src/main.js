import { BootScene }  from "./scenes/BootScene.js";
import { IntroScene } from "./scenes/IntroScene.js";
import { GameScene }  from "./scenes/GameScene.js";
import { CANVAS_W, CANVAS_H } from "./constants.js";

const config = {
  type: Phaser.AUTO,
  width:  CANVAS_W,
  height: CANVAS_H,
  backgroundColor: "#0f0c08",
  parent: "game-container",
  scene: [BootScene, IntroScene, GameScene],
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
};

new Phaser.Game(config);
