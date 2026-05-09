export const HELP_POPUP_SELECTORS = {
  root: ".help-popup-root",
  overlay: "[data-help-overlay]",
  panel: ".help-popup__panel",
  close: "[data-help-close]",
  tabButton: "[data-tab-btn]",
  tabPane: "[data-tab-pane]",
};


export function buildHelpPopupTemplate({ width, height }) {
  return `
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Rye&family=Barlow:wght@400;600;700&display=swap');

      .help-popup-root, .help-popup-root *, .help-popup-root *::before, .help-popup-root *::after {
        box-sizing: border-box;
      }

      .help-popup-root {
        --ochre: #d4a42a;
        --ochre-light: #f5dfa0;
        --ochre-dark: #8a6010;
        --ink: #1a1208;
        --parchment: #f5ede0;
        --paper: #faf6f0;
        --rule: rgba(26, 18, 8, 0.12);
        width: ${width}px;
        height: ${height}px;
        position: relative;
        font-family: 'Barlow', Georgia, serif;
        pointer-events: auto;
      }

      .help-popup__overlay {
        position: absolute;
        inset: 0;
        background: rgba(10, 8, 4, 0.72);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px;
      }

      .help-popup__panel {
        background: var(--parchment);
        border-radius: 16px;
        border: 1.5px solid var(--ochre);
        width: min(100%, 640px);
        max-height: min(88vh, calc(100% - 32px));
        overflow: hidden;
        display: flex;
        flex-direction: column;
        box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
        color: var(--ink);
      }

      .help-popup__header {
        padding: 18px 20px 16px;
        border-bottom: 1.5px solid var(--ochre);
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: var(--paper);
        flex-shrink: 0;
        gap: 16px;
      }

      .help-popup__header-left {
        display: flex;
        flex-direction: column;
        gap: 2px;
        min-width: 0;
      }

      .help-popup__label {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--ochre-dark);
      }

      .help-popup__title {
        font-family: 'Rye', serif;
        font-size: 18px;
        line-height: 1.1;
      }

      .help-popup__close {
        width: 32px;
        height: 32px;
        border-radius: 8px;
        border: 1px solid var(--rule);
        background: none;
        color: var(--ink);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0.5;
        transition: opacity 0.15s, background 0.15s;
        flex-shrink: 0;
      }

      .help-popup__close:hover {
        opacity: 1;
        background: rgba(26, 18, 8, 0.06);
      }

      .help-popup__close svg {
        width: 14px;
        height: 14px;
      }

      .help-popup__tabs {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        border-bottom: 1.5px solid var(--rule);
        background: var(--paper);
        flex-shrink: 0;
        padding: 0 20px;
      }

      .help-popup__tab-btn {
        font-family: 'Barlow', Georgia, serif;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--ink);
        opacity: 0.4;
        background: none;
        border: none;
        border-bottom: 2.5px solid transparent;
        padding: 12px 0;
        cursor: pointer;
        transition: opacity 0.15s, border-color 0.15s;
      }

      .help-popup__tab-btn:hover {
        opacity: 0.7;
      }

      .help-popup__tab-btn.is-active {
        opacity: 1;
        border-bottom-color: var(--ochre);
      }

      .help-popup__body {
        overflow-y: auto;
        flex: 1;
        padding: 0;
      }

      .help-popup__body::-webkit-scrollbar {
        width: 4px;
      }

      .help-popup__body::-webkit-scrollbar-track {
        background: transparent;
      }

      .help-popup__body::-webkit-scrollbar-thumb {
        background: var(--ochre-light);
        border-radius: 4px;
      }

      .help-popup__pane {
        display: none;
        padding: 20px;
      }

      .help-popup__pane.is-active {
        display: block;
      }

      .help-popup__sec-label {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        color: var(--ochre-dark);
        margin-bottom: 10px;
        margin-top: 20px;
        padding-bottom: 6px;
        border-bottom: 1px solid var(--ochre-light);
      }

      .help-popup__sec-label:first-child {
        margin-top: 0;
      }

      .help-popup__side-split,
      .help-popup__token-grid,
      .help-popup__win-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
      }

      .help-popup__side-card,
      .help-popup__token-card,
      .help-popup__win-card,
      .help-popup__prose,
      .help-popup__upgrade-cell {
        background: var(--paper);
        border-radius: 10px;
      }

      .help-popup__side-card {
        padding: 12px 14px;
        border: 1px solid;
      }

      .help-popup__side-card.is-farmer {
        background: #d4e8b0;
        border-color: #6a9a30;
      }

      .help-popup__side-card.is-emu {
        background: #f5e8c0;
        border-color: #c8980a;
      }

      .help-popup__side-tag,
      .help-popup__token-side,
      .help-popup__win-type,
      .help-popup__tier-tag,
      .help-popup__col-hdr,
      .help-popup__label-pill {
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }

      .help-popup__side-tag {
        margin-bottom: 3px;
      }

      .help-popup__side-card.is-farmer .help-popup__side-tag,
      .help-popup__farmer-col {
        color: #1e4a08;
      }

      .help-popup__side-card.is-emu .help-popup__side-tag,
      .help-popup__emu-col {
        color: #7a4800;
      }

      .help-popup__both-col {
        color: #5a4020;
      }

      .help-popup__side-name,
      .help-popup__token-name,
      .help-popup__upgrade-name,
      .help-popup__win-name {
        font-family: 'Rye', serif;
        font-size: 13px;
        color: var(--ink);
        margin-bottom: 4px;
      }

      .help-popup__side-desc,
      .help-popup__token-desc,
      .help-popup__upgrade-desc,
      .help-popup__win-desc {
        font-size: 12px;
        color: #4a3a1a;
        line-height: 1.5;
      }

      .help-popup__token-card,
      .help-popup__win-card,
      .help-popup__prose {
        border: 0.5px solid var(--rule);
      }

      .help-popup__token-card,
      .help-popup__win-card {
        padding: 12px 14px;
      }

      .help-popup__token-img,
      .help-popup__upgrade-img {
        background: #1a1208;
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid rgba(212, 164, 42, 0.25);
      }

      .help-popup__token-img {
        width: 52px;
        height: 52px;
        margin-bottom: 8px;
      }

      .help-popup__upgrade-img {
        width: 40px;
        height: 40px;
        margin-bottom: 6px;
      }

      .help-popup__token-img img,
      .help-popup__upgrade-img img {
        width: 100%;
        height: 100%;
        object-fit: contain;
      }

      .help-popup__label-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 99px;
        margin-bottom: 6px;
      }

      .help-popup__label-pill.is-atk {
        background: #f0c8b8;
        color: #7a1f0a;
      }

      .help-popup__label-pill.is-def {
        background: #b8d4e8;
        color: #1a5a8a;
      }

      .help-popup__label-pill.is-hq {
        background: #d8d0f0;
        color: #3a2878;
      }

      .help-popup__label-pill.is-terrain {
        background: #e0d8c8;
        color: #5a4020;
      }

      .help-popup__prose {
        padding: 14px 16px;
        font-size: 13px;
        line-height: 1.8;
        color: #2a1e0e;
        margin-bottom: 10px;
      }

      .help-popup__prose strong {
        color: var(--ink);
      }

      .help-popup__col-headers,
      .help-popup__upgrade-row {
        display: grid;
        grid-template-columns: 56px 1fr 1fr;
      }

      .help-popup__col-headers {
        border-radius: 12px 12px 0 0;
        border: 0.5px solid var(--rule);
        border-bottom: none;
        overflow: hidden;
      }

      .help-popup__col-hdr {
        padding: 8px 13px;
      }

      .help-popup__col-hdr.is-blank {
        background: #f0e8d0;
        border-right: 0.5px solid var(--rule);
      }

      .help-popup__col-hdr.is-farmer {
        background: #eef5e0;
        color: #1e4a08;
        border-right: 0.5px solid var(--rule);
      }

      .help-popup__col-hdr.is-emu {
        background: #f5edd8;
        color: #7a4800;
      }

      .help-popup__upgrade-table {
        border: 0.5px solid var(--rule);
        border-top: none;
        border-radius: 0 0 12px 12px;
        overflow: hidden;
      }

      .help-popup__upgrade-row {
        border-bottom: 0.5px solid var(--rule);
      }

      .help-popup__upgrade-row:last-child {
        border-bottom: none;
      }

      .help-popup__tier-cell {
        background: #f0e8d0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 12px 8px;
        border-right: 0.5px solid var(--rule);
      }

      .help-popup__tier-num {
        font-family: 'Rye', serif;
        font-size: 20px;
        line-height: 1;
      }

      .help-popup__tier-tag {
        color: #888;
        margin-top: 2px;
      }

      .help-popup__upgrade-cell {
        padding: 12px 13px;
      }

      .help-popup__upgrade-cell:first-of-type {
        border-right: 0.5px solid var(--rule);
      }

      .help-popup__upgrade-token {
        margin-bottom: 5px;
      }

      .help-popup__win-card.is-farmer {
        border-top: 3px solid #c8980a;
      }

      .help-popup__win-card.is-emu {
        border-top: 3px solid #6a9a30;
      }

      .help-popup__instant-col {
        color: #3a2878;
      }

      .help-popup__attrition-col {
        color: #7a4800;
      }

      .help-popup__footer {
        padding: 12px 20px;
        border-top: 1px solid var(--rule);
        background: var(--paper);
        display: flex;
        justify-content: flex-end;
        flex-shrink: 0;
      }

      .help-popup__button {
        font-family: 'Barlow', Georgia, serif;
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 8px 20px;
        border-radius: 8px;
        border: 1.5px solid var(--ochre);
        background: #f0d070;
        color: #5a3800;
        cursor: pointer;
        transition: background 0.15s, transform 0.1s;
      }

      .help-popup__button:hover {
        background: var(--ochre);
        color: #fff;
      }

      .help-popup__button:active {
        transform: scale(0.97);
      }

      @media (max-width: 480px) {
        .help-popup__side-split,
        .help-popup__token-grid,
        .help-popup__win-grid {
          grid-template-columns: 1fr;
        }

        .help-popup__col-headers,
        .help-popup__upgrade-row {
          grid-template-columns: 48px 1fr;
        }

        .help-popup__upgrade-row > :nth-child(3),
        .help-popup__col-headers > :nth-child(3) {
          display: none;
        }

        .help-popup__upgrade-cell:first-of-type {
          border-right: none;
        }

        .help-popup__title {
          font-size: 15px;
        }
      }
    </style>

    <div class="help-popup-root">
      <div class="help-popup__overlay" data-help-overlay>
        <div class="help-popup__panel" role="dialog" aria-modal="true" aria-label="Game Help">
          <div class="help-popup__header">
            <div class="help-popup__header-left">
              <span class="help-popup__label">How to play</span>
              <span class="help-popup__title">Old Mick Against the Mob</span>
            </div>
            <button class="help-popup__close" type="button" data-help-close aria-label="Close help">
              <svg viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
                <line x1="1" y1="1" x2="13" y2="13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></line>
                <line x1="13" y1="1" x2="1" y2="13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></line>
              </svg>
            </button>
          </div>

          <div class="help-popup__tabs">
            <button class="help-popup__tab-btn is-active" type="button" data-tab-btn="overview">Overview</button>
            <button class="help-popup__tab-btn" type="button" data-tab-btn="tokens">Tokens</button>
            <button class="help-popup__tab-btn" type="button" data-tab-btn="upgrades">Upgrades</button>
            <button class="help-popup__tab-btn" type="button" data-tab-btn="winconditions">Win</button>
          </div>

          <div class="help-popup__body">
            <div class="help-popup__pane is-active" data-tab-pane="overview">
              <div class="help-popup__sec-label">The two sides</div>
              <div class="help-popup__side-split">
                <div class="help-popup__side-card is-farmer">
                  <div class="help-popup__side-tag">Farmer side</div>
                  <div class="help-popup__side-name">Old Mick</div>
                  <div class="help-popup__side-desc">Protect wheat paddocks. Find the Nest or destroy the feeding grounds. Two riflemen, one stubborn farmer.</div>
                </div>
                <div class="help-popup__side-card is-emu">
                  <div class="help-popup__side-tag">Emu side</div>
                  <div class="help-popup__side-name">The Mob</div>
                  <div class="help-popup__side-desc">Raid wheat, defend feeding grounds. Find the Homestead or destroy the wheat paddocks. Two emu packs, one cassowary.</div>
                </div>
              </div>

              <div class="help-popup__sec-label">How to play</div>
              <div class="help-popup__prose"><strong>Positioning:</strong> Place ATK tokens on your side and aim them in a straight line. They hit the first enemy cell they reach across the fence. DEF tokens do not attack; they protect nearby cells with extra HP.</div>
              <div class="help-popup__prose"><strong>Upgrades:</strong> Destroy enemy resource cells to earn progress. Tier 1 and 3 improve ATK splash. Tier 2 expands the DEF zone. Tier 4 unlocks a one-time nuke.</div>
              <div class="help-popup__prose"><strong>Win:</strong> Destroy the enemy HQ for an instant win, or wipe out all enemy resource cells for an attrition victory.</div>

              <div class="help-popup__sec-label">Terrain</div>
              <div class="help-popup__token-grid">
                <div class="help-popup__token-card">
                  <div class="help-popup__token-img"><img src="assets/images/hard-mick-v2.png" alt="Hard terrain"></div>
                  <span class="help-popup__label-pill is-terrain">Hard</span>
                  <div class="help-popup__token-name">Rocks</div>
                  <div class="help-popup__token-desc">Permanently blocks straight-line attacks.</div>
                </div>
                <div class="help-popup__token-card">
                  <div class="help-popup__token-img"><img src="assets/images/soft-mick-v1.png" alt="Soft terrain"></div>
                  <span class="help-popup__label-pill is-terrain">Soft</span>
                  <div class="help-popup__token-name">Termite Mounds</div>
                  <div class="help-popup__token-desc">Blocks attacks until destroyed. Soft terrain takes 2 hits to clear.</div>
                </div>
              </div>
            </div>

            <div class="help-popup__pane" data-tab-pane="tokens">
              <div class="help-popup__sec-label">The two sides</div>
              <div class="help-popup__side-split">
                <div class="help-popup__side-card is-farmer">
                  <div class="help-popup__side-tag">Farmer side</div>
                  <div class="help-popup__side-name">Old Mick's Paddock</div>
                  <div class="help-popup__side-desc">Red dirt, wheat rows, corrugated iron. Old Mick defends. The riflemen attack. Nobody asks Keith questions.</div>
                </div>
                <div class="help-popup__side-card is-emu">
                  <div class="help-popup__side-tag">Emu side</div>
                  <div class="help-popup__side-name">The Scrublands</div>
                  <div class="help-popup__side-desc">Dense bush, termite mounds, spinifex. The Emu Pack raids. The Cassowary guards. The Nest is hidden and wants to stay that way.</div>
                </div>
              </div>

              <div class="help-popup__sec-label">Attack tokens — 2 per side</div>
              <div class="help-popup__token-grid">
                <div class="help-popup__token-card">
                  <div class="help-popup__token-img"><img src="assets/images/atk-mick-rifleman.png" alt="The Riflemen"></div>
                  <span class="help-popup__label-pill is-atk">ATK × 2</span>
                  <div class="help-popup__token-name">The Riflemen</div>
                  <div class="help-popup__token-side help-popup__farmer-col">Farmer side</div>
                  <div class="help-popup__token-desc">Each turn you direct a rifleman token. It fires in a straight line, hits the first enemy target across the fence, and stops there. Two riflemen means two attack lines to plan around.</div>
                </div>
                <div class="help-popup__token-card">
                  <div class="help-popup__token-img"><img src="assets/images/atk-emu.png" alt="The Emu Pack"></div>
                  <span class="help-popup__label-pill is-atk">ATK × 2</span>
                  <div class="help-popup__token-name">The Emu Pack</div>
                  <div class="help-popup__token-side help-popup__emu-col">Emu side</div>
                  <div class="help-popup__token-desc">Each turn you direct a mob token. It charges in a straight line, hits the first enemy target across the fence, and stops there. Two mob tokens let you threaten multiple lanes.</div>
                </div>
              </div>

              <div class="help-popup__sec-label">Defence tokens — 1 per side</div>
              <div class="help-popup__token-grid">
                <div class="help-popup__token-card">
                  <div class="help-popup__token-img"><img src="assets/images/def-mick.png" alt="Old Mick"></div>
                  <span class="help-popup__label-pill is-def">DEF × 1</span>
                  <div class="help-popup__token-name">Old Mick</div>
                  <div class="help-popup__token-side help-popup__farmer-col">Farmer side</div>
                  <div class="help-popup__token-desc">Every wheat paddock within his 3×3 protection zone gains +1 HP, taking 2 hits instead of 1. At Tier 2 that zone expands to 5×5.</div>
                </div>
                <div class="help-popup__token-card">
                  <div class="help-popup__token-img"><img src="assets/images/atk-emu-cassowary.png" alt="Cassowary"></div>
                  <span class="help-popup__label-pill is-def">DEF × 1</span>
                  <div class="help-popup__token-name">Cassowary</div>
                  <div class="help-popup__token-side help-popup__emu-col">Emu side</div>
                  <div class="help-popup__token-desc">Every feeding ground within its 3×3 protection zone gains +1 HP, taking 2 hits instead of 1. At Tier 2 that zone expands to 5×5.</div>
                </div>
              </div>

              <div class="help-popup__sec-label">Hidden HQs — 1 per side</div>
              <div class="help-popup__token-grid">
                <div class="help-popup__token-card">
                  <div class="help-popup__token-img"><img src="assets/images/hq-mick.png" alt="Homestead"></div>
                  <span class="help-popup__label-pill is-hq">Hidden HQ</span>
                  <div class="help-popup__token-name">Homestead</div>
                  <div class="help-popup__token-side help-popup__farmer-col">Farmer side</div>
                  <div class="help-popup__token-desc">Old Mick's Homestead. If the Mob finds and destroys it, the farm is finished immediately.</div>
                </div>
                <div class="help-popup__token-card">
                  <div class="help-popup__token-img"><img src="assets/images/hq-emu.png" alt="Nest"></div>
                  <span class="help-popup__label-pill is-hq">Hidden HQ</span>
                  <div class="help-popup__token-name">Nest</div>
                  <div class="help-popup__token-side help-popup__emu-col">Emu side</div>
                  <div class="help-popup__token-desc">The hidden Nest. If the riflemen find and destroy it, the Mob breaks instantly.</div>
                </div>
              </div>

              <div class="help-popup__sec-label">Terrain — both sides</div>
              <div class="help-popup__token-grid">
                <div class="help-popup__token-card">
                  <div class="help-popup__token-img"><img src="assets/images/hard-mick-v2.png" alt="Rocks"></div>
                  <span class="help-popup__label-pill is-terrain">Hard</span>
                  <div class="help-popup__token-name">Rocks</div>
                  <div class="help-popup__token-side help-popup__both-col">Both sides</div>
                  <div class="help-popup__token-desc">Impassable and permanent. Hard terrain blocks any straight-line attack that reaches it first.</div>
                </div>
                <div class="help-popup__token-card">
                  <div class="help-popup__token-img"><img src="assets/images/soft-mick-v1.png" alt="Termite Mounds"></div>
                  <span class="help-popup__label-pill is-terrain">Soft</span>
                  <div class="help-popup__token-name">Termite Mounds</div>
                  <div class="help-popup__token-side help-popup__both-col">Both sides</div>
                  <div class="help-popup__token-desc">Destructible blocker. Soft terrain absorbs hits until it is destroyed, then the lane opens.</div>
                </div>
              </div>

              <div class="help-popup__sec-label">Positioning rule</div>
              <div class="help-popup__prose">ATK tokens aim in a <strong>straight line only</strong> — horizontal, vertical, or diagonal based on the token's facing. They hit the first valid enemy target in that lane. <strong>Hard terrain</strong> permanently blocks those shots. <strong>Soft terrain</strong> blocks until destroyed.</div>
            </div>

            <div class="help-popup__pane" data-tab-pane="upgrades">
              <div class="help-popup__sec-label">How upgrades are funded</div>
              <div class="help-popup__prose"><strong>Farmer side</strong> upgrades by destroying feeding grounds. <strong>Emu side</strong> upgrades by destroying wheat paddocks. Progress earned from destroyed resource cells feeds the same tier system on both sides.</div>

              <div class="help-popup__sec-label">Upgrade levels</div>
              <div class="help-popup__col-headers">
                <div class="help-popup__col-hdr is-blank"></div>
                <div class="help-popup__col-hdr is-farmer">Farmer side</div>
                <div class="help-popup__col-hdr is-emu">Emu side</div>
              </div>
              <div class="help-popup__upgrade-table">
                <div class="help-popup__upgrade-row">
                  <div class="help-popup__tier-cell">
                    <span class="help-popup__tier-num">1</span>
                    <span class="help-popup__tier-tag">ATK</span>
                  </div>
                  <div class="help-popup__upgrade-cell">
                    <div class="help-popup__upgrade-img"><img src="assets/images/atk-mick-rifleman.png" alt="Tier 1 riflemen"></div>
                    <div class="help-popup__upgrade-name">Better Aim</div>
                    <div class="help-popup__upgrade-token help-popup__farmer-col">The Riflemen</div>
                    <div class="help-popup__upgrade-desc">Riflemen shots splash into one neighbouring feeding ground when possible.</div>
                  </div>
                  <div class="help-popup__upgrade-cell">
                    <div class="help-popup__upgrade-img"><img src="assets/images/atk-emu.png" alt="Tier 1 emu pack"></div>
                    <div class="help-popup__upgrade-name">First Lesson</div>
                    <div class="help-popup__upgrade-token help-popup__emu-col">The Emu Pack</div>
                    <div class="help-popup__upgrade-desc">Mob attacks splash into one neighbouring wheat paddock when possible.</div>
                  </div>
                </div>

                <div class="help-popup__upgrade-row">
                  <div class="help-popup__tier-cell">
                    <span class="help-popup__tier-num">2</span>
                    <span class="help-popup__tier-tag">DEF</span>
                  </div>
                  <div class="help-popup__upgrade-cell">
                    <div class="help-popup__upgrade-img"><img src="assets/images/def-mick.png" alt="Tier 2 Old Mick"></div>
                    <div class="help-popup__upgrade-name">Machine Gun Nest</div>
                    <div class="help-popup__upgrade-token help-popup__farmer-col">Old Mick</div>
                    <div class="help-popup__upgrade-desc">Old Mick's protection zone expands from 3×3 to 5×5.</div>
                  </div>
                  <div class="help-popup__upgrade-cell">
                    <div class="help-popup__upgrade-img"><img src="assets/images/atk-emu-cassowary.png" alt="Tier 2 Cassowary"></div>
                    <div class="help-popup__upgrade-name">Dark Awakening</div>
                    <div class="help-popup__upgrade-token help-popup__emu-col">Cassowary</div>
                    <div class="help-popup__upgrade-desc">The Cassowary's protection zone expands from 3×3 to 5×5.</div>
                  </div>
                </div>

                <div class="help-popup__upgrade-row">
                  <div class="help-popup__tier-cell">
                    <span class="help-popup__tier-num">3</span>
                    <span class="help-popup__tier-tag">ATK</span>
                  </div>
                  <div class="help-popup__upgrade-cell">
                    <div class="help-popup__upgrade-img"><img src="assets/images/atk-mick-rifleman.png" alt="Tier 3 riflemen"></div>
                    <div class="help-popup__upgrade-name">Call Canberra</div>
                    <div class="help-popup__upgrade-token help-popup__farmer-col">The Riflemen</div>
                    <div class="help-popup__upgrade-desc">Riflemen shots can splash into up to two neighbouring feeding grounds.</div>
                  </div>
                  <div class="help-popup__upgrade-cell">
                    <div class="help-popup__upgrade-img"><img src="assets/images/atk-emu.png" alt="Tier 3 emu pack"></div>
                    <div class="help-popup__upgrade-name">The Stampede</div>
                    <div class="help-popup__upgrade-token help-popup__emu-col">The Emu Pack</div>
                    <div class="help-popup__upgrade-desc">Mob attacks can splash into up to two neighbouring wheat paddocks.</div>
                  </div>
                </div>

                <div class="help-popup__upgrade-row">
                  <div class="help-popup__tier-cell">
                    <span class="help-popup__tier-num">4</span>
                    <span class="help-popup__tier-tag">Nuke</span>
                  </div>
                  <div class="help-popup__upgrade-cell">
                    <div class="help-popup__upgrade-img"><img src="assets/images/nuke-mick-keith.png" alt="Keith nuke"></div>
                    <div class="help-popup__upgrade-name">Unleash Keith</div>
                    <div class="help-popup__upgrade-token help-popup__farmer-col">One use only</div>
                    <div class="help-popup__upgrade-desc">One devastating 3×3 strike for the active side. Keith does not come back.</div>
                  </div>
                  <div class="help-popup__upgrade-cell">
                    <div class="help-popup__upgrade-img"><img src="assets/images/nuke-emu-ancestors.png" alt="Ancestors nuke"></div>
                    <div class="help-popup__upgrade-name">The Ancestors</div>
                    <div class="help-popup__upgrade-token help-popup__emu-col">One use only</div>
                    <div class="help-popup__upgrade-desc">One devastating 3×3 strike powered by dark bird magic. No explanation given.</div>
                  </div>
                </div>
              </div>
            </div>

            <div class="help-popup__pane" data-tab-pane="winconditions">
              <div class="help-popup__sec-label">Instant wins</div>
              <div class="help-popup__win-grid">
                <div class="help-popup__win-card is-farmer">
                  <div class="help-popup__win-type help-popup__instant-col">Instant win — Farmer</div>
                  <div class="help-popup__win-name">Destroy the Nest</div>
                  <div class="help-popup__win-desc">The Nest is gone. The Mob breaks immediately.</div>
                </div>
                <div class="help-popup__win-card is-emu">
                  <div class="help-popup__win-type help-popup__instant-col">Instant win — Emu</div>
                  <div class="help-popup__win-name">Destroy the Homestead</div>
                  <div class="help-popup__win-desc">The Homestead is gone. Old Mick has nothing left to defend.</div>
                </div>
              </div>

              <div class="help-popup__sec-label">Attrition wins</div>
              <div class="help-popup__win-grid">
                <div class="help-popup__win-card is-farmer">
                  <div class="help-popup__win-type help-popup__attrition-col">Attrition win — Farmer</div>
                  <div class="help-popup__win-name">Wipe the Feeding Grounds</div>
                  <div class="help-popup__win-desc">The scrublands go quiet. The outback belongs to Old Mick.</div>
                </div>
                <div class="help-popup__win-card is-emu">
                  <div class="help-popup__win-type help-popup__attrition-col">Attrition win — Emu</div>
                  <div class="help-popup__win-name">Raze the Paddocks</div>
                  <div class="help-popup__win-desc">No grain, no operation. The pack eats well tonight.</div>
                </div>
              </div>

              <div class="help-popup__sec-label">Strategy note</div>
              <div class="help-popup__prose">You are always playing two games at once: <strong>the hidden game</strong> of finding their HQ before they find yours, and <strong>the attrition game</strong> of destroying enough enemy territory to starve them out. Upgrades strengthen both plans, but every turn still comes down to positioning the right lane.</div>
            </div>
          </div>

          <div class="help-popup__footer">
            <button class="help-popup__button" type="button" data-help-close>Got it</button>
          </div>
        </div>
      </div>
    </div>
  `;
}
