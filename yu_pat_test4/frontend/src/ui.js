/**
 * ui.js — HTML panel updater.
 *
 * Subscribes to WSClient and reflects every state change into the DOM.
 * Phaser does NOT touch any of these elements.
 *
 * New panel layout (matching screenshot):
 *   score block · token cards (atk_a, atk_b, def, nuke) · player name
 *
 * New mechanics reflected here:
 *   • Per-token kill count + 2-star upgrade system
 *   • Defense "protecting" count + 2-star upgrade at ≤12 cells
 *   • Nuke card: locked → pulsing-ready when player has ≤12 active cells
 *   • Bottom bar: hint text during turn, attack result for 10 s after resolve
 */

// ─── Constants ────────────────────────────────────────────────────────────────

const UPGRADE_1 = 5;
const UPGRADE_2 = 8;
const ACTIVE_TOTAL = 24;

// ─── Helpers ──────────────────────────────────────────────────────────────────

function pad2(n) { return String(Math.max(0, n ?? 0)).padStart(2, "0"); }

function upgradeLevel(kills) {
  if (kills >= UPGRADE_2) return 2;
  if (kills >= UPGRADE_1) return 1;
  return 0;
}

function upgradeFill(kills) {
  const lvl = upgradeLevel(kills);
  if (lvl === 0) return kills / UPGRADE_1;
  if (lvl === 1) return (kills - UPGRADE_1) / (UPGRADE_2 - UPGRADE_1);
  return 1.0;
}

function starsHTML(filled, total = 2) {
  return "★".repeat(filled) + "☆".repeat(total - filled);
}

function el(id) { return document.getElementById(id); }

// ─── Panel state update ───────────────────────────────────────────────────────

function onState(s) {
  if (!s) return;
  const p1         = s.p1      || {};
  const p2         = s.p2      || {};
  const battle     = s.battle  || {};
  const activeSide = battle.active_side ?? null;

  // ── Score blocks ───────────────────────────────────────────────────────────
  const rem1 = p1.active_remaining ?? ACTIVE_TOTAL;
  const rem2 = p2.active_remaining ?? ACTIVE_TOTAL;
  _setScore("p1", rem1, ACTIVE_TOTAL);
  _setScore("p2", rem2, ACTIVE_TOTAL);

  // ── Token cards ────────────────────────────────────────────────────────────
  _setAttackCard("p1", "atk_a", p1.atk_a, activeSide === "p1");
  _setAttackCard("p1", "atk_b", p1.atk_b, activeSide === "p1");
  _setAttackCard("p2", "atk_a", p2.atk_a, activeSide === "p2");
  _setAttackCard("p2", "atk_b", p2.atk_b, activeSide === "p2");

  _setDefCard("p1", p1.def, rem1);
  _setDefCard("p2", p2.def, rem2);

  _setNukeCard("p1", p1.nuke_available ?? false, p1.nuke_used ?? false, activeSide === "p1");
  _setNukeCard("p2", p2.nuke_available ?? false, p2.nuke_used ?? false, activeSide === "p2");

  // ── Panel active glow ──────────────────────────────────────────────────────
  el("panel-left") ?.classList.toggle("active-p1", activeSide === "p1");
  el("panel-right")?.classList.toggle("active-p2", activeSide === "p2");

  // ── Bottom bar hint ────────────────────────────────────────────────────────
  if (!_resultTimerActive) {
    _updateHint(activeSide, p1, p2);
  }
}

// ── Score ──────────────────────────────────────────────────────────────────────

function _setScore(side, remaining, total) {
  const scoreEl = el(`${side}-score`);
  const barEl   = el(`${side}-score-bar`);
  if (scoreEl) {
    scoreEl.innerHTML = `${remaining}<span class="score-denom">/${total}</span>`;
  }
  if (barEl) {
    // Bar fills as cells are LOST (damage indicator)
    const pct = Math.min(100, ((total - remaining) / total) * 100);
    barEl.style.width = `${pct.toFixed(1)}%`;
  }
}

// ── Attack token card ──────────────────────────────────────────────────────────

function _setAttackCard(side, role, tok, isActive) {
  const kills    = tok?.kills ?? 0;
  const level    = upgradeLevel(kills);
  const fill     = upgradeFill(kills);

  const numEl    = el(`${side}-num-${role}`);
  const starsEl  = el(`${side}-stars-${role}`);
  const fillEl   = el(`${side}-fill-${role}`);

  if (numEl)   numEl.textContent   = pad2(kills);
  if (starsEl) starsEl.textContent = starsHTML(level);
  if (fillEl)  fillEl.style.height = `${(fill * 100).toFixed(1)}%`;
}

// ── Defense card ──────────────────────────────────────────────────────────────

