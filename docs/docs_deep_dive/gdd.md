# Old Mick Against the Mob — Game Design Document

## Overview
2-player asymmetric strategy game. 12×12 grid split diagonally.
Farmer side (bottom-left): Old Mick's Paddock — red dirt, wheat rows.
Emu side (top-right): The Scrublands — dense bush.
The diagonal is the fence line.

## Sides
Farmer territory cells: Wheat Paddocks
Emu territory cells: Feeding Grounds

## Tokens
| Role | Farmer Side | Emu Side |
|------|-------------|----------|
| ATK × 2 | The Riflemen | The Mob |
| DEF × 1 | Old Mick | Cassowary |
| Hidden HQ × 1 | The Homestead | The Nest |

## Terrain (both sides)
| Type | Name | Effect |
|------|------|--------|
| Hard × 3 | Rocks | Impassable. Permanently blocks straight-line attacks. |
| Soft × 3 | Termite Mounds | Slows tokens passing through. Takes 2 hits to destroy. |

## Movement & Combat
- All tokens move in a straight line only — horizontal, vertical, or diagonal
- Unlimited range, line must be clear
- ATK tokens hit the first enemy cell across the fence and return
- DEF tokens reposition using the same movement — uses their action for that turn
- Hard terrain permanently blocks lines
- Soft terrain slows tokens, takes 2 hits to clear

## Cell HP
- Default: 1 hit to destroy
- Inside DEF patrol zone: +1 HP, takes 2 hits to destroy
- DEF patrol zone: 3×3 default, expands to 5×5 after Tier 2 upgrade

## Upgrades
Farmer funds upgrades by destroying Feeding Grounds.
Emu funds upgrades by raiding Wheat Paddocks.

| Tier | Type | Farmer | Emu |
|------|------|--------|-----|
| 1 | ATK | Better Aim — The Riflemen | First Lesson — The Mob |
| 2 | DEF | Machine Gun Nest — Old Mick | Dark Awakening — Cassowary |
| 3 | ATK | Call Canberra — The Riflemen | The Stampede — The Mob |
| 4 | NUKE | Unleash Keith | The Ancestors |

Tier 1 & 3: ATK token hits target + 1 neighbour / target + 2 neighbours
Tier 2: DEF patrol zone expands 3×3 → 5×5
Tier 4: 3×3 area destruction anywhere on enemy territory. One use only.

## Win Conditions
### Instant wins
- Farmer: Destroy the Nest → game ends immediately
- Emu: Destroy the Homestead → game ends immediately

### Attrition wins
- Farmer: Destroy enough Feeding Grounds — mob can't sustain
- Emu: Raze enough Wheat Paddocks — farm can't fund riflemen or upgrades