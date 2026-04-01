// Pitch: Expansion → Contention → Decisive Battle

const PHASE_LABEL = {
  1: "Expansion",
  2: "Contention",
  3: "Decisive battle",
};

export default function PhaseIndicator({ phase }) {
  const isLate = phase >= 3;

  return (
    <div
      className={`
        flex items-center gap-3 px-5 py-2 rounded-full border text-sm font-bold tracking-widest uppercase
        ${isLate
          ? "border-red-500 bg-red-950/60 text-red-300 pulse-bright"
          : "border-cyan-700 bg-cyan-950/40 text-cyan-300"
        }
      `}
    >
      <span className={`text-lg ${isLate ? "text-red-400" : "text-cyan-400"}`}>
        {isLate ? "⚠" : "◈"}
      </span>
      <span>
        Phase {phase} — {PHASE_LABEL[phase] ?? "—"}
      </span>
    </div>
  );
}
