/**
 * GameScene — board rendering + no-camera interactive gameplay.
 *
 * Two players pass the device. Tap cells to place / cycle tokens,
 * then tap END TURN to hand control to the other player.
 *
 * Phaser renders: board image, grid, terrain tiles, token sprites,
 * HQ sprites, attack rays, defence zones, HQ placement rings,
 * win overlay (board-centered), tutorial overlay,
 * token picker popup, end-turn button, turn indicator overlay.
 *
 * All panel / score / tier / log UI lives in HTML (ui.js).
 */

import {
  GRID_SIZE, CELL, BOARD_PX,
  BOARD_OFF_X, BOARD_OFF_Y,
  CANVAS_W, CANVAS_H,
  GRID_INSET_X, GRID_INSET_Y, GRID_DRAW_W, GRID_DRAW_H,
  COLORS, DIR_VEC, ARROW_CHAR,
  FONT_TITLE, FONT_LABEL, FONT_MONO,
} from "../constants.js";
import { playSfx, playBgm, toggleMute, isMuted } from "../audio.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function cellXY(col, row) {
  const cw = GRID_DRAW_W / GRID_SIZE;
  const ch = GRID_DRAW_H / GRID_SIZE;
  return {
    x: BOARD_OFF_X + GRID_INSET_X + col * cw + cw / 2,
    y: BOARD_OFF_Y + GRID_INSET_Y + row * ch + ch / 2,
  };
}

function isP1Cell(c, r)  { return c + r < 11; }
function isP2Cell(c, r)  { return c + r > 11; }
function isOnFence(c, r) { return c + r === 11; }
function colLabel(col)   { return String.fromCharCode(65 + col); }

function isWrongSideDir(side, dir) {
  if (!dir || !DIR_VEC[dir]) return false;
  const [dc, dr] = DIR_VEC[dir];
  if (side === "p1") return dc + dr <= 0;
  if (side === "p2") return dc + dr >= 0;
  return false;
}

function computeRay(startCol, startRow, dir, hardMap, softMap, attackerSide, destroyedMap, targetMap) {
  if (!dir || !DIR_VEC[dir]) return [];
  const [dc, dr] = DIR_VEC[dir];
  const isEnemy  = attackerSide === "p1" ? isP2Cell : isP1Cell;
  const cells    = [];
  let c = startCol + dc, r = startRow + dr;
  while (c >= 0 && c < GRID_SIZE && r >= 0 && r < GRID_SIZE) {
    const key = `${c},${r}`;
    if (hardMap[key])                        { cells.push({ col: c, row: r, type: "blocked" }); break; }
    if (softMap[key])                        { cells.push({ col: c, row: r, type: "soft"    }); break; }
    if (isEnemy(c, r) && targetMap[key] && !destroyedMap[key]) {
      cells.push({ col: c, row: r, type: "hit" });
      break;
    }
    cells.push({ col: c, row: r, type: "path" });
    c += dc; r += dr;
  }
  return cells;
}

function posLabel(tok) {
  if (!tok || tok.col == null) return "—";
  return `${colLabel(tok.col)}${tok.row + 1}`;
}

// ─── Idle Animation Helpers ───────────────────────────────────────────────────

function addAttackIdle(scene, image, posRef) {
  scene.time.addEvent({
    delay: 120,
    loop: true,
    callback: () => {
      if (!image.visible || posRef.x == null) return;
      image.x = posRef.x + Phaser.Math.Between(-1, 1);
      image.y = posRef.y + Phaser.Math.Between(0, 1);
    }
  });
}

// ─── Direction cycling tables ─────────────────────────────────────────────────

// P1 atk cycles towards enemy lower-right: E → SE → S → E
const P1_ATK_CYCLE = ["E", "SE", "S"];
// P2 atk cycles towards enemy upper-left: W → NW → N → W
const P2_ATK_CYCLE = ["W", "NW", "N"];

// Default placement directions
const DEFAULT_DIR = {
  p1: { atk_a: "E",  atk_b: "SE", def: null },
  p2: { atk_a: "W",  atk_b: "NW", def: null },
};

// ─── Scene ────────────────────────────────────────────────────────────────────

export class GameScene extends Phaser.Scene {
  constructor() { super("Game"); }

  init() {
    this.ws               = this.game.registry.get("ws") ?? null;
    this.gameState        = null;
    this._lastSeed        = null;
    this._nukeArmingSide  = null;
    this._prevWinner      = null;
    this._terrainSprites  = [];
    this._rayGfxPool      = [];   // recycled Graphics objects for ray animations
    this._pickerData      = null; // {container, col, row, side} when picker is open
    this._lastActiveSide  = null; // track turn changes
  }

  create() {
    this.boardGfx    = this.add.graphics().setDepth(0);
    this.resourceGfx = this.add.graphics().setDepth(1);
    this.dmgGfx      = this.add.graphics().setDepth(2);
    this.dynGfx      = this.add.graphics().setDepth(3);

    this._buildBoardImage();
    this._drawGridOnce();
    this._buildTokenSprites();
    this._buildHqSprites();
    this._buildWinOverlay();
    this._buildTutorialOverlay();
    this._buildEndTurnBtn();
    this._buildTurnOverlay();
    this._bindWS();

    this.input.on("pointerdown", this._handleBoardClick, this);

    this.input.keyboard.on("keydown-N", () => this.ws?.send("demo_next", {}));

    this.time.addEvent({ delay: 33, loop: true, callback: () => this._render() });

    // ── Nuke bridge: HTML card click → Phaser ────────────────────────────────
    window._nukeArm = (side) => {
      const s = this.gameState;
      if (!s || s.phase !== "game") return;
      const activeSide = s.battle?.active_side;
      if (activeSide !== side) return;
      const available = side === "p1" ? s.game?.nuke_available_p1 : s.game?.nuke_available_p2;
      if (!available) return;
      this._nukeArmingSide = side;
      // Brief visual feedback: flash the board border
      this.cameras.main.flash(200, 255, 140, 0, false);
    };
  }

  // ══════════════════════════════════════════════════════════════════════════════
  // Build
  // ══════════════════════════════════════════════════════════════════════════════

  _buildBoardImage() {
    this.add.image(BOARD_OFF_X, BOARD_OFF_Y, "board")
      .setOrigin(0, 0)
      .setDisplaySize(BOARD_PX, BOARD_PX)
      .setDepth(-1);
  }

  _drawGridOnce() {
    const g    = this.boardGfx;
    const cw   = GRID_DRAW_W / GRID_SIZE;
    const ch   = GRID_DRAW_H / GRID_SIZE;
    const x0   = BOARD_OFF_X + GRID_INSET_X;
    const y0   = BOARD_OFF_Y + GRID_INSET_Y;
    const x1   = x0 + GRID_DRAW_W;
    const y1   = y0 + GRID_DRAW_H;

    g.lineStyle(1, COLORS.gridLine, 0.20);
    for (let i = 0; i <= GRID_SIZE; i++) {
      g.strokeLineShape(new Phaser.Geom.Line(x0 + i * cw, y0, x0 + i * cw, y1));
      g.strokeLineShape(new Phaser.Geom.Line(x0, y0 + i * ch, x1, y0 + i * ch));
    }

    const labelStyle = { fontFamily: FONT_MONO, fontSize: "11px", color: "#c8a070" };
    for (let i = 0; i < GRID_SIZE; i++) {
      this.add.text(x0 + i * cw + cw / 2, y0 - 16, colLabel(i), labelStyle).setOrigin(0.5).setDepth(0);
    }
    for (let i = 0; i < GRID_SIZE; i++) {
      this.add.text(x0 - 18, y0 + i * ch + ch / 2, String(i + 1), labelStyle).setOrigin(0.5).setDepth(0);
    }
  }

