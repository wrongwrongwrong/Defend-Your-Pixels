// Connects to Python backend at ws://localhost:8765.
// Merges marker positions into token state. Falls back to mock data if offline.

import { useState, useEffect, useRef, useCallback } from "react";
import {
  applyTrackedTokens,
  translateTrackerFrame,
} from "../../bridge/translation/translateTrackerFrame";
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
    setGameState((prev) => {
      const translation = translateTrackerFrame(data, prev);
      return applyTrackedTokens(prev, translation);
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
