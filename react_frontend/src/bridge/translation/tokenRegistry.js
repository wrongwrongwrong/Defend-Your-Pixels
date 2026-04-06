function inferTokenKind(markerId) {
  if ([10, 12, 14, 16].includes(markerId)) return "attacker";
  if ([11, 13, 15, 17].includes(markerId)) return "defender";
  return null;
}


export function buildTokenRegistry(gameState) {
  const registry = new Map();

  for (const player of gameState?.players ?? []) {
    for (const token of player.tokens ?? []) {
      const tokenId = String(token.id);
      registry.set(tokenId, {
        tokenId,
        playerId: player.id,
        zone: player.zone,
        kind: token.kind,
      });
    }
  }

  for (const markerId of [10, 11, 12, 13, 14, 15, 16, 17]) {
    const tokenId = String(markerId);
    if (registry.has(tokenId)) continue;
    const playerId = markerId >= 14 ? 2 : 1;
    registry.set(tokenId, {
      tokenId,
      playerId,
      zone: playerId === 1 ? "bottom" : "top",
      kind: inferTokenKind(markerId),
    });
  }

  return registry;
}
