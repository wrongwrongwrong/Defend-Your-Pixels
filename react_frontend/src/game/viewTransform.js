import { PLAYER_ID } from "./constants";

const MIRRORED_DIRECTION = {
  forward: "backward",
  backward: "forward",
  left: "right",
  right: "left",
  up: "down",
  down: "up",
  up_left: "down_right",
  up_right: "down_left",
  down_left: "up_right",
  down_right: "up_left",
};

export function isMirroredView(viewPlayerId) {
  return viewPlayerId === PLAYER_ID.P2;
}

export function transformBoardPosition(position, viewPlayerId, gridSize) {
  if (!position) return position;
  if (!isMirroredView(viewPlayerId)) return position;
  return {
    x: gridSize - 1 - position.x,
    y: gridSize - 1 - position.y,
  };
}

export function toAuthoritativeBoardPosition(position, viewPlayerId, gridSize) {
  return transformBoardPosition(position, viewPlayerId, gridSize);
}

export function transformFacing(facing, viewPlayerId) {
  if (!isMirroredView(viewPlayerId)) return facing;
  return MIRRORED_DIRECTION[facing] ?? facing;
}

export function transformDirectionLabel(direction, viewPlayerId) {
  if (!isMirroredView(viewPlayerId)) return direction;
  return MIRRORED_DIRECTION[direction] ?? direction;
}

export function formatBoardPosition(position, viewPlayerId, gridSize) {
  if (!position) return "(?, ?)";
  const displayPosition = transformBoardPosition(position, viewPlayerId, gridSize);
  return `(${displayPosition.x + 1}, ${displayPosition.y + 1})`;
}
