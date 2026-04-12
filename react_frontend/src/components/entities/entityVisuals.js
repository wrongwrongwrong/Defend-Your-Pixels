export const KIND_ICONS = {
  attacker: "◎",
  defender: "▣",
};

export function getEntityVisuals(playerColorOrId) {
  const isBlue = playerColorOrId === "blue" || playerColorOrId === 1;
  return {
    isBlue,
    accent: isBlue ? "#3b82f6" : "#ef4444",
    glowClass: isBlue ? "glow-blue" : "glow-red",
    tokenBorderColor: isBlue ? "border-blue-500" : "border-red-500",
    unitBorderColor: isBlue ? "border-blue-400" : "border-red-400",
    tokenBackground: isBlue ? "rgba(10,20,60,0.9)" : "rgba(60,10,10,0.9)",
    unitBackground: isBlue ? "rgba(10,20,80,0.88)" : "rgba(80,10,10,0.88)",
  };
}
