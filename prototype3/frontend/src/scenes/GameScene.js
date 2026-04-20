import {
  GRID_SIZE, CELL, BOARD_OFF_X, BOARD_OFF_Y,
  CANVAS_W, CANVAS_H, LOG_Y, BUTTON_Y,
  COLORS, PLAYER_NAMES, SIDE_NAMES, TOKEN_NAMES, TERRAIN_NAMES
} from "../constants.js";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function cellXY(col, row) {
  return {
    x: BOARD_OFF_X + col * CELL + CELL / 2,
    y: BOARD_OFF_Y + row * CELL + CELL / 2,
  };
}

function drawDashed(g, x1, y1, x2, y2, dash = 6, gap = 5) {
  const dx = x2 - x1, dy = y2 - y1;
  const len = Math.hypot(dx, dy);
  if (len === 0) return;
  const ux = dx / len, uy = dy / len;
  let d = 0, on = true;
  while (d < len) {
    const seg = Math.min(on ? dash : gap, len - d);
    if (on) {
      g.strokeLineShape(new Phaser.Geom.Line(
        x1 + ux * d, y1 + uy * d,
        x1 + ux * (d + seg), y1 + uy * (d + seg)
      ));
    }
    d += seg;
    on = !on;
  }
}

// ─── Scene ───────────────────────────────────────────────────────────────────

export class GameScene extends Phaser.Scene {
  constructor() { super("Game"); }

  init(data) {
    this.ws = data.ws;
    this._initialState = data.initialState ?? null;
    this.gameState = null;
    this.preview = null;
    this._log = [];
    this._tokenObjs = [];
    this._baseObjs = [];
    this._animating = false;
    this._pendingState = null;
    this._movedThisTurn = new Set();
    this._prevTurnPlayer = null;
    this._terrainObjs = [];
  }

  create() {
    this._createParticleTextures();
    this._createTokenTextures();
    this._buildBoard();
    this._buildLayers();
    this._buildTurnBanner();
    this._buildButtons();
    this._buildLog();
    this._bindWS();
    // Apply state passed from IntroScene so we never block on LOADING
    if (this._initialState) {
      this.gameState = this._initialState;
      this._render();
    }
  }

  // ─── Static board (drawn once) ───────────────────────────────────────────

  _buildBoard() {
    const g = this.add.graphics();

    // Base territory fill — muted ground color, active cells overlaid later
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
      g.strokeLineShape(new Phaser.Geom.Line(x, BOARD_OFF_Y, x, BOARD_OFF_Y + GRID_SIZE * CELL));
      g.strokeLineShape(new Phaser.Geom.Line(BOARD_OFF_X, y, BOARD_OFF_X + GRID_SIZE * CELL, y));
    }

    // Diagonal boundary — thick dark line with tick marks
    const bx1 = BOARD_OFF_X, by1 = BOARD_OFF_Y;
    const bx2 = BOARD_OFF_X + GRID_SIZE * CELL, by2 = BOARD_OFF_Y + GRID_SIZE * CELL;
    g.lineStyle(3, COLORS.diagonal, 1);
    g.strokeLineShape(new Phaser.Geom.Line(bx1, by1, bx2, by2));

    // Tick marks along diagonal every 2 cells
    g.lineStyle(2, COLORS.diagonalTick, 0.9);
    for (let i = 1; i < GRID_SIZE; i++) {
      const cx = BOARD_OFF_X + i * CELL;
      const cy = BOARD_OFF_Y + i * CELL;
      const perp = 6;
      g.strokeLineShape(new Phaser.Geom.Line(cx - perp, cy + perp, cx + perp, cy - perp));
    }

