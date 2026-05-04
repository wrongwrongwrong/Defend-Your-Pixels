/**
 * Drawing functions for Old Mick Against the Mob.
 * Handles all board rendering, tokens, rays, and terrain.
 * @module drawing
 */

import { BX, BY, CELL, COLS, ROWS, C } from './constants.js';
import { cc, buildResourceMaps } from './helpers.js';

// ═══════════════════════════════════════════════════════════════════
//  UTILITY DRAWING FUNCTIONS
// ═══════════════════════════════════════════════════════════════════

/**
 * Draw a dashed line.
 */
export function dashLine(g, x1, y1, x2, y2, dashLen, gapLen) {
  const dx = x2 - x1, dy = y2 - y1;
  const len = Math.hypot(dx, dy);
  if (len === 0) return;
  const ux = dx / len, uy = dy / len;
  let d = 0, draw = true;
  while (d < len) {
    const seg = Math.min(draw ? dashLen : gapLen, len - d);
    if (draw)
      g.lineBetween(x1 + ux * d, y1 + uy * d,
                    x1 + ux * (d + seg), y1 + uy * (d + seg));
    d += seg; draw = !draw;
  }
}

/**
 * Draw a dashed rectangle outline.
 */
export function dashRect(g, x, y, w, h, dashLen, gapLen) {
  dashLine(g, x,     y,     x + w, y,     dashLen, gapLen);
  dashLine(g, x + w, y,     x + w, y + h, dashLen, gapLen);
  dashLine(g, x + w, y + h, x,     y + h, dashLen, gapLen);
  dashLine(g, x,     y + h, x,     y,     dashLen, gapLen);
}

/**
 * Draw a filled 5-point star.
 */
export function drawStar(g, cx, cy, outerR, innerR, points) {
  const pts = [];
  for (let i = 0; i < points * 2; i++) {
    const r = i % 2 === 0 ? outerR : innerR;
    const a = (Math.PI / 2) + (i * Math.PI / points);
    pts.push({ x: cx + r * Math.cos(a), y: cy - r * Math.sin(a) });
  }
  g.fillPoints(pts, true);
}

// ═══════════════════════════════════════════════════════════════════
//  TERRAIN DRAWING
// ═══════════════════════════════════════════════════════════════════

/**
 * Draw terrain pieces (hard and soft).
 * @param {Phaser.GameObjects.Graphics} g - Graphics object
 * @param {object} terrain - Terrain data from game state
 * @param {Set} softGoneKeys - Set of "c,r" strings for destroyed soft terrain
 */
export function drawTerrain(g, terrain, softGoneKeys = new Set()) {
  if (!terrain) return;

  const drawPiece = (col, row, isHard, isP1side) => {
    if (col == null) return;
    if (!isHard && softGoneKeys.has(`${col},${row}`)) return;
    const x = BX + col * CELL, y = BY + row * CELL;
    const pad = 3, s = CELL - 1 - pad * 2;

    if (isHard) {
      g.fillStyle(isP1side ? 0x907050 : 0x606050, 0.90);
      g.fillRect(x + pad, y + pad, s, s);
      g.lineStyle(2, isP1side ? 0xd0b880 : 0xa09070, 1);
      g.strokeRect(x + pad, y + pad, s, s);

      const m = 7;
      g.lineStyle(5, 0x000000, 0.50);
      g.lineBetween(x + m, y + m, x + CELL - m, y + CELL - m);
      g.lineBetween(x + CELL - m, y + m, x + m, y + CELL - m);
      g.lineStyle(3.5, 0xffffff, 0.85);
      g.lineBetween(x + m, y + m, x + CELL - m, y + CELL - m);
      g.lineBetween(x + CELL - m, y + m, x + m, y + CELL - m);

    } else {
      g.fillStyle(isP1side ? 0xc8be38 : 0x80c448, 0.70);
      g.fillRect(x + pad + 2, y + pad + 2, s - 4, s - 4);

      g.lineStyle(1.5, isP1side ? 0xe8e060 : 0xa0e870, 0.9);
      dashRect(g, x + pad + 2, y + pad + 2, s - 4, s - 4, 5, 3);

      g.lineStyle(1.5, 0xffffff, 0.40);
      const hx = x + CELL / 2, hy = y + CELL / 2, hr = 10;
      g.lineBetween(hx - hr - 4, hy + hr, hx + hr - 4, hy - hr);
      g.lineBetween(hx - hr,     hy + hr, hx + hr,     hy - hr);
      g.lineBetween(hx - hr + 4, hy + hr, hx + hr + 4, hy - hr);
    }
  };

  (terrain.p1_hard || []).forEach(t => drawPiece(t.col, t.row, true,  true));
  (terrain.p1_soft || []).forEach(t => drawPiece(t.col, t.row, false, true));
  (terrain.p2_hard || []).forEach(t => drawPiece(t.col, t.row, true,  false));
  (terrain.p2_soft || []).forEach(t => drawPiece(t.col, t.row, false, false));
}

