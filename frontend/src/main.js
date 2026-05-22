import { BootScene } from "./scenes/BootScene.js";
import { IntroScene } from "./scenes/IntroScene.js";
import { GameScene } from "./scenes/GameScene.js";
import { WSClient, resolveWsUrl } from "/protocol/websocket/browser_client.js";
import { initUI }    from "./ui.js";
import { CANVAS_W, CANVAS_H } from "./constants.js";

// WebSocket — created once, shared between HTML panels (ui.js) and Phaser (GameScene)
const ws = new WSClient(resolveWsUrl());
initUI(ws);

const game = new Phaser.Game({
  type:            Phaser.AUTO,
  width:           CANVAS_W,
  height:          CANVAS_H,
  transparent:      true,
  parent:          "game-canvas",
  // Required for tutorial GIF <img> overlays (add.dom) to align with the scaled canvas.
  dom:             { createContainer: true },
  scene:           [BootScene, IntroScene, GameScene],
  scale: {
    mode:       Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.NO_CENTER,
  },
});

// Make ws available to Phaser scenes via the registry
game.registry.set("ws", ws);
