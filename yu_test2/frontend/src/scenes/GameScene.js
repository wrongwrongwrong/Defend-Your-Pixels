import {
  GRID_SIZE, CELL, BOARD_OFF_X, BOARD_OFF_Y,
  CANVAS_W, CANVAS_H, COLORS, DIR_VEC, ARROW_CHAR,
} from "../constants.js";

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

function cellXY(col, row) {
  return {
    x: BOARD_OFF_X + col * CELL + CELL / 2,
    y: BOARD_OFF_Y + row * CELL + CELL / 2,
  };
}

export class GameScene extends Phaser.Scene {
  constructor() { super("Game"); }

  init(data) {
    this.ws            = data.ws;
    this._initialState = data.initialState ?? null;
    this.gameState     = null;
    this._lastSeed     = null;
  }

  create() {
    this.boardGfx    = this.add.graphics().setDepth(0);
    this.resourceGfx = this.add.graphics().setDepth(1);
    this.dmgGfx      = this.add.graphics().setDepth(2);
    this.dynGfx      = this.add.graphics().setDepth(3);

    this._createTokenTextures();
    this._buildBoard();
    this._buildHUD();
    this._buildTokenSprites();
    this._buildArrows();
    this._bindWS();

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

  _renderTokens(p1, p2) {
    const g = this.dynGfx;
    g.clear();

    const drawToken = (key, tok) => {
      const sprite = this.tokenSprites[key];
      const arrow  = this.arrows[key];
      const badge  = this.tokenBadges[key];
      const visible = tok && tok.col != null && tok.row != null;

      if (!visible) {
        sprite.setVisible(false);
        if (arrow) arrow.setVisible(false);
        if (badge) badge.setVisible(false);
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

      // ATK direction arrow
      if (arrow) {
        if (tok.direction && DIR_VEC[tok.direction]) {
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
    this.statusScore   = text(baseY + 36,   "P1 razed: 0   P2 razed: 0");
    this.statusTier    = text(baseY + 54,   "Tier P1: 0   Tier P2: 0");
    this.statusWinner  = text(baseY + 78,   "", {
      color: "#f0d070", fontSize: "14px", fontStyle: "bold",
    });

    this.add.text(CANVAS_W / 2, CANVAS_H - 28,
      "yu_test2 — tokens live · rays/win banner pending", {
        fontFamily: "monospace", fontSize: "10px",
        color: "#5a3a10",
      }).setOrigin(0.5);
  }

  _renderHUD() {
    const s = this.gameState;
    if (!s) return;
    const G = s.game || {};
    this.statusTurn?.setText(`Turn:           ${s.turn ? `P${s.turn}` : "—"}`);
    this.statusCorners?.setText(`Corners:        ${s.corners_found ?? 0}/4`);

    const s1 = G.score_p2_destroyed ?? 0;
    const s2 = G.score_p1_destroyed ?? 0;
    this.statusScore?.setText(`P1 razed: ${s1}   P2 razed: ${s2}`);

    this.statusTier?.setText(
      `Tier P1: ${G.tier_p1 ?? 0}   Tier P2: ${G.tier_p2 ?? 0}`);

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

    // Resources only redraw when the seed changes
    if (s.terrain && s.map_seed !== this._lastSeed) {
      this._renderResources(s.terrain);
      this._lastSeed = s.map_seed;
    }
    this._renderDamage(s.game);
    this._renderTokens(s.p1, s.p2);
    this._renderHUD();
  }

  // ─── WS binding ───────────────────────────────────────────────────────

  _bindWS() {
    if (!this.ws) return;
    this._stateHandler = (s) => { this.gameState = s; };
    this.ws.on("state", this._stateHandler);
  }
}
