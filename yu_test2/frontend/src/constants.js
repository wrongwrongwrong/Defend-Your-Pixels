export const GRID_SIZE = 12;
export const CELL = 52;
export const BOARD_OFF_X = 38;
export const BOARD_OFF_Y = 58;
export const CANVAS_W = 894;
export const CANVAS_H = 880;

export const COLORS = {
  p1Base: 0xe8c890,
  p2Base: 0xb8d090,
  gridLine: 0x6a4a20,
  diagonal: 0xe8d068,
  diagonalTick: 0xb89030,
  p1Active: 0xc84818,
  p1ActiveAlt: 0xe06820,
  p2Active: 0x0f4a10,
  p2ActiveAlt: 0x2a8a20,
  resourceStronghold: 0x6d4db3,
  terrainHard: 0x706050,
  terrainSoft: 0xc0d060,
  destroyed: 0x0a0603,
  destroyedX: 0x802010,
  attackRay: 0x44ff88,
  attackRayHit: 0xff4400,
  turnBanner: 0x2a1208,
  btnBorder: 0x6a4a20,
};

export const DIR_VEC = {
  E: [1, 0],
  SE: [1, 1],
  S: [0, 1],
  SW: [-1, 1],
  W: [-1, 0],
  NW: [-1, -1],
  N: [0, -1],
  NE: [1, -1],
};

export const ARROW_CHAR = {
  E: ">",
  SE: "\\",
  S: "v",
  SW: "/",
  W: "<",
  NW: "/",
  N: "^",
  NE: "\\",
};
