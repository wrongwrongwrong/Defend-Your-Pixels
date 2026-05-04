/**
 * Main GameScene class for Old Mick Against the Mob.
 * Integrates all modules and handles the game lifecycle.
 * @module game-scene
 */

import {
  CELL, COLS, ROWS, BX, BY, PANEL_X, PW, W, H, C,
  ARROW_CHAR, WARNING_SHOW_MS, WARNING_REPEAT_GAP_MS, WARNING_RECENT_MS
} from './constants.js';
import { SFX, initAudioUnlock } from './sound.js';
import {
  cc, isP1, isP2, hex, cellLabel, phaseLabel, sideLabel,
  sideOwnsCell, computeRay, defZoneCells, buildResourceMaps,
  primaryError, errorTitle, errorMessage, errorTone
} from './helpers.js';
import { TutorialManager, isTutorialMode } from './tutorial.js';
import { SetupUIManager, drawPendingHqCandidate } from './setup-ui.js';
import {
  dashLine, dashRect, drawStar,
  drawTerrain, drawDamageLayer, drawScorched,
  drawDefZone, drawRay, drawToken, drawPlacementGuide
} from './drawing.js';

// Shared state
let gameState = null;
let prevState = null;
let wsInstance = null;

const IS_TUTORIAL = isTutorialMode();

/**
 * Detect state changes and trigger sounds.
 */
function detectSoundEvents(prev, curr) {
  if (!prev || !curr) return;

  if (prev.turn !== curr.turn && curr.turn !== null) SFX.turn();
  if (prev.map_seed !== curr.map_seed) SFX.lock();

  const checkMove = (a, b) => {
    if (!a || !b) return;
    if (a.col !== b.col || a.row !== b.row) {
      if (b.col !== null) SFX.place();
    }
  };
  if (prev.p1 && curr.p1) {
    checkMove(prev.p1.atk_a, curr.p1.atk_a);
    checkMove(prev.p1.atk_b, curr.p1.atk_b);
    checkMove(prev.p1.def,   curr.p1.def);
  }
  if (prev.p2 && curr.p2) {
    checkMove(prev.p2.atk_a, curr.p2.atk_a);
    checkMove(prev.p2.atk_b, curr.p2.atk_b);
    checkMove(prev.p2.def,   curr.p2.def);
  }
}

/**
 * Main Phaser GameScene class.
 */
export class GameScene extends Phaser.Scene {
  constructor() {
    super({ key: 'GameScene' });
    this.tutorialManager = null;
    this.setupUIManager = null;
  }

  create() {
    this.boardGfx = this.add.graphics().setDepth(0);
    this.dynGfx   = this.add.graphics().setDepth(2);

    this._drawBoardLabels();
    this._drawStaticBoard();
    this._buildPanel();
    this._buildSetupUi();
    this._buildWarningUi();
    this._buildLabels();
    this._buildLockButton();
    this._connectWS();

    if (IS_TUTORIAL) {
      this.tutorialManager = new TutorialManager(this);
      this.tutorialManager.init();
    }

    this.time.addEvent({ delay: 50, callback: this._applyState, callbackScope: this, loop: true });
    this.input.on('pointerdown', this._handleBoardPointerDown, this);

    this.tweens.add({
      targets: this.lockBtnGfx, alpha: { from: 1, to: 0.55 },
      yoyo: true, repeat: -1, duration: 800, ease: 'Sine.easeInOut'
    });

    initAudioUnlock();
  }

  _drawBoardLabels() {
    for (let c = 0; c < COLS; c++) {
      this.add.text(BX + c * CELL + CELL / 2 - 4, BY - 18,
        String.fromCharCode(65 + c),
        { fontSize: '11px', color: '#d8b070', fontFamily: 'Georgia', fontStyle: 'bold' });
    }
    for (let r = 0; r < ROWS; r++) {
      this.add.text(BX - 22, BY + r * CELL + CELL / 2 - 7,
        String(r + 1),
        { fontSize: '11px', color: '#d8b070', fontFamily: 'Georgia', fontStyle: 'bold' });
    }
  }

  _drawStaticBoard(terrain, illuminatedSide = null) {
    const g = this.boardGfx;
    g.clear();
    if (this._boardBadges) {
      this._boardBadges.forEach((badge) => badge.destroy());
      this._boardBadges = [];
    }

    const resourceKey = (c, r) => `${c},${r}`;
    const { p1: p1ResourceMap, p2: p2ResourceMap } = buildResourceMaps(terrain);
    const illuminate = illuminatedSide;

    g.fillStyle(0x0c0804, 1);
    g.fillRoundedRect(BX - 10, BY - 10, COLS * CELL + 20, ROWS * CELL + 20, 14);

    for (let r = 0; r < ROWS; r++) {
      for (let c = 0; c < COLS; c++) {
        const x = BX + c * CELL, y = BY + r * CELL;
        const w = CELL - 1, h = CELL - 1;
        const onFence  = (c + r === 11);
        const p1side   = isP1(c, r);
        const ownerSide = p1side ? 'p1' : 'p2';
        const key = resourceKey(c, r);
        const resource = p1side ? p1ResourceMap[key] : p2ResourceMap[key];
        const isResource = !!resource;

        let baseFill = C.board_bg;
        let fillAlpha = 1;
        let strongBorder = false;

        if (onFence) {
          baseFill = C.fence_cell;
          fillAlpha = 1;
        } else if (isResource) {
          const isIlluminatedResource = !illuminate || ownerSide === illuminate;
          if (isIlluminatedResource) {
            baseFill = ownerSide === 'p1' ? C.p1_target : C.p2_target;
            fillAlpha = 1;
            strongBorder = true;
          } else {
            baseFill = ownerSide === 'p1' ? C.farmer_cell : C.emu_cell;
            fillAlpha = 0.30;
          }
        } else {
          baseFill = C.board_bg;
          fillAlpha = 1;
        }

        g.fillStyle(baseFill, fillAlpha);
        g.fillRoundedRect(x + 1, y + 1, w - 1, h - 1, 4);

        g.fillStyle(0xffffff, 0.07);
        g.fillRoundedRect(x + 1, y + 1, w - 1, (h - 1) / 2, 4);
        g.fillStyle(0x000000, 0.10);
        g.fillRect(x + 2, y + h - 4, w - 3, 3);

        if (strongBorder) {
          g.lineStyle(1.5, 0x000000, 0.35);
        } else {
          g.lineStyle(1, 0x000000, 0.12);
        }
        g.strokeRoundedRect(x + 1, y + 1, w - 1, h - 1, 4);

        const isIlluminatedResource = !illuminate || ownerSide === illuminate;
        if (resource?.visible && resource?.value === 5 && isIlluminatedResource) {
          g.lineStyle(3, 0xffe070, 0.95);
          g.strokeRoundedRect(x + 3, y + 3, w - 5, h - 5, 6);
          g.fillStyle(0x120904, 0.55);
          g.fillRoundedRect(x + 14, y + 12, 22, 16, 5);
          const badge = this.add.text(x + 25, y + 20, '5', {
            fontSize: '12px', fontFamily: 'Georgia', color: '#ffe070', fontStyle: 'bold'
          }).setOrigin(0.5, 0.5).setDepth(1);
          if (!this._boardBadges) this._boardBadges = [];
          this._boardBadges.push(badge);
        }
      }
    }

    g.lineStyle(6, 0x000000, 0.30);
    g.lineBetween(BX + COLS * CELL, BY, BX, BY + ROWS * CELL);
    g.lineStyle(3, 0x8b5a20, 0.95);
    g.lineBetween(BX + COLS * CELL, BY, BX, BY + ROWS * CELL);

    for (let i = 0; i < 12; i++) {
      const t = (i + 0.5) / 12;
      const fx = BX + COLS * CELL - t * COLS * CELL;
      const fy = BY + t * ROWS * CELL;
      g.fillStyle(0x000000, 0.3);
      g.fillEllipse(fx + 1, fy + 8, 10, 3);
      g.fillStyle(0x6a3a10, 1);
      g.fillRoundedRect(fx - 3, fy - 10, 6, 18, 2);
      g.fillStyle(0xb07a30, 0.8);
      g.fillRect(fx - 2, fy - 9, 1.5, 16);
    }

    g.fillStyle(0x2a1a0a, 0.95);
    g.fillRoundedRect(BX - 2, 4, COLS * CELL + 4, 46, 10);
    g.lineStyle(1.5, 0x8a6030, 0.9);
    g.strokeRoundedRect(BX - 2, 4, COLS * CELL + 4, 46, 10);
    for (const sx of [BX + 12, BX + COLS * CELL - 20]) {
      g.fillStyle(0xf0d070, 1);
      drawStar(g, sx, 27, 7, 3, 5);
    }

    if (!this._titleDrawn) {
      this.add.text(BX + COLS * CELL / 2, 14, '⭐  OLD MICK  vs  THE MOB  ⭐', {
        fontSize: '19px', fontFamily: 'Georgia', color: '#f8d870',
        fontStyle: 'bold', stroke: '#3a2010', strokeThickness: 3,
      }).setOrigin(0.5, 0);
      this.add.text(BX + COLS * CELL / 2, 35, '~ 1932 Great Emu War ~', {
        fontSize: '11px', fontFamily: 'Georgia', color: '#d0a060', fontStyle: 'italic',
      }).setOrigin(0.5, 0);
      this._titleDrawn = true;
    }
  }

