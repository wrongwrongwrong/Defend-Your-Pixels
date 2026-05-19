export const HELP_POPUP_SELECTORS = {
  root: ".help-popup-root",
  overlay: "[data-help-overlay]",
  panel: ".help-popup__panel",
  close: "[data-help-close]",
  tabButton: "[data-tab-btn]",
  tabPane: "[data-tab-pane]",
};

export function buildHelpPopupTemplate() {
  return `
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Rye&family=Barlow:wght@400;600;700&display=swap');
      .help-popup-root, .help-popup-root *, .help-popup-root *::before, .help-popup-root *::after { box-sizing: border-box; margin: 0; padding: 0; }
      .help-popup-root {
        --bg:#1a1208; --surface:rgba(240,232,208,0.06); --border:rgba(240,232,208,0.08);
        --text:#c8b898; --text-bright:#f0e8d0; --gold:#d4a84a; --muted:#5a4a30;
        --farmer-bg:rgba(200,152,10,0.08); --farmer-border:rgba(200,152,10,0.2);
        --emu-bg:rgba(106,154,48,0.08); --emu-border:rgba(106,154,48,0.2);
        --placeholder-bg:#0f0a04; --placeholder-border:#2a1e0e;
        width:100vw; height:100vh; background:var(--bg); color:var(--text); font-family:'Barlow',sans-serif; pointer-events:auto;
      }
      .help-screen { width:100vw; height:100vh; display:flex; flex-direction:column; overflow:hidden; }
      .help-topbar { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:10px 20px; border-bottom:1px solid var(--border); flex-shrink:0; }
      .help-topbar-left { display:flex; align-items:baseline; gap:18px; min-width:0; }
      .help-title { font-family:'Rye',serif; font-size:15px; color:var(--gold); white-space:nowrap; }
      .help-marker-note { color:var(--muted); font-size:11px; line-height:1.35; }
      .help-close { width:28px; height:28px; border:1px solid var(--border); border-radius:6px; background:none; color:var(--text); cursor:pointer; display:flex; align-items:center; justify-content:center; opacity:.5; flex-shrink:0; }
      .help-close:hover { opacity:1; } .help-close svg { width:12px; height:12px; }
      .help-rows { flex:1; overflow-y:auto; padding:12px 16px; display:flex; flex-direction:column; gap:10px; }
      .help-rows::-webkit-scrollbar { width:3px; } .help-rows::-webkit-scrollbar-thumb { background:var(--muted); border-radius:3px; }
      .help-row { display:grid; grid-template-columns:1fr 2.4fr 1fr; gap:10px; align-items:stretch; min-height:0; }
      .help-card { border-radius:8px; padding:12px; display:flex; flex-direction:column; gap:6px; }
      .help-card.farmer { background:var(--farmer-bg); border:1px solid var(--farmer-border); }
      .help-card.emu { background:var(--emu-bg); border:1px solid var(--emu-border); }
      .help-thumb { width:44px; height:44px; background:var(--bg); border-radius:4px; overflow:hidden; border:1px solid var(--border); image-rendering:pixelated; }
      .help-thumb img { width:100%; height:100%; object-fit:contain; image-rendering:pixelated; }
      .help-card-name { font-family:'Rye',serif; font-size:13px; color:var(--text-bright); line-height:1.2; }
      .help-card-sub { font-size:11px; color:var(--muted); }
      .help-center { display:flex; gap:12px; align-items:stretch; }
      .help-mechanic { flex:1; display:flex; flex-direction:column; justify-content:center; gap:8px; }
      .help-mechanic-title { font-family:'Rye',serif; font-size:13px; color:var(--gold); }
      .help-text, .help-list { font-size:12px; line-height:1.6; color:var(--text); }
      .help-list { padding-left:16px; } .help-list li { margin-bottom:2px; }
      .help-text strong, .help-list strong { color:var(--text-bright); font-weight:700; }
      .help-pills { display:flex; align-items:center; gap:4px; flex-wrap:wrap; }
      .help-pill { font-size:10px; font-weight:700; background:var(--surface); border:1px solid var(--border); border-radius:99px; padding:2px 8px; color:var(--gold); white-space:nowrap; }
      .help-pill-arrow, .help-upgrade-note { font-size:10px; color:var(--muted); }
      .help-gif { flex:1.2; min-width:0; background:var(--placeholder-bg); border:1px dashed var(--placeholder-border); border-radius:6px; display:flex; align-items:center; justify-content:center; padding:10px; }
      .help-gif-label { font-size:10px; color:var(--muted); font-style:italic; text-align:center; line-height:1.5; }
      .help-center.no-gif .help-mechanic { flex:1; }
      @media (max-width:768px) { .help-row { grid-template-columns:1fr; gap:8px; } .help-center { flex-direction:column; } .help-card { flex-direction:row; align-items:center; gap:10px; } .help-rows { padding:10px; } .help-topbar-left { flex-direction:column; gap:4px; } }
    </style>

    <div class="help-popup-root">
      <div class="help-screen">
        <div class="help-topbar">
          <div class="help-topbar-left">
            <span class="help-title">How to Play</span>
            <span class="help-marker-note">To close this guide, cover or remove marker ID5 from the camera view.</span>
          </div>
          <button class="help-close" type="button" aria-label="Close" data-help-close>
            <svg viewBox="0 0 14 14" fill="none"><line x1="1" y1="1" x2="13" y2="13" stroke="currentColor" stroke-width="2" stroke-linecap="round"></line><line x1="13" y1="1" x2="1" y2="13" stroke="currentColor" stroke-width="2" stroke-linecap="round"></line></svg>
          </button>
        </div>
        <div class="help-rows">
          ${row(card('farmer', 'assets/images/hq-mick.png', 'Grain Stash', 'Secret HQ - hidden'), winMechanic(), card('emu', 'assets/images/hq-emu.png', 'Bird Council', 'Secret HQ - hidden'))}
          ${row(card('farmer', 'assets/images/atk-mick-rifleman.png', 'Riflemen x 2'), attackMechanic(), card('emu', 'assets/images/atk-emu.png', 'Emu Pack x 2'))}
          ${row(card('farmer', 'assets/images/def-mick.png', 'Old Mick x 1'), defenseMechanic(), card('emu', 'assets/images/atk-emu-cassowary.png', 'Cassowary x 1'))}
          ${row(card('farmer', 'assets/images/nuke-mick-keith.png', "Keith's Cannon", 'One use only'), wildMechanic(), card('emu', 'assets/images/nuke-emu-ancestors.png', 'The Ancestors', 'One use only'))}
          ${row(card('farmer', 'assets/images/cell-mick-wheat fields.png', 'Farms', 'Your cells'), terrainMechanic(), card('emu', 'assets/images/cell-emu-feeding grounds.png', 'Nests', 'Your cells'))}
        </div>
      </div>
    </div>
  `;
}

