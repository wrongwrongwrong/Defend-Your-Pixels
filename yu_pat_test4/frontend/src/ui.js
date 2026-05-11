/**
 * ui.js — HTML/CSS panel updater.
 *
 * Subscribes to the WSClient and reflects every game state change
 * into the DOM elements defined in index.html.  Phaser does NOT touch
 * any of these elements.
 */

// Level names per side — index = level number (0–4)
const LEVEL_NAMES_P1 = ["Base Level", "Better Aim", "Machine Gun Nest", "Call Canberra", "Unleash Keith"];
const LEVEL_NAMES_P2 = ["Base Level", "First Lesson", "Dark Awakening", "The Stampede", "The Ancestors"];
const ARROW_CHAR = { E:"→", SE:"↘", S:"↓", SW:"↙", W:"←", NW:"↖", N:"↑", NE:"↗" };

function colLabel(col) { return String.fromCharCode(65 + col); }

function posLabel(tok) {
  if (!tok || tok.col == null) return "—";
  return `${colLabel(tok.col)}${tok.row + 1}`;
}

function tierPips(t) {
  t = Math.max(0, Math.min(4, t ?? 0));
  return "●".repeat(t) + "○".repeat(4 - t);
}

// ─── Game log ─────────────────────────────────────────────────────────────────

const _log = [];

function addLog(text, cls = "") {
  _log.unshift({ text, cls });
  if (_log.length > 4) _log.length = 4;
  _renderLog();
}

function _renderLog() {
  for (let i = 0; i < 4; i++) {
    const el = document.getElementById(`log-${i}`);
    if (!el) continue;
    const entry = _log[i];
    el.textContent = entry ? `▸ ${entry.text}` : "";
    el.className   = "log-entry" + (entry?.cls ? ` ${entry.cls}` : "");
  }
}

// ─── State render ─────────────────────────────────────────────────────────────

function onState(s) {
  const G          = s.game    || {};
  const battle     = s.battle  || {};
  const setup      = s.setup   || {};
  const p1         = s.p1      || {};
  const p2         = s.p2      || {};
  const activeSide = battle.active_side ?? null;
  const threshold  = G.attrition_threshold ?? 40;
  const tier1      = G.tier_p1 ?? 0;
  const tier2      = G.tier_p2 ?? 0;

  // Turn badge (header, top-right)
  const badge = document.getElementById("turn-badge");
  if (badge) {
    if (activeSide === "p1") {
      badge.textContent = "OLD MICK'S TURN ▶";
      badge.className   = "turn-badge p1";
    } else if (activeSide === "p2") {
      badge.textContent = "◀ THE MOB'S TURN";
      badge.className   = "turn-badge p2";
    } else {
      badge.textContent = "";
      badge.className   = "turn-badge";
    }
  }

  // Panel active glow
  document.getElementById("panel-left") ?.classList.toggle("active-p1", activeSide === "p1");
  document.getElementById("panel-right")?.classList.toggle("active-p2", activeSide === "p2");

  // Score
  _setScore("p1", G.score_p1_attrition ?? 0, threshold);
  _setScore("p2", G.score_p2_attrition ?? 0, threshold);

  // Level
  _setTier("p1", tier1, LEVEL_NAMES_P1);
  _setTier("p2", tier2, LEVEL_NAMES_P2);

  // Tokens
  _setToken("p1", "atk_a", p1.atk_a, tier1);
  _setToken("p1", "atk_b", p1.atk_b, tier1);
  _setToken("p1", "def",   p1.def,   null);
  _setToken("p2", "atk_a", p2.atk_a, tier2);
  _setToken("p2", "atk_b", p2.atk_b, tier2);
  _setToken("p2", "def",   p2.def,   null);

  // HQ
  _setHq("p1", setup.hq?.p1, G.hq_revealed?.p1);
  _setHq("p2", setup.hq?.p2, G.hq_revealed?.p2);

  // Upgrade path
  _setUpgrades("p1", tier1);
  _setUpgrades("p2", tier2);

  // Notification
  _setNotif(s, G, battle);
}

