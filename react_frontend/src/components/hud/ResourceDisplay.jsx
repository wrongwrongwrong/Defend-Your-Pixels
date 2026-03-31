// ResourceDisplay.jsx
// Shows each player's name, zone color, HP bar, and resource count.
// Rendered once per player in the HUD strip above/below the board.

import { hpColor } from "../../game/gameLogic";

export default function ResourceDisplay({ player }) {
  const isBlue = player.color === "blue";
  const accent = isBlue ? "text-blue-400" : "text-red-400";
  const borderColor = isBlue ? "border-blue-700" : "border-red-700";
  const bgColor = isBlue ? "bg-blue-950/40" : "bg-red-950/40";
  const glowClass = isBlue ? "glow-blue" : "glow-red";
  const barFill = hpColor(player.hp, 100);

  return (
    <div
      className={`flex flex-col gap-1 px-4 py-2 rounded-lg border ${borderColor} ${bgColor} ${glowClass} min-w-[180px]`}
    >
      {/* Player label */}
      <div className={`flex items-center gap-2 font-bold text-sm ${accent}`}>
        <span className="text-base">{isBlue ? "🔵" : "🔴"}</span>
        <span>Player {player.id}</span>
        <span className="text-xs font-normal text-slate-400 ml-auto">
          ({player.zone})
        </span>
      </div>

      {/* HP bar */}
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span className="w-6">HP</span>
        <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full hp-bar-fill"
            style={{ width: `${player.hp}%`, background: barFill }}
          />
        </div>
        <span className="w-8 text-right">{player.hp}</span>
      </div>

      {/* Resources */}
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span className="w-6">⬡</span>
        <span className="text-yellow-300 font-bold">{player.resources}</span>
        <span className="text-slate-500">resources</span>
      </div>
    </div>
  );
}