function _setDefCard(side, def, activeRemaining) {
  const protecting = def?.protecting ?? 0;
  const upgrade    = def?.upgrade    ?? 0;   // 0 = 1 star, 1 = 2 stars (glowing)
  const fillPct    = def?.upgrade_fill ?? 0;

  const numEl   = el(`${side}-num-def`);
  const starsEl = el(`${side}-stars-def`);
  const fillEl  = el(`${side}-fill-def`);
  const cardEl  = el(`${side}-card-def`);

  if (numEl)   numEl.textContent   = pad2(protecting);
  if (starsEl) starsEl.textContent = starsHTML(1 + upgrade);  // starts at 1
  if (fillEl)  fillEl.style.height = `${(fillPct * 100).toFixed(1)}%`;

  // Glow when fully upgraded (2nd star)
  if (cardEl) {
    cardEl.classList.toggle("def-maxed", upgrade >= 1);
  }
}

// ── Nuke card ──────────────────────────────────────────────────────────────────

function _setNukeCard(side, available, used, isActiveSide) {
  const cardEl   = el(`${side}-card-nuke`);
  const statusEl = el(`${side}-nuke-status`);
  if (!cardEl || !statusEl) return;

  const pulsing = available && isActiveSide && !used;
  cardEl.classList.toggle("nuke-ready", pulsing);

  if (used) {
    statusEl.textContent = "USED";
  } else if (available) {
    statusEl.textContent = isActiveSide ? "ARMED" : "READY";
  } else {
    statusEl.textContent = "LOCKED";
  }
}

// ─── Bottom bar ───────────────────────────────────────────────────────────────

let _resultTimerActive = false;
let _resultTimer       = null;
let _lastActiveSide    = null;
let _lastP1 = {};
let _lastP2 = {};
let _wsConnected       = false;   // tracks live WebSocket state

function _updateHint(activeSide, p1, p2) {
  _lastActiveSide = activeSide;
  _lastP1 = p1;
  _lastP2 = p2;

  const bar     = el("notif-bar");
  const textEl  = el("notif-text");
  if (!bar || !textEl) return;

  bar.className = activeSide === "p1" ? "notif-bar turn-p1"
                : activeSide === "p2" ? "notif-bar turn-p2"
                : "notif-bar";

  if (!activeSide) {
    textEl.textContent = _wsConnected ? "CONNECTED — READY TO PLAY" : "Waiting for server…";
    return;
  }

  const toks = activeSide === "p1" ? p1 : p2;
  const hints = [];

  for (const role of ["atk_a", "atk_b"]) {
    const tok   = toks?.[role];
    const kills = tok?.kills ?? 0;
    const level = upgradeLevel(kills);
    const label = role === "atk_a" ? "Token A" : "Token B";

    if (level === 0) {
      const need = UPGRADE_1 - kills;
      hints.push(`${label}: ${need} more hit${need !== 1 ? "s" : ""} to upgrade`);
    } else if (level === 1) {
      const need = UPGRADE_2 - kills;
      hints.push(`${label}: ${need} more hit${need !== 1 ? "s" : ""} to max`);
    } else {
      hints.push(`${label}: MAX`);
    }
  }

  textEl.textContent = hints.join("   ·   ");
}

function _showAttackResult(text, side) {
  clearTimeout(_resultTimer);
  _resultTimerActive = true;

  const bar    = el("notif-bar");
  const textEl = el("notif-text");
  if (!bar || !textEl) return;

  bar.className    = `notif-bar result-${side}`;
  textEl.textContent = text;

  _resultTimer = setTimeout(() => {
    _resultTimerActive = false;
    _updateHint(_lastActiveSide, _lastP1, _lastP2);
  }, 10_000);
}

// ─── Event handling ───────────────────────────────────────────────────────────

function onEvents(events) {
  for (const ev of events) {
    if (ev.type === "attack_result") {
      const byLabel = ev.by === "p1" ? "OLD MICK" : "THE MOB";
      const count   = ev.successful ?? 0;
      _showAttackResult(
        `${count} SUCCESSFUL ATTACK${count !== 1 ? "S" : ""} BY ${byLabel}`,
        ev.by,
      );
      break;  // only one attack_result per resolve
    }
  }
}

// ─── Public init ──────────────────────────────────────────────────────────────

export function initUI(ws) {
  ws.on("connected", () => {
    _wsConnected = true;
    // Update bar immediately so it doesn't flicker before first state arrives
    if (!_resultTimerActive) {
      _updateHint(_lastActiveSide, _lastP1, _lastP2);
    }
  });

  ws.on("state",  onState);
  ws.on("events", onEvents);

  ws.on("disconnected", () => {
    _wsConnected = false;
    const t = el("notif-text");
    if (t) t.textContent = "Disconnected — reconnecting…";
    el("notif-bar")?.classList.remove("turn-p1","turn-p2","result-p1","result-p2");
  });
}
