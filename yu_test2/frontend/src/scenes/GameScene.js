import {
  GRID_SIZE, CELL, BOARD_OFF_X, BOARD_OFF_Y,
  CANVAS_W, CANVAS_H, COLORS, DIR_VEC, ARROW_CHAR,
} from "../constants.js";
import { playSfx, playBgm, toggleMute, isMuted } from "../audio.js";

/**
 * GameScene — visual layer for live state.
 *
 * Static layer (drawn once):  board base, diagonal fence, labels
 * Resource layer (per map):   wheat / scrubland active cells; redrawn on map_seed change
 * Dynamic layer (every frame): tokens, ATK direction arrows, damage / destroyed
 */

// ATK / DEF tokens use the prototype3 pixel-art textures.
// The tiny role indicator letter ("A" / "B") goes on the sprite itself.
const TOKEN_TEX = {
  p1_atk_a: "tok_farmer_attack",  p1_atk_b: "tok_farmer_attack",  p1_def: "tok_farmer_defense",
  p2_atk_a: "tok_emu_attack",     p2_atk_b: "tok_emu_attack",     p2_def: "tok_emu_defense",
};
const TOKEN_BADGE = {
  p1_atk_a: "A", p1_atk_b: "B",
  p2_atk_a: "A", p2_atk_b: "B",
};

const PHASE_LABEL = {
  scan: "Board Scan",
  side_selection: "Choose First HQ Side",
  hq_placement: "Hidden HQ Placement",
  game: "Battle",
};

const SIDE_LABEL = {
  p1: "Old Mick",
  p2: "The Mob",
  old_mick: "Old Mick",
  mob: "The Mob",
};

const ERROR_PRIORITY = [
  "camera_unavailable",
  "marker_map_scan_failed",
  "token_detection_failed",
  "inactive_side_token_changed",
  "hq_wrong_side",
  "old_mick_token_invalid_zone",
  "mob_token_invalid_zone",
  "old_mick_attack_direction_invalid",
  "mob_attack_direction_invalid",
  "hq_setup_complete",
];

const ERROR_TITLE = {
  camera_unavailable: "Camera Unavailable",
  marker_map_scan_failed: "Board Scan Failed",
  token_detection_failed: "Token Detection Failed",
  inactive_side_token_changed: "Wrong Turn Movement",
  hq_wrong_side: "Invalid HQ Placement",
  old_mick_token_invalid_zone: "Old Mick Position Invalid",
  mob_token_invalid_zone: "Mob Position Invalid",
  old_mick_attack_direction_invalid: "Old Mick Aim Invalid",
  mob_attack_direction_invalid: "Mob Aim Invalid",
  hq_setup_complete: "HQ Setup Complete",
};

const ERROR_MESSAGE_OVERRIDE = {
  inactive_side_token_changed: "Only the active player may move this turn. Opponent movement was ignored.",
  hq_setup_complete: "Both HQs are locked in. Battle setup is complete.",
};

const HIDDEN_ERROR_CODES = new Set([
  "inactive_side_token_changed",
]);

const HELP_ROLE_ROWS = [
  ["tok_farmer_attack", "Riflemen ATK", "Aim in one of 8 directions to attack down a line."],
  ["tok_farmer_defense", "Old Mick DEF", "Protects nearby friendly tiles from going down in one hit."],
  ["tok_emu_attack", "Mob ATK", "Aim in one of 8 directions to attack down a line."],
  ["tok_emu_defense", "Cassowary DEF", "Protects nearby friendly tiles from going down in one hit."],
];

function cellXY(col, row) {
  return {
    x: BOARD_OFF_X + col * CELL + CELL / 2,
    y: BOARD_OFF_Y + row * CELL + CELL / 2,
  };
}

function isP1(col, row) { return col + row < 11; }
function isP2(col, row) { return col + row > 11; }
function sideOwnsCell(side, col, row) {
  if (side === "p1") return isP1(col, row);
  if (side === "p2") return isP2(col, row);
  return false;
}
function terrainOccupiesCell(terrain, col, row) {
  for (const group of ["p1_hard", "p1_soft", "p2_hard", "p2_soft"]) {
    for (const tile of (terrain?.[group] || [])) {
      if (tile?.col === col && tile?.row === row) return true;
    }
  }
  return false;
}
function isValidHqPlacementCell(side, col, row, terrain) {
  if (side !== "p1" && side !== "p2") return false;
  if (!Number.isInteger(col) || !Number.isInteger(row)) return false;
  if (col < 0 || col >= GRID_SIZE || row < 0 || row >= GRID_SIZE) return false;
  if (!sideOwnsCell(side, col, row)) return false;
  if ((side === "p1" && ["0,0", "0,1", "1,0"].includes(`${col},${row}`))
    || (side === "p2" && ["11,11", "11,10", "10,11"].includes(`${col},${row}`))) return false;
  return !terrainOccupiesCell(terrain, col, row);
}
function phaseLabel(phase) { return PHASE_LABEL[phase] || "Setup"; }
function sideLabel(side) { return SIDE_LABEL[side] || "Waiting"; }
function hqProgressLabel(sideState) {
  if (!sideState) return "waiting";
  if (sideState.confirmed) return "confirmed (hidden)";
  if (sideState.has_candidate) return "candidate saved";
  return "waiting";
}
function errorPriority(code) {
  const index = ERROR_PRIORITY.indexOf(code);
  return index === -1 ? ERROR_PRIORITY.length : index;
}
function primaryError(errors) {
  return [...(Array.isArray(errors) ? errors : [])]
    .filter((error) => error?.code)
    .filter((error) => !HIDDEN_ERROR_CODES.has(error.code))
    .sort((left, right) => errorPriority(left.code) - errorPriority(right.code))[0] || null;
}
function errorTitle(code) { return ERROR_TITLE[code] || "Live Warning"; }
function errorMessage(error) {
  const code = error?.code;
  return ERROR_MESSAGE_OVERRIDE[code] || error?.message || "Live validation warning.";
}
function buildResourceMaps(terrain) {
  const p1 = {};
  const p2 = {};
  for (const resource of (terrain?.p1_resources || [])) p1[`${resource.col},${resource.row}`] = resource;
  for (const resource of (terrain?.p2_resources || [])) p2[`${resource.col},${resource.row}`] = resource;
  return { p1, p2 };
}
function computeRay(startCol, startRow, dir, hardMap, softMap, attackerSide, destroyedMap, resourceMap) {
  if (!dir || !DIR_VEC[dir]) return [];
  const [dc, dr] = DIR_VEC[dir];
  const cells = [];
  let c = startCol + dc;
  let r = startRow + dr;
  const isEnemyCell = attackerSide === "p1" ? isP2 : isP1;

  while (c >= 0 && c < GRID_SIZE && r >= 0 && r < GRID_SIZE) {
    const key = `${c},${r}`;
    if (hardMap[key]) { cells.push({ col: c, row: r, type: "blocked" }); break; }
    if (softMap[key]) { cells.push({ col: c, row: r, type: "soft" }); break; }
    if (isEnemyCell(c, r) && resourceMap[key] && !destroyedMap[key]) {
      cells.push({ col: c, row: r, type: "hit" });
      break;
    }
    cells.push({ col: c, row: r, type: "path" });
    c += dc;
    r += dr;
  }
  return cells;
}

