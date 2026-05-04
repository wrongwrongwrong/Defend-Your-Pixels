/**
 * Utility functions for Old Mick Against the Mob.
 * @module helpers
 */

import {
  BX, BY, CELL, COLS, ROWS, DIR_VEC,
  PHASE_LABEL, SIDE_LABEL, ERROR_PRIORITY, ERROR_TITLE, ERROR_MESSAGE_OVERRIDE
} from './constants.js';

// ═══════════════════════════════════════════════════════════════════
//  GRID & COORDINATE HELPERS
// ═══════════════════════════════════════════════════════════════════

/** Pixel centre of grid cell (col, row) */
export function cc(col, row) {
  return { x: BX + col * CELL + CELL / 2, y: BY + row * CELL + CELL / 2 };
}

/** Check if cell belongs to P1 (Old Mick) territory */
export function isP1(col, row) { return col + row < 11; }

/** Check if cell belongs to P2 (The Mob) territory */
export function isP2(col, row) { return col + row > 11; }

/** Check if a side owns a cell */
export function sideOwnsCell(side, col, row) {
  if (side === 'p1') return isP1(col, row);
  if (side === 'p2') return isP2(col, row);
  return false;
}

/** Convert number colour to CSS hex string */
export function hex(n) { return '#' + n.toString(16).padStart(6, '0'); }

/** Get cell label from col/row (e.g., "D4") */
export function cellLabel(col, row) {
  if (col == null || row == null) return '--';
  return `${String.fromCharCode(65 + col)}${row + 1}`;
}

// ═══════════════════════════════════════════════════════════════════
//  LABEL HELPERS
// ═══════════════════════════════════════════════════════════════════

export function phaseLabel(phase) {
  return PHASE_LABEL[phase] || 'Setup';
}

export function sideLabel(side) {
  return SIDE_LABEL[side] || 'Not chosen';
}

export function setupFlag(flag, readyText, waitingText) {
  return flag ? readyText : waitingText;
}

export function hqProgressLabel(sideState) {
  if (!sideState) return 'waiting';
  if (sideState.confirmed) return 'confirmed (hidden)';
  if (sideState.has_candidate) return 'candidate saved';
  return 'waiting';
}

// ═══════════════════════════════════════════════════════════════════
//  ERROR HANDLING HELPERS
// ═══════════════════════════════════════════════════════════════════

export function isIgnoredErrorCode(code) {
  return code === 'token_detection_failed' || code === 'inactive_side_token_changed';
}

export function dedupeErrorsByCode(errors) {
  const deduped = [];
  const seen = new Set();
  for (const error of Array.isArray(errors) ? errors : []) {
    const code = error?.code;
    if (!code || isIgnoredErrorCode(code) || seen.has(code)) continue;
    seen.add(code);
    deduped.push(error);
  }
  return deduped;
}

export function errorPriority(code) {
  const index = ERROR_PRIORITY.indexOf(code);
  return index === -1 ? ERROR_PRIORITY.length : index;
}

export function primaryError(errors) {
  const deduped = dedupeErrorsByCode(errors);
  deduped.sort((left, right) => errorPriority(left.code) - errorPriority(right.code));
  return deduped[0] || null;
}

export function errorTitle(code) {
  return ERROR_TITLE[code] || 'Live Warning';
}

export function errorMessage(error) {
  const code = error?.code;
  return ERROR_MESSAGE_OVERRIDE[code] || error?.message || 'Live validation warning.';
}

export function errorTone(code) {
  if (code === 'hq_setup_complete') return 'success';
  if (code === 'inactive_side_token_changed') return 'warning';
  return 'error';
}

// ═══════════════════════════════════════════════════════════════════
//  RAY & ZONE COMPUTATION
// ═══════════════════════════════════════════════════════════════════

/**
 * Trace a ray from (startCol, startRow) in direction dir.
 * Returns array of { col, row, type } where type is:
 *   'path'    — free cell
 *   'hit'     — first undestroyed enemy cell
 *   'soft'    — first soft-terrain cell (absorbed, stops ray)
 *   'blocked' — hard terrain (stops ray, shows X)
 */
export function computeRay(startCol, startRow, dir, hardMap, softMap, attackerSide, destroyedMap, resourceMap) {
  if (!dir || !DIR_VEC[dir]) return [];
  const [dc, dr] = DIR_VEC[dir];
  const cells = [];
  let c = startCol + dc, r = startRow + dr;
  const isEnemyCell = attackerSide === 'p1' ? isP2 : isP1;

  while (c >= 0 && c < COLS && r >= 0 && r < ROWS) {
    const k = `${c},${r}`;
    if (hardMap[k])  { cells.push({ col: c, row: r, type: 'blocked' }); break; }
    if (softMap[k])  { cells.push({ col: c, row: r, type: 'soft'    }); break; }
    if (isEnemyCell(c, r) && resourceMap[k] && !destroyedMap[k]) {
      cells.push({ col: c, row: r, type: 'hit' });
      break;
    }
    cells.push({ col: c, row: r, type: 'path' });
    c += dc; r += dr;
  }
  return cells;
}

/** Return all cells in the DEF zone centred at (col, row), radius depends on tier. */
export function defZoneCells(col, row, tier) {
  const rad = tier >= 2 ? 2 : 1;   // tier 2 → 5×5, else 3×3
  const out = [];
  for (let dr = -rad; dr <= rad; dr++)
    for (let dc = -rad; dc <= rad; dc++) {
      const c = col + dc, r = row + dr;
      if (c >= 0 && c < COLS && r >= 0 && r < ROWS) out.push({ col: c, row: r });
    }
  return out;
}

// ═══════════════════════════════════════════════════════════════════
//  RESOURCE MAP BUILDER
// ═══════════════════════════════════════════════════════════════════

export function buildResourceMaps(terrain) {
  const p1 = {};
  const p2 = {};
  for (const resource of (terrain?.p1_resources || [])) p1[`${resource.col},${resource.row}`] = resource;
  for (const resource of (terrain?.p2_resources || [])) p2[`${resource.col},${resource.row}`] = resource;
  return { p1, p2 };
}
