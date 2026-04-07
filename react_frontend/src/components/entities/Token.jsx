// Physical marker on grid — kind: attacker | defender (model_backend UnitKind)

import { useState } from "react";
import { hpColor, UNIT_STATS } from "../../game/gameLogic";

const KIND_ICONS = {
  attacker: "◎",
  defender: "▣",
};

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

const UPGRADE_COST_ETHER = 5;

export default function Token({
  token,
  playerColor,
  cellSize,
  onUpgrade,
  playerEther,
  isActivePlayer,
  upgradesEnabled,
  selected,
  onSelect,
}) {
  const [showUpgrade, setShowUpgrade] = useState(false);
  const kind = token.kind ?? "attacker";

  const isBlue = playerColor === "blue";
  const accent = isBlue ? "#3b82f6" : "#ef4444";
  const glowClass = isBlue ? "glow-blue" : "glow-red";
  const borderColor = isBlue ? "border-blue-500" : "border-red-500";

  const maxHp = token.maxHp ?? UNIT_STATS[kind]?.maxHp ?? 30;
  const barColor = hpColor(token.hp, maxHp);
  const hpPct = token.hp / maxHp;

  const rangeRadius = (KIND_RANGE[kind] ?? 2) * cellSize;
  const dirAngle = DIR_ANGLE[token.rotation] ?? 0;

  const canAfford = playerEther >= UPGRADE_COST_ETHER;
  const canUseMenu = isActivePlayer && upgradesEnabled;
  const upgradeDisabledReason = upgradesEnabled
    ? !isActivePlayer
      ? " (not your turn)"
      : ""
    : " (upgrade disabled in backend prototype)";

  return (
    <div
      className={`absolute flex flex-col items-center justify-center rounded border ${borderColor} ${glowClass} cursor-pointer select-none z-20`}
      style={{
        width: cellSize - 4,
        height: cellSize - 4,
        left: token.position.x * cellSize + 2,
        top: token.position.y * cellSize + 2,
        background: isBlue ? "rgba(10,20,60,0.9)" : "rgba(60,10,10,0.9)",
        opacity: isActivePlayer ? 1 : 0.85,
        boxShadow: selected ? `0 0 0 2px ${accent}, 0 0 20px ${accent}88` : undefined,
      }}
      onClick={(event) => {
        event.stopPropagation();
        onSelect?.(token.id);
        if (upgradesEnabled) {
          setShowUpgrade((v) => !v);
        }
      }}
      title={`${kind} — HP ${token.hp} | ${token.rotation}${upgradeDisabledReason}`}
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

      {showUpgrade && upgradesEnabled && (
        <UpgradeMenu
          kind={kind}
          canAfford={canAfford && canUseMenu}
          cost={UPGRADE_COST_ETHER}
          onUpgrade={(type) => {
            onUpgrade?.(token.id, type);
            setShowUpgrade(false);
          }}
          onClose={() => setShowUpgrade(false)}
        />
      )}
    </div>
  );
}

function UpgradeMenu({ kind, canAfford, cost, onUpgrade, onClose }) {
  const upgrades =
    kind === "attacker"
      ? [
          { key: "damage", label: "↑ Shot", icon: "⚡" },
          { key: "heatVent", label: "Vent path", icon: "❄" },
        ]
      : [
          { key: "shield", label: "↑ Shield", icon: "🛡" },
          { key: "hp", label: "↑ HP", icon: "❤" },
        ];

  return (
    <div
      className="absolute z-50 flex flex-col gap-1 p-2 rounded border border-amber-600 bg-slate-900/95 shadow-xl"
      style={{ bottom: "110%", left: "50%", transform: "translateX(-50%)", minWidth: 130 }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="text-amber-200 text-xs font-bold text-center mb-1">
        Upgrade ({cost} ether)
      </div>
      {upgrades.map((u) => (
        <button
          key={u.key}
          type="button"
          disabled={!canAfford}
          className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold transition
            ${canAfford
              ? "hover:bg-amber-900/40 text-amber-100 cursor-pointer"
              : "text-slate-600 cursor-not-allowed"
            }`}
          onClick={() => canAfford && onUpgrade(u.key)}
        >
          <span>{u.icon}</span>
          <span>{u.label}</span>
        </button>
      ))}
      <button
        type="button"
        className="text-slate-500 text-xs mt-1 hover:text-slate-300"
        onClick={onClose}
      >
        ✕ close
      </button>
    </div>
  );
}