export class GameScene extends Phaser.Scene {
  constructor() { super("Game"); }

  init(data) {
    this.ws            = data.ws;
    this._initialState = data.initialState ?? null;
    this.gameState     = null;
    this._lastSeed     = null;
    this._nukeArmingSide = null;
    this._helpVisible = false;
  }

  create() {
    this.boardGfx    = this.add.graphics().setDepth(0);
    this.resourceGfx = this.add.graphics().setDepth(1);
    this.dmgGfx      = this.add.graphics().setDepth(2);
    this.dynGfx      = this.add.graphics().setDepth(3);

    this._createTokenTextures();
    this._buildBoard();
    this._buildHUD();
    this._buildSetupUi();
    this._buildWarningUi();
    this._buildWinBanner();
    this._buildHelpUi();
    this._buildMuteButton();
    this._buildTokenSprites();
    this._buildArrows();
    this._bindWS();
    this.input.on("pointerdown", this._handleBoardPointerDown, this);

    if (this._initialState) {
      this.gameState = this._initialState;
      this._render();
    }

    // Repaint at ~30 fps even without new state (so the dynamic layer
    // doesn't lag visually on slow networks)
    this.time.addEvent({
      delay: 33, loop: true,
      callback: () => this._render(),
    });
  }

  // ─── Static board ──────────────────────────────────────────────────────

  _buildBoard() {
    const g = this.boardGfx;

    // Territory base
    for (let col = 0; col < GRID_SIZE; col++) {
      for (let row = 0; row < GRID_SIZE; row++) {
        const bx = BOARD_OFF_X + col * CELL;
        const by = BOARD_OFF_Y + row * CELL;
        const isP1 = row >= col;
        g.fillStyle(isP1 ? COLORS.p1Base : COLORS.p2Base, 1);
        g.fillRect(bx, by, CELL, CELL);
      }
    }

    // Grid lines
    g.lineStyle(1, COLORS.gridLine, 1);
    for (let i = 0; i <= GRID_SIZE; i++) {
      const x = BOARD_OFF_X + i * CELL;
      const y = BOARD_OFF_Y + i * CELL;
      g.strokeLineShape(new Phaser.Geom.Line(
        x, BOARD_OFF_Y, x, BOARD_OFF_Y + GRID_SIZE * CELL));
      g.strokeLineShape(new Phaser.Geom.Line(
        BOARD_OFF_X, y, BOARD_OFF_X + GRID_SIZE * CELL, y));
    }

    // Diagonal fence
    g.lineStyle(3, COLORS.diagonal, 1);
    g.strokeLineShape(new Phaser.Geom.Line(
      BOARD_OFF_X, BOARD_OFF_Y,
      BOARD_OFF_X + GRID_SIZE * CELL,
      BOARD_OFF_Y + GRID_SIZE * CELL));

    g.lineStyle(2, COLORS.diagonalTick, 0.9);
    for (let i = 1; i < GRID_SIZE; i++) {
      const cx = BOARD_OFF_X + i * CELL;
      const cy = BOARD_OFF_Y + i * CELL;
      const perp = 6;
      g.strokeLineShape(new Phaser.Geom.Line(
        cx - perp, cy + perp, cx + perp, cy - perp));
    }

    // Coordinate labels
    const labelStyle = { fontFamily: "monospace", fontSize: "10px", color: "#6b5030" };
    for (let i = 0; i < GRID_SIZE; i++) {
      const lx = BOARD_OFF_X + i * CELL + CELL / 2;
      const ly = BOARD_OFF_Y + i * CELL + CELL / 2;
      this.add.text(lx, BOARD_OFF_Y - 16,
        String.fromCharCode(65 + i), labelStyle).setOrigin(0.5);
      this.add.text(BOARD_OFF_X - 18, ly,
        String(i + 1), labelStyle).setOrigin(0.5);
    }
  }

  // ─── Resources (per-map static overlay) ────────────────────────────────

  _renderResources(terrain) {
    const g = this.resourceGfx;
    g.clear();
    if (!terrain) return;

    const drawCell = (cell, color, valueLabel) => {
      const { col, row } = cell;
      const bx = BOARD_OFF_X + col * CELL;
      const by = BOARD_OFF_Y + row * CELL;
      g.fillStyle(color, 1);
      g.fillRect(bx + 1, by + 1, CELL - 2, CELL - 2);
      g.lineStyle(1, 0x000000, 0.18);
      g.strokeRect(bx + 1, by + 1, CELL - 2, CELL - 2);
    };

    const colorFor = (resource, baseColor, altColor, strongColor) => {
      if (resource.resource_type === "stronghold") return strongColor;
      if (resource.value === 3) return altColor;
      if (resource.value === 2) return altColor;
      return baseColor;
    };

    for (const r of terrain.p1_resources || []) {
      drawCell(r, colorFor(r,
        COLORS.p1Active, COLORS.p1ActiveAlt, COLORS.resourceStronghold));
    }
    for (const r of terrain.p2_resources || []) {
      drawCell(r, colorFor(r,
        COLORS.p2Active, COLORS.p2ActiveAlt, COLORS.resourceStronghold));
    }

    // Soft / hard terrain overlays
    const drawTerrain = (cells, fill, border, dashed = false) => {
      for (const t of cells || []) {
        const bx = BOARD_OFF_X + t.col * CELL;
        const by = BOARD_OFF_Y + t.row * CELL;
        g.fillStyle(fill, 1);
        g.fillRect(bx + 3, by + 3, CELL - 6, CELL - 6);
        if (dashed) {
          g.lineStyle(2, border, 0.9);
        } else {
          g.lineStyle(2, border, 1);
        }
        g.strokeRect(bx + 3, by + 3, CELL - 6, CELL - 6);
      }
    };
    drawTerrain(terrain.p1_hard, COLORS.terrainHard,  0x000000);
    drawTerrain(terrain.p2_hard, COLORS.terrainHard,  0x000000);
    drawTerrain(terrain.p1_soft, COLORS.terrainSoft,  0xffe8a0, true);
    drawTerrain(terrain.p2_soft, COLORS.terrainSoft,  0xffe8a0, true);

    // Stronghold markers (a small × badge in the corner so it's recognisable)
    const drawBadge = (resource) => {
      if (resource.resource_type !== "stronghold") return;
      const { x, y } = cellXY(resource.col, resource.row);
      g.lineStyle(2, 0xffffff, 0.9);
      g.strokeCircle(x, y, 12);
    };
    (terrain.p1_resources || []).forEach(drawBadge);
    (terrain.p2_resources || []).forEach(drawBadge);
  }

  // ─── Damage / destroyed overlay ───────────────────────────────────────

