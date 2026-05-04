import { COLORS } from "../constants.js";
import { preloadAll } from "../audio.js";

/**
 * BootScene — preloads all assets, then starts GameScene.
 * WebSocket is managed externally (main.js → registry).
 */
export class BootScene extends Phaser.Scene {
  constructor() { super("Boot"); }

  preload() {
    preloadAll(this);

    this.load.image("board",          "assets/images/board1.png");

    this.load.image("tok_mick_atk_a", "assets/images/atk-mick-a.png");
    this.load.image("tok_mick_atk_b", "assets/images/atk-mick-b.png");
    this.load.image("tok_mick_def",   "assets/images/def-mick.png");
    this.load.image("tok_mick_nuke",  "assets/images/nuke-mick-keith.png");

    this.load.image("tok_emu_atk_a",  "assets/images/atk-emu-a.png");
    this.load.image("tok_emu_atk_b",  "assets/images/atk-emu-b.png");
    this.load.image("tok_emu_def",    "assets/images/atk-emu-cassowary.png");
    this.load.image("tok_emu_nuke",   "assets/images/nuke-emu-ancestors.png");

    this.load.image("hq_mick",        "assets/images/hq-mick.png");
    this.load.image("hq_mick_dead",   "assets/images/hq-mick-destroyed.png");
    this.load.image("hq_emu",         "assets/images/hq-emu.png");
    this.load.image("hq_emu_dead",    "assets/images/hq-emu-destroyed.png");

    this.load.image("cell_mick",      "assets/images/cell-mick-wheat fields.png");
    this.load.image("cell_emu",       "assets/images/cell-emu-feeding grounds.png");
    this.load.image("hard_mick",      "assets/images/hard-mick-v2.png");
    this.load.image("hard_emu",       "assets/images/hard-emu-v1.png");
    this.load.image("soft_mick",      "assets/images/soft-mick-v1.png");
    this.load.image("soft_emu",       "assets/images/soft-emu-v1.png");

    this.load.on("loaderror", (file) => {
      console.warn(`[boot] missing: ${file.key} (${file.url})`);
    });
  }

  _removeWhiteBg(key, threshold = 230) {
    if (!this.textures.exists(key)) return;
    const img    = this.textures.get(key).getSourceImage();
    const canvas = document.createElement("canvas");
    canvas.width  = img.naturalWidth  || img.width;
    canvas.height = img.naturalHeight || img.height;
    const ctx  = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0);
    const id   = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = id.data;
    for (let i = 0; i < data.length; i += 4) {
      if (data[i] > threshold && data[i+1] > threshold && data[i+2] > threshold)
        data[i+3] = 0;
    }
    ctx.putImageData(id, 0, 0);
    this.textures.remove(key);
    this.textures.addCanvas(key, canvas);
  }

  create() {
    const WHITE_BG_KEYS = [
      "tok_mick_atk_a", "tok_mick_atk_b", "tok_mick_def", "tok_mick_nuke",
      "tok_emu_atk_a",  "tok_emu_atk_b",  "tok_emu_def",  "tok_emu_nuke",
      "hq_mick", "hq_mick_dead", "hq_emu", "hq_emu_dead",
      "cell_mick", "cell_emu", "hard_mick", "hard_emu", "soft_mick", "soft_emu",
    ];
    for (const key of WHITE_BG_KEYS) this._removeWhiteBg(key);

    this.scene.start("Game");
  }
}
