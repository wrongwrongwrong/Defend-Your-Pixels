// Connects to Python backend at ws://localhost:8765.
// - board_state: authoritative snapshot → replace UI state (after adaptBoardStateToUi).
// - tracker_frame: marker positions / facing → merge into current state.
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

export function useWebSocket() {
  const [gameState, setGameState] = useState(initialMockGameState);
  const [connected, setConnected] = useState(false);
  const [usingMock, setUsingMock] = useState(true);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const applyAuthoritativeBoardState = useCallback((data) => {
    // board_state replaces the UI snapshot wholesale because Python is authoritative.
    setGameState(adaptBoardStateToUi(data));
  }, []);

  const mergeMarkerData = useCallback((data) => {
    // tracker_frame is only telemetry, so merge it on top of the current board_state.
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

      if (message.type === "tracker_frame" && message.data) {
        mergeMarkerData(message.data);
      }
    },
    [applyAuthoritativeBoardState, mergeMarkerData]
  );

  useEffect(() => {
    let reconnectTimeout = null;

    function connect() {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          setConnected(true);
          setUsingMock(false);
          if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
            reconnectTimeout = null;
          }
          reconnectTimer.current = null;
        };

        ws.onmessage = (event) => {
          handleSocketMessage(event.data);
        };

        ws.onerror = () => {};

        ws.onclose = () => {
          // Drop back to mock mode when the backend disappears, then keep retrying.
          setConnected(false);
          setUsingMock(true);
          scheduleReconnect(reconnectTimer, connect);
          reconnectTimeout = reconnectTimer.current;
        };
      } catch {
        setUsingMock(true);
        scheduleReconnect(reconnectTimer, connect);
        reconnectTimeout = reconnectTimer.current;
      }
    }

    connect();
    return () => {
      // Close any active socket and cancel the pending reconnect when unmounting.
      const ws = wsRef.current;
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [handleSocketMessage]);

  return { gameState, setGameState, connected, usingMock, sendAction };
}