  _renderDamage(G) {
    const g = this.dmgGfx;
    g.clear();
    if (!G) return;

    // Damaged but not destroyed — smoky overlay
    for (const key of Object.keys(G.damage || {})) {
      const [c, r] = key.split(",").map(Number);
      const destroyedKey = (G.destroyed || []).some(d => d[0] === c && d[1] === r);
      if (destroyedKey) continue;
      const bx = BOARD_OFF_X + c * CELL;
      const by = BOARD_OFF_Y + r * CELL;
      g.fillStyle(0x000000, 0.35);
      g.fillRect(bx + 2, by + 2, CELL - 4, CELL - 4);
      g.lineStyle(1.5, 0xff6020, 0.7);
      g.strokeLineShape(new Phaser.Geom.Line(bx + 6, by + 8, bx + CELL - 6, by + CELL - 8));
      g.strokeLineShape(new Phaser.Geom.Line(bx + CELL - 8, by + 6, bx + 10, by + CELL - 6));
    }

    // Destroyed — full scorch + ✕
    for (const cell of G.destroyed || []) {
      const [c, r] = cell;
      const bx = BOARD_OFF_X + c * CELL;
      const by = BOARD_OFF_Y + r * CELL;
      g.fillStyle(COLORS.destroyed, 0.95);
      g.fillRect(bx + 1, by + 1, CELL - 2, CELL - 2);
      g.lineStyle(2.5, COLORS.destroyedX, 1);
      g.strokeLineShape(new Phaser.Geom.Line(bx + 8, by + 8, bx + CELL - 8, by + CELL - 8));
      g.strokeLineShape(new Phaser.Geom.Line(bx + CELL - 8, by + 8, bx + 8, by + CELL - 8));
    }

    // HQ revealed — gold ring
    for (const [side, cell] of Object.entries(G.hq_revealed || {})) {
      const [c, r] = cell;
      const { x, y } = cellXY(c, r);
      g.lineStyle(3, 0xfff080, 1);
      g.strokeCircle(x, y, CELL * 0.45);
    }
  }

  // ─── Token visuals (drawn each frame on dynGfx) ───────────────────────

  // ─── Pixel-art token textures (ported from prototype3) ───────────────

  _makeTex(key, w, h, fn) {
    if (this.textures.exists(key)) return;
    const g = this.make.graphics({ x: 0, y: 0, add: false });
    fn(g);
    g.generateTexture(key, w, h);
    g.destroy();
  }

  _createTokenTextures() {
    const S = 40;

    // Riflemen / Keith (P1 attack)
    this._makeTex("tok_farmer_attack", S, S, g => {
      g.fillStyle(0x2a1400, 1);
      g.fillRect(9, 9, 22, 3);
      g.fillRect(13, 3, 14, 7);
      g.fillStyle(0xd4956a, 1);
      g.fillCircle(20, 16, 6);
      g.fillStyle(0x8a7040, 1);
      g.fillRect(13, 22, 14, 13);
      g.fillStyle(0x5a4020, 1);
      g.fillRect(13, 35, 5, 5);
      g.fillRect(22, 35, 5, 5);
      g.lineStyle(2.5, 0x2a1800, 1);
      g.strokeLineShape(new Phaser.Geom.Line(26, 18, 37, 30));
      g.fillStyle(0x2a1800, 1);
      g.fillCircle(37, 30, 2);
    });

    // Old Mick (P1 defense)
    this._makeTex("tok_farmer_defense", S, S, g => {
      g.fillStyle(0x2a1400, 1);
      g.fillRect(7, 9, 26, 3);
      g.fillRect(11, 3, 18, 7);
      g.fillStyle(0xd4956a, 1);
      g.fillCircle(20, 16, 6);
      g.fillStyle(0x2a1400, 1);
      g.fillRect(15, 18, 10, 2);
      g.fillStyle(0x7a5020, 1);
      g.fillRect(11, 22, 18, 13);
      g.fillStyle(0x5a3a10, 1);
      g.fillRect(11, 35, 6, 5);
      g.fillRect(23, 35, 6, 5);
      g.lineStyle(2.5, 0x2a1800, 1);
      g.strokeLineShape(new Phaser.Geom.Line(32, 5, 32, 35));
      g.strokeLineShape(new Phaser.Geom.Line(29, 22, 35, 22));
    });

    // The Mob / Emu (P2 attack)
    this._makeTex("tok_emu_attack", S, S, g => {
      g.fillStyle(0x2a2218, 1);
      g.fillRoundedRect(9, 22, 20, 14, 8);
      g.fillRect(16, 9, 7, 15);
      g.fillCircle(19, 8, 7);
      g.fillStyle(0xd08020, 1);
      g.fillTriangle(25, 7, 33, 6, 24, 11);
      g.fillStyle(0xe8a030, 1);
      g.fillCircle(22, 5, 2.5);
      g.fillStyle(0x1a1810, 1);
      g.fillCircle(23, 5, 1);
      g.fillStyle(0x3a3028, 1);
      g.fillCircle(8, 28, 4);
      g.fillCircle(30, 28, 4);
      g.lineStyle(2.5, 0x1a1810, 1);
      g.strokeLineShape(new Phaser.Geom.Line(14, 36, 10, 40));
      g.strokeLineShape(new Phaser.Geom.Line(24, 36, 28, 40));
    });

    // Cassowary (P2 defense)
    this._makeTex("tok_emu_defense", S, S, g => {
      g.fillStyle(0x1a1810, 1);
      g.fillRoundedRect(8, 20, 22, 16, 8);
      g.fillRect(15, 7, 8, 16);
      g.fillCircle(19, 9, 8);
      g.fillStyle(0x7a5a10, 1);
      g.fillTriangle(11, 9, 19, -2, 27, 9);
      g.fillStyle(0x0060c0, 1);
      g.fillRoundedRect(14, 11, 4, 12, 2);
      g.fillStyle(0xee3010, 1);
      g.fillRoundedRect(18, 13, 4, 8, 2);
      g.fillStyle(0xff8000, 1);
      g.fillCircle(23, 6, 2.5);
      g.fillStyle(0x1a1810, 1);
      g.fillCircle(24, 6, 1);
      g.lineStyle(3, 0x1a1810, 1);
      g.strokeLineShape(new Phaser.Geom.Line(14, 36, 9, 40));
      g.strokeLineShape(new Phaser.Geom.Line(22, 36, 27, 40));
    });
  }

  _buildTokenSprites() {
    this.tokenSprites = {};
    this.tokenBadges  = {};
    this.tokenLabels  = {};
    for (const [key, tex] of Object.entries(TOKEN_TEX)) {
      const sprite = this.add.image(0, 0, tex)
        .setDepth(11).setVisible(false);
      this.tokenSprites[key] = sprite;
      // Small badge ("A" / "B") for the two ATK tokens so they're distinguishable
      if (TOKEN_BADGE[key]) {
        const badge = this.add.text(0, 0, TOKEN_BADGE[key], {
          fontFamily: "monospace", fontSize: "11px",
          color: "#fff080", fontStyle: "bold",
          stroke: "#000000", strokeThickness: 3,
        }).setDepth(13).setOrigin(0.5).setVisible(false);
        this.tokenBadges[key] = badge;
      }
      this.tokenLabels[key] = this.add.text(0, 0, key.replaceAll("_", " ").toUpperCase(), {
        fontFamily: "monospace", fontSize: "9px", color: "#f0e0c0", stroke: "#000000", strokeThickness: 3,
      }).setDepth(12).setOrigin(0.5).setVisible(false);
    }
  }

