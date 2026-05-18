import { CANVAS_W, CANVAS_H, COLORS } from "../constants.js";
import { playBgm, playSfx } from "../audio.js";

const W = CANVAS_W, H = CANVAS_H;
const CX = W / 2;

// ─── Story slides (ported from prototype3) ─────────────────────────────────
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

// ─── Scene ─────────────────────────────────────────────────────────────────

export class IntroScene extends Phaser.Scene {
  constructor() { super("Intro"); }

  init(data) {
    this.ws           = data.ws;
    this._slideIndex  = 0;
    this._slideObjs   = [];
    this._advancing   = false;
    this._inModeSelection = false;
    this._inSelection = false;
    this._latestState = null;
    this._modeStatus  = null;
    this._selectionStatus = null;
  }

  create() {
    this.add.rectangle(CX, H / 2, W, H, 0x0a0804);
    this._drawAtmosphere();

    // First pointer/key kicks off BGM (browsers block autoplay before user input)
    const startAudio = () => {
      if (this._audioStarted) return;
      this._audioStarted = true;
      // Phaser's sound system can be locked until first gesture — unlock if so
      if (this.sound.locked) this.sound.unlock();
      playBgm(this, "bgm_outback");
    };

    this._pointerAdvanceHandler = () => {
      startAudio();
      if (this._canAdvanceSlides()) this._advance();
    };
    this._keyAdvanceHandler = () => {
      startAudio();
      if (this._canAdvanceSlides()) this._advance();
    };
    this.input.on("pointerdown", this._pointerAdvanceHandler);
    this.input.keyboard.on("keydown", this._keyAdvanceHandler);

    // If server is mid-game already, skip the intro on first state arrival
    if (this.ws) {
      this._stateHandler = (s) => {
        this._latestState = s;
        const setup = s?.setup || {};
        const phase = s?.phase;
        if (s?.phase === "game" || setup.side_selection_complete) {
          this._goToGame(s);
          return;
        }
        if (phase === "mode_select") {
          this._refreshModeStatus();
          return;
        }
        if ((s?.mode === "normal" || s?.mode === "tutorial") && !this._inSelection) {
          this._showSideSelection();
          return;
        }
        this._refreshSelectionStatus();
      };
      this.ws.on("state", this._stateHandler);
    }

    this._showSlide(0);
  }

  _canAdvanceSlides() {
    return !this._inModeSelection && !this._inSelection;
  }

  _drawAtmosphere() {
    const g = this.add.graphics();
    for (let i = 0; i < 120; i++) {
      const x = Phaser.Math.Between(0, W);
      const y = Phaser.Math.Between(0, H);
      const a = Phaser.Math.FloatBetween(0.04, 0.18);
      g.fillStyle(0x5a3a10, a);
      g.fillRect(x, y, Phaser.Math.Between(1, 3), Phaser.Math.Between(1, 3));
    }
    g.lineStyle(1, 0x3a2010, 0.4);
    g.strokeLineShape(new Phaser.Geom.Line(0, H * 0.68, W, H * 0.68));
  }

  // ─── Slide rendering ────────────────────────────────────────────────────

