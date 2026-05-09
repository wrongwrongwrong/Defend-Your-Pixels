import { CANVAS_W, CANVAS_H, COLORS, GRID_SIZE } from "../constants.js";

const W = CANVAS_W, H = CANVAS_H, CX = W / 2;

// ─── Mini-board constants ─────────────────────────────────────────────────────
const MC  = 28;              // mini cell px
const MS  = GRID_SIZE * MC;  // board size (336)
const MX  = (W - MS) / 2;   // board left edge (182)
const MY  = 350;             // board top edge

const P_COL = {
  1: { base: 0x4a2208, active: 0xd4a828, token: 0xe87030, rim: "#d4a030" },
  2: { base: 0x0a2a14, active: 0x4ea044, token: 0x50c060, rim: "#6aaa50" },
};

// ─── Tutorial step definitions ────────────────────────────────────────────────
const STEPS = [
  // ── HQ placement ──────────────────────────────────────────────────────────
  { id: "hq_p2_away", phase: "hq",
    title: "SETTING HEADQUARTERS",
    body:  "Player 2 — look away from the screen.\n\nPlayer 1: place your HQ marker secretly\non any cell in your gold territory.\nOnce detected, remove the marker.",
    advance: "hq_1", showBoard: false },

  { id: "hq_p1_away", phase: "hq",
    title: "PLAYER 1 HQ SET  ✓",
    body:  "Player 1 — now look away.\n\nPlayer 2: place your HQ marker secretly\non any cell in your green territory.\nOnce detected, remove the marker.",
    advance: "hq_2", showBoard: false },

  { id: "hq_done", phase: "hq",
    title: "BOTH HEADQUARTERS LOCKED",
    body:  "Both players return to the table.\n\nNeither side knows where the other's\nheadquarters is hidden.\nIf the enemy finds it — the game ends.",
    advance: "tap", showBoard: false },

  // ── Player 1 tutorial ─────────────────────────────────────────────────────
  { id: "p1_intro", phase: "p1", player: 1,
    title: "PLAYER 1 — PLACE YOUR UNITS",
    body:  "You command the gold territory.\nYou have two attack tokens and one defense token.\nFollow the steps below.",
    advance: "tap", showBoard: true },

  { id: "p1_atk_a", phase: "p1", player: 1,
    title: "PLACE ATTACK A",
    body:  "Put your Attack A marker anywhere\nin the gold territory.",
    tokenKey: "p1_attack_a", advance: "placed", showBoard: true },

  { id: "p1_atk_a_h", phase: "p1", player: 1,
    title: "AIM LEFT OR RIGHT  ←→",
    body:  "Rotate the marker so it points\nhorizontally along a row.",
    tokenKey: "p1_attack_a", targetDir: "horizontal",
    advance: "direction", showBoard: true, showRay: true },

  { id: "p1_atk_a_v", phase: "p1", player: 1,
    title: "AIM UP OR DOWN  ↑↓",
    body:  "Now rotate to point vertically\nalong a column.",
    tokenKey: "p1_attack_a", targetDir: "vertical",
    advance: "direction", showBoard: true, showRay: true },

  { id: "p1_atk_b", phase: "p1", player: 1,
    title: "PLACE ATTACK B",
    body:  "Place your second Attack marker\nanywhere in the gold territory.",
    tokenKey: "p1_attack_b", advance: "placed", showBoard: true },

  { id: "p1_atk_b_h", phase: "p1", player: 1,
    title: "AIM LEFT OR RIGHT  ←→",
    body:  "Rotate Attack B horizontally.",
    tokenKey: "p1_attack_b", targetDir: "horizontal",
    advance: "direction", showBoard: true, showRay: true },

  { id: "p1_atk_b_v", phase: "p1", player: 1,
    title: "AIM UP OR DOWN  ↑↓",
    body:  "Rotate Attack B vertically.",
    tokenKey: "p1_attack_b", targetDir: "vertical",
    advance: "direction", showBoard: true, showRay: true },

  { id: "p1_def", phase: "p1", player: 1,
    title: "PLACE YOUR DEFENSE",
    body:  "Place your Defense marker in your territory.\nIt shields everything around it — attacks that\npass through the zone are absorbed.",
    tokenKey: "p1_defense", advance: "placed",
    showBoard: true, showDefenseOverlay: true },

  // ── Player 2 tutorial ─────────────────────────────────────────────────────
  { id: "p2_intro", phase: "p2", player: 2,
    title: "PLAYER 2 — PLACE YOUR UNITS",
    body:  "You command the green territory.\nSame drill — two attacks, one defense.",
    advance: "tap", showBoard: true },

  { id: "p2_atk_a", phase: "p2", player: 2,
    title: "PLACE ATTACK A",
    body:  "Put your Attack A marker anywhere\nin the green territory.",
    tokenKey: "p2_attack_a", advance: "placed", showBoard: true },

  { id: "p2_atk_a_h", phase: "p2", player: 2,
    title: "AIM LEFT OR RIGHT  ←→",
    body:  "Rotate the marker horizontally.",
    tokenKey: "p2_attack_a", targetDir: "horizontal",
    advance: "direction", showBoard: true, showRay: true },

  { id: "p2_atk_a_v", phase: "p2", player: 2,
    title: "AIM UP OR DOWN  ↑↓",
    body:  "Rotate to point vertically.",
    tokenKey: "p2_attack_a", targetDir: "vertical",
    advance: "direction", showBoard: true, showRay: true },

  { id: "p2_atk_b", phase: "p2", player: 2,
    title: "PLACE ATTACK B",
    body:  "Place your second Attack marker\nin the green territory.",
    tokenKey: "p2_attack_b", advance: "placed", showBoard: true },

  { id: "p2_atk_b_h", phase: "p2", player: 2,
    title: "AIM LEFT OR RIGHT  ←→",
    body:  "Rotate Attack B horizontally.",
    tokenKey: "p2_attack_b", targetDir: "horizontal",
    advance: "direction", showBoard: true, showRay: true },

  { id: "p2_atk_b_v", phase: "p2", player: 2,
    title: "AIM UP OR DOWN  ↑↓",
    body:  "Rotate Attack B vertically.",
    tokenKey: "p2_attack_b", targetDir: "vertical",
    advance: "direction", showBoard: true, showRay: true },

  { id: "p2_def", phase: "p2", player: 2,
    title: "PLACE YOUR DEFENSE",
    body:  "Place your Defense marker in your territory.\nThe shield zone will appear on-screen.",
    tokenKey: "p2_defense", advance: "placed",
    showBoard: true, showDefenseOverlay: true },

  // ── Cube introduction ──────────────────────────────────────────────────────
  { id: "cube", phase: "cube",
    title: "THE TURN CUBE",
    body:  "One cube controls the flow of play.\n\n▸  Player 1 face  →  Player 1 moves tokens\n▸  Player 2 face  →  Player 2 moves tokens\n▸  Resolve face   →  Both attacks fire\n\nFlip it at the start of each turn.\nThe game begins now.",
    advance: "tap", showBoard: false },
];

