/**
 * GameScene — yu_test3
 *
 * Visual layout:
 *   ┌──────────────────────────────────────────────────────────────────┐
 *   │                   TOP STATUS BAR  (55 px)                        │
 *   ├──────────────┬────────────────────────────────┬──────────────────┤
 *   │  LEFT PANEL  │   BOARD  (board1.png + grid)   │  RIGHT PANEL     │
 *   │  (Old Mick)  │         720 × 720 px           │  (The Mob/Emu)   │
 *   │   230 px     │                                │   230 px         │
 *   ├──────────────┴────────────────────────────────┴──────────────────┤
 *   │                   BOTTOM WARNING BAR  (52 px)                    │
 *   └──────────────────────────────────────────────────────────────────┘
 *
 * Panels glow (bright border + lighter bg) when it is that player's turn.
 */

import {
  GRID_SIZE, CELL, BOARD_PX,
  PANEL_W, TOP_BAR_H, BOT_BAR_H,
  BOARD_OFF_X, BOARD_OFF_Y,
  CANVAS_W, CANVAS_H,
  GRID_INSET_X, GRID_INSET_Y, GRID_DRAW_W, GRID_DRAW_H,
  COLORS, DIR_VEC, ARROW_CHAR,
  FONT_TITLE, FONT_LABEL, FONT_MONO,
} from "../constants.js";
import { playSfx, playBgm, toggleMute, isMuted } from "../audio.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Pixel centre of a grid cell (col, row). */
function cellXY(col, row) {
  const cellW = GRID_DRAW_W / GRID_SIZE;
  const cellH = GRID_DRAW_H / GRID_SIZE;
  return {
    x: BOARD_OFF_X + GRID_INSET_X + col * cellW + cellW / 2,
    y: BOARD_OFF_Y + GRID_INSET_Y + row * cellH + cellH / 2,
  };
}

// Territory: anti-diagonal at col+row=11 (L1 → A12) is the fence.
// Matches game_model.py: _side_of() returns "p1" / "p2" / None.
function isP1Cell(col, row)  { return col + row < 11; }
function isP2Cell(col, row)  { return col + row > 11; }
function isOnFence(col, row) { return col + row === 11; }

/** Convert col index to letter label (0→A, 1→B …). */
function colLabel(col) { return String.fromCharCode(65 + col); }

/**
 * Return true when the attack direction points into the player's OWN territory.
 *
 * Fence = anti-diagonal at col+row=11 (L1→A12).
 * P1 territory: col+row < 11.  P1 must fire towards larger col+row (+dc+dr > 0).
 * P2 territory: col+row > 11.  P2 must fire towards smaller col+row (dc+dr < 0).
 *
 * dc+dr = 0 (NE/SW) keeps col+row constant → never crosses the fence → also wrong.
 */
function isWrongSideDir(side, dir) {
  if (!dir || !DIR_VEC[dir]) return false;
  const [dc, dr] = DIR_VEC[dir];
  if (side === "p1") return dc + dr <= 0;  // needs dc+dr > 0 to cross into P2
  if (side === "p2") return dc + dr >= 0;  // needs dc+dr < 0 to cross into P1
  return false;
}

/** Compute attack ray cells. Returns array of {col, row, type}. */
function computeRay(startCol, startRow, dir, hardMap, softMap, attackerSide, destroyedMap, resourceMap) {
  if (!dir || !DIR_VEC[dir]) return [];
  const [dc, dr] = DIR_VEC[dir];
  const isEnemy  = attackerSide === "p1" ? isP2Cell : isP1Cell;
  const cells    = [];
  let c = startCol + dc;
  let r = startRow + dr;
  while (c >= 0 && c < GRID_SIZE && r >= 0 && r < GRID_SIZE) {
    const key = `${c},${r}`;
    if (hardMap[key])                          { cells.push({ col: c, row: r, type: "blocked" }); break; }
    if (softMap[key])                          { cells.push({ col: c, row: r, type: "soft"    }); break; }
    if (isEnemy(c, r) && !destroyedMap[key])  { cells.push({ col: c, row: r, type: "hit"     }); break; }
    cells.push({ col: c, row: r, type: "path" });
    c += dc; r += dr;
  }
  return cells;
}

/** Build {key: resource} maps from terrain object. */
function buildResourceMaps(terrain) {
  const p1 = {}, p2 = {};
  for (const r of terrain?.p1_resources || []) p1[`${r.col},${r.row}`] = r;
  for (const r of terrain?.p2_resources || []) p2[`${r.col},${r.row}`] = r;
  return { p1, p2 };
}

/** Short "col,row" display like "C3". */
function posLabel(tok) {
  if (!tok || tok.col == null) return "—";
  return `${colLabel(tok.col)}${tok.row + 1}`;
}

/** Tier as filled/empty circle pips: "●●○○". */
function tierPips(tier) {
  const t = Math.max(0, Math.min(4, tier ?? 0));
  return "●".repeat(t) + "○".repeat(4 - t);
}

// ─── Error helpers (same as yu_test2) ────────────────────────────────────────
const ERROR_PRIORITY = [
  "camera_unavailable", "marker_map_scan_failed", "token_detection_failed",
  "inactive_side_token_changed", "hq_wrong_side",
  "old_mick_token_invalid_zone", "mob_token_invalid_zone",
  "old_mick_attack_direction_invalid", "mob_attack_direction_invalid",
  "hq_setup_complete",
];
const ERROR_TITLE = {
  camera_unavailable:              "Camera Unavailable",
  marker_map_scan_failed:          "Board Scan Failed",
  token_detection_failed:          "Token Not Detected",
  inactive_side_token_changed:     "Wrong Turn Movement",
  hq_wrong_side:                   "Invalid HQ Side",
  old_mick_token_invalid_zone:     "Mick Token Out of Zone",
  mob_token_invalid_zone:          "Mob Token Out of Zone",
  old_mick_attack_direction_invalid: "Mick Aim Invalid",
  mob_attack_direction_invalid:    "Mob Aim Invalid",
  hq_setup_complete:               "HQ Setup Complete",
};
const HIDDEN_ERRORS = new Set(["inactive_side_token_changed"]);

function primaryError(errors) {
  return [...(Array.isArray(errors) ? errors : [])]
    .filter(e => e?.code && !HIDDEN_ERRORS.has(e.code))
    .sort((a, b) => (ERROR_PRIORITY.indexOf(a.code) ?? 99) - (ERROR_PRIORITY.indexOf(b.code) ?? 99))[0] ?? null;
}

// ─── Scene ────────────────────────────────────────────────────────────────────
export class GameScene extends Phaser.Scene {
  constructor() { super("Game"); }

  init(data) {
    this.ws            = data.ws;
    this._initialState = data.initialState ?? null;
    this.gameState     = null;
    this._lastSeed     = null;
    this._nukeArmingSide = null;
  }

