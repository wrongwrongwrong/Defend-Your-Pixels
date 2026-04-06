import { normalizeTrackerFrame } from "./normalizeTrackerFrame";
import { degreesToFacing } from "./rotationMapping";
import { buildTokenRegistry } from "./tokenRegistry";


export function translateTrackerFrame(payload, gameState) {
  const frame = normalizeTrackerFrame(payload);
  const registry = buildTokenRegistry(gameState);

  const trackedTokens = frame.markers
    .map((marker) => {
      const meta = registry.get(String(marker.id));
      if (!meta) return null;
      const rotationDeg = marker.rotation ?? 0;
      return {
        markerId: marker.id,
        tokenId: meta.tokenId,
        playerId: meta.playerId,
        zone: meta.zone,
        kind: meta.kind,
        position: marker.position,
        rotationDeg,
        facing: degreesToFacing(rotationDeg, meta.zone),
        tracked: true,
      };
    })
    .filter(Boolean);

  return {
    calibrationReady: frame.calibrationReady,
    boardCorners: frame.boardCorners,
    trackedTokens,
  };
}


export function applyTrackedTokens(gameState, translation) {
  if (!translation?.trackedTokens?.length) {
    return {
      ...gameState,
      trackerCalibrationReady: translation?.calibrationReady ?? false,
      trackerBoardCorners: translation?.boardCorners ?? [],
    };
  }

  const trackedById = new Map(
    translation.trackedTokens.map((token) => [String(token.tokenId), token])
  );

  return {
    ...gameState,
    trackerCalibrationReady: translation.calibrationReady,
    trackerBoardCorners: translation.boardCorners,
    players: gameState.players.map((player) => ({
      ...player,
      tokens: player.tokens.map((token) => {
        const tracked = trackedById.get(String(token.id));
        if (!tracked) return token;
        return {
          ...token,
          position: tracked.position ?? token.position,
          rotation: tracked.facing ?? token.rotation,
          tracked: tracked.tracked,
        };
      }),
    })),
  };
}
