// Connects to Python backend at ws://localhost:8765.
// Merges marker positions into token state. Falls back to mock data if offline.

import { useState, useEffect, useRef, useCallback } from "react";
import { createInitialGameState } from "../../game/turns";

const WS_URL = "ws://localhost:8765";

const mockGameState = createInitialGameState();

/**
 * Merge tracker payload into game state.
 * Accepts tracker_frame (bridge) or legacy game_state shape.
 */
export function useWebSocket() {
  const [gameState, setGameState] = useState(mockGameState);
  const [connected, setConnected] = useState(false);
  const [usingMock, setUsingMock] = useState(true);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const mergeMarkerData = useCallback((data) => {
    if (!data?.markers) return;
    setGameState((prev) => {
      const markerMap = {};
      data.markers.forEach((m) => {
        markerMap[m.id] = m;
      });

      return {
        ...prev,
        players: prev.players.map((player) => ({
          ...player,
          tokens: player.tokens.map((token) => {
            const marker = markerMap[token.id];
            if (!marker) return token;
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
          if (msg.type === "game_state" && msg.data) {
            mergeMarkerData(msg.data);
          } else if (msg.type === "tracker_frame" && msg.data) {
            mergeMarkerData(msg.data);
          }
        } catch {
          // ignore
        }
      };

      ws.onerror = () => {};

      ws.onclose = () => {
        setConnected(false);
        setUsingMock(true);
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

function degreesToRotation(deg, zone) {
  const norm = ((deg % 360) + 360) % 360;
  if (norm < 45 || norm >= 315) return zone === "bottom" ? "forward" : "backward";
  if (norm < 135) return "right";
  if (norm < 225) return zone === "bottom" ? "backward" : "forward";
  return "left";
}