  create() {
    // Layered graphics objects (drawn in order)
    this.boardGfx    = this.add.graphics().setDepth(0);  // grid lines
    this.resourceGfx = this.add.graphics().setDepth(1);  // terrain / resource overlays
    this.dmgGfx      = this.add.graphics().setDepth(2);  // damage / destroyed overlays
    this.dynGfx      = this.add.graphics().setDepth(3);  // attack rays, HQ rings

    this._buildBoardImage();
    this._drawGridOnce();
    this._buildPanels();
    this._buildTopBar();
    this._buildBottomBar();
    this._buildTokenSprites();
    this._buildHqSprites();
    this._buildWinOverlay();
    this._buildMuteButton();
    this._bindWS();

    // Pointer-down for nuke targeting
    this.input.on("pointerdown", this._handleBoardClick, this);

    if (this._initialState) {
      this.gameState = this._initialState;
      this._render();
    }

    // Repaint ~30 fps (keeps dynamic elements smooth even on slow networks)
    this.time.addEvent({ delay: 33, loop: true, callback: () => this._render() });
  }

  // ══════════════════════════════════════════════════════════════════════════════
  // Build helpers (called once in create)
  // ══════════════════════════════════════════════════════════════════════════════

  /** Display the board PNG image as the board background. */
  _buildBoardImage() {
    this.add.image(BOARD_OFF_X, BOARD_OFF_Y, "board")
      .setOrigin(0, 0)
      .setDisplaySize(BOARD_PX, BOARD_PX)
      .setDepth(-1);
  }

  /** Draw the grid lines once into boardGfx (static, never redrawn). */
  _drawGridOnce() {
    const g   = this.boardGfx;
    const cellW = GRID_DRAW_W / GRID_SIZE;
    const cellH = GRID_DRAW_H / GRID_SIZE;
    const x0  = BOARD_OFF_X + GRID_INSET_X;
    const y0  = BOARD_OFF_Y + GRID_INSET_Y;
    const x1  = x0 + GRID_DRAW_W;
    const y1  = y0 + GRID_DRAW_H;

    // Thin white semi-transparent grid lines only — no diagonal drawn here
    // because board1.png already shows the fence/diagonal boundary visually.
    g.lineStyle(1, COLORS.gridLine, 0.20);
    for (let i = 0; i <= GRID_SIZE; i++) {
      g.strokeLineShape(new Phaser.Geom.Line(x0 + i * cellW, y0, x0 + i * cellW, y1));
      g.strokeLineShape(new Phaser.Geom.Line(x0, y0 + i * cellH, x1, y0 + i * cellH));
    }

    // Column labels (A–L) above the board
    const labelStyle = { fontFamily: FONT_MONO, fontSize: "11px", color: "#c8a070" };
    for (let i = 0; i < GRID_SIZE; i++) {
      const cx = x0 + i * cellW + cellW / 2;
      this.add.text(cx, y0 - 16, colLabel(i), labelStyle).setOrigin(0.5).setDepth(0);
    }
    // Row labels (1–12) to the left of the board
    for (let i = 0; i < GRID_SIZE; i++) {
      const cy = y0 + i * cellH + cellH / 2;
      this.add.text(x0 - 18, cy, String(i + 1), labelStyle).setOrigin(0.5).setDepth(0);
    }
  }

  // ─── Side panels ──────────────────────────────────────────────────────────

