// Central board marker: mid-field / conflict zone (not a single shared HP bar)

export default function HQ({ cellSize }) {
  const size = cellSize * 2;

  return (
    <div
      className="absolute flex flex-col items-center justify-center rounded border-2 z-10 border-amber-700/60 glow-gold pointer-events-none"
      style={{
        width: size,
        height: size,
        left: 5 * cellSize,
        top: 5 * cellSize,
        background: "rgba(20, 15, 5, 0.75)",
      }}
    >
      <span className="text-amber-200 font-bold text-[10px] tracking-widest text-center px-1">
        MID-FIELD
      </span>
      <span className="text-slate-500 text-[9px] mt-0.5">Ether drills / contest</span>
    </div>
  );
}