  _showSlide(index) {
    if (index >= SLIDES.length) {
      this._showModeSelection();
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

    const yearText = this.add.text(CX, 75, slide.year, {
      fontFamily: "serif", fontSize: "15px", fontStyle: "italic",
      color: "#d4a030", letterSpacing: 3, align: "center",
    }).setOrigin(0.5).setAlpha(0);
    objs.push(yearText);

    if (slide.place) {
      const placeText = this.add.text(CX, 98, slide.place, {
        fontFamily: "monospace", fontSize: "11px",
        color: "#8a7060", letterSpacing: 2, align: "center",
      }).setOrigin(0.5).setAlpha(0);
      objs.push(placeText);
      this.tweens.add({ targets: placeText, alpha: 1, delay: 600, duration: 800 });
    }

    const sep = this.add.graphics().setAlpha(0);
    sep.lineStyle(1, 0x5a3a10, 0.8);
    sep.strokeLineShape(new Phaser.Geom.Line(CX - 60, 115, CX + 60, 115));
    objs.push(sep);
    this.tweens.add({ targets: sep, alpha: 1, delay: 300, duration: 600 });

    const bodyText = this.add.text(CX, 155, "", {
      fontFamily: "serif", fontSize: "15px",
      color: "#f0e0c0", align: "center", lineSpacing: 8,
      wordWrap: { width: W - 100 },
    }).setOrigin(0.5, 0);
    objs.push(bodyText);

    const hint = this.add.text(CX, H - 55, "tap to continue  ›", {
      fontFamily: "monospace", fontSize: "11px", color: "#5a3a10",
    }).setOrigin(0.5).setAlpha(0);
    objs.push(hint);

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
    textObj._fullText = fullText;
    this._currentBodyObj = textObj;
  }

  _advance() {
    if (this._advancing || this._inModeSelection || this._inSelection) return;
    if (this._currentBodyObj && this._currentBodyObj.text !== this._currentBodyObj._fullText) {
      this._activeTimer?.remove();
      this._currentBodyObj.setText(this._currentBodyObj._fullText);
      this._currentBodyObj = null;
      return;
    }
    this._advancing = true;
    this._slideIndex++;
    playSfx(this, "sfx_page");
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
      targets: this._slideObjs, alpha: 0, duration: 350,
      onComplete: () => { this._clearSlide(); onDone?.(); },
    });
  }

  // ─── Mode selection ─────────────────────────────────────────────────────

  _showModeSelection() {
    this._inModeSelection = true;
    this._inSelection = false;
    this._clearSlide();
    const objs = [];

    objs.push(this.add.text(CX, 52, "THE GREAT EMU WAR", {
      fontFamily: "monospace", fontSize: "11px",
      color: "#5a3a10", letterSpacing: 4,
    }).setOrigin(0.5).setAlpha(0));

    objs.push(this.add.text(CX, 82, "CHOOSE YOUR MODE", {
      fontFamily: "serif", fontSize: "22px", fontStyle: "bold",
      color: "#d4a030",
    }).setOrigin(0.5).setAlpha(0));

    objs.push(this.add.text(CX, 110,
      "Tutorial runs once, then continues directly into the same live game.", {
        fontFamily: "monospace", fontSize: "11px",
        color: "#8a7060", align: "center",
      }).setOrigin(0.5).setAlpha(0));

    const sep = this.add.graphics().setAlpha(0);
    sep.lineStyle(1, 0x3a2010, 0.8);
    sep.strokeLineShape(new Phaser.Geom.Line(40, 128, W - 40, 128));
    objs.push(sep);

    const gameCard = this._makeCard(
      W * 0.25, H / 2 + 20,
      "GAME MODE", "LIVE",
      "#d4a030", 0x4a2208, 0xb03030,
      [
        "Start the normal live match.",
        "",
        "No guided prompts.",
        "Use the existing marker flow.",
        "",
        "Best for regular play.",
      ]);
    gameCard.hitArea.on("pointerdown", () => this._chooseMode("normal"));
    objs.push(gameCard);

    const tutorialCard = this._makeCard(
      W * 0.75, H / 2 + 20,
      "TUTORIAL MODE", "GUIDED",
      "#6aaa50", 0x0a2a14, 0x30a060,
      [
        "Play through guided setup.",
        "Learn HQ, turn, and token rules.",
        "",
        "Highlights teach each move.",
        "",
        "Ends by continuing this same match.",
      ]);
    tutorialCard.hitArea.on("pointerdown", () => this._chooseMode("tutorial"));
    objs.push(tutorialCard);

    this._modeStatus = this.add.text(CX, H - 52,
      "Choose a mode to begin.", {
        fontFamily: "monospace", fontSize: "10px",
        color: "#8a7060", align: "center",
        wordWrap: { width: W - 80 },
      }).setOrigin(0.5).setAlpha(0);
    objs.push(this._modeStatus);

    this.tweens.add({
      targets: objs, alpha: 1, duration: 700,
      delay: this.tweens.stagger(80),
    });

    this._slideObjs = objs;
    this._refreshModeStatus();
  }

  _refreshModeStatus() {
    if (!this._modeStatus) return;
    const phase = this._latestState?.phase;
    const mode = this._latestState?.mode;
    if (phase !== "mode_select") {
      this._modeStatus.setText("Mode locked. Preparing setup...").setColor("#d4a030");
      return;
    }
    if (mode === "normal" || mode === "tutorial") {
      this._modeStatus.setText("Mode locked. Preparing setup...").setColor("#d4a030");
      return;
    }
    this._modeStatus.setText("Choose a mode to begin.").setColor("#8a7060");
  }

  _chooseMode(mode) {
    if (!this._inModeSelection) return;
    this._modeStatus?.setText(mode === "tutorial"
      ? "Tutorial mode selected. Preparing guided setup..."
      : "Game mode selected. Preparing live setup...")
      .setColor("#d4a030");
    playSfx(this, "sfx_select");
    this.ws?.send("select_mode", { mode });
  }

  // ─── Side selection ─────────────────────────────────────────────────────

  _showSideSelection() {
    this._inModeSelection = false;
    this._inSelection = true;
    this._clearSlide();
    const objs = [];

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

    const sep = this.add.graphics().setAlpha(0);
    sep.lineStyle(1, 0x3a2010, 0.8);
    sep.strokeLineShape(new Phaser.Geom.Line(40, 128, W - 40, 128));
    objs.push(sep);

    const farmerCard = this._makeCard(
      W * 0.25, H / 2 + 20,
      "OLD MICK'S SIDE", "FARMER",
      "#d4a030", 0x4a2208, 0xb03030,
      [
        "Protect the paddocks.",
        "Hold the fence line.",
        "Find the Nest.",
        "",
        "Two riflemen.",
        "One stubborn farmer.",
        "Forty years of dirt.",
      ]);
    farmerCard.hitArea.on("pointerdown", () => this._chooseSide("old_mick"));
    objs.push(farmerCard);

    const emuCard = this._makeCard(
      W * 0.75, H / 2 + 20,
      "THE MOB'S SIDE", "EMU",
      "#6aaa50", 0x0a2a14, 0x30a060,
      [
        "Raid the wheat.",
        "Breach the fence.",
        "Find the Homestead.",
        "",
        "Two mobs.",
        "One Cassowary.",
        "Twenty thousand strong.",
      ]);
    emuCard.hitArea.on("pointerdown", () => this._chooseSide("mob"));
    objs.push(emuCard);

    objs.push(this.add.text(CX, H - 52,
      "Board scan must be ready before side selection can lock in.", {
        fontFamily: "monospace", fontSize: "9px",
        color: "#3a2810", align: "center",
      }).setOrigin(0.5).setAlpha(0));

    this._selectionStatus = this.add.text(CX, 136,
      "Waiting for a valid board scan.", {
        fontFamily: "monospace", fontSize: "10px",
        color: "#8a7060", align: "center",
        wordWrap: { width: W - 80 },
      }).setOrigin(0.5).setAlpha(0);
    objs.push(this._selectionStatus);

    this.tweens.add({
      targets: objs, alpha: 1, duration: 700,
      delay: this.tweens.stagger(80),
    });

    this._slideObjs = objs;
    this._refreshSelectionStatus();
  }

  _refreshSelectionStatus() {
    if (!this._selectionStatus) return;
    const setup = this._latestState?.setup || {};
    const ready = !!setup.board_scan_ready;
    const text = ready
      ? "Board scan ready. Choose who places the first hidden HQ."
      : (setup.status_message || "Waiting for a valid board scan.");
    this._selectionStatus
      .setText(text)
      .setColor(ready ? "#d4a030" : "#8a7060");
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

    container.add(this.add.text(0, -cardH/2 + 22, tag, {
      fontFamily: "monospace", fontSize: "9px",
      color: titleColor, letterSpacing: 3,
    }).setOrigin(0.5));

    container.add(this.add.text(0, -cardH/2 + 45, title, {
      fontFamily: "serif", fontSize: "15px", fontStyle: "bold",
      color: titleColor, align: "center", wordWrap: { width: cardW - 24 },
    }).setOrigin(0.5));

    const div = this.add.graphics();
    div.lineStyle(1, rimColor, 0.4);
    div.strokeLineShape(new Phaser.Geom.Line(
      -cardW/2 + 16, -cardH/2 + 66,
      cardW/2 - 16, -cardH/2 + 66));
    container.add(div);

    bullets.forEach((line, i) => {
      const bt = this.add.text(0, -cardH/2 + 85 + i * 24, line, {
        fontFamily: "serif", fontSize: "13px",
        color: "#f0e0c0", align: "center",
        alpha: line === "" ? 0 : 0.85,
      }).setOrigin(0.5);
      container.add(bt);
    });

    const cta = this.add.text(0, cardH/2 - 28, "[ TAP TO CHOOSE ]", {
      fontFamily: "monospace", fontSize: "10px",
      color: titleColor, letterSpacing: 1,
    }).setOrigin(0.5);
    container.add(cta);
    this.tweens.add({
      targets: cta, alpha: 0.3, yoyo: true, repeat: -1,
      duration: 900, ease: "Sine.easeInOut",
    });

    const hitArea = this.add.rectangle(0, 0, cardW, cardH, 0x000000, 0)
      .setInteractive({ useHandCursor: true });
    container.add(hitArea);

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

    container.hitArea = hitArea;
    return container;
  }

  _goToGame(initialState) {
    if (this.ws && this._stateHandler) {
      this.ws.off("state", this._stateHandler);
      this._stateHandler = null;
    }
    this.cameras.main.fadeOut(400, 10, 8, 4);
    this.cameras.main.once("camerafadeoutcomplete", () => {
      this.scene.start("Game", { ws: this.ws, initialState });
    });
  }

  _chooseSide(side) {
    if (!this._inSelection) return;
    const boardReady = !!this._latestState?.setup?.board_scan_ready;
    if (!boardReady) {
      this._selectionStatus?.setText("Waiting for board scan before side selection can start.")
        .setColor("#d87850");
      return;
    }

    this._inSelection = false;

    playSfx(this, "sfx_select");

    this.ws?.send("choose_side", { first_player_side: side });

    const name  = side === "old_mick" ? "OLD MICK'S SIDE" : "THE MOB'S SIDE";
    const color = side === "old_mick" ? "#d4a030" : "#6aaa50";

    this._fadeOutSlide(() => {
      this.add.text(CX, H / 2 - 30, "PLAYER 1:", {
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

      this.time.delayedCall(2200, () => this._goToGame(null));
    });
  }
}
