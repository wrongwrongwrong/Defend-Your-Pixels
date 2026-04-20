import { hpColor } from "../../game/gameLogic";
import { transformBoardPosition } from "../../game/viewTransform";
import { getEntityVisuals } from "../entities/entityVisuals";

export default function CommandTower({ player, cellSize, gridSize, viewPlayerId }) {
  const towerPosition = player.commandTowerPosition;
  if (!towerPosition) return null;

  const displayPosition = transformBoardPosition(towerPosition, viewPlayerId, gridSize);
  const { accent, glowClass, tokenBorderColor, tokenBackground } = getEntityVisuals(player.color);
  const maxHp = player.commandTowerMaxHp ?? 20;
  const towerHp = player.commandTowerHp ?? maxHp;
  const hpPct = Math.max(0, towerHp) / Math.max(1, maxHp);
  const barColor = hpColor(towerHp, maxHp);
  const size = cellSize - 8;

  return (
    <div
      className={`absolute z-20 flex flex-col items-center justify-center rounded border-2 ${tokenBorderColor} ${glowClass} pointer-events-none`}
      style={{
        width: size,
        height: size,
        left: displayPosition.x * cellSize + 4,
        top: displayPosition.y * cellSize + 4,
        background: tokenBackground,
        boxShadow: `0 0 0 2px ${accent}55`,
      }}
      title={`${player.hqName ?? "HQ"} ${towerHp}/${maxHp}`}
    >
      <span className="text-[9px] font-black tracking-[0.2em] text-amber-200">HQ</span>
      <span className="mt-0.5 text-[9px] font-bold text-slate-200 text-center px-1 leading-tight">
        {player.hqName ?? "Command Tower"}
      </span>
      <div className="mt-1 h-1 w-4/5 overflow-hidden rounded-full bg-slate-950/90">
        <div
          className="h-full rounded-full hp-bar-fill"
          style={{ width: `${hpPct * 100}%`, background: barColor }}
        />
      </div>
      <span className="mt-1 text-[8px] font-semibold text-slate-400">
        {towerHp}/{maxHp}
      </span>
    </div>
  );
}
