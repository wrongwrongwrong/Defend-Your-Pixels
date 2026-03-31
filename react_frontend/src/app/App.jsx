// App.jsx
// Root component. Hosts the game loop (requestAnimationFrame),
// manages unit spawning, movement, combat, and resource collection.
// Passes derived state down to Board and HUD components.

import { useEffect, useRef, useCallback } from "react";
import Board from "../components/board/Board";
import ResourceDisplay from "../components/hud/ResourceDisplay";
import PhaseIndicator from "../components/hud/PhaseIndicator";
import { useWebSocket } from "../hooks/bridge/useWebSocket";
import {
  SPAWN_COOLDOWNS,
  UNIT_STATS,
  getUnitTarget,
  stepToward,
  hasReachedTarget,
  findNearestEnemy,
  shouldTriggerPhase2,
  REWARD_KILL_UNIT,
  REWARD_HQ_HIT,
} from "../game/gameLogic";

let nextUnitId = 1000;

export default function App() {
  const { gameState, setGameState, connected } = useWebSocket();

  const cooldownsRef = useRef({});
  const lastTickRef  = useRef(null);
  const rafRef       = useRef(null);
  const gameOverRef  = useRef(false);
  const elapsedRef   = useRef(0);

  // ── Game loop ──────────────────────────────────────────────────────────────
  const tick = useCallback((timestamp) => {
    if (gameOverRef.current) return;

    const dt = lastTickRef.current ? Math.min(timestamp - lastTickRef.current, 100) : 16;
    lastTickRef.current = timestamp;
    elapsedRef.current += dt;

    setGameState((prev) => {
      if (prev.gameOver) { gameOverRef.current = true; return prev; }

      let hqHP    = prev.hqHP;
      let units   = prev.units.filter((u) => !u.dying || u.dyingTimer > 0);
      let players = prev.players;
      const phase = shouldTriggerPhase2(hqHP, 100, elapsedRef.current) ? 2 : prev.phase;

      // ── 1. Spawn units from tokens ─────────────────────────────────────
      players = players.map((player) => ({
        ...player,
        tokens: player.tokens.map((token) => {
          if (token.type === "def") return token;

          const key = token.id;
          if (cooldownsRef.current[key] === undefined) {
            cooldownsRef.current[key] = SPAWN_COOLDOWNS[token.type];
          }
          cooldownsRef.current[key] -= dt;

          if (cooldownsRef.current[key] <= 0) {
            cooldownsRef.current[key] = SPAWN_COOLDOWNS[token.type];
            const stats = UNIT_STATS[token.type];
            const target = getUnitTarget(token.rotation, player.zone);
            units = [...units, {
              id: nextUnitId++,
              playerId: player.id,
              type: token.type,
              hp: stats.hp, maxHp: stats.maxHp,
              speed: stats.speed, atk: stats.atk, range: stats.range,
              pos: { x: token.position.x + 0.5, y: token.position.y + 0.5 },
              target,
              fighting: false, dying: false, dyingTimer: 0, atkCooldown: 0,
            }];
          }
          return token;
        }),
      }));

      // ── 2. Phase 2: HQ spawns units ────────────────────────────────────
      if (phase === 2) {
        const hqKey = "hq_spawn";
        if (cooldownsRef.current[hqKey] === undefined) cooldownsRef.current[hqKey] = 5000;
        cooldownsRef.current[hqKey] -= dt;
        if (cooldownsRef.current[hqKey] <= 0) {
          cooldownsRef.current[hqKey] = 5000;
          const tgt = Math.random() < 0.5 ? { x: 6, y: 11 } : { x: 6, y: 0 };
          units = [...units, {
            id: nextUnitId++, playerId: 0, type: "infantry",
            hp: 25, maxHp: 25, speed: 1.0, atk: 7, range: 1,
            pos: { x: 6, y: 6 }, target: tgt,
            fighting: false, dying: false, dyingTimer: 0, atkCooldown: 0,
          }];
        }
      }

      // ── 3. Tick dying timers ────────────────────────────────────────────
      units = units.map((u) => u.dying ? { ...u, dyingTimer: u.dyingTimer - dt } : u);

      // ── 4. Move & find combat ───────────────────────────────────────────
      const resourceDeltas = { 1: 0, 2: 0 };

      units = units.map((unit) => {
        if (unit.dying || unit.hp <= 0) return unit;

        const enemy = findNearestEnemy(unit, units);
        if (enemy) {
          const newCd = unit.atkCooldown - dt;
          return {
            ...unit, fighting: true,
            atkCooldown: newCd <= 0 ? 800 : newCd,
            pendingAtk: newCd <= 0 ? enemy.id : unit.pendingAtk,
          };
        }

        const newPos  = stepToward(unit.pos, unit.target, unit.speed, dt);
        const arrived = hasReachedTarget(newPos, unit.target);

        if (arrived) {
          const distToHQ = Math.sqrt((newPos.x - 6) ** 2 + (newPos.y - 6) ** 2);
          if (distToHQ < 1.5) {
            hqHP = Math.max(0, hqHP - unit.atk);
            if (unit.playerId !== 0) resourceDeltas[unit.playerId] = (resourceDeltas[unit.playerId] ?? 0) + REWARD_HQ_HIT;
            return { ...unit, dying: true, dyingTimer: 450, hp: 0 };
          }
          // Hit enemy player zone
          const enemyPlayer = players.find(
            (p) => p.id !== unit.playerId && p.id !== 0 &&
              ((p.zone === "bottom" && unit.target.y >= 10) ||
               (p.zone === "top"    && unit.target.y <= 1))
          );
          if (enemyPlayer) {
            players = players.map((p) =>
              p.id === enemyPlayer.id ? { ...p, hp: Math.max(0, p.hp - unit.atk) } : p
            );
            return { ...unit, dying: true, dyingTimer: 450, hp: 0 };
          }
        }

        return { ...unit, pos: newPos, fighting: false, atkCooldown: Math.max(0, unit.atkCooldown - dt) };
      });

      // ── 5. Apply combat damage ──────────────────────────────────────────
      const pendingMap = {};
      units.forEach((u) => { if (u.pendingAtk) pendingMap[u.pendingAtk] = (pendingMap[u.pendingAtk] ?? 0) + u.atk; });
      units = units.map((u) => ({ ...u, pendingAtk: undefined }));
      units = units.map((u) => {
        const dmg = pendingMap[u.id];
        if (!dmg) return u;
        const newHp = u.hp - dmg;
        if (newHp <= 0) {
          // Credit killer
          const killerUnit = units.find((k) => k.pendingAtk === u.id);
          if (killerUnit && killerUnit.playerId !== u.playerId && killerUnit.playerId !== 0) {
            resourceDeltas[killerUnit.playerId] = (resourceDeltas[killerUnit.playerId] ?? 0) + REWARD_KILL_UNIT;
          }
          return { ...u, hp: 0, dying: true, dyingTimer: 450 };
        }
        return { ...u, hp: newHp };
      });

      // ── 6. Apply resources ──────────────────────────────────────────────
      players = players.map((p) => ({
        ...p,
        resources: p.resources + (resourceDeltas[p.id] ?? 0),
      }));

      const gameOver = hqHP <= 0 || players.some((p) => p.hp <= 0);
      return { ...prev, hqHP, units, players, phase, gameOver };
    });

    rafRef.current = requestAnimationFrame(tick);
  }, [setGameState]);

  useEffect(() => {
    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [tick]);

  // ── Upgrade handler ────────────────────────────────────────────────────────
  const handleUpgrade = useCallback((tokenId, upgradeType) => {
    setGameState((prev) => ({
      ...prev,
      players: prev.players.map((player) => {
        const has = player.tokens.some((t) => t.id === tokenId);
        if (!has || player.resources < 10) return player;
        return {
          ...player,
          resources: player.resources - 10,
          tokens: player.tokens.map((token) => {
            if (token.id !== tokenId) return token;
            if (upgradeType === "damage")   return { ...token, atk: (token.atk ?? 5) + 3 };
            if (upgradeType === "cooldown") {
              cooldownsRef.current[token.id] = Math.max(500, (SPAWN_COOLDOWNS[token.type] ?? 3000) * 0.7);
              return token;
            }
            if (upgradeType === "hp")       return { ...token, hp: token.hp + 20, maxHp: (token.maxHp ?? token.hp) + 20 };
            return token;
          }),
        };
      }),
    }));
  }, [setGameState]);

  const { phase, hqHP, players, gameOver } = gameState;
  const p1 = players.find((p) => p.zone === "bottom");
  const p2 = players.find((p) => p.zone === "top");

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center gap-3 p-4"
      style={{ background: "linear-gradient(160deg, #050a14 0%, #0a0f1e 60%, #080d1a 100%)" }}
    >
      {/* Title */}
      <h1
        className="text-2xl font-bold tracking-widest text-cyan-300 uppercase"
        style={{ textShadow: "0 0 16px rgba(34,211,238,0.5)" }}
      >
        ◈ Pixel Defense
      </h1>

      {/* Connection badge */}
      <div className="flex items-center gap-2 text-xs">
        <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-slate-600"}`} />
        <span className={connected ? "text-green-400" : "text-slate-500"}>
          {connected ? "Connected to backend" : "Running on mock data"}
        </span>
      </div>

      {/* Phase */}
      <PhaseIndicator phase={phase} />

      {/* P2 HUD (top) */}
      {p2 && <ResourceDisplay player={p2} />}

      {/* Board */}
      <div className="relative">
        <Board gameState={gameState} onUpgrade={handleUpgrade} />

        {gameOver && (
          <div className="absolute inset-0 flex flex-col items-center justify-center rounded bg-black/85 z-50">
            <div
              className="text-5xl font-black text-yellow-300 tracking-widest"
              style={{ textShadow: "0 0 30px rgba(234,179,8,0.9)" }}
            >
              GAME OVER
            </div>
            <p className="text-slate-400 text-sm mt-3">
              {hqHP <= 0 ? "HQ has fallen." : "A player base was destroyed."}
            </p>
            <button
              className="mt-4 px-5 py-2 rounded border border-cyan-600 text-cyan-300 text-sm hover:bg-cyan-900/30"
              onClick={() => window.location.reload()}
            >
              Restart
            </button>
          </div>
        )}
      </div>

      {/* P1 HUD (bottom) */}
      {p1 && <ResourceDisplay player={p1} />}

      {/* Legend */}
      <div className="flex gap-4 text-xs text-slate-500 mt-1 flex-wrap justify-center">
        <span>⚔ Infantry — fast, low HP</span>
        <span>🛡 Tank — slow, high HP</span>
        <span>💣 Bomber — AoE, slow cooldown</span>
        <span>🔒 DEF — stationary defender</span>
        <span className="text-yellow-700">| Click token to upgrade (10 ⬡)</span>
      </div>
    </div>
  );
}
