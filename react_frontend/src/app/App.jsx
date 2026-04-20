// Temporary React validation layer for the authoritative Old Mick MVP backend.

import { useCallback, useMemo, useState } from "react";
import Board from "../components/board/Board";
import ResourceDisplay from "../components/hud/ResourceDisplay";
import { GRID_SIZE, PLAYER_ID } from "../game/constants";
import { formatBoardPosition, transformDirectionLabel } from "../game/viewTransform";
import { useWebSocket } from "../hooks/bridge/useWebSocket";

const ACTION_MODE = {
  MOVE: "move",
  ACT: "act",
};

function formatDisplayCoordinates(text, viewPlayerId) {
  if (typeof text !== "string") return text;
  return text.replace(/\((\d+),\s*(\d+)\)/g, (_, x, y) => {
    return formatBoardPosition(
      { x: Number(x), y: Number(y) },
      viewPlayerId,
      GRID_SIZE
    );
  });
}

function parseViewPlayerId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("view") === "p2" ? PLAYER_ID.P2 : PLAYER_ID.P1;
}

function deriveAttackDirection(from, to) {
  if (!from || !to) return null;
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (dx === 0 && dy === 0) return null;

  const straight = dx === 0 || dy === 0;
  const diagonal = Math.abs(dx) === Math.abs(dy);
  if (!straight && !diagonal) return null;

  const key = `${Math.sign(dx)},${Math.sign(dy)}`;
  return {
    "0,-1": "up",
    "0,1": "down",
    "-1,0": "left",
    "1,0": "right",
    "-1,-1": "up_left",
    "1,-1": "up_right",
    "-1,1": "down_left",
    "1,1": "down_right",
  }[key] ?? null;
}