  /**
   * Build left (Mick) and right (Emu) panels.
   * Each panel contains a background rect + several Text objects that are
   * updated every render cycle via _renderPanels().
   */
  _buildPanels() {
    // ── Shared panel dimensions ──────────────────────────────────────────────
    const pH   = BOARD_PX + TOP_BAR_H; // panel height (from top of canvas)
    const pad  = 14;                    // inner padding

    // ── Left panel (Mick) ────────────────────────────────────────────────────
    this.p1PanelBg  = this.add.rectangle(0, 0, PANEL_W, pH, COLORS.panelBg)
      .setOrigin(0, 0).setDepth(4);
    this.p1PanelBdr = this.add.graphics().setDepth(5);

    const lx = pad;   // left text x inside panel

    // Player name (large)
    this.p1NameTxt = this.add.text(PANEL_W / 2, TOP_BAR_H + 30,
      "OLD MICK", {
        fontFamily: FONT_TITLE, fontSize: "22px", fontStyle: "bold",
        color: "#7a5820", align: "center",
      }).setOrigin(0.5, 0.5).setDepth(6);

    this.p1SubTxt = this.add.text(PANEL_W / 2, TOP_BAR_H + 58,
      "The Farmer", {
        fontFamily: FONT_LABEL, fontSize: "12px",
        color: "#6a5030", align: "center",
      }).setOrigin(0.5, 0.5).setDepth(6);

    // Divider line (drawn once — static)
    const p1Div = (y) => {
      const div = this.add.graphics().setDepth(5);
      div.lineStyle(1, 0x3a2810, 0.7);
      div.strokeLineShape(new Phaser.Geom.Line(lx, y, PANEL_W - lx, y));
    };
    p1Div(TOP_BAR_H + 80);

    // Score section
    this.add.text(lx, TOP_BAR_H + 90, "SCORE", {
      fontFamily: FONT_LABEL, fontSize: "11px", color: "#8a7060",
    }).setDepth(6);
    this.p1ScoreValTxt = this.add.text(PANEL_W - lx, TOP_BAR_H + 90, "0 / 40", {
      fontFamily: FONT_LABEL, fontSize: "11px", color: "#c8a878",
    }).setOrigin(1, 0).setDepth(6);
    this.p1ScoreBarGfx = this.add.graphics().setDepth(6);

    p1Div(TOP_BAR_H + 130);

    // Tier section
    this.add.text(lx, TOP_BAR_H + 140, "TIER", {
      fontFamily: FONT_LABEL, fontSize: "11px", color: "#8a7060",
    }).setDepth(6);
    this.p1TierNumTxt = this.add.text(lx + 46, TOP_BAR_H + 140, "0", {
      fontFamily: FONT_LABEL, fontSize: "13px", fontStyle: "bold", color: "#c8a878",
    }).setDepth(6);
    this.p1TierPipTxt = this.add.text(PANEL_W - lx, TOP_BAR_H + 140, "○○○○", {
      fontFamily: FONT_MONO, fontSize: "13px", color: "#5a4020",
    }).setOrigin(1, 0).setDepth(6);

    p1Div(TOP_BAR_H + 170);

    // Token section
    this.add.text(lx, TOP_BAR_H + 180, "TOKENS", {
      fontFamily: FONT_LABEL, fontSize: "11px", color: "#8a7060",
    }).setDepth(6);

    const tokStyle = { fontFamily: FONT_LABEL, fontSize: "12px", color: "#b89868" };
    const posStyle = { fontFamily: FONT_MONO,  fontSize: "12px", color: "#d4b880" };
    // Keith A
    this.add.text(lx, TOP_BAR_H + 200, "⚔ Keith A", tokStyle).setDepth(6);
    this.p1AtkAPosTxt = this.add.text(PANEL_W - lx, TOP_BAR_H + 200, "—", posStyle).setOrigin(1, 0).setDepth(6);
    // Keith B
    this.add.text(lx, TOP_BAR_H + 222, "⚔ Keith B", tokStyle).setDepth(6);
    this.p1AtkBPosTxt = this.add.text(PANEL_W - lx, TOP_BAR_H + 222, "—", posStyle).setOrigin(1, 0).setDepth(6);
    // Old Mick (def)
    this.add.text(lx, TOP_BAR_H + 244, "🛡 Old Mick", tokStyle).setDepth(6);
    this.p1DefPosTxt  = this.add.text(PANEL_W - lx, TOP_BAR_H + 244, "—", posStyle).setOrigin(1, 0).setDepth(6);

    p1Div(TOP_BAR_H + 275);

    // HQ status
    this.add.text(lx, TOP_BAR_H + 285, "HQ", {
      fontFamily: FONT_LABEL, fontSize: "11px", color: "#8a7060",
    }).setDepth(6);
    this.p1HqTxt = this.add.text(PANEL_W - lx, TOP_BAR_H + 285, "hidden", {
      fontFamily: FONT_LABEL, fontSize: "12px", color: "#9a8060",
    }).setOrigin(1, 0).setDepth(6);

    // ── Right panel (Emu) ─────────────────────────────────────────────────────
    const rx = CANVAS_W - PANEL_W;  // panel starts at this x

    this.p2PanelBg  = this.add.rectangle(rx, 0, PANEL_W, pH, COLORS.panelBg)
      .setOrigin(0, 0).setDepth(4);
    this.p2PanelBdr = this.add.graphics().setDepth(5);

    const rlx = rx + pad;  // text x inside right panel
    const rrx = CANVAS_W - pad; // right-align x

    this.p2NameTxt = this.add.text(rx + PANEL_W / 2, TOP_BAR_H + 30,
      "THE MOB", {
        fontFamily: FONT_TITLE, fontSize: "22px", fontStyle: "bold",
        color: "#2a7020", align: "center",
      }).setOrigin(0.5, 0.5).setDepth(6);

    this.p2SubTxt = this.add.text(rx + PANEL_W / 2, TOP_BAR_H + 58,
      "The Emu Mob", {
        fontFamily: FONT_LABEL, fontSize: "12px",
        color: "#285020", align: "center",
      }).setOrigin(0.5, 0.5).setDepth(6);

    const p2Div = (y) => {
      const div = this.add.graphics().setDepth(5);
      div.lineStyle(1, 0x1a3a14, 0.7);
      div.strokeLineShape(new Phaser.Geom.Line(rlx, y, rrx, y));
    };
    p2Div(TOP_BAR_H + 80);

    this.add.text(rlx, TOP_BAR_H + 90, "SCORE", {
      fontFamily: FONT_LABEL, fontSize: "11px", color: "#50785a",
    }).setDepth(6);
    this.p2ScoreValTxt = this.add.text(rrx, TOP_BAR_H + 90, "0 / 40", {
      fontFamily: FONT_LABEL, fontSize: "11px", color: "#78c878",
    }).setOrigin(1, 0).setDepth(6);
    this.p2ScoreBarGfx = this.add.graphics().setDepth(6);

    p2Div(TOP_BAR_H + 130);

    this.add.text(rlx, TOP_BAR_H + 140, "TIER", {
      fontFamily: FONT_LABEL, fontSize: "11px", color: "#50785a",
    }).setDepth(6);
    this.p2TierNumTxt = this.add.text(rlx + 46, TOP_BAR_H + 140, "0", {
      fontFamily: FONT_LABEL, fontSize: "13px", fontStyle: "bold", color: "#78c878",
    }).setDepth(6);
    this.p2TierPipTxt = this.add.text(rrx, TOP_BAR_H + 140, "○○○○", {
      fontFamily: FONT_MONO, fontSize: "13px", color: "#204820",
    }).setOrigin(1, 0).setDepth(6);

    p2Div(TOP_BAR_H + 170);

    this.add.text(rlx, TOP_BAR_H + 180, "TOKENS", {
      fontFamily: FONT_LABEL, fontSize: "11px", color: "#50785a",
    }).setDepth(6);

    const tok2Style = { fontFamily: FONT_LABEL, fontSize: "12px", color: "#58a868" };
    const pos2Style = { fontFamily: FONT_MONO,  fontSize: "12px", color: "#70d870" };
    this.add.text(rlx, TOP_BAR_H + 200, "⚔ Mob A",    tok2Style).setDepth(6);
    this.p2AtkAPosTxt = this.add.text(rrx, TOP_BAR_H + 200, "—", pos2Style).setOrigin(1, 0).setDepth(6);
    this.add.text(rlx, TOP_BAR_H + 222, "⚔ Mob B",    tok2Style).setDepth(6);
    this.p2AtkBPosTxt = this.add.text(rrx, TOP_BAR_H + 222, "—", pos2Style).setOrigin(1, 0).setDepth(6);
    this.add.text(rlx, TOP_BAR_H + 244, "🛡 Cassowary", tok2Style).setDepth(6);
    this.p2DefPosTxt  = this.add.text(rrx, TOP_BAR_H + 244, "—", pos2Style).setOrigin(1, 0).setDepth(6);

    p2Div(TOP_BAR_H + 275);

    this.add.text(rlx, TOP_BAR_H + 285, "HQ", {
      fontFamily: FONT_LABEL, fontSize: "11px", color: "#50785a",
    }).setDepth(6);
    this.p2HqTxt = this.add.text(rrx, TOP_BAR_H + 285, "hidden", {
      fontFamily: FONT_LABEL, fontSize: "12px", color: "#307030",
    }).setOrigin(1, 0).setDepth(6);
  }

  /** Top status bar — shows game title and current turn info. */
  _buildTopBar() {
    // Dark background strip
    this.add.rectangle(CANVAS_W / 2, TOP_BAR_H / 2, CANVAS_W, TOP_BAR_H, COLORS.topBarBg)
      .setDepth(7);
    // Game title (static, left-of-centre)
    this.add.text(CANVAS_W / 2, TOP_BAR_H / 2, "OLD MICK AGAINST THE MOB", {
      fontFamily: FONT_TITLE, fontSize: "18px",
      color: "#8a6030", letterSpacing: 2,
    }).setOrigin(0.5).setDepth(8);

    // Dynamic: phase / turn text (shown on top of title when something is happening)
    this.topTurnTxt = this.add.text(CANVAS_W / 2, TOP_BAR_H / 2, "", {
      fontFamily: FONT_LABEL, fontSize: "20px", fontStyle: "bold",
      color: "#f0d060",
    }).setOrigin(0.5).setDepth(9).setVisible(false);

    // Mute button sits in top-right corner
  }