    // Coordinate labels
    const labelStyle = { fontFamily: "monospace", fontSize: "10px", color: "#6b5030" };
    for (let i = 0; i < GRID_SIZE; i++) {
      const lx = BOARD_OFF_X + i * CELL + CELL / 2;
      const ly = BOARD_OFF_Y + i * CELL + CELL / 2;
      this.add.text(lx, BOARD_OFF_Y - 16, String.fromCharCode(65 + i), labelStyle).setOrigin(0.5);
      this.add.text(BOARD_OFF_X - 18, ly, String(i + 1), labelStyle).setOrigin(0.5);
    }
  }

  _buildLayers() {
    this.lyrActive    = this.add.graphics();    // active territory (wheat/feeding cells)
    this.lyrDestroyed = this.add.graphics();
    this.lyrTerrain   = this.add.graphics();
    this.lyrDefense   = this.add.graphics();
    this.lyrRays      = this.add.graphics();
    this.lyrTokenBg   = this.add.graphics();
    this.lyrHits      = this.add.graphics();
  }

  // ─── Turn banner ─────────────────────────────────────────────────────────

  _buildTurnBanner() {
    const cx = CANVAS_W / 2;
    this.bannerG = this.add.graphics();
    this.bannerText = this.add.text(cx, 24, "LOADING...", {
      fontFamily: "serif",
      fontSize: "15px",
      fontStyle: "bold",
      color: "#" + COLORS.turnBannerText.toString(16).padStart(6, "0"),
      letterSpacing: 2,
    }).setOrigin(0.5);
    this._updateBanner("LOADING...");
  }

  _updateBanner(text) {
    this.bannerText?.setText(text);
    const tw = this.bannerText?.width ?? 120;
    const g = this.bannerG;
    g.clear();
    const cx = CANVAS_W / 2, cy = 24, pw = tw + 40, ph = 28, r = 14;
    g.fillStyle(COLORS.turnBanner, 1);
    g.fillRoundedRect(cx - pw / 2, cy - ph / 2, pw, ph, r);
    g.lineStyle(1.5, 0xd4a030, 0.6);
    g.strokeRoundedRect(cx - pw / 2, cy - ph / 2, pw, ph, r);
  }

  // ─── Buttons ─────────────────────────────────────────────────────────────

  _buildButtons() {
    const y = BUTTON_Y;
    const halfW = CANVAS_W / 2;

    // End Turn button (left half)
    const btnEnd = this._makeButton(halfW / 2, y, halfW - 20, 40, "End Turn");
    btnEnd.on("pointerdown", () => {
      const err = this._resolveError();
      if (err) { this._showErrorToast(err); return; }
      this.ws?.send("resolve_turn", {});
    });

    // Pass button (right half)
    const btnPass = this._makeButton(halfW + halfW / 2, y, halfW - 20, 40, "Pass");
    btnPass.on("pointerdown", () => this.ws?.send("resolve_turn", { pass: true }));
  }

  _makeButton(x, y, w, h, label) {
    const g = this.add.graphics();
    g.fillStyle(COLORS.btnMain, 1);
    g.fillRoundedRect(x - w / 2, y - h / 2, w, h, 8);
    g.lineStyle(1.5, COLORS.btnBorder, 1);
    g.strokeRoundedRect(x - w / 2, y - h / 2, w, h, 8);

    const txt = this.add.text(x, y, label, {
      fontFamily: "serif",
      fontSize: "16px",
      fontStyle: "bold",
      color: "#" + COLORS.btnText.toString(16).padStart(6, "0"),
    }).setOrigin(0.5).setInteractive({ useHandCursor: true });

    txt.on("pointerover", () => { g.clear(); g.fillStyle(0x3a2818, 1); g.fillRoundedRect(x-w/2,y-h/2,w,h,8); g.lineStyle(1.5,0x8a6030,1); g.strokeRoundedRect(x-w/2,y-h/2,w,h,8); });
    txt.on("pointerout",  () => { g.clear(); g.fillStyle(COLORS.btnMain,1); g.fillRoundedRect(x-w/2,y-h/2,w,h,8); g.lineStyle(1.5,COLORS.btnBorder,1); g.strokeRoundedRect(x-w/2,y-h/2,w,h,8); });

    return txt;
  }

  // ─── Game log ────────────────────────────────────────────────────────────

  _buildLog() {
    // Background strip
    const g = this.add.graphics();
    g.fillStyle(COLORS.logBg, 1);
    g.fillRect(0, LOG_Y - 8, CANVAS_W, BUTTON_Y - LOG_Y - 4);

    this.add.text(BOARD_OFF_X, LOG_Y - 4, "GAME LOG", {
      fontFamily: "monospace", fontSize: "9px",
      color: "#6b5030", letterSpacing: 2,
    });

    // 4 log card slots
    this._logCards = [];
    for (let i = 0; i < 4; i++) {
      const cy = LOG_Y + 14 + i * 34;
      const cardG = this.add.graphics();
      cardG.fillStyle(COLORS.logCard, 1);
      cardG.fillRoundedRect(BOARD_OFF_X, cy - 12, CANVAS_W - BOARD_OFF_X * 2, 28, 5);
      cardG.lineStyle(1, COLORS.logCardBorder, 1);
      cardG.strokeRoundedRect(BOARD_OFF_X, cy - 12, CANVAS_W - BOARD_OFF_X * 2, 28, 5);

      const dot  = this.add.graphics();
      const text = this.add.text(BOARD_OFF_X + 22, cy, "", {
        fontFamily: "monospace", fontSize: "11px", color: "#c8a878",
      }).setOrigin(0, 0.5);

      this._logCards.push({ dot, text, cy });
    }
  }

  _pushLog(color, message) {
    this._log.unshift({ color, message });
    if (this._log.length > 4) this._log.length = 4;
    this._refreshLog();
  }

  _refreshLog() {
    const dotColors = { red: 0xd04040, green: 0x40c060, yellow: 0xd4a030, gray: 0x6a5a4a };
    this._log.forEach((entry, i) => {
      const card = this._logCards[i];
      if (!card) return;
      const dc = dotColors[entry.color] ?? dotColors.gray;
      card.dot.clear();
      card.dot.fillStyle(dc, 1);
      card.dot.fillCircle(BOARD_OFF_X + 10, card.cy, 5);
      card.text.setText(entry.message).setAlpha(1 - i * 0.18);
    });
    // Clear unused cards
    for (let i = this._log.length; i < 4; i++) {
      this._logCards[i]?.dot.clear();
      this._logCards[i]?.text.setText("");
    }
  }

  // ─── WebSocket bindings ──────────────────────────────────────────────────

  _bindWS() {
    if (!this.ws) return;
    this.ws.on("board_state", d => {
      if (this._animating) { this._pendingState = d; return; }
      // Reset moved indicator when the turn changes player
      if (this._prevTurnPlayer !== null && d.current_player !== this._prevTurnPlayer) {
        this._movedThisTurn.clear();
      }
      // Track which tokens moved since last state
      if (this.gameState && d.current_player === this.gameState.current_player) {
        for (const [k, t] of Object.entries(d.tokens ?? {})) {
          const prev = this.gameState.tokens?.[k];
          if (prev && t.col >= 0 && (prev.col !== t.col || prev.row !== t.row)) {
            this._movedThisTurn.add(k);
          }
        }
      }
      this._prevTurnPlayer = d.current_player;
      this.gameState = d; this._render();
    });
    this.ws.on("marker_update", d => {
      if (!this.gameState) return;
      Object.assign(this.gameState.tokens, d.tokens);
      this._renderTokens();
    });
    this.ws.on("preview_state", d => { this.preview = d; this._renderRays(); });
    this.ws.on("resolve_error", d => this._showErrorToast(d.message));
    this.ws.on("attack_result", async d => {
      this._animating = true;
      this.lyrRays.clear();   // hide preview during animation
      await this._animateAttacks(d);
      this._animating = false;
      this._logAttackResult(d);
      if (this._pendingState) {
        this.gameState = this._pendingState;
        this._pendingState = null;
        this._render();
      }
    });
    this.ws.on("game_over", d => this._showGameOver(d));
  }

  // ─── Full render ─────────────────────────────────────────────────────────

  _render() {
    if (!this.gameState) return;
    const s = this.gameState;
    const phaseLabel = {
      terrain_placement: "TERRAIN SETUP",
      planning: "PLANNING",
      resolve: "RESOLVING...",
      game_over: "GAME OVER",
    }[s.phase] ?? s.phase.toUpperCase();

    const name = PLAYER_NAMES[s.current_player] ?? `Player ${s.current_player}`;
    this._updateBanner(`${name.toUpperCase()}'S TURN  ·  ${phaseLabel}`);

    this._renderActiveTerritory();
    this._renderDestroyed();
    this._renderTerrain();
    this._renderHiddenBases();
    this._renderTokens();
    this._renderRays();
  }

  // ─── Destroyed cells ─────────────────────────────────────────────────────

  _renderDestroyed() {
    const g = this.lyrDestroyed;
    g.clear();
    if (!this.gameState?.destroyed_cells) return;

    for (const [col, row] of this.gameState.destroyed_cells) {
      const bx = BOARD_OFF_X + col * CELL;
      const by = BOARD_OFF_Y + row * CELL;

      // Darker rubbled cell overlay
      g.fillStyle(COLORS.destroyed, 0.55);
      g.fillRect(bx, by, CELL, CELL);

      // Bold X mark
      const pad = 10;
      g.lineStyle(3, COLORS.destroyedX, 0.85);
      g.strokeLineShape(new Phaser.Geom.Line(bx + pad, by + pad, bx + CELL - pad, by + CELL - pad));
      g.strokeLineShape(new Phaser.Geom.Line(bx + CELL - pad, by + pad, bx + pad, by + CELL - pad));
    }
  }

  // ─── Terrain ─────────────────────────────────────────────────────────────

  _renderTerrain() {
    this._terrainObjs.forEach(o => o.destroy());
    this._terrainObjs = [];
    const g = this.lyrTerrain;
    g.clear();
    if (!this.gameState?.terrain) return;

    for (const [key, cell] of Object.entries(this.gameState.terrain)) {
      const [col, row] = key.split(",").map(Number);
      const bx = BOARD_OFF_X + col * CELL;
      const by = BOARD_OFF_Y + row * CELL;
      const pad = 3;

      const isHard = cell.type === "hard";
      const color  = isHard ? COLORS.terrainHard : (cell.hp < 2 ? COLORS.terrainSoftDmg : COLORS.terrainSoft);

      g.fillStyle(color, 1);
      g.fillRoundedRect(bx + pad, by + pad, CELL - pad * 2, CELL - pad * 2, 4);

      const isP1side = row >= col;
      if (isHard) {
        const texKey = isP1side ? "tok_farmer_hard" : "tok_emu_hard";
        if (this.textures.exists(texKey)) {
          const ico = this.add.image(bx + CELL/2, by + CELL/2, texKey)
            .setScale(0.68).setAlpha(0.9).setDepth(5);
          this._terrainObjs.push(ico);
        }
      } else {
        const texKey = isP1side ? "tok_farmer_soft" : "tok_emu_soft";
        if (this.textures.exists(texKey)) {
          const ico = this.add.image(bx + CELL/2, by + CELL/2, texKey)
            .setScale(0.65).setAlpha(0.85).setDepth(5);
          this._terrainObjs.push(ico);
        }
        if (cell.hp < 2) {
          g.fillStyle(0xff6020, 0.8);
          g.fillRect(bx + pad, by + CELL - pad - 4, CELL - pad * 2, 4);
        }
      }
    }
  }

  // ─── Hidden bases ─────────────────────────────────────────────────────────

  _renderHiddenBases() {
    // Remove old base objects
    this._baseObjs?.forEach(o => o.destroy());
    this._baseObjs = [];

    if (!this.gameState) return;
    // Show "?" for bases that haven't been revealed yet
    for (const [pid, base] of Object.entries(this.gameState.hidden_bases ?? {})) {
      if (!base) {
        // Show placeholder "?" near their corner
        const isP1 = Number(pid) === 1;
        const col = isP1 ? 0 : GRID_SIZE - 1;
        const row = isP1 ? GRID_SIZE - 1 : 0;
        const { x, y } = cellXY(col, row);
        const g = this.add.graphics();
        g.fillStyle(COLORS.hiddenBase, 0.6);
        g.fillRoundedRect(x - 16, y - 16, 32, 32, 5);
        g.lineStyle(1.5, 0xd4a030, 0.5);
        g.strokeRoundedRect(x - 16, y - 16, 32, 32, 5);
        const t = this.add.text(x, y, "?", {
          fontFamily: "serif", fontSize: "18px", fontStyle: "bold", color: "#f0d090",
        }).setOrigin(0.5);
        this._baseObjs.push(g, t);
      }
    }
  }

  // ─── Tokens ──────────────────────────────────────────────────────────────

  _renderTokens() {
    // Destroy previous token display objects
    this._tokenObjs?.forEach(o => o.destroy());
    this._tokenObjs = [];
    this.lyrTokenBg.clear();

    if (!this.gameState?.tokens) return;

    for (const [key, token] of Object.entries(this.gameState.tokens)) {
      if (token.col < 0 || token.row < 0) continue;
      const { x, y } = cellXY(token.col, token.row);
      this._drawTokenBadge(x, y, token);
      if (token.role !== "defense" && token.direction) {
        this._drawDirectionArrow(x, y, token.direction, token.player);
      }
    }
  }

  _drawTokenBadge(x, y, token) {
    const key   = `p${token.player}_${token.role}`;
    const g     = this.lyrTokenBg;
    const moved = this._movedThisTurn.has(key);
    const isP1  = token.player === 1;

    const bgColor  = isP1 ? 0x4a2208 : 0x0a2a14;
    const rimColor = moved ? 0xffd700 : (isP1 ? 0xb03030 : 0x30a060);
    const radius   = 19;

    g.fillStyle(bgColor, 0.92);
    g.fillCircle(x, y, radius);
    g.lineStyle(moved ? 3 : 1.5, rimColor, 1);
    g.strokeCircle(x, y, radius);
    if (moved) {
      g.fillStyle(0xffd700, 0.12);
      g.fillCircle(x, y, radius);
    }

    // Unit icon
    const texKey = `tok_${isP1 ? "farmer" : "emu"}_${token.role === "defense" ? "defense" : "attack"}`;
    if (this.textures.exists(texKey)) {
      const icon = this.add.image(x, y, texKey).setScale(0.82).setDepth(25);
      this._tokenObjs.push(icon);
    }

    // Name label
    const label = TOKEN_NAMES[key] ?? key.toUpperCase();
    const nameTxt = this.add.text(x, y + radius + 5, label, {
      fontFamily: "monospace", fontSize: "7px",
      color: moved ? "#ffd700" : "#f0e0c0",
      stroke: "#000000", strokeThickness: 2,
    }).setOrigin(0.5).setDepth(25);
    this._tokenObjs.push(nameTxt);

    // Gold checkmark when moved
    if (moved) {
      const chk = this.add.text(x + radius - 3, y - radius + 3, "✓", {
        fontFamily: "monospace", fontSize: "10px",
        color: "#ffd700", stroke: "#000000", strokeThickness: 3,
      }).setOrigin(0.5).setDepth(26);
      this._tokenObjs.push(chk);
    }
  }

  _drawDirectionArrow(cx, cy, direction, player) {
    const g = this.lyrTokenBg;
    const color = player === 1 ? 0xff6060 : 0x60ff90;
    let dx = 0, dy = 0;
    const len = CELL * 0.7;
    if (direction === "horizontal") { dx = player === 1 ? len : -len; }
    else if (direction === "vertical") { dy = player === 1 ? -len : len; }
    else { dx = player === 1 ? len * 0.707 : -len * 0.707; dy = player === 1 ? -len * 0.707 : len * 0.707; }

    g.lineStyle(2, color, 0.85);
    drawDashed(g, cx, cy, cx + dx, cy + dy, 5, 4);

    // Arrowhead
    const angle = Math.atan2(dy, dx);
    const hw = 0.45;
    g.fillStyle(color, 1);
    g.fillTriangle(
      cx + dx, cy + dy,
      cx + dx - 9 * Math.cos(angle - hw), cy + dy - 9 * Math.sin(angle - hw),
      cx + dx - 9 * Math.cos(angle + hw), cy + dy - 9 * Math.sin(angle + hw)
    );
  }

  // ─── Attack rays / defense zones ─────────────────────────────────────────

  _renderRays() {
    const g = this.lyrRays;
    g.clear();

    // Defense zone — warm gold tinted cells + dashed border
    const shields = this.gameState?.defense_shields ?? [];
    if (shields.length) {
      for (const [col, row] of shields) {
        const bx = BOARD_OFF_X + col * CELL;
        const by = BOARD_OFF_Y + row * CELL;
        g.fillStyle(COLORS.defenseZone, 0.22);
        g.fillRect(bx + 1, by + 1, CELL - 2, CELL - 2);
      }
      // Outline the whole zone with dashed border
      g.lineStyle(2, COLORS.defenseZoneBorder, 0.9);
      for (const [col, row] of shields) {
        const bx = BOARD_OFF_X + col * CELL;
        const by = BOARD_OFF_Y + row * CELL;
        // Only draw edges that don't border another shield cell
        const neighbors = [[0,-1],[1,0],[0,1],[-1,0]];
        const shieldSet = new Set(shields.map(([c,r]) => `${c},${r}`));
        neighbors.forEach(([dc, dr], edge) => {
          if (!shieldSet.has(`${col+dc},${row+dr}`)) {
            const edges = [
              [[bx,by],[bx+CELL,by]],
              [[bx+CELL,by],[bx+CELL,by+CELL]],
              [[bx,by+CELL],[bx+CELL,by+CELL]],
              [[bx,by],[bx,by+CELL]],
            ];
            const [[x1,y1],[x2,y2]] = edges[edge];
            drawDashed(g, x1, y1, x2, y2, 5, 4);
          }
        });
      }
    }

    // Preview attack rays
    if (!this.preview?.previews) return;
    for (const { rays } of this.preview.previews) {
      for (const ray of rays) {
        if (!ray.path?.length) continue;

        // Highlight path cells
        for (const cell of ray.path) {
          const bx = BOARD_OFF_X + cell.col * CELL;
          const by = BOARD_OFF_Y + cell.row * CELL;
          g.fillStyle(cell.hit ? COLORS.attackRayHit : COLORS.attackRay, cell.hit ? 0.3 : 0.1);
          g.fillRect(bx + 1, by + 1, CELL - 2, CELL - 2);
        }

        // Dashed golden ray line
        const first = ray.path[0], last = ray.path[ray.path.length - 1];
        const p1 = cellXY(first.col, first.row);
        const p2 = cellXY(last.col,  last.row);
        g.lineStyle(2.5, COLORS.attackRay, 0.9);
        drawDashed(g, p1.x, p1.y, p2.x, p2.y, 8, 5);

        // Hit target ring
        if (ray.hit) {
          const { x, y } = cellXY(ray.hit.col, ray.hit.row);
          g.lineStyle(2.5, COLORS.attackRayHit, 1);
          g.strokeCircle(x, y, CELL * 0.4);
          g.lineStyle(1, COLORS.attackRayHit, 0.5);
          g.strokeCircle(x, y, CELL * 0.28);
        }
      }
    }
  }

  // ─── Attack animation ────────────────────────────────────────────────────

  _createParticleTextures() {
    // Soft glow blob — used for trail + impact bursts (white so tint applies)
    const g1 = this.make.graphics({ add: false });
    g1.fillStyle(0xffffff, 0.25);
    g1.fillCircle(14, 14, 14);
    g1.fillStyle(0xffffff, 0.7);
    g1.fillCircle(14, 14, 8);
    g1.fillStyle(0xffffff, 1);
    g1.fillCircle(14, 14, 4);
    g1.generateTexture("p_glow", 28, 28);
    g1.destroy();

    // Hard bright core — projectile bullet
    const g2 = this.make.graphics({ add: false });
    g2.fillStyle(0xffffff, 1);
    g2.fillCircle(7, 7, 7);
    g2.generateTexture("p_bullet", 14, 14);
    g2.destroy();
  }

  _animateAttacks(data) {
    const all = (data.results ?? []).map(r => this._animateRay(r, data.attacking_player));
    return Promise.all(all);
  }

  _animateRay(result, attackingPlayer) {
    return new Promise(resolve => {
      const path = result.path;
      if (!path?.length) { resolve(); return; }

      // Start: token position; fall back to first path cell
      const tokenKey = result.token;
      const token = this.gameState?.tokens?.[tokenKey];
      const startCell = (token && token.col >= 0)
        ? { col: token.col, row: token.row }
        : path[0];
      const endCell = path[path.length - 1];

      const start = cellXY(startCell.col, startCell.row);
      const end   = cellXY(endCell.col,   endCell.row);
      const dist  = Math.hypot(end.x - start.x, end.y - start.y);
      const dur   = Math.max(180, Math.min(650, dist * 2.8));

      const tint = result.outcome === "shielded" ? 0x60ffaa
                 : result.outcome === "blocked"   ? 0xbbbbbb
                 : result.outcome === "miss"       ? 0xaaaaff
                 : 0xffcc00;  // hit / terrain — golden

      // Projectile sprite
      const proj = this.add.image(start.x, start.y, "p_bullet")
        .setTint(tint).setScale(1.4).setDepth(30);

      // Particle trail that follows the projectile
      const trail = this.add.particles(start.x, start.y, "p_glow", {
        tint,
        speed: 8,
        scale:    { start: 0.55, end: 0 },
        alpha:    { start: 0.75, end: 0 },
        lifespan: 280,
        frequency: 22,
        depth: 29,
      });
      trail.startFollow(proj);

      this.tweens.add({
        targets: proj,
        x: end.x, y: end.y,
        duration: dur,
        ease: "Linear",
        onComplete: () => {
          trail.stopFollow();
          trail.stop();
          proj.destroy();

          // Let trail particles finish fading, then impact
          this.time.delayedCall(320, () => {
            trail.destroy();
            if (result.outcome !== "miss") {
              const hx = result.col != null ? cellXY(result.col, result.row).x : end.x;
              const hy = result.col != null ? cellXY(result.col, result.row).y : end.y;
              this._spawnImpact(hx, hy, result.outcome, tint);
            }
            this.time.delayedCall(350, resolve);
          });
        },
      });
    });
  }

  _spawnImpact(x, y, outcome, tint) {
    // Radial burst
    const burst = this.add.particles(x, y, "p_glow", {
      tint,
      speed:    { min: 70, max: 200 },
      angle:    { min: 0, max: 360 },
      scale:    { start: 0.9, end: 0 },
      alpha:    { start: 1, end: 0 },
      lifespan: 550,
      depth: 31,
      emitting: false,
    });
    burst.explode(outcome === "hit" ? 18 : 10);
    this.time.delayedCall(700, () => burst.destroy());

    // Screen shake on a real hit
    if (outcome === "hit" || outcome === "terrain_destroyed") {
      this.cameras.main.shake(220, 0.006);
    }

    // Expanding ring flash
    const ring = this.add.graphics().setDepth(32);
    ring.lineStyle(3, tint, 1);
    ring.strokeCircle(x, y, CELL * 0.35);
    this.tweens.add({
      targets: ring, scaleX: 2.8, scaleY: 2.8, alpha: 0,
      duration: 420, ease: "Power2",
      onComplete: () => ring.destroy(),
    });
  }

  _logAttackResult(data) {
    const outcomes = {
      hit:               { color: "red",    verb: "destroyed territory at" },
      shielded:          { color: "yellow", verb: "blocked by shield at" },
      blocked:           { color: "gray",   verb: "blocked by hard terrain at" },
      terrain_hit:       { color: "yellow", verb: "damaged terrain at" },
      terrain_destroyed: { color: "red",    verb: "cleared terrain at" },
      miss:              { color: "gray",   verb: "missed" },
    };
    for (const result of data.results ?? []) {
      const info = outcomes[result.outcome] ?? { color: "gray", verb: result.outcome };
      const pos  = result.col != null
        ? `[${String.fromCharCode(65 + result.col)}${result.row + 1}]` : "";
      const name = PLAYER_NAMES[data.attacking_player] ?? `P${data.attacking_player}`;
      this._pushLog(info.color, `${name}: ${info.verb} ${pos}`);
    }
  }

  // ─── Resolve validation + error toast ────────────────────────────────────

  _resolveError() {
    if (!this.gameState || this.gameState.phase !== "planning") return null;
    const p = this.gameState.current_player;
    const tokens = this.gameState.tokens ?? {};

    const missing = [];
    for (const role of ["attack_a", "attack_b", "defense"]) {
      const t = tokens[`p${p}_${role}`];
      if (!t || t.col < 0 || t.row < 0) {
        const label = TOKEN_NAMES[`p${p}_${role}`] ?? role;
        missing.push(label);
      }
    }
    if (missing.length === 0) return null;

    const noun = missing.length === 1 ? "unit" : "units";
    return `You haven't placed ${missing.join(" or ")} yet.\nCannot attack.`;
  }

  _showErrorToast(message) {
    // Dismiss any existing toast
    this._toastObjs?.forEach(o => o.destroy());

    const cx = CANVAS_W / 2;
    const cy = BOARD_OFF_Y + GRID_SIZE * CELL / 2;

    const txt = this.add.text(cx, cy, message, {
      fontFamily: "serif",
      fontSize: "17px",
      color: "#ff5533",
      stroke: "#000000",
      strokeThickness: 4,
      align: "center",
      lineSpacing: 6,
      wordWrap: { width: CANVAS_W - 80 },
    }).setOrigin(0.5).setDepth(60).setAlpha(0);

    const pad = 20;
    const bg = this.add.rectangle(
      cx, cy,
      txt.width + pad * 2, txt.height + pad,
      0x0a0804, 0.88
    ).setDepth(59).setAlpha(0);

    const border = this.add.graphics().setDepth(59).setAlpha(0);
    border.lineStyle(1.5, 0x8a2010, 0.9);
    border.strokeRoundedRect(
      cx - txt.width / 2 - pad, cy - txt.height / 2 - pad / 2,
      txt.width + pad * 2, txt.height + pad, 6
    );

    this._toastObjs = [bg, border, txt];

    // Fade in → hold → fade out
    this.tweens.add({
      targets: this._toastObjs, alpha: 1, duration: 250,
      onComplete: () => {
        this.tweens.add({
          targets: this._toastObjs, alpha: 0,
          delay: 2200, duration: 400,
          onComplete: () => this._toastObjs?.forEach(o => o.destroy()),
        });
      },
    });

    // Shake camera lightly
    this.cameras.main.shake(180, 0.004);
  }

  // ─── Active territory ────────────────────────────────────────────────────

  _renderActiveTerritory() {
    const g = this.lyrActive;
    g.clear();
    if (!this.gameState?.active_cells) return;

    for (const [pidStr, cells] of Object.entries(this.gameState.active_cells)) {
      const pid = Number(pidStr);
      for (const [col, row] of cells) {
        const bx = BOARD_OFF_X + col * CELL;
        const by = BOARD_OFF_Y + row * CELL;
        const even = (col + row) % 2 === 0;
        const color = pid === 1
          ? (even ? COLORS.p1Active : COLORS.p1ActiveAlt)
          : (even ? COLORS.p2Active : COLORS.p2ActiveAlt);
        g.fillStyle(color, 1);
        g.fillRect(bx, by, CELL, CELL);
      }
    }
  }

  // ─── Token textures ───────────────────────────────────────────────────────

  _makeTex(key, w, h, fn) {
    if (this.textures.exists(key)) return;
    const g = this.make.graphics({ x: 0, y: 0, add: false });
    fn(g);
    g.generateTexture(key, w, h);
    g.destroy();
  }

  _createTokenTextures() {
    const S = 40;  // texture canvas size

    // ── Riflemen / Keith (P1 attack) ──────────────────────────────────────
    this._makeTex("tok_farmer_attack", S, S, g => {
      g.fillStyle(0x2a1400, 1);   // hat brim
      g.fillRect(9, 9, 22, 3);
      g.fillRect(13, 3, 14, 7);   // hat crown
      g.fillStyle(0xd4956a, 1);   // head
      g.fillCircle(20, 16, 6);
      g.fillStyle(0x8a7040, 1);   // khaki body
      g.fillRect(13, 22, 14, 13);
      g.fillStyle(0x5a4020, 1);   // legs
      g.fillRect(13, 35, 5, 5);
      g.fillRect(22, 35, 5, 5);
      g.lineStyle(2.5, 0x2a1800, 1); // rifle (angled forward)
      g.strokeLineShape(new Phaser.Geom.Line(26, 18, 37, 30));
      g.fillStyle(0x2a1800, 1);   // muzzle tip
      g.fillCircle(37, 30, 2);
    });

    // ── Old Mick (P1 defense) ─────────────────────────────────────────────
    this._makeTex("tok_farmer_defense", S, S, g => {
      g.fillStyle(0x2a1400, 1);   // wide hat brim
      g.fillRect(7, 9, 26, 3);
      g.fillRect(11, 3, 18, 7);
      g.fillStyle(0xd4956a, 1);   // head
      g.fillCircle(20, 16, 6);
      g.fillStyle(0x2a1400, 1);   // mustache
      g.fillRect(15, 18, 10, 2);
      g.fillStyle(0x7a5020, 1);   // duster coat (wider)
      g.fillRect(11, 22, 18, 13);
      g.fillStyle(0x5a3a10, 1);
      g.fillRect(11, 35, 6, 5);
      g.fillRect(23, 35, 6, 5);
      g.lineStyle(2.5, 0x2a1800, 1); // upright rifle
      g.strokeLineShape(new Phaser.Geom.Line(32, 5, 32, 35));
      g.strokeLineShape(new Phaser.Geom.Line(29, 22, 35, 22)); // trigger guard
    });

    // ── The Mob / Emu (P2 attack) ─────────────────────────────────────────
    this._makeTex("tok_emu_attack", S, S, g => {
      g.fillStyle(0x2a2218, 1);   // dark emu body
      g.fillRoundedRect(9, 22, 20, 14, 8);
      g.fillRect(16, 9, 7, 15);   // neck
      g.fillCircle(19, 8, 7);     // head
      g.fillStyle(0xd08020, 1);   // beak
      g.fillTriangle(25, 7, 33, 6, 24, 11);
      g.fillStyle(0xe8a030, 1);   // eye
      g.fillCircle(22, 5, 2.5);
      g.fillStyle(0x1a1810, 1);   // pupil
      g.fillCircle(23, 5, 1);
      g.fillStyle(0x3a3028, 1);   // wing nubbins
      g.fillCircle(8, 28, 4);
      g.fillCircle(30, 28, 4);
      g.lineStyle(2.5, 0x1a1810, 1); // legs
      g.strokeLineShape(new Phaser.Geom.Line(14, 36, 10, 40));
      g.strokeLineShape(new Phaser.Geom.Line(24, 36, 28, 40));
    });

    // ── Cassowary (P2 defense) ─────────────────────────────────────────────
    this._makeTex("tok_emu_defense", S, S, g => {
      g.fillStyle(0x1a1810, 1);   // dark body (larger)
      g.fillRoundedRect(8, 20, 22, 16, 8);
      g.fillRect(15, 7, 8, 16);   // neck
      g.fillCircle(19, 9, 8);     // head
      g.fillStyle(0x7a5a10, 1);   // casque/helmet
      g.fillTriangle(11, 9, 19, -2, 27, 9);
      g.fillStyle(0x0060c0, 1);   // blue wattle
      g.fillRoundedRect(14, 11, 4, 12, 2);
      g.fillStyle(0xee3010, 1);   // red wattle
      g.fillRoundedRect(18, 13, 4, 8, 2);
      g.fillStyle(0xff8000, 1);   // eye
      g.fillCircle(23, 6, 2.5);
      g.fillStyle(0x1a1810, 1);
      g.fillCircle(24, 6, 1);
      g.lineStyle(3, 0x1a1810, 1);
      g.strokeLineShape(new Phaser.Geom.Line(14, 36, 9, 40));
      g.strokeLineShape(new Phaser.Geom.Line(22, 36, 27, 40));
    });

    // ── Fence Barricade (P1 hard terrain) ────────────────────────────────
    this._makeTex("tok_farmer_hard", S, S, g => {
      g.fillStyle(0x5a3a1a, 1);   // posts
      g.fillRect(5, 3, 6, 34);
      g.fillRect(29, 3, 6, 34);
      g.fillStyle(0x8a6030, 1);   // rails
      g.fillRect(3, 10, 34, 4);
      g.fillRect(3, 20, 34, 4);
      g.fillRect(3, 30, 34, 4);
      g.fillStyle(0x3a2010, 1);   // barbs
      for (let bx = 10; bx <= 28; bx += 9) {
        g.fillTriangle(bx-3, 10, bx, 5, bx+3, 10);
        g.fillTriangle(bx-3, 24, bx, 19, bx+3, 24);
      }
    });

    // ── Wheat Scarecrow (P1 soft terrain) ────────────────────────────────
    this._makeTex("tok_farmer_soft", S, S, g => {
      g.fillStyle(0x5a4010, 1);   // vertical post
      g.fillRect(18, 10, 4, 30);
      g.fillRect(7, 18, 26, 4);   // arms
      g.fillStyle(0xd4a030, 1);   // shirt
      g.fillRect(12, 18, 16, 14);
      g.fillStyle(0xd4956a, 1);   // head
      g.fillCircle(20, 13, 6);
      g.fillStyle(0x2a1800, 1);   // hat brim
      g.fillRect(10, 8, 20, 3);
      g.fillRect(13, 2, 14, 7);
      g.lineStyle(2, 0xd4a030, 1); // straw hands
      g.strokeLineShape(new Phaser.Geom.Line(7, 19, 2, 13));
      g.strokeLineShape(new Phaser.Geom.Line(33, 19, 38, 13));
    });

    // ── Termite Mounds (P2 hard terrain) ──────────────────────────────────
    this._makeTex("tok_emu_hard", S, S, g => {
      g.fillStyle(0x7a5a2a, 1);   // side mounds
      g.fillRoundedRect(1, 22, 12, 14, 5);
      g.fillTriangle(1, 22, 7, 10, 13, 22);
      g.fillRoundedRect(27, 22, 12, 14, 5);
      g.fillTriangle(27, 22, 33, 10, 39, 22);
      g.fillStyle(0x9a7a3a, 1);   // centre mound (tallest)
      g.fillRoundedRect(11, 18, 18, 18, 6);
      g.fillTriangle(11, 18, 20, 2, 29, 18);
      g.fillStyle(0x6a4a18, 1);   // surface texture
      g.fillCircle(20, 22, 3);
      g.fillCircle(15, 28, 2);
      g.fillCircle(25, 30, 2);
    });

    // ── Spinifex (P2 soft terrain) ─────────────────────────────────────────
    this._makeTex("tok_emu_soft", S, S, g => {
      const cx = 20, cy = 24;
      g.lineStyle(2.5, 0x4a8a20, 1);
      const tips = [[20,4],[6,10],[2,22],[6,34],[20,38],[34,34],[38,22],[34,10]];
      for (const [tx, ty] of tips) {
        g.strokeLineShape(new Phaser.Geom.Line(cx, cy, tx, ty));
      }
      g.lineStyle(1.5, 0x7aca40, 1);
      const inner = [[20,9],[10,13],[7,22],[10,31],[20,34],[30,31],[33,22],[30,13]];
      for (const [tx, ty] of inner) {
        g.strokeLineShape(new Phaser.Geom.Line(cx, cy, tx, ty));
      }
      g.fillStyle(0x5aaa30, 1);
      g.fillCircle(cx, cy, 6);
      g.fillStyle(0x8aca40, 1);
      g.fillCircle(cx, cy, 3);
    });
  }

  // ─── Game over overlay ───────────────────────────────────────────────────

  _showGameOver(data) {
    const overlay = this.add.rectangle(CANVAS_W / 2, CANVAS_H / 2, CANVAS_W, CANVAS_H, 0x000000, 0.75);

    const winner = data.winner;
    const name   = PLAYER_NAMES[winner] ?? `Player ${winner}`;
    const color  = winner === 1 ? "#e88050" : "#60c880";

    this.add.text(CANVAS_W / 2, CANVAS_H / 2 - 50,
      `${name.toUpperCase()} WINS`, {
        fontFamily: "serif", fontSize: "32px", fontStyle: "bold",
        color, stroke: "#000000", strokeThickness: 4,
      }).setOrigin(0.5);

    const reasons = {
      base_destroyed:      "Enemy base was found and destroyed!",
      territory_destroyed: "All enemy territory captured!",
    };
    this.add.text(CANVAS_W / 2, CANVAS_H / 2,
      reasons[data.reason] ?? "", {
        fontFamily: "serif", fontSize: "14px", color: "#f0e0c0",
      }).setOrigin(0.5);

    this.add.text(CANVAS_W / 2, CANVAS_H / 2 + 50,
      "Press  R  to reset", {
        fontFamily: "monospace", fontSize: "12px", color: "#8a7060",
      }).setOrigin(0.5);

    this.input.keyboard.once("keydown-R", () => {
      overlay.destroy();
      this.ws?.send("reset_game", {});
    });
  }
}
