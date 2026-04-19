// Visual helpers for the validation frontend. Authoritative rules live in model_backend.

export { GRID_SIZE, CELL_SIZE, UNIT_KIND, COMMAND_TOWER_MAX_HP } from "./constants";

export function hpColor(current, max) {
  const pct = current / max;
  if (pct > 0.6) return "#22c55e";
  if (pct > 0.3) return "#eab308";
  return "#ef4444";
}