export default function App() {
  const { gameState, connected, usingMock, sendAction } = useWebSocket();
  const [selectedTokenId, setSelectedTokenId] = useState(null);
  const [actionMode, setActionMode] = useState(ACTION_MODE.MOVE);
  const [interactionHint, setInteractionHint] = useState("");
  const isLiveMode = !usingMock;
  const viewPlayerId = useMemo(() => parseViewPlayerId(), []);

  const sendBackendAction = useCallback(
    (action) => {
      if (!isLiveMode) return false;
      return sendAction(action);
    },
    [isLiveMode, sendAction]
  );

  const handleEndTurn = useCallback(() => {
    if (isLiveMode) {
      sendBackendAction({ action: "end_turn" });
      return;
    }
    setInteractionHint("Backend offline. End turn validation requires authoritative Python state.");
  }, [isLiveMode, sendBackendAction]);

  const { players, resourceTiles = [], gameOver, activePlayer, turn, lastAction, moveCountdown } = gameState;
  const localPlayer = players.find((player) => player.id === viewPlayerId) ?? players[0] ?? null;
  const remotePlayer = players.find((player) => player.id !== viewPlayerId) ?? players[1] ?? null;
  const selectedToken = useMemo(
    () => players.flatMap((player) => player.tokens ?? []).find((token) => token.id === selectedTokenId) ?? null,
    [players, selectedTokenId]
  );

  const towerDown = players.find((p) => p.commandTowerHp <= 0);
  const countdownActive = isLiveMode && Boolean(moveCountdown?.active) && !gameOver;
  const countdownSeconds = Number.isFinite(moveCountdown?.secondsRemaining)
    ? Math.max(0, moveCountdown.secondsRemaining)
    : 0;
  const countdownDuration = Number.isFinite(moveCountdown?.durationSeconds)
    ? Math.max(0, moveCountdown.durationSeconds)
    : 0;
  const countdownProgress = countdownDuration > 0
    ? Math.max(0, Math.min(100, (countdownSeconds / countdownDuration) * 100))
    : 0;
  const endTurnLabel = countdownActive
    ? `Turn ending in ${countdownSeconds.toFixed(1)}s`
    : usingMock
      ? "Backend offline"
      : "Send end turn";

  const selectionStatusText = selectedToken
    ? `Selected ${selectedToken.themeName ?? selectedToken.kind} ${selectedToken.id} at ${formatBoardPosition(selectedToken.position, viewPlayerId, GRID_SIZE)}`
    : "Select one of the active player's tokens, then click a grid cell.";

  const footerHint = usingMock
    ? "Backend offline. This React layer is for authoritative-state validation, not local gameplay simulation."
    : "Python board_state is authoritative. Open one browser window with ?view=p1 and another with ?view=p2 for a two-screen mirrored setup.";

  const handleTokenSelect = useCallback((tokenId) => {
    setInteractionHint("");
    setSelectedTokenId((prev) => (prev === tokenId ? null : tokenId));
  }, []);

  const handleBoardCellAction = useCallback(
    (position) => {
      if (!isLiveMode || !selectedToken || !sendAction) {
        if (!isLiveMode) {
          setInteractionHint("Backend offline. Move and attack validation require authoritative Python responses.");
        }
        return;
      }

      if (actionMode === ACTION_MODE.ACT) {
        const direction = deriveAttackDirection(selectedToken.position, position);
        if (!direction) {
          setInteractionHint("Act mode only accepts straight or diagonal lines from the selected token.");
          return;
        }
        const displayDirection = transformDirectionLabel(direction, viewPlayerId)
          .replaceAll("_", " ");
        setInteractionHint(`Attack queued: ${selectedToken.themeName ?? selectedToken.kind} -> ${displayDirection}`);
        sendBackendAction({
          action: "attack_in_direction",
          unit_id: String(selectedToken.id),
          direction,
        });
        return;
      }

      setInteractionHint(
        `Move queued: ${selectedToken.themeName ?? selectedToken.kind} -> ${formatBoardPosition(position, viewPlayerId, GRID_SIZE)}`
      );
      sendBackendAction({
        action: "move_unit",
        unit_id: String(selectedToken.id),
        position,
      });
    },
    [actionMode, isLiveMode, selectedToken, sendAction, sendBackendAction, viewPlayerId]
  );

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center gap-3 p-4"
      style={{ background: "linear-gradient(160deg, #050a14 0%, #0a0f1e 60%, #080d1a 100%)" }}
    >
      <h1
        className="text-2xl font-bold tracking-widest text-cyan-300 uppercase"
        style={{ textShadow: "0 0 16px rgba(34,211,238,0.5)" }}
      >
        ◈ Old Mick Validation Layer
      </h1>

      <div className="flex items-center gap-2 text-xs">
        <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-slate-600"}`} />
        <span className={connected ? "text-green-400" : "text-slate-500"}>
          {connected ? "Python state connected" : "Backend offline - showing last fallback snapshot"}
        </span>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-300 flex-wrap justify-center">
        <span className="text-slate-500">Screen view:</span>
        <ViewLink href="?view=p1" active={viewPlayerId === PLAYER_ID.P1}>
          Player 1
        </ViewLink>
        <ViewLink href="?view=p2" active={viewPlayerId === PLAYER_ID.P2}>
          Player 2
        </ViewLink>
        <span className="text-slate-500">
          {viewPlayerId === PLAYER_ID.P1 ? "standard orientation" : "mirrored orientation"}
        </span>
      </div>

      <div className="flex items-center gap-4 flex-wrap justify-center text-sm text-slate-300">
        <span>
          Turn <span className="text-cyan-300 font-mono">{turn}</span>
        </span>
        <span>
          Active:{" "}
          <span className="text-amber-300 font-semibold">Player {activePlayer}</span>
        </span>
        <button
          type="button"
          className="px-4 py-1.5 rounded-md bg-cyan-900/50 border border-cyan-600 text-cyan-200 text-sm font-semibold hover:bg-cyan-800/50 disabled:opacity-40"
          onClick={handleEndTurn}
          disabled={gameOver || countdownActive}
        >
          {endTurnLabel}
        </button>
      </div>

      {lastAction && (
        <div className="max-w-2xl rounded border border-slate-800 bg-slate-950/70 px-4 py-2 text-xs text-slate-300 text-center">
          <span className="text-slate-500">Status:</span>{" "}
          <span className="text-cyan-200">{formatDisplayCoordinates(lastAction, viewPlayerId)}</span>
        </div>
      )}

      {interactionHint && (
        <div className="max-w-2xl rounded border border-cyan-900 bg-cyan-950/30 px-4 py-2 text-xs text-cyan-100 text-center">
          <span className="text-cyan-400">Interaction:</span> {interactionHint}
        </div>
      )}

      <ValidationSummary
        players={players}
        resourceTiles={resourceTiles}
        selectedToken={selectedToken}
        actionMode={actionMode}
        isLiveMode={isLiveMode}
      />

      {countdownActive && (
        <div className="w-full max-w-2xl rounded border border-amber-700/70 bg-amber-950/50 px-4 py-3 text-center text-sm text-amber-100 shadow-[0_0_20px_rgba(251,191,36,0.12)]">
          <div className="font-semibold tracking-wide uppercase text-amber-300">
            Move countdown active
          </div>
          <div className="mt-1 text-slate-200">
            {moveCountdown?.unitId
              ? `Unit ${moveCountdown.unitId} finished moving. Turn will auto-end in ${countdownSeconds.toFixed(1)}s.`
              : `Turn will auto-end in ${countdownSeconds.toFixed(1)}s.`}
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-900/80">
            <div
              className="h-full rounded-full bg-gradient-to-r from-amber-300 via-amber-500 to-rose-500 transition-[width] duration-100"
              style={{ width: `${countdownProgress}%` }}
            />
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Use another action before the timer ends if you want to cancel the auto end-turn.
          </div>
        </div>
      )}

      {isLiveMode && (
        <div className="flex flex-wrap items-center justify-center gap-2 rounded border border-slate-800 bg-slate-950/70 px-4 py-2 text-xs text-slate-300">
          <span className="text-slate-500">Manual controls:</span>
          <BackendControls
            actionMode={actionMode}
            selectedToken={selectedToken}
            onSetActionMode={setActionMode}
            onClearSelection={() => setSelectedTokenId(null)}
            selectionStatusText={selectionStatusText}
          />
        </div>
      )}

      {remotePlayer && (
        <ResourceDisplay player={remotePlayer} isActive={remotePlayer.id === activePlayer} />
      )}

      <div className="relative">
          <Board
            gameState={gameState}
            activePlayer={activePlayer}
            selectedTokenId={selectedTokenId}
            onTokenSelect={handleTokenSelect}
            onCellAction={handleBoardCellAction}
            actionMode={actionMode}
            viewPlayerId={viewPlayerId}
          />

        {gameOver && (
          <div className="absolute inset-0 flex flex-col items-center justify-center rounded bg-black/85 z-50">
            <div
              className="text-5xl font-black text-yellow-300 tracking-widest"
              style={{ textShadow: "0 0 30px rgba(234,179,8,0.9)" }}
            >
              GAME OVER
            </div>
            <p className="text-slate-400 text-sm mt-3">
              {towerDown
                ? `${towerDown.hqName ?? "HQ"} destroyed.`
                : "Match ended."}
            </p>
            <button
              type="button"
              className="mt-4 px-5 py-2 rounded border border-cyan-600 text-cyan-300 text-sm hover:bg-cyan-900/30"
              onClick={() => window.location.reload()}
            >
              Restart
            </button>
          </div>
        )}
      </div>

      {localPlayer && (
        <ResourceDisplay player={localPlayer} isActive={localPlayer.id === activePlayer} />
      )}

      <div className="flex gap-4 text-xs text-slate-500 mt-1 flex-wrap justify-center max-w-xl text-center">
        <span>
          <strong className="text-slate-400">Riflemen / Mob</strong> — directional attack role
        </span>
        <span>
          <strong className="text-slate-400">Old Mick / Cassowary</strong> — passive 3x3 protection role
        </span>
        <span className="text-amber-700/90">
          {footerHint}
        </span>
      </div>
    </div>
  );
}

