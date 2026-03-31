// Board.jsx
// The main 12×12 grid board. Renders:
//   - Subtle grid lines
//   - Player zone overlays (PlayerZone)
//   - HQ at the center (HQ)
//   - All tokens (Token)
//   - All active units (Unit)
// All child components are positioned absolutely within this div using
// cell coordinates multiplied by CELL_SIZE.

import { GRID_SIZE, CELL_SIZE } from "../../game/gameLogic";
import HQ from "./HQ";
import PlayerZone from "./PlayerZone";
import Token from "../entities/Token";
import Unit from "../entities/Unit";

export default function Board({ gameState, onUpgrade }) {
  const totalSize = GRID_SIZE * CELL_SIZE;
  //                   12    ×   56px   = 672px

  return (
    <div
      className="relative border border-slate-700 rounded"
      style={{
        width: totalSize,   // 672px
        height: totalSize,  // 672px
        background: "rgba(8, 12, 28, 0.97)",
        flexShrink: 0,
      }}
    >
      {/* ── Grid lines ────────────────────────────────────────── */}
      <GridLines size={totalSize} cellSize={CELL_SIZE} />

      {/* ── Player zone tints ─────────────────────────────────── */}
      {gameState.players.map((p) => (
        <PlayerZone key={p.id} player={p} cellSize={CELL_SIZE} gridSize={GRID_SIZE} />
      ))}

      {/* ── HQ ────────────────────────────────────────────────── */}
      <HQ hp={gameState.hqHP} maxHp={100} cellSize={CELL_SIZE} />

      {/* ── Tokens ────────────────────────────────────────────── */}
      {gameState.players.map((player) =>
        player.tokens.map((token) => (
          <Token
            key={token.id}
            token={token}
            playerColor={player.color}
            cellSize={CELL_SIZE}
            playerResources={player.resources}
            onUpgrade={onUpgrade}
          />
        ))
      )}

      {/* ── Units ─────────────────────────────────────────────── */}
      {gameState.units
        .filter((u) => u.hp > 0 || u.dying) // filter out dead units (but keep dying ones for death animation)
        .map((unit) => (
          <Unit key={unit.id} unit={unit} cellSize={CELL_SIZE} />
        ))}
    </div>
  );
}

// ─── Grid lines ──────────────────────────────────────────────────────────────

function GridLines({ size, cellSize }) {
  const lines = [];
  const count = size / cellSize;

  for (let i = 1; i < count; i++) {
    const pos = i * cellSize;
    // Vertical
    lines.push(
      <line
        key={`v${i}`}
        x1={pos} y1={0} x2={pos} y2={size}
        stroke="rgba(148,163,184,0.07)"
        strokeWidth="1"
      />
    );
    // Horizontal
    lines.push(
      <line
        key={`h${i}`}
        x1={0} y1={pos} x2={size} y2={pos}
        stroke="rgba(148,163,184,0.07)"
        strokeWidth="1"
      />
    );
  }

  return (
    <svg
      className="absolute inset-0 pointer-events-none"
      width={size}
      height={size}
    >
      {lines}
    </svg>
  );
}
