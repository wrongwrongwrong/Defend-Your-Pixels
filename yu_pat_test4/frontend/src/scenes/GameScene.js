/**
 * GameScene — board rendering only.
 *
 * Phaser renders: board image, grid, terrain tiles, token sprites,
 * HQ sprites, attack rays, defence zones, HQ placement rings,
 * win overlay (board-centered), tutorial overlay.
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

function computeRay(startCol, startRow, dir, hardMap, softMap, attackerSide, destroyedMap) {
  if (!dir || !DIR_VEC[dir]) return [];
  const [dc, dr] = DIR_VEC[dir];
  const isEnemy  = attackerSide === "p1" ? isP2Cell : isP1Cell;
  const cells    = [];
  let c = startCol + dc, r = startRow + dr;
  while (c >= 0 && c < GRID_SIZE && r >= 0 && r < GRID_SIZE) {
    const key = `${c},${r}`;
    if (hardMap[key])                        { cells.push({ col: c, row: r, type: "blocked" }); break; }
    if (softMap[key])                        { cells.push({ col: c, row: r, type: "soft"    }); break; }
    if (isEnemy(c, r) && !destroyedMap[key]) { cells.push({ col: c, row: r, type: "hit"     }); break; }
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
  }

  create() {
    this.boardGfx    = this.add.graphics().setDepth(0);
    this.resourceGfx = this.add.graphics().setDepth(1);
    this.dmgGfx      = this.add.graphics().setDepth(2);
    this.dynGfx      = this.add.graphics().setDepth(3);

    this._buildBoardImage();
    this._drawGridOnce();

    this.anims.create({
      key: "mick_def_idle",
      frames: this.anims.generateFrameNumbers("tok_mick_def", { start: 0, end: 1 }),
      frameRate: 4,
      repeat: -1,
    });

    this._buildTokenSprites();
    this._buildHqSprites();
    this._buildWinOverlay();
    this._buildTutorialOverlay();
    this._bindWS();

    this.input.on("pointerdown", this._handleBoardClick, this);

    this.input.keyboard.on("keydown-N", () => this.ws?.send("demo_next", {}));

    this.time.addEvent({ delay: 33, loop: true, callback: () => this._render() });
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
      if (key === "p1_def") {
        this.tokenSprites[key] = this.add.sprite(0, 0, tex)
          .setDisplaySize(sz, sz).setDepth(11).setVisible(false);
        this.tokenSprites[key].play("mick_def_idle");
      } else {
        this.tokenSprites[key] = this.add.image(0, 0, tex)
          .setDisplaySize(sz, sz).setDepth(11).setVisible(false);
      }

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

  // ══════════════════════════════════════════════════════════════════════════════
  // Render
  // ══════════════════════════════════════════════════════════════════════════════

  _render() {
    const s = this.gameState;
    if (!s) return;

    const G        = s.game   || {};
    const battle   = s.battle || {};
    const inBattle = s.phase === "game" || s.phase == null;

    if (s.terrain && s.map_seed !== this._lastSeed) {
      this._renderResources(s.terrain);
      this._lastSeed = s.map_seed;
    }

    this._renderDamage(G);

    this.dynGfx.clear();
    const { hardMap, softMap, destroyedMap } = this._buildMaps(s);

    if (inBattle) {
      if (s.p1?.def?.col != null)
        this._drawDefZone(s.p1.def.col, s.p1.def.row, G.tier_p1 ?? 0, 0xe8d060);
      if (s.p2?.def?.col != null)
        this._drawDefZone(s.p2.def.col, s.p2.def.row, G.tier_p2 ?? 0, 0x60e8a0);

      for (const role of ["atk_a", "atk_b"]) {
        if (s.p1?.[role]?.col != null && s.p1[role].direction)
          this._drawRay(s.p1[role].col, s.p1[role].row,
            computeRay(s.p1[role].col, s.p1[role].row, s.p1[role].direction,
                       hardMap, softMap, "p1", destroyedMap));
        if (s.p2?.[role]?.col != null && s.p2[role].direction)
          this._drawRay(s.p2[role].col, s.p2[role].row,
            computeRay(s.p2[role].col, s.p2[role].row, s.p2[role].direction,
                       hardMap, softMap, "p2", destroyedMap));
      }
    }

    this._drawHqPlacementRings(s);
    this._renderTokens(s.p1, s.p2, inBattle, G);
    this._renderHqSprites(s, G);
    this._renderWinOverlay(G);
    this._renderTutorial(s.tutorial);
  }

  // ─── Resources / terrain ────────────────────────────────────────────────────

  _renderResources(terrain) {
    for (const sp of this._terrainSprites) sp.destroy();
    this._terrainSprites = [];
    this.resourceGfx.clear();
    if (!terrain) return;

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
    for (const t of terrain.p1_hard      || []) place(t.col, t.row, "hard_mick");
    for (const t of terrain.p2_hard      || []) place(t.col, t.row, "hard_emu");
    for (const t of terrain.p1_soft      || []) place(t.col, t.row, "soft_mick");
    for (const t of terrain.p2_soft      || []) place(t.col, t.row, "soft_emu");

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

    for (const [c, r] of (G.destroyed || [])) {
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
    const rad  = tier >= 2 ? 2 : 1;
    const cw   = GRID_DRAW_W / GRID_SIZE, ch = GRID_DRAW_H / GRID_SIZE;
    const size = rad * 2 + 1;
    const x    = BOARD_OFF_X + GRID_INSET_X + (col - rad) * cw;
    const y    = BOARD_OFF_Y + GRID_INSET_Y + (row - rad) * ch;
    this.dynGfx.fillStyle(color, 0.09);  this.dynGfx.fillRect(x, y, size * cw, size * ch);
    this.dynGfx.lineStyle(2, color, 0.55); this.dynGfx.strokeRect(x, y, size * cw, size * ch);
  }

  // ─── Attack ray ─────────────────────────────────────────────────────────────

  _drawRay(startCol, startRow, rayCells) {
    if (!rayCells?.length) return;
    const g  = this.dynGfx;
    const cw = GRID_DRAW_W / GRID_SIZE, ch = GRID_DRAW_H / GRID_SIZE;

    for (const cell of rayCells) {
      const bx = BOARD_OFF_X + GRID_INSET_X + cell.col * cw;
      const by = BOARD_OFF_Y + GRID_INSET_Y + cell.row * ch;
      if      (cell.type === "path")    g.fillStyle(COLORS.attackRay,    0.16);
      else if (cell.type === "hit")     g.fillStyle(COLORS.attackRayHit, 0.55);
      else if (cell.type === "soft")    g.fillStyle(0xff6000, 0.45);
      else                              g.fillStyle(0x1a0000, 0.60);
      g.fillRect(bx + 1, by + 1, cw - 2, ch - 2);
    }

    let px = cellXY(startCol, startRow).x, py = cellXY(startCol, startRow).y;
    for (const cell of rayCells) {
      const { x: cx, y: cy } = cellXY(cell.col, cell.row);
      const isPath = cell.type === "path";
      g.lineStyle(isPath ? 5 : 6, 0x000000, 0.55);
      g.strokeLineShape(new Phaser.Geom.Line(px, py, cx, cy));
      g.lineStyle(isPath ? 3 : 3.5, COLORS.attackRay, 1.0);
      g.strokeLineShape(new Phaser.Geom.Line(px, py, cx, cy));
      px = cx; py = cy;
    }

    const last    = rayCells[rayCells.length - 1];
    const { x, y } = cellXY(last.col, last.row);
    if (last.type === "hit" || last.type === "blocked") {
      const cross = () => {
        g.strokeLineShape(new Phaser.Geom.Line(x - 13, y - 13, x + 13, y + 13));
        g.strokeLineShape(new Phaser.Geom.Line(x + 13, y - 13, x - 13, y + 13));
      };
      g.lineStyle(6, 0x000000, 0.7); cross();
      g.lineStyle(3.5, last.type === "blocked" ? 0xff2200 : COLORS.attackRayHit, 1); cross();
    }
  }

  // ─── HQ placement rings ─────────────────────────────────────────────────────

  _drawHqPlacementRings(s) {
    const cw = GRID_DRAW_W / GRID_SIZE, ch = GRID_DRAW_H / GRID_SIZE;
    for (const side of ["p1", "p2"]) {
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

  static _dirAngle(dir) {
    return { E: 0, SE: 45, S: 90, SW: 135, W: 180, NW: -135, N: -90, NE: -45 }[dir] ?? 0;
  }
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
      const tier     = side === "p1" ? (G?.tier_p1 ?? 0) : (G?.tier_p2 ?? 0);

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

      const angle = (GameScene._isAtkKey(key) && tok.direction)
        ? GameScene._dirAngle(tok.direction) : 0;

      sprite.setPosition(x, y - 1).setAngle(angle).setAlpha(alpha).setVisible(true);

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
    if (!tut?.active) { this.tutorialContainer.setVisible(false); return; }

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
    const hardMap = {}, softMap = {};
    const softGoneKeys = new Set((s.game?.soft_gone || []).map(([c, r]) => `${c},${r}`));

    for (const t of [...(s.terrain?.p1_hard || []), ...(s.terrain?.p2_hard || [])])
      hardMap[`${t.col},${t.row}`] = t;
    for (const t of [...(s.terrain?.p1_soft || []), ...(s.terrain?.p2_soft || [])]) {
      if (!softGoneKeys.has(`${t.col},${t.row}`)) softMap[`${t.col},${t.row}`] = t;
    }

    const destroyedMap = {};
    for (const [c, r] of (s.game?.destroyed || [])) destroyedMap[`${c},${r}`] = true;

    return { hardMap, softMap, destroyedMap };
  }

  // ─── Board click (nuke targeting) ────────────────────────────────────────────

  _handleBoardClick(pointer) {
    if (this.gameState?.phase !== "game" || !this._nukeArmingSide) return;
    const cw  = GRID_DRAW_W / GRID_SIZE, ch = GRID_DRAW_H / GRID_SIZE;
    const col = Math.floor((pointer.x - BOARD_OFF_X - GRID_INSET_X) / cw);
    const row = Math.floor((pointer.y - BOARD_OFF_Y - GRID_INSET_Y) / ch);
    if (col < 0 || col >= GRID_SIZE || row < 0 || row >= GRID_SIZE) return;

    const onEnemy = this._nukeArmingSide === "p1" ? isP2Cell(col, row) : isP1Cell(col, row);
    if (onEnemy) {
      this.ws?.send("trigger_nuke", { side: this._nukeArmingSide, position: { x: col, y: row } });
      playSfx(this, "sfx_select");
    }
    this._nukeArmingSide = null;
  }

  // ─── WebSocket binding ───────────────────────────────────────────────────────

  _bindWS() {
    if (!this.ws) return;

    this.ws.on("state", (s) => { this.gameState = s; });

    this.ws.on("events", (events) => {
      for (const ev of events) {
        switch (ev.type) {
          case "cell_damaged":   playSfx(this, (ev.required_hp ?? 1) >= 2 ? "sfx_first_hit" : "sfx_p1_attack"); break;
          case "cell_destroyed": playSfx(this, "sfx_destroy");   break;
          case "soft_destroyed":
          case "blocked_hard":   playSfx(this, "sfx_block");     break;
          case "hq_destroyed":   playSfx(this, "sfx_explosion"); break;
          case "nuke_triggered": playSfx(this, "sfx_explosion"); break;
          case "attrition_win":  playSfx(this, "sfx_victory");   break;
        }
      }
    });
  }
}
