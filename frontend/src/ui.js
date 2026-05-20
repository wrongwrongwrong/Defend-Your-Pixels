/**
 * ui.js — HTML panel updater for Prototype 4.
 * Subscribes to WSClient and reflects every state change into the DOM.
 */

const UPGRADE_1 = 4;
const UPGRADE_2 = 8;
const ACTIVE_TOTAL = 24;

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

function countProtectedResources(side, def, state, defTier) {
  if (!def || def.col == null || def.row == null) return 0;
  const resources = state.terrain?.[`${side}_resources`] || [];
  const destroyed = new Set((state.game?.destroyed || []).map(([c, r]) => `${c},${r}`));
  const consumed = new Set();
  const anchor = state.game?.def_anchor_cells?.[side];
  if (Array.isArray(anchor) && anchor[0] === def.col && anchor[1] === def.row) {
    for (const cell of state.game?.def_consumed_cells?.[side] || []) {
      consumed.add(`${cell[0]},${cell[1]}`);
    }
  }
  const radius = defTier >= 1 ? 2 : 1;
  return resources.filter((resource) => {
    const key = `${resource.col},${resource.row}`;
    return !destroyed.has(key)
      && !consumed.has(key)
      && Math.abs(resource.col - def.col) <= radius
      && Math.abs(resource.row - def.row) <= radius;
  }).length;
}

// ─── State update ─────────────────────────────────────────────────────────────

function onState(s) {
  if (!s) return;
  _updateModeOverlay(s);
  _setHelpVisible(!!s.help_visible);
  const p1         = s.p1      || {};
  const p2         = s.p2      || {};
  const game       = s.game    || {};
  const battle     = s.battle  || {};
  const activeSide = battle.active_side ?? null;

  const total = game.resource_cell_total ?? ACTIVE_TOTAL;
  const rem1 = game.score_p1_remaining_cells ?? total;
  const rem2 = game.score_p2_remaining_cells ?? total;
  _setScore("p1", rem1, total);
  _setScore("p2", rem2, total);

  _setAttackCard("p1", "atk_a", game, activeSide === "p1");
  _setAttackCard("p1", "atk_b", game, activeSide === "p1");
  _setAttackCard("p2", "atk_a", game, activeSide === "p2");
  _setAttackCard("p2", "atk_b", game, activeSide === "p2");

  _setDefCard("p1", p1.def, rem1, total, game.def_tier_p1 ?? 0, s);
  _setDefCard("p2", p2.def, rem2, total, game.def_tier_p2 ?? 0, s);

  _setNukeCard("p1", game.nuke_available_p1 ?? false, game.nuke_used_p1 ?? false, activeSide === "p1");
  _setNukeCard("p2", game.nuke_available_p2 ?? false, game.nuke_used_p2 ?? false, activeSide === "p2");

  el("panel-left") ?.classList.toggle("active-p1", activeSide === "p1");
  el("panel-right")?.classList.toggle("active-p2", activeSide === "p2");
  el("panel-left") ?.classList.toggle("tutorial-highlight", s.tutorial?.highlight_sidebar === "left");
  el("panel-right")?.classList.toggle("tutorial-highlight", s.tutorial?.highlight_sidebar === "right");

  if (!_resultTimerActive) {
    _updateStatus(s, activeSide, game);
  }
}

// ─── Help overlay (how-to-play) ───────────────────────────────────────────────

const HELP_IFRAME_SRC = "how-to-play/index.html";

let _helpRoot = null;
let _helpUserClosed = false;
let _helpWasVisible = false;
let _helpMessageBound = false;

function _bindHelpMessageListener() {
  if (_helpMessageBound) return;
  _helpMessageBound = true;
  window.addEventListener("message", (event) => {
    if (event.data === "closeHowToPlay") {
      _helpUserClosed = true;
      if (_helpRoot) _helpRoot.style.display = "none";
    }
  });
}

function _ensureHelpPopup() {
  if (_helpRoot) return _helpRoot;

  _bindHelpMessageListener();

  _helpRoot = document.createElement("div");
  _helpRoot.id = "help-overlay-root";
  _helpRoot.style.cssText =
    "position:fixed;inset:0;width:100%;height:100%;z-index:1200;display:none;";

  const iframe = document.createElement("iframe");
  iframe.src = HELP_IFRAME_SRC;
  iframe.title = "How to Play";
  iframe.style.cssText = "width:100%;height:100%;border:0;display:block;";

  _helpRoot.appendChild(iframe);
  document.body.appendChild(_helpRoot);
  return _helpRoot;
}

function _setHelpVisible(visible) {
  const root = _ensureHelpPopup();
  if (visible && !_helpWasVisible) {
    _helpUserClosed = false;
  }
  _helpWasVisible = visible;

  if (visible && !_helpUserClosed) {
    root.style.display = "block";
  } else if (!visible) {
    root.style.display = "none";
    _helpUserClosed = false;
  }
}