function card(side, img, name, sub = '') {
  return `<div class="help-card ${side}"><div class="help-thumb"><img src="${img}" alt="${name}"></div><div class="help-card-name">${name}</div>${sub ? `<div class="help-card-sub">${sub}</div>` : ''}</div>`;
}

function row(left, center, right) {
  return `<div class="help-row">${left}${center}${right}</div>`;
}

function center(mechanic, gifLabel = null) {
  const gif = gifLabel ? `<div class="help-gif"><span class="help-gif-label">${gifLabel}</span></div>` : '';
  return `<div class="help-center${gifLabel ? '' : ' no-gif'}"><div class="help-mechanic">${mechanic}</div>${gif}</div>`;
}

function winMechanic() {
  return center(`<div class="help-mechanic-title">Win Condition</div><ul class="help-list"><li>Destroy the enemy's secret HQ - instant win</li><li>Wipe all enemy cells - destroy every Farm or every Nest</li></ul>`, 'GIF - HQ cell hit and destroyed');
}

function attackMechanic() {
  return center(`<div class="help-mechanic-title">Attack</div><p class="help-text">Fires in a straight line - horizontal, vertical, or diagonal. Hits the first enemy cell it reaches.</p><div class="help-pills"><span class="help-pill">Lv 1 - 1 cell</span><span class="help-pill-arrow">-></span><span class="help-pill">Lv 2 - 2 cells</span><span class="help-pill-arrow">-></span><span class="help-pill">Lv 3 - 3 cells</span></div><span class="help-upgrade-note">Each token levels up independently.</span>`, 'GIF - Token firing straight line, H / V / diagonal');
}

function defenseMechanic() {
  return center(`<div class="help-mechanic-title">Defence</div><p class="help-text">Projects a perimeter zone around itself. Break the perimeter first - then the cell. Move the token and the perimeter resets.</p><div class="help-pills"><span class="help-pill">Default - 3x3</span><span class="help-pill-arrow">-></span><span class="help-pill">Upgraded - 5x5</span></div><span class="help-upgrade-note">Upgrades when your own cells reach roughly half.</span>`, 'GIF - Perimeter zone, tile break, cell destroy, token move resets');
}

function wildMechanic() {
  return center(`<div class="help-mechanic-title">Wild</div><p class="help-text">Place a 3x3 zone in enemy territory. 5 random cells destroyed. Bypasses perimeter. One use only.</p><span class="help-upgrade-note">Unlocks when your own cells reach critically low.</span>`, 'GIF - 3x3 zone, 5 random cells pop');
}

function terrainMechanic() {
  return center(`<div class="help-mechanic-title">Terrain & Cells</div><ul class="help-list"><li><strong>Terrain</strong> - Rocks and Termite Mounds appear on both sides. Blocks attacks. Hit it enough and it breaks.</li><li><strong>Cells</strong> - Farms and Nests are what you're fighting over. Destroy theirs. Protect yours.</li></ul>`);
}
