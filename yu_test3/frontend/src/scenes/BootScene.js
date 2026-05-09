import { COLORS, FONT_TITLE, FONT_MONO } from "../constants.js";
import { preloadAll } from "../audio.js";

/**
 * BootScene — runs once on page load.
 *
 * Responsibilities:
 *   1. Preload ALL audio assets (missing files are silently skipped).
 *   2. Preload ALL image assets used in GameScene.
 *   3. Connect to the WebSocket server and hand the connection to IntroScene.
 *
 * Falls back after 3 s so the UI isn't blocked if the server is down —
 * useful for pure visual iteration without running the backend.
 */
export class BootScene extends Phaser.Scene {
  constructor() { super("Boot"); }

  preload() {
    // ── Audio ──────────────────────────────────────────────────────────────────
    preloadAll(this);

    // ── Board background ───────────────────────────────────────────────────────
    this.load.image("board",          "assets/images/board1.png");

    // ── Mick tokens ────────────────────────────────────────────────────────────
    this.load.image("tok_mick_atk_a", "assets/images/atk-mick-a.png");       // Keith A
    this.load.image("tok_mick_atk_b", "assets/images/atk-mick-b.png");       // Keith B
    this.load.image("tok_mick_def",   "assets/images/def-mick.png");         // Old Mick (defense)
    this.load.image("tok_mick_nuke",  "assets/images/nuke-mick-keith.png");

    // ── Emu tokens ─────────────────────────────────────────────────────────────
    this.load.image("tok_emu_atk_a",  "assets/images/atk-emu-a.png");        // Mob A
    this.load.image("tok_emu_atk_b",  "assets/images/atk-emu-b.png");        // Mob B
    this.load.image("tok_emu_def",    "assets/images/atk-emu-cassowary.png"); // Cassowary (defense)
    this.load.image("tok_emu_nuke",   "assets/images/nuke-emu-ancestors.png");

    // ── HQ sprites ─────────────────────────────────────────────────────────────
    this.load.image("hq_mick",        "assets/images/hq-mick.png");
    this.load.image("hq_mick_dead",   "assets/images/hq-mick-destroyed.png");
    this.load.image("hq_emu",         "assets/images/hq-emu.png");
    this.load.image("hq_emu_dead",    "assets/images/hq-emu-destroyed.png");

    // ── Terrain tiles ──────────────────────────────────────────────────────────
    // Resource cells
    this.load.image("cell_mick",      "assets/images/cell-mick-wheat fields.png");
    this.load.image("cell_emu",       "assets/images/cell-emu-feeding grounds.png");
    // Hard terrain (impassable)
    this.load.image("hard_mick",      "assets/images/hard-final.png");
    this.load.image("hard_emu",       "assets/images/hard-final.png");
    // Soft terrain (destructible blocker)
    this.load.image("soft_mick",      "assets/images/soft-final1.png");
    this.load.image("soft_emu",       "assets/images/soft-final1.png");

    // Gracefully skip any missing image
    this.load.on("loaderror", (file) => {
      console.warn(`[boot] Image missing: ${file.key} (${file.url})`);
    });
  }

  // ── Post-process: make white/near-white pixels transparent ──────────────────
  // Called after preload() finishes, before scenes start.
  // Threshold 230 means R>230 && G>230 && B>230 → alpha = 0.
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
      if (data[i] > threshold && data[i + 1] > threshold && data[i + 2] > threshold) {
        data[i + 3] = 0;  // make transparent
      }
    }
    ctx.putImageData(id, 0, 0);
    // Replace the Phaser texture with the processed (transparent-bg) version
    this.textures.remove(key);
    this.textures.addCanvas(key, canvas);
  }

  create() {
    const { width, height } = this.scale;

    // Strip white backgrounds from tokens, HQ sprites, and terrain tile images.
    // (Any PNG that was designed on a white canvas needs this treatment.)
    const WHITE_BG_KEYS = [
      // Tokens
      "tok_mick_atk_a", "tok_mick_atk_b", "tok_mick_def", "tok_mick_nuke",
      "tok_emu_atk_a",  "tok_emu_atk_b",  "tok_emu_def",  "tok_emu_nuke",
      // HQ
      "hq_mick", "hq_mick_dead", "hq_emu", "hq_emu_dead",
      // Terrain tiles
      "cell_mick", "cell_emu",
      "hard_mick",  "hard_emu",
      "soft_mick",  "soft_emu",
    ];
    for (const key of WHITE_BG_KEYS) this._removeWhiteBg(key);

    // Dark background
    this.add.rectangle(width / 2, height / 2, width, height, COLORS.bg);

    // Title
    this.add.text(width / 2, height / 2 - 60, "OLD MICK AGAINST THE MOB", {
      fontFamily: FONT_TITLE, fontSize: "26px",
      color: "#d4a030", align: "center",
    }).setOrigin(0.5);

    // Connecting indicator with animated dots
    const sub = this.add.text(width / 2, height / 2 + 10, "Connecting", {
      fontFamily: FONT_MONO, fontSize: "13px",
      color: "#8a7060", align: "center",
    }).setOrigin(0.5);

    let dots = 0;
    this.time.addEvent({
      delay: 420, loop: true,
      callback: () => sub.setText("Connecting" + ".".repeat((++dots % 4))),
    });

    // Connect to WS — import lazily so first paint is fast
    import("../WSClient.js").then(({ WSClient }) => {
      const ws = new WSClient();
      let advanced = false;

      const advance = () => {
        if (advanced) return;
        advanced = true;
        this.time.delayedCall(300, () => this.scene.start("Intro", { ws }));
      };

      ws.on("connected", advance);
      // Fallback: proceed after 3 s even if the server never responds
      this.time.delayedCall(3000, advance);
    });
  }
}
