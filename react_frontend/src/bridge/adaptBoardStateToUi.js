import { createInitialGameState } from "../game/turns";
import { degreesToFacing } from "./translation/rotationMapping";

const PLAYER_TWO_ID = 2;
const DEFAULT_UNIT_KIND = "attacker";

/**
 * Merge authoritative board_state from Python/bridge into the React UI game shape.
 * v1: snake_case payload from Python -> existing React UI shape.
 *
 * The UI still uses a prototype-era state shape, so this adapter is the single place
 * where authoritative backend payloads are translated into that frontend structure.
 */
export function adaptBoardStateToUi(raw) {
  const baseState = createInitialGameState();
  if (!isRecord(raw)) return baseState;

  const players = adaptPlayers(raw.players, baseState.players);
  const tokensByOwner = adaptTokensByOwner(raw.units, players);

  return {
    ...baseState,
    turn: numberOr(raw.turn, baseState.turn),
    activePlayer: numberOr(raw.active_player, baseState.activePlayer),
    gameOver: booleanOr(raw.game_over, baseState.gameOver),
    winner: raw.winner ?? null,
    moveCountdown: adaptMoveCountdown(raw.move_countdown, baseState.moveCountdown),
    lastAction:
      typeof raw.last_action === "string" ? raw.last_action : baseState.lastAction,
    players: players.map((player) => ({
      ...player,
      tokens: tokensByOwner.get(player.id) ?? [],
    })),
    // UI `units` is reserved for non-marker board entities. Authoritative `units[]`
    // currently maps to player tokens instead of these transient board units.
    units: baseState.units,
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
      hqName:
        typeof rawPlayer.hq_name === "string" ? rawPlayer.hq_name : basePlayer.hqName,
      resourceName:
        typeof rawPlayer.resource_name === "string"
          ? rawPlayer.resource_name
          : basePlayer.resourceName,
      commandTowerHp: numberOr(rawPlayer.command_tower_hp, basePlayer.commandTowerHp),
      commandTowerMaxHp: numberOr(
        rawPlayer.command_tower_max_hp,
        basePlayer.commandTowerMaxHp
      ),
      commandTowerPosition: adaptNullablePosition(
        rawPlayer.command_tower_position,
        basePlayer.commandTowerPosition
      ),
      tokens: [],
    };
  });
}

function adaptTokensByOwner(rawUnits, players) {
  // Python serializes all units in a flat list; the existing UI expects them nested
  // under each player as token-like objects.
  const tokensByOwner = new Map(players.map((player) => [player.id, []]));
  if (!Array.isArray(rawUnits)) return tokensByOwner;

  for (const unit of rawUnits) {
    if (!isRecord(unit)) continue;

    const owner = unit.owner;
    if (!tokensByOwner.has(owner)) continue;

    tokensByOwner.get(owner).push({
      id: String(unit.id),
      kind: unit.kind ?? DEFAULT_UNIT_KIND,
      themeName: typeof unit.theme_name === "string" ? unit.theme_name : null,
      hp: numberOr(unit.hp, 0),
      maxHp: numberOr(unit.max_hp, numberOr(unit.hp, 0)),
      position: adaptPosition(unit.position),
      rotation: degreesToFacing(unit.rotation_deg ?? 0, zoneForOwner(owner)),
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

function adaptNullablePosition(position, fallback) {
  if (!isRecord(position)) return fallback ?? null;
  return adaptPosition(position);
}

function adaptMoveCountdown(rawCountdown, baseCountdown) {
  if (!isRecord(rawCountdown)) return baseCountdown;

  return {
    active: booleanOr(rawCountdown.active, baseCountdown.active),
    secondsRemaining: numberOr(
      rawCountdown.seconds_remaining,
      baseCountdown.secondsRemaining
    ),
    durationSeconds: numberOr(
      rawCountdown.duration_seconds,
      baseCountdown.durationSeconds
    ),
    unitId:
      typeof rawCountdown.unit_id === "string" || rawCountdown.unit_id == null
        ? rawCountdown.unit_id
        : baseCountdown.unitId,
  };
}

function zoneForOwner(owner) {
  return owner === PLAYER_TWO_ID ? "top" : "bottom";
}

function isRecord(value) {
  return value != null && typeof value === "object";
}

function numberOr(value, fallback) {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function booleanOr(value, fallback) {
  return typeof value === "boolean" ? value : fallback;
}
