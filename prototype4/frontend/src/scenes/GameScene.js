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

  preload() {
    this.load.image("board",          "assets/board.png");
    this.load.image("active_farmer",  "assets/active_farmer.png");
    this.load.image("active_emu",     "assets/active_emu.png");
    // Pixel-art character sprites — farmer side
    this.load.image("spr_keith_a",    "assets/keith_a.png");
    this.load.image("spr_keith_b",    "assets/keith_b.png");
    this.load.image("spr_old_mick",   "assets/old_mick.png");
    // Pixel-art character sprites — emu side
    this.load.image("spr_mob_a",      "assets/mob_a.png");
    this.load.image("spr_mob_b",      "assets/mob_b.png");
    this.load.image("spr_cassowary",  "assets/cassowary.png");
    // Terrain sprite images
    this.load.image("terrain_hard",   "assets/terrain_hard.png");
    this.load.image("terrain_soft",   "assets/terrain_soft.png");
  }

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
    this._activeCellImgs = [];
    this._tokenDirs   = {};   // {tokenKey: 0|1|2} — persists direction index across placements
    this._pickerObjs  = [];   // token-picker popup objects (cleared on dismiss)
    this._tokenTweens = [];   // active bob tweens — stopped before each re-render
    this._shieldLbl   = null; // center 🛡 label for defense zone
    this._hqUiPlayer  = 1;   // which player is currently placing HQ
    this._hqPassObjs  = [];  // pass-screen overlay objects
    this._hqUIObjs    = [];  // HQ placement UI objects
  }

  create() {
    this._initAudio();
    this._createParticleTextures();
    this._createTokenTextures();
    this._buildBoard();
    this._buildLayers();
    this._buildTurnBanner();
    this._buildButtons();
    this._buildLog();
    this._buildTokenPlacer();
    this._bindWS();
    if (this._initialState) {
      // State passed directly from previous scene — apply immediately
      this.gameState = this._initialState;
      this._render();
    } else if (this.ws) {
      // No state handed over — ask server for current state
      this.ws.send("request_state", {});
    }
  }

  // ─── Static board (drawn once) ───────────────────────────────────────────

  _buildBoard() {
    const OX = BOARD_OFF_X, OY = BOARD_OFF_Y;
    const BS = GRID_SIZE * CELL;

    // ── Board image ────────────────────────────────────────────────────────
    const img = this.add.image(OX + BS / 2, OY + BS / 2, "board");
    img.setDisplaySize(BS, BS).setDepth(0);

    // ── Grid overlay — very faint, for guidance only ───────────────────────
    const g = this.add.graphics().setDepth(1);
    g.lineStyle(1, 0x000000, 0.18);
    for (let i = 0; i <= GRID_SIZE; i++) {
      const x = OX + i * CELL, y = OY + i * CELL;
      g.strokeLineShape(new Phaser.Geom.Line(x, OY, x, OY + BS));
      g.strokeLineShape(new Phaser.Geom.Line(OX, y, OX + BS, y));
    }

    // ── Coordinate labels ──────────────────────────────────────────────────
    const labelStyle = { fontFamily: "monospace", fontSize: "10px", color: "#c8a878" };
    for (let i = 0; i < GRID_SIZE; i++) {
      const lx = OX + i * CELL + CELL / 2;
      const ly = OY + i * CELL + CELL / 2;
      this.add.text(lx, OY - 16, String.fromCharCode(65 + i), labelStyle).setOrigin(0.5);
      this.add.text(OX - 18, ly, String(i + 1), labelStyle).setOrigin(0.5);
    }
  }

  _buildLayers() {
    // Explicit depths keep z-order correct regardless of creation time.
    // Active cell images are created at depth 10 inside _renderActiveTerritory().
    this.lyrActive      = this.add.graphics().setDepth(10);  // solid-colour fallback
    this.lyrDestroyed   = this.add.graphics().setDepth(20);
    this.lyrTerrain     = this.add.graphics().setDepth(30);
    this.lyrDefense     = this.add.graphics().setDepth(40);  // unused legacy
    this.lyrDefenseZone = this.add.graphics().setDepth(42);  // animated defense overlay
    this.lyrRays        = this.add.graphics().setDepth(50);
    this.lyrTokenBg     = this.add.graphics().setDepth(60);
    // depth 62 — sprite containers (created per token in _drawSpriteToken)
    this.lyrArrows      = this.add.graphics().setDepth(65);  // arrows above sprites
    this.lyrHits        = this.add.graphics().setDepth(70);
    this._defenseZoneTween = null;
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

  // ─── Tap-to-place (no-camera mode) ──────────────────────────────────────

  _buildTokenPlacer() {
    const boardW = GRID_SIZE * CELL;
    const boardH = GRID_SIZE * CELL;

    // A transparent rectangle that covers the board, sits above tokens (depth 150)
    // but below the picker popup (depth 200+).  It receives all board taps first.
    const hitZone = this.add.rectangle(
      BOARD_OFF_X + boardW / 2,
      BOARD_OFF_Y + boardH / 2,
      boardW, boardH,
      0x000000, 0,       // fully invisible
    ).setInteractive({ useHandCursor: false }).setDepth(150);

    hitZone.on("pointerdown", pointer => {
      const col = Math.floor((pointer.x - BOARD_OFF_X) / CELL);
      const row = Math.floor((pointer.y - BOARD_OFF_Y) / CELL);
      if (col < 0 || col >= GRID_SIZE || row < 0 || row >= GRID_SIZE) return;
      this._handleBoardTap(col, row);
    });
  }

  _handleBoardTap(col, row) {
    if (!this.gameState) return;

    // Route taps during HQ placement phase
    if (this.gameState.phase === "hq_placement") {
      this._handleHQTap(col, row); return;
    }

    if (this.gameState.phase !== "planning") {
      this._dismissPicker(); return;
    }
    const tokens = this.gameState.tokens ?? {};

    // Tapping any already-placed token → cycle its fire direction
    // (works for both players — useful in no-camera / demo mode)
    for (const [key, token] of Object.entries(tokens)) {
      if (token.col === col && token.row === row) {
        this._dismissPicker();
        this._cycleTokenDirection(key, col, row, token);
        return;
      }
    }

    // Derive player from territory so both players can place tokens freely
    // P1 = upper-left (col+row < GRID_SIZE-1), P2 = lower-right
    const p = (col + row) < GRID_SIZE - 1 ? 1 : 2;

    this._showTokenPicker(col, row, p);
  }

  _showTokenPicker(col, row, player) {
    this._dismissPicker();   // clear any previous popup

    const { x: cx, y: cy } = cellXY(col, row);

    // Show popup above the cell; if near the top edge, show below instead
    const above  = cy - BOARD_OFF_Y > CELL * 2;
    const popY   = above ? cy - CELL * 0.9 : cy + CELL * 1.1;

    const roles = [
      { role: "attack_a", label: TOKEN_NAMES[`p${player}_attack_a`] ?? "ATK A" },
      { role: "attack_b", label: TOKEN_NAMES[`p${player}_attack_b`] ?? "ATK B" },
      { role: "defense",  label: TOKEN_NAMES[`p${player}_defense`]  ?? "DEF"   },
    ];

    const btnW   = 64, btnH = 26, gap = 6;
    const count  = roles.length;
    const totalW = count * btnW + (count - 1) * gap + 20;

    // Panel background
    const panel = this.add.graphics().setDepth(200);
    panel.fillStyle(0x120a04, 0.96);
    panel.fillRoundedRect(cx - totalW / 2, popY - btnH / 2 - 10, totalW, btnH + 20, 6);
    panel.lineStyle(1.5, 0x9a6a28, 1);
    panel.strokeRoundedRect(cx - totalW / 2, popY - btnH / 2 - 10, totalW, btnH + 20, 6);
    this._pickerObjs.push(panel);

    // "PLACE:" label
    const hdr = this.add.text(cx, popY - btnH / 2 - 3, "PLACE:", {
      fontFamily: "monospace", fontSize: "8px", color: "#8a6a40",
    }).setOrigin(0.5, 1).setDepth(201);
    this._pickerObjs.push(hdr);

    // Arrow pointing to the cell
    const arrG = this.add.graphics().setDepth(201);
    const arrY = above ? cy - CELL * 0.35 : cy + CELL * 0.35;
    arrG.fillStyle(0x9a6a28, 0.8);
    if (above) {
      arrG.fillTriangle(cx - 6, popY + btnH / 2 + 10, cx + 6, popY + btnH / 2 + 10, cx, arrY);
    } else {
      arrG.fillTriangle(cx - 6, popY - btnH / 2 - 10, cx + 6, popY - btnH / 2 - 10, cx, arrY);
    }
    this._pickerObjs.push(arrG);

    // One button per role
    const startX = cx - (count - 1) * (btnW + gap) / 2;

    roles.forEach(({ role, label }, i) => {
      const bx = startX + i * (btnW + gap);

      // Is this token already placed somewhere?
      const t = this.gameState?.tokens?.[`p${player}_${role}`];
      const isPlaced = t && t.col >= 0 && t.row >= 0;

      const bgCol  = isPlaced ? 0x1a2e10 : 0x221608;
      const rimCol = isPlaced ? 0x60c040 : 0xc07020;

      const btnG = this.add.graphics().setDepth(200);
      const _drawBtn = (bg, rim) => {
        btnG.clear();
        btnG.fillStyle(bg, 1);
        btnG.fillRoundedRect(bx - btnW / 2, popY - btnH / 2, btnW, btnH, 4);
        btnG.lineStyle(1.5, rim, 1);
        btnG.strokeRoundedRect(bx - btnW / 2, popY - btnH / 2, btnW, btnH, 4);
      };
      _drawBtn(bgCol, rimCol);
      this._pickerObjs.push(btnG);

      const shortLabel = label.length > 9 ? label.slice(0, 8) + "…" : label;
      const btnTxt = this.add.text(bx, popY, shortLabel, {
        fontFamily: "monospace", fontSize: "9px",
        color: isPlaced ? "#90d060" : "#f0d090",
      }).setOrigin(0.5).setDepth(202)
        .setInteractive({
          useHandCursor: true,
          hitArea: new Phaser.Geom.Rectangle(-btnW / 2, -btnH / 2, btnW, btnH),
          hitAreaCallback: Phaser.Geom.Rectangle.Contains,
        });

      btnTxt.on("pointerdown", () => {
        this._placeToken(col, row, role, player);
        this._dismissPicker();
      });
      btnTxt.on("pointerover",  () => _drawBtn(0x3a2c1e, 0xffa030));
      btnTxt.on("pointerout",   () => _drawBtn(bgCol,    rimCol));
      this._pickerObjs.push(btnTxt);
    });
  }

  _dismissPicker() {
    this._pickerObjs.forEach(o => o.destroy());
    this._pickerObjs = [];
  }

  _placeToken(col, row, role, player) {
    // Attack tokens cannot be placed on terrain cells
    if (role !== "defense") {
      const terrainKey = `${col},${row}`;
      const terrain = this.gameState?.terrain ?? {};
      if (terrain[terrainKey]) {
        this._showErrorToast("Attack tokens can't be\nplaced on terrain!");
        return;
      }
    }
    const tokenKey = `p${player}_${role}`;
    // Defense tokens don't need a meaningful direction; attack tokens use stored direction
    const ANGLES   = [0, 90, 45];    // horizontal, vertical, diagonal
    const dirIdx   = role === "defense" ? 0 : (this._tokenDirs[tokenKey] ?? 0);
    this._playSound("place");
    this.ws?.send("demo_token", { player, role, col, row, angle: ANGLES[dirIdx] });
  }

  _cycleTokenDirection(tokenKey, col, row, token) {
    if (token.role === "defense") return;   // defense has no direction
    const DIRS   = ["horizontal", "vertical", "diagonal"];
    const ANGLES = [0, 90, 45];
    const curIdx = DIRS.indexOf(token.direction ?? "horizontal");
    const nxtIdx = (curIdx + 1) % DIRS.length;
    this._tokenDirs[tokenKey] = nxtIdx;
    this._playSound("rotate");
    this.ws?.send("demo_token", {
      player: token.player, role: token.role, col, row, angle: ANGLES[nxtIdx],
    });
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
      // Reset HQ player tracker when a new game starts
      if (d.phase === "side_selection" || d.phase === "tutorial") {
        this._hqUiPlayer = 1;
        this._hqPassObjs.forEach(o => o.destroy()); this._hqPassObjs = [];
        this._hqUIObjs.forEach(o => o.destroy());   this._hqUIObjs = [];
      }
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
    this.ws.on("resolve_error",  d => this._showErrorToast(d.message));
    this.ws.on("set_base_error", d => this._showErrorToast(d.message));
    this.ws.on("token_placement_error", d => this._showErrorToast(d.message));
    this.ws.on("base_confirmed", d => {
      const justPlaced = d.player;
      // If P1 just placed, show the pass overlay so P2 can place secretly
      if (justPlaced === 1) {
        this._showHQPassOverlay(1, () => {
          this._hqUiPlayer = 2;
          // Re-render HQ UI for P2 (state is already updated by board_state event)
          this._hqUIObjs.forEach(o => o.destroy());
          this._hqUIObjs = [];
          if (this.gameState?.phase === "hq_placement") {
            this._renderHQPlacementUI();
          }
        });
      }
      // P2 confirmation → board_state will arrive with phase=planning, handled by board_state handler
    });
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
    this._dismissPicker();
    this._shieldLbl?.destroy(); this._shieldLbl = null;
    const s = this.gameState;

    // Clear HQ UI whenever we re-render (rebuilt below if still needed)
    this._hqUIObjs.forEach(o => o.destroy());
    this._hqUIObjs = [];

    const phaseLabel = {
      terrain_placement: "TERRAIN SETUP",
      hq_placement:      "HQ PLACEMENT",
      planning:          "PLANNING",
      resolve:           "RESOLVING...",
      game_over:         "GAME OVER",
    }[s.phase] ?? s.phase.toUpperCase();

    const name = PLAYER_NAMES[s.current_player] ?? `Player ${s.current_player}`;
    this._updateBanner(`${name.toUpperCase()}'S TURN  ·  ${phaseLabel}`);

    this._renderActiveTerritory();
    this._renderDestroyed();
    this._renderTerrain();
    this._renderHiddenBases();
    this._renderTokens();
    this._renderRays();

    // HQ placement phase — show territory highlight + instructions
    if (s.phase === "hq_placement") {
      this._renderHQPlacementUI();
    }
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
      const maxHp  = isHard ? 4 : 2;
      const color  = isHard
        ? (cell.hp < maxHp ? COLORS.terrainHardDmg : COLORS.terrainHard)
        : (cell.hp < 2     ? COLORS.terrainSoftDmg : COLORS.terrainSoft);

      g.fillStyle(color, 1);
      g.fillRoundedRect(bx + pad, by + pad, CELL - pad * 2, CELL - pad * 2, 4);

      const isP1side = (col + row) < GRID_SIZE - 1;  // P1 = upper-left
      if (isHard) {
        // Try loaded terrain_hard.png first, fall back to procedural token texture
        const texKey = this.textures.exists("terrain_hard") ? "terrain_hard"
                     : (isP1side ? "tok_farmer_hard" : "tok_emu_hard");
        const ico = this.add.image(bx + CELL/2, by + CELL/2, texKey)
          .setDisplaySize(CELL - pad*2, CELL - pad*2).setAlpha(0.9).setDepth(31);
        this._terrainObjs.push(ico);
        // HP dots: 4 max for hard terrain
        this._drawTerrainHPDots(bx + pad, by + CELL - pad - 5, CELL - pad*2, cell.hp, 4);
      } else {
        // Try loaded terrain_soft.png first, fall back to procedural token texture
        const texKey = this.textures.exists("terrain_soft") ? "terrain_soft"
                     : (isP1side ? "tok_farmer_soft" : "tok_emu_soft");
        const ico = this.add.image(bx + CELL/2, by + CELL/2, texKey)
          .setDisplaySize(CELL - pad*2, CELL - pad*2).setAlpha(0.85).setDepth(31);
        this._terrainObjs.push(ico);
        // HP dots: 2 max for soft terrain
        this._drawTerrainHPDots(bx + pad, by + CELL - pad - 5, CELL - pad*2, cell.hp, 2);
      }
    }
  }

  // ─── Hidden bases ─────────────────────────────────────────────────────────

  _renderHiddenBases() {
    // Remove old base objects
    this._baseObjs?.forEach(o => o.destroy());
    this._baseObjs = [];

    if (!this.gameState) return;
    // Don't show any base indicators while HQ is being placed
    if (this.gameState.phase === "hq_placement") return;
    // Show "?" for bases that haven't been revealed yet
    for (const [pid, base] of Object.entries(this.gameState.hidden_bases ?? {})) {
      if (!base) {
        // Show placeholder "?" near their corner of the anti-diagonal territory
        const isP1 = Number(pid) === 1;
        const col = isP1 ? 0 : GRID_SIZE - 1;   // P1=upper-left, P2=lower-right
        const row = isP1 ? 0 : GRID_SIZE - 1;
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

  // Sprite keys for tokens that have real pixel-art images (keyed by token key string)
  static SPRITE_MAP = {
    // Farmer side
    p1_attack_a: "spr_keith_a",
    p1_attack_b: "spr_keith_b",
    p1_defense:  "spr_old_mick",
    // Emu side
    p2_attack_a: "spr_mob_a",
    p2_attack_b: "spr_mob_b",
    p2_defense:  "spr_cassowary",
  };

  _renderTokens() {
    // Stop all bob tweens before destroying their targets
    this._tokenTweens.forEach(t => { try { t.stop(); t.remove(); } catch {} });
    this._tokenTweens = [];

    // Destroy previous token display objects
    this._tokenObjs?.forEach(o => o.destroy());
    this._tokenObjs = [];
    this.lyrTokenBg.clear();
    this.lyrArrows.clear();

    if (!this.gameState?.tokens) return;

    for (const [key, token] of Object.entries(this.gameState.tokens)) {
      if (token.col < 0 || token.row < 0) continue;
      const { x, y } = cellXY(token.col, token.row);

      const sprKey = GameScene.SPRITE_MAP[key];
      if (sprKey && this.textures.exists(sprKey)) {
        this._drawSpriteToken(x, y, token, key, sprKey);
      } else {
        this._drawTokenBadge(x, y, token);
      }

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

  _drawSpriteToken(x, y, token, key, sprKey) {
    const moved    = this._movedThisTurn.has(key);
    const isMyTurn = token.player === this.gameState?.current_player;

    // ── Natural aspect ratio — read from loaded texture ───────────────────────
    const frame    = this.textures.getFrame(sprKey);
    const natW     = frame?.realWidth  ?? CELL;
    const natH     = frame?.realHeight ?? CELL;
    const sprH     = CELL;                      // fit height to one cell
    const sprW     = sprH * (natW / natH);      // width follows aspect ratio
    const baseY    = y - 4;

    // ── Container holds drop-shadow + main sprite so they bob together ────────
    const container = this.add.container(x, baseY).setDepth(62);
    this._tokenObjs.push(container);

    // Dark drop-shadow — one copy, offset down-right, black tint.
    // Works correctly whether the PNG has a transparent or white background.
    container.add(
      this.add.image(3, 5, sprKey)
        .setDisplaySize(sprW, sprH)
        .setTint(0x000000)
        .setAlpha(0.50)
    );

    // Main sprite on top (no tint, full opacity)
    container.add(
      this.add.image(0, 0, sprKey).setDisplaySize(sprW, sprH)
    );

    // ── Bob tween — ONLY while it is this token's player's turn ──────────────
    if (isMyTurn) {
      const phaseDelay = (Math.random() * 350) | 0;   // stagger so tokens don't sync
      const tween = this.tweens.add({
        targets:  container,
        y:        baseY - 5,
        duration: 820,
        yoyo:     true,
        repeat:   -1,
        ease:     "Sine.easeInOut",
        delay:    phaseDelay,
      });
      this._tokenTweens.push(tween);
    }

    // ── Name label — sits just below the sprite bottom edge ──────────────────
    const label   = TOKEN_NAMES[key] ?? key.toUpperCase();
    const nameTxt = this.add.text(x, baseY + sprH / 2 + 5, label, {
      fontFamily: "monospace", fontSize: "7px",
      color:           moved ? "#ffd700" : "#f0e0c0",
      stroke:          "#000000",
      strokeThickness: 2,
    }).setOrigin(0.5, 0).setDepth(63);
    this._tokenObjs.push(nameTxt);

    // ── Gold checkmark badge when just moved ─────────────────────────────────
    if (moved) {
      const chk = this.add.text(x + sprW / 2 + 2, baseY - sprH / 2, "✓", {
        fontFamily: "monospace", fontSize: "11px",
        color: "#ffd700", stroke: "#000000", strokeThickness: 3,
      }).setOrigin(0, 1).setDepth(64);
      this._tokenObjs.push(chk);
    }
  }

  _drawDirectionArrow(cx, cy, direction, player) {
    // Drawn on lyrArrows (depth 65) — above sprite containers (depth 62).
    const g     = this.lyrArrows;
    const color = player === 1 ? 0xff6060 : 0x60ff90;

    let dx = 0, dy = 0;
    const len = CELL * 1.1;   // extend 1.1 cells from the sprite edge

    // Mirror backend cast_ray exactly:
    // P1: right / down / down-right    P2: left / up / up-left
    if (direction === "horizontal") {
      dx = player === 1 ? len : -len;
    } else if (direction === "vertical") {
      dy = player === 1 ? len : -len;
    } else {
      const d = len * 0.707;
      dx = player === 1 ?  d : -d;
      dy = player === 1 ?  d : -d;
    }

    // Normalise direction vector so we can offset the START point to the sprite edge
    const mag    = Math.hypot(dx, dy);
    const nx     = dx / mag;
    const ny     = dy / mag;
    const EDGE   = CELL * 0.38;   // ~half a sprite width — arrow starts here
    const startX = cx + nx * EDGE;
    const startY = cy + ny * EDGE;
    const endX   = cx + dx;
    const endY   = cy + dy;

    // Dashed shaft
    g.lineStyle(2.5, color, 0.9);
    drawDashed(g, startX, startY, endX, endY, 6, 4);

    // Arrowhead at the far end (pointing away from token)
    const angle = Math.atan2(dy, dx);
    const hw    = 0.42;
    const hl    = 10;
    g.fillStyle(color, 1);
    g.fillTriangle(
      endX, endY,
      endX - hl * Math.cos(angle - hw), endY - hl * Math.sin(angle - hw),
      endX - hl * Math.cos(angle + hw), endY - hl * Math.sin(angle + hw)
    );
  }

  // ─── Attack rays / defense zones ─────────────────────────────────────────

  _renderRays() {
    this._renderDefenseZone();

    const g = this.lyrRays;
    g.clear();

    // Preview attack rays
    if (!this.preview?.previews) return;
    for (const { rays } of this.preview.previews) {
      for (const ray of rays) {
        if (!ray.path?.length) continue;

        for (const cell of ray.path) {
          const bx = BOARD_OFF_X + cell.col * CELL;
          const by = BOARD_OFF_Y + cell.row * CELL;
          g.fillStyle(cell.hit ? COLORS.attackRayHit : COLORS.attackRay, cell.hit ? 0.3 : 0.1);
          g.fillRect(bx + 1, by + 1, CELL - 2, CELL - 2);
        }

        const first = ray.path[0], last = ray.path[ray.path.length - 1];
        const p1 = cellXY(first.col, first.row);
        const p2 = cellXY(last.col,  last.row);
        g.lineStyle(2.5, COLORS.attackRay, 0.9);
        drawDashed(g, p1.x, p1.y, p2.x, p2.y, 8, 5);

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

  _renderDefenseZone() {
    // Stop any running pulse tween
    if (this._defenseZoneTween) {
      try { this._defenseZoneTween.stop(); this._defenseZoneTween.remove(); } catch {}
      this._defenseZoneTween = null;
    }

    const dg = this.lyrDefenseZone;
    dg.clear();
    dg.setAlpha(1);

    const shields = this.gameState?.defense_shields ?? [];
    if (!shields.length) return;

    const shieldSet = new Set(shields.map(([c, r]) => `${c},${r}`));

    // ── Per-cell fill — cyan-blue shield tint ────────────────────────────────
    for (const [col, row] of shields) {
      const bx = BOARD_OFF_X + col * CELL;
      const by = BOARD_OFF_Y + row * CELL;

      // Checkerboard-style dual tones for depth
      const even = (col + row) % 2 === 0;
      dg.fillStyle(even ? 0x2060d8 : 0x1848b0, 0.30);
      dg.fillRect(bx + 1, by + 1, CELL - 2, CELL - 2);

      // Bright inner border on every cell edge that is NOT shared with another shield cell
      const sides = [[0,-1],[1,0],[0,1],[-1,0]];
      const edges = [
        [[bx+2, by+2],  [bx+CELL-2, by+2]],       // top
        [[bx+CELL-2, by+2],  [bx+CELL-2, by+CELL-2]], // right
        [[bx+2, by+CELL-2],  [bx+CELL-2, by+CELL-2]], // bottom
        [[bx+2, by+2],  [bx+2, by+CELL-2]],        // left
      ];
      dg.lineStyle(2, 0x60aaff, 0.85);
      sides.forEach(([dc, dr], i) => {
        if (!shieldSet.has(`${col+dc},${row+dr}`)) {
          const [[x1,y1],[x2,y2]] = edges[i];
          dg.strokeLineShape(new Phaser.Geom.Line(x1, y1, x2, y2));
        }
      });

      // Corner L-brackets — small cyan ticks that mark defended corners
      const br = 5;   // bracket arm length
      dg.lineStyle(2.5, 0xa0d0ff, 1);
      const corners = [
        [bx+4,  by+4,  +1, +1],   // top-left
        [bx+CELL-4, by+4,  -1, +1],   // top-right
        [bx+4,  by+CELL-4, +1, -1],   // bottom-left
        [bx+CELL-4, by+CELL-4, -1, -1],   // bottom-right
      ];
      for (const [cx, cy, sx, sy] of corners) {
        dg.strokeLineShape(new Phaser.Geom.Line(cx, cy, cx + sx*br, cy));
        dg.strokeLineShape(new Phaser.Geom.Line(cx, cy, cx, cy + sy*br));
      }
    }

    // ── Outer perimeter — thick bright border around whole zone ──────────────
    dg.lineStyle(2.5, 0x80c8ff, 1);
    for (const [col, row] of shields) {
      const bx = BOARD_OFF_X + col * CELL;
      const by = BOARD_OFF_Y + row * CELL;
      const sides = [[0,-1],[1,0],[0,1],[-1,0]];
      const perimEdges = [
        [[bx, by],[bx+CELL, by]],
        [[bx+CELL, by],[bx+CELL, by+CELL]],
        [[bx, by+CELL],[bx+CELL, by+CELL]],
        [[bx, by],[bx, by+CELL]],
      ];
      sides.forEach(([dc, dr], i) => {
        if (!shieldSet.has(`${col+dc},${row+dr}`)) {
          const [[x1,y1],[x2,y2]] = perimEdges[i];
          drawDashed(dg, x1, y1, x2, y2, 7, 4);
        }
      });
    }

    // ── "SHIELD" label at zone centre ────────────────────────────────────────
    const cols = shields.map(([c]) => c);
    const rows = shields.map(([,r]) => r);
    const midCol = (Math.min(...cols) + Math.max(...cols)) / 2;
    const midRow = (Math.min(...rows) + Math.max(...rows)) / 2;
    const { x: lx, y: ly } = cellXY(midCol, midRow);
    this._shieldLbl?.destroy();
    this._shieldLbl = this.add.text(lx, ly, "🛡", {
      fontSize: "18px",
    }).setOrigin(0.5).setDepth(43).setAlpha(0.75);

    // ── Pulse animation — lyrDefenseZone alpha breathes 0.7 → 1.0 ───────────
    this._defenseZoneTween = this.tweens.add({
      targets:  dg,
      alpha:    0.65,
      duration: 1100,
      yoyo:     true,
      repeat:   -1,
      ease:     "Sine.easeInOut",
    });
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

      const tint = result.outcome === "shielded"  ? 0x60ffaa
                 : result.outcome === "miss"        ? 0xaaaaff
                 : result.outcome === "base_hit"    ? 0xff2020   // bright red — HQ destroyed
                 : 0xffcc00;  // hit / terrain — golden

      // Fire sound when projectile launches
      this._playSound("shoot");

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
    // Impact sound — keyed to outcome type
    const soundMap = {
      hit:               "hit",
      base_hit:          "explosion",
      terrain_hit:       "terrain_hit",
      terrain_destroyed: "terrain_hit",
      shielded:          "shield",
      miss:              "miss",
    };
    this._playSound(soundMap[outcome] ?? "hit");

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
    burst.explode(outcome === "base_hit" ? 32 : outcome === "hit" ? 18 : 10);
    this.time.delayedCall(700, () => burst.destroy());

    // Screen shake on a real hit — harder shake for HQ
    if (outcome === "base_hit") {
      this.cameras.main.shake(500, 0.016);
    } else if (outcome === "hit" || outcome === "terrain_destroyed") {
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
      base_hit:          { color: "red",    verb: "⭐ FOUND & DESTROYED ENEMY HQ at" },
      shielded:          { color: "yellow", verb: "blocked by shield at" },
      terrain_hit:       { color: "yellow", verb: "damaged terrain at" },
      terrain_destroyed: { color: "red",    verb: "destroyed terrain at" },
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
    const tokens = this.gameState.tokens ?? {};

    // Both players must have all 3 tokens placed before the first attack
    const missing = [];
    for (const pid of [1, 2]) {
      for (const role of ["attack_a", "attack_b", "defense"]) {
        const t = tokens[`p${pid}_${role}`];
        if (!t || t.col < 0 || t.row < 0) {
          const label = TOKEN_NAMES[`p${pid}_${role}`] ?? role;
          missing.push(`P${pid} ${label}`);
        }
      }
    }
    if (missing.length === 0) return null;
    return `All tokens must be placed first.\nMissing: ${missing.join(", ")}`;
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
    // Destroy images from last render
    this._activeCellImgs.forEach(o => o.destroy());
    this._activeCellImgs = [];
    this.lyrActive.clear();

    if (!this.gameState?.active_cells) return;

    for (const [pidStr, cells] of Object.entries(this.gameState.active_cells)) {
      const pid    = Number(pidStr);
      const texKey = pid === 1 ? "active_farmer" : "active_emu";
      const hasTex = this.textures.exists(texKey);

      for (const [col, row] of cells) {
        const bx = BOARD_OFF_X + col * CELL;
        const by = BOARD_OFF_Y + row * CELL;

        if (hasTex) {
          // Full texture scaled to exactly one cell
          const img = this.add.image(bx + CELL / 2, by + CELL / 2, texKey)
            .setDisplaySize(CELL, CELL)
            .setDepth(10);
          this._activeCellImgs.push(img);
        } else {
          // Solid-colour fallback
          const even  = (col + row) % 2 === 0;
          const color = pid === 1
            ? (even ? COLORS.p1Active : COLORS.p1ActiveAlt)
            : (even ? COLORS.p2Active : COLORS.p2ActiveAlt);
          this.lyrActive.fillStyle(color, 1);
          this.lyrActive.fillRect(bx, by, CELL, CELL);
        }
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

  // ─── Terrain HP indicator dots ───────────────────────────────────────────

  _drawTerrainHPDots(x, y, width, hp, maxHp) {
    if (maxHp <= 0) return;
    const g = this.lyrTerrain;
    const dotR  = 3;
    const gap   = 2;
    const total = maxHp * (dotR * 2 + gap) - gap;
    const sx    = x + (width - total) / 2;
    for (let i = 0; i < maxHp; i++) {
      const cx = sx + i * (dotR * 2 + gap) + dotR;
      const alive = i < hp;
      g.fillStyle(alive ? 0xffffff : 0x333333, alive ? 0.9 : 0.4);
      g.fillCircle(cx, y, dotR);
      if (alive) {
        g.lineStyle(1, 0x000000, 0.5);
        g.strokeCircle(cx, y, dotR);
      }
    }
  }

  // ─── HQ placement phase ──────────────────────────────────────────────────

  _handleHQTap(col, row) {
    const p = this._hqUiPlayer;

    // Reject corner cells (A1 = 0,0 and L12 = 11,11)
    if ((col === 0 && row === 0) || (col === GRID_SIZE - 1 && row === GRID_SIZE - 1)) {
      this._showErrorToast("Can't place HQ on a\ncorner cell!");
      return;
    }

    // Validate own territory (must match backend exactly)
    const inMyTerritory = p === 1
      ? (col + row) < GRID_SIZE - 1
      : (col + row) >= GRID_SIZE - 1;

    if (!inMyTerritory) {
      this._showErrorToast("HQ must be placed in\nyour own territory!");
      return;
    }

    this.ws?.send("set_base", { player: p, col, row });
  }

  _renderHQPlacementUI() {
    // Clean up any existing HQ UI first
    this._hqUIObjs.forEach(o => o.destroy());
    this._hqUIObjs = [];

    const p = this._hqUiPlayer;

    // ── Territory highlight: tint the current player's territory ─────────────
    const g = this.add.graphics().setDepth(48).setAlpha(0.22);
    this._hqUIObjs.push(g);

    const hlColor = p === 1 ? 0x60e040 : 0xe07020;
    g.fillStyle(hlColor, 1);
    for (let col = 0; col < GRID_SIZE; col++) {
      for (let row = 0; row < GRID_SIZE; row++) {
        const inTerritory = p === 1
          ? (col + row) < GRID_SIZE - 1
          : (col + row) >= GRID_SIZE - 1;
        if (!inTerritory) continue;
        // Skip corners
        if ((col === 0 && row === 0) || (col === GRID_SIZE-1 && row === GRID_SIZE-1)) continue;
        const bx = BOARD_OFF_X + col * CELL;
        const by = BOARD_OFF_Y + row * CELL;
        g.fillRect(bx + 1, by + 1, CELL - 2, CELL - 2);
      }
    }

    // Corner cells marked with an X so the player knows they're forbidden
    const xg = this.add.graphics().setDepth(49);
    this._hqUIObjs.push(xg);
    xg.lineStyle(3, 0xff4444, 0.85);
    for (const [fc, fr] of [[0, 0], [GRID_SIZE-1, GRID_SIZE-1]]) {
      const bx = BOARD_OFF_X + fc * CELL;
      const by = BOARD_OFF_Y + fr * CELL;
      const pad = 6;
      xg.strokeLineShape(new Phaser.Geom.Line(bx+pad, by+pad, bx+CELL-pad, by+CELL-pad));
      xg.strokeLineShape(new Phaser.Geom.Line(bx+CELL-pad, by+pad, bx+pad, by+CELL-pad));
    }

    // ── Instruction banner ───────────────────────────────────────────────────
    const pName   = PLAYER_NAMES[p] ?? `Player ${p}`;
    const instrTx = this.add.text(
      CANVAS_W / 2,
      BOARD_OFF_Y + GRID_SIZE * CELL + 8,
      `${pName.toUpperCase()}: TAP YOUR TERRITORY TO PLACE HQ`,
      {
        fontFamily: "monospace", fontSize: "11px",
        color: p === 1 ? "#80ff60" : "#ffb060",
        stroke: "#000000", strokeThickness: 3,
      }
    ).setOrigin(0.5, 0).setDepth(49);
    this._hqUIObjs.push(instrTx);
  }

  _showHQPassOverlay(playerJustPlaced, onReady) {
    // Clear any existing pass overlay
    this._hqPassObjs.forEach(o => o.destroy());
    this._hqPassObjs = [];

    const cx   = CANVAS_W / 2;
    const cy   = CANVAS_H / 2;
    const pName = PLAYER_NAMES[playerJustPlaced] ?? `Player ${playerJustPlaced}`;
    const nextP = 3 - playerJustPlaced;
    const nextName = PLAYER_NAMES[nextP] ?? `Player ${nextP}`;

    // Dark full-screen overlay
    const overlay = this.add.rectangle(cx, cy, CANVAS_W, CANVAS_H, 0x050305, 0.94)
      .setDepth(300)
      .setInteractive({ useHandCursor: false });
    this._hqPassObjs.push(overlay);

    // Content box
    const box = this.add.graphics().setDepth(301);
    box.fillStyle(0x120a04, 1);
    box.fillRoundedRect(cx - 200, cy - 90, 400, 180, 14);
    box.lineStyle(2, 0x9a6a28, 1);
    box.strokeRoundedRect(cx - 200, cy - 90, 400, 180, 14);
    this._hqPassObjs.push(box);

    const lines = [
      { text: `${pName.toUpperCase()}'S HQ IS SET`, color: "#d4a030", size: "17px", dy: -58 },
      { text: `Hand the device to ${nextName}`, color: "#f0e0c0", size: "13px", dy: -20 },
      { text: `(other player look away now)`,   color: "#8a7060", size: "11px", dy: +6  },
      { text: `─────────────────────`,           color: "#4a3818", size: "12px", dy: +28 },
      { text: "Tap anywhere to continue",        color: "#60c060", size: "13px", dy: +54 },
    ];

    for (const { text, color, size, dy } of lines) {
      const t = this.add.text(cx, cy + dy, text, {
        fontFamily: "serif", fontSize: size,
        color, stroke: "#000000", strokeThickness: 2,
        align: "center",
      }).setOrigin(0.5).setDepth(302);
      this._hqPassObjs.push(t);
    }

    // Pulse the "Tap" line
    const tapTxt = this._hqPassObjs[this._hqPassObjs.length - 1];
    this.tweens.add({
      targets: tapTxt, alpha: 0.45, duration: 700,
      yoyo: true, repeat: -1, ease: "Sine.easeInOut",
    });

    // Tap overlay to proceed
    overlay.once("pointerdown", () => {
      this._hqPassObjs.forEach(o => o.destroy());
      this._hqPassObjs = [];
      onReady();
    });
  }

  // ─── Audio (Web Audio API, no asset files needed) ───────────────────────

  _initAudio() {
    try {
      this._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    } catch (e) {
      this._audioCtx = null;
    }
  }

  _playSound(type) {
    const ctx = this._audioCtx;
    if (!ctx) return;
    // Browser autoplay policy: resume context on first user gesture
    if (ctx.state === "suspended") ctx.resume();
    const t = ctx.currentTime;

    switch (type) {

      case "rotate": {
        // Short mechanical click — direction change feedback
        const osc  = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.type = "square";
        osc.frequency.setValueAtTime(520, t);
        osc.frequency.exponentialRampToValueAtTime(140, t + 0.055);
        gain.gain.setValueAtTime(0.22, t);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.055);
        osc.start(t); osc.stop(t + 0.06);
        break;
      }

      case "place": {
        // Satisfying low thunk — token placed on board
        const osc  = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.type = "sine";
        osc.frequency.setValueAtTime(220, t);
        osc.frequency.exponentialRampToValueAtTime(70, t + 0.09);
        gain.gain.setValueAtTime(0.45, t);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.11);
        osc.start(t); osc.stop(t + 0.12);
        break;
      }

      case "shoot": {
        // Rifle crack: sharp noise burst + low-end thump
        const dur  = 0.18;
        const rate = ctx.sampleRate;
        const buf  = ctx.createBuffer(1, Math.ceil(rate * dur), rate);
        const data = buf.getChannelData(0);
        for (let i = 0; i < data.length; i++)
          data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / data.length, 2.2);
        const src  = ctx.createBufferSource();
        src.buffer = buf;
        const bpf  = ctx.createBiquadFilter();
        bpf.type = "bandpass"; bpf.frequency.value = 1800; bpf.Q.value = 0.8;
        const gn   = ctx.createGain();
        gn.gain.setValueAtTime(1.0, t);
        gn.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        src.connect(bpf); bpf.connect(gn); gn.connect(ctx.destination);
        src.start(t); src.stop(t + dur);
        // Sub-bass thump underneath the crack
        const osc  = ctx.createOscillator();
        const gn2  = ctx.createGain();
        osc.connect(gn2); gn2.connect(ctx.destination);
        osc.type = "sine";
        osc.frequency.setValueAtTime(130, t);
        osc.frequency.exponentialRampToValueAtTime(35, t + 0.12);
        gn2.gain.setValueAtTime(0.65, t);
        gn2.gain.exponentialRampToValueAtTime(0.0001, t + 0.14);
        osc.start(t); osc.stop(t + 0.14);
        break;
      }

      case "hit": {
        // Territory destroyed — punchy low thud
        const dur  = 0.28;
        const rate = ctx.sampleRate;
        const buf  = ctx.createBuffer(1, Math.ceil(rate * dur), rate);
        const data = buf.getChannelData(0);
        for (let i = 0; i < data.length; i++)
          data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / data.length, 1.6);
        const src  = ctx.createBufferSource();
        src.buffer = buf;
        const lpf  = ctx.createBiquadFilter();
        lpf.type = "lowpass"; lpf.frequency.value = 380;
        const gn   = ctx.createGain();
        gn.gain.setValueAtTime(1.3, t);
        gn.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        src.connect(lpf); lpf.connect(gn); gn.connect(ctx.destination);
        src.start(t); src.stop(t + dur);
        break;
      }

      case "shield": {
        // Metallic deflection ping — two harmonics that decay quickly
        [[1800, 0.45], [2700, 0.22]].forEach(([freq, vol], i) => {
          const osc  = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain); gain.connect(ctx.destination);
          osc.type = "sine";
          osc.frequency.setValueAtTime(freq, t);
          osc.frequency.exponentialRampToValueAtTime(freq * 0.35, t + 0.32);
          gain.gain.setValueAtTime(vol, t);
          gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.32);
          osc.start(t); osc.stop(t + 0.33);
        });
        break;
      }

      case "terrain_hit": {
        // Stone/wood crack — mid-band noise burst
        const dur  = 0.16;
        const rate = ctx.sampleRate;
        const buf  = ctx.createBuffer(1, Math.ceil(rate * dur), rate);
        const data = buf.getChannelData(0);
        for (let i = 0; i < data.length; i++)
          data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / data.length, 2.8);
        const src  = ctx.createBufferSource();
        src.buffer = buf;
        const bpf  = ctx.createBiquadFilter();
        bpf.type = "bandpass"; bpf.frequency.value = 700; bpf.Q.value = 1.4;
        const gn   = ctx.createGain();
        gn.gain.setValueAtTime(0.9, t);
        gn.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        src.connect(bpf); bpf.connect(gn); gn.connect(ctx.destination);
        src.start(t); src.stop(t + dur);
        break;
      }

      case "explosion": {
        // HQ destroyed — deep rumbling explosion
        const dur  = 0.85;
        const rate = ctx.sampleRate;
        const buf  = ctx.createBuffer(1, Math.ceil(rate * dur), rate);
        const data = buf.getChannelData(0);
        for (let i = 0; i < data.length; i++)
          data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / data.length, 1.1);
        const src  = ctx.createBufferSource();
        src.buffer = buf;
        const lpf  = ctx.createBiquadFilter();
        lpf.type = "lowpass"; lpf.frequency.value = 180;
        const gn   = ctx.createGain();
        gn.gain.setValueAtTime(1.6, t);
        gn.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        src.connect(lpf); lpf.connect(gn); gn.connect(ctx.destination);
        src.start(t); src.stop(t + dur);
        // Sub-bass rumble sine
        const osc  = ctx.createOscillator();
        const gn2  = ctx.createGain();
        osc.connect(gn2); gn2.connect(ctx.destination);
        osc.type = "sine";
        osc.frequency.setValueAtTime(90, t);
        osc.frequency.exponentialRampToValueAtTime(18, t + 0.6);
        gn2.gain.setValueAtTime(1.1, t);
        gn2.gain.exponentialRampToValueAtTime(0.0001, t + 0.6);
        osc.start(t); osc.stop(t + 0.6);
        break;
      }

      case "miss": {
        // Whoosh / ricochet — descending sawtooth
        const osc  = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(550, t);
        osc.frequency.exponentialRampToValueAtTime(90, t + 0.22);
        gain.gain.setValueAtTime(0.14, t);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.22);
        osc.start(t); osc.stop(t + 0.23);
        break;
      }
    }
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