// ═══════════════════════════════════════════════════════════════════
//  DAMAGE AND DESTRUCTION DRAWING
// ═══════════════════════════════════════════════════════════════════

/**
 * Draw a single scorched-earth cell (destroyed forever).
 */
export function drawScorched(g, c, r) {
  const x = BX + c * CELL + 1, y = BY + r * CELL + 1;
  const w = CELL - 3, h = CELL - 3;

  g.fillStyle(0x0a0603, 0.92);
  g.fillRoundedRect(x, y, w, h, 3);

  const rnd = (k) => {
    const v = Math.sin((c * 91 + r * 17 + k * 131) * 12.97) * 43758.55;
    return v - Math.floor(v);
  };
  for (let i = 0; i < 5; i++) {
    const ex = x + 4 + rnd(i) * (w - 8);
    const ey = y + 4 + rnd(i + 10) * (h - 8);
    g.fillStyle(0xff6a20, 0.55);
    g.fillCircle(ex, ey, 1.4);
  }

  g.lineStyle(1, 0x502010, 0.8);
  g.lineBetween(x + 4, y + 8,  x + w - 8, y + h - 6);
  g.lineBetween(x + w - 6, y + 10, x + 10, y + h - 10);

  g.lineStyle(2, 0x802010, 0.55);
  g.lineBetween(x + w / 2 - 5, y + h / 2 - 5, x + w / 2 + 5, y + h / 2 + 5);
  g.lineBetween(x + w / 2 + 5, y + h / 2 - 5, x + w / 2 - 5, y + h / 2 + 5);
}

/**
 * Draw damage layer (cracked cells, scorched earth, revealed HQ).
 */
export function drawDamageLayer(g, G, terrain) {
  const { p1: p1ResourceMap, p2: p2ResourceMap } = buildResourceMaps(terrain);

  const dmg = G.damage || {};
  for (const key in dmg) {
    const [c, r] = key.split(',').map(Number);
    if ((G.destroyed || []).some(d => d[0] === c && d[1] === r)) continue;
    const x = BX + c * CELL + 1, y = BY + r * CELL + 1;
    const resource = p1ResourceMap[key] || p2ResourceMap[key];

    g.fillStyle(0x000000, 0.28);
    g.fillRoundedRect(x, y, CELL - 3, CELL - 3, 3);

    g.lineStyle(1.5, 0x201008, 0.8);
    g.lineBetween(x + 6, y + 10, x + CELL - 12, y + CELL - 8);
    g.lineBetween(x + CELL - 14, y + 12, x + CELL - 6, y + CELL - 14);

    if (resource?.visible && resource?.value === 5) {
      const maxHp = resource.max_hp ?? 3;
      const hits = dmg[key] ?? 0;
      const remain = Math.max(0, maxHp - hits);
      for (let i = 0; i < maxHp; i++) {
        const cx = x + 14 + i * 12;
        const cy = y + CELL - 12;
        g.fillStyle(i < remain ? 0xffe070 : 0x4a3010, 0.95);
        g.fillCircle(cx, cy, 4);
        g.lineStyle(1, 0x120904, 0.8);
        g.strokeCircle(cx, cy, 4);
      }
    }
  }

  (G.destroyed || []).forEach(([c, r]) => drawScorched(g, c, r));

  const hqR = G.hq_revealed || {};
  Object.entries(hqR).forEach(([side, pos]) => {
    if (!pos) return;
    const [c, r] = pos;
    const cx = BX + c * CELL + CELL / 2, cy = BY + r * CELL + CELL / 2;
    g.lineStyle(3, 0xffd060, 0.95);
    g.strokeCircle(cx, cy, CELL * 0.38);
    g.lineStyle(1.5, 0xffffff, 0.8);
    g.strokeCircle(cx, cy, CELL * 0.28);
  });
}

