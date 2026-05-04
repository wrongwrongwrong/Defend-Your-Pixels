/**
 * Setup UI Manager for Old Mick Against the Mob.
 * Handles HQ placement phase UI and user interactions.
 * @module setup-ui
 */

import { BX, BY, CELL, COLS, ROWS, W, H, SIDE_LABEL } from './constants.js';
import { sideOwnsCell, cellLabel, sideLabel } from './helpers.js';

/**
 * SetupUIManager handles the HQ placement modal and board interactions.
 */
export class SetupUIManager {
  constructor(scene) {
    this.scene = scene;
    this.modal = null;
    this.setupSelection = {
      pendingBySide: { p1: null, p2: null },
    };
    this.hqPlacementUiSide = null;
    this.hqPlacementInstructionAck = false;
    this.hqCandidateCancelled = false;
    this.chooseSideSent = false;
  }

  /**
   * Create the setup modal UI elements.
   * @param {Function} sendAction - Function to send actions to the server
   * @param {Function} getGameState - Function to get current game state
   */
  ensureModal(sendAction, getGameState) {
    if (this.modal) return;

    const scene = this.scene;

    const overlay = scene.add.graphics().setDepth(54);
    const gfx = scene.add.graphics().setDepth(55);

    const titleTxt = scene.add.text(0, 0, '', {
      fontSize: '18px',
      fontFamily: 'Georgia',
      color: '#ffe070',
      fontStyle: 'bold',
    }).setDepth(56);

    const bodyTxt = scene.add.text(0, 0, '', {
      fontSize: '15px',
      fontFamily: 'Georgia',
      color: '#f2d8a0',
      lineSpacing: 6,
    }).setDepth(56);

    const candidateTxt = scene.add.text(0, 0, '', {
      fontSize: '13px',
      fontFamily: 'monospace',
      color: '#d8c890',
      lineSpacing: 5,
    }).setDepth(56);

    const instructionHintTxt = scene.add.text(0, 0, '[ Click anywhere to continue ]', {
      fontSize: '14px',
      fontFamily: 'Georgia',
      fontStyle: 'italic',
      color: '#ffe070',
    }).setDepth(56).setVisible(false);

    const mkModalBtn = (label, bgColor, color, onClick) => {
      const btn = scene.add.text(0, 0, label, {
        fontSize: '13px',
        fontFamily: 'Georgia',
        color,
        backgroundColor: bgColor,
        padding: { x: 10, y: 8 },
        fontStyle: 'bold',
      })
        .setInteractive({ useHandCursor: true })
        .setDepth(56)
        .setOrigin(0.5, 0.5);

      btn._baseColor = color;
      btn._baseBgColor = bgColor;
      btn._enabled = true;

      btn.on('pointerdown', () => {
        if (btn._enabled) onClick();
      });
      btn.on('pointerover', () => {
        if (btn._enabled) btn.setColor('#fff8dc');
      });
      btn.on('pointerout', () => {
        btn.setColor(btn._enabled ? btn._baseColor : '#8a7a68');
      });

      return btn;
    };

    const confirmBtn = mkModalBtn('Confirm HQ', '#6a3812', '#ffe0a0', () => {
      const activeSide = getGameState()?.setup?.active_setup_side;
      if (activeSide) sendAction({ action: 'confirm_hq', side: activeSide });
    });

    const cancelBtn = mkModalBtn('Cancel', '#402318', '#f0c8b0', () => {
      const activeSide = getGameState()?.setup?.active_setup_side;
      if (activeSide) {
        this.setupSelection.pendingBySide[activeSide] = null;
      }
      this.hqCandidateCancelled = true;
      this.setModalVisible(false);
    });

    overlay.setInteractive(new Phaser.Geom.Rectangle(0, 0, W, H), Phaser.Geom.Rectangle.Contains);
    overlay.input.enabled = false;
    overlay.on('pointerdown', (pointer) => {
      if (!this.modal?.visible) return;
      if (getGameState()?.phase !== 'hq_placement') return;
      if (this.hqPlacementInstructionAck) return;
      try {
        pointer.event?.stopPropagation?.();
      } catch (_) { /* ignore */ }
      this.hqPlacementInstructionAck = true;
      if (this.modal.overlay?.input) this.modal.overlay.input.enabled = false;
      this.setModalVisible(false);
    });

    this.modal = {
      overlay,
      gfx,
      titleTxt,
      bodyTxt,
      candidateTxt,
      instructionHintTxt,
      confirmBtn,
      cancelBtn,
      visible: false,
    };

    this.layoutModal();
    this.setModalVisible(false);

    return { confirmBtn, cancelBtn };
  }

