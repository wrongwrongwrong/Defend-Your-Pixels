// Physical marker on grid — kind: attacker | defender (model_backend UnitKind)

import { hpColor } from "../../game/gameLogic";
import { transformBoardPosition, transformFacing } from "../../game/viewTransform";
import { getEntityVisuals, KIND_ICONS } from "./entityVisuals";

const KIND_RANGE = {
  attacker: 2,
  defender: 1.5,
};

const DIR_ANGLE = {
  forward: 0,
  right: 90,
  backward: 180,
  left: 270,
};

export default function Token({
  token,
  playerColor,
  cellSize,
  gridSize,
  viewPlayerId,
  isActivePlayer,
  selected,
  onSelect,
}) {
  const kind = token.kind ?? "attacker";
  const displayPosition = transformBoardPosition(token.position, viewPlayerId, gridSize);
  const displayRotation = transformFacing(token.rotation, viewPlayerId);

  const { accent, glowClass, tokenBorderColor, tokenBackground } = getEntityVisuals(playerColor);

  const maxHp = token.maxHp ?? token.hp ?? 1;
  const barColor = hpColor(token.hp, maxHp);
  const hpPct = Math.max(0, token.hp) / Math.max(1, maxHp);

  const rangeRadius = (KIND_RANGE[kind] ?? 2) * cellSize;
  const dirAngle = DIR_ANGLE[displayRotation] ?? 0;

  return (
    <div
      className={`absolute flex flex-col items-center justify-center rounded border ${tokenBorderColor} ${glowClass} cursor-pointer select-none z-20`}
      style={{
        width: cellSize - 4,
        height: cellSize - 4,
        left: displayPosition.x * cellSize + 2,
        top: displayPosition.y * cellSize + 2,
        background: tokenBackground,
        opacity: isActivePlayer ? 1 : 0.85,
        boxShadow: selected ? `0 0 0 2px ${accent}, 0 0 20px ${accent}88` : undefined,
      }}
      onClick={(event) => {
        event.stopPropagation();
        onSelect?.(token.id);
      }}
      title={`${kind} — HP ${token.hp} | ${displayRotation}`}
    >
      <div
        className="absolute rounded-full pointer-events-none"
        style={{
          width: rangeRadius * 2,
          height: rangeRadius * 2,
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%)",
          border: `1px solid ${accent}44`,
          background: `${accent}0d`,
        }}
      />

      <div
        className="absolute top-0.5 right-0.5 text-yellow-300 text-xs leading-none"
        style={{ transform: `rotate(${dirAngle}deg)`, transformOrigin: "center" }}
      >
        ▲
      </div>

      <span className="text-base leading-none">{KIND_ICONS[kind] ?? "?"}</span>
      <span
        className="text-[10px] font-bold leading-none mt-0.5 uppercase"
        style={{ color: accent }}
      >
        {kind}
      </span>

      <div className="w-4/5 h-1 bg-slate-800 rounded-full overflow-hidden mt-1">
        <div
          className="h-full rounded-full hp-bar-fill"
          style={{ width: `${hpPct * 100}%`, background: barColor }}
        />
      </div>
    </div>
  );
}
