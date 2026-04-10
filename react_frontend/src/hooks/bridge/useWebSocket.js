// Connects to Python backend at ws://localhost:8765.
// - board_state: authoritative snapshot → replace UI state (after adaptBoardStateToUi).
// - tracker_frame / game_state (legacy): marker calibration + positions → merge into current state.
// Falls back to mock data if offline.

import { useState, useEffect, useRef, useCallback } from "react";
import { adaptBoardStateToUi } from "../../bridge/adaptBoardStateToUi";
import {
  applyTrackedTokens,
  translateTrackerFrame,
} from "../../bridge/translation/translateTrackerFrame";
import { createInitialGameState } from "../../game/turns";

const WS_URL = "ws://localhost:8765";
const RECONNECT_DELAY_MS = 5000;

const initialMockGameState = createInitialGameState();

function parseSocketMessage(rawMessage) {
  try {
    return JSON.parse(rawMessage);
  } catch {
    return null;
  }
}

function scheduleReconnect(reconnectTimerRef, connect) {
  reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
}

/**
 * Merge tracker payload into game state (positions / facing only).
 * Accepts tracker_frame (bridge) or legacy game_state shape (same merge semantics).
 */
export function useWebSocket() {
  const [gameState, setGameState] = useState(initialMockGameState);
  const [connected, setConnected] = useState(false);
  const [usingMock, setUsingMock] = useState(true);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const applyAuthoritativeBoardState = useCallback((data) => {
    setGameState(adaptBoardStateToUi(data));
  }, []);

  const mergeMarkerData = useCallback((data) => {
    setGameState((prev) => {
      const translation = translateTrackerFrame(data, prev);
      return applyTrackedTokens(prev, translation);
    });
  }, []);

  const sendAction = useCallback((action) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;

    ws.send(
      JSON.stringify({
        type: "action",
        data: action,
      })
    );
    return true;
  }, []);

  const handleSocketMessage = useCallback(
    (rawMessage) => {
      const message = parseSocketMessage(rawMessage);
      if (!message) return;

      if (message.type === "board_state" && message.data != null) {
        applyAuthoritativeBoardState(message.data);
        return;
      }

      if (
        (message.type === "game_state" || message.type === "tracker_frame") &&
        message.data
      ) {
        mergeMarkerData(message.data);
      }
    },
    [applyAuthoritativeBoardState, mergeMarkerData]
  );

  useEffect(() => {
    function connect() {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          setConnected(true);
          setUsingMock(false);
          if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
        };

        ws.onmessage = (event) => {
          handleSocketMessage(event.data);
        };

        ws.onerror = () => {};

        ws.onclose = () => {
          setConnected(false);
          setUsingMock(true);
          scheduleReconnect(reconnectTimer, connect);
        };
      } catch {
        setUsingMock(true);
        scheduleReconnect(reconnectTimer, connect);
      }
    }

    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [handleSocketMessage]);

  return { gameState, setGameState, connected, usingMock, sendAction };
}