// ─── Scene ────────────────────────────────────────────────────────────────────

export class TutorialScene extends Phaser.Scene {
  constructor() { super("Tutorial"); }

  init(data) {
    this.ws          = data.ws;
    this._tokens     = {};
    this._stepIdx    = 0;
    this._stepObjs   = [];
    this._boardGfx   = null;
    this._advancing  = false;
    this._dirPending = false;
    this._hqDone     = { 1: false, 2: false };
    this._dirFeedback = null;
    this._wsHandlers  = {};

    // Seed token state from initial board_state if provided
    if (data.initialState?.tokens) {
      this._tokens = { ...data.initialState.tokens };
    }
  }

  create() {
    // Background
    this.add.rectangle(CX, H / 2, W, H, 0x0a0804);
    this._drawAtmosphere();

    // Board graphics layer — redrawn on each update
    this._boardGfx = this.add.graphics();

    this._bindWS();
    this._showStep(0);
  }

  // ─── Atmosphere ────────────────────────────────────────────────────────────

  _drawAtmosphere() {
    const g = this.add.graphics();
    for (let i = 0; i < 80; i++) {
      g.fillStyle(0x5a3a10, Phaser.Math.FloatBetween(0.03, 0.12));
      g.fillRect(
        Phaser.Math.Between(0, W), Phaser.Math.Between(0, H),
        Phaser.Math.Between(1, 3), Phaser.Math.Between(1, 3)
      );
    }
  }

