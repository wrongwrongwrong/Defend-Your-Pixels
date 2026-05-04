/**
 * Layout, color, and game constants for Old Mick Against the Mob.
 * @module constants
 */

// ═══════════════════════════════════════════════════════════════════
//  LAYOUT CONSTANTS
// ═══════════════════════════════════════════════════════════════════
export const CELL   = 52;          // px per grid cell
export const COLS   = 12;
export const ROWS   = 12;
export const BX     = 38;          // board top-left X (leaves room for row labels)
export const BY     = 58;          // board top-left Y (leaves room for col labels + title)
export const PANEL_X = BX + COLS * CELL + 14;   // right panel start X
export const PW      = 210;        // panel width
export const W       = PANEL_X + PW + 8;        // total canvas width
export const H       = BY + ROWS * CELL + 28;   // total canvas height

// ═══════════════════════════════════════════════════════════════════
//  COLOUR PALETTE  (Old Mick / Emu War theme)
// ═══════════════════════════════════════════════════════════════════
export const C = {
  farmer_cell : 0xe8c890,   // pale wheat (safe / non-target, washed out)
  emu_cell    : 0xb8d090,   // pale sage (safe / non-target, washed out)
  p1_target   : 0xc84818,   // vivid dark orange — P1 resource cells
  p2_target   : 0x0f4a10,   // deep forest green — P2 resource cells
  fence_cell  : 0xe8d068,   // golden fence line
  board_bg    : 0x2a1e0e,   // dark earth background
  panel_bg    : 0x1e1408,   // panel background
  panel_border: 0x6a4a20,

  // ATK tokens
  p1_atk : 0xe06820,        // farmer orange-brown
  p2_atk : 0x2a8a20,        // emu green

  // DEF tokens
  p1_def : 0x905020,        // Old Mick dark brown
  p2_def : 0x1a6010,        // Cassowary dark green

  // Token borders
  p1_border : 0xf8e090,     // warm yellow
  p2_border : 0xb8ee60,     // bright green

  // Terrain
  hard_fill   : 0x706050,
  hard_border : 0xb0a080,
  soft_fill   : 0xc0d060,
  soft_border : 0xe0f080,

  // Rays
  ray_path    : 0x44ff88,   // green dashes
  ray_blocked : 0xff2200,   // red X (hard terrain stops)
  ray_soft    : 0xff9900,   // orange triangle (soft terrain hit)
  ray_hit     : 0xff4400,   // explosion (enemy token hit)

  // Defense zone
  p1_zone : 0xf8c040,
  p2_zone : 0x44cc20,

  // Phase bar
  phase_terrain : 0x3060c0,
  phase_battle  : 0xb03010,
};

// ═══════════════════════════════════════════════════════════════════
//  RAY DIRECTION VECTORS  (direction string → [dcol, drow])
// ═══════════════════════════════════════════════════════════════════
export const DIR_VEC = {
  E  : [ 1,  0],
  SE : [ 1,  1],
  S  : [ 0,  1],
  SW : [-1,  1],
  W  : [-1,  0],
  NW : [-1, -1],
  N  : [ 0, -1],
  NE : [ 1, -1],
};

// Unicode arrow characters
export const ARROW_CHAR = {
  E: '→', SE: '↘', S: '↓', SW: '↙',
  W: '←', NW: '↖', N: '↑', NE: '↗',
};

// ═══════════════════════════════════════════════════════════════════
//  TUTORIAL CONSTANTS
// ═══════════════════════════════════════════════════════════════════
export const TUTORIAL_TARGETS = {
  p1AtkStart: { col: 3, row: 3 },  // D4
  p1DefSpot:  { col: 1, row: 1 },  // B2
};

// ═══════════════════════════════════════════════════════════════════
//  LABELS AND MESSAGES
// ═══════════════════════════════════════════════════════════════════
export const PHASE_LABEL = {
  scan: 'Board Scan',
  side_selection: 'Choose First HQ Side',
  hq_placement: 'Hidden HQ Placement',
  game: 'Battle',
};

export const SIDE_LABEL = {
  p1: 'Old Mick',
  p2: 'The Mob',
  old_mick: 'Old Mick',
  mob: 'The Mob',
};

// ═══════════════════════════════════════════════════════════════════
//  ERROR HANDLING
// ═══════════════════════════════════════════════════════════════════
export const ERROR_PRIORITY = [
  'camera_unavailable',
  'marker_map_scan_failed',
  'token_detection_failed',
  'inactive_side_token_changed',
  'hq_wrong_side',
  'old_mick_token_invalid_zone',
  'mob_token_invalid_zone',
  'old_mick_attack_direction_invalid',
  'mob_attack_direction_invalid',
  'hq_setup_complete',
];

export const ERROR_TITLE = {
  camera_unavailable: 'Camera Unavailable',
  marker_map_scan_failed: 'Board Scan Failed',
  token_detection_failed: 'Token Detection Failed',
  inactive_side_token_changed: 'Wrong Turn Movement',
  hq_wrong_side: 'Invalid HQ Placement',
  old_mick_token_invalid_zone: 'Old Mick Position Invalid',
  mob_token_invalid_zone: 'Mob Position Invalid',
  old_mick_attack_direction_invalid: 'Old Mick Aim Invalid',
  mob_attack_direction_invalid: 'Mob Aim Invalid',
  hq_setup_complete: 'HQ Setup Complete',
};

export const ERROR_MESSAGE_OVERRIDE = {
  inactive_side_token_changed: 'Only the active player may move this turn. Opponent movement was ignored.',
  hq_setup_complete: 'Both HQs are locked in. Battle setup is complete.',
};

// ═══════════════════════════════════════════════════════════════════
//  TIMING CONSTANTS
// ═══════════════════════════════════════════════════════════════════
export const WARNING_SHOW_MS = 1800;
export const WARNING_REPEAT_GAP_MS = 900;
export const WARNING_RECENT_MS = 3600;
