export function normalizeTrackerFrame(payload) {
  if (!payload || typeof payload !== "object") {
    return {
      calibrationReady: false,
      markers: [],
      boardCorners: [],
    };
  }

  const markers = Array.isArray(payload.markers) ? payload.markers : [];
  const boardCorners = Array.isArray(payload.board_corners)
    ? payload.board_corners
    : Array.isArray(payload.boardCorners)
      ? payload.boardCorners
      : [];

  const calibrationReady = Boolean(
    payload.calibration_ready ?? payload.calibrationReady ?? boardCorners.length === 4
  );

  return {
    calibrationReady,
    markers,
    boardCorners,
  };
}
