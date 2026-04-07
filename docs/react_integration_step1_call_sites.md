# Step 1：前端規則函式呼叫點盤點

主程式目錄：`react_frontend/src`（`archive/react_frontend_ui_reference` 為備份，不列入整合修改範圍）。

## `createInitialGameState`

| 檔案 | 用途 | 整合後預期 |
|------|------|------------|
| [`turns.js`](../react_frontend/src/game/turns.js) | 定義 | 保留為 **fallback 初始狀態** |
| [`useWebSocket.js`](../react_frontend/src/hooks/bridge/useWebSocket.js) | `useState` 初值、`board_state` 正規化基底 | 保留 |

## `endTurn`

| 檔案 | 用途 | 整合後預期 |
|------|------|------------|
| [`turns.js`](../react_frontend/src/game/turns.js) | 定義（內用 `phaseForTurn`） | 改為 **僅 mock / 離線測試**，或刪除呼叫改由後端推狀態 |
| [`gameLogic.js`](../react_frontend/src/game/gameLogic.js) | re-export | 同上 |
| [`App.jsx`](../react_frontend/src/app/App.jsx) | `handleEndTurn` → `setGameState(endTurn)` | 改為送 **action** 給 Python，或以 `board_state` 反映結果 |

## `trySpendEther`

| 檔案 | 用途 | 整合後預期 |
|------|------|------------|
| [`ether.js`](../react_frontend/src/game/ether.js) | 定義 | 保留為純函式可給單機測試；**權威扣款在 Python** |
| [`gameLogic.js`](../react_frontend/src/game/gameLogic.js) | re-export | 同上 |
| [`App.jsx`](../react_frontend/src/app/App.jsx) | `handleUpgrade` 內扣 5 ether | 改為後端驗證；前端僅樂觀 UI 或等 `board_state` |

## `phaseForTurn`

| 檔案 | 用途 | 整合後預期 |
|------|------|------------|
| [`turns.js`](../react_frontend/src/game/turns.js) | 定義；`endTurn` 內呼叫 | 第一版 contract 可不送 phase 時，仍可由 mock `endTurn` 更新，或改為 **Python 下發 `phase`** |
| [`gameLogic.js`](../react_frontend/src/game/gameLogic.js) | re-export | 無其他 import；整合後可停止 re-export 若不再使用 |

**備註：** `phaseForTurn` 目前**沒有被** `App.jsx` 或其他元件直接 import；`PhaseIndicator` 只吃 `gameState.phase`（由 `endTurn` / 初始 state 寫入）。

## `getEther` / `addEther`

| 檔案 | 用途 | 整合後預期 |
|------|------|------------|
| [`ether.js`](../react_frontend/src/game/ether.js) | 定義 | 目前 **react_frontend 內無其他引用**；可保留供測試或刪減 export |

## 摘要

- **實際驅動 UI 規則的呼叫鏈：** `App.jsx` → `endTurn`、`trySpendEther`；WebSocket → 僅 `applyTrackedTokens`（位置/朝向）。
- **下一階段：** 見 [`board_state_v1.md`](board_state_v1.md) 與 `useWebSocket` 中 `board_state` 全量替換路徑。
