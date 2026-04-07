export function degreesToFacing(deg, zone) {
  const norm = ((deg % 360) + 360) % 360;
  if (norm < 45 || norm >= 315) return zone === "bottom" ? "forward" : "backward";
  if (norm < 135) return "right";
  if (norm < 225) return zone === "bottom" ? "backward" : "forward";
  return "left";
}
