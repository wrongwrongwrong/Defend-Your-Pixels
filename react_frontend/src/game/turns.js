import { DEFAULT_INCOME_PER_TURN, PLAYER_ID } from "./constants";

/**
 * Pitch: Expansion → Contention → Decisive Battle (coarse mapping by turn).
 */
export function phaseForTurn(turn) {
  if (turn <= 4) return 1;
  if (turn <= 10) return 2;
  return 3;
}

/**
 * Create initial UI game state (turn-based prototype).
 * `units` reserved for later grid combat; keep [] for now.
 */
export function createInitialGameState() {
  return {
    turn: 1,
    activePlayer: PLAYER_ID.P1,
    phase: 1,
    players: [
      {
        id: PLAYER_ID.P1,
        color: "blue",
        zone: "bottom",
        ether: 10,
        incomePerTurn: DEFAULT_INCOME_PER_TURN,
        commandTowerHp: 20,
        commandTowerMaxHp: 20,
        tokens: [
          {
            id: 10,
            kind: "attacker",
            hp: 30,
            maxHp: 30,
            position: { x: 3, y: 10 },
            rotation: "forward",
          },
          {
            id: 11,
            kind: "defender",
            hp: 40,
            maxHp: 40,
            position: { x: 8, y: 10 },
            rotation: "forward",
          },
        ],
      },
      {
        id: PLAYER_ID.P2,
        color: "red",
        zone: "top",
        ether: 10,
        incomePerTurn: DEFAULT_INCOME_PER_TURN,
        commandTowerHp: 20,
        commandTowerMaxHp: 20,
        tokens: [
          {
            id: 14,
            kind: "attacker",
            hp: 30,
            maxHp: 30,
            position: { x: 3, y: 1 },
            rotation: "forward",
          },
          {
            id: 15,
            kind: "defender",
            hp: 40,
            maxHp: 40,
            position: { x: 8, y: 1 },
            rotation: "forward",
          },
        ],
      },
    ],
    units: [],
    gameOver: false,
  };
}

/**
 * End active player's turn; switch sides and grant Ether income to the
 * player who is now active (same order as model_backend GameState.end_turn → start_turn).
 */
export function endTurn(state) {
  if (state.gameOver) return state;

  const nextPlayer =
    state.activePlayer === PLAYER_ID.P1 ? PLAYER_ID.P2 : PLAYER_ID.P1;
  const turn = state.turn + 1;

  const players = state.players.map((p) => {
    if (p.id !== nextPlayer) return p;
    const gain = p.incomePerTurn ?? 0;
    return { ...p, ether: p.ether + gain };
  });

  const phase = phaseForTurn(turn);

  const gameOver = players.some((p) => p.commandTowerHp <= 0);

  return {
    ...state,
    activePlayer: nextPlayer,
    turn,
    phase,
    players,
    gameOver,
  };
}
