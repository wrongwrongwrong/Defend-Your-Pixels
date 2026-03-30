// Token.jsx
// Renders a single physical token on the board grid.
// Shows: type icon, HP bar, attack range circle, direction arrow, cooldown ring.
// Clicking a token with enough resources shows upgrade options.

import { useMemo, useState } from "react";
import { hpColor, SPAWN_COOLDOWNS, UNIT_STATS } from "../utils/gameLogic";

const TYPE_ICONS = {
  infantry: "⚔",
  tank:     "🛡",
  bomber:   "💣",
  def:      "🔒",
};

const TYPE_RANGE = {
  infantry: 2,
  tank:     1.5,
  bomber:   3,
  def:      1,
};

// Direction arrow rotation (CSS degrees)
const DIR_ANGLE = {
  forward:  0,
  right:    90,
  backward: 180,
  left:     270,
};

export default function Token({ token, playerColor, cellSize, onUpgrade, playerResources }) {
  const [showUpgrade, setShowUpgrade] = useState(false);

  const isBlue = playerColor === "blue";
  const accent = isBlue ? "#3b82f6" : "#ef4444";
  const glowClass = isBlue ? "glow-blue" : "glow-red";
  const borderColor = isBlue ? "border-blue-500" : "border-red-500";

  const hpPct = token.hp / (token.maxHp ?? token.hp);
  const barColor = hpColor(token.hp, token.maxHp ?? token.hp);

  // Range circle radius in pixels
  const rangeRadius = (TYPE_RANGE[token.type] ?? 1.5) * cellSize;

  // Cooldown SVG ring
  const cooldownMs = SPAWN_COOLDOWNS[token.type];
  const hasCooldown = isFinite(cooldownMs);
  const circumference = 2 * Math.PI * 14; // radius=14

  const dirAngle = DIR_ANGLE[token.rotation] ?? 0;

  const UPGRADE_COST = 10;
  const canAfford = playerResources >= UPGRADE_COST;

  return (
    <div
      className={`absolute flex flex-col items-center justify-center rounded border ${borderColor} ${glowClass} cursor-pointer select-none z-20`}
      style={{
        width: cellSize - 4,
        height: cellSize - 4,
        left: token.position.x * cellSize + 2,
        top:  token.position.y * cellSize + 2,
        background: isBlue ? "rgba(10,20,60,0.9)" : "rgba(60,10,10,0.9)",
      }}
      onClick={() => setShowUpgrade((v) => !v)}
      title={`${token.type} — HP ${token.hp} | Rotation: ${token.rotation}`}
    >
      {/* Attack range overlay (transparent circle behind token) */}
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

      {/* Direction indicator */}
      <div
        className="absolute top-0.5 right-0.5 text-yellow-300 text-xs leading-none"
        style={{ transform: `rotate(${dirAngle}deg)`, transformOrigin: "center" }}
        title={`Facing: ${token.rotation}`}
      >
        ▲
      </div>

      {/* Type icon */}
      <span className="text-base leading-none">{TYPE_ICONS[token.type] ?? "?"}</span>

      {/* Type label */}
      <span
        className="text-xs font-bold leading-none mt-0.5"
        style={{ color: accent }}
      >
        {token.type.toUpperCase()}
      </span>

      {/* HP bar */}
      <div className="w-4/5 h-1 bg-slate-800 rounded-full overflow-hidden mt-1">
        <div
          className="h-full rounded-full hp-bar-fill"
          style={{ width: `${hpPct * 100}%`, background: barColor }}
        />
      </div>

      {/* Cooldown ring (SVG) — only for ATK tokens */}
      {hasCooldown && (
        <svg
          className="absolute bottom-0.5 left-0.5 opacity-60"
          width="18"
          height="18"
          viewBox="0 0 32 32"
        >
          <circle cx="16" cy="16" r="14" fill="none" stroke="#334155" strokeWidth="3" />
          <circle
            cx="16" cy="16" r="14"
            fill="none"
            stroke={accent}
            strokeWidth="3"
            strokeDasharray={circumference}
            strokeDashoffset={0}
            strokeLinecap="round"
            transform="rotate(-90 16 16)"
            style={{
              animation: `cooldownShrink ${cooldownMs}ms linear infinite`,
            }}
          />
        </svg>
      )}

      {/* Upgrade popup */}
      {showUpgrade && (
        <UpgradeMenu
          token={token}
          canAfford={canAfford}
          cost={UPGRADE_COST}
          accent={accent}
          onUpgrade={(type) => { onUpgrade?.(token.id, type); setShowUpgrade(false); }}
          onClose={() => setShowUpgrade(false)}
        />
      )}
    </div>
  );
}

// ─── Upgrade sub-component ───────────────────────────────────────────────────

function UpgradeMenu({ token, canAfford, cost, accent, onUpgrade, onClose }) {
  const upgrades = [
    { key: "damage",   label: "↑ Damage",   icon: "⚡" },
    { key: "cooldown", label: "↓ Cooldown", icon: "⏱" },
    { key: "hp",       label: "↑ HP",       icon: "❤" },
  ];

  return (
    <div
      className="absolute z-50 flex flex-col gap-1 p-2 rounded border border-yellow-500 bg-slate-900/95 shadow-xl"
      style={{ bottom: "110%", left: "50%", transform: "translateX(-50%)", minWidth: 130 }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="text-yellow-300 text-xs font-bold text-center mb-1">
        Upgrade ({cost} ⬡)
      </div>
      {upgrades.map((u) => (
        <button
          key={u.key}
          disabled={!canAfford}
          className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold transition
            ${canAfford
              ? "hover:bg-yellow-900/50 text-yellow-200 cursor-pointer"
              : "text-slate-600 cursor-not-allowed"
            }`}
          onClick={() => canAfford && onUpgrade(u.key)}
        >
          <span>{u.icon}</span>
          <span>{u.label}</span>
        </button>
      ))}
      <button
        className="text-slate-500 text-xs mt-1 hover:text-slate-300"
        onClick={onClose}
      >
        ✕ close
      </button>
    </div>
  );
}
