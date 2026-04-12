# How to Run — yuhsuan_test

## Install dependencies
```bash
pip install -r requirements.txt
```

## Run
Open two terminals from the `yuhsuan_test/` folder:

**Terminal 1 — backend (camera + detection)**
```bash
python server.py
```

**Terminal 2 — frontend**
```bash
open index.html
```
Or just double-click `index.html` to open it in a browser.

---

## Marker ID reference

| ID  | Role              |
|-----|-------------------|
| 0   | Board corner TL   |
| 1   | Board corner TR   |
| 2   | Board corner BL   |
| 3   | Board corner BR   |
| 10  | P1 ATK-A          |
| 11  | P1 ATK-B          |
| 12  | P1 DEF            |
| 14  | P2 ATK-A          |
| 15  | P2 ATK-B          |
| 16  | P2 DEF            |
| 20  | Turn marker       |

## Token rotation → direction

| Rotation | ATK direction | Turn marker |
|----------|---------------|-------------|
| ~0°      | HORIZONTAL    | P1's turn   |
| ~90°     | VERTICAL      | —           |
| ~180°    | DIAGONAL      | P2's turn   |

## Board layout

The board is printed as **14×14** but only the inner **12×12** is playable.
The outer strip protects the 4 corner markers from being covered by tokens.

```
[0] ─────────────────── [1]
 │   ┌───────────────┐   │
 │   │  Blue (P1)    │   │
 │   │       ╲       │   │  [20] ← turn marker
 │   │   ╲   Red(P2) │   │   (placed outside the board)
 │   └───────────────┘   │
[2] ─────────────────── [3]
```

Blue = upper-left triangle (row + col < 11)
Red  = lower-right triangle (row + col > 11)
