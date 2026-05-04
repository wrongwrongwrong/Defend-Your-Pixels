import { CANVAS_H, CANVAS_W } from "./constants.js";
import { WSClient } from "./WSClient.js";
import { IntroScene } from "./scenes/IntroScene.js";
import { GameScene } from "./scenes/GameScene.js";

const ws = new WSClient(`ws://${window.location.hostname || "localhost"}:8765`);

const game = new Phaser.Game({
  type: Phaser.AUTO,
  width: CANVAS_W,
  height: CANVAS_H,
  parent: "game-container",
  backgroundColor: "#1a1008",
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
});

game.scene.add("Intro", IntroScene, false);
game.scene.add("Game", GameScene, false);
game.scene.start("Intro", { ws });
