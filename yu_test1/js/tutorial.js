/**
 * Tutorial system for Old Mick Against the Mob.
 * Manages step-by-step guidance for new players.
 * @module tutorial
 */

import { BX, BY, CELL, W, H, TUTORIAL_TARGETS } from './constants.js';
import { defZoneCells } from './helpers.js';

// Tutorial steps enum
export const TUTORIAL_STEPS = {
  PLACE_P1_ATK: 0,    // Place P1 ATK A at D4
  AIM_P1_ATK: 1,      // Aim P1 ATK A to the right (E)
  END_P1_TURN: 2,     // End P1 turn
  END_P2_TURN: 3,     // Quickly end P2 turn
  PLACE_P1_DEF: 4,    // Place P1 defender at B2
  END_P1_DEF_TURN: 5, // End P1 turn after placing defender
  WAIT_FOR_HIT: 6,    // Wait for P2 to hit protected zone
};

/**
 * TutorialManager handles tutorial state and UI for the game.
 */
export class TutorialManager {
  constructor(scene) {
    this.scene = scene;
    this.state = null;
    this.popup = null;
  }

  /**
   * Initialize the tutorial system.
   */
  init() {
    this.state = {
      step: TUTORIAL_STEPS.PLACE_P1_ATK,
      lastTurn: null,
      highlightCell: null,      // {col, row}
      highlightZone: null,      // array of {col, row}
      expectedHitCell: null,    // {col, row}
      completed: false,
      introActive: true,        // show intro modal before enabling steps
    };

    this.showIntroPopup();
  }

  /**
   * Check if tutorial is active.
   */
  isActive() {
    return this.state && !this.state.completed;
  }

  /**
   * Check if intro modal is showing.
   */
  isIntroActive() {
    return this.state?.introActive ?? false;
  }

  /**
   * Show the tutorial intro popup.
   */
  showIntroPopup() {
    if (this.popup) this.dismissIntroPopup();

    const scene = this.scene;
    const modalW = Math.min(560, W * 0.92);
    const modalH = 230;
    const padX = 20;
    const padY = 18;

    const centerX = W / 2;
    const centerY = H / 2 - 10;

    const modalX = centerX - modalW / 2;
    const modalY = centerY - modalH / 2;

    const gfx = scene.add.graphics().setDepth(60);
    gfx.fillStyle(0x000000, 0.35);
    gfx.fillRect(0, 0, W, H);

    gfx.fillStyle(0x2a2010, 1);
    gfx.lineStyle(2, 0x6a4a20, 1);
    gfx.fillRoundedRect(modalX, modalY, modalW, modalH, 14);
    gfx.strokeRoundedRect(modalX, modalY, modalW, modalH, 14);

    const textStyle = {
      fontSize: '15px',
      fontFamily: 'Georgia',
      color: '#f2d8a0',
      lineSpacing: 6,
    };

    const p1 = "In 1932, a misterious Hive Mind from outer space landed in the outback. It brainwashed the flocks of emus in the wilderness, mutated them and want to blaze the land fenced by the Farmers.";
    const p2 = "Farmers, hiding their families in a digout, needs to find the Hive Mind, destroy it before it is too late.";

    const wrapW = modalW - padX * 2;
    const t1 = scene.add.text(modalX + padX, modalY + padY, p1, {
      ...textStyle,
      wordWrap: { width: wrapW },
    }).setDepth(61);

    const t2Y = modalY + padY + (t1.height || 100) + 10;
    const t2 = scene.add.text(modalX + padX, t2Y, p2, {
      ...textStyle,
      wordWrap: { width: wrapW },
    }).setDepth(61);

    const hint = scene.add.text(centerX, modalY + modalH + 22, 'press any key to continue', {
      fontSize: '13px',
      fontFamily: 'Georgia',
      color: '#9a7a58',
    }).setOrigin(0.5, 0).setDepth(61);

    this.popup = { gfx, t1, t2, hint };

    this._keydownHandler = () => this.dismissIntroPopup();
    window.addEventListener('keydown', this._keydownHandler, { once: true });
  }

  /**
   * Dismiss the tutorial intro popup.
   */
  dismissIntroPopup() {
    if (!this.popup) return;
    const { gfx, t1, t2, hint } = this.popup;
    gfx?.destroy?.();
    t1?.destroy?.();
    t2?.destroy?.();
    hint?.destroy?.();
    this.popup = null;

    if (this.state) this.state.introActive = false;

    if (this._keydownHandler) {
      window.removeEventListener('keydown', this._keydownHandler);
      this._keydownHandler = null;
    }
  }