function _updateModeOverlay(state) {
  const overlay = el("mode-overlay");
  if (!overlay) return;
  overlay.classList.toggle("hidden", state.mode != null || state.phase !== "mode_select");
}

// ── Score ──────────────────────────────────────────────────────────────────────

function _setScore(side, remaining, total) {
  const scoreEl = el(`${side}-score`);
  const barEl   = el(`${side}-score-bar`);
  if (scoreEl) {
    scoreEl.innerHTML = `${remaining}<span class="score-denom">/${total}</span>`;
  }
  if (barEl) {
    // Bar represents territories REMAINING — starts full, shrinks from the right
    const pct = Math.max(0, (remaining / total) * 100);
    barEl.style.width = `${pct.toFixed(1)}%`;
  }
}

// ── Attack card ────────────────────────────────────────────────────────────────

function _setAttackCard(side, role, game, isActive) {
  const kills   = game.atk_destroyed_counts?.[side]?.[role] ?? 0;
  const level   = game.atk_tiers?.[side]?.[role] ?? upgradeLevel(kills);
  const fill    = upgradeFill(kills);

  const numEl   = el(`${side}-num-${role}`);
  const starsEl = el(`${side}-stars-${role}`);
  const fillEl  = el(`${side}-fill-${role}`);

  if (numEl)   numEl.textContent   = pad2(kills);
  if (starsEl) starsEl.textContent = starsHTML(level);
  if (fillEl)  fillEl.style.height = `${(fill * 100).toFixed(1)}%`;
}

// ── Defense card ───────────────────────────────────────────────────────────────

function _setDefCard(side, def, activeRemaining, total, upgrade, state) {
  const protecting = countProtectedResources(side, def, state, upgrade);
  const threshold = state.game?.def_upgrade_remaining_cells ?? 12;
  const fillPct = Math.max(0, Math.min(1, (total - activeRemaining) / Math.max(1, total - threshold)));

  const numEl   = el(`${side}-num-def`);
  const starsEl = el(`${side}-stars-def`);
  const fillEl  = el(`${side}-fill-def`);
  const cardEl  = el(`${side}-card-def`);

  if (numEl)   numEl.textContent   = pad2(protecting);
  if (starsEl) starsEl.textContent = starsHTML(1 + upgrade);
  if (fillEl)  fillEl.style.height = `${(fillPct * 100).toFixed(1)}%`;

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
let _lastGame          = {};
let _lastState         = null;
let _wsConnected       = false;

function _updateStatus(state, activeSide, game) {
  _lastActiveSide = activeSide;
  _lastState = state || null;
  _lastGame = game || {};

  const bar    = el("notif-bar");
  const textEl = el("notif-text");
  if (!bar || !textEl) return;

  bar.className = activeSide === "p1" ? "notif-bar turn-p1"
                : activeSide === "p2" ? "notif-bar turn-p2"
                : "notif-bar";

  const setupMessage = state?.setup?.status_message;
  if (setupMessage && state?.phase !== "game") {
    textEl.textContent = setupMessage;
    return;
  }

  const battleMessage = state?.battle?.status_message;
  if (battleMessage) {
    textEl.textContent = battleMessage;
    return;
  }

  const primaryError = Array.isArray(state?.errors) ? state.errors.find((err) => err?.message) : null;
  if (primaryError?.message) {
    textEl.textContent = primaryError.message;
    return;
  }

  if (!activeSide) {
    textEl.textContent = _wsConnected ? "CONNECTED - READY TO PLAY" : "Waiting for server...";
    return;
  }

  const hints = [];

  for (const role of ["atk_a", "atk_b"]) {
    const kills = game?.atk_destroyed_counts?.[activeSide]?.[role] ?? 0;
    const level = game?.atk_tiers?.[activeSide]?.[role] ?? upgradeLevel(kills);
    const label = role === "atk_a" ? "Token A" : "Token B";

    if (level === 0) {
      const need = UPGRADE_1 - kills;
      hints.push(`${label}: ${need} hit${need !== 1 ? "s" : ""} to upgrade`);
    } else if (level === 1) {
      const need = UPGRADE_2 - kills;
      hints.push(`${label}: ${need} hit${need !== 1 ? "s" : ""} to max`);
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

  bar.className      = `notif-bar result-${side}`;
  textEl.textContent = text;

  _resultTimer = setTimeout(() => {
    _resultTimerActive = false;
    _updateStatus(_lastState, _lastActiveSide, _lastGame);
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
      break;
    }
  }
}

// ─── Public init ──────────────────────────────────────────────────────────────

export function initUI(ws) {
  el("mode-normal")?.addEventListener("click", () => ws.send("select_mode", { mode: "normal" }));
  el("mode-tutorial")?.addEventListener("click", () => ws.send("select_mode", { mode: "tutorial" }));

  ws.on("connected", () => {
    _wsConnected = true;
    if (!_resultTimerActive) _updateStatus(_lastState, _lastActiveSide, _lastGame);
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