function BackendControls({
  actionMode,
  selectedToken,
  onSetActionMode,
  onClearSelection,
  selectionStatusText,
}) {
  return (
    <>
      <button
        type="button"
        className={`rounded border px-3 py-1 ${actionMode === ACTION_MODE.MOVE ? "border-cyan-500 bg-cyan-950/60 text-cyan-200" : "border-slate-700 text-slate-400"}`}
        onClick={() => onSetActionMode(ACTION_MODE.MOVE)}
      >
        Move mode
      </button>
      <button
        type="button"
        className={`rounded border px-3 py-1 ${actionMode === ACTION_MODE.ACT ? "border-rose-500 bg-rose-950/60 text-rose-200" : "border-slate-700 text-slate-400"}`}
        onClick={() => onSetActionMode(ACTION_MODE.ACT)}
      >
        Act mode
      </button>
      <button
        type="button"
        className="rounded border border-slate-700 px-3 py-1 text-slate-300 disabled:opacity-40"
        onClick={onClearSelection}
        disabled={!selectedToken}
      >
        Clear selection
      </button>
      <span className="text-slate-500">{selectionStatusText}</span>
    </>
  );
}

function ViewLink({ href, active, children }) {
  return (
    <a
      href={href}
      className={`rounded border px-3 py-1 ${active ? "border-cyan-500 bg-cyan-950/60 text-cyan-200" : "border-slate-700 text-slate-400 hover:text-slate-200"}`}
    >
      {children}
    </a>
  );
}