  _buildTokenSprites() {
    const sz  = CELL * 0.88;
    const TEX = {
      p1_atk_a: "tok_mick_atk_a",
      p1_atk_b: "tok_mick_atk_b",
      p1_def:   "tok_mick_def",
      p2_atk_a: "tok_emu_atk_a",
      p2_atk_b: "tok_emu_atk_b",
      p2_def:   "tok_emu_def",
    };

    this.tokenSprites    = {};
    this.tokenBadges     = {};
    this.tokenArrows     = {};
    this.tokenWarnLabels = {};
    this.tokenIdlePos    = {};

    for (const [key, tex] of Object.entries(TEX)) {
      this.tokenSprites[key] = this.add.image(0, 0, tex)
        .setDisplaySize(sz, sz).setDepth(11).setVisible(false);

      if (key.endsWith("_a") || key.endsWith("_b")) {
        this.tokenBadges[key] = this.add.text(0, 0, key.endsWith("_a") ? "A" : "B", {
          fontFamily: FONT_MONO, fontSize: "12px", fontStyle: "bold",
          color: "#fff080", stroke: "#000000", strokeThickness: 3,
        }).setOrigin(0.5).setDepth(13).setVisible(false);

        this.tokenArrows[key] = this.add.text(0, 0, "→", {
          fontFamily: "monospace", fontSize: "20px",
          color: "#fff080", stroke: "#000000", strokeThickness: 3,
        }).setOrigin(0.5).setDepth(13).setVisible(false);
      }

      this.tokenWarnLabels[key] = this.add.text(0, 0, "", {
        fontFamily: FONT_LABEL, fontSize: "11px", fontStyle: "bold",
        color: "#ffffff", backgroundColor: "#cc0000",
        padding: { x: 5, y: 3 },
      }).setOrigin(0.5, 0).setDepth(20).setVisible(false);
    }

    // Apply aggressive idle animation to Mick's first rifleman (demo)
    this.tokenIdlePos["p1_atk_a"] = { x: 0, y: 0 };
    addAttackIdle(this, this.tokenSprites["p1_atk_a"], this.tokenIdlePos["p1_atk_a"]);
  }

  _buildHqSprites() {
    const sz   = CELL * 1.0;
    const make = (tex) => this.add.image(0, 0, tex)
      .setDisplaySize(sz, sz).setDepth(10).setVisible(false);
    this.hqSprites = {
      p1:      make("hq_grain_stash"),
      p1_dead: make("hq_grain_stash_dead"),
      p2:      make("hq_bird_council"),
      p2_dead: make("hq_bird_council_dead"),
    };
  }

  _buildWinOverlay() {
    const cx = CANVAS_W / 2;
    const cy = CANVAS_H / 2;

    this._winDimRect = this.add.rectangle(cx, cy, BOARD_PX, BOARD_PX, 0x000000, 0)
      .setDepth(39).setVisible(false);

    this.winContainer = this.add.container(cx, cy).setDepth(40).setVisible(false);

    const bg = this.add.rectangle(0, 0, 560, 160, 0x080502, 0.96)
      .setStrokeStyle(2, 0xd4a030, 1);

    this._winTitleTxt = this.add.text(0, -42, "", {
      fontFamily: FONT_TITLE, fontSize: "36px", fontStyle: "bold",
      color: "#ffe070", stroke: "#3a2010", strokeThickness: 4,
    }).setOrigin(0.5);

    this._winSubTxt = this.add.text(0, 8, "", {
      fontFamily: FONT_LABEL, fontSize: "15px",
      color: "#f0c080", align: "center", wordWrap: { width: 500 },
    }).setOrigin(0.5);

    this._winHintTxt = this.add.text(0, 54, "Press N to advance demo", {
      fontFamily: FONT_MONO, fontSize: "10px", color: "#6a5030",
    }).setOrigin(0.5);

    this._winHqLeft  = this.add.image(-220, 0, "hq_grain_stash").setDisplaySize(80, 80).setDepth(41);
    this._winHqRight = this.add.image( 220, 0, "hq_bird_council" ).setDisplaySize(80, 80).setDepth(41);

    this.winContainer.add([bg, this._winTitleTxt, this._winSubTxt, this._winHintTxt,
                           this._winHqLeft, this._winHqRight]);
  }

  _buildTutorialOverlay() {
    const cx   = CANVAS_W / 2;
    const topY = BOARD_OFF_Y + 80;

    this.tutorialContainer = this.add.container(cx, topY).setDepth(50).setVisible(false);

    const panelW = 550, panelH = 140;
    const bg = this.add.rectangle(0, 0, panelW, panelH, 0x1a1008, 0.95)
      .setStrokeStyle(2, 0xffd060);

    this._tutStepTxt = this.add.text(panelW / 2 - 12, -panelH / 2 + 12, "", {
      fontFamily: FONT_MONO, fontSize: "11px", color: "#8a7060",
    }).setOrigin(1, 0);

    this._tutTitleTxt = this.add.text(0, -panelH / 2 + 30, "", {
      fontFamily: FONT_TITLE, fontSize: "20px", fontStyle: "bold", color: "#ffd060",
    }).setOrigin(0.5, 0);

    this._tutTextTxt = this.add.text(0, -panelH / 2 + 65, "", {
      fontFamily: FONT_LABEL, fontSize: "14px", color: "#d0c0a0",
      align: "center", wordWrap: { width: panelW - 40 }, lineSpacing: 4,
    }).setOrigin(0.5, 0);

    this._tutHintTxt = this.add.text(0, panelH / 2 - 18, "Press SPACE or click to continue", {
      fontFamily: FONT_MONO, fontSize: "11px", color: "#7a6a50",
    }).setOrigin(0.5).setVisible(false);

    this.tutorialContainer.add([bg, this._tutStepTxt, this._tutTitleTxt, this._tutTextTxt, this._tutHintTxt]);
    this.tutHighlightGfx = this.add.graphics().setDepth(45);

    this.input.keyboard.on("keydown-SPACE", () => {
      const tut = this.gameState?.tutorial;
      if (tut?.active && tut?.needs_dismiss) this._sendTutorialDismiss();
    });

    this.tutorialContainer.setInteractive(
      new Phaser.Geom.Rectangle(-275, -70, 550, 140), Phaser.Geom.Rectangle.Contains);
    this.tutorialContainer.on("pointerdown", () => {
      const tut = this.gameState?.tutorial;
      if (tut?.active && tut?.needs_dismiss) this._sendTutorialDismiss();
    });
  }

  _sendTutorialDismiss() {
    if (this.ws) { this.ws.send("tutorial_dismiss", {}); playSfx(this, "sfx_select"); }
  }

  // ─── End Turn Button ─────────────────────────────────────────────────────────

