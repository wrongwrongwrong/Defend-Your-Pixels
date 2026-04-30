// ─── Board layout ─────────────────────────────────────────────────────────────
export const GRID_SIZE   = 12;
export const CELL        = 50;
export const BOARD_OFF_X = 50;
export const BOARD_OFF_Y = 72;   // below turn banner

export const CANVAS_W = BOARD_OFF_X * 2 + GRID_SIZE * CELL;  // 700
export const CANVAS_H = 940;

export const LOG_Y      = BOARD_OFF_Y + GRID_SIZE * CELL + 18;
export const BUTTON_Y   = CANVAS_H - 52;

// ─── Colour palette (ported from prototype3) ──────────────────────────────────
export const COLORS = {
  bg:               0x1a120a,
  // Territory base (inactive ground)
  p1Base:           0xa86030,   // red dirt paddock ground
  p2Base:           0x3a6040,   // dry scrubland
  // Active cells (the shootable/resource tiles)
  p1Active:         0xd4a828,   // wheat paddock — golden
  p1ActiveAlt:      0xc89c22,
  p2Active:         0x5ab050,   // emu feeding ground — lush green
  p2ActiveAlt:      0x4ea044,
  gridLine:         0x00000033,
  diagonal:         0x1e0e04,
  diagonalTick:     0x120a02,
  p1Token:          0x7a1818,   // farmer deep red
  p2Token:          0x1a5020,   // emu deep green
  defenseZone:      0xe8d060,
  defenseZoneBorder:0xd4a820,
  attackRay:        0xe8c030,
  attackRayHit:     0xff6020,
  terrainHard:      0x3e2e1a,
  terrainSoft:      0x6e4e28,
  terrainSoftDmg:   0x9a6a38,
  destroyed:        0x6a3818,   // scorched/raided cell
  destroyedX:       0x180800,
  hitFlash:         0xff3300,
  shielded:         0x60e8a0,
  turnBanner:       0x6b4410,
  turnBannerText:   0xfff0d0,
  logBg:            0x120c06,
  logCard:          0x1e1509,
  logCardBorder:    0x3a2810,
  btnMain:          0x2a1c0e,
  btnBorder:        0x5a3e1e,
  btnText:          0xf0e0c0,
  hiddenBase:       0x8a6040,
  uiText:           0xf0e0c0,
  uiTextDim:        0x8a7060,

  // Resource tiers (extra — for varied target values)
  resource1:        0xd4a828,
  resource2:        0xe6b830,
  resource3:        0xf0c840,
  resourceStronghold: 0xff8030,
};

// ─── Theme strings ────────────────────────────────────────────────────────────
export const PLAYER_NAMES  = { 1: "Old Mick",  2: "The Mob" };
export const SIDE_NAMES    = { 1: "Farmer Side", 2: "Emu Side" };
export const TERRITORY_NAMES = { 1: "Wheat Paddock", 2: "Feeding Ground" };
export const TOKEN_NAMES   = {
  p1_attack_a: "KEITH A",   p1_attack_b: "KEITH B",   p1_defense: "OLD MICK",
  p2_attack_a: "MOB A",     p2_attack_b: "MOB B",     p2_defense: "CASSOWARY",
};
export const TERRAIN_NAMES = {
  p1_hard: "Fence",    p1_soft: "Scarecrow",
  p2_hard: "Termite",  p2_soft: "Spinifex",
};

// ─── Direction vectors (8-way compass) ────────────────────────────────────────
export const DIR_VEC = {
  E:  [ 1,  0], SE: [ 1,  1], S:  [ 0,  1], SW: [-1,  1],
  W:  [-1,  0], NW: [-1, -1], N:  [ 0, -1], NE: [ 1, -1],
};

export const ARROW_CHAR = {
  E: '→', SE: '↘', S: '↓', SW: '↙',
  W: '←', NW: '↖', N: '↑', NE: '↗',
};
