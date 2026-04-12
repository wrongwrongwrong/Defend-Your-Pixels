# PixelWar — Game Logic Reference
**Version:** 2.0 (Python / Pygame implementation)

---

## 1. Board

- The board is split by a **diagonal** running from the **top-right corner to the bottom-left corner** (`/` shape)
- The split condition: `row + col == 11` → neutral strip (rendered darker, no cells placed here)

```
      A    B    C    D    E    F    G    H    I    J    K    L
 1  [ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ /  ]
 2  [ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ /  ][ R  ]
 3  [ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ B  ][ /  ][ R  ][ R  ]
    ...
12  [ /  ][ R  ][ R  ][ R  ][ R  ][ R  ][ R  ][ R  ][ R  ][ R  ][ R  ][ R  ]
```

- **Blue** occupies the upper-left triangle (`row + col < 11`)
- **Red** occupies the lower-right triangle (`row + col > 11`)
- The `/` diagonal strip is neutral — no cells, no tokens

---

## 2. Cell Placement

- Each player starts with **24 living cells**
- Cells are **randomly distributed** within the player's triangle
- Distribution is **corner-biased** — cells cluster strongly toward the home corner:
  - Blue clusters toward the **top-left** `(row 0, col 0)`
  - Red clusters toward the **bottom-right** `(row 11, col 11)`
- The further from the home corner, the less likely a cell appears there

---

## 3. Terrain

Two terrain types are scattered across the board at game start, weighted toward the mid-board area near the diagonal. Terrain blocks attack rays.

| Terrain | Colour | HP | Behaviour |
|---------|--------|----|-----------|
| **Hard** | Dark slate | ∞ | **Indestructible.** Permanently blocks any ray that hits it. Cannot be damaged. |
| **Soft** | Warm brown | 2 | Takes 2 hits to destroy. Blocks rays until fully destroyed. Once destroyed, rays pass through the empty space. |

- Terrain is **neutral** — it does not belong to either player
- Hitting terrain gives **no kill credit**
- Hard terrain is drawn with a cross (`×`) pattern to distinguish it from empty cells
- Soft terrain shows small HP pip indicators in its top-left corner

---

## 4. Tokens

Each player has exactly **3 tokens** per turn:

| Token | Name | Function |
|-------|------|----------|
| ATK-A | Attack A | Fires a ray in a chosen direction — hits the first enemy cell or soft terrain on that line |
| ATK-B | Attack B | Independent second attacker — same mechanics as ATK-A |
| DEF   | Defense  | Shields the cell it occupies — the next hit on that cell is absorbed |

**Placement rules:**
- Tokens must be placed on **your own living cells** (not empty squares, not dead cells, not enemy cells)
- **DEF may not share a cell with an ATK token**
- ATK-A and ATK-B **may** share a cell (stacking — see Section 8)
- Moving a token that was already placed marks it as **MOVED** — it acts as a placeholder that turn but does not fire or shield

---

## 5. Attack Directions

When placing an ATK token, the player chooses **one of 3 directions**. Directions are relative to the attacker's side:

| Direction | Blue fires | Red fires |
|-----------|-----------|-----------|
| Horizontal | → right | ← left |
| Vertical | ↓ down | ↑ up |
| Diagonal | ↘ down-right | ↖ up-left |

All three directions point **toward the enemy's side of the board**.

The direction is locked in after placement. Moving the token to a new cell requires choosing a direction again.

**Area of effect visibility:** After a direction is chosen, the full ray path is highlighted on the board:
- **Dim yellow** — ray path (cells the ray passes through)
- **Bright red** — the actual target (first enemy cell on the ray)
- **Orange** — ray blocked by terrain

---

## 6. Attack Ray Rules

- The ray fires from the token's cell in the chosen direction
- It travels cell by cell until it finds a target
- **What the ray passes through:** empty cells, your own cells, the neutral diagonal strip, destroyed soft terrain
- **What the ray hits (and stops at):**
  - First **living enemy cell** → damages it
  - First **living soft terrain** → damages it (no kill credit)
  - First **hard terrain** → stops, no damage dealt

---

## 7. Damage & HP

| Target | HP | Result when HP reaches 0 |
|--------|----|--------------------------|
| Normal cell (unshielded) | 1 | Destroyed in one hit |
| Shielded cell | — | First hit absorbed by shield; cell survives with HP intact |
| Shielded cell (second hit) | 1 → 0 | Destroyed |
| Soft terrain | 2 | Two hits to destroy; shows HP pips |
| Hard terrain | ∞ | Cannot be destroyed |

- Destroyed cells remain on the board as **ghost markers** (faded colour, no function)
- There is no healing or respawning

---

## 8. Defense Mechanics

- The DEF token **shields** the cell it occupies
- A shielded cell **absorbs the next hit** it receives — that hit deals no damage and the shield is consumed
- If the shielded cell is not attacked that round, the shield **expires** (does not carry over to the next round)
- Shielding an already-dead cell has no effect