  _buildEndTurnBtn() {
    const bx = CANVAS_W / 2;
    const by = CANVAS_H - 22;
    const bw = 200, bh = 36;

    // Background rectangle
    this._endTurnBg = this.add.rectangle(bx, by, bw, bh, 0x1a1208)
      .setDepth(60)
      .setStrokeStyle(2, 0xc8a030)
      .setVisible(false)
      .setInteractive({ useHandCursor: true });

    // Button text
    this._endTurnTxt = this.add.text(bx, by, "END TURN", {
      fontFamily: "'Press Start 2P'",
      fontSize: "9px",
      color: "#f0e060",
    }).setOrigin(0.5).setDepth(61).setVisible(false);

    // Hover effects
    this._endTurnBg.on("pointerover", () => {
      this._endTurnBg.setFillStyle(0x2e2010);
    });
    this._endTurnBg.on("pointerout", () => {
      this._endTurnBg.setFillStyle(0x1a1208);
    });
    this._endTurnBg.on("pointerdown", () => {
      this._endTurn();
    });
  }

  _updateEndTurnBtn() {
    const s = this.gameState;
    const activeSide = s?.battle?.active_side ?? null;
    const visible = !!s?.manual_controls && activeSide != null && s?.phase === "game";
    this._endTurnBg?.setVisible(visible);
    this._endTurnTxt?.setVisible(visible);
  }

  _endTurn() {
    const s = this.gameState;
    if (!s?.manual_controls || s.phase !== "game") return;
    const activeSide = s.battle?.active_side;
    if (!activeSide) return;
    const player = activeSide === "p1" ? 1 : 2;
    this.ws?.send("end_turn", { player });
    playSfx(this, "sfx_select");
  }

  // ─── Turn Indicator Overlay (pass-the-device) ────────────────────────────────

  _buildTurnOverlay() {
    const cx = CANVAS_W / 2;
    const cy = CANVAS_H / 2;

    this._turnOverlayContainer = this.add.container(cx, cy).setDepth(70).setVisible(false).setAlpha(0);

    // Semi-transparent dark background
    const bg = this.add.rectangle(0, 0, CANVAS_W, 200, 0x000000, 0.80);

    // Player name text (large)
    this._turnOverlayTitle = this.add.text(0, -38, "", {
      fontFamily: "'Press Start 2P'",
      fontSize: "22px",
      color: "#f0e060",
      stroke: "#1a0e00",
      strokeThickness: 4,
      align: "center",
    }).setOrigin(0.5);

    // Instruction text (smaller)
    this._turnOverlaySub = this.add.text(0, 18, "Arrange physical tokens and confirm with markers", {
      fontFamily: "'Press Start 2P'",
      fontSize: "7px",
      color: "#c8a070",
      align: "center",
    }).setOrigin(0.5);

    this._turnOverlayContainer.add([bg, this._turnOverlayTitle, this._turnOverlaySub]);
  }

  _showTurnOverlay(side) {
    const label = side === "p1" ? "PLAYER 1'S TURN" : "PLAYER 2'S TURN";
    const sub = this.gameState?.manual_controls
      ? "Click your side to place tokens, then press END TURN"
      : "Arrange physical tokens and confirm with markers";
    this._turnOverlayTitle.setText(label);
    this._turnOverlaySub.setText(sub);
    this._turnOverlayContainer.setVisible(true);

    // Kill any running tween on this target
    this.tweens.killTweensOf(this._turnOverlayContainer);

    // Fade in 300ms, hold, fade out 400ms — total 2500ms visible duration
    this.tweens.add({
      targets: this._turnOverlayContainer,
      alpha: 1,
      duration: 300,
      ease: "Linear",
      onComplete: () => {
        this.time.delayedCall(1800, () => {
          this.tweens.add({
            targets: this._turnOverlayContainer,
            alpha: 0,
            duration: 400,
            ease: "Linear",
            onComplete: () => {
              this._turnOverlayContainer.setVisible(false);
            },
          });
        });
      },
    });
  }

  // ─── Token Picker Popup ───────────────────────────────────────────────────────

  _showTokenPicker(side, col, row) {
    // Close any existing picker first
    this._hideTokenPicker();

    const s = this.gameState;
    if (!s) return;

    const { x: cx, y: cy } = cellXY(col, row);
    const cw = GRID_DRAW_W / GRID_SIZE;

    // Token definitions for each side
    const tokens = side === "p1"
      ? [
          { role: "def",   label: "FARMER"  },
          { role: "atk_a", label: "RIFLE A" },
          { role: "atk_b", label: "RIFLE B" },
        ]
      : [
          { role: "def",   label: "CASSOWARY" },
          { role: "atk_a", label: "EMU A"     },
          { role: "atk_b", label: "EMU B"     },
        ];

    const BTN_W = 150, BTN_H = 28, BTN_GAP = 4;
    const totalH = tokens.length * (BTN_H + BTN_GAP) + BTN_H + BTN_GAP; // tokens + CANCEL
    // Position popup above the cell, clamped to canvas
    let popX = cx;
    let popY = cy - cw * 0.5 - totalH / 2 - 8;
    // Clamp horizontally
    popX = Phaser.Math.Clamp(popX, BTN_W / 2 + 4, CANVAS_W - BTN_W / 2 - 4);
    // If would go off top, flip below
    if (popY - totalH / 2 < 10) {
      popY = cy + cw * 0.5 + totalH / 2 + 8;
    }

    const container = this.add.container(popX, popY).setDepth(80);
    const items = [];

    const allTokenSlots = { def: s[side]?.def, atk_a: s[side]?.atk_a, atk_b: s[side]?.atk_b };

    let offsetY = -(tokens.length * (BTN_H + BTN_GAP)) / 2;

    for (const tok of tokens) {
      const isPlaced = allTokenSlots[tok.role]?.col != null;
      const borderColor = isPlaced ? 0x4a8a30 : 0x8a6020;
      const btnBg = this.add.rectangle(0, offsetY, BTN_W, BTN_H, 0x1a1208)
        .setStrokeStyle(1.5, borderColor);
      const btnTxt = this.add.text(0, offsetY, tok.label, {
        fontFamily: "'Press Start 2P'",
        fontSize: "7px",
        color: isPlaced ? "#80d040" : "#d4a040",
      }).setOrigin(0.5);

      btnBg.setInteractive({ useHandCursor: true });
      btnBg.on("pointerover",  () => btnBg.setFillStyle(0x2e2010));
      btnBg.on("pointerout",   () => btnBg.setFillStyle(0x1a1208));

      const capturedRole = tok.role;
      const capturedSide = side;
      const capturedCol  = col;
      const capturedRow  = row;
      btnBg.on("pointerdown", (ptr) => {
        ptr.event?.stopPropagation?.();
        const dir = DEFAULT_DIR[capturedSide][capturedRole] ?? null;
        this.ws?.send("place_token", {
          side: capturedSide,
          role: capturedRole,
          col:  capturedCol,
          row:  capturedRow,
          direction: dir,
        });
        playSfx(this, "sfx_select");
        this._hideTokenPicker();
      });

      container.add([btnBg, btnTxt]);
      items.push(btnBg, btnTxt);
      offsetY += BTN_H + BTN_GAP;
    }

    // CANCEL button
    const cancelY = offsetY;
    const cancelBg = this.add.rectangle(0, cancelY, BTN_W, BTN_H, 0x1a1208)
      .setStrokeStyle(1.5, 0x6a4010);
    const cancelTxt = this.add.text(0, cancelY, "CANCEL", {
      fontFamily: "'Press Start 2P'",
      fontSize: "7px",
      color: "#a07040",
    }).setOrigin(0.5);

    cancelBg.setInteractive({ useHandCursor: true });
    cancelBg.on("pointerover",  () => cancelBg.setFillStyle(0x2e1808));
    cancelBg.on("pointerout",   () => cancelBg.setFillStyle(0x1a1208));
    cancelBg.on("pointerdown", (ptr) => {
      ptr.event?.stopPropagation?.();
      this._hideTokenPicker();
    });

    container.add([cancelBg, cancelTxt]);

    this._pickerData = { container, col, row, side };
  }