  /** Bottom warning / status bar. */
  _buildBottomBar() {
    const y = CANVAS_H - BOT_BAR_H / 2;
    this.add.rectangle(CANVAS_W / 2, y, CANVAS_W, BOT_BAR_H, COLORS.botBarBg).setDepth(7);

    // Camera / board detection status (left side)
    this.botCameraIcon = this.add.text(18, y, "📷", {
      fontFamily: "monospace", fontSize: "14px",
    }).setOrigin(0, 0.5).setDepth(8);
    this.botCameraTxt = this.add.text(40, y, "Connecting…", {
      fontFamily: FONT_MONO, fontSize: "12px", color: "#8a7060",
    }).setOrigin(0, 0.5).setDepth(8);

    // Warning / error message (centre)
    this.botWarnTxt = this.add.text(CANVAS_W / 2, y, "", {
      fontFamily: FONT_LABEL, fontSize: "13px",
      color: "#f0a040", align: "center",
      wordWrap: { width: 500 },
    }).setOrigin(0.5).setDepth(9).setVisible(false);

    // Corners found (right side)
    this.botCornersTxt = this.add.text(CANVAS_W - 14, y, "Corners: 0/4", {
      fontFamily: FONT_MONO, fontSize: "11px", color: "#6a5838",
    }).setOrigin(1, 0.5).setDepth(8);
  }

  // ─── Token sprites ────────────────────────────────────────────────────────

  /** Create Phaser.Image objects for all 6 tokens. Hidden by default. */
  _buildTokenSprites() {
    const sz = CELL * 0.88; // display size (fits within one grid cell)

    // Map token key → texture key loaded in BootScene.
    // A and B attack tokens now use separate images.
    const TEX = {
      p1_atk_a: "tok_mick_atk_a",  // Keith A
      p1_atk_b: "tok_mick_atk_b",  // Keith B
      p1_def:   "tok_mick_def",     // Old Mick
      p2_atk_a: "tok_emu_atk_a",   // Mob A
      p2_atk_b: "tok_emu_atk_b",   // Mob B
      p2_def:   "tok_emu_def",      // Cassowary
    };

    this.tokenSprites   = {};
    this.tokenBadges    = {};  // "A" / "B" labels for the two ATK tokens of each side
    this.tokenArrows    = {};  // direction arrow for ATK tokens
    this.tokenWarnLabels = {}; // "FACING OWN SIDE" warning text per ATK token

    for (const [key, tex] of Object.entries(TEX)) {
      // Token image
      const img = this.add.image(0, 0, tex)
        .setDisplaySize(sz, sz)
        .setDepth(11)
        .setVisible(false);
      this.tokenSprites[key] = img;

      // "A" / "B" badge for distinguishing the two attack tokens
      if (key.endsWith("_a") || key.endsWith("_b")) {
        const badge = this.add.text(0, 0,
          key.endsWith("_a") ? "A" : "B", {
            fontFamily: FONT_MONO, fontSize: "12px", fontStyle: "bold",
            color: "#fff080", stroke: "#000000", strokeThickness: 3,
          }).setOrigin(0.5).setDepth(13).setVisible(false);
        this.tokenBadges[key] = badge;

        // Direction arrow
        const arrow = this.add.text(0, 0, "→", {
          fontFamily: "monospace", fontSize: "20px",
          color: "#fff080", stroke: "#000000", strokeThickness: 3,
        }).setOrigin(0.5).setDepth(13).setVisible(false);
        this.tokenArrows[key] = arrow;
      }

      // Warning label — all 6 tokens get one (ATK: "FACING OWN SIDE", ALL: "ON FENCE")
      const warn = this.add.text(0, 0, "", {
        fontFamily: FONT_LABEL, fontSize: "11px", fontStyle: "bold",
        color: "#ffffff",
        backgroundColor: "#cc0000",
        padding: { x: 5, y: 3 },
      }).setOrigin(0.5, 0).setDepth(20).setVisible(false);
      this.tokenWarnLabels[key] = warn;
    }
  }

  /** Create HQ image sprites (shown/hidden based on game phase). */
  _buildHqSprites() {
    const sz = CELL * 1.0;

    const make = (tex) => this.add.image(0, 0, tex)
      .setDisplaySize(sz, sz)
      .setDepth(10)
      .setVisible(false);

    this.hqSprites = {
      p1:      make("hq_mick"),
      p1_dead: make("hq_mick_dead"),
      p2:      make("hq_emu"),
      p2_dead: make("hq_emu_dead"),
    };
  }

  // ─── Win overlay ──────────────────────────────────────────────────────────

  _buildWinOverlay() {
    const cx = BOARD_OFF_X + BOARD_PX / 2;
    const cy = BOARD_OFF_Y + BOARD_PX / 2;

    this.winContainer = this.add.container(cx, cy).setDepth(40).setVisible(false);

    const bg = this.add.rectangle(0, 0, 500, 110, 0x0a0602, 0.92)
      .setStrokeStyle(3, 0xd4a030, 1);
    this._winTitleTxt = this.add.text(0, -22, "", {
      fontFamily: FONT_TITLE, fontSize: "32px", fontStyle: "bold",
      color: "#ffe070", stroke: "#3a2010", strokeThickness: 4,
    }).setOrigin(0.5);
    this._winSubTxt   = this.add.text(0, 22, "", {
      fontFamily: FONT_LABEL, fontSize: "14px",
      color: "#f0c080", align: "center", wordWrap: { width: 440 },
    }).setOrigin(0.5);

    this.winContainer.add([bg, this._winTitleTxt, this._winSubTxt]);
  }

  // ─── Mute button ──────────────────────────────────────────────────────────

  _buildMuteButton() {
    const btn = this.add.text(CANVAS_W - 20, TOP_BAR_H / 2, "🔊", {
      fontFamily: "monospace", fontSize: "18px", color: "#fff0d0",
    }).setOrigin(1, 0.5).setDepth(50).setInteractive({ useHandCursor: true });

    btn.on("pointerdown", () => {
      const muted = toggleMute();
      btn.setText(muted ? "🔇" : "🔊");
      if (!muted) playBgm(this, "bgm_outback");
    });
    this._muteBtn = btn;
  }

  // ══════════════════════════════════════════════════════════════════════════════
  // Render helpers (called every ~33 ms)
  // ══════════════════════════════════════════════════════════════════════════════

