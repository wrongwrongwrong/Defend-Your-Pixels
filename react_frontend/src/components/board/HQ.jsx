// HQ.jsx
// Renders the central HQ tile at the intersection of the board.
// Shows a large HP bar and glows gold. Flashes red when HP is low.

import { hpColor } from "../../game/gameLogic";

export default function HQ({ hp, maxHp = 100, cellSize }) {
  const pct = Math.max(0, hp) / maxHp;
  // HP 百分比，Math.max(0, hp) 確保不會出現負數
  // 例如 hp=75 → pct=0.75

  const barColor = hpColor(hp, maxHp);
  // 從 gameLogic.js 引入的函式：
  // pct > 0.6 → 綠色
  // pct > 0.3 → 黃色
  // pct ≤ 0.3 → 紅色

  const isLow = pct < 0.3;
  // HP 低於 30% 時為 true，觸發警示動畫

  const size = cellSize * 2; // HQ occupies a 2×2 visual area

  return (
    <div
      className={`absolute flex flex-col items-center justify-center rounded border-2 z-10
        ${isLow ? "border-red-500 pulse-bright" : "border-yellow-400"}
        glow-gold
      `}
      style={{
        width: size,
        height: size,
        left: 5 * cellSize,   // column 5 (0-indexed), center at 5,5 on 12-cell grid
        top: 5 * cellSize,    // row 5
        background: "rgba(30, 20, 0, 0.85)",
        pointerEvents: "none",
      }}
    >
      {/* Title */}
      <span className="text-yellow-300 font-bold text-xs tracking-widest">HQ</span>

      {/* HP bar */}
      <div className="w-4/5 h-2 bg-slate-800 rounded-full overflow-hidden mt-1">
        <div
          className="h-full rounded-full hp-bar-fill"
          style={{ width: `${pct * 100}%`, background: barColor }}
        />
      </div>
      <span className="text-yellow-200 text-xs mt-0.5">{hp}/{maxHp}</span>
    </div>
  );
}
