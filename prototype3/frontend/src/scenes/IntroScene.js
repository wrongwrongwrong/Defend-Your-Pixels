import { CANVAS_W, CANVAS_H, COLORS } from "../constants.js";

const W = CANVAS_W, H = CANVAS_H;
const CX = W / 2;

// ─── Story slides ─────────────────────────────────────────────────────────────
const SLIDES = [
  {
    year:  "1932",
    place: "Western Australia",
    body:
`The harvest was nearly ready.

Twenty thousand emus arrived first.

They came from the interior — following ancient migration
routes that had nothing to do with anyone's fence lines.

They ate everything.`,
  },
  {
    year:  "THE FARMERS PETITIONED THE GOVERNMENT.",
    body:
`The government sent Major G.P.W. Meredith.
Major Meredith brought two Lewis guns and a truck.

He was confident.

The emus were not impressed.

The operation was quietly abandoned.
The newspapers called it the Great Emu War.
The emus called it Tuesday.`,
  },
  {
    year:  "BUT OLD MICK IS STILL OUT THERE.",
    body:
`He's farmed his patch of red dirt his entire life.
He has riflemen. A boundary fence.
Forty years of stubbornness.

He is not moving.

His goal: destroy enough emu feeding grounds
that the Mob can't sustain itself and collapses.

If his men find the Nest — it ends instantly.`,
  },
  {
    year:  "AND THE MOB KEEPS COMING.",
    body:
`Hungry. Relentless.
Not interested in negotiation.

The emus raid Old Mick's wheat paddocks —
that grain is everything.

The Cassowary guards the Mob's territory.
The Nest is hidden somewhere in the scrublands.

If they find the Homestead first — it ends there.`,
  },
  {
    year:  "THE FENCE STOPPED MEANING ANYTHING WEEKS AGO.",
    body:
`Somewhere on each side, hidden in the chaos,
is the one thing that ends this if it falls.

Find theirs.
Protect yours.

Position your units. Choose your shots wisely.
Only the first thing in a line gets hit.`,
  },
];

// ─── Scene ───────────────────────────────────────────────────────────────────

export class IntroScene extends Phaser.Scene {
  constructor() { super("Intro"); }

  init(data) {
    this.ws = data.ws;
    this._slideIndex = 0;
    this._slideObjs  = [];
    this._advancing  = false;
    this._inSelection = false;
  }

  create() {
    // Dark atmospheric background
    this.add.rectangle(CX, H / 2, W, H, 0x0a0804);
    this._drawAtmosphere();

    // Click / any key advances
    this.input.on("pointerdown", () => this._advance());
    this.input.keyboard.on("keydown", () => this._advance());

    // WS: if server already past side_selection, skip intro
    if (this.ws) {
      this._boardStateHandler = d => {
        if (d.phase !== "side_selection") {
          this._goToGame(d);
        }
      };
      this.ws.on("board_state", this._boardStateHandler);
    }


    this._showSlide(0);
  }

  _drawAtmosphere() {
    const g = this.add.graphics();
    // Scattered dust/noise
    for (let i = 0; i < 120; i++) {
      const x = Phaser.Math.Between(0, W);
      const y = Phaser.Math.Between(0, H);
      const a = Phaser.Math.FloatBetween(0.04, 0.18);
      g.fillStyle(0x5a3a10, a);
      g.fillRect(x, y, Phaser.Math.Between(1, 3), Phaser.Math.Between(1, 3));
    }
    // Horizon line
    g.lineStyle(1, 0x3a2010, 0.4);
    g.strokeLineShape(new Phaser.Geom.Line(0, H * 0.68, W, H * 0.68));
  }

  // ─── Slide display ─────────────────────────────────────────────────────────