  /** Master render — updates every visual element from current gameState. */
  _render() {
    const s = this.gameState;
    if (!s) return;

    const G       = s.game    || {};
    const battle  = s.battle  || {};
    const setup   = s.setup   || {};
    const inBattle = s.phase === "game" || s.phase == null;

    // ── Resource / terrain overlay — only redrawn when map seed changes ───────
    if (s.terrain && s.map_seed !== this._lastSeed) {
      this._renderResources(s.terrain);
      this._lastSeed = s.map_seed;
    }

    // ── Damage overlay ─────────────────────────────────────────────────────────
    this._renderDamage(G);

    // ── Dynamic layer (rays, defence zones, HQ ring) ──────────────────────────
    this.dynGfx.clear();
    const { hardMap, softMap, destroyedMap, p1ResourceMap, p2ResourceMap }
      = this._buildMaps(s);

    if (inBattle) {
      if (s.p1?.def?.col != null)
        this._drawDefZone(s.p1.def.col, s.p1.def.row, G.tier_p1 ?? 0, 0xe8d060);
      if (s.p2?.def?.col != null)
        this._drawDefZone(s.p2.def.col, s.p2.def.row, G.tier_p2 ?? 0, 0x60e8a0);

      for (const role of ["atk_a", "atk_b"]) {
        if (s.p1?.[role]?.col != null && s.p1[role].direction)
          this._drawRay(s.p1[role].col, s.p1[role].row,
            computeRay(s.p1[role].col, s.p1[role].row, s.p1[role].direction,
                       hardMap, softMap, "p1", destroyedMap, p2ResourceMap));
        if (s.p2?.[role]?.col != null && s.p2[role].direction)
          this._drawRay(s.p2[role].col, s.p2[role].row,
            computeRay(s.p2[role].col, s.p2[role].row, s.p2[role].direction,
                       hardMap, softMap, "p2", destroyedMap, p1ResourceMap));
      }
    }

    // HQ marker ring — show whenever a physical HQ token is on the board
    this._drawHqPlacementRing(s);

    // ── Tokens ─────────────────────────────────────────────────────────────────
    this._renderTokens(s.p1, s.p2, inBattle);

    // ── HQ sprites ─────────────────────────────────────────────────────────────
    this._renderHqSprites(s, G);

    // ── Side panels ────────────────────────────────────────────────────────────
    this._renderPanels(s, G, battle);

    // ── Top bar ────────────────────────────────────────────────────────────────
    this._renderTopBar(s, G, battle);

    // ── Bottom bar ─────────────────────────────────────────────────────────────
    this._renderBottomBar(s);

    // ── Win overlay ────────────────────────────────────────────────────────────
    this._renderWinOverlay(G);
  }

  // ─── Resource / terrain overlay ──────────────────────────────────────────

  /**
   * Place PNG tile images at every resource / terrain cell.
   * Called once per map seed change — destroys old sprites and creates new ones.
   */
  _renderResources(terrain) {
    // Destroy sprites from the previous map
    for (const sp of (this._terrainSprites || [])) sp.destroy();
    this._terrainSprites = [];
    this.resourceGfx.clear();
    if (!terrain) return;

    const cellW = GRID_DRAW_W / GRID_SIZE;
    const cellH = GRID_DRAW_H / GRID_SIZE;

    // Place one PNG image centred on (col, row) at depth 1 (above board, below tokens)
    const placeImg = (col, row, tex, alpha = 1.0) => {
      // Only place if the texture loaded successfully
      if (!this.textures.exists(tex)) return;
      const { x, y } = cellXY(col, row);
      const sp = this.add.image(x, y, tex)
        .setDisplaySize(cellW, cellH)
        .setAlpha(alpha)
        .setDepth(1);
      this._terrainSprites.push(sp);
    };

    // Resource cells — wheat fields (P1) and feeding grounds (P2)
    for (const r of terrain.p1_resources || [])
      placeImg(r.col, r.row, "cell_mick");
    for (const r of terrain.p2_resources || [])
      placeImg(r.col, r.row, "cell_emu");

    // Hard terrain — impassable blockers
    for (const t of terrain.p1_hard || []) placeImg(t.col, t.row, "hard_mick");
    for (const t of terrain.p2_hard || []) placeImg(t.col, t.row, "hard_emu");

    // Soft terrain — destructible obstacles
    for (const t of terrain.p1_soft || []) placeImg(t.col, t.row, "soft_mick");
    for (const t of terrain.p2_soft || []) placeImg(t.col, t.row, "soft_emu");

    // Stronghold marker — extra white ring to highlight high-value cells
    const g = this.resourceGfx;
    for (const r of [...(terrain.p1_resources || []), ...(terrain.p2_resources || [])]) {
      if (r.resource_type !== "stronghold") continue;
      const { x, y } = cellXY(r.col, r.row);
      g.lineStyle(2, 0xffffff, 0.75);
      g.strokeCircle(x, y, cellW * 0.32);
    }
  }

  // ─── Damage overlay ───────────────────────────────────────────────────────

  _renderDamage(G) {
    const g = this.dmgGfx;
    g.clear();
    const cellW = GRID_DRAW_W / GRID_SIZE;
    const cellH = GRID_DRAW_H / GRID_SIZE;

    // Damaged but not destroyed — dark smoky overlay
    for (const key of Object.keys(G.damage || {})) {
      const [c, r] = key.split(",").map(Number);
      if ((G.destroyed || []).some(d => d[0] === c && d[1] === r)) continue;
      const bx = BOARD_OFF_X + GRID_INSET_X + c * cellW;
      const by = BOARD_OFF_Y + GRID_INSET_Y + r * cellH;
      g.fillStyle(0x000000, 0.40);
      g.fillRect(bx + 2, by + 2, cellW - 4, cellH - 4);
      g.lineStyle(1.5, 0xff5000, 0.65);
      g.strokeLineShape(new Phaser.Geom.Line(bx + 8, by + 9, bx + cellW - 8, by + cellH - 9));
      g.strokeLineShape(new Phaser.Geom.Line(bx + cellW - 9, by + 8, bx + 10, by + cellH - 8));
    }

    // Destroyed cells — scorch + ✕
    for (const [c, r] of G.destroyed || []) {
      const bx = BOARD_OFF_X + GRID_INSET_X + c * cellW;
      const by = BOARD_OFF_Y + GRID_INSET_Y + r * cellH;
      g.fillStyle(COLORS.destroyed, 0.92);
      g.fillRect(bx + 1, by + 1, cellW - 2, cellH - 2);
      g.lineStyle(2.5, COLORS.destroyedX, 1);
      g.strokeLineShape(new Phaser.Geom.Line(bx + 9, by + 9, bx + cellW - 9, by + cellH - 9));
      g.strokeLineShape(new Phaser.Geom.Line(bx + cellW - 9, by + 9, bx + 9, by + cellH - 9));
    }
  }

  // ─── Defence zone ─────────────────────────────────────────────────────────

  _drawDefZone(col, row, tier, color) {
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
  }

  // ─── Attack ray ───────────────────────────────────────────────────────────