  _buildPanel() {
    const g   = this.boardGfx;
    const px  = PANEL_X;

    g.fillStyle(C.panel_bg, 1);
    g.fillRect(px, 0, PW, H);
    g.lineStyle(1, C.panel_border, 0.8);
    g.strokeRect(px, 0, PW, H);

    const sep = (y) => {
      g.lineStyle(0.5, C.panel_border, 0.4);
      g.lineBetween(px + 6, y, px + PW - 6, y);
    };

    const T = (x, y, str, col, size = '11px') =>
      this.add.text(px + x, y, str, {
        fontSize: size, fontFamily: 'Georgia', color: col
      });

    T(8, 10, '⚔  BATTLE LOG', '#f0d070', '13px');
    sep(30);
    this.turnText   = T(8, 36, 'Phase: —', '#f0d070', '13px');
    sep(58);

    T(8, 64, 'TERRAIN', '#c8a050', '11px');
    T(8, 80, '██ Hard  — impassable (blocks ray)', '#b0a080');
    T(8, 93, '▪▪ Soft  — absorbs hit (2 hits)', '#c8d860');
    sep(108);

    T(8, 112, 'TIER UPGRADES', '#c8a050', '11px');

    this.scoreText  = T(8, H - 174, 'Paddock score: 0/40  Feeding ground score: 0/40', '#ffb060', '10px');
    this.cornerText = T(8, H - 156, 'Corners: 0/4', '#a08040');
    this.wsText     = T(8, H - 138, '◌ connecting…', '#888860');

    this.p1TierTxt = T(8,  130, 'P1 Tier: 0', '#f0c060');
    this.p2TierTxt = T(8,  144, 'P2 Tier: 0', '#90e050');

    const mkBtn = (label, x, y, cb, col) => {
      const btn = this.add.text(PANEL_X + x, y, label,
        { fontSize: '11px', fontFamily: 'Georgia', color: col,
          backgroundColor: '#2a2010', padding: { x: 4, y: 2 } })
        .setInteractive({ useHandCursor: true });
      btn.on('pointerdown', cb);
      btn.on('pointerover', () => btn.setColor('#ffffff'));
      btn.on('pointerout',  () => btn.setColor(col));
      return btn;
    };

    this._p1Tier = 0;
    this._p2Tier = 0;
    mkBtn('[P1 +Tier]', 8,  272, () => this._changeTier(1,  1), '#f0c060');
    mkBtn('[P1 −Tier]', 90, 272, () => this._changeTier(1, -1), '#c8a040');
    mkBtn('[P2 +Tier]', 8,  288, () => this._changeTier(2,  1), '#90e050');
    mkBtn('[P2 −Tier]', 90, 288, () => this._changeTier(2, -1), '#70c030');

    T(8, 320, 'LATEST ALERT', '#c89060', '11px');
    this.warningMiniTxt = this.add.text(PANEL_X + 8, 338, 'Recent alert: none', {
      fontSize: '10px', fontFamily: 'Georgia', color: '#9a7a58',
      wordWrap: { width: PW - 16 },
    });

    const mkActionBtn = (label, x, y, width, bgColor, color, onClick) => {
      const btn = this.add.text(PANEL_X + x, y, label, {
        fontSize: '11px', fontFamily: 'Georgia', color,
        backgroundColor: bgColor, padding: { x: 6, y: 4 }, fontStyle: 'bold',
      }).setInteractive({ useHandCursor: true }).setVisible(false);
      btn._baseColor = color;
      btn._baseBgColor = bgColor;
      btn._enabled = true;
      btn._fullWidth = width;
      btn.setFixedSize(width, 24);
      btn.setAlign('center');
      btn.on('pointerdown', () => { if (btn._enabled) onClick(); });
      btn.on('pointerover', () => {
        if (btn._enabled) btn.setColor('#fff8dc');
      });
      btn.on('pointerout', () => {
        btn.setColor(btn._enabled ? btn._baseColor : '#8a7a68');
      });
      return btn;
    };

    this.nukeBtn = mkActionBtn('Arm Nuke', 8, 400, 194, '#5a1f12', '#ffd070', () => {
      const activeSide = gameState?.turn === 1 ? 'p1' : gameState?.turn === 2 ? 'p2' : null;
      if (!activeSide) return;
      this._nukeArmingSide = this._nukeArmingSide === activeSide ? null : activeSide;
    });
    this._nukeArmingSide = null;
  }