  _hideTokenPicker() {
    if (!this._pickerData) return;
    this._pickerData.container.destroy();
    this._pickerData = null;
  }

  // ─── Direction cycling ────────────────────────────────────────────────────────

  _cycleDir(side, role, col, row) {
    const s = this.gameState;
    if (!s) return;
    const tok = s[side]?.[role];
    if (!tok) return;

    const cycle = side === "p1" ? P1_ATK_CYCLE : P2_ATK_CYCLE;
    const curDir = tok.direction ?? cycle[0];
    const curIdx = cycle.indexOf(curDir);
    const nextDir = cycle[(curIdx + 1) % cycle.length];

    this.ws?.send("rotate_token", { side, role, direction: nextDir });
    playSfx(this, "sfx_select");
  }

  // ══════════════════════════════════════════════════════════════════════════════
  // Board click handler (full replacement)
  // ══════════════════════════════════════════════════════════════════════════════

  _handleBoardClick(pointer) {
    const s = this.gameState;
    if (!s || s.phase !== "game") return;

    const cw  = GRID_DRAW_W / GRID_SIZE;
    const ch  = GRID_DRAW_H / GRID_SIZE;
    const col = Math.floor((pointer.x - BOARD_OFF_X - GRID_INSET_X) / cw);
    const row = Math.floor((pointer.y - BOARD_OFF_Y - GRID_INSET_Y) / ch);

    // ── Nuke targeting (highest priority) ────────────────────────────────────
    if (this._nukeArmingSide) {
      if (col >= 0 && col < GRID_SIZE && row >= 0 && row < GRID_SIZE) {
        const onEnemy = this._nukeArmingSide === "p1" ? isP2Cell(col, row) : isP1Cell(col, row);
        if (onEnemy) {
          this.ws?.send("trigger_nuke", { side: this._nukeArmingSide, position: { x: col, y: row } });
          playSfx(this, "sfx_select");
        }
      }
      this._nukeArmingSide = null;
      return;
    }

    if (!s.manual_controls) {
      this._hideTokenPicker();
      return;
    }

    // ── Close picker if a picker is open and click is outside it ─────────────
    if (this._pickerData) {
      this._hideTokenPicker();
      return;
    }

    // ── Validate cell is on the board ─────────────────────────────────────────
    if (col < 0 || col >= GRID_SIZE || row < 0 || row >= GRID_SIZE) return;

    const activeSide = s.battle?.active_side ?? null;
    if (!activeSide) return;

    // ── Determine cell territory owner ────────────────────────────────────────
    const cellOwner = isP1Cell(col, row) ? "p1" : (isP2Cell(col, row) ? "p2" : null);

    // Only allow interaction if the active side owns this cell
    if (cellOwner !== activeSide) return;

    const side = activeSide;

    // ── Check if an existing token is at this cell ────────────────────────────
    const tokensAtCell = [];
    for (const role of ["atk_a", "atk_b", "def"]) {
      const tok = s[side]?.[role];
      if (tok && tok.col === col && tok.row === row) {
        tokensAtCell.push({ role, tok });
      }
    }

    if (tokensAtCell.length > 0) {
      const { role, tok } = tokensAtCell[0];
      if (role === "atk_a" || role === "atk_b") {
        // Cycle direction for attack tokens
        this._cycleDir(side, role, col, row);
      } else if (role === "def") {
        // Remove defense token by sending null position
        this.ws?.send("place_token", {
          side,
          role: "def",
          col:  null,
          row:  null,
          direction: null,
        });
        playSfx(this, "sfx_select");
      }
      return;
    }

    // ── Empty cell — show token picker ────────────────────────────────────────
    this._showTokenPicker(side, col, row);
  }

  // ══════════════════════════════════════════════════════════════════════════════
  // Render
  // ══════════════════════════════════════════════════════════════════════════════

  _render() {
    const s = this.gameState;
    if (!s) return;

    const G        = s.game   || {};
    const battle   = s.battle || {};
    const inBattle = s.phase === "game" || s.phase == null;

    const terrainKey = `${s.map_seed}|${JSON.stringify(G.hard_gone || [])}|${JSON.stringify(G.soft_gone || [])}`;
    if (s.terrain && terrainKey !== this._lastSeed) {
      this._renderResources(s);
      this._lastSeed = terrainKey;
    }

    this._renderDamage(G);

    this.dynGfx.clear();
    const { hardMap, softMap, destroyedMap, p1TargetMap, p2TargetMap } = this._buildMaps(s);

    if (inBattle) {
      if (s.p1?.def?.col != null)
        this._drawDefZone(s.p1.def.col, s.p1.def.row, G.def_tier_p1 ?? 0, 0xe8d060);
      if (s.p2?.def?.col != null)
        this._drawDefZone(s.p2.def.col, s.p2.def.row, G.def_tier_p2 ?? 0, 0x60e8a0);

      for (const role of ["atk_a", "atk_b"]) {
        if (s.p1?.[role]?.col != null && s.p1[role].direction)
          this._drawRay(s.p1[role].col, s.p1[role].row,
            computeRay(s.p1[role].col, s.p1[role].row, s.p1[role].direction,
                       hardMap, softMap, "p1", destroyedMap, p2TargetMap));
        if (s.p2?.[role]?.col != null && s.p2[role].direction)
          this._drawRay(s.p2[role].col, s.p2[role].row,
            computeRay(s.p2[role].col, s.p2[role].row, s.p2[role].direction,
                       hardMap, softMap, "p2", destroyedMap, p1TargetMap));
      }
    }

    this._drawHqPlacementRings(s);
    this._renderTokens(s.p1, s.p2, inBattle, G);
    this._renderHqSprites(s, G);
    this._renderWinOverlay(G);
    this._renderTutorial(s.tutorial);
    this._updateEndTurnBtn();
  }

  // ─── Resources / terrain ────────────────────────────────────────────────────

  _renderResources(state) {
    for (const sp of this._terrainSprites) sp.destroy();
    this._terrainSprites = [];
    this.resourceGfx.clear();
    const terrain = state?.terrain;
    if (!terrain) return;
    const hardGoneKeys = new Set((state.game?.hard_gone || []).map(([c, r]) => `${c},${r}`));
    const softGoneKeys = new Set((state.game?.soft_gone || []).map(([c, r]) => `${c},${r}`));

    const cw = GRID_DRAW_W / GRID_SIZE;
    const ch = GRID_DRAW_H / GRID_SIZE;

    const place = (col, row, tex) => {
      if (!this.textures.exists(tex)) return;
      const { x, y } = cellXY(col, row);
      const sp = this.add.image(x, y, tex).setDisplaySize(cw, ch).setAlpha(1).setDepth(1);
      this._terrainSprites.push(sp);
    };

    for (const r of terrain.p1_resources || []) place(r.col, r.row, "cell_mick");
    for (const r of terrain.p2_resources || []) place(r.col, r.row, "cell_emu");
    for (const t of terrain.p1_hard      || []) if (!hardGoneKeys.has(`${t.col},${t.row}`)) place(t.col, t.row, "hard_mick");
    for (const t of terrain.p2_hard      || []) if (!hardGoneKeys.has(`${t.col},${t.row}`)) place(t.col, t.row, "hard_emu");
    for (const t of terrain.p1_soft      || []) if (!softGoneKeys.has(`${t.col},${t.row}`)) place(t.col, t.row, "soft_mick");
    for (const t of terrain.p2_soft      || []) if (!softGoneKeys.has(`${t.col},${t.row}`)) place(t.col, t.row, "soft_emu");

    const g = this.resourceGfx;
    for (const r of [...(terrain.p1_resources || []), ...(terrain.p2_resources || [])]) {
      if (r.resource_type !== "stronghold") continue;
      const { x, y } = cellXY(r.col, r.row);
      g.lineStyle(2, 0xffffff, 0.75); g.strokeCircle(x, y, cw * 0.32);
    }
  }