  _drawRay(startCol, startRow, rayCells) {
    if (!rayCells?.length) return;
    const g     = this.dynGfx;
    const cellW = GRID_DRAW_W / GRID_SIZE;
    const cellH = GRID_DRAW_H / GRID_SIZE;

    for (const cell of rayCells) {
      const bx = BOARD_OFF_X + GRID_INSET_X + cell.col * cellW;
      const by = BOARD_OFF_Y + GRID_INSET_Y + cell.row * cellH;
      if      (cell.type === "path")    g.fillStyle(COLORS.attackRay,    0.16);
      else if (cell.type === "hit")     g.fillStyle(COLORS.attackRayHit, 0.55);
      else if (cell.type === "soft")    g.fillStyle(0xff6000, 0.45);
      else                               g.fillStyle(0x1a0000, 0.60);
      g.fillRect(bx + 1, by + 1, cellW - 2, cellH - 2);
    }

    // Draw the ray line — thicker and darker so it reads on any background
    let px = cellXY(startCol, startRow).x;
    let py = cellXY(startCol, startRow).y;
    for (const cell of rayCells) {
      const { x: cx, y: cy } = cellXY(cell.col, cell.row);
      // Outline (black, slightly wider) drawn first for contrast
      g.lineStyle(cell.type === "path" ? 5 : 6, 0x000000, 0.55);
      g.strokeLineShape(new Phaser.Geom.Line(px, py, cx, cy));
      // Coloured line on top
      g.lineStyle(cell.type === "path" ? 3 : 3.5, COLORS.attackRay, 1.0);
      g.strokeLineShape(new Phaser.Geom.Line(px, py, cx, cy));
      px = cx; py = cy;
    }

    // Terminal marker at the end of the ray
    const last = rayCells[rayCells.length - 1];
    const { x, y } = cellXY(last.col, last.row);
    if (last.type === "hit" || last.type === "blocked") {
      // Bold ✕ — black outline then coloured cross
      const cross = (color) => {
        g.strokeLineShape(new Phaser.Geom.Line(x - 13, y - 13, x + 13, y + 13));
        g.strokeLineShape(new Phaser.Geom.Line(x + 13, y - 13, x - 13, y + 13));
      };
      g.lineStyle(6, 0x000000, 0.7); cross();
      g.lineStyle(3.5, last.type === "blocked" ? 0xff2200 : COLORS.attackRayHit, 1); cross();
    }
  }

  // ─── HQ placement preview ring ────────────────────────────────────────────

  _drawHqPlacementRing(s) {
    // Draw a pulsing ring at every visible HQ marker position (both sides).
    // Works during any game phase — the server now always sends hq_markers.
    for (const side of ["p1", "p2"]) {
      const marker = s.hq_markers?.[side];
      if (!marker || marker.col == null || marker.stale) continue;

      const { col, row } = marker;
      const cellW = GRID_DRAW_W / GRID_SIZE;
      const cellH = GRID_DRAW_H / GRID_SIZE;
      const bx = BOARD_OFF_X + GRID_INSET_X + col * cellW + 2;
      const by = BOARD_OFF_Y + GRID_INSET_Y + row * cellH + 2;
      const pulse = 0.55 + 0.22 * Math.sin(this.time.now / 180);
      const color = side === "p1" ? 0xffd060 : 0x70ef50;

      this.dynGfx.lineStyle(3, color, pulse);
      this.dynGfx.strokeRoundedRect(bx, by, cellW - 4, cellH - 4, 5);
      this.dynGfx.lineStyle(1, 0xffffff, 0.7);
      const cx = bx + (cellW - 4) / 2;
      const cy = by + (cellH - 4) / 2;
      this.dynGfx.strokeCircle(cx, cy, cellW * 0.18);
    }
  }

  // ─── Token sprites ────────────────────────────────────────────────────────

  // Direction → rotation angle in degrees.
  // Assumes the token image faces EAST (right) at 0°.
  // If the image faces a different direction, add/subtract an offset below.
  static _dirAngle(dir) {
    return { E: 0, SE: 45, S: 90, SW: 135, W: 180, NW: -135, N: -90, NE: -45 }[dir] ?? 0;
  }

  // Only ATK tokens rotate with direction; DEF tokens always stay upright.
  static _isAtkKey(key) { return key.includes("atk"); }

  _renderTokens(p1, p2, inBattle) {
    const g     = this.dynGfx;
    const cellW = GRID_DRAW_W / GRID_SIZE;
    const cellH = GRID_DRAW_H / GRID_SIZE;

    const drawToken = (key, tok) => {
      const sprite = this.tokenSprites[key];
      const badge  = this.tokenBadges[key];
      const arrow  = this.tokenArrows[key];
      const vis    = tok && tok.col != null && tok.row != null;

      const warn = this.tokenWarnLabels[key];
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

      // Drop-shadow ellipse
      g.fillStyle(0x000000, 0.28 * alpha);
      g.fillEllipse(x, y + cellH * 0.30, cellW * 0.55, cellH * 0.15);

      // Rotate ATK tokens to face their attack direction.
      // DEF tokens stay at 0° (upright) since they don't have a direction.
      const angle = (GameScene._isAtkKey(key) && tok.direction)
        ? GameScene._dirAngle(tok.direction)
        : 0;

      sprite.setPosition(x, y - 1)
            .setAngle(angle)
            .setAlpha(alpha)
            .setVisible(true);

      // Stale: dashed ring warning
      if (stale) {
        g.lineStyle(1, 0xfff080, 0.50);
        for (let a = 0; a < Math.PI * 2; a += Math.PI / 8) {
          const r = cellW * 0.46;
          g.strokeLineShape(new Phaser.Geom.Line(
            x + Math.cos(a) * r, y + Math.sin(a) * r,
            x + Math.cos(a + Math.PI / 16) * r, y + Math.sin(a + Math.PI / 16) * r));
        }
      }

      // Badge (A/B) — always top-right in screen space (no rotation)
      if (badge) {
        badge.setPosition(x + cellW * 0.32, y - cellH * 0.32)
             .setAlpha(alpha).setVisible(true);
      }

      // Direction arrow for ATK tokens in battle
      if (arrow) {
        if (inBattle && tok.direction && DIR_VEC[tok.direction]) {
          const [dc, dr] = DIR_VEC[tok.direction];
          arrow.setText(ARROW_CHAR[tok.direction] || "→")
               .setPosition(x + dc * cellW * 0.60, y + dr * cellH * 0.60)
               .setAlpha(alpha).setVisible(true);
        } else {
          arrow.setVisible(false);
        }
      }

      // Placement warnings — red ring + label below the token
      if (warn) {
        const side       = key.startsWith("p1") ? "p1" : "p2";
        const isAtk      = GameScene._isAtkKey(key);
        const onFence    = isOnFence(tok.col, tok.row);
        // ATK token physically placed inside the enemy's territory
        const inEnemy    = isAtk && (side === "p1"
          ? isP2Cell(tok.col, tok.row)
          : isP1Cell(tok.col, tok.row));
        // ATK token's aim direction points back into own territory
        const wrongDir   = isAtk && inBattle && tok.direction
          && isWrongSideDir(side, tok.direction);

        // Priority: fence > enemy territory > wrong direction
        let msg = null;
        if (onFence)  msg = "⚠ ON FENCE";
        else if (inEnemy)  msg = "⚠ IN ENEMY ZONE";
        else if (wrongDir) msg = "⚠ FACING OWN SIDE";

        if (msg) {
          const pulse = 0.70 + 0.30 * Math.sin(this.time.now / 200);
          g.lineStyle(3, 0xff0000, pulse);
          g.strokeCircle(x, y, cellW * 0.50);
          warn.setText(msg)
              .setPosition(x, y + cellH * 0.52)
              .setAlpha(alpha)
              .setVisible(true);
        } else {
          warn.setVisible(false);
        }
      }
    };

    drawToken("p1_atk_a", p1?.atk_a);
    drawToken("p1_atk_b", p1?.atk_b);
    drawToken("p1_def",   p1?.def);
    drawToken("p2_atk_a", p2?.atk_a);
    drawToken("p2_atk_b", p2?.atk_b);
    drawToken("p2_def",   p2?.def);
  }