  _showSlide(index) {
    if (index >= SLIDES.length) {
      this._showSideSelection();
      return;
    }

    const slide = SLIDES[index];
    this._clearSlide();

    const objs = [];

    // Slide counter dots
    const dotY = 42;
    SLIDES.forEach((_, i) => {
      const dx = CX + (i - (SLIDES.length - 1) / 2) * 16;
      const dot = this.add.graphics();
      dot.fillStyle(i === index ? 0xd4a030 : 0x3a2810, 1);
      dot.fillCircle(dx, dotY, i === index ? 4 : 3);
      objs.push(dot);
    });

    // Year / chapter title
    const yearText = this.add.text(CX, 75, slide.year, {
      fontFamily: "serif",
      fontSize: "15px",
      fontStyle: "italic",
      color: "#d4a030",
      letterSpacing: 3,
      align: "center",
    }).setOrigin(0.5).setAlpha(0);
    objs.push(yearText);

    // Place subtitle
    if (slide.place) {
      const placeText = this.add.text(CX, 98, slide.place, {
        fontFamily: "monospace",
        fontSize: "11px",
        color: "#8a7060",
        letterSpacing: 2,
        align: "center",
      }).setOrigin(0.5).setAlpha(0);
      objs.push(placeText);
      this.tweens.add({ targets: placeText, alpha: 1, delay: 600, duration: 800 });
    }

    // Separator
    const sep = this.add.graphics().setAlpha(0);
    sep.lineStyle(1, 0x5a3a10, 0.8);
    sep.strokeLineShape(new Phaser.Geom.Line(CX - 60, 115, CX + 60, 115));
    objs.push(sep);
    this.tweens.add({ targets: sep, alpha: 1, delay: 300, duration: 600 });

    // Body text with typewriter effect
    const bodyText = this.add.text(CX, 155, "", {
      fontFamily: "serif",
      fontSize: "15px",
      color: "#f0e0c0",
      align: "center",
      lineSpacing: 8,
      wordWrap: { width: W - 100 },
    }).setOrigin(0.5, 0);
    objs.push(bodyText);

    // "Tap to continue" hint
    const hint = this.add.text(CX, H - 55, "tap to continue  ›", {
      fontFamily: "monospace",
      fontSize: "11px",
      color: "#5a3a10",
    }).setOrigin(0.5).setAlpha(0);
    objs.push(hint);

    // Fade in title, then typewrite body
    this.tweens.add({ targets: yearText, alpha: 1, delay: 0, duration: 700 });
    this._typewrite(bodyText, slide.body, 18, () => {
      this.tweens.add({
        targets: hint, alpha: 1, duration: 600,
        yoyo: true, repeat: -1, ease: "Sine.easeInOut",
      });
    });

    this._slideObjs = objs;
  }

  _typewrite(textObj, fullText, speed, onDone) {
    let i = 0;
    const timer = this.time.addEvent({
      delay: speed,
      repeat: fullText.length - 1,
      callback: () => {
        i++;
        textObj.setText(fullText.slice(0, i));
        if (i >= fullText.length && onDone) onDone();
      },
    });
    this._activeTimer = timer;
    // Store full text so a tap skips to the end
    textObj._fullText = fullText;
    this._currentBodyObj = textObj;
  }

  _advance() {
    if (this._advancing || this._inSelection) return;

    // If still typing — skip to end first tap, advance on second
    if (this._currentBodyObj && this._currentBodyObj.text !== this._currentBodyObj._fullText) {
      this._activeTimer?.remove();
      this._currentBodyObj.setText(this._currentBodyObj._fullText);
      this._currentBodyObj = null;
      return;
    }

    this._advancing = true;
    this._slideIndex++;
    this._fadeOutSlide(() => {
      this._advancing = false;
      this._showSlide(this._slideIndex);
    });
  }

  _clearSlide() {
    this._slideObjs.forEach(o => o.destroy());
    this._slideObjs = [];
    this._activeTimer?.remove();
    this._currentBodyObj = null;
  }

  _fadeOutSlide(onDone) {
    if (!this._slideObjs.length) { onDone?.(); return; }
    this.tweens.add({
      targets: this._slideObjs,
      alpha: 0,
      duration: 350,
      onComplete: () => { this._clearSlide(); onDone?.(); },
    });
  }

  // ─── Side selection ────────────────────────────────────────────────────────