  // ─── WebSocket ─────────────────────────────────────────────────────────────

  _bindWS() {
    if (!this.ws) return;

    const onMarker = d => {
      if (d.tokens) Object.assign(this._tokens, d.tokens);
      this._drawBoard();
      this._checkAutoAdvance();
    };

    const onBoard = d => {
      if (d.tokens) this._tokens = { ...d.tokens };
      this._drawBoard();
      this._checkAutoAdvance();
      // If server jumped to planning already, go straight to game
      if (d.phase === "planning") this._exitToGame(d);
    };

    const onHQ = d => {
      const pid = d.player;
      this._hqDone[pid] = true;
      const step = STEPS[this._stepIdx];
      if (step?.advance === `hq_${pid}`) this._advance();
    };

    this.ws.on("marker_update", onMarker);
    this.ws.on("board_state",   onBoard);
    this.ws.on("hq_confirmed",  onHQ);

    this._wsHandlers = { onMarker, onBoard, onHQ };
  }

  _unbindWS() {
    if (!this.ws) return;
    const { onMarker, onBoard, onHQ } = this._wsHandlers;
    this.ws.off("marker_update", onMarker);
    this.ws.off("board_state",   onBoard);
    this.ws.off("hq_confirmed",  onHQ);
  }

  // ─── Mini-board rendering ──────────────────────────────────────────────────

  _drawBoard() {
    const g = this._boardGfx;
    g.clear();

    const step = STEPS[this._stepIdx];
    if (!step?.showBoard) return;

    // Territory fill — anti-diagonal: P1 lower-right (col+row >= 11), P2 upper-left
    for (let col = 0; col < GRID_SIZE; col++) {
      for (let row = 0; row < GRID_SIZE; row++) {
        const isP1 = (col + row) >= GRID_SIZE - 1;
        g.fillStyle(isP1 ? 0xb85024 : 0x6a8c28, 1);
        g.fillRect(MX + col * MC, MY + row * MC, MC, MC);
      }
    }

    // Grid lines — faint guidance only
    g.lineStyle(1, 0x000000, 0.10);
    for (let i = 0; i <= GRID_SIZE; i++) {
      g.strokeLineShape(new Phaser.Geom.Line(MX + i * MC, MY, MX + i * MC, MY + MS));
      g.strokeLineShape(new Phaser.Geom.Line(MX, MY + i * MC, MX + MS, MY + i * MC));
    }

    // Fence along anti-diagonal (top-right → bottom-left)
    g.lineStyle(2, 0x7a3c14, 0.85);
    g.strokeLineShape(new Phaser.Geom.Line(MX + MS, MY, MX, MY + MS));
    for (let i = 0; i <= GRID_SIZE; i++) {
      const fx = MX + MS - i * MC, fy = MY + i * MC;
      g.fillStyle(0x7a3c14, 1);
      g.fillRect(fx - 2, fy - 4, 3, 8);
    }

    // Defense shield overlay
    if (step.showDefenseOverlay) {
      const def = this._tokens[step.tokenKey];
      if (def && def.col >= 0) {
        for (let dc = -2; dc <= 2; dc++) {
          for (let dr = -2; dr <= 2; dr++) {
            const c = def.col + dc, r = def.row + dr;
            if (c < 0 || r < 0 || c >= GRID_SIZE || r >= GRID_SIZE) continue;
            const dist = Math.max(Math.abs(dc), Math.abs(dr));
            const alpha = dist === 0 ? 0.55 : dist === 1 ? 0.28 : 0.1;
            g.fillStyle(COLORS.defenseZone, alpha);
            g.fillRect(MX + c * MC + 1, MY + r * MC + 1, MC - 2, MC - 2);
          }
        }
      }
    }

    // Ray overlay
    if (step.showRay) {
      const tk = this._tokens[step.tokenKey];
      if (tk && tk.col >= 0 && tk.direction) {
        this._drawRay(g, tk.col, tk.row, tk.direction);
      }
    }

    // All token dots
    for (const [key, tk] of Object.entries(this._tokens)) {
      if (tk.col < 0) continue;
      const col = P_COL[tk.player];
      const isActive = key === step.tokenKey;
      const px = MX + tk.col * MC + MC / 2;
      const py = MY + tk.row * MC + MC / 2;
      const r  = MC * 0.36;

      // Pulse ring for the step's active token
      if (isActive) {
        g.lineStyle(2, 0xffffff, 0.5);
        g.strokeCircle(px, py, r + 4);
      }

      g.fillStyle(col.token, 1);
      g.fillCircle(px, py, r);

      // Direction arrow
      if (tk.direction) {
        const angles = { horizontal: 0, vertical: Math.PI / 2, diagonal: Math.PI / 4 };
        const a = angles[tk.direction] ?? 0;
        const len = r + 7;
        g.lineStyle(2, 0xffffff, 0.85);
        g.strokeLineShape(new Phaser.Geom.Line(
          px, py,
          px + Math.cos(a) * len, py + Math.sin(a) * len
        ));
        g.strokeLineShape(new Phaser.Geom.Line(
          px, py,
          px - Math.cos(a) * len, py - Math.sin(a) * len
        ));
      }
    }
  }