function _setScore(side, score, max) {
  const bar = document.getElementById(`${side}-score-bar`);
  const val = document.getElementById(`${side}-score-val`);
  if (bar) bar.style.width = `${Math.min(100, (score / max) * 100).toFixed(1)}%`;
  if (val) val.textContent = `${score} / ${max}`;
}

function _setTier(side, tier, names) {
  const num  = document.getElementById(`${side}-tier-num`);
  const pips = document.getElementById(`${side}-tier-pips`);
  const name = document.getElementById(`${side}-tier-name`);
  if (num)  num.textContent  = `${tier}`;
  if (pips) pips.textContent = tierPips(tier);
  if (name) name.textContent = names[tier] ?? "";
}

function _setToken(side, role, tok, tier) {
  const posEl  = document.getElementById(`${side}-pos-${role}`);
  const tierEl = document.getElementById(`${side}-tier-${role}`);
  if (posEl) {
    const label = posLabel(tok);
    const isAtk = role === "atk_a" || role === "atk_b";
    const arrow = (isAtk && tok?.direction) ? ` ${ARROW_CHAR[tok.direction] ?? ""}` : "";
    posEl.textContent = label === "—" ? "—" : `${label}${arrow}`;
    posEl.classList.toggle("stale", !!tok?.stale);
  }
  if (tierEl && tier != null) tierEl.textContent = tierPips(tier);
}

function _setHq(side, setupHq, revealedPos) {
  const wrap   = document.getElementById(`${side}-hq-wrap`);
  const status = document.getElementById(`${side}-hq-status`);
  const sub    = document.getElementById(`${side}-hq-sub`);
  if (!wrap || !status || !sub) return;

  wrap.classList.remove("hidden", "candidate", "confirmed", "revealed");
  status.classList.remove("revealed", "confirmed");

  if (revealedPos) {
    const label = `${colLabel(revealedPos[0])}${revealedPos[1] + 1}`;
    wrap.classList.add("revealed");
    status.textContent = "REVEALED";
    status.classList.add("revealed");
    sub.textContent    = `at ${label}`;
  } else if (setupHq?.confirmed) {
    wrap.classList.add("confirmed");
    status.textContent = "CONFIRMED";
    status.classList.add("confirmed");
    sub.textContent    = "location locked";
  } else if (setupHq?.has_candidate) {
    wrap.classList.add("candidate");
    status.textContent = "PLACING…";
    sub.textContent    = "";
  } else {
    wrap.classList.add("hidden");
    status.textContent = "HIDDEN";
    sub.textContent    = "";
  }
}

function _setUpgrades(side, currentTier) {
  const container = document.getElementById(`${side}-upgrades`);
  if (!container) return;
  container.querySelectorAll(".upg-stage").forEach((el, t) => {
    el.classList.remove("current", "unlocked");
    if (t === currentTier)      el.classList.add("current");
    else if (t < currentTier)   el.classList.add("unlocked");
  });
}

