// Per-player HUD for the Old Mick MVP validation layer.

import { hpColor } from "../../game/gameLogic";

export default function ResourceDisplay({ player, isActive }) {
  const isBlue = player.color === "blue";
  const accent = isBlue ? "text-blue-400" : "text-red-400";
  const borderColor = isBlue ? "border-blue-700" : "border-red-700";
  const bgColor = isBlue ? "bg-blue-950/40" : "bg-red-950/40";
  const glowClass = isBlue ? "glow-blue" : "glow-red";
  const maxT = player.commandTowerMaxHp ?? 20;
  const towerHp = player.commandTowerHp ?? maxT;
  const barFill = hpColor(towerHp, maxT);

  return (
    <div
      className={`flex flex-col gap-1 px-4 py-2 rounded-lg border ${borderColor} ${bgColor} ${glowClass} min-w-[200px] ${
        isActive ? "ring-2 ring-cyan-500/60" : ""
      }`}
    >
      <div className={`flex items-center gap-2 font-bold text-sm ${accent}`}>
        <span className="text-base">{isBlue ? "🔵" : "🔴"}</span>
        <span>Player {player.id}</span>
        <span className="text-xs font-normal text-slate-500">{player.hqName ?? "HQ"}</span>
        <span className="text-xs font-normal text-slate-500 ml-auto">
          {player.zone}
          {isActive && <span className="text-cyan-300 ml-1">· your turn</span>}
        </span>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span className="w-24 shrink-0">{player.hqName ?? "HQ"}</span>
        <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full hp-bar-fill"
            style={{ width: `${(towerHp / maxT) * 100}%`, background: barFill }}
          />
        </div>
        <span className="w-10 text-right">
          {towerHp}/{maxT}
        </span>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span className="w-24 shrink-0">{player.resourceName ?? "Resources"}</span>
        <span className="text-amber-300 font-bold">{player.ether}</span>
        <span className="text-slate-500">placeholder contract field for future economy work</span>
      </div>
    </div>
  );
}
