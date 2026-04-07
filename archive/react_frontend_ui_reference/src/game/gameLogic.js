// Visual + light math helpers. Rules live in turns.js / ether.js / constants.js

export { GRID_SIZE, CELL_SIZE, UNIT_KIND, COMMAND_TOWER_MAX_HP } from "./constants";
export { getEther, addEther, trySpendEther } from "./ether";
export { createInitialGameState, endTurn, phaseForTurn } from "./turns";

/** Token / unit stat hints for rendering (pitch: Attacker vs Defender) */
export const UNIT_STATS = {
  attacker: { maxHp: 30, label: "ATK" },
  defender: { maxHp: 40, label: "DEF" },
};

export function distance(a, b) {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
}

export function hpColor(current, max) {
  const pct = current / max;
  if (pct > 0.6) return "#22c55e";
  if (pct > 0.3) return "#eab308";
  return "#ef4444";
}
