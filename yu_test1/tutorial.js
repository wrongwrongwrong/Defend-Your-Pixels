// Connected tutorial logic for yu_test1.
// Loaded by index.html and used when ?tutorial=1.

window.DypTutorial = (() => {
  const TARGETS = {
    p1AtkStart: { col: 3, row: 3 }, // D4
    p1DefSpot:  { col: 1, row: 1 }, // B2
  };

  function _isVisible(tok) {
    return tok && tok.col != null && tok.row != null && !tok.stale;
  }

  function _atCell(tok, col, row) {
    return tok && tok.col === col && tok.row === row;
  }

  function init(scene) {
    scene._tut = {
      step: 0,
      lastTurn: null,
      highlightCell: null,
      highlightZone: null,
      completed: false,
    };

    scene.tutorialTxt = scene.add.text(PANEL_X + 8, 520, '', {
      fontSize: '12px',
      fontFamily: 'Georgia',
      color: '#ffe070',
      lineSpacing: 6,
      wordWrap: { width: PW - 16 },
    }).setDepth(5);

    scene.tutorialHintTxt = scene.add.text(PANEL_X + 8, 690, '', {
      fontSize: '11px',
      fontFamily: 'Georgia',
      color: '#f0c080',
      lineSpacing: 5,
      wordWrap: { width: PW - 16 },
    }).setDepth(5);

    // Ask backend to enter tutorial mode (fixed HQs, skip HQ setup).
    try {
      if (window.wsInstance && window.wsInstance.readyState === WebSocket.OPEN) {
        window.wsInstance.send(JSON.stringify({ type: 'tutorial', enabled: true }));
      } else {
        // If WS isn't open yet, onopen handler in index.html will retry via tick().
        scene._tut._needsEnable = true;
      }
    } catch (_) {}
  }

  function tick(scene) {
    if (!scene._tut || scene._tut.completed) return;
    const s = window.gameState;
    if (!s) return;

    // Ensure backend tutorial mode is enabled.
    if (scene._tut._needsEnable && window.wsInstance && window.wsInstance.readyState === WebSocket.OPEN) {
      try {
        window.wsInstance.send(JSON.stringify({ type: 'tutorial', enabled: true }));
        scene._tut._needsEnable = false;
      } catch (_) {}
    }

    const phase = s.phase;
    const turn = s.turn;
    const p1 = s.p1 || {};
    const G = s.game || {};
    const tutorial = s.tutorial || null;
    const events = Array.isArray(s.events) ? s.events : [];

    if (scene._tut.lastTurn == null && turn != null) scene._tut.lastTurn = turn;
    const turnChanged = (turn != null && scene._tut.lastTurn != null && turn !== scene._tut.lastTurn);
    if (turnChanged) scene._tut.lastTurn = turn;

    const setCellHighlight = (col, row) => {
      scene._tut.highlightZone = null;
      scene._tut.highlightCell = (col == null ? null : { col, row });
    };
    const setZoneHighlight = (cells) => {
      scene._tut.highlightCell = null;
      scene._tut.highlightZone = cells || null;
    };

    // Wait for backend to be in tutorial game phase.
    if (phase != null && phase !== 'game') {
      setCellHighlight(null, null);
      scene.tutorialTxt?.setText('Tutorial (connected)\n\nWaiting for battle phase…');
      scene.tutorialHintTxt?.setText('Wait for board scan. Tutorial mode will skip HQ setup automatically.');
      return;
    }

    // Optional: show target HQ tile if backend provided it.
    const enemyHq = Array.isArray(tutorial?.hq_p2) ? { col: tutorial.hq_p2[0], row: tutorial.hq_p2[1] } : null;

    // Step progression (same as before, but now lives outside index.html).
    if (scene._tut.step === 0) {
      const t = TARGETS.p1AtkStart;
      setCellHighlight(t.col, t.row);
      scene.tutorialTxt?.setText('Step 1 — Place ATK\n\nMove P1 ATK A onto D4.');
      scene.tutorialHintTxt?.setText('When the marker is detected in D4, we continue.');
      if (_isVisible(p1.atk_a) && _atCell(p1.atk_a, t.col, t.row)) scene._tut.step = 1;
      return;
    }

    if (scene._tut.step === 1) {
      const t = TARGETS.p1AtkStart;
      setCellHighlight(t.col, t.row);
      scene.tutorialTxt?.setText('Step 2 — Aim\n\nRotate P1 ATK A to point → (E).');
      scene.tutorialHintTxt?.setText('Keep it on D4. The arrow should show →.');
      if (_isVisible(p1.atk_a) && _atCell(p1.atk_a, t.col, t.row) && p1.atk_a.direction === 'E') {
        scene._tut.step = 2;
      }
      return;
    }

    if (scene._tut.step === 2) {
      setCellHighlight(null, null);
      scene.tutorialTxt?.setText('Step 3 — End turn\n\nEnd P1 turn using the physical turn marker.');
      scene.tutorialHintTxt?.setText('When turn switches to The Mob, we continue.');
      if (turnChanged && turn === 2) scene._tut.step = 3;
      return;
    }

    if (scene._tut.step === 3) {
      setCellHighlight(null, null);
      scene.tutorialTxt?.setText('Step 4 — Back to P1\n\nEnd P2 turn to return to P1.');
      scene.tutorialHintTxt?.setText('Use the physical turn marker again.');
      if (turnChanged && turn === 1) scene._tut.step = 4;
      return;
    }

    if (scene._tut.step === 4) {
      const d = TARGETS.p1DefSpot;
      setCellHighlight(d.col, d.row);
      scene.tutorialTxt?.setText('Step 5 — Defend\n\nMove P1 DEF to B2.');
      scene.tutorialHintTxt?.setText('After it lands, we’ll highlight the protected zone.');
      if (_isVisible(p1.def) && _atCell(p1.def, d.col, d.row)) {
        const tier = (G.tier_p1 ?? 1);
        setZoneHighlight(defZoneCells(d.col, d.row, tier));
        scene._tut.step = 5;
      }
      return;
    }

    if (scene._tut.step === 5) {
      const d = TARGETS.p1DefSpot;
      const tier = (G.tier_p1 ?? 1);
      setZoneHighlight(defZoneCells(d.col, d.row, tier));
      scene.tutorialTxt?.setText('Step 6 — Demonstrate protection\n\nEnd P1 turn. Then, as P2, aim an attack into the highlighted zone and end turn.');
      scene.tutorialHintTxt?.setText('We complete this when a protected cell is damaged (not destroyed) by the attack.');
      if (turnChanged && turn === 2) scene._tut.step = 6;
      return;
    }

    if (scene._tut.step === 6) {
      const d = TARGETS.p1DefSpot;
      const tier = (G.tier_p1 ?? 1);
      const zone = defZoneCells(d.col, d.row, tier);
      setZoneHighlight(zone);

      const zoneKey = new Set(zone.map(({ col, row }) => `${col},${row}`));
      const gotDamagedProtected = events.some((ev) => {
        if (ev?.type !== 'cell_damaged') return false;
        const cell = ev.cell;
        const c = Array.isArray(cell) ? cell[0] : cell?.col;
        const r = Array.isArray(cell) ? cell[1] : cell?.row;
        return zoneKey.has(`${c},${r}`);
      });

      // Bonus final goal: destroy enemy HQ to “finish tutorial”.
      if (G.winner || events.some((ev) => ev?.type === 'hq_destroyed')) {
        scene._tut.completed = true;
        scene._tut.highlightCell = null;
        scene._tut.highlightZone = null;
        scene.tutorialTxt?.setText('Tutorial complete!\n\nEnemy HQ destroyed.');
        scene.tutorialHintTxt?.setText('You can now switch to normal mode (index.html) anytime.');
        return;
      }

      // Otherwise we still accept the protection demo as completion milestone.
      if (gotDamagedProtected) {
        scene.tutorialTxt?.setText('Good!\n\nProtection absorbed the first hit.\nNow keep playing and destroy the enemy HQ to finish.');
        if (enemyHq) {
          setCellHighlight(enemyHq.col, enemyHq.row);
          scene.tutorialHintTxt?.setText(`Enemy HQ is at ${String.fromCharCode(65 + enemyHq.col)}${enemyHq.row + 1}.\nAim an ATK ray at it and end the turn to resolve.`);
        } else {
          scene.tutorialHintTxt?.setText('Now aim an ATK ray at the enemy HQ and end the turn to resolve.');
        }
      } else {
        scene.tutorialTxt?.setText('Step 7 — Protection demo\n\nAs P2, hit a highlighted protected tile and end the turn.');
        scene.tutorialHintTxt?.setText('We are waiting for `cell_damaged` on a protected tile.');
      }
    }
  }

  function draw(scene) {
    if (!scene._tut) return;
    const pulse = 0.55 + 0.35 * Math.sin(scene.time.now / 180);

    if (scene._tut.highlightCell) {
      const { col, row } = scene._tut.highlightCell;
      const x = BX + col * CELL, y = BY + row * CELL;
      const pad = 2;
      scene.dynGfx.lineStyle(4, 0xffe070, pulse);
      scene.dynGfx.strokeRect(x + pad, y + pad, CELL - pad * 2, CELL - pad * 2);
    }

    if (Array.isArray(scene._tut.highlightZone)) {
      scene.dynGfx.lineStyle(2.5, 0xffe070, 0.22 + 0.25 * pulse);
      for (const cell of scene._tut.highlightZone) {
        const x = BX + cell.col * CELL, y = BY + cell.row * CELL;
        const pad = 3;
        scene.dynGfx.strokeRect(x + pad, y + pad, CELL - pad * 2, CELL - pad * 2);
      }
    }
  }

  return { init, tick, draw };
})();

