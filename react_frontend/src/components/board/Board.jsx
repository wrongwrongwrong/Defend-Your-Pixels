import { GRID_SIZE, CELL_SIZE } from "../../game/gameLogic";
import HQ from "./HQ";
import PlayerZone from "./PlayerZone";
import Token from "../entities/Token";
import Unit from "../entities/Unit";

export default function Board({ gameState, onUpgrade, activePlayer }) {
  const totalSize = GRID_SIZE * CELL_SIZE;

  return (
    <div
      className="relative border border-slate-700 rounded"
      style={{
        width: totalSize,
        height: totalSize,
        background: "rgba(8, 12, 28, 0.97)",
        flexShrink: 0,
      }}
    >
      <GridLines size={totalSize} cellSize={CELL_SIZE} />

      {gameState.players.map((p) => (
        <PlayerZone key={p.id} player={p} cellSize={CELL_SIZE} gridSize={GRID_SIZE} />
      ))}

      <HQ cellSize={CELL_SIZE} />

      {gameState.players.map((player) =>
        player.tokens.map((token) => (
          <Token
            key={token.id}
            token={token}
            playerColor={player.color}
            cellSize={CELL_SIZE}
            playerEther={player.ether}
            isActivePlayer={player.id === activePlayer}
            onUpgrade={onUpgrade}
          />
        ))
      )}

      {gameState.units
        .filter((u) => u.hp > 0 || u.dying)
        .map((unit) => (
          <Unit key={unit.id} unit={unit} cellSize={CELL_SIZE} />
        ))}
    </div>
  );
}

function GridLines({ size, cellSize }) {
  const lines = [];
  const count = size / cellSize;
  for (let i = 1; i < count; i++) {
    const pos = i * cellSize;
    lines.push(
      <line
        key={`v${i}`}
        x1={pos}
        y1={0}
        x2={pos}
        y2={size}
        stroke="rgba(148,163,184,0.07)"
        strokeWidth="1"
      />
    );
    lines.push(
      <line
        key={`h${i}`}
        x1={0}
        y1={pos}
        x2={size}
        y2={pos}
        stroke="rgba(148,163,184,0.07)"
        strokeWidth="1"
      />
    );
  }
  return (
    <svg
      className="absolute inset-0 pointer-events-none z-[1]"
      width={size}
      height={size}
    >
      {lines}
    </svg>
  );
}