  _showSideSelection() {
    this._inSelection = true;
    this._clearSlide();

    const objs = [];

    // Header
    objs.push(this.add.text(CX, 52, "THE GREAT EMU WAR", {
      fontFamily: "monospace", fontSize: "11px",
      color: "#5a3a10", letterSpacing: 4,
    }).setOrigin(0.5).setAlpha(0));

    objs.push(this.add.text(CX, 82, "CHOOSE YOUR SIDE", {
      fontFamily: "serif", fontSize: "22px", fontStyle: "bold",
      color: "#d4a030",
    }).setOrigin(0.5).setAlpha(0));

    objs.push(this.add.text(CX, 110,
      "Player 1 — hold up your side card, or tap below.", {
        fontFamily: "monospace", fontSize: "11px",
        color: "#8a7060", align: "center",
      }).setOrigin(0.5).setAlpha(0));

    // Separator
    const sep = this.add.graphics().setAlpha(0);
    sep.lineStyle(1, 0x3a2010, 0.8);
    sep.strokeLineShape(new Phaser.Geom.Line(40, 128, W - 40, 128));
    objs.push(sep);

    // ── Farmer card ─────────────────────────────────────────────────────
    const farmerCard = this._makeCard(
      W * 0.25, H / 2 + 20,
      "OLD MICK'S SIDE",
      "FARMER",
      "#d4a030",
      0x4a2208,
      0xb03030,
      [
        "Protect the paddocks.",
        "Hold the fence line.",
        "Find the Nest.",
        "",
        "Two riflemen.",
        "One stubborn farmer.",
        "Forty years of dirt.",
      ]
    );
    farmerCard.on("pointerdown", () => this._chooseSide("farmer"));
    objs.push(farmerCard);

    // ── Emu card ────────────────────────────────────────────────────────
    const emuCard = this._makeCard(
      W * 0.75, H / 2 + 20,
      "THE MOB'S SIDE",
      "EMU",
      "#6aaa50",
      0x0a2a14,
      0x30a060,
      [
        "Raid the wheat.",
        "Breach the fence.",
        "Find the Homestead.",
        "",
        "Two mobs.",
        "One Cassowary.",
        "Twenty thousand strong.",
      ]
    );
    emuCard.on("pointerdown", () => this._chooseSide("emu"));
    objs.push(emuCard);

    // ArUco hint
    objs.push(this.add.text(CX, H - 52,
      "Camera mode: hold up marker 20 (Farmer) or marker 21 (Emu)", {
        fontFamily: "monospace", fontSize: "9px",
        color: "#3a2810", align: "center",
      }).setOrigin(0.5).setAlpha(0));

    // Fade everything in
    this.tweens.add({
      targets: objs,
      alpha: 1,
      duration: 700,
      delay: this.tweens.stagger(80),
    });

    this._slideObjs = objs;
  }