function _setNotif(s, G, battle) {
  const notif = document.getElementById("notif-text");
  if (!notif) return;

  const inBattle   = s.phase === "game" || s.phase == null;
  const activeSide = battle.active_side;

  // Live aim hint while in battle
  if (inBattle && activeSide) {
    const toks  = activeSide === "p1" ? s.p1 : s.p2;
    const parts = [];
    for (const role of ["atk_a", "atk_b"]) {
      const tok = toks?.[role];
      if (tok?.col != null && tok.direction && !tok.stale) {
        const arrow = ARROW_CHAR[tok.direction] ?? "?";
        const name  = role === "atk_a"
          ? (activeSide === "p1" ? "Rifleman A" : "Emu Pack A")
          : (activeSide === "p1" ? "Rifleman B" : "Emu Pack B");
        parts.push(`${name} ${arrow} ${posLabel(tok)}`);
      }
    }
    if (parts.length) {
      notif.textContent = parts.join("   ·   ");
      notif.className   = "info";
      return;
    }
  }

  // Phase-based fallback message
  const phase = s.phase;
  const msgs = {
    scan:           "Align all 4 corner markers to start",
    side_selection: "Choose your side",
    hq_placement:   "Place your hidden HQ marker",
    game:           activeSide === "p1"
                      ? "Old Mick — make your move"
                      : "The Mob — make your move",
  };
  const msg = msgs[phase] ?? (phase ? `Phase: ${phase}` : "Waiting for server…");
  notif.textContent = msg;
  notif.className   = activeSide === "p1" ? "p1-turn"
                    : activeSide === "p2" ? "p2-turn"
                    : "";
}

// ─── State-transition log entries ─────────────────────────────────────────────

let _prevTiers      = { p1: 0, p2: 0 };
let _prevHqRevealed = {};
let _prevWinner     = null;

function checkTransitions(s) {
  const G     = s.game || {};
  const tier1 = G.tier_p1 ?? 0;
  const tier2 = G.tier_p2 ?? 0;

  if (tier1 > _prevTiers.p1) addLog(`▲ The Riflemen: ${LEVEL_NAMES_P1[tier1] ?? `Level ${tier1}`}`, "highlight");
  if (tier2 > _prevTiers.p2) addLog(`▲ The Emu Pack: ${LEVEL_NAMES_P2[tier2] ?? `Level ${tier2}`}`, "success");
  _prevTiers.p1 = tier1;
  _prevTiers.p2 = tier2;

  for (const [side, pos] of Object.entries(G.hq_revealed || {})) {
    const posKey = `${pos[0]},${pos[1]}`;
    if (_prevHqRevealed[side] !== posKey) {
      _prevHqRevealed[side] = posKey;
      const label = `${colLabel(pos[0])}${pos[1] + 1}`;
      const name  = side === "p1" ? "The Grain Stash" : "The Bird Council";
      addLog(`🎯 ${name} revealed at ${label}!`, "danger");
    }
  }

  if (G.winner && !_prevWinner) {
    const winner = G.winner === "p1" ? "Old Mick" : "The Mob";
    addLog(`🏆 ${winner} wins! — ${G.win_reason ?? ""}`, "highlight");
  }
  _prevWinner = G.winner ?? null;
}

function onEvents(events) {
  for (const ev of events) {
    switch (ev.type) {
      case "cell_damaged":
        addLog(`Hit — ${ev.cell ? `${colLabel(ev.cell[0])}${ev.cell[1]+1}` : "cell"} damaged`, "danger");
        break;
      case "cell_destroyed":
        addLog(`💥 ${ev.cell ? `${colLabel(ev.cell[0])}${ev.cell[1]+1}` : "Cell"} destroyed!`, "danger");
        break;
      case "soft_destroyed":
      case "blocked_hard":
        addLog("Shot blocked by terrain");
        break;
      case "hq_destroyed":
        addLog("🎯 HQ destroyed!", "danger");
        break;
      case "nuke_triggered":
        addLog("💣 Nuke triggered!", "danger");
        break;
      case "attrition_win":
        addLog("⚔ Attrition victory!", "success");
        break;
    }
  }
}

// ─── Public init ──────────────────────────────────────────────────────────────

export function initUI(ws) {
  ws.on("connected", () => {
    const notif = document.getElementById("notif-text");
    if (notif) { notif.textContent = "Connected — waiting for game…"; notif.className = ""; }
  });

  ws.on("state", (s) => {
    onState(s);
    checkTransitions(s);
  });

  ws.on("events", onEvents);

  ws.on("disconnected", () => {
    const notif = document.getElementById("notif-text");
    if (notif) { notif.textContent = "Disconnected — reconnecting…"; notif.className = ""; }
  });
}
