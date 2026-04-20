import { transformBoardPosition } from "../../game/viewTransform";

export default function ResourceTile({ tile, cellSize, gridSize, viewPlayerId }) {
  const displayPosition = transformBoardPosition(tile.position, viewPlayerId, gridSize);
  const isBlue = tile.owner === 1;
  const protectedTile = (tile.protectionLayers ?? 0) > 0;

  return (
    <div
      className="absolute z-10 flex items-center justify-center rounded border pointer-events-none"
      style={{
        width: cellSize - 12,
        height: cellSize - 12,
        left: displayPosition.x * cellSize + 6,
        top: displayPosition.y * cellSize + 6,
        borderColor: protectedTile
          ? isBlue
            ? "rgba(147,197,253,0.95)"
            : "rgba(252,165,165,0.95)"
          : isBlue
            ? "rgba(59,130,246,0.45)"
            : "rgba(239,68,68,0.45)",
        background: protectedTile
          ? isBlue
            ? "rgba(59,130,246,0.3)"
            : "rgba(239,68,68,0.3)"
          : isBlue
            ? "rgba(30,64,175,0.16)"
            : "rgba(127,29,29,0.16)",
        boxShadow: protectedTile
          ? isBlue
            ? "0 0 12px rgba(147,197,253,0.45)"
            : "0 0 12px rgba(252,165,165,0.45)"
          : undefined,
      }}
      title={`${tile.themeName}${protectedTile ? " (protected)" : ""}`}
    >
      <span
        className="text-[10px] font-bold tracking-wide"
        style={{ color: protectedTile ? "#fef3c7" : isBlue ? "#bfdbfe" : "#fecaca" }}
      >
        {protectedTile ? "✦" : "•"}
      </span>
    </div>
  );
}
