// gameLogic.js — pure functions for Pixel Defense game rules

export const GRID_SIZE = 12;
export const CELL_SIZE = 56; // px per cell

// Token spawn cooldowns (ms)
export const SPAWN_COOLDOWNS = {
  infantry: 3000,
  tank: 6000,
  bomber: 8000,
  def: Infinity, // DEF tokens never spawn units
};

// Base unit stats per type
export const UNIT_STATS = {
  infantry: { hp: 20, maxHp: 20, speed: 1.4, atk: 5, range: 1 },
  tank:     { hp: 50, maxHp: 50, speed: 0.6, atk: 12, range: 1 },
  bomber:   { hp: 15, maxHp: 15, speed: 0.5, atk: 25, range: 2 },
  def:      { hp: 80, maxHp: 80, speed: 0,   atk: 8,  range: 1 },
};

// Map rotation string → grid direction vector
export const ROTATION_TO_DIRECTION = {
  forward:  { dx: 0,  dy: -1 },
  backward: { dx: 0,  dy: 1  },
  left:     { dx: -1, dy: 0  },
  right:    { dx: 1,  dy: 0  },
};

/** Euclidean distance between two {x,y} positions */
export function distance(a, b) {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
}

/**
 * Determine a unit's target cell based on token rotation.
 * forward  → HQ (center of board)
 * left     → left enemy zone
 * right    → right enemy zone
 * backward → stay near token (defend)
 */
export function getUnitTarget(rotation, ownerZone) {
  const center = { x: 6, y: 6 };
  switch (rotation) {
    case "forward":
      return ownerZone === "bottom" ? { x: 6, y: 0 } : { x: 6, y: 11 };
    case "left":
      return { x: 0, y: 6 };
    case "right":
      return { x: 11, y: 6 };
    case "backward":
      return center; // defend HQ area
    default:
      return center;
  }
}

/**
 * Move a unit one step toward its target.
 * Returns the new {x, y} position (floating point for smooth rendering).
 */
export function stepToward(pos, target, speed, dt) {
  const dx = target.x - pos.x;
  const dy = target.y - pos.y;
  const dist = Math.sqrt(dx * dx + dy * dy);
  if (dist < 0.05) return { ...target };
  const step = (speed * dt) / 1000; // dt in ms
  return {
    x: pos.x + (dx / dist) * step,
    y: pos.y + (dy / dist) * step,
  };
}

/** Returns true if a unit has reached its target (within 0.3 cells) */
export function hasReachedTarget(pos, target) {
  return distance(pos, target) < 0.3;
}

/** Find nearest enemy unit within attack range */
export function findNearestEnemy(unit, allUnits) {
  const enemies = allUnits.filter(u => u.playerId !== unit.playerId && u.hp > 0);
  if (!enemies.length) return null;
  let nearest = null;
  let minDist = Infinity;
  for (const e of enemies) {
    const d = distance(unit.pos, e.pos);
    if (d < minDist) { minDist = d; nearest = e; }
  }
  return minDist <= unit.range + 0.5 ? nearest : null;
}

/** Calculate HP percentage for color coding */
export function hpColor(current, max) {
  const pct = current / max;
  if (pct > 0.6) return "#22c55e"; // green
  if (pct > 0.3) return "#eab308"; // yellow
  return "#ef4444";                 // red
}

/** Phase 2 triggers when HQ HP drops below 50% */
export function shouldTriggerPhase2(hqHp, hqMaxHp = 100, elapsedMs = 0) {
  return hqHp <= hqMaxHp * 0.5 || elapsedMs >= 120_000;
}

/** Resource rewards */
export const REWARD_HQ_HIT   = 5;
export const REWARD_KILL_UNIT = 3;
export const REWARD_HQ_DAMAGE_PER_HIT = 1;