  _drawRay(g, col, row, direction) {
    const PAIRS = {
      horizontal: [[1, 0], [-1, 0]],
      vertical:   [[0, 1], [0, -1]],
      diagonal:   [[1, -1], [-1, 1]],
    };
    const pairs = PAIRS[direction] ?? [[1, 0]];

    for (const [dc, dr] of pairs) {
      let c = col + dc, r = row + dr;
      while (c >= 0 && r >= 0 && c < GRID_SIZE && r < GRID_SIZE) {
        g.fillStyle(0xe8c030, 0.18);
        g.fillRect(MX + c * MC + 1, MY + r * MC + 1, MC - 2, MC - 2);
        c += dc; r += dr;
      }
    }
  }

  // ─── Step display ──────────────────────────────────────────────────────────

  _clearStep() {
    this._stepObjs.forEach(o => o?.destroy());
    this._stepObjs   = [];
    this._dirFeedback = null;
  }

  _showStep(idx) {
    if (idx >= STEPS.length) { this._completeTutorial(); return; }
    this._stepIdx = idx;
    const step = STEPS[idx];
    this._drawBoard();

    const objs = [];

    // ── Progress dots ──────────────────────────────────────────────────────
    STEPS.forEach((_, i) => {
      const dx = CX + (i - (STEPS.length - 1) / 2) * 8;
      const dot = this.add.graphics();
      const active = i === idx;
      dot.fillStyle(active ? 0xd4a030 : (i < idx ? 0x4a3010 : 0x221508), 1);
      dot.fillCircle(dx, 20, active ? 3.5 : 2);
      objs.push(dot);
    });

    // ── Phase label ─────────────────────────────────────────────────────────
    const phaseLabels = {
      hq:   "SETUP  ·  HEADQUARTERS",
      p1:   "TUTORIAL  ·  PLAYER 1",
      p2:   "TUTORIAL  ·  PLAYER 2",
      cube: "SETUP COMPLETE",
    };
    const phLabel = this.add.text(CX, 38, phaseLabels[step.phase] ?? "", {
      fontFamily: "monospace", fontSize: "10px",
      color: "#5a3a10", letterSpacing: 3,
    }).setOrigin(0.5).setAlpha(0);
    objs.push(phLabel);
    this.tweens.add({ targets: phLabel, alpha: 1, duration: 500 });

    // ── Card ────────────────────────────────────────────────────────────────
    const cardH = step.showBoard ? 185 : 380;
    const card  = this.add.graphics().setAlpha(0);
    card.fillStyle(0x180e08, 0.96);
    card.fillRoundedRect(30, 54, W - 60, cardH, 10);
    card.lineStyle(1, 0x3a2810, 0.9);
    card.strokeRoundedRect(30, 54, W - 60, cardH, 10);
    objs.push(card);
    this.tweens.add({ targets: card, alpha: 1, delay: 80, duration: 400 });

    // ── Title ───────────────────────────────────────────────────────────────
    const titleColor = step.player === 2 ? "#6aaa50" : "#d4a030";
    const titleObj = this.add.text(CX, 88, step.title, {
      fontFamily: "serif", fontSize: "17px", fontStyle: "bold",
      color: titleColor, align: "center",
    }).setOrigin(0.5).setAlpha(0);
    objs.push(titleObj);
    this.tweens.add({ targets: titleObj, alpha: 1, delay: 150, duration: 500 });

    // ── Separator ───────────────────────────────────────────────────────────
    const sep = this.add.graphics().setAlpha(0);
    sep.lineStyle(1, 0x3a2010, 0.6);
    sep.strokeLineShape(new Phaser.Geom.Line(CX - 90, 110, CX + 90, 110));
    objs.push(sep);
    this.tweens.add({ targets: sep, alpha: 1, delay: 200, duration: 400 });

    // ── Body ────────────────────────────────────────────────────────────────
    const bodyObj = this.add.text(CX, 122, step.body, {
      fontFamily: "serif", fontSize: "13px",
      color: "#f0e0c0", align: "center",
      lineSpacing: 5, wordWrap: { width: W - 100 },
    }).setOrigin(0.5, 0).setAlpha(0);
    objs.push(bodyObj);
    this.tweens.add({ targets: bodyObj, alpha: 1, delay: 280, duration: 500 });

    // ── Direction target indicator ──────────────────────────────────────────
    if (step.targetDir) {
      const icons = { horizontal: "← →", vertical: "↑ ↓", diagonal: "↗ ↙" };
      const dirTarget = this.add.text(CX, 302, `TARGET: ${icons[step.targetDir]}`, {
        fontFamily: "monospace", fontSize: "18px",
        color: titleColor, letterSpacing: 5,
      }).setOrigin(0.5).setAlpha(0);
      objs.push(dirTarget);
      this.tweens.add({
        targets: dirTarget, alpha: 1, yoyo: true, repeat: -1,
        duration: 750, ease: "Sine.easeInOut", delay: 400,
      });

      // Live direction feedback (updated in _checkAutoAdvance)
      const fb = this.add.text(CX, 326, "waiting for rotation…", {
        fontFamily: "monospace", fontSize: "11px", color: "#3a2810",
      }).setOrigin(0.5);
      objs.push(fb);
      this._dirFeedback = fb;
    }

    // ── Tap-to-continue hint ────────────────────────────────────────────────
    if (step.advance === "tap") {
      const hint = this.add.text(CX, H - 44, "tap to continue  ›", {
        fontFamily: "monospace", fontSize: "11px", color: "#5a3a10",
      }).setOrigin(0.5).setAlpha(0);
      objs.push(hint);
      this.tweens.add({
        targets: hint, alpha: 1, yoyo: true, repeat: -1,
        duration: 900, ease: "Sine.easeInOut", delay: 700,
      });
      this.input.once("pointerdown", () => this._advance());
      this.input.keyboard.once("keydown", () => this._advance());
    }

    // ── Camera-waiting hint ─────────────────────────────────────────────────
    if (step.advance === "placed" || step.advance === "direction") {
      const msg = step.advance === "placed"
        ? "place the marker on the board…"
        : "rotate the marker to match the target…";
      const camHint = this.add.text(CX, H - 44, msg, {
        fontFamily: "monospace", fontSize: "10px", color: "#3a2810",
      }).setOrigin(0.5);
      objs.push(camHint);

      // Always allow tap as fallback (covers no-camera mode and testing)
      const tapFallback = this.add.text(CX, H - 28, "tap to skip  ›", {
        fontFamily: "monospace", fontSize: "9px", color: "#3a2810",
      }).setOrigin(0.5);
      objs.push(tapFallback);
      this.input.once("pointerdown", () => this._advance());
      this.input.keyboard.once("keydown", () => this._advance());
    }

    // ── HQ-waiting hint ─────────────────────────────────────────────────────
    if (step.advance === "hq_1" || step.advance === "hq_2") {
      const hint = this.add.text(CX, H - 44, "hold HQ marker over your territory…", {
        fontFamily: "monospace", fontSize: "10px", color: "#3a2810",
      }).setOrigin(0.5);
      objs.push(hint);

      // Always allow tap as fallback
      const tapFallback = this.add.text(CX, H - 28, "tap to skip  ›", {
        fontFamily: "monospace", fontSize: "9px", color: "#3a2810",
      }).setOrigin(0.5);
      objs.push(tapFallback);
      this.input.once("pointerdown", () => this._advance());
      this.input.keyboard.once("keydown", () => this._advance());
    }

    this._stepObjs = objs;
  }