  // ─── Damage overlay ─────────────────────────────────────────────────────────

  _renderDamage(G) {
    const g  = this.dmgGfx;
    g.clear();
    const cw = GRID_DRAW_W / GRID_SIZE, ch = GRID_DRAW_H / GRID_SIZE;
    const hqCells = new Set(Object.values(G.hq_revealed || {}).map(([c, r]) => `${c},${r}`));

    for (const key of Object.keys(G.damage || {})) {
      const [c, r] = key.split(",").map(Number);
      if ((G.destroyed || []).some(d => d[0] === c && d[1] === r)) continue;
      const bx = BOARD_OFF_X + GRID_INSET_X + c * cw;
      const by = BOARD_OFF_Y + GRID_INSET_Y + r * ch;
      g.fillStyle(0x000000, 0.40); g.fillRect(bx + 2, by + 2, cw - 4, ch - 4);
      g.lineStyle(1.5, 0xff5000, 0.65);
      g.strokeLineShape(new Phaser.Geom.Line(bx + 8, by + 9, bx + cw - 8, by + ch - 9));
      g.strokeLineShape(new Phaser.Geom.Line(bx + cw - 9, by + 8, bx + 10, by + ch - 8));
    }

    const hardGoneKeys = new Set((G.hard_gone || []).map(([c, r]) => `${c},${r}`));
    const softGoneKeys = new Set((G.soft_gone || []).map(([c, r]) => `${c},${r}`));
    for (const [damageMap, goneKeys, color] of [
      [G.hard_damage || {}, hardGoneKeys, 0xffa020],
      [G.soft_damage || {}, softGoneKeys, 0xff6000],
    ]) {
      for (const key of Object.keys(damageMap)) {
        if (goneKeys.has(key)) continue;
        const [c, r] = key.split(",").map(Number);
        const bx = BOARD_OFF_X + GRID_INSET_X + c * cw;
        const by = BOARD_OFF_Y + GRID_INSET_Y + r * ch;
        g.fillStyle(color, 0.22); g.fillRect(bx + 2, by + 2, cw - 4, ch - 4);
        g.lineStyle(2, color, 0.8);
        g.strokeLineShape(new Phaser.Geom.Line(bx + 10, by + ch - 10, bx + cw - 10, by + 10));
      }
    }

    for (const [c, r] of (G.destroyed || [])) {
      if (hqCells.has(`${c},${r}`)) continue;
      const bx = BOARD_OFF_X + GRID_INSET_X + c * cw;
      const by = BOARD_OFF_Y + GRID_INSET_Y + r * ch;
      g.fillStyle(COLORS.destroyed, 0.92); g.fillRect(bx + 1, by + 1, cw - 2, ch - 2);
      g.lineStyle(2.5, COLORS.destroyedX, 1);
      g.strokeLineShape(new Phaser.Geom.Line(bx + 9, by + 9, bx + cw - 9, by + ch - 9));
      g.strokeLineShape(new Phaser.Geom.Line(bx + cw - 9, by + 9, bx + 9,  by + ch - 9));
    }
  }

  // ─── Defence zone ───────────────────────────────────────────────────────────

  _drawDefZone(col, row, tier, color) {
<<<<<<< Updated upstream
    const rad  = tier >= 2 ? 2 : 1;
    const cellW = GRID_DRAW_W / GRID_SIZE;
    const cellH = GRID_DRAW_H / GRID_SIZE;
    const size  = (rad * 2 + 1);
    const x     = BOARD_OFF_X + GRID_INSET_X + (col - rad) * cellW;
    const y     = BOARD_OFF_Y + GRID_INSET_Y + (row - rad) * cellH;
    this.dynGfx.fillStyle(color, 0.09);
    this.dynGfx.fillRect(x, y, size * cellW, size * cellH);
    this.dynGfx.lineStyle(2, color, 0.55);
    this.dynGfx.strokeRect(x, y, size * cellW, size * cellH);
=======
    const rad  = tier >= 1 ? 2 : 1;
    const cw   = GRID_DRAW_W / GRID_SIZE, ch = GRID_DRAW_H / GRID_SIZE;
    const size = rad * 2 + 1;
    const x    = BOARD_OFF_X + GRID_INSET_X + (col - rad) * cw;
    const y    = BOARD_OFF_Y + GRID_INSET_Y + (row - rad) * ch;
    this.dynGfx.fillStyle(color, 0.09);  this.dynGfx.fillRect(x, y, size * cw, size * ch);
    this.dynGfx.lineStyle(2, color, 0.55); this.dynGfx.strokeRect(x, y, size * cw, size * ch);
>>>>>>> Stashed changes
  }

  // ─── Attack ray ─────────────────────────────────────────────────────────────

  _drawRay(startCol, startRow, rayCells) {
    if (!rayCells?.length) return;
    const g  = this.dynGfx;
    const cw = GRID_DRAW_W / GRID_SIZE, ch = GRID_DRAW_H / GRID_SIZE;

    // Subtle cell tint under the ray
    for (const cell of rayCells) {
      const bx = BOARD_OFF_X + GRID_INSET_X + cell.col * cw;
      const by = BOARD_OFF_Y + GRID_INSET_Y + cell.row * ch;
      if      (cell.type === "path")    g.fillStyle(0xffe040, 0.12);
      else if (cell.type === "hit")     g.fillStyle(0xffa000, 0.45);
      else if (cell.type === "soft")    g.fillStyle(0xff8000, 0.40);
      else                              g.fillStyle(0x604000, 0.55);
      g.fillRect(bx + 1, by + 1, cw - 2, ch - 2);
    }

    // Yellow dashed line along the ray path
    const DASH = 7, GAP = 5;
    let px = cellXY(startCol, startRow).x, py = cellXY(startCol, startRow).y;
    for (const cell of rayCells) {
      const { x: cx, y: cy } = cellXY(cell.col, cell.row);
      const dx = cx - px, dy = cy - py;
      const len = Math.sqrt(dx * dx + dy * dy);
      if (len > 0) {
        const nx = dx / len, ny = dy / len;
        let t = 0;
        let drawing = true;
        while (t < len) {
          const segLen = Math.min(drawing ? DASH : GAP, len - t);
          if (drawing) {
            const x0 = px + nx * t, y0 = py + ny * t;
            const x1 = px + nx * (t + segLen), y1 = py + ny * (t + segLen);
            g.lineStyle(3.5, 0x000000, 0.6);
            g.strokeLineShape(new Phaser.Geom.Line(x0, y0, x1, y1));
            g.lineStyle(2.5, 0xffe040, 1.0);
            g.strokeLineShape(new Phaser.Geom.Line(x0, y0, x1, y1));
          }
          t += segLen;
          drawing = !drawing;
        }
      }
      px = cx; py = cy;
    }

    // Hit marker — diamond at the end cell
    const last    = rayCells[rayCells.length - 1];
    const { x, y } = cellXY(last.col, last.row);
    if (last.type === "hit" || last.type === "blocked") {
      const s = 10;
      g.lineStyle(4, 0x000000, 0.7);
      g.strokeTriangle(x, y - s, x + s, y, x - s, y);
      g.lineStyle(2.5, last.type === "blocked" ? 0xff4000 : 0xffe040, 1);
      g.strokeTriangle(x, y - s, x + s, y, x - s, y);
    }
  }