  /**
   * Set modal visibility.
   */
  setModalVisible(visible) {
    if (!this.modal) return;
    this.modal.visible = visible;
    const { overlay, gfx, titleTxt, bodyTxt, candidateTxt, instructionHintTxt, confirmBtn, cancelBtn } = this.modal;
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

  /**
   * Layout the modal contents.
   */
  layoutModal() {
    if (!this.modal) return;

    const modalW = Math.min(560, W * 0.92);
    const padX = 20;
    const padY = 18;
    const centerX = W / 2;
    const centerY = H / 2 - 10;

    const { overlay, gfx, titleTxt, bodyTxt, candidateTxt, instructionHintTxt, confirmBtn, cancelBtn } = this.modal;
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
      y += candH;
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

  /**
   * Handle board click during HQ placement.
   * @param {number} col - Column clicked
   * @param {number} row - Row clicked
   * @param {object} gameState - Current game state
   * @param {Function} sendAction - Function to send actions
   */
  handleBoardClick(col, row, gameState, sendAction) {
    if (!gameState || gameState.phase !== 'hq_placement') return false;
    if (!this.hqPlacementInstructionAck) return false;
    const activeSide = gameState.setup?.active_setup_side;
    if (!activeSide) return false;

    sendAction({
      action: 'set_hq_candidate',
      side: activeSide,
      position: { x: col, y: row },
    });

    if (sideOwnsCell(activeSide, col, row)) {
      this.setupSelection.pendingBySide[activeSide] = { col, row };
      this.hqCandidateCancelled = false;
    }

    return true;
  }

  /**
   * Sync local selection state with server state.
   * @param {object} hq - HQ state from server
   * @param {string} phase - Current phase
   */
  syncSelection(hq, phase) {
    if (!hq) return;
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

  /**
   * Get the local candidate for a side.
   */
  getLocalCandidate(side) {
    return side ? this.setupSelection.pendingBySide[side] : null;
  }

  /**
   * Reset state for a new setup side.
   */
  resetForNewSide(activeSide) {
    if (activeSide && activeSide !== this.hqPlacementUiSide) {
      this.hqPlacementUiSide = activeSide;
      this.hqPlacementInstructionAck = false;
      this.hqCandidateCancelled = false;
    }
  }
}

/**
 * Draw pending HQ candidate highlight.
 * @param {Phaser.GameObjects.Graphics} gfx - Graphics object
 * @param {object} candidate - { col, row } or null
 * @param {string} activeSide - 'p1' or 'p2'
 * @param {number} time - Current time for animation
 */
export function drawPendingHqCandidate(gfx, candidate, activeSide, time) {
  if (!candidate) return;

  const { col, row } = candidate;
  const x = BX + col * CELL + 2;
  const y = BY + row * CELL + 2;
  const ring = activeSide === 'p2' ? 0xb8ff60 : 0xffdc70;
  const cx = x + (CELL - 4) / 2;
  const cy = y + (CELL - 4) / 2;
  const pulse = 0.55 + 0.20 * Math.sin(time / 170);

  gfx.fillStyle(0x120904, 0.25);
  gfx.fillRoundedRect(x, y, CELL - 4, CELL - 4, 5);
  gfx.lineStyle(3, ring, pulse);
  gfx.strokeCircle(cx, cy, 14);

  gfx.lineStyle(2, 0xffffff, pulse * 0.4);
  const crossLen = 8;
  gfx.beginPath();
  gfx.moveTo(cx - crossLen, cy);
  gfx.lineTo(cx + crossLen, cy);
  gfx.moveTo(cx, cy - crossLen);
  gfx.lineTo(cx, cy + crossLen);
  gfx.strokePath();
}