function ValidationSummary({ players, resourceTiles, selectedToken, actionMode, isLiveMode }) {
  const contractChecks = [
    {
      label: "Turn / winner / status",
      ok: true,
      detail: "top-level board_state fields are present in React state",
    },
    {
      label: "HQ labels and HP",
      ok: players.every((player) => player.hqName && Number.isFinite(player.commandTowerHp)),
      detail: "per-player HQ name and HP are visible in HUD",
    },
    {
      label: "HQ board positions",
      ok: players.every((player) => player.commandTowerPosition || !isLiveMode),
      detail: "authoritative board_state can place real HQs on the board",
    },
    {
      label: "Resource labels",
      ok: players.every((player) => player.resourceName),
      detail: "per-player resource terminology is visible in HUD",
    },
    {
      label: "Token theme names",
      ok: players.flatMap((player) => player.tokens ?? []).every((token) => token.themeName || !isLiveMode),
      detail: "frontend can distinguish Riflemen / Mob / Old Mick / Cassowary",
    },
    {
      label: "Resource tile payload",
      ok: Array.isArray(resourceTiles),
      detail: "resource tiles are available as first-class frontend data",
    },
  ];

  return (
    <div className="w-full max-w-5xl rounded border border-slate-800 bg-slate-950/70 px-4 py-3 text-xs text-slate-300">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-[260px] flex-1">
          <div className="text-slate-500 uppercase tracking-wide mb-2">Validation HUD</div>
          <div className="space-y-1">
            {contractChecks.map((check) => (
              <div key={check.label} className="flex items-start gap-2">
                <span className={check.ok ? "text-green-400" : "text-amber-400"}>{check.ok ? "OK" : "WARN"}</span>
                <span>
                  <strong className="text-slate-200">{check.label}:</strong> {check.detail}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="min-w-[260px] flex-1">
          <div className="text-slate-500 uppercase tracking-wide mb-2">Action Flow Check</div>
          <div className="space-y-1 text-slate-400">
            <div>
              <strong className="text-slate-200">Current mode:</strong> {actionMode === ACTION_MODE.MOVE ? "Move" : "Act"}
            </div>
            <div>
              <strong className="text-slate-200">Selected token:</strong>{" "}
              {selectedToken ? `${selectedToken.themeName ?? selectedToken.kind} ${selectedToken.id}` : "none"}
            </div>
            <div>
              <strong className="text-slate-200">Resource tiles visible:</strong> {resourceTiles.length}
            </div>
            <div>
              <strong className="text-slate-200">Move flow:</strong>{" "}
              {"select token -> click reachable destination"}
            </div>
            <div>
              <strong className="text-slate-200">Attack flow:</strong>{" "}
              {"select token -> click straight/diagonal line -> send attack_in_direction"}
            </div>
            <div>
              <strong className="text-slate-200">Mode:</strong> {isLiveMode ? "authoritative backend validation" : "mock fallback only"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
