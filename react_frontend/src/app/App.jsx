// Turn-based shell aligned with model_backend + pitch: Ether, Command Tower, Attacker/Defender tokens.

import { useCallback, useMemo, useState } from "react";
import Board from "../components/board/Board";
import ResourceDisplay from "../components/hud/ResourceDisplay";
import PhaseIndicator from "../components/hud/PhaseIndicator";
import { useWebSocket } from "../hooks/bridge/useWebSocket";
import { endTurn, trySpendEther } from "../game/gameLogic";

const ACTION_MODE = {
  MOVE: "move",
  ACT: "act",
};

function formatDisplayCoordinates(text) {
  if (typeof text !== "string") return text;
  return text.replace(/\((\d+),\s*(\d+)\)/g, (_, x, y) => {
    return `(${Number(x) + 1}, ${Number(y) + 1})`;
  });
}

export default function App() {
  const { gameState, setGameState, connected, usingMock, sendAction } = useWebSocket();
  const [selectedTokenId, setSelectedTokenId] = useState(null);
  const [actionMode, setActionMode] = useState(ACTION_MODE.MOVE);
  const isLiveMode = !usingMock;

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
    setGameState((prev) => endTurn(prev));
  }, [isLiveMode, sendBackendAction, setGameState]);

  const handleUpgrade = useCallback(
    (tokenId, upgradeType) => {
      if (isLiveMode) return;
      setGameState((prev) => {
        const pid = prev.activePlayer;
        const owns = prev.players.some(
          (p) => p.id === pid && p.tokens.some((t) => t.id === tokenId)
        );
        if (!owns) return prev;

        const { ok, players: afterSpend } = trySpendEther(prev.players, pid, 5);
        if (!ok) return prev;

        const players = afterSpend.map((player) => {
          if (player.id !== pid) return player;
          return {
            ...player,
            tokens: player.tokens.map((token) => {
              if (token.id !== tokenId) return token;
              if (upgradeType === "damage" && token.kind === "attacker") {
                return { ...token, atkBonus: (token.atkBonus ?? 0) + 2 };
              }
              if (upgradeType === "heatVent" && token.kind === "attacker") {
                return { ...token, heatVent: true };
              }
              if (upgradeType === "shield" && token.kind === "defender") {
                return { ...token, shieldBonus: (token.shieldBonus ?? 0) + 1 };
              }
              if (upgradeType === "hp") {
                return {
                  ...token,
                  maxHp: (token.maxHp ?? 40) + 10,
                  hp: (token.hp ?? 40) + 10,
                };
              }
              return token;
            }),
          };
        });

        return { ...prev, players };
      });
    },
    [isLiveMode, setGameState]
  );

  const { phase, players, gameOver, activePlayer, turn, lastAction, moveCountdown } = gameState;
  const p1 = players.find((p) => p.zone === "bottom");
  const p2 = players.find((p) => p.zone === "top");
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
      ? "End turn"
      : "Send end turn";

  const selectionStatusText = selectedToken
    ? `Selected ${selectedToken.kind} ${selectedToken.id} at (${selectedToken.position.x + 1}, ${selectedToken.position.y + 1})`
    : "Select one of the active player's tokens, then click a grid cell.";

  const footerHint = usingMock
    ? "End turn -> next player gains Ether (incomePerTurn). Upgrades cost 5 ether (your turn, your token)."
    : "Python board_state is authoritative. Select a token, choose move/act mode, then click a grid cell.";

  const handleTokenSelect = useCallback((tokenId) => {
    setSelectedTokenId((prev) => (prev === tokenId ? null : tokenId));
  }, []);

  const handleBoardCellAction = useCallback(
    (position) => {
      if (!isLiveMode || !selectedToken || !sendAction) return;

      if (actionMode === ACTION_MODE.ACT) {
        sendBackendAction({
          action: "act_on_target",
          unit_id: String(selectedToken.id),
          target: position,
        });
        return;
      }

      sendBackendAction({
        action: "move_unit",
        unit_id: String(selectedToken.id),
        position,
      });
    },
    [actionMode, isLiveMode, selectedToken, sendAction, sendBackendAction]
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
        ◈ Pixel Defense
      </h1>

      <div className="flex items-center gap-2 text-xs">
        <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-slate-600"}`} />
        <span className={connected ? "text-green-400" : "text-slate-500"}>
          {connected ? "Python state connected" : "Mock board (no backend)"}
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
          <span className="text-cyan-200">{formatDisplayCoordinates(lastAction)}</span>
        </div>
      )}

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

      <PhaseIndicator phase={phase} />

      {p2 && (
        <ResourceDisplay player={p2} isActive={p2.id === activePlayer} />
      )}

      <div className="relative">
        <Board
          gameState={gameState}
          onUpgrade={handleUpgrade}
          activePlayer={activePlayer}
          upgradesEnabled={usingMock}
          selectedTokenId={selectedTokenId}
          onTokenSelect={handleTokenSelect}
          onCellAction={handleBoardCellAction}
          actionMode={actionMode}
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
                ? `Player ${towerDown.id} Command Tower destroyed.`
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

      {p1 && (
        <ResourceDisplay player={p1} isActive={p1.id === activePlayer} />
      )}

      <div className="flex gap-4 text-xs text-slate-500 mt-1 flex-wrap justify-center max-w-xl text-center">
        <span>
          <strong className="text-slate-400">Attacker</strong> — offensive marker
        </span>
        <span>
          <strong className="text-slate-400">Defender</strong> — area denial / shield role
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
        className="rounded border border-amber-700 px-3 py-1 text-amber-200 opacity-40"
        disabled
        title="Capture is not implemented in the Python prototype yet"
      >
        Capture
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
