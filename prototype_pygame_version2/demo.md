# PixelWar — Quick Demo (6×6)

## Setup

**Grid:** 6×6, split by a `/` diagonal from **F1** (top-right) down to **A6** (bottom-left).
- **Blue** occupies the lower-right triangle
- **Red** occupies the upper-left triangle

**Starting cells (3 per player):**
| Player | Cells |
|--------|-------|
| Blue   | F3, E4, D5 |
| Red    | E1, D2, C3 |

**Each player has 3 tokens:** ATK-A · ATK-B · DEF

---

## Initial Board

|   | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| **1** | · | · | · | · | R | / |
| **2** | · | · | · | R | / | · |
| **3** | · | · | R | / | · | B |
| **4** | · | · | / | · | B | · |
| **5** | · | / | · | B | · | · |
| **6** | / | · | · | · | · | · |

> `/` = diagonal border · `B` = Blue cell · `R` = Red cell · `·` = empty

---

## Round 1

### Token Placement

**Blue places:**
| Token | Cell | Direction |
|-------|------|-----------|
| ATK-A | F3   | ← West    |
| ATK-B | E4   | ↑ North   |
| DEF   | D5   | shields D5 |

**Red places:**
| Token | Cell | Direction |
|-------|------|-----------|
| ATK-A | E1   | ↓ South   |
| ATK-B | D2   | ↓ South   |
| DEF   | C3   | shields C3 |

---

### Resolution (all simultaneous)

**Shields applied first:** D5 (Blue) · C3 (Red)

| Token | Path | Result |
|-------|------|--------|
| Blue ATK-A (F3 →W) | F3 → E3 → D3`/` → **C3** | 🛡 C3 shielded — **blocked!** Shield used up. |
| Blue ATK-B (E4 →N) | E4 → E3 → E2`/` → **E1** | 💥 E1 destroyed |
| Red ATK-A  (E1 →S) | E1 → E2`/` → E3 → **E4** | 💥 E4 destroyed *(fires before being destroyed)* |
| Red ATK-B  (D2 →S) | D2 → D3`/` → D4 → **D5** | 🛡 D5 shielded — **blocked!** Shield used up. |

### Board After Round 1

|   | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| **1** | · | · | · | · | ✕ | / |
| **2** | · | · | · | R | / | · |
| **3** | · | · | R | / | · | B |
| **4** | · | · | / | · | ✕ | · |
| **5** | · | / | · | B | · | · |
| **6** | / | · | · | · | · | · |

> `✕` = destroyed

**Score:** Blue lost E4 · Red lost E1 · Shields on D5 and C3 are now spent.

---

## Round 2

### Token Placement

**Blue places:**
| Token | Cell | Direction | Note |
|-------|------|-----------|------|
| ATK-A | F4 *(empty Blue territory)* | ↖ NW | Bypasses diagonal, hits D2 |
| ATK-B | E3 *(empty Blue territory)* | ← West | Passes diagonal, hits C3 |
| DEF   | F3 | shields F3 | |

**Red places:**
| Token | Cell | Direction | Note |
|-------|------|-----------|------|
| ATK-A | C3   | → East | Passes diagonal, hits F3 |
| ATK-B | D2   | ↓ South | Passes diagonal, hits D5 |
| DEF   | — | *(not placed)* | No cells left to protect |

---

### Resolution

**Shields applied first:** F3 (Blue) · none (Red)

| Token | Path | Result |
|-------|------|--------|
| Blue ATK-A (F4 →NW) | F4 → E3 → D2`/`... → **D2** | 💥 D2 destroyed |
| Blue ATK-B (E3 →W)  | E3 → D3`/` → **C3** | 💥 C3 destroyed |
| Red ATK-A  (C3 →E)  | C3 → D3`/` → E3 → **F3** | 🛡 F3 shielded — **blocked!** *(fires before destroyed)* |
| Red ATK-B  (D2 →S)  | D2 → D3`/` → D4 → **D5** | 💥 D5 destroyed *(fires before destroyed)* |

### Board After Round 2

|   | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| **1** | · | · | · | · | ✕ | / |
| **2** | · | · | · | ✕ | / | · |
| **3** | · | · | ✕ | / | · | B |
| **4** | · | · | / | · | ✕ | · |
| **5** | · | / | · | ✕ | · | · |
| **6** | / | · | · | · | · | · |

---

## 🏆 Result: Blue Wins

All 3 Red cells destroyed. Blue's F3 survives.

| | Blue | Red |
|--|------|-----|
| Cells remaining | **F3** (1 cell) | **0 cells** |
| Cells lost | E4, D5 | E1, D2, C3 |

---

## Key Mechanics Demonstrated

- **Tokens can be placed on empty territory** — Blue fired from F4 and E3, both empty Blue squares
- **Simultaneous resolution** — Red's E1 and D2 fired their attacks even as they were being destroyed
- **Shields block one hit** — C3's DEF absorbed Blue ATK-A in Round 1; F3's DEF absorbed Red ATK-A in Round 2
- **Attacks pass through empty cells and the diagonal border** — hitting only the first enemy cell in the chosen direction
