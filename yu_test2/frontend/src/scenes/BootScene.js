import { COLORS } from "../constants.js";

/**
 * Boot scene — shown once on page load.
 * Connects to WS server, then transitions to Intro.
 * Falls back after 3s so the UI isn't blocked if the server is down
 * (useful for pure visual iteration with no backend running).
 */
export class BootScene extends Phaser.Scene {
  constructor() { super("Boot"); }

  create() {
    const { width, height } = this.scale;
    this.add.rectangle(width / 2, height / 2, width, height, COLORS.bg);

    this.add.text(width / 2, height / 2 - 60,
      "OLD MICK AGAINST THE MOB", {
        fontFamily: "monospace", fontSize: "22px",
        color: "#d4a030", letterSpacing: 3, align: "center",
      }).setOrigin(0.5);

    const sub = this.add.text(width / 2, height / 2,
      "Connecting to game server", {
        fontFamily: "monospace", fontSize: "13px",
        color: "#8a7060", align: "center",
      }).setOrigin(0.5);

    // Animated dots
    let dots = 0;
    this.time.addEvent({
      delay: 450, loop: true,
      callback: () => sub.setText("Connecting" + ".".repeat((++dots % 4))),
    });

    // Lazy-load WSClient so this module stays small for first paint
    import("../WSClient.js").then(({ WSClient }) => {
      const ws = new WSClient();
      let advanced = false;

      const advance = () => {
        if (advanced) return;
        advanced = true;
        this.time.delayedCall(350, () => this.scene.start("Intro", { ws }));
      };

      ws.on("connected", advance);
      // Fallback so design iteration without a backend still works
      this.time.delayedCall(3000, advance);
    });
  }
}