// ═══════════════════════════════════════════════════════════════════
//  DEFENSE ZONE DRAWING
// ═══════════════════════════════════════════════════════════════════

/**
 * Draw defense zone (semi-transparent highlighted rectangle).
 */
export function drawDefZone(g, defCol, defRow, tier, color) {
  const rad = tier >= 2 ? 2 : 1;
  const sx  = BX + (defCol - rad) * CELL;
  const sy  = BY + (defRow - rad) * CELL;
  const sz  = (rad * 2 + 1) * CELL;

  g.fillStyle(color, 0.10);
  g.fillRect(sx, sy, sz, sz);
  g.lineStyle(2, color, 0.65);
  g.strokeRect(sx, sy, sz, sz);

  g.lineStyle(3, color, 0.9);
  [[sx, sy], [sx + sz, sy], [sx, sy + sz], [sx + sz, sy + sz]].forEach(([cx, cy]) => {
    const dx = cx === sx ? 6 : -6, dy = cy === sy ? 6 : -6;
    g.lineBetween(cx, cy, cx + dx, cy);
    g.lineBetween(cx, cy, cx, cy + dy);
  });
}

// ═══════════════════════════════════════════════════════════════════
//  RAY DRAWING
// ═══════════════════════════════════════════════════════════════════

/**
 * Draw ray visualization.
 * @param {Phaser.GameObjects.Graphics} g - Graphics object
 * @param {number} startCol - Starting column
 * @param {number} startRow - Starting row
 * @param {Array} rayCells - Array of ray cells with type info
 */
