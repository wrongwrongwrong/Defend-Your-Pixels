export function normalizeTrackerFrame(payload) {
  if (!payload || typeof payload !== "object") {
    return {
      markers: [],
    };
  }

  const markers = Array.isArray(payload.markers) ? payload.markers : [];

  return {
    markers,
  };
}
