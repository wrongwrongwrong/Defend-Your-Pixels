// ─── Board grid ────────────────────────────────────────────────────────────────
export const GRID_SIZE  = 12;
export const CELL       = 60;             // pixels per grid cell
export const BOARD_PX   = GRID_SIZE * CELL; // 720 — board width = height

// ─── Canvas layout ─────────────────────────────────────────────────────────────
// [ LEFT PANEL | BOARD (720×720) | RIGHT PANEL ]
// [              TOP BAR (top)                 ]
// [              BOT BAR (bottom)              ]
export const PANEL_W    = 230;            // side panel width (each side)
export const TOP_BAR_H  = 55;            // status bar above board
export const BOT_BAR_H  = 52;            // warning bar below board

export const BOARD_OFF_X = PANEL_W;      // board starts at x = 230
export const BOARD_OFF_Y = TOP_BAR_H;    // board starts at y = 55

export const CANVAS_W   = PANEL_W * 2 + BOARD_PX;  // 1180
export const CANVAS_H   = TOP_BAR_H + BOARD_PX + BOT_BAR_H; // 827

// ─── Board image calibration ──────────────────────────────────────────────────
// If the grid in board1.png doesn't perfectly fill the image edge-to-edge,
// tweak these offsets (in pixels relative to the board image's top-left corner).
// GRID_INSET_* = gap between image edge and first grid line.
// GRID_DRAW_W/H = total pixel span of the playable grid within the image.
export const GRID_INSET_X = 0;
export const GRID_INSET_Y = 0;
export const GRID_DRAW_W  = BOARD_PX;    // change if board image has a border
export const GRID_DRAW_H  = BOARD_PX;

// ─── Direction vectors (8-way compass) ────────────────────────────────────────
export const DIR_VEC = {
  E:  [ 1,  0], SE: [ 1,  1], S:  [ 0,  1], SW: [-1,  1],
  W:  [-1,  0], NW: [-1, -1], N:  [ 0, -1], NE: [ 1, -1],
};
export const ARROW_CHAR = {
  E: '→', SE: '↘', S: '↓', SW: '↙',
  W: '←', NW: '↖', N: '↑', NE: '↗',
};

// ─── Colour palette ────────────────────────────────────────────────────────────
export const COLORS = {
  bg:              0x0f0c08,

  // ── Side panels ──────────────────────────────────────────────────────────────
  panelBg:         0x16100a,    // inactive panel background
  panelBorderDim:  0x3a2810,    // inactive panel border
  p1PanelActive:   0x2a1c0c,    // Mick panel lit up (warm amber tint)
  p1BorderActive:  0xd4a030,    // Mick active border (gold)
  p2PanelActive:   0x0a1e0e,    // Emu panel lit up (cool green tint)
  p2BorderActive:  0x52c840,    // Emu active border (bright green)

  // ── Player name text ─────────────────────────────────────────────────────────
  p1NameActive:    0xffd060,    // gold when it's Mick's turn
  p1NameDim:       0x7a5820,    // dimmed otherwise
  p2NameActive:    0x72ef52,    // bright green when it's Emu's turn
  p2NameDim:       0x2a7220,    // dimmed otherwise

  // ── Board overlays ───────────────────────────────────────────────────────────
  gridLine:        0xffffff,    // white grid lines (drawn at low alpha)
  diagonal:        0xd49020,    // dividing diagonal line
  p1Active:        0xd4a828,    // wheat paddock active cells (golden)
  p2Active:        0x48aa3a,    // feeding ground active cells (green)
  terrainHard:     0x3e2e1a,    // hard terrain fill
  terrainSoft:     0x6e5030,    // soft terrain fill
  destroyed:       0x5a3010,    // scorched/destroyed cell
  destroyedX:      0x1a0800,    // × mark on destroyed cell
  attackRay:       0xcc1010,    // attack ray path — dark red, clearly visible
  attackRayHit:    0xff3300,    // attack ray terminal hit — bright red

  // ── Score bars ───────────────────────────────────────────────────────────────
  scoreBarBg:      0x251509,
  scoreBarFill1:   0xd4a030,    // Mick's progress bar
  scoreBarFill2:   0x50c840,    // Emu's progress bar

  // ── Top / bottom bars ────────────────────────────────────────────────────────
  topBarBg:        0x0e0a06,
  botBarBg:        0x0c0804,
  warnText:        0xf0b870,
  okText:          0x80c868,
};

// ─── Fonts ─────────────────────────────────────────────────────────────────────
// Loaded via Google Fonts in index.html.
// Change these strings if you swap the font in the <link> tag.
export const FONT_TITLE  = "'Special Elite', serif";       // dramatic headers
export const FONT_LABEL  = "'Oswald', sans-serif";         // bold labels / numbers
export const FONT_MONO   = "'Share Tech Mono', monospace"; // coordinates / tech info