  // ─── HQ sprites ───────────────────────────────────────────────────────────

  _renderHqSprites(s, G) {
    // Hide all first, then show what's needed
    for (const sp of Object.values(this.hqSprites)) sp.setVisible(false);

    const showAt = (key, col, row) => {
      const sp = this.hqSprites[key];
      if (!sp) return;
      const { x, y } = cellXY(col, row);
      sp.setPosition(x, y).setVisible(true);
    };

    const hqDestroyed = G.winner &&
      (G.win_reason === "homestead_destroyed" || G.win_reason === "nest_destroyed");

    // Show ghost HQ sprite wherever the physical HQ token is visible on the board.
    // This works in any phase — the server now always populates hq_markers.
    for (const side of ["p1", "p2"]) {
      const m = s.hq_markers?.[side];
      if (m?.col != null && !m.stale) {
        showAt(side, m.col, m.row);
        this.hqSprites[side]?.setAlpha(0.55);
      }
    }

    // Also show fully-revealed HQs (confirmed / destroyed) at their locked position
    for (const [side, pos] of Object.entries(G.hq_revealed || {})) {
      const [col, row] = pos;
      const deadKey    = `${side}_dead`;
      const liveKey    = side;
      if (hqDestroyed) {
        // Show destroyed sprite for the losing HQ
        const loser = G.win_reason === "homestead_destroyed" ? "p1" : "p2";
        showAt(side === loser ? deadKey : liveKey, col, row);
      } else {
        showAt(liveKey, col, row);
      }
      this.hqSprites[side]?.setAlpha(1);
      this.hqSprites[`${side}_dead`]?.setAlpha(1);
    }
  }

  // ─── Side panels ─────────────────────────────────────────────────────────

  /**
   * Update panel colours (active glow), score bar, tier pips, token positions.
   * Called every render tick — all updates are cheap text/colour changes.
   */
  _renderPanels(s, G, battle) {
    const activeSide  = battle.active_side ?? null;
    const threshold   = G.attrition_threshold ?? 40;
    const p1Score     = G.score_p1_attrition ?? 0;
    const p2Score     = G.score_p2_attrition ?? 0;
    const tier1       = G.tier_p1 ?? 0;
    const tier2       = G.tier_p2 ?? 0;

    const p1Active = activeSide === "p1";
    const p2Active = activeSide === "p2";

    // ── Panel background + border glow ────────────────────────────────────────
    this.p1PanelBg.setFillStyle(p1Active ? COLORS.p1PanelActive : COLORS.panelBg);
    this.p2PanelBg.setFillStyle(p2Active ? COLORS.p2PanelActive : COLORS.panelBg);

    // Border — redrawn so we can change colour
    const drawBorder = (gfx, x, w, h, active, color) => {
      gfx.clear();
      gfx.lineStyle(active ? 3 : 1, active ? color : COLORS.panelBorderDim, active ? 1 : 0.55);
      gfx.strokeRect(x, 0, w, h);
    };
    const panelH = TOP_BAR_H + BOARD_PX;
    drawBorder(this.p1PanelBdr, 0, PANEL_W, panelH, p1Active, COLORS.p1BorderActive);
    drawBorder(this.p2PanelBdr, CANVAS_W - PANEL_W, PANEL_W, panelH, p2Active, COLORS.p2BorderActive);

    // Active pulse on panel name when it's that player's turn
    const pulse = 0.72 + 0.28 * Math.sin(this.time.now / 400);
    this.p1NameTxt.setColor(p1Active
      ? `#${Math.floor(0xffd060 * pulse).toString(16).padStart(6, "0")}`
      : "#7a5820");
    this.p2NameTxt.setColor(p2Active
      ? `#${Math.floor(0x70ef50 * pulse).toString(16).padStart(6, "0")}`
      : "#2a7020");

    // ── Score bars ────────────────────────────────────────────────────────────
    this._drawScoreBar(this.p1ScoreBarGfx,
      14, TOP_BAR_H + 108, PANEL_W - 28, 12,
      p1Score, threshold, COLORS.scoreBarFill1);
    this.p1ScoreValTxt.setText(`${p1Score} / ${threshold}`);

    this._drawScoreBar(this.p2ScoreBarGfx,
      CANVAS_W - PANEL_W + 14, TOP_BAR_H + 108, PANEL_W - 28, 12,
      p2Score, threshold, COLORS.scoreBarFill2);
    this.p2ScoreValTxt.setText(`${p2Score} / ${threshold}`);

    // ── Tier pips ─────────────────────────────────────────────────────────────
    this.p1TierNumTxt.setText(`${tier1}`);
    this.p1TierPipTxt.setText(tierPips(tier1))
      .setColor(p1Active ? "#d4a030" : "#5a4020");
    this.p2TierNumTxt.setText(`${tier2}`);
    this.p2TierPipTxt.setText(tierPips(tier2))
      .setColor(p2Active ? "#50cc40" : "#204820");

    // ── Token positions ───────────────────────────────────────────────────────
    this.p1AtkAPosTxt.setText(posLabel(s.p1?.atk_a));
    this.p1AtkBPosTxt.setText(posLabel(s.p1?.atk_b));
    this.p1DefPosTxt .setText(posLabel(s.p1?.def));
    this.p2AtkAPosTxt.setText(posLabel(s.p2?.atk_a));
    this.p2AtkBPosTxt.setText(posLabel(s.p2?.atk_b));
    this.p2DefPosTxt .setText(posLabel(s.p2?.def));

    // ── HQ status text ────────────────────────────────────────────────────────
    const hqLabel = (hq, revealedPos) => {
      if (revealedPos) return `${colLabel(revealedPos[0])}${revealedPos[1] + 1}`;
      if (hq?.confirmed) return "confirmed";
      if (hq?.has_candidate) return "pending";
      return "hidden";
    };
    this.p1HqTxt.setText(hqLabel(s.setup?.hq?.p1, G.hq_revealed?.p1));
    this.p2HqTxt.setText(hqLabel(s.setup?.hq?.p2, G.hq_revealed?.p2));
  }

  /** Draw a filled progress bar. */
  _drawScoreBar(gfx, x, y, w, h, value, maxVal, fillColor) {
    gfx.clear();
    gfx.fillStyle(COLORS.scoreBarBg, 1);
    gfx.fillRect(x, y, w, h);
    const fillW = Math.round((Math.min(value, maxVal) / maxVal) * w);
    if (fillW > 0) {
      gfx.fillStyle(fillColor, 0.88);
      gfx.fillRect(x, y, fillW, h);
    }
    gfx.lineStyle(1, 0x5a4020, 0.7);
    gfx.strokeRect(x, y, w, h);
  }

  // ─── Top bar ──────────────────────────────────────────────────────────────

