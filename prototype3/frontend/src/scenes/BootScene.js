import { COLORS } from "../constants.js";

export class BootScene extends Phaser.Scene {
  constructor() { super("Boot"); }

  create() {
    const { width, height } = this.scale;
    this.add.rectangle(width / 2, height / 2, width, height, COLORS.bg);

    const title = this.add.text(width / 2, height / 2 - 60,
      "TABLETOP AR STRATEGY", {
        fontFamily: "monospace", fontSize: "28px",
        color: "#00aaff", align: "center",
      }).setOrigin(0.5);

    const sub = this.add.text(width / 2, height / 2,
      "Connecting to game server...", {
        fontFamily: "monospace", fontSize: "14px",
        color: "#9ca3af", align: "center",
      }).setOrigin(0.5);

    // Animate dots
    let dots = 0;
    this.time.addEvent({
      delay: 500, loop: true,
      callback: () => { sub.setText("Connecting" + ".".repeat((++dots % 4))); }
    });

    // Import WSClient lazily to avoid circular deps
    import("../WSClient.js").then(({ WSClient }) => {
      const ws = new WSClient();
      ws.on("connected", () => {
        this.time.delayedCall(400, () => {
          this.scene.start("Intro", { ws });
        });
      });
      // Timeout fallback — go to intro without server
      this.time.delayedCall(3000, () => {
        if (this.scene.isActive("Boot")) {
          this.scene.start("Intro", { ws });
        }
      });
    });
  }
}