  // ─── HQ placement rings ─────────────────────────────────────────────────────

  _drawHqPlacementRings(s) {
    const cw = GRID_DRAW_W / GRID_SIZE, ch = GRID_DRAW_H / GRID_SIZE;
    for (const side of ["p1", "p2"]) {
      if (s.phase === "hq_placement" && s.setup?.active_setup_side !== side) continue;
      const marker = s.hq_markers?.[side];
      if (!marker || marker.col == null || marker.stale) continue;
      const { col, row } = marker;
      const bx    = BOARD_OFF_X + GRID_INSET_X + col * cw + 2;
      const by    = BOARD_OFF_Y + GRID_INSET_Y + row * ch + 2;
      const pulse = 0.55 + 0.22 * Math.sin(this.time.now / 180);
      const color = side === "p1" ? 0xffd060 : 0x70ef50;
      this.dynGfx.lineStyle(3, color, pulse);
      this.dynGfx.strokeRoundedRect(bx, by, cw - 4, ch - 4, 5);
      this.dynGfx.lineStyle(1, 0xffffff, 0.7);
      this.dynGfx.strokeCircle(bx + (cw - 4) / 2, by + (ch - 4) / 2, cw * 0.18);
    }
  }

  // ─── Token sprites ──────────────────────────────────────────────────────────

  static _isAtkKey(key) { return key.includes("atk"); }

  _renderTokens(p1, p2, inBattle, G) {
    const g  = this.dynGfx;
    const cw = GRID_DRAW_W / GRID_SIZE, ch = GRID_DRAW_H / GRID_SIZE;

    const draw = (key, tok) => {
      const sprite = this.tokenSprites[key];
      const badge  = this.tokenBadges[key];
      const arrow  = this.tokenArrows[key];
      const warn   = this.tokenWarnLabels[key];
      const vis    = tok && tok.col != null && tok.row != null;

      if (!vis) {
        sprite.setVisible(false);
        badge?.setVisible(false);
        arrow?.setVisible(false);
        warn?.setVisible(false);
        return;
      }

      const { x, y } = cellXY(tok.col, tok.row);
      const stale    = !!tok.stale;
      const alpha    = stale ? 0.45 : 1;
      const side     = key.startsWith("p1") ? "p1" : "p2";
      const role     = key.replace(`${side}_`, "");
      const tier     = role === "def"
        ? (side === "p1" ? (G?.def_tier_p1 ?? 0) : (G?.def_tier_p2 ?? 0))
        : (G?.atk_tiers?.[side]?.[role] ?? 0);

      // Update idle animation reference position when token moves
      if (this.tokenIdlePos[key]) {
        this.tokenIdlePos[key].x = x;
        this.tokenIdlePos[key].y = y;
      }

      if (tier > 0 && !stale) {
        const haloColor = side === "p1" ? 0xffd060 : 0x60ef50;
        const haloAlpha = 0.12 + tier * 0.08;
        g.fillStyle(haloColor, haloAlpha); g.fillCircle(x, y, cw * 0.55);
        g.lineStyle(1.5, haloColor, 0.3 + tier * 0.12); g.strokeCircle(x, y, cw * 0.50);
      }

      g.fillStyle(0x000000, 0.28 * alpha);
      g.fillEllipse(x, y + ch * 0.30, cw * 0.55, ch * 0.15);

      sprite.setPosition(x, y - 1).setAngle(0).setAlpha(alpha).setVisible(true);

      if (stale) {
        g.lineStyle(1, 0xfff080, 0.50);
        for (let a = 0; a < Math.PI * 2; a += Math.PI / 8) {
          const r = cw * 0.46;
          g.strokeLineShape(new Phaser.Geom.Line(
            x + Math.cos(a) * r, y + Math.sin(a) * r,
            x + Math.cos(a + Math.PI / 16) * r, y + Math.sin(a + Math.PI / 16) * r));
        }
      }

      if (badge) badge.setPosition(x + cw * 0.32, y - ch * 0.32).setAlpha(alpha).setVisible(true);

      if (arrow) {
        if (inBattle && tok.direction && DIR_VEC[tok.direction]) {
          const [dc, dr] = DIR_VEC[tok.direction];
          arrow.setText(ARROW_CHAR[tok.direction] || "→")
               .setPosition(x + dc * cw * 0.60, y + dr * ch * 0.60)
               .setAlpha(alpha).setVisible(true);
        } else {
          arrow.setVisible(false);
        }
      }

      if (warn) {
        const isAtk   = GameScene._isAtkKey(key);
        const onFence = isOnFence(tok.col, tok.row);
        const inEnemy = isAtk && (side === "p1" ? isP2Cell(tok.col, tok.row) : isP1Cell(tok.col, tok.row));
        const wrongDir = isAtk && inBattle && tok.direction && isWrongSideDir(side, tok.direction);
        let msg = null;
        if (onFence)   msg = "⚠ ON FENCE";
        else if (inEnemy)   msg = "⚠ IN ENEMY ZONE";
        else if (wrongDir)  msg = "⚠ FACING OWN SIDE";

        if (msg) {
          const pulse = 0.70 + 0.30 * Math.sin(this.time.now / 200);
          g.lineStyle(3, 0xff0000, pulse); g.strokeCircle(x, y, cw * 0.50);
          warn.setText(msg).setPosition(x, y + ch * 0.52).setAlpha(alpha).setVisible(true);
        } else {
          warn.setVisible(false);
        }
      }
    };

    draw("p1_atk_a", p1?.atk_a);
    draw("p1_atk_b", p1?.atk_b);
    draw("p1_def",   p1?.def);
    draw("p2_atk_a", p2?.atk_a);
    draw("p2_atk_b", p2?.atk_b);
    draw("p2_def",   p2?.def);
  }

  // ─── HQ sprites ─────────────────────────────────────────────────────────────

  _renderHqSprites(s, G) {
    for (const sp of Object.values(this.hqSprites)) sp.setVisible(false);

    const showAt = (key, col, row) => {
      const sp = this.hqSprites[key];
      if (!sp) return;
      const { x, y } = cellXY(col, row);
      sp.setPosition(x, y).setVisible(true);
    };

    const hqDestroyed = G.winner &&
      (G.win_reason === "homestead_destroyed" || G.win_reason === "nest_destroyed");

    for (const side of ["p1", "p2"]) {
      if (s.phase === "hq_placement" && s.setup?.active_setup_side !== side) continue;
      const m = s.hq_markers?.[side];
      if (m?.col != null && !m.stale) {
        showAt(side, m.col, m.row);
        this.hqSprites[side]?.setAlpha(0.55);
      }
    }

    for (const [side, pos] of Object.entries(G.hq_revealed || {})) {
      const [col, row] = pos;
      if (hqDestroyed) {
        const loser = G.win_reason === "homestead_destroyed" ? "p1" : "p2";
        showAt(side === loser ? `${side}_dead` : side, col, row);
      } else {
        showAt(side, col, row);
      }
      this.hqSprites[side]?.setAlpha(1);
      this.hqSprites[`${side}_dead`]?.setAlpha(1);
    }
  }