  _renderTopBar(s, G, battle) {
    const inBattle = s.phase === "game" || s.phase == null;
    const phase    = s.phase;

    // Only show the dynamic turn text when there is something meaningful
    if (!inBattle) {
      this.topTurnTxt
        .setText(this._phaseLabel(phase))
        .setColor("#f0d060")
        .setVisible(true);
    } else if (battle.active_side === "p1") {
      this.topTurnTxt.setText("OLD MICK'S TURN").setColor("#ffd060").setVisible(true);
    } else if (battle.active_side === "p2") {
      this.topTurnTxt.setText("THE MOB'S TURN").setColor("#72ef52").setVisible(true);
    } else {
      // No active side — hide turn text so the title shows through
      this.topTurnTxt.setVisible(false);
    }
  }

  _phaseLabel(phase) {
    return {
      scan:           "Board Scan",
      side_selection: "Choose First HQ Side",
      hq_placement:   "Hidden HQ Placement",
      game:           "Battle",
    }[phase] ?? "Setup";
  }

  // ─── Bottom bar ───────────────────────────────────────────────────────────

  _renderBottomBar(s) {
    const corners = s.corners_found ?? 0;
    this.botCornersTxt.setText(`Corners: ${corners}/4`);

    // Camera / board status icon and text
    if (corners >= 4) {
      this.botCameraIcon.setText("📷").setAlpha(1);
      this.botCameraTxt.setText("Board detected").setColor("#80c868");
    } else if (corners > 0) {
      this.botCameraIcon.setText("⚠️").setAlpha(1);
      this.botCameraTxt.setText(`Board partial — ${corners}/4 corners`).setColor("#e0a040");
    } else {
      this.botCameraIcon.setText("⚠️").setAlpha(0.7);
      this.botCameraTxt.setText("Board not detected").setColor("#c06030");
    }

    // Primary error / warning
    const err = primaryError(s.errors || []);
    if (err) {
      const title = ERROR_TITLE[err.code] ?? "Warning";
      const msg   = err.message ? `${title} — ${err.message}` : title;
      this.botWarnTxt.setText(msg)
        .setColor(err.code === "hq_setup_complete" ? "#80e870" : "#f0a040")
        .setVisible(true);
    } else {
      this.botWarnTxt.setVisible(false);
    }
  }

  // ─── Win overlay ──────────────────────────────────────────────────────────

  _renderWinOverlay(G) {
    if (!G.winner) { this.winContainer.setVisible(false); return; }

    const msgs = {
      homestead_destroyed: ["THE MOB WINS", "Old Mick's Homestead is gone."],
      nest_destroyed:      ["OLD MICK WINS", "The Nest has been destroyed."],
      attrition: G.winner === "p1"
        ? ["OLD MICK WINS", "Feeding grounds razed. The Mob starves."]
        : ["THE MOB WINS",  "Paddocks trampled. Old Mick runs out."],
    };
    const [title, sub] = msgs[G.win_reason] ?? [`${G.winner.toUpperCase()} WINS`, ""];
    this._winTitleTxt.setText(title);
    this._winSubTxt  .setText(sub);

    if (!this.winContainer.visible) {
      this.winContainer.setScale(0.7);
      this.tweens.add({ targets: this.winContainer, scale: 1, duration: 320, ease: "Back.easeOut" });
    }
    this.winContainer.setVisible(true);
  }

  // ─── Map building helpers ─────────────────────────────────────────────────

  _buildMaps(s) {
    const hardMap      = {};
    const softMap      = {};
    const softGoneKeys = new Set((s.game?.soft_gone || []).map(([c, r]) => `${c},${r}`));

    for (const t of [...(s.terrain?.p1_hard || []), ...(s.terrain?.p2_hard || [])])
      hardMap[`${t.col},${t.row}`] = t;
    for (const t of [...(s.terrain?.p1_soft || []), ...(s.terrain?.p2_soft || [])]) {
      if (!softGoneKeys.has(`${t.col},${t.row}`)) softMap[`${t.col},${t.row}`] = t;
    }

    const destroyedMap = {};
    for (const [c, r] of (s.game?.destroyed || [])) destroyedMap[`${c},${r}`] = true;

    const { p1: p1ResourceMap, p2: p2ResourceMap } = buildResourceMaps(s.terrain);

    return { hardMap, softMap, destroyedMap, p1ResourceMap, p2ResourceMap };
  }

  // ─── Nuke handling ────────────────────────────────────────────────────────

  _handleBoardClick(pointer) {
    if (this.gameState?.phase !== "game" || !this._nukeArmingSide) return;
    const cellW = GRID_DRAW_W / GRID_SIZE;
    const cellH = GRID_DRAW_H / GRID_SIZE;
    const col   = Math.floor((pointer.x - BOARD_OFF_X - GRID_INSET_X) / cellW);
    const row   = Math.floor((pointer.y - BOARD_OFF_Y - GRID_INSET_Y) / cellH);
    if (col < 0 || col >= GRID_SIZE || row < 0 || row >= GRID_SIZE) return;

    const enemySide = this._nukeArmingSide === "p1" ? "p2" : "p1";
    const onEnemy   = this._nukeArmingSide === "p1" ? isP2Cell(col, row) : isP1Cell(col, row);
    if (onEnemy) {
      this.ws?.send("trigger_nuke", { side: this._nukeArmingSide, position: { x: col, y: row } });
      playSfx(this, "sfx_select");
    }
    this._nukeArmingSide = null;
  }

  // ─── WebSocket binding ────────────────────────────────────────────────────

  _bindWS() {
    if (!this.ws) return;

    // State updates
    this._stateHandler = (s) => { this.gameState = s; };
    this.ws.on("state", this._stateHandler);

    // Game events → SFX
    this._eventsHandler = (events) => {
      for (const ev of events) {
        switch (ev.type) {
          case "cell_damaged":
            if ((ev.required_hp ?? 1) >= 2) playSfx(this, "sfx_first_hit");
            else                            playSfx(this, "sfx_p1_attack");
            break;
          case "cell_destroyed":   playSfx(this, "sfx_destroy");    break;
          case "soft_destroyed":
          case "blocked_hard":     playSfx(this, "sfx_block");      break;
          case "hq_destroyed":     playSfx(this, "sfx_explosion");  break;
          case "nuke_triggered":   playSfx(this, "sfx_explosion");  break;
          case "attrition_win":    playSfx(this, "sfx_victory");    break;
        }
      }
    };
    this.ws.on("events", this._eventsHandler);

    // Tier-up and winner detection (state-diff)
    this._prevTiers  = { p1: 0, p2: 0 };
    this._prevWinner = null;
    this._tierWinHandler = (s) => {
      const G = s.game || {};
      if ((G.tier_p1 ?? 0) > this._prevTiers.p1) playSfx(this, "sfx_tier_up");
      if ((G.tier_p2 ?? 0) > this._prevTiers.p2) playSfx(this, "sfx_tier_up");
      this._prevTiers.p1 = G.tier_p1 ?? 0;
      this._prevTiers.p2 = G.tier_p2 ?? 0;
      if (G.winner && !this._prevWinner) playSfx(this, "sfx_victory");
      this._prevWinner = G.winner ?? null;
    };
    this.ws.on("state", this._tierWinHandler);
  }
}
