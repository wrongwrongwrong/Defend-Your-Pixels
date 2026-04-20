import { PLAYER_ID } from "./constants";

/**
 * Create initial UI fallback state for the Old Mick MVP validation layer.
 * This snapshot is only used when authoritative backend state is unavailable and should
 * mirror the current MVP contract shape as closely as possible.
 */
export function createInitialGameState() {
  return {
    turn: 1,
    activePlayer: PLAYER_ID.P1,
    moveCountdown: {
      active: false,
      secondsRemaining: 0,
      durationSeconds: 0,
      unitId: null,
    },
    players: [
      {
        id: PLAYER_ID.P1,
        color: "blue",
        zone: "bottom",
        hqName: "Homestead",
        resourceName: "Wheat Paddock",
        ether: 0,
        incomePerTurn: 0,
        commandTowerHp: 20,
        commandTowerMaxHp: 20,
        commandTowerPosition: null,
        tokens: [
          {
            id: 10,
            kind: "attacker",
            themeName: "Riflemen",
            hp: 3,
            maxHp: 3,
            position: { x: 3, y: 10 },
            rotation: "forward",
          },
          {
            id: 11,
            kind: "defender",
            themeName: "Old Mick",
            hp: 3,
            maxHp: 3,
            position: { x: 8, y: 10 },
            rotation: "forward",
          },
        ],
      },
      {
        id: PLAYER_ID.P2,
        color: "red",
        zone: "top",
        hqName: "Nest",
        resourceName: "Feeding Ground",
        ether: 0,
        incomePerTurn: 0,
        commandTowerHp: 20,
        commandTowerMaxHp: 20,
        commandTowerPosition: null,
        tokens: [
          {
            id: 14,
            kind: "attacker",
            themeName: "Mob",
            hp: 3,
            maxHp: 3,
            position: { x: 3, y: 1 },
            rotation: "forward",
          },
          {
            id: 15,
            kind: "defender",
            themeName: "Cassowary",
            hp: 3,
            maxHp: 3,
            position: { x: 8, y: 1 },
            rotation: "forward",
          },
        ],
      },
    ],
    resourceTiles: [],
    units: [],
    gameOver: false,
  };
}
