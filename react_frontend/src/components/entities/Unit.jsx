import { hpColor } from "../../game/gameLogic";
import { transformBoardPosition } from "../../game/viewTransform";
import { getEntityVisuals, KIND_ICONS } from "./entityVisuals";

export default function Unit({ unit, cellSize, gridSize, viewPlayerId }) {
  const kind = unit.kind ?? "attacker";
  const displayPosition = transformBoardPosition(unit.pos, viewPlayerId, gridSize);
  const { glowClass, unitBorderColor, unitBackground } = getEntityVisuals(unit.playerId);

  const maxHp = unit.maxHp ?? unit.hp ?? 1;
  const hpPct = Math.max(0, unit.hp) / Math.max(1, maxHp);
  const barColor = hpColor(unit.hp, maxHp);

  const size = Math.floor(cellSize * 0.65);
  const half = size / 2;

  return (
    <div
      className={`absolute flex flex-col items-center justify-center rounded border ${unitBorderColor} ${glowClass} unit-spawn pointer-events-none z-30
        ${unit.fighting ? "pulse-bright" : ""}
        ${unit.dying ? "unit-die" : ""}
      `}
      style={{
        width: size,
        height: size,
        left: displayPosition.x * cellSize - half + cellSize / 2,
        top: displayPosition.y * cellSize - half + cellSize / 2,
        background: unitBackground,
      }}
      title={`${kind} HP:${unit.hp}`}
    >
      <span className="text-xs leading-none">{KIND_ICONS[kind] ?? "•"}</span>
      <div className="w-4/5 h-0.5 bg-slate-800 rounded-full overflow-hidden mt-0.5">
        <div
          className="h-full rounded-full hp-bar-fill"
          style={{ width: `${hpPct * 100}%`, background: barColor }}
        />
      </div>
      {unit.fighting && (
        <span className="absolute -top-2 -right-2 text-red-400 text-xs animate-ping">⚡</span>
      )}
    </div>
  );
}