  // ─── Win overlay ─────────────────────────────────────────────────────────────

  _renderWinOverlay(G) {
    if (!G.winner) {
      this.winContainer.setVisible(false);
      this._winDimRect.setVisible(false);
      return;
    }

    const msgs = {
      homestead_destroyed: ["THE MOB WINS",  "The Grain Stash is gone. No wheat, no operation. Old Mick has nothing left to protect."],
      nest_destroyed:      ["OLD MICK WINS", "The Bird Council is gone. The ostriches went home. The emus have no idea what they're doing anymore."],
      attrition: G.winner === "p1"
        ? ["OLD MICK WINS", "The scrublands go quiet. The outback belongs to Old Mick."]
        : ["THE MOB WINS",  "No grain, no operation. The pack eats well tonight."],
    };
    const [title, sub] = msgs[G.win_reason] ?? [`${G.winner?.toUpperCase()} WINS`, ""];
    this._winTitleTxt.setText(title);
    this._winSubTxt.setText(sub);

    const loser      = G.win_reason === "homestead_destroyed" ? "p1" : "p2";
    const winnerSide = loser === "p1" ? "p2" : "p1";
    this._winHqLeft.setTexture(winnerSide === "p1" ? "hq_grain_stash" : "hq_grain_stash_dead");
    this._winHqRight.setTexture(loser === "p2"     ? "hq_bird_council_dead"  : "hq_bird_council");

    this._winDimRect.setFillStyle(0x000000, 0.55).setVisible(true);

    if (!this.winContainer.visible) {
      this.winContainer.setScale(0.75);
      this.tweens.add({ targets: this.winContainer, scale: 1, duration: 380, ease: "Back.easeOut" });
    }
    this.winContainer.setVisible(true);
  }

  // ─── Tutorial overlay ────────────────────────────────────────────────────────

  _renderTutorial(tut) {
    this.tutHighlightGfx.clear();
    if (!tut?.active) {
      this.tutorialContainer.setVisible(false);
      this._tutCellLabel?.setVisible(false);
      return;
    }

    this._tutStepTxt.setText(`${tut.step_index + 1} / ${tut.total_steps}`);
    this._tutTitleTxt.setText(tut.title || "");
    this._tutTextTxt.setText(tut.text  || "");
    this._tutHintTxt.setVisible(!!tut.needs_dismiss);
    this.tutorialContainer.setVisible(true);

    if (tut.highlight) {
      const { col, row } = tut.highlight;
      const cw = GRID_DRAW_W / GRID_SIZE, ch = GRID_DRAW_H / GRID_SIZE;
      const bx = BOARD_OFF_X + GRID_INSET_X + col * cw;
      const by = BOARD_OFF_Y + GRID_INSET_Y + row * ch;
      const pulse = 0.5 + 0.5 * Math.sin(this.time.now / 200);
      this.tutHighlightGfx.fillStyle(0xffd060, 0.15 + 0.15 * pulse);
      this.tutHighlightGfx.fillRect(bx + 2, by + 2, cw - 4, ch - 4);
      this.tutHighlightGfx.lineStyle(3, 0xffd060, 0.6 + 0.4 * pulse);
      this.tutHighlightGfx.strokeRect(bx + 2, by + 2, cw - 4, ch - 4);

      if (!this._tutCellLabel) {
        this._tutCellLabel = this.add.text(0, 0, "", {
          fontFamily: FONT_MONO, fontSize: "12px", fontStyle: "bold",
          color: "#ffd060", stroke: "#000000", strokeThickness: 3,
        }).setOrigin(0.5).setDepth(46);
      }
      this._tutCellLabel.setText(`${colLabel(col)}${row + 1}`)
        .setPosition(bx + cw / 2, by + ch + 8).setVisible(true);
    } else {
      this._tutCellLabel?.setVisible(false);
    }

    if (tut.completed) {
      this._tutHintTxt.setText("Tutorial Complete! Press SPACE to continue.").setVisible(true);
    }
  }

  // ─── Map helpers ─────────────────────────────────────────────────────────────

  _buildMaps(s) {
    const hardMap = {}, softMap = {}, p1TargetMap = {}, p2TargetMap = {};
    const hardGoneKeys = new Set((s.game?.hard_gone || []).map(([c, r]) => `${c},${r}`));
    const softGoneKeys = new Set((s.game?.soft_gone || []).map(([c, r]) => `${c},${r}`));

    for (const t of [...(s.terrain?.p1_hard || []), ...(s.terrain?.p2_hard || [])]) {
      if (!hardGoneKeys.has(`${t.col},${t.row}`)) hardMap[`${t.col},${t.row}`] = t;
    }
    for (const t of [...(s.terrain?.p1_soft || []), ...(s.terrain?.p2_soft || [])]) {
      if (!softGoneKeys.has(`${t.col},${t.row}`)) softMap[`${t.col},${t.row}`] = t;
    }

    for (const r of s.terrain?.p1_resources || []) p1TargetMap[`${r.col},${r.row}`] = true;
    for (const r of s.terrain?.p2_resources || []) p2TargetMap[`${r.col},${r.row}`] = true;
    for (const [side, pos] of Object.entries(s.game?.hq_revealed || {})) {
      const [col, row] = pos || [];
      if (col == null || row == null) continue;
      (side === "p1" ? p1TargetMap : p2TargetMap)[`${col},${row}`] = true;
    }
    for (const side of ["p1", "p2"]) {
      const marker = s.hq_markers?.[side];
      if (!marker || marker.stale || marker.col == null || marker.row == null) continue;
      (side === "p1" ? p1TargetMap : p2TargetMap)[`${marker.col},${marker.row}`] = true;
    }

    const destroyedMap = {};
    for (const [c, r] of (s.game?.destroyed || [])) destroyedMap[`${c},${r}`] = true;

    return { hardMap, softMap, destroyedMap, p1TargetMap, p2TargetMap };
  }

<<<<<<< Updated upstream
  // ─── Nuke handling ────────────────────────────────────────────────────────

  _toggleNukeArming() {
    // Live nuke targeting is marker-driven: scan ID19 (P1) or ID29 (P2).
    this._nukeArmingSide = null;
  }

  _updateNukeUi(s) {
    const battle = s?.battle || {};
    const game = s?.game || {};
    const activeSide = battle.active_side || null;
    this._nukeArmingSide = null;

    if (!activeSide) {
      this.nukeBtn?.setVisible(false);
      return;
    }

    const nukeUsed = activeSide === "p1" ? !!game.nuke_used_p1 : !!game.nuke_used_p2;
    const nukeAvailable = activeSide === "p1" ? !!game.nuke_available_p1 : !!game.nuke_available_p2;
    const markerId = activeSide === "p1" ? 19 : 29;

    this.nukeBtn
      .setVisible(true)
      .setText(nukeUsed ? "Nuke Spent" : (nukeAvailable ? `Scan ID${markerId}` : "Nuke Locked"))
      .setColor(nukeAvailable ? "#ffd070" : "#8a7a68")
      .setBackgroundColor(nukeAvailable ? "#2a120c" : "#241812")
      .setAlpha(nukeAvailable || nukeUsed ? 1 : 0.45);
  }

