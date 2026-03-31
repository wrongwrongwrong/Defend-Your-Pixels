// useWebSocket.js
// Connects to the Python/OpenCV backend at ws://localhost:8765.
// Falls back to mock data automatically when no connection is available.

import { useState, useEffect, useRef, useCallback } from "react";

const WS_URL = "ws://localhost:8765";

const mockGameState = {
  phase: 1,
  hqHP: 100,
  players: [
    {
      id: 1,
      color: "blue",
      zone: "bottom",
      resources: 0,
      hp: 100,
      tokens: [
        { id: 10, type: "infantry", hp: 50, maxHp: 50, position: { x: 2, y: 10 }, rotation: "forward" },
        { id: 11, type: "tank",     hp: 80, maxHp: 80, position: { x: 5, y: 10 }, rotation: "forward" },
        { id: 12, type: "bomber",   hp: 60, maxHp: 60, position: { x: 8, y: 10 }, rotation: "forward" },
        { id: 13, type: "def",      hp: 100, maxHp: 100, position: { x: 5, y: 11 }, rotation: "forward" },
      ],
    },
    {
      id: 2,
      color: "red",
      zone: "top",
      resources: 0,
      hp: 100,
      tokens: [
        { id: 14, type: "infantry", hp: 50, maxHp: 50, position: { x: 2, y: 1 }, rotation: "forward" },
        { id: 15, type: "tank",     hp: 80, maxHp: 80, position: { x: 5, y: 1 }, rotation: "forward" },
        { id: 16, type: "bomber",   hp: 60, maxHp: 60, position: { x: 8, y: 1 }, rotation: "forward" },
        { id: 17, type: "def",      hp: 100, maxHp: 100, position: { x: 5, y: 0 }, rotation: "forward" },
      ],
    },
  ],
  units: [],
};

/**
 * useWebSocket
 * Returns { gameState, connected, usingMock }
 * Merges incoming marker positions from Python into the base game state.
 */
export function useWebSocket() {
  const [gameState, setGameState] = useState(mockGameState);
  const [connected, setConnected] = useState(false);
  const [usingMock, setUsingMock] = useState(true);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  // Merge Python marker data into game state (updates token positions/rotations)
  const mergeMarkerData = useCallback((data) => {
    if (!data?.markers) return;
    setGameState((prev) => {
      const markerMap = {};
      data.markers.forEach((m) => { markerMap[m.id] = m; });

      return {
        ...prev,
        players: prev.players.map((player) => ({
          ...player,
          tokens: player.tokens.map((token) => {
            const marker = markerMap[token.id];
            if (!marker) return token;
            // Map raw rotation degrees → rotation string
            const rotDeg = marker.rotation ?? 0;
            const rotation = degreesToRotation(rotDeg, player.zone);
            return {
              ...token,
              position: marker.position ?? token.position,
              rotation,
            };
          }),
        })),
      };
    });
  }, []);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setUsingMock(false);
        if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "game_state") {
            mergeMarkerData(msg.data);
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onerror = () => {
        // silently fall through to onclose
      };

      ws.onclose = () => {
        setConnected(false);
        setUsingMock(true);
        // Attempt reconnect every 5 s
        reconnectTimer.current = setTimeout(connect, 5000);
      };
    } catch {
      setUsingMock(true);
      reconnectTimer.current = setTimeout(connect, 5000);
    }
  }, [mergeMarkerData]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  return { gameState, setGameState, connected, usingMock };
}

// ─── helpers ────────────────────────────────────────────────────────────────

/**
 * Convert ArUco marker rotation (degrees, 0 = up in camera view)
 * into a game rotation string relative to the player's zone.
 */
function degreesToRotation(deg, zone) {
  const norm = ((deg % 360) + 360) % 360;
  // Bucket into 4 quadrants
  if (norm < 45 || norm >= 315) return zone === "bottom" ? "forward" : "backward";
  if (norm < 135) return "right";
  if (norm < 225) return zone === "bottom" ? "backward" : "forward";
  return "left";
}
