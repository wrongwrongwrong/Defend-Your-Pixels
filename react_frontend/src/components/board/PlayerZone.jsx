// PlayerZone.jsx
// Highlights the player's home zone at the top or bottom of the board.
// Shows a tinted overlay and a zone label.

import { isMirroredView } from "../../game/viewTransform";

export default function PlayerZone({ player, cellSize, gridSize = 12, viewPlayerId }) {
  const isBlue = player.color === "blue";
  const displayZone = isMirroredView(viewPlayerId)
    ? player.zone === "bottom"
      ? "top"
      : "bottom"
    : player.zone;
  const isBottom = displayZone === "bottom";

  // Zone spans 2 rows at top or bottom of the 12-row grid
  const zoneRows = 2;
  const y = isBottom ? (gridSize - zoneRows) * cellSize : 0;
  const height = zoneRows * cellSize;
  const width = gridSize * cellSize;

  return (
    <div
      className="absolute pointer-events-none z-0"
      style={{
        left: 0,
        top: y,
        width,
        height,
        background: isBlue
          ? "rgba(37,99,235,0.08)"
          : "rgba(185,28,28,0.08)",
        borderTop: isBottom
          ? `1px solid ${isBlue ? "rgba(59,130,246,0.3)" : "rgba(239,68,68,0.3)"}`
          : "none",
        borderBottom: !isBottom
          ? `1px solid ${isBlue ? "rgba(59,130,246,0.3)" : "rgba(239,68,68,0.3)"}`
          : "none",
      }}
    >
      {/* Zone label */}
      <div
        className="absolute text-xs font-bold tracking-widest uppercase opacity-30"
        style={{
          left: 6,
          [isBottom ? "top" : "bottom"]: 4,
          color: isBlue ? "#93c5fd" : "#fca5a5",
        }}
      >
        P{player.id} Zone
      </div>
    </div>
  );
}