  // ─── Advance logic ─────────────────────────────────────────────────────────

  _checkAutoAdvance() {
    if (this._advancing) return;
    const step = STEPS[this._stepIdx];
    if (!step) return;

    if (step.advance === "placed") {
      const tk = this._tokens[step.tokenKey];
      if (tk && tk.col >= 0) this._advance();

    } else if (step.advance === "direction") {
      const tk = this._tokens[step.tokenKey];
      if (!tk) return;

      // Update live feedback text
      if (this._dirFeedback) {
        if (tk.direction) {
          const match = tk.direction === step.targetDir;
          this._dirFeedback.setText(`detected: ${tk.direction.toUpperCase()}`);
          this._dirFeedback.setColor(match ? "#50c060" : "#8a7060");
        } else {
          this._dirFeedback.setText("waiting for rotation…");
          this._dirFeedback.setColor("#3a2810");
        }
      }

      // Advance when direction matches — short delay so they see the green flash
      if (tk.direction === step.targetDir && !this._dirPending) {
        this._dirPending = true;
        this.time.delayedCall(600, () => {
          this._dirPending = false;
          const s  = STEPS[this._stepIdx];
          const t2 = this._tokens[s?.tokenKey];
          if (t2?.direction === s?.targetDir) this._advance();
        });
      }
    }
  }

  _advance() {
    if (this._advancing) return;
    this._advancing = true;

    this.tweens.add({
      targets: this._stepObjs, alpha: 0, duration: 220,
      onComplete: () => {
        this._clearStep();
        this._advancing = false;
        const next = this._stepIdx + 1;
        if (next >= STEPS.length) {
          this._completeTutorial();
        } else {
          this._showStep(next);
        }
      },
    });
  }

  // ─── Completion ────────────────────────────────────────────────────────────

  _completeTutorial() {
    if (this.ws) {
      this.ws.send("tutorial_complete", {});
      // The onBoard handler will receive phase=planning and call _exitToGame(d)
      // with the full state. Add a 3s fallback in case the server is slow.
      this.time.delayedCall(3000, () => {
        if (this.scene.isActive("Tutorial")) this._exitToGame(null);
      });
    } else {
      this._exitToGame(null);
    }
  }

  _exitToGame(initialState) {
    this._unbindWS();
    this.cameras.main.fadeOut(500, 10, 8, 4);
    this.cameras.main.once("camerafadeoutcomplete", () => {
      this.scene.start("Game", { ws: this.ws, initialState });
    });
  }
}