---

## 9. Stacked Attack

If **ATK-A and ATK-B are placed on the same cell** and neither was moved that turn:

- They fire together as a **combined stack**
- The stack hits the first enemy on the ray, then also hits **all adjacent enemies** around the target (AOE)
- The direction used is ATK-A's direction

---

## 10. Turn Structure

### Game Start — Initial Placement (one time only)

Before Round 1 fires, both players place their tokens without any damage happening:

```
King setup (Blue) → look away → King setup (Red)
    → Blue places tokens → Done → look away
    → Red places tokens → Done
    → Normal turn-based play begins
```

This ensures neither player is hit before having a chance to place their defense.

### Each Turn (Rounds 1, 2, 3, ...)

1. **Active player places tokens** — ATK-A, ATK-B, and/or DEF on their living cells
2. **For ATK tokens** — choose a direction (Horizontal / Vertical / Diagonal) after placing
3. **Click Resolve** — all effects fire in this order:
   - Clear own shields from the previous round
   - Apply DEF shield to its cell (and an adjacent cell if DEF+ is unlocked)
   - Fire ATK tokens (or stacked combo if both ATK on same cell)
   - Apply Splash if unlocked
   - Fire Bonus Attack from ATK-A if T3 is unlocked
   - Check win conditions
4. **Device passes** to the other player — they take their turn

Tokens are re-placed every turn. A token that was **moved** from one cell to another fires no attack that turn.

---

## 11. Win Conditions

| Condition | Result |
|-----------|--------|
| All enemy cells are destroyed | Current player wins |
| The enemy's **King cell** is destroyed | Instant win |

---

## 12. King Cell

- Before the first turn, each player secretly clicks one of their cells to designate as their **King**
- Blue places King first, then looks away — Red places King privately
- The King is marked with a **K** on the board — visible to its owner, but the opponent must figure out which cell it is through play
- If the King is destroyed, the owning player loses **immediately**, regardless of how many cells remain

---

## 13. Upgrades

Upgrades unlock automatically when a player's kill count reaches the threshold. They apply from that point forward.

| Kills | Key | Name | Effect |
|-------|-----|------|--------|
| 3  | t2   | Splash    | ATK also hits one adjacent enemy cell after the primary hit |
| 6  | dt2  | DEF+      | DEF also shields one adjacent friendly cell |
| 10 | t3   | Bonus ATK | ATK-A fires a second attack from its position each resolve |
| 15 | nuke | NUKE      | Unlocks a one-time **3×3 area blast** activated manually |

**Tracking:** Both players' upgrade progress is visible in the UI at all times — kill count, progress bar to next unlock, and status of each upgrade (locked / active / newly unlocked).

**Upgrade pips:** Small gold dots appear in the corner of a token's cell on the board to show how many upgrades are active.

---

## 14. Nuke

- Unlocks at **15 kills**
- One-time use — consumed on activation
- Player clicks the **NUKE** button to enter targeting mode, then clicks any enemy cell
- Destroys all enemy cells in a **3×3 area** centred on the target
- Win conditions are checked immediately after

---

## 15. UI Reference

### Panel layout
The bottom panel is always split into two halves:
- **Left half — Blue** at all times
- **Right half — Red** at all times

Each half shows:
- Token buttons (ATK-A, ATK-B, DEF) with current position and direction
- Kill count with progress bar to next upgrade
- All 4 upgrade rows with status

### Legend

| Colour | Meaning |
|--------|---------|
| Dark blue | Blue alive cell |
| Faded blue | Blue dead cell (ghost) |
| Dark red | Red alive cell |
| Faded red | Red dead cell (ghost) |
| Dark slate + × | Hard terrain (indestructible) |
| Warm brown | Soft terrain (2 hits to destroy) |
| Green border | Shield active on this cell |
| Orange border | Nuke targeting mode |
| Dim yellow overlay | Attack ray path |
| Bright red overlay | Attack target (will be hit this turn) |
| Orange overlay | Ray blocked by terrain |
| Green overlay | DEF shield coverage area |
| Gold dots (bottom-right of cell) | Active upgrades on token |

---

## 16. Quick Reference

| Rule | Value |
|------|-------|
| Grid | 12 × 12 |
| Board split | Diagonal `/` at `row + col = 11` |
| Cells per player | 24, corner-biased |
| Tokens per player | 3 (ATK-A, ATK-B, DEF) |
| Attack directions | 3 (Horizontal, Vertical, Diagonal — toward enemy) |
| Normal cell HP | 1 (one hit = destroyed) |
| Shielded cell | Absorbs first hit; then 1 HP |
| Hard terrain | Indestructible, permanently blocks rays |
| Soft terrain HP | 2 (blocks until destroyed, then ray passes through) |
| Upgrade kills | 3 / 6 / 10 / 15 |
| Nuke area | 3 × 3 centred on target |
| Win by attrition | All enemy cells destroyed |
| Win by king kill | King cell destroyed (instant) |