  /**
   * Update tutorial state based on game state.
   * Called each frame.
   * @param {object} gameState - Current game state
   */
  tick(gameState) {
    if (!this.state || this.state.completed) return;
    if (this.state.introActive) return;
    if (!gameState) return;

    const turn = gameState.turn;
    const p1 = gameState.p1 || {};
    const G = gameState.game || {};
    const events = Array.isArray(gameState.events) ? gameState.events : [];

    // Track turn changes for step gating.
    if (this.state.lastTurn == null && turn != null) this.state.lastTurn = turn;
    const turnChanged = (turn != null && this.state.lastTurn != null && turn !== this.state.lastTurn);
    if (turnChanged) this.state.lastTurn = turn;

    const atCell = (tok, col, row) => tok?.col === col && tok?.row === row;
    const isVisible = (tok) => tok?.col != null && tok?.row != null && !tok?.stale;

    const setCellHighlight = (col, row) => {
      this.state.highlightZone = null;
      this.state.highlightCell = (col == null ? null : { col, row });
    };
    const setZoneHighlight = (cells) => {
      this.state.highlightCell = null;
      this.state.highlightZone = cells || null;
    };

    // STEP 0: Place P1 ATK A at D4.
    if (this.state.step === TUTORIAL_STEPS.PLACE_P1_ATK) {
      const t = TUTORIAL_TARGETS.p1AtkStart;
      setCellHighlight(t.col, t.row);
      if (isVisible(p1.atk_a) && atCell(p1.atk_a, t.col, t.row)) {
        this.state.step = TUTORIAL_STEPS.AIM_P1_ATK;
      }
      return;
    }

    // STEP 1: Aim P1 ATK A to the right (E).
    if (this.state.step === TUTORIAL_STEPS.AIM_P1_ATK) {
      const t = TUTORIAL_TARGETS.p1AtkStart;
      setCellHighlight(t.col, t.row);
      if (isVisible(p1.atk_a) && atCell(p1.atk_a, t.col, t.row) && p1.atk_a.direction === 'E') {
        this.state.step = TUTORIAL_STEPS.END_P1_TURN;
      }
      return;
    }

    // STEP 2: End P1 turn (physical confirm marker triggers turn change).
    if (this.state.step === TUTORIAL_STEPS.END_P1_TURN) {
      setCellHighlight(null, null);
      if (turnChanged && turn === 2) this.state.step = TUTORIAL_STEPS.END_P2_TURN;
      return;
    }

    // STEP 3: Quickly end P2 turn so we can place defender as P1.
    if (this.state.step === TUTORIAL_STEPS.END_P2_TURN) {
      setCellHighlight(null, null);
      if (turnChanged && turn === 1) this.state.step = TUTORIAL_STEPS.PLACE_P1_DEF;
      return;
    }

    // STEP 4: Place P1 defender at B2 and highlight its zone.
    if (this.state.step === TUTORIAL_STEPS.PLACE_P1_DEF) {
      const d = TUTORIAL_TARGETS.p1DefSpot;
      setCellHighlight(d.col, d.row);
      if (isVisible(p1.def) && atCell(p1.def, d.col, d.row)) {
        const tier = (G.tier_p1 ?? 0);
        setZoneHighlight(defZoneCells(d.col, d.row, tier));
        this.state.step = TUTORIAL_STEPS.END_P1_DEF_TURN;
      }
      return;
    }

    // STEP 5: End P1 turn so the enemy can attack into the protected zone.
    if (this.state.step === TUTORIAL_STEPS.END_P1_DEF_TURN) {
      const d = TUTORIAL_TARGETS.p1DefSpot;
      const tier = (G.tier_p1 ?? 0);
      setZoneHighlight(defZoneCells(d.col, d.row, tier));
      if (turnChanged && turn === 2) this.state.step = TUTORIAL_STEPS.WAIT_FOR_HIT;
      return;
    }

    // STEP 6: Wait for a P2-resolved hit that only DAMAGES (not destroys) a protected cell.
    if (this.state.step === TUTORIAL_STEPS.WAIT_FOR_HIT) {
      const d = TUTORIAL_TARGETS.p1DefSpot;
      const tier = (G.tier_p1 ?? 0);
      const zone = defZoneCells(d.col, d.row, tier);
      setZoneHighlight(zone);

      // Detect "protected first hit": cell_damaged where cell is inside the DEF zone.
      const zoneKey = new Set(zone.map(({ col, row }) => `${col},${row}`));
      const gotDamagedProtected = events.some((ev) => {
        if (ev?.type !== 'cell_damaged') return false;
        const cell = ev.cell;
        const c = Array.isArray(cell) ? cell[0] : cell?.col;
        const r = Array.isArray(cell) ? cell[1] : cell?.row;
        return zoneKey.has(`${c},${r}`);
      });

      if (gotDamagedProtected) {
        this.state.completed = true;
        this.state.highlightCell = null;
        this.state.highlightZone = null;
      }
      return;
    }
  }

  /**
   * Draw tutorial highlights on the board.
   * @param {Phaser.GameObjects.Graphics} gfx - Graphics object to draw on
   * @param {number} time - Current time for animation
   */
  drawHighlights(gfx, time) {
    if (!this.state) return;
    const pulse = 0.55 + 0.35 * Math.sin(time / 180);

    if (this.state.highlightCell) {
      const { col, row } = this.state.highlightCell;
      const x = BX + col * CELL, y = BY + row * CELL;
      const pad = 2;
      gfx.lineStyle(4, 0xffe070, pulse);
      gfx.strokeRect(x + pad, y + pad, CELL - pad * 2, CELL - pad * 2);
    }

    if (Array.isArray(this.state.highlightZone)) {
      gfx.lineStyle(2.5, 0xffe070, 0.22 + 0.25 * pulse);
      for (const cell of this.state.highlightZone) {
        const x = BX + cell.col * CELL, y = BY + cell.row * CELL;
        const pad = 3;
        gfx.strokeRect(x + pad, y + pad, CELL - pad * 2, CELL - pad * 2);
      }
    }
  }
}

/**
 * Check if tutorial mode is enabled via URL parameter.
 */
export function isTutorialMode() {
  return new URLSearchParams(window.location.search).get('tutorial') === '1';
}