  _buildArrows() {
    const style = {
      fontFamily: "monospace", fontSize: "22px",
      color: "#fff080", stroke: "#000000", strokeThickness: 3,
    };
    this.arrows = {
      p1_atk_a: this.add.text(0, 0, "→", style).setDepth(12).setOrigin(0.5).setVisible(false),
      p1_atk_b: this.add.text(0, 0, "→", style).setDepth(12).setOrigin(0.5).setVisible(false),
      p2_atk_a: this.add.text(0, 0, "→", style).setDepth(12).setOrigin(0.5).setVisible(false),
      p2_atk_b: this.add.text(0, 0, "→", style).setDepth(12).setOrigin(0.5).setVisible(false),
    };
  }

  _renderTokens(p1, p2, inBattle) {
    const g = this.dynGfx;

    const drawToken = (key, tok) => {
      const sprite = this.tokenSprites[key];
      const arrow  = this.arrows[key];
      const badge  = this.tokenBadges[key];
      const label  = this.tokenLabels[key];
      const visible = tok && tok.col != null && tok.row != null;

      if (!visible) {
        sprite.setVisible(false);
        if (arrow) arrow.setVisible(false);
        if (badge) badge.setVisible(false);
        if (label) label.setVisible(false);
        return;
      }
      const { x, y } = cellXY(tok.col, tok.row);
      const stale = !!tok.stale;
      const alpha = stale ? 0.45 : 1;

      // Soft circular shadow under the sprite (helps the token pop on busy cells)
      g.fillStyle(0x000000, 0.30 * alpha);
      g.fillEllipse(x, y + CELL * 0.30, CELL * 0.55, CELL * 0.16);

      sprite.setPosition(x, y - 1)
            .setAlpha(alpha)
            .setVisible(true);

      // Stale: dashed outer ring as warning
      if (stale) {
        g.lineStyle(1, 0xfff080, 0.55);
        for (let a = 0; a < Math.PI * 2; a += Math.PI / 8) {
          const x1 = x + Math.cos(a) * (CELL * 0.48);
          const y1 = y + Math.sin(a) * (CELL * 0.48);
          const x2 = x + Math.cos(a + Math.PI / 16) * (CELL * 0.48);
          const y2 = y + Math.sin(a + Math.PI / 16) * (CELL * 0.48);
          g.strokeLineShape(new Phaser.Geom.Line(x1, y1, x2, y2));
        }
      }

      // Badge ("A" / "B") sits top-right of the sprite
      if (badge) {
        badge.setPosition(x + CELL * 0.30, y - CELL * 0.30)
             .setAlpha(alpha)
             .setVisible(true);
      }

      if (label) {
        label.setPosition(x, y + CELL * 0.42)
             .setAlpha(alpha)
             .setVisible(true);
      }

      // ATK direction arrow
      if (arrow) {
        if (inBattle && tok.direction && DIR_VEC[tok.direction]) {
          const [dc, dr] = DIR_VEC[tok.direction];
          arrow.setText(ARROW_CHAR[tok.direction] || "→")
               .setPosition(x + dc * CELL * 0.60, y + dr * CELL * 0.60)
               .setAlpha(alpha)
               .setVisible(true);
        } else {
          arrow.setVisible(false);
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

  // ─── HUD ──────────────────────────────────────────────────────────────

  _buildHUD() {
    this.add.rectangle(CANVAS_W / 2, 28, CANVAS_W - 24, 40, COLORS.turnBanner, 0.85)
      .setStrokeStyle(1, COLORS.btnBorder);
    this.add.text(CANVAS_W / 2, 28, "OLD MICK AGAINST THE MOB", {
      fontFamily: "monospace", fontSize: "14px",
      color: "#fff0d0", letterSpacing: 4, fontStyle: "bold",
    }).setOrigin(0.5);

    const baseY = BOARD_OFF_Y + GRID_SIZE * CELL + 30;
    const text = (y, str, opts = {}) =>
      this.add.text(BOARD_OFF_X, y, str, {
        fontFamily: "monospace", fontSize: "12px",
        color: "#c8a878", ...opts,
      });

    this.statusTurn    = text(baseY,        "Turn:           —");
    this.statusCorners = text(baseY + 18,   "Corners:        0/4");
    this.statusScore   = text(baseY + 36,   "Paddock score: 0/40   Feeding ground score: 0/40");
    this.statusTier    = text(baseY + 54,   "Tier P1: 0   Tier P2: 0");
    this.statusBattle  = text(baseY + 72,   "Status: waiting for live state", {
      color: "#d8c890", fontSize: "11px",
    });
    this.statusWinner  = text(baseY + 94,   "", {
      color: "#f0d070", fontSize: "14px", fontStyle: "bold",
    });
    this.statusWarning = text(baseY + 120, "Recent alert: none", {
      color: "#9a7a58", fontSize: "10px", wordWrap: { width: CANVAS_W - BOARD_OFF_X * 2 },
    });

    this.nukeBtn = this.add.text(CANVAS_W - 108, baseY + 88, "Arm Nuke", {
      fontFamily: "monospace", fontSize: "11px", fontStyle: "bold",
      color: "#ffd070", backgroundColor: "#2a120c", padding: { x: 8, y: 5 },
    }).setOrigin(0.5).setDepth(30).setInteractive({ useHandCursor: true }).setVisible(false);
    this.nukeBtn.on("pointerdown", () => this._toggleNukeArming());

    this.add.text(CANVAS_W / 2, CANVAS_H - 28,
      "yu_test2 — live runtime mainline", {
        fontFamily: "monospace", fontSize: "10px",
        color: "#5a3a10",
      }).setOrigin(0.5);
  }

  _buildSetupUi() {
    const cardX = BOARD_OFF_X + 12;
    const cardY = BOARD_OFF_Y + 10;
    const cardW = GRID_SIZE * CELL - 24;
    this.setupCard = this.add.rectangle(cardX + cardW / 2, cardY + 96, cardW, 196, 0x120904, 0.90)
      .setStrokeStyle(2, 0xb88338, 0.85).setDepth(18).setVisible(false).setOrigin(0.5);
    const titleStyle = { fontFamily: "serif", fontSize: "16px", fontStyle: "bold", color: "#fff0b0", stroke: "#2a1408", strokeThickness: 3 };
    const monoStyle = { fontFamily: "monospace", fontSize: "11px", color: "#e6d2a8", stroke: "#1e0e06", strokeThickness: 2 };
    this.setupTitleTxt = this.add.text(cardX + 12, cardY + 12, "", titleStyle).setDepth(19).setVisible(false);
    this.setupStatusTxt = this.add.text(cardX + 12, cardY + 36, "", {
      fontFamily: "serif", fontSize: "12px", color: "#f2d8a0", stroke: "#241208", strokeThickness: 2, wordWrap: { width: cardW - 26 },
    }).setDepth(19).setVisible(false);
    this.setupScanTxt = this.add.text(cardX + 12, cardY + 92, "", monoStyle).setDepth(19).setVisible(false);
    this.setupSideTxt = this.add.text(cardX + 12, cardY + 110, "", monoStyle).setDepth(19).setVisible(false);
    this.setupActiveTxt = this.add.text(cardX + 12, cardY + 128, "", monoStyle).setDepth(19).setVisible(false);
    this.setupP1Txt = this.add.text(cardX + 12, cardY + 146, "", monoStyle).setDepth(19).setVisible(false);
    this.setupP2Txt = this.add.text(cardX + 12, cardY + 164, "", monoStyle).setDepth(19).setVisible(false);
  }

  _buildWarningUi() {
    this.warningCard = this.add.rectangle(CANVAS_W / 2, BOARD_OFF_Y + 120, 470, 104, 0x1a0905, 0.86)
      .setStrokeStyle(3, 0xe0883a, 0.95).setDepth(24).setVisible(false);
    this.warningTitleTxt = this.add.text(CANVAS_W / 2, BOARD_OFF_Y + 84, "", {
      fontFamily: "serif", fontSize: "18px", fontStyle: "bold", color: "#ffe0a0", stroke: "#2a1008", strokeThickness: 3,
    }).setOrigin(0.5, 0).setDepth(25).setVisible(false);
    this.warningBodyTxt = this.add.text(CANVAS_W / 2, BOARD_OFF_Y + 112, "", {
      fontFamily: "serif", fontSize: "13px", color: "#ffd0a0", align: "center", wordWrap: { width: 380 }, stroke: "#220c06", strokeThickness: 2,
    }).setOrigin(0.5, 0).setDepth(25).setVisible(false);
  }

  _buildWinBanner() {
    this.winBanner = this.add.container(CANVAS_W / 2, BOARD_OFF_Y + GRID_SIZE * CELL / 2).setDepth(35).setVisible(false);
    const bg = this.add.rectangle(0, -8, 430, 86, 0x0c0602, 0.88).setStrokeStyle(3, 0xd4a030, 0.9);
    const title = this.add.text(0, -20, "", {
      fontFamily: "serif", fontSize: "28px", fontStyle: "bold", color: "#ffe070", stroke: "#3a2010", strokeThickness: 4,
    }).setOrigin(0.5);
    const sub = this.add.text(0, 18, "", {
      fontFamily: "serif", fontSize: "13px", fontStyle: "italic", color: "#f0c080", align: "center", wordWrap: { width: 380 },
    }).setOrigin(0.5);
    this.winBanner.add([bg, title, sub]);
    this._winBannerTitle = title;
    this._winBannerSub = sub;
  }

  _buildHelpUi() {
    const overlay = this.add.container(CANVAS_W / 2, CANVAS_H / 2).setDepth(45).setVisible(false);
    const bg = this.add.rectangle(0, 0, 620, 730, 0x100804, 0.94).setStrokeStyle(3, 0xb88338, 0.92);
    const inner = this.add.rectangle(0, 0, 596, 706, 0x000000, 0).setStrokeStyle(1, 0xf0d070, 0.18);
    overlay.add([bg, inner]);

    const addText = (x, y, text, style) => {
      const node = this.add.text(x, y, text, style);
      overlay.add(node);
      return node;
    };
    const leftX = -278;
    const rightX = 40;
    const bodyStyle = {
      fontFamily: "serif",
      fontSize: "13px",
      color: "#f0dfbd",
      lineSpacing: 6,
      wordWrap: { width: 250 },
    };
    const sectionStyle = {
      fontFamily: "monospace",
      fontSize: "11px",
      fontStyle: "bold",
      color: "#d4a030",
      letterSpacing: 1,
    };

    addText(0, -338, "HELP", {
      fontFamily: "monospace",
      fontSize: "22px",
      fontStyle: "bold",
      color: "#fff0d0",
      stroke: "#2a1408",
      strokeThickness: 4,
    }).setOrigin(0.5, 0);
    addText(0, -304, "Keep ID 5 visible to keep this open.", {
      fontFamily: "monospace",
      fontSize: "10px",
      color: "#9f8660",
    }).setOrigin(0.5, 0);

    addText(leftX, -258, "OBJECTIVE", sectionStyle).setOrigin(0, 0);
    addText(leftX, -234, "Destroy the enemy HQ first. Protect your own.", bodyStyle).setOrigin(0, 0);

    addText(leftX, -162, "SETUP", sectionStyle).setOrigin(0, 0);
    addText(leftX, -138,
      "Show all 4 board corners.\nChoose which side places an HQ first.\nPlace the hidden HQ in your own territory.\nScan confirm to lock it in.\nRepeat for the other side.",
      bodyStyle).setOrigin(0, 0);

    addText(leftX, 16, "BATTLE TURN", sectionStyle).setOrigin(0, 0);
    addText(leftX, 40,
      "Scan your side's turn marker.\nMove your side's tokens.\nRotate ATK tokens to aim.\nScan confirm to resolve attacks.",
      bodyStyle).setOrigin(0, 0);

    addText(leftX, 172, "ATTACK AND DEFENSE", sectionStyle).setOrigin(0, 0);
    addText(leftX, 196,
      "ATK attacks in 8 directions.\nOnly the first valid target in the line is hit.\nHard terrain blocks attacks.\nDEF protects nearby friendly tiles.",
      bodyStyle).setOrigin(0, 0);

    addText(rightX, -258, "UNIT ROLES", sectionStyle).setOrigin(0, 0);
    HELP_ROLE_ROWS.forEach(([textureKey, title, description], index) => {
      const rowY = -214 + index * 68;
      const icon = this.add.image(rightX + 20, rowY + 18, textureKey).setScale(1.05).setOrigin(0.5);
      const titleTxt = this.add.text(rightX + 54, rowY, title, {
        fontFamily: "monospace",
        fontSize: "11px",
        fontStyle: "bold",
        color: "#ffe7b0",
      }).setOrigin(0, 0);
      const bodyTxt = this.add.text(rightX + 54, rowY + 18, description, {
        fontFamily: "serif",
        fontSize: "12px",
        color: "#e0d0b0",
        wordWrap: { width: 200 },
      }).setOrigin(0, 0);
      overlay.add([icon, titleTxt, bodyTxt]);
    });

    addText(rightX, 78, "UI LEGEND", sectionStyle).setOrigin(0, 0);
    addText(rightX, 102,
      "Arrow near token = attack direction.\nHighlighted path or cells = attack line.\nFaded or dashed token = stale tracking.\nWarning card = ignored or invalid interaction.\nGold ring = revealed HQ.",
      {
        ...bodyStyle,
        wordWrap: { width: 220 },
      }).setOrigin(0, 0);

    addText(0, 324, "Remove ID 5 to close help and return to normal overlays.", {
      fontFamily: "monospace",
      fontSize: "10px",
      color: "#9f8660",
      align: "center",
    }).setOrigin(0.5, 0);

    this.helpOverlay = overlay;
  }

  _renderHelpUi(help = {}) {
    const visible = !!help?.visible;
    this._helpVisible = visible;
    this.helpOverlay?.setVisible(visible);
  }

  _hideSetupUi() {
    const texts = [this.setupTitleTxt, this.setupStatusTxt, this.setupScanTxt, this.setupSideTxt, this.setupActiveTxt, this.setupP1Txt, this.setupP2Txt];
    this.setupCard?.setVisible(false);
    texts.forEach((txt) => txt?.setVisible(false));
  }

  _hideWarningUi() {
    this.warningCard?.setVisible(false);
    this.warningTitleTxt?.setVisible(false);
    this.warningBodyTxt?.setVisible(false);
  }

  _renderSetupUi(phase, setup = {}) {
    if (this._helpVisible) {
      this._hideSetupUi();
      return;
    }
    const visible = phase && phase !== "game";
    const texts = [this.setupTitleTxt, this.setupStatusTxt, this.setupScanTxt, this.setupSideTxt, this.setupActiveTxt, this.setupP1Txt, this.setupP2Txt];
    this.setupCard.setVisible(visible);
    texts.forEach((txt) => txt.setVisible(visible));
    if (!visible) return;

    this.setupTitleTxt.setText(`Hidden HQ Setup  |  ${phaseLabel(phase)}`);
    this.setupStatusTxt.setText(setup.status_message || "Waiting for backend setup state.");
    this.setupScanTxt.setText(`Board scan: ${setup.board_scan_ready ? "ready" : "waiting"}`).setColor(setup.board_scan_ready ? "#8cf0a0" : "#ffcc88");
    this.setupSideTxt.setText(`First HQ side: ${setup.side_selection_complete ? sideLabel(setup.first_player_side) : "Pending"}`).setColor(setup.side_selection_complete ? "#f2df9a" : "#ffcc88");
    this.setupActiveTxt.setText(`Active setup side: ${setup.active_setup_side ? sideLabel(setup.active_setup_side) : "Waiting"}`).setColor(setup.active_setup_side === "p2" ? "#b8ff78" : "#ffd878");
    this.setupP1Txt.setText(`Old Mick HQ: ${hqProgressLabel(setup.hq?.p1)}`).setColor(setup.hq?.p1?.confirmed ? "#8cf0a0" : "#f2df9a");
    this.setupP2Txt.setText(`The Mob HQ: ${hqProgressLabel(setup.hq?.p2)}`).setColor(setup.hq?.p2?.confirmed ? "#8cf0a0" : "#d8ef9a");
  }

  _renderWarning(errors = []) {
    if (this._helpVisible) {
      this._hideWarningUi();
      const currentError = primaryError(errors);
      if (!currentError) {
        this.statusWarning?.setText("Recent alert: none").setColor("#9a7a58");
        return;
      }
      const title = errorTitle(currentError.code);
      const message = errorMessage(currentError);
      this.statusWarning?.setText(`Recent alert: ${title} - ${message}`).setColor(currentError.code === "hq_setup_complete" ? "#98d48a" : "#e0a070");
      return;
    }
    const currentError = primaryError(errors);
    if (!currentError) {
      this.warningCard.setVisible(false);
      this.warningTitleTxt.setVisible(false);
      this.warningBodyTxt.setVisible(false);
      this.statusWarning?.setText("Recent alert: none").setColor("#9a7a58");
      return;
    }
    const title = errorTitle(currentError.code);
    const message = errorMessage(currentError);
    this.warningCard.setVisible(true);
    this.warningTitleTxt.setText(title).setVisible(true);
    this.warningBodyTxt.setText(message).setVisible(true);
    this.statusWarning?.setText(`Recent alert: ${title} — ${message}`).setColor(currentError.code === "hq_setup_complete" ? "#98d48a" : "#e0a070");
  }

  _toggleNukeArming() {
    const battle = this.gameState?.battle || {};
    const game = this.gameState?.game || {};
    const activeSide = battle.active_side || null;
    if (!activeSide) return;
    const activeTier = activeSide === "p1" ? (game.tier_p1 ?? 0) : (game.tier_p2 ?? 0);
    const nukeUsed = activeSide === "p1" ? !!game.nuke_used_p1 : !!game.nuke_used_p2;
    if (activeTier < 4 || nukeUsed) return;
    this._nukeArmingSide = this._nukeArmingSide === activeSide ? null : activeSide;
    playSfx(this, "sfx_select");
  }

  _updateNukeUi(s) {
    const battle = s?.battle || {};
    const game = s?.game || {};
    const activeSide = battle.active_side || null;
    if (this._nukeArmingSide && activeSide !== this._nukeArmingSide) this._nukeArmingSide = null;

    if (!activeSide) {
      this.nukeBtn.setVisible(false);
      return;
    }

    const activeTier = activeSide === "p1" ? (game.tier_p1 ?? 0) : (game.tier_p2 ?? 0);
    const nukeUsed = activeSide === "p1" ? !!game.nuke_used_p1 : !!game.nuke_used_p2;
    const isArming = this._nukeArmingSide === activeSide;
    const canArm = activeTier >= 4 && !nukeUsed;
    this.nukeBtn
      .setVisible(true)
      .setText(isArming ? "Cancel Nuke" : (nukeUsed ? "Nuke Spent" : "Arm Nuke"))
      .setColor(canArm || isArming ? "#ffd070" : "#8a7a68")
      .setBackgroundColor(canArm || isArming ? "#2a120c" : "#241812")
      .setAlpha(canArm || isArming ? 1 : 0.45);

    if (isArming) {
      this.statusBattle?.setText(`${sideLabel(activeSide)} nuke armed. Click an enemy cell to center the 3x3 strike.`).setColor("#ffd878");
    }
  }

  _handleBoardPointerDown(pointer) {
    if (this._helpVisible) return;
    if (this.gameState?.phase !== "game" || !this._nukeArmingSide) return;
    const col = Math.floor((pointer.x - BOARD_OFF_X) / CELL);
    const row = Math.floor((pointer.y - BOARD_OFF_Y) / CELL);
    if (col < 0 || col >= GRID_SIZE || row < 0 || row >= GRID_SIZE) return;

    const enemySide = this._nukeArmingSide === "p1" ? "p2" : "p1";
    if (sideOwnsCell(enemySide, col, row)) {
      this.ws?.send("trigger_nuke", { side: this._nukeArmingSide, position: { x: col, y: row } });
      playSfx(this, "sfx_select");
    }
    this._nukeArmingSide = null;
  }

  _updateWinBanner(G) {
    if (this._helpVisible) {
      this.winBanner.setVisible(false);
      return;
    }
    const winner = G?.winner;
    if (!winner) {
      this.winBanner.setVisible(false);
      return;
    }

    const msgs = {
      homestead_destroyed: ["THE MOB WINS", "Old Mick's homestead burns — no shelter, no grain."],
      nest_destroyed: ["OLD MICK WINS", "The hidden Nest is gone. The emu breeding heart is dead."],
      attrition: winner === "p1"
        ? ["OLD MICK WINS", "Feeding grounds razed. The Mob starves."]
        : ["THE MOB WINS", "Paddocks trampled. Old Mick can't fund another shot."],
    };
    const [title, sub] = msgs[G.win_reason] || [`${winner.toUpperCase()} WINS`, ""];
    this._winBannerTitle.setText(title);
    this._winBannerSub.setText(sub);
    if (!this.winBanner.visible) {
      this.winBanner.setScale(0.75);
      this.tweens.add({ targets: this.winBanner, scale: 1, duration: 320, ease: "Back.easeOut" });
    }
    this.winBanner.setVisible(true);
  }

  _drawDefZone(defCol, defRow, tier, color) {
    const rad = tier >= 2 ? 2 : 1;
    const size = (rad * 2 + 1) * CELL;
    const x = BOARD_OFF_X + (defCol - rad) * CELL;
    const y = BOARD_OFF_Y + (defRow - rad) * CELL;
    this.dynGfx.fillStyle(color, 0.10);
    this.dynGfx.fillRect(x, y, size, size);
    this.dynGfx.lineStyle(2, color, 0.65);
    this.dynGfx.strokeRect(x, y, size, size);
  }

  _drawPendingHqCandidate(phase, setup = {}) {
    if (phase !== "hq_placement") return;
    const activeSide = setup.active_setup_side;
    const marker = this.gameState?.hq_markers?.[activeSide] || null;
    if (!activeSide || !marker || marker.col == null || marker.row == null || marker.stale) return;

    const { col, row } = marker;
    const isValid = isValidHqPlacementCell(activeSide, col, row, this.gameState?.terrain);
    const x = BOARD_OFF_X + col * CELL + 2;
    const y = BOARD_OFF_Y + row * CELL + 2;
    const ring = isValid ? (activeSide === "p2" ? 0xb8ff60 : 0xffdc70) : 0xff7070;
    const cx = x + (CELL - 4) / 2;
    const cy = y + (CELL - 4) / 2;
    const pulse = 0.55 + 0.20 * Math.sin(this.time.now / 170);

    this.dynGfx.fillStyle(0x120904, 0.25);
    this.dynGfx.fillRoundedRect(x, y, CELL - 4, CELL - 4, 5);
    this.dynGfx.lineStyle(3, ring, pulse);
    this.dynGfx.strokeRoundedRect(x, y, CELL - 4, CELL - 4, 5);
    this.dynGfx.lineStyle(1.5, isValid ? 0xffffff : 0xffd0d0, 0.82);
    this.dynGfx.strokeCircle(cx, cy, CELL * 0.18);
  }

  _drawRay(startCol, startRow, rayCells) {
    if (!rayCells?.length) return;
    const g = this.dynGfx;
    for (const cell of rayCells) {
      const x = BOARD_OFF_X + cell.col * CELL;
      const y = BOARD_OFF_Y + cell.row * CELL;
      if (cell.type === "path")      g.fillStyle(COLORS.attackRay, 0.18);
      else if (cell.type === "hit")  g.fillStyle(COLORS.attackRayHit, 0.42);
      else if (cell.type === "soft") g.fillStyle(0xffa040, 0.34);
      else                            g.fillStyle(0x303030, 0.60);
      g.fillRect(x + 1, y + 1, CELL - 2, CELL - 2);
    }

    let px = BOARD_OFF_X + startCol * CELL + CELL / 2;
    let py = BOARD_OFF_Y + startRow * CELL + CELL / 2;
    for (const cell of rayCells) {
      const cx = BOARD_OFF_X + cell.col * CELL + CELL / 2;
      const cy = BOARD_OFF_Y + cell.row * CELL + CELL / 2;
      g.lineStyle(cell.type === "path" ? 2 : 2.5, cell.type === "blocked" ? 0xff2200 : COLORS.attackRay, 0.95);
      g.strokeLineShape(new Phaser.Geom.Line(px, py, cx, cy));
      px = cx;
      py = cy;
    }

    const last = rayCells[rayCells.length - 1];
    const { x, y } = cellXY(last.col, last.row);
    if (last.type === "hit" || last.type === "blocked") {
      g.lineStyle(3, last.type === "blocked" ? 0xff2200 : 0xffffff, 0.95);
      g.strokeLineShape(new Phaser.Geom.Line(x - 12, y - 12, x + 12, y + 12));
      g.strokeLineShape(new Phaser.Geom.Line(x + 12, y - 12, x - 12, y + 12));
    } else if (last.type === "soft") {
      g.fillStyle(0xffd080, 0.95);
      g.fillTriangle(x, y - 12, x - 12, y + 10, x + 12, y + 10);
    }
  }

  _renderHUD() {
    const s = this.gameState;
    if (!s) return;
    const G = s.game || {};
    const setup = s.setup || {};
    const battle = s.battle || {};
    const inBattle = s.phase === "game" || s.phase == null;
    const tierThresholds = Array.isArray(G.tier_thresholds) ? G.tier_thresholds : [6, 14, 22, 32];
    const nextThreshold = (tier) => tier >= 4 ? null : tierThresholds[tier] ?? null;

    if (!inBattle) {
      this.statusTurn?.setText(`Phase:          ${phaseLabel(s.phase)}`).setColor("#f0d070");
      this.statusScore?.setText("Setup: backend-guided hidden HQ flow").setColor("#d8c890");
      this.statusBattle?.setText(`Status: ${setup.status_message || "Waiting for setup state"}`).setColor("#d8c890");
    } else if (battle.active_side === "p1") {
      this.statusTurn?.setText(`Turn:           Old Mick positioning`).setColor("#f8d060");
      this.statusScore?.setText(`Paddock score: ${G.score_p2_attrition ?? 0}/${G.attrition_threshold ?? 40}   Feeding ground score: ${G.score_p1_attrition ?? 0}/${G.attrition_threshold ?? 40}`).setColor("#ffb060");
      this.statusBattle?.setText(`Status: ${battle.status_message || "Scan ID4 to attack."}`).setColor("#ffd878");
    } else if (battle.active_side === "p2") {
      this.statusTurn?.setText(`Turn:           The Mob positioning`).setColor("#90ee40");
      this.statusScore?.setText(`Paddock score: ${G.score_p2_attrition ?? 0}/${G.attrition_threshold ?? 40}   Feeding ground score: ${G.score_p1_attrition ?? 0}/${G.attrition_threshold ?? 40}`).setColor("#ffb060");
      this.statusBattle?.setText(`Status: ${battle.status_message || "Scan ID4 to attack."}`).setColor("#b8ff78");
    } else {
      this.statusTurn?.setText(`Turn:           ${battle.waiting_for_side ? `waiting for ${sideLabel(battle.waiting_for_side)}` : "waiting for first side"}`).setColor("#c8b080");
      this.statusScore?.setText(`Paddock score: ${G.score_p2_attrition ?? 0}/${G.attrition_threshold ?? 40}   Feeding ground score: ${G.score_p1_attrition ?? 0}/${G.attrition_threshold ?? 40}`).setColor("#ffb060");
      this.statusBattle?.setText(`Status: ${battle.status_message || "Waiting for battle state"}`).setColor("#d8c890");
    }

    this.statusCorners?.setText(`Corners:        ${s.corners_found ?? 0}/4`);
    const nextP1 = nextThreshold(G.tier_p1 ?? 0);
    const nextP2 = nextThreshold(G.tier_p2 ?? 0);
    this.statusTier?.setText(`Tier P1: ${G.tier_p1 ?? 0}${(G.tier_p1 ?? 0) === 4 ? " *" : nextP1 != null ? ` (${G.progress_p1 ?? 0}/${nextP1})` : ""}   Tier P2: ${G.tier_p2 ?? 0}${(G.tier_p2 ?? 0) === 4 ? " *" : nextP2 != null ? ` (${G.progress_p2 ?? 0}/${nextP2})` : ""}`);

    if (G.winner) {
      this.statusWinner?.setText(
        `★ WINNER: ${G.winner.toUpperCase()} (${G.win_reason ?? "—"})`);
    } else {
      this.statusWinner?.setText("");
    }
  }

  // ─── Frame render ─────────────────────────────────────────────────────

  _render() {
    const s = this.gameState;
    if (!s) return;

    const G = s.game || {};
    const inBattle = s.phase === "game" || s.phase == null;

    // Resources only redraw when the seed changes
    if (s.terrain && s.map_seed !== this._lastSeed) {
      this._renderResources(s.terrain);
      this._lastSeed = s.map_seed;
    }
    this._renderDamage(G);
    this.dynGfx.clear();

    const hardMap = {};
    const softMap = {};
    const { p1: p1ResourceMap, p2: p2ResourceMap } = buildResourceMaps(s.terrain);
    const softGoneKeys = new Set((G.soft_gone || []).map(([c, r]) => `${c},${r}`));
    for (const t of ([...(s.terrain?.p1_hard || []), ...(s.terrain?.p2_hard || [])])) hardMap[`${t.col},${t.row}`] = t;
    for (const t of ([...(s.terrain?.p1_soft || []), ...(s.terrain?.p2_soft || [])])) {
      if (!softGoneKeys.has(`${t.col},${t.row}`)) softMap[`${t.col},${t.row}`] = t;
    }
    const destroyedMap = {};
    for (const [c, r] of (G.destroyed || [])) destroyedMap[`${c},${r}`] = true;

    if (inBattle && s.p1?.def?.col != null) this._drawDefZone(s.p1.def.col, s.p1.def.row, G.tier_p1 ?? 0, 0xe8d060);
    if (inBattle && s.p2?.def?.col != null) this._drawDefZone(s.p2.def.col, s.p2.def.row, G.tier_p2 ?? 0, 0x60e8a0);
    if (inBattle) {
      for (const role of ["atk_a", "atk_b"]) {
        if (s.p1?.[role]?.col != null && s.p1[role].direction) {
          this._drawRay(s.p1[role].col, s.p1[role].row, computeRay(s.p1[role].col, s.p1[role].row, s.p1[role].direction, hardMap, softMap, "p1", destroyedMap, p2ResourceMap));
        }
        if (s.p2?.[role]?.col != null && s.p2[role].direction) {
          this._drawRay(s.p2[role].col, s.p2[role].row, computeRay(s.p2[role].col, s.p2[role].row, s.p2[role].direction, hardMap, softMap, "p2", destroyedMap, p1ResourceMap));
        }
      }
    }
    this._drawPendingHqCandidate(s.phase, s.setup || {});

    this._renderTokens(s.p1, s.p2, inBattle);
    this._renderHelpUi(s.help || {});
    this._renderSetupUi(s.phase, s.setup || {});
    this._renderWarning(s.errors || []);
    this._updateNukeUi(s);
    this._updateWinBanner(G);
    this._renderHUD();
  }

  // ─── WS binding ───────────────────────────────────────────────────────

  _bindWS() {
    if (!this.ws) return;
    this._stateHandler = (s) => { this.gameState = s; };
    this.ws.on("state", this._stateHandler);

    // Map game events to SFX. The events array arrives inside each state
    // payload, and the WSClient re-emits it as a synthetic 'events' event.
    this._eventsHandler = (events) => {
      for (const ev of events) {
        switch (ev.type) {
          case "cell_damaged":
            // C — 2-HP cell (DEF zone) chip vs single-HP cell hit:
            // the splash flag and required_hp tell us which.
            if ((ev.required_hp ?? 1) >= 2) playSfx(this, "sfx_first_hit");
            else                            playSfx(this, "sfx_p1_attack"); // generic attack
            break;
          case "cell_destroyed":   playSfx(this, "sfx_destroy");   break;  // C: final hit
          case "soft_destroyed":
          case "blocked_hard":     playSfx(this, "sfx_block");     break;
          case "hq_destroyed":     playSfx(this, "sfx_explosion"); break;
          case "nuke_triggered":   playSfx(this, "sfx_explosion"); break;
          case "attrition_win":    playSfx(this, "sfx_victory");   break;
        }
      }
    };
    this.ws.on("events", this._eventsHandler);

    // D — Tier up: detect change between successive states.
    // E — Game end: detect winner field flipping from null → side.
    this._prevTiers  = { p1: 0, p2: 0 };
    this._prevWinner = null;
    this._tierWinHandler = (s) => {
      const G = s.game || {};
      if ((G.tier_p1 ?? 0) > this._prevTiers.p1) playSfx(this, "sfx_tier_up");
      if ((G.tier_p2 ?? 0) > this._prevTiers.p2) playSfx(this, "sfx_tier_up");
      this._prevTiers.p1 = G.tier_p1 ?? 0;
      this._prevTiers.p2 = G.tier_p2 ?? 0;

      if (G.winner && !this._prevWinner) {
        // Generic finish ping — the per-side victory/defeat sound is
        // played by `attrition_win` / `hq_destroyed` events above already,
        // but if we ever miss the event, this guarantees a sound on win.
        playSfx(this, "sfx_victory");
      }
      this._prevWinner = G.winner ?? null;
    };
    this.ws.on("state", this._tierWinHandler);
  }

  // ─── Mute toggle button (top-right corner of canvas) ──────────────────

  _buildMuteButton() {
    const x = CANVAS_W - 24, y = 28;
    const btn = this.add.text(x, y, "🔊", {
      fontFamily: "monospace", fontSize: "18px",
      color: "#fff0d0",
    }).setOrigin(0.5).setDepth(50)
      .setInteractive({ useHandCursor: true });

    btn.on("pointerdown", () => {
      const muted = toggleMute();
      btn.setText(muted ? "🔇" : "🔊");
      // Re-cue BGM if user un-muted after the IntroScene autostart slot
      if (!muted) playBgm(this, "bgm_outback");
    });
  }
}