  _buildSetupUi() {
    const tx = BX + 24;
    const ty = BY + 18;
    const titleStyle = {
      fontSize: '16px', fontFamily: 'Georgia', fontStyle: 'bold', color: '#fff0b0',
      stroke: '#2a1408', strokeThickness: 3,
    };
    const bodyStyle = {
      fontSize: '12px', fontFamily: 'Georgia', color: '#f2d8a0',
      stroke: '#241208', strokeThickness: 2,
    };
    const monoStyle = {
      fontSize: '11px', fontFamily: 'monospace', color: '#e6d2a8',
      stroke: '#1e0e06', strokeThickness: 2,
    };

    this.setupCardGfx = this.add.graphics().setDepth(18).setVisible(false);
    this.setupTitleTxt = this.add.text(tx, ty, '', titleStyle).setDepth(19).setVisible(false);
    this.setupStatusTxt = this.add.text(tx, ty + 24, '', {
      ...bodyStyle,
      wordWrap: { width: COLS * CELL - 110 },
    }).setDepth(19).setVisible(false);
    this.setupScanTxt = this.add.text(tx, ty + 80, '', monoStyle).setDepth(19).setVisible(false);
    this.setupSideTxt = this.add.text(tx, ty + 98, '', monoStyle).setDepth(19).setVisible(false);
    this.setupActiveTxt = this.add.text(tx, ty + 116, '', monoStyle).setDepth(19).setVisible(false);
    this.setupP1Txt = this.add.text(tx, ty + 134, '', monoStyle).setDepth(19).setVisible(false);
    this.setupP2Txt = this.add.text(tx, ty + 152, '', monoStyle).setDepth(19).setVisible(false);
    this.setupHintTxt = this.add.text(tx, ty + 174, 'Confirmed HQ cells stay hidden until an HQ is destroyed.', {
      fontSize: '11px', fontFamily: 'Georgia', fontStyle: 'italic', color: '#ffdf90',
      stroke: '#2a1408', strokeThickness: 2,
    }).setDepth(19).setVisible(false);

    this.setupSelection = {
      pendingBySide: { p1: null, p2: null },
    };
  }

  _buildWarningUi() {
    this.warningState = {
      activeCode: null,
      activeTitle: '',
      activeMessage: '',
      activeTone: 'error',
      showUntil: 0,
      suppressUntil: 0,
      recentTitle: '',
      recentMessage: '',
      recentTone: 'error',
      recentUntil: 0,
    };

    const centerX = BX + COLS * CELL / 2;
    const topY = BY + 96;
    this.warningCardGfx = this.add.graphics().setDepth(24).setVisible(false);
    this.warningTitleTxt = this.add.text(centerX, topY, '', {
      fontSize: '18px', fontFamily: 'Georgia', fontStyle: 'bold', color: '#ffe0a0',
      stroke: '#2a1008', strokeThickness: 3,
    }).setOrigin(0.5, 0).setDepth(25).setVisible(false);
    this.warningBodyTxt = this.add.text(centerX, topY + 28, '', {
      fontSize: '13px', fontFamily: 'Georgia', color: '#ffd0a0', align: 'center',
      wordWrap: { width: 380 }, stroke: '#220c06', strokeThickness: 2,
    }).setOrigin(0.5, 0).setDepth(25).setVisible(false);
  }

  _buildLabels() {
    this.labels = {};
    this.arrows = {};
    const mkLabel = (key, txt, col, bgCol) => {
      this.labels[key] = this.add.text(0, 0, txt, {
        fontSize: '9px', fontFamily: 'monospace', fontStyle: 'bold',
        color: col, backgroundColor: bgCol, padding: { x: 2, y: 1 }
      }).setDepth(10).setVisible(false);
    };
    const mkArrow = (key, col) => {
      this.arrows[key] = this.add.text(0, 0, '', {
        fontSize: '22px', fontFamily: 'sans-serif', color: col,
        stroke: '#000', strokeThickness: 4,
      }).setDepth(11).setOrigin(0.5, 0.5).setVisible(false);
    };
    mkLabel('p1_atk_a', 'A1', '#fff0b0', '#8a5020'); mkArrow('p1_atk_a', '#fff0b0');
    mkLabel('p1_atk_b', 'A2', '#fff0b0', '#8a5020'); mkArrow('p1_atk_b', '#fff0b0');
    mkLabel('p1_def',   'D',  '#fff0b0', '#6a3a18');
    mkLabel('p2_atk_a', 'A1', '#e0ffb0', '#2a6018'); mkArrow('p2_atk_a', '#e0ffb0');
    mkLabel('p2_atk_b', 'A2', '#e0ffb0', '#2a6018'); mkArrow('p2_atk_b', '#e0ffb0');
    mkLabel('p2_def',   'D',  '#e0ffb0', '#1a4a10');
  }

  _buildLockButton() {
    const lx = PANEL_X + 8, ly = H - 116, lw = PW - 16, lh = 28;
    this.lockBtnGfx = this.add.graphics().setDepth(12);
    this.lockBtnGfx.fillStyle(0x44aa30, 1);
    this.lockBtnGfx.fillRoundedRect(lx, ly, lw, lh, 6);
    this.lockBtnGfx.lineStyle(2, 0x88ee60, 0.85);
    this.lockBtnGfx.strokeRoundedRect(lx, ly, lw, lh, 6);

    this.lockBtnTxt = this.add.text(lx + lw / 2, ly + lh / 2, '🔒 LOCK TERRAIN', {
      fontSize: '13px', fontFamily: 'Georgia', color: '#ffffff', fontStyle: 'bold',
    }).setOrigin(0.5, 0.5).setDepth(13);

    const hitArea = new Phaser.Geom.Rectangle(lx, ly, lw, lh);
    const hitZone = this.add.zone(lx, ly, lw, lh).setOrigin(0, 0).setInteractive({ hitArea, useHandCursor: true });
    hitZone.on('pointerdown', () => {
      this._requestNewMap();
    });

    const nmx = PANEL_X + 8, nmy = H - 80, nmw = PW - 16, nmh = 24;
    this.newMapBtnGfx = this.add.graphics().setDepth(12);
    this.newMapBtnGfx.fillStyle(0x3a6a28, 1);
    this.newMapBtnGfx.fillRoundedRect(nmx, nmy, nmw, nmh, 5);
    this.newMapBtnGfx.lineStyle(1.5, 0x70c050, 0.8);
    this.newMapBtnGfx.strokeRoundedRect(nmx, nmy, nmw, nmh, 5);

    this.add.text(nmx + nmw / 2, nmy + nmh / 2, '🔄 NEW MAP', {
      fontSize: '11px', fontFamily: 'Georgia', color: '#d0f0a0', fontStyle: 'bold',
    }).setOrigin(0.5, 0.5).setDepth(13);

    const nmHitZone = this.add.zone(nmx, nmy, nmw, nmh).setOrigin(0, 0)
      .setInteractive({ hitArea: new Phaser.Geom.Rectangle(0, 0, nmw, nmh), useHandCursor: true });
    nmHitZone.on('pointerdown', () => this._requestNewMap());
  }