export function drawRay(g, startCol, startRow, rayCells) {
  if (!rayCells || rayCells.length === 0) return;

  for (const cell of rayCells) {
    const x = BX + cell.col * CELL, y = BY + cell.row * CELL;
    const w = CELL - 1, h = CELL - 1;

    if      (cell.type === 'path')    { g.fillStyle(C.ray_path,    0.28); g.fillRect(x, y, w, h); }
    else if (cell.type === 'hit')     { g.fillStyle(C.ray_hit,     0.55); g.fillRect(x, y, w, h); }
    else if (cell.type === 'blocked') { g.fillStyle(0x303030,      0.70); g.fillRect(x, y, w, h); }
    else if (cell.type === 'soft')    { g.fillStyle(C.ray_soft,    0.45); g.fillRect(x, y, w, h); }
  }

  let px = BX + startCol * CELL + CELL / 2;
  let py = BY + startRow * CELL + CELL / 2;

  for (const cell of rayCells) {
    const cx = BX + cell.col * CELL + CELL / 2;
    const cy = BY + cell.row * CELL + CELL / 2;

    if (cell.type === 'path') {
      g.lineStyle(2, C.ray_path, 0.9);
      dashLine(g, px, py, cx, cy, 7, 4);
    } else {
      g.lineStyle(2.5, cell.type === 'blocked' ? C.ray_blocked : C.ray_hit, 1);
      g.lineBetween(px, py, cx, cy);
    }
    px = cx; py = cy;
  }

  const last = rayCells[rayCells.length - 1];
  const lx = BX + last.col * CELL + CELL / 2;
  const ly = BY + last.row * CELL + CELL / 2;
  const m  = CELL * 0.30;

  if (last.type === 'hit') {
    g.lineStyle(5, 0x000000, 0.5);
    g.lineBetween(lx - m, ly - m, lx + m, ly + m);
    g.lineBetween(lx + m, ly - m, lx - m, ly + m);
    g.lineStyle(4, 0xffffff, 1);
    g.lineBetween(lx - m, ly - m, lx + m, ly + m);
    g.lineBetween(lx + m, ly - m, lx - m, ly + m);
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2 + Math.PI / 8;
      g.lineStyle(2, 0xffffff, 0.75);
      g.lineBetween(lx + Math.cos(a) * (m + 2), ly + Math.sin(a) * (m + 2),
                    lx + Math.cos(a) * (m + 10), ly + Math.sin(a) * (m + 10));
    }

  } else if (last.type === 'blocked') {
    g.lineStyle(5, 0x000000, 0.5);
    g.lineBetween(lx - m, ly - m, lx + m, ly + m);
    g.lineBetween(lx + m, ly - m, lx - m, ly + m);
    g.lineStyle(4, C.ray_blocked, 1);
    g.lineBetween(lx - m, ly - m, lx + m, ly + m);
    g.lineBetween(lx + m, ly - m, lx - m, ly + m);
    g.lineStyle(2, C.ray_blocked, 0.7);
    g.strokeCircle(lx, ly, m + 5);

  } else if (last.type === 'soft') {
    const tr = m + 2;
    g.lineStyle(3, 0x000000, 0.4);
    g.fillStyle(C.ray_soft, 1);
    g.fillTriangle(lx, ly - tr, lx - tr, ly + tr * 0.7, lx + tr, ly + tr * 0.7);
    g.lineStyle(2.5, 0xffffff, 0.9);
    g.strokeTriangle(lx, ly - tr, lx - tr, ly + tr * 0.7, lx + tr, ly + tr * 0.7);
    g.fillStyle(0x000000, 0.7);
    g.fillRect(lx - 1.5, ly - tr * 0.45, 3, tr * 0.5);
    g.fillCircle(lx, ly + tr * 0.25, 2);
  }
}

// ═══════════════════════════════════════════════════════════════════
//  TOKEN DRAWING
// ═══════════════════════════════════════════════════════════════════

/**
 * Draw a token (ATK or DEF).
 * @param {Phaser.GameObjects.Graphics} g - Graphics object
 * @param {number} col - Column
 * @param {number} row - Row
 * @param {number} angle - Token angle (unused in current implementation)
 * @param {string} role - 'atk' or 'def'
 * @param {boolean} isP1 - Is player 1
 * @param {boolean} stale - Is cached position (draw semi-transparent)
 * @param {number} time - Current time for animation
 */
