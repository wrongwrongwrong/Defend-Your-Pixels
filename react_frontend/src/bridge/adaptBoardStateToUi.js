import { createInitialGameState } from "../game/turns";
import { degreesToFacing } from "./translation/rotationMapping";

/**
 * Merge authoritative board_state from Python/bridge into the React UI game shape.
 * v1: snake_case payload from Python -> existing React UI shape.
 */
export function adaptBoardStateToUi(raw) {
  const base = createInitialGameState();
  if (!raw || typeof raw !== "object") return base;

  const players = adaptPlayers(raw.players, base.players);
  const tokensByOwner = adaptTokensByOwner(raw.units, players);

  return {
    ...base,
    turn: numberOr(raw.turn, base.turn),
    activePlayer: numberOr(raw.active_player, base.activePlayer),
    phase: base.phase,
    gameOver: booleanOr(raw.game_over, base.gameOver),
    winner: raw.winner ?? null,
    lastAction: typeof raw.last_action === "string" ? raw.last_action : base.lastAction,
    players: players.map((player) => ({
      ...player,
      tokens: tokensByOwner.get(player.id) ?? [],
    })),
    // UI `units` is reserved for non-marker board entities. Authoritative `units[]`
    // currently maps to player tokens instead of these transient board units.
    units: base.units,
  };
}

function adaptPlayers(rawPlayers, basePlayers) {
  if (!Array.isArray(rawPlayers)) return basePlayers;

  const incomingById = new Map(
    rawPlayers
      .filter((player) => player && typeof player === "object")
      .map((player) => [player.id, player])
  );

  return basePlayers.map((basePlayer) => {
    const rawPlayer = incomingById.get(basePlayer.id);
    if (!rawPlayer) {
      return {
        ...basePlayer,
        tokens: [],
      };
    }

    return {
      ...basePlayer,
      ether: numberOr(rawPlayer.ether, basePlayer.ether),
      incomePerTurn: numberOr(rawPlayer.income_per_turn, basePlayer.incomePerTurn),
      commandTowerHp: numberOr(rawPlayer.command_tower_hp, basePlayer.commandTowerHp),
      commandTowerMaxHp: numberOr(
        rawPlayer.command_tower_max_hp,
        basePlayer.commandTowerMaxHp
      ),
      tokens: [],
    };
  });
}

function adaptTokensByOwner(rawUnits, players) {
  const tokensByOwner = new Map(players.map((player) => [player.id, []]));
  if (!Array.isArray(rawUnits)) return tokensByOwner;

  for (const unit of rawUnits) {
    if (!unit || typeof unit !== "object") continue;
    const owner = unit.owner;
    if (!tokensByOwner.has(owner)) continue;

    tokensByOwner.get(owner).push({
      id: String(unit.id),
      kind: unit.kind ?? "attacker",
      hp: numberOr(unit.hp, 0),
      maxHp: numberOr(unit.max_hp, numberOr(unit.hp, 0)),
      position: adaptPosition(unit.position),
      rotation: degreesToFacing(unit.rotation_deg ?? 0, owner === 2 ? "top" : "bottom"),
    });
  }

  return tokensByOwner;
}

function adaptPosition(position) {
  return {
    x: numberOr(position?.x, 0),
    y: numberOr(position?.y, 0),
  };
}

function numberOr(value, fallback) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function booleanOr(value, fallback) {
  return typeof value === "boolean" ? value : fallback;
}
