import { hpColor, UNIT_STATS } from "../../game/gameLogic";

const KIND_ICONS = {
  attacker: "◎",
  defender: "▣",
};

export default function Unit({ unit, cellSize }) {
  const kind = unit.kind ?? "attacker";
  const isBlue = unit.playerId === 1;
  const accent = isBlue ? "#60a5fa" : "#f87171";
  const glowClass = isBlue ? "glow-blue" : "glow-red";
  const borderColor = isBlue ? "border-blue-400" : "border-red-400";

  const maxHp = unit.maxHp ?? UNIT_STATS[kind]?.maxHp ?? 30;
  const hpPct = Math.max(0, unit.hp) / maxHp;
  const barColor = hpColor(unit.hp, maxHp);

  const size = Math.floor(cellSize * 0.65);
  const half = size / 2;

  return (
    <div
      className={`absolute flex flex-col items-center justify-center rounded border ${borderColor} ${glowClass} unit-spawn pointer-events-none z-30
        ${unit.fighting ? "pulse-bright" : ""}
        ${unit.dying ? "unit-die" : ""}
      `}
      style={{
        width: size,
        height: size,
        left: unit.pos.x * cellSize - half + cellSize / 2,
        top: unit.pos.y * cellSize - half + cellSize / 2,
        background: isBlue ? "rgba(10,20,80,0.88)" : "rgba(80,10,10,0.88)",
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