export function drawToken(g, col, row, angle, role, isP1, stale, time) {
  const { x: cx0, y: cy0 } = cc(col, row);
  const r16    = CELL * 0.36;
  const fill   = isP1 ? (role === 'atk' ? C.p1_atk : C.p1_def)
                      : (role === 'atk' ? C.p2_atk : C.p2_def);
  const border = isP1 ? C.p1_border : C.p2_border;

  const phase = (col * 7 + row * 13) * 0.3;
  const bob   = Math.sin(time / 450 + phase) * 1.4;
  const cx = cx0, cy = cy0 + bob;

  const bodyA   = stale ? 0.45 : 1.0;
  const borderA = stale ? 0.6  : 1.0;

  g.fillStyle(0x000000, 0.28 * bodyA);
  g.fillEllipse(cx + 1, cy0 + r16 + 3, r16 * 1.6, r16 * 0.45);

  if (role === 'atk') {
    g.fillStyle(fill, bodyA);
    g.fillRoundedRect(cx - r16, cy - r16, r16 * 2, r16 * 2, 6);
    g.fillStyle(0xffffff, 0.20 * bodyA);
    g.fillRoundedRect(cx - r16 + 2, cy - r16 + 2, r16 * 2 - 4, r16 * 0.7, 5);
    g.lineStyle(2.5, border, borderA);
    g.strokeRoundedRect(cx - r16, cy - r16, r16 * 2, r16 * 2, 6);
  } else {
    g.fillStyle(fill, bodyA);
    g.fillPoints([
      { x: cx,       y: cy - r16 }, { x: cx + r16, y: cy },
      { x: cx,       y: cy + r16 }, { x: cx - r16, y: cy }
    ], true);
    g.fillStyle(0xffffff, 0.22 * bodyA);
    g.fillPoints([
      { x: cx,           y: cy - r16 + 2 }, { x: cx + r16 * 0.6, y: cy - r16 * 0.2 },
      { x: cx,           y: cy },           { x: cx - r16 * 0.6, y: cy - r16 * 0.2 }
    ], true);
    g.lineStyle(2.5, border, borderA);
    g.strokePoints([
      { x: cx,       y: cy - r16 }, { x: cx + r16, y: cy },
      { x: cx,       y: cy + r16 }, { x: cx - r16, y: cy }
    ], true);
  }
}

// ═══════════════════════════════════════════════════════════════════
//  PLACEMENT GUIDE DRAWING
// ═══════════════════════════════════════════════════════════════════

/**
 * Draw HQ placement guide overlay.
 * Note: Zone labels need to be created by the scene.
 */
export function drawPlacementGuide(g, phase, activeSide, time) {
  const isScan = phase === 'scan';

  const pulseA = 0.18 + 0.10 * Math.sin(time / 350);
  const pulseB = 0.18 + 0.10 * Math.sin(time / 350 + Math.PI);

  g.fillStyle(0x120904, isScan ? 0.44 : 0.24);
  g.fillRoundedRect(BX + 1, BY + 1, COLS * CELL - 2, ROWS * CELL - 2, 8);

  if (!isScan) {
    for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
      if (c + r < 11) {
        const x = BX + c * CELL + 1, y = BY + r * CELL + 1;
        const p1Alpha = activeSide === 'p2' ? pulseA * 0.45 : pulseA;
        g.fillStyle(C.p1_border, p1Alpha);
        g.fillRoundedRect(x, y, CELL - 3, CELL - 3, 3);
        g.lineStyle(1.5, 0x40a040, 0.85);
        g.lineBetween(x + CELL - 11, y + 6, x + CELL - 8, y + 9);
        g.lineBetween(x + CELL - 8,  y + 9, x + CELL - 4, y + 4);
      }
    }

    for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
      if (c + r > 11) {
        const x = BX + c * CELL + 1, y = BY + r * CELL + 1;
        const p2Alpha = activeSide === 'p1' ? pulseB * 0.45 : pulseB;
        g.fillStyle(C.p2_border, p2Alpha);
        g.fillRoundedRect(x, y, CELL - 3, CELL - 3, 3);
        g.lineStyle(1.5, 0x40a040, 0.85);
        g.lineBetween(x + 4, y + 7, x + 7, y + 10);
        g.lineBetween(x + 7, y + 10, x + 11, y + 5);
      }
    }

    const noPlaceA = 0.30 + 0.10 * Math.sin(time / 250);
    for (let r = 0; r < ROWS; r++) for (let c = 0; c < COLS; c++) {
      if (c + r === 11) {
        const x = BX + c * CELL + 1, y = BY + r * CELL + 1;
        g.fillStyle(0xff4040, noPlaceA * 0.35);
        g.fillRoundedRect(x, y, CELL - 3, CELL - 3, 3);
        g.lineStyle(2, 0xff3030, noPlaceA);
        g.lineBetween(x + 6, y + CELL - 9, x + CELL - 9, y + 6);
      }
    }
  }
}