  _makeCard(x, y, title, tag, titleColor, bgColor, rimColor, bullets) {
    const cardW = W * 0.42, cardH = 340, r = 10;

    const container = this.add.container(x, y).setAlpha(0);

    const bg = this.add.graphics();
    bg.fillStyle(bgColor, 0.92);
    bg.fillRoundedRect(-cardW/2, -cardH/2, cardW, cardH, r);
    bg.lineStyle(2, rimColor, 0.85);
    bg.strokeRoundedRect(-cardW/2, -cardH/2, cardW, cardH, r);
    container.add(bg);

    // Tag
    const tagTxt = this.add.text(0, -cardH/2 + 22, tag, {
      fontFamily: "monospace", fontSize: "9px",
      color: titleColor, letterSpacing: 3,
    }).setOrigin(0.5);
    container.add(tagTxt);

    // Title
    const titleTxt = this.add.text(0, -cardH/2 + 45, title, {
      fontFamily: "serif", fontSize: "15px", fontStyle: "bold",
      color: titleColor, align: "center", wordWrap: { width: cardW - 24 },
    }).setOrigin(0.5);
    container.add(titleTxt);

    // Divider
    const div = this.add.graphics();
    div.lineStyle(1, rimColor, 0.4);
    div.strokeLineShape(new Phaser.Geom.Line(-cardW/2 + 16, -cardH/2 + 66, cardW/2 - 16, -cardH/2 + 66));
    container.add(div);

    // Bullet points
    bullets.forEach((line, i) => {
      const bt = this.add.text(0, -cardH/2 + 85 + i * 24, line, {
        fontFamily: "serif", fontSize: "13px",
        color: "#f0e0c0", align: "center",
        alpha: line === "" ? 0 : 0.85,
      }).setOrigin(0.5);
      container.add(bt);
    });

    // CTA
    const cta = this.add.text(0, cardH/2 - 28, "[ TAP TO CHOOSE ]", {
      fontFamily: "monospace", fontSize: "10px",
      color: titleColor, letterSpacing: 1,
    }).setOrigin(0.5);
    container.add(cta);
    this.tweens.add({
      targets: cta, alpha: 0.3, yoyo: true, repeat: -1,
      duration: 900, ease: "Sine.easeInOut",
    });

    // Make interactive
    const hitArea = this.add.rectangle(0, 0, cardW, cardH, 0x000000, 0)
      .setInteractive({ useHandCursor: true });
    container.add(hitArea);

    // Hover glow
    hitArea.on("pointerover", () => {
      bg.clear();
      bg.fillStyle(bgColor, 1);
      bg.fillRoundedRect(-cardW/2, -cardH/2, cardW, cardH, r);
      bg.lineStyle(2.5, rimColor, 1);
      bg.strokeRoundedRect(-cardW/2, -cardH/2, cardW, cardH, r);
    });
    hitArea.on("pointerout", () => {
      bg.clear();
      bg.fillStyle(bgColor, 0.92);
      bg.fillRoundedRect(-cardW/2, -cardH/2, cardW, cardH, r);
      bg.lineStyle(2, rimColor, 0.85);
      bg.strokeRoundedRect(-cardW/2, -cardH/2, cardW, cardH, r);
    });

    return hitArea;
  }

  _goToGame(initialState) {
    if (this.ws && this._boardStateHandler) {
      this.ws.off("board_state", this._boardStateHandler);
      this._boardStateHandler = null;
    }
    this.cameras.main.fadeOut(400, 10, 8, 4);
    this.cameras.main.once("camerafadeoutcomplete", () => {
      this.scene.start("Game", { ws: this.ws, initialState });
    });
  }

  _chooseSide(side) {
    if (!this._inSelection) return;
    this._inSelection = false;

    // Send to server
    this.ws?.send("choose_side", { side });

    const name  = side === "farmer" ? "OLD MICK'S SIDE" : "THE MOB'S SIDE";
    const color = side === "farmer" ? "#d4a030" : "#6aaa50";

    // Confirmation flash
    this._fadeOutSlide(() => {
      const confirm = this.add.text(CX, H / 2 - 30, "PLAYER 1:", {
        fontFamily: "monospace", fontSize: "13px",
        color: "#8a7060", letterSpacing: 3,
      }).setOrigin(0.5);

      const choice = this.add.text(CX, H / 2 + 10, name, {
        fontFamily: "serif", fontSize: "26px", fontStyle: "bold",
        color, stroke: "#000000", strokeThickness: 3,
      }).setOrigin(0.5).setAlpha(0);

      this.tweens.add({ targets: choice, alpha: 1, duration: 500 });

      const sub = this.add.text(CX, H / 2 + 54,
        "Player 2 takes the other side.\nGame begins…", {
          fontFamily: "serif", fontSize: "14px",
          color: "#c8a878", align: "center",
        }).setOrigin(0.5).setAlpha(0);
      this.tweens.add({ targets: sub, alpha: 1, delay: 600, duration: 600 });

      // Wait for server's board_state confirming phase change, or timeout
      this.time.delayedCall(2200, () => {
        // If WS sent us a state already, _goToGame was already called;
        // the delayedCall fires anyway but _inSelection guard above prevents double-fire.
        // Without WS, transition manually.
        if (!this.ws) {
          this._goToGame(null);
        }
      });
    });
  }
}
