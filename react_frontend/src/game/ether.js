/**
 * Ether economy — same resource name as pitch / model_backend PlayerState.ether
 * Pure helpers: pass `players` array, get updated array back.
 */

/**
 * @returns {{ ok: boolean, players: typeof players }}
 */
export function trySpendEther(players, playerId, cost) {
  if (cost <= 0) return { ok: true, players };
  const p = players.find((x) => x.id === playerId);
  if (!p || p.ether < cost) return { ok: false, players };
  return {
    ok: true,
    players: players.map((x) =>
      x.id === playerId ? { ...x, ether: x.ether - cost } : x
    ),
  };
}