  _handleBoardClick(pointer) {
    if (this._tutorialCanSpaceContinue()) {
      this._sendTutorialDismiss();
      return;
    }
  }

  // ─── WebSocket binding ────────────────────────────────────────────────────
=======
  // ─── WebSocket binding ───────────────────────────────────────────────────────
>>>>>>> Stashed changes

  _bindWS() {
    if (!this.ws) return;

    this.ws.on("state", (s) => {
      const prevSide = this._lastActiveSide;
      const newSide  = s.battle?.active_side ?? null;

      this.gameState = s;

      // Detect turn switch: show overlay when active_side changes to a non-null value
      if (newSide && newSide !== prevSide) {
        this._showTurnOverlay(newSide);
        // Close any open picker when turn changes
        this._hideTokenPicker();
      }

      this._lastActiveSide = newSide;
    });

    this.ws.on("events", (events) => {
      const nukeCells = events
        .filter((ev) => ev?.nuke && Array.isArray(ev.cell))
        .map((ev) => ev.cell);
      // ── Animated rays (one per ray_complete event) ─────────────────────────
      let rayDelay = 0;
      for (const ev of events) {
        if (ev.type === "ray_complete") {
          const capturedEv    = ev;
          const capturedDelay = rayDelay;
          this.time.delayedCall(capturedDelay, () => {
            this._animateRay(capturedEv);
          });
          // Each ray animation = path.length * 70 ms + 400 ms tail
          rayDelay += (ev.path?.length ?? 0) * 70 + 420;
        }
      }

      // ── Sound & shake for other events ─────────────────────────────────────
      for (const ev of events) {
        switch (ev.type) {
          case "cell_damaged":
            playSfx(this, "sfx_first_hit");
            break;
          case "cell_destroyed":
            playSfx(this, "sfx_destroy");
            break;
          case "hard_destroyed":
          case "soft_destroyed":
            playSfx(this, "sfx_destroy");
            break;
          case "hard_hit":
          case "soft_hit":
          case "blocked_hard":
            playSfx(this, "sfx_block");
            break;
          case "hq_destroyed":
            playSfx(this, "sfx_explosion");
            this.time.delayedCall(rayDelay, () => {
              this.cameras.main.shake(600, 0.020);
            });
            break;
          case "nuke_triggered":
            playSfx(this, "sfx_explosion");
            this._animateNuke({ ...ev, cells: nukeCells });
            this.cameras.main.shake(500, 0.018);
            break;
          case "cell_shielded":
            playSfx(this, "sfx_p1_defense");
            break;
          case "attrition_win":
            playSfx(this, "sfx_victory");
            break;
        }
      }
    });
  }

  // ─── Ray animation ───────────────────────────────────────────────────────────

  _animateRay(ev) {
    const path   = ev.path  ?? [];
    const token  = ev.token ?? "";
    const isP1   = token.startsWith("p1");

    if (!path.length) return;

    const g = this.add.graphics().setDepth(30);
    this._rayGfxPool.push(g);

    // Play shoot sound immediately
    playSfx(this, isP1 ? "sfx_p1_attack" : "sfx_p2_attack");

    const cw = GRID_DRAW_W / GRID_SIZE;
    const ch = GRID_DRAW_H / GRID_SIZE;

    path.forEach((step, i) => {
      this.time.delayedCall(i * 70, () => {
        const bx = BOARD_OFF_X + GRID_INSET_X + step.col * cw;
        const by = BOARD_OFF_Y + GRID_INSET_Y + step.row * ch;

        if (step.hit) {
          // Bright flash on hit cell — gold/orange
          g.fillStyle(0xffa000, 0.80);
          g.fillRect(bx + 1, by + 1, cw - 2, ch - 2);

          // Diamond hit marker
          const mx = bx + cw / 2, my = by + ch / 2, s = 9;
          g.lineStyle(3, 0x000000, 0.7);
          g.strokeTriangle(mx, my - s, mx + s, my, mx - s, my);
          g.lineStyle(2, 0xffe040, 1.0);
          g.strokeTriangle(mx, my - s, mx + s, my, mx - s, my);

          if (step.type === "territory") {
            playSfx(this, "sfx_destroy");
            this._spawnImpactFlash(step.col, step.row, 0xffd000);
            this.cameras.main.shake(120, 0.006);
          } else if (step.type === "terrain") {
            playSfx(this, "sfx_block");
            this._spawnImpactFlash(step.col, step.row, 0xff8800);
          } else if (step.type === "hq") {
            playSfx(this, "sfx_explosion");
            this._spawnImpactFlash(step.col, step.row, 0xffffff);
            this.cameras.main.shake(500, 0.020);
          }
        } else {
          // Path cell — gold dashed trail
          g.fillStyle(0xffe040, 0.14);
          g.fillRect(bx + 2, by + 2, cw - 4, ch - 4);
          g.lineStyle(2, 0xffe040, 0.55);
          g.strokeRect(bx + 2, by + 2, cw - 4, ch - 4);
        }
      });
    });

    // Fade out and destroy ray graphics after animation completes
    const totalMs = path.length * 70 + 300;
    this.time.delayedCall(totalMs, () => {
      this.tweens.add({
        targets:  g,
        alpha:    0,
        duration: 350,
        onComplete: () => {
          g.destroy();
          const idx = this._rayGfxPool.indexOf(g);
          if (idx !== -1) this._rayGfxPool.splice(idx, 1);
        },
      });
    });
  }

  // ─── Impact flash ────────────────────────────────────────────────────────────

  _spawnImpactFlash(col, row, color = 0xff4400) {
    const { x, y } = cellXY(col, row);
    const cw = GRID_DRAW_W / GRID_SIZE;

    // Expanding ring
    const ring = this.add.graphics().setDepth(31);
    ring.lineStyle(3, color, 1.0);
    ring.strokeCircle(x, y, cw * 0.20);

    this.tweens.add({
      targets: ring,
      scaleX: 2.8, scaleY: 2.8,
      alpha: 0,
      duration: 380,
      ease: "Quad.easeOut",
      onComplete: () => ring.destroy(),
    });

    // Four corner sparks
    for (let s = 0; s < 4; s++) {
      const angle  = (s / 4) * Math.PI * 2;
      const spark  = this.add.graphics().setDepth(31);
      const sx     = x + Math.cos(angle) * cw * 0.28;
      const sy     = y + Math.sin(angle) * cw * 0.28;
      spark.fillStyle(color, 1.0);
      spark.fillCircle(sx, sy, 3);

      this.tweens.add({
        targets: spark,
        x:       spark.x + Math.cos(angle) * cw * 0.55,
        y:       spark.y + Math.sin(angle) * cw * 0.55,
        alpha:   0,
        duration: 320,
        ease: "Quad.easeOut",
        onComplete: () => spark.destroy(),
      });
    }
  }

  // ─── Nuke animation ──────────────────────────────────────────────────────────

  _animateNuke(ev) {
    const cells  = ev.cells ?? [];
    const center = ev.center;

    // Flash the whole board white briefly
    this.cameras.main.flash(180, 255, 220, 80, false);

    cells.forEach((cell, i) => {
      this.time.delayedCall(i * 60, () => {
        this._spawnImpactFlash(cell[0], cell[1], 0xffd000);
        playSfx(this, i === 0 ? "sfx_explosion" : "sfx_destroy");
      });
    });
  }
}