  _connectWS() {
    wsInstance = new WebSocket('ws://localhost:8765');
    wsInstance.onopen = () => {
      this.wsText.setText('● connected').setColor('#44ff88');
    };
    wsInstance.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        detectSoundEvents(prevState, data);
        prevState  = gameState;
        gameState  = data;
      } catch(_) {}
    };
    wsInstance.onclose = () => {
      this.wsText.setText('◌ disconnected — retry…').setColor('#ff8844');
      setTimeout(() => this._connectWS(), 2000);
    };
    wsInstance.onerror = () => {
      this.wsText.setText('✕ WS error').setColor('#ff2200');
    };
  }

  _sendAction(data) {
    if (!wsInstance || wsInstance.readyState !== WebSocket.OPEN) return;
    wsInstance.send(JSON.stringify({ type: 'action', data }));
  }

  _requestNewMap() {
    if (wsInstance && wsInstance.readyState === WebSocket.OPEN) {
      wsInstance.send(JSON.stringify({ type: 'new_map' }));
    }
    this.tweens.add({
      targets: this.newMapBtnGfx,
      alpha: { from: 0.5, to: 1 }, duration: 250, ease: 'Sine.easeOut',
    });
    SFX.lock();
  }

  _changeTier(player, delta) {
    if (player === 1) {
      this._p1Tier = Math.max(0, Math.min(4, this._p1Tier + delta));
      this.p1TierTxt.setText(`P1 Tier: ${this._p1Tier}`);
    } else {
      this._p2Tier = Math.max(0, Math.min(4, this._p2Tier + delta));
      this.p2TierTxt.setText(`P2 Tier: ${this._p2Tier}`);
    }
  }

  _placeLabel(key, col, row) {
    const lbl = this.labels[key];
    if (!lbl) return;
    if (col == null || row == null) { lbl.setVisible(false); return; }
    const { x, y } = cc(col, row);
    lbl.setPosition(x + 12, y - 18).setVisible(true);
  }

  _placeArrow(key, tok) {
    const arrow = this.arrows[key];
    if (!arrow) return;
    if (!tok || tok.col == null || !tok.direction) { arrow.setVisible(false); return; }
    const { x, y } = cc(tok.col, tok.row);
    arrow.setText(ARROW_CHAR[tok.direction] || '').setPosition(x, y - 26).setVisible(true);
  }

  _setActionButtonState(button, { visible, enabled, label = null }) {
    if (!button) return;
    if (label != null) button.setText(label);
    button._enabled = enabled;
    button.setVisible(visible);
    button.setAlpha(enabled ? 1 : 0.45);
    button.setColor(enabled ? button._baseColor : '#8a7a68');
    button.setBackgroundColor(enabled ? button._baseBgColor : '#241812');
    if (button.input) button.input.enabled = visible && enabled;
  }

  _ensureSetupModal() {
    if (this._setupModal) return;

    const overlay = this.add.graphics().setDepth(54);
    const gfx = this.add.graphics().setDepth(55);

    const titleTxt = this.add.text(0, 0, '', {
      fontSize: '18px', fontFamily: 'Georgia', color: '#ffe070', fontStyle: 'bold',
    }).setDepth(56);

    const bodyTxt = this.add.text(0, 0, '', {
      fontSize: '15px', fontFamily: 'Georgia', color: '#f2d8a0', lineSpacing: 6,
    }).setDepth(56);

    const candidateTxt = this.add.text(0, 0, '', {
      fontSize: '13px', fontFamily: 'monospace', color: '#d8c890', lineSpacing: 5,
    }).setDepth(56);

    const instructionHintTxt = this.add.text(0, 0, '[ Click anywhere to continue ]', {
      fontSize: '14px', fontFamily: 'Georgia', fontStyle: 'italic', color: '#ffe070',
    }).setDepth(56).setVisible(false);

    const mkModalBtn = (label, bgColor, color, onClick) => {
      const btn = this.add.text(0, 0, label, {
        fontSize: '13px', fontFamily: 'Georgia', color,
        backgroundColor: bgColor, padding: { x: 10, y: 8 }, fontStyle: 'bold',
      }).setInteractive({ useHandCursor: true }).setDepth(56).setOrigin(0.5, 0.5);
      btn._baseColor = color;
      btn._baseBgColor = bgColor;
      btn._enabled = true;
      btn.on('pointerdown', () => { if (btn._enabled) onClick(); });
      btn.on('pointerover', () => { if (btn._enabled) btn.setColor('#fff8dc'); });
      btn.on('pointerout', () => { btn.setColor(btn._enabled ? btn._baseColor : '#8a7a68'); });
      return btn;
    };

    const confirmBtn = mkModalBtn('Confirm HQ', '#6a3812', '#ffe0a0', () => {
      const activeSide = gameState?.setup?.active_setup_side;
      if (activeSide) this._sendAction({ action: 'confirm_hq', side: activeSide });
    });

    const cancelBtn = mkModalBtn('Cancel', '#402318', '#f0c8b0', () => {
      const activeSide = gameState?.setup?.active_setup_side;
      if (activeSide) this.setupSelection.pendingBySide[activeSide] = null;
      this._hqCandidateCancelled = true;
      this._setSetupModalVisible(false);
    });

    this.confirmHqBtn = confirmBtn;
    this.cancelHqBtn = cancelBtn;

    overlay.setInteractive(new Phaser.Geom.Rectangle(0, 0, W, H), Phaser.Geom.Rectangle.Contains);
    overlay.input.enabled = false;
    overlay.on('pointerdown', (pointer) => {
      if (!this._setupModal?.visible) return;
      if (gameState?.phase !== 'hq_placement') return;
      if (this._hqPlacementInstructionAck) return;
      try { pointer.event?.stopPropagation?.(); } catch (_) {}
      this._hqPlacementInstructionAck = true;
      if (this._setupModal.overlay?.input) this._setupModal.overlay.input.enabled = false;
      this._setSetupModalVisible(false);
    });

    this._setupModal = {
      overlay, gfx, titleTxt, bodyTxt, candidateTxt, instructionHintTxt,
      confirmBtn, cancelBtn, visible: false,
    };

    this._layoutSetupModal();
    this._setSetupModalVisible(false);
  }

  _setSetupModalVisible(visible) {
    if (!this._setupModal) return;
    this._setupModal.visible = visible;
    const { overlay, gfx, titleTxt, bodyTxt, candidateTxt, instructionHintTxt, confirmBtn, cancelBtn } = this._setupModal;
    overlay.setVisible(visible);
    gfx.setVisible(visible);
    titleTxt.setVisible(visible);
    bodyTxt.setVisible(visible);
    if (!visible) {
      instructionHintTxt.setVisible(false);
      candidateTxt.setVisible(false);
      confirmBtn.setVisible(false);
      cancelBtn.setVisible(false);
      if (confirmBtn.input) confirmBtn.input.enabled = false;
      if (cancelBtn.input) cancelBtn.input.enabled = false;
      if (overlay.input) overlay.input.enabled = false;
    }
  }

  _layoutSetupModal() {
    if (!this._setupModal) return;

    const modalW = Math.min(560, W * 0.92);
    const padX = 20;
    const padY = 18;
    const centerX = W / 2;
    const centerY = H / 2 - 10;

    const { overlay, gfx, titleTxt, bodyTxt, candidateTxt, instructionHintTxt, confirmBtn, cancelBtn } = this._setupModal;
    const wrapW = modalW - padX * 2;

    titleTxt.setWordWrapWidth(wrapW, true);
    bodyTxt.setWordWrapWidth(wrapW, true);
    candidateTxt.setWordWrapWidth(wrapW, true);

    const titleH = titleTxt.height || 24;
    const bodyH = bodyTxt.height || 0;
    const hintLineH = instructionHintTxt.visible ? (instructionHintTxt.height || 18) : 0;
    const candH = candidateTxt.visible ? (candidateTxt.height || 0) : 0;
    const gapTitleBody = 10;
    const gapBodyHint = instructionHintTxt.visible ? 10 : 0;
    const gapBodyCand = candidateTxt.visible ? 10 : 0;
    const gapCandBtns = 16;
    const showConfirm = !!confirmBtn.visible;
    const showCancel = !!cancelBtn.visible;
    const anyButtons = showConfirm || showCancel;
    const btnH = anyButtons ? 40 : 0;
    const gapAfterCand = anyButtons ? gapCandBtns : 0;
    const modalH = padY + titleH + gapTitleBody + bodyH + gapBodyHint + hintLineH + gapBodyCand + candH + gapAfterCand + btnH + padY;

    const modalX = centerX - modalW / 2;
    const modalY = centerY - modalH / 2;

    overlay.clear();
    overlay.fillStyle(0x000000, 0.35);
    overlay.fillRect(0, 0, W, H);

    gfx.clear();
    gfx.fillStyle(0x2a2010, 1);
    gfx.lineStyle(2, 0x6a4a20, 1);
    gfx.fillRoundedRect(modalX, modalY, modalW, modalH, 14);
    gfx.strokeRoundedRect(modalX, modalY, modalW, modalH, 14);

    titleTxt.setPosition(modalX + padX, modalY + padY);

    let y = modalY + padY + titleH + gapTitleBody;
    bodyTxt.setPosition(modalX + padX, y);
    y += bodyH;
    if (instructionHintTxt.visible) {
      y += gapBodyHint;
      instructionHintTxt.setPosition(modalX + padX, y);
      y += hintLineH;
    }
    if (candidateTxt.visible) y += gapBodyCand;
    if (candidateTxt.visible) {
      candidateTxt.setPosition(modalX + padX, y);
    }

    if (anyButtons) {
      const btnY = modalY + modalH - padY - btnH / 2;
      const gap = 18;
      if (showConfirm && showCancel) {
        confirmBtn.setPosition(centerX - (194 / 2 + gap / 2), btnY);
        cancelBtn.setPosition(centerX + (194 / 2 + gap / 2), btnY);
      } else if (showConfirm) {
        confirmBtn.setPosition(centerX, btnY);
        cancelBtn.setPosition(-10000, -10000);
      } else {
        cancelBtn.setPosition(centerX, btnY);
        confirmBtn.setPosition(-10000, -10000);
      }
      confirmBtn.setFixedSize(194, btnH);
      cancelBtn.setFixedSize(194, btnH);
      confirmBtn.setAlign('center');
      cancelBtn.setAlign('center');
    } else {
      confirmBtn.setPosition(-10000, -10000);
      cancelBtn.setPosition(-10000, -10000);
    }
  }

  _syncSetupSelection(phase, setup) {
    const hq = setup.hq || {};
    ['p1', 'p2'].forEach((side) => {
      const sideState = hq[side] || {};
      if (phase !== 'hq_placement') {
        this.setupSelection.pendingBySide[side] = null;
        return;
      }
      if (sideState.confirmed || sideState.has_candidate === false) {
        this.setupSelection.pendingBySide[side] = null;
      }
    });
  }

  _handleBoardPointerDown(pointer) {
    const col = Math.floor((pointer.x - BX) / CELL);
    const row = Math.floor((pointer.y - BY) / CELL);
    if (col < 0 || col >= COLS || row < 0 || row >= ROWS) return;

    if (gameState?.phase === 'game' && this._nukeArmingSide) {
      const enemySide = this._nukeArmingSide === 'p1' ? 'p2' : 'p1';
      if (sideOwnsCell(enemySide, col, row)) {
        this._sendAction({
          action: 'trigger_nuke',
          side: this._nukeArmingSide,
          position: { x: col, y: row },
        });
      }
      this._nukeArmingSide = null;
      return;
    }

    if (!gameState || gameState.phase !== 'hq_placement') return;
    if (!this._hqPlacementInstructionAck) return;
    const activeSide = gameState.setup?.active_setup_side;
    if (!activeSide) return;

    this._sendAction({
      action: 'set_hq_candidate',
      side: activeSide,
      position: { x: col, y: row },
    });

    if (sideOwnsCell(activeSide, col, row)) {
      this.setupSelection.pendingBySide[activeSide] = { col, row };
      this._hqCandidateCancelled = false;
    }
  }

  _drawPendingHqCandidate(phase, setup = {}) {
    if (phase !== 'hq_placement') return;
    const activeSide = setup.active_setup_side;
    const candidate = activeSide ? this.setupSelection.pendingBySide[activeSide] : null;
    if (candidate) {
      drawPendingHqCandidate(this.dynGfx, candidate, activeSide, this.time.now);
    }
  }

  _updateSetupUi(phase, setup = {}) {
    const isSetupPhase = phase != null && phase !== 'game';
    const texts = [
      this.setupTitleTxt, this.setupStatusTxt, this.setupScanTxt,
      this.setupSideTxt, this.setupActiveTxt, this.setupP1Txt,
      this.setupP2Txt, this.setupHintTxt,
    ];

    if (!isSetupPhase) {
      this.setupCardGfx.clear();
      this.setupCardGfx.setVisible(false);
      texts.forEach((txt) => txt.setVisible(false));
      return;
    }

    this.setupCardGfx.clear();
    this.setupCardGfx.setVisible(false);
    texts.forEach((txt) => txt.setVisible(false));
  }

  _hideSetupUi() {
    this._hidePlacementLabels();
    this._updateSetupUi('game');
  }

  _hidePlacementLabels() {
    if (this._zoneLabels) {
      this._zoneLabels.p1?.setVisible(false);
      this._zoneLabels.p2?.setVisible(false);
      this._zoneLabels.fence?.setVisible(false);
    }
  }

  _updateSetupControls(phase, setup = {}) {
    const activeSide = setup.active_setup_side;
    const hasActiveCandidate = activeSide && !!setup.hq?.[activeSide]?.has_candidate;
    const localCandidate = activeSide ? this.setupSelection.pendingBySide[activeSide] : null;

    const inBattle = phase === 'game' || phase === null;
    if (inBattle) {
      this._setSetupModalVisible(false);
      const activeTurnSide = gameState?.turn === 1 ? 'p1' : gameState?.turn === 2 ? 'p2' : null;
      const activeTier = activeTurnSide === 'p1' ? (gameState?.game?.tier_p1 ?? 0) : activeTurnSide === 'p2' ? (gameState?.game?.tier_p2 ?? 0) : 0;
      const nukeUsed = activeTurnSide === 'p1' ? !!gameState?.game?.nuke_used_p1 : activeTurnSide === 'p2' ? !!gameState?.game?.nuke_used_p2 : true;
      const isArming = !!activeTurnSide && this._nukeArmingSide === activeTurnSide;
      const canArmNuke = !!activeTurnSide && activeTier >= 4 && !nukeUsed;
      this._setActionButtonState(this.nukeBtn, {
        visible: !!activeTurnSide,
        enabled: canArmNuke || isArming,
        label: isArming ? 'Cancel Nuke' : (nukeUsed ? 'Nuke Spent' : 'Arm Nuke'),
      });
      return;
    }

    this._ensureSetupModal();

    if (phase !== 'hq_placement') {
      this._hqPlacementUiSide = null;
      this._hqPlacementInstructionAck = false;
    }

    const deferForTutorialIntro = !!(this.tutorialManager && this.tutorialManager.isIntroActive());
    if (deferForTutorialIntro) {
      this._setSetupModalVisible(false);
      this._setActionButtonState(this.nukeBtn, { visible: false, enabled: false });
      return;
    }

    this._setActionButtonState(this.nukeBtn, { visible: false, enabled: false });

    const m = this._setupModal;
    m.titleTxt.setText('Setup');

    if (phase === 'scan') {
      this._chooseSideSent = false;
      m.instructionHintTxt.setVisible(false);
      if (m.overlay?.input) m.overlay.input.enabled = false;
      m.bodyTxt.setText('Waiting for a valid board scan before HQ setup can continue.').setColor('#f2d8a0');
      m.candidateTxt.setVisible(false).setText('');
      this._setActionButtonState(this.confirmHqBtn, { visible: false, enabled: false });
      this._setActionButtonState(this.cancelHqBtn, { visible: false, enabled: false });
      this._setSetupModalVisible(true);
      this._layoutSetupModal();
      return;
    }

    if (phase === 'side_selection') {
      this._chooseSideSent = this._chooseSideSent || false;
      m.instructionHintTxt.setVisible(false);
      if (m.overlay?.input) m.overlay.input.enabled = false;
      m.bodyTxt.setText('The Mob places the hidden HQ first (default).').setColor('#b8ff78');
      m.candidateTxt.setVisible(false).setText('');

      if (!this._chooseSideSent) {
        this._chooseSideSent = true;
        this._sendAction({ action: 'choose_side', first_player_side: 'mob' });
      }

      this._setActionButtonState(this.confirmHqBtn, { visible: false, enabled: false });
      this._setActionButtonState(this.cancelHqBtn, { visible: false, enabled: false });
      this._setSetupModalVisible(true);
      this._layoutSetupModal();
      return;
    }

    if (phase === 'hq_placement') {
      if (activeSide && activeSide !== this._hqPlacementUiSide) {
        this._hqPlacementUiSide = activeSide;
        this._hqPlacementInstructionAck = false;
        this._hqCandidateCancelled = false;
      }

      const showInstructionOnly = !this._hqPlacementInstructionAck;

      if (showInstructionOnly) {
        if (IS_TUTORIAL && this.tutorialManager) {
          const placingMob = activeSide === 'p2';
          const instructionBody = placingMob
            ? 'Mob: click a board cell in your territory, then confirm the hidden HQ.\n(Look away, Old Mick!)'
            : 'Old Mick: click a board cell in your territory, then confirm the hidden HQ.\n(Look away, Mob!)';
          m.bodyTxt.setText(instructionBody).setColor(placingMob ? '#b8ff78' : '#ffd878');
        } else {
          const activeLabel = sideLabel(activeSide);
          m.bodyTxt
            .setText(`${activeLabel}: click a board cell in your territory, then confirm the hidden HQ.`)
            .setColor(activeSide === 'p2' ? '#b8ff78' : '#ffd878');
        }
        m.instructionHintTxt.setVisible(true);
        m.candidateTxt.setVisible(false).setText('');
        this._setActionButtonState(this.confirmHqBtn, { visible: false, enabled: false });
        this._setActionButtonState(this.cancelHqBtn, { visible: false, enabled: false });
        if (m.overlay?.input) m.overlay.input.enabled = true;
        this._chooseSideSent = true;
        this._setSetupModalVisible(true);
        this._layoutSetupModal();
        return;
      }

      if (m.overlay?.input) m.overlay.input.enabled = false;
      m.instructionHintTxt.setVisible(false);

      const showTileModal = !!localCandidate && !this._hqCandidateCancelled;

      if (!showTileModal) {
        this._setSetupModalVisible(false);
        m.candidateTxt.setVisible(false).setText('');
        this._setActionButtonState(this.confirmHqBtn, { visible: false, enabled: false });
        this._setActionButtonState(this.cancelHqBtn, { visible: false, enabled: false });
        this._chooseSideSent = true;
        return;
      }

      const activeLabel = sideLabel(activeSide);
      const cellText = `${activeLabel} selected cell: ${cellLabel(localCandidate.col, localCandidate.row)}`;
      m.bodyTxt.setText(cellText).setColor(hasActiveCandidate ? '#f0d8a0' : '#a89878');
      m.candidateTxt.setVisible(false).setText('');
      this._chooseSideSent = true;
      this._setActionButtonState(this.confirmHqBtn, { visible: true, enabled: !!hasActiveCandidate });
      this._setActionButtonState(this.cancelHqBtn, { visible: true, enabled: true });
      this._setSetupModalVisible(true);
      this._layoutSetupModal();
      return;
    }

    this._setSetupModalVisible(false);
  }

  _hideWarningOverlay() {
    this.warningCardGfx.clear();
    this.warningCardGfx.setVisible(false);
    this.warningTitleTxt.setVisible(false);
    this.warningBodyTxt.setVisible(false);
  }

  _renderWarningOverlay(title, message, alpha, tone = 'error') {
    const width = 470;
    const height = 108;
    const x = BX + COLS * CELL / 2 - width / 2;
    const y = BY + 82;
    const palette = tone === 'success'
      ? { fill: 0x0b1608, border: 0x5ad060, inner: 0xc8f8b8, stripe: 0x1f5e1a, title: '#dcffcf', body: '#c6f0bc' }
      : tone === 'warning'
        ? { fill: 0x1a1105, border: 0xe0a040, inner: 0xffe0a0, stripe: 0x6a3812, title: '#ffe7b8', body: '#ffd4a8' }
        : { fill: 0x1c0808, border: 0xc04020, inner: 0xffc8b0, stripe: 0x6a1812, title: '#ffe0a0', body: '#ffd0a0' };

    this.warningCardGfx.clear();
    this.warningCardGfx.setVisible(true);
    this.warningCardGfx.fillStyle(palette.fill, alpha * 0.95);
    this.warningCardGfx.fillRoundedRect(x, y, width, height, 10);
    this.warningCardGfx.lineStyle(2.5, palette.border, alpha);
    this.warningCardGfx.strokeRoundedRect(x, y, width, height, 10);
    this.warningCardGfx.fillStyle(palette.stripe, alpha * 0.65);
    this.warningCardGfx.fillRect(x + 6, y + 6, 4, height - 12);

    this.warningTitleTxt.setText(title).setColor(palette.title).setAlpha(alpha).setVisible(true);
    this.warningBodyTxt.setText(message).setColor(palette.body).setAlpha(alpha).setVisible(true);
  }

  _updateWarningPanel(now) {
    const ws = this.warningState;
    if (now < ws.recentUntil) {
      this.warningMiniTxt?.setText(`Recent alert: ${ws.recentTitle}`);
    } else {
      this.warningMiniTxt?.setText('Recent alert: none');
    }
  }

  _updateWarningUi(errors) {
    const now = this.time.now;
    const error = primaryError(errors);

    if (error) {
      const code = error.code;
      const ws = this.warningState;
      const isSameError = code === ws.activeCode;
      const allowRepeat = now >= ws.suppressUntil;

      if (!isSameError || allowRepeat) {
        ws.activeCode = code;
        ws.activeTitle = errorTitle(code);
        ws.activeMessage = errorMessage(error);
        ws.activeTone = errorTone(code);
        ws.showUntil = now + WARNING_SHOW_MS;
        ws.suppressUntil = now + WARNING_REPEAT_GAP_MS;
        ws.recentTitle = ws.activeTitle;
        ws.recentMessage = ws.activeMessage;
        ws.recentTone = ws.activeTone;
        ws.recentUntil = now + WARNING_RECENT_MS;
      }
    }

    if (now >= this.warningState.showUntil) {
      this._hideWarningOverlay();
      this._updateWarningPanel(now);
      return;
    }

    const elapsed = this.warningState.showUntil - now;
    let alpha = 1;
    if (elapsed < 260) alpha = Math.max(0, elapsed / 260);
    else if (elapsed > WARNING_SHOW_MS - 180) alpha = Math.min(1, (WARNING_SHOW_MS - elapsed) / 180);
    alpha = 0.35 + alpha * 0.65;

    this._renderWarningOverlay(this.warningState.activeTitle, this.warningState.activeMessage, alpha, this.warningState.activeTone);
    this._updateWarningPanel(now);
  }

  _updateWinBanner(G) {
    const winner = G.winner;
    if (!winner) {
      if (this._winBanner) this._winBanner.setVisible(false);
      if (this._winSub) this._winSub.setVisible(false);
      return;
    }

    if (!this._winBanner) {
      this._winBanner = this.add.text(BX + COLS * CELL / 2, BY + ROWS * CELL / 2 - 18, '', {
        fontSize: '28px', fontFamily: 'Georgia', fontStyle: 'bold',
        color: '#fff8d0', stroke: '#1a0c04', strokeThickness: 6,
      }).setOrigin(0.5, 0.5).setDepth(40);
      this._winSub = this.add.text(BX + COLS * CELL / 2, BY + ROWS * CELL / 2 + 18, '', {
        fontSize: '14px', fontFamily: 'Georgia', color: '#ffd890',
        stroke: '#1a0c04', strokeThickness: 3,
      }).setOrigin(0.5, 0.5).setDepth(40);
    }

    const msgs = {
      homestead_destroyed: ['🐦 THE MOB WINS', 'Old Mick\'s homestead burns — no shelter, no grain.'],
      nest_destroyed:      ['🌾 OLD MICK WINS', 'The hidden Nest is gone. The emu breeding heart is dead.'],
      attrition: winner === 'p1'
          ? ['🌾 OLD MICK WINS', 'Feeding grounds razed. The Mob starves.']
          : ['🐦 THE MOB WINS', 'Paddocks trampled. Old Mick can\'t fund another shot.'],
    };
    const [title, sub] = msgs[G.win_reason] || [`${winner.toUpperCase()} WINS`, ''];
    this._winBanner.setText(title).setVisible(true);
    this._winSub.setText(sub).setVisible(true);
  }

  _drawTerrain(terrain, softGoneKeys) {
    drawTerrain(this.dynGfx, terrain, softGoneKeys);
  }

  _drawDamageLayer(G, terrain) {
    drawDamageLayer(this.dynGfx, G, terrain);
  }

  _drawDefZone(defCol, defRow, tier, color) {
    drawDefZone(this.dynGfx, defCol, defRow, tier, color);
  }

  _drawRay(startCol, startRow, rayCells) {
    drawRay(this.dynGfx, startCol, startRow, rayCells);
  }

  _drawToken(col, row, angle, role, isP1, stale = false) {
    drawToken(this.dynGfx, col, row, angle, role, isP1, stale, this.time.now);
  }

  _drawPlacementGuide(phase, setup = {}) {
    const activeSide = setup.active_setup_side;
    const isScan = phase === 'scan';
    const isHqPlacement = phase === 'hq_placement';

    drawPlacementGuide(this.dynGfx, phase, activeSide, this.time.now);

    if (!this._zoneLabels) {
      const mk = (x, y, txt, col) => this.add.text(x, y, txt, {
        fontSize: '12px', fontFamily: 'Georgia', fontStyle: 'bold',
        color: col, backgroundColor: 'rgba(20,14,4,0.78)',
        padding: { x: 8, y: 4 },
        stroke: '#000', strokeThickness: 2,
      }).setDepth(9).setOrigin(0.5, 0.5);

      this._zoneLabels = {
        p1: mk(BX + CELL * 3, BY + CELL * 9.5, '🌾 OLD MICK TERRITORY', '#f8d870'),
        p2: mk(BX + CELL * 9, BY + CELL * 2.5, '🐦 THE MOB TERRITORY', '#b8ff60'),
        fence: mk(BX + CELL * 6, BY + CELL * 6, '🚫 FENCE LINE — NO HQ', '#ff9090'),
      };
    }

    this._zoneLabels.p1.setText(
      isHqPlacement && activeSide === 'p1'
        ? '🌾 OLD MICK TERRITORY — ACTIVE HQ SIDE'
        : '🌾 OLD MICK TERRITORY'
    );
    this._zoneLabels.p2.setText(
      isHqPlacement && activeSide === 'p2'
        ? '🐦 THE MOB TERRITORY — ACTIVE HQ SIDE'
        : '🐦 THE MOB TERRITORY'
    );
    this._zoneLabels.p1.setVisible(!isScan);
    this._zoneLabels.p2.setVisible(!isScan);
    this._zoneLabels.fence.setVisible(!isScan);
  }

  _dashLine(g, x1, y1, x2, y2, dashLen, gapLen) {
    dashLine(g, x1, y1, x2, y2, dashLen, gapLen);
  }

  _dashRect(g, x, y, w, h, dashLen, gapLen) {
    dashRect(g, x, y, w, h, dashLen, gapLen);
  }

  _applyState() {
    if (!gameState) return;
    const { phase, turn, corners_found, p1, p2, terrain, map_seed, game } = gameState;
    const setup = gameState.setup || {};
    const G = game || {};
    const inBattle = (phase === 'game' || phase == null);

    this._syncSetupSelection(phase, setup);

    let illuminatedSide = null;
    if (phase === 'game') {
      if (turn === 1) illuminatedSide = 'p1';
      else if (turn === 2) illuminatedSide = 'p2';
    } else {
      illuminatedSide = setup.active_setup_side || null;
      if (!illuminatedSide && setup.side_selection_complete) {
        illuminatedSide = setup.first_player_side === 'mob' ? 'p2' : 'p1';
      }
      if (!illuminatedSide) illuminatedSide = 'p2';
    }

    if (terrain && (map_seed !== this._drawnSeed || illuminatedSide !== this._drawnIlluminatedSide)) {
      this._drawStaticBoard(terrain, illuminatedSide);
      this._drawnSeed = map_seed;
      this._drawnIlluminatedSide = illuminatedSide;
    }

    const tierThresholds = Array.isArray(G.tier_thresholds) ? G.tier_thresholds : [6, 14, 22, 32];
    const nextThreshold = (tier) => tier >= 4 ? null : tierThresholds[tier] ?? null;
    if (G.tier_p1 != null) {
      this._p1Tier = G.tier_p1;
      const nextP1 = nextThreshold(G.tier_p1);
      const p1Progress = G.progress_p1 ?? 0;
      this.p1TierTxt?.setText(`P1 Tier: ${G.tier_p1}${G.tier_p1 === 4 ? ' 💥' : nextP1 != null ? ` (${p1Progress}/${nextP1})` : ''}`);
    }
    if (G.tier_p2 != null) {
      this._p2Tier = G.tier_p2;
      const nextP2 = nextThreshold(G.tier_p2);
      const p2Progress = G.progress_p2 ?? 0;
      this.p2TierTxt?.setText(`P2 Tier: ${G.tier_p2}${G.tier_p2 === 4 ? ' 💥' : nextP2 != null ? ` (${p2Progress}/${nextP2})` : ''}`);
    }

    const thr = G.attrition_threshold ?? 40;
    const s1 = G.score_p2_attrition ?? 0;
    const s2 = G.score_p1_attrition ?? 0;
    if (inBattle) {
      this.scoreText?.setText(`Paddock score: ${s1}/${thr}   Feeding ground score: ${s2}/${thr}`).setColor('#ffb060');
    } else {
      this.scoreText?.setText('Setup: backend-guided hidden HQ flow').setColor('#d8c890');
    }

    if (Array.isArray(gameState.events)) {
      for (const ev of gameState.events) {
        if (ev.type === 'cell_destroyed')    SFX.hit();
        else if (ev.type === 'cell_damaged') SFX.fire();
        else if (ev.type === 'hq_destroyed') SFX.nuke();
        else if (ev.type === 'soft_destroyed') SFX.block();
        else if (ev.type === 'nuke_triggered') SFX.nuke();
      }
    }

    if (!IS_TUTORIAL) this._updateWinBanner(G);
    else if (this._winBanner) { this._winBanner.setVisible(false); this._winSub?.setVisible(false); }

    if (!inBattle) {
      this.turnText.setText(`Phase: ${phaseLabel(phase)}`).setColor('#f0d070');
    } else if (turn === 1) {
      this.turnText.setText(`Turn: 🌾 Old Mick  |  Tier ${G.tier_p1 ?? 0}`).setColor('#f8d060');
    } else if (turn === 2) {
      this.turnText.setText(`Turn: 🐦 The Mob  |  Tier ${G.tier_p2 ?? 0}`).setColor('#90ee40');
    } else {
      this.turnText.setText('Turn: — waiting —').setColor('#807060');
    }

    this.cornerText.setText(`Corners: ${corners_found || 0}/4`)
      .setColor(corners_found === 4 ? '#44ff88' : '#ff8844');

    const hardMap = {}, softMap = {};
    const { p1: p1ResourceMap, p2: p2ResourceMap } = buildResourceMaps(terrain);
    const softGoneKeys = new Set((G.soft_gone || []).map(([c, r]) => `${c},${r}`));
    if (terrain) {
      [...(terrain.p1_hard || []), ...(terrain.p2_hard || [])].forEach(t => {
        if (t.col != null) hardMap[`${t.col},${t.row}`] = t;
      });
      [...(terrain.p1_soft || []), ...(terrain.p2_soft || [])].forEach(t => {
        if (t.col != null && !softGoneKeys.has(`${t.col},${t.row}`)) {
          softMap[`${t.col},${t.row}`] = t;
        }
      });
    }

    const destroyedMap = {};
    (G.destroyed || []).forEach(([c, r]) => {
      destroyedMap[`${c},${r}`] = true;
    });

    this.dynGfx.clear();

    this._drawDamageLayer(G, terrain);
    this._drawTerrain(terrain, softGoneKeys);

    if (inBattle && p1?.def?.col != null)
      this._drawDefZone(p1.def.col, p1.def.row, this._p1Tier, C.p1_zone);
    if (inBattle && p2?.def?.col != null)
      this._drawDefZone(p2.def.col, p2.def.row, this._p2Tier, C.p2_zone);

    if (inBattle) {
      ['atk_a', 'atk_b'].forEach(role => {
        if (p1?.[role]?.col != null && p1[role].direction) {
          const ray = computeRay(p1[role].col, p1[role].row, p1[role].direction, hardMap, softMap, 'p1', destroyedMap, p2ResourceMap);
          this._drawRay(p1[role].col, p1[role].row, ray);
        }
        if (p2?.[role]?.col != null && p2[role].direction) {
          const ray = computeRay(p2[role].col, p2[role].row, p2[role].direction, hardMap, softMap, 'p2', destroyedMap, p1ResourceMap);
          this._drawRay(p2[role].col, p2[role].row, ray);
        }
      });
    }

    const drawTok = (tok, role, p1side) => {
      if (!tok || tok.col == null) return;
      this._drawToken(tok.col, tok.row, tok.angle, role, p1side, !!tok.stale);
    };
    if (p1) { drawTok(p1.atk_a, 'atk', true);  drawTok(p1.atk_b, 'atk', true);  drawTok(p1.def, 'def', true);  }
    if (p2) { drawTok(p2.atk_a, 'atk', false); drawTok(p2.atk_b, 'atk', false); drawTok(p2.def, 'def', false); }

    this._placeLabel('p1_atk_a', p1?.atk_a?.col, p1?.atk_a?.row);
    this._placeLabel('p1_atk_b', p1?.atk_b?.col, p1?.atk_b?.row);
    this._placeLabel('p1_def',   p1?.def?.col,   p1?.def?.row);
    this._placeLabel('p2_atk_a', p2?.atk_a?.col, p2?.atk_a?.row);
    this._placeLabel('p2_atk_b', p2?.atk_b?.col, p2?.atk_b?.row);
    this._placeLabel('p2_def',   p2?.def?.col,   p2?.def?.row);

    if (inBattle) {
      this._placeArrow('p1_atk_a', p1?.atk_a);
      this._placeArrow('p1_atk_b', p1?.atk_b);
      this._placeArrow('p2_atk_a', p2?.atk_a);
      this._placeArrow('p2_atk_b', p2?.atk_b);
    } else {
      Object.values(this.arrows).forEach((arrow) => arrow.setVisible(false));
    }

    if (inBattle) {
      this._hideSetupUi();
      const activeSide = turn === 1 ? 'p1' : turn === 2 ? 'p2' : null;
      if (this._nukeArmingSide && activeSide !== this._nukeArmingSide) this._nukeArmingSide = null;
    } else {
      this._drawPlacementGuide(phase, setup);
      this._drawPendingHqCandidate(phase, setup);
      this._updateSetupUi(phase, setup);
    }

    this._updateSetupControls(phase, setup);
    this._updateWarningUi(gameState.errors || []);

    if (IS_TUTORIAL && this.tutorialManager) {
      this.tutorialManager.tick(gameState);
      this.tutorialManager.drawHighlights(this.dynGfx, this.time.now);
    }
  }
}

/**
 * Initialize the Phaser game.
 */
export function initGame() {
  new Phaser.Game({
    type: Phaser.AUTO,
    width: W,
    height: H,
    parent: 'game-container',
    backgroundColor: '#1a1008',
    scene: GameScene,
  });
}
