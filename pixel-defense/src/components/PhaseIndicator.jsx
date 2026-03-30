// PhaseIndicator.jsx
// Displays the current game phase (1 or 2) prominently at the top of the screen.
// Phase 2 triggers a pulsing red alert style.

export default function PhaseIndicator({ phase }) {
  const isPhase2 = phase === 2;

  return (
    <div
      className={`
        flex items-center gap-3 px-5 py-2 rounded-full border text-sm font-bold tracking-widest uppercase
        ${isPhase2
          ? "border-red-500 bg-red-950/60 text-red-300 pulse-bright"
          : "border-cyan-700 bg-cyan-950/40 text-cyan-300"
        }
      `}
    >
      {/* Phase icon */}
      <span className={`text-lg ${isPhase2 ? "text-red-400" : "text-cyan-400"}`}>
        {isPhase2 ? "⚠" : "◈"}
      </span>

      <span>Phase {phase}</span>

      {isPhase2 && (
        <span className="text-xs font-normal text-red-400 ml-1">— HQ ALERT</span>
      )}
    </div>
  );
}
