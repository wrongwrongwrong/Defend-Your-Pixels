# PixelWar — Game Logic Reference

## 1. Board

- Grid is **6×6** in the demo (scales to 12×12 in full game)
- The board is divided by a **diagonal line** running from the **top-right corner** to the **bottom-left corner** (a `/` shape)
- This creates two triangular halves — one per player

```
      A    B    C    D    E    F
 1  [ ·  ][ ·  ][ ·  ][ ·  ][ ·  ][ /  ]  ← top-right corner
 2  [ ·  ][ ·  ][ ·  ][ ·  ][ /  ][ ·  ]
 3  [ ·  ][ ·  ][ ·  ][ /  ][ ·  ][ ·  ]
 4  [ ·  ][ ·  ][ /  ][ ·  ][ ·  ][ ·  ]
 5  [ ·  ][ /  ][ ·  ][ ·  ][ ·  ][ ·  ]
 6  [ /  ][ ·  ][ ·  ][ ·  ][ ·  ][ ·  ]  ← bottom-left corner
```

- Each player's cells are **randomly scattered** within their own triangle at the start
- The diagonal `/` border cells are **neutral** — tokens pass through them

---

## 2. Tokens

Each player has exactly **3 tokens**:

| Token | Name | Function |
|-------|------|----------|
| ATK-A | Attack A | Fires in a chosen direction, destroys first enemy cell hit |
| ATK-B | Attack B | Same as ATK-A, independent second attacker |
| DEF   | Defense  | Shields the cell it sits on — blocks one incoming hit |

---

## 3. Turn Structure

### Step 1 — Both Players Place Tokens
- **The turn does not resolve until both players have placed all 3 of their tokens**
- Players place tokens privately (hot-seat: one player looks away while the other places)
- Tokens can be placed on **any cell within your own half** of the diagonal — including empty territory squares, not just squares with your own alive cells
- **DEF may not share a square with an ATK token**
- ATK-A and ATK-B may share a square (stacking — advanced mechanic, ignored for now)

### Step 2 — Resolution (Simultaneous)
All token effects resolve at the same time in this order:

1. **Shields are applied** — DEF tokens shield their cell before any attacks fire
2. **All ATK tokens fire simultaneously** — a cell that is being destroyed this round still fires its attack before disappearing

### Step 3 — Repeat
- Both players re-place tokens each round (can move, redirect, or keep the same)
- There is no "cooldown" — every token is available every round

---

## 4. Attack Mechanics

- When placing an ATK token, the player **chooses a direction**
- Valid directions: **8 total** — the 4 cardinal directions (N, S, E, W) and the 4 diagonal directions (NE, NW, SE, SW)
- On resolve, the attack fires a ray from the token's position in that direction
- The ray travels cell by cell until it hits the **first enemy cell** in its path
- **One hit = one cell destroyed** — no HP, no partial damage
- Empty cells, empty territory, and the diagonal border are **passed through**
- Friendly cells are also **passed through** (attacks do not harm your own pieces)

---

## 5. Defense Mechanics

- The DEF token **shields** the cell it occupies
- A shielded cell **blocks the next hit it receives**, then the shield is gone
- If the shielded cell is not attacked, the shield expires at the end of the round (does not carry over)
- Shielding an empty territory square has no practical effect

---

## 6. Cell Rules

- Each cell has effectively **1 hit point** — one attack = destroyed
- Destroyed cells remain on the board as ghost markers (visual only)
- There is no healing or respawning

---

## 7. Win Conditions

| Condition | Result |
|-----------|--------|
| All enemy cells are destroyed | Current player wins |
| The enemy's **King cell** is destroyed | Instant win (full game only) |

---

## 8. King Cell (Full Game Only)

- Before the first turn, each player secretly designates one of their cells as their **King**
- If the King is destroyed, the owning player loses immediately, regardless of remaining cells
- The King is not visually distinct to the opponent — choosing the right cell to defend is strategic

---

## 9. Upgrades (Full Game Only)

Earned by accumulating kills over multiple rounds:

| Kills | Upgrade | Effect |
|-------|---------|--------|
| 5  | ATK Tier 2 | Attack also hits one adjacent enemy cell after the primary hit |
| 10 | DEF Tier 2 | DEF also shields one adjacent friendly cell |
| 15 | Bonus Attack | ATK-A fires a second shot from the same position |
| 20 | Nuke | One-time use: destroys all cells in a 3×3 area |

---

## 10. Summary of Rules (Quick Reference)

- Diagonal `/` splits the board — one team per side
- Tokens go anywhere on your half — even empty squares
- Both players must place all tokens before anything resolves
- ATK fires in 1 of 8 directions, hits the first enemy cell in the line
- DEF shields one cell, blocks one hit, expires end of round
- One hit = cell destroyed, no HP
- Resolution is simultaneous — dying cells still fire
- DEF and ATK cannot share the same square
